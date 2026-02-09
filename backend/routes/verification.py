"""
Routes pour la vérification nocturne et les rapports
- Exécution manuelle de la vérification
- Récupération des rapports
- Planification
"""

from fastapi import APIRouter, Depends, Query
from routes.auth import get_current_user, require_admin
from services.nightly_verification import (
    verify_and_retry_leads,
    get_verification_reports,
    get_last_report
)

router = APIRouter(prefix="/verification", tags=["Vérification"])


@router.get("/reports")
async def list_reports(
    limit: int = Query(30, description="Nombre de rapports à retourner"),
    user: dict = Depends(get_current_user)
):
    """
    Liste les derniers rapports de vérification nocturne.
    """
    reports = await get_verification_reports(limit=limit)
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/latest")
async def latest_report(user: dict = Depends(get_current_user)):
    """
    Récupère le dernier rapport de vérification.
    """
    report = await get_last_report()
    if not report:
        return {"message": "Aucun rapport disponible", "report": None}
    return {"report": report}


@router.post("/run")
async def run_verification(user: dict = Depends(require_admin)):
    """
    Exécute manuellement la vérification des leads des 24 dernières heures.
    
    Cette opération:
    1. Récupère tous les leads des 24h
    2. Identifie ceux qui ne sont pas intégrés
    3. Relance automatiquement les leads échoués (sauf doublons CRM)
    4. Génère un rapport
    
    Note: En production, cette vérification s'exécute automatiquement à 3h du matin.
    """
    report = await verify_and_retry_leads()
    return {
        "success": True,
        "message": f"Vérification terminée: {report['total_leads']} leads analysés, "
                   f"{report['retried']} relancés, {report['retry_success']} succès",
        "report": report
    }


@router.get("/status")
async def verification_status(user: dict = Depends(get_current_user)):
    """
    Statut du système de vérification nocturne.
    """
    last_report = await get_last_report()
    
    return {
        "enabled": True,
        "schedule": "03:00 UTC (tous les jours)",
        "last_run": last_report.get("run_at") if last_report else None,
        "last_result": {
            "total_leads": last_report.get("total_leads", 0) if last_report else 0,
            "retried": last_report.get("retried", 0) if last_report else 0,
            "retry_success": last_report.get("retry_success", 0) if last_report else 0
        } if last_report else None
    }
