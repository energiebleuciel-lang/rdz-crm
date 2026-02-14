"""
RDZ CRM - Routes Event Log (audit trail)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from config import db
from routes.auth import get_current_user
from services.permissions import require_permission

router = APIRouter(prefix="/event-log", tags=["EventLog"])


@router.get("")
async def list_events(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity: Optional[str] = None,
    week: Optional[str] = None,
    user: Optional[str] = Query(None, alias="user_filter"),
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(require_permission("activity.view"))
):
    """Liste les events avec filtres"""
    query = {}
    if action:
        query["action"] = action
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["$or"] = [
            {"entity_id": entity_id},
            {"related.lead_id": entity_id},
            {"related.client_id": entity_id},
            {"related.delivery_id": entity_id},
            {"related.commande_id": entity_id}
        ]
    if entity:
        query["entity"] = entity.upper()
    if week:
        from services.routing_engine import week_key_to_range
        ws, we = week_key_to_range(week)
        query["created_at"] = {"$gte": ws, "$lte": we}
    if user:
        query["user"] = {"$regex": user, "$options": "i"}
    if search:
        query["$or"] = [
            {"action": {"$regex": search, "$options": "i"}},
            {"details.reason": {"$regex": search, "$options": "i"}},
            {"related.client_name": {"$regex": search, "$options": "i"}},
            {"user": {"$regex": search, "$options": "i"}}
        ]

    events = await db.event_log.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    total = await db.event_log.count_documents(query)

    return {"events": events, "count": len(events), "total": total}


@router.get("/actions")
async def list_action_types(
    current_user: dict = Depends(require_permission("activity.view"))
):
    """Liste les types d'actions distincts dans le log"""
    actions = await db.event_log.distinct("action")
    return {"actions": sorted(actions)}


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    current_user: dict = Depends(require_permission("activity.view"))
):
    """Détail d'un event"""
    event = await db.event_log.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event non trouvé")
    return event
