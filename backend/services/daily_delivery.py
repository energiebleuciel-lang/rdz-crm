"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Scheduler de Livraison Quotidienne                                ║
║                                                                              ║
║  CRON: Tous les jours à 09h30 Europe/Paris                                   ║
║                                                                              ║
║  LOGIQUE LB (Lead Backlog) - POOL DE LEADS REVENDABLES:                      ║
║  ═══════════════════════════════════════════════════════════════════════     ║
║  Un lead entre en LB dans 2 cas:                                             ║
║                                                                              ║
║  1. JAMAIS LIVRÉ → non_livre depuis > 8 jours → LB                           ║
║  2. DÉJÀ LIVRÉ → dernière livraison > 30 jours → LB                          ║
║                                                                              ║
║  LB = statut unique pour leads recyclables/revendables                       ║
║  Doublon = période de blocage 30 jours PAR CLIENT                            ║
║  Une fois expiré → retour automatique en LB                                  ║
║                                                                              ║
║  ACTIONS QUOTIDIENNES:                                                       ║
║  1. Marquer les leads éligibles comme LB                                     ║
║  2. Récupérer les leads "new" ou "non_livre" récents                         ║
║  3. Router chaque lead vers un client éligible                               ║
║  4. Éviter doublons 30 jours                                                 ║
║  5. Compléter quotas avec LB si nécessaire                                   ║
║  6. Générer CSV                                                              ║
║  7. Envoyer par email                                                        ║
║                                                                              ║
║  ZÉRO MANIPULATION HUMAINE                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict

from config import db, now_iso
from services.routing_engine import route_lead, get_week_start, get_commande_stats
from services.csv_delivery import deliver_to_client
from services.duplicate_detector_v2 import check_duplicate_30_days

logger = logging.getLogger("daily_delivery")

# Configuration LB
LB_NON_LIVRE_DAYS = 8   # Leads non livrés > 8 jours → LB
LB_LIVRE_DAYS = 30      # Leads livrés > 30 jours → LB (revendables)


async def mark_leads_as_lb():
    """
    Marque les leads éligibles comme LB (Lead Backlog = pool revendable)
    
    ╔══════════════════════════════════════════════════════════════════╗
    ║  LOGIQUE LB - 2 CONDITIONS D'ENTRÉE                              ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  1. JAMAIS LIVRÉ:                                                ║
    ║     - status = new ou non_livre                                  ║
    ║     - register_date > 8 jours                                    ║
    ║     → Devient LB                                                 ║
    ║                                                                  ║
    ║  2. DÉJÀ LIVRÉ (recyclable):                                     ║
    ║     - status = livre                                             ║
    ║     - delivered_at > 30 jours                                    ║
    ║     → Devient LB (revendable à un AUTRE client)                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    Returns:
        Tuple (nb_non_livres_to_lb, nb_livres_to_lb)
    """
    now = datetime.now(timezone.utc)
    now_str = now_iso()
    
    # === CONDITION 1: Non livrés > 8 jours ===
    cutoff_non_livre = (now - timedelta(days=LB_NON_LIVRE_DAYS)).isoformat()
    
    result_non_livre = await db.leads.update_many(
        {
            "status": {"$in": ["new", "non_livre"]},
            "created_at": {"$lt": cutoff_non_livre},
            "is_lb": {"$ne": True}
        },
        {"$set": {
            "is_lb": True,
            "status": "lb",
            "lb_since": now_str,
            "lb_reason": "non_livre_8_days"
        }}
    )
    
    nb_non_livres = result_non_livre.modified_count
    if nb_non_livres > 0:
        logger.info(f"[LB_MARKING] {nb_non_livres} leads non livrés > 8j → LB")
    
    # === CONDITION 2: Livrés > 30 jours (recyclables) ===
    cutoff_livre = (now - timedelta(days=LB_LIVRE_DAYS)).isoformat()
    
    result_livre = await db.leads.update_many(
        {
            "status": "livre",
            "delivered_at": {"$lt": cutoff_livre},
            "is_lb": {"$ne": True}
        },
        {"$set": {
            "is_lb": True,
            "status": "lb",
            "lb_since": now_str,
            "lb_reason": "livre_30_days_expired"
        }}
    )
    
    nb_livres = result_livre.modified_count
    if nb_livres > 0:
        logger.info(f"[LB_MARKING] {nb_livres} leads livrés > 30j → LB (recyclables)")
    
    total = nb_non_livres + nb_livres
    if total > 0:
        logger.info(f"[LB_MARKING] Total: {total} leads entrés en LB")
    
    return nb_non_livres, nb_livres


