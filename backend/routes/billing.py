"""
Routes pour la Facturation inter-CRM
- Prix des leads par produit/département
- Historique de facturation
- Dashboard facturation
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import uuid

from config import db, now_iso
from routes.auth import get_current_user, require_admin

router = APIRouter(prefix="/billing", tags=["Facturation"])


# ==================== MODELS ====================

class LeadPriceCreate(BaseModel):
    product_type: str  # PV, PAC, ITE
    department: str    # 75, 92, etc. ou "default"
    price: float       # Prix en euros
    from_crm_id: Optional[str] = ""  # CRM source (vide = tous)
    to_crm_id: Optional[str] = ""    # CRM destination (vide = tous)

class BillingPeriodCreate(BaseModel):
    year: int
    month: int
    from_crm_id: str
    to_crm_id: str


# ==================== PRIX DES LEADS ====================

@router.get("/prices")
async def list_prices(user: dict = Depends(get_current_user)):
    """Liste tous les prix configurés"""
    prices = await db.lead_prices.find({}, {"_id": 0}).to_list(100)
    return {"prices": prices}


@router.post("/prices")
async def create_price(data: LeadPriceCreate, user: dict = Depends(require_admin)):
    """Créer ou mettre à jour un prix"""
    # Chercher si existe déjà
    existing = await db.lead_prices.find_one({
        "product_type": data.product_type,
        "department": data.department,
        "from_crm_id": data.from_crm_id or "",
        "to_crm_id": data.to_crm_id or ""
    })
    
    if existing:
        # Mettre à jour
        await db.lead_prices.update_one(
            {"_id": existing["_id"]},
            {"$set": {"price": data.price, "updated_at": now_iso()}}
        )
        return {"success": True, "action": "updated", "price": data.price}
    else:
        # Créer
        price_doc = {
            "id": str(uuid.uuid4()),
            "product_type": data.product_type,
            "department": data.department,
            "price": data.price,
            "from_crm_id": data.from_crm_id or "",
            "to_crm_id": data.to_crm_id or "",
            "created_at": now_iso()
        }
        await db.lead_prices.insert_one(price_doc)
        return {"success": True, "action": "created", "id": price_doc["id"]}


@router.delete("/prices/{price_id}")
async def delete_price(price_id: str, user: dict = Depends(require_admin)):
    """Supprimer un prix"""
    result = await db.lead_prices.delete_one({"id": price_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prix non trouvé")
    return {"success": True}


async def get_lead_price(product_type: str, department: str, from_crm_id: str = "", to_crm_id: str = "") -> float:
    """
    Récupère le prix d'un lead selon le produit et département.
    Ordre de priorité:
    1. Prix spécifique produit + département + CRMs
    2. Prix spécifique produit + département
    3. Prix par défaut du produit
    4. Prix par défaut global (10€)
    """
    # 1. Prix spécifique complet
    price = await db.lead_prices.find_one({
        "product_type": product_type,
        "department": department,
        "from_crm_id": from_crm_id,
        "to_crm_id": to_crm_id
    })
    if price:
        return price["price"]
    
    # 2. Prix produit + département
    price = await db.lead_prices.find_one({
        "product_type": product_type,
        "department": department,
        "from_crm_id": "",
        "to_crm_id": ""
    })
    if price:
        return price["price"]
    
    # 3. Prix par défaut du produit
    price = await db.lead_prices.find_one({
        "product_type": product_type,
        "department": "default"
    })
    if price:
        return price["price"]
    
    # 4. Prix par défaut global
    return 10.0


# ==================== HISTORIQUE FACTURATION ====================

@router.get("/history")
async def get_billing_history(
    year: Optional[int] = None,
    month: Optional[int] = None,
    from_crm_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Historique de facturation"""
    query = {}
    if year:
        query["year"] = year
    if month:
        query["month"] = month
    if from_crm_id:
        query["from_crm_id"] = from_crm_id
    
    history = await db.billing_history.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return {"history": history}


