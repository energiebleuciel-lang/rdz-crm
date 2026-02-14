"""
RDZ CRM - Moteur de Routing

COMMANDE OPEN = active=true AND semaine courante AND delivered_this_week < quota_semaine
                AND client.delivery_enabled=true AND delivery_day_enabled=true

ORDRE DE PRIORITÉ DES RÈGLES:
1. Calendar gating (day OFF) → bloque routing
2. Client non livrable → aucune commande OPEN possible
3. Quota / Doublon → règles standard

Cross-entity fallback uniquement si settings l'autorisent ET commande OPEN compatible existe.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from config import db
from services.duplicate_detector import check_duplicate_30_days
from services.settings import is_delivery_day_enabled

logger = logging.getLogger("routing_engine")


class RoutingResult:
    """Resultat du routing d'un lead"""

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


def get_week_end() -> str:
    """Retourne le dimanche 23:59:59 de la semaine courante (ISO)"""
    now = datetime.now(timezone.utc)
    sunday = now + timedelta(days=6 - now.weekday())
    return sunday.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()


def get_week_key() -> str:
    """Retourne la cle de semaine courante (ex: 2026-W07)"""
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


async def get_commande_stats(commande_id: str, week_start: str) -> Dict[str, int]:
    """
    Stats de la commande pour la semaine en cours.
    Supporte les deux formats (ancien: livre/delivered_at et nouveau: routed/routed_at).
    """
    pipeline = [
        {
            "$match": {
                "delivery_commande_id": commande_id,
                "status": {"$in": ["livre", "routed"]},
                "$or": [
                    {"delivered_at": {"$gte": week_start}},
                    {"routed_at": {"$gte": week_start}}
                ]
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


async def is_commande_open(cmd: Dict, week_start: str) -> Tuple[bool, Dict]:
    """
    COMMANDE OPEN = active=true AND semaine courante AND delivered_this_week < quota_semaine

    Returns:
        (is_open, stats_dict)
        stats_dict contient: leads_delivered, lb_delivered, quota_remaining
    """
    if not cmd.get("active", False):
        return False, {"reason": "inactive"}

    cmd_id = cmd.get("id")
    quota = cmd.get("quota_semaine", 0)

    stats = await get_commande_stats(cmd_id, week_start)
    delivered = stats.get("leads_delivered", 0)
    lb_delivered = stats.get("lb_delivered", 0)

    info = {
        "leads_delivered": delivered,
        "lb_delivered": lb_delivered,
        "quota_semaine": quota,
    }

    # Quota 0 = illimite -> toujours open
    if quota <= 0:
        info["quota_remaining"] = 999999
        return True, info

    remaining = quota - delivered
    info["quota_remaining"] = max(0, remaining)

    if remaining <= 0:
        return False, {**info, "reason": "quota_full"}

    return True, info


async def find_open_commandes(
    entity: str,
    produit: str,
    departement: str,
    is_lb: bool = False
) -> List[Dict]:
    """
    Trouve les commandes OPEN pour un lead.

    OPEN = active + semaine courante + delivered < quota
    + departement compatible + client actif ET livrable
    + si LB: lb_percent_max > 0 et % LB non depasse
    """
    from models.client import check_client_deliverable
    from services.settings import get_email_denylist_settings
    
    week_start = get_week_start()

    query = {
        "entity": entity,
        "produit": produit,
        "active": True,
        "$or": [
            {"departements": departement},
            {"departements": "*"}
        ]
    }

    commandes = await db.commandes.find(query, {"_id": 0}).sort("priorite", 1).to_list(100)

    # Récupérer la denylist pour vérification client livrable
    denylist_settings = await get_email_denylist_settings()
    denylist = denylist_settings.get("domains", [])

    open_commandes = []

    for cmd in commandes:
        # Client actif ET livrable ?
        client = await db.clients.find_one(
            {"id": cmd.get("client_id")},
            {"_id": 0, "name": 1, "active": 1, "email": 1, "delivery_emails": 1, "api_endpoint": 1}
        )
        if not client:
            continue
        
        if not client.get("active", True):
            logger.debug(f"[ROUTING] Skip client {client.get('name')}: inactive")
            continue
        
        # Vérifier si client est livrable (a un canal valide)
        deliverable_check = check_client_deliverable(
            email=client.get("email", ""),
            delivery_emails=client.get("delivery_emails", []),
            api_endpoint=client.get("api_endpoint", ""),
            denylist=denylist
        )
        
        if not deliverable_check["deliverable"]:
            logger.debug(
                f"[ROUTING] Skip client {client.get('name')}: non livrable - {deliverable_check['reason']}"
            )
            continue

        cmd["client_name"] = client.get("name", "")
        cmd["client_delivery_emails"] = client.get("delivery_emails", [])
        cmd["client_email"] = client.get("email", "")

        # OPEN ?
        is_open, stats = await is_commande_open(cmd, week_start)
        if not is_open:
            logger.debug(
                f"[ROUTING] Commande {cmd.get('id')[:8]}... CLOSED: {stats.get('reason', 'quota_full')}"
            )
            continue

        cmd["quota_remaining"] = stats["quota_remaining"]
        cmd["leads_delivered_this_week"] = stats["leads_delivered"]
        cmd["lb_delivered_this_week"] = stats["lb_delivered"]

        # LB: verifier % autorise
        if is_lb:
            lb_max = cmd.get("lb_percent_max", 0)
            if lb_max <= 0:
                continue

            total = stats["leads_delivered"]
            lb_count = stats["lb_delivered"]
            if total > 0:
                current_pct = (lb_count / total) * 100
                if current_pct >= lb_max:
                    continue

        open_commandes.append(cmd)

    return open_commandes


async def route_lead(
    entity: str,
    produit: str,
    departement: str,
    phone: str,
    is_lb: bool = False,
    entity_locked: bool = False
) -> RoutingResult:
    """
    Route un lead vers le meilleur client avec une commande OPEN.

    ORDRE DE PRIORITÉ:
    1. Calendar gating - si jour OFF → no_open_orders (delivery_day_disabled)
    2. Chercher commandes OPEN dans l'entite (client livrable)
    3. Filtrer doublons 30 jours
    4. Si aucune -> tenter cross-entity fallback (si autorise ET entity_locked=False)
    """
    logger.info(
        f"[ROUTING] entity={entity} produit={produit} dept={departement} "
        f"phone=***{phone[-4:] if len(phone) >= 4 else phone} is_lb={is_lb} "
        f"entity_locked={entity_locked}"
    )

    # 0. CALENDAR GATING - Vérifier si c'est un jour de livraison
    day_enabled, day_reason = await is_delivery_day_enabled(entity)
    if not day_enabled:
        logger.info(f"[ROUTING] {entity}: {day_reason} - aucune livraison ce jour")
        return RoutingResult(success=False, reason=day_reason)

    # 1. Commandes OPEN dans l'entite principale
    commandes = await find_open_commandes(entity, produit, departement, is_lb)

    if not commandes:
        logger.info(f"[ROUTING] {entity}: aucune commande OPEN pour {produit}/{departement}")

        # Cross-entity INTERDIT si entity_locked (provider)
        if entity_locked:
            logger.info(
                "[ROUTING] entity_locked_by_provider -> pas de cross-entity"
            )
            return RoutingResult(success=False, reason="no_open_orders_entity_locked")

        fallback = await _try_cross_entity(entity, produit, departement, phone, is_lb)
        if fallback:
            return fallback

        return RoutingResult(success=False, reason="no_open_orders")

    # 2. Verifier doublon 30 jours pour chaque commande
    for cmd in commandes:
        client_id = cmd.get("client_id")
        client_name = cmd.get("client_name", "")

        dup = await check_duplicate_30_days(phone, produit, client_id)
        if dup.is_duplicate:
            logger.debug(f"[ROUTING] Skip {client_name}: doublon 30j")
            continue

        logger.info(
            f"[ROUTING_OK] -> {client_name} commande={cmd.get('id')[:8]}... "
            f"priorite={cmd.get('priorite')} is_lb={is_lb}"
        )
        return RoutingResult(
            success=True,
            client_id=client_id,
            client_name=client_name,
            commande_id=cmd.get("id"),
            is_lb=is_lb,
            reason="open_commande_found"
        )

    # Toutes doublons -> tenter cross-entity (sauf entity_locked)
    logger.info(f"[ROUTING] {entity}: toutes commandes OPEN = doublon 30j")

    if entity_locked:
        logger.info("[ROUTING] entity_locked_by_provider -> pas de cross-entity")
        return RoutingResult(success=False, reason="all_commandes_duplicate_entity_locked")

    fallback = await _try_cross_entity(entity, produit, departement, phone, is_lb)
    if fallback:
        return fallback

    return RoutingResult(success=False, reason="all_commandes_duplicate")


async def _try_cross_entity(
    from_entity: str,
    produit: str,
    departement: str,
    phone: str,
    is_lb: bool
) -> Optional[RoutingResult]:
    """
    Tente le fallback cross-entity.

    Conditions:
    1. Settings cross_entity autorisent le transfert
    2. L'autre entite a au moins une commande OPEN compatible
    3. Pas de doublon 30j chez le client cible
    """
    from services.settings import is_cross_entity_allowed

    to_entity = "MDL" if from_entity == "ZR7" else "ZR7"

    # Check settings
    allowed = await is_cross_entity_allowed(from_entity, to_entity)
    if not allowed:
        logger.info(
            f"[CROSS_ENTITY] {from_entity}->{to_entity} BLOQUE par settings"
        )
        return None

    # Chercher commandes OPEN dans l'autre entite
    commandes = await find_open_commandes(to_entity, produit, departement, is_lb)

    if not commandes:
        logger.info(
            f"[CROSS_ENTITY] {to_entity}: no_open_orders pour {produit}/{departement}"
        )
        return None

    # Verifier doublons
    for cmd in commandes:
        client_id = cmd.get("client_id")
        client_name = cmd.get("client_name", "")

        dup = await check_duplicate_30_days(phone, produit, client_id)
        if dup.is_duplicate:
            continue

        logger.info(
            f"[CROSS_ENTITY_OK] {from_entity}->{to_entity} -> {client_name} "
            f"commande={cmd.get('id')[:8]}..."
        )
        return RoutingResult(
            success=True,
            client_id=client_id,
            client_name=client_name,
            commande_id=cmd.get("id"),
            is_lb=is_lb,
            reason=f"cross_entity_{from_entity}_to_{to_entity}"
        )

    logger.info(
        f"[CROSS_ENTITY] {to_entity}: toutes commandes OPEN = doublon 30j"
    )
    return None


async def route_lead_batch(leads: List[Dict]) -> List[Tuple[Dict, RoutingResult]]:
    """Route un batch de leads"""
    results = []
    for lead in leads:
        result = await route_lead(
            entity=lead.get("entity", ""),
            produit=lead.get("produit", ""),
            departement=lead.get("departement", ""),
            phone=lead.get("phone", ""),
            is_lb=lead.get("is_lb", False),
            entity_locked=lead.get("entity_locked", False)
        )
        results.append((lead, result))
    return results
