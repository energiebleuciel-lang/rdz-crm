"""
RDZ CRM - Models Package
Exports tous les modeles pour import facile
"""

# Auth & Utilisateurs
from .auth import (
    UserPermissions,
    UserLogin,
    UserCreate,
    UserUpdate,
    UserResponse,
    ActivityLog,
)

# Entity
from .entity import (
    EntityConfig,
    EntityCreate,
    EntityUpdate,
    validate_entity,
    get_entity_or_raise,
)

# Client (Acheteur de leads)
from .client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
)

# Commande
from .commande import (
    VALID_PRODUCTS,
    DEPARTEMENTS_METRO,
    CommandeCreate,
    CommandeUpdate,
    CommandeResponse,
    CommandeListResponse,
)

# Lead (SOURCE UNIQUE)
from .lead import (
    EntityType,
    ProductType,
    LeadStatus,
    LeadCreate,
    LeadDocument,
    LeadPublicSubmit,
    validate_lead_required_fields,
    is_lead_exploitable,
)

# Delivery
from .delivery import (
    DeliveryBatch,
    DeliveryStats,
)

__all__ = [
    # Auth
    "UserPermissions", "UserLogin", "UserCreate", "UserUpdate", "UserResponse",
    "ActivityLog",
    # Entity
    "EntityConfig", "EntityCreate", "EntityUpdate", "validate_entity", "get_entity_or_raise",
    # Client
    "ClientCreate", "ClientUpdate", "ClientResponse", "ClientListResponse",
    # Commande
    "VALID_PRODUCTS", "DEPARTEMENTS_METRO",
    "CommandeCreate", "CommandeUpdate", "CommandeResponse", "CommandeListResponse",
    # Lead
    "EntityType", "ProductType", "LeadStatus",
    "LeadCreate", "LeadDocument", "LeadPublicSubmit",
    "validate_lead_required_fields", "is_lead_exploitable",
    # Delivery
    "DeliveryBatch", "DeliveryStats",
]
