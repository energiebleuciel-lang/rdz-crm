"""
Models Pydantic pour le CRM EnerSolar
Toutes les structures de données en un seul fichier
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== AUTH ====================

class UserPermissions(BaseModel):
    """Permissions par section"""
    dashboard: bool = True
    accounts: bool = True
    lps: bool = True
    forms: bool = True
    leads: bool = True
    departements: bool = True  # Stats départements
    commandes: bool = False  # Réservé admin par défaut
    settings: bool = False   # Réservé admin par défaut
    users: bool = False      # Réservé admin par défaut

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    role: str = "viewer"  # admin, editor, viewer
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


# ==================== JOURNAL D'ACTIVITÉ ====================

class ActivityLog(BaseModel):
    """Log d'activité utilisateur"""
    user_id: str
    user_email: str
    action: str  # create, update, delete, login, logout
    entity_type: str  # account, lp, form, lead, commande, user
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


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
    cgu_text: Optional[str] = ""           # CGU séparées
    privacy_policy_text: Optional[str] = ""
    legal_mentions_text: Optional[str] = ""
    # GTM & Tracking
    gtm_head: Optional[str] = ""
    gtm_body: Optional[str] = ""
    gtm_conversion: Optional[str] = ""
    default_tracking_type: Optional[str] = "redirect"  # redirect, gtm, both
    notes: Optional[str] = ""

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_main_url: Optional[str] = None
    logo_secondary_url: Optional[str] = None
    logo_mini_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    cgu_text: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    legal_mentions_text: Optional[str] = None
    gtm_head: Optional[str] = None
    gtm_body: Optional[str] = None
    gtm_conversion: Optional[str] = None
    default_tracking_type: Optional[str] = None
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
    """Création LP + Form en duo"""
    account_id: str
    name: str
    url: str  # OBLIGATOIRE - URL de la LP
    # Produit et mode
    product_type: str  # PV, PAC, ITE
    form_mode: str = "redirect"  # embedded (même page) ou redirect (page séparée)
    form_url: Optional[str] = ""  # URL du form (si redirect) ou vide (si embedded = même URL)
    # Tracking post-submit
    tracking_type: str = "redirect"  # gtm, redirect, both, none
    redirect_url: Optional[str] = "/merci"  # URL après soumission
    # Source
    source_type: str = "native"  # native, google, facebook
    source_name: Optional[str] = ""  # Taboola, Outbrain, etc.
    # CRM
    crm_api_key: Optional[str] = ""  # Clé API ZR7/MDL pour ce form
    notes: Optional[str] = ""

class LPUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    product_type: Optional[str] = None
    form_mode: Optional[str] = None
    form_url: Optional[str] = None
    tracking_type: Optional[str] = None
    redirect_url: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    crm_api_key: Optional[str] = None
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
    target_crm: Optional[str] = ""  # "zr7" ou "mdl" - vers quel CRM envoyer
    crm_api_key: Optional[str] = ""  # Clé API du CRM pour ce formulaire
    allow_cross_crm: Optional[bool] = True  # Si True, fallback vers autre CRM si pas de commande
    # Tracking
    tracking_type: str = "redirect"  # gtm, redirect, both
    redirect_url: Optional[str] = "/merci"
    notes: Optional[str] = ""

class FormUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    product_type: Optional[str] = None
    lp_id: Optional[str] = None
    target_crm: Optional[str] = None  # "zr7" ou "mdl"
    crm_api_key: Optional[str] = None
    allow_cross_crm: Optional[bool] = None
    tracking_type: Optional[str] = None
    redirect_url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ==================== COMMANDES ====================

class CommandeCreate(BaseModel):
    """Commande de leads pour un CRM"""
    crm_id: str  # ID du CRM (ZR7 ou MDL)
    product_type: str  # PV, PAC, ITE ou * pour tous
    departements: List[str]  # ["75", "92"] ou ["*"] pour tous
    active: bool = True
    prix_unitaire: Optional[float] = 0.0  # Prix par lead
    notes: Optional[str] = ""

class CommandeUpdate(BaseModel):
    product_type: Optional[str] = None
    departements: Optional[List[str]] = None
    active: Optional[bool] = None
    prix_unitaire: Optional[float] = None
    notes: Optional[str] = None


# ==================== LEADS ====================

class LeadSubmit(BaseModel):
    """Lead soumis via API v1"""
    form_id: str
    phone: str
    # Identité
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""  # M., Mme, Mlle
    email: Optional[str] = ""
    # Localisation
    code_postal: Optional[str] = ""
    departement: Optional[str] = ""
    ville: Optional[str] = ""
    adresse: Optional[str] = ""
    # Logement
    type_logement: Optional[str] = ""  # Maison, Appartement
    statut_occupant: Optional[str] = ""  # Propriétaire, Locataire
    surface_habitable: Optional[str] = ""  # m²
    annee_construction: Optional[str] = ""
    type_chauffage: Optional[str] = ""  # Électrique, Gaz, Fioul, Bois
    # Énergie
    facture_electricite: Optional[str] = ""  # Tranche: <100€, 100-150€, etc.
    facture_chauffage: Optional[str] = ""
    # Projet
    type_projet: Optional[str] = ""  # Installation, Remplacement
    delai_projet: Optional[str] = ""  # Immédiat, 3 mois, 6 mois, 1 an
    budget: Optional[str] = ""
    # Tracking
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    source: Optional[str] = ""  # google, facebook, native, etc.
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    # Consentement
    rgpd_consent: Optional[bool] = True
    newsletter: Optional[bool] = False


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
