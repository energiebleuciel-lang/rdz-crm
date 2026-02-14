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
    """
    Statistiques détaillées d'un client
    """
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    from services.routing_engine import get_week_start
    week_start = get_week_start()
    
    # Stats globales
    total_delivered = await db.leads.count_documents({
        "delivered_to_client_id": client_id,
        "status": "livre"
    })
    
    this_week = await db.leads.count_documents({
        "delivered_to_client_id": client_id,
        "status": "livre",
        "delivered_at": {"$gte": week_start}
    })
    
    # Par produit
    pipeline = [
        {"$match": {"delivered_to_client_id": client_id, "status": "livre"}},
        {"$group": {
            "_id": "$produit",
            "count": {"$sum": 1}
        }}
    ]
    by_product = await db.leads.aggregate(pipeline).to_list(10)
    
    # Rejets
    rejected_count = await db.leads.count_documents({
        "delivered_to_client_id": client_id,
        "status": "rejet_client"
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
