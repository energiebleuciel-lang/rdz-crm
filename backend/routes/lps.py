"""
Routes pour les Landing Pages
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid

from models import LPCreate, LPUpdate
from config import db, now_iso, generate_lp_code
from routes.auth import get_current_user

router = APIRouter(prefix="/lps", tags=["Landing Pages"])


@router.get("")
async def list_lps(
    account_id: str = None,
    status: str = "active",
    user: dict = Depends(get_current_user)
):
    """Liste les Landing Pages"""
    query = {}
    if account_id:
        query["account_id"] = account_id
    if status:
        # Inclure les documents qui ont status=active OU qui n'ont pas de champ status
        query["$or"] = [
            {"status": status},
            {"status": {"$exists": False}}
        ]
    
    # Exclure _id dans la projection
    cursor = db.lps.find(query)
    lps_raw = await cursor.to_list(200)
    
    # Convertir et trier
    lps = []
    for l in lps_raw:
        l.pop("_id", None)  # Supprimer _id
        lps.append(l)
    
    # Trier par created_at desc
    lps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Enrichir avec stats
    for lp in lps:
        lp["stats"] = {
            "visits": await db.tracking.count_documents({"lp_code": lp.get("code"), "event": "lp_visit"}),
            "cta_clicks": await db.tracking.count_documents({"lp_code": lp.get("code"), "event": "cta_click"})
        }
        # Récupérer le nom du compte
        account = await db.accounts.find_one({"id": lp.get("account_id")}, {"name": 1})
        lp["account_name"] = account.get("name") if account else "N/A"
    
    return {"lps": lps, "count": len(lps)}


@router.get("/{lp_id}")
async def get_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Récupère une LP par ID"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Stats
    lp["stats"] = {
        "visits": await db.tracking.count_documents({"lp_code": lp.get("code"), "event": "lp_visit"}),
        "cta_clicks": await db.tracking.count_documents({"lp_code": lp.get("code"), "event": "cta_click"})
    }
    
    return lp


@router.post("")
async def create_lp(data: LPCreate, user: dict = Depends(get_current_user)):
    """Créer une nouvelle LP"""
    # Vérifier que le compte existe
    account = await db.accounts.find_one({"id": data.account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Compte non trouvé")
    
    # Générer code unique
    code = await generate_lp_code()
    
    lp = {
        "id": str(uuid.uuid4()),
        "code": code,
        "account_id": data.account_id,
        "name": data.name,
        "url": data.url,  # OBLIGATOIRE
        "source_type": data.source_type or "native",
        "source_name": data.source_name or "",
        "notes": data.notes or "",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    
    await db.lps.insert_one(lp)
    
    return {
        "success": True, 
        "lp": {k: v for k, v in lp.items() if k != "_id"},
        "code": code
    }


@router.put("/{lp_id}")
async def update_lp(lp_id: str, data: LPUpdate, user: dict = Depends(get_current_user)):
    """Modifier une LP"""
    lp = await db.lps.find_one({"id": lp_id})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    update_data["updated_by"] = user["id"]
    
    await db.lps.update_one({"id": lp_id}, {"$set": update_data})
    
    updated = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    return {"success": True, "lp": updated}


@router.delete("/{lp_id}")
async def archive_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Archiver une LP (soft delete)"""
    lp = await db.lps.find_one({"id": lp_id})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    await db.lps.update_one(
        {"id": lp_id},
        {"$set": {"status": "archived", "archived_at": now_iso(), "archived_by": user["id"]}}
    )
    
    return {"success": True}


@router.post("/{lp_id}/duplicate")
async def duplicate_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Dupliquer une LP"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Nouveau code
    new_code = await generate_lp_code()
    
    new_lp = {
        **lp,
        "id": str(uuid.uuid4()),
        "code": new_code,
        "name": f"{lp['name']} (copie)",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    # Supprimer les anciens champs de tracking
    new_lp.pop("updated_at", None)
    new_lp.pop("archived_at", None)
    
    await db.lps.insert_one(new_lp)
    
    return {"success": True, "lp": new_lp, "code": new_code}
