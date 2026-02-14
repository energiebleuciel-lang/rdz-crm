"""
RDZ CRM - Routes Leads (admin read-only)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta
from config import db, now_iso
from routes.auth import get_current_user

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/stats")
async def get_lead_stats(
    entity: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Stats leads par status"""
    match_query = {}
    if entity:
        match_query["entity"] = entity.upper()

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
    week: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Stats agrégées pour le cockpit dashboard.
    Un seul appel = toutes les données nécessaires.
    """
    from services.settings import is_delivery_day_enabled, get_email_denylist_settings
    from models.client import check_client_deliverable
    from services.routing_engine import resolve_week_range

    week_start, week_end = resolve_week_range(week)

    # Lead stats by status (scoped to selected week)
    lead_pipeline = [{"$match": {"created_at": {"$gte": week_start, "$lte": week_end}}}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    lead_stats_raw = await db.leads.aggregate(lead_pipeline).to_list(20)
    lead_stats = {r["_id"]: r["count"] for r in lead_stats_raw if r["_id"]}

    # Delivery stats (scoped to selected week)
    week_match = {"created_at": {"$gte": week_start, "$lte": week_end}}
    del_pipeline = [{"$match": week_match}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    del_stats_raw = await db.deliveries.aggregate(del_pipeline).to_list(10)
    del_stats = {r["_id"]: r["count"] for r in del_stats_raw if r["_id"]}
    rejected_total = await db.deliveries.count_documents({"outcome": "rejected", **week_match})
    removed_total = await db.deliveries.count_documents({"outcome": "removed", **week_match})
    billable_total = await db.deliveries.count_documents({"status": "sent", "outcome": {"$nin": ["rejected", "removed"]}, **week_match})

    # Calendar status
    zr7_enabled, zr7_reason = await is_delivery_day_enabled("ZR7")
    mdl_enabled, mdl_reason = await is_delivery_day_enabled("MDL")

    # Top clients semaine (by delivery count)
    top_clients_pipeline = [
        {"$match": {"status": "sent", "created_at": {"$gte": week_start, "$lte": week_end}}},
        {"$group": {
            "_id": "$client_id",
            "client_name": {"$first": "$client_name"},
            "entity": {"$first": "$entity"},
            "sent": {"$sum": 1}
        }},
        {"$sort": {"sent": -1}},
        {"$limit": 10}
    ]
    top_clients = await db.deliveries.aggregate(top_clients_pipeline).to_list(10)

    # Enrich top clients with rejected + billable for week
    for tc in top_clients:
        cid = tc["_id"]
        tc["rejected_7d"] = await db.deliveries.count_documents({
            "client_id": cid, "outcome": "rejected", "created_at": {"$gte": week_start, "$lte": week_end}
        })
        tc["billable_7d"] = await db.deliveries.count_documents({
            "client_id": cid, "status": "sent", "outcome": {"$nin": ["rejected", "removed"]}, "created_at": {"$gte": week_start, "$lte": week_end}
        })
        tc["failed_7d"] = await db.deliveries.count_documents({
            "client_id": cid, "status": "failed", "created_at": {"$gte": week_start, "$lte": week_end}
        })
        tc["ready_7d"] = await db.deliveries.count_documents({
            "client_id": cid, "status": "ready_to_send", "created_at": {"$gte": week_start, "$lte": week_end}
        })
        tc.pop("_id")
        tc["client_id"] = cid

    # Clients à problème
    denylist_settings = await get_email_denylist_settings()
    denylist = denylist_settings.get("domains", [])
    all_clients = await db.clients.find({"active": True}, {"_id": 0, "id": 1, "name": 1, "entity": 1, "email": 1, "delivery_emails": 1, "api_endpoint": 1}).to_list(500)
    problem_clients = []
    for c in all_clients:
        check = check_client_deliverable(c.get("email",""), c.get("delivery_emails",[]), c.get("api_endpoint",""), denylist)
        if not check["deliverable"]:
            problem_clients.append({"client_id": c["id"], "name": c["name"], "entity": c["entity"], "reason": check["reason"]})

    # Commandes proches de la fin (quota_remaining <= 5)
    low_quota_cmds = []
    for entity in ["ZR7", "MDL"]:
        cmds = await db.commandes.find({"entity": entity, "active": True}, {"_id": 0}).to_list(200)
        for cmd in cmds:
            delivered = await db.leads.count_documents({
                "delivery_commande_id": cmd["id"],
                "delivered_at": {"$gte": week_start}
            })
            remaining = max(0, (cmd.get("quota_semaine", 0)) - delivered)
            if remaining <= 5 and cmd.get("quota_semaine", 0) > 0:
                client = await db.clients.find_one({"id": cmd["client_id"]}, {"_id": 0, "name": 1})
                low_quota_cmds.append({
                    "commande_id": cmd["id"], "client_name": client.get("name") if client else "",
                    "entity": entity, "produit": cmd.get("produit"), "quota": cmd.get("quota_semaine"),
                    "delivered": delivered, "remaining": remaining
                })

    # Stock bloqué by entity+produit
    blocked_pipeline = [
        {"$match": {"status": {"$in": ["no_open_orders", "hold_source", "pending_config"]}}},
        {"$group": {"_id": {"entity": "$entity", "produit": "$produit", "status": "$status"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    blocked_raw = await db.leads.aggregate(blocked_pipeline).to_list(50)
    blocked_stock = [{"entity": b["_id"].get("entity"), "produit": b["_id"].get("produit"), "status": b["_id"]["status"], "count": b["count"]} for b in blocked_raw]

    return {
        "lead_stats": lead_stats,
        "delivery_stats": {**del_stats, "rejected": rejected_total, "removed": removed_total, "billable": billable_total},
        "calendar": {
            "ZR7": {"is_delivery_day": zr7_enabled, "reason": zr7_reason},
            "MDL": {"is_delivery_day": mdl_enabled, "reason": mdl_reason}
        },
        "top_clients_7d": top_clients,
        "problem_clients": problem_clients,
        "low_quota_commandes": low_quota_cmds,
        "blocked_stock": blocked_stock
    }


@router.get("/list")
async def list_leads(
    entity: Optional[str] = None,
    produit: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    departement: Optional[str] = None,
    client_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    """Liste les leads avec filtres avancés"""
    from fastapi import Query
    
    query = {}
    if entity:
        query["entity"] = entity.upper()
    if produit:
        query["produit"] = produit.upper()
    if status:
        query["status"] = status
    if source:
        query["source"] = {"$regex": source, "$options": "i"}
    if departement:
        query["departement"] = departement
    if client_id:
        query["$or"] = [
            {"delivered_to_client_id": client_id},
            {"delivery_client_id": client_id}
        ]
    if search:
        query["$or"] = [
            {"phone": {"$regex": search, "$options": "i"}},
            {"nom": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    leads = await db.leads.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.leads.count_documents(query)
    
    return {"leads": leads, "count": len(leads), "total": total}


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: dict = Depends(get_current_user)
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
