"""
Service de facturation inter-CRM
- Calcule les leads envoyés entre CRMs
- Si ZR7 envoie à MDL → MDL doit à ZR7
- Vue par semaine avec navigation
- Statut facturé/non facturé
"""

import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso
from typing import Optional

logger = logging.getLogger("billing")


def get_week_bounds(year: int, week: int):
    """
    Retourne les dates de début et fin d'une semaine ISO.
    """
    # Premier jour de l'année
    jan1 = datetime(year, 1, 1, tzinfo=timezone.utc)
    
    # Trouver le premier lundi de la semaine 1
    # Semaine 1 contient le 4 janvier
    jan4 = datetime(year, 1, 4, tzinfo=timezone.utc)
    first_monday = jan4 - timedelta(days=jan4.weekday())
    
    # Calculer le lundi de la semaine demandée
    week_start = first_monday + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def get_current_week():
    """Retourne année et numéro de semaine ISO actuels."""
    now = datetime.now(timezone.utc)
    iso_cal = now.isocalendar()
    return iso_cal.year, iso_cal.week


async def get_cross_crm_billing(
    period: str = "month",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    year: Optional[int] = None,
    week: Optional[int] = None
) -> dict:
    """
    Calcule la facturation inter-CRM.
    
    Args:
        period: "week", "month", "custom", ou "specific_week"
        date_from/date_to: Pour période custom
        year/week: Pour semaine spécifique
    
    Returns:
        dict: Rapport de facturation
    """
    now = datetime.now(timezone.utc)
    week_info = None
    
    # Déterminer les dates selon la période
    if period == "specific_week" and year and week:
        week_start, week_end = get_week_bounds(year, week)
        start_date = week_start.isoformat()
        end_date = week_end.isoformat()
        week_info = {
            "year": year,
            "week": week,
            "start": week_start.strftime("%d/%m/%Y"),
            "end": week_end.strftime("%d/%m/%Y")
        }
    elif period == "week":
        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()
    elif period == "month":
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
    elif period == "custom" and date_from and date_to:
        # Convertir dates simples en ISO
        if len(date_from) == 10:  # Format YYYY-MM-DD
            start_date = f"{date_from}T00:00:00+00:00"
        else:
            start_date = date_from
        if len(date_to) == 10:
            end_date = f"{date_to}T23:59:59+00:00"
        else:
            end_date = date_to
    else:
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
    
    # Récupérer les CRMs
    crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {c["id"]: c for c in crms}
    crm_by_slug = {c["slug"]: c for c in crms}
    
    # Récupérer les commandes (pour les prix)
    commandes = await db.commandes.find({}, {"_id": 0}).to_list(100)
    
    # Map crm_id + product_type -> prix
    prix_par_crm_product = {}
    for cmd in commandes:
        crm_id = cmd.get("crm_id")
        product = cmd.get("product_type", "*")
        prix = cmd.get("prix_unitaire", 0)
        key = f"{crm_id}_{product}"
        if prix > 0:
            prix_par_crm_product[key] = prix
    
    # Prix moyen par CRM (fallback)
    prix_moyen_crm = {}
    for cmd in commandes:
        crm_id = cmd.get("crm_id")
        prix = cmd.get("prix_unitaire", 0)
        if crm_id not in prix_moyen_crm:
            prix_moyen_crm[crm_id] = []
        if prix > 0:
            prix_moyen_crm[crm_id].append(prix)
    
    for crm_id in prix_moyen_crm:
        prices = prix_moyen_crm[crm_id]
        prix_moyen_crm[crm_id] = sum(prices) / len(prices) if prices else 0
    
    # Récupérer les leads cross-CRM de la période
    cross_crm_leads = await db.leads.find({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "routing_reason": {"$regex": "^cross_crm_"},
        "api_status": {"$in": ["success", "duplicate"]}
    }, {"_id": 0}).to_list(10000)
    
    # Récupérer tous les leads pour comparaison
    all_leads = await db.leads.find({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "api_status": {"$in": ["success", "duplicate"]}
    }, {"_id": 0}).to_list(10000)
    
    # Calculer les transactions
    transactions = {}
    lead_details = []
    
    for lead in cross_crm_leads:
        routing = lead.get("routing_reason", "")
        
        if routing.startswith("cross_crm_"):
            dest_slug = routing.replace("cross_crm_", "")
            dest_crm = crm_by_slug.get(dest_slug)
            
            if not dest_crm:
                continue
            
            dest_crm_id = dest_crm.get("id")
            dest_crm_name = dest_crm.get("name")
            
            # Trouver le CRM d'origine
            form = await db.forms.find_one({"code": lead.get("form_code")})
            if not form:
                continue
            
            account = await db.accounts.find_one({"id": form.get("account_id")})
            if not account:
                continue
            
            origin_crm_id = account.get("crm_id")
            origin_crm = crm_map.get(origin_crm_id)
            
            if not origin_crm:
                continue
            
            origin_crm_name = origin_crm.get("name")
            product_type = lead.get("product_type") or form.get("product_type", "PV")
            
            # Chercher le prix spécifique produit, sinon prix moyen
            prix_key = f"{origin_crm_id}_{product_type}"
            prix = prix_par_crm_product.get(prix_key, prix_moyen_crm.get(origin_crm_id, 0))
            
            # Initialiser transactions
            if dest_crm_id not in transactions:
                transactions[dest_crm_id] = {}
            
            if origin_crm_id not in transactions[dest_crm_id]:
                transactions[dest_crm_id][origin_crm_id] = {
                    "count": 0,
                    "amount": 0,
                    "from_crm_name": dest_crm_name,
                    "to_crm_name": origin_crm_name
                }
            
            transactions[dest_crm_id][origin_crm_id]["count"] += 1
            transactions[dest_crm_id][origin_crm_id]["amount"] += prix
            
            lead_details.append({
                "lead_id": lead.get("id"),
                "phone": lead.get("phone", "")[-4:],
                "product_type": product_type,
                "departement": lead.get("departement"),
                "origin_crm": origin_crm_name,
                "dest_crm": dest_crm_name,
                "prix": prix,
                "date": lead.get("created_at", "")[:10]
            })
    
    # Construire le résumé
    summary = {
        "period": {
            "type": period,
            "from": start_date,
            "to": end_date
        },
        "week_info": week_info,
        "total_leads_period": len(all_leads),
        "cross_crm_leads": len(cross_crm_leads),
        "cross_crm_percentage": round(len(cross_crm_leads) / len(all_leads) * 100, 1) if all_leads else 0,
        "transactions": [],
        "balances": {}
    }
    
    # Transformer les transactions en liste
    for debtor_crm_id, creditors in transactions.items():
        debtor_crm = crm_map.get(debtor_crm_id, {})
        
        for creditor_crm_id, data in creditors.items():
            creditor_crm = crm_map.get(creditor_crm_id, {})
            
            summary["transactions"].append({
                "debtor": {
                    "id": debtor_crm_id,
                    "name": debtor_crm.get("name", "Inconnu"),
                    "slug": debtor_crm.get("slug", "")
                },
                "creditor": {
                    "id": creditor_crm_id,
                    "name": creditor_crm.get("name", "Inconnu"),
                    "slug": creditor_crm.get("slug", "")
                },
                "count": data["count"],
                "amount": round(data["amount"], 2),
                "description": f"{debtor_crm.get('name')} doit {round(data['amount'], 2)}€ à {creditor_crm.get('name')} ({data['count']} leads)"
            })
            
            # Balances
            if debtor_crm_id not in summary["balances"]:
                summary["balances"][debtor_crm_id] = {
                    "name": debtor_crm.get("name"),
                    "slug": debtor_crm.get("slug"),
                    "owes": 0,
                    "owed": 0,
                    "net": 0
                }
            
            if creditor_crm_id not in summary["balances"]:
                summary["balances"][creditor_crm_id] = {
                    "name": creditor_crm.get("name"),
                    "slug": creditor_crm.get("slug"),
                    "owes": 0,
                    "owed": 0,
                    "net": 0
                }
            
            summary["balances"][debtor_crm_id]["owes"] += data["amount"]
            summary["balances"][creditor_crm_id]["owed"] += data["amount"]
    
    # Calculer les balances nettes
    for crm_id in summary["balances"]:
        balance = summary["balances"][crm_id]
        balance["owes"] = round(balance["owes"], 2)
        balance["owed"] = round(balance["owed"], 2)
        balance["net"] = round(balance["owed"] - balance["owes"], 2)
    
    summary["lead_details"] = lead_details
    
    return summary


