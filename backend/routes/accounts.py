"""
Routes pour les Comptes (entreprises clientes)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import uuid

from models import AccountCreate, AccountUpdate
from config import db, now_iso
from routes.auth import get_current_user, require_admin
from services.brief_generator import get_account_brief_options, generate_mini_brief


class MiniBriefRequest(BaseModel):
    selections: List[str]  # liste des clés à inclure dans le brief

router = APIRouter(prefix="/accounts", tags=["Comptes"])


@router.get("")
async def list_accounts(crm_id: str = None, user: dict = Depends(get_current_user)):
    """Liste les comptes, optionnellement filtrés par CRM"""
    query = {}
    if crm_id:
        query["crm_id"] = crm_id
    
    accounts = await db.accounts.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    return {"accounts": accounts, "count": len(accounts)}


@router.get("/{account_id}")
async def get_account(account_id: str, user: dict = Depends(get_current_user)):
    """Récupère un compte par ID"""
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    return account


@router.post("")
async def create_account(data: AccountCreate, user: dict = Depends(get_current_user)):
    """Créer un nouveau compte"""
    account = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "crm_id": data.crm_id,
        "domain": data.domain or "",
        "logo_main_url": data.logo_main_url or "",
        "logo_secondary_url": data.logo_secondary_url or "",
        "logo_mini_url": data.logo_mini_url or "",
        "primary_color": data.primary_color or "#3B82F6",
        "secondary_color": data.secondary_color or "#1E40AF",
        "redirect_url_pv": data.redirect_url_pv or "",
        "redirect_url_pac": data.redirect_url_pac or "",
        "redirect_url_ite": data.redirect_url_ite or "",
        "cgu_text": data.cgu_text or "",
        "privacy_policy_text": data.privacy_policy_text or "",
        "legal_mentions_text": data.legal_mentions_text or "",
        "gtm_head": data.gtm_head or "",
        "gtm_body": data.gtm_body or "",
        "gtm_conversion": data.gtm_conversion or "",
        "default_tracking_type": data.default_tracking_type or "redirect",
        "notes": data.notes or "",
        "crm_routing": {k: v.model_dump() for k, v in data.crm_routing.items()} if data.crm_routing else {},
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    
    await db.accounts.insert_one(account)
    
    return {"success": True, "account": {k: v for k, v in account.items() if k != "_id"}}


@router.put("/{account_id}")
async def update_account(account_id: str, data: AccountUpdate, user: dict = Depends(get_current_user)):
    """Modifier un compte"""
    account = await db.accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    
    # Ne mettre à jour que les champs fournis
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    # Sérialiser crm_routing si présent (Pydantic → dict)
    if "crm_routing" in update_data and update_data["crm_routing"]:
        update_data["crm_routing"] = {
            k: v if isinstance(v, dict) else v
            for k, v in update_data["crm_routing"].items()
        }
    update_data["updated_at"] = now_iso()
    update_data["updated_by"] = user["id"]
    
    await db.accounts.update_one({"id": account_id}, {"$set": update_data})
    
    updated = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    return {"success": True, "account": updated}


@router.delete("/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(require_admin)):
    """Supprimer un compte (admin only)"""
    account = await db.accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    
    # Vérifier s'il y a des LPs ou Forms liés
    lps_count = await db.lps.count_documents({"account_id": account_id})
    forms_count = await db.forms.count_documents({"account_id": account_id})
    
    if lps_count > 0 or forms_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer: {lps_count} LP(s) et {forms_count} formulaire(s) liés"
        )
    
    await db.accounts.delete_one({"id": account_id})
    return {"success": True}


@router.get("/{account_id}/brief-options")
async def get_brief_options(account_id: str, user: dict = Depends(get_current_user)):
    """Récupère les options disponibles pour générer un mini brief"""
    result = await get_account_brief_options(account_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{account_id}/mini-brief")
async def create_mini_brief(account_id: str, data: MiniBriefRequest, user: dict = Depends(get_current_user)):
    """Génère un mini brief avec les éléments sélectionnés"""
    result = await generate_mini_brief(account_id, data.selections)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
