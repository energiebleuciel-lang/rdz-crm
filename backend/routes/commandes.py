"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Routes Commandes (Refonte spec RDZ)                               ║
║                                                                              ║
║  CRUD pour les commandes hebdomadaires                                       ║
║  Multi-tenant strict: toutes les requêtes filtrées par entity                ║
║                                                                              ║
║  Une commande = demande d'un client pour des leads                           ║
║  - Par produit, par départements                                             ║
║  - Quota semaine, prix, % LB autorisé                                        ║
║  - Priorité pour routing                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid

from config import db, now_iso
from routes.auth import get_current_user
from models import (
    EntityType,
    CommandeCreate,
    CommandeUpdate,
    CommandeResponse,
    DEPARTEMENTS_METRO,
    VALID_PRODUCTS,
    validate_entity
)
from services.routing_engine import get_week_start, get_commande_stats

router = APIRouter(prefix="/commandes", tags=["Commandes"])


@router.get("")
async def list_commandes(
    entity: str = Query(..., description="Entité obligatoire: ZR7 ou MDL"),
    client_id: Optional[str] = Query(None, description="Filtrer par client"),
    produit: Optional[str] = Query(None, description="Filtrer par produit"),
    active_only: bool = Query(True, description="Uniquement les commandes actives"),
    user: dict = Depends(get_current_user)
):
    """
    Liste les commandes d'une entité
    
    RÈGLE: entity est OBLIGATOIRE
    """
    if not validate_entity(entity):
        raise HTTPException(status_code=400, detail="Entity invalide. Doit être ZR7 ou MDL")
    
    query = {"entity": entity}
    if client_id:
        query["client_id"] = client_id
    if produit:
        query["produit"] = produit
    if active_only:
        query["active"] = True
    
    commandes = await db.commandes.find(query, {"_id": 0}).sort("priorite", 1).to_list(500)
    
    # Enrichir avec nom client et stats
    week_start = get_week_start()
    
    for cmd in commandes:
        # Nom client
        client = await db.clients.find_one(
            {"id": cmd.get("client_id")}, 
            {"_id": 0, "name": 1}
        )
        cmd["client_name"] = client.get("name", "") if client else "Inconnu"
        
        # Stats semaine
        stats = await get_commande_stats(cmd.get("id"), week_start)
        cmd["leads_delivered_this_week"] = stats.get("leads_delivered", 0)
        cmd["lb_delivered_this_week"] = stats.get("lb_delivered", 0)
        
        # Quota restant
        quota = cmd.get("quota_semaine", 0)
        if quota > 0:
            cmd["quota_remaining"] = max(0, quota - stats.get("leads_delivered", 0))
        else:
            cmd["quota_remaining"] = "illimité"
        
        cmd["week_start"] = week_start
    
    return {
        "commandes": commandes,
        "count": len(commandes),
        "entity": entity
    }


@router.get("/departements")
async def list_departements(user: dict = Depends(get_current_user)):
    """Retourne la liste des départements métropole valides"""
    return {
        "departements": DEPARTEMENTS_METRO,
        "count": len(DEPARTEMENTS_METRO),
        "note": "Métropole France (01-95), hors Corse"
    }


@router.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    """Retourne la liste des produits"""
    return {
        "products": VALID_PRODUCTS,
        "note": "Produits disponibles: PV, PAC, ITE"
    }


@router.get("/{commande_id}")
async def get_commande(
    commande_id: str,
    user: dict = Depends(get_current_user)
):
    """Récupère une commande par ID"""
    cmd = await db.commandes.find_one({"id": commande_id}, {"_id": 0})
    
    if not cmd:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    # Enrichir
    client = await db.clients.find_one(
        {"id": cmd.get("client_id")}, 
        {"_id": 0, "name": 1}
    )
    cmd["client_name"] = client.get("name", "") if client else "Inconnu"
    
    week_start = get_week_start()
    stats = await get_commande_stats(commande_id, week_start)
    cmd["leads_delivered_this_week"] = stats.get("leads_delivered", 0)
    cmd["lb_delivered_this_week"] = stats.get("lb_delivered", 0)
    
    return {"commande": cmd}