async def get_week_billing(year: int, week: int) -> dict:
    """
    Récupère la facturation pour une semaine spécifique.
    """
    return await get_cross_crm_billing(
        period="specific_week",
        year=year,
        week=week
    )


async def mark_week_as_invoiced(year: int, week: int, invoiced: bool = True) -> dict:
    """
    Marque une semaine comme facturée ou non.
    """
    week_start, week_end = get_week_bounds(year, week)
    week_key = f"{year}_W{week:02d}"
    
    # Vérifier si existe déjà
    existing = await db.billing_weeks.find_one({"week_key": week_key})
    
    billing_data = await get_week_billing(year, week)
    
    doc = {
        "week_key": week_key,
        "year": year,
        "week": week,
        "start_date": week_start.isoformat(),
        "end_date": week_end.isoformat(),
        "invoiced": invoiced,
        "invoiced_at": now_iso() if invoiced else None,
        "total_leads": billing_data.get("total_leads_period", 0),
        "cross_crm_leads": billing_data.get("cross_crm_leads", 0),
        "transactions": billing_data.get("transactions", []),
        "balances": billing_data.get("balances", {}),
        "updated_at": now_iso()
    }
    
    if existing:
        await db.billing_weeks.update_one(
            {"week_key": week_key},
            {"$set": doc}
        )
    else:
        doc["created_at"] = now_iso()
        await db.billing_weeks.insert_one(doc)
    
    return {
        "success": True,
        "week_key": week_key,
        "invoiced": invoiced,
        "message": f"Semaine {week}/{year} marquée comme {'facturée' if invoiced else 'non facturée'}"
    }


async def get_week_invoice_status(year: int, week: int) -> dict:
    """
    Récupère le statut de facturation d'une semaine.
    """
    week_key = f"{year}_W{week:02d}"
    doc = await db.billing_weeks.find_one({"week_key": week_key}, {"_id": 0})
    
    if doc:
        return {
            "exists": True,
            "invoiced": doc.get("invoiced", False),
            "invoiced_at": doc.get("invoiced_at"),
            "data": doc
        }
    
    return {
        "exists": False,
        "invoiced": False,
        "invoiced_at": None,
        "data": None
    }


async def list_invoiced_weeks(limit: int = 52) -> list:
    """
    Liste les semaines facturées.
    """
    weeks = await db.billing_weeks.find(
        {},
        {"_id": 0}
    ).sort("week_key", -1).to_list(limit)
    
    return weeks
