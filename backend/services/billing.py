"""
Service de facturation inter-CRM
- Calcule les leads envoyés entre CRMs
- Si ZR7 envoie à MDL → MDL doit à ZR7
- Vue par période (7 jours, 1 mois, personnalisé)
"""

import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso
from typing import Optional

logger = logging.getLogger("billing")


async def get_cross_crm_billing(
    period: str = "month",  # "week", "month", "custom"
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> dict:
    """
    Calcule la facturation inter-CRM.
    
    Logique:
    - Un lead est "cross-CRM" si routing_reason commence par "cross_crm_"
    - Le CRM d'origine (celui du compte/form) doit recevoir le paiement
    - Le CRM destination (celui qui a reçu le lead) doit payer
    
    Args:
        period: "week" (7 jours), "month" (30 jours), ou "custom"
        date_from: Date de début (pour période custom)
        date_to: Date de fin (pour période custom)
    
    Returns:
        dict: Rapport de facturation avec les montants par CRM
    """
    # Calculer les dates
    now = datetime.now(timezone.utc)
    
    if period == "week":
        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()
    elif period == "month":
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
    elif period == "custom" and date_from and date_to:
        start_date = date_from
        end_date = date_to
    else:
        # Par défaut: 30 jours
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
    
    # Récupérer les CRMs
    crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {c["id"]: c for c in crms}
    crm_by_slug = {c["slug"]: c for c in crms}
    
    # Récupérer les commandes (pour les prix)
    commandes = await db.commandes.find({}, {"_id": 0}).to_list(100)
    
    # Map crm_id -> prix moyen par lead
    prix_par_crm = {}
    for cmd in commandes:
        crm_id = cmd.get("crm_id")
        prix = cmd.get("prix_unitaire", 0)
        if crm_id not in prix_par_crm:
            prix_par_crm[crm_id] = []
        if prix > 0:
            prix_par_crm[crm_id].append(prix)
    
    # Calculer prix moyen par CRM
    for crm_id in prix_par_crm:
        prices = prix_par_crm[crm_id]
        prix_par_crm[crm_id] = sum(prices) / len(prices) if prices else 0
    
    # Récupérer les leads cross-CRM de la période
    cross_crm_leads = await db.leads.find({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "routing_reason": {"$regex": "^cross_crm_"},
        "api_status": {"$in": ["success", "duplicate"]}  # Seulement les leads intégrés
    }, {"_id": 0}).to_list(10000)
    
    # Récupérer aussi les leads normaux pour comparaison
    all_leads = await db.leads.find({
        "created_at": {"$gte": start_date, "$lte": end_date},
        "api_status": {"$in": ["success", "duplicate"]}
    }, {"_id": 0}).to_list(10000)
    
    # Calculer les transactions inter-CRM
    # Structure: {crm_qui_doit: {crm_a_qui_il_doit: {count, amount}}}
    transactions = {}
    
    # Détails par lead
    lead_details = []
    
    for lead in cross_crm_leads:
        routing = lead.get("routing_reason", "")
        
        # Extraire le CRM destination du routing_reason (ex: "cross_crm_mdl" -> "mdl")
        if routing.startswith("cross_crm_"):
            dest_slug = routing.replace("cross_crm_", "")
            dest_crm = crm_by_slug.get(dest_slug)
            
            if not dest_crm:
                continue
            
            dest_crm_id = dest_crm.get("id")
            dest_crm_name = dest_crm.get("name")
            
            # Trouver le CRM d'origine (celui du compte)
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
            
            # Le CRM destination (qui a reçu le lead) doit payer au CRM d'origine
            # Donc: dest_crm doit à origin_crm
            
            # Utiliser le prix de la commande du CRM d'origine
            prix = prix_par_crm.get(origin_crm_id, 0)
            
            # Initialiser si nécessaire
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
            
            # Détail du lead
            lead_details.append({
                "lead_id": lead.get("id"),
                "phone": lead.get("phone", "")[-4:],  # 4 derniers chiffres
                "product_type": lead.get("product_type"),
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
        "total_leads_period": len(all_leads),
        "cross_crm_leads": len(cross_crm_leads),
        "cross_crm_percentage": round(len(cross_crm_leads) / len(all_leads) * 100, 1) if all_leads else 0,
        "transactions": [],
        "balances": {}
    }
    
    # Transformer les transactions en liste lisible
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
            
            # Calculer les balances nettes
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
    
    # Ajouter les détails des leads
    summary["lead_details"] = lead_details
    
    return summary


async def get_billing_by_crm(crm_id: str, period: str = "month") -> dict:
    """
    Récupère la facturation pour un CRM spécifique.
    """
    billing = await get_cross_crm_billing(period=period)
    
    crm_balance = billing.get("balances", {}).get(crm_id, {
        "owes": 0,
        "owed": 0,
        "net": 0
    })
    
    # Filtrer les transactions concernant ce CRM
    crm_transactions = [
        tx for tx in billing.get("transactions", [])
        if tx["debtor"]["id"] == crm_id or tx["creditor"]["id"] == crm_id
    ]
    
    # Filtrer les détails de leads (simplification car billing n'est pas async)
    crm_leads = [
        lead for lead in billing.get("lead_details", [])
    ]
    
    return {
        "crm_id": crm_id,
        "period": billing.get("period"),
        "balance": crm_balance,
        "transactions": crm_transactions,
        "leads_count": len(crm_leads)
    }
