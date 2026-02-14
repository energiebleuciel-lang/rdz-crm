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
from services.permissions import require_permission, validate_entity_access
from models.delivery import DeliveryStatus, SendDeliveryRequest, RejectDeliveryRequest, VALID_STATUS_TRANSITIONS
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
    week: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    user: dict = Depends(require_permission("deliveries.view"))
):
    """Liste les deliveries avec filtres"""
    query = {}
    
    if entity:
        query["entity"] = entity.upper()
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    if week:
        from services.routing_engine import week_key_to_range
        ws, we = week_key_to_range(week)
        query["created_at"] = {"$gte": ws, "$lte": we}
    
    deliveries = await db.deliveries.find(
        query,
        {"_id": 0, "csv_content": 0}  # Exclure csv_content pour perf
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.deliveries.count_documents(query)
    
    # Ajouter has_csv + outcome + billable
    for d in deliveries:
        d["has_csv"] = bool(d.get("csv_filename"))
        outcome = d.get("outcome", "accepted")
        d["outcome"] = outcome
        d["billable"] = d.get("status") == "sent" and outcome == "accepted"
    
    return {
        "deliveries": deliveries,
        "count": len(deliveries),
        "total": total
    }


@router.get("/stats")
async def get_delivery_stats(
    entity: Optional[str] = None,
    user: dict = Depends(require_permission("deliveries.view"))
):
    """Stats des deliveries par statut + outcome"""
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
    
    # Outcome stats (rejected / removed / billable)
    rejected_count = await db.deliveries.count_documents({**match_query, "outcome": "rejected"})
    removed_count = await db.deliveries.count_documents({**match_query, "outcome": "removed"})
    billable_count = await db.deliveries.count_documents({**match_query, "status": "sent", "outcome": {"$nin": ["rejected", "removed"]}})
    
    stats["rejected"] = rejected_count
    stats["removed"] = removed_count
    stats["billable"] = billable_count
    
    return stats


@router.get("/{delivery_id}")
async def get_delivery(
    delivery_id: str,
    user: dict = Depends(require_permission("deliveries.view"))
):
    """Récupère une delivery par ID"""
    delivery = await db.deliveries.find_one(
        {"id": delivery_id},
        {"_id": 0, "csv_content": 0}
    )
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    delivery["has_csv"] = bool(delivery.get("csv_filename"))
    outcome = delivery.get("outcome", "accepted")
    delivery["outcome"] = outcome
    delivery["billable"] = delivery.get("status") == "sent" and outcome == "accepted"
    
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
    
    🔒 Utilise delivery_state_machine pour les transitions
    """
    from services.delivery_state_machine import mark_delivery_sent, mark_delivery_failed, mark_delivery_sending
    
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
    
    # Marquer comme sending (si pas déjà sent avec force)
    if current_status != "sent":
        try:
            await mark_delivery_sending(delivery_id)
        except Exception:
            pass  # Continue anyway for retry
    
    try:
        # Générer CSV si pas déjà fait
        entity = delivery.get("entity")
        produit = delivery.get("produit")
        
        csv_content = delivery.get("csv_content")
        if not csv_content:
            csv_content = generate_csv_content([lead], produit, entity)
        
        csv_filename = delivery.get("csv_filename") or f"lead_{entity}_{produit}_{lead.get('id')[:8]}.csv"
        
        # 1. Envoyer l'email RÉELLEMENT
        await send_csv_email(
            entity=entity,
            to_emails=to_emails,
            csv_content=csv_content,
            csv_filename=csv_filename,
            lead_count=1,
            lb_count=1 if lead.get("is_lb") else 0,
            produit=produit
        )
        
        # 2. 🔒 SEULEMENT après envoi réussi: marquer via state machine
        await mark_delivery_sent(
            delivery_id=delivery_id,
            sent_to=to_emails,
            send_attempts=delivery.get("send_attempts", 0) + 1,
            sent_by=user.get("email")
        )
        
        # 3. Stocker le CSV pour téléchargement
        await db.deliveries.update_one(
            {"id": delivery_id},
            {"$set": {
                "csv_content": csv_content,
                "csv_filename": csv_filename,
                "csv_generated_at": now_iso()
            }}
        )
        
        logger.info(f"[DELIVERY_SENT] id={delivery_id} to={to_emails} by={user.get('email')}")
        
        from services.event_logger import log_event
        action_name = "resend_delivery" if current_status == "sent" else "send_delivery"
        await log_event(
            action=action_name,
            entity_type="delivery",
            entity_id=delivery_id,
            entity=delivery.get("entity", ""),
            user=user.get("email"),
            details={"sent_to": to_emails, "force": current_status == "sent"},
            related={"lead_id": delivery.get("lead_id"), "client_id": delivery.get("client_id"), "client_name": delivery.get("client_name")}
        )
        
        return {
            "success": True,
            "delivery_id": delivery_id,
            "status": "sent",
            "sent_to": to_emails,
            "message": f"Delivery envoyée à {', '.join(to_emails)}"
        }
        
    except Exception as e:
        # 🔒 Marquer comme failed via state machine
        try:
            await mark_delivery_failed(
                delivery_id=delivery_id,
                error=str(e),
                increment_attempts=True
            )
        except Exception as sm_err:
            # CRITICAL: state machine elle-même a échoué - ne PAS bypass
            logger.critical(
                f"[DELIVERY_CRITICAL] State machine failed for delivery {delivery_id}: "
                f"original_error={str(e)} sm_error={str(sm_err)}"
            )
        
        logger.error(f"[DELIVERY_FAILED] id={delivery_id} error={str(e)}")
        
        from services.event_logger import log_event as _log_fail
        await _log_fail(
            action="delivery_failed",
            entity_type="delivery",
            entity_id=delivery_id,
            entity=delivery.get("entity", ""),
            user=user.get("email"),
            details={"error": str(e)[:200]},
            related={"lead_id": delivery.get("lead_id"), "client_id": delivery.get("client_id")}
        )
        
        raise HTTPException(status_code=500, detail=f"Erreur d'envoi: {str(e)}")


# ---- Reject leads (rejet client) ----

@router.post("/{delivery_id}/reject-leads")
async def reject_delivery_leads(
    delivery_id: str,
    data: RejectDeliveryRequest = RejectDeliveryRequest(),
    user: dict = Depends(require_admin)
):
    """
    Rejet client: le lead redevient un lead entrant neuf.
    
    Comportement:
    - delivery.outcome = "rejected" (delivery.status inchangé, CSV intact)
    - lead.status = "new" (re-routable comme un lead frais)
    - Références delivery supprimées du lead
    - Idempotent: rejeter 2x = pas d'erreur
    
    Billing: billable = status=sent AND outcome=accepted
    """
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    # Seul un delivery "sent" peut être rejeté (on a bien livré, le client refuse)
    if delivery.get("status") != "sent":
        raise HTTPException(
            status_code=400,
            detail=f"Rejet impossible: delivery status={delivery.get('status')} (doit être sent)"
        )
    
    # Idempotency: déjà rejeté → retour OK
    if delivery.get("outcome") == "rejected":
        return {
            "success": True,
            "delivery_id": delivery_id,
            "outcome": "rejected",
            "already_rejected": True,
            "message": "Delivery déjà rejetée"
        }
    
    now = now_iso()
    lead_id = delivery.get("lead_id")
    
    # 1. Marquer la delivery comme rejected (status reste "sent", CSV intact)
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "outcome": "rejected",
            "rejected_at": now,
            "rejected_by": user.get("email"),
            "rejection_reason": data.reason or "",
            "updated_at": now
        }}
    )
    
    # 2. Reset le lead: status=new, supprimer références delivery
    await db.leads.update_one(
        {"id": lead_id},
        {
            "$set": {
                "status": "new",
                "updated_at": now
            },
            "$unset": {
                "delivered_at": "",
                "delivered_to_client_id": "",
                "delivered_to_client_name": "",
                "delivery_commande_id": "",
                "delivery_id": "",
                "routed_at": "",
                "delivery_client_id": "",
                "delivery_client_name": ""
            }
        }
    )
    
    # Event log
    from services.event_logger import log_event
    await log_event(
        action="reject_lead",
        entity_type="delivery",
        entity_id=delivery_id,
        entity=delivery.get("entity", ""),
        user=user.get("email"),
        details={"reason": data.reason or ""},
        related={"lead_id": lead_id, "client_id": delivery.get("client_id"), "client_name": delivery.get("client_name"), "produit": delivery.get("produit")}
    )
    
    logger.info(
        f"[REJECT] delivery={delivery_id} lead={lead_id} "
        f"by={user.get('email')} reason={data.reason or 'N/A'}"
    )
    
    return {
        "success": True,
        "delivery_id": delivery_id,
        "lead_id": lead_id,
        "outcome": "rejected",
        "already_rejected": False,
        "message": f"Lead {lead_id} rejeté et remis en circulation"
    }


# ---- Remove lead from delivery ----

REMOVE_REASONS = ["refus_client", "doublon", "hors_zone", "mauvaise_commande", "test", "autre"]

class RemoveLeadRequest(BaseModel):
    reason: str = ""
    reason_detail: Optional[str] = ""


@router.post("/{delivery_id}/remove-lead")
async def remove_lead_from_delivery(
    delivery_id: str,
    data: RemoveLeadRequest = RemoveLeadRequest(),
    user: dict = Depends(require_admin)
):
    """
    Retirer un lead d'une livraison.
    
    - delivery.outcome = "removed" (status + CSV inchangés)
    - lead.status = "new" (re-routable)
    - Event log écrit
    - billable = status=sent AND outcome=accepted (removed = non facturable)
    - Idempotent
    """
    delivery = await db.deliveries.find_one({"id": delivery_id}, {"_id": 0})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery non trouvée")
    
    if delivery.get("status") != "sent":
        raise HTTPException(status_code=400, detail=f"Retrait impossible: status={delivery.get('status')} (doit être sent)")
    
    # Idempotent
    if delivery.get("outcome") == "removed":
        return {"success": True, "delivery_id": delivery_id, "outcome": "removed", "already_removed": True}
    
    # Cannot remove if already rejected
    if delivery.get("outcome") == "rejected":
        raise HTTPException(status_code=400, detail="Delivery déjà rejetée — utiliser reject-leads pour les rejets client")
    
    reason = data.reason or "autre"
    now = now_iso()
    lead_id = delivery.get("lead_id")
    
    # 1. Annotate delivery
    await db.deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "outcome": "removed",
            "removed_at": now,
            "removed_by": user.get("email"),
            "removal_reason": reason,
            "removal_detail": data.reason_detail or "",
            "updated_at": now
        }}
    )
    
    # 2. Reset lead to new (re-routable)
    await db.leads.update_one(
        {"id": lead_id},
        {
            "$set": {"status": "new", "updated_at": now},
            "$unset": {
                "delivered_at": "",
                "delivered_to_client_id": "",
                "delivered_to_client_name": "",
                "delivery_commande_id": "",
                "delivery_id": "",
                "routed_at": "",
                "delivery_client_id": "",
                "delivery_client_name": ""
            }
        }
    )
    
    # 3. Event log
    from services.event_logger import log_event
    await log_event(
        action="lead_removed_from_delivery",
        entity_type="delivery",
        entity_id=delivery_id,
        entity=delivery.get("entity", ""),
        user=user.get("email"),
        details={"reason": reason, "detail": data.reason_detail or ""},
        related={"lead_id": lead_id, "client_id": delivery.get("client_id"), "client_name": delivery.get("client_name"), "produit": delivery.get("produit")}
    )
    
    logger.info(f"[REMOVE] delivery={delivery_id} lead={lead_id} reason={reason} by={user.get('email')}")
    
    return {
        "success": True,
        "delivery_id": delivery_id,
        "lead_id": lead_id,
        "outcome": "removed",
        "reason": reason,
        "already_removed": False
    }


# ---- Download CSV ----

@router.get("/{delivery_id}/download")
async def download_delivery_csv(
    delivery_id: str,
    user: dict = Depends(require_permission("deliveries.view"))
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
    
    🔒 Utilise delivery_state_machine pour les transitions
    """
    from services.delivery_state_machine import mark_delivery_ready_to_send, DeliveryInvariantError
    
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
            
            d_entity = delivery.get("entity")
            produit = delivery.get("produit")
            
            csv_content = generate_csv_content([lead], produit, d_entity)
            csv_filename = f"lead_{d_entity}_{produit}_{lead.get('id')[:8]}.csv"
            
            # 🔒 Via state machine uniquement
            await mark_delivery_ready_to_send(
                delivery_id=delivery.get("id"),
                csv_content=csv_content,
                csv_filename=csv_filename
            )
            processed += 1
            
        except DeliveryInvariantError as e:
            logger.warning(f"[BATCH_CSV] Transition refusée: {str(e)}")
            errors.append({"delivery_id": delivery.get("id"), "error": str(e)})
        except Exception as e:
            errors.append({"delivery_id": delivery.get("id"), "error": str(e)})
    
    return {
        "success": True,
        "processed": processed,
        "errors": errors
    }


@router.post("/batch/send-ready")
async def batch_send_ready(
    entity: Optional[str] = None,
    client_id: Optional[str] = None,
    override_email: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """
    Envoie toutes les deliveries ready_to_send (groupées par client)
    
    - Respecte le calendar gating
    - Utilise le CSV déjà généré
    - 🔒 Utilise delivery_state_machine pour les transitions
    """
    from services.settings import is_delivery_day_enabled, get_simulation_email_override
    from services.csv_delivery import send_csv_email
    from services.delivery_state_machine import (
        batch_mark_deliveries_sent,
        batch_mark_deliveries_failed,
        DeliveryInvariantError
    )
    from collections import defaultdict
    
    query = {"status": "ready_to_send"}
    if entity:
        query["entity"] = entity.upper()
    if client_id:
        query["client_id"] = client_id
    
    ready = await db.deliveries.find(query, {"_id": 0}).to_list(1000)
    
    if not ready:
        return {"success": True, "sent": 0, "message": "Aucune delivery ready_to_send"}
    
    results = {
        "sent": 0,
        "skipped_calendar": 0,
        "errors": []
    }
    
    simulation_email = await get_simulation_email_override()
    
    grouped = defaultdict(list)
    for delivery in ready:
        key = (delivery.get("client_id"), delivery.get("commande_id"), delivery.get("entity"))
        grouped[key].append(delivery)
    
    for (grp_client_id, grp_commande_id, grp_entity), deliveries in grouped.items():
        # Calendar gating
        day_enabled, day_reason = await is_delivery_day_enabled(grp_entity)
        if not day_enabled:
            logger.info(f"[BATCH_SEND] {grp_entity}: {day_reason} - skipped")
            results["skipped_calendar"] += len(deliveries)
            continue
        
        client = await db.clients.find_one({"id": grp_client_id}, {"_id": 0})
        if not client:
            results["errors"].append({"client_id": grp_client_id, "error": "client_not_found"})
            continue
        
        client_name = client.get("name", "")
        
        if override_email:
            to_emails = [override_email]
        elif simulation_email:
            to_emails = [simulation_email]
        else:
            to_emails = client.get("delivery_emails", [])
            if not to_emails and client.get("email"):
                to_emails = [client.get("email")]
        
        if not to_emails:
            results["errors"].append({"client": client_name, "error": "no_email"})
            continue
        
        lead_ids = [d.get("lead_id") for d in deliveries]
        leads = await db.leads.find(
            {"id": {"$in": lead_ids}},
            {"_id": 0}
        ).to_list(len(lead_ids))
        
        if not leads:
            continue
        
        produit = deliveries[0].get("produit", "")
        csv_content = generate_csv_content(leads, produit, grp_entity)
        csv_filename = f"leads_{grp_entity}_{produit}_{now_iso()[:10].replace('-', '')}_{len(leads)}.csv"
        lb_count = sum(1 for lead in leads if lead.get("is_lb"))
        delivery_ids = [d.get("id") for d in deliveries]
        
        try:
            # 1. Envoyer l'email RÉELLEMENT
            await send_csv_email(
                entity=grp_entity,
                to_emails=to_emails,
                csv_content=csv_content,
                csv_filename=csv_filename,
                lead_count=len(leads),
                lb_count=lb_count,
                produit=produit
            )
            
            # 2. 🔒 SEULEMENT après envoi réussi: state machine
            await batch_mark_deliveries_sent(
                delivery_ids=delivery_ids,
                lead_ids=lead_ids,
                sent_to=to_emails,
                client_id=grp_client_id,
                client_name=client_name,
                commande_id=grp_commande_id or ""
            )
            
            # 3. Stocker CSV pour téléchargement
            await db.deliveries.update_many(
                {"id": {"$in": delivery_ids}},
                {"$set": {
                    "csv_content": csv_content,
                    "csv_filename": csv_filename,
                    "csv_generated_at": now_iso(),
                    "sent_by": user.get("email")
                }}
            )
            
            results["sent"] += len(leads)
            logger.info(f"[BATCH_SEND] {client_name}: {len(leads)} leads sent to {to_emails}")
            
        except Exception as e:
            # 🔒 Marquer comme failed via state machine
            try:
                await batch_mark_deliveries_failed(
                    delivery_ids=delivery_ids,
                    error=str(e)
                )
            except DeliveryInvariantError:
                logger.error(f"[BATCH_SEND] State machine failed for batch: {str(e)}")
            
            results["errors"].append({"client": client_name, "error": str(e)})
    
    return {
        "success": True,
        "sent": results["sent"],
        "skipped_calendar": results["skipped_calendar"],
        "errors": results["errors"]
    }

