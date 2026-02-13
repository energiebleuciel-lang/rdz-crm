"""
Monitoring - Taux de succès par CRM / produit / compte + alertes
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from config import db, now_iso
from routes.auth import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

ALERT_THRESHOLD = 80  # Alerte si success_rate < 80%
SPIKE_MULTIPLIER = 3  # Alerte si fails dernière heure > 3x la moyenne horaire sur 24h


async def _compute_stats(window_hours: int):
    """Calcule les stats d'envoi pour une fenêtre donnée."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {
                "target_crm": "$target_crm",
                "product_type": "$product_type",
                "account_id": "$account_id",
                "api_status": "$api_status",
            },
            "count": {"$sum": 1},
        }},
    ]
    raw = await db.leads.aggregate(pipeline).to_list(5000)

    # Indexer par (crm, product, account)
    buckets = {}
    for row in raw:
        key_parts = row["_id"]
        crm = key_parts.get("target_crm") or "none"
        product = key_parts.get("product_type") or "?"
        account = key_parts.get("account_id") or "?"
        status = key_parts.get("api_status") or "unknown"
        count = row["count"]

        for group_key in [
            ("crm", crm),
            ("product", product),
            ("account", account),
            ("crm_product", f"{crm}|{product}"),
        ]:
            if group_key not in buckets:
                buckets[group_key] = {"total": 0, "success": 0, "duplicate": 0, "failures": {}}
            b = buckets[group_key]
            b["total"] += count
            if status in ("success", "duplicate"):
                b["success"] += count
                if status == "duplicate":
                    b["duplicate"] += count
            else:
                b["failures"][status] = b["failures"].get(status, 0) + count

    # Enrichir avec account_name
    account_ids = list({k[1] for k in buckets if k[0] == "account"})
    account_names = {}
    if account_ids:
        accounts = await db.accounts.find(
            {"id": {"$in": account_ids}}, {"_id": 0, "id": 1, "name": 1}
        ).to_list(200)
        account_names = {a["id"]: a["name"] for a in accounts}

    # Construire les résultats
    results = []
    for (dim, val), b in buckets.items():
        total = b["total"]
        success = b["success"]
        rate = round(success / total * 100, 1) if total > 0 else 0
        entry = {
            "dimension": dim,
            "value": val,
            "label": val,
            "total": total,
            "success": success,
            "duplicate": b["duplicate"],
            "failed": total - success,
            "success_rate": rate,
            "failures": b["failures"],
        }
        if dim == "account":
            entry["label"] = account_names.get(val, val[:12])
        results.append(entry)

    return results


async def _detect_alerts(stats_24h):
    """Génère les alertes basées sur les stats 24h."""
    alerts = []
    for s in stats_24h:
        if s["total"] < 3:
            continue  # Pas assez de données
        if s["success_rate"] < ALERT_THRESHOLD:
            top_fail = max(s["failures"].items(), key=lambda x: x[1]) if s["failures"] else ("?", 0)
            alerts.append({
                "level": "critical" if s["success_rate"] < 50 else "warning",
                "dimension": s["dimension"],
                "value": s["value"],
                "label": s["label"],
                "success_rate": s["success_rate"],
                "total": s["total"],
                "failed": s["failed"],
                "top_failure_reason": top_fail[0],
                "top_failure_count": top_fail[1],
                "message": f"{s['label']}: {s['success_rate']}% success ({s['failed']}/{s['total']} fails) — cause principale: {top_fail[0]}",
            })

    # Spike detection : comparer dernière heure vs moyenne horaire 24h
    cutoff_1h = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    fails_1h = await db.leads.count_documents({
        "created_at": {"$gte": cutoff_1h},
        "api_status": {"$nin": ["success", "duplicate", "pending"]},
    })
    fails_24h = await db.leads.count_documents({
        "created_at": {"$gte": cutoff_24h},
        "api_status": {"$nin": ["success", "duplicate", "pending"]},
    })
    avg_hourly = fails_24h / 24 if fails_24h > 0 else 0

    if fails_1h > 0 and avg_hourly > 0 and fails_1h > avg_hourly * SPIKE_MULTIPLIER:
        alerts.append({
            "level": "critical",
            "dimension": "system",
            "value": "spike",
            "label": "Spike de fails",
            "success_rate": None,
            "total": None,
            "failed": fails_1h,
            "top_failure_reason": "spike_detected",
            "top_failure_count": fails_1h,
            "message": f"Spike: {fails_1h} fails dans la dernière heure (moyenne 24h: {avg_hourly:.1f}/h, seuil: {avg_hourly * SPIKE_MULTIPLIER:.0f})",
        })

    alerts.sort(key=lambda a: (0 if a["level"] == "critical" else 1, -(a.get("failed") or 0)))
    return alerts


@router.get("/stats")
async def get_monitoring_stats(user: dict = Depends(get_current_user)):
    """
    Taux de succès par CRM / produit / compte sur 24h et 7j.
    """
    stats_24h = await _compute_stats(24)
    stats_7d = await _compute_stats(168)
    alerts = await _detect_alerts(stats_24h)

    # Structurer par dimension
    def by_dim(stats, dim):
        return sorted(
            [s for s in stats if s["dimension"] == dim],
            key=lambda s: -s["total"],
        )

    return {
        "window_24h": {
            "by_crm": by_dim(stats_24h, "crm"),
            "by_product": by_dim(stats_24h, "product"),
            "by_account": by_dim(stats_24h, "account"),
            "by_crm_product": by_dim(stats_24h, "crm_product"),
        },
        "window_7d": {
            "by_crm": by_dim(stats_7d, "crm"),
            "by_product": by_dim(stats_7d, "product"),
            "by_account": by_dim(stats_7d, "account"),
            "by_crm_product": by_dim(stats_7d, "crm_product"),
        },
        "alerts": alerts,
        "config": {
            "alert_threshold": ALERT_THRESHOLD,
            "spike_multiplier": SPIKE_MULTIPLIER,
        },
        "generated_at": now_iso(),
    }
