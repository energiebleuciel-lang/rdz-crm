"""
Routes pour les Formulaires
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid

from models import FormCreate, FormUpdate
from config import db, now_iso, generate_form_code
from routes.auth import get_current_user

router = APIRouter(prefix="/forms", tags=["Formulaires"])


@router.get("")
async def list_forms(
    account_id: str = None,
    product_type: str = None,
    status: str = "active",
    user: dict = Depends(get_current_user)
):
    """Liste les formulaires avec stats"""
    query = {}
    if account_id:
        query["account_id"] = account_id
    if product_type:
        query["product_type"] = product_type.upper()
    if status:
        query["status"] = status
    
    forms = await db.forms.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrichir avec stats et infos liées
    for form in forms:
        code = form.get("code", "")
        
        # Stats
        started = await db.tracking.count_documents({"form_code": code, "event": "form_start"})
        finished = await db.leads.count_documents({"form_code": code, "api_status": {"$in": ["success", "duplicate"]}})
        
        form["stats"] = {
            "started": started,
            "finished": finished,
            "conversion": round((finished / started * 100), 1) if started > 0 else 0
        }
        
        # Nom du compte
        account = await db.accounts.find_one({"id": form.get("account_id")}, {"name": 1})
        form["account_name"] = account.get("name") if account else "N/A"
        
        # LP liée
        if form.get("lp_id"):
            lp = await db.lps.find_one({"id": form["lp_id"]}, {"code": 1, "name": 1, "url": 1})
            form["lp"] = lp if lp else None
        else:
            form["lp"] = None
    
    return {"forms": forms, "count": len(forms)}


@router.get("/{form_id}")
async def get_form(form_id: str, user: dict = Depends(get_current_user)):
    """Récupère un formulaire par ID"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    code = form.get("code", "")
    
    # Stats
    started = await db.tracking.count_documents({"form_code": code, "event": "form_start"})
    finished = await db.leads.count_documents({"form_code": code, "api_status": {"$in": ["success", "duplicate"]}})
    
    form["stats"] = {
        "started": started,
        "finished": finished,
        "conversion": round((finished / started * 100), 1) if started > 0 else 0
    }
    
    # LP liée complète
    if form.get("lp_id"):
        lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0})
        form["lp"] = lp
    
    # Compte complet
    account = await db.accounts.find_one({"id": form.get("account_id")}, {"_id": 0})
    form["account"] = account
    
    return form


@router.post("")
async def create_form(data: FormCreate, user: dict = Depends(get_current_user)):
    """Créer un nouveau formulaire"""
    # Vérifier que le compte existe
    account = await db.accounts.find_one({"id": data.account_id})
    if not account:
        raise HTTPException(status_code=400, detail="Compte non trouvé")
    
    # Vérifier la LP si fournie
    if data.lp_id:
        lp = await db.lps.find_one({"id": data.lp_id})
        if not lp:
            raise HTTPException(status_code=400, detail="LP non trouvée")
    
    # Générer code unique
    code = await generate_form_code(data.product_type)
    
    form = {
        "id": str(uuid.uuid4()),
        "code": code,
        "account_id": data.account_id,
        "name": data.name,
        "url": data.url,  # OBLIGATOIRE
        "product_type": data.product_type.upper(),
        "lp_id": data.lp_id or "",
        "crm_api_key": data.crm_api_key or "",
        "tracking_type": data.tracking_type or "redirect",
        "redirect_url": data.redirect_url or "/merci",
        "notes": data.notes or "",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    
    await db.forms.insert_one(form)
    
    return {
        "success": True,
        "form": {k: v for k, v in form.items() if k != "_id"},
        "code": code
    }


@router.put("/{form_id}")
async def update_form(form_id: str, data: FormUpdate, user: dict = Depends(get_current_user)):
    """Modifier un formulaire"""
    form = await db.forms.find_one({"id": form_id})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Vérifier la LP si fournie
    if data.lp_id:
        lp = await db.lps.find_one({"id": data.lp_id})
        if not lp:
            raise HTTPException(status_code=400, detail="LP non trouvée")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_iso()
    update_data["updated_by"] = user["id"]
    
    await db.forms.update_one({"id": form_id}, {"$set": update_data})
    
    updated = await db.forms.find_one({"id": form_id}, {"_id": 0})
    return {"success": True, "form": updated}


@router.delete("/{form_id}")
async def archive_form(form_id: str, user: dict = Depends(get_current_user)):
    """Archiver un formulaire (soft delete)"""
    form = await db.forms.find_one({"id": form_id})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    await db.forms.update_one(
        {"id": form_id},
        {"$set": {"status": "archived", "archived_at": now_iso(), "archived_by": user["id"]}}
    )
    
    return {"success": True}


@router.post("/{form_id}/duplicate")
async def duplicate_form(form_id: str, user: dict = Depends(get_current_user)):
    """Dupliquer un formulaire"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Nouveau code
    new_code = await generate_form_code(form.get("product_type", "PV"))
    
    new_form = {
        **form,
        "id": str(uuid.uuid4()),
        "code": new_code,
        "name": f"{form['name']} (copie)",
        "status": "active",
        "created_at": now_iso(),
        "created_by": user["id"]
    }
    # Supprimer les anciens champs
    new_form.pop("updated_at", None)
    new_form.pop("archived_at", None)
    
    await db.forms.insert_one(new_form)
    
    return {"success": True, "form": new_form, "code": new_code}
