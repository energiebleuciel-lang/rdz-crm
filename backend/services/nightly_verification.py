"""
Service de vérification nocturne des leads
- Vérifie tous les leads des 24 dernières heures
- Relance automatiquement les leads échoués (sauf doublons CRM)
- Génère un rapport de réconciliation
"""

import logging
from datetime import datetime, timezone, timedelta
from config import db, now_iso

logger = logging.getLogger("nightly_verification")


async def verify_and_retry_leads():
    """
    Vérification nocturne des leads des 24 dernières heures.
    
    1. Récupère tous les leads des 24h
    2. Identifie ceux qui ne sont pas intégrés correctement
    3. Relance ceux qui ont échoué (sauf doublons CRM)
    4. Génère un rapport
    
    Returns:
        dict: Rapport de vérification
    """
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(hours=24)).isoformat()
    
    report = {
        "run_at": now_iso(),
        "period": {
            "from": yesterday,
            "to": now.isoformat()
        },
        "total_leads": 0,
        "successful": 0,
        "duplicates": 0,
        "failed": 0,
        "retried": 0,
        "retry_success": 0,
        "retry_failed": 0,
        "skipped_duplicates": 0,
        "details": []
    }
    
    # 1. Récupérer tous les leads des 24 dernières heures
    leads = await db.leads.find({
        "created_at": {"$gte": yesterday}
    }, {"_id": 0}).to_list(10000)
    
    report["total_leads"] = len(leads)
    
    # 2. Catégoriser les leads
    for lead in leads:
        status = lead.get("api_status", "pending")
        
        if status == "success":
            report["successful"] += 1
        elif status == "duplicate":
            report["duplicates"] += 1
        elif status in ["failed", "queued", "no_crm", "pending"]:
            report["failed"] += 1
            
            # 3. Vérifier si c'est un doublon CRM (ne pas relancer)
            api_response = str(lead.get("api_response", "")).lower()
            is_crm_duplicate = "doublon" in api_response or "duplicate" in api_response
            
            if is_crm_duplicate:
                report["skipped_duplicates"] += 1
                report["details"].append({
                    "lead_id": lead.get("id"),
                    "action": "skipped",
                    "reason": "Doublon CRM",
                    "original_status": status
                })
            else:
                # 4. Tenter de relancer
                retry_result = await retry_lead_internal(lead)
                report["retried"] += 1
                
                if retry_result.get("success"):
                    report["retry_success"] += 1
                    report["details"].append({
                        "lead_id": lead.get("id"),
                        "action": "retry_success",
                        "new_status": retry_result.get("status"),
                        "crm": retry_result.get("crm")
                    })
                else:
                    report["retry_failed"] += 1
                    report["details"].append({
                        "lead_id": lead.get("id"),
                        "action": "retry_failed",
                        "error": retry_result.get("error"),
                        "original_status": status
                    })
    
    # 5. Sauvegarder le rapport
    report["id"] = f"report_{now.strftime('%Y%m%d_%H%M%S')}"
    await db.verification_reports.insert_one({**report})
    
    logger.info(f"Vérification nocturne terminée: {report['total_leads']} leads, "
                f"{report['retried']} relancés, {report['retry_success']} succès")
    
    return report


async def retry_lead_internal(lead: dict) -> dict:
    """
    Relance un lead en interne (sans passer par l'API).
    Utilise la même logique que /api/leads/{lead_id}/retry
    """
    from routes.commandes import has_commande
    from services.lead_sender import send_to_crm
    
    lead_id = lead.get("id")
    
    # Récupérer config
    form = await db.forms.find_one({"code": lead.get("form_code")})
    if not form:
        return {"success": False, "error": "Formulaire non trouvé"}
    
    api_key_crm = form.get("crm_api_key")
    if not api_key_crm:
        return {"success": False, "error": "Clé API CRM non configurée"}
    
    allow_cross_crm = form.get("allow_cross_crm", True)
    product_type = form.get("product_type", "PV")
    dept = lead.get("departement", "")
    
    account = await db.accounts.find_one({"id": form.get("account_id")})
    primary_crm_id = account.get("crm_id") if account else None
    
    # Chercher un CRM avec commande active
    all_crms = await db.crms.find({}, {"_id": 0}).to_list(10)
    crm_map = {c["id"]: c for c in all_crms}
    
    target_crm = None
    routing_reason = "no_commande"
    
    # Essayer le CRM principal
    if primary_crm_id:
        if await has_commande(primary_crm_id, product_type, dept):
            target_crm = crm_map.get(primary_crm_id)
            routing_reason = f"commande_{target_crm.get('slug')}" if target_crm else "primary"
    
    # Cross-CRM si autorisé
    if not target_crm and allow_cross_crm:
        for crm_id, crm in crm_map.items():
            if crm_id != primary_crm_id:
                if await has_commande(crm_id, product_type, dept):
                    target_crm = crm
                    routing_reason = f"cross_crm_{crm.get('slug')}"
                    break
    
    if not target_crm:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "api_status": "no_crm",
                "routing_reason": "no_commande",
                "retried_at": now_iso(),
                "retried_by": "nightly_verification"
            }}
        )
        return {"success": False, "error": "Aucun CRM avec commande active"}
    
    # Envoyer au CRM
    status, response, _ = await send_to_crm(lead, target_crm.get("api_url"), api_key_crm)
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "api_status": status,
            "api_response": response,
            "sent_to_crm": status in ["success", "duplicate"],
            "target_crm_id": target_crm.get("id"),
            "target_crm_slug": target_crm.get("slug"),
            "routing_reason": routing_reason,
            "retried_at": now_iso(),
            "retried_by": "nightly_verification",
            "retry_count": lead.get("retry_count", 0) + 1
        }}
    )
    
    return {
        "success": status in ["success", "duplicate"],
        "status": status,
        "crm": target_crm.get("slug")
    }


async def get_verification_reports(limit: int = 30):
    """
    Récupère les derniers rapports de vérification
    """
    reports = await db.verification_reports.find(
        {},
        {"_id": 0}
    ).sort("run_at", -1).to_list(limit)
    
    return reports


async def get_last_report():
    """
    Récupère le dernier rapport de vérification
    """
    report = await db.verification_reports.find_one(
        {},
        {"_id": 0},
        sort=[("run_at", -1)]
    )
    return report
