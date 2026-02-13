# RDZ CRM — Fichiers Critiques (Export Complet)

> Date : Février 2026
> 6 fichiers = tout le noyau fonctionnel du CRM

---

## 1. backend/routes/public.py (741 lignes)

```python
"""
Routes Publiques - Tracking et soumission leads
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json

from config import db, now_iso, timestamp, validate_phone_fr

router = APIRouter(prefix="/public", tags=["Public"])


# ==================== SENDBEACON COMPATIBLE PARSER ====================

async def parse_beacon_body(request: Request) -> dict:
    try:
        body = await request.body()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))
    except Exception:
        return {}


# ==================== HELPERS ====================

async def get_crm_info(slug: str) -> dict:
    crm = await db.crms.find_one({"slug": slug}, {"_id": 0})
    return crm if crm else None

async def get_crm_id(slug: str) -> str:
    crm = await get_crm_info(slug)
    return crm.get("id") if crm else None

async def get_crm_url(slug: str) -> str:
    crm = await get_crm_info(slug)
    return crm.get("api_url") if crm else None


# ==================== MODELS ====================

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
    session_id: str
    form_code: str
    phone: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""
    email: Optional[str] = ""
    departement: Optional[str] = ""
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
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    utm_campaign: Optional[str] = ""


# ==================== ENDPOINTS ====================

@router.post("/track/session")
async def create_session(data: SessionData, request: Request):
    visitor_id = request.cookies.get("_rdz_vid")
    is_new = not visitor_id
    if is_new:
        visitor_id = str(uuid.uuid4())
    
    lp_code = data.lp_code or ""
    form_code = data.form_code or ""
    liaison_code = data.liaison_code or ""
    
    if lp_code and not form_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp and lp.get("form_id"):
            form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
            if form:
                form_code = form.get("code", "")
                if not liaison_code:
                    liaison_code = f"{lp_code}_{form_code}"
    
    if visitor_id and lp_code:
        from datetime import datetime, timedelta, timezone
        thirty_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        existing = await db.visitor_sessions.find_one({
            "visitor_id": visitor_id,
            "lp_code": lp_code,
            "created_at": {"$gte": thirty_min_ago}
        }, {"_id": 0})
        if existing:
            response = JSONResponse({
                "success": True,
                "session_id": existing["id"],
                "visitor_id": visitor_id,
                "lp_code": lp_code,
                "form_code": existing.get("form_code", form_code),
                "reused": True
            })
            return response
    
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
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")
    
    if not session_id:
        return {"success": False, "error": "session_id requis"}
    
    session = await db.visitor_sessions.find_one({"id": session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}
    
    existing = await db.tracking.find_one({
        "session_id": session_id,
        "event": "lp_visit"
    })
    if existing:
        return {"success": True, "event_id": existing.get("id"), "duplicate": True}
    
    event_id = str(uuid.uuid4())
    lp_code = data.get("lp_code") or session.get("lp_code", "")
    
    account_id = None
    lp_id = None
    if lp_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp:
            lp_id = lp.get("id")
            account_id = lp.get("account_id")
    
    event = {
        "id": event_id,
        "session_id": session_id,
        "visitor_id": session.get("visitor_id"),
        "event": "lp_visit",
        "lp_code": lp_code,
        "lp_id": lp_id,
        "account_id": account_id,
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
    
    update_session = {}
    if data.get("utm_source") and not session.get("utm_source"):
        update_session["utm_source"] = data.get("utm_source")
    if data.get("utm_medium") and not session.get("utm_medium"):
        update_session["utm_medium"] = data.get("utm_medium")
    if data.get("utm_campaign") and not session.get("utm_campaign"):
        update_session["utm_campaign"] = data.get("utm_campaign")
    if data.get("utm_content") and not session.get("utm_content"):
        update_session["utm_content"] = data.get("utm_content")
    if data.get("utm_term") and not session.get("utm_term"):
        update_session["utm_term"] = data.get("utm_term")
    if data.get("gclid") and not session.get("gclid"):
        update_session["gclid"] = data.get("gclid")
    if data.get("fbclid") and not session.get("fbclid"):
        update_session["fbclid"] = data.get("fbclid")
    
    if update_session:
        await db.visitor_sessions.update_one(
            {"id": session_id},
            {"$set": update_session}
        )
    
    return {"success": True, "event_id": event_id}


@router.post("/track/event")
async def track_event(request: Request):
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")
    event_type = data.get("event_type", "")
    
    if not session_id or not event_type:
        return {"success": False, "error": "session_id et event_type requis"}
    
    session = await db.visitor_sessions.find_one({"id": session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}
    
    if event_type in ["lp_visit", "cta_click", "form_start"]:
        existing = await db.tracking.find_one({
            "session_id": session_id,
            "event": event_type
        })
        if existing:
            return {"success": True, "event_id": existing.get("id"), "duplicate": True}
    
    event_id = str(uuid.uuid4())
    lp_code = data.get("lp_code") or session.get("lp_code", "")
    form_code = data.get("form_code") or session.get("form_code", "")
    liaison_code = data.get("liaison_code") or session.get("liaison_code", "")
    
    if not liaison_code and lp_code and form_code:
        liaison_code = f"{lp_code}_{form_code}"
    
    event = {
        "id": event_id,
        "session_id": session_id,
        "visitor_id": session.get("visitor_id"),
        "event": event_type,
        "lp_code": lp_code,
        "form_code": form_code,
        "liaison_code": liaison_code,
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
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
    """
    RÈGLE ABSOLUE : Le lead est TOUJOURS créé dans RDZ.
    PROTECTION ANTI DOUBLE-SUBMIT: 5 secondes (même session + même phone)
    CHAMPS OBLIGATOIRES : phone, nom, departement
    """
    from services.duplicate_detector import check_duplicate
    
    is_valid, phone_result = validate_phone_fr(data.phone)
    phone = phone_result if is_valid else data.phone
    phone_invalid = not is_valid
    
    nom = (data.nom or "").strip()
    dept = (data.departement or "").strip()
    missing_nom = not nom
    missing_dept = not dept
    missing_required = missing_nom or missing_dept
    
    # === ANTI DOUBLE-SUBMIT ===
    duplicate_result = None
    is_double_submit = False
    
    if is_valid:
        duplicate_result = await check_duplicate(
            phone=phone,
            departement=dept,
            session_id=data.session_id
        )
        is_double_submit = duplicate_result.is_duplicate
    
    # Récupérer formulaire
    form = await db.forms.find_one(
        {"$or": [{"code": data.form_code}, {"id": data.form_code}]},
        {"_id": 0}
    )
    
    form_not_found = form is None
    if form_not_found:
        form = {
            "id": None,
            "code": data.form_code or "UNKNOWN",
            "product_type": "PV",
            "account_id": "",
            "target_crm": "",
            "crm_api_key": "",
            "allow_cross_crm": False,
        }
    
    form_code = form.get("code", "")
    product_type = form.get("product_type", "PV")
    account_id = form.get("account_id", "")
    
    # Form-level CRM config (override optionnel)
    form_target_crm = form.get("target_crm", "").lower().strip()
    form_crm_api_key = form.get("crm_api_key", "").strip()
    
    # Récupérer le compte pour routing account-centric
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    origin_crm_id = account.get("crm_id") if account else None
    origin_crm_slug = None
    if origin_crm_id:
        origin_crm_doc = await db.crms.find_one({"id": origin_crm_id}, {"_id": 0})
        origin_crm_slug = origin_crm_doc.get("slug") if origin_crm_doc else None
    
    # === ROUTING ACCOUNT-CENTRIC ===
    import logging
    routing_logger = logging.getLogger("routing")
    
    VALID_TARGET_CRMS = {"zr7", "mdl"}
    
    target_crm = ""
    crm_api_key = ""
    routing_source = "none"
    
    # Étape 1: Override formulaire (whitelist)
    form_override_valid = bool(
        form_target_crm and form_crm_api_key
        and form_target_crm in VALID_TARGET_CRMS
    )
    has_form_override = form_override_valid
    
    if form_target_crm and form_target_crm not in VALID_TARGET_CRMS:
        routing_logger.warning(
            f"[ROUTING_WARN] form override rejeté: target_crm='{form_target_crm}' "
            f"not in whitelist {VALID_TARGET_CRMS} form_code={form_code}"
        )
    
    # Étape 2: Config account
    account_routing = {}
    if account:
        account_routing = account.get("crm_routing") or {}
    account_product_config = account_routing.get(product_type, {})
    if isinstance(account_product_config, dict):
        acct_crm = account_product_config.get("target_crm", "").lower().strip()
        acct_key = account_product_config.get("api_key", "").strip()
    else:
        acct_crm = ""
        acct_key = ""
    has_account_config = bool(acct_crm and acct_key and acct_crm in VALID_TARGET_CRMS)
    
    # Résolution: override form > config account
    if has_form_override:
        target_crm = form_target_crm
        crm_api_key = form_crm_api_key
        routing_source = "form_override"
    elif has_account_config:
        target_crm = acct_crm
        crm_api_key = acct_key
        routing_source = "account_routing"
    
    routing_logger.info(
        f"[ROUTING] lead_phone={phone[-4:] if len(phone) >= 4 else phone} "
        f"account_id={account_id} product={product_type} "
        f"source={routing_source} target_crm={target_crm or 'none'} "
        f"has_form_override={has_form_override} has_account_config={has_account_config}"
    )
    
    target_crm_url = await get_crm_url(target_crm) if target_crm else None
    
    has_api_key = bool(crm_api_key)
    has_crm_config = bool(target_crm and target_crm_url)
    
    # Résolution finale
    final_crm = None
    final_key = None
    routing_reason = "no_crm"
    
    if has_crm_config and has_api_key:
        final_crm = target_crm
        final_key = crm_api_key
        routing_reason = f"{routing_source}_{target_crm}"
    
    # Déterminer le statut initial
    original_lead_id = None
    
    if form_not_found:
        initial_status = "orphan"
        distribution_reason = "FORM_NOT_FOUND"
    elif phone_invalid:
        initial_status = "invalid_phone"
        distribution_reason = "PHONE_INVALID"
    elif missing_required:
        initial_status = "missing_required"
        missing_fields = []
        if missing_nom:
            missing_fields.append("nom")
        if missing_dept:
            missing_fields.append("departement")
        distribution_reason = f"MISSING_REQUIRED:{','.join(missing_fields)}"
    elif is_double_submit and duplicate_result:
        original_lead_id = duplicate_result.original_lead_id
        initial_status = "double_submit"
        distribution_reason = "DOUBLE_SUBMIT_BLOCKED"
    elif not has_crm_config:
        initial_status = "no_crm"
        distribution_reason = "CRM_NOT_CONFIGURED"
    elif not has_api_key:
        initial_status = "no_api_key"
        distribution_reason = "API_KEY_MISSING"
    elif final_crm and final_key:
        initial_status = "pending"
        distribution_reason = routing_reason
    else:
        initial_status = "pending_no_order"
        distribution_reason = "NO_ELIGIBLE_ORDER"
    
    # Récupérer session
    session = await db.visitor_sessions.find_one({"id": data.session_id}, {"_id": 0})
    lp_code_from_session = session.get("lp_code", "") if session else ""
    utm = {
        "source": session.get("utm_source", "") if session else "",
        "medium": session.get("utm_medium", "") if session else "",
        "campaign": session.get("utm_campaign", "") if session else ""
    }
    
    final_lp_code = data.lp_code or lp_code_from_session
    final_liaison_code = data.liaison_code or (f"{final_lp_code}_{form_code}" if final_lp_code else form_code)
    final_utm_campaign = data.utm_campaign or utm["campaign"]
    
    quality_tier = None
    if final_utm_campaign:
        mapping = await db.quality_mappings.find_one({"utm_campaign": final_utm_campaign}, {"_id": 0})
        if mapping:
            quality_tier = mapping.get("quality_tier")
    
    # Créer le lead - TOUJOURS SAUVEGARDÉ
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
        "departement": dept,
        "ville": data.ville or "",
        "adresse": data.adresse or "",
        "type_logement": "maison",
        "statut_occupant": "proprietaire",
        "surface_habitable": data.surface_habitable or "",
        "annee_construction": data.annee_construction or "",
        "type_chauffage": data.type_chauffage or "",
        "facture_electricite": data.facture_electricite or "",
        "facture_chauffage": data.facture_chauffage or "",
        "type_projet": data.type_projet or "",
        "delai_projet": data.delai_projet or "",
        "budget": data.budget or "",
        "lp_code": final_lp_code,
        "liaison_code": final_liaison_code,
        "utm_source": utm["source"],
        "utm_medium": utm["medium"],
        "utm_campaign": final_utm_campaign,
        "quality_tier": quality_tier,
        "rgpd_consent": data.rgpd_consent,
        "newsletter": data.newsletter,
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        "origin_crm": origin_crm_slug or target_crm,
        "target_crm": final_crm or "none",
        "routing_reason": routing_reason,
        "routing_source": routing_source,
        "distribution_reason": distribution_reason,
        "api_status": initial_status,
        "sent_to_crm": False,
        "retry_count": 0,
        "phone_invalid": phone_invalid,
        "missing_nom": missing_nom,
        "missing_dept": missing_dept,
        "form_not_found": form_not_found,
        "is_double_submit": is_double_submit,
        "original_lead_id": original_lead_id,
    }
    
    await db.leads.insert_one(lead)
    
    # Envoyer au CRM
    status = initial_status
    message = ""
    actual_crm_sent = None
    warning = None
    
    if initial_status == "orphan":
        message = "Lead enregistré - Formulaire non trouvé"
        warning = "FORM_NOT_FOUND"
    elif initial_status == "invalid_phone":
        message = "Lead enregistré - Téléphone invalide"
        warning = "PHONE_INVALID"
    elif initial_status == "missing_required":
        missing_list = []
        if missing_nom:
            missing_list.append("nom")
        if missing_dept:
            missing_list.append("département")
        message = f"Lead enregistré - Champs manquants: {', '.join(missing_list)}"
        warning = "MISSING_REQUIRED"
    elif initial_status == "double_submit":
        message = "Double soumission détectée - lead déjà créé"
        warning = "DOUBLE_SUBMIT"
        lead_id = original_lead_id
    elif initial_status == "no_crm":
        message = "Lead enregistré - CRM non configuré"
        warning = "CRM_NOT_CONFIGURED"
    elif initial_status == "no_api_key":
        message = "Lead enregistré - Clé API manquante"
        warning = "API_KEY_MISSING"
    elif final_crm and final_key:
        from services.lead_sender import send_to_crm, add_to_queue
        
        api_url = await get_crm_url(final_crm)
        if not api_url:
            status = "no_crm"
            message = f"Lead enregistré - URL API non configurée pour {final_crm.upper()}"
            warning = "API_URL_MISSING"
        else:
            status, response, should_queue = await send_to_crm(lead, api_url, final_key)
            actual_crm_sent = final_crm
            
            if should_queue:
                await add_to_queue(lead, api_url, final_key, "error")
                status = "queued"
            
            message = f"Envoyé vers {actual_crm_sent.upper()}" if status == "success" else str(response)
    else:
        message = "Lead enregistré - Pas de CRM configuré"
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "target_crm": actual_crm_sent or target_crm or "none",
            "sent_to_crm": status in ["success", "duplicate"],
            "sent_at": now_iso() if status in ["success", "duplicate"] else None
        }}
    )
    
    routing_logger.info(
        f"[ROUTING_RESULT] lead_id={lead_id} account_id={account_id} "
        f"product_type={product_type} routing_source={routing_source} "
        f"target_crm={actual_crm_sent or target_crm or 'none'} "
        f"status={status} routing_reason={routing_reason}"
    )
    
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {"status": "converted", "lead_id": lead_id}}
        )
    
    response_data = {
        "success": True,
        "lead_id": lead_id,
        "status": status,
        "crm": actual_crm_sent or target_crm or "none",
        "message": message
    }
    
    if warning:
        response_data["warning"] = warning
        response_data["stored"] = True
    
    return response_data
```

