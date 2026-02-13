"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Client (Acheteur de leads)                                 ║
║                                                                              ║
║  Client = Acheteur de leads (installateur, call center, etc.)                ║
║  DIFFÉRENT d'un Account (tenant/espace interne)                              ║
║                                                                              ║
║  RÈGLE: Un client est TOUJOURS rattaché à une entité (ZR7 ou MDL)            ║
║  Un même acheteur peut exister dans les deux entités (bases séparées)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from .entity import EntityType


class ClientCreate(BaseModel):
    """Création d'un client acheteur de leads"""
    entity: EntityType  # OBLIGATOIRE - ZR7 ou MDL
    name: str  # Nom de la société
    contact_name: Optional[str] = ""  # Nom du contact principal
    email: str  # Email principal pour livraison
    phone: Optional[str] = ""
    
    # Configuration livraison
    delivery_emails: List[str] = []  # Emails additionnels pour livraison CSV
    api_endpoint: Optional[str] = ""  # Endpoint API si livraison par API
    api_key: Optional[str] = ""  # Clé API client
    
    # Paramètres commerciaux
    default_prix_lead: float = 0.0  # Prix par défaut par lead
    remise_percent: float = 0.0  # Remise globale %
    
    notes: Optional[str] = ""


class ClientUpdate(BaseModel):
    """Mise à jour d'un client"""
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    delivery_emails: Optional[List[str]] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    default_prix_lead: Optional[float] = None
    remise_percent: Optional[float] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class ClientResponse(BaseModel):
    """Réponse client pour l'API"""
    id: str
    entity: str
    name: str
    contact_name: str = ""
    email: str
    phone: str = ""
    delivery_emails: List[str] = []
    api_endpoint: str = ""
    default_prix_lead: float = 0.0
    remise_percent: float = 0.0
    notes: str = ""
    active: bool = True
    
    # Stats calculées
    total_leads_received: int = 0
    total_leads_this_week: int = 0
    total_revenue: float = 0.0
    
    created_at: str = ""
    updated_at: str = ""


class ClientListResponse(BaseModel):
    """Liste de clients"""
    clients: List[ClientResponse]
    count: int
    entity: str  # Entité filtrée
