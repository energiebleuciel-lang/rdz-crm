"""
Routes pour les CRMs externes (ZR7, MDL)
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid

from models import CRMCreate, CRMUpdate
from config import db, now_iso
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/crms", tags=["CRMs"])


@router.get("")
async def list_crms(user: dict = Depends(get_current_user)):
    """Liste tous les CRMs"""
    crms = await db.crms.find({}, {"_id": 0}).to_list(100)
    return {"crms": crms}


@router.post("/init")
async def init_default_crms(user: dict = Depends(require_admin)):
    """
    Initialise les CRMs par défaut (ZR7 + MDL).
    À appeler une seule fois au démarrage.
    """
    existing = await db.crms.count_documents({})
    if existing > 0:
        return {"success": False, "message": "CRMs déjà initialisés", "count": existing}
    
    default_crms = [
        {
            "id": str(uuid.uuid4()),
            "name": "ZR7 Digital",
            "slug": "zr7",
            "api_url": "https://app.zr7-digital.fr/lead/api/create_lead/",
            "description": "CRM ZR7 Digital",
            "commandes": {},
            "created_at": now_iso()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Maison du Lead",
            "slug": "mdl",
            "api_url": "https://maison-du-lead.com/lead/api/create_lead/",
            "description": "CRM Maison du Lead",
            "commandes": {},
            "created_at": now_iso()
        }
    ]
    
    await db.crms.insert_many(default_crms)
    
    return {"success": True, "crms": default_crms}


@router.get("/{crm_id}")
async def get_crm(crm_id: str, user: dict = Depends(get_current_user)):
    """Récupère un CRM par ID"""
    crm = await db.crms.find_one({"id": crm_id}, {"_id": 0})
    if not crm:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    return crm


@router.put("/{crm_id}")
async def update_crm(crm_id: str, data: CRMUpdate, user: dict = Depends(require_admin)):
    """Modifier un CRM (admin only)"""
    crm = await db.crms.find_one({"id": crm_id})
    if not crm:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    
    await db.crms.update_one({"id": crm_id}, {"$set": update_data})
    
    updated = await db.crms.find_one({"id": crm_id}, {"_id": 0})
    return {"success": True, "crm": updated}


@router.put("/{crm_id}/commandes")
async def update_crm_commandes(crm_id: str, commandes: dict, user: dict = Depends(require_admin)):
    """
    Mettre à jour les commandes d'un CRM.
    Format: {"PAC": ["75", "92"], "PV": ["13", "31"], "ITE": ["59"]}
    """
    crm = await db.crms.find_one({"id": crm_id})
    if not crm:
        raise HTTPException(status_code=404, detail="CRM non trouvé")
    
    await db.crms.update_one(
        {"id": crm_id},
        {"$set": {"commandes": commandes, "updated_at": now_iso()}}
    )
    
    return {"success": True, "commandes": commandes}