async def get_leads_to_process(entity: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Récupère les leads à traiter pour une entité
    
    Returns:
        (fresh_leads, lb_leads) triés par priorité
    """
    # Leads frais (new/non_livre, < 8 jours)
    fresh_leads = await db.leads.find({
        "entity": entity,
        "status": {"$in": ["new", "non_livre"]},
        "is_lb": {"$ne": True},
        "phone": {"$exists": True, "$ne": ""}
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    # Leads LB disponibles
    lb_leads = await db.leads.find({
        "entity": entity,
        "status": "lb",
        "is_lb": True,
        "phone": {"$exists": True, "$ne": ""}
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    logger.info(f"[GET_LEADS] entity={entity} fresh={len(fresh_leads)} lb={len(lb_leads)}")
    
    return fresh_leads, lb_leads


async def process_entity_deliveries(entity: str) -> Dict:
    """
    Traite toutes les livraisons pour une entité
    
    Algorithme:
    1. Récupérer les commandes actives groupées par client
    2. Pour chaque commande:
        a. Calculer le quota restant
        b. Router des leads frais jusqu'au quota
        c. Compléter avec LB si autorisé
    3. Générer et envoyer les CSV
    """
    results = {
        "entity": entity,
        "processed_leads": 0,
        "delivered_leads": 0,
        "lb_delivered": 0,
        "clients_served": 0,
        "batches_sent": 0,
        "errors": []
    }
    
    # 1. Récupérer tous les leads disponibles
    fresh_leads, lb_leads = await get_leads_to_process(entity)
    
    if not fresh_leads and not lb_leads:
        logger.info(f"[DELIVERY] entity={entity} - Aucun lead à traiter")
        return results
    
    # 2. Récupérer les commandes actives
    commandes = await db.commandes.find({
        "entity": entity,
        "active": True
    }, {"_id": 0}).sort("priorite", 1).to_list(500)
    
    if not commandes:
        logger.info(f"[DELIVERY] entity={entity} - Aucune commande active")
        return results
    
    # 3. Grouper les leads par client
    # Structure: { client_id: { leads: [], commande: {...} } }
    client_batches = defaultdict(lambda: {"leads": [], "commande": None})
    
    week_start = get_week_start()
    
    # Index pour suivre les leads utilisés
    used_fresh = set()
    used_lb = set()
    
    # 4. Traiter chaque commande par priorité
    for cmd in commandes:
        client_id = cmd.get("client_id")
        produit = cmd.get("produit")
        departements = cmd.get("departements", [])
        quota = cmd.get("quota_semaine", 0)
        lb_max_percent = cmd.get("lb_percent_max", 0)
        
        # Stats actuelles
        stats = await get_commande_stats(cmd.get("id"), week_start)
        already_delivered = stats.get("leads_delivered", 0)
        already_lb = stats.get("lb_delivered", 0)
        
        # Calculer combien on peut encore livrer
        if quota > 0:
            quota_remaining = quota - already_delivered
            if quota_remaining <= 0:
                continue
        else:
            quota_remaining = 999999  # Illimité
        
        # Leads à livrer pour cette commande
        to_deliver = []
        lb_count = 0
        
        # 4a. D'abord les leads frais
        for lead in fresh_leads:
            if lead.get("id") in used_fresh:
                continue
            
            # Vérifier produit
            if lead.get("produit") != produit:
                continue
            
            # Vérifier département
            dept = lead.get("departement", "")
            if "*" not in departements and dept not in departements:
                continue
            
            # Vérifier doublon 30 jours
            dup = await check_duplicate_30_days(
                lead.get("phone"),
                produit,
                client_id
            )
            if dup.is_duplicate:
                continue
            
            # Lead éligible
            to_deliver.append(lead)
            used_fresh.add(lead.get("id"))
            
            if len(to_deliver) >= quota_remaining:
                break
        
        # 4b. Compléter avec LB si autorisé et quota non atteint
        if lb_max_percent > 0 and len(to_deliver) < quota_remaining:
            # Calculer combien de LB on peut ajouter
            total_with_existing = already_delivered + len(to_deliver)
            max_lb_total = int(total_with_existing * lb_max_percent / 100)
            lb_allowed = max_lb_total - already_lb
            
            for lead in lb_leads:
                if lead.get("id") in used_lb:
                    continue
                
                if lb_count >= lb_allowed:
                    break
                
                if len(to_deliver) >= quota_remaining:
                    break
                
                # Vérifier département (produit peut être différent pour LB)
                dept = lead.get("departement", "")
                if "*" not in departements and dept not in departements:
                    continue
                
                # Vérifier doublon 30 jours
                dup = await check_duplicate_30_days(
                    lead.get("phone"),
                    produit,  # Produit de la COMMANDE
                    client_id
                )
                if dup.is_duplicate:
                    continue
                
                # LB éligible
                to_deliver.append(lead)
                used_lb.add(lead.get("id"))
                lb_count += 1
        
        # Stocker pour livraison groupée par client
        if to_deliver:
            if not client_batches[client_id]["commande"]:
                client_batches[client_id]["commande"] = cmd
            client_batches[client_id]["leads"].extend(to_deliver)
            client_batches[client_id]["lb_count"] = client_batches[client_id].get("lb_count", 0) + lb_count
    
    # 5. Livrer par client
    for client_id, batch_data in client_batches.items():
        leads = batch_data["leads"]
        cmd = batch_data["commande"]
        
        if not leads:
            continue
        
        batch_id = str(uuid.uuid4())
        produit = cmd.get("produit")
        
        try:
            result = await deliver_to_client(
                entity=entity,
                client_id=client_id,
                leads=leads,
                produit=produit,
                batch_id=batch_id
            )
            
            if result.get("success"):
                results["delivered_leads"] += len(leads)
                results["lb_delivered"] += batch_data.get("lb_count", 0)
                results["clients_served"] += 1
                results["batches_sent"] += 1
            else:
                results["errors"].append({
                    "client_id": client_id,
                    "error": result.get("error")
                })
                
        except Exception as e:
            logger.error(f"[DELIVERY_ERROR] client={client_id}: {str(e)}")
            results["errors"].append({
                "client_id": client_id,
                "error": str(e)
            })
    
    results["processed_leads"] = len(used_fresh) + len(used_lb)
    
    return results


async def run_daily_delivery():
    """
    Fonction principale appelée par le cron à 09h30
    
    Traite les deux entités: ZR7 et MDL
    """
    logger.info("[DAILY_DELIVERY] === DÉBUT LIVRAISON QUOTIDIENNE ===")
    
    start_time = datetime.now(timezone.utc)
    
    # 1. Marquer les vieux leads comme LB
    lb_marked = await mark_old_leads_as_lb()
    
    # 2. Traiter chaque entité
    all_results = {
        "run_at": now_iso(),
        "lb_marked": lb_marked,
        "entities": {}
    }
    
    for entity in ["ZR7", "MDL"]:
        try:
            result = await process_entity_deliveries(entity)
            all_results["entities"][entity] = result
            
            logger.info(
                f"[DAILY_DELIVERY] {entity}: "
                f"delivered={result['delivered_leads']} "
                f"lb={result['lb_delivered']} "
                f"clients={result['clients_served']} "
                f"errors={len(result['errors'])}"
            )
            
        except Exception as e:
            logger.error(f"[DAILY_DELIVERY] Erreur entity {entity}: {str(e)}")
            all_results["entities"][entity] = {"error": str(e)}
    
    # 3. Sauvegarder le rapport
    all_results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    await db.delivery_reports.insert_one(all_results)
    
    logger.info(
        f"[DAILY_DELIVERY] === FIN (durée: {all_results['duration_seconds']:.1f}s) ==="
    )
    
    return all_results
