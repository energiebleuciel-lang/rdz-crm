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
    
    # Récupérer le compte
    account = await db.accounts.find_one({"id": account_id})
    crm_id = account.get("crm_id") if account else None
    
    # 3. Router vers le bon CRM selon commandes
    target_crm = None
    routing_reason = "no_order"
    api_url = ""
    api_key_crm = ""
    
    # D'abord vérifier la clé API du formulaire
    if form.get("crm_api_key"):
        # Utiliser le CRM du compte
        crm = await db.crms.find_one({"id": crm_id})
        if crm:
            # Vérifier les commandes
            commandes = crm.get("commandes", {})
            if product_type in commandes and dept in commandes[product_type]:
                target_crm = crm
                routing_reason = f"commande_{crm.get('slug')}"
                api_url = crm.get("api_url", "")
                api_key_crm = form.get("crm_api_key")
    
    # Sinon, chercher dans tous les CRMs qui ont une commande pour ce dept/produit
    if not target_crm:
        crms = await db.crms.find({}).to_list(100)
        for crm in crms:
            commandes = crm.get("commandes", {})
            if product_type in commandes and dept in commandes[product_type]:
                # Trouver un formulaire avec une clé API pour ce CRM
                form_with_key = await db.forms.find_one({
                    "account_id": account_id,
                    "product_type": product_type,
                    "crm_api_key": {"$exists": True, "$ne": ""}
                })
                if form_with_key:
                    target_crm = crm
                    routing_reason = f"commande_{crm.get('slug')}"
                    api_url = crm.get("api_url", "")
                    api_key_crm = form_with_key.get("crm_api_key")
                    break
    
    # 4. Créer le document lead
    lead_doc = {
        "id": str(uuid.uuid4()),
        "form_id": form.get("id"),
        "form_code": form_code,
        "account_id": account_id,
        "product_type": product_type,
        # Données lead
        "phone": phone,
        "nom": data.nom or "",
        "prenom": data.prenom or "",
        "civilite": data.civilite or "",
        "email": data.email or "",
        "code_postal": code_postal,
        "departement": dept,
        "type_logement": data.type_logement or "",
        "statut_occupant": data.statut_occupant or "",
        "facture_electricite": data.facture_electricite or "",
        # Tracking
        "lp_code": data.lp_code or "",
        "liaison_code": data.liaison_code or "",
        # Metadata
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        # Status
        "target_crm_id": target_crm.get("id") if target_crm else None,
        "target_crm_slug": target_crm.get("slug") if target_crm else None,
        "routing_reason": routing_reason,
        "api_status": "pending",
        "sent_to_crm": False
    }
    
    await db.leads.insert_one(lead_doc)
    
    # 5. Envoyer au CRM externe
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
