"""
RDZ CRM - Routes Settings (Admin)

Endpoints pour gerer les parametres systeme:
- Cross-entity toggle (ZR7 <-> MDL)
- Source gating (blacklist de sources)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from config import db, now_iso
from routes.auth import get_current_user, require_admin
from services.permissions import require_permission
from services.settings import (
    get_setting,
    upsert_setting,
    get_cross_entity_settings,
    get_source_gating_settings,
    DEFAULT_CROSS_ENTITY,
    DEFAULT_SOURCE_GATING,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ---- Models ----

class PerEntityConfig(BaseModel):
    in_enabled: bool = True
    out_enabled: bool = True


class CrossEntityUpdate(BaseModel):
    cross_entity_enabled: bool = True
    per_entity: Optional[Dict[str, PerEntityConfig]] = None


class SourceGatingUpdate(BaseModel):
    mode: str = "blacklist"
    blocked_sources: List[str] = []


# ---- Endpoints ----

@router.get("")
async def list_settings(user: dict = Depends(require_permission("settings.access"))):
    """Liste tous les settings"""
    docs = await db.settings.find({}, {"_id": 0}).to_list(50)

    # Ajouter defaults si absents
    keys = [d.get("key") for d in docs]
    if "cross_entity" not in keys:
        docs.append({**DEFAULT_CROSS_ENTITY, "key": "cross_entity", "source": "default"})
    if "source_gating" not in keys:
        docs.append({**DEFAULT_SOURCE_GATING, "key": "source_gating", "source": "default"})

    return {"settings": docs, "count": len(docs)}


@router.get("/cross-entity")
async def get_cross_entity(user: dict = Depends(require_permission("settings.access"))):
    """Recupere les settings cross-entity"""
    return await get_cross_entity_settings()


@router.put("/cross-entity")
async def update_cross_entity(
    data: CrossEntityUpdate,
    user: dict = Depends(require_admin)
):
    """Met a jour les settings cross-entity"""
    payload = {
        "cross_entity_enabled": data.cross_entity_enabled,
    }

    if data.per_entity:
        payload["per_entity"] = {
            k: v.dict() for k, v in data.per_entity.items()
        }
    else:
        # Garder les per_entity existants
        current = await get_cross_entity_settings()
        payload["per_entity"] = current.get("per_entity", DEFAULT_CROSS_ENTITY["per_entity"])

    result = await upsert_setting(
        "cross_entity",
        payload,
        updated_by=user.get("email", "admin")
    )
    return {"success": True, "setting": result}


@router.get("/source-gating")
async def get_source_gating(user: dict = Depends(require_permission("settings.access"))):
    """Recupere les settings source gating"""
    return await get_source_gating_settings()


@router.put("/source-gating")
async def update_source_gating(
    data: SourceGatingUpdate,
    user: dict = Depends(require_admin)
):
    """Met a jour le source gating"""
    payload = {
        "mode": data.mode,
        "blocked_sources": [s.strip() for s in data.blocked_sources if s.strip()],
    }

    result = await upsert_setting(
        "source_gating",
        payload,
        updated_by=user.get("email", "admin")
    )
    return {"success": True, "setting": result}


# ---- Forms Config ----

class FormConfigItem(BaseModel):
    form_code: str
    entity: str
    produit: str


class FormsConfigUpdate(BaseModel):
    forms: List[FormConfigItem]


@router.get("/forms-config")
async def get_forms_config(user: dict = Depends(require_permission("settings.access"))):
    """Recupere la config des formulaires (form_code -> entity + produit)"""
    doc = await get_setting("forms_config")
    if not doc:
        return {"forms": {}, "count": 0}
    
    return {"forms": doc.get("forms", {}), "count": len(doc.get("forms", {}))}


@router.put("/forms-config")
async def update_forms_config(
    data: FormsConfigUpdate,
    user: dict = Depends(require_admin)
):
    """Met a jour la config des formulaires"""
    forms_map = {}
    for item in data.forms:
        forms_map[item.form_code] = {
            "entity": item.entity.upper(),
            "produit": item.produit.upper()
        }
    
    result = await upsert_setting(
        "forms_config",
        {"forms": forms_map},
        updated_by=user.get("email", "admin")
    )
    return {"success": True, "setting": result}


@router.post("/forms-config/{form_code}")
async def upsert_single_form_config(
    form_code: str,
    entity: str,
    produit: str,
    user: dict = Depends(require_admin)
):
    """Ajoute ou met a jour un seul formulaire"""
    from services.settings import upsert_form_config
    
    result = await upsert_form_config(
        form_code=form_code,
        entity=entity.upper(),
        produit=produit.upper(),
        updated_by=user.get("email", "admin")
    )
    return {"success": True, "form_code": form_code, "config": result.get("forms", {}).get(form_code)}



# ---- Email Denylist ----

class EmailDenylistUpdate(BaseModel):
    domains: List[str]
    simulation_mode: bool = False
    simulation_email: str = "energiebleuciel@gmail.com"


@router.get("/email-denylist")
async def get_email_denylist(user: dict = Depends(require_permission("settings.access"))):
    """Récupère la config email denylist"""
    from services.settings import get_email_denylist_settings
    return await get_email_denylist_settings()


@router.put("/email-denylist")
async def update_email_denylist(
    data: EmailDenylistUpdate,
    user: dict = Depends(require_admin)
):
    """Met à jour la denylist emails"""
    payload = {
        "domains": [d.strip().lower() for d in data.domains if d.strip()],
        "simulation_mode": data.simulation_mode,
        "simulation_email": data.simulation_email
    }
    
    result = await upsert_setting(
        "email_denylist",
        payload,
        updated_by=user.get("email", "admin")
    )
    return {"success": True, "setting": result}


# ---- Delivery Calendar ----

class DeliveryCalendarUpdate(BaseModel):
    entity: str
    enabled_days: List[int]  # 0=lundi, 6=dimanche
    disabled_dates: List[str] = []  # Format YYYY-MM-DD


@router.get("/delivery-calendar")
async def get_delivery_calendar(user: dict = Depends(require_permission("settings.access"))):
    """Récupère le calendrier de livraison par entity"""
    from services.settings import get_delivery_calendar_settings
    return await get_delivery_calendar_settings()


@router.put("/delivery-calendar")
async def update_delivery_calendar(
    data: DeliveryCalendarUpdate,
    user: dict = Depends(require_admin)
):
    """Met à jour le calendrier de livraison pour une entity"""
    from services.settings import update_delivery_calendar as update_cal
    
    if data.entity.upper() not in ["ZR7", "MDL"]:
        raise HTTPException(status_code=400, detail="Entity invalide (ZR7 ou MDL)")
    
    # Valider les jours (0-6)
    valid_days = [d for d in data.enabled_days if 0 <= d <= 6]
    
    result = await update_cal(
        entity=data.entity.upper(),
        enabled_days=valid_days,
        disabled_dates=data.disabled_dates,
        updated_by=user.get("email", "admin")
    )
    
    return {"success": True, "entity": data.entity.upper(), "setting": result}


@router.get("/delivery-calendar/check/{entity}")
async def check_delivery_day(
    entity: str,
    user: dict = Depends(get_current_user)
):
    """Vérifie si aujourd'hui est un jour de livraison pour l'entity"""
    from services.settings import is_delivery_day_enabled
    
    if entity.upper() not in ["ZR7", "MDL"]:
        raise HTTPException(status_code=400, detail="Entity invalide")
    
    is_enabled, reason = await is_delivery_day_enabled(entity.upper())
    
    return {
        "entity": entity.upper(),
        "is_delivery_day": is_enabled,
        "reason": reason
    }
