"""
Service de file d'attente pour les leads.
Gère la mise en file d'attente et le retry automatique des leads
quand les CRM externes (ZR7, MDL) sont indisponibles.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("lead_queue")

# Configuration
MAX_RETRY_ATTEMPTS = 5  # Nombre max de tentatives
RETRY_DELAYS = [60, 300, 900, 3600, 7200]  # Délais entre retries: 1min, 5min, 15min, 1h, 2h
CRM_HEALTH_CHECK_INTERVAL = 60  # Vérifier la santé des CRM toutes les 60 secondes
CRM_TIMEOUT = 10.0  # Timeout pour les appels CRM

# État global des CRM (en mémoire)
crm_health_status = {
    "zr7": {"healthy": True, "last_check": None, "consecutive_failures": 0},
    "mdl": {"healthy": True, "last_check": None, "consecutive_failures": 0}
}


async def check_crm_health(api_url: str, api_key: str) -> bool:
    """
    Vérifie si un CRM externe est accessible.
    On fait un appel léger pour tester la connectivité.
    """
    if not api_url or not api_key:
        return True  # Pas de config = on assume que c'est OK
    
    try:
        async with httpx.AsyncClient(timeout=CRM_TIMEOUT) as client:
            # Test avec un payload minimal (sera rejeté mais on vérifie la connectivité)
            response = await client.post(
                api_url,
                json={"phone": "0000000000", "register_date": 0},  # Payload test
                headers={"Authorization": api_key, "Content-Type": "application/json"}
            )
            # Si on reçoit une réponse (même erreur 400/401), le CRM est up
            return response.status_code < 500
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        logger.warning(f"CRM health check failed: {api_url} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"CRM health check error: {api_url} - {str(e)}")
        return False


def update_crm_health(crm_slug: str, success: bool):
    """
    Met à jour le statut de santé d'un CRM après un appel.
    """
    if crm_slug not in crm_health_status:
        crm_health_status[crm_slug] = {"healthy": True, "last_check": None, "consecutive_failures": 0}
    
    status = crm_health_status[crm_slug]
    status["last_check"] = datetime.now(timezone.utc).isoformat()
    
    if success:
        status["healthy"] = True
        status["consecutive_failures"] = 0
    else:
        status["consecutive_failures"] += 1
        # Marquer comme unhealthy après 3 échecs consécutifs
        if status["consecutive_failures"] >= 3:
            status["healthy"] = False
            logger.warning(f"CRM {crm_slug} marked as unhealthy after {status['consecutive_failures']} failures")


def is_crm_healthy(crm_slug: str) -> bool:
    """
    Vérifie si un CRM est considéré comme healthy.
    """
    if crm_slug not in crm_health_status:
        return True
    return crm_health_status[crm_slug]["healthy"]


def get_next_retry_time(retry_count: int) -> datetime:
    """
    Calcule le prochain moment de retry basé sur le nombre de tentatives.
    """
    delay_index = min(retry_count, len(RETRY_DELAYS) - 1)
    delay_seconds = RETRY_DELAYS[delay_index]
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


async def add_to_queue(db, lead_doc: dict, api_url: str, api_key: str, reason: str = "crm_down"):
    """
    Ajoute un lead à la file d'attente pour retry ultérieur.
    """
    queue_entry = {
        "id": lead_doc.get("id"),
        "lead_id": lead_doc.get("id"),
        "lead_data": lead_doc,
        "api_url": api_url,
        "api_key": api_key,
        "reason": reason,
        "retry_count": 0,
        "max_retries": MAX_RETRY_ATTEMPTS,
        "next_retry_at": datetime.now(timezone.utc).isoformat(),  # Retry immédiat la première fois
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",  # pending, processing, success, failed, exhausted
        "last_error": None
    }
    
    # Vérifier si déjà en queue
    existing = await db.lead_queue.find_one({"lead_id": lead_doc.get("id")})
    if existing:
        logger.info(f"Lead {lead_doc.get('id')} already in queue")
        return existing
    
    await db.lead_queue.insert_one(queue_entry)
    logger.info(f"Lead {lead_doc.get('id')} added to queue - reason: {reason}")
    
    # Mettre à jour le lead original
    await db.leads.update_one(
        {"id": lead_doc.get("id")},
        {"$set": {
            "api_status": "queued",
            "queue_reason": reason,
            "queued_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return queue_entry


async def process_queue_item(db, queue_item: dict) -> tuple:
    """
    Traite un élément de la file d'attente.
    Retourne (success: bool, should_retry: bool, error: str)
    """
    from server import send_lead_to_crm  # Import local pour éviter circular import
    
    lead_data = queue_item.get("lead_data", {})
    api_url = queue_item.get("api_url")
    api_key = queue_item.get("api_key")
    
    if not api_url or not api_key:
        return False, False, "Missing API configuration"
    
    try:
        api_status, api_response = await send_lead_to_crm(lead_data, api_url, api_key)
        
        if api_status == "success":
            return True, False, None
        elif api_status == "duplicate":
            return True, False, "duplicate"  # Considéré comme succès (pas besoin de retry)
        else:
            return False, True, str(api_response)
            
    except Exception as e:
        return False, True, str(e)


async def run_queue_processor(db):
    """
    Worker qui traite la file d'attente en continu.
    Appelé périodiquement par le scheduler.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Récupérer les éléments prêts à être retryés
    pending_items = await db.lead_queue.find({
        "status": "pending",
        "next_retry_at": {"$lte": now},
        "retry_count": {"$lt": MAX_RETRY_ATTEMPTS}
    }).to_list(50)  # Traiter max 50 à la fois
    
    if not pending_items:
        return {"processed": 0, "success": 0, "failed": 0}
    
    logger.info(f"Processing {len(pending_items)} queued leads")
    
    results = {"processed": 0, "success": 0, "failed": 0, "exhausted": 0}
    
    for item in pending_items:
        # Marquer comme en cours de traitement
        await db.lead_queue.update_one(
            {"id": item["id"]},
            {"$set": {"status": "processing"}}
        )
        
        success, should_retry, error = await process_queue_item(db, item)
        results["processed"] += 1
        
        if success:
            results["success"] += 1
            # Succès - retirer de la queue et mettre à jour le lead
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {
                    "status": "success",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {
                    "api_status": "success" if error != "duplicate" else "duplicate",
                    "sent_to_crm": True,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "retry_count": item["retry_count"] + 1
                }}
            )
            
            # Mettre à jour la santé du CRM
            crm_slug = item.get("lead_data", {}).get("target_crm_slug", "")
            if crm_slug:
                update_crm_health(crm_slug, True)
                
        elif should_retry:
            new_retry_count = item["retry_count"] + 1
            
            if new_retry_count >= MAX_RETRY_ATTEMPTS:
                results["exhausted"] += 1
                # Épuisé les retries
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "exhausted",
                        "last_error": error,
                        "exhausted_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                await db.leads.update_one(
                    {"id": item["lead_id"]},
                    {"$set": {
                        "api_status": "failed",
                        "api_response": f"Queue exhausted after {MAX_RETRY_ATTEMPTS} attempts: {error}",
                        "retry_count": new_retry_count
                    }}
                )
                logger.warning(f"Lead {item['lead_id']} exhausted all retries")
            else:
                results["failed"] += 1
                # Programmer le prochain retry
                next_retry = get_next_retry_time(new_retry_count)
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "pending",
                        "retry_count": new_retry_count,
                        "next_retry_at": next_retry.isoformat(),
                        "last_error": error
                    }}
                )
                await db.leads.update_one(
                    {"id": item["lead_id"]},
                    {"$set": {
                        "api_status": "queued",
                        "retry_count": new_retry_count,
                        "last_retry_error": error
                    }}
                )
                
                # Mettre à jour la santé du CRM
                crm_slug = item.get("lead_data", {}).get("target_crm_slug", "")
                if crm_slug:
                    update_crm_health(crm_slug, False)
                    
                logger.info(f"Lead {item['lead_id']} retry {new_retry_count}/{MAX_RETRY_ATTEMPTS} scheduled for {next_retry}")
        else:
            results["failed"] += 1
            # Échec sans retry (erreur permanente)
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {
                    "status": "failed",
                    "last_error": error,
                    "failed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {
                    "api_status": "failed",
                    "api_response": error
                }}
            )
    
    return results


def get_queue_stats_sync(db) -> dict:
    """
    Retourne les statistiques de la file d'attente (version sync pour usage simple).
    """
    return {
        "crm_health": crm_health_status,
        "retry_config": {
            "max_attempts": MAX_RETRY_ATTEMPTS,
            "delays_seconds": RETRY_DELAYS
        }
    }
