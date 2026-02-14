"""
RDZ CRM - Permission System
Granular permission keys + role presets + FastAPI dependencies.
Permissions are the source of truth. Roles are presets only.
"""

import logging
from typing import Optional, Dict, List
from fastapi import Depends, HTTPException, Request
from config import db, now_iso

logger = logging.getLogger("permissions")

# ════════════════════════════════════════════════════════════════════════
# ALL PERMISSION KEYS
# ════════════════════════════════════════════════════════════════════════

ALL_PERMISSION_KEYS = [
    "dashboard.view",

    "leads.view",
    "leads.edit_status",
    "leads.add_note",
    "leads.delete",

    "clients.view",
    "clients.create",
    "clients.edit",
    "clients.delete",

    "commandes.view",
    "commandes.create",
    "commandes.edit_quota",
    "commandes.edit_lb_target",
    "commandes.activate_pause",
    "commandes.delete",

    "deliveries.view",
    "deliveries.resend",

    "billing.view",
    "billing.manage",

    "departements.view",

    "activity.view",

    "settings.access",
    "providers.access",

    "users.manage",

    "monitoring.lb.view",
]

# ════════════════════════════════════════════════════════════════════════
# ROLE PRESETS (defaults when creating a user with a role)
# ════════════════════════════════════════════════════════════════════════

ROLE_PRESETS: Dict[str, Dict[str, bool]] = {
    "super_admin": {k: True for k in ALL_PERMISSION_KEYS},

    "admin": {
        "dashboard.view": True,
        "leads.view": True, "leads.edit_status": True, "leads.add_note": True, "leads.delete": True,
        "clients.view": True, "clients.create": True, "clients.edit": True, "clients.delete": True,
        "commandes.view": True, "commandes.create": True, "commandes.edit_quota": True,
        "commandes.edit_lb_target": True, "commandes.activate_pause": True, "commandes.delete": True,
        "deliveries.view": True, "deliveries.resend": True,
        "billing.view": True, "billing.manage": True,
        "departements.view": True,
        "activity.view": True,
        "settings.access": True, "providers.access": True,
        "users.manage": False,
        "monitoring.lb.view": False,
    },

    "ops": {
        "dashboard.view": True,
        "leads.view": True, "leads.edit_status": True, "leads.add_note": True, "leads.delete": False,
        "clients.view": True, "clients.create": False, "clients.edit": False, "clients.delete": False,
        "commandes.view": True, "commandes.create": False, "commandes.edit_quota": True,
        "commandes.edit_lb_target": True, "commandes.activate_pause": True, "commandes.delete": False,
        "deliveries.view": True, "deliveries.resend": True,
        "billing.view": False, "billing.manage": False,
        "departements.view": True,
        "activity.view": False,
        "settings.access": False, "providers.access": False,
        "users.manage": False,
        "monitoring.lb.view": False,
    },

    "viewer": {
        "dashboard.view": True,
        "leads.view": True, "leads.edit_status": False, "leads.add_note": False, "leads.delete": False,
        "clients.view": True, "clients.create": False, "clients.edit": False, "clients.delete": False,
        "commandes.view": True, "commandes.create": False, "commandes.edit_quota": False,
        "commandes.edit_lb_target": False, "commandes.activate_pause": False, "commandes.delete": False,
        "deliveries.view": True, "deliveries.resend": False,
        "billing.view": False, "billing.manage": False,
        "departements.view": True,
        "activity.view": False,
        "settings.access": False, "providers.access": False,
        "users.manage": False,
        "monitoring.lb.view": False,
    },
}

VALID_ROLES = list(ROLE_PRESETS.keys())


def get_preset_permissions(role: str) -> Dict[str, bool]:
    """Returns the default permissions for a role."""
    return dict(ROLE_PRESETS.get(role, ROLE_PRESETS["viewer"]))


# ════════════════════════════════════════════════════════════════════════
# PERMISSION CHECK HELPERS
# ════════════════════════════════════════════════════════════════════════

def user_has_permission(user: dict, key: str) -> bool:
    """Check if user has a specific permission."""
    if user.get("role") == "super_admin":
        return True
    perms = user.get("permissions", {})
    return perms.get(key, False) is True


def get_entity_scope_from_request(user: dict, request: Request) -> Optional[str]:
    """
    Resolve entity scope for the current request.
    - super_admin: reads X-Entity-Scope header (ZR7/MDL/BOTH), defaults to BOTH
    - others: always forced to user.entity
    """
    if user.get("role") == "super_admin":
        scope = request.headers.get("x-entity-scope", "BOTH").upper()
        if scope in ("ZR7", "MDL", "BOTH"):
            return scope
        return "BOTH"
    return user.get("entity", "ZR7")


def build_entity_filter(scope: str, field: str = "entity") -> dict:
    """
    Build a MongoDB filter for entity isolation.
    scope=BOTH -> no filter on entity
    scope=ZR7/MDL -> strict filter
    """
    if scope == "BOTH":
        return {}
    return {field: scope}


def enforce_write_entity(user: dict, request: Request, provided_entity: Optional[str] = None) -> str:
    """
    Determine the entity for a write operation.
    - Normal users: always user.entity (ignore client-provided)
    - super_admin with scope ZR7/MDL: use scope
    - super_admin with scope BOTH: require explicit entity or 403
    """
    if user.get("role") != "super_admin":
        return user.get("entity", "ZR7")

    scope = get_entity_scope_from_request(user, request)

    if scope in ("ZR7", "MDL"):
        return scope

    # scope == BOTH: write requires explicit entity
    if provided_entity and provided_entity.upper() in ("ZR7", "MDL"):
        return provided_entity.upper()

    raise HTTPException(
        status_code=400,
        detail="Entity explicite requise pour les écritures en scope BOTH. "
               "Sélectionnez ZR7 ou MDL."
    )


# ════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════

def require_permission(permission_key: str):
    """
    FastAPI dependency factory.
    Usage: @router.get("/endpoint", dependencies=[Depends(require_permission("leads.view"))])
    """
    from routes.auth import get_current_user

    async def _check(request: Request, user: dict = Depends(get_current_user)):
        if not user_has_permission(user, permission_key):
            logger.warning(
                f"[PERMISSION_DENIED] user={user.get('email')} "
                f"key={permission_key} role={user.get('role')}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Permission requise: {permission_key}"
            )
        return user

    return _check


def require_super_admin():
    """FastAPI dependency: only super_admin allowed."""
    from routes.auth import get_current_user

    async def _check(user: dict = Depends(get_current_user)):
        if user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="Accès super_admin requis")
        return user

    return _check
