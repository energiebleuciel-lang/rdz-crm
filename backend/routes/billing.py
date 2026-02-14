"""
RDZ CRM - Billing & Pricing Engine (Simplified)

Collections:
  products, client_pricing, client_product_pricing,
  billing_credits, prepayment_balances, billing_ledger, billing_records

Rules:
  billable = delivery.status=sent AND outcome=accepted
  LB facturé au même prix qu'un lead (1 unité)
  Ledger = snapshot immutable (prix/remise copiés au build-ledger)
  billing_records = suivi financier interne (pas de facture générée)
  Credits toujours sur order_id + product_code + week_key, non reportables
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from config import db, now_iso
from routes.auth import get_current_user
from services.event_logger import log_event

router = APIRouter(tags=["Billing"])

CREDIT_REASONS = ["fin_de_semaine", "geste_commercial", "retard", "qualite", "bug", "autre"]
BILLING_MODES = ["WEEKLY_INVOICE", "PREPAID"]
RECORD_STATUSES = ["not_invoiced", "invoiced", "paid", "overdue"]


def _parse_week(week_str: str):
    try:
        parts = week_str.split("-W")
        year, wn = int(parts[0]), int(parts[1])
        start = datetime.fromisocalendar(year, wn, 1).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        return start.isoformat(), end.isoformat()
    except Exception:
        raise HTTPException(400, f"Invalid week format: {week_str}. Expected YYYY-W##")


def _current_week_key():
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


# ═══════════════════════════════════════════════════
# PRODUCTS
# ═══════════════════════════════════════════════════

@router.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    products = await db.products.find({}, {"_id": 0}).to_list(100)
    if not products:
        for code, name in [("PV", "Panneaux Solaires"), ("PAC", "Pompe à Chaleur"), ("ITE", "Isolation Thermique")]:
            await db.products.insert_one({
                "code": code, "name": name, "active": True,
                "unit": "unit", "created_at": now_iso(), "updated_at": now_iso()
            })
        products = await db.products.find({}, {"_id": 0}).to_list(100)
    return {"products": products}


class ProductCreate(BaseModel):
    code: str
    name: str


@router.post("/products")
async def create_product(data: ProductCreate, user: dict = Depends(get_current_user)):
    code = data.code.upper()
    if await db.products.find_one({"code": code}):
        raise HTTPException(400, "Product code already exists")
    doc = {"code": code, "name": data.name, "active": True,
           "unit": "unit", "created_at": now_iso(), "updated_at": now_iso()}
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "product": doc}


# ═══════════════════════════════════════════════════
# CLIENT PRICING
# ═══════════════════════════════════════════════════

class GlobalPricingUpdate(BaseModel):
    discount_pct_global: float = 0
    tva_rate: float = 20.0


class ProductPricingUpsert(BaseModel):
    product_code: str
    unit_price_eur: float = 0
    discount_pct: float = 0
    billing_mode: str = "WEEKLY_INVOICE"
    active: bool = True
    valid_from: Optional[str] = None


@router.get("/clients/{client_id}/pricing")
async def get_client_pricing(client_id: str, user: dict = Depends(get_current_user)):
    gp = await db.client_pricing.find_one({"client_id": client_id}, {"_id": 0})
    if not gp:
        gp = {"client_id": client_id, "discount_pct_global": 0, "tva_rate": 20.0}
    products = await db.client_product_pricing.find(
        {"client_id": client_id}, {"_id": 0}
    ).to_list(50)
    return {"client_id": client_id, "global": gp, "products": products}


@router.put("/clients/{client_id}/pricing")
async def update_global_pricing(
    client_id: str, data: GlobalPricingUpdate,
    user: dict = Depends(get_current_user)
):
    await db.client_pricing.update_one(
        {"client_id": client_id},
        {"$set": {"client_id": client_id, "discount_pct_global": data.discount_pct_global,
                  "tva_rate": data.tva_rate, "updated_at": now_iso()}},
        upsert=True,
    )
    await log_event("pricing_update", "client", client_id, user=user.get("email"),
                     details={"discount_pct_global": data.discount_pct_global, "tva_rate": data.tva_rate})
    return {"success": True}


@router.post("/clients/{client_id}/pricing/product")
async def upsert_product_pricing(
    client_id: str, data: ProductPricingUpsert,
    user: dict = Depends(get_current_user)
):
    if data.billing_mode not in BILLING_MODES:
        raise HTTPException(400, f"billing_mode must be one of {BILLING_MODES}")
    pc = data.product_code.upper()
    doc = {
        "client_id": client_id, "product_code": pc,
        "unit_price_eur": data.unit_price_eur, "discount_pct": data.discount_pct,
        "billing_mode": data.billing_mode, "active": data.active,
        "valid_from": data.valid_from, "updated_at": now_iso(),
    }
    existing = await db.client_product_pricing.find_one({"client_id": client_id, "product_code": pc})
    if existing:
        await db.client_product_pricing.update_one({"client_id": client_id, "product_code": pc}, {"$set": doc})
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = now_iso()
        await db.client_product_pricing.insert_one(doc)
        doc.pop("_id", None)
    if data.billing_mode == "PREPAID":
        if not await db.prepayment_balances.find_one({"client_id": client_id, "product_code": pc}):
            await db.prepayment_balances.insert_one({
                "client_id": client_id, "product_code": pc,
                "units_purchased_total": 0, "units_delivered_total": 0,
                "units_remaining": 0, "updated_at": now_iso(),
            })
    await log_event("pricing_update", "client", client_id, user=user.get("email"),
                     details={"product": pc, "unit_price": data.unit_price_eur,
                              "discount_pct": data.discount_pct, "billing_mode": data.billing_mode})
    return {"success": True}


@router.delete("/clients/{client_id}/pricing/product/{product_code}")
async def delete_product_pricing(client_id: str, product_code: str, user: dict = Depends(get_current_user)):
    r = await db.client_product_pricing.delete_one({"client_id": client_id, "product_code": product_code.upper()})
    if r.deleted_count == 0:
        raise HTTPException(404, "Product pricing not found")
    await log_event("pricing_delete", "client", client_id, user=user.get("email"),
                     details={"product": product_code})
    return {"success": True}


# ═══════════════════════════════════════════════════
# BILLING CREDITS (offres — toujours sur order_id)
# ═══════════════════════════════════════════════════

class CreditCreate(BaseModel):
    order_id: str
    product_code: str
    week_key: str
    quantity_units_free: int
    reason: str
    note: str = ""


@router.get("/clients/{client_id}/credits")
async def list_credits(client_id: str, week_key: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"client_id": client_id}
    if week_key:
        q["week_key"] = week_key
    credits = await db.billing_credits.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"credits": credits, "count": len(credits)}


@router.post("/clients/{client_id}/credits")
async def add_credit(client_id: str, data: CreditCreate, user: dict = Depends(get_current_user)):
    if data.reason not in CREDIT_REASONS:
        raise HTTPException(400, f"reason must be one of {CREDIT_REASONS}")
    if not data.order_id:
        raise HTTPException(400, "order_id is required")
    if not data.product_code:
        raise HTTPException(400, "product_code is required")
    doc = {
        "id": str(uuid.uuid4()), "client_id": client_id,
        "order_id": data.order_id,
        "product_code": data.product_code.upper(),
        "week_key": data.week_key, "quantity_units_free": data.quantity_units_free,
        "reason": data.reason, "note": data.note,
        "created_by": user.get("email"), "created_at": now_iso(),
    }
    await db.billing_credits.insert_one(doc)
    doc.pop("_id", None)
    await log_event("credit_added", "client", client_id, user=user.get("email"),
                     details={"order_id": data.order_id, "product": data.product_code,
                              "week": data.week_key, "units_free": data.quantity_units_free, "reason": data.reason})
    return {"success": True, "credit": doc}


@router.delete("/clients/{client_id}/credits/{credit_id}")
async def delete_credit(client_id: str, credit_id: str, user: dict = Depends(get_current_user)):
    c = await db.billing_credits.find_one({"id": credit_id, "client_id": client_id})
    if not c:
        raise HTTPException(404, "Credit not found")
    await db.billing_credits.delete_one({"id": credit_id})
    await log_event("credit_deleted", "client", client_id, user=user.get("email"),
                     details={"credit_id": credit_id})
    return {"success": True}


# ═══════════════════════════════════════════════════
# PREPAYMENT BALANCES
# ═══════════════════════════════════════════════════

class PrepaymentAddUnits(BaseModel):
    product_code: str
    units_to_add: int
    note: str = ""


@router.get("/clients/{client_id}/prepayment")
async def get_prepayment(client_id: str, user: dict = Depends(get_current_user)):
    balances = await db.prepayment_balances.find({"client_id": client_id}, {"_id": 0}).to_list(50)
    return {"client_id": client_id, "balances": balances}


@router.post("/clients/{client_id}/prepayment/add-units")
async def add_prepayment_units(client_id: str, data: PrepaymentAddUnits, user: dict = Depends(get_current_user)):
    pc = data.product_code.upper()
    await db.prepayment_balances.update_one(
        {"client_id": client_id, "product_code": pc},
        {"$inc": {"units_purchased_total": data.units_to_add, "units_remaining": data.units_to_add},
         "$set": {"updated_at": now_iso()},
         "$setOnInsert": {"client_id": client_id, "product_code": pc, "units_delivered_total": 0}},
        upsert=True,
    )
    bal = await db.prepayment_balances.find_one({"client_id": client_id, "product_code": pc}, {"_id": 0})
    await log_event("prepayment_units_added", "client", client_id, user=user.get("email"),
                     details={"product": pc, "units_added": data.units_to_add,
                              "remaining": bal.get("units_remaining"), "note": data.note})
    return {"success": True, "balance": bal}


# ═══════════════════════════════════════════════════
# BILLING WEEK DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/billing/week")
async def billing_week_dashboard(week_key: Optional[str] = None, user: dict = Depends(get_current_user)):
    wk = week_key or _current_week_key()
    ws, we = _parse_week(wk)

    # Check if billing_records exist
    records = await db.billing_records.find({"week_key": wk}, {"_id": 0}).to_list(5000)
    has_records = len(records) > 0

    # Always compute summary from deliveries (live)
    cmap = {c["id"]: c for c in await db.clients.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "entity": 1}).to_list(500)}
    deliveries = await db.deliveries.find(
        {"created_at": {"$gte": ws, "$lt": we}},
        {"_id": 0, "id": 1, "client_id": 1, "produit": 1, "status": 1, "outcome": 1, "is_lb": 1},
    ).to_list(50000)

    total_delivered = len(deliveries)
    total_billable = sum(1 for d in deliveries if d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted")
    total_nonbill = sum(1 for d in deliveries if (d.get("outcome") or "accepted") in ("rejected", "removed"))
    total_leads = sum(1 for d in deliveries if not d.get("is_lb", False))
    total_lb = sum(1 for d in deliveries if d.get("is_lb", False))
    billable_leads = sum(1 for d in deliveries if d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted" and not d.get("is_lb", False))
    billable_lb = sum(1 for d in deliveries if d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted" and d.get("is_lb", False))
    leads_produced = await db.leads.count_documents({"created_at": {"$gte": ws, "$lt": we}})

    # Prepaid data
    prepay_raw = await db.prepayment_balances.find({}, {"_id": 0}).to_list(500)
    prepay_map = {f"{p['client_id']}:{p['product_code']}": p for p in prepay_raw}
    all_pp = await db.client_product_pricing.find({}, {"_id": 0}).to_list(5000)
    pp_map = {f"{p['client_id']}:{p['product_code']}": p for p in all_pp}

    if has_records:
        # Use billing_records for the table
        weekly_rows = []
        prepaid_rows = []
        totals = {"units_billable": 0, "units_free": 0, "net_ht": 0, "ttc": 0, "units_leads": 0, "units_lb": 0}

        for r in records:
            bmode = r.get("billing_mode", "WEEKLY_INVOICE")
            r["client_name"] = r.get("client_name") or cmap.get(r.get("client_id"), {}).get("name", "")
            r["entity"] = cmap.get(r.get("client_id"), {}).get("entity", "")
            r["pricing_missing"] = r.get("unit_price_ht_snapshot", 0) <= 0

            if bmode == "PREPAID":
                b = prepay_map.get(f"{r['client_id']}:{r['product_code']}", {})
                r["prepaid_remaining"] = b.get("units_remaining", 0)
                r["prepaid_purchased"] = b.get("units_purchased_total", 0)
                r["prepaid_delivered"] = b.get("units_delivered_total", 0)
                r["prepaid_status"] = "BLOCKED" if b.get("units_remaining", 0) <= 0 else "LOW" if b.get("units_remaining", 0) <= 10 else "OK"
                r["units_leads"] = r.get("units_leads", 0)
                r["units_lb"] = r.get("units_lb", 0)
                prepaid_rows.append(r)
            else:
                weekly_rows.append(r)
                totals["units_billable"] += r.get("units_billable", 0)
                totals["units_free"] += r.get("units_free", 0)
                totals["units_leads"] += r.get("units_leads", 0)
                totals["units_lb"] += r.get("units_lb", 0)
                totals["net_ht"] += r.get("net_total_ht", 0)
                totals["ttc"] += r.get("total_ttc_expected", 0)

        totals["net_ht"] = round(totals["net_ht"], 2)
        totals["ttc"] = round(totals["ttc"], 2)
    else:
        # Compute preview from deliveries
        grp = defaultdict(lambda: {"leads": 0, "lb": 0, "billable": 0, "billable_leads": 0, "billable_lb": 0, "rejected": 0, "removed": 0})
        for d in deliveries:
            k = f"{d['client_id']}:{d.get('produit', '')}"
            is_lb = d.get("is_lb", False)
            grp[k]["lb" if is_lb else "leads"] += 1
            outcome = d.get("outcome") or "accepted"
            if d.get("status") == "sent":
                if outcome == "accepted":
                    grp[k]["billable"] += 1
                    grp[k]["billable_lb" if is_lb else "billable_leads"] += 1
            if outcome == "rejected":
                grp[k]["rejected"] += 1
            elif outcome == "removed":
                grp[k]["removed"] += 1

        all_gp = await db.client_pricing.find({}, {"_id": 0}).to_list(500)
        gp_map = {g["client_id"]: g for g in all_gp}

        weekly_rows, prepaid_rows = [], []
        totals = {"units_billable": 0, "units_free": 0, "net_ht": 0, "ttc": 0, "units_leads": 0, "units_lb": 0}

        for key, s in sorted(grp.items()):
            parts = key.split(":", 1)
            if len(parts) != 2:
                continue
            cid, pc = parts
            cl = cmap.get(cid, {})
            pp = pp_map.get(key)
            gd = gp_map.get(cid, {}).get("discount_pct_global", 0)
            tva = gp_map.get(cid, {}).get("tva_rate", 20.0)

            bmode = pp.get("billing_mode", "WEEKLY_INVOICE") if pp else "WEEKLY_INVOICE"
            uprice = pp.get("unit_price_eur", 0) if pp else 0
            disc = pp.get("discount_pct", gd) if pp else gd
            pmissing = not pp or uprice <= 0

            gross = round(s["billable"] * uprice, 2)
            net_val = round(gross * (1 - disc / 100), 2)
            tva_amt = round(net_val * tva / 100, 2)
            ttc = round(net_val + tva_amt, 2)

            row = {
                "client_id": cid, "client_name": cl.get("name", ""), "entity": cl.get("entity", ""),
                "product_code": pc, "billing_mode": bmode, "pricing_missing": pmissing,
                "units_billable": s["billable"], "units_leads": s["billable_leads"], "units_lb": s["billable_lb"],
                "units_free": 0, "units_invoiced": s["billable"],
                "unit_price_ht_snapshot": uprice, "discount_pct_snapshot": disc,
                "net_total_ht": net_val, "vat_rate_snapshot": tva, "vat_amount": tva_amt,
                "total_ttc_expected": ttc,
                "status": "not_invoiced", "is_preview": True,
            }

            if bmode == "PREPAID":
                b = prepay_map.get(key, {})
                row["prepaid_remaining"] = b.get("units_remaining", 0)
                row["prepaid_purchased"] = b.get("units_purchased_total", 0)
                row["prepaid_delivered"] = b.get("units_delivered_total", 0)
                row["prepaid_status"] = "BLOCKED" if b.get("units_remaining", 0) <= 0 else "LOW" if b.get("units_remaining", 0) <= 10 else "OK"
                prepaid_rows.append(row)
            else:
                weekly_rows.append(row)
                totals["units_billable"] += s["billable"]
                totals["units_leads"] += s["billable_leads"]
                totals["units_lb"] += s["billable_lb"]
                totals["net_ht"] += net_val
                totals["ttc"] += ttc

        totals["net_ht"] = round(totals["net_ht"], 2)
        totals["ttc"] = round(totals["ttc"], 2)

    return {
        "week_key": wk,
        "has_records": has_records,
        "summary": {
            "leads_produced": leads_produced,
            "units_delivered": total_delivered,
            "units_billable": total_billable,
            "units_non_billable": total_nonbill,
            "total_leads": total_leads,
            "total_lb": total_lb,
            "billable_leads": billable_leads,
            "billable_lb": billable_lb,
        },
        "totals": totals,
        "weekly_invoice": weekly_rows,
        "prepaid": prepaid_rows,
    }


# ═══════════════════════════════════════════════════
# BUILD LEDGER + BILLING RECORDS
# ═══════════════════════════════════════════════════

@router.post("/billing/week/{week_key}/build-ledger")
async def build_ledger(week_key: str, user: dict = Depends(get_current_user)):
    ws, we = _parse_week(week_key)

    # Block if any billing_record is invoiced/paid
    locked = await db.billing_records.find_one(
        {"week_key": week_key, "status": {"$in": ["invoiced", "paid"]}}
    )
    if locked:
        raise HTTPException(400, f"Cannot rebuild: record for {locked.get('client_name')} / {locked.get('product_code')} is '{locked.get('status')}'")

    # Preserve external tracking from existing records
    existing_records = {}
    async for r in db.billing_records.find({"week_key": week_key}, {"_id": 0}):
        existing_records[f"{r['client_id']}:{r['product_code']}:{r.get('order_id', '')}"] = {
            "external_invoice_number": r.get("external_invoice_number"),
            "external_invoice_ttc": r.get("external_invoice_ttc"),
            "issued_at": r.get("issued_at"),
            "due_date": r.get("due_date"),
            "paid_at": r.get("paid_at"),
            "status": r.get("status", "not_invoiced"),
        }

    # Delete existing ledger + records
    del_ledger = await db.billing_ledger.delete_many({"week_key": week_key})
    await db.billing_records.delete_many({"week_key": week_key})

    # Get all deliveries
    deliveries = await db.deliveries.find({"created_at": {"$gte": ws, "$lt": we}}, {"_id": 0}).to_list(50000)

    # Lead departments + entity
    lead_ids = list({d["lead_id"] for d in deliveries})
    lead_info = {}
    for i in range(0, len(lead_ids), 5000):
        chunk = lead_ids[i:i + 5000]
        for ld in await db.leads.find({"id": {"$in": chunk}}, {"_id": 0, "id": 1, "departement": 1, "entity": 1}).to_list(len(chunk)):
            lead_info[ld["id"]] = {"dept": ld.get("departement", "??"), "entity": ld.get("entity", "")}

    # Pricing maps
    all_pp = await db.client_product_pricing.find({}, {"_id": 0}).to_list(5000)
    pp_map = {f"{p['client_id']}:{p['product_code']}": p for p in all_pp}
    all_gp = await db.client_pricing.find({}, {"_id": 0}).to_list(500)
    gp_map = {g["client_id"]: g for g in all_gp}

    # Client names + entity
    client_map = {c["id"]: {"name": c["name"], "entity": c.get("entity", "")} for c in await db.clients.find({}, {"_id": 0, "id": 1, "name": 1, "entity": 1}).to_list(500)}

    # Credits map: key = client_id:product_code:order_id:week_key
    credits = await db.billing_credits.find({"week_key": week_key}, {"_id": 0}).to_list(500)
    credit_map = defaultdict(int)
    for c in credits:
        oid = c.get("order_id", "")  # Old credits may not have order_id
        pc = c.get("product_code", "")
        cid = c.get("client_id", "")
        if pc:  # Allow credits without order_id for backwards compatibility
            credit_map[f"{cid}:{pc}:{oid}"] += c["quantity_units_free"]

    # 1. Build ledger entries
    entries = []
    for d in deliveries:
        outcome = d.get("outcome") or "accepted"
        billable = d.get("status") == "sent" and outcome == "accepted"
        cid = d.get("client_id", "")
        pc = d.get("produit", "")
        pkey = f"{cid}:{pc}"
        pp = pp_map.get(pkey)
        gp = gp_map.get(cid, {})
        li = lead_info.get(d.get("lead_id", ""), {})

        uprice = pp.get("unit_price_eur", 0) if pp else 0
        disc = pp.get("discount_pct", gp.get("discount_pct_global", 0)) if pp else gp.get("discount_pct_global", 0)
        bmode = pp.get("billing_mode", "WEEKLY_INVOICE") if pp else "WEEKLY_INVOICE"
        tva = gp.get("tva_rate", 20.0)
        psource = "client_product_pricing" if pp else ("client_pricing_global" if gp.get("discount_pct_global") else "none")

        source_entity = li.get("entity", d.get("entity", ""))
        billing_entity = client_map.get(cid, {}).get("entity", "")

        agross = round(uprice, 2) if billable else 0
        anet = round(agross * (1 - disc / 100), 2) if billable else 0

        entries.append({
            "id": str(uuid.uuid4()), "week_key": week_key,
            "client_id": cid, "order_id": d.get("commande_id", ""),
            "delivery_id": d.get("id", ""), "lead_id": d.get("lead_id", ""),
            "product_code": pc, "dept": li.get("dept", "??"),
            "unit_type": "lb" if d.get("is_lb") else "lead",
            "source_entity": source_entity, "billing_entity": billing_entity,
            "outcome": outcome, "is_billable": billable,
            "unit_price_eur_snapshot": uprice, "discount_pct_snapshot": disc,
            "billing_mode_snapshot": bmode, "pricing_source": psource,
            "vat_rate_snapshot": tva,
            "amount_gross_eur": agross, "amount_net_eur": anet,
            "created_at": now_iso(), "source_event_id": None,
        })

    if entries:
        await db.billing_ledger.insert_many(entries)
        for e in entries:
            e.pop("_id", None)

    # 2. Aggregate into billing_records (per client + product + order + week)
    agg = defaultdict(lambda: {"leads": 0, "lb": 0, "billable": 0, "uprice": 0, "disc": 0, "bmode": "WEEKLY_INVOICE", "tva": 20.0, "source_entity": "", "billing_entity": ""})
    for e in entries:
        if not e["is_billable"]:
            continue
        rk = f"{e['client_id']}:{e['product_code']}:{e['order_id']}"
        agg[rk]["billable"] += 1
        agg[rk]["lb" if e["unit_type"] == "lb" else "leads"] += 1
        agg[rk]["uprice"] = e["unit_price_eur_snapshot"]
        agg[rk]["disc"] = e["discount_pct_snapshot"]
        agg[rk]["bmode"] = e["billing_mode_snapshot"]
        agg[rk]["tva"] = e.get("vat_rate_snapshot", 20.0)
        agg[rk]["source_entity"] = e.get("source_entity", "")
        agg[rk]["billing_entity"] = e.get("billing_entity", "")

    # Also include non-billable-only groups (for visibility)
    for e in entries:
        rk = f"{e['client_id']}:{e['product_code']}:{e['order_id']}"
        if rk not in agg:
            agg[rk]["uprice"] = e["unit_price_eur_snapshot"]
            agg[rk]["disc"] = e["discount_pct_snapshot"]
            agg[rk]["bmode"] = e["billing_mode_snapshot"]
            agg[rk]["tva"] = e.get("vat_rate_snapshot", 20.0)
            agg[rk]["source_entity"] = e.get("source_entity", "")
            agg[rk]["billing_entity"] = e.get("billing_entity", "")

    records_created = 0
    for rk, s in agg.items():
        parts = rk.split(":", 2)
        cid, pc, oid = parts[0], parts[1], parts[2] if len(parts) > 2 else ""

        ufree = min(credit_map.get(rk, 0), s["billable"])
        uinv = max(0, s["billable"] - ufree)
        gross = round(uinv * s["uprice"], 2)
        net_val = round(gross * (1 - s["disc"] / 100), 2)
        tva_amt = round(net_val * s["tva"] / 100, 2)
        ttc = round(net_val + tva_amt, 2)

        # Restore external tracking if existed
        ext = existing_records.get(rk, {})

        record = {
            "id": str(uuid.uuid4()), "week_key": week_key,
            "client_id": cid, "client_name": cnames.get(cid, ""),
            "product_code": pc, "order_id": oid,
            "billing_mode": s["bmode"],
            "units_billable": s["billable"], "units_leads": s["leads"], "units_lb": s["lb"],
            "units_free": ufree, "units_invoiced": uinv,
            "unit_price_ht_snapshot": s["uprice"], "discount_pct_snapshot": s["disc"],
            "net_total_ht": net_val, "vat_rate_snapshot": s["tva"],
            "vat_amount": tva_amt, "total_ttc_expected": ttc,
            "external_invoice_number": ext.get("external_invoice_number"),
            "external_invoice_ttc": ext.get("external_invoice_ttc"),
            "issued_at": ext.get("issued_at"), "due_date": ext.get("due_date"),
            "paid_at": ext.get("paid_at"),
            "status": ext.get("status", "not_invoiced"),
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.billing_records.insert_one(record)
        record.pop("_id", None)
        records_created += 1

    await log_event("ledger_built", "billing", week_key, user=user.get("email"),
                     details={"ledger_entries": len(entries), "billing_records": records_created,
                              "deleted_previous": del_ledger.deleted_count})

    return {"success": True, "week_key": week_key,
            "ledger_entries": len(entries), "billing_records_created": records_created}


# ═══════════════════════════════════════════════════
# BILLING RECORDS — LIST + EXTERNAL TRACKING
# ═══════════════════════════════════════════════════

@router.get("/billing/records")
async def list_billing_records(
    week_key: Optional[str] = None, client_id: Optional[str] = None,
    status: Optional[str] = None, user: dict = Depends(get_current_user),
):
    q = {}
    if week_key:
        q["week_key"] = week_key
    if client_id:
        q["client_id"] = client_id
    if status:
        q["status"] = status
    recs = await db.billing_records.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"records": recs, "count": len(recs)}


class BillingRecordUpdate(BaseModel):
    external_invoice_number: Optional[str] = None
    external_invoice_ttc: Optional[float] = None
    issued_at: Optional[str] = None
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    status: Optional[str] = None


@router.put("/billing/records/{record_id}")
async def update_billing_record(
    record_id: str, data: BillingRecordUpdate,
    user: dict = Depends(get_current_user),
):
    rec = await db.billing_records.find_one({"id": record_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Billing record not found")
    if data.status and data.status not in RECORD_STATUSES:
        raise HTTPException(400, f"status must be one of {RECORD_STATUSES}")

    update = {k: v for k, v in data.dict().items() if v is not None}
    update["updated_at"] = now_iso()

    await db.billing_records.update_one({"id": record_id}, {"$set": update})

    await log_event("billing_record_updated", "billing", record_id, user=user.get("email"),
                     details=update)
    return {"success": True}
