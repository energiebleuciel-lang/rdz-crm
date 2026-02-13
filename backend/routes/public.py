"""
RDZ CRM - Routes Publiques
- Tracking sessions visiteurs
- Tracking evenements LP/Form
- Soumission leads (sauvegarde en base, routing par daily_delivery)
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import logging

from config import db, now_iso, timestamp, validate_phone_fr

router = APIRouter(prefix="/public", tags=["Public"])
logger = logging.getLogger("public")


async def parse_beacon_body(request: Request) -> dict:
    """Parse body sendBeacon-compatible"""
    try:
        body = await request.body()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))
    except Exception:
        return {}


# Models

class SessionData(BaseModel):
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    referrer: Optional[str] = ""
    user_agent: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    utm_content: Optional[str] = ""
    utm_term: Optional[str] = ""
    gclid: Optional[str] = ""
    fbclid: Optional[str] = ""


class LeadData(BaseModel):
    """Soumission de lead via formulaire public"""
    session_id: str
    form_code: str
    phone: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    email: Optional[str] = ""
    departement: Optional[str] = ""
    # Champs secondaires
    civilite: Optional[str] = ""
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
    # Attribution
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    # RDZ direct (Phase 2)
    entity: Optional[str] = ""
    produit: Optional[str] = ""


# Tracking endpoints

@router.post("/track/session")
async def create_session(data: SessionData, request: Request):
    """Creer une session visiteur"""
    visitor_id = request.cookies.get("_rdz_vid")
    is_new = not visitor_id
    if is_new:
        visitor_id = str(uuid.uuid4())

    lp_code = data.lp_code or ""
    form_code = data.form_code or ""
    liaison_code = data.liaison_code or ""

    # Anti-doublon: session existante pour ce visiteur + LP
    if visitor_id and lp_code:
        from datetime import datetime, timedelta, timezone
        thirty_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        existing = await db.visitor_sessions.find_one({
            "visitor_id": visitor_id,
            "lp_code": lp_code,
            "created_at": {"$gte": thirty_min_ago}
        }, {"_id": 0})
        if existing:
            return JSONResponse({
                "success": True,
                "session_id": existing["id"],
                "visitor_id": visitor_id,
                "lp_code": lp_code,
                "form_code": existing.get("form_code", form_code),
                "reused": True
            })

    session_id = str(uuid.uuid4())

    session = {
        "id": session_id,
        "visitor_id": visitor_id,
        "lp_code": lp_code,
        "form_code": form_code,
        "liaison_code": liaison_code,
        "referrer": data.referrer or "",
        "user_agent": data.user_agent or request.headers.get("user-agent", ""),
        "utm_source": data.utm_source or "",
        "utm_medium": data.utm_medium or "",
        "utm_campaign": data.utm_campaign or "",
        "utm_content": data.utm_content or "",
        "utm_term": data.utm_term or "",
        "gclid": data.gclid or "",
        "fbclid": data.fbclid or "",
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


@router.post("/track/lp-visit")
async def track_lp_visit(request: Request):
    """Tracking visite LP (sendBeacon compatible)"""
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")

    if not session_id:
        return {"success": False, "error": "session_id requis"}

    session = await db.visitor_sessions.find_one({"id": session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}

    # Anti-doublon: 1 seule lp_visit par session
    existing = await db.tracking.find_one({
        "session_id": session_id,
        "event": "lp_visit"
    })
    if existing:
        return {"success": True, "event_id": existing.get("id"), "duplicate": True}

    event_id = str(uuid.uuid4())
    lp_code = data.get("lp_code") or session.get("lp_code", "")

    event = {
        "id": event_id,
        "session_id": session_id,
        "visitor_id": session.get("visitor_id"),
        "event": "lp_visit",
        "lp_code": lp_code,
        "utm_source": data.get("utm_source") or "",
        "utm_medium": data.get("utm_medium") or "",
        "utm_campaign": data.get("utm_campaign") or "",
        "utm_content": data.get("utm_content") or "",
        "utm_term": data.get("utm_term") or "",
        "gclid": data.get("gclid") or "",
        "fbclid": data.get("fbclid") or "",
        "referrer": data.get("referrer") or "",
        "user_agent": data.get("user_agent") or request.headers.get("user-agent", ""),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }

    await db.tracking.insert_one(event)

    # MAJ session UTM si manquant
    update_session = {}
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"]:
        if data.get(key) and not session.get(key):
            update_session[key] = data.get(key)
    if update_session:
        await db.visitor_sessions.update_one({"id": session_id}, {"$set": update_session})

    return {"success": True, "event_id": event_id}


@router.post("/track/event")
async def track_event(request: Request):
    """Tracking evenement (sendBeacon compatible)"""
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")
    event_type = data.get("event_type", "")

    if not session_id or not event_type:
        return {"success": False, "error": "session_id et event_type requis"}

    session = await db.visitor_sessions.find_one({"id": session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}

    # Anti-doublon pour certains events
    if event_type in ["lp_visit", "cta_click", "form_start"]:
        existing = await db.tracking.find_one({
            "session_id": session_id,
            "event": event_type
        })
        if existing:
            return {"success": True, "event_id": existing.get("id"), "duplicate": True}

    event_id = str(uuid.uuid4())

    event = {
        "id": event_id,
        "session_id": session_id,
        "visitor_id": session.get("visitor_id"),
        "event": event_type,
        "lp_code": data.get("lp_code") or session.get("lp_code", ""),
        "form_code": data.get("form_code") or session.get("form_code", ""),
        "liaison_code": data.get("liaison_code") or session.get("liaison_code", ""),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }

    await db.tracking.insert_one(event)
    return {"success": True, "event_id": event_id}


# Lead submission

@router.post("/leads")
async def submit_lead(data: LeadData, request: Request):
    """
    Soumettre un lead

    REGLE: Le lead est TOUJOURS insere si telephone present.
    Le routing est gere par le daily_delivery (09h30).

    1. Valider telephone
    2. Anti double-submit (5 sec)
    3. Sauvegarder lead status=new
    4. Retourner success
    """
    from services.duplicate_detector import check_double_submit

    # Valider telephone
    is_valid, phone_result = validate_phone_fr(data.phone)
    phone = phone_result if is_valid else data.phone

    # Champs obligatoires
    nom = (data.nom or "").strip()
    dept = (data.departement or "").strip()[:2] if data.departement else ""

    # Anti double-submit
    is_double_submit = False
    original_lead_id = None

    if is_valid and data.session_id:
        dup_result = await check_double_submit(phone, data.session_id)
        if dup_result.is_duplicate:
            is_double_submit = True
            original_lead_id = dup_result.original_lead_id

    if is_double_submit:
        return {
            "success": True,
            "lead_id": original_lead_id,
            "status": "double_submit",
            "message": "Double soumission detectee - lead deja cree"
        }

    # Determiner entity et produit
    entity = (data.entity or "").upper()
    produit = (data.produit or "").upper()

    # Recuperer session
    session = await db.visitor_sessions.find_one({"id": data.session_id}, {"_id": 0})
    lp_code = data.lp_code or (session.get("lp_code", "") if session else "")
    utm_source = session.get("utm_source", "") if session else ""
    utm_medium = session.get("utm_medium", "") if session else ""
    utm_campaign = data.utm_campaign or (session.get("utm_campaign", "") if session else "")

    # Creer le lead
    lead_id = str(uuid.uuid4())
    lead = {
        "id": lead_id,
        "phone": phone,
        "nom": nom,
        "prenom": (data.prenom or "").strip(),
        "email": (data.email or "").strip(),
        "departement": dept,
        "entity": entity,
        "produit": produit,
        "status": "new",
        "is_lb": False,
        # Tracking
        "session_id": data.session_id,
        "form_code": data.form_code or "",
        "lp_code": lp_code,
        "liaison_code": data.liaison_code or "",
        "source": utm_source,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        # Champs secondaires dans custom_fields
        "custom_fields": {},
        # Meta
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
    }

    # Champs secondaires
    secondary = {}
    for field in ["civilite", "ville", "adresse", "type_logement", "statut_occupant",
                   "surface_habitable", "annee_construction", "type_chauffage",
                   "facture_electricite", "facture_chauffage", "type_projet",
                   "delai_projet", "budget"]:
        val = getattr(data, field, None)
        if val:
            secondary[field] = val
    if secondary:
        lead["custom_fields"] = secondary

    await db.leads.insert_one(lead)

    # MAJ session
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {"status": "converted", "lead_id": lead_id}}
        )

    logger.info(
        f"[LEAD_CREATED] id={lead_id} phone=***{phone[-4:] if len(phone) >= 4 else phone} "
        f"entity={entity or 'TBD'} produit={produit or 'TBD'} dept={dept}"
    )

    return {
        "success": True,
        "lead_id": lead_id,
        "status": "new",
        "message": "Lead enregistre"
    }
