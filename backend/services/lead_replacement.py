"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  SERVICE DE REMPLACEMENT AUTOMATIQUE PAR LB (Lead Backup)                    ║
║                                                                              ║
║  Logique:                                                                    ║
║  - Quand un lead est bloqué (doublon_recent), on cherche un LB              ║
║  - LB = lead réel existant, > 30 jours, jamais livré à ce CRM               ║
║  - On envoie le LB à la place pour remplir le quota                         ║
║                                                                              ║
║  Règles:                                                                     ║
║  - Jamais créer de faux leads                                               ║
║  - Jamais modifier les données                                              ║
║  - Uniquement données réelles                                               ║
║                                                                              ║
║  Priorité de sélection:                                                      ║
║  1. Leads récents redistribuables (< 30 jours, non livrés)                  ║
║  2. LB (aged leads > 30 jours, jamais livrés à ce CRM)                      ║
║  3. Sinon: crédit/report (pas de remplacement)                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from config import db

logger = logging.getLogger("lead_replacement")

# Configuration
LB_MIN_AGE_DAYS = 30  # Âge minimum pour être considéré comme LB
FRESH_MAX_AGE_DAYS = 30  # Âge max pour être considéré comme "fresh"

# Statuts éligibles pour remplacement
REDISTRIBUTABLE_STATUSES = [
    "pending_no_order",      # En attente de commande
    "pending_manual",        # Trop vieux pour auto, en attente manuelle
    "non_livre",             # Doublon non livré (redistribuable)
    "no_crm",                # CRM non configuré
    "no_api_key",            # Clé API manquante
    "failed",                # Échec de livraison (peut être retesté)
]


class LBResult:
    """Résultat de la recherche de LB"""
    
    def __init__(
        self,
        found: bool,
        lb_lead: Optional[Dict] = None,
        lb_type: Optional[str] = None,  # "fresh" ou "aged"
        reason: str = ""
    ):
        self.found = found
        self.lb_lead = lb_lead
        self.lb_type = lb_type
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "lb_lead_id": self.lb_lead.get("id") if self.lb_lead else None,
            "lb_type": self.lb_type,
            "reason": self.reason
        }


async def find_replacement_lead(
    target_crm: str,
    departement: str,
    product_type: str,
    excluded_lead_id: Optional[str] = None
) -> LBResult:
    """
    Cherche un lead de remplacement (LB) pour un doublon bloqué.
    
    Ordre de priorité:
    1. Fresh leads (< 30 jours, non livrés, redistribuables)
    2. LB aged (> 30 jours, jamais livré à ce CRM)
    
    Args:
        target_crm: CRM cible (zr7, mdl)
        departement: Département requis
        product_type: Type de produit (PV, PAC, ITE)
        excluded_lead_id: ID du lead doublon à exclure
    
    Returns:
        LBResult avec le lead trouvé ou None
    """
    
    if not target_crm or not departement or not product_type:
        return LBResult(
            found=False,
            reason="Paramètres manquants (target_crm, departement, product_type)"
        )
    
    now = datetime.now(timezone.utc)
    fresh_cutoff = (now - timedelta(days=FRESH_MAX_AGE_DAYS)).isoformat()
    lb_cutoff = (now - timedelta(days=LB_MIN_AGE_DAYS)).isoformat()
    
    # Base query pour leads redistribuables
    base_query = {
        "departement": departement,
        "product_type": product_type,
        "api_status": {"$in": REDISTRIBUTABLE_STATUSES},
        "sent_to_crm": False,  # Jamais livré
        "phone_invalid": {"$ne": True},  # Téléphone valide
    }
    
    # Exclure le lead doublon lui-même
    if excluded_lead_id:
        base_query["id"] = {"$ne": excluded_lead_id}
    
    # === PRIORITÉ 1: Fresh leads (< 30 jours) ===
    fresh_query = {
        **base_query,
        "created_at": {"$gte": fresh_cutoff}  # Moins de 30 jours
    }
    
    # Trier par date de création (plus ancien en premier pour équité)
    fresh_lead = await db.leads.find_one(
        fresh_query,
        {"_id": 0},
        sort=[("created_at", 1)]  # Plus ancien d'abord
    )
    
    if fresh_lead:
        logger.info(f"LB Fresh trouvé: {fresh_lead.get('id')[:8]}... pour {target_crm}/{departement}/{product_type}")
        return LBResult(
            found=True,
            lb_lead=fresh_lead,
            lb_type="fresh",
            reason=f"Lead frais redistribuable (créé le {fresh_lead.get('created_at', '')[:10]})"
        )
    
    # === PRIORITÉ 2: LB Aged (> 30 jours) ===
    # Pour les LB aged, on vérifie aussi qu'ils n'ont jamais été livrés à CE CRM spécifique
    lb_query = {
        **base_query,
        "created_at": {"$lt": lb_cutoff},  # Plus de 30 jours
        # Vérifier que ce lead n'a jamais été livré à ce CRM
        "$or": [
            {"target_crm": {"$exists": False}},
            {"target_crm": ""},
            {"target_crm": None},
            {"target_crm": {"$ne": target_crm}}  # Ou livré à un autre CRM
        ]
    }
    
    # Pour les LB, on prend aussi les leads qui ont été envoyés à un AUTRE CRM mais pas celui-ci
    # Cela permet de maximiser le remplissage des quotas
    lb_lead = await db.leads.find_one(
        lb_query,
        {"_id": 0},
        sort=[("created_at", 1)]  # Plus ancien d'abord (équité FIFO)
    )
    
    if lb_lead:
        logger.info(f"LB Aged trouvé: {lb_lead.get('id')[:8]}... pour {target_crm}/{departement}/{product_type}")
        return LBResult(
            found=True,
            lb_lead=lb_lead,
            lb_type="aged",
            reason=f"Lead LB aged (créé le {lb_lead.get('created_at', '')[:10]})"
        )
    
    # === PAS DE LB TROUVÉ ===
    logger.info(f"Aucun LB trouvé pour {target_crm}/{departement}/{product_type}")
    return LBResult(
        found=False,
        reason=f"Aucun lead redistribuable pour {departement}/{product_type}"
    )