---

## 2. backend/services/lead_sender.py (329 lignes)

```python
"""
Service d'envoi de leads vers les CRMs externes (ZR7, MDL)
- send_to_crm()   : Unique point d'envoi
- add_to_queue()   : File d'attente retry automatique
- process_queue()  : Traitement périodique de la queue

Format API ZR7/MDL:
- Endpoint: POST /lead/api/create_lead/
- Auth: Header Authorization: {token}
- Body: JSON avec phone, register_date, nom, prenom, email, custom_fields
"""

import httpx
import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso

logger = logging.getLogger("lead_sender")

MAX_RETRY_ATTEMPTS = 5
RETRY_DELAYS = [60, 300, 900, 3600, 7200]  # 1min, 5min, 15min, 1h, 2h


async def send_to_crm(lead_doc: dict, api_url: str, api_key: str) -> tuple:
    """
    UNIQUE FONCTION D'ENVOI vers ZR7 ou MDL.
    Returns: (status, response, should_queue)
    """
    custom_fields = {}
    
    custom_field_mapping = {
        "departement": "departement",
        "ville": "ville",
        "adresse": "adresse",
        "type_logement": "type_logement",
        "statut_occupant": "statut_occupant",
        "surface_habitable": "superficie_logement",
        "annee_construction": "annee_construction",
        "type_chauffage": "chauffage_actuel",
        "facture_electricite": "facture_electricite",
        "facture_chauffage": "facture_chauffage",
        "type_projet": "type_projet",
        "delai_projet": "delai_projet",
        "budget": "budget",
        "product_type": "product_type",
        "lp_code": "lp_code",
        "liaison_code": "liaison_code",
        "utm_source": "utm_source",
        "utm_medium": "utm_medium",
        "utm_campaign": "utm_campaign"
    }
    
    for lead_field, crm_field in custom_field_mapping.items():
        value = lead_doc.get(lead_field)
        if value:
            custom_fields[crm_field] = {"value": str(value)}
    
    payload = {
        "phone": lead_doc["phone"],
        "register_date": lead_doc.get("register_date", int(datetime.now().timestamp())),
        "nom": lead_doc.get("nom", ""),
        "prenom": lead_doc.get("prenom", ""),
        "email": lead_doc.get("email", "")
    }
    
    if lead_doc.get("civilite"):
        payload["civilite"] = lead_doc["civilite"]
    
    if custom_fields:
        payload["custom_fields"] = custom_fields
    
    status = "failed"
    response = None
    should_queue = False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json"
                }
            )
            
            try:
                data = resp.json()
                response = str(data)
            except Exception:
                response = resp.text
            
            if resp.status_code == 201:
                status = "success"
                logger.info(f"Lead {lead_doc.get('id')} envoyé avec succès à {api_url}")
            elif resp.status_code == 200 and "doublon" in str(response).lower():
                status = "duplicate"
                logger.info(f"Lead {lead_doc.get('id')} est un doublon")
            elif resp.status_code == 403:
                status = "auth_error"
                logger.error(f"Erreur auth CRM: {response}")
            elif resp.status_code == 400:
                status = "validation_error"
                logger.warning(f"Erreur validation CRM: {response}")
            elif resp.status_code >= 500:
                status = "server_error"
                should_queue = True
                logger.warning(f"Erreur serveur CRM {resp.status_code}: {api_url}")
            else:
                status = "failed"
                logger.warning(f"CRM rejected lead: {response}")
                
    except httpx.TimeoutException as e:
        status = "timeout"
        response = f"Timeout après 30s: {str(e)}"
        should_queue = True
        logger.warning(f"CRM timeout: {api_url}")
        
    except httpx.ConnectError as e:
        status = "connection_error"
        response = f"Erreur connexion: {str(e)}"
        should_queue = True
        logger.warning(f"CRM connection error: {api_url}")
        
    except Exception as e:
        status = "failed"
        response = str(e)
        should_queue = True
        logger.error(f"CRM error: {str(e)}")
    
    return status, response, should_queue


async def add_to_queue(lead_doc: dict, api_url: str, api_key: str, reason: str = "crm_error"):
    existing = await db.lead_queue.find_one({"lead_id": lead_doc.get("id")})
    if existing:
        logger.info(f"Lead {lead_doc.get('id')} déjà en queue")
        return existing
    
    queue_entry = {
        "id": lead_doc.get("id"),
        "lead_id": lead_doc.get("id"),
        "lead_data": lead_doc,
        "api_url": api_url,
        "api_key": api_key,
        "reason": reason,
        "retry_count": 0,
        "max_retries": MAX_RETRY_ATTEMPTS,
        "next_retry_at": now_iso(),
        "created_at": now_iso(),
        "status": "pending",
        "last_error": None
    }
    
    await db.lead_queue.insert_one(queue_entry)
    logger.info(f"Lead {lead_doc.get('id')} ajouté à la queue - raison: {reason}")
    
    await db.leads.update_one(
        {"id": lead_doc.get("id")},
        {"$set": {
            "api_status": "queued",
            "queue_reason": reason,
            "queued_at": now_iso()
        }}
    )
    
    return queue_entry


async def process_queue():
    now = now_iso()
    
    pending = await db.lead_queue.find({
        "status": "pending",
        "next_retry_at": {"$lte": now},
        "retry_count": {"$lt": MAX_RETRY_ATTEMPTS}
    }).to_list(50)
    
    if not pending:
        return {"processed": 0, "success": 0, "failed": 0, "exhausted": 0}
    
    results = {"processed": 0, "success": 0, "failed": 0, "exhausted": 0}
    
    for item in pending:
        await db.lead_queue.update_one(
            {"id": item["id"]},
            {"$set": {"status": "processing"}}
        )
        
        lead_data = item.get("lead_data", {})
        status, response, should_retry = await send_to_crm(
            lead_data, 
            item.get("api_url"), 
            item.get("api_key")
        )
        
        results["processed"] += 1
        
        if status in ["success", "duplicate"]:
            results["success"] += 1
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {"status": "success", "completed_at": now_iso()}}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {
                    "api_status": status,
                    "sent_to_crm": True,
                    "sent_at": now_iso(),
                    "retry_count": item["retry_count"] + 1
                }}
            )
            
        elif should_retry:
            new_count = item["retry_count"] + 1
            
            if new_count >= MAX_RETRY_ATTEMPTS:
                results["exhausted"] += 1
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "exhausted",
                        "last_error": response,
                        "exhausted_at": now_iso()
                    }}
                )
                await db.leads.update_one(
                    {"id": item["lead_id"]},
                    {"$set": {
                        "api_status": "failed",
                        "api_response": f"Épuisé après {MAX_RETRY_ATTEMPTS} tentatives: {response}"
                    }}
                )
            else:
                results["failed"] += 1
                delay = RETRY_DELAYS[min(new_count, len(RETRY_DELAYS) - 1)]
                next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "pending",
                        "retry_count": new_count,
                        "next_retry_at": next_retry,
                        "last_error": response
                    }}
                )
        else:
            results["failed"] += 1
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {
                    "status": "failed",
                    "last_error": response,
                    "failed_at": now_iso()
                }}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {"api_status": "failed", "api_response": response}}
            )
    
    return results


async def get_queue_stats():
    return {
        "pending": await db.lead_queue.count_documents({"status": "pending"}),
        "processing": await db.lead_queue.count_documents({"status": "processing"}),
        "success": await db.lead_queue.count_documents({"status": "success"}),
        "failed": await db.lead_queue.count_documents({"status": "failed"}),
        "exhausted": await db.lead_queue.count_documents({"status": "exhausted"}),
        "total": await db.lead_queue.count_documents({})
    }
```

