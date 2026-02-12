"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SERVICE DE REDISTRIBUTION DES LEADS                                         ║
║                                                                              ║
║  Gère la redistribution automatique et manuelle des leads :                  ║
║  - Auto-reprise quand une commande s'active (< 8 jours)                      ║
║  - Passage en manual_only après 8 jours                                      ║
║  - Redistribution manuelle par admin                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso

logger = logging.getLogger("lead_redistributor")

# Constantes
DAYS_AUTO_REDISTRIBUTION = 8  # Jours max pour auto-redistribution


# ==================== HELPERS ====================

async def get_redistribution_key(target_crm: str, product_type: str) -> str:
    """
    Récupère la clé API de redistribution pour un CRM/produit donné.
    Ces clés sont configurées dans Paramètres pour la distribution inter-CRM.
    """
    config = await db.system_config.find_one(
        {"type": "redistribution_keys"}, 
        {"_id": 0}
    )
    
    if not config:
        return ""
    
    keys = config.get("keys", {})
    crm_keys = keys.get(target_crm, {})
    
    # Cherche la clé exacte ou wildcard
    return crm_keys.get(product_type, crm_keys.get("*", ""))


async def get_lead_age_days(lead: dict) -> int:
    """Calcule l'âge du lead en jours depuis sa création RDZ"""
    created_at_str = lead.get("created_at", "")
    if not created_at_str:
        return 999  # Très vieux si pas de date
    
    try:
        # Parse ISO date
        if "T" in created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        else:
            created_at = datetime.fromisoformat(created_at_str)
        
        # Si pas de timezone, assume UTC
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        delta = now - created_at
        return delta.days
    except Exception as e:
        logger.error(f"Erreur calcul age lead: {e}")
        return 999


async def is_lead_eligible_for_auto_redistribution(lead: dict) -> bool:
    """
    Vérifie si un lead est éligible à la redistribution automatique.
    Conditions: status pending_no_order ET age < 8 jours ET pas manual_only
    """
    status = lead.get("api_status", "")
    manual_only = lead.get("manual_only", False)
    
    if status != "pending_no_order":
        return False
    
    if manual_only:
        return False
    
    age_days = await get_lead_age_days(lead)
    return age_days < DAYS_AUTO_REDISTRIBUTION


# ==================== REDISTRIBUTION AUTO ====================

async def redistribute_leads_for_command(command: dict) -> dict:
    """
    Redistribue automatiquement les leads en attente quand une commande s'active.
    Appelé quand une commande passe à active=True.
    
    Retourne: {redistributed: int, failed: int, skipped: int}
    """
    from routes.commandes import has_commande
    from services.lead_sender import send_to_crm_v2
    
    crm_id = command.get("crm_id", "")
    product_type = command.get("product_type", "*")
    departements = command.get("departements", ["*"])
    
    # Récupérer le slug du CRM
    crm = await db.crms.find_one({"id": crm_id}, {"_id": 0})
    if not crm:
        logger.error(f"CRM introuvable: {crm_id}")
        return {"redistributed": 0, "failed": 0, "skipped": 0, "error": "CRM not found"}
    
    crm_slug = crm.get("slug", "")
    crm_url = crm.get("api_url", "")
    
    # Chercher les leads en attente éligibles
    query = {
        "api_status": "pending_no_order",
        "manual_only": {"$ne": True}
    }
    
    # Filtrer par produit si pas wildcard
    if product_type != "*":
        query["product_type"] = product_type
    
    # Filtrer par département si pas wildcard
    if "*" not in departements:
        query["departement"] = {"$in": departements}
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(500)
    
    results = {"redistributed": 0, "failed": 0, "skipped": 0}
    
    for lead in leads:
        # Vérifier l'âge
        if not await is_lead_eligible_for_auto_redistribution(lead):
            results["skipped"] += 1
            continue
        
        lead_id = lead.get("id")
        lead_dept = lead.get("departement", "")
        lead_product = lead.get("product_type", "PV")
        
        # Vérifier si la commande match vraiment
        if not await has_commande(crm_id, lead_product, lead_dept):
            results["skipped"] += 1
            continue
        
        # Récupérer la clé de redistribution
        api_key = await get_redistribution_key(crm_slug, lead_product)
        if not api_key:
            logger.warning(f"Pas de clé redistribution pour {crm_slug}/{lead_product}")
            results["skipped"] += 1
            continue
        
        # Envoyer au CRM
        try:
            status, response, should_queue = await send_to_crm_v2(lead, crm_url, api_key)
            
            if status == "success":
                # Mettre à jour le lead
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {
                        "api_status": "success",
                        "sent_to_crm": True,
                        "target_crm": crm_slug,
                        "is_transferred": True,
                        "distribution_reason": "auto_redistribution",
                        "redistributed_at": now_iso(),
                        "api_response": str(response)[:500]
                    }}
                )
                results["redistributed"] += 1
                logger.info(f"Lead {lead_id} redistribué vers {crm_slug}")
            else:
                results["failed"] += 1
                logger.warning(f"Échec redistribution lead {lead_id}: {response}")
                
        except Exception as e:
            logger.error(f"Erreur redistribution lead {lead_id}: {e}")
            results["failed"] += 1
    
    return results


