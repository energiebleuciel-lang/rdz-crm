"""
Service d'envoi de leads vers les CRMs externes (ZR7, MDL)
Gère l'envoi, les erreurs, et la mise en file d'attente

Format API ZR7/MDL:
- Endpoint: POST /lead/api/create_lead/
- Auth: Header Authorization: {token}
- Body: JSON avec phone, register_date, nom, prenom, email, custom_fields
"""

import httpx
import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso

logger = logging.getLogger("lead_sender")

# Configuration retry
MAX_RETRY_ATTEMPTS = 5
RETRY_DELAYS = [60, 300, 900, 3600, 7200]  # 1min, 5min, 15min, 1h, 2h


# ==================== NOUVELLE FONCTION V2 ====================

async def send_to_crm_v2(lead_doc: dict, api_url: str, api_key: str) -> tuple:
    """
    Envoie un lead vers ZR7 ou MDL avec le format API exact.
    
    Format requis par l'API:
    {
        "phone": "0706548485",
        "register_date": 1734307200,
        "nom": "Doe",
        "prenom": "John",
        "email": "john.doe@example.com",
        "civilite": "M.",
        "custom_fields": {
            "departement": {"value": "75"},
            "code_postal": {"value": "75001"},
            "type_logement": {"value": "Maison"},
            ...
        }
    }
    
    Returns:
        (status, response, should_queue)
    """
    # Construire les custom_fields
    custom_fields = {}
    
    # Tous les champs qui vont dans custom_fields
    custom_field_mapping = {
        "departement": "departement",
        "code_postal": "code_postal",
        "ville": "ville",
        "adresse": "adresse",
        "type_logement": "type_logement",
        "statut_occupant": "statut_occupant",
        "surface_habitable": "superficie_logement",  # Mapping vers nom ZR7
        "annee_construction": "annee_construction",
        "type_chauffage": "chauffage_actuel",  # Mapping vers nom ZR7
        "facture_electricite": "facture_electricite",
        "facture_chauffage": "facture_chauffage",
        "type_projet": "type_projet",
        "delai_projet": "delai_projet",
        "budget": "budget",
        "product_type": "product_type",
        "lp_code": "lp_code",
        "liaison_code": "liaison_code",
        "utm_source": "utm_source",
        "utm_medium": "utm_medium",
        "utm_campaign": "utm_campaign"
    }
    
    for lead_field, crm_field in custom_field_mapping.items():
        value = lead_doc.get(lead_field)
        if value:
            custom_fields[crm_field] = {"value": str(value)}
    
    # Construire le payload principal
    payload = {
        "phone": lead_doc["phone"],
        "register_date": lead_doc.get("register_date", int(datetime.now().timestamp())),
        "nom": lead_doc.get("nom", ""),
        "prenom": lead_doc.get("prenom", ""),
        "email": lead_doc.get("email", "")
    }
    
    # Ajouter civilité si présente
    if lead_doc.get("civilite"):
        payload["civilite"] = lead_doc["civilite"]
    
    # Ajouter custom_fields si non vide
    if custom_fields:
        payload["custom_fields"] = custom_fields
    
    # Envoi HTTP
    status = "failed"
    response = None
    should_queue = False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json"
                }
            )
            
            try:
                data = resp.json()
                response = str(data)
            except Exception:
                response = resp.text
            
            # Analyser la réponse selon la doc API
            if resp.status_code == 201:
                status = "success"
                logger.info(f"Lead {lead_doc.get('id')} envoyé avec succès à {api_url}")
            elif resp.status_code == 200 and "doublon" in str(response).lower():
                status = "duplicate"
                logger.info(f"Lead {lead_doc.get('id')} est un doublon")
            elif resp.status_code == 403:
                # Erreur d'auth - ne pas retry
                status = "auth_error"
                logger.error(f"Erreur auth CRM: {response}")
            elif resp.status_code == 400:
                # Erreur de validation - ne pas retry
                status = "validation_error"
                logger.warning(f"Erreur validation CRM: {response}")
            elif resp.status_code >= 500:
                # Erreur serveur - retry
                status = "server_error"
                should_queue = True
                logger.warning(f"Erreur serveur CRM {resp.status_code}: {api_url}")
            else:
                status = "failed"
                logger.warning(f"CRM rejected lead: {response}")
                
    except httpx.TimeoutException as e:
        status = "timeout"
        response = f"Timeout après 30s: {str(e)}"
        should_queue = True
        logger.warning(f"CRM timeout: {api_url}")
        
    except httpx.ConnectError as e:
        status = "connection_error"
        response = f"Erreur connexion: {str(e)}"
        should_queue = True
        logger.warning(f"CRM connection error: {api_url}")
        
    except Exception as e:
        status = "failed"
        response = str(e)
        should_queue = True
        logger.error(f"CRM error: {str(e)}")
    
    return status, response, should_queue