async def execute_lb_replacement(
    lb_lead: Dict,
    target_crm: str,
    crm_api_key: str,
    original_doublon_id: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Exécute l'envoi d'un LB en remplacement d'un doublon.
    
    Args:
        lb_lead: Le lead LB à envoyer
        target_crm: CRM cible
        crm_api_key: Clé API du CRM
        original_doublon_id: ID du lead doublon qui a déclenché le remplacement
    
    Returns:
        Tuple (success: bool, status: str, message: str)
    """
    from services.lead_sender import send_to_crm_v2
    from routes.public import get_crm_url
    
    lb_id = lb_lead.get("id")
    
    # Préparer le lead pour l'envoi
    # IMPORTANT: On ne modifie PAS les données du lead, on l'envoie tel quel
    
    try:
        # Récupérer l'URL du CRM
        api_url = await get_crm_url(target_crm)
        if not api_url:
            return False, "no_crm_url", f"URL CRM non configurée pour {target_crm}"
        
        # Envoyer au CRM
        status, response, should_queue = await send_to_crm_v2(
            lead_doc=lb_lead,
            api_url=api_url,
            api_key=crm_api_key
        )
        
        success = status in ["success", "duplicate"]
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        if success:
            # Mise à jour du LB avec les infos de remplacement
            await db.leads.update_one(
                {"id": lb_id},
                {"$set": {
                    "api_status": status,
                    "sent_to_crm": True,
                    "sent_at": now_iso,
                    "target_crm": target_crm,
                    # Champs spécifiques LB
                    "is_lb_replacement": True,
                    "lb_replaced_doublon_id": original_doublon_id,
                    "lb_sent_at": now_iso,
                    "lb_type": "replacement",
                    "distribution_reason": f"LB_REPLACEMENT:{original_doublon_id[:8]}"
                }}
            )
            
            # Mise à jour du lead doublon original pour traçabilité
            await db.leads.update_one(
                {"id": original_doublon_id},
                {"$set": {
                    "lb_replacement_id": lb_id,
                    "lb_replacement_status": status,
                    "lb_replacement_at": now_iso
                }}
            )
            
            logger.info(f"LB {lb_id[:8]}... envoyé avec succès en remplacement de {original_doublon_id[:8]}...")
            return True, status, f"LB envoyé en remplacement (status: {status})"
        
        else:
            # Échec de l'envoi du LB
            await db.leads.update_one(
                {"id": lb_id},
                {"$set": {
                    "api_status": status,
                    "lb_attempt_failed": True,
                    "lb_attempt_at": now_iso,
                    "lb_attempt_error": str(response)[:500]
                }}
            )
            
            logger.warning(f"Échec envoi LB {lb_id[:8]}...: {status}")
            return False, status, f"Échec envoi LB: {status}"
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi LB {lb_id[:8]}...: {str(e)}")
        return False, "error", str(e)


async def process_doublon_with_replacement(
    doublon_lead: Dict,
    target_crm: str,
    crm_api_key: str
) -> Dict[str, Any]:
    """
    Traitement complet d'un doublon avec tentative de remplacement par LB.
    
    Args:
        doublon_lead: Le lead détecté comme doublon
        target_crm: CRM cible
        crm_api_key: Clé API du CRM
    
    Returns:
        Dict avec le résultat du traitement
    """
    
    doublon_id = doublon_lead.get("id")
    departement = doublon_lead.get("departement")
    product_type = doublon_lead.get("product_type", "PV")  # Défaut PV
    
    result = {
        "doublon_id": doublon_id,
        "doublon_status": "doublon_recent",
        "lb_found": False,
        "lb_sent": False,
        "lb_id": None,
        "lb_status": None,
        "message": ""
    }
    
    # Chercher un LB de remplacement
    lb_result = await find_replacement_lead(
        target_crm=target_crm,
        departement=departement,
        product_type=product_type,
        excluded_lead_id=doublon_id
    )
    
    if not lb_result.found:
        result["message"] = f"Doublon bloqué, aucun LB disponible ({lb_result.reason})"
        return result
    
    result["lb_found"] = True
    result["lb_id"] = lb_result.lb_lead.get("id")
    result["lb_type"] = lb_result.lb_type
    
    # Exécuter le remplacement
    success, status, message = await execute_lb_replacement(
        lb_lead=lb_result.lb_lead,
        target_crm=target_crm,
        crm_api_key=crm_api_key,
        original_doublon_id=doublon_id
    )
    
    result["lb_sent"] = success
    result["lb_status"] = status
    result["message"] = message
    
    return result


async def get_lb_stats() -> Dict[str, Any]:
    """
    Retourne les statistiques des LB envoyés.
    """
    
    # Total LB envoyés
    lb_sent = await db.leads.count_documents({"is_lb_replacement": True})
    
    # Par type (fresh vs aged)
    lb_fresh = await db.leads.count_documents({
        "is_lb_replacement": True,
        "lb_type": "fresh"
    })
    lb_aged = await db.leads.count_documents({
        "is_lb_replacement": True,
        "lb_type": "aged"
    })
    
    # Par statut
    lb_success = await db.leads.count_documents({
        "is_lb_replacement": True,
        "api_status": "success"
    })
    lb_failed = await db.leads.count_documents({
        "is_lb_replacement": True,
        "api_status": {"$in": ["failed", "duplicate", "validation_error"]}
    })
    
    # Leads avec remplacement réussi
    doublons_replaced = await db.leads.count_documents({
        "lb_replacement_id": {"$exists": True, "$ne": None}
    })
    
    return {
        "total_lb_sent": lb_sent,
        "lb_fresh": lb_fresh,
        "lb_aged": lb_aged,
        "lb_success": lb_success,
        "lb_failed": lb_failed,
        "doublons_with_replacement": doublons_replaced,
        "replacement_rate": round(doublons_replaced / max(lb_sent, 1) * 100, 1)
    }


async def get_available_lb_count(
    target_crm: str,
    departement: Optional[str] = None,
    product_type: Optional[str] = None
) -> Dict[str, int]:
    """
    Compte les LB disponibles pour un CRM/département/produit.
    """
    
    now = datetime.now(timezone.utc)
    fresh_cutoff = (now - timedelta(days=FRESH_MAX_AGE_DAYS)).isoformat()
    lb_cutoff = (now - timedelta(days=LB_MIN_AGE_DAYS)).isoformat()
    
    base_query = {
        "api_status": {"$in": REDISTRIBUTABLE_STATUSES},
        "sent_to_crm": False,
        "phone_invalid": {"$ne": True},
    }
    
    if departement:
        base_query["departement"] = departement
    if product_type:
        base_query["product_type"] = product_type
    
    # Fresh
    fresh_query = {**base_query, "created_at": {"$gte": fresh_cutoff}}
    fresh_count = await db.leads.count_documents(fresh_query)
    
    # Aged
    aged_query = {**base_query, "created_at": {"$lt": lb_cutoff}}
    aged_count = await db.leads.count_documents(aged_query)
    
    return {
        "fresh_available": fresh_count,
        "aged_available": aged_count,
        "total_available": fresh_count + aged_count
    }