---

## 3. backend/config.py (176 lignes)

```python
"""
Configuration et utilitaires partagés
"""

import os
import hashlib
import secrets
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

print(f"[CONFIG] Using database: {DB_NAME}")

BACKEND_URL = os.environ.get('BACKEND_URL')
if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable is required")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    return f"crm_{secrets.token_urlsafe(32)}"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def validate_phone_fr(phone: str) -> tuple[bool, str]:
    """
    Valide un numéro de téléphone français.
    Règles: 10 chiffres, commence par 0, pas de suite, pas de répétition.
    Returns: (is_valid, cleaned_phone_or_error)
    """
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 9 and not digits.startswith('0'):
        digits = '0' + digits
    
    if len(digits) != 10:
        return False, "Le téléphone doit contenir 10 chiffres"
    
    if not digits.startswith('0'):
        return False, "Le téléphone doit commencer par 0"
    
    if digits in "0123456789" or digits in "9876543210":
        return False, "Numéro invalide (suite)"
    
    is_pair_sequence = True
    for i in range(0, 8, 2):
        curr = int(digits[i:i+2])
        next_val = int(digits[i+2:i+4])
        if abs(next_val - curr) != 1:
            is_pair_sequence = False
            break
    if is_pair_sequence:
        return False, "Numéro invalide (suite)"
    
    first_digit = digits[1]
    same_count = sum(1 for d in digits[1:] if d == first_digit)
    if same_count >= 8:
        return False, "Numéro invalide (répétition)"
    
    return True, digits


FRANCE_METRO_DEPTS = [str(i).zfill(2) for i in range(1, 96)] + ["2A", "2B"]

def validate_postal_code_fr(code: str) -> tuple[bool, str]:
    if not code:
        return True, ""
    
    digits = ''.join(filter(str.isdigit, code))
    
    if len(digits) != 5:
        return False, "Le code postal doit contenir 5 chiffres"
    
    dept = digits[:2]
    if dept not in FRANCE_METRO_DEPTS:
        return False, "Code postal France métropolitaine uniquement (01-95)"
    
    return True, digits


async def generate_lp_code() -> str:
    all_lps = await db.lps.find({"code": {"$regex": "^LP-\\d+$"}}, {"code": 1}).to_list(1000)
    
    max_num = 0
    for lp in all_lps:
        code = lp.get("code", "")
        try:
            num = int(code.split("-")[1])
            if num > max_num:
                max_num = num
        except:
            pass
    
    return f"LP-{str(max_num + 1).zfill(3)}"


async def generate_form_code(product_type: str) -> str:
    prefix = product_type.upper()
    if prefix not in ["PV", "PAC", "ITE"]:
        prefix = "PV"
    
    all_forms = await db.forms.find({"code": {"$regex": f"^{prefix}-\\d+$"}}, {"code": 1}).to_list(1000)
    
    max_num = 0
    for form in all_forms:
        code = form.get("code", "")
        try:
            num = int(code.split("-")[1])
            if num > max_num:
                max_num = num
        except:
            pass
    
    return f"{prefix}-{str(max_num + 1).zfill(3)}"
```