# ==================== ANCIENNE FONCTION (compatibilité) ====================

async def send_to_crm(lead_doc: dict, api_url: str, api_key: str) -> tuple:
    """
    Envoie un lead vers un CRM externe.
    
    Args:
        lead_doc: Document du lead
        api_url: URL de l'API CRM
        api_key: Clé API du CRM
    
    Returns:
        (status, response, should_queue)
        - status: "success", "duplicate", "failed", "timeout", "connection_error"
        - response: Réponse API ou message d'erreur
        - should_queue: True si on doit mettre en file d'attente (erreur temporaire)
    """
    # Construire le payload
    custom_fields = {}
    
    for field in ["superficie_logement", "chauffage_actuel", "departement", 
                  "code_postal", "type_logement", "statut_occupant", "facture_electricite"]:
        if lead_doc.get(field):
            custom_fields[field] = {"value": lead_doc[field]}
    
    payload = {
        "phone": lead_doc["phone"],
        "register_date": lead_doc.get("register_date", int(datetime.now().timestamp())),
        "nom": lead_doc.get("nom", ""),
        "prenom": lead_doc.get("prenom", ""),
        "email": lead_doc.get("email", ""),
    }
    
    if lead_doc.get("civilite"):
        payload["civilite"] = lead_doc["civilite"]
    
    if custom_fields:
        payload["custom_fields"] = custom_fields
    
    # Envoi
    status = "failed"
    response = None
    should_queue = False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={"Authorization": api_key, "Content-Type": "application/json"}
            )
            data = resp.json()
            response = str(data)
            
            if resp.status_code == 201:
                status = "success"
            elif "doublon" in str(data.get("message", "")).lower():
                status = "duplicate"
            elif resp.status_code >= 500:
                status = "server_error"
                should_queue = True
                logger.warning(f"CRM server error {resp.status_code}: {api_url}")
            else:
                status = "failed"
                logger.warning(f"CRM rejected lead: {response}")
                
    except httpx.TimeoutException as e:
        status = "timeout"
        response = f"Timeout après 30s: {str(e)}"
        should_queue = True
        logger.warning(f"CRM timeout: {api_url}")
        
    except httpx.ConnectError as e:
        status = "connection_error"
        response = f"Erreur connexion: {str(e)}"
        should_queue = True
        logger.warning(f"CRM connection error: {api_url}")
        
    except Exception as e:
        status = "failed"
        response = str(e)
        should_queue = True
        logger.error(f"CRM error: {str(e)}")
    
    return status, response, should_queue


