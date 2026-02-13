"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Models Package                                                    ║
║                                                                              ║
║  Exports tous les modèles pour import facile                                 ║
║  from models import EntityType, ClientCreate, CommandeCreate, etc.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# Entity (Multi-tenant)
from .entity import (
    EntityType,
    EntityConfig,
    EntityCreate,
    EntityUpdate,
    validate_entity,
    get_entity_or_raise
)

# Client (Acheteur de leads)
from .client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse
)

# Commande (Ordres d'achat)
from .commande import (
    ProductType,
    VALID_PRODUCTS,
    DEPARTEMENTS_METRO,
    CommandeCreate,
    CommandeUpdate,
    CommandeResponse,
    CommandeListResponse
)

# Lead
from .lead import (
    LeadStatus,
    VALID_LEAD_STATUSES,
    LeadSubmitPublic,
    LeadDocument,
    LeadUpdate,
    LeadDeliveryInfo,
    DuplicateCheckResult
)

# Delivery
from .delivery import (
    DeliveryBatch,
    DeliveryStats
)

__all__ = [
    # Entity
    "EntityType",
    "EntityConfig",
    "EntityCreate",
    "EntityUpdate",
    "validate_entity",
    "get_entity_or_raise",
    # Client
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "ClientListResponse",
    # Commande
    "ProductType",
    "VALID_PRODUCTS",
    "DEPARTEMENTS_METRO",
    "CommandeCreate",
    "CommandeUpdate",
    "CommandeResponse",
    "CommandeListResponse",
    # Lead
    "LeadStatus",
    "VALID_LEAD_STATUSES",
    "LeadSubmitPublic",
    "LeadDocument",
    "LeadUpdate",
    "LeadDeliveryInfo",
    "DuplicateCheckResult",
    # Delivery
    "DeliveryBatch",
    "DeliveryStats",
]
