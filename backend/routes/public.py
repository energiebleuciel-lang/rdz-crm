"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔒🔒🔒  FICHIER CRITIQUE VERROUILLÉ - NE PAS MODIFIER  🔒🔒🔒               ║
║                                                                              ║
║  Ce fichier contient le NOYAU CRITIQUE d'intégration des leads:              ║
║  - submit_lead()    : Réception leads                                        ║
║  - create_session() : Tracking sessions                                      ║
║  - track_event()    : Événements tracking                                    ║
║  - get_crm_url()    : URLs CRM                                               ║
║                                                                              ║
║  DÉVERROUILLAGE REQUIS: "Je déverrouille le noyau critique pour modifier X"  ║
╚══════════════════════════════════════════════════════════════════════════════╝

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
    """
    Parse le body de manière tolérante pour sendBeacon
    sendBeacon peut envoyer avec content-type: text/plain ou application/json
    """
    try:
        body = await request.body()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))
    except Exception:
        return {}


# ==================== HELPERS ====================

async def get_crm_info(slug: str) -> dict:
    """Récupère les infos complètes du CRM depuis son slug (ID + URL)"""
    crm = await db.crms.find_one({"slug": slug}, {"_id": 0})
    return crm if crm else None


async def get_crm_id(slug: str) -> str:
    """Récupère l'ID du CRM depuis son slug"""
    crm = await get_crm_info(slug)
    return crm.get("id") if crm else None


async def get_crm_url(slug: str) -> str:
    """Récupère l'URL API du CRM depuis son slug (dynamique depuis DB)"""
    crm = await get_crm_info(slug)
    return crm.get("api_url") if crm else None


# ==================== MODELS ====================

class SessionData(BaseModel):
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    referrer: Optional[str] = ""
    user_agent: Optional[str] = ""
    # UTM complet
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    utm_content: Optional[str] = ""
    utm_term: Optional[str] = ""
    # Tracking publicitaire
    gclid: Optional[str] = ""
    fbclid: Optional[str] = ""


class LeadData(BaseModel):
    """
    Modèle pour soumission de lead
    Utilisé par POST /leads
    """
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
    # Attribution
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    utm_campaign: Optional[str] = ""


# ==================== ENDPOINTS ====================

