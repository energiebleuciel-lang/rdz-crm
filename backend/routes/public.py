"""
Routes Publiques - Tracking et soumission leads
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid

from config import db, now_iso, timestamp, validate_phone_fr, validate_postal_code_fr

router = APIRouter(prefix="/public", tags=["Public"])

# URLs des CRMs
CRM_URLS = {
    "zr7": "https://app.zr7-digital.fr/lead/api/create_lead/",
    "mdl": "https://maison-du-lead.com/lead/api/create_lead/"
}


# ==================== HELPERS ====================

async def get_crm_id(slug: str) -> str:
    """Récupère l'ID du CRM depuis son slug"""
    crm = await db.crms.find_one({"slug": slug}, {"_id": 0})
    return crm.get("id") if crm else None


async def has_commande(crm_id: str, dept: str, product: str) -> bool:
    """Vérifie si un CRM a une commande pour ce département/produit"""
    query = {
        "crm_id": crm_id,
        "active": True,
        "$or": [{"product_type": product}, {"product_type": "*"}]
    }
    commandes = await db.commandes.find(query, {"_id": 0}).to_list(100)
    for cmd in commandes:
        depts = cmd.get("departements", [])
        if "*" in depts or dept in depts:
            return True
    return False


# ==================== MODELS ====================

class SessionData(BaseModel):
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""
    referrer: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""


class EventData(BaseModel):
    session_id: str
    event_type: str
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""


class LeadData(BaseModel):
    session_id: str
    form_code: str
    phone: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""
    email: Optional[str] = ""
    code_postal: Optional[str] = ""
    ville: Optional[str] = ""
    adresse: Optional[str] = ""
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    surface_habitable: Optional[str] = ""
    annee_construction: Optional[str] = ""
    type_chauffage: Optional[str] = ""
    facture_electricite: Optional[str] = ""
    facture_chauffage: Optional[str] = ""
    type_projet: Optional[str] = ""
    delai_projet: Optional[str] = ""
    budget: Optional[str] = ""
    rgpd_consent: Optional[bool] = True
    newsletter: Optional[bool] = False


# ==================== ENDPOINTS ====================

@router.post("/track/session")
async def create_session(data: SessionData, request: Request):
    """Créer une session visiteur"""
    
    visitor_id = request.cookies.get("_rdz_vid")
    is_new = not visitor_id
    if is_new:
        visitor_id = str(uuid.uuid4())
    
    session_id = str(uuid.uuid4())
    lp_code = data.lp_code or ""
    form_code = data.form_code or ""
    
    # Si LP sans form, chercher le form lié
    if lp_code and not form_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp and lp.get("form_id"):
            form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
            if form:
                form_code = form.get("code", "")
    
    session = {
        "id": session_id,
        "visitor_id": visitor_id,
        "lp_code": lp_code,
        "form_code": form_code,
        "referrer": data.referrer or "",
        "utm_source": data.utm_source or "",
        "utm_medium": data.utm_medium or "",
        "utm_campaign": data.utm_campaign or "",
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso(),
        "status": "active"
    }
    
    await db.visitor_sessions.insert_one(session)
    
    response = JSONResponse({
        "success": True,
        "session_id": session_id,
        "visitor_id": visitor_id,
        "lp_code": lp_code,
        "form_code": form_code
    })
    
    if is_new:
        response.set_cookie(
            key="_rdz_vid",
            value=visitor_id,
            max_age=365*24*60*60,
            httponly=True,
            samesite="lax"
        )
    
    return response


