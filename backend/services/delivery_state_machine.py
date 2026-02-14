"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Delivery State Machine                                            ║
║                                                                              ║
║  RÈGLES STRICTES DE TRANSITION DE STATUT                                     ║
║                                                                              ║
║  SEUL CE MODULE peut marquer une delivery comme "sent"                       ║
║  SEUL CE MODULE peut marquer un lead comme "livre"                           ║
║                                                                              ║
║  INVARIANTS DE SÉCURITÉ:                                                     ║
║  - status="sent" IMPLIQUE sent_to non vide                                   ║
║  - status="sent" IMPLIQUE last_sent_at non null                              ║
║  - status="sent" IMPLIQUE send_attempts >= 1                                 ║
║  - lead.status="livre" IMPLIQUE delivery.status="sent"                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from config import db, now_iso

logger = logging.getLogger("delivery_state_machine")


# ════════════════════════════════════════════════════════════════════════════
# VALID STATE TRANSITIONS
# ════════════════════════════════════════════════════════════════════════════

VALID_DELIVERY_TRANSITIONS = {
    "pending_csv": ["ready_to_send", "sending", "failed"],
    "ready_to_send": ["sending", "failed"],
    "sending": ["sent", "failed"],
    "sent": [],  # TERMINAL - no going back
    "failed": ["pending_csv", "sending"],  # Can retry
}

VALID_LEAD_TRANSITIONS = {
    "new": ["routed", "no_open_orders", "hold_source", "pending_config", "invalid", "duplicate"],
    "routed": ["livre", "failed"],  # routed -> livre ONLY via delivery_state_machine
    "livre": [],  # TERMINAL
    "no_open_orders": ["routed"],  # Can be re-routed later
    "hold_source": ["routed", "no_open_orders"],  # If source unblocked
    "pending_config": ["routed", "no_open_orders"],  # If config added
    "duplicate": [],  # TERMINAL
    "invalid": [],  # TERMINAL
}


# ════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKS
# ════════════════════════════════════════════════════════════════════════════

class DeliveryInvariantError(Exception):
    """Raised when a delivery invariant is violated"""
    pass


def check_sent_invariants(sent_to: List[str], last_sent_at: str, send_attempts: int) -> bool:
    """
    Vérifie que les invariants pour status="sent" sont respectés.
    
    INVARIANTS:
    - sent_to doit être une liste non vide
    - last_sent_at doit être non null
    - send_attempts doit être >= 1
    """
    if not sent_to or len(sent_to) == 0:
        raise DeliveryInvariantError("INVARIANT VIOLATION: status=sent requires non-empty sent_to")
    
    if not last_sent_at:
        raise DeliveryInvariantError("INVARIANT VIOLATION: status=sent requires last_sent_at")
    
    if send_attempts < 1:
        raise DeliveryInvariantError("INVARIANT VIOLATION: status=sent requires send_attempts >= 1")
    
    return True


async def validate_delivery_transition(delivery_id: str, from_status: str, to_status: str) -> bool:
    """
    Valide qu'une transition de statut delivery est autorisée.
    """
    valid_next = VALID_DELIVERY_TRANSITIONS.get(from_status, [])
    
    if to_status not in valid_next:
        raise DeliveryInvariantError(
            f"INVALID TRANSITION: delivery {delivery_id} cannot go from '{from_status}' to '{to_status}'. "
            f"Valid transitions from '{from_status}': {valid_next}"
        )
    
    return True


# ════════════════════════════════════════════════════════════════════════════
# SAFE STATE TRANSITIONS (THE ONLY WAY TO MARK SENT/LIVRE)
# ════════════════════════════════════════════════════════════════════════════

