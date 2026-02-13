"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Modèle Livraison (Delivery Batch)                                 ║
║                                                                              ║
║  Chaque livraison quotidienne (09h30) crée un batch                          ║
║  - Par entité, par client                                                    ║
║  - Contient les leads livrés (CSV ou API)                                    ║
║  - Traçabilité complète                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Optional, List
from pydantic import BaseModel
from .entity import EntityType


class DeliveryBatch(BaseModel):
    """
    Batch de livraison quotidienne
    """
    id: str
    entity: str  # ZR7 ou MDL
    client_id: str
    client_name: str
    
    # Méthode
    delivery_method: str  # "csv_email", "api", "both"
    
    # Contenu
    lead_ids: List[str] = []  # IDs des leads livrés
    lead_count: int = 0
    lb_count: int = 0  # Combien étaient des LB
    
    # Résultat
    status: str = "pending"  # pending, sent, failed
    
    # CSV
    csv_filename: Optional[str] = None
    csv_emails_sent_to: List[str] = []
    
    # API
    api_endpoint: Optional[str] = None
    api_response: Optional[str] = None
    
    # Dates
    scheduled_at: str = ""  # Quand la livraison était prévue
    sent_at: Optional[str] = None  # Quand effectivement envoyée
    created_at: str = ""
    
    # Erreur
    error_message: Optional[str] = None


class DeliveryStats(BaseModel):
    """
    Stats de livraison pour dashboard
    """
    entity: str
    date: str  # Date du jour
    
    # Totaux
    total_batches: int = 0
    total_leads_delivered: int = 0
    total_lb_delivered: int = 0
    
    # Par méthode
    csv_batches: int = 0
    api_batches: int = 0
    
    # Par client
    clients_served: int = 0
    
    # Erreurs
    failed_batches: int = 0
