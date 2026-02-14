"""
RDZ CRM - Service Settings

Gestion des parametres systeme dynamiques.
Collection: settings (chaque doc identifie par key)

Settings disponibles:
- cross_entity: toggle cross-entity ZR7<->MDL
- source_gating: whitelist/blacklist de sources
- forms_config: mapping form_code -> entity + produit
- email_denylist: domaines email interdits
- delivery_calendar: jours de livraison par entity
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
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


# ---- Forms Config helpers ----

async def get_form_config(form_code: str) -> Optional[Dict]:
    """
    Recupere la config d'un formulaire (entity + produit).
    
    Cherche dans:
    1. settings.forms_config[form_code]
    2. collection forms (si existante)
    
    Returns: {"entity": "ZR7", "produit": "PV"} ou None
    """
    # 1. Settings forms_config
    settings = await get_setting("forms_config")
    if settings:
        forms_map = settings.get("forms", {})
        if form_code in forms_map:
            return forms_map[form_code]
    
    # 2. Collection forms (legacy)
    form = await db.forms.find_one({"code": form_code}, {"_id": 0})
    if form:
        return {
            "entity": form.get("entity", ""),
            "produit": form.get("produit", form.get("product_type", ""))
        }
    
    return None


async def upsert_form_config(form_code: str, entity: str, produit: str, updated_by: str = "system") -> Dict:
    """
    Ajoute ou met a jour la config d'un formulaire.
    """
    settings = await get_setting("forms_config")
    
    if not settings:
        settings = {"forms": {}}
    
    if "forms" not in settings:
        settings["forms"] = {}
    
    settings["forms"][form_code] = {
        "entity": entity.upper(),
        "produit": produit.upper()
    }
    
    return await upsert_setting("forms_config", settings, updated_by)


# ---- Email Denylist helpers ----

DEFAULT_EMAIL_DENYLIST = {
    "domains": [
        "example.com",
        "test.com",
        "localhost",
        "invalid",
        "fake.com",
        "temp.com",
        "mailinator.com"
    ],
    "simulation_mode": False,  # Si True, override tous les emails
    "simulation_email": "energiebleuciel@gmail.com"
}


async def get_email_denylist_settings() -> Dict:
    """Retourne les settings email denylist (avec defaults)"""
    doc = await get_setting("email_denylist")
    if not doc:
        return DEFAULT_EMAIL_DENYLIST
    # Merge avec defaults
    return {**DEFAULT_EMAIL_DENYLIST, **doc}


async def is_email_domain_allowed(email: str) -> bool:
    """
    Verifie si le domaine email n'est pas dans la denylist.
    """
    if not email or "@" not in email:
        return False
    
    settings = await get_email_denylist_settings()
    denylist = settings.get("domains", [])
    
    domain = email.split("@")[-1].lower()
    return domain not in [d.lower() for d in denylist]


async def get_simulation_email_override() -> Optional[str]:
    """
    Retourne l'email override si mode simulation actif.
    """
    settings = await get_email_denylist_settings()
    if settings.get("simulation_mode", False):
        return settings.get("simulation_email", "energiebleuciel@gmail.com")
    return None


# ---- Delivery Calendar helpers ----

# Jours: 0=lundi, 1=mardi, ..., 6=dimanche
DEFAULT_DELIVERY_CALENDAR = {
    "ZR7": {
        "enabled_days": [0, 1, 2, 3, 4],  # Lun-Ven
        "disabled_dates": [],  # Dates specifiques desactivees (format YYYY-MM-DD)
    },
    "MDL": {
        "enabled_days": [0, 1, 2, 3, 4],  # Lun-Ven
        "disabled_dates": [],
    }
}

DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


async def get_delivery_calendar_settings() -> Dict:
    """Retourne les settings calendrier livraison (avec defaults)"""
    doc = await get_setting("delivery_calendar")
    if not doc:
        return DEFAULT_DELIVERY_CALENDAR
    # Merge avec defaults pour chaque entity
    result = {}
    for entity in ["ZR7", "MDL"]:
        default = DEFAULT_DELIVERY_CALENDAR.get(entity, {"enabled_days": [0,1,2,3,4], "disabled_dates": []})
        entity_cfg = doc.get(entity, {})
        result[entity] = {**default, **entity_cfg}
    return result


async def is_delivery_day_enabled(entity: str, check_date: datetime = None) -> tuple:
    """
    Verifie si la livraison est active pour une entity a une date donnee.
    
    Args:
        entity: ZR7 ou MDL
        check_date: Date a verifier (default: maintenant)
    
    Returns:
        (is_enabled: bool, reason: str or None)
    """
    if check_date is None:
        check_date = datetime.now(timezone.utc)
    
    settings = await get_delivery_calendar_settings()
    entity_cfg = settings.get(entity, DEFAULT_DELIVERY_CALENDAR.get(entity, {}))
    
    # 1. Verifier le jour de la semaine
    day_of_week = check_date.weekday()  # 0=lundi
    enabled_days = entity_cfg.get("enabled_days", [0, 1, 2, 3, 4])
    
    if day_of_week not in enabled_days:
        day_name = DAY_NAMES[day_of_week]
        return False, f"delivery_day_disabled:{day_name}"
    
    # 2. Verifier les dates specifiques desactivees
    date_str = check_date.strftime("%Y-%m-%d")
    disabled_dates = entity_cfg.get("disabled_dates", [])
    
    if date_str in disabled_dates:
        return False, f"delivery_date_disabled:{date_str}"
    
    return True, None


async def update_delivery_calendar(entity: str, enabled_days: List[int] = None, 
                                    disabled_dates: List[str] = None, 
                                    updated_by: str = "system") -> Dict:
    """
    Met a jour le calendrier de livraison pour une entity.
    """
    settings = await get_delivery_calendar_settings()
    
    if entity not in settings:
        settings[entity] = {"enabled_days": [0,1,2,3,4], "disabled_dates": []}
    
    if enabled_days is not None:
        # Valider les jours (0-6)
        settings[entity]["enabled_days"] = [d for d in enabled_days if 0 <= d <= 6]
    
    if disabled_dates is not None:
        settings[entity]["disabled_dates"] = disabled_dates
    
    return await upsert_setting("delivery_calendar", settings, updated_by)
