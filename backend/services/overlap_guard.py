"""
RDZ CRM - Client Overlap Guard
Soft protection: avoid delivering to shared clients (same email across entities)
when an alternative non-shared commande exists.

FAIL-OPEN: any error → deliver normally, never block.
BOUNDED: max 10 candidates, timeout ~100ms.
KILL SWITCH: OVERLAP_GUARD_ENABLED setting.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from config import db, now_iso

logger = logging.getLogger("overlap_guard")

OVERLAP_WINDOW_DAYS = 30
MAX_CANDIDATES = 10


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def compute_client_group_key(client: dict) -> str:
    """Build a canonical group key from delivery emails."""
    emails = set()
    for e in client.get("delivery_emails", []):
        n = _normalize_email(e)
        if n:
            emails.add(n)
    main = _normalize_email(client.get("email", ""))
    if main:
        emails.add(main)
    if not emails:
        return ""
    return "|".join(sorted(emails))


async def is_guard_enabled() -> bool:
    """Check kill switch in settings."""
    doc = await db.settings.find_one({"key": "overlap_guard"}, {"_id": 0})
    if not doc:
        return True  # Enabled by default
    return doc.get("enabled", True)


async def check_overlap_and_find_alternative(
    selected_client_id: str,
    selected_commande_id: str,
    entity: str,
    produit: str,
    departement: str,
    phone: str,
) -> dict:
    """
    FAIL-OPEN overlap check + alternative search.

    Returns:
        {
            "is_shared": bool,
            "overlap_active_30d": bool,
            "client_group_key": str,
            "alternative_found": bool,
            "alternative_client_id": str|None,
            "alternative_client_name": str|None,
            "alternative_commande_id": str|None,
            "fallback": bool,  # True = delivered to original despite overlap
        }
    """
    try:
        return await asyncio.wait_for(
            _check_overlap_internal(
                selected_client_id, selected_commande_id,
                entity, produit, departement, phone,
            ),
            timeout=0.5,  # 500ms hard timeout (generous for safety)
        )
    except asyncio.TimeoutError:
        logger.warning("[OVERLAP] Timeout — fallback to normal delivery")
        return _no_overlap_result("")
    except Exception as e:
        logger.error(f"[OVERLAP] Error — fallback: {e}")
        return _no_overlap_result("")


def _no_overlap_result(key: str) -> dict:
    return {
        "is_shared": False, "overlap_active_30d": False,
        "client_group_key": key,
        "alternative_found": False, "alternative_client_id": None,
        "alternative_client_name": None, "alternative_commande_id": None,
        "fallback": False,
    }


async def _check_overlap_internal(
    selected_client_id, selected_commande_id,
    entity, produit, departement, phone,
) -> dict:
    # 1. Get selected client's group key
    client = await db.clients.find_one(
        {"id": selected_client_id},
        {"_id": 0, "email": 1, "delivery_emails": 1}
    )
    if not client:
        return _no_overlap_result("")

    group_key = compute_client_group_key(client)
    if not group_key:
        return _no_overlap_result("")

    # 2. Check if any client in the OTHER entity shares the same emails
    other_entity = "MDL" if entity == "ZR7" else "ZR7"
    emails_list = [e for e in group_key.split("|") if e]

    shared_client = await db.clients.find_one({
        "entity": other_entity,
        "$or": [
            {"email": {"$in": emails_list}},
            {"delivery_emails": {"$elemMatch": {"$in": emails_list}}},
        ],
    }, {"_id": 0, "id": 1})

    if not shared_client:
        return _no_overlap_result(group_key)

    # 3. Check 30-day window: was there a cross-entity delivery to this group?
    cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=OVERLAP_WINDOW_DAYS)).isoformat()
    cross_delivery = await db.deliveries.find_one({
        "client_group_key": group_key,
        "entity": other_entity,
        "status": "sent",
        "created_at": {"$gte": cutoff_30d},
    }, {"_id": 0, "id": 1})

    if not cross_delivery:
        # Also check by client_id of the shared client
        cross_delivery = await db.deliveries.find_one({
            "client_id": shared_client["id"],
            "entity": other_entity,
            "status": "sent",
            "created_at": {"$gte": cutoff_30d},
        }, {"_id": 0, "id": 1})

    if not cross_delivery:
        # Shared structure exists but no active overlap in 30d
        return {
            **_no_overlap_result(group_key),
            "is_shared": True,
            "overlap_active_30d": False,
        }

    # 4. Overlap active! Try to find alternative non-shared commande
    logger.info(
        f"[OVERLAP] Active overlap detected: client={selected_client_id[:8]}... "
        f"group_key={group_key[:30]}... entity={entity}"
    )

    from services.routing_engine import find_open_commandes
    from services.duplicate_detector import check_duplicate_30_days

    alt_commandes = await find_open_commandes(entity, produit, departement, False)

    candidates_checked = 0
    for cmd in alt_commandes:
        if candidates_checked >= MAX_CANDIDATES:
            break
        if cmd.get("client_id") == selected_client_id:
            continue  # Skip the original

        candidates_checked += 1
        alt_client_id = cmd.get("client_id")

        # Check if this alternative is also shared
        alt_client = await db.clients.find_one(
            {"id": alt_client_id},
            {"_id": 0, "email": 1, "delivery_emails": 1}
        )
        if alt_client:
            alt_key = compute_client_group_key(alt_client)
            # Check if alt also has cross-entity overlap
            if alt_key:
                alt_shared = await db.clients.find_one({
                    "entity": other_entity,
                    "$or": [
                        {"email": {"$in": [e for e in alt_key.split("|") if e]}},
                        {"delivery_emails": {"$elemMatch": {"$in": [e for e in alt_key.split("|") if e]}}},
                    ],
                }, {"_id": 0, "id": 1})
                if alt_shared:
                    continue  # This alternative is also shared, skip

        # Check duplicate
        dup = await check_duplicate_30_days(phone, produit, alt_client_id)
        if dup.is_duplicate:
            continue

        # Found a non-shared alternative!
        logger.info(
            f"[OVERLAP] Alternative found: {cmd.get('client_name')} "
            f"commande={cmd.get('id')[:8]}..."
        )
        return {
            "is_shared": True, "overlap_active_30d": True,
            "client_group_key": group_key,
            "alternative_found": True,
            "alternative_client_id": alt_client_id,
            "alternative_client_name": cmd.get("client_name", ""),
            "alternative_commande_id": cmd.get("id"),
            "fallback": False,
        }

    # No alternative — fallback to original (fail-open)
    logger.info(f"[OVERLAP] No alternative — fallback delivery to shared client")
    return {
        "is_shared": True, "overlap_active_30d": True,
        "client_group_key": group_key,
        "alternative_found": False, "alternative_client_id": None,
        "alternative_client_name": None, "alternative_commande_id": None,
        "fallback": True,
    }
