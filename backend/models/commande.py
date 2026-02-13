"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Commande (Ordres d'achat de leads)                         ║
║                                                                              ║
║  Une commande = demande hebdomadaire d'un client pour des leads              ║
║  - Par client, produit, départements                                         ║
║  - Quota semaine avec % LB autorisé                                          ║
║  - Priorité (1-10) pour routing                                              ║
║                                                                              ║
║  RÈGLE: Commande TOUJOURS rattachée à une entité et un client                ║
║                                                                              ║
║  NOTE: EntityType et ProductType importés depuis models/lead.py              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator

# Import depuis lead.py (source unique)
from .lead import EntityType, ProductType


# Liste pour validation
VALID_PRODUCTS = [p.value for p in ProductType]

# Départements métropole France (01-95, hors 2A/2B Corse)
DEPARTEMENTS_METRO = [str(i).zfill(2) for i in range(1, 96) if i != 20]


class CommandeCreate(BaseModel):
    """
    Création d'une commande hebdomadaire
    
    Exemple:
    {
        "entity": "ZR7",
        "client_id": "xxx",
        "produit": "PV",
        "departements": ["75", "92", "93", "94"],
        "quota_semaine": 50,
        "prix_lead": 25.0,
        "lb_percent_max": 20,
        "priorite": 5
    }
    """
    entity: EntityType  # OBLIGATOIRE - ZR7 ou MDL
    client_id: str  # Client acheteur
    produit: ProductType  # PV, PAC ou ITE
    departements: List[str]  # Liste des départements couverts
    
    # Quotas et prix
    quota_semaine: int = 0  # Nombre de leads/semaine souhaités (0 = illimité)
    prix_lead: float = 0.0  # Prix unitaire par lead
    lb_percent_max: int = 0  # % maximum de LB autorisé (0-100)
    
    # Priorité
    priorite: int = Field(default=5, ge=1, le=10)  # 1=haute, 10=basse
    
    # Auto-renew
    auto_renew: bool = True  # Renouvellement automatique semaine suivante
    
    # Remise spécifique à cette commande
    remise_percent: float = 0.0
    
    notes: Optional[str] = ""
    
    @validator('departements')
    def validate_departements(cls, v):
        """Valide que tous les départements sont valides"""
        if "*" in v:
            return ["*"]  # Wildcard = tous les départements
        for dept in v:
            if dept not in DEPARTEMENTS_METRO:
                raise ValueError(f"Département invalide: {dept}")
        return v
    
    @validator('lb_percent_max')
    def validate_lb_percent(cls, v):
        """% LB entre 0 et 100"""
        if v < 0 or v > 100:
            raise ValueError("lb_percent_max doit être entre 0 et 100")
        return v


class CommandeUpdate(BaseModel):
    """Mise à jour d'une commande"""
    departements: Optional[List[str]] = None
    quota_semaine: Optional[int] = None
    prix_lead: Optional[float] = None
    lb_percent_max: Optional[int] = None
    priorite: Optional[int] = None
    auto_renew: Optional[bool] = None
    remise_percent: Optional[float] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    
    @validator('departements')
    def validate_departements(cls, v):
        if v is None:
            return v
        if "*" in v:
            return ["*"]
        for dept in v:
            if dept not in DEPARTEMENTS_METRO:
                raise ValueError(f"Département invalide: {dept}")
        return v
    
    @validator('priorite')
    def validate_priorite(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Priorité doit être entre 1 et 10")
        return v


class CommandeResponse(BaseModel):
    """Réponse commande pour l'API"""
    id: str
    entity: str
    client_id: str
    client_name: str = ""  # Enrichi à la lecture
    produit: str
    departements: List[str]
    quota_semaine: int = 0
    prix_lead: float = 0.0
    lb_percent_max: int = 0
    priorite: int = 5
    auto_renew: bool = True
    remise_percent: float = 0.0
    notes: str = ""
    active: bool = True
    
    # Stats de la semaine en cours
    leads_delivered_this_week: int = 0
    lb_delivered_this_week: int = 0
    quota_remaining: int = 0
    
    # Dates
    week_start: str = ""  # Début de semaine ISO
    created_at: str = ""
    updated_at: str = ""


class CommandeListResponse(BaseModel):
    """Liste de commandes"""
    commandes: List[CommandeResponse]
    count: int
    entity: str