@router.post("/track/event")
async def track_event(data: EventData, request: Request):
    """Enregistrer un événement de tracking"""
    
    session = await db.visitor_sessions.find_one({"id": data.session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}
    
    event_id = str(uuid.uuid4())
    lp_code = data.lp_code or session.get("lp_code", "")
    form_code = data.form_code or session.get("form_code", "")
    
    # Stocker dans tracking
    event = {
        "id": event_id,
        "session_id": data.session_id,
        "visitor_id": session.get("visitor_id"),
        "event": data.event_type,
        "lp_code": lp_code,
        "form_code": form_code,
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
    # Ajouter account_id si disponible
    if form_code:
        form = await db.forms.find_one({"code": form_code}, {"_id": 0})
        if form:
            event["account_id"] = form.get("account_id")
            event["form_id"] = form.get("id")
    
    if lp_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp:
            event["lp_id"] = lp.get("id")
            if not event.get("account_id"):
                event["account_id"] = lp.get("account_id")
    
    await db.tracking.insert_one(event)
    
    return {"success": True, "event_id": event_id}


@router.post("/leads")
async def submit_lead(data: LeadData, request: Request):
    """Soumettre un lead"""
    
    # Valider téléphone
    is_valid, phone = validate_phone_fr(data.phone)
    if not is_valid:
        return {"success": False, "error": phone}
    
    # Valider code postal
    dept = ""
    code_postal = ""
    if data.code_postal:
        is_valid, code_postal = validate_postal_code_fr(data.code_postal)
        if not is_valid:
            return {"success": False, "error": code_postal}
        dept = code_postal[:2]
    
    # Récupérer formulaire
    form = await db.forms.find_one(
        {"$or": [{"code": data.form_code}, {"id": data.form_code}]},
        {"_id": 0}
    )
    if not form:
        return {"success": False, "error": "Formulaire non trouvé"}
    
    form_code = form.get("code", "")
    product_type = form.get("product_type", "PV")
    account_id = form.get("account_id", "")
    target_crm = form.get("target_crm", "").lower()
    crm_api_key = form.get("crm_api_key", "")
    allow_cross_crm = form.get("allow_cross_crm", True)
    
    # Récupérer le compte pour déterminer le CRM d'origine
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    origin_crm_id = account.get("crm_id") if account else None
    origin_crm_slug = None
    if origin_crm_id:
        origin_crm_doc = await db.crms.find_one({"id": origin_crm_id}, {"_id": 0})
        origin_crm_slug = origin_crm_doc.get("slug") if origin_crm_doc else None
    
    if not target_crm or target_crm not in CRM_URLS:
        return {"success": False, "error": "CRM non configuré"}
    
    if not crm_api_key:
        return {"success": False, "error": f"Clé API {target_crm.upper()} non configurée"}
    
    # Vérifier commandes et trouver le bon CRM
    final_crm = None
    final_key = None
    is_transferred = False  # Le lead sera-t-il transféré vers un autre CRM ?
    routing_reason = "no_crm"  # Raison du routing
    
    crm_id = await get_crm_id(target_crm)
    if crm_id and await has_commande(crm_id, dept, product_type):
        final_crm = target_crm
        final_key = crm_api_key
        routing_reason = f"commande_{target_crm}"
    elif allow_cross_crm:
        other = "mdl" if target_crm == "zr7" else "zr7"
        other_id = await get_crm_id(other)
        if other_id and await has_commande(other_id, dept, product_type):
            other_form = await db.forms.find_one({
                "account_id": account_id,
                "target_crm": other,
                "crm_api_key": {"$exists": True, "$ne": ""}
            }, {"_id": 0})
            if other_form:
                final_crm = other
                final_key = other_form.get("crm_api_key")
                is_transferred = True  # Transfert inter-CRM !
                routing_reason = f"cross_crm_{other}"
    
    # Récupérer session
    session = await db.visitor_sessions.find_one({"id": data.session_id}, {"_id": 0})
    lp_code = session.get("lp_code", "") if session else ""
    utm = {
        "source": session.get("utm_source", "") if session else "",
        "medium": session.get("utm_medium", "") if session else "",
        "campaign": session.get("utm_campaign", "") if session else ""
    }
    
    # Créer le lead
    lead_id = str(uuid.uuid4())
    lead = {
        "id": lead_id,
        "session_id": data.session_id,
        "form_id": form.get("id"),
        "form_code": form_code,
        "account_id": account_id,
        "product_type": product_type,
        "phone": phone,
        "nom": data.nom or "",
        "prenom": data.prenom or "",
        "civilite": data.civilite or "",
        "email": data.email or "",
        "code_postal": code_postal,
        "departement": dept,
        "ville": data.ville or "",
        "adresse": data.adresse or "",
        "type_logement": data.type_logement or "",
        "statut_occupant": data.statut_occupant or "",
        "surface_habitable": data.surface_habitable or "",
        "annee_construction": data.annee_construction or "",
        "type_chauffage": data.type_chauffage or "",
        "facture_electricite": data.facture_electricite or "",
        "facture_chauffage": data.facture_chauffage or "",
        "type_projet": data.type_projet or "",
        "delai_projet": data.delai_projet or "",
        "budget": data.budget or "",
        "lp_code": lp_code,
        "liaison_code": f"{lp_code}_{form_code}" if lp_code else form_code,
        "utm_source": utm["source"],
        "utm_medium": utm["medium"],
        "utm_campaign": utm["campaign"],
        "rgpd_consent": data.rgpd_consent,
        "newsletter": data.newsletter,
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        # CRM info
        "origin_crm": origin_crm_slug or target_crm,  # CRM d'origine (compte)
        "target_crm": final_crm or "none",  # CRM de destination final
        "is_transferred": is_transferred,  # Transféré vers autre CRM ?
        "api_status": "pending" if final_crm else "no_crm",
        "sent_to_crm": False
    }
    
    await db.leads.insert_one(lead)
    
    # Envoyer au CRM
    status = "no_crm"
    message = "Aucun CRM disponible"
    
    if final_crm and final_key:
        from services.lead_sender import send_to_crm_v2, add_to_queue
        
        api_url = CRM_URLS[final_crm]
        status, response, should_queue = await send_to_crm_v2(lead, api_url, final_key)
        
        if should_queue:
            await add_to_queue(lead, api_url, final_key, "error")
            status = "queued"
        
        message = f"Envoyé vers {final_crm.upper()}" if status == "success" else response
    
    # Mettre à jour le lead
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "sent_to_crm": status in ["success", "duplicate"],
            "sent_at": now_iso() if status in ["success", "duplicate"] else None
        }}
    )
    
    # Mettre à jour la session
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {"status": "converted", "lead_id": lead_id}}
        )
    
    return {
        "success": status in ["success", "duplicate", "queued", "no_crm"],
        "lead_id": lead_id,
        "status": status,
        "crm": final_crm or "none",
        "message": message
    }
