"""
Routes pour les Leads
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import APIKeyHeader
from typing import Optional
import uuid

from models import LeadSubmit
from config import db, now_iso, timestamp, validate_phone_fr
from routes.auth import get_current_user, require_admin
from services.lead_sender import send_to_crm, add_to_queue

router = APIRouter(tags=["Leads"])

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_api_key(authorization: Optional[str] = Header(None)):
    """Valide la clé API RDZ"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Clé API manquante")
    
    parts = authorization.split(" ")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Format clé invalide")
    
    token = parts[1]
    
    config = await db.system_config.find_one({"type": "global_api_key"})
    if config and config.get("api_key") == token:
        return token
    
    raise HTTPException(status_code=401, detail="Clé API invalide")


# ==================== API EXTERNE (avec clé API RDZ) ====================

@router.get("/leads/export")
async def get_leads_api(
    form_code: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    api_key: str = Depends(get_api_key)
):
    """
    Récupérer les leads depuis RDZ avec la clé API.
    
    Paramètres:
    - form_code: Filtrer par code formulaire
    - status: Filtrer par statut (success, failed, queued, no_crm)
    - since: Leads depuis cette date ISO (ex: 2024-01-01T00:00:00)
    - limit: Nombre max de leads (défaut: 100, max: 1000)
    
    Exemple:
    GET /api/v1/leads?form_code=PV-007&limit=50
    Authorization: Token VOTRE_CLE_API_RDZ
    """
    query = {}
    
    if form_code:
        query["form_code"] = form_code
    if status:
        query["api_status"] = status
    if since:
        query["created_at"] = {"$gte": since}
    
    # Limiter à 1000 max
    limit = min(limit, 1000)
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    total = await db.leads.count_documents(query)
    
    return {
        "success": True,
        "leads": leads,
        "count": len(leads),
        "total": total
    }

