"""
Routes pour les Formulaires
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid

from models import FormCreate, FormUpdate
from config import db, now_iso, generate_form_code, FRANCE_METRO_DEPTS
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/forms", tags=["Formulaires"])


# ==================== ENDPOINTS PUBLICS (sans auth) ====================

@router.get("/public/{form_code}")
async def get_form_public(form_code: str):
    """
    Endpoint PUBLIC pour récupérer un formulaire par son code.
    Utilisé par les développeurs pour récupérer la config du form.
    URL: /api/forms/public/{form_code}
    """
    form = await db.forms.find_one(
        {"$or": [{"code": form_code}, {"id": form_code}]},
        {"_id": 0}
    )
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    # Récupérer infos compte (logos, couleurs)
    account = await db.accounts.find_one({"id": form.get("account_id")}, {"_id": 0})
    
    # Récupérer LP liée si présente
    lp = None
    if form.get("lp_id"):
        lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0})
    
    return {
        "form": {
            "id": form.get("id"),
            "code": form.get("code"),
            "name": form.get("name"),
            "url": form.get("url"),
            "product_type": form.get("product_type"),
            "tracking_type": form.get("tracking_type"),
            "redirect_url": form.get("redirect_url")
        },
        "lp": {
            "id": lp.get("id") if lp else None,
            "code": lp.get("code") if lp else None,
            "url": lp.get("url") if lp else None
        } if lp else None,
        "account": {
            "name": account.get("name") if account else None,
            "logos": {
                "main": account.get("logo_main_url") if account else None,
                "secondary": account.get("logo_secondary_url") if account else None,
                "mini": account.get("logo_mini_url") if account else None
            },
            "colors": {
                "primary": account.get("primary_color") if account else "#3B82F6",
                "secondary": account.get("secondary_color") if account else "#1E40AF"
            }
        } if account else None
    }


@router.get("/public/by-lp/{lp_code}")
async def get_forms_by_lp(lp_code: str):
    """
    Endpoint PUBLIC pour récupérer les formulaires liés à une LP.
    URL: /api/forms/public/by-lp/{lp_code}
    """
    lp = await db.lps.find_one({"code": lp_code}, {"_id": 0})
    if not lp:
        raise HTTPException(status_code=404, detail="LP non trouvée")
    
    forms = await db.forms.find(
        {"lp_id": lp.get("id"), "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    return {
        "lp": {
            "id": lp.get("id"),
            "code": lp.get("code"),
            "url": lp.get("url")
        },
        "forms": [{
            "id": f.get("id"),
            "code": f.get("code"),
            "name": f.get("name"),
            "url": f.get("url"),
            "product_type": f.get("product_type")
        } for f in forms]
    }


# ==================== ENDPOINTS CONFIG ====================

@router.get("/config/departements")
async def get_departements():
    """
    Retourne la liste des départements France métropolitaine (01-95 + 2A, 2B).
    Utilisé pour les sélecteurs de départements dans les formulaires.
    """
    departements = [
        {"code": "01", "nom": "Ain"},
        {"code": "02", "nom": "Aisne"},
        {"code": "03", "nom": "Allier"},
        {"code": "04", "nom": "Alpes-de-Haute-Provence"},
        {"code": "05", "nom": "Hautes-Alpes"},
        {"code": "06", "nom": "Alpes-Maritimes"},
        {"code": "07", "nom": "Ardèche"},
        {"code": "08", "nom": "Ardennes"},
        {"code": "09", "nom": "Ariège"},
        {"code": "10", "nom": "Aube"},
        {"code": "11", "nom": "Aude"},
        {"code": "12", "nom": "Aveyron"},
        {"code": "13", "nom": "Bouches-du-Rhône"},
        {"code": "14", "nom": "Calvados"},
        {"code": "15", "nom": "Cantal"},
        {"code": "16", "nom": "Charente"},
        {"code": "17", "nom": "Charente-Maritime"},
        {"code": "18", "nom": "Cher"},
        {"code": "19", "nom": "Corrèze"},
        {"code": "2A", "nom": "Corse-du-Sud"},
        {"code": "2B", "nom": "Haute-Corse"},
        {"code": "21", "nom": "Côte-d'Or"},
        {"code": "22", "nom": "Côtes-d'Armor"},
        {"code": "23", "nom": "Creuse"},
        {"code": "24", "nom": "Dordogne"},
        {"code": "25", "nom": "Doubs"},
        {"code": "26", "nom": "Drôme"},
        {"code": "27", "nom": "Eure"},
        {"code": "28", "nom": "Eure-et-Loir"},
        {"code": "29", "nom": "Finistère"},
        {"code": "30", "nom": "Gard"},
        {"code": "31", "nom": "Haute-Garonne"},
        {"code": "32", "nom": "Gers"},
        {"code": "33", "nom": "Gironde"},
        {"code": "34", "nom": "Hérault"},
        {"code": "35", "nom": "Ille-et-Vilaine"},
        {"code": "36", "nom": "Indre"},
        {"code": "37", "nom": "Indre-et-Loire"},
        {"code": "38", "nom": "Isère"},
        {"code": "39", "nom": "Jura"},
        {"code": "40", "nom": "Landes"},
        {"code": "41", "nom": "Loir-et-Cher"},
        {"code": "42", "nom": "Loire"},
        {"code": "43", "nom": "Haute-Loire"},
        {"code": "44", "nom": "Loire-Atlantique"},
        {"code": "45", "nom": "Loiret"},
        {"code": "46", "nom": "Lot"},
        {"code": "47", "nom": "Lot-et-Garonne"},
        {"code": "48", "nom": "Lozère"},
        {"code": "49", "nom": "Maine-et-Loire"},
        {"code": "50", "nom": "Manche"},
        {"code": "51", "nom": "Marne"},
        {"code": "52", "nom": "Haute-Marne"},
        {"code": "53", "nom": "Mayenne"},
        {"code": "54", "nom": "Meurthe-et-Moselle"},
        {"code": "55", "nom": "Meuse"},
        {"code": "56", "nom": "Morbihan"},
        {"code": "57", "nom": "Moselle"},
        {"code": "58", "nom": "Nièvre"},
        {"code": "59", "nom": "Nord"},
        {"code": "60", "nom": "Oise"},
        {"code": "61", "nom": "Orne"},
        {"code": "62", "nom": "Pas-de-Calais"},
        {"code": "63", "nom": "Puy-de-Dôme"},
        {"code": "64", "nom": "Pyrénées-Atlantiques"},
        {"code": "65", "nom": "Hautes-Pyrénées"},
        {"code": "66", "nom": "Pyrénées-Orientales"},
        {"code": "67", "nom": "Bas-Rhin"},
        {"code": "68", "nom": "Haut-Rhin"},
        {"code": "69", "nom": "Rhône"},
        {"code": "70", "nom": "Haute-Saône"},
        {"code": "71", "nom": "Saône-et-Loire"},
        {"code": "72", "nom": "Sarthe"},
        {"code": "73", "nom": "Savoie"},
        {"code": "74", "nom": "Haute-Savoie"},
        {"code": "75", "nom": "Paris"},
        {"code": "76", "nom": "Seine-Maritime"},
        {"code": "77", "nom": "Seine-et-Marne"},
        {"code": "78", "nom": "Yvelines"},
        {"code": "79", "nom": "Deux-Sèvres"},
        {"code": "80", "nom": "Somme"},
        {"code": "81", "nom": "Tarn"},
        {"code": "82", "nom": "Tarn-et-Garonne"},
        {"code": "83", "nom": "Var"},
        {"code": "84", "nom": "Vaucluse"},
        {"code": "85", "nom": "Vendée"},
        {"code": "86", "nom": "Vienne"},
        {"code": "87", "nom": "Haute-Vienne"},
        {"code": "88", "nom": "Vosges"},
        {"code": "89", "nom": "Yonne"},
        {"code": "90", "nom": "Territoire de Belfort"},
        {"code": "91", "nom": "Essonne"},
        {"code": "92", "nom": "Hauts-de-Seine"},
        {"code": "93", "nom": "Seine-Saint-Denis"},
        {"code": "94", "nom": "Val-de-Marne"},
        {"code": "95", "nom": "Val-d'Oise"}
    ]
    return {"departements": departements}


# ==================== ENDPOINTS AUTHENTIFIÉS ====================


@router.get("/brief/{form_id}")
async def get_form_brief(form_id: str, user: dict = Depends(get_current_user)):
    """Génère le brief complet pour un formulaire"""
    from services.brief_generator import generate_brief
    return await generate_brief(form_id)


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
        # Inclure les documents qui ont status=active OU qui n'ont pas de champ status
        if "$or" not in query:
            query["$or"] = []
        query["$or"] = [
            {"status": status},
            {"status": {"$exists": False}}
        ]
    
    # Exclure _id dans la projection
    cursor = db.forms.find(query)
    forms_raw = await cursor.to_list(200)
    
    # Convertir et trier
    forms = []
    for f in forms_raw:
        f.pop("_id", None)  # Supprimer _id
        forms.append(f)
    
    # Trier par created_at desc
    forms.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Enrichir avec stats et infos liées
    for form in forms:
        code = form.get("code", "")
        
        # Stats - EXCLURE les leads avec stats_reset: True
        started = await db.tracking.count_documents({
            "form_code": code, 
            "event": "form_start",
            "stats_reset": {"$ne": True}
        })
        leads_total = await db.leads.count_documents({
            "form_code": code,
            "stats_reset": {"$ne": True}
        })
        leads_sent = await db.leads.count_documents({
            "form_code": code, 
            "sent_to_crm": True,
            "stats_reset": {"$ne": True}
        })
        
        form["stats"] = {
            "started": started,
            "leads": leads_total,
            "sent": leads_sent,
            "conversion": round((leads_total / started * 100), 1) if started > 0 else 0
        }
        
        # Nom et logo du compte
        account = await db.accounts.find_one({"id": form.get("account_id")}, {"_id": 0, "name": 1, "logo": 1})
        form["account_name"] = account.get("name") if account else "N/A"
        form["account_logo"] = account.get("logo") if account else None
        
        # LP liée
        if form.get("lp_id"):
            lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0, "code": 1, "name": 1, "url": 1})
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
    
    # Stats - "finished" = tous les leads créés (pas seulement success/duplicate)
    # EXCLURE les leads avec stats_reset: True
    started = await db.tracking.count_documents({
        "form_code": code, 
        "event": "form_start",
        "stats_reset": {"$ne": True}
    })
    finished = await db.leads.count_documents({
        "form_code": code,
        "stats_reset": {"$ne": True}
    })
    sent = await db.leads.count_documents({
        "form_code": code, 
        "sent_to_crm": True,
        "stats_reset": {"$ne": True}
    })
    
    form["stats"] = {
        "started": started,
        "finished": finished,
        "sent": sent,
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
        "target_crm": data.target_crm or "",  # CRM cible (zr7/mdl)
        "crm_api_key": data.crm_api_key or "",
        "allow_cross_crm": data.allow_cross_crm if data.allow_cross_crm is not None else True,
        "tracking_type": data.tracking_type or "redirect",
        "redirect_url": data.redirect_url or "/merci",
        "redirect_url_pv": data.redirect_url_pv or "",
        "redirect_url_pac": data.redirect_url_pac or "",
        "redirect_url_ite": data.redirect_url_ite or "",
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
    
    # SÉCURITÉ : Empêcher la suppression de la clé API une fois enregistrée
    existing_api_key = form.get("crm_api_key", "")
    if existing_api_key and data.crm_api_key is not None:
        if data.crm_api_key == "" or data.crm_api_key.strip() == "":
            raise HTTPException(
                status_code=400, 
                detail="Impossible de supprimer la clé API une fois enregistrée. Contactez un administrateur."
            )
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # SÉCURITÉ : Le code du formulaire (tracking) ne peut JAMAIS être modifié
    update_data.pop("code", None)
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


# ==================== ADMIN : RESET STATS ====================

@router.post("/{form_id}/reset-stats")
async def reset_form_stats(
    form_id: str,
    user: dict = Depends(require_admin)
):
    """
    Remet les stats d'un formulaire à 0 (admin seulement).
    Les leads ne sont PAS supprimés, seulement les compteurs.
    
    Crée un snapshot des stats avant reset pour historique.
    """
    # Récupérer le formulaire
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="Formulaire non trouvé")
    
    form_code = form.get("code", "")
    
    # Compter les leads actuels pour le snapshot
    total_leads = await db.leads.count_documents({"form_code": form_code})
    success_leads = await db.leads.count_documents({"form_code": form_code, "api_status": "success"})
    
    # Créer un snapshot avant reset
    snapshot = {
        "id": str(uuid.uuid4()),
        "form_id": form_id,
        "form_code": form_code,
        "type": "stats_reset",
        "stats_before_reset": {
            "total": total_leads,
            "success": success_leads
        },
        "reset_by": user.get("email"),
        "reset_at": now_iso()
    }
    await db.stats_snapshots.insert_one(snapshot)
    
    # Marquer les leads existants comme "pre-reset" 
    # (pour ne plus les compter dans les stats actuelles)
    await db.leads.update_many(
        {"form_code": form_code, "stats_reset": {"$ne": True}},
        {"$set": {
            "stats_reset": True,
            "stats_reset_at": now_iso()
        }}
    )
    
    # Marquer aussi les tracking events (form_start) comme resetés
    await db.tracking.update_many(
        {"form_code": form_code, "stats_reset": {"$ne": True}},
        {"$set": {
            "stats_reset": True,
            "stats_reset_at": now_iso()
        }}
    )
    
    # Mettre à jour le formulaire
    await db.forms.update_one(
        {"id": form_id},
        {"$set": {
            "stats_reset_at": now_iso(),
            "stats_reset_by": user.get("email")
        }}
    )
    
    # Log activité
    await db.activity_log.insert_one({
        "user_id": user.get("id"),
        "user_email": user.get("email"),
        "action": "reset_stats",
        "entity_type": "form",
        "entity_id": form_id,
        "entity_name": form_code,
        "details": {"leads_affected": total_leads},
        "created_at": now_iso()
    })
    
    return {
        "success": True,
        "message": f"Stats remises à 0 pour {form_code}",
        "leads_affected": total_leads,
        "snapshot_id": snapshot["id"]
    }

