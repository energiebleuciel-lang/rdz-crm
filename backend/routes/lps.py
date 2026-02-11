"""
Routes pour les Landing Pages
Création LP = Création automatique du Form lié (duo obligatoire)
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid

from models import LPCreate, LPUpdate
from config import db, now_iso, generate_lp_code, generate_form_code
from routes.auth import get_current_user

router = APIRouter(prefix="/lps", tags=["Landing Pages"])


@router.get("")
async def list_lps(
    account_id: str = None,
    status: str = "active",
    user: dict = Depends(get_current_user)
):
    """Liste les Landing Pages avec leurs Forms liés"""
    query = {}
    if account_id:
        query["account_id"] = account_id
    if status:
        query["$or"] = [
            {"status": status},
            {"status": {"$exists": False}}
        ]
    
    cursor = db.lps.find(query)
    lps_raw = await cursor.to_list(200)
    
    lps = []
    for lp_item in lps_raw:
        lp_item.pop("_id", None)
        lps.append(lp_item)
    
    lps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Enrichir avec stats et form lié
    for lp in lps:
        lp_code = lp.get("code", "")
        form_id = lp.get("form_id")
        
        # Stats LP - EXCLURE les events avec stats_reset: True
        lp["stats"] = {
            "visits": await db.tracking.count_documents({
                "lp_code": lp_code, 
                "event": "lp_visit",
                "stats_reset": {"$ne": True}
            }),
            "cta_clicks": await db.tracking.count_documents({
                "lp_code": lp_code, 
                "event": "cta_click",
                "stats_reset": {"$ne": True}
            })
        }
        
        # Form lié
        if form_id:
            form = await db.forms.find_one({"id": form_id}, {"_id": 0, "code": 1, "name": 1, "url": 1})
            if form:
                lp["form"] = form
                form_code = form.get("code", "")
                # Stats Form - EXCLURE stats_reset
                lp["stats"]["form_starts"] = await db.tracking.count_documents({
                    "form_code": form_code, 
                    "event": "form_start",
                    "stats_reset": {"$ne": True}
                })
                lp["stats"]["form_submits"] = await db.leads.count_documents({
                    "form_code": form_code,
                    "stats_reset": {"$ne": True}
                })
                # Liaison
                lp["liaison_code"] = f"{lp_code}_{form_code}"
        
        # Nom du compte
        account = await db.accounts.find_one({"id": lp.get("account_id")}, {"_id": 0, "name": 1})
        lp["account_name"] = account.get("name") if account else "N/A"
    
    return {"lps": lps, "count": len(lps)}


@router.get("/{lp_id}")
async def get_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Récupère une LP par ID avec son Form lié"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    lp_code = lp.get("code", "")
    
    # Stats
    lp["stats"] = {
        "visits": await db.tracking.count_documents({"lp_code": lp_code, "event": "lp_visit"}),
        "cta_clicks": await db.tracking.count_documents({"lp_code": lp_code, "event": "cta_click"})
    }
    
    # Form lié
    if lp.get("form_id"):
        form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
        if form:
            lp["form"] = form
            form_code = form.get("code", "")
            lp["stats"]["form_starts"] = await db.tracking.count_documents({"form_code": form_code, "event": "form_start"})
            lp["stats"]["form_submits"] = await db.leads.count_documents({"form_code": form_code})
            lp["liaison_code"] = f"{lp_code}_{form_code}"
    
    return lp


@router.post("")
async def create_lp(data: LPCreate, user: dict = Depends(get_current_user)):
    """
    Créer une nouvelle LP + Form (duo obligatoire)
    Génère automatiquement les codes et la liaison
    """
    # Vérifier que le compte existe
    account = await db.accounts.find_one({"id": data.account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Compte non trouvé")
    
    # Générer les codes
    lp_code = await generate_lp_code()
    form_code = await generate_form_code(data.product_type)
    liaison_code = f"{lp_code}_{form_code}"
    
    # Déterminer l'URL du form
    form_url = data.form_url if data.form_mode == "redirect" and data.form_url else data.url
    
    # 1. Créer le FORM d'abord
    form_id = str(uuid.uuid4())
    form = {
        "id": form_id,
        "code": form_code,
        "account_id": data.account_id,
        "name": f"Form {data.name}",
        "url": form_url,
        "product_type": data.product_type.upper(),
        "lp_id": None,  # Sera mis à jour après création LP
        "crm_api_key": data.crm_api_key or "",
        "tracking_type": data.tracking_type or "redirect",
        "redirect_url": data.redirect_url or "/merci",
        "notes": "",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    await db.forms.insert_one(form)
    
    # 2. Créer la LP
    lp_id = str(uuid.uuid4())
    lp = {
        "id": lp_id,
        "code": lp_code,
        "account_id": data.account_id,
        "name": data.name,
        "url": data.url,
        "product_type": data.product_type.upper(),
        "form_mode": data.form_mode,  # embedded ou redirect
        "form_id": form_id,  # Lien vers le form
        "form_url": form_url,
        "tracking_type": data.tracking_type or "redirect",
        "redirect_url": data.redirect_url or "/merci",
        "source_type": data.source_type or "native",
        "source_name": data.source_name or "",
        "crm_api_key": data.crm_api_key or "",
        "notes": data.notes or "",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    await db.lps.insert_one(lp)
    
    # 3. Mettre à jour le Form avec le lp_id
    await db.forms.update_one({"id": form_id}, {"$set": {"lp_id": lp_id}})
    
    return {
        "success": True,
        "lp": {k: v for k, v in lp.items() if k != "_id"},
        "form": {k: v for k, v in form.items() if k != "_id"},
        "codes": {
            "lp_code": lp_code,
            "form_code": form_code,
            "liaison_code": liaison_code
        }
    }


@router.get("/{lp_id}/brief")
async def get_lp_brief(lp_id: str, user: dict = Depends(get_current_user)):
    """
    Génère le brief avec script simplifié
    - 1 seul script universel (~50 lignes)
    - Pas de clé API visible
    - Cookie de session automatique
    """
    from services.brief_generator import generate_brief_v2
    return await generate_brief_v2(lp_id)


@router.put("/{lp_id}")
async def update_lp(lp_id: str, data: LPUpdate, user: dict = Depends(get_current_user)):
    """Modifier une LP (et son Form lié si nécessaire)"""
    lp = await db.lps.find_one({"id": lp_id})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    update_data["updated_by"] = user["id"]
    
    await db.lps.update_one({"id": lp_id}, {"$set": update_data})
    
    # Mettre à jour le Form lié si certains champs changent
    form_id = lp.get("form_id")
    if form_id:
        form_update = {}
        if data.tracking_type is not None:
            form_update["tracking_type"] = data.tracking_type
        if data.redirect_url is not None:
            form_update["redirect_url"] = data.redirect_url
        if data.crm_api_key is not None:
            form_update["crm_api_key"] = data.crm_api_key
        if data.form_url is not None:
            form_update["url"] = data.form_url
        if data.product_type is not None:
            form_update["product_type"] = data.product_type.upper()
        
        if form_update:
            form_update["updated_at"] = now_iso()
            await db.forms.update_one({"id": form_id}, {"$set": form_update})
    
    updated = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    return {"success": True, "lp": updated}


@router.delete("/{lp_id}")
async def archive_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Archiver une LP et son Form lié"""
    lp = await db.lps.find_one({"id": lp_id})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Archiver la LP
    await db.lps.update_one(
        {"id": lp_id},
        {"$set": {"status": "archived", "archived_at": now_iso(), "archived_by": user["id"]}}
    )
    
    # Archiver le Form lié
    if lp.get("form_id"):
        await db.forms.update_one(
            {"id": lp["form_id"]},
            {"$set": {"status": "archived", "archived_at": now_iso(), "archived_by": user["id"]}}
        )
    
    return {"success": True}


