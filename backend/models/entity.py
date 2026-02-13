"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Entité (Multi-tenant strict)                                      ║
║                                                                              ║
║  RÈGLE FONDAMENTALE:                                                         ║
║  - Deux entités isolées: ZR7 et MDL                                          ║
║  - AUCUN mélange de données possible                                         ║
║  - Toute requête DOIT avoir un filtre entity                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """
    Entités possibles - multi-tenant strict
    """
    ZR7 = "ZR7"
    MDL = "MDL"


class EntityConfig(BaseModel):
    """
    Configuration d'une entité (ZR7 ou MDL)
    Stockée en DB pour paramétrage dynamique
    """
    id: str
    code: EntityType
    name: str  # "ZR7 Digital" ou "Maison du Lead"
    
    # SMTP Configuration
    smtp_host: str = "ssl0.ovh.net"
    smtp_port: int = 465
    smtp_email: str = ""
    smtp_password: str = ""  # Stocké en env var, référencé ici
    
    # API CRM
    api_url: str = ""
    api_key_env: str = ""  # Nom de la variable d'env contenant la clé
    
    # Stats
    total_leads_received: int = 0
    total_leads_delivered: int = 0
    
    active: bool = True
    created_at: str = ""
    updated_at: str = ""


class EntityCreate(BaseModel):
    """Création d'entité"""
    code: EntityType
    name: str
    smtp_email: str = ""
    api_url: str = ""


class EntityUpdate(BaseModel):
    """Mise à jour d'entité"""
    name: Optional[str] = None
    smtp_email: Optional[str] = None
    smtp_password: Optional[str] = None
    api_url: Optional[str] = None
    active: Optional[bool] = None


# ==================== VALIDATION HELPER ====================

def validate_entity(entity: str) -> bool:
    """
    Valide qu'une entité est bien ZR7 ou MDL
    À utiliser PARTOUT avant toute opération
    """
    return entity in [e.value for e in EntityType]


def get_entity_or_raise(entity: str) -> EntityType:
    """
    Retourne l'EntityType ou raise une erreur
    """
    if not validate_entity(entity):
        raise ValueError(f"Entity invalide: {entity}. Doit être ZR7 ou MDL")
    return EntityType(entity)
