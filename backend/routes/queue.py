"""
Routes pour la File d'attente et le Brief
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta

from config import db, now_iso
from routes.auth import get_current_user, require_admin
from services.lead_sender import process_queue, get_queue_stats
from services.brief_generator import generate_brief

router = APIRouter(tags=["Queue & Brief"])


# ==================== FILE D'ATTENTE ====================

@router.get("/queue/stats")
async def queue_stats(user: dict = Depends(get_current_user)):
    """Stats de la file d'attente"""
    stats = await get_queue_stats()
    
    # Stats 24h
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    stats["last_24h"] = {
        "added": await db.lead_queue.count_documents({"created_at": {"$gte": yesterday}}),
        "completed": await db.lead_queue.count_documents({"completed_at": {"$gte": yesterday}})
    }
    
    return stats


@router.get("/queue/items")
async def queue_items(
    status: str = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Liste les éléments en queue"""
    query = {}
    if status:
        query["status"] = status
    
    items = await db.lead_queue.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Masquer les clés API
    for item in items:
        if item.get("api_key"):
            item["api_key"] = "****" + item["api_key"][-4:]
    
    return {"items": items, "count": len(items)}


@router.post("/queue/process")
async def queue_process(user: dict = Depends(require_admin)):
    """Traiter la queue manuellement"""
    results = await process_queue()
    return {"success": True, "results": results}


@router.post("/queue/retry-exhausted")
async def queue_retry_exhausted(user: dict = Depends(require_admin)):
    """Réinitialiser les leads épuisés"""
    result = await db.lead_queue.update_many(
        {"status": "exhausted"},
        {"$set": {
            "status": "pending",
            "retry_count": 0,
            "next_retry_at": now_iso(),
            "reset_at": now_iso()
        }}
    )
    return {"success": True, "reset_count": result.modified_count}


@router.delete("/queue/clear-completed")
async def queue_clear(days: int = 7, user: dict = Depends(require_admin)):
    """Nettoyer les éléments terminés"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = await db.lead_queue.delete_many({
        "status": {"$in": ["success", "failed"]},
        "created_at": {"$lt": cutoff}
    })
    return {"success": True, "deleted": result.deleted_count}


# ==================== BRIEF GENERATOR ====================

@router.get("/forms/{form_id}/brief")
async def get_brief(form_id: str, user: dict = Depends(get_current_user)):
    """
    Génère le brief complet pour un formulaire.
    Inclut les scripts LP et Form, les URLs, les stats expliquées.
    """
    brief = await generate_brief(form_id)
    
    if brief.get("error"):
        raise HTTPException(status_code=404, detail=brief["error"])
    
    return brief


# ==================== CLEF API GLOBALE ====================

@router.get("/settings/api-key")
async def get_api_key(user: dict = Depends(get_current_user)):
    """Récupère la clé API globale"""
    config = await db.system_config.find_one({"type": "global_api_key"})
    
    if not config:
        # Créer une clé si elle n'existe pas
        import secrets
        new_key = f"crm_{secrets.token_urlsafe(32)}"
        await db.system_config.insert_one({
            "type": "global_api_key",
            "api_key": new_key,
            "created_at": now_iso()
        })
        return {"api_key": new_key, "usage": "Authorization: Token VOTRE_CLE"}
    
    return {"api_key": config["api_key"], "usage": "Authorization: Token VOTRE_CLE"}


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def health_check():
    """Vérifie l'état du système"""
    health = {
        "status": "healthy",
        "timestamp": now_iso(),
        "checks": {}
    }
    
    # Check MongoDB
    try:
        await db.command("ping")
        health["checks"]["mongodb"] = "ok"
    except Exception as e:
        health["checks"]["mongodb"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    # Stats rapides
    health["checks"]["leads"] = {
        "total": await db.leads.count_documents({}),
        "today": await db.leads.count_documents({
            "created_at": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()}
        })
    }
    
    health["checks"]["queue"] = await get_queue_stats()
    
    return health
