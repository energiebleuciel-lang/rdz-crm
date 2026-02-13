"""
RDZ CRM - Modeles Auth & Utilisateurs
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class UserPermissions(BaseModel):
    """Permissions par section"""
    dashboard: bool = True
    leads: bool = True
    clients: bool = False
    commandes: bool = False
    settings: bool = False
    users: bool = False


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    role: str = "viewer"
    permissions: Optional[UserPermissions] = None


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[UserPermissions] = None
    active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: str
    nom: str
    role: str
    permissions: Optional[dict] = None


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
