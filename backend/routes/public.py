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

from config import db, now_iso, timestamp, validate_phone_fr
from routes.commandes import has_commande  # Import centralisé - PAS DE DUPLICATION

router = APIRouter(prefix="/public", tags=["Public"])


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
    
    # Anti-doublon: lp_visit, cta_click et form_start = 1x par session maximum
    if data.event_type in ["lp_visit", "cta_click", "form_start"]:
        existing = await db.tracking.find_one({
            "session_id": data.session_id,
            "event": data.event_type
        })
        if existing:
            return {"success": True, "event_id": existing.get("id"), "duplicate": True}
    
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
    """
    Soumettre un lead
    
    RÈGLE ABSOLUE : Le lead est TOUJOURS créé dans RDZ, peu importe :
    - Si le téléphone est invalide → lead créé avec flag phone_invalid
    - Si nom/département manquant → lead créé avec flag missing_required
    - Si le formulaire n'existe pas → lead orphelin créé
    - Si la clé API est manquante → lead créé avec status no_api_key
    - Si pas de commande → lead créé avec status pending_no_order
    
    CHAMPS OBLIGATOIRES : phone, nom, departement
    """
    
    # Valider téléphone - mais NE PAS bloquer si invalide
    is_valid, phone_result = validate_phone_fr(data.phone)
    phone = phone_result if is_valid else data.phone  # Garder le téléphone brut si invalide
    phone_invalid = not is_valid
    
    # Valider champs obligatoires (nom, departement)
    nom = (data.nom or "").strip()
    dept = (data.departement or "").strip()
    missing_nom = not nom
    missing_dept = not dept
    missing_required = missing_nom or missing_dept
    
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
    
    # Vérifier que le CRM cible est configuré en DB
    target_crm_url = await get_crm_url(target_crm) if target_crm else None
    
    # IMPORTANT: On ne bloque plus si clé API manquante !
    # Le lead sera TOUJOURS créé, avec un statut approprié
    has_api_key = bool(crm_api_key and crm_api_key.strip())
    has_crm_config = bool(target_crm and target_crm_url)
    
    # Vérifier commandes et trouver le bon CRM
    final_crm = None
    final_key = None
    is_transferred = False  # Le lead sera-t-il transféré vers un autre CRM ?
    routing_reason = "no_crm"  # Raison du routing
    
    if has_crm_config and has_api_key:
        # Cas normal : CRM et clé configurés
        crm_id = await get_crm_id(target_crm)
        if crm_id and await has_commande(crm_id, product_type, dept):
            final_crm = target_crm
            final_key = crm_api_key
            routing_reason = f"commande_{target_crm}"
        elif allow_cross_crm:
            other = "mdl" if target_crm == "zr7" else "zr7"
            other_id = await get_crm_id(other)
            if other_id and await has_commande(other_id, product_type, dept):
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
    
    # Déterminer le statut initial
    # RÈGLE: Lead TOUJOURS sauvegardé, peu importe la config
    if form_not_found:
        initial_status = "orphan"  # Lead orphelin - formulaire non trouvé
        distribution_reason = "FORM_NOT_FOUND"
    elif phone_invalid:
        initial_status = "invalid_phone"  # Téléphone invalide
        distribution_reason = "PHONE_INVALID"
    elif missing_required:
        initial_status = "missing_required"  # Champs obligatoires manquants
        missing_fields = []
        if missing_nom:
            missing_fields.append("nom")
        if missing_dept:
            missing_fields.append("departement")
        distribution_reason = f"MISSING_REQUIRED:{','.join(missing_fields)}"
    elif not has_crm_config:
        initial_status = "no_crm"
        distribution_reason = "CRM_NOT_CONFIGURED"
    elif not has_api_key:
        initial_status = "no_api_key"  # Clé API manquante
        distribution_reason = "API_KEY_MISSING"
    elif final_crm and final_key:
        initial_status = "pending"
        distribution_reason = routing_reason
    else:
        initial_status = "pending_no_order"  # En attente de redistribution
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
        "distribution_reason": distribution_reason,  # Raison de la distribution
        "allow_cross_crm": allow_cross_crm,  # Cross-CRM autorisé ?
        "api_status": initial_status,  # pending, pending_no_order, no_api_key, no_crm, orphan, invalid_phone, missing_required
        "sent_to_crm": False,
        "manual_only": False,  # Pour redistribution auto
        "retry_count": 0,
        # FLAGS de diagnostic
        "phone_invalid": phone_invalid,  # True si téléphone non valide
        "missing_nom": missing_nom,  # True si nom manquant
        "missing_dept": missing_dept,  # True si département manquant
        "form_not_found": form_not_found  # True si formulaire non trouvé
    }
    
    # TOUJOURS sauvegarder le lead
    await db.leads.insert_one(lead)
    
    # Envoyer au CRM (seulement si on a un CRM et une clé ET pas de problème de données)
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
    elif initial_status == "no_crm":
        message = "Lead enregistré - CRM non configuré"
        warning = "CRM_NOT_CONFIGURED"
    elif initial_status == "no_api_key":
        message = "Lead enregistré - Clé API manquante"
        warning = "API_KEY_MISSING"
    elif final_crm and final_key:
        from services.lead_sender import send_to_crm_v2, add_to_queue
        
        # Récupérer URL dynamiquement depuis la DB
        api_url = await get_crm_url(final_crm)
        if not api_url:
            # URL manquante - on garde le lead mais on notifie
            status = "no_crm"
            message = f"Lead enregistré - URL API non configurée pour {final_crm.upper()}"
            warning = "API_URL_MISSING"
        else:
            status, response, should_queue = await send_to_crm_v2(lead, api_url, final_key)
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
                        status, response, should_queue = await send_to_crm_v2(lead, other_url, other_key)
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
        response_data["stored"] = True  # Confirme que le lead est stocké dans RDZ
    
    return response_data
