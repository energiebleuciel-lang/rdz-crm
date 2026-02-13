"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Service de Détection de Doublons                                  ║
║                                                                              ║
║  RÈGLE DOUBLON 30 JOURS:                                                     ║
║  - Même téléphone                                                            ║
║  - Même produit                                                              ║
║  - Déjà livré AU MÊME CLIENT                                                 ║
║  - Dans les 30 derniers jours                                                ║
║                                                                              ║
║  COMPORTEMENT:                                                               ║
║  - Si doublon: NE PAS envoyer                                                ║
║  - Mais TOUJOURS stocker en base avec statut "doublon"                       ║
║  - Logger: client déjà livré + date livraison précédente                     ║
║                                                                              ║
║  PROTECTION ANTI DOUBLE-SUBMIT:                                              ║
║  - Même session + même phone en < 5 secondes                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from config import db

logger = logging.getLogger("duplicate_detector")

# Configuration
DOUBLE_SUBMIT_SECONDS = 5
DUPLICATE_WINDOW_DAYS = 30


class DuplicateResult:
    """Résultat de la détection de doublon"""

    def __init__(
        self,
        is_duplicate: bool,
        duplicate_type: Optional[str] = None,
        original_lead_id: Optional[str] = None,
        original_client_id: Optional[str] = None,
        original_client_name: Optional[str] = None,
        original_delivery_date: Optional[str] = None,
        message: str = ""
    ):
        self.is_duplicate = is_duplicate
        self.duplicate_type = duplicate_type  # "double_submit" ou "30_days"
        self.original_lead_id = original_lead_id
        self.original_client_id = original_client_id
        self.original_client_name = original_client_name
        self.original_delivery_date = original_delivery_date
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "duplicate_type": self.duplicate_type,
            "original_lead_id": self.original_lead_id,
            "original_client_id": self.original_client_id,
            "original_client_name": self.original_client_name,
            "original_delivery_date": self.original_delivery_date,
            "message": self.message
        }


async def check_double_submit(
    phone: str,
    session_id: str
) -> DuplicateResult:
    """
    Vérifie le double-submit (anti double-clic)
    Même session + même phone en < 5 secondes
    """
    if not phone or not session_id:
        return DuplicateResult(is_duplicate=False)
    
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(seconds=DOUBLE_SUBMIT_SECONDS)).isoformat()
    
    double_submit = await db.leads.find_one({
        "session_id": session_id,
        "phone": phone,
        "created_at": {"$gte": cutoff}
    }, {"_id": 0, "id": 1})

    if double_submit:
        logger.info(f"[DOUBLE_SUBMIT] Détecté pour session {session_id[:8]}... phone={phone[-4:]}")
        return DuplicateResult(
            is_duplicate=True,
            duplicate_type="double_submit",
            original_lead_id=double_submit.get("id"),
            message="Double soumission détectée - lead déjà créé"
        )
    
    return DuplicateResult(is_duplicate=False)


async def check_duplicate_30_days(
    phone: str,
    product_type: str,
    target_client_id: str
) -> DuplicateResult:
    """
    Vérifie la règle doublon 30 jours:
    - Même téléphone
    - Même produit  
    - Déjà livré AU MÊME CLIENT
    - Dans les 30 derniers jours
    
    IMPORTANT: Cette fonction vérifie si le lead peut être envoyé à un client spécifique.
    Un lead peut être doublon pour un client mais pas pour un autre.
    """
    if not phone or not product_type or not target_client_id:
        return DuplicateResult(is_duplicate=False)
    
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    
    # Chercher un lead déjà livré à CE CLIENT avec ce phone+produit dans les 30 jours
    existing = await db.leads.find_one({
        "phone": phone,
        "product_type": product_type,
        "delivered_to_client_id": target_client_id,
        "status": "livre",  # Seulement les leads effectivement livrés
        "delivered_at": {"$gte": cutoff}
    }, {"_id": 0, "id": 1, "delivered_to_client_id": 1, "delivered_to_client_name": 1, "delivered_at": 1})

    if existing:
        logger.info(
            f"[DOUBLON_30J] phone={phone[-4:]} product={product_type} "
            f"client={target_client_id[:8]}... déjà livré le {existing.get('delivered_at', '')[:10]}"
        )
        return DuplicateResult(
            is_duplicate=True,
            duplicate_type="30_days",
            original_lead_id=existing.get("id"),
            original_client_id=existing.get("delivered_to_client_id"),
            original_client_name=existing.get("delivered_to_client_name"),
            original_delivery_date=existing.get("delivered_at"),
            message=f"Doublon 30 jours - déjà livré à ce client le {existing.get('delivered_at', '')[:10]}"
        )
    
    return DuplicateResult(is_duplicate=False)


async def check_duplicate_for_any_client(
    phone: str,
    product_type: str,
    entity: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Vérifie si un lead a déjà été livré à N'IMPORTE QUEL client de l'entité
    dans les 30 jours (pour le même phone + produit).
    
    Retourne:
    - (False, {}) si pas de doublon
    - (True, {clients_already_delivered: [...]}) si doublon
    
    Utilisé pour le routing: on peut proposer le lead à un autre client
    qui ne l'a pas encore reçu.
    """
    if not phone or not product_type or not entity:
        return False, {}
    
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    
    # Chercher tous les clients à qui ce lead a déjà été livré
    cursor = db.leads.find({
        "phone": phone,
        "product_type": product_type,
        "entity": entity,
        "status": "livre",
        "delivered_at": {"$gte": cutoff}
    }, {"_id": 0, "delivered_to_client_id": 1, "delivered_to_client_name": 1, "delivered_at": 1})
    
    already_delivered = await cursor.to_list(100)
    
    if already_delivered:
        clients = [
            {
                "client_id": d.get("delivered_to_client_id"),
                "client_name": d.get("delivered_to_client_name"),
                "delivered_at": d.get("delivered_at")
            }
            for d in already_delivered
        ]
        return True, {"clients_already_delivered": clients}
    
    return False, {}


async def check_duplicate(
    phone: str,
    product_type: str,
    session_id: Optional[str] = None,
    target_client_id: Optional[str] = None
) -> DuplicateResult:
    """
    Fonction principale de vérification de doublon.
    
    Vérifie dans l'ordre:
    1. Double-submit (si session_id fourni)
    2. Règle 30 jours (si target_client_id fourni)
    
    Args:
        phone: Numéro de téléphone du lead
        product_type: Type de produit (PV, PAC, ITE)
        session_id: ID de session (pour anti double-clic)
        target_client_id: Client cible (pour règle 30 jours)
    
    Returns:
        DuplicateResult avec is_duplicate=True si doublon détecté
    """
    if not phone:
        return DuplicateResult(is_duplicate=False)
    
    # 1. Anti double-submit
    if session_id:
        result = await check_double_submit(phone, session_id)
        if result.is_duplicate:
            return result
    
    # 2. Règle 30 jours (si client cible spécifié)
    if target_client_id and product_type:
        result = await check_duplicate_30_days(phone, product_type, target_client_id)
        if result.is_duplicate:
            return result
    
    return DuplicateResult(is_duplicate=False)
