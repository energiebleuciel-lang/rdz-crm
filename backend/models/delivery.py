"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Delivery (Livraison individuelle)                          ║
║                                                                              ║
║  LIFECYCLE STRICT:                                                           ║
║  pending_csv → ready_to_send → sending → sent / failed                       ║
║                                                                              ║
║  RÈGLE: lead.status = "livre" UNIQUEMENT si delivery.status = "sent"         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class DeliveryStatus(str, Enum):
    """Statuts stricts du cycle de vie delivery"""
    PENDING_CSV = "pending_csv"        # En attente de traitement batch
    READY_TO_SEND = "ready_to_send"    # CSV généré, en attente envoi (mode manuel)
    SENDING = "sending"                 # En cours d'envoi
    SENT = "sent"                       # Accepté par SMTP / envoyé
    FAILED = "failed"                   # Erreur d'envoi


# Statuts valides pour transition
VALID_STATUS_TRANSITIONS = {
    "pending_csv": ["ready_to_send", "sending", "failed"],
    "ready_to_send": ["sending", "failed"],
    "sending": ["sent", "failed"],
    "sent": [],  # Terminal - pas de retour
    "failed": ["sending"],  # Peut être retenté
}


class Delivery(BaseModel):
    """
    Livraison individuelle d'un lead à un client
    
    Créée au moment du routing (status=pending_csv)
    Traitée par le batch quotidien ou manuellement
    """
    id: str
    lead_id: str
    client_id: str
    client_name: str
    commande_id: str
    
    # Classification
    entity: str  # ZR7 ou MDL
    produit: str
    
    # Méthode
    delivery_method: str = "csv_email"  # csv_email | api | manual
    
    # Statut lifecycle
    status: str = "pending_csv"
    
    # Traçabilité envoi
    sent_to: List[str] = []         # Emails auxquels le CSV a été envoyé
    send_attempts: int = 0          # Nombre de tentatives d'envoi
    last_sent_at: Optional[str] = None  # Dernier envoi tenté
    last_error: Optional[str] = None    # Dernière erreur
    sent_by: Optional[str] = None   # User qui a envoyé (si manuel)
    
    # CSV stocké (pour ready_to_send / téléchargement)
    csv_content: Optional[str] = None       # Contenu CSV (string)
    csv_filename: Optional[str] = None      # Nom du fichier
    csv_generated_at: Optional[str] = None  # Date génération
    
    # Flags
    is_lb: bool = False
    
    # Dates
    created_at: str = ""
    updated_at: Optional[str] = None


class DeliveryBatch(BaseModel):
    """
    Batch de livraison quotidienne (agrégé)
    Regroupe plusieurs deliveries pour un même client/commande
    """
    id: str
    entity: str
    client_id: str
    client_name: str
    commande_id: str
    produit: str
    
    # Contenu
    delivery_ids: List[str] = []
    lead_count: int = 0
    lb_count: int = 0
    
    # Résultat
    status: str = "pending"  # pending, sent, partial, failed
    
    # CSV
    csv_filename: Optional[str] = None
    csv_content: Optional[str] = None
    
    # Envoi
    sent_to: List[str] = []
    send_attempts: int = 0
    last_error: Optional[str] = None
    
    # Dates
    scheduled_at: str = ""
    sent_at: Optional[str] = None
    created_at: str = ""


class DeliveryStats(BaseModel):
    """Stats de livraison pour dashboard"""
    entity: str
    date: str
    
    # Par statut
    pending_csv: int = 0
    ready_to_send: int = 0
    sending: int = 0
    sent: int = 0
    failed: int = 0
    
    # Totaux
    total_leads_delivered: int = 0
    total_lb_delivered: int = 0
    clients_served: int = 0


class SendDeliveryRequest(BaseModel):
    """Request pour envoyer/renvoyer une delivery"""
    override_email: Optional[str] = None  # Email override (optionnel)
    force: bool = False  # Forcer même si déjà sent


class RejectDeliveryRequest(BaseModel):
    """Request pour rejeter une delivery (rejet client)"""
    reason: str = ""  # Motif du rejet


class DeliveryResponse(BaseModel):
    """Response API pour une delivery"""
    id: str
    lead_id: str
    client_id: str
    client_name: str
    commande_id: str
    entity: str
    produit: str
    status: str
    delivery_method: str
    sent_to: List[str] = []
    send_attempts: int = 0
    last_sent_at: Optional[str] = None
    last_error: Optional[str] = None
    is_lb: bool = False
    has_csv: bool = False  # True si csv_content existe
    csv_filename: Optional[str] = None
    created_at: str = ""
    updated_at: Optional[str] = None