@router.post("/v1/leads")
async def submit_lead_v1(data: LeadSubmit, request: Request, api_key: str = Depends(get_api_key)):
    """
    API v1 - Soumission de lead depuis un formulaire externe.
    Authentification par clé API globale.
    
    Flow:
    1. Valider téléphone
    2. Récupérer config formulaire
    3. Router vers le bon CRM (ZR7/MDL) selon commandes
    4. Envoyer au CRM externe
    5. Si échec → mettre en file d'attente
    """
    # 1. Valider téléphone
    is_valid, phone_result = validate_phone_fr(data.phone)
    if not is_valid:
        return {"success": False, "error": phone_result}
    phone = phone_result
    
    # Récupérer département directement
    dept = data.departement or ""
    
    # 2. Récupérer config formulaire (par code ou ID)
    form = await db.forms.find_one({
        "$or": [{"id": data.form_id}, {"code": data.form_id}]
    })
    
    if not form:
        return {"success": False, "error": "Formulaire non trouvé"}
    
    form_code = form.get("code", "")
    product_type = form.get("product_type", "PV")
    account_id = form.get("account_id", "")
    allow_cross_crm = form.get("allow_cross_crm", True)  # Cross-CRM par défaut
    
    # Récupérer le compte et son CRM principal
    account = await db.accounts.find_one({"id": account_id})
    primary_crm_id = account.get("crm_id") if account else None
    
    # Import de la fonction has_commande
    from routes.commandes import has_commande
    
    # 3. Router vers le bon CRM selon les commandes
    target_crm = None
    routing_reason = "no_crm"
    api_url = ""
    api_key_crm = form.get("crm_api_key", "")
    is_transferred = False  # Sera True si cross-CRM
    
    # Récupérer le CRM d'origine du compte
    origin_crm_slug = None
    origin_crm = await db.crms.find_one({"id": primary_crm_id}, {"_id": 0}) if primary_crm_id else None
    if origin_crm:
        origin_crm_slug = origin_crm.get("slug")
    
    # Récupérer tous les CRMs
    all_crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {c["id"]: c for c in all_crms}
    
    # Étape 3a: Vérifier le CRM principal (celui du compte)
    if primary_crm_id and api_key_crm:
        if await has_commande(primary_crm_id, product_type, dept):
            target_crm = crm_map.get(primary_crm_id)
            routing_reason = f"commande_{target_crm.get('slug')}" if target_crm else "primary_crm"
    
    # Étape 3b: Si pas de commande sur CRM principal ET cross_crm autorisé
    if not target_crm and allow_cross_crm and api_key_crm:
        # Chercher un autre CRM qui a une commande
        for crm_id, crm in crm_map.items():
            if crm_id != primary_crm_id:
                if await has_commande(crm_id, product_type, dept):
                    target_crm = crm
                    routing_reason = f"cross_crm_{crm.get('slug')}"
                    is_transferred = True  # Transfert inter-CRM !
                    break
    
    # Étape 3c: Si toujours pas de CRM, stocker localement
    if not target_crm:
        routing_reason = "no_commande"
        api_status = "no_crm"
    else:
        api_url = target_crm.get("api_url", "")
        api_status = "pending"
    
    # 4. Créer le document lead
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": form.get("id"),
        "form_code": form_code,
        "account_id": account_id,
        "product_type": product_type,
        # Identité
        "phone": phone,
        "nom": data.nom or "",
        "prenom": data.prenom or "",
        "civilite": data.civilite or "",
        "email": data.email or "",
        # Localisation
        "departement": dept,
        "ville": data.ville or "",
        "adresse": data.adresse or "",
        # Logement
        "type_logement": data.type_logement or "",
        "statut_occupant": data.statut_occupant or "",
        "surface_habitable": data.surface_habitable or "",
        "annee_construction": data.annee_construction or "",
        "type_chauffage": data.type_chauffage or "",
        # Énergie
        "facture_electricite": data.facture_electricite or "",
        "facture_chauffage": data.facture_chauffage or "",
        # Projet
        "type_projet": data.type_projet or "",
        "delai_projet": data.delai_projet or "",
        "budget": data.budget or "",
        # Tracking
        "lp_code": data.lp_code or "",
        "liaison_code": data.liaison_code or "",
        "source": data.source or "",
        "utm_source": data.utm_source or "",
        "utm_medium": data.utm_medium or "",
        "utm_campaign": data.utm_campaign or "",
        # Consentement
        "rgpd_consent": data.rgpd_consent if data.rgpd_consent is not None else True,
        "newsletter": data.newsletter or False,
        # Metadata
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        # CRM info - Schéma normalisé
        "origin_crm": origin_crm_slug or "",  # CRM d'origine (compte) - slug
        "target_crm": target_crm.get("slug") if target_crm else "none",  # CRM destination - slug
        "is_transferred": is_transferred,  # Transféré inter-CRM ?
        "routing_reason": routing_reason,
        "allow_cross_crm": allow_cross_crm,
        "api_status": api_status,
        "sent_to_crm": False
    }
    
    await db.leads.insert_one(lead_doc)
    
    # 5. Envoyer au CRM externe si on a une cible
    if target_crm and api_url and api_key_crm:
        status, response, should_queue = await send_to_crm(lead_doc, api_url, api_key_crm)
        
        if should_queue:
            await add_to_queue(lead_doc, api_url, api_key_crm, "crm_error")
            status = "queued"
        
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "api_status": status,
                "api_response": response,
                "sent_to_crm": status in ["success", "duplicate"],
                "sent_at": now_iso() if status in ["success", "duplicate"] else None
            }}
        )
        
        return {
            "success": status in ["success", "duplicate", "queued"],
            "lead_id": lead_doc["id"],
            "status": status,
            "message": "Lead enregistré" if status == "queued" else ("Lead envoyé" if status == "success" else response)
        }
    else:
        # Pas de CRM configuré - lead sauvegardé
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {"api_status": "no_crm", "routing_reason": "no_order"}}
        )
        return {
            "success": True,
            "lead_id": lead_doc["id"],
            "status": "no_crm",
            "message": "Lead enregistré (pas de commande active)"
        }


# ==================== ROUTES INTERNES ====================

