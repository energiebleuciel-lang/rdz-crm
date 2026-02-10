"""
Routes Publiques - Nouveau système de tracking v2
Endpoints SANS authentification pour:
- Gestion des sessions visiteurs (cookie fonctionnel)
- Tracking unifié des événements
- Soumission de leads (clé API côté serveur)
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os
from datetime import datetime, timezone

from config import db, now_iso, timestamp, validate_phone_fr, validate_postal_code_fr

router = APIRouter(prefix="/public", tags=["Public API v2"])

# ==================== CONFIGURATION CRM ====================

# Clés API stockées côté serveur (non visibles côté client)
CRM_CONFIG = {
    "zr7": {
        "name": "ZR7 Digital",
        "api_url": os.environ.get("ZR7_API_URL", "https://app.zr7-digital.fr/lead/api/create_lead/"),
        "api_key": os.environ.get("ZR7_API_KEY", "")
    },
    "mdl": {
        "name": "Maison du Lead",
        "api_url": os.environ.get("MDL_API_URL", "https://maison-du-lead.com/lead/api/create_lead/"),
        "api_key": os.environ.get("MDL_API_KEY", "")
    }
}


# ==================== MODELS ====================

class SessionInit(BaseModel):
    """Initialisation de session visiteur"""
    lp_code: Optional[str] = None
    form_code: Optional[str] = None
    referrer: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""


class TrackEvent(BaseModel):
    """Événement de tracking unifié"""
    session_id: str
    event_type: str  # lp_visit, cta_click, form_start, form_step, form_submit
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""
    data: Optional[dict] = {}  # Données supplémentaires (step_name, cta_id, etc.)


class LeadSubmit(BaseModel):
    """Soumission de lead - SANS clé API visible"""
    session_id: str
    form_code: str
    # Identité
    phone: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""
    email: Optional[str] = ""
    # Localisation
    code_postal: Optional[str] = ""
    ville: Optional[str] = ""
    adresse: Optional[str] = ""
    # Logement
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    surface_habitable: Optional[str] = ""
    annee_construction: Optional[str] = ""
    type_chauffage: Optional[str] = ""
    # Énergie
    facture_electricite: Optional[str] = ""
    facture_chauffage: Optional[str] = ""
    # Projet
    type_projet: Optional[str] = ""
    delai_projet: Optional[str] = ""
    budget: Optional[str] = ""
    # Consentement
    rgpd_consent: Optional[bool] = True
    newsletter: Optional[bool] = False


# ==================== SESSION VISITEUR ====================

@router.post("/track/session")
async def init_session(data: SessionInit, request: Request, response: Response):
    """
    Initialise ou récupère une session visiteur.
    Utilise un cookie fonctionnel (pas besoin de consentement RGPD).
    
    Flow:
    1. Vérifie si cookie visitor_id existe
    2. Si oui, récupère/crée nouvelle session pour ce visiteur
    3. Si non, crée nouveau visiteur + session
    
    Returns: session_id à utiliser pour tous les appels suivants
    """
    # Récupérer visitor_id depuis cookie ou en créer un nouveau
    visitor_id = request.cookies.get("_rdz_vid")
    is_new_visitor = False
    
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        is_new_visitor = True
    
    # Créer une nouvelle session
    session_id = str(uuid.uuid4())
    
    # Déterminer LP et Form
    lp_code = data.lp_code or ""
    form_code = data.form_code or ""
    
    # Si on a un lp_code, récupérer le form lié
    if lp_code and not form_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp and lp.get("form_id"):
            form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
            if form:
                form_code = form.get("code", "")
    
    # Créer la session
    session_doc = {
        "id": session_id,
        "visitor_id": visitor_id,
        "is_new_visitor": is_new_visitor,
        "lp_code": lp_code,
        "form_code": form_code,
        "referrer": data.referrer or "",
        "utm": {
            "source": data.utm_source or "",
            "medium": data.utm_medium or "",
            "campaign": data.utm_campaign or ""
        },
        "events": [],
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "user_agent": request.headers.get("user-agent", ""),
        "started_at": now_iso(),
        "last_activity": now_iso(),
        "status": "active",  # active, converted, abandoned
        "lead_id": None
    }
    
    await db.visitor_sessions.insert_one(session_doc)
    
    # Créer la réponse avec le cookie
    resp_data = {
        "success": True,
        "session_id": session_id,
        "visitor_id": visitor_id,
        "is_new_visitor": is_new_visitor,
        "lp_code": lp_code,
        "form_code": form_code
    }
    
    json_response = JSONResponse(content=resp_data)
    
    # Cookie fonctionnel - 1 an de durée
    if is_new_visitor:
        json_response.set_cookie(
            key="_rdz_vid",
            value=visitor_id,
            max_age=365 * 24 * 60 * 60,  # 1 an
            httponly=True,
            samesite="lax",
            secure=True
        )
    
    return json_response


@router.post("/track/event")
async def track_event(data: TrackEvent, request: Request):
    """
    Enregistre un événement de tracking.
    
    Types d'événements:
    - lp_visit: Visite de la landing page
    - cta_click: Clic sur un CTA
    - form_start: Premier champ du formulaire touché
    - form_step: Étape du formulaire complétée
    - form_submit: Formulaire soumis (lead créé)
    """
    # Vérifier que la session existe
    session = await db.visitor_sessions.find_one({"id": data.session_id})
    if not session:
        raise HTTPException(status_code=400, detail="Session invalide")
    
    # Créer l'événement
    event = {
        "id": str(uuid.uuid4()),
        "type": data.event_type,
        "lp_code": data.lp_code or session.get("lp_code", ""),
        "form_code": data.form_code or session.get("form_code", ""),
        "data": data.data or {},
        "timestamp": now_iso(),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else "")
    }
    
    # Ajouter à la session
    await db.visitor_sessions.update_one(
        {"id": data.session_id},
        {
            "$push": {"events": event},
            "$set": {"last_activity": now_iso()}
        }
    )
    
    # Aussi enregistrer dans la collection tracking pour compatibilité stats
    tracking_event = {
        "id": event["id"],
        "session_id": data.session_id,
        "visitor_id": session.get("visitor_id"),
        "event": data.event_type,
        "lp_code": event["lp_code"],
        "form_code": event["form_code"],
        "data": event["data"],
        "ip": event["ip"],
        "created_at": event["timestamp"]
    }
    
    # Ajouter account_id si on trouve le form
    if event["form_code"]:
        form = await db.forms.find_one({"code": event["form_code"]}, {"_id": 0})
        if form:
            tracking_event["account_id"] = form.get("account_id")
            tracking_event["form_id"] = form.get("id")
    
    if event["lp_code"]:
        lp = await db.lps.find_one({"code": event["lp_code"]}, {"_id": 0})
        if lp:
            tracking_event["lp_id"] = lp.get("id")
            if not tracking_event.get("account_id"):
                tracking_event["account_id"] = lp.get("account_id")
    
    await db.tracking.insert_one(tracking_event)
    
    return {"success": True, "event_id": event["id"]}


# ==================== SOUMISSION LEAD ====================

@router.post("/leads")
async def submit_lead(data: LeadSubmit, request: Request):
    """
    Soumission de lead SANS clé API visible.
    La clé API est stockée côté serveur et associée au CRM du compte.
    
    Flow:
    1. Valider téléphone
    2. Récupérer config formulaire
    3. Déterminer CRM destination (ZR7 ou MDL)
    4. Envoyer avec la clé API serveur
    5. Mettre à jour la session
    """
    # 1. Valider téléphone
    is_valid, phone_result = validate_phone_fr(data.phone)
    if not is_valid:
        return {"success": False, "error": phone_result}
    phone = phone_result
    
    # Valider code postal si fourni
    code_postal = ""
    dept = ""
    if data.code_postal:
        is_valid, postal_result = validate_postal_code_fr(data.code_postal)
        if not is_valid:
            return {"success": False, "error": postal_result}
        code_postal = postal_result
        dept = code_postal[:2]
    
    # 2. Récupérer config formulaire
    form = await db.forms.find_one(
        {"$or": [{"code": data.form_code}, {"id": data.form_code}]},
        {"_id": 0}
    )
    if not form:
        return {"success": False, "error": "Formulaire non trouvé"}
    
    form_code = form.get("code", "")
    product_type = form.get("product_type", "PV")
    account_id = form.get("account_id", "")
    
    # Récupérer le compte pour avoir le CRM
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        return {"success": False, "error": "Compte non trouvé"}
    
    crm_id = account.get("crm_id", "")
    
    # Récupérer le CRM pour avoir le slug
    crm = await db.crms.find_one({"id": crm_id}, {"_id": 0})
    if not crm:
        return {"success": False, "error": f"CRM non trouvé: {crm_id}"}
    
    crm_slug = crm.get("slug", "").lower()  # "zr7" ou "mdl"
    
    # 3. Déterminer CRM destination et récupérer clé API
    crm_config = CRM_CONFIG.get(crm_slug)
    if not crm_config:
        return {"success": False, "error": f"CRM non configuré: {crm_slug}"}
    
    api_url = crm_config["api_url"]
    api_key = crm_config["api_key"]
    
    if not api_key:
        return {"success": False, "error": f"Clé API {crm_slug.upper()} non configurée sur le serveur"}
    
    # Récupérer la session pour avoir les UTM et lp_code
    session = await db.visitor_sessions.find_one({"id": data.session_id}, {"_id": 0})
    lp_code = session.get("lp_code", "") if session else ""
    utm = session.get("utm", {}) if session else {}
    liaison_code = f"{lp_code}_{form_code}" if lp_code else form_code
    
    # 4. Créer le document lead
    lead_id = str(uuid.uuid4())
    lead_doc = {
        "id": lead_id,
        "session_id": data.session_id,
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
        "lp_code": lp_code,
        "liaison_code": liaison_code,
        "source": utm.get("source", ""),
        "utm_source": utm.get("source", ""),
        "utm_medium": utm.get("medium", ""),
        "utm_campaign": utm.get("campaign", ""),
        # Consentement
        "rgpd_consent": data.rgpd_consent if data.rgpd_consent is not None else True,
        "newsletter": data.newsletter or False,
        # Metadata
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        # CRM
        "target_crm": crm_slug,
        "api_status": "pending",
        "sent_to_crm": False
    }
    
    await db.leads.insert_one(lead_doc)
    
    # 5. Envoyer au CRM
    from services.lead_sender import send_to_crm_v2, add_to_queue
    
    status, response, should_queue = await send_to_crm_v2(lead_doc, api_url, api_key)
    
    if should_queue:
        await add_to_queue(lead_doc, api_url, api_key, "crm_error")
        status = "queued"
    
    # Mettre à jour le lead
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "api_response": response,
            "sent_to_crm": status in ["success", "duplicate"],
            "sent_at": now_iso() if status in ["success", "duplicate"] else None
        }}
    )
    
    # 6. Mettre à jour la session
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {
                "status": "converted",
                "lead_id": lead_id,
                "converted_at": now_iso()
            }}
        )
        
        # Ajouter événement form_submit
        await track_event(TrackEvent(
            session_id=data.session_id,
            event_type="form_submit",
            form_code=form_code,
            lp_code=lp_code,
            data={"lead_id": lead_id, "status": status}
        ), request)
    
    return {
        "success": status in ["success", "duplicate", "queued"],
        "lead_id": lead_id,
        "status": status,
        "message": "Lead enregistré" if status == "queued" else ("Lead envoyé" if status == "success" else response)
    }


# ==================== CONFIG PUBLIQUE ====================

@router.get("/config/{form_code}")
async def get_public_config(form_code: str):
    """
    Récupère la configuration publique d'un formulaire.
    Utilisé par le script client pour s'initialiser.
    """
    form = await db.forms.find_one(
        {"$or": [{"code": form_code}, {"id": form_code}]},
        {"_id": 0}
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Récupérer LP liée
    lp = None
    if form.get("lp_id"):
        lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0})
    
    # Récupérer compte
    account = await db.accounts.find_one({"id": form.get("account_id")}, {"_id": 0})
    
    return {
        "form": {
            "code": form.get("code"),
            "name": form.get("name"),
            "product_type": form.get("product_type"),
            "tracking_type": form.get("tracking_type", "redirect"),
            "redirect_url": form.get("redirect_url", "/merci")
        },
        "lp": {
            "code": lp.get("code") if lp else None,
            "url": lp.get("url") if lp else None
        } if lp else None,
        "account": {
            "name": account.get("name") if account else None,
            "logos": {
                "main": account.get("logo_main_url") if account else None,
                "secondary": account.get("logo_secondary_url") if account else None,
                "mini": account.get("logo_mini_url") if account else None
            },
            "gtm": {
                "conversion": account.get("gtm_conversion") if account else None
            }
        } if account else None
    }
