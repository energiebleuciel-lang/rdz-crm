"""
RDZ CRM - Event Logger

Centralized audit trail for all sensitive actions.
Single function to call from any route/service.
"""

import uuid
from config import db, now_iso


async def log_event(
    action: str,
    entity_type: str,
    entity_id: str,
    user: str = "system",
    entity: str = "",
    details: dict = None,
    related: dict = None
):
    """
    Write a single event to the event_log collection.

    Args:
        action: e.g. reject_lead, send_delivery, order_activate
        entity_type: lead | delivery | client | commande | provider | settings
        entity_id: ID of the primary entity
        user: email of user performing action
        entity: ZR7 | MDL (business entity)
        details: free-form dict (reason, old_value, new_value, etc.)
        related: linked entity IDs (lead_id, client_id, commande_id, etc.)
    """
    await db.event_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity": entity,
        "user": user,
        "details": details or {},
        "related": related or {},
        "created_at": now_iso()
    })
