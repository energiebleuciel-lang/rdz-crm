"""
RDZ CRM - Routes Deliveries

Gestion des livraisons:
- Liste des deliveries par statut
- Envoi/Renvoi manuel
- Téléchargement CSV
- Stats
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import io

from config import db, now_iso
from routes.auth import get_current_user, require_admin
from models.delivery import DeliveryStatus, SendDeliveryRequest, VALID_STATUS_TRANSITIONS
from services.csv_delivery import send_csv_email, generate_csv_content
from services.settings import get_simulation_email_override, get_email_denylist_settings

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])
logger = logging.getLogger("deliveries")


# ---- List deliveries ----

class DeliveryFilter(BaseModel):
    entity: Optional[str] = None
    status: Optional[str] = None
    client_id: Optional[str] = None
    limit: int = 100
    skip: int = 0


@router.get("")
async def list_deliveries(
    entity: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(get_current_user)
):
    """Liste les deliveries avec filtres"""
    query = {}
    
    if entity:
        query["entity"] = entity.upper()
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    deliveries = await db.deliveries.find(
        query,
        {"_id": 0, "csv_content": 0}  # Exclure csv_content pour perf
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.deliveries.count_documents(query)
    
    # Ajouter has_csv
    for d in deliveries:
        d["has_csv"] = bool(d.get("csv_filename"))
    
    return {
        "deliveries": deliveries,
        "count": len(deliveries),
        "total": total
    }


@router.get("/stats")
async def get_delivery_stats(
    entity: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Stats des deliveries par statut"""
    match_query = {}
    if entity:
        match_query["entity"] = entity.upper()
    
    pipeline = [
        {"$match": match_query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.deliveries.aggregate(pipeline).to_list(20)
    
    stats = {
        "pending_csv": 0,
        "ready_to_send": 0,
        "sending": 0,
        "sent": 0,
        "failed": 0
    }
    
    for r in results:
        status = r["_id"]
        if status in stats:
            stats[status] = r["count"]
    
    stats["total"] = sum(stats.values())
    
    return stats


@router.get("/{delivery_id}")
async def get_delivery(
    delivery_id: str,
    user: dict = Depends(get_current_user)
):
    """Récupère une delivery par ID"""
    delivery = await db.deliveries.find_one(
        {"id": delivery_id},
        {"_id": 0, "csv_content": 0}
    )
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    delivery["has_csv"] = bool(delivery.get("csv_filename"))
    
    return delivery


# ---- Send / Resend ----

@router.post("/{delivery_id}/send")
async def send_delivery(
    delivery_id: str,
    data: SendDeliveryRequest = SendDeliveryRequest(),
    user: dict = Depends(require_admin)
):
    """
    Envoie ou renvoie une delivery
    
    - Si status=pending_csv ou ready_to_send: génère CSV et envoie
    - Si status=failed: retente l'envoi
    - Si status=sent et force=True: renvoie
    """
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    current_status = delivery.get("status")
    
    # Vérifier si envoi autorisé
    if current_status == "sent" and not data.force:
        raise HTTPException(
            status_code=400, 
            detail="Delivery déjà envoyée. Utilisez force=true pour renvoyer."
        )
    
    if current_status == "sending":
        raise HTTPException(status_code=400, detail="Envoi déjà en cours")
    
    # Récupérer le lead
    lead = await db.leads.find_one({"id": delivery.get("lead_id")}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead associé non trouvé")
    
    # Récupérer le client
    client = await db.clients.find_one({"id": delivery.get("client_id")}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client associé non trouvé")
    
    # Déterminer l'email de destination
    override_email = await get_simulation_email_override()
    
    if data.override_email:
        to_emails = [data.override_email]
    elif override_email:
        to_emails = [override_email]
    else:
        to_emails = client.get("delivery_emails", [])
        if not to_emails and client.get("email"):
            to_emails = [client.get("email")]
    
    if not to_emails:
        raise HTTPException(status_code=400, detail="Aucun email de destination")
    
    # Marquer comme sending
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {"status": "sending", "updated_at": now_iso()}}
    )
    
    try:
        # Générer CSV si pas déjà fait
        entity = delivery.get("entity")
        produit = delivery.get("produit")
        
        csv_content = delivery.get("csv_content")
        if not csv_content:
            csv_content = generate_csv_content([lead], produit, entity)
        
        csv_filename = delivery.get("csv_filename") or f"lead_{entity}_{produit}_{lead.get('id')[:8]}.csv"
        
        # Envoyer
        result = await send_csv_email(
            entity=entity,
            to_emails=to_emails,
            csv_content=csv_content,
            csv_filename=csv_filename,
            lead_count=1,
            lb_count=1 if lead.get("is_lb") else 0,
            produit=produit
        )
        
        # Marquer comme sent
        now = now_iso()
        await db.deliveries.update_one(
            {"id": delivery_id},
            {"$set": {
                "status": "sent",
                "sent_to": to_emails,
                "last_sent_at": now,
                "send_attempts": delivery.get("send_attempts", 0) + 1,
                "sent_by": user.get("email"),
                "csv_content": csv_content,
                "csv_filename": csv_filename,
                "csv_generated_at": now,
                "last_error": None,
                "updated_at": now
            }}
        )
        
        # Marquer le lead comme livre
        await db.leads.update_one(
            {"id": lead.get("id")},
            {"$set": {
                "status": "livre",
                "delivered_at": now,
                "delivered_to_client_id": client.get("id"),
                "delivered_to_client_name": client.get("name")
            }}
        )
        
        logger.info(f"[DELIVERY_SENT] id={delivery_id} to={to_emails} by={user.get('email')}")
        
        return {
            "success": True,
            "delivery_id": delivery_id,
            "status": "sent",
            "sent_to": to_emails,
            "message": f"Delivery envoyée à {', '.join(to_emails)}"
        }
        
    except Exception as e:
        # Marquer comme failed
        await db.deliveries.update_one(
            {"id": delivery_id},
            {"$set": {
                "status": "failed",
                "last_error": str(e),
                "send_attempts": delivery.get("send_attempts", 0) + 1,
                "updated_at": now_iso()
            }}
        )
        
        logger.error(f"[DELIVERY_FAILED] id={delivery_id} error={str(e)}")
        
        raise HTTPException(status_code=500, detail=f"Erreur d'envoi: {str(e)}")


# ---- Download CSV ----

@router.get("/{delivery_id}/download")
async def download_delivery_csv(
    delivery_id: str,
    user: dict = Depends(get_current_user)
):
    """Télécharge le CSV d'une delivery"""
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    csv_content = delivery.get("csv_content")
    
    # Si pas de CSV stocké, le générer
    if not csv_content:
        lead = await db.leads.find_one({"id": delivery.get("lead_id")}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead associé non trouvé")
        
        csv_content = generate_csv_content(
            [lead], 
            delivery.get("produit"), 
            delivery.get("entity")
        )
    
    csv_filename = delivery.get("csv_filename") or f"delivery_{delivery_id}.csv"
    
    # Retourner comme fichier téléchargeable
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{csv_filename}"'
        }
    )


# ---- Batch operations ----

@router.post("/batch/generate-csv")
async def batch_generate_csv(
    entity: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Génère les CSV pour toutes les deliveries pending_csv
    Sans les envoyer (mode manuel)
    """
    query = {"status": "pending_csv"}
    if entity:
        query["entity"] = entity.upper()
    
    pending = await db.deliveries.find(query, {"_id": 0}).to_list(1000)
    
    if not pending:
        return {"success": True, "processed": 0, "message": "Aucune delivery en attente"}
    
    processed = 0
    errors = []
    
    for delivery in pending:
        try:
            lead = await db.leads.find_one({"id": delivery.get("lead_id")}, {"_id": 0})
            if not lead:
                continue
            
            entity = delivery.get("entity")
            produit = delivery.get("produit")
            
            csv_content = generate_csv_content([lead], produit, entity)
            csv_filename = f"lead_{entity}_{produit}_{lead.get('id')[:8]}.csv"
            
            now = now_iso()
            await db.deliveries.update_one(
                {"id": delivery.get("id")},
                {"$set": {
                    "status": "ready_to_send",
                    "csv_content": csv_content,
                    "csv_filename": csv_filename,
                    "csv_generated_at": now,
                    "updated_at": now
                }}
            )
            processed += 1
            
        except Exception as e:
            errors.append({"delivery_id": delivery.get("id"), "error": str(e)})
    
    return {
        "success": True,
        "processed": processed,
        "errors": errors
    }
