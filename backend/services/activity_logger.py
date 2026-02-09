"""
Service de journalisation des activités
"""

from config import db, now_iso
import uuid


async def log_activity(
    user: dict,
    action: str,
    entity_type: str,
    entity_id: str = None,
    entity_name: str = None,
    details: dict = None,
    ip_address: str = None
):
    """
    Enregistre une activité dans le journal
    
    Actions: create, update, delete, login, logout, view, export, retry
    Entity types: account, lp, form, lead, commande, user, system
    """
    log_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user.get("id", "system"),
        "user_email": user.get("email", "system"),
        "user_nom": user.get("nom", "Système"),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "details": details or {},
        "ip_address": ip_address,
        "created_at": now_iso()
    }
    
    await db.activity_logs.insert_one(log_entry)
    return log_entry


async def get_activity_logs(
    user_id: str = None,
    entity_type: str = None,
    action: str = None,
    limit: int = 100,
    skip: int = 0
):
    """
    Récupère les logs d'activité avec filtres optionnels
    """
    query = {}
    
    if user_id:
        query["user_id"] = user_id
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    
    logs = await db.activity_logs.find(query, {"_id": 0}) \
        .sort("created_at", -1) \
        .skip(skip) \
        .limit(limit) \
        .to_list(limit)
    
    total = await db.activity_logs.count_documents(query)
    
    return {"logs": logs, "total": total, "limit": limit, "skip": skip}
