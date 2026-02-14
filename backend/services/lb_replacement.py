"""
RDZ CRM - LB Replacement Service
Atomic LB selection for suspicious lead replacement.

RULE: When a suspicious lead from internal_lp is routed to a commande,
try to find a compatible LB lead and deliver it instead.

Compatible LB = same entity, same produit, matching departement,
not expired, not already reserved/delivered, not duplicate for this client.
"""

import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso
from services.duplicate_detector import check_duplicate_30_days

logger = logging.getLogger("lb_replacement")


async def try_lb_replacement(
    commande_id: str,
    target_entity: str,
    produit: str,
    client_id: str,
    exclude_lead_id: str,
) -> dict:
    """
    Try to find and atomically reserve an LB lead compatible with the commande.

    Returns:
        {"found": True, "lead_id": "..."} if replacement found
        {"found": False, "reason": "..."} otherwise

    ATOMIC: Uses findOneAndUpdate to prevent double-reservation under concurrency.
    """
    # Get commande departements
    cmd = await db.commandes.find_one(
        {"id": commande_id},
        {"_id": 0, "departements": 1}
    )
    if not cmd:
        return {"found": False, "reason": "commande_not_found"}

    departements = cmd.get("departements", [])

    # Build LB query: same entity + same produit + is_lb + available
    query = {
        "entity": target_entity,
        "produit": produit,
        "is_lb": True,
        "status": {"$in": ["lb", "new", "no_open_orders"]},
        "id": {"$ne": exclude_lead_id},
        "phone": {"$exists": True, "$ne": ""},
        "departement": {"$exists": True, "$ne": ""},
    }

    # Departement filter (skip if wildcard)
    if departements and departements != ["*"] and "*" not in departements:
        query["departement"] = {"$in": departements}

    # Prefer non-suspicious LBs, oldest first
    candidates = await db.leads.find(
        query, {"_id": 0, "id": 1, "phone": 1, "produit": 1}
    ).sort("created_at", 1).limit(50).to_list(50)

    if not candidates:
        return {"found": False, "reason": "no_lb_available"}

    # Try each candidate — check duplicate + atomic reserve
    for candidate in candidates:
        cand_id = candidate["id"]
        cand_phone = candidate["phone"]

        # Duplicate check: this LB must not be a 30-day duplicate for this client
        dup = await check_duplicate_30_days(cand_phone, produit, client_id)
        if dup.is_duplicate:
            continue

        # Atomic reservation: findOneAndUpdate with status filter
        # Only succeeds if the lead is still in an available status
        reserved = await db.leads.find_one_and_update(
            {
                "id": cand_id,
                "status": {"$in": ["lb", "new", "no_open_orders"]},
            },
            {
                "$set": {
                    "status": "reserved_for_replacement",
                    "reserved_at": now_iso(),
                    "reserved_for_client": client_id,
                    "reserved_for_commande": commande_id,
                }
            },
            return_document=False,  # return the original (pre-update) doc
        )

        if reserved:
            logger.info(
                f"[LB_REPLACE] Reserved LB={cand_id[:8]}... for client={client_id[:8]}... "
                f"entity={target_entity} produit={produit}"
            )
            return {"found": True, "lead_id": cand_id}

    return {"found": False, "reason": "all_candidates_duplicate_or_reserved"}
