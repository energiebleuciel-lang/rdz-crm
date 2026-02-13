"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Lead (VERROUILLÉ)                                          ║
║                                                                              ║
║  NAMING UNIQUE - AUCUN ALIAS - AUCUNE AMBIGUÏTÉ                              ║
║                                                                              ║
║  RÈGLE MÉTIER:                                                               ║
║  Un lead est exploitable/vendable si: phone + departement + nom              ║
║                                                                              ║
║  CHAMPS OBLIGATOIRES (ROOT):                                                 ║
║  - phone, departement, nom, register_date, entity, produit                   ║
║                                                                              ║
║  CHAMPS OPTIONNELS (ROOT):                                                   ║
║  - prenom, email, session_id, lp_code, form_code, liaison_code, source, utm_*║
║                                                                              ║
║  CHAMPS SECONDAIRES: custom_fields.* uniquement                              ║
║                                                                              ║
║  ⚠️ departement EST EN ROOT - PAS dans custom_fields                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


# ==================== ENUMS STRICTS ====================

class EntityType(str, Enum):
    """Entités - Multi-tenant strict"""
    ZR7 = "ZR7"
    MDL = "MDL"


class ProductType(str, Enum):
    """Types de produits"""
    PV = "PV"    # Panneaux solaires
    PAC = "PAC"  # Pompe à chaleur
    ITE = "ITE"  # Isolation thermique extérieure


class LeadStatus(str, Enum):
    """Statuts de lead"""
    NEW = "new"
    NON_LIVRE = "non_livre"
    LIVRE = "livre"
    DOUBLON = "doublon"
    REJET_CLIENT = "rejet_client"
    LB = "lb"


# ==================== MODÈLE LEAD PRINCIPAL ====================

class LeadCreate(BaseModel):
    """
    Création d'un lead via API publique
    
    CHAMPS OBLIGATOIRES:
    - phone: numéro de téléphone
    - departement: code département (2 chiffres)
    - nom: nom de famille
    - entity: ZR7 ou MDL
    - produit: PV, PAC ou ITE
    """
    # === OBLIGATOIRES ===
    phone: str = Field(..., min_length=1, description="Téléphone (obligatoire)")
    departement: str = Field(..., min_length=2, max_length=2, description="Département 2 chiffres (obligatoire)")
    nom: str = Field(..., min_length=1, description="Nom (obligatoire)")
    entity: EntityType = Field(..., description="Entité ZR7 ou MDL (obligatoire)")
    produit: ProductType = Field(..., description="Produit PV/PAC/ITE (obligatoire)")
    
    # === OPTIONNELS (ROOT) ===
    prenom: Optional[str] = ""
    email: Optional[str] = ""
    session_id: Optional[str] = ""
    lp_code: Optional[str] = ""
    form_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    source: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    utm_term: Optional[str] = ""
    utm_content: Optional[str] = ""
    
    # === CHAMPS SECONDAIRES ===
    custom_fields: Optional[Dict[str, Any]] = {}
    
    @validator('departement')
    def validate_departement(cls, v):
        """Département = 2 chiffres"""
        if not v.isdigit() or len(v) != 2:
            raise ValueError("departement doit être 2 chiffres (ex: 75, 92)")
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Phone ne doit pas être vide"""
        if not v or not v.strip():
            raise ValueError("phone est obligatoire")
        return v.strip()
    
    @validator('nom')
    def validate_nom(cls, v):
        """Nom ne doit pas être vide"""
        if not v or not v.strip():
            raise ValueError("nom est obligatoire")
        return v.strip()


class LeadDocument(BaseModel):
    """
    Structure complète d'un lead en base MongoDB
    
    NAMING STRICT - AUCUN ALIAS
    """
    # === ID ===
    id: str
    
    # === OBLIGATOIRES (ROOT) ===
    phone: str
    departement: str  # ⚠️ TOUJOURS EN ROOT - jamais dans custom_fields
    nom: str
    register_date: int  # Unix timestamp ms
    entity: str  # ZR7 ou MDL
    produit: str  # PV, PAC, ITE
    
    # === OPTIONNELS (ROOT) ===
    prenom: str = ""
    email: str = ""
    session_id: str = ""
    lp_code: str = ""
    form_code: str = ""
    liaison_code: str = ""
    source: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_term: str = ""
    utm_content: str = ""
    
    # === STATUT ===
    status: str = "new"  # new, non_livre, livre, doublon, rejet_client, lb
    
    # === DOUBLON INFO ===
    is_duplicate: bool = False
    duplicate_of_client_id: Optional[str] = None
    duplicate_of_client_name: Optional[str] = None
    duplicate_delivery_date: Optional[str] = None
    
    # === LIVRAISON INFO ===
    delivered_to_client_id: Optional[str] = None
    delivered_to_client_name: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_method: Optional[str] = None
    delivery_batch_id: Optional[str] = None
    delivery_commande_id: Optional[str] = None
    
    # === LB INFO ===
    # LB = Lead Backlog = Pool de leads revendables
    # Condition 1: non_livre > 8 jours → LB
    # Condition 2: livre > 30 jours → LB (recyclable)
    is_lb: bool = False
    lb_since: Optional[str] = None
    lb_reason: Optional[str] = None  # "non_livre_8_days" ou "livre_30_days_expired"
    lb_original_produit: Optional[str] = None
    
    # === REJET CLIENT ===
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # === CHAMPS SECONDAIRES ===
    custom_fields: Dict[str, Any] = {}
    
    # === META ===
    ip: str = ""
    created_at: str = ""
    updated_at: str = ""


class LeadPublicSubmit(BaseModel):
    """
    Lead soumis via formulaire public (LP)
    Validation minimale côté API publique
    """
    # === OBLIGATOIRES ===
    phone: str
    departement: str
    nom: str
    
    # === OPTIONNELS ===
    prenom: Optional[str] = ""
    email: Optional[str] = ""
    session_id: Optional[str] = ""
    form_code: Optional[str] = ""
    
    # === TRACKING ===
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    source: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    
    # === SECONDAIRES ===
    custom_fields: Optional[Dict[str, Any]] = {}
    
    @validator('phone')
    def validate_phone(cls, v):
        if not v or not v.strip():
            raise ValueError("phone est obligatoire")
        return v.strip()
    
    @validator('departement')
    def validate_departement(cls, v):
        if not v or len(v) < 2:
            raise ValueError("departement est obligatoire (2 chiffres)")
        return v[:2]  # Prendre les 2 premiers caractères
    
    @validator('nom')
    def validate_nom(cls, v):
        if not v or not v.strip():
            raise ValueError("nom est obligatoire")
        return v.strip()


# ==================== HELPERS ====================

def validate_lead_required_fields(lead: dict) -> tuple:
    """
    Valide qu'un lead a les champs obligatoires
    
    Returns:
        (is_valid: bool, missing_fields: list)
    """
    required = ["phone", "departement", "nom"]
    missing = [f for f in required if not lead.get(f)]
    return (len(missing) == 0, missing)


def is_lead_exploitable(lead: dict) -> bool:
    """
    Un lead est exploitable/vendable si:
    phone + departement + nom sont présents
    """
    return bool(
        lead.get("phone") and 
        lead.get("departement") and 
        lead.get("nom")
    )
