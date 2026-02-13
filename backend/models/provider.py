"""
RDZ CRM - Modele Provider (Fournisseur externe de leads)

Un provider est un fournisseur externe rattache a UNE seule entite (ZR7 ou MDL).
Authentification par API key.

Regle:
- Leads provider -> entity verrouillee = provider.entity
- Jamais de cross-entity pour ces leads
"""

from typing import Optional, List
from pydantic import BaseModel
from .lead import EntityType


class ProviderCreate(BaseModel):
    """Creation d'un provider"""
    name: str
    slug: str
    entity: EntityType
    contact_email: Optional[str] = ""
    notes: Optional[str] = ""


class ProviderUpdate(BaseModel):
    """Mise a jour d'un provider"""
    name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class ProviderResponse(BaseModel):
    """Reponse provider pour l'API"""
    id: str
    name: str
    slug: str
    entity: str
    api_key: str
    contact_email: str = ""
    notes: str = ""
    active: bool = True
    total_leads: int = 0
    created_at: str = ""
    updated_at: str = ""