@router.post("/track/session")
async def create_session(data: SessionData, request: Request):
    """
    Créer une session visiteur
    
    Retourne session_id existante si déjà créée pour ce visiteur + LP
    pour éviter les doublons de session
    """
    
    visitor_id = request.cookies.get("_rdz_vid")
    is_new = not visitor_id
    if is_new:
        visitor_id = str(uuid.uuid4())
    
    lp_code = data.lp_code or ""
    form_code = data.form_code or ""
    liaison_code = data.liaison_code or ""
    
    # Si LP sans form, chercher le form lié
    if lp_code and not form_code:
        lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
        if lp and lp.get("form_id"):
            form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
            if form:
                form_code = form.get("code", "")
                if not liaison_code:
                    liaison_code = f"{lp_code}_{form_code}"
    
    # Anti-doublon: vérifier si une session existe déjà pour ce visiteur + LP
    # (dans les dernières 30 minutes)
    if visitor_id and lp_code:
        from datetime import datetime, timedelta, timezone
        thirty_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        existing = await db.visitor_sessions.find_one({
            "visitor_id": visitor_id,
            "lp_code": lp_code,
            "created_at": {"$gte": thirty_min_ago}
        }, {"_id": 0})
        if existing:
            # Retourner la session existante
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
        # UTM complet
        "utm_source": data.utm_source or "",
        "utm_medium": data.utm_medium or "",
        "utm_campaign": data.utm_campaign or "",
        "utm_content": data.utm_content or "",
        "utm_term": data.utm_term or "",
        # Tracking publicitaire
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
    """
    Endpoint dédié pour tracking visite LP
    Compatible sendBeacon (content-type tolérant)
    
    Anti-doublon: 1 seule visite par session
    Enregistre tous les paramètres UTM et tracking
    """
    
    # Parse body de manière tolérante (sendBeacon compatible)
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")
    
    if not session_id:
        return {"success": False, "error": "session_id requis"}
    
    # Vérifier que la session existe
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
    
    # Récupérer infos LP
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
        # UTM complet
        "utm_source": data.get("utm_source") or "",
        "utm_medium": data.get("utm_medium") or "",
        "utm_campaign": data.get("utm_campaign") or "",
        "utm_content": data.get("utm_content") or "",
        "utm_term": data.get("utm_term") or "",
        # Tracking publicitaire
        "gclid": data.get("gclid") or "",
        "fbclid": data.get("fbclid") or "",
        # Contexte
        "referrer": data.get("referrer") or "",
        "user_agent": data.get("user_agent") or request.headers.get("user-agent", ""),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
    await db.tracking.insert_one(event)
    
    # Mettre à jour la session avec les UTM si non renseignés
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
    """
    Enregistrer un événement de tracking
    Compatible sendBeacon (content-type tolérant)
    """
    
    # Parse body de manière tolérante (sendBeacon compatible)
    data = await parse_beacon_body(request)
    session_id = data.get("session_id", "")
    event_type = data.get("event_type", "")
    
    if not session_id or not event_type:
        return {"success": False, "error": "session_id et event_type requis"}
    
    session = await db.visitor_sessions.find_one({"id": session_id})
    if not session:
        return {"success": False, "error": "Session invalide"}
    
    # Anti-doublon: lp_visit, cta_click et form_start = 1x par session maximum
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
    
    # Construire liaison_code si non fourni
    if not liaison_code and lp_code and form_code:
        liaison_code = f"{lp_code}_{form_code}"
    
    # Stocker dans tracking
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
    """
    Soumettre un lead
    
    RÈGLE ABSOLUE : Le lead est TOUJOURS créé dans RDZ, peu importe :
    - Si le téléphone est invalide → lead créé avec flag phone_invalid
    - Si nom/département manquant → lead créé avec flag missing_required
    - Si le formulaire n'existe pas → lead orphelin créé
    - Si la clé API est manquante → lead créé avec status no_api_key
    - Si pas de commande → lead créé avec status pending_no_order
    
    PROTECTION ANTI DOUBLE-SUBMIT: 5 secondes (même session + même phone)
    
    CHAMPS OBLIGATOIRES : phone, nom, departement
    """
    from services.duplicate_detector import check_duplicate
    
    # Valider téléphone - mais NE PAS bloquer si invalide
    is_valid, phone_result = validate_phone_fr(data.phone)
    phone = phone_result if is_valid else data.phone
    phone_invalid = not is_valid
    
    # Valider champs obligatoires (nom, departement)
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
    
    # Si formulaire non trouvé, créer un lead "orphelin" quand même
    form_not_found = form is None
    if form_not_found:
        form = {
            "id": None,
            "code": data.form_code or "UNKNOWN",
            "product_type": "PV",
            "account_id": "",
            "target_crm": "",
            "crm_api_key": "",
            "allow_cross_crm": False
        }
    
    form_code = form.get("code", "")
    product_type = form.get("product_type", "PV")
    account_id = form.get("account_id", "")
    allow_cross_crm = form.get("allow_cross_crm", True)
    
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
    # Hiérarchie:
    #   1. form.target_crm + form.crm_api_key (override si les deux sont renseignés)
    #   2. account.crm_routing[product_type] (config par défaut du compte)
    #   3. Aucun CRM configuré → no_crm
    
    import logging
    routing_logger = logging.getLogger("routing")
    
    VALID_TARGET_CRMS = {"zr7", "mdl"}
    
    target_crm = ""
    crm_api_key = ""
    routing_source = "none"  # Traçabilité: d'où vient la config
    
    # Étape 1: Vérifier l'override formulaire (whitelist obligatoire)
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
    
    # Étape 2: Vérifier la config account
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
    
    # Vérifier que le CRM cible est configuré en DB
    target_crm_url = await get_crm_url(target_crm) if target_crm else None
    
    has_api_key = bool(crm_api_key)
    has_crm_config = bool(target_crm and target_crm_url)
    
    # Résolution finale du CRM
    final_crm = None
    final_key = None
    routing_reason = "no_crm"
    
    if has_crm_config and has_api_key:
        final_crm = target_crm
        final_key = crm_api_key
        routing_reason = f"{routing_source}_{target_crm}"
    
    # Déterminer le statut initial
    # RÈGLE: Lead TOUJOURS sauvegardé, peu importe la config
    # PRIORITÉ: Double-submit > Erreurs de données > Config CRM
    
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
    
    # Priorité: données du formulaire > session
    final_lp_code = data.lp_code or lp_code_from_session
    final_liaison_code = data.liaison_code or (f"{final_lp_code}_{form_code}" if final_lp_code else form_code)
    final_utm_campaign = data.utm_campaign or utm["campaign"]
    
    # Mapping utm_campaign → quality_tier (1/2/3)
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
        "quality_tier": quality_tier,  # 1/2/3 ou null si pas de mapping
        "rgpd_consent": data.rgpd_consent,
        "newsletter": data.newsletter,
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "register_date": timestamp(),
        "created_at": now_iso(),
        # CRM info - Champs harmonisés avec leads.py v1
        "origin_crm": origin_crm_slug or target_crm,  # CRM d'origine (compte)
        "target_crm": final_crm or "none",  # CRM de destination final (slug)
        "is_transferred": is_transferred,  # Transféré vers autre CRM ?
        "routing_reason": routing_reason,  # Raison du routing
        "routing_source": routing_source,  # D'où vient la config CRM: account_routing, form_override, none
        "distribution_reason": distribution_reason,  # Raison de la distribution
        "allow_cross_crm": allow_cross_crm,  # Cross-CRM autorisé ?
        "api_status": initial_status,  # pending, pending_no_order, no_api_key, no_crm, orphan, invalid_phone, missing_required, double_submit
        "sent_to_crm": False,
        "manual_only": False,  # Pour redistribution auto
        "retry_count": 0,
        # FLAGS de diagnostic
        "phone_invalid": phone_invalid,
        "missing_nom": missing_nom,
        "missing_dept": missing_dept,
        "form_not_found": form_not_found,
        "is_double_submit": is_double_submit,
        "original_lead_id": original_lead_id,
    }
    
    # TOUJOURS sauvegarder le lead
    await db.leads.insert_one(lead)
    
    # Envoyer au CRM (seulement si on a un CRM et une clé ET pas de problème de données ET pas doublon)
    status = initial_status  # Garder le statut initial par défaut
    message = ""
    actual_crm_sent = None
    warning = None  # Pour notifier des problèmes non-bloquants
    
    # Gérer les différents cas d'erreur
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
    # === NOUVEAU: Gestion doublons internes RDZ ===
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
        
        # Récupérer URL dynamiquement depuis la DB
        api_url = await get_crm_url(final_crm)
        if not api_url:
            # URL manquante - on garde le lead mais on notifie
            status = "no_crm"
            message = f"Lead enregistré - URL API non configurée pour {final_crm.upper()}"
            warning = "API_URL_MISSING"
        else:
            status, response, should_queue = await send_to_crm(lead, api_url, final_key)
            actual_crm_sent = final_crm
            
            # FALLBACK : Si erreur (Token invalide, etc.) et cross_crm autorisé → essayer l'autre CRM
            if status == "failed" and allow_cross_crm:
                other_crm = "mdl" if final_crm == "zr7" else "zr7"
                # Chercher la clé API de l'autre CRM dans les formulaires du même compte
                other_form = await db.forms.find_one({
                    "account_id": account_id,
                    "target_crm": other_crm,
                    "crm_api_key": {"$exists": True, "$ne": ""}
                }, {"_id": 0})
                
                if other_form and other_form.get("crm_api_key"):
                    other_key = other_form["crm_api_key"]
                    other_url = await get_crm_url(other_crm)  # URL dynamique
                    if other_url:
                        status, response, should_queue = await send_to_crm(lead, other_url, other_key)
                        actual_crm_sent = other_crm
                        
                        # Marquer comme transféré (fallback utilisé)
                        await db.leads.update_one(
                            {"id": lead_id},
                            {"$set": {"is_transferred": True, "routing_reason": f"fallback_{other_crm}"}}
                        )
            
            if should_queue:
                await add_to_queue(lead, api_url, final_key, "error")
                status = "queued"
            
            message = f"Envoyé vers {actual_crm_sent.upper()}" if status == "success" else str(response)
    else:
        # Pas de commande trouvée
        message = "Lead enregistré - En attente de commande active"
    
    # Mettre à jour le lead avec le statut final
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "target_crm": actual_crm_sent or target_crm or "none",
            "sent_to_crm": status in ["success", "duplicate"],
            "sent_at": now_iso() if status in ["success", "duplicate"] else None
        }}
    )
    
    # LOG COMPLET DE ROUTAGE
    routing_logger.info(
        f"[ROUTING_RESULT] lead_id={lead_id} account_id={account_id} "
        f"product_type={product_type} routing_source={routing_source} "
        f"target_crm={actual_crm_sent or target_crm or 'none'} "
        f"status={status} is_transferred={is_transferred} "
        f"routing_reason={routing_reason}"
    )
    
    # Mettre à jour la session
    if session:
        await db.visitor_sessions.update_one(
            {"id": data.session_id},
            {"$set": {"status": "converted", "lead_id": lead_id}}
        )
    
    # IMPORTANT: Toujours retourner success=true pour le formulaire
    # Le visiteur ne doit pas voir d'erreur, même si le lead n'est pas envoyé au CRM
    response_data = {
        "success": True,  # TOUJOURS true si le lead est créé
        "lead_id": lead_id,
        "status": status,
        "crm": actual_crm_sent or target_crm or "none",
        "message": message
    }
    
    # Ajouter le warning si présent (pour debug/logs côté client)
    if warning:
        response_data["warning"] = warning
        response_data["stored"] = True
    
    return response_data
