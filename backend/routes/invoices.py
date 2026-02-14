"""
RDZ CRM - Invoice Routes (Billing v1)
Invoices: amount_ht, vat_rate, amount_ttc, invoice_number, status, dates.
Overdue dashboard: list clients with overdue invoices + total overdue TTC.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone, timedelta

from config import db, now_iso
from routes.auth import get_current_user
from services.permissions import (
    require_permission, validate_entity_access,
    get_entity_scope_from_request, build_entity_filter, enforce_write_entity,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])

INVOICE_STATUSES = ["draft", "sent", "paid", "overdue"]


class InvoiceCreate(BaseModel):
    client_id: str
    entity: Optional[str] = None  # Required only for super_admin BOTH scope
    amount_ht: float
    description: str = ""
    line_items: Optional[list] = None  # [{label, qty, unit_price_ht}]


class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    amount_ht: Optional[float] = None
    description: Optional[str] = None
    paid_at: Optional[str] = None


def _next_invoice_number(entity: str, seq: int) -> str:
    now = datetime.now(timezone.utc)
    return f"{entity}-{now.year}{now.month:02d}-{seq:04d}"


# ════════════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_invoices(
    request: Request,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(require_permission("billing.view"))
):
    """List invoices, filtered by entity scope."""
    scope = get_entity_scope_from_request(user, request)
    query = build_entity_filter(scope)
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id

    invoices = await db.invoices.find(
        query, {"_id": 0}
    ).sort("issued_at", -1).skip(skip).limit(limit).to_list(limit)

    total = await db.invoices.count_documents(query)
    return {"invoices": invoices, "count": len(invoices), "total": total}


@router.get("/overdue-dashboard")
async def overdue_dashboard(
    request: Request,
    user: dict = Depends(require_permission("billing.view"))
):
    """
    Overdue dashboard: clients with unpaid overdue invoices.
    Returns per-client totals + global total.
    """
    scope = get_entity_scope_from_request(user, request)
    base_filter = build_entity_filter(scope)

    # Mark overdue: any sent invoice past due_at
    now = now_iso()
    await db.invoices.update_many(
        {**base_filter, "status": "sent", "due_at": {"$lt": now}},
        {"$set": {"status": "overdue"}}
    )

    # Aggregate overdue per client
    match = {**base_filter, "status": "overdue"}
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$client_id",
            "entity": {"$first": "$entity"},
            "total_ht": {"$sum": "$amount_ht"},
            "total_ttc": {"$sum": "$amount_ttc"},
            "count": {"$sum": 1},
            "oldest_due": {"$min": "$due_at"},
        }},
        {"$sort": {"total_ttc": -1}}
    ]

    results = await db.invoices.aggregate(pipeline).to_list(500)

    # Enrich with client names
    clients_overdue = []
    grand_total_ttc = 0
    for r in results:
        client = await db.clients.find_one({"id": r["_id"]}, {"_id": 0, "name": 1})
        days_overdue = 0
        if r.get("oldest_due"):
            try:
                oldest = datetime.fromisoformat(r["oldest_due"].replace("Z", "+00:00"))
                days_overdue = (datetime.now(timezone.utc) - oldest).days
            except (ValueError, TypeError):
                pass
        clients_overdue.append({
            "client_id": r["_id"],
            "client_name": client.get("name", "?") if client else "?",
            "entity": r.get("entity", ""),
            "invoice_count": r["count"],
            "total_ht": round(r["total_ht"], 2),
            "total_ttc": round(r["total_ttc"], 2),
            "oldest_due": r.get("oldest_due"),
            "days_overdue": days_overdue,
        })
        grand_total_ttc += r["total_ttc"]

    return {
        "clients": clients_overdue,
        "total_overdue_ttc": round(grand_total_ttc, 2),
        "client_count": len(clients_overdue),
    }


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    user: dict = Depends(require_permission("billing.view"))
):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Facture non trouvée")
    return {"invoice": inv}


@router.post("")
async def create_invoice(
    data: InvoiceCreate,
    request: Request,
    user: dict = Depends(require_permission("billing.manage"))
):
    """Create a new invoice. TTC computed from client's vat_rate."""
    entity = enforce_write_entity(user, request, data.entity)

    client = await db.clients.find_one({"id": data.client_id, "entity": entity}, {"_id": 0})
    if not client:
        raise HTTPException(404, f"Client non trouvé dans l'entité {entity}")

    vat_rate = client.get("vat_rate", 20.0)
    amount_ttc = round(data.amount_ht * (1 + vat_rate / 100), 2)
    payment_days = client.get("payment_terms_days", 30)

    issued_at = now_iso()
    due_at = (datetime.now(timezone.utc) + timedelta(days=payment_days)).isoformat()

    # Generate invoice number
    count = await db.invoices.count_documents({"entity": entity}) + 1
    invoice_number = _next_invoice_number(entity, count)

    invoice = {
        "id": str(uuid.uuid4()),
        "invoice_number": invoice_number,
        "entity": entity,
        "client_id": data.client_id,
        "client_name": client.get("name", ""),
        "amount_ht": round(data.amount_ht, 2),
        "vat_rate": vat_rate,
        "amount_ttc": amount_ttc,
        "description": data.description,
        "line_items": data.line_items or [],
        "status": "draft",
        "issued_at": issued_at,
        "due_at": due_at,
        "paid_at": None,
        "created_at": issued_at,
        "created_by": user.get("email"),
    }

    await db.invoices.insert_one(invoice)
    invoice.pop("_id", None)
    return {"success": True, "invoice": invoice}


