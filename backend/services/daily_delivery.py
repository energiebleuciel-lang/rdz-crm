"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Scheduler de Livraison Quotidienne                                ║
║                                                                              ║
║  CRON: Tous les jours à 09h30 Europe/Paris                                   ║
║                                                                              ║
║  ════════════════════════════════════════════════════════════════════════    ║
║                    LOGIQUE MÉTIER VERROUILLÉE                                ║
║  ════════════════════════════════════════════════════════════════════════    ║
║                                                                              ║
║  1. LEAD LIVRABLE: phone + departement + nom                                 ║
║                                                                              ║
║  2. CATÉGORIES:                                                              ║
║     🟢 FRESH = jamais livré AND âge < 8 jours                                ║
║     🟡 LB = âge >= 8 jours OR déjà livré                                     ║
║     ⚠️ LB ne redevient JAMAIS Fresh                                          ║
║                                                                              ║
║  3. DOUBLON = blocage 30j PAR CLIENT uniquement                              ║
║     - Autorisé pour autres clients                                           ║
║     - Autorisé pour autre entité                                             ║
║     - Après 30j: blocage levé mais reste LB                                  ║
║                                                                              ║
║  4. ORDRE DE LIVRAISON:                                                      ║
║     PASS 1 → Fresh                                                           ║
║     PASS 2 → LB jamais livrés à ce client                                    ║
║     PASS 3 → LB déjà livrés à ce client (>30j) - dernier recours             ║
║     ⚠️ Ne jamais dépasser % LB autorisé                                      ║
║                                                                              ║
║  5. CROSS-ENTITY: Fallback ZR7 ↔ MDL si aucune commande éligible             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from config import db, now_iso
from services.duplicate_detector import check_duplicate_30_days
from services.routing_engine import get_week_start

logger = logging.getLogger("daily_delivery")

# ════════════════════════════════════════════════════════════════════════
# CONSTANTES VERROUILLÉES
# ════════════════════════════════════════════════════════════════════════
FRESH_MAX_AGE_DAYS = 8      # Fresh = < 8 jours ET jamais livré
DUPLICATE_BLOCK_DAYS = 30   # Doublon = blocage 30 jours PAR CLIENT


# ════════════════════════════════════════════════════════════════════════
# CATÉGORISATION DES LEADS
# ════════════════════════════════════════════════════════════════════════

def is_lead_fresh(lead: dict) -> bool:
    """
    🟢 FRESH = jamais livré AND âge < 8 jours
    
    Un lead Fresh n'a JAMAIS été livré et a moins de 8 jours.
    """
    # Déjà livré ? → pas Fresh
    if lead.get("status") == "livre" or lead.get("delivered_at"):
        return False
    
    # Déjà marqué LB ? → pas Fresh (LB ne redevient JAMAIS Fresh)
    if lead.get("is_lb"):
        return False
    
    # Vérifier l'âge
    created_at = lead.get("created_at", "")
    if not created_at:
        return False
    
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - created
        return age.days < FRESH_MAX_AGE_DAYS
    except (ValueError, TypeError):
        return False


def is_lead_lb(lead: dict) -> bool:
    """
    🟡 LB = âge >= 8 jours OR déjà livré
    
    LB = Lead Backlog = stock de remplissage
    ⚠️ Un lead LB ne redevient JAMAIS Fresh
    """
    # Déjà marqué LB
    if lead.get("is_lb"):
        return True
    
    # Déjà livré → LB
    if lead.get("status") == "livre" or lead.get("delivered_at"):
        return True
    
    # Âge >= 8 jours → LB
    created_at = lead.get("created_at", "")
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - created
            if age.days >= FRESH_MAX_AGE_DAYS:
                return True
        except (ValueError, TypeError):
            pass
    
    return False


