"""
RDZ CRM - Routes Providers (Fournisseurs externes)

CRUD + generation API key.
Chaque provider est rattache a UNE entite (ZR7 ou MDL).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import uuid
import secrets

from config import db, now_iso
from routes.auth import get_current_user, require_admin
from models import validate_entity
from models.provider import ProviderCreate, ProviderUpdate
from services.permissions import require_permission

router = APIRouter(prefix="/providers", tags=["Providers"])


def generate_provider_key() -> str:
    """Genere une API key provider: prov_xxx"""
    return f"prov_{secrets.token_urlsafe(32)}"


@router.get("")
async def list_providers(
    entity: Optional[str] = Query(None, description="Filtrer par entite"),
    user: dict = Depends(require_permission("providers.access"))
):
    """Liste les providers"""
    query = {}
    if entity:
        if not validate_entity(entity):
            raise HTTPException(status_code=400, detail="Entity invalide")
        query["entity"] = entity

    providers = await db.providers.find(query, {"_id": 0}).sort("name", 1).to_list(200)

    # Enrichir avec stats
    for p in providers:
        count = await db.leads.count_documents({"provider_id": p.get("id")})
        p["total_leads"] = count

    return {"providers": providers, "count": len(providers)}


@router.get("/{provider_id}")
async def get_provider(provider_id: str, user: dict = Depends(require_permission("providers.access"))):
    """Recupere un provider"""
    p = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Provider non trouve")

    count = await db.leads.count_documents({"provider_id": provider_id})
    p["total_leads"] = count

    return {"provider": p}


@router.post("")
async def create_provider(data: ProviderCreate, user: dict = Depends(require_permission("providers.access"))):
    """Cree un provider avec API key auto-generee"""
    # Slug unique
    existing = await db.providers.find_one({"slug": data.slug.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail=f"Slug '{data.slug}' deja utilise")

    provider = {
        "id": str(uuid.uuid4()),
        "name": data.name.strip(),
        "slug": data.slug.lower().strip(),
        "entity": data.entity.value,
        "api_key": generate_provider_key(),
        "contact_email": data.contact_email or "",
        "notes": data.notes or "",
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    await db.providers.insert_one(provider)
    provider.pop("_id", None)

    return {"success": True, "provider": provider}


@router.put("/{provider_id}")
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    user: dict = Depends(require_permission("providers.access"))
):
    """Met a jour un provider"""
    p = await db.providers.find_one({"id": provider_id})
    if not p:
        raise HTTPException(status_code=404, detail="Provider non trouve")

    update = {k: v for k, v in data.dict().items() if v is not None}
    update["updated_at"] = now_iso()

    await db.providers.update_one({"id": provider_id}, {"$set": update})
    updated = await db.providers.find_one({"id": provider_id}, {"_id": 0})
    return {"success": True, "provider": updated}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, user: dict = Depends(require_permission("providers.access"))):
    """Supprime un provider"""
    result = await db.providers.delete_one({"id": provider_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Provider non trouve")
    return {"success": True, "deleted_id": provider_id}


@router.post("/{provider_id}/rotate-key")
async def rotate_api_key(provider_id: str, user: dict = Depends(require_permission("providers.access"))):
    """Regenere l'API key d'un provider"""
    p = await db.providers.find_one({"id": provider_id})
    if not p:
        raise HTTPException(status_code=404, detail="Provider non trouve")

    new_key = generate_provider_key()
    await db.providers.update_one(
        {"id": provider_id},
        {"$set": {"api_key": new_key, "updated_at": now_iso()}}
    )
    
    from services.event_logger import log_event
    await log_event(
        action="rotate_provider_key",
        entity_type="provider",
        entity_id=provider_id,
        entity=p.get("entity", ""),
        user=user.get("email"),
        details={"provider_name": p.get("name"), "provider_slug": p.get("slug")},
    )
    
    return {"success": True, "api_key": new_key}