async def mark_delivery_sent(
    delivery_id: str,
    sent_to: List[str],
    send_attempts: int = 1,
    sent_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    🔒 SEULE FONCTION AUTORISÉE pour marquer une delivery comme "sent"
    
    Cette fonction:
    1. Vérifie les invariants
    2. Met à jour la delivery
    3. Met à jour le lead associé comme "livre"
    
    Args:
        delivery_id: ID de la delivery
        sent_to: Liste des emails de destination (OBLIGATOIRE, non vide)
        send_attempts: Nombre de tentatives (default 1)
        sent_by: Email de l'utilisateur qui a envoyé (optionnel)
    
    Returns:
        Dict avec les IDs mis à jour
    
    Raises:
        DeliveryInvariantError si les invariants ne sont pas respectés
    """
    now = now_iso()
    
    # 1. Vérifier les invariants AVANT toute modification
    check_sent_invariants(sent_to, now, send_attempts)
    
    # 2. Récupérer la delivery actuelle
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    if not delivery:
        raise DeliveryInvariantError(f"Delivery {delivery_id} not found")
    
    current_status = delivery.get("status")
    
    # 3. Valider la transition
    await validate_delivery_transition(delivery_id, current_status, "sent")
    
    # 4. Mettre à jour la delivery avec TOUS les champs requis
    update_data = {
        "status": "sent",
        "sent_to": sent_to,
        "last_sent_at": now,
        "send_attempts": send_attempts,
        "last_error": None,
        "updated_at": now
    }
    
    if sent_by:
        update_data["sent_by"] = sent_by
    
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": update_data}
    )
    
    # 5. Mettre à jour le lead comme "livre"
    lead_id = delivery.get("lead_id")
    client_id = delivery.get("client_id")
    client_name = delivery.get("client_name", "")
    commande_id = delivery.get("commande_id")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "status": "livre",
            "delivered_at": now,
            "delivered_to_client_id": client_id,
            "delivered_to_client_name": client_name,
            "delivery_commande_id": commande_id,
            "updated_at": now
        }}
    )
    
    logger.info(
        f"[STATE_MACHINE] Delivery {delivery_id} -> sent | "
        f"Lead {lead_id} -> livre | sent_to={sent_to}"
    )
    
    return {
        "delivery_id": delivery_id,
        "lead_id": lead_id,
        "status": "sent",
        "sent_to": sent_to
    }


async def mark_delivery_ready_to_send(
    delivery_id: str,
    csv_content: str,
    csv_filename: str
) -> Dict[str, Any]:
    """
    🔒 Marque une delivery comme "ready_to_send" (CSV généré, pas envoyé)
    
    Le lead reste "routed" (PAS livre).
    """
    now = now_iso()
    
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    if not delivery:
        raise DeliveryInvariantError(f"Delivery {delivery_id} not found")
    
    current_status = delivery.get("status")
    await validate_delivery_transition(delivery_id, current_status, "ready_to_send")
    
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "status": "ready_to_send",
            "csv_content": csv_content,
            "csv_filename": csv_filename,
            "csv_generated_at": now,
            "updated_at": now
        }}
    )
    
    # Lead reste "routed" - pas de modification
    
    logger.info(f"[STATE_MACHINE] Delivery {delivery_id} -> ready_to_send")
    
    return {
        "delivery_id": delivery_id,
        "status": "ready_to_send"
    }


async def mark_delivery_failed(
    delivery_id: str,
    error: str,
    increment_attempts: bool = True
) -> Dict[str, Any]:
    """
    🔒 Marque une delivery comme "failed"
    
    Le lead reste "routed" (PAS livre).
    """
    now = now_iso()
    
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    if not delivery:
        raise DeliveryInvariantError(f"Delivery {delivery_id} not found")
    
    current_status = delivery.get("status")
    
    # Failed est autorisé depuis plusieurs états
    if current_status not in ["pending_csv", "ready_to_send", "sending"]:
        raise DeliveryInvariantError(
            f"Cannot mark delivery {delivery_id} as failed from status '{current_status}'"
        )
    
    current_attempts = delivery.get("send_attempts", 0)
    new_attempts = current_attempts + 1 if increment_attempts else current_attempts
    
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "status": "failed",
            "last_error": error,
            "send_attempts": new_attempts,
            "updated_at": now
        }}
    )
    
    logger.warning(f"[STATE_MACHINE] Delivery {delivery_id} -> failed | error={error}")
    
    return {
        "delivery_id": delivery_id,
        "status": "failed",
        "error": error
    }


async def mark_delivery_sending(delivery_id: str) -> Dict[str, Any]:
    """
    🔒 Marque une delivery comme "sending" (envoi en cours)
    """
    now = now_iso()
    
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    if not delivery:
        raise DeliveryInvariantError(f"Delivery {delivery_id} not found")
    
    current_status = delivery.get("status")
    
    # Sending autorisé depuis pending_csv, ready_to_send, ou failed (retry)
    if current_status not in ["pending_csv", "ready_to_send", "failed"]:
        raise DeliveryInvariantError(
            f"Cannot mark delivery {delivery_id} as sending from status '{current_status}'"
        )
    
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "status": "sending",
            "updated_at": now
        }}
    )
    
    logger.info(f"[STATE_MACHINE] Delivery {delivery_id} -> sending")
    
    return {
        "delivery_id": delivery_id,
        "status": "sending"
    }


# ════════════════════════════════════════════════════════════════════════════
# BATCH SAFE TRANSITIONS
# ════════════════════════════════════════════════════════════════════════════

async def batch_mark_deliveries_sent(
    delivery_ids: List[str],
    lead_ids: List[str],
    sent_to: List[str],
    client_id: str,
    client_name: str,
    commande_id: str
) -> Dict[str, Any]:
    """
    🔒 Marque un batch de deliveries comme "sent" de manière atomique
    
    FAIL-FAST: Refuse si les invariants ne sont pas respectés.
    Vérifie que TOUTES les deliveries sont dans un état source valide.
    """
    now = now_iso()
    
    # Vérifier les invariants AVANT toute modification
    check_sent_invariants(sent_to, now, 1)
    
    # Guard: vérifier que les deliveries sont dans un état source valide
    invalid_deliveries = await db.deliveries.count_documents({
        "id": {"$in": delivery_ids},
        "status": {"$nin": ["pending_csv", "ready_to_send", "sending", "failed"]}
    })
    
    if invalid_deliveries > 0:
        # Trouver les IDs invalides pour le log
        bad = await db.deliveries.find(
            {"id": {"$in": delivery_ids}, "status": {"$nin": ["pending_csv", "ready_to_send", "sending", "failed"]}},
            {"_id": 0, "id": 1, "status": 1}
        ).to_list(10)
        raise DeliveryInvariantError(
            f"BATCH BLOCKED: {invalid_deliveries} deliveries dans un état invalide pour -> sent: {bad}"
        )
    
    # Mettre à jour les deliveries (ONLY from valid source states)
    result_deliveries = await db.deliveries.update_many(
        {
            "id": {"$in": delivery_ids},
            "status": {"$in": ["pending_csv", "ready_to_send", "sending", "failed"]}
        },
        {"$set": {
            "status": "sent",
            "sent_to": sent_to,
            "last_sent_at": now,
            "send_attempts": 1,
            "last_error": None,
            "updated_at": now
        }}
    )
    
    # Mettre à jour les leads
    result_leads = await db.leads.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": {
            "status": "livre",
            "delivered_at": now,
            "delivered_to_client_id": client_id,
            "delivered_to_client_name": client_name,
            "delivery_commande_id": commande_id,
            "updated_at": now
        }}
    )
    
    logger.info(
        f"[STATE_MACHINE_BATCH] {result_deliveries.modified_count} deliveries -> sent | "
        f"{result_leads.modified_count} leads -> livre | sent_to={sent_to}"
    )
    
    return {
        "deliveries_updated": result_deliveries.modified_count,
        "leads_updated": result_leads.modified_count,
        "sent_to": sent_to
    }


async def batch_mark_deliveries_ready_to_send(
    delivery_ids: List[str],
    csv_content: str,
    csv_filename: str
) -> Dict[str, Any]:
    """
    🔒 Marque un batch de deliveries comme "ready_to_send"
    
    Les leads restent "routed". Vérifie les états sources.
    """
    now = now_iso()
    
    # Guard: vérifier que les deliveries sont dans un état source valide
    invalid = await db.deliveries.count_documents({
        "id": {"$in": delivery_ids},
        "status": {"$nin": ["pending_csv"]}
    })
    
    if invalid > 0:
        bad = await db.deliveries.find(
            {"id": {"$in": delivery_ids}, "status": {"$nin": ["pending_csv"]}},
            {"_id": 0, "id": 1, "status": 1}
        ).to_list(10)
        raise DeliveryInvariantError(
            f"BATCH BLOCKED: {invalid} deliveries dans un état invalide pour -> ready_to_send: {bad}"
        )
    
    result = await db.deliveries.update_many(
        {
            "id": {"$in": delivery_ids},
            "status": "pending_csv"
        },
        {"$set": {
            "status": "ready_to_send",
            "csv_content": csv_content,
            "csv_filename": csv_filename,
            "csv_generated_at": now,
            "updated_at": now
        }}
    )
    
    logger.info(f"[STATE_MACHINE_BATCH] {result.modified_count} deliveries -> ready_to_send")
    
    return {
        "deliveries_updated": result.modified_count,
        "status": "ready_to_send"
    }


async def batch_mark_deliveries_failed(
    delivery_ids: List[str],
    error: str
) -> Dict[str, Any]:
    """
    🔒 Marque un batch de deliveries comme "failed"
    
    Guard: vérifie que les deliveries ne sont PAS déjà sent (terminal).
    """
    now = now_iso()
    
    # Guard: bloquer si déjà sent (état terminal)
    already_sent = await db.deliveries.count_documents({
        "id": {"$in": delivery_ids},
        "status": "sent"
    })
    
    if already_sent > 0:
        raise DeliveryInvariantError(
            f"BATCH BLOCKED: {already_sent} deliveries déjà en status 'sent' (terminal)"
        )
    
    result = await db.deliveries.update_many(
        {
            "id": {"$in": delivery_ids},
            "status": {"$in": ["pending_csv", "ready_to_send", "sending"]}
        },
        {"$set": {
            "status": "failed",
            "last_error": error,
            "updated_at": now
        },
        "$inc": {"send_attempts": 1}}
    )
    
    logger.warning(f"[STATE_MACHINE_BATCH] {result.modified_count} deliveries -> failed | error={error}")
    
    return {
        "deliveries_updated": result.modified_count,
        "status": "failed",
        "error": error
    }
