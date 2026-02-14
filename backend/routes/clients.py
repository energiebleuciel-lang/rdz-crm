"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Routes Clients                                                    ║
║                                                                              ║
║  CRUD pour les clients acheteurs de leads                                    ║
║  Multi-tenant strict: toutes les requêtes filtrées par entity                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid

from config import db, now_iso
from routes.auth import get_current_user
from models import (
    EntityType,
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    validate_entity
)

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("")
async def list_clients(
    entity: str = Query(..., description="Entité obligatoire: ZR7 ou MDL"),
    active_only: bool = Query(True, description="Filtrer les clients actifs uniquement"),
    user: dict = Depends(get_current_user)
):
    """
    Liste tous les clients d'une entité
    
    RÈGLE: entity est OBLIGATOIRE
    """
    if not validate_entity(entity):
        raise HTTPException(status_code=400, detail="Entity invalide. Doit être ZR7 ou MDL")
    
    query = {"entity": entity}
    if active_only:
        query["active"] = True
    
    clients = await db.clients.find(query, {"_id": 0}).to_list(500)
    
    # Enrichir avec stats + deliverability
    from models.client import check_client_deliverable
    from services.settings import get_email_denylist_settings
    denylist_settings = await get_email_denylist_settings()
    denylist = denylist_settings.get("domains", [])
    
    for client in clients:
        # Deliverability check
        check = check_client_deliverable(
            email=client.get("email", ""),
            delivery_emails=client.get("delivery_emails", []),
            api_endpoint=client.get("api_endpoint", ""),
            denylist=denylist
        )
        client["has_valid_channel"] = check["deliverable"]
        client["deliverable_reason"] = check.get("reason")
        
        # Ensure auto_send_enabled is present
        if "auto_send_enabled" not in client:
            client["auto_send_enabled"] = True
        
        # Compter les leads livrés
        delivered_count = await db.leads.count_documents({
            "delivered_to_client_id": client.get("id"),
            "status": "livre"
        })
        client["total_leads_received"] = delivered_count
        
        # Leads cette semaine
        from services.routing_engine import get_week_start
        week_start = get_week_start()
        week_count = await db.leads.count_documents({
            "delivered_to_client_id": client.get("id"),
            "status": "livre",
            "delivered_at": {"$gte": week_start}
        })
        client["total_leads_this_week"] = week_count
    
    return {
        "clients": clients,
        "count": len(clients),
        "entity": entity
    }


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Récupère un client par ID"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Stats
    delivered_count = await db.leads.count_documents({
        "delivered_to_client_id": client_id,
        "status": "livre"
    })
    client["total_leads_received"] = delivered_count
    
    return {"client": client}


