"""
RDZ CRM - Routes Leads (admin read-only)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone, timedelta
from config import db, now_iso
from routes.auth import get_current_user
from services.permissions import require_permission, validate_entity_access, get_entity_scope_from_request, build_entity_filter

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/stats")
async def get_lead_stats(
    request: Request,
    entity: Optional[str] = None,
    user: dict = Depends(require_permission("leads.view"))
):
    """Stats leads par status — scoped by X-Entity-Scope"""
    from services.permissions import get_entity_scope_from_request, build_entity_filter

    match_query = {}
    if entity:
        validate_entity_access(user, entity)
        match_query["entity"] = entity.upper()
    else:
        scope = get_entity_scope_from_request(user, request)
        match_query.update(build_entity_filter(scope))

    pipeline = [
        {"$match": match_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]

    results = await db.leads.aggregate(pipeline).to_list(20)
    stats = {}
    for r in results:
        if r["_id"]:
            stats[r["_id"]] = r["count"]
    stats["total"] = sum(stats.values())
    return stats


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    request: Request,
    week: Optional[str] = None,
    user: dict = Depends(require_permission("leads.view"))
):
    """
    Stats agrégées pour le cockpit dashboard.
    Scoped by X-Entity-Scope header.
    FAIL-OPEN: each widget isolated — partial failures return partial data.
    """
    import logging
    _logger = logging.getLogger("dashboard")
    from services.settings import is_delivery_day_enabled, get_email_denylist_settings
    from models.client import check_client_deliverable
    from services.routing_engine import resolve_week_range

    scope = get_entity_scope_from_request(user, request)
    entity_filter = build_entity_filter(scope)

    week_start, week_end = resolve_week_range(week)

    result = {"_errors": []}

    # Widget: Lead stats
    try:
        lead_pipeline = [{"$match": {**entity_filter, "created_at": {"$gte": week_start, "$lte": week_end}}}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        lead_stats_raw = await db.leads.aggregate(lead_pipeline).to_list(20)
        result["lead_stats"] = {r["_id"]: r["count"] for r in lead_stats_raw if r["_id"]}
    except Exception as e:
        _logger.error(f"[DASHBOARD] lead_stats failed: {e}")
        result["lead_stats"] = {}
        result["_errors"].append("lead_stats")

    # Widget: Delivery stats
    try:
        week_match = {**entity_filter, "created_at": {"$gte": week_start, "$lte": week_end}}
        del_pipeline = [{"$match": week_match}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        del_stats_raw = await db.deliveries.aggregate(del_pipeline).to_list(10)
        del_stats = {r["_id"]: r["count"] for r in del_stats_raw if r["_id"]}
        rejected_total = await db.deliveries.count_documents({"outcome": "rejected", **week_match})
        removed_total = await db.deliveries.count_documents({"outcome": "removed", **week_match})
        billable_total = await db.deliveries.count_documents({"status": "sent", "outcome": {"$nin": ["rejected", "removed"]}, **week_match})
        result["delivery_stats"] = {**del_stats, "rejected": rejected_total, "removed": removed_total, "billable": billable_total}
    except Exception as e:
        _logger.error(f"[DASHBOARD] delivery_stats failed: {e}")
        result["delivery_stats"] = {}
        result["_errors"].append("delivery_stats")

    # Widget: Calendar status
    try:
        zr7_enabled, zr7_reason = await is_delivery_day_enabled("ZR7")
        mdl_enabled, mdl_reason = await is_delivery_day_enabled("MDL")
        result["calendar"] = {
            "ZR7": {"is_delivery_day": zr7_enabled, "reason": zr7_reason},
            "MDL": {"is_delivery_day": mdl_enabled, "reason": mdl_reason}
        }
    except Exception as e:
        _logger.error(f"[DASHBOARD] calendar failed: {e}")
        result["calendar"] = {}
        result["_errors"].append("calendar")

    # Widget: Top clients
    try:
        top_clients_pipeline = [
            {"$match": {"status": "sent", **entity_filter, "created_at": {"$gte": week_start, "$lte": week_end}}},
            {"$group": {"_id": "$client_id", "client_name": {"$first": "$client_name"}, "entity": {"$first": "$entity"}, "sent": {"$sum": 1}}},
            {"$sort": {"sent": -1}}, {"$limit": 10}
        ]
        top_clients = await db.deliveries.aggregate(top_clients_pipeline).to_list(10)
        for tc in top_clients:
            cid = tc["_id"]
            tc["rejected_7d"] = await db.deliveries.count_documents({"client_id": cid, "outcome": "rejected", "created_at": {"$gte": week_start, "$lte": week_end}})
            tc["billable_7d"] = await db.deliveries.count_documents({"client_id": cid, "status": "sent", "outcome": {"$nin": ["rejected", "removed"]}, "created_at": {"$gte": week_start, "$lte": week_end}})
            tc["failed_7d"] = await db.deliveries.count_documents({"client_id": cid, "status": "failed", "created_at": {"$gte": week_start, "$lte": week_end}})
            tc["ready_7d"] = await db.deliveries.count_documents({"client_id": cid, "status": "ready_to_send", "created_at": {"$gte": week_start, "$lte": week_end}})
            tc.pop("_id")
            tc["client_id"] = cid
        result["top_clients_7d"] = top_clients
    except Exception as e:
        _logger.error(f"[DASHBOARD] top_clients failed: {e}")
        result["top_clients_7d"] = []
        result["_errors"].append("top_clients")

    # Widget: Problem clients
    try:
        denylist_settings = await get_email_denylist_settings()
        denylist = denylist_settings.get("domains", [])
        client_query = {"active": True, **entity_filter}
        all_clients = await db.clients.find(client_query, {"_id": 0, "id": 1, "name": 1, "entity": 1, "email": 1, "delivery_emails": 1, "api_endpoint": 1}).to_list(500)
        problem_clients = []
        for c in all_clients:
            check = check_client_deliverable(c.get("email",""), c.get("delivery_emails",[]), c.get("api_endpoint",""), denylist)
            if not check["deliverable"]:
                problem_clients.append({"client_id": c["id"], "name": c["name"], "entity": c["entity"], "reason": check["reason"]})
        result["problem_clients"] = problem_clients
    except Exception as e:
        _logger.error(f"[DASHBOARD] problem_clients failed: {e}")
        result["problem_clients"] = []
        result["_errors"].append("problem_clients")

    # Widget: Low quota commandes
    try:
        low_quota_cmds = []
        for ent in ["ZR7", "MDL"]:
            cmds = await db.commandes.find({"entity": ent, "active": True}, {"_id": 0}).to_list(200)
            for cmd in cmds:
                delivered = await db.leads.count_documents({"delivery_commande_id": cmd["id"], "delivered_at": {"$gte": week_start}})
                remaining = max(0, (cmd.get("quota_semaine", 0)) - delivered)
                if remaining <= 5 and cmd.get("quota_semaine", 0) > 0:
                    client = await db.clients.find_one({"id": cmd["client_id"]}, {"_id": 0, "name": 1})
                    low_quota_cmds.append({"commande_id": cmd["id"], "client_name": client.get("name") if client else "", "entity": ent, "produit": cmd.get("produit"), "quota": cmd.get("quota_semaine"), "delivered": delivered, "remaining": remaining})
        result["low_quota_commandes"] = low_quota_cmds
    except Exception as e:
        _logger.error(f"[DASHBOARD] low_quota failed: {e}")
        result["low_quota_commandes"] = []
        result["_errors"].append("low_quota")

    # Widget: Blocked stock
    try:
        blocked_pipeline = [
            {"$match": {"status": {"$in": ["no_open_orders", "hold_source", "pending_config"]}}},
            {"$group": {"_id": {"entity": "$entity", "produit": "$produit", "status": "$status"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        blocked_raw = await db.leads.aggregate(blocked_pipeline).to_list(50)
        result["blocked_stock"] = [{"entity": b["_id"].get("entity"), "produit": b["_id"].get("produit"), "status": b["_id"]["status"], "count": b["count"]} for b in blocked_raw]
    except Exception as e:
        _logger.error(f"[DASHBOARD] blocked_stock failed: {e}")
        result["blocked_stock"] = []
        result["_errors"].append("blocked_stock")

    # Remove _errors if empty
    if not result["_errors"]:
        del result["_errors"]

    return result


@router.get("/list")
async def list_leads(
    request: Request,
    entity: Optional[str] = None,
    produit: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    departement: Optional[str] = None,
    client_id: Optional[str] = None,
    search: Optional[str] = None,
    week: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(require_permission("leads.view"))
):
    """Liste les leads avec filtres avancés — scoped by X-Entity-Scope"""
    query = {}
    if entity:
        validate_entity_access(user, entity)
        query["entity"] = entity.upper()
    else:
        scope = get_entity_scope_from_request(user, request)
        query.update(build_entity_filter(scope))
    if produit:
        query["produit"] = produit.upper()
    if status:
        query["status"] = status
    if source:
        query["source"] = {"$regex": source, "$options": "i"}
    if departement:
        query["departement"] = departement
    if client_id and search:
        query["$and"] = [
            {"$or": [
                {"delivered_to_client_id": client_id},
                {"delivery_client_id": client_id}
            ]},
            {"$or": [
                {"phone": {"$regex": search, "$options": "i"}},
                {"nom": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]}
        ]
    elif client_id:
        query["$or"] = [
            {"delivered_to_client_id": client_id},
            {"delivery_client_id": client_id}
        ]
    elif search:
        query["$or"] = [
            {"phone": {"$regex": search, "$options": "i"}},
            {"nom": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    if week:
        from services.routing_engine import week_key_to_range
        ws, we = week_key_to_range(week)
        query["created_at"] = {"$gte": ws, "$lte": we}
    
    leads = await db.leads.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.leads.count_documents(query)
    
    return {"leads": leads, "count": len(leads), "total": total}


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: dict = Depends(require_permission("leads.view"))
):
    """Get a single lead by ID with delivery history"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouve")
    
    # Attach delivery history
    deliveries = await db.deliveries.find(
        {"lead_id": lead_id},
        {"_id": 0, "csv_content": 0}
    ).sort("created_at", -1).to_list(20)
    
    for d in deliveries:
        d["outcome"] = d.get("outcome", "accepted")
        d["billable"] = d.get("status") == "sent" and d.get("outcome", "accepted") == "accepted"
    
    lead["deliveries"] = deliveries
    return lead