@router.post("/{lp_id}/duplicate")
async def duplicate_lp(lp_id: str, user: dict = Depends(get_current_user)):
    """Dupliquer une LP et son Form lié"""
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    # Nouveaux codes
    new_lp_code = await generate_lp_code()
    product_type = lp.get("product_type", "PV")
    new_form_code = await generate_form_code(product_type)
    new_liaison_code = f"{new_lp_code}_{new_form_code}"
    
    # Dupliquer le Form
    new_form_id = str(uuid.uuid4())
    if lp.get("form_id"):
        old_form = await db.forms.find_one({"id": lp["form_id"]}, {"_id": 0})
        if old_form:
            new_form = {
                **old_form,
                "id": new_form_id,
                "code": new_form_code,
                "name": f"{old_form.get('name', '')} (copie)",
                "lp_id": None,  # Sera mis à jour
                "status": "active",
                "created_at": now_iso(),
                "created_by": user["id"]
            }
            new_form.pop("updated_at", None)
            new_form.pop("archived_at", None)
            await db.forms.insert_one(new_form)
    
    # Dupliquer la LP
    new_lp_id = str(uuid.uuid4())
    new_lp = {
        **lp,
        "id": new_lp_id,
        "code": new_lp_code,
        "name": f"{lp['name']} (copie)",
        "form_id": new_form_id,
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    new_lp.pop("updated_at", None)
    new_lp.pop("archived_at", None)
    await db.lps.insert_one(new_lp)
    
    # Mettre à jour le Form avec le lp_id
    await db.forms.update_one({"id": new_form_id}, {"$set": {"lp_id": new_lp_id}})
    
    return {
        "success": True,
        "lp": new_lp,
        "codes": {
            "lp_code": new_lp_code,
            "form_code": new_form_code,
            "liaison_code": new_liaison_code
        }
    }