# ==================== PASSAGE MANUAL ONLY ====================

async def mark_old_leads_as_manual_only() -> int:
    """
    Marque les leads en attente depuis plus de 8 jours comme manual_only.
    À appeler périodiquement (cron quotidien).
    
    Retourne: nombre de leads marqués
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_AUTO_REDISTRIBUTION)
    cutoff_iso = cutoff_date.isoformat()
    
    result = await db.leads.update_many(
        {
            "api_status": "pending_no_order",
            "manual_only": {"$ne": True},
            "created_at": {"$lt": cutoff_iso}
        },
        {"$set": {
            "manual_only": True,
            "api_status": "pending_manual",
            "manual_only_at": now_iso()
        }}
    )
    
    count = result.modified_count
    if count > 0:
        logger.info(f"{count} leads marqués manual_only (> {DAYS_AUTO_REDISTRIBUTION} jours)")
    
    return count


# ==================== REDISTRIBUTION MANUELLE ====================

async def force_send_lead(lead_id: str, target_crm: str, admin_user: str) -> dict:
    """
    Force l'envoi d'un lead vers un CRM spécifique (action admin).
    Utilise la clé du formulaire d'origine si même CRM, sinon clé redistribution.
    
    Retourne: {success: bool, message: str, status: str}
    """
    from services.lead_sender import send_to_crm_v2
    
    # Récupérer le lead
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        return {"success": False, "message": "Lead introuvable", "status": "error"}
    
    origin_crm = lead.get("origin_crm", "")
    product_type = lead.get("product_type", "PV")
    form_code = lead.get("form_code", "")
    
    # Récupérer le CRM cible
    target_crm_doc = await db.crms.find_one({"slug": target_crm}, {"_id": 0})
    if not target_crm_doc:
        return {"success": False, "message": f"CRM '{target_crm}' introuvable", "status": "error"}
    
    crm_url = target_crm_doc.get("api_url", "")
    
    # Déterminer la clé API à utiliser
    if target_crm == origin_crm:
        # Même CRM = utiliser la clé du formulaire d'origine
        form = await db.forms.find_one({"code": form_code}, {"_id": 0})
        api_key = form.get("crm_api_key", "") if form else ""
        key_source = "formulaire_origine"
    else:
        # CRM différent = utiliser la clé de redistribution
        api_key = await get_redistribution_key(target_crm, product_type)
        key_source = "redistribution_inter_crm"
    
    if not api_key:
        return {
            "success": False, 
            "message": f"Pas de clé API disponible ({key_source})",
            "status": "no_key"
        }
    
    # Envoyer au CRM
    try:
        status, response, should_queue = await send_to_crm_v2(lead, crm_url, api_key)
        
        # Mettre à jour le lead
        update_data = {
            "target_crm": target_crm,
            "api_status": status,
            "api_response": str(response)[:500],
            "force_sent_at": now_iso(),
            "force_sent_by": admin_user,
            "key_source": key_source
        }
        
        if status == "success":
            update_data["sent_to_crm"] = True
            update_data["is_transferred"] = (target_crm != origin_crm)
            update_data["distribution_reason"] = "manual_force_send"
        
        await db.leads.update_one({"id": lead_id}, {"$set": update_data})
        
        return {
            "success": status == "success",
            "message": f"Envoyé vers {target_crm.upper()}" if status == "success" else str(response),
            "status": status,
            "response": str(response)[:500] if response else ""  # Sérialiser la réponse en string
        }
        
    except Exception as e:
        logger.error(f"Erreur force_send lead {lead_id}: {e}")
        return {"success": False, "message": str(e), "status": "error"}


# ==================== STATS REDISTRIBUTION ====================

async def get_pending_leads_stats() -> dict:
    """
    Retourne les stats des leads en attente de redistribution.
    """
    # Leads éligibles auto (< 8 jours)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_AUTO_REDISTRIBUTION)
    cutoff_iso = cutoff_date.isoformat()
    
    auto_eligible = await db.leads.count_documents({
        "api_status": "pending_no_order",
        "manual_only": {"$ne": True},
        "created_at": {"$gte": cutoff_iso}
    })
    
    # Leads manual only (> 8 jours)
    manual_only = await db.leads.count_documents({
        "$or": [
            {"api_status": "pending_manual"},
            {"manual_only": True}
        ]
    })
    
    # Total en attente
    total_pending = await db.leads.count_documents({
        "api_status": {"$in": ["pending_no_order", "pending_manual"]}
    })
    
    return {
        "total_pending": total_pending,
        "auto_eligible": auto_eligible,
        "manual_only": manual_only,
        "days_threshold": DAYS_AUTO_REDISTRIBUTION
    }
