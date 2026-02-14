"""
RDZ CRM - Routes Publiques
- Tracking sessions visiteurs
- Tracking evenements LP/Form
- Soumission leads avec routing immediat (Phase 2)
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import logging

from config import db, now_iso, timestamp, validate_phone_fr
from services.routing_engine import route_lead, RoutingResult
from services.settings import get_form_config, is_source_allowed

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
    # Provider auth (API key dans le body ou header)
    api_key: Optional[str] = ""


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
    Soumettre un lead avec routing immediat (Phase 2)

    FLUX:
    1. Valider telephone
    2. Anti double-submit (5 sec)
    3. Resoudre entity + produit (provider OU form_code)
    4. Sauvegarder lead
    5. Router immediatement si eligible
    6. Retourner resultat enrichi

    STATUTS POSSIBLES:
    - routed: lead livre a un client
    - no_open_orders: aucune commande OPEN compatible
    - hold_source: source blacklistee
    - duplicate: doublon 30j chez tous les clients
    - invalid: donnees incompletes
    """
    from services.duplicate_detector import check_double_submit

    # ---- Provider auth ----
    api_key = data.api_key or ""
    if not api_key:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:].strip()
        elif auth_header.startswith("prov_"):
            api_key = auth_header.strip()

    provider = None
    entity_locked = False

    if api_key and api_key.startswith("prov_"):
        provider = await db.providers.find_one(
            {"api_key": api_key, "active": True},
            {"_id": 0}
        )
        if not provider:
            return {"success": False, "error": "API key provider invalide ou inactive"}

    # Valider telephone
    is_valid, phone_result = validate_phone_fr(data.phone)
    phone = phone_result if is_valid else data.phone

    # Champs obligatoires
    nom = (data.nom or "").strip()
    dept = (data.departement or "").strip()[:2] if data.departement else ""

    # Champs minimaux valides (phone + departement + nom)
    lead_minimal_valid = bool(is_valid and nom and dept)

    # Anti double-submit (5 sec)
    if is_valid and data.session_id:
        dup_result = await check_double_submit(phone, data.session_id)
        if dup_result.is_duplicate:
            return {
                "success": True,
                "lead_id": dup_result.original_lead_id,
                "status": "double_submit",
                "message": "Double soumission detectee - lead deja cree"
            }

    # ---- Resoudre entity + produit ----
    entity = (data.entity or "").upper()
    produit = (data.produit or "").upper()

    # Si provider: entity VERROUILLEE
    if provider:
        entity = provider.get("entity", "")
        entity_locked = True
        # produit peut venir du body
    
    # Si pas provider ET pas entity/produit: resoudre depuis form_code
    if not provider and (not entity or not produit) and data.form_code:
        form_config = await get_form_config(data.form_code)
        if form_config:
            entity = entity or form_config.get("entity", "")
            produit = produit or form_config.get("produit", "")
        else:
            logger.warning(f"[LEAD] form_code={data.form_code} non configure - entity/produit manquants")

    # Recuperer session pour source/UTM
    session = await db.visitor_sessions.find_one({"id": data.session_id}, {"_id": 0})
    utm_source = session.get("utm_source", "") if session else ""
    utm_medium = session.get("utm_medium", "") if session else ""
    utm_campaign = data.utm_campaign or (session.get("utm_campaign", "") if session else "")
    lp_code = data.lp_code or (session.get("lp_code", "") if session else "")

    source_name = utm_source or lp_code or ""
    
    # Source gating
    source_blocked = False
    if lead_minimal_valid and source_name:
        allowed = await is_source_allowed(source_name)
        if not allowed:
            source_blocked = True

    # Determiner le statut initial
    if not lead_minimal_valid:
        initial_status = "invalid"
    elif source_blocked:
        initial_status = "hold_source"
    elif not entity or not produit:
        initial_status = "pending_config"  # Manque config form
    else:
        initial_status = "new"

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
        "lead_owner_entity": entity,  # Immutable: entity at ingestion time
        "produit": produit,
        "status": initial_status,
        "is_lb": False,
        # Provider
        "provider_id": provider.get("id") if provider else None,
        "provider_slug": provider.get("slug") if provider else None,
        "entity_locked": entity_locked,
        # Tracking
        "session_id": data.session_id,
        "form_code": data.form_code or "",
        "lp_code": lp_code,
        "liaison_code": data.liaison_code or "",
        "source": source_name,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        # Champs secondaires
        "custom_fields": {},
        # Meta
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
    }

    # Source blocked flag
    if source_blocked:
        lead["hold_reason"] = f"source_blocked:{source_name}"

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

    # ======== INSERT LEAD ========
    await db.leads.insert_one(lead)

    # MAJ session
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {"status": "converted", "lead_id": lead_id}}
        )

    # ======== ROUTING IMMEDIAT ========
    routing_result = None
    delivery_id = None
    
    # Conditions pour router:
    # - lead_minimal_valid
    # - NOT source_blocked
    # - entity + produit presents
    can_route = lead_minimal_valid and not source_blocked and entity and produit

    if can_route:
        routing_result = await route_lead(
            entity=entity,
            produit=produit,
            departement=dept,
            phone=phone,
            is_lb=False,
            entity_locked=entity_locked
        )

        if routing_result.success:
            # Creer delivery record
            delivery_id = str(uuid.uuid4())
            delivery = {
                "id": delivery_id,
                "lead_id": lead_id,
                "client_id": routing_result.client_id,
                "client_name": routing_result.client_name,
                "commande_id": routing_result.commande_id,
                "entity": entity,
                "produit": produit,
                "delivery_method": "realtime",
                "status": "pending_csv",  # Sera envoye dans le batch CSV du matin
                "is_lb": False,
                "created_at": now_iso(),
            }
            await db.deliveries.insert_one(delivery)

            # MAJ lead
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {
                    "status": "routed",
                    "delivery_id": delivery_id,
                    "delivery_client_id": routing_result.client_id,
                    "delivery_client_name": routing_result.client_name,
                    "delivery_commande_id": routing_result.commande_id,
                    "routed_at": now_iso()
                }}
            )
            lead["status"] = "routed"
        else:
            # Pas de commande OPEN
            reason = routing_result.reason
            if "duplicate" in reason:
                new_status = "duplicate"
            else:
                new_status = "no_open_orders"
            
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {
                    "status": new_status,
                    "routing_reason": reason
                }}
            )
            lead["status"] = new_status

    # ======== LOG ========
    log_msg = (
        f"[LEAD_CREATED] id={lead_id} phone=***{phone[-4:] if len(phone) >= 4 else phone} "
        f"entity={entity or 'N/A'} produit={produit or 'N/A'} dept={dept} "
        f"status={lead['status']}"
    )
    if provider:
        log_msg += f" provider={provider.get('slug')} entity_locked=True"
    if source_blocked:
        log_msg += f" HOLD_SOURCE={source_name}"
    if routing_result:
        if routing_result.success:
            log_msg += f" -> ROUTED to {routing_result.client_name}"
        else:
            log_msg += f" -> {routing_result.reason}"
    logger.info(log_msg)

    # ======== RESPONSE ========
    response = {
        "success": True,
        "lead_id": lead_id,
        "status": lead["status"],
        "entity": entity or None,
        "produit": produit or None,
    }

    if delivery_id:
        response["delivery_id"] = delivery_id
        response["client_id"] = routing_result.client_id
        response["client_name"] = routing_result.client_name
        response["message"] = f"Lead route vers {routing_result.client_name}"
    elif source_blocked:
        response["message"] = "Lead stocke - source en attente de validation"
    elif not lead_minimal_valid:
        response["message"] = "Lead stocke - donnees incompletes"
    elif not entity or not produit:
        response["message"] = "Lead stocke - configuration formulaire manquante"
    elif routing_result and not routing_result.success:
        response["message"] = f"Lead stocke - {routing_result.reason}"
        response["routing_reason"] = routing_result.reason
    else:
        response["message"] = "Lead enregistre"

    return response
