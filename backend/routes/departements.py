"""
RDZ CRM - Routes Départements (Pilotage industriel)

V1 = ALL uniquement (agrège ZR7 + MDL)

Endpoints:
- GET /api/departements/overview — Vue globale par (dept, produit)
- GET /api/departements/{dept}/detail — Drawer detail avec timeseries
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from config import db
from routes.auth import get_current_user
from services.permissions import require_permission

router = APIRouter(prefix="/departements", tags=["Departements"])


def _current_week_key():
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _parse_week(week_str: str):
    """Parse 'YYYY-W##' -> (start_iso, end_iso)"""
    parts = week_str.split("-W")
    year, wn = int(parts[0]), int(parts[1])
    start = datetime.fromisocalendar(year, wn, 1).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start.isoformat(), end.isoformat()


def _prev_week_key(week_str: str):
    parts = week_str.split("-W")
    year, wn = int(parts[0]), int(parts[1])
    start = datetime.fromisocalendar(year, wn, 1).replace(tzinfo=timezone.utc)
    prev = start - timedelta(days=7)
    iso = prev.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _delta_pct(cur, prev):
    if prev > 0:
        return round((cur - prev) / prev * 100, 1)
    return 100.0 if cur > 0 else 0.0


@router.get("/overview")
async def departements_overview(
    product: str = Query("ALL"),
    period: str = Query("week"),
    week: Optional[str] = None,
    departements: Optional[str] = None,
    client_id: Optional[str] = None,
    user: dict = Depends(require_permission("departements.view")),
):
    week_key = week or _current_week_key()
    prev_key = _prev_week_key(week_key)
    cur_start, cur_end = _parse_week(week_key)
    prev_start, prev_end = _parse_week(prev_key)

    if period == "day":
        now = datetime.now(timezone.utc)
        ds = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cur_start, cur_end = ds.isoformat(), (ds + timedelta(days=1)).isoformat()
        prev_start, prev_end = (ds - timedelta(days=1)).isoformat(), ds.isoformat()

    dept_filter = [d.strip() for d in departements.split(",")] if departements else None
    prod_match = {} if not product or product.upper() == "ALL" else {"produit": product.upper()}

    # --- 1. Active commandes ---
    cmd_q = {"active": True, **prod_match}
    if client_id:
        cmd_q["client_id"] = client_id
    active_cmds = await db.commandes.find(cmd_q, {"_id": 0}).to_list(2000)

    # Client names
    cids = list({c["client_id"] for c in active_cmds})
    cname_map = {}
    if cids:
        for cl in await db.clients.find({"id": {"$in": cids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(cids)):
            cname_map[cl["id"]] = cl["name"]

    # --- 2. Deliveries in period -> compute cmd_stats + dept_del_stats ---
    del_match = {"created_at": {"$gte": cur_start, "$lt": cur_end}}
    if prod_match:
        del_match.update(prod_match)
    deliveries = await db.deliveries.find(
        del_match, {"_id": 0, "lead_id": 1, "status": 1, "outcome": 1, "commande_id": 1, "produit": 1}
    ).to_list(50000)

    lead_ids = list({d["lead_id"] for d in deliveries})
    lead_dept_map = {}
    if lead_ids:
        for chunk_start in range(0, len(lead_ids), 5000):
            chunk = lead_ids[chunk_start:chunk_start + 5000]
            for ld in await db.leads.find({"id": {"$in": chunk}}, {"_id": 0, "id": 1, "departement": 1}).to_list(len(chunk)):
                lead_dept_map[ld["id"]] = ld.get("departement", "??")

    cmd_stats = defaultdict(lambda: {"sent": 0, "billable": 0, "rejected": 0, "removed": 0})
    dept_del = defaultdict(lambda: {"sent": 0, "billable": 0, "rejected": 0, "removed": 0})

    for d in deliveries:
        dept = lead_dept_map.get(d["lead_id"], "??")
        produit = d.get("produit", "")
        key = f"{dept}:{produit}"
        cid = d.get("commande_id", "")
        outcome = d.get("outcome") or "accepted"
        is_sent = d.get("status") == "sent"

        if is_sent:
            cmd_stats[cid]["sent"] += 1
            dept_del[key]["sent"] += 1
            if outcome == "accepted":
                cmd_stats[cid]["billable"] += 1
                dept_del[key]["billable"] += 1
        if outcome == "rejected":
            cmd_stats[cid]["rejected"] += 1
            dept_del[key]["rejected"] += 1
        elif outcome == "removed":
            cmd_stats[cid]["removed"] += 1
            dept_del[key]["removed"] += 1

    # --- 3. Coverage map (dept:produit -> covering clients) ---
    coverage = defaultdict(list)
    wildcard_cmds = defaultdict(list)
    inactive_coverage = set()
    inactive_wildcards = set()

    for cmd in active_cmds:
        cid_cmd = cmd["id"]
        produit = cmd.get("produit", "")
        cs = cmd_stats.get(cid_cmd, {"sent": 0, "billable": 0})
        quota = cmd.get("quota_semaine", 0)
        remaining = max(0, quota - cs["billable"]) if quota > 0 else -1

        info = {
            "client_id": cmd["client_id"],
            "name": cname_map.get(cmd["client_id"], ""),
            "commande_id": cid_cmd,
            "quota_week": quota,
            "billable_week": cs["billable"],
            "remaining_week": remaining,
            "order_ids": [cid_cmd],
        }

        if cmd.get("departements") == ["*"]:
            wildcard_cmds[produit].append(info)
        else:
            for dp in cmd.get("departements", []):
                coverage[f"{dp}:{produit}"].append(info)

    # Inactive commandes for inactive_blocked status
    inactive_q = {"active": False, **prod_match}
    for ic in await db.commandes.find(inactive_q, {"_id": 0, "departements": 1, "produit": 1}).to_list(2000):
        p = ic.get("produit", "")
        if ic.get("departements") == ["*"]:
            inactive_wildcards.add(p)
        else:
            for dp in ic.get("departements", []):
                inactive_coverage.add(f"{dp}:{p}")

    # --- 4. Produced current + prev ---
    lead_q = {**prod_match}
    if dept_filter:
        lead_q["departement"] = {"$in": dept_filter}

    async def _agg_produced(start, end):
        pipe = [
            {"$match": {**lead_q, "created_at": {"$gte": start, "$lt": end}}},
            {"$group": {"_id": {"d": "$departement", "p": {"$ifNull": ["$produit", "unknown"]}}, "c": {"$sum": 1}}},
        ]
        out = {}
        for r in await db.leads.aggregate(pipe).to_list(5000):
            d = r["_id"].get("d", "??")
            p = r["_id"].get("p", "unknown")
            if d and p and d != "??" and p != "unknown":
                out[f"{d}:{p}"] = r["c"]
        return out

    produced_cur, produced_prev = await _agg_produced(cur_start, cur_end), await _agg_produced(prev_start, prev_end)

    # --- 5. Merge results ---
    all_keys = set()
    all_keys.update(produced_cur.keys())
    all_keys.update(produced_prev.keys())
    all_keys.update(coverage.keys())
    all_keys.update(dept_del.keys())

    # Add wildcard dept keys (from produced) for wildcard commandes
    for k in list(all_keys):
        parts = k.split(":")
        if len(parts) == 2 and parts[1] in wildcard_cmds:
            pass  # already in set

    results = []
    for key in sorted(all_keys):
        parts = key.split(":")
        if len(parts) != 2:
            continue
        dept, produit = parts
        if dept == "??" or dept == "unknown":
            continue
        if dept_filter and dept not in dept_filter:
            continue

        pc = produced_cur.get(key, 0)
        pp = produced_prev.get(key, 0)
        ds = dept_del.get(key, {"sent": 0, "billable": 0, "rejected": 0, "removed": 0})
        covering = list(coverage.get(key, []))
        if produit in wildcard_cmds:
            covering.extend(wildcard_cmds[produit])

        if covering:
            qt = sum(c["quota_week"] for c in covering)
            unlim = any(c["remaining_week"] < 0 for c in covering)
            rem = sum(c["remaining_week"] for c in covering if c["remaining_week"] >= 0)
            status = "on_remaining" if (unlim or rem > 0) else "saturated"
            remaining = -1 if unlim else rem
        else:
            qt = 0
            remaining = 0
            if key in inactive_coverage or produit in inactive_wildcards:
                status = "inactive_blocked"
            else:
                status = "no_order"

        results.append({
            "departement": dept,
            "produit": produit,
            "produced_current": pc,
            "produced_prev": pp,
            "produced_delta_pct": _delta_pct(pc, pp),
            "billable_current": ds["billable"],
            "non_billable_current": ds["rejected"] + ds["removed"],
            "quota_week_total": qt,
            "remaining_week": remaining,
            "status": status,
            "clients_covering": covering,
        })

    return {
        "results": results,
        "count": len(results),
        "week": week_key,
        "period": period,
        "product": product,
    }


@router.get("/{dept}/detail")
async def dept_detail(
    dept: str,
    product: str = Query("ALL"),
    week: Optional[str] = None,
    user: dict = Depends(require_permission("departements.view")),
):
    week_key = week or _current_week_key()
    prod_match = {} if not product or product.upper() == "ALL" else {"produit": product.upper()}

    # Build 8-week range
    weeks = []
    wk = week_key
    for _ in range(8):
        weeks.append(wk)
        wk = _prev_week_key(wk)
    weeks.reverse()

    oldest_start, _ = _parse_week(weeks[0])
    _, newest_end = _parse_week(weeks[-1])

    # Produced per week (batch)
    prod_pipe = [
        {"$match": {"departement": dept, "created_at": {"$gte": oldest_start, "$lt": newest_end}, **prod_match}},
        {"$project": {"created_at": 1}},
    ]
    all_leads = await db.leads.aggregate(prod_pipe).to_list(50000)

    week_ranges = {}
    for w in weeks:
        ws, we = _parse_week(w)
        week_ranges[w] = (ws, we)

    weekly_produced = defaultdict(int)
    for ld in all_leads:
        ca = ld.get("created_at", "")
        for w, (ws, we) in week_ranges.items():
            if ws <= ca < we:
                weekly_produced[w] += 1
                break

    # Deliveries per week (batch)
    del_pipe_match = {"created_at": {"$gte": oldest_start, "$lt": newest_end}, **prod_match}
    all_dels = await db.deliveries.find(
        del_pipe_match, {"_id": 0, "lead_id": 1, "status": 1, "outcome": 1, "created_at": 1}
    ).to_list(50000)

    del_lead_ids = list({d["lead_id"] for d in all_dels})
    del_lead_dept = {}
    if del_lead_ids:
        for chunk_start in range(0, len(del_lead_ids), 5000):
            chunk = del_lead_ids[chunk_start:chunk_start + 5000]
            for ld in await db.leads.find({"id": {"$in": chunk}}, {"_id": 0, "id": 1, "departement": 1}).to_list(len(chunk)):
                del_lead_dept[ld["id"]] = ld.get("departement", "??")

    # Filter deliveries for this dept
    dept_dels = [d for d in all_dels if del_lead_dept.get(d["lead_id"]) == dept]

    weekly_del = defaultdict(lambda: {"billable": 0, "non_billable": 0, "sent": 0})
    for d in dept_dels:
        ca = d.get("created_at", "")
        outcome = d.get("outcome") or "accepted"
        for w, (ws, we) in week_ranges.items():
            if ws <= ca < we:
                if d.get("status") == "sent":
                    weekly_del[w]["sent"] += 1
                    if outcome == "accepted":
                        weekly_del[w]["billable"] += 1
                if outcome in ("rejected", "removed"):
                    weekly_del[w]["non_billable"] += 1
                break

    # Quota from active commandes covering this dept
    active_cmds = await db.commandes.find(
        {"active": True, **prod_match, "$or": [{"departements": {"$in": [dept]}}, {"departements": ["*"]}]},
        {"_id": 0},
    ).to_list(500)

    cmd_ids = [c["id"] for c in active_cmds]
    cids = list({c["client_id"] for c in active_cmds})
    cname_map = {}
    if cids:
        for cl in await db.clients.find({"id": {"$in": cids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(cids)):
            cname_map[cl["id"]] = cl["name"]

    quota_total = sum(c.get("quota_semaine", 0) for c in active_cmds)

    # Per-cmd billable for current week
    cur_start, cur_end = _parse_week(week_key)
    cmd_billable = defaultdict(int)
    for d in dept_dels:
        if d.get("created_at", "") >= cur_start and d.get("created_at", "") < cur_end:
            if d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted":
                pass  # We need commande_id here, but we didn't fetch it for dept_dels
    # Re-fetch with commande_id for current week
    cur_cmd_dels = await db.deliveries.find(
        {"created_at": {"$gte": cur_start, "$lt": cur_end}, "commande_id": {"$in": cmd_ids}, **prod_match},
        {"_id": 0, "lead_id": 1, "commande_id": 1, "status": 1, "outcome": 1},
    ).to_list(10000)
    for d in cur_cmd_dels:
        if del_lead_dept.get(d["lead_id"]) == dept:
            if d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted":
                cmd_billable[d["commande_id"]] += 1

    clients_covering = []
    for cmd in active_cmds:
        quota = cmd.get("quota_semaine", 0)
        # Global billable for this commande (for remaining calc)
        global_billable = 0
        for d in cur_cmd_dels:
            if d["commande_id"] == cmd["id"] and d.get("status") == "sent" and (d.get("outcome") or "accepted") == "accepted":
                global_billable += 1
        remaining = max(0, quota - global_billable) if quota > 0 else -1

        clients_covering.append({
            "client_id": cmd["client_id"],
            "name": cname_map.get(cmd["client_id"], ""),
            "commande_id": cmd["id"],
            "produit": cmd.get("produit", ""),
            "quota_week": quota,
            "billable_week": cmd_billable.get(cmd["id"], 0),
            "remaining_week": remaining,
            "order_ids": [cmd["id"]],
        })

    timeseries = []
    for w in weeks:
        timeseries.append({
            "week": w,
            "produced": weekly_produced.get(w, 0),
            "billable": weekly_del.get(w, {}).get("billable", 0),
            "non_billable": weekly_del.get(w, {}).get("non_billable", 0),
            "quota": quota_total,
        })

    # KPIs for current week
    cur_w = week_key
    prev_w = _prev_week_key(cur_w)
    kpi = {
        "produced_current": weekly_produced.get(cur_w, 0),
        "produced_prev": weekly_produced.get(prev_w, 0),
        "billable_current": weekly_del.get(cur_w, {}).get("billable", 0),
        "non_billable_current": weekly_del.get(cur_w, {}).get("non_billable", 0),
        "quota_week_total": quota_total,
    }

    return {
        "departement": dept,
        "product": product,
        "week": week_key,
        "kpi": kpi,
        "timeseries": timeseries,
        "clients_covering": clients_covering,
    }
