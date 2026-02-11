"""
Routes pour la configuration
- Sources de diffusion
- Types de produits
- Aides financières
- Bibliothèque d'images
- Statut des clés API CRM
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import os

from config import db, now_iso
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/config", tags=["Configuration"])


# ==================== CLÉ API GLOBALE ====================

@router.get("/api-key")
async def get_global_api_key(user: dict = Depends(require_admin)):
    """Récupère la clé API globale pour l'API v1 - UNIQUE et NON-REGENERABLE"""
    config = await db.system_config.find_one({"type": "global_api_key"})
    if not config:
        # Créer une clé unique à la première demande
        import secrets
        new_key = secrets.token_urlsafe(32)
        await db.system_config.insert_one({
            "type": "global_api_key",
            "api_key": new_key,
            "created_at": now_iso(),
            "locked": True,  # Verrouillé dès la création
            "note": "Clé unique - Ne peut pas être régénérée ou supprimée"
        })
        return {"api_key": new_key, "created": True, "locked": True}
    
    return {"api_key": config.get("api_key"), "created": False, "locked": True}


# SÉCURITÉ : Aucun endpoint de régénération ou suppression de la clé API
# La clé API RDZ est PERMANENTE et ne peut jamais être modifiée


# ==================== STATUT CLÉS API CRM (v2) ====================

@router.get("/crm-api-status")
async def get_crm_api_status(user: dict = Depends(get_current_user)):
    """
    Vérifie si les clés API CRM sont configurées côté serveur.
    Ne retourne PAS les clés - juste un booléen pour chaque CRM.
    """
    zr7_key = os.environ.get("ZR7_API_KEY", "")
    mdl_key = os.environ.get("MDL_API_KEY", "")
    
    return {
        "zr7": bool(zr7_key and len(zr7_key) > 10),
        "mdl": bool(mdl_key and len(mdl_key) > 10),
        "note": "Les clés sont configurées dans le fichier .env du serveur"
    }


# ==================== MODELS ====================

class DiffusionSourceCreate(BaseModel):
    name: str           # Google Ads, Facebook, Taboola
    slug: str           # google, facebook, taboola
    icon: Optional[str] = ""
    color: Optional[str] = "#3B82F6"

class ProductTypeCreate(BaseModel):
    code: str           # PV, PAC, ITE
    name: str           # Panneaux solaires, Pompe à chaleur
    color: str          # Couleur UI
    aides: Optional[List[Dict]] = []  # Liste des aides financières

class ImageCreate(BaseModel):
    name: str
    url: str
    category: str       # logo, banner, icon, photo
    tags: Optional[List[str]] = []


# ==================== SOURCES DE DIFFUSION ====================

@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    """Liste toutes les sources de diffusion"""
    sources = await db.diffusion_sources.find({}, {"_id": 0}).to_list(100)
    return {"sources": sources}