---

## 4. backend/services/duplicate_detector.py (85 lignes)

```python
"""
SERVICE DE PROTECTION ANTI DOUBLE-SUBMIT
Unique règle: même session + même phone en < 5 secondes
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from config import db

logger = logging.getLogger("duplicate_detector")

DOUBLE_SUBMIT_SECONDS = 5


class DuplicateResult:
    def __init__(
        self,
        is_duplicate: bool,
        duplicate_type: Optional[str] = None,
        original_lead_id: Optional[str] = None,
        original_status: Optional[str] = None,
        original_sent_to_crm: bool = False,
        message: str = ""
    ):
        self.is_duplicate = is_duplicate
        self.duplicate_type = duplicate_type
        self.original_lead_id = original_lead_id
        self.original_status = original_status
        self.original_sent_to_crm = original_sent_to_crm
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "duplicate_type": self.duplicate_type,
            "original_lead_id": self.original_lead_id,
            "original_status": self.original_status,
            "original_sent_to_crm": self.original_sent_to_crm,
            "message": self.message
        }


async def check_duplicate(
    phone: str,
    departement: str,
    session_id: Optional[str] = None
) -> DuplicateResult:
    if not phone:
        return DuplicateResult(is_duplicate=False)

    now = datetime.now(timezone.utc)

    if session_id:
        cutoff = (now - timedelta(seconds=DOUBLE_SUBMIT_SECONDS)).isoformat()
        double_submit = await db.leads.find_one({
            "session_id": session_id,
            "phone": phone,
            "created_at": {"$gte": cutoff}
        }, {"_id": 0, "id": 1})

        if double_submit:
            logger.info(f"Double-submit détecté pour session {session_id[:8]}...")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type="double_submit",
                original_lead_id=double_submit.get("id"),
                message="Double soumission détectée - lead déjà créé"
            )

    return DuplicateResult(is_duplicate=False)
```

