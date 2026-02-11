"""
Routes pour les statistiques par département
"""

from fastapi import APIRouter, Depends, Query
from config import db, now_iso
from routes.auth import get_current_user
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter(prefix="/stats", tags=["Statistiques"])


@router.get("/departements")
async def get_stats_departements(
    crm_id: str = None,
    departements: str = None,  # Comma-separated: "75,92,93"
    product_type: str = None,
    date_from: str = None,
    date_to: str = None,
    period: str = None,  # "today", "week", "month", "custom"
    user: dict = Depends(get_current_user)
):
    """
    Statistiques des leads par département
    """
    # Construire le filtre de date
    date_filter = {}
    
    if period == "today":
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"created_at": {"$gte": today.isoformat()}}
    elif period == "week":
        week_ago = datetime.utcnow() - timedelta(days=7)
        date_filter = {"created_at": {"$gte": week_ago.isoformat()}}
    elif period == "month":
        month_ago = datetime.utcnow() - timedelta(days=30)
        date_filter = {"created_at": {"$gte": month_ago.isoformat()}}
    elif date_from and date_to:
        date_filter = {"created_at": {"$gte": date_from, "$lte": date_to}}
    elif date_from:
        date_filter = {"created_at": {"$gte": date_from}}
    
    # Construire le query principal
    query = {**date_filter}
    
    # Filtre par départements
    if departements:
        dept_list = [d.strip() for d in departements.split(",")]
        query["departement"] = {"$in": dept_list}
    
    # Filtre par produit
    if product_type:
        query["product_type"] = product_type
    
    # Filtre par CRM (via account)
    if crm_id:
        # Trouver les accounts de ce CRM
        accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        account_ids = [a["id"] for a in accounts]
        
        # Trouver les forms de ces accounts
        forms = await db.forms.find({"account_id": {"$in": account_ids}}, {"code": 1}).to_list(500)
        form_codes = [f["code"] for f in forms]
        
        query["form_code"] = {"$in": form_codes}
    
    # Récupérer les leads avec projection des champs nécessaires uniquement
    projection = {
        "_id": 0,
        "departement": 1,
        "product_type": 1,
        "source": 1,
        "utm_source": 1,
        "api_status": 1,
        "created_at": 1
    }
    leads = await db.leads.find(query, projection).to_list(5000)
    
    # Agréger par département
    by_departement = {}
    by_product = {"PV": 0, "PAC": 0, "ITE": 0}
    by_source = {}
    by_status = {"success": 0, "failed": 0, "no_crm": 0, "queued": 0, "duplicate": 0}
    
    for lead in leads:
        dept = lead.get("departement", "??")
        product = lead.get("product_type", "PV")
        source = lead.get("source", "") or lead.get("utm_source", "") or "Direct"
        status = lead.get("api_status", "pending")
        
        # Par département
        if dept not in by_departement:
            by_departement[dept] = {"total": 0, "PV": 0, "PAC": 0, "ITE": 0}
        by_departement[dept]["total"] += 1
        by_departement[dept][product] = by_departement[dept].get(product, 0) + 1
        
        # Par produit
        by_product[product] = by_product.get(product, 0) + 1
        
        # Par source
        if source not in by_source:
            by_source[source] = {"total": 0, "PV": 0, "PAC": 0, "ITE": 0}
        by_source[source]["total"] += 1
        by_source[source][product] = by_source[source].get(product, 0) + 1
        
        # Par status
        by_status[status] = by_status.get(status, 0) + 1
    
    # Trier départements par nombre de leads
    sorted_depts = sorted(by_departement.items(), key=lambda x: x[1]["total"], reverse=True)
    
    # Trier sources par nombre de leads
    sorted_sources = sorted(by_source.items(), key=lambda x: x[1]["total"], reverse=True)
    
    return {
        "total_leads": len(leads),
        "by_departement": dict(sorted_depts),
        "by_product": by_product,
        "by_source": dict(sorted_sources),
        "by_status": by_status,
        "filters": {
            "crm_id": crm_id,
            "departements": departements,
            "product_type": product_type,
            "period": period,
            "date_from": date_from,
            "date_to": date_to
        }
    }


@router.get("/timeline")
async def get_stats_timeline(
    crm_id: str = None,
    days: int = 7,
    user: dict = Depends(get_current_user)
):
    """
    Statistiques des leads sur une période (timeline)
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = {"created_at": {"$gte": start_date.isoformat()}}
    
    if crm_id:
        accounts = await db.accounts.find({"crm_id": crm_id}, {"id": 1}).to_list(100)
        account_ids = [a["id"] for a in accounts]
        forms = await db.forms.find({"account_id": {"$in": account_ids}}, {"code": 1}).to_list(500)
        form_codes = [f["code"] for f in forms]
        query["form_code"] = {"$in": form_codes}
    
    leads = await db.leads.find(query, {"_id": 0, "created_at": 1, "product_type": 1}).to_list(10000)
    
    # Agréger par jour
    by_day = {}
    for lead in leads:
        day = lead.get("created_at", "")[:10]  # YYYY-MM-DD
        product = lead.get("product_type", "PV")
        
        if day not in by_day:
            by_day[day] = {"total": 0, "PV": 0, "PAC": 0, "ITE": 0}
        by_day[day]["total"] += 1
        by_day[day][product] = by_day[day].get(product, 0) + 1
    
    # Trier par date
    sorted_days = sorted(by_day.items())
    
    return {
        "total": len(leads),
        "days": days,
        "timeline": dict(sorted_days)
    }
