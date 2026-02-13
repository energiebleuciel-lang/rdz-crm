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
async def list_settings(user: dict = Depends(get_current_user)):
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
async def get_cross_entity(user: dict = Depends(get_current_user)):
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
async def get_source_gating(user: dict = Depends(get_current_user)):
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