@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: InvoiceUpdate,
    user: dict = Depends(require_permission("billing.manage"))
):
    """Update invoice status or amount."""
    inv = await db.invoices.find_one({"id": invoice_id})
    if not inv:
        raise HTTPException(404, "Facture non trouvée")

    update = {}
    if data.status:
        if data.status not in INVOICE_STATUSES:
            raise HTTPException(400, f"Statut invalide: {data.status}")
        update["status"] = data.status
        if data.status == "paid":
            update["paid_at"] = data.paid_at or now_iso()
    if data.amount_ht is not None:
        vat = inv.get("vat_rate", 20.0)
        update["amount_ht"] = round(data.amount_ht, 2)
        update["amount_ttc"] = round(data.amount_ht * (1 + vat / 100), 2)
    if data.description is not None:
        update["description"] = data.description

    update["updated_at"] = now_iso()
    await db.invoices.update_one({"id": invoice_id}, {"$set": update})

    updated = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return {"success": True, "invoice": updated}


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    user: dict = Depends(require_permission("billing.manage"))
):
    """Mark invoice as sent (draft → sent)."""
    inv = await db.invoices.find_one({"id": invoice_id})
    if not inv:
        raise HTTPException(404, "Facture non trouvée")
    if inv.get("status") != "draft":
        raise HTTPException(400, f"Seule une facture draft peut être envoyée (actuel: {inv.get('status')})")

    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "sent", "sent_at": now_iso(), "updated_at": now_iso()}}
    )
    return {"success": True, "status": "sent"}


@router.post("/{invoice_id}/mark-paid")
async def mark_paid(
    invoice_id: str,
    user: dict = Depends(require_permission("billing.manage"))
):
    """Mark invoice as paid."""
    inv = await db.invoices.find_one({"id": invoice_id})
    if not inv:
        raise HTTPException(404, "Facture non trouvée")
    if inv.get("status") not in ("sent", "overdue"):
        raise HTTPException(400, f"Seule une facture sent/overdue peut être marquée payée")

    paid_at = now_iso()
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "paid", "paid_at": paid_at, "updated_at": paid_at}}
    )
    return {"success": True, "status": "paid", "paid_at": paid_at}
