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
