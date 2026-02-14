"""
RDZ CRM - Modeles Auth & Utilisateurs
Role + Permission hybrid model.
Roles are presets. Permissions are the real authority.
"""

from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List


VALID_ROLES = ["super_admin", "admin", "ops", "viewer"]
VALID_ENTITIES = ["ZR7", "MDL"]


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    entity: str
    role: str = "viewer"
    permissions: Optional[Dict[str, bool]] = None

    @validator("entity")
    def validate_entity(cls, v):
        if v.upper() not in VALID_ENTITIES:
            raise ValueError(f"Entity invalide: {v}. Doit être ZR7 ou MDL")
        return v.upper()

    @validator("role")
    def validate_role(cls, v):
        if v not in VALID_ROLES:
            raise ValueError(f"Role invalide: {v}. Valides: {VALID_ROLES}")
        return v


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    entity: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None

    @validator("entity")
    def validate_entity(cls, v):
        if v is not None and v.upper() not in VALID_ENTITIES:
            raise ValueError(f"Entity invalide: {v}")
        return v.upper() if v else v

    @validator("role")
    def validate_role(cls, v):
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Role invalide: {v}")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    nom: str
    entity: str = ""
    role: str = "viewer"
    permissions: Optional[Dict[str, bool]] = None
    is_active: bool = True


class UserPermissions(BaseModel):
    """Legacy compat — kept for import, unused in new system"""
    dashboard: bool = True
    leads: bool = True
    clients: bool = False
    commandes: bool = False
    settings: bool = False
    users: bool = False


class ActivityLog(BaseModel):
    """Log d'activite utilisateur"""
    user_id: str
    user_email: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
