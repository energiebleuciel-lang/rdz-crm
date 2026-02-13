"""
RDZ CRM - Service Settings

Gestion des parametres systeme dynamiques.
Collection: settings (chaque doc identifie par key)

Settings disponibles:
- cross_entity: toggle cross-entity ZR7<->MDL
- source_gating: whitelist/blacklist de sources
"""

import logging
from typing import Optional, Dict, Any
from config import db, now_iso

logger = logging.getLogger("settings")


async def get_setting(key: str) -> Optional[Dict]:
    """Recupere un setting par sa cle"""
    doc = await db.settings.find_one({"key": key}, {"_id": 0})
    return doc


async def upsert_setting(key: str, data: Dict[str, Any], updated_by: str = "system") -> Dict:
    """Cree ou met a jour un setting"""
    data["key"] = key
    data["updated_at"] = now_iso()
    data["updated_by"] = updated_by

    existing = await db.settings.find_one({"key": key})
    if existing:
        await db.settings.update_one({"key": key}, {"$set": data})
    else:
        data["created_at"] = now_iso()
        await db.settings.insert_one(data)

    result = await db.settings.find_one({"key": key}, {"_id": 0})
    return result


# ---- Cross-entity helpers ----

DEFAULT_CROSS_ENTITY = {
    "cross_entity_enabled": True,
    "per_entity": {
        "ZR7": {"in_enabled": True, "out_enabled": True},
        "MDL": {"in_enabled": True, "out_enabled": True},
    }
}


async def get_cross_entity_settings() -> Dict:
    """Retourne les settings cross-entity (avec defaults)"""
    doc = await get_setting("cross_entity")
    if not doc:
        return DEFAULT_CROSS_ENTITY
    return doc


async def is_cross_entity_allowed(from_entity: str, to_entity: str) -> bool:
    """
    Verifie si le transfert cross-entity est autorise.

    Conditions:
    1. cross_entity_enabled = true (global)
    2. from_entity.out_enabled = true
    3. to_entity.in_enabled = true
    """
    settings = await get_cross_entity_settings()

    if not settings.get("cross_entity_enabled", True):
        return False

    per_entity = settings.get("per_entity", {})

    from_cfg = per_entity.get(from_entity, {"out_enabled": True})
    if not from_cfg.get("out_enabled", True):
        return False

    to_cfg = per_entity.get(to_entity, {"in_enabled": True})
    if not to_cfg.get("in_enabled", True):
        return False

    return True


# ---- Source gating helpers ----

DEFAULT_SOURCE_GATING = {
    "mode": "blacklist",
    "blocked_sources": [],
}


async def get_source_gating_settings() -> Dict:
    """Retourne les settings source gating (avec defaults)"""
    doc = await get_setting("source_gating")
    if not doc:
        return DEFAULT_SOURCE_GATING
    return doc


async def is_source_allowed(source: str) -> bool:
    """
    Verifie si une source est autorisee.
    Mode blacklist: tout est autorise sauf les sources dans blocked_sources.
    """
    if not source:
        return True

    settings = await get_source_gating_settings()
    blocked = settings.get("blocked_sources", [])

    if not blocked:
        return True

    return source.lower() not in [s.lower() for s in blocked]