---

## 5. backend/services/brief_generator.py

> Fichier trop long (1556 lignes) pour être dupliqué ici en markdown.
> Contenu complet déjà affiché dans la réponse précédente.
> Résumé des templates JS générés :

**Mode A (separate) — 2 scripts distincts :**
- Script LP (~290 lignes JS) : session init, lp-visit, UTM capture, CTA auto-bind, MutationObserver
- Script Form (~290 lignes JS) : session recovery (URL > sessionStorage > new), form_start, rdzSubmitLead(), GTM conversion, redirection

**Mode B (integrated) — 1 script unique :**
- Script unique (~360 lignes JS) : tout combiné sur 1 page (LP + Form)

**Mini Brief (comptes) :** logos, GTM head/body/conversion, textes légaux, URL redirection

---

## 6. frontend/src/pages/Forms.jsx

> Fichier complet (902 lignes) déjà affiché dans la réponse précédente.
> Résumé fonctionnel :

- **Liste formulaires** : cartes colorées par produit (PV/PAC/ITE), stats, LP liée
- **CRUD** : création (LP obligatoire), édition, duplication, archivage
- **Brief modal** : sélecteur produit (PV/PAC/ITE pour URL redirection), affichage script LP + script Form, bouton copier
- **Reset stats** : admin only, snapshot avant reset
- **Config CRM** : target_crm, crm_api_key (verrouillée après enregistrement), cross-CRM checkbox