async def mark_leads_as_lb():
    """
    Marque les leads éligibles comme LB
    
    🟡 LB = âge >= 8 jours OR déjà livré
    ⚠️ LB ne redevient JAMAIS Fresh
    """
    now = datetime.now(timezone.utc)
    now_str = now_iso()
    cutoff_8_days = (now - timedelta(days=FRESH_MAX_AGE_DAYS)).isoformat()
    
    # Condition 1: Non livrés >= 8 jours → LB
    result_old = await db.leads.update_many(
        {
            "status": {"$in": ["new", "non_livre"]},
            "created_at": {"$lt": cutoff_8_days},
            "is_lb": {"$ne": True}
        },
        {"$set": {
            "is_lb": True,
            "status": "lb",
            "lb_since": now_str,
            "lb_reason": "age_8_days"
        }}
    )
    
    # Condition 2: Déjà livrés → LB (pour le pool de recyclage)
    result_delivered = await db.leads.update_many(
        {
            "status": "livre",
            "is_lb": {"$ne": True}
        },
        {"$set": {
            "is_lb": True,
            "lb_since": now_str,
            "lb_reason": "already_delivered"
        }}
    )
    # Note: on garde status="livre" pour garder l'historique
    
    total = result_old.modified_count + result_delivered.modified_count
    if total > 0:
        logger.info(
            f"[LB_MARKING] {result_old.modified_count} vieux leads + "
            f"{result_delivered.modified_count} livrés → LB (total: {total})"
        )
    
    return result_old.modified_count, result_delivered.modified_count


# ════════════════════════════════════════════════════════════════════════
# ROUTING - 3 PASSES
# ════════════════════════════════════════════════════════════════════════

# (get_week_start imported from routing_engine)