@router.post("/calculate")
async def calculate_billing(data: BillingPeriodCreate, user: dict = Depends(require_admin)):
    """
    Calcule la facturation pour une période donnée.
    Compte tous les leads envoyés avec succès.
    """
    # Dates de la période
    start_date = datetime(data.year, data.month, 1, tzinfo=timezone.utc)
    if data.month == 12:
        end_date = datetime(data.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(data.year, data.month + 1, 1, tzinfo=timezone.utc)
    
    # Récupérer les leads de la période
    leads = await db.leads.find({
        "created_at": {
            "$gte": start_date.isoformat(),
            "$lt": end_date.isoformat()
        },
        "api_status": {"$in": ["success", "duplicate"]},
        "target_crm_id": data.to_crm_id
    }, {"_id": 0}).to_list(10000)
    
    # Calculer par produit/département
    breakdown = {}
    total_amount = 0.0
    total_leads = 0
    
    for lead in leads:
        product = lead.get("product_type", "PV")
        dept = lead.get("departement", "00")
        key = f"{product}_{dept}"
        
        price = await get_lead_price(product, dept, data.from_crm_id, data.to_crm_id)
        
        if key not in breakdown:
            breakdown[key] = {"product": product, "department": dept, "count": 0, "price": price, "total": 0}
        
        breakdown[key]["count"] += 1
        breakdown[key]["total"] += price
        total_amount += price
        total_leads += 1
    
    # Sauvegarder ou mettre à jour
    existing = await db.billing_history.find_one({
        "year": data.year,
        "month": data.month,
        "from_crm_id": data.from_crm_id,
        "to_crm_id": data.to_crm_id
    })
    
    billing_doc = {
        "year": data.year,
        "month": data.month,
        "from_crm_id": data.from_crm_id,
        "to_crm_id": data.to_crm_id,
        "total_leads": total_leads,
        "total_amount": round(total_amount, 2),
        "breakdown": list(breakdown.values()),
        "calculated_at": now_iso(),
        "status": "draft"  # draft, sent, paid
    }
    
    if existing:
        await db.billing_history.update_one({"_id": existing["_id"]}, {"$set": billing_doc})
        billing_doc["id"] = existing.get("id")
    else:
        billing_doc["id"] = str(uuid.uuid4())
        await db.billing_history.insert_one(billing_doc)
    
    return {
        "success": True,
        "billing": {
            "period": f"{data.year}-{data.month:02d}",
            "total_leads": total_leads,
            "total_amount": round(total_amount, 2),
            "breakdown": list(breakdown.values())
        }
    }


@router.put("/history/{billing_id}/status")
async def update_billing_status(billing_id: str, status: str, user: dict = Depends(require_admin)):
    """Mettre à jour le statut d'une facturation (draft, sent, paid)"""
    if status not in ["draft", "sent", "paid"]:
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    result = await db.billing_history.update_one(
        {"id": billing_id},
        {"$set": {"status": status, "updated_at": now_iso()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Facturation non trouvée")
    
    return {"success": True, "status": status}


# ==================== STATS FACTURATION ====================

@router.get("/stats")
async def get_billing_stats(user: dict = Depends(get_current_user)):
    """Stats de facturation globales"""
    # Ce mois
    now = datetime.now(timezone.utc)
    this_month = await db.billing_history.find_one({
        "year": now.year,
        "month": now.month
    })
    
    # Mois dernier
    last_month_date = now - timedelta(days=30)
    last_month = await db.billing_history.find_one({
        "year": last_month_date.year,
        "month": last_month_date.month
    })
    
    # Total année
    year_history = await db.billing_history.find({
        "year": now.year,
        "status": {"$in": ["sent", "paid"]}
    }).to_list(12)
    
    year_total = sum(h.get("total_amount", 0) for h in year_history)
    year_leads = sum(h.get("total_leads", 0) for h in year_history)
    
    return {
        "this_month": {
            "total_leads": this_month.get("total_leads", 0) if this_month else 0,
            "total_amount": this_month.get("total_amount", 0) if this_month else 0
        },
        "last_month": {
            "total_leads": last_month.get("total_leads", 0) if last_month else 0,
            "total_amount": last_month.get("total_amount", 0) if last_month else 0
        },
        "year_total": {
            "total_leads": year_leads,
            "total_amount": round(year_total, 2)
        }
    }
