"""
Routes pour la gestion des mappings utm_campaign → quality_tier
Collection: quality_mappings
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from config import db
from routes.auth import get_current_user

router = APIRouter(tags=["Quality Mappings"], prefix="/quality-mappings")


class QualityMappingCreate(BaseModel):
    utm_campaign: str
    quality_tier: int  # 1, 2 ou 3


class QualityMappingUpdate(BaseModel):
    utm_campaign: Optional[str] = None  # Optionnel pour rename
    quality_tier: int  # 1, 2 ou 3


@router.get("")
async def list_mappings(user: dict = Depends(get_current_user)):
    """Liste tous les mappings utm_campaign → quality_tier"""
    mappings = await db.quality_mappings.find({}, {"_id": 0}).to_list(1000)
    return {
        "mappings": mappings,
        "count": len(mappings)
    }


@router.post("")
async def create_mapping(data: QualityMappingCreate, user: dict = Depends(get_current_user)):
    """Créer un nouveau mapping"""
    
    # Valider quality_tier
    if data.quality_tier not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="quality_tier doit être 1, 2 ou 3")
    
    # Vérifier si existe déjà
    existing = await db.quality_mappings.find_one({"utm_campaign": data.utm_campaign})
    if existing:
        raise HTTPException(status_code=400, detail=f"Mapping pour '{data.utm_campaign}' existe déjà")
    
    mapping = {
        "utm_campaign": data.utm_campaign,
        "quality_tier": data.quality_tier
    }
    
    await db.quality_mappings.insert_one(mapping)
    
    return {
        "success": True,
        "mapping": {
            "utm_campaign": data.utm_campaign,
            "quality_tier": data.quality_tier
        }
    }


@router.put("/{utm_campaign}")
async def update_mapping(utm_campaign: str, data: QualityMappingUpdate, user: dict = Depends(get_current_user)):
    """Modifier un mapping existant (peut renommer utm_campaign)"""
    
    # Valider quality_tier
    if data.quality_tier not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="quality_tier doit être 1, 2 ou 3")
    
    # Vérifier que le mapping existe
    existing = await db.quality_mappings.find_one({"utm_campaign": utm_campaign})
    if not existing:
        raise HTTPException(status_code=404, detail=f"Mapping pour '{utm_campaign}' non trouvé")
    
    # Si rename, vérifier que le nouveau nom n'existe pas déjà
    new_utm = data.utm_campaign if data.utm_campaign else utm_campaign
    if new_utm != utm_campaign:
        conflict = await db.quality_mappings.find_one({"utm_campaign": new_utm})
        if conflict:
            raise HTTPException(status_code=400, detail=f"Mapping pour '{new_utm}' existe déjà")
    
    # Mise à jour
    result = await db.quality_mappings.update_one(
        {"utm_campaign": utm_campaign},
        {"$set": {
            "utm_campaign": new_utm,
            "quality_tier": data.quality_tier
        }}
    )
    
    return {
        "success": True,
        "mapping": {
            "utm_campaign": new_utm,
            "quality_tier": data.quality_tier
        },
        "renamed": new_utm != utm_campaign
    }


@router.delete("/{utm_campaign}")
async def delete_mapping(utm_campaign: str, user: dict = Depends(get_current_user)):
    """Supprimer un mapping"""
    
    result = await db.quality_mappings.delete_one({"utm_campaign": utm_campaign})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Mapping pour '{utm_campaign}' non trouvé")
    
    return {
        "success": True,
        "deleted": utm_campaign
    }
