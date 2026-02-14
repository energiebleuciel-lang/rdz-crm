"""
RDZ CRM - Intercompany Routes
Transfer list, pricing CRUD, weekly invoice generation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from config import db, now_iso
from routes.auth import get_current_user
from services.permissions import (
    require_permission, validate_entity_access,
    get_entity_scope_from_request, build_entity_filter, enforce_write_entity,
)

router = APIRouter(prefix="/intercompany", tags=["Intercompany"])


class PricingUpsert(BaseModel):
    from_entity: str
    to_entity: str
    product: str
    unit_price_ht: float


# ════════════════════════════════════════════════════════════════════════
# PRICING
# ════════════════════════════════════════════════════════════════════════

@router.get("/pricing")
async def list_pricing(user: dict = Depends(require_permission("intercompany.view"))):
    items = await db.intercompany_pricing.find({}, {"_id": 0}).to_list(50)
    return {"pricing": items, "count": len(items)}


@router.put("/pricing")
async def upsert_pricing(
    data: PricingUpsert,
    user: dict = Depends(require_permission("intercompany.manage"))
):
    existing = await db.intercompany_pricing.find_one({
        "from_entity": data.from_entity.upper(),
        "to_entity": data.to_entity.upper(),
        "product": data.product.upper(),
    })
    if existing:
        await db.intercompany_pricing.update_one(
            {"id": existing["id"]},
            {"$set": {"unit_price_ht": data.unit_price_ht, "updated_at": now_iso()}}
        )
        return {"success": True, "action": "updated"}
    else:
        doc = {
            "id": str(uuid.uuid4()),
            "from_entity": data.from_entity.upper(),
            "to_entity": data.to_entity.upper(),
            "product": data.product.upper(),
            "unit_price_ht": data.unit_price_ht,
            "created_at": now_iso(),
        }
        await db.intercompany_pricing.insert_one(doc)
        return {"success": True, "action": "created"}


# ════════════════════════════════════════════════════════════════════════
# TRANSFERS
# ════════════════════════════════════════════════════════════════════════

@router.get("/transfers")
async def list_transfers(
    request: Request,
    week_key: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(require_permission("intercompany.view"))
):
    scope = get_entity_scope_from_request(user, request)
    query = {}
    if scope != "BOTH":
        query["$or"] = [{"from_entity": scope}, {"to_entity": scope}]
    if week_key:
        query["week_key"] = week_key
    if status:
        query["transfer_status"] = status

    transfers = await db.intercompany_transfers.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    total = await db.intercompany_transfers.count_documents(query)
    return {"transfers": transfers, "count": len(transfers), "total": total}


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(
    transfer_id: str,
    user: dict = Depends(require_permission("intercompany.manage"))
):
    t = await db.intercompany_transfers.find_one({"id": transfer_id})
    if not t:
        raise HTTPException(404, "Transfert non trouvé")
    if t.get("transfer_status") != "pending":
        raise HTTPException(400, f"Seul un transfert pending peut être annulé (actuel: {t.get('transfer_status')})")

    await db.intercompany_transfers.update_one(
        {"id": transfer_id},
        {"$set": {"transfer_status": "cancelled", "cancelled_at": now_iso()}}
    )
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════
# WEEKLY INVOICE GENERATION
# ════════════════════════════════════════════════════════════════════════

@router.post("/generate-invoices")
async def generate_weekly_invoices(
    week_key: Optional[str] = None,
    user: dict = Depends(require_permission("billing.manage"))
):
    """
    Aggregate pending transfers from a week and generate intercompany invoices.
    Groups by (from_entity, to_entity, product).
    One invoice per (from_entity → to_entity) direction.
    """
    # Default: previous week
    if not week_key:
        now = datetime.now(timezone.utc)
        prev = now - timedelta(days=7)
        iso = prev.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"

    # Get pending transfers for the week
    pending = await db.intercompany_transfers.find({
        "week_key": week_key,
        "transfer_status": "pending",
    }, {"_id": 0}).to_list(10000)

    if not pending:
        return {"success": True, "invoices_created": 0, "message": "Aucun transfert pending pour cette semaine"}

    # Group by (from_entity, to_entity)
    groups = defaultdict(list)
    for t in pending:
        key = (t["from_entity"], t["to_entity"])
        groups[key].append(t)

    invoices_created = []

    for (from_ent, to_ent), transfers in groups.items():
        # IDEMPOTENT: skip if invoice already exists for this direction+week
        existing_inv = await db.invoices.find_one({
            "type": "intercompany",
            "from_entity": from_ent,
            "to_entity": to_ent,
            "week_key": week_key,
        }, {"_id": 0, "id": 1, "invoice_number": 1})
        if existing_inv:
            # Still mark transfers as invoiced (in case previous run partially failed)
            tids = [t["id"] for t in transfers]
            await db.intercompany_transfers.update_many(
                {"id": {"$in": tids}, "transfer_status": "pending"},
                {"$set": {"transfer_status": "invoiced", "invoice_id": existing_inv["id"]}}
            )
            invoices_created.append({
                "invoice_number": existing_inv["invoice_number"],
                "from_entity": from_ent, "to_entity": to_ent,
                "skipped": True, "reason": "already_exists",
            })
            continue

        # Build line items by product
        lines_by_product = defaultdict(lambda: {"qty": 0, "unit_price_ht": 0, "transfer_ids": []})
        for t in transfers:
            p = t["product"]
            lines_by_product[p]["qty"] += 1
            lines_by_product[p]["unit_price_ht"] = t["unit_price_ht"]
            lines_by_product[p]["transfer_ids"].append(t["id"])

        line_items = []
        total_ht = 0
        all_transfer_ids = []
        for product, data in lines_by_product.items():
            line_ht = data["qty"] * data["unit_price_ht"]
            line_items.append({
                "product": product,
                "qty": data["qty"],
                "unit_price_ht": data["unit_price_ht"],
                "total_ht": round(line_ht, 2),
            })
            total_ht += line_ht
            all_transfer_ids.extend(data["transfer_ids"])

        # Compute week date range for display
        from services.routing_engine import week_key_to_range
        ws, we = week_key_to_range(week_key)

        # Generate invoice
        inv_count = await db.invoices.count_documents({"entity": from_ent}) + 1
        now_str = now_iso()
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": f"IC-{from_ent}-{week_key}-{inv_count:04d}",
            "entity": from_ent,
            "type": "intercompany",
            "client_id": None,
            "client_name": to_ent,
            "from_entity": from_ent,
            "to_entity": to_ent,
            "week_key": week_key,
            "week_start": ws,
            "week_end": we,
            "line_items": line_items,
            "transfer_ids": all_transfer_ids,
            "amount_ht": round(total_ht, 2),
            "vat_rate": 0,
            "amount_ttc": round(total_ht, 2),
            "status": "draft",
            "issued_at": now_str,
            "due_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "paid_at": None,
            "created_at": now_str,
            "created_by": user.get("email", "system"),
        }

        await db.invoices.insert_one(invoice)

        # Mark transfers as invoiced
        await db.intercompany_transfers.update_many(
            {"id": {"$in": all_transfer_ids}},
            {"$set": {"transfer_status": "invoiced", "invoice_id": invoice["id"]}}
        )

        invoice.pop("_id", None)
        invoices_created.append({
            "invoice_number": invoice["invoice_number"],
            "from_entity": from_ent,
            "to_entity": to_ent,
            "amount_ht": invoice["amount_ht"],
            "lines": len(line_items),
            "transfers_count": len(all_transfer_ids),
        })

    return {
        "success": True,
        "week_key": week_key,
        "invoices_created": len(invoices_created),
        "invoices": invoices_created,
    }


async def generate_weekly_invoices_internal(week_key: str) -> dict:
    """Internal function for cron — no auth required."""
    import logging
    _logger = logging.getLogger("intercompany")

    pending = await db.intercompany_transfers.find({
        "week_key": week_key, "transfer_status": "pending",
    }, {"_id": 0}).to_list(10000)

    if not pending:
        return {"invoices_created": 0}

    groups = defaultdict(list)
    for t in pending:
        groups[(t["from_entity"], t["to_entity"])].append(t)

    created = 0
    for (from_ent, to_ent), transfers in groups.items():
        existing_inv = await db.invoices.find_one({
            "type": "intercompany", "from_entity": from_ent,
            "to_entity": to_ent, "week_key": week_key,
        }, {"_id": 0, "id": 1})
        if existing_inv:
            tids = [t["id"] for t in transfers]
            await db.intercompany_transfers.update_many(
                {"id": {"$in": tids}, "transfer_status": "pending"},
                {"$set": {"transfer_status": "invoiced", "invoice_id": existing_inv["id"]}}
            )
            continue

        lines_by_product = defaultdict(lambda: {"qty": 0, "unit_price_ht": 0, "transfer_ids": []})
        for t in transfers:
            lines_by_product[t["product"]]["qty"] += 1
            lines_by_product[t["product"]]["unit_price_ht"] = t["unit_price_ht"]
            lines_by_product[t["product"]]["transfer_ids"].append(t["id"])

        line_items, total_ht, all_ids = [], 0, []
        for product, data in lines_by_product.items():
            lht = data["qty"] * data["unit_price_ht"]
            line_items.append({"product": product, "qty": data["qty"], "unit_price_ht": data["unit_price_ht"], "total_ht": round(lht, 2)})
            total_ht += lht
            all_ids.extend(data["transfer_ids"])

        from services.routing_engine import week_key_to_range
        ws, we = week_key_to_range(week_key)
        inv_count = await db.invoices.count_documents({"entity": from_ent}) + 1
        now_str = now_iso()

        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": f"IC-{from_ent}-{week_key}-{inv_count:04d}",
            "entity": from_ent, "type": "intercompany",
            "client_id": None, "client_name": to_ent,
            "from_entity": from_ent, "to_entity": to_ent,
            "week_key": week_key, "week_start": ws, "week_end": we,
            "line_items": line_items, "transfer_ids": all_ids,
            "amount_ht": round(total_ht, 2), "vat_rate": 0, "amount_ttc": round(total_ht, 2),
            "status": "draft", "issued_at": now_str,
            "due_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "paid_at": None, "created_at": now_str, "created_by": "cron",
        }
        await db.invoices.insert_one(invoice)
        await db.intercompany_transfers.update_many(
            {"id": {"$in": all_ids}},
            {"$set": {"transfer_status": "invoiced", "invoice_id": invoice["id"]}}
        )
        created += 1
        _logger.info(f"[INTERCO_CRON] Invoice {invoice['invoice_number']}: {from_ent}->{to_ent} {total_ht}EUR")

    return {"invoices_created": created, "week_key": week_key}



# ════════════════════════════════════════════════════════════════════════
# INTERCOMPANY INVOICES
# ════════════════════════════════════════════════════════════════════════

@router.get("/invoices")
async def list_intercompany_invoices(
    request: Request,
    week_key: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(require_permission("intercompany.view"))
):
    """List intercompany invoices with filters."""
    scope = get_entity_scope_from_request(user, request)
    query = {"type": "intercompany"}

    if scope != "BOTH":
        query["$or"] = [{"from_entity": scope}, {"to_entity": scope}]
    if week_key:
        query["week_key"] = week_key
    if direction:
        parts = direction.split("->")
        if len(parts) == 2:
            query["from_entity"] = parts[0].strip()
            query["to_entity"] = parts[1].strip()
    if status:
        query["status"] = status

    invoices = await db.invoices.find(query, {"_id": 0}).sort("issued_at", -1).limit(limit).to_list(limit)
    total = await db.invoices.count_documents(query)
    return {"invoices": invoices, "count": len(invoices), "total": total}


@router.get("/invoices/{invoice_id}")
async def get_intercompany_invoice_detail(
    invoice_id: str,
    user: dict = Depends(require_permission("intercompany.view"))
):
    """Get intercompany invoice with transfer details."""
    inv = await db.invoices.find_one({"id": invoice_id, "type": "intercompany"}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Facture intercompany non trouvée")

    # Fetch transfer details
    transfer_ids = inv.get("transfer_ids", [])
    transfers = await db.intercompany_transfers.find(
        {"id": {"$in": transfer_ids}}, {"_id": 0}
    ).to_list(len(transfer_ids))

    return {"invoice": inv, "transfers": transfers}


# ════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH + RETRY
# ════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def intercompany_health(
    user: dict = Depends(require_permission("intercompany.view"))
):
    """System health: failed transfers, last cron, failed invoices."""
    # Failed transfers
    error_count = await db.intercompany_transfers.count_documents({"transfer_status": "error"})
    pending_count = await db.intercompany_transfers.count_documents({"transfer_status": "pending"})
    invoiced_count = await db.intercompany_transfers.count_documents({"transfer_status": "invoiced"})
    total_count = await db.intercompany_transfers.count_documents({})

    # Recent errors (last 10)
    recent_errors = await db.intercompany_transfers.find(
        {"transfer_status": "error"}, {"_id": 0, "id": 1, "delivery_id": 1, "error_code": 1, "error_message": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)

    # Last cron runs
    last_crons = await db.cron_logs.find(
        {"job": "intercompany_invoices"}, {"_id": 0}
    ).sort("run_at", -1).limit(5).to_list(5)

    # Failed intercompany invoices (draft with old issue date)
    failed_invoice_gen = await db.invoices.count_documents({
        "type": "intercompany", "status": "draft",
    })

    return {
        "transfers": {
            "total": total_count,
            "pending": pending_count,
            "invoiced": invoiced_count,
            "error": error_count,
        },
        "recent_errors": recent_errors,
        "cron": {
            "last_runs": last_crons,
        },
        "invoices": {
            "draft_count": failed_invoice_gen,
        },
        "status": "healthy" if error_count == 0 else "degraded",
    }


@router.post("/retry-errors")
async def retry_failed_transfers(
    user: dict = Depends(require_permission("intercompany.manage"))
):
    """Retry all transfers with status=error."""
    from services.intercompany import maybe_create_intercompany_transfer

    errors = await db.intercompany_transfers.find(
        {"transfer_status": "error"}, {"_id": 0}
    ).to_list(500)

    if not errors:
        return {"retried": 0, "message": "Aucun transfert en erreur"}

    retried = 0
    fixed = 0
    still_error = 0

    for t in errors:
        # Delete the error record so maybe_create can re-insert
        await db.intercompany_transfers.delete_one({"id": t["id"]})

        result = await maybe_create_intercompany_transfer(
            delivery_id=t.get("delivery_id", ""),
            lead_id=t.get("lead_id", ""),
            commande_id=t.get("commande_id", ""),
            product=t.get("product", ""),
            target_entity=t.get("to_entity", ""),
        )
        retried += 1
        if result.get("created"):
            fixed += 1
        elif "error" in result.get("reason", ""):
            still_error += 1

    return {"retried": retried, "fixed": fixed, "still_error": still_error}