@router.get("/leads")
async def list_leads(
    form_code: str = None,
    status: str = None,
    crm_id: str = None,
    transferred: bool = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Liste les leads avec filtres, y compris par CRM, transfert et période"""
    query = {}
    if form_code:
        query["form_code"] = form_code
    if status:
        query["api_status"] = status
    
    # Filtrer par CRM via les accounts
    if crm_id:
        # Récupérer les IDs des accounts de ce CRM
        accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(1000)
        account_ids = [a["id"] for a in accounts]
        query["account_id"] = {"$in": account_ids}
    
    # Filtrer par leads transférés
    if transferred is not None:
        query["is_transferred"] = transferred
    
    # Filtrer par période
    if date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            # Ajouter T23:59:59 pour inclure toute la journée
            date_query["$lte"] = date_to + "T23:59:59" if "T" not in date_to else date_to
        if date_query:
            query["created_at"] = date_query
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    total = await db.leads.count_documents(query)
    
    # Ajouter origin_crm pour les anciens leads qui n'en ont pas
    for lead in leads:
        if not lead.get("origin_crm"):
            # Récupérer depuis le compte
            account = await db.accounts.find_one({"id": lead.get("account_id")}, {"crm_id": 1})
            if account and account.get("crm_id"):
                crm = await db.crms.find_one({"id": account["crm_id"]}, {"slug": 1})
                lead["origin_crm"] = crm.get("slug") if crm else lead.get("target_crm", "")
            else:
                lead["origin_crm"] = lead.get("target_crm", "")
    
    return {"leads": leads, "count": len(leads), "total": total}


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Récupère un lead par ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    return lead


@router.post("/leads/{lead_id}/retry")
async def retry_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Retenter l'envoi d'un lead avec la logique de commandes"""
    from routes.commandes import has_commande
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Récupérer config
    form = await db.forms.find_one({"code": lead.get("form_code")})
    if not form:
        return {"success": False, "error": "Formulaire non trouvé"}
    
    api_key_crm = form.get("crm_api_key")
    if not api_key_crm:
        return {"success": False, "error": "Clé API CRM non configurée sur le formulaire"}
    
    allow_cross_crm = form.get("allow_cross_crm", True)
    product_type = form.get("product_type", "PV")
    dept = lead.get("departement", "")
    
    account = await db.accounts.find_one({"id": form.get("account_id")})
    primary_crm_id = account.get("crm_id") if account else None
    
    # Chercher un CRM avec commande active
    all_crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {c["id"]: c for c in all_crms}
    
    target_crm = None
    routing_reason = "no_commande"
    
    # Essayer le CRM principal
    if primary_crm_id:
        if await has_commande(primary_crm_id, product_type, dept):
            target_crm = crm_map.get(primary_crm_id)
            routing_reason = f"commande_{target_crm.get('slug')}" if target_crm else "primary"
    
    # Cross-CRM si autorisé
    if not target_crm and allow_cross_crm:
        for crm_id, crm in crm_map.items():
            if crm_id != primary_crm_id:
                if await has_commande(crm_id, product_type, dept):
                    target_crm = crm
                    routing_reason = f"cross_crm_{crm.get('slug')}"
                    break
    
    if not target_crm:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"api_status": "no_crm", "routing_reason": "no_commande", "retried_at": now_iso()}}
        )
        return {"success": False, "error": "Aucun CRM avec commande active pour ce département/produit"}
    
    # Envoyer au CRM
    status, response, _ = await send_to_crm(lead, target_crm.get("api_url"), api_key_crm)
    
    # Déterminer si c'est un transfert
    is_transferred = routing_reason.startswith("cross_crm_")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "api_response": response,
            "sent_to_crm": status in ["success", "duplicate"],
            "target_crm": target_crm.get("slug"),  # Schéma normalisé
            "is_transferred": is_transferred,
            "routing_reason": routing_reason,
            "retried_at": now_iso(),
            "retry_count": lead.get("retry_count", 0) + 1
        }}
    )
    
    return {"success": status in ["success", "duplicate"], "status": status, "crm": target_crm.get("slug")}


@router.delete("/leads/{lead_id}")
async def archive_lead(lead_id: str, user: dict = Depends(get_current_user)):
    """Archive un lead (soft delete)"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Copier dans archives
    lead["archived_at"] = now_iso()
    lead["archived_by"] = user["id"]
    await db.leads_archived.insert_one(lead)
    
    # Supprimer de la collection principale
    await db.leads.delete_one({"id": lead_id})
    
    return {"success": True}


@router.get("/leads/stats/global")
async def get_leads_stats(crm_id: str = None, user: dict = Depends(get_current_user)):
    """Stats globales des leads, optionnellement filtrées par CRM"""
    query = {}
    
    # Filtrer par CRM via les accounts
    if crm_id:
        accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(1000)
        account_ids = [a["id"] for a in accounts]
        query["account_id"] = {"$in": account_ids}
    
    total = await db.leads.count_documents(query)
    
    success_query = {**query, "api_status": "success"}
    duplicate_query = {**query, "api_status": "duplicate"}
    failed_query = {**query, "api_status": "failed"}
    queued_query = {**query, "api_status": "queued"}
    no_crm_query = {**query, "api_status": "no_crm"}
    
    success = await db.leads.count_documents(success_query)
    duplicate = await db.leads.count_documents(duplicate_query)
    failed = await db.leads.count_documents(failed_query)
    queued = await db.leads.count_documents(queued_query)
    no_crm = await db.leads.count_documents(no_crm_query)
    
    return {
        "total": total,
        "success": success,
        "duplicate": duplicate,
        "failed": failed,
        "queued": queued,
        "no_crm": no_crm,
        "sent_rate": round((success + duplicate) / total * 100, 1) if total > 0 else 0
    }