async def add_to_queue(lead_doc: dict, api_url: str, api_key: str, reason: str = "crm_error"):
    """
    Ajoute un lead à la file d'attente pour retry.
    """
    # Vérifier si déjà en queue
    existing = await db.lead_queue.find_one({"lead_id": lead_doc.get("id")})
    if existing:
        logger.info(f"Lead {lead_doc.get('id')} déjà en queue")
        return existing
    
    queue_entry = {
        "id": lead_doc.get("id"),
        "lead_id": lead_doc.get("id"),
        "lead_data": lead_doc,
        "api_url": api_url,
        "api_key": api_key,
        "reason": reason,
        "retry_count": 0,
        "max_retries": MAX_RETRY_ATTEMPTS,
        "next_retry_at": now_iso(),
        "created_at": now_iso(),
        "status": "pending",
        "last_error": None
    }
    
    await db.lead_queue.insert_one(queue_entry)
    logger.info(f"Lead {lead_doc.get('id')} ajouté à la queue - raison: {reason}")
    
    # Mettre à jour le lead
    await db.leads.update_one(
        {"id": lead_doc.get("id")},
        {"$set": {
            "api_status": "queued",
            "queue_reason": reason,
            "queued_at": now_iso()
        }}
    )
    
    return queue_entry


async def process_queue():
    """
    Traite la file d'attente.
    Appelé périodiquement ou manuellement.
    """
    now = now_iso()
    
    # Récupérer les éléments prêts
    pending = await db.lead_queue.find({
        "status": "pending",
        "next_retry_at": {"$lte": now},
        "retry_count": {"$lt": MAX_RETRY_ATTEMPTS}
    }).to_list(50)
    
    if not pending:
        return {"processed": 0, "success": 0, "failed": 0, "exhausted": 0}
    
    results = {"processed": 0, "success": 0, "failed": 0, "exhausted": 0}
    
    for item in pending:
        # Marquer en cours
        await db.lead_queue.update_one(
            {"id": item["id"]},
            {"$set": {"status": "processing"}}
        )
        
        # Tenter l'envoi
        lead_data = item.get("lead_data", {})
        status, response, should_retry = await send_to_crm(
            lead_data, 
            item.get("api_url"), 
            item.get("api_key")
        )
        
        results["processed"] += 1
        
        if status in ["success", "duplicate"]:
            results["success"] += 1
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {"status": "success", "completed_at": now_iso()}}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {
                    "api_status": status,
                    "sent_to_crm": True,
                    "sent_at": now_iso(),
                    "retry_count": item["retry_count"] + 1
                }}
            )
            
        elif should_retry:
            new_count = item["retry_count"] + 1
            
            if new_count >= MAX_RETRY_ATTEMPTS:
                results["exhausted"] += 1
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "exhausted",
                        "last_error": response,
                        "exhausted_at": now_iso()
                    }}
                )
                await db.leads.update_one(
                    {"id": item["lead_id"]},
                    {"$set": {
                        "api_status": "failed",
                        "api_response": f"Épuisé après {MAX_RETRY_ATTEMPTS} tentatives: {response}"
                    }}
                )
            else:
                results["failed"] += 1
                # Programmer prochain retry
                delay = RETRY_DELAYS[min(new_count, len(RETRY_DELAYS) - 1)]
                next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                
                await db.lead_queue.update_one(
                    {"id": item["id"]},
                    {"$set": {
                        "status": "pending",
                        "retry_count": new_count,
                        "next_retry_at": next_retry,
                        "last_error": response
                    }}
                )
        else:
            results["failed"] += 1
            await db.lead_queue.update_one(
                {"id": item["id"]},
                {"$set": {
                    "status": "failed",
                    "last_error": response,
                    "failed_at": now_iso()
                }}
            )
            await db.leads.update_one(
                {"id": item["lead_id"]},
                {"$set": {"api_status": "failed", "api_response": response}}
            )
    
    return results


async def get_queue_stats():
    """Retourne les stats de la file d'attente."""
    return {
        "pending": await db.lead_queue.count_documents({"status": "pending"}),
        "processing": await db.lead_queue.count_documents({"status": "processing"}),
        "success": await db.lead_queue.count_documents({"status": "success"}),
        "failed": await db.lead_queue.count_documents({"status": "failed"}),
        "exhausted": await db.lead_queue.count_documents({"status": "exhausted"}),
        "total": await db.lead_queue.count_documents({})
    }