async def get_commande_stats_delivery(commande_id: str, week_start: str) -> Dict[str, int]:
    """Stats de la commande pour la semaine en cours"""
    pipeline = [
        {
            "$match": {
                "delivery_commande_id": commande_id,
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


async def was_delivered_to_client(phone: str, produit: str, client_id: str) -> Tuple[bool, Optional[str]]:
    """
    Vérifie si ce lead a déjà été livré à ce client
    
    Returns:
        (was_delivered, delivered_at) - delivered_at est None si jamais livré
    """
    existing = await db.leads.find_one({
        "phone": phone,
        "produit": produit,
        "delivered_to_client_id": client_id
    }, {"_id": 0, "delivered_at": 1})
    
    if existing:
        return True, existing.get("delivered_at")
    return False, None


async def is_duplicate_blocked(phone: str, produit: str, client_id: str) -> bool:
    """
    Vérifie si le lead est bloqué par la règle doublon 30 jours
    
    RÈGLE: same phone + same produit + same client + < 30 jours
    """
    result = await check_duplicate_30_days(phone, produit, client_id)
    return result.is_duplicate


async def get_fresh_leads(entity: str) -> List[Dict]:
    """
    🟢 Récupère les leads FRESH pour une entité
    
    FRESH = jamais livré AND âge < 8 jours AND is_lb = False
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=FRESH_MAX_AGE_DAYS)).isoformat()
    
    leads = await db.leads.find({
        "entity": entity,
        "status": {"$in": ["new", "non_livre"]},
        "is_lb": {"$ne": True},
        "delivered_at": {"$exists": False},
        "created_at": {"$gte": cutoff},
        "phone": {"$exists": True, "$ne": ""},
        "departement": {"$exists": True, "$ne": ""},
        "nom": {"$exists": True, "$ne": ""}
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    return leads


async def get_lb_leads(entity: str) -> List[Dict]:
    """
    🟡 Récupère les leads LB pour une entité
    
    LB = is_lb = True (âge >= 8j OR déjà livré)
    """
    leads = await db.leads.find({
        "entity": entity,
        "is_lb": True,
        "phone": {"$exists": True, "$ne": ""},
        "departement": {"$exists": True, "$ne": ""},
        "nom": {"$exists": True, "$ne": ""}
    }, {"_id": 0}).sort("created_at", 1).to_list(2000)
    
    return leads


async def get_active_commandes(entity: str) -> List[Dict]:
    """
    Recupere les commandes OPEN pour une entite.
    OPEN = active + semaine courante + delivered < quota + client actif
    """
    from services.routing_engine import is_commande_open

    week_start = get_week_start()

    commandes = await db.commandes.find({
        "entity": entity,
        "active": True
    }, {"_id": 0}).sort("priorite", 1).to_list(500)

    open_commandes = []

    for cmd in commandes:
        # Client actif ?
        client = await db.clients.find_one(
            {"id": cmd.get("client_id")},
            {"_id": 0, "name": 1, "active": 1, "email": 1, "delivery_emails": 1}
        )
        if not client or not client.get("active", True):
            continue

        cmd["client_name"] = client.get("name", "")
        cmd["client_active"] = True
        cmd["client_email"] = client.get("email", "")
        cmd["client_delivery_emails"] = client.get("delivery_emails", [])

        # OPEN ?
        is_open, stats = await is_commande_open(cmd, week_start)
        if not is_open:
            logger.debug(
                f"[DELIVERY] Commande {cmd.get('id')[:8]}... CLOSED "
                f"({stats.get('leads_delivered', 0)}/{stats.get('quota_semaine', 0)})"
            )
            continue

        cmd["quota_remaining"] = stats["quota_remaining"]
        cmd["leads_delivered_this_week"] = stats["leads_delivered"]
        cmd["lb_delivered_this_week"] = stats["lb_delivered"]

        open_commandes.append(cmd)

    return open_commandes


async def process_commande_delivery(
    cmd: Dict,
    fresh_leads: List[Dict],
    lb_leads: List[Dict],
    used_lead_ids: Set[str],
    week_start: str
) -> Dict:
    """
    Traite une commande avec LB target dynamique.

    Le mix LB/Fresh est piloté au fil de l'eau selon lb_target_pct.
    À chaque attribution: lb_needed = ceil(target * (delivered + 1)) - lb_delivered

    Si lb_needed > 0 → prioriser LB (si dispo)
    Sinon → prioriser Fresh
    Ne jamais bloquer: si type priorisé indisponible, attribuer l'autre type.

    target = 0 → Fresh uniquement (aucun LB volontaire)
    """
    from math import ceil
    from services.routing_engine import get_accepted_stats_for_lb_target, get_week_end

    client_id = cmd.get("client_id")
    client_name = cmd.get("client_name", "")
    produit = cmd.get("produit")
    departements = cmd.get("departements", [])
    quota = cmd.get("quota_semaine", 0)
    lb_target_pct = cmd.get("lb_target_pct", 0)

    # Stats acceptées cette semaine (delivery.status=sent, outcome=accepted)
    week_end = get_week_end()
    accepted = await get_accepted_stats_for_lb_target(cmd.get("id"), week_start, week_end)
    already_delivered = accepted["units_accepted"]
    already_lb = accepted["lb_accepted"]

    # Quota restant (basé sur les stats de leads comme avant pour la compat)
    stats = await get_commande_stats_delivery(cmd.get("id"), week_start)
    total_in_pipeline = stats.get("leads_delivered", 0)

    if quota > 0:
        quota_remaining = quota - total_in_pipeline
        if quota_remaining <= 0:
            return {"leads": [], "lb_count": 0, "fresh_count": 0, "skipped": "quota_full"}
    else:
        quota_remaining = 999999

    to_deliver = []
    lb_count = 0
    skipped_duplicates = 0
    lb_shortfall_logged = False

    def matches_dept(lead):
        dept = lead.get("departement", "")
        return "*" in departements or dept in departements

    def matches_produit(lead):
        return lead.get("produit") == produit

    # Pré-filtrer les leads compatibles
    def filter_leads(leads_list):
        return [l for l in leads_list if l.get("id") not in used_lead_ids
                and matches_dept(l) and matches_produit(l)]

    available_fresh = filter_leads(fresh_leads)
    # LB: séparer en "jamais livré à ce client" et "déjà livré (>30j)"
    available_lb_new = []
    available_lb_recycled = []
    for lead in filter_leads(lb_leads):
        was_del, _ = await was_delivered_to_client(lead.get("phone"), produit, client_id)
        if not was_del:
            available_lb_new.append(lead)
        else:
            available_lb_recycled.append(lead)

    fresh_idx = 0
    lb_new_idx = 0
    lb_recycled_idx = 0

    async def pick_fresh():
        nonlocal fresh_idx, skipped_duplicates
        while fresh_idx < len(available_fresh):
            lead = available_fresh[fresh_idx]
            fresh_idx += 1
            if lead.get("id") in used_lead_ids:
                continue
            if await is_duplicate_blocked(lead.get("phone"), produit, client_id):
                skipped_duplicates += 1
                continue
            return lead
        return None

    async def pick_lb():
        nonlocal lb_new_idx, lb_recycled_idx, skipped_duplicates
        # D'abord LB jamais livrés à ce client
        while lb_new_idx < len(available_lb_new):
            lead = available_lb_new[lb_new_idx]
            lb_new_idx += 1
            if lead.get("id") in used_lead_ids:
                continue
            if await is_duplicate_blocked(lead.get("phone"), produit, client_id):
                skipped_duplicates += 1
                continue
            return lead
        # Ensuite LB déjà livrés (>30j, doublon expiré)
        while lb_recycled_idx < len(available_lb_recycled):
            lead = available_lb_recycled[lb_recycled_idx]
            lb_recycled_idx += 1
            if lead.get("id") in used_lead_ids:
                continue
            if await is_duplicate_blocked(lead.get("phone"), produit, client_id):
                skipped_duplicates += 1
                continue
            return lead
        return None

    # Boucle principale: attribution dynamique
    while len(to_deliver) < quota_remaining:
        # Calcul du besoin LB en temps réel
        current_total = already_delivered + len(to_deliver)
        current_lb = already_lb + lb_count
        lb_needed = ceil(lb_target_pct * (current_total + 1)) - current_lb if lb_target_pct > 0 else 0

        lead = None
        is_lb_pick = False

        if lb_needed > 0:
            # Prioriser LB
            lead = await pick_lb()
            if lead:
                is_lb_pick = True
            else:
                # LB shortfall: log event si pas encore fait
                if not lb_shortfall_logged:
                    lb_shortfall_logged = True
                    from services.event_logger import log_event
                    from services.routing_engine import get_week_key
                    current_pct = (current_lb / current_total * 100) if current_total > 0 else 0
                    avail_lb = (len(available_lb_new) - lb_new_idx) + (len(available_lb_recycled) - lb_recycled_idx)
                    await log_event(
                        action="lb_shortfall",
                        entity_type="commande",
                        entity_id=cmd.get("id", ""),
                        entity=cmd.get("entity", ""),
                        user="system",
                        details={
                            "week_key": get_week_key(),
                            "target_pct": lb_target_pct,
                            "current_pct": round(current_pct, 2),
                            "lb_needed": lb_needed,
                            "available_lb": avail_lb
                        },
                        related={"client_id": client_id, "client_name": client_name}
                    )
                # Fallback: prendre un Fresh
                lead = await pick_fresh()
        else:
            # Prioriser Fresh
            lead = await pick_fresh()
            if not lead and lb_target_pct > 0:
                # Fallback: prendre un LB si target > 0
                lead = await pick_lb()
                if lead:
                    is_lb_pick = True

        if not lead:
            break  # Plus aucun lead disponible

        to_deliver.append(lead)
        used_lead_ids.add(lead.get("id"))
        if is_lb_pick:
            lb_count += 1

    if skipped_duplicates > 0:
        logger.debug(
            f"[ROUTING] {client_name}: {skipped_duplicates} doublons sautés et remplacés"
        )

    return {
        "leads": to_deliver,
        "lb_count": lb_count,
        "fresh_count": len(to_deliver) - lb_count,
        "skipped_duplicates": skipped_duplicates
    }


# ════════════════════════════════════════════════════════════════════════
# LIVRAISON CSV
# ════════════════════════════════════════════════════════════════════════

async def deliver_leads_to_client(
    entity: str,
    cmd: Dict,
    leads: List[Dict],
    lb_count: int
) -> Dict:
    """
    Génère le CSV et envoie par email
    
    🔒 Utilise delivery_state_machine pour les transitions de statut
    """
    from services.csv_delivery import generate_csv_content, generate_csv_filename, send_csv_email
    from services.delivery_state_machine import (
        batch_mark_deliveries_sent,
        batch_mark_deliveries_failed,
        DeliveryInvariantError
    )
    
    client_id = cmd.get("client_id")
    client_name = cmd.get("client_name", "")
    produit = cmd.get("produit")
    commande_id = cmd.get("id")
    
    # Emails
    emails = [cmd.get("client_email")]
    emails.extend(cmd.get("client_delivery_emails", []))
    emails = list(set(filter(None, emails)))
    
    if not emails:
        return {"success": False, "error": "Aucun email configuré"}
    
    # Générer CSV
    csv_content = generate_csv_content(leads, produit, entity)
    csv_filename = generate_csv_filename(entity, produit)
    
    # Créer les delivery records dans la collection deliveries
    batch_id = str(uuid.uuid4())
    now = now_iso()
    lead_ids = [lead.get("id") for lead in leads]
    delivery_ids = []
    
    for lead in leads:
        delivery_id = str(uuid.uuid4())
        delivery_ids.append(delivery_id)
        await db.deliveries.insert_one({
            "id": delivery_id,
            "lead_id": lead.get("id"),
            "client_id": client_id,
            "client_name": client_name,
            "commande_id": commande_id,
            "entity": entity,
            "produit": produit,
            "status": "pending_csv",
            "csv_content": csv_content,
            "csv_filename": csv_filename,
            "csv_generated_at": now,
            "batch_id": batch_id,
            "send_attempts": 0,
            "created_at": now,
            "updated_at": now
        })
    
    # Envoyer
    try:
        result = await send_csv_email(
            entity=entity,
            to_emails=emails,
            csv_content=csv_content,
            csv_filename=csv_filename,
            lead_count=len(leads),
            lb_count=lb_count,
            produit=produit
        )
        
        if not result.get("success"):
            # 🔒 Marquer failed via state machine
            await batch_mark_deliveries_failed(
                delivery_ids=delivery_ids,
                error=result.get("error", "send_failed")
            )
            return result
        
        # 🔒 SEULEMENT après envoi réussi: state machine
        await batch_mark_deliveries_sent(
            delivery_ids=delivery_ids,
            lead_ids=lead_ids,
            sent_to=emails,
            client_id=client_id,
            client_name=client_name,
            commande_id=commande_id
        )
        
        # Sauvegarder batch (backward compatibility)
        await db.delivery_batches.insert_one({
            "id": batch_id,
            "entity": entity,
            "client_id": client_id,
            "client_name": client_name,
            "commande_id": commande_id,
            "produit": produit,
            "lead_ids": lead_ids,
            "delivery_ids": delivery_ids,
            "lead_count": len(leads),
            "lb_count": lb_count,
            "fresh_count": len(leads) - lb_count,
            "status": "sent",
            "csv_filename": csv_filename,
            "emails_sent_to": emails,
            "sent_at": now,
            "created_at": now
        })
        
        return {
            "success": True,
            "batch_id": batch_id,
            "lead_count": len(leads),
            "lb_count": lb_count
        }
        
    except Exception as e:
        # 🔒 Marquer failed via state machine
        try:
            await batch_mark_deliveries_failed(
                delivery_ids=delivery_ids,
                error=str(e)
            )
        except DeliveryInvariantError:
            logger.error(f"[DELIVER] State machine failed: {str(e)}")
        
        return {"success": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# PROCESS ENTITY
# ════════════════════════════════════════════════════════════════════════

async def process_entity_deliveries(entity: str) -> Dict:
    """
    Traite toutes les livraisons pour une entité
    """
    results = {
        "entity": entity,
        "fresh_delivered": 0,
        "lb_delivered": 0,
        "total_delivered": 0,
        "clients_served": 0,
        "batches_sent": 0,
        "errors": []
    }
    
    # Récupérer les leads
    fresh_leads = await get_fresh_leads(entity)
    lb_leads = await get_lb_leads(entity)
    
    logger.info(f"[{entity}] Fresh: {len(fresh_leads)}, LB: {len(lb_leads)}")
    
    if not fresh_leads and not lb_leads:
        return results
    
    # Récupérer les commandes
    commandes = await get_active_commandes(entity)
    if not commandes:
        logger.info(f"[{entity}] Aucune commande active")
        return results
    
    week_start = get_week_start()
    used_lead_ids: Set[str] = set()
    
    # Traiter chaque commande
    for cmd in commandes:
        try:
            delivery_result = await process_commande_delivery(
                cmd, fresh_leads, lb_leads, used_lead_ids, week_start
            )
            
            leads_to_deliver = delivery_result.get("leads", [])
            lb_count = delivery_result.get("lb_count", 0)
            
            if not leads_to_deliver:
                continue
            
            # Livrer
            send_result = await deliver_leads_to_client(
                entity, cmd, leads_to_deliver, lb_count
            )
            
            if send_result.get("success"):
                results["fresh_delivered"] += len(leads_to_deliver) - lb_count
                results["lb_delivered"] += lb_count
                results["total_delivered"] += len(leads_to_deliver)
                results["clients_served"] += 1
                results["batches_sent"] += 1
                
                logger.info(
                    f"[{entity}] {cmd.get('client_name')}: "
                    f"{len(leads_to_deliver)} leads (Fresh: {len(leads_to_deliver) - lb_count}, LB: {lb_count})"
                )
            else:
                results["errors"].append({
                    "client": cmd.get("client_name"),
                    "error": send_result.get("error")
                })
                
        except Exception as e:
            logger.error(f"[{entity}] Erreur commande {cmd.get('id')}: {str(e)}")
            results["errors"].append({
                "client": cmd.get("client_name"),
                "error": str(e)
            })
    
    return results


# ---- CROSS-ENTITY FALLBACK ----

async def try_cross_entity_fallback(
    lead: Dict,
    original_entity: str
) -> Optional[str]:
    """
    Tente de router vers l'autre entite si aucune commande OPEN
    dans l'entite principale.

    Conditions:
    1. Settings cross_entity autorisent le transfert
    2. L'autre entite a au moins une commande OPEN compatible
    3. Pas de doublon 30j chez le client cible

    Returns:
        ID de la commande trouvee ou None
    """
    from services.settings import is_cross_entity_allowed

    other_entity = "MDL" if original_entity == "ZR7" else "ZR7"

    # 1. Check settings
    allowed = await is_cross_entity_allowed(original_entity, other_entity)
    if not allowed:
        logger.info(
            f"[CROSS_ENTITY] {original_entity}->{other_entity} BLOQUE par settings"
        )
        return None

    # 2. Commandes OPEN dans l'autre entite
    commandes = await get_active_commandes(other_entity)

    if not commandes:
        logger.info(
            f"[CROSS_ENTITY] {other_entity}: no_open_orders "
            f"pour {lead.get('produit')}/{lead.get('departement')}"
        )
        return None

    for cmd in commandes:
        departements = cmd.get("departements", [])
        client_id = cmd.get("client_id")

        # Departement compatible ?
        dept = lead.get("departement", "")
        if "*" not in departements and dept not in departements:
            continue

        # Doublon 30j ?
        if await is_duplicate_blocked(lead.get("phone"), cmd.get("produit"), client_id):
            continue

        logger.info(
            f"[CROSS_ENTITY_OK] {original_entity}->{other_entity} "
            f"lead={lead.get('id', '')[:8]}... -> {cmd.get('client_name')}"
        )
        return cmd.get("id")

    logger.info(
        f"[CROSS_ENTITY] {other_entity}: no_open_orders compatible"
    )
    return None


# ════════════════════════════════════════════════════════════════════════
# MAIN - RUN DAILY DELIVERY
# ════════════════════════════════════════════════════════════════════════

async def process_pending_csv_deliveries() -> Dict:
    """
    📤 Traite les deliveries créées par le routing immédiat (Phase 2)
    
    ORDRE DE PRIORITÉ STRICT:
    1. Calendar gating (hard stop) - Si jour OFF → ne rien faire
    2. Client deliverable check - Skip si client non livrable
    3. auto_send_enabled check - Si false → ready_to_send (pas d'envoi)
    
    COMPORTEMENT:
    - Jour OFF → deliveries restent pending_csv
    - Jour OK + auto_send=true → sent + leads=livre (via state machine)
    - Jour OK + auto_send=false → ready_to_send (CSV généré, pas envoyé)
    
    🔒 UTILISE delivery_state_machine pour les transitions de statut
    
    Returns:
        Dict avec stats de traitement
    """
    from services.csv_delivery import send_csv_email, generate_csv_content
    from services.settings import is_delivery_day_enabled, get_email_denylist_settings, get_simulation_email_override
    from services.delivery_state_machine import (
        batch_mark_deliveries_sent,
        batch_mark_deliveries_ready_to_send,
        batch_mark_deliveries_failed
    )
    from models.client import check_client_deliverable
    
    results = {
        "processed": 0,
        "sent": 0,
        "ready_to_send": 0,
        "skipped_calendar": 0,
        "skipped_not_deliverable": 0,
        "errors": []
    }
    
    # Récupérer toutes les deliveries pending_csv
    pending = await db.deliveries.find(
        {"status": "pending_csv"},
        {"_id": 0}
    ).to_list(1000)
    
    if not pending:
        logger.info("[PENDING_CSV] Aucune delivery en attente")
        return results
    
    results["processed"] = len(pending)
    logger.info(f"[PENDING_CSV] {len(pending)} deliveries à traiter")
    
    # Récupérer la denylist et le mode simulation
    denylist_settings = await get_email_denylist_settings()
    denylist = denylist_settings.get("domains", [])
    simulation_email = await get_simulation_email_override()
    
    # Grouper par client_id + commande_id + entity
    grouped = defaultdict(list)
    
    for delivery in pending:
        key = (delivery.get("client_id"), delivery.get("commande_id"), delivery.get("entity"))
        grouped[key].append(delivery)
    
    # Traiter chaque groupe
    for (client_id, commande_id, entity), deliveries in grouped.items():
        try:
            # ════════════════════════════════════════════════════════════
            # PRIORITÉ 1: CALENDAR GATING
            # ════════════════════════════════════════════════════════════
            day_enabled, day_reason = await is_delivery_day_enabled(entity)
            if not day_enabled:
                logger.info(
                    f"[PENDING_CSV] {entity}: {day_reason} - {len(deliveries)} deliveries skipped"
                )
                results["skipped_calendar"] += len(deliveries)
                continue  # Reste pending_csv
            
            # Récupérer les leads associés
            lead_ids = [d.get("lead_id") for d in deliveries]
            leads = await db.leads.find(
                {"id": {"$in": lead_ids}},
                {"_id": 0}
            ).to_list(len(lead_ids))
            
            if not leads:
                continue
            
            # Récupérer info client et commande
            client = await db.clients.find_one({"id": client_id}, {"_id": 0})
            commande = await db.commandes.find_one({"id": commande_id}, {"_id": 0})
            
            if not client or not commande:
                logger.error(f"[PENDING_CSV] Client ou commande introuvable: {client_id}/{commande_id}")
                results["errors"].append({"client_id": client_id, "error": "client_or_commande_not_found"})
                continue
            
            produit = commande.get("produit", deliveries[0].get("produit", ""))
            client_name = client.get("name", "")
            
            # ════════════════════════════════════════════════════════════
            # PRIORITÉ 2: CLIENT DELIVERABLE
            # ════════════════════════════════════════════════════════════
            deliverable_check = check_client_deliverable(
                email=client.get("email", ""),
                delivery_emails=client.get("delivery_emails", []),
                api_endpoint=client.get("api_endpoint", ""),
                denylist=denylist
            )
            
            if not deliverable_check["deliverable"]:
                logger.warning(
                    f"[PENDING_CSV] Client {client_name} non livrable: {deliverable_check['reason']}"
                )
                results["skipped_not_deliverable"] += len(deliveries)
                # 🔒 Marquer comme failed via state machine
                delivery_ids = [d.get("id") for d in deliveries]
                await batch_mark_deliveries_failed(
                    delivery_ids=delivery_ids,
                    error=f"client_not_deliverable: {deliverable_check['reason']}"
                )
                results["errors"].append({"client": client_name, "error": deliverable_check["reason"]})
                continue
            
            # Emails de livraison (avec simulation override)
            if simulation_email:
                emails = [simulation_email]
            else:
                emails = client.get("delivery_emails", [])
                if not emails and client.get("email"):
                    emails = [client.get("email")]
            
            if not emails:
                logger.warning(f"[PENDING_CSV] Pas d'email pour client {client_name}")
                results["errors"].append({"client": client_name, "error": "no_email"})
                continue
            
            # ════════════════════════════════════════════════════════════
            # PRIORITÉ 3: AUTO_SEND_ENABLED
            # ════════════════════════════════════════════════════════════
            auto_send_enabled = client.get("auto_send_enabled", True)
            
            # Générer CSV (toujours)
            lb_count = sum(1 for lead in leads if lead.get("is_lb"))
            csv_content = generate_csv_content(leads, produit, entity)
            
            now = now_iso()
            csv_filename = f"leads_{entity}_{produit}_{now[:10].replace('-', '')}_{len(leads)}.csv"
            
            delivery_ids = [d.get("id") for d in deliveries]
            
            if not auto_send_enabled:
                # ════════════════════════════════════════════════════════
                # MODE MANUEL: ready_to_send (CSV généré, pas envoyé)
                # 🔒 Via state machine
                # ════════════════════════════════════════════════════════
                await batch_mark_deliveries_ready_to_send(
                    delivery_ids=delivery_ids,
                    csv_content=csv_content,
                    csv_filename=csv_filename
                )
                
                # Lead reste en "routed" (PAS livre) - géré par state machine
                
                results["ready_to_send"] += len(leads)
                logger.info(
                    f"[PENDING_CSV] {client_name}: {len(leads)} leads → ready_to_send "
                    f"(auto_send_enabled=false)"
                )
            else:
                # ════════════════════════════════════════════════════════
                # MODE AUTO: Envoyer et marquer livre
                # 🔒 Via state machine APRÈS envoi réussi
                # ════════════════════════════════════════════════════════
                try:
                    # 1. Envoyer l'email RÉELLEMENT
                    await send_csv_email(
                        entity=entity,
                        to_emails=emails,
                        csv_content=csv_content,
                        csv_filename=csv_filename,
                        lead_count=len(leads),
                        lb_count=lb_count,
                        produit=produit
                    )
                    
                    # 2. SEULEMENT après envoi réussi: marquer via state machine
                    # 🔒 batch_mark_deliveries_sent vérifie les invariants
                    await batch_mark_deliveries_sent(
                        delivery_ids=delivery_ids,
                        lead_ids=lead_ids,
                        sent_to=emails,
                        client_id=client_id,
                        client_name=client_name,
                        commande_id=commande_id
                    )
                    
                    # Stocker le CSV dans les deliveries (pour téléchargement)
                    await db.deliveries.update_many(
                        {"id": {"$in": delivery_ids}},
                        {"$set": {
                            "csv_content": csv_content,
                            "csv_filename": csv_filename,
                            "csv_generated_at": now_iso()
                        }}
                    )
                    
                    results["sent"] += len(leads)
                    logger.info(
                        f"[PENDING_CSV] {client_name}: {len(leads)} leads envoyés → sent "
                        f"(entity={entity}, produit={produit}, to={emails})"
                    )
                    
                except Exception as e:
                    logger.error(f"[PENDING_CSV] Erreur envoi CSV {client_name}: {str(e)}")
                    
                    # 🔒 Marquer comme failed via state machine
                    await batch_mark_deliveries_failed(
                        delivery_ids=delivery_ids,
                        error=str(e)
                    )
                    
                    # Stocker le CSV même en cas d'échec (pour retry manuel)
                    await db.deliveries.update_many(
                        {"id": {"$in": delivery_ids}},
                        {"$set": {
                            "csv_content": csv_content,
                            "csv_filename": csv_filename,
                            "csv_generated_at": now_iso()
                        }}
                    )
                    
                    results["errors"].append({"client": client_name, "error": str(e)})
                
        except Exception as e:
            logger.error(f"[PENDING_CSV] Erreur traitement groupe: {str(e)}")
            results["errors"].append({"group": f"{client_id}/{commande_id}", "error": str(e)})
    
    return results


async def run_daily_delivery():
    """
    Fonction principale appelée par le cron à 09h30 Europe/Paris
    
    1. Traiter les deliveries pending_csv (routing immédiat Phase 2)
    2. Marquer leads éligibles → LB
    3. Traiter ZR7 (leads new non encore routés)
    4. Traiter MDL (leads new non encore routés)
    5. Sauvegarder rapport
    """
    logger.info("[DAILY_DELIVERY] ════════════════════════════════════════")
    logger.info("[DAILY_DELIVERY] DÉBUT LIVRAISON QUOTIDIENNE 09h30")
    logger.info("[DAILY_DELIVERY] ════════════════════════════════════════")
    
    start_time = datetime.now(timezone.utc)
    
    # 0. Traiter les deliveries pending_csv (Phase 2)
    pending_csv_results = await process_pending_csv_deliveries()
    logger.info(
        f"[DAILY_DELIVERY] Pending CSV: {pending_csv_results['sent']} leads envoyés "
        f"({pending_csv_results['processed']} deliveries traitées)"
    )
    
    # 1. Marquer les leads LB
    lb_old, lb_delivered = await mark_leads_as_lb()
    
    # 2. Traiter chaque entité (leads new non encore routés)
    all_results = {
        "run_at": now_iso(),
        "pending_csv": pending_csv_results,
        "lb_marked": {
            "from_old_leads": lb_old,
            "from_delivered": lb_delivered,
            "total": lb_old + lb_delivered
        },
        "entities": {}
    }
    
    for entity in ["ZR7", "MDL"]:
        try:
            result = await process_entity_deliveries(entity)
            all_results["entities"][entity] = result
            
            logger.info(
                f"[DAILY_DELIVERY] {entity}: "
                f"Total={result['total_delivered']} "
                f"(Fresh={result['fresh_delivered']}, LB={result['lb_delivered']}) "
                f"Clients={result['clients_served']}"
            )
            
        except Exception as e:
            logger.error(f"[DAILY_DELIVERY] Erreur {entity}: {str(e)}")
            all_results["entities"][entity] = {"error": str(e)}
    
    # 3. Sauvegarder le rapport
    all_results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
    await db.delivery_reports.insert_one(all_results)
    
    logger.info("[DAILY_DELIVERY] ════════════════════════════════════════")
    logger.info(f"[DAILY_DELIVERY] FIN (durée: {all_results['duration_seconds']:.1f}s)")
    logger.info("[DAILY_DELIVERY] ════════════════════════════════════════")
    
    return all_results