@router.post("")
async def create_commande(
    data: CommandeCreate,
    user: dict = Depends(get_current_user)
):
    """
    Crée une nouvelle commande
    
    Entity et client_id sont OBLIGATOIRES
    """
    # Vérifier que le client existe et appartient à la même entity
    client = await db.clients.find_one({
        "id": data.client_id,
        "entity": data.entity.value
    })
    if not client:
        raise HTTPException(
            status_code=404, 
            detail=f"Client non trouvé ou n'appartient pas à {data.entity.value}"
        )
    
    # Vérifier qu'une commande similaire n'existe pas déjà
    existing = await db.commandes.find_one({
        "entity": data.entity.value,
        "client_id": data.client_id,
        "produit": data.produit.value,
        "active": True
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Une commande active existe deja pour ce client/produit"
        )
    
    commande = {
        "id": str(uuid.uuid4()),
        "entity": data.entity.value,
        "client_id": data.client_id,
        "produit": data.produit.value,
        "departements": data.departements,
        "quota_semaine": data.quota_semaine,
        "prix_lead": data.prix_lead,
        "lb_percent_max": data.lb_percent_max,
        "priorite": data.priorite,
        "auto_renew": data.auto_renew,
        "remise_percent": data.remise_percent,
        "notes": data.notes or "",
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    
    await db.commandes.insert_one(commande)
    commande.pop("_id", None)
    
    # Ajouter nom client
    commande["client_name"] = client.get("name", "")
    
    return {"success": True, "commande": commande}


@router.put("/{commande_id}")
async def update_commande(
    commande_id: str,
    data: CommandeUpdate,
    user: dict = Depends(get_current_user)
):
    """Met à jour une commande"""
    cmd = await db.commandes.find_one({"id": commande_id})
    if not cmd:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.commandes.update_one(
        {"id": commande_id},
        {"$set": update_data}
    )
    
    updated = await db.commandes.find_one({"id": commande_id}, {"_id": 0})
    
    # Enrichir
    client = await db.clients.find_one(
        {"id": updated.get("client_id")}, 
        {"_id": 0, "name": 1}
    )
    updated["client_name"] = client.get("name", "") if client else "Inconnu"
    
    # Log if active status changed
    old_active = cmd.get("active")
    new_active = updated.get("active")
    if old_active != new_active and new_active is not None:
        from services.event_logger import log_event
        await log_event(
            action="order_activate" if new_active else "order_deactivate",
            entity_type="commande",
            entity_id=commande_id,
            entity=updated.get("entity", ""),
            user=user.get("email"),
            details={"old_active": old_active, "new_active": new_active},
            related={"client_id": updated.get("client_id"), "client_name": updated.get("client_name"), "produit": updated.get("produit")}
        )
    
    return {"success": True, "commande": updated}


@router.delete("/{commande_id}")
async def delete_commande(
    commande_id: str,
    user: dict = Depends(get_current_user)
):
    """Supprime une commande"""
    result = await db.commandes.delete_one({"id": commande_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    return {"success": True, "deleted_id": commande_id}


@router.post("/{commande_id}/toggle")
async def toggle_commande(
    commande_id: str,
    user: dict = Depends(get_current_user)
):
    """Active/désactive une commande"""
    cmd = await db.commandes.find_one({"id": commande_id})
    if not cmd:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    new_status = not cmd.get("active", True)
    
    await db.commandes.update_one(
        {"id": commande_id},
        {"$set": {"active": new_status, "updated_at": now_iso()}}
    )
    
    from services.event_logger import log_event
    await log_event(
        action="order_activate" if new_status else "order_deactivate",
        entity_type="commande",
        entity_id=commande_id,
        entity=cmd.get("entity", ""),
        user=user.get("email"),
        details={"active": new_status},
        related={"client_id": cmd.get("client_id"), "produit": cmd.get("produit")}
    )
    
    return {"success": True, "active": new_status}


@router.get("/{commande_id}/stats")
async def get_commande_stats_endpoint(
    commande_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Statistiques détaillées d'une commande
    """
    cmd = await db.commandes.find_one({"id": commande_id}, {"_id": 0})
    if not cmd:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    week_start = get_week_start()
    stats = await get_commande_stats(commande_id, week_start)
    
    # Stats globales
    total_delivered = await db.leads.count_documents({
        "delivery_commande_id": commande_id,
        "status": "livre"
    })
    
    # Par semaine (4 dernières)
    from datetime import datetime, timezone, timedelta
    weeks_stats = []
    for i in range(4):
        start = (datetime.now(timezone.utc) - timedelta(weeks=i+1)).isoformat()
        end = (datetime.now(timezone.utc) - timedelta(weeks=i)).isoformat()
        count = await db.leads.count_documents({
            "delivery_commande_id": commande_id,
            "status": "livre",
            "delivered_at": {"$gte": start, "$lt": end}
        })
        weeks_stats.append({"week_offset": -i-1, "delivered": count})
    
    return {
        "commande_id": commande_id,
        "current_week": {
            "start": week_start,
            "delivered": stats.get("leads_delivered", 0),
            "lb_delivered": stats.get("lb_delivered", 0),
            "quota": cmd.get("quota_semaine", 0)
        },
        "total_delivered": total_delivered,
        "last_4_weeks": weeks_stats
    }
