"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Lead (Refonte spec RDZ)                                    ║
║                                                                              ║
║  RÈGLES FONDAMENTALES:                                                       ║
║  1. Un lead est TOUJOURS inséré si téléphone présent                         ║
║  2. JAMAIS de perte de lead (même doublon, même rejeté)                      ║
║  3. Statuts obligatoires: new, non_livre, livre, doublon, rejet_client, lb   ║
║  4. Doublon 30 jours: même phone + même produit + même client = ne pas livrer║
║  5. LB après 8 jours sans livraison                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
from .entity import EntityType
from .commande import ProductType


class LeadStatus(str, Enum):
    """
    Statuts de lead - OBLIGATOIRES selon spec
    """
    NEW = "new"               # Nouveau lead, pas encore traité
    NON_LIVRE = "non_livre"   # Non livré (pas de commande, etc.)
    LIVRE = "livre"           # Livré avec succès à un client
    DOUBLON = "doublon"       # Doublon 30 jours (non envoyé mais stocké)
    REJET_CLIENT = "rejet_client"  # Rejeté par le client après livraison
    LB = "lb"                 # Lead Backlog (>8 jours sans livraison)


# Pour validation
VALID_LEAD_STATUSES = [s.value for s in LeadStatus]


class LeadSubmitPublic(BaseModel):
    """
    Lead soumis via l'API publique (formulaire LP)
    Minimum requis: phone (le reste est optionnel mais recommandé)
    """
    # Identification formulaire/session
    session_id: str
    form_code: str
    
    # OBLIGATOIRE
    phone: str
    
    # Identité
    nom: Optional[str] = ""
    prenom: Optional[str] = ""
    civilite: Optional[str] = ""  # M., Mme
    email: Optional[str] = ""
    
    # Localisation
    departement: Optional[str] = ""
    ville: Optional[str] = ""
    adresse: Optional[str] = ""
    
    # Logement
    type_logement: Optional[str] = ""  # Maison, Appartement
    statut_occupant: Optional[str] = ""  # Propriétaire, Locataire
    surface_habitable: Optional[str] = ""
    annee_construction: Optional[str] = ""
    type_chauffage: Optional[str] = ""
    
    # Énergie
    facture_electricite: Optional[str] = ""
    facture_chauffage: Optional[str] = ""
    
    # Projet
    type_projet: Optional[str] = ""
    delai_projet: Optional[str] = ""
    budget: Optional[str] = ""
    
    # Tracking
    lp_code: Optional[str] = ""
    liaison_code: Optional[str] = ""
    utm_source: Optional[str] = ""
    utm_medium: Optional[str] = ""
    utm_campaign: Optional[str] = ""
    
    # Consentement
    rgpd_consent: Optional[bool] = True
    newsletter: Optional[bool] = False


class LeadDocument(BaseModel):
    """
    Structure complète d'un lead en base de données
    """
    id: str
    
    # Multi-tenant
    entity: str  # ZR7 ou MDL - OBLIGATOIRE
    
    # Statut
    status: LeadStatus = LeadStatus.NEW
    
    # Source
    session_id: str = ""
    form_id: str = ""
    form_code: str = ""
    account_id: str = ""  # Account source (LP/Form)
    product_type: str = ""  # PV, PAC, ITE
    
    # Contact
    phone: str
    nom: str = ""
    prenom: str = ""
    civilite: str = ""
    email: str = ""
    
    # Localisation
    departement: str = ""
    ville: str = ""
    adresse: str = ""
    
    # Logement (toujours TRUE pour proprietaire_maison selon spec)
    type_logement: str = "maison"
    statut_occupant: str = "proprietaire"
    surface_habitable: str = ""
    annee_construction: str = ""
    type_chauffage: str = ""
    
    # Énergie
    facture_electricite: str = ""
    facture_chauffage: str = ""
    
    # Projet
    type_projet: str = ""
    delai_projet: str = ""
    budget: str = ""
    
    # Tracking UTM
    lp_code: str = ""
    liaison_code: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    
    # Consentement
    rgpd_consent: bool = True
    newsletter: bool = False
    
    # === DOUBLON INFO (si statut=doublon) ===
    is_duplicate: bool = False
    duplicate_of_client_id: Optional[str] = None  # Client déjà livré
    duplicate_of_client_name: Optional[str] = None
    duplicate_delivery_date: Optional[str] = None  # Date livraison précédente
    
    # === LIVRAISON INFO ===
    delivered_to_client_id: Optional[str] = None  # Client à qui le lead a été livré
    delivered_to_client_name: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_method: Optional[str] = None  # "csv" ou "api"
    delivery_batch_id: Optional[str] = None  # ID du batch de livraison
    
    # === LB INFO ===
    is_lb: bool = False  # True si lead devenu LB
    lb_since: Optional[str] = None  # Date de passage en LB
    lb_original_product: Optional[str] = None  # Produit original si redistribué
    
    # === REJET CLIENT ===
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # === META ===
    ip: str = ""
    register_date: int = 0  # Timestamp
    created_at: str = ""
    updated_at: str = ""
    
    # Flags techniques
    phone_invalid: bool = False
    missing_required: bool = False


class LeadUpdate(BaseModel):
    """Modification d'un lead par admin"""
    phone: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    departement: Optional[str] = None
    status: Optional[LeadStatus] = None
    notes_admin: Optional[str] = None


class LeadDeliveryInfo(BaseModel):
    """
    Information de livraison d'un lead
    Stockée après chaque livraison
    """
    lead_id: str
    client_id: str
    client_name: str
    entity: str
    product_type: str
    delivery_method: str  # "csv" ou "api"
    delivered_at: str
    batch_id: str
    is_lb: bool = False  # Ce lead était-il un LB ?


class DuplicateCheckResult(BaseModel):
    """
    Résultat de la vérification de doublon
    """
    is_duplicate: bool
    reason: Optional[str] = None
    original_client_id: Optional[str] = None
    original_client_name: Optional[str] = None
    original_delivery_date: Optional[str] = None