@router.post("")
async def create_client(
    data: ClientCreate,
    user: dict = Depends(get_current_user)
):
    """
    Crée un nouveau client
    
    Entity est OBLIGATOIRE dans le body
    """
    # Vérifier que l'email n'existe pas déjà pour cette entity
    existing = await db.clients.find_one({
        "entity": data.entity.value,
        "email": data.email
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Un client avec cet email existe déjà pour {data.entity.value}"
        )
    
    client = {
        "id": str(uuid.uuid4()),
        "entity": data.entity.value,
        "name": data.name,
        "contact_name": data.contact_name or "",
        "email": data.email,
        "phone": data.phone or "",
        "delivery_emails": data.delivery_emails or [],
        "api_endpoint": data.api_endpoint or "",
        "api_key": data.api_key or "",
        "auto_send_enabled": data.auto_send_enabled,  # Phase 2.5: contrôle envoi auto
        "default_prix_lead": data.default_prix_lead,
        "remise_percent": data.remise_percent,
        "notes": data.notes or "",
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    
    await db.clients.insert_one(client)
    client.pop("_id", None)
    
    return {"success": True, "client": client}


@router.put("/{client_id}")
async def update_client(
    client_id: str,
    data: ClientUpdate,
    user: dict = Depends(get_current_user)
):
    """Met à jour un client"""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": update_data}
    )
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return {"success": True, "client": updated}


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Supprime un client
    
    ATTENTION: Vérifie qu'aucune commande active n'est liée
    """
    # Vérifier les commandes actives
    active_commandes = await db.commandes.count_documents({
        "client_id": client_id,
        "active": True
    })
    if active_commandes > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de supprimer: {active_commandes} commande(s) active(s)"
        )
    
    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return {"success": True, "deleted_id": client_id}


@router.get("/{client_id}/leads")
async def get_client_leads(
    client_id: str,
    limit: int = Query(50, le=200),
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Liste les leads livrés à un client
    """
    query = {"delivered_to_client_id": client_id}
    if status:
        query["status"] = status
    
    leads = await db.leads.find(
        query, 
        {"_id": 0}
    ).sort("delivered_at", -1).limit(limit).to_list(limit)
    
    return {
        "leads": leads,
        "count": len(leads),
        "client_id": client_id
    }


@router.get("/{client_id}/stats")
async def get_client_stats(
    client_id: str,
    user: dict = Depends(get_current_user)
):
    """Statistiques détaillées d'un client"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    from services.routing_engine import get_week_start
    week_start = get_week_start()
    
    total_delivered = await db.leads.count_documents({
        "delivered_to_client_id": client_id, "status": "livre"
    })
    this_week = await db.leads.count_documents({
        "delivered_to_client_id": client_id, "status": "livre",
        "delivered_at": {"$gte": week_start}
    })
    pipeline = [
        {"$match": {"delivered_to_client_id": client_id, "status": "livre"}},
        {"$group": {"_id": "$produit", "count": {"$sum": 1}}}
    ]
    by_product = await db.leads.aggregate(pipeline).to_list(10)
    rejected_count = await db.leads.count_documents({
        "delivered_to_client_id": client_id, "status": "rejet_client"
    })
    
    return {
        "client_id": client_id,
        "client_name": client.get("name"),
        "stats": {
            "total_delivered": total_delivered,
            "this_week": this_week,
            "by_product": {p["_id"]: p["count"] for p in by_product},
            "rejected": rejected_count,
            "rejection_rate": (rejected_count / total_delivered * 100) if total_delivered > 0 else 0
        }
    }


@router.get("/{client_id}/summary")
async def get_client_summary(
    client_id: str,
    group_by: str = Query("day", description="day|week|month"),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    user: dict = Depends(get_current_user)
):
    """
    Aggregation endpoint for client performance.
    Returns delivery stats grouped by day/week/month.
    """
    from datetime import datetime, timezone, timedelta
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    # Date range
    now = datetime.now(timezone.utc)
    if from_date:
        date_from = from_date
    else:
        date_from = (now - timedelta(days=30)).isoformat()
    date_to = to_date or now.isoformat()
    
    # Delivery aggregation
    match = {
        "client_id": client_id,
        "created_at": {"$gte": date_from, "$lte": date_to}
    }
    
    # Group key based on group_by
    if group_by == "month":
        group_expr = {"$substr": ["$created_at", 0, 7]}  # YYYY-MM
    elif group_by == "week":
        group_expr = {"$substr": ["$created_at", 0, 10]}  # YYYY-MM-DD (we'll bucket later)
    else:
        group_expr = {"$substr": ["$created_at", 0, 10]}  # YYYY-MM-DD
    
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {
                "period": group_expr,
                "produit": "$produit",
                "status": "$status"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.period": 1}}
    ]
    
    raw = await db.deliveries.aggregate(pipeline).to_list(500)
    
    # Also get outcome stats
    outcome_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {
                "period": group_expr,
                "outcome": {"$ifNull": ["$outcome", "accepted"]}
            },
            "count": {"$sum": 1}
        }}
    ]
    outcome_raw = await db.deliveries.aggregate(outcome_pipeline).to_list(200)
    
    # Flatten into periods
    periods = {}
    for r in raw:
        p = r["_id"]["period"]
        if p not in periods:
            periods[p] = {"period": p, "sent": 0, "failed": 0, "ready_to_send": 0, "pending_csv": 0, "by_produit": {}}
        status = r["_id"]["status"]
        count = r["count"]
        produit = r["_id"].get("produit", "?")
        if status in periods[p]:
            periods[p][status] += count
        if produit not in periods[p]["by_produit"]:
            periods[p]["by_produit"][produit] = 0
        if status == "sent":
            periods[p]["by_produit"][produit] += count
    
    for r in outcome_raw:
        p = r["_id"]["period"]
        if p not in periods:
            periods[p] = {"period": p, "sent": 0, "failed": 0, "ready_to_send": 0, "pending_csv": 0, "by_produit": {}}
        outcome = r["_id"]["outcome"]
        if outcome == "rejected":
            periods[p]["rejected"] = periods[p].get("rejected", 0) + r["count"]
    
    # Compute billable + reject_rate
    result = []
    for p in sorted(periods.values(), key=lambda x: x["period"]):
        sent = p.get("sent", 0)
        rejected = p.get("rejected", 0)
        billable = sent - rejected
        p["billable"] = max(0, billable)
        p["reject_rate"] = round(rejected / sent * 100, 1) if sent > 0 else 0
        result.append(p)
    
    # Totals
    total_sent = sum(p.get("sent", 0) for p in result)
    total_rejected = sum(p.get("rejected", 0) for p in result)
    total_failed = sum(p.get("failed", 0) for p in result)
    total_billable = sum(p.get("billable", 0) for p in result)
    
    # Last delivery info
    last_delivery = await db.deliveries.find_one(
        {"client_id": client_id, "status": "sent"},
        {"_id": 0, "created_at": 1, "sent_to": 1, "last_sent_at": 1}
    , sort=[("last_sent_at", -1)])
    
    # Next delivery day
    from services.settings import get_delivery_calendar_settings
    cal = await get_delivery_calendar_settings()
    entity_days = cal.get(client.get("entity", ""), {}).get("enabled_days", [0,1,2,3,4])
    today_weekday = now.weekday()
    next_day = None
    for i in range(1, 8):
        check = (today_weekday + i) % 7
        if check in entity_days:
            next_day = (now + timedelta(days=i)).strftime("%A %d/%m")
            break
    
    return {
        "client_id": client_id,
        "client_name": client.get("name"),
        "entity": client.get("entity"),
        "group_by": group_by,
        "from": date_from[:10],
        "to": date_to[:10],
        "periods": result,
        "totals": {
            "sent": total_sent,
            "rejected": total_rejected,
            "failed": total_failed,
            "billable": total_billable,
            "reject_rate": round(total_rejected / total_sent * 100, 1) if total_sent > 0 else 0
        },
        "last_delivery": {
            "sent_at": last_delivery.get("last_sent_at") if last_delivery else None,
            "sent_to": last_delivery.get("sent_to") if last_delivery else None
        },
        "next_delivery_day": next_day,
        "auto_send_enabled": client.get("auto_send_enabled", True)
    }


@router.put("/{client_id}/crm")
async def update_client_crm(
    client_id: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Update CRM-specific fields on a client (ratings, payment, tags, notes)."""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    allowed_fields = {
        "global_rating", "payment_rating", "lead_satisfaction_rating",
        "discount_pressure_rating", "client_status", "payment_terms",
        "payment_method", "last_payment_date", "last_payment_amount",
        "accounting_status", "tags"
    }
    
    update = {}
    for k, v in data.items():
        if k in allowed_fields:
            update[k] = v
    
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ valide")
    
    update["updated_at"] = now_iso()
    await db.clients.update_one({"id": client_id}, {"$set": update})
    
    # Log activity
    await db.client_activity.insert_one({
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": "crm_update",
        "details": {k: v for k, v in update.items() if k != "updated_at"},
        "user": user.get("email"),
        "created_at": now_iso()
    })
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return {"success": True, "client": updated}


@router.post("/{client_id}/notes")
async def add_client_note(
    client_id: str,
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Add a timestamped internal note to a client."""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    note_text = data.get("text", "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note vide")
    
    note = {
        "id": str(uuid.uuid4()),
        "text": note_text,
        "author": user.get("email"),
        "created_at": now_iso()
    }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"internal_notes": note}, "$set": {"updated_at": now_iso()}}
    )
    
    # Log activity
    await db.client_activity.insert_one({
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "action": "note_added",
        "details": {"text": note_text[:100]},
        "user": user.get("email"),
        "created_at": now_iso()
    })
    
    return {"success": True, "note": note}


@router.get("/{client_id}/activity")
async def get_client_activity(
    client_id: str,
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user)
):
    """Get activity timeline for a client (rejects, resends, CRM updates, notes, etc.)."""
    # Combine delivery events + explicit activity log
    activities = []
    
    # 1. Explicit activity log
    logs = await db.client_activity.find(
        {"client_id": client_id}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    activities.extend(logs)
    
    # 2. Delivery rejection events
    rejected = await db.deliveries.find(
        {"client_id": client_id, "outcome": "rejected"},
        {"_id": 0, "id": 1, "lead_id": 1, "rejected_at": 1, "rejected_by": 1, "rejection_reason": 1, "produit": 1}
    ).sort("rejected_at", -1).limit(20).to_list(20)
    
    for r in rejected:
        activities.append({
            "id": f"reject_{r['id']}",
            "client_id": client_id,
            "action": "delivery_rejected",
            "details": {"delivery_id": r["id"], "reason": r.get("rejection_reason"), "produit": r.get("produit")},
            "user": r.get("rejected_by"),
            "created_at": r.get("rejected_at")
        })
    
    # 3. Failed deliveries
    failed = await db.deliveries.find(
        {"client_id": client_id, "status": "failed"},
        {"_id": 0, "id": 1, "last_error": 1, "updated_at": 1, "produit": 1}
    ).sort("updated_at", -1).limit(10).to_list(10)
    
    for f in failed:
        activities.append({
            "id": f"fail_{f['id']}",
            "client_id": client_id,
            "action": "delivery_failed",
            "details": {"delivery_id": f["id"], "error": f.get("last_error"), "produit": f.get("produit")},
            "user": "system",
            "created_at": f.get("updated_at")
        })
    
    # Sort all by date
    activities.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    return {"activities": activities[:limit], "count": len(activities)}
