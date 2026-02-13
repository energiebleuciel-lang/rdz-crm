"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Moteur de Routing                                                 ║
║                                                                              ║
║  RÔLE: Trouver le meilleur client pour un lead selon:                        ║
║  1. Entité (ZR7/MDL) - obligatoire                                           ║
║  2. Produit (PV/PAC/ITE)                                                     ║
║  3. Département                                                              ║
║  4. Commandes actives avec quota disponible                                  ║
║  5. Priorité des commandes                                                   ║
║  6. Règle doublon 30 jours (éviter client déjà servi)                        ║
║                                                                              ║
║  RÉSULTAT: Client trouvé OU lead en statut "non_livre"                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from config import db
from services.duplicate_detector_v2 import check_duplicate_30_days, check_duplicate_for_any_client

logger = logging.getLogger("routing_engine")


class RoutingResult:
    """Résultat du routing d'un lead"""
    
    def __init__(
        self,
        success: bool,
        client_id: Optional[str] = None,
        client_name: Optional[str] = None,
        commande_id: Optional[str] = None,
        is_lb: bool = False,
        reason: str = ""
    ):
        self.success = success
        self.client_id = client_id
        self.client_name = client_name
        self.commande_id = commande_id
        self.is_lb = is_lb
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "commande_id": self.commande_id,
            "is_lb": self.is_lb,
            "reason": self.reason
        }


def get_week_start() -> str:
    """Retourne le lundi de la semaine courante (ISO)"""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


async def get_commande_stats(commande_id: str, week_start: str) -> Dict[str, int]:
    """
    Récupère les stats de la commande pour la semaine en cours
    """
    # Compter les leads livrés cette semaine pour cette commande
    pipeline = [
        {
            "$match": {
                "delivery_commande_id": commande_id,
                "status": "livre",
                "delivered_at": {"$gte": week_start}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_delivered": {"$sum": 1},
                "lb_delivered": {"$sum": {"$cond": [{"$eq": ["$is_lb", True]}, 1, 0]}}
            }
        }
    ]
    
    result = await db.leads.aggregate(pipeline).to_list(1)
    
    if result:
        return {
            "leads_delivered": result[0].get("total_delivered", 0),
            "lb_delivered": result[0].get("lb_delivered", 0)
        }
    return {"leads_delivered": 0, "lb_delivered": 0}


async def find_eligible_commandes(
    entity: str,
    product_type: str,
    departement: str,
    is_lb: bool = False
) -> List[Dict]:
    """
    Trouve toutes les commandes éligibles pour un lead
    
    Critères:
    - Même entité
    - Produit correspondant
    - Département couvert
    - Commande active
    - Quota non atteint
    - Si LB: lb_percent_max > 0
    
    Tri par priorité (1=haute)
    """
    week_start = get_week_start()
    
    # Requête de base
    query = {
        "entity": entity,
        "product_type": product_type,
        "active": True,
        "$or": [
            {"departements": departement},
            {"departements": "*"}  # Wildcard = tous
        ]
    }
    
    # Récupérer les commandes candidates
    commandes = await db.commandes.find(query, {"_id": 0}).sort("priorite", 1).to_list(100)
    
    eligible = []
    
    for cmd in commandes:
        cmd_id = cmd.get("id")
        
        # Récupérer le client
        client = await db.clients.find_one(
            {"id": cmd.get("client_id")}, 
            {"_id": 0, "name": 1, "active": 1}
        )
        if not client or not client.get("active", True):
            continue
        
        cmd["client_name"] = client.get("name", "")
        
        # Vérifier quota
        quota = cmd.get("quota_semaine", 0)
        if quota > 0:
            stats = await get_commande_stats(cmd_id, week_start)
            delivered = stats.get("leads_delivered", 0)
            lb_delivered = stats.get("lb_delivered", 0)
            
            if delivered >= quota:
                logger.debug(f"Commande {cmd_id}: quota atteint ({delivered}/{quota})")
                continue
            
            cmd["quota_remaining"] = quota - delivered
            cmd["leads_delivered_this_week"] = delivered
            cmd["lb_delivered_this_week"] = lb_delivered
        else:
            cmd["quota_remaining"] = 999999  # Illimité
        
        # Si LB, vérifier % autorisé
        if is_lb:
            lb_max = cmd.get("lb_percent_max", 0)
            if lb_max <= 0:
                logger.debug(f"Commande {cmd_id}: LB non autorisé")
                continue
            
            # Calculer % LB actuel
            total = cmd.get("leads_delivered_this_week", 0)
            lb_count = cmd.get("lb_delivered_this_week", 0)
            if total > 0:
                current_lb_percent = (lb_count / total) * 100
                if current_lb_percent >= lb_max:
                    logger.debug(f"Commande {cmd_id}: % LB max atteint ({current_lb_percent:.1f}%/{lb_max}%)")
                    continue
        
        eligible.append(cmd)
    
    return eligible


