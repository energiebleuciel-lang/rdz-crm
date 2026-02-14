"""
RDZ CRM - Intercompany Transfer Service
FAIL-OPEN: never blocks delivery flow. All errors caught + stored.
"""

import logging
import uuid
import pytz
from config import db, now_iso

logger = logging.getLogger("intercompany")
PARIS_TZ = pytz.timezone("Europe/Paris")


async def maybe_create_intercompany_transfer(
    delivery_id: str,
    lead_id: str,
    commande_id: str,
    product: str,
    target_entity: str,
) -> dict:
    """
    FAIL-OPEN: this function NEVER raises.
    Any error → logged + transfer with status="error" stored for retry.
    Returns: {"created": bool, "transfer_id": str|None, "reason": str}
    """
    try:
        return await _create_transfer(delivery_id, lead_id, commande_id, product, target_entity)
    except Exception as e:
        logger.error(f"[INTERCO_FAIL] delivery={delivery_id[:12]}... error={e}")
        # Best-effort: store error record for retry
        try:
            from datetime import datetime
            now = datetime.now(PARIS_TZ)
            iso = now.isocalendar()
            week_key = f"{iso[0]}-W{iso[1]:02d}"

            await db.intercompany_transfers.update_one(
                {"delivery_id": delivery_id},
                {"$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "delivery_id": delivery_id,
                    "lead_id": lead_id,
                    "commande_id": commande_id,
                    "from_entity": "",
                    "to_entity": target_entity,
                    "product": product,
                    "unit_price_ht": 0,
                    "transfer_status": "error",
                    "error_code": type(e).__name__,
                    "error_message": str(e)[:500],
                    "invoice_id": None,
                    "routing_mode": "unknown",
                    "week_key": week_key,
                    "created_at": now_iso(),
                }},
                upsert=True,
            )
        except Exception:
            pass  # Absolute last resort: silently fail
        return {"created": False, "transfer_id": None, "reason": f"error:{type(e).__name__}"}


async def _create_transfer(delivery_id, lead_id, commande_id, product, target_entity):
    """Internal logic — may raise. Caller catches everything."""
    from datetime import datetime

    # 1. Get lead owner
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "lead_owner_entity": 1, "entity": 1})
    if not lead:
        return {"created": False, "transfer_id": None, "reason": "lead_not_found"}

    owner_entity = lead.get("lead_owner_entity") or lead.get("entity", "")

    # 2. Same entity = no transfer
    if not owner_entity or owner_entity == target_entity:
        return {"created": False, "transfer_id": None, "reason": "same_entity"}

    # 3. Anti-double: unique on delivery_id
    existing = await db.intercompany_transfers.find_one({"delivery_id": delivery_id}, {"_id": 0, "id": 1})
    if existing:
        return {"created": False, "transfer_id": existing["id"], "reason": "already_exists"}

    # 4. Fetch pricing (missing = warning, not crash)
    pricing = await db.intercompany_pricing.find_one({
        "from_entity": owner_entity, "to_entity": target_entity, "product": product,
    }, {"_id": 0})

    unit_price_ht = pricing.get("unit_price_ht", 0) if pricing else 0
    if not pricing:
        logger.warning(f"[INTERCO] Missing pricing {owner_entity}->{target_entity} {product} — using 0")

    # 5. Week key (Europe/Paris)
    now = datetime.now(PARIS_TZ)
    iso = now.isocalendar()
    week_key = f"{iso[0]}-W{iso[1]:02d}"

    # 6. Routing mode from delivery
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0, "routing_mode": 1})
    routing_mode = delivery.get("routing_mode", "unknown") if delivery else "unknown"

    # 7. Create transfer
    transfer_id = str(uuid.uuid4())
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
        "error_code": None,
        "error_message": None,
        "invoice_id": None,
        "routing_mode": routing_mode,
        "week_key": week_key,
        "created_at": now_iso(),
    }

    await db.intercompany_transfers.insert_one(transfer)

    # 8. Event log (best-effort)
    try:
        from services.event_logger import log_event
        await log_event(
            action="intercompany_transfer",
            entity_type="lead",
            entity_id=lead_id,
            entity=owner_entity,
            user="system",
            details={
                "from_entity": owner_entity, "to_entity": target_entity,
                "product": product, "unit_price_ht": unit_price_ht,
                "week_key": week_key, "transfer_id": transfer_id,
                "pricing_found": bool(pricing),
            },
            related={"delivery_id": delivery_id, "commande_id": commande_id},
        )
    except Exception as e:
        logger.error(f"[INTERCO] Event log failed (non-blocking): {e}")

    logger.info(
        f"[INTERCO] Transfer: {owner_entity}->{target_entity} "
        f"lead={lead_id[:8]}... product={product} price={unit_price_ht} week={week_key}"
    )

    return {"created": True, "transfer_id": transfer_id, "reason": "cross_entity"}


async def seed_intercompany_pricing():
    """Seed default pricing if empty."""
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
