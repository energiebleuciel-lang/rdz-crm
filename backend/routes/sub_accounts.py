"""
Routes pour les Sous-comptes
- Comptes enfants rattachés à un compte parent
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import uuid

from config import db, now_iso
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/sub-accounts", tags=["Sous-comptes"])


# ==================== MODELS ====================

class SubAccountCreate(BaseModel):
    parent_account_id: str
    name: str
    domain: Optional[str] = ""
    logo_url: Optional[str] = ""
    crm_api_key: Optional[str] = ""  # Clé API spécifique
    notes: Optional[str] = ""


class SubAccountUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    crm_api_key: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ==================== ROUTES ====================

@router.get("")
async def list_sub_accounts(
    parent_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Liste tous les sous-comptes"""
    query = {}
    if parent_id:
        query["parent_account_id"] = parent_id
    
    sub_accounts = await db.sub_accounts.find(query, {"_id": 0}).sort("name", 1).to_list(200)
    
    # Enrichir avec le nom du parent
    for sa in sub_accounts:
        parent = await db.accounts.find_one({"id": sa.get("parent_account_id")}, {"name": 1})
        sa["parent_name"] = parent.get("name") if parent else "N/A"
    
    return {"sub_accounts": sub_accounts, "count": len(sub_accounts)}


@router.get("/{sub_account_id}")
async def get_sub_account(sub_account_id: str, user: dict = Depends(get_current_user)):
    """Récupère un sous-compte"""
    sub_account = await db.sub_accounts.find_one({"id": sub_account_id}, {"_id": 0})
    if not sub_account:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    
    # Parent
    parent = await db.accounts.find_one({"id": sub_account.get("parent_account_id")}, {"_id": 0})
    sub_account["parent"] = parent
    
    return sub_account


@router.post("")
async def create_sub_account(data: SubAccountCreate, user: dict = Depends(get_current_user)):
    """Créer un sous-compte"""
    # Vérifier que le parent existe
    parent = await db.accounts.find_one({"id": data.parent_account_id})
    if not parent:
        raise HTTPException(status_code=400, detail="Compte parent non trouvé")
    
    sub_account = {
        "id": str(uuid.uuid4()),
        "parent_account_id": data.parent_account_id,
        "name": data.name,
        "domain": data.domain or "",
        "logo_url": data.logo_url or "",
        "crm_api_key": data.crm_api_key or "",
        "notes": data.notes or "",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    
    await db.sub_accounts.insert_one(sub_account)
    
    return {"success": True, "sub_account": {k: v for k, v in sub_account.items() if k != "_id"}}


@router.put("/{sub_account_id}")
async def update_sub_account(
    sub_account_id: str, 
    data: SubAccountUpdate, 
    user: dict = Depends(get_current_user)
):
    """Modifier un sous-compte"""
    sub_account = await db.sub_accounts.find_one({"id": sub_account_id})
    if not sub_account:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    update_data["updated_by"] = user["id"]
    
    await db.sub_accounts.update_one({"id": sub_account_id}, {"$set": update_data})
    
    updated = await db.sub_accounts.find_one({"id": sub_account_id}, {"_id": 0})
    return {"success": True, "sub_account": updated}


@router.delete("/{sub_account_id}")
async def delete_sub_account(sub_account_id: str, user: dict = Depends(require_admin)):
    """Supprimer un sous-compte"""
    sub_account = await db.sub_accounts.find_one({"id": sub_account_id})
    if not sub_account:
        raise HTTPException(status_code=404, detail="Sous-compte non trouvé")
    
    # Vérifier si des forms sont liés
    forms_count = await db.forms.count_documents({"sub_account_id": sub_account_id})
    if forms_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer: {forms_count} formulaire(s) lié(s)"
        )
    
    await db.sub_accounts.delete_one({"id": sub_account_id})
    return {"success": True}


@router.get("/{sub_account_id}/forms")
async def get_sub_account_forms(sub_account_id: str, user: dict = Depends(get_current_user)):
    """Liste les formulaires d'un sous-compte"""
    forms = await db.forms.find(
        {"sub_account_id": sub_account_id}, 
        {"_id": 0}
    ).to_list(100)
    
    return {"forms": forms, "count": len(forms)}
