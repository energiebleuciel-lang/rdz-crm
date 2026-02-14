"""
RDZ CRM - Routes Leads (admin read-only)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from config import db
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
        stats[r["_id"]] = r["count"]
    stats["total"] = sum(stats.values())
    return stats


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a single lead by ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead non trouve")
    return lead
