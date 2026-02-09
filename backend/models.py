"""
Models Pydantic pour le CRM EnerSolar
Toutes les structures de données en un seul fichier
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== AUTH ====================

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    role: str = "viewer"  # admin, editor, viewer

class UserResponse(BaseModel):
    id: str
    email: str
    nom: str
    role: str


# ==================== COMPTES ====================

class AccountCreate(BaseModel):
    name: str
    crm_id: str  # ZR7 ou MDL
    domain: Optional[str] = ""
    # Logos
    logo_main_url: Optional[str] = ""      # Logo gauche
    logo_secondary_url: Optional[str] = "" # Logo droite
    logo_mini_url: Optional[str] = ""      # Favicon
    # Couleurs
    primary_color: Optional[str] = "#3B82F6"
    secondary_color: Optional[str] = "#1E40AF"
    # Textes légaux
    privacy_policy_text: Optional[str] = ""
    legal_mentions_text: Optional[str] = ""
    # GTM
    gtm_head: Optional[str] = ""
    gtm_body: Optional[str] = ""
    gtm_conversion: Optional[str] = ""
    notes: Optional[str] = ""

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_main_url: Optional[str] = None
    logo_secondary_url: Optional[str] = None
    logo_mini_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    legal_mentions_text: Optional[str] = None
    gtm_head: Optional[str] = None
    gtm_body: Optional[str] = None
    gtm_conversion: Optional[str] = None
    notes: Optional[str] = None


# ==================== CRMs EXTERNES ====================

class CRMCreate(BaseModel):
    name: str           # "ZR7 Digital", "Maison du Lead"
    slug: str           # "zr7", "mdl"
    api_url: str        # URL de l'API
    description: Optional[str] = ""
    # Commandes par produit/département
    # {"PAC": ["75", "92"], "PV": ["13", "31"]}
    commandes: Optional[Dict[str, List[str]]] = {}

class CRMUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    description: Optional[str] = None
    commandes: Optional[Dict[str, List[str]]] = None


# ==================== LANDING PAGES ====================

class LPCreate(BaseModel):
    account_id: str
    name: str
    url: str  # OBLIGATOIRE - URL de la LP
    source_type: str = "native"  # native, google, facebook
    source_name: Optional[str] = ""  # Taboola, Outbrain, etc.
    notes: Optional[str] = ""

class LPUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ==================== FORMULAIRES ====================

class FormCreate(BaseModel):
    account_id: str
    name: str
    url: str  # OBLIGATOIRE - URL du formulaire
    product_type: str  # PV, PAC, ITE
    lp_id: Optional[str] = ""  # LP liée (optionnel)
    # Config CRM destination
    crm_api_key: Optional[str] = ""  # Clé API ZR7/MDL
    # Tracking
    tracking_type: str = "redirect"  # gtm, redirect, both
    redirect_url: Optional[str] = "/merci"
    notes: Optional[str] = ""

class FormUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    product_type: Optional[str] = None
    lp_id: Optional[str] = None
    crm_api_key: Optional[str] = None
    tracking_type: Optional[str] = None
    redirect_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ==================== LEADS ====================

class LeadSubmit(BaseModel):
    """Lead soumis via API v1"""
    form_id: str
    phone: str
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""
    email: Optional[str] = ""
    code_postal: Optional[str] = ""
    departement: Optional[str] = ""
    type_logement: Optional[str] = ""
    statut_occupant: Optional[str] = ""
    facture_electricite: Optional[str] = ""
    # Tracking
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""


# ==================== TRACKING ====================

class TrackLPVisit(BaseModel):
    """Visite d'une LP"""
    lp_code: str
    referrer: Optional[str] = ""
    user_agent: Optional[str] = ""

class TrackCTAClick(BaseModel):
    """Clic sur CTA de la LP"""
    lp_code: str
    form_code: Optional[str] = ""

class TrackFormStart(BaseModel):
    """Début de formulaire"""
    form_code: str
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""


# ==================== QUEUE ====================

class QueueItem(BaseModel):
    lead_id: str
    api_url: str
    api_key: str
    retry_count: int = 0
    next_retry_at: str
    status: str = "pending"  # pending, processing, success, failed, exhausted
    last_error: Optional[str] = None
