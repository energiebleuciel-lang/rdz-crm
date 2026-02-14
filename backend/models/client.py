"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Client (Acheteur de leads)                                 ║
║                                                                              ║
║  RÈGLES DE LIVRAISON:                                                        ║
║  - Un client DOIT avoir au moins 1 canal valide (email OU api)               ║
║  - delivery_enabled = False si aucun canal valide                            ║
║  - Commande OPEN impossible si client non livrable                           ║
║                                                                              ║
║  RÈGLE: Un client est TOUJOURS rattaché à une entité (ZR7 ou MDL)            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from .entity import EntityType
import re


# Denylist par défaut (configurable via settings)
DEFAULT_EMAIL_DENYLIST = [
    "example.com",
    "test.com", 
    "localhost",
    "invalid",
    "fake.com",
    "temp.com",
    "mailinator.com"
]


def is_valid_email_format(email: str) -> bool:
    """Vérifie le format email basique"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_email_in_denylist(email: str, denylist: List[str] = None) -> bool:
    """Vérifie si l'email est dans la denylist"""
    if not email:
        return False
    if denylist is None:
        denylist = DEFAULT_EMAIL_DENYLIST
    domain = email.split('@')[-1].lower()
    return domain in [d.lower() for d in denylist]


class ClientCreate(BaseModel):
    """Création d'un client acheteur de leads"""
    entity: EntityType  # OBLIGATOIRE - ZR7 ou MDL
    name: str  # Nom de la société
    contact_name: Optional[str] = ""
    email: str  # Email principal pour livraison
    phone: Optional[str] = ""
    
    # Configuration livraison
    delivery_emails: List[str] = []  # Emails additionnels
    api_endpoint: Optional[str] = ""  # Endpoint API si livraison par API
    api_key: Optional[str] = ""  # Clé API client
    
    # Nouveau: contrôle livraison
    auto_send_enabled: bool = True  # Si False → ready_to_send au lieu de sent
    
    # Paramètres commerciaux
    default_prix_lead: float = 0.0
    remise_percent: float = 0.0
    
    # Facturation
    vat_rate: float = 20.0  # TVA % (0 ou 20)
    payment_terms_days: int = 30  # Délai de paiement en jours
    
    notes: Optional[str] = ""
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not is_valid_email_format(v):
            raise ValueError(f"Format email invalide: {v}")
        return v


class ClientUpdate(BaseModel):
    """Mise à jour d'un client"""
    name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    delivery_emails: Optional[List[str]] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    auto_send_enabled: Optional[bool] = None
    default_prix_lead: Optional[float] = None
    remise_percent: Optional[float] = None
    vat_rate: Optional[float] = None
    payment_terms_days: Optional[int] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None and not is_valid_email_format(v):
            raise ValueError(f"Format email invalide: {v}")
        return v


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
    
    # Contrôle livraison
    delivery_enabled: bool = True   # Calculé: True si au moins 1 canal valide
    auto_send_enabled: bool = True  # Si False → mode manuel
    
    # Commercial
    default_prix_lead: float = 0.0
    remise_percent: float = 0.0
    vat_rate: float = 20.0
    payment_terms_days: int = 30
    notes: str = ""
    active: bool = True
    
    # Stats calculées
    total_leads_received: int = 0
    total_leads_this_week: int = 0
    total_revenue: float = 0.0
    
    # Validation
    email_valid: bool = True        # Email principal valide et pas en denylist
    has_valid_channel: bool = True  # Au moins 1 canal de livraison valide
    
    created_at: str = ""
    updated_at: str = ""


class ClientListResponse(BaseModel):
    """Liste de clients"""
    clients: List[ClientResponse]
    count: int
    entity: str


def check_client_deliverable(
    email: str,
    delivery_emails: List[str],
    api_endpoint: str,
    denylist: List[str] = None
) -> dict:
    """
    Vérifie si un client est livrable
    
    Returns:
        {
            "deliverable": bool,
            "email_valid": bool,
            "has_valid_email": bool,
            "has_api": bool,
            "invalid_emails": [],
            "reason": str or None
        }
    """
    if denylist is None:
        denylist = DEFAULT_EMAIL_DENYLIST
    
    result = {
        "deliverable": False,
        "email_valid": False,
        "has_valid_email": False,
        "has_api": False,
        "invalid_emails": [],
        "reason": None
    }
    
    # Check email principal
    if email and is_valid_email_format(email):
        if is_email_in_denylist(email, denylist):
            result["invalid_emails"].append(email)
        else:
            result["email_valid"] = True
            result["has_valid_email"] = True
    
    # Check delivery_emails
    for de in (delivery_emails or []):
        if de and is_valid_email_format(de):
            if is_email_in_denylist(de, denylist):
                result["invalid_emails"].append(de)
            else:
                result["has_valid_email"] = True
    
    # Check API
    if api_endpoint and api_endpoint.strip():
        result["has_api"] = True
    
    # Deliverable si au moins 1 canal valide
    result["deliverable"] = result["has_valid_email"] or result["has_api"]
    
    if not result["deliverable"]:
        if result["invalid_emails"]:
            result["reason"] = f"Tous les emails sont en denylist: {result['invalid_emails']}"
        else:
            result["reason"] = "Aucun canal de livraison valide (email ou API)"
    
    return result
