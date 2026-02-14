"""
RDZ CRM - System Health Endpoint
Aggregated health dashboard: cron, deliveries, transfers, modules.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from config import db, now_iso
from routes.auth import get_current_user
from services.permissions import require_permission

router = APIRouter(prefix="/system", tags=["System"])
logger = logging.getLogger("system_health")

CORE_VERSION = "1.0.0"
CORE_TAG = "rdz-core-distribution-validated"


@router.get("/version")
async def system_version():
    """Public: returns version, tag, build info."""
    import subprocess
    git_sha = "unknown"
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/app", timeout=3, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        pass

    return {
        "version": CORE_VERSION,
        "tag": CORE_TAG,
        "git_sha": git_sha,
        "build_date": "2026-02-14",
        "env": "preview",
    }


@router.get("/health")
async def system_health(
    user: dict = Depends(require_permission("dashboard.view"))
):
    """
    Aggregated health endpoint:
    - Last cron run status
    - Failed cron count (7 days)
    - Failed transfers count
    - Failed deliveries count
    - Module status summary
    """
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    health = {
        "status": "healthy",
        "timestamp": now_iso(),
        "modules": {},
    }
    # --- CRON ---
    try:
        last_daily = await db.delivery_reports.find_one(
            {}, {"_id": 0, "run_at": 1, "duration_seconds": 1}
        , sort=[("run_at", -1)])

        last_interco_cron = await db.cron_logs.find_one(
            {"job": "intercompany_invoices"},
            {"_id": 0, "status": 1, "run_at": 1, "completed_at": 1, "week_key": 1}
        , sort=[("run_at", -1)])

        failed_crons_7d = await db.cron_logs.count_documents({
            "status": "error",
            "run_at": {"$gte": seven_days_ago}
        })

        health["modules"]["cron"] = {
            "status": "healthy" if failed_crons_7d == 0 else "degraded",
            "last_daily_delivery": {
                "run_at": last_daily.get("run_at") if last_daily else None,
                "duration_s": last_daily.get("duration_seconds") if last_daily else None,
            },
            "last_intercompany_cron": {
                "status": last_interco_cron.get("status") if last_interco_cron else None,
                "run_at": last_interco_cron.get("run_at") if last_interco_cron else None,
                "week_key": last_interco_cron.get("week_key") if last_interco_cron else None,
            },
            "failed_crons_7d": failed_crons_7d,
        }
    except Exception as e:
        health["modules"]["cron"] = {"status": "error", "error": str(e)[:200]}

    # --- DELIVERIES ---
    try:
        failed_deliveries = await db.deliveries.count_documents({"status": "failed"})
        pending_csv = await db.deliveries.count_documents({"status": "pending_csv"})
        total_sent = await db.deliveries.count_documents({"status": "sent"})

        health["modules"]["deliveries"] = {
            "status": "healthy" if failed_deliveries == 0 else "degraded",
            "failed": failed_deliveries,
            "pending_csv": pending_csv,
            "total_sent": total_sent,
        }
    except Exception as e:
        health["modules"]["deliveries"] = {"status": "error", "error": str(e)[:200]}

    # --- INTERCOMPANY TRANSFERS ---
    try:
        error_transfers = await db.intercompany_transfers.count_documents({"transfer_status": "error"})
        pending_transfers = await db.intercompany_transfers.count_documents({"transfer_status": "pending"})

        health["modules"]["intercompany"] = {
            "status": "healthy" if error_transfers == 0 else "degraded",
            "error_transfers": error_transfers,
            "pending_transfers": pending_transfers,
        }
    except Exception as e:
        health["modules"]["intercompany"] = {"status": "error", "error": str(e)[:200]}

    # --- INVOICES ---
    try:
        overdue_count = await db.invoices.count_documents({
            "status": "overdue", "type": {"$ne": "intercompany"}
        })
        draft_count = await db.invoices.count_documents({"status": "draft"})

        health["modules"]["invoices"] = {
            "status": "healthy" if overdue_count == 0 else "warning",
            "overdue": overdue_count,
            "draft": draft_count,
        }
    except Exception as e:
        health["modules"]["invoices"] = {"status": "error", "error": str(e)[:200]}

    # --- OVERALL STATUS ---
    statuses = [m.get("status", "healthy") for m in health["modules"].values()]
    if "error" in statuses:
        health["status"] = "error"
    elif "degraded" in statuses:
        health["status"] = "degraded"
    elif "warning" in statuses:
        health["status"] = "warning"

    return health
