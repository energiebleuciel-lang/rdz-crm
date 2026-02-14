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
from math import ceil
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
        reason: str = "",
        routing_mode: str = "normal"
    ):
        self.success = success
        self.client_id = client_id
        self.client_name = client_name
        self.commande_id = commande_id
        self.is_lb = is_lb
        self.reason = reason
        self.routing_mode = routing_mode  # "normal" | "fallback_no_orders"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "commande_id": self.commande_id,
            "is_lb": self.is_lb,
            "reason": self.reason,
            "routing_mode": self.routing_mode,
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


def week_key_to_range(week_key: str):
    """Convertit YYYY-W## en (monday_iso, sunday_iso)"""
    parts = week_key.split("-W")
    year, wn = int(parts[0]), int(parts[1])
    jan4 = datetime(year, 1, 4, tzinfo=timezone.utc)
    monday = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=wn - 1)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday.isoformat(), sunday.isoformat()


def resolve_week_range(week_key=None):
    """Retourne (week_start, week_end) pour une semaine donnée ou la semaine courante"""
    if week_key:
        return week_key_to_range(week_key)
    return get_week_start(), get_week_end()


async def get_accepted_stats_for_lb_target(commande_id: str, week_start: str, week_end: str) -> Dict[str, int]:
    """
    Compte les deliveries acceptées pour le calcul du LB target.
    Comptage basé uniquement sur: delivery.status == "sent" AND outcome == "accepted"
    Ne compte jamais rejected / removed.
    """
    pipeline = [
        {
            "$match": {
                "commande_id": commande_id,
                "status": "sent",
                "outcome": {"$nin": ["rejected", "removed"]},
                "last_sent_at": {"$gte": week_start, "$lte": week_end}
            }
        },
        {
            "$lookup": {
                "from": "leads",
                "localField": "lead_id",
                "foreignField": "id",
                "pipeline": [{"$project": {"_id": 0, "is_lb": 1}}],
                "as": "lead_info"
            }
        },
        {
            "$group": {
                "_id": None,
                "units_accepted": {"$sum": 1},
                "lb_accepted": {
                    "$sum": {
                        "$cond": [
                            {"$or": [
                                {"$eq": ["$is_lb", True]},
                                {"$eq": [{"$arrayElemAt": ["$lead_info.is_lb", 0]}, True]}
                            ]},
                            1, 0
                        ]
                    }
                }
            }
        }
    ]

    result = await db.deliveries.aggregate(pipeline).to_list(1)
    if result:
        total = result[0].get("units_accepted", 0)
        lb = result[0].get("lb_accepted", 0)
        return {"units_accepted": total, "lb_accepted": lb, "fresh_accepted": total - lb}
    return {"units_accepted": 0, "lb_accepted": 0, "fresh_accepted": 0}


def compute_lb_needed(lb_target_pct: float, delivered_units: int, lb_delivered: int) -> int:
    """
    Calcule le nombre de LB nécessaires pour atteindre le target.
    lb_needed = ceil(target * (delivered_units + 1)) - lb_delivered
    """
    if lb_target_pct <= 0:
        return 0
    return ceil(lb_target_pct * (delivered_units + 1)) - lb_delivered


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

        # PREPAID BLOCK: Skip if billing_mode=PREPAID and balance empty
        prepay_pricing = await db.client_product_pricing.find_one(
            {"client_id": cmd.get("client_id"), "product_code": produit, "billing_mode": "PREPAID", "active": True},
            {"_id": 0, "billing_mode": 1}
        )
        if prepay_pricing:
            balance = await db.prepayment_balances.find_one(
                {"client_id": cmd.get("client_id"), "product_code": produit},
                {"_id": 0, "units_remaining": 1}
            )
            if not balance or balance.get("units_remaining", 0) <= 0:
                logger.info(
                    f"[ROUTING] Skip {client.get('name')}: PREPAID balance empty for {produit}"
                )
                continue

        cmd["quota_remaining"] = stats["quota_remaining"]
        cmd["leads_delivered_this_week"] = stats["leads_delivered"]
        cmd["lb_delivered_this_week"] = stats["lb_delivered"]

        # LB: vérifier lb_target_pct (remplace lb_percent_max)
        if is_lb:
            target = cmd.get("lb_target_pct", 0)
            if target <= 0:
                logger.debug(f"[ROUTING] Skip {client.get('name')}: lb_target_pct=0, no LB wanted")
                continue

            # Calculer lb_needed avec les stats acceptées
            accepted = await get_accepted_stats_for_lb_target(
                cmd.get("id"), week_start, get_week_end()
            )
            delivered_units = accepted["units_accepted"]
            lb_delivered = accepted["lb_accepted"]
            lb_needed = compute_lb_needed(target, delivered_units, lb_delivered)

            if lb_needed <= 0:
                logger.debug(
                    f"[ROUTING] Skip {client.get('name')}: LB target atteint "
                    f"({lb_delivered}/{delivered_units}, target={target})"
                )
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
    1. Calendar gating: l'entity cible doit aussi être en jour livrable
    2. Settings cross_entity autorisent le transfert
    3. L'autre entite a au moins une commande OPEN compatible
    4. Pas de doublon 30j chez le client cible
    """
    from services.settings import is_cross_entity_allowed

    to_entity = "MDL" if from_entity == "ZR7" else "ZR7"

    # 0. Check calendar gating pour l'entity cible
    day_enabled, day_reason = await is_delivery_day_enabled(to_entity)
    if not day_enabled:
        logger.info(
            f"[CROSS_ENTITY] {to_entity}: {day_reason} - fallback bloqué"
        )
        return None

    # 1. Check settings
    allowed = await is_cross_entity_allowed(from_entity, to_entity)
    if not allowed:
        logger.info(
            f"[CROSS_ENTITY] {from_entity}->{to_entity} BLOQUE par settings"
        )
        return None

    # 2. Chercher commandes OPEN dans l'autre entite
    commandes = await find_open_commandes(to_entity, produit, departement, is_lb)

    if not commandes:
        logger.info(
            f"[CROSS_ENTITY] {to_entity}: no_open_orders pour {produit}/{departement}"
        )
        return None

    # 3. Verifier doublons
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
            reason=f"cross_entity_{from_entity}_to_{to_entity}",
            routing_mode="fallback_no_orders"
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
