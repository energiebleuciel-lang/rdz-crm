"""
RDZ CRM - Billing & Pricing Engine (Phase A)

Collections:
  products, client_pricing, client_product_pricing,
  billing_credits, prepayment_balances, billing_ledger, invoices

Rules:
  billable = delivery.status=sent AND outcome=accepted
  LB facturé au même prix qu'un lead (1 unité)
  Ledger = snapshot immutable (prix/remise copiés au build-ledger)
  Invoice frozen = immutable
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


def _parse_week(week_str: str):
    try:
        parts = week_str.split("-W")
        if len(parts) != 2:
            raise HTTPException(400, f"Invalid week format: {week_str}. Expected YYYY-W##")
        year, wn = int(parts[0]), int(parts[1])
        start = datetime.fromisocalendar(year, wn, 1).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        return start.isoformat(), end.isoformat()
    except ValueError as e:
        raise HTTPException(400, f"Invalid week: {week_str}. {str(e)}")


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
        gp = {"client_id": client_id, "discount_pct_global": 0}
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
        {"$set": {"client_id": client_id, "discount_pct_global": data.discount_pct_global, "updated_at": now_iso()}},
        upsert=True,
    )
    await log_event("pricing_update", "client", client_id, user=user.get("email"),
                     details={"discount_pct_global": data.discount_pct_global})
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

    existing = await db.client_product_pricing.find_one(
        {"client_id": client_id, "product_code": pc}
    )
    if existing:
        await db.client_product_pricing.update_one(
            {"client_id": client_id, "product_code": pc}, {"$set": doc}
        )
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = now_iso()
        await db.client_product_pricing.insert_one(doc)
        doc.pop("_id", None)

    if data.billing_mode == "PREPAID":
        bal = await db.prepayment_balances.find_one(
            {"client_id": client_id, "product_code": pc}
        )
        if not bal:
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
async def delete_product_pricing(
    client_id: str, product_code: str,
    user: dict = Depends(get_current_user)
):
    r = await db.client_product_pricing.delete_one(
        {"client_id": client_id, "product_code": product_code.upper()}
    )
    if r.deleted_count == 0:
        raise HTTPException(404, "Product pricing not found")
    await log_event("pricing_delete", "client", client_id, user=user.get("email"),
                     details={"product": product_code})
    return {"success": True}


# ═══════════════════════════════════════════════════
# BILLING CREDITS (free units / offers)
# ═══════════════════════════════════════════════════

class CreditCreate(BaseModel):
    product_code: Optional[str] = None
    week_key: str
    quantity_units_free: int
    reason: str
    note: str = ""


@router.get("/clients/{client_id}/credits")
async def list_credits(
    client_id: str, week_key: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    q = {"client_id": client_id}
    if week_key:
        q["week_key"] = week_key
    credits = await db.billing_credits.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"credits": credits, "count": len(credits)}


@router.post("/clients/{client_id}/credits")
async def add_credit(
    client_id: str, data: CreditCreate,
    user: dict = Depends(get_current_user)
):
    if data.reason not in CREDIT_REASONS:
        raise HTTPException(400, f"reason must be one of {CREDIT_REASONS}")
    doc = {
        "id": str(uuid.uuid4()), "client_id": client_id,
        "product_code": data.product_code.upper() if data.product_code else None,
        "week_key": data.week_key, "quantity_units_free": data.quantity_units_free,
        "reason": data.reason, "note": data.note,
        "created_by": user.get("email"), "created_at": now_iso(),
        "applied_invoice_id": None,
    }
    await db.billing_credits.insert_one(doc)
    doc.pop("_id", None)
    await log_event("credit_added", "client", client_id, user=user.get("email"),
                     details={"product": data.product_code, "week": data.week_key,
                              "units_free": data.quantity_units_free, "reason": data.reason})
    return {"success": True, "credit": doc}


@router.delete("/clients/{client_id}/credits/{credit_id}")
async def delete_credit(
    client_id: str, credit_id: str,
    user: dict = Depends(get_current_user)
):
    c = await db.billing_credits.find_one({"id": credit_id, "client_id": client_id})
    if not c:
        raise HTTPException(404, "Credit not found")
    if c.get("applied_invoice_id"):
        raise HTTPException(400, "Cannot delete credit applied to invoice")
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
async def add_prepayment_units(
    client_id: str, data: PrepaymentAddUnits,
    user: dict = Depends(get_current_user)
):
    pc = data.product_code.upper()
    await db.prepayment_balances.update_one(
        {"client_id": client_id, "product_code": pc},
        {"$inc": {"units_purchased_total": data.units_to_add, "units_remaining": data.units_to_add},
         "$set": {"updated_at": now_iso()},
         "$setOnInsert": {"client_id": client_id, "product_code": pc, "units_delivered_total": 0}},
        upsert=True,
    )
    bal = await db.prepayment_balances.find_one(
        {"client_id": client_id, "product_code": pc}, {"_id": 0}
    )
    await log_event("prepayment_units_added", "client", client_id, user=user.get("email"),
                     details={"product": pc, "units_added": data.units_to_add,
                              "remaining": bal.get("units_remaining"), "note": data.note})
    return {"success": True, "balance": bal}


# ═══════════════════════════════════════════════════
# BILLING WEEK DASHBOARD
# ═══════════════════════════════════════════════════

@router.get("/billing/week")
async def billing_week_dashboard(
    week_key: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    wk = week_key or _current_week_key()
    ws, we = _parse_week(wk)

    # Clients
    all_clients = await db.clients.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "entity": 1}).to_list(500)
    cmap = {c["id"]: c for c in all_clients}

    # Deliveries
    deliveries = await db.deliveries.find(
        {"created_at": {"$gte": ws, "$lt": we}},
        {"_id": 0, "id": 1, "lead_id": 1, "client_id": 1, "commande_id": 1,
         "produit": 1, "status": 1, "outcome": 1, "is_lb": 1},
    ).to_list(50000)

    grp = defaultdict(lambda: {"leads": 0, "lb": 0, "sent": 0,
                                "billable": 0, "billable_leads": 0, "billable_lb": 0,
                                "rejected": 0, "removed": 0})
    for d in deliveries:
        k = f"{d['client_id']}:{d.get('produit', '')}"
        is_lb = d.get("is_lb", False)
        grp[k]["lb" if is_lb else "leads"] += 1
        outcome = d.get("outcome") or "accepted"
        if d.get("status") == "sent":
            grp[k]["sent"] += 1
            if outcome == "accepted":
                grp[k]["billable"] += 1
                grp[k]["billable_lb" if is_lb else "billable_leads"] += 1
        if outcome == "rejected":
            grp[k]["rejected"] += 1
        elif outcome == "removed":
            grp[k]["removed"] += 1

    # Pricing maps
    all_pp = await db.client_product_pricing.find({}, {"_id": 0}).to_list(5000)
    pp_map = {f"{p['client_id']}:{p['product_code']}": p for p in all_pp}
    all_gp = await db.client_pricing.find({}, {"_id": 0}).to_list(500)
    gp_map = {g["client_id"]: g for g in all_gp}

    # Credits
    credits = await db.billing_credits.find({"week_key": wk}, {"_id": 0}).to_list(500)
    cr_prod = defaultdict(int)
    cr_global = defaultdict(int)
    for c in credits:
        if c.get("product_code"):
            cr_prod[f"{c['client_id']}:{c['product_code']}"] += c["quantity_units_free"]
        else:
            cr_global[c["client_id"]] += c["quantity_units_free"]

    # Invoices
    invs = await db.invoices.find({"week_key": wk}, {"_id": 0}).to_list(500)
    inv_map = {f"{i['client_id']}:{i.get('product_code', '')}": i for i in invs}

    # Prepay
    prepay_raw = await db.prepayment_balances.find({}, {"_id": 0}).to_list(500)
    prepay_map = {f"{p['client_id']}:{p['product_code']}": p for p in prepay_raw}

    weekly_rows, prepaid_rows = [], []
    inv_totals = {"units_billable": 0, "units_free": 0, "gross": 0, "net": 0}

    for key, s in sorted(grp.items()):
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue
        cid, pc = parts
        cl = cmap.get(cid, {})
        pp = pp_map.get(key)
        gd = gp_map.get(cid, {}).get("discount_pct_global", 0)

        bmode = pp.get("billing_mode", "WEEKLY_INVOICE") if pp else "WEEKLY_INVOICE"
        uprice = pp.get("unit_price_eur", 0) if pp else 0
        disc = pp.get("discount_pct", gd) if pp else gd
        pmissing = not pp or uprice <= 0

        total_credits = cr_prod.get(key, 0) + cr_global.get(cid, 0)
        ufree = min(total_credits, s["billable"])
        uinv = max(0, s["billable"] - ufree)
        gross = round(uinv * uprice, 2)
        net_val = round(gross * (1 - disc / 100), 2)

        inv = inv_map.get(key)

        row = {
            "client_id": cid, "client_name": cl.get("name", ""), "entity": cl.get("entity", ""),
            "product_code": pc, "billing_mode": bmode, "pricing_missing": pmissing,
            "unit_price_eur": uprice, "discount_pct": disc,
            "units_leads": s["billable_leads"], "units_lb": s["billable_lb"],
            "units_total_delivered": s["leads"] + s["lb"],
            "units_billable": s["billable"], "units_rejected": s["rejected"],
            "units_removed": s["removed"],
            "units_free_applied": ufree, "units_invoiced": uinv,
            "gross_total": gross, "discount_amount": round(gross - net_val, 2), "net_total": net_val,
            "invoice_status": inv.get("status") if inv else None,
            "invoice_id": inv.get("id") if inv else None,
            "invoice_number": inv.get("invoice_number") if inv else None,
        }

        if bmode == "PREPAID":
            b = prepay_map.get(key, {})
            row["prepaid_remaining"] = b.get("units_remaining", 0)
            row["prepaid_purchased"] = b.get("units_purchased_total", 0)
            row["prepaid_delivered"] = b.get("units_delivered_total", 0)
            row["prepaid_status"] = (
                "BLOCKED" if b.get("units_remaining", 0) <= 0
                else "LOW" if b.get("units_remaining", 0) <= 10
                else "OK"
            )
            prepaid_rows.append(row)
        else:
            weekly_rows.append(row)
            inv_totals["units_billable"] += s["billable"]
            inv_totals["units_free"] += ufree
            inv_totals["gross"] += gross
            inv_totals["net"] += net_val

    inv_totals["gross"] = round(inv_totals["gross"], 2)
    inv_totals["net"] = round(inv_totals["net"], 2)

    leads_produced = await db.leads.count_documents({"created_at": {"$gte": ws, "$lt": we}})

    return {
        "week_key": wk,
        "summary": {
            "leads_produced": leads_produced,
            "units_delivered": sum(s["leads"] + s["lb"] for s in grp.values()),
            "units_billable": sum(s["billable"] for s in grp.values()),
            "units_non_billable": sum(s["rejected"] + s["removed"] for s in grp.values()),
        },
        "totals_invoice": inv_totals,
        "weekly_invoice": weekly_rows,
        "prepaid": prepaid_rows,
    }


# ═══════════════════════════════════════════════════
# BUILD LEDGER
# ═══════════════════════════════════════════════════

@router.post("/billing/week/{week_key}/build-ledger")
async def build_ledger(week_key: str, user: dict = Depends(get_current_user)):
    ws, we = _parse_week(week_key)

    frozen = await db.invoices.find_one(
        {"week_key": week_key, "status": {"$in": ["frozen", "sent", "paid"]}}
    )
    if frozen:
        raise HTTPException(
            400, f"Cannot rebuild ledger: invoice {frozen.get('invoice_number')} is {frozen.get('status')}"
        )

    deleted = await db.billing_ledger.delete_many({"week_key": week_key})

    deliveries = await db.deliveries.find(
        {"created_at": {"$gte": ws, "$lt": we}}, {"_id": 0}
    ).to_list(50000)

    lead_ids = list({d["lead_id"] for d in deliveries})
    lead_dept = {}
    for i in range(0, len(lead_ids), 5000):
        chunk = lead_ids[i : i + 5000]
        for ld in await db.leads.find({"id": {"$in": chunk}}, {"_id": 0, "id": 1, "departement": 1}).to_list(len(chunk)):
            lead_dept[ld["id"]] = ld.get("departement", "??")

    all_pp = await db.client_product_pricing.find({}, {"_id": 0}).to_list(5000)
    pp_map = {f"{p['client_id']}:{p['product_code']}": p for p in all_pp}
    all_gp = await db.client_pricing.find({}, {"_id": 0}).to_list(500)
    gp_map = {g["client_id"]: g for g in all_gp}

    entries = []
    for d in deliveries:
        outcome = d.get("outcome") or "accepted"
        billable = d.get("status") == "sent" and outcome == "accepted"
        cid = d.get("client_id", "")
        pc = d.get("produit", "")
        pkey = f"{cid}:{pc}"

        pp = pp_map.get(pkey)
        gp = gp_map.get(cid, {})

        uprice = pp.get("unit_price_eur", 0) if pp else 0
        disc = pp.get("discount_pct", gp.get("discount_pct_global", 0)) if pp else gp.get("discount_pct_global", 0)
        bmode = pp.get("billing_mode", "WEEKLY_INVOICE") if pp else "WEEKLY_INVOICE"
        psource = "client_product_pricing" if pp else ("client_pricing_global" if gp.get("discount_pct_global") else "none")

        agross = round(uprice, 2) if billable else 0
        anet = round(agross * (1 - disc / 100), 2) if billable else 0

        entries.append({
            "id": str(uuid.uuid4()), "week_key": week_key,
            "client_id": cid, "order_id": d.get("commande_id", ""),
            "delivery_id": d.get("id", ""), "lead_id": d.get("lead_id", ""),
            "product_code": pc, "dept": lead_dept.get(d.get("lead_id", ""), "??"),
            "unit_type": "lb" if d.get("is_lb") else "lead",
            "outcome": outcome, "is_billable": billable,
            "unit_price_eur_snapshot": uprice, "discount_pct_snapshot": disc,
            "billing_mode_snapshot": bmode, "pricing_source": psource,
            "amount_gross_eur": agross, "amount_net_eur": anet,
            "created_at": now_iso(), "source_event_id": None,
        })

    if entries:
        await db.billing_ledger.insert_many(entries)
        for e in entries:
            e.pop("_id", None)

    await log_event("ledger_built", "billing", week_key, user=user.get("email"),
                     details={"entries": len(entries), "deleted_previous": deleted.deleted_count})

    return {"success": True, "week_key": week_key,
            "entries_created": len(entries), "entries_deleted_previous": deleted.deleted_count}


# ═══════════════════════════════════════════════════
# GENERATE INVOICES
# ═══════════════════════════════════════════════════

@router.post("/billing/week/{week_key}/generate-invoices")
async def generate_invoices(week_key: str, user: dict = Depends(get_current_user)):
    lc = await db.billing_ledger.count_documents({"week_key": week_key})
    if lc == 0:
        raise HTTPException(400, "No ledger entries. Run build-ledger first.")

    ledger = await db.billing_ledger.find(
        {"week_key": week_key, "is_billable": True}, {"_id": 0}
    ).to_list(50000)

    groups = defaultdict(list)
    for e in ledger:
        groups[f"{e['client_id']}:{e['product_code']}"].append(e)

    credits = await db.billing_credits.find({"week_key": week_key}, {"_id": 0}).to_list(500)
    cr_prod = defaultdict(int)
    cr_global = defaultdict(int)
    for c in credits:
        if c.get("product_code"):
            cr_prod[f"{c['client_id']}:{c['product_code']}"] += c["quantity_units_free"]
        else:
            cr_global[c["client_id"]] += c["quantity_units_free"]

    cnames = {c["id"]: c["name"] for c in await db.clients.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}

    last_inv = await db.invoices.find_one({}, {"_id": 0, "invoice_number": 1}, sort=[("created_at", -1)])
    counter = 1
    if last_inv and last_inv.get("invoice_number"):
        try:
            counter = int(last_inv["invoice_number"].split("-")[-1]) + 1
        except ValueError:
            pass

    created = []
    for key, entries in sorted(groups.items()):
        cid, pc = key.split(":", 1)

        frozen_inv = await db.invoices.find_one(
            {"week_key": week_key, "client_id": cid, "product_code": pc,
             "status": {"$in": ["frozen", "sent", "paid"]}}
        )
        if frozen_inv:
            continue

        u_leads = sum(1 for e in entries if e["unit_type"] == "lead")
        u_lb = sum(1 for e in entries if e["unit_type"] == "lb")
        u_total = u_leads + u_lb

        total_credits = cr_prod.get(key, 0) + cr_global.get(cid, 0)
        u_free = min(total_credits, u_total)
        u_inv = max(0, u_total - u_free)

        uprice = entries[0]["unit_price_eur_snapshot"] if entries else 0
        disc = entries[0]["discount_pct_snapshot"] if entries else 0
        bmode = entries[0].get("billing_mode_snapshot", "WEEKLY_INVOICE")

        gross = round(u_inv * uprice, 2)
        disc_amt = round(gross * disc / 100, 2)
        net_val = round(gross - disc_amt, 2)

        await db.invoices.delete_many(
            {"week_key": week_key, "client_id": cid, "product_code": pc, "status": "draft"}
        )

        inv_num = f"INV-{week_key}-{counter:04d}"
        counter += 1

        inv = {
            "id": str(uuid.uuid4()), "invoice_number": inv_num,
            "week_key": week_key, "client_id": cid,
            "client_name": cnames.get(cid, ""), "product_code": pc,
            "billing_mode": bmode, "status": "draft",
            "generated_at": now_iso(),
            "units_leads": u_leads, "units_lb": u_lb, "units_total": u_total,
            "units_free_applied": u_free, "units_invoiced": u_inv,
            "unit_price_eur": uprice, "discount_pct": disc,
            "gross_total": gross, "discount_total": disc_amt, "net_total": net_val,
            "notes": "", "pdf_url": None,
            "sent_at": None, "paid_at": None, "frozen_at": None,
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.invoices.insert_one(inv)
        inv.pop("_id", None)
        created.append(inv)

    await log_event("invoices_generated", "billing", week_key, user=user.get("email"),
                     details={"count": len(created)})
    return {"success": True, "week_key": week_key,
            "invoices_created": len(created), "invoices": created}


# ═══════════════════════════════════════════════════
# INVOICES LIST + ACTIONS
# ═══════════════════════════════════════════════════

@router.get("/invoices")
async def list_invoices(
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
    invs = await db.invoices.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"invoices": invs, "count": len(invs)}


@router.post("/invoices/{invoice_id}/freeze")
async def freeze_invoice(invoice_id: str, user: dict = Depends(get_current_user)):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv["status"] != "draft":
        raise HTTPException(400, f"Cannot freeze: status is '{inv['status']}', must be draft")
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "frozen", "frozen_at": now_iso(), "updated_at": now_iso()}},
    )
    await log_event("invoice_frozen", "invoice", invoice_id, user=user.get("email"),
                     details={"invoice_number": inv.get("invoice_number"),
                              "client_id": inv.get("client_id"), "net_total": inv.get("net_total")})
    return {"success": True, "status": "frozen"}


@router.post("/invoices/{invoice_id}/mark-sent")
async def mark_invoice_sent(invoice_id: str, user: dict = Depends(get_current_user)):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv["status"] != "frozen":
        raise HTTPException(400, f"Cannot send: status is '{inv['status']}', must be frozen")
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "sent", "sent_at": now_iso(), "updated_at": now_iso()}},
    )
    await log_event("invoice_sent", "invoice", invoice_id, user=user.get("email"),
                     details={"invoice_number": inv.get("invoice_number")})
    return {"success": True, "status": "sent"}


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(invoice_id: str, user: dict = Depends(get_current_user)):
    inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv["status"] not in ("sent", "frozen"):
        raise HTTPException(400, f"Cannot mark paid from '{inv['status']}'")
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": "paid", "paid_at": now_iso(), "updated_at": now_iso()}},
    )
    await log_event("invoice_paid", "invoice", invoice_id, user=user.get("email"),
                     details={"invoice_number": inv.get("invoice_number")})
    return {"success": True, "status": "paid"}
