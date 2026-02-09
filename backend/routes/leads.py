"""
Routes pour les Leads
- Réception via API v1 (externe)
- Liste et gestion interne
- Routage intelligent vers CRM
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import APIKeyHeader
from typing import Optional
import uuid

from models import LeadSubmit
from config import db, now_iso, timestamp, validate_phone_fr, validate_postal_code_fr
from routes.auth import get_current_user, require_admin
from services.lead_sender import send_to_crm, add_to_queue

router = APIRouter(tags=["Leads"])

# Auth par API Key pour l'API v1
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def get_api_key(authorization: Optional[str] = Header(None)):
    """Valide la clé API pour l'API v1"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Clé API manquante")
    
    # Format: "Token xxx" ou "Bearer xxx"
    parts = authorization.split(" ")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Format clé invalide")
    
    token = parts[1]
    
    # Vérifier la clé globale
    config = await db.system_config.find_one({"type": "global_api_key"})
    if config and config.get("api_key") == token:
        return token
    
    raise HTTPException(status_code=401, detail="Clé API invalide")


# ==================== API V1 (EXTERNE) ====================

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
    
    # Valider code postal
    is_valid, postal_result = validate_postal_code_fr(data.code_postal or "")
    if not is_valid:
        return {"success": False, "error": postal_result}
    code_postal = postal_result
    dept = code_postal[:2] if code_postal else data.departement or ""
    
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
                    # Note: On utilise la même clé API du formulaire
                    # car c'est la clé qui permet d'envoyer au CRM
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
        "code_postal": code_postal,
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
        # Status
        "target_crm_id": target_crm.get("id") if target_crm else None,
        "target_crm_slug": target_crm.get("slug") if target_crm else None,
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
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Liste les leads avec filtres"""
    query = {}
    if form_code:
        query["form_code"] = form_code
    if status:
        query["api_status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    total = await db.leads.count_documents(query)
    
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
    """Retenter l'envoi d'un lead"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouvé")
    
    # Récupérer config
    form = await db.forms.find_one({"code": lead.get("form_code")})
    if not form or not form.get("crm_api_key"):
        return {"success": False, "error": "Config CRM manquante"}
    
    account = await db.accounts.find_one({"id": form.get("account_id")})
    crm = await db.crms.find_one({"id": account.get("crm_id")}) if account else None
    
    if not crm:
        return {"success": False, "error": "CRM non trouvé"}
    
    status, response, _ = await send_to_crm(lead, crm.get("api_url"), form.get("crm_api_key"))
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "api_response": response,
            "sent_to_crm": status in ["success", "duplicate"],
            "retried_at": now_iso(),
            "retry_count": lead.get("retry_count", 0) + 1
        }}
    )
    
    return {"success": True, "status": status}


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
async def get_leads_stats(user: dict = Depends(get_current_user)):
    """Stats globales des leads"""
    total = await db.leads.count_documents({})
    success = await db.leads.count_documents({"api_status": "success"})
    duplicate = await db.leads.count_documents({"api_status": "duplicate"})
    failed = await db.leads.count_documents({"api_status": "failed"})
    queued = await db.leads.count_documents({"api_status": "queued"})
    no_crm = await db.leads.count_documents({"api_status": "no_crm"})
    
    return {
        "total": total,
        "success": success,
        "duplicate": duplicate,
        "failed": failed,
        "queued": queued,
        "no_crm": no_crm,
        "sent_rate": round((success + duplicate) / total * 100, 1) if total > 0 else 0
    }