@router.post("/sources")
async def create_source(data: DiffusionSourceCreate, user: dict = Depends(require_admin)):
    """Créer une source de diffusion"""
    # Vérifier unicité du slug
    existing = await db.diffusion_sources.find_one({"slug": data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Ce slug existe déjà")
    
    source = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "slug": data.slug,
        "icon": data.icon or "",
        "color": data.color or "#3B82F6",
        "created_at": now_iso()
    }
    
    await db.diffusion_sources.insert_one(source)
    return {"success": True, "source": {k: v for k, v in source.items() if k != "_id"}}


@router.post("/sources/init")
async def init_default_sources(user: dict = Depends(require_admin)):
    """Initialise les sources par défaut"""
    existing = await db.diffusion_sources.count_documents({})
    if existing > 0:
        return {"success": False, "message": "Sources déjà initialisées", "count": existing}
    
    default_sources = [
        {"name": "Google Ads", "slug": "google", "color": "#4285F4", "icon": "google"},
        {"name": "Facebook Ads", "slug": "facebook", "color": "#1877F2", "icon": "facebook"},
        {"name": "Taboola", "slug": "taboola", "color": "#0052CC", "icon": "link"},
        {"name": "Outbrain", "slug": "outbrain", "color": "#FF6600", "icon": "link"},
        {"name": "Native", "slug": "native", "color": "#10B981", "icon": "globe"},
        {"name": "Email", "slug": "email", "color": "#6366F1", "icon": "mail"},
        {"name": "SMS", "slug": "sms", "color": "#F59E0B", "icon": "message"},
        {"name": "Partenaire", "slug": "partner", "color": "#8B5CF6", "icon": "users"},
    ]
    
    for source in default_sources:
        source["id"] = str(uuid.uuid4())
        source["created_at"] = now_iso()
        await db.diffusion_sources.insert_one(source)
    
    return {"success": True, "count": len(default_sources)}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(require_admin)):
    """Supprimer une source"""
    result = await db.diffusion_sources.delete_one({"id": source_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source non trouvée")
    return {"success": True}


# ==================== TYPES DE PRODUITS ====================

@router.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    """Liste tous les types de produits avec leurs aides"""
    products = await db.product_types.find({}, {"_id": 0}).to_list(100)
    return {"products": products}


@router.post("/products")
async def create_product(data: ProductTypeCreate, user: dict = Depends(require_admin)):
    """Créer un type de produit"""
    existing = await db.product_types.find_one({"code": data.code})
    if existing:
        raise HTTPException(status_code=400, detail="Ce code existe déjà")
    
    product = {
        "id": str(uuid.uuid4()),
        "code": data.code.upper(),
        "name": data.name,
        "color": data.color,
        "aides": data.aides or [],
        "created_at": now_iso()
    }
    
    await db.product_types.insert_one(product)
    return {"success": True, "product": {k: v for k, v in product.items() if k != "_id"}}


@router.post("/products/init")
async def init_default_products(user: dict = Depends(require_admin)):
    """Initialise les produits par défaut avec aides"""
    existing = await db.product_types.count_documents({})
    if existing > 0:
        return {"success": False, "message": "Produits déjà initialisés", "count": existing}
    
    default_products = [
        {
            "code": "PV",
            "name": "Panneaux Photovoltaïques",
            "color": "#F59E0B",
            "aides": [
                {"name": "Prime autoconsommation", "amount": "380€/kWc", "conditions": "Installation ≤ 3kWc"},
                {"name": "TVA réduite", "amount": "10%", "conditions": "Installation ≤ 3kWc"},
                {"name": "Obligation d'achat EDF OA", "amount": "0.13€/kWh", "conditions": "Vente surplus"}
            ]
        },
        {
            "code": "PAC",
            "name": "Pompe à Chaleur",
            "color": "#3B82F6",
            "aides": [
                {"name": "MaPrimeRénov'", "amount": "Jusqu'à 5000€", "conditions": "Selon revenus"},
                {"name": "CEE", "amount": "Jusqu'à 4000€", "conditions": "Prime énergie"},
                {"name": "TVA réduite", "amount": "5.5%", "conditions": "Logement > 2 ans"},
                {"name": "Éco-PTZ", "amount": "Jusqu'à 15000€", "conditions": "Prêt à taux zéro"}
            ]
        },
        {
            "code": "ITE",
            "name": "Isolation Thermique Extérieure",
            "color": "#10B981",
            "aides": [
                {"name": "MaPrimeRénov'", "amount": "Jusqu'à 75€/m²", "conditions": "Selon revenus"},
                {"name": "CEE", "amount": "Variable", "conditions": "Prime énergie"},
                {"name": "TVA réduite", "amount": "5.5%", "conditions": "Logement > 2 ans"}
            ]
        }
    ]
    
    for product in default_products:
        product["id"] = str(uuid.uuid4())
        product["created_at"] = now_iso()
        await db.product_types.insert_one(product)
    
    return {"success": True, "count": len(default_products)}


@router.put("/products/{product_id}/aides")
async def update_product_aides(product_id: str, aides: List[Dict], user: dict = Depends(require_admin)):
    """Mettre à jour les aides d'un produit"""
    result = await db.product_types.update_one(
        {"id": product_id},
        {"$set": {"aides": aides, "updated_at": now_iso()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    return {"success": True}


# ==================== BIBLIOTHÈQUE D'IMAGES ====================

@router.get("/images")
async def list_images(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Liste toutes les images de la bibliothèque"""
    query = {}
    if category:
        query["category"] = category
    
    images = await db.images.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"images": images}


@router.post("/images")
async def add_image(data: ImageCreate, user: dict = Depends(get_current_user)):
    """Ajouter une image à la bibliothèque"""
    image = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "url": data.url,
        "category": data.category,
        "tags": data.tags or [],
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    
    await db.images.insert_one(image)
    return {"success": True, "image": {k: v for k, v in image.items() if k != "_id"}}


@router.delete("/images/{image_id}")
async def delete_image(image_id: str, user: dict = Depends(get_current_user)):
    """Supprimer une image"""
    result = await db.images.delete_one({"id": image_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Image non trouvée")
    return {"success": True}


# ==================== LOGS D'ACTIVITÉ ====================

@router.get("/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Historique des activités"""
    query = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    
    logs = await db.activity_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"logs": logs, "count": len(logs)}


async def log_activity(user_id: str, user_email: str, action: str, entity_type: str, entity_id: str, details: str = ""):
    """Helper pour logger une activité"""
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
        "created_at": now_iso()
    })


# ==================== CLÉS API REDISTRIBUTION INTER-CRM ====================

@router.get("/redistribution-keys")
async def get_redistribution_keys(user: dict = Depends(require_admin)):
    """
    Récupère les 6 clés API pour la redistribution inter-CRM.
    Ces clés sont utilisées quand un lead est envoyé d'un CRM vers l'autre.
    """
    config = await db.system_config.find_one({"type": "redistribution_keys"}, {"_id": 0})
    
    if not config:
        # Structure par défaut
        return {
            "keys": {
                "zr7": {"PV": "", "PAC": "", "ITE": ""},
                "mdl": {"PV": "", "PAC": "", "ITE": ""}
            }
        }
    
    return {"keys": config.get("keys", {})}


@router.put("/redistribution-keys")
async def update_redistribution_keys(
    data: dict,
    user: dict = Depends(require_admin)
):
    """
    Met à jour les 6 clés API de redistribution inter-CRM.
    
    Format attendu:
    {
        "keys": {
            "zr7": {"PV": "key1", "PAC": "key2", "ITE": "key3"},
            "mdl": {"PV": "key4", "PAC": "key5", "ITE": "key6"}
        }
    }
    """
    keys = data.get("keys", {})
    
    # Validation basique
    if not isinstance(keys, dict):
        raise HTTPException(status_code=400, detail="Format invalide pour 'keys'")
    
    # Sauvegarder
    await db.system_config.update_one(
        {"type": "redistribution_keys"},
        {"$set": {
            "type": "redistribution_keys",
            "keys": keys,
            "updated_at": now_iso(),
            "updated_by": user.get("email")
        }},
        upsert=True
    )
    
    # Log activité
    await log_activity(
        user.get("id", ""),
        user.get("email", ""),
        "update",
        "redistribution_keys",
        "system",
        "Mise à jour des clés de redistribution"
    )
    
    return {"success": True, "message": "Clés de redistribution mises à jour"}

