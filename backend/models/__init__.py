"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Models Package                                                    ║
║                                                                              ║
║  Exports tous les modèles pour import facile                                 ║
║  from models import EntityType, ClientCreate, CommandeCreate, etc.           ║
║                                                                              ║
║  Inclut aussi les modèles legacy pour compatibilité                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ==================== LEGACY MODELS (compatibilité) ====================
# Ces modèles viennent de l'ancien fichier models.py monolithique
import sys
from pathlib import Path

# Import depuis le fichier renommé
sys.path.insert(0, str(Path(__file__).parent.parent))
from models_legacy import (
    # Auth
    UserPermissions,
    UserLogin,
    UserCreate,
    UserUpdate,
    UserResponse,
    # Activity
    ActivityLog,
    # Accounts
    CRMProductConfig,
    AccountCreate,
    AccountUpdate,
    # CRMs
    CRMCreate,
    CRMUpdate,
    # LPs
    LPCreate,
    LPUpdate,
    # Forms
    FormCreate,
    FormUpdate,
    # Leads (legacy)
    LeadSubmit,
    LeadUpdate as LeadUpdateLegacy,
    LeadForceSend,
    # Tracking
    TrackLPVisit,
    TrackCTAClick,
    TrackFormStart,
    # Queue
    QueueItem,
)

# ==================== NEW RDZ MODELS ====================

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

# Lead (VERROUILLÉ)
from .lead import (
    EntityType,
    ProductType,
    LeadStatus,
    LeadCreate,
    LeadDocument,
    LeadPublicSubmit,
    validate_lead_required_fields,
    is_lead_exploitable
)

# Delivery
from .delivery import (
    DeliveryBatch,
    DeliveryStats
)

__all__ = [
    # Legacy Auth
    "UserPermissions",
    "UserLogin",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Legacy Activity
    "ActivityLog",
    # Legacy Accounts
    "CRMProductConfig",
    "AccountCreate",
    "AccountUpdate",
    # Legacy CRMs
    "CRMCreate",
    "CRMUpdate",
    # Legacy LPs
    "LPCreate",
    "LPUpdate",
    # Legacy Forms
    "FormCreate",
    "FormUpdate",
    # Legacy Leads
    "LeadSubmit",
    "LeadUpdateLegacy",
    "LeadForceSend",
    # Legacy Tracking
    "TrackLPVisit",
    "TrackCTAClick",
    "TrackFormStart",
    # Legacy Queue
    "QueueItem",
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
    # Lead (VERROUILLÉ)
    "EntityType",
    "ProductType",
    "LeadStatus",
    "LeadCreate",
    "LeadDocument",
    "LeadPublicSubmit",
    "validate_lead_required_fields",
    "is_lead_exploitable",
    # Delivery
    "DeliveryBatch",
    "DeliveryStats",
]