async def route_lead(
    entity: str,
    product_type: str,
    departement: str,
    phone: str,
    is_lb: bool = False
) -> RoutingResult:
    """
    Route un lead vers le meilleur client disponible
    
    Algorithme:
    1. Trouver toutes les commandes éligibles
    2. Filtrer celles où le lead serait doublon (30 jours)
    3. Prendre la commande avec la meilleure priorité
    
    Args:
        entity: ZR7 ou MDL
        product_type: PV, PAC, ITE
        departement: Code département
        phone: Téléphone du lead
        is_lb: True si le lead est un LB
    
    Returns:
        RoutingResult avec succès ou raison d'échec
    """
    logger.info(
        f"[ROUTING] entity={entity} product={product_type} dept={departement} "
        f"phone=***{phone[-4:] if len(phone) >= 4 else phone} is_lb={is_lb}"
    )
    
    # 1. Trouver les commandes éligibles
    commandes = await find_eligible_commandes(entity, product_type, departement, is_lb)
    
    if not commandes:
        logger.info(f"[ROUTING] Aucune commande éligible trouvée")
        return RoutingResult(
            success=False,
            reason="no_eligible_commande"
        )
    
    # 2. Vérifier doublon 30 jours pour chaque commande
    for cmd in commandes:
        client_id = cmd.get("client_id")
        client_name = cmd.get("client_name", "")
        
        # Vérifier si doublon pour ce client
        dup_result = await check_duplicate_30_days(phone, product_type, client_id)
        
        if dup_result.is_duplicate:
            logger.debug(
                f"[ROUTING] Skip client {client_name}: doublon 30j "
                f"(livré le {dup_result.original_delivery_date})"
            )
            continue
        
        # Client trouvé !
        logger.info(
            f"[ROUTING_SUCCESS] client={client_name} commande={cmd.get('id')} "
            f"priorite={cmd.get('priorite')} is_lb={is_lb}"
        )
        
        return RoutingResult(
            success=True,
            client_id=client_id,
            client_name=client_name,
            commande_id=cmd.get("id"),
            is_lb=is_lb,
            reason="commande_found"
        )
    
    # Toutes les commandes éligibles ont un doublon
    logger.info(f"[ROUTING] Toutes les commandes ont doublon 30j")
    return RoutingResult(
        success=False,
        reason="all_commandes_duplicate"
    )


async def route_lead_batch(leads: List[Dict]) -> List[Tuple[Dict, RoutingResult]]:
    """
    Route un batch de leads (utilisé pour la livraison quotidienne)
    
    Args:
        leads: Liste de documents lead
    
    Returns:
        Liste de tuples (lead, RoutingResult)
    """
    results = []
    
    for lead in leads:
        result = await route_lead(
            entity=lead.get("entity", ""),
            product_type=lead.get("product_type", ""),
            departement=lead.get("departement", ""),
            phone=lead.get("phone", ""),
            is_lb=lead.get("is_lb", False)
        )
        results.append((lead, result))
    
    return results
