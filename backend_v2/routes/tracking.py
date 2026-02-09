"""
Routes de Tracking
Gère les événements: visite LP, clic CTA, début form
"""

from fastapi import APIRouter, HTTPException, Request
import uuid

from models import TrackLPVisit, TrackCTAClick, TrackFormStart
from config import db, now_iso

router = APIRouter(prefix="/track", tags=["Tracking"])


@router.post("/lp-visit")
async def track_lp_visit(data: TrackLPVisit, request: Request):
    """
    Enregistre une visite de LP.
    Appelé quand la page LP est chargée.
    """
    # Vérifier que la LP existe
    lp = await db.lps.find_one({"code": data.lp_code})
    if not lp:
        return {"success": False, "error": "LP inconnue"}
    
    event = {
        "id": str(uuid.uuid4()),
        "event": "lp_visit",
        "lp_code": data.lp_code,
        "lp_id": lp.get("id"),
        "account_id": lp.get("account_id"),
        "referrer": data.referrer or "",
        "user_agent": data.user_agent or request.headers.get("user-agent", ""),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
    await db.tracking.insert_one(event)
    
    return {"success": True, "event_id": event["id"]}


@router.post("/cta-click")
async def track_cta_click(data: TrackCTAClick, request: Request):
    """
    Enregistre un clic sur le CTA de la LP.
    Appelé quand l'utilisateur clique sur "Demander un devis" etc.
    """
    # Vérifier que la LP existe
    lp = await db.lps.find_one({"code": data.lp_code})
    if not lp:
        return {"success": False, "error": "LP inconnue"}
    
    event = {
        "id": str(uuid.uuid4()),
        "event": "cta_click",
        "lp_code": data.lp_code,
        "lp_id": lp.get("id"),
        "form_code": data.form_code or "",
        "account_id": lp.get("account_id"),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
    await db.tracking.insert_one(event)
    
    return {"success": True, "event_id": event["id"]}


@router.post("/form-start")
async def track_form_start(data: TrackFormStart, request: Request):
    """
    Enregistre le début d'un formulaire.
    Appelé quand l'utilisateur commence à remplir le form.
    """
    # Vérifier que le form existe
    form = await db.forms.find_one({"code": data.form_code})
    if not form:
        return {"success": False, "error": "Formulaire inconnu"}
    
    # Générer le code de liaison si LP fournie
    liaison_code = data.liaison_code or ""
    if not liaison_code and data.lp_code:
        liaison_code = f"{data.lp_code}_{data.form_code}"
    
    event = {
        "id": str(uuid.uuid4()),
        "event": "form_start",
        "form_code": data.form_code,
        "form_id": form.get("id"),
        "lp_code": data.lp_code or "",
        "liaison_code": liaison_code,
        "account_id": form.get("account_id"),
        "ip": request.headers.get("x-forwarded-for", request.client.host if request.client else ""),
        "created_at": now_iso()
    }
    
    await db.tracking.insert_one(event)
    
    return {"success": True, "event_id": event["id"]}


@router.get("/stats/{code}")
async def get_tracking_stats(code: str):
    """
    Récupère les stats de tracking pour un code (LP ou Form).
    """
    # Stats LP
    lp_visits = await db.tracking.count_documents({"lp_code": code, "event": "lp_visit"})
    cta_clicks = await db.tracking.count_documents({"lp_code": code, "event": "cta_click"})
    
    # Stats Form
    form_starts = await db.tracking.count_documents({"form_code": code, "event": "form_start"})
    leads_finished = await db.leads.count_documents({
        "form_code": code, 
        "api_status": {"$in": ["success", "duplicate"]}
    })
    
    # Calcul des taux
    lp_to_cta = round((cta_clicks / lp_visits * 100), 1) if lp_visits > 0 else 0
    cta_to_start = round((form_starts / cta_clicks * 100), 1) if cta_clicks > 0 else 0
    start_to_finish = round((leads_finished / form_starts * 100), 1) if form_starts > 0 else 0
    global_conversion = round((leads_finished / lp_visits * 100), 1) if lp_visits > 0 else 0
    
    return {
        "code": code,
        "events": {
            "lp_visits": lp_visits,
            "cta_clicks": cta_clicks,
            "form_starts": form_starts,
            "leads_finished": leads_finished
        },
        "rates": {
            "lp_to_cta": lp_to_cta,
            "cta_to_start": cta_to_start,
            "start_to_finish": start_to_finish,
            "global_conversion": global_conversion
        }
    }
