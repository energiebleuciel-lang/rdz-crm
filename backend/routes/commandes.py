"""
Routes pour les Commandes
- Gestion des commandes de leads par CRM/produit/département
- Logique de routage cross-CRM
"""

from fastapi import APIRouter, Depends, HTTPException
from config import db, now_iso
from routes.auth import get_current_user
from models import CommandeCreate, CommandeUpdate
import uuid

router = APIRouter(prefix="/commandes", tags=["Commandes"])

# Départements métropole (01-95 sauf 2A/2B)
DEPARTEMENTS_METRO = [str(i).zfill(2) for i in range(1, 96) if i not in [20]]
# 20 est remplacé par 2A et 2B qu'on exclut

PRODUCT_TYPES = ["PV", "PAC", "ITE"]


@router.get("")
async def list_commandes(crm_id: str = None, user: dict = Depends(require_auth)):
    """Liste toutes les commandes, optionnellement filtrées par CRM"""
    query = {}
    if crm_id:
        query["crm_id"] = crm_id
    
    commandes = await db.commandes.find(query, {"_id": 0}).to_list(500)
    
    # Enrichir avec le nom du CRM
    for cmd in commandes:
        crm = await db.crms.find_one({"id": cmd.get("crm_id")}, {"_id": 0, "name": 1, "slug": 1})
        cmd["crm_name"] = crm.get("name") if crm else "Inconnu"
        cmd["crm_slug"] = crm.get("slug") if crm else ""
    
    return {"commandes": commandes, "count": len(commandes)}


@router.get("/check")
async def check_commande(crm_id: str, product_type: str, departement: str, user: dict = Depends(require_auth)):
    """
    Vérifie si un CRM a une commande active pour un produit/département
    Retourne True/False
    """
    result = await has_commande(crm_id, product_type, departement)
    return {"has_commande": result, "crm_id": crm_id, "product_type": product_type, "departement": departement}


async def has_commande(crm_id: str, product_type: str, departement: str) -> bool:
    """
    Vérifie si un CRM a une commande active pour un produit/département donné.
    Utilisé par le routage des leads.
    """
    # Chercher une commande active qui match
    commande = await db.commandes.find_one({
        "crm_id": crm_id,
        "active": True,
        "$or": [
            # Match exact sur le produit
            {"product_type": product_type},
            # Ou wildcard (tous les produits)
            {"product_type": "*"}
        ]
    })
    
    if not commande:
        return False
    
    departements = commande.get("departements", [])
    
    # Wildcard = tous les départements
    if "*" in departements:
        return True
    
    # Match exact sur le département
    return departement in departements


@router.post("")
async def create_commande(data: CommandeCreate, user: dict = Depends(require_auth)):
    """Crée une nouvelle commande"""
    # Vérifier que le CRM existe
    crm = await db.crms.find_one({"id": data.crm_id})
    if not crm:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    
    # Valider le product_type
    if data.product_type != "*" and data.product_type not in PRODUCT_TYPES:
        raise HTTPException(status_code=400, detail=f"Product type invalide. Valeurs: {PRODUCT_TYPES} ou *")
    
    # Valider les départements
    if "*" not in data.departements:
        for dept in data.departements:
            if dept not in DEPARTEMENTS_METRO:
                raise HTTPException(status_code=400, detail=f"Département invalide: {dept}")
    
    commande = {
        "id": str(uuid.uuid4()),
        "crm_id": data.crm_id,
        "product_type": data.product_type,
        "departements": data.departements,
        "active": data.active,
        "prix_unitaire": data.prix_unitaire or 0.0,
        "notes": data.notes or "",
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    
    await db.commandes.insert_one(commande)
    commande.pop("_id", None)
    
    return {"success": True, "commande": commande}


@router.put("/{commande_id}")
async def update_commande(commande_id: str, data: CommandeUpdate, user: dict = Depends(require_auth)):
    """Met à jour une commande"""
    commande = await db.commandes.find_one({"id": commande_id})
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    # Valider les départements si fournis
    if "departements" in update_data and "*" not in update_data["departements"]:
        for dept in update_data["departements"]:
            if dept not in DEPARTEMENTS_METRO:
                raise HTTPException(status_code=400, detail=f"Département invalide: {dept}")
    
    update_data["updated_at"] = now_iso()
    
    await db.commandes.update_one(
        {"id": commande_id},
        {"$set": update_data}
    )
    
    updated = await db.commandes.find_one({"id": commande_id}, {"_id": 0})
    return {"success": True, "commande": updated}


@router.delete("/{commande_id}")
async def delete_commande(commande_id: str, user: dict = Depends(require_auth)):
    """Supprime une commande"""
    result = await db.commandes.delete_one({"id": commande_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    
    return {"success": True, "deleted_id": commande_id}


@router.post("/init-defaults")
async def init_default_commandes(user: dict = Depends(require_auth)):
    """
    Initialise les commandes par défaut : tous les produits et tous les départements métro
    pour les deux CRMs (MDL et ZR7)
    """
    # Récupérer les CRMs
    crms = await db.crms.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(10)
    
    if not crms:
        raise HTTPException(status_code=400, detail="Aucun CRM configuré")
    
    created = []
    
    for crm in crms:
        # Vérifier si des commandes existent déjà pour ce CRM
        existing = await db.commandes.count_documents({"crm_id": crm["id"]})
        
        if existing == 0:
            # Créer une commande wildcard (tous produits, tous départements)
            commande = {
                "id": str(uuid.uuid4()),
                "crm_id": crm["id"],
                "product_type": "*",  # Tous les produits
                "departements": ["*"],  # Tous les départements métro
                "active": True,
                "prix_unitaire": 0.0,
                "notes": "Commande par défaut - tous produits/départements",
                "created_at": now_iso(),
                "updated_at": now_iso()
            }
            await db.commandes.insert_one(commande)
            created.append({"crm": crm["name"], "commande_id": commande["id"]})
    
    return {
        "success": True,
        "message": f"{len(created)} commandes créées",
        "created": created
    }


@router.get("/departements")
async def list_departements(user: dict = Depends(require_auth)):
    """Retourne la liste des départements métropole valides"""
    return {
        "departements": DEPARTEMENTS_METRO,
        "count": len(DEPARTEMENTS_METRO),
        "note": "Métropole uniquement (01-95), excluant 2A et 2B (Corse)"
    }


@router.get("/products")
async def list_products(user: dict = Depends(require_auth)):
    """Retourne la liste des types de produits"""
    return {
        "products": PRODUCT_TYPES,
        "wildcard": "*"
    }
