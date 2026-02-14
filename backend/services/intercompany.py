"""
RDZ CRM - Intercompany Transfer Service
Triggered when a delivery becomes billable (status=sent, outcome=accepted).
Creates transfer ONLY when lead_owner_entity != target_entity.
Anti-double: unique index on (lead_id, from_entity, to_entity).
"""

import logging
import uuid
from config import db, now_iso
from services.event_logger import log_event

logger = logging.getLogger("intercompany")


async def maybe_create_intercompany_transfer(
    delivery_id: str,
    lead_id: str,
    commande_id: str,
    product: str,
    target_entity: str,
) -> dict:
    """
    Check if this billable delivery triggers an intercompany transfer.
    Called when delivery becomes billable (status=sent, outcome=accepted).

    Returns: {"created": bool, "transfer_id": str|None, "reason": str}
    """
    # 1. Get lead to find owner entity
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "lead_owner_entity": 1, "entity": 1})
    if not lead:
        return {"created": False, "transfer_id": None, "reason": "lead_not_found"}

    owner_entity = lead.get("lead_owner_entity") or lead.get("entity", "")

    # 2. Same entity = no transfer
    if not owner_entity or owner_entity == target_entity:
        return {"created": False, "transfer_id": None, "reason": "same_entity"}

    # 3. Anti-double: check existing transfer for this delivery
    existing = await db.intercompany_transfers.find_one({
        "delivery_id": delivery_id,
    }, {"_id": 0, "id": 1})

    if existing:
        logger.info(f"[INTERCO] Skip duplicate transfer delivery={delivery_id[:8]}... already exists")
        return {"created": False, "transfer_id": existing["id"], "reason": "already_exists"}

    # 4. Fetch pricing
    pricing = await db.intercompany_pricing.find_one({
        "from_entity": owner_entity,
        "to_entity": target_entity,
        "product": product,
    }, {"_id": 0})

    unit_price_ht = pricing.get("unit_price_ht", 0) if pricing else 0

    # 5. Compute week_key
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    week_key = f"{iso[0]}-W{iso[1]:02d}"

    # 6. Create transfer record
    transfer_id = str(uuid.uuid4())

    # Get routing_mode from delivery for audit
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0, "routing_mode": 1})
    routing_mode = delivery.get("routing_mode", "unknown") if delivery else "unknown"

    transfer = {
        "id": transfer_id,
        "lead_id": lead_id,
        "delivery_id": delivery_id,
        "commande_id": commande_id,
        "from_entity": owner_entity,
        "to_entity": target_entity,
        "product": product,
        "unit_price_ht": unit_price_ht,
        "transfer_status": "pending",
        "invoice_id": None,
        "routing_mode": routing_mode,
        "week_key": week_key,
        "created_at": now_iso(),
    }

    await db.intercompany_transfers.insert_one(transfer)

    # 7. Log event + lead timeline
    await log_event(
        action="intercompany_transfer",
        entity_type="lead",
        entity_id=lead_id,
        entity=owner_entity,
        user="system",
        details={
            "from_entity": owner_entity,
            "to_entity": target_entity,
            "product": product,
            "unit_price_ht": unit_price_ht,
            "week_key": week_key,
            "transfer_id": transfer_id,
        },
        related={
            "delivery_id": delivery_id,
            "commande_id": commande_id,
        }
    )

    logger.info(
        f"[INTERCO] Transfer created: {owner_entity}->{target_entity} "
        f"lead={lead_id[:8]}... product={product} price={unit_price_ht} week={week_key}"
    )

    return {"created": True, "transfer_id": transfer_id, "reason": "cross_entity"}


async def seed_intercompany_pricing():
    """Seed default intercompany pricing if empty."""
    count = await db.intercompany_pricing.count_documents({})
    if count > 0:
        return

    defaults = [
        {"from_entity": "ZR7", "to_entity": "MDL", "product": "PV", "unit_price_ht": 25.0},
        {"from_entity": "ZR7", "to_entity": "MDL", "product": "PAC", "unit_price_ht": 30.0},
        {"from_entity": "ZR7", "to_entity": "MDL", "product": "ITE", "unit_price_ht": 20.0},
        {"from_entity": "MDL", "to_entity": "ZR7", "product": "PV", "unit_price_ht": 25.0},
        {"from_entity": "MDL", "to_entity": "ZR7", "product": "PAC", "unit_price_ht": 30.0},
        {"from_entity": "MDL", "to_entity": "ZR7", "product": "ITE", "unit_price_ht": 20.0},
    ]

    for d in defaults:
        d["id"] = str(uuid.uuid4())
        d["created_at"] = now_iso()

    await db.intercompany_pricing.insert_many(defaults)
    logger.info(f"[INTERCO] Seeded {len(defaults)} default pricing records")
