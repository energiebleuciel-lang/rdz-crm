"""
RDZ CRM - Monitoring Intelligence Layer
READ-ONLY aggregation endpoint. Fail-open per-widget.
"""

import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
from config import db, now_iso
from routes.auth import get_current_user
from services.permissions import (
    require_permission, get_entity_scope_from_request, build_entity_filter,
)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
logger = logging.getLogger("monitoring")

RANGES = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}


def _cutoff(range_key: str) -> str:
    days = RANGES.get(range_key, 7)
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _prev_cutoff(range_key: str) -> tuple:
    days = RANGES.get(range_key, 7)
    end = datetime.now(timezone.utc) - timedelta(days=days)
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


@router.get("/intelligence")
async def monitoring_intelligence(
    request: Request,
    range: str = Query("7d", description="24h|7d|30d|90d"),
    product: Optional[str] = None,
    user: dict = Depends(require_permission("dashboard.view")),
):
    """
    Monitoring Intelligence — single aggregated endpoint.
    Fail-open: each section isolated, partial data on error.
    """
    scope = get_entity_scope_from_request(user, request)
    ef = build_entity_filter(scope)
    cutoff = _cutoff(range)
    prev_start, prev_end = _prev_cutoff(range)

    base = {**ef, "created_at": {"$gte": cutoff}}
    prev_base = {**ef, "created_at": {"$gte": prev_start, "$lt": prev_end}}
    if product:
        base["produit"] = product.upper()
        prev_base["produit"] = product.upper()

    result = {"range": range, "scope": scope, "product": product, "_errors": []}

    # ═══════════════════════════════════════════════════════════
    # 1. PHONE QUALITY BY SOURCE
    # ═══════════════════════════════════════════════════════════
    try:
        pq_pipe = [
            {"$match": base},
            {"$group": {
                "_id": {
                    "source_type": {"$ifNull": ["$lead_source_type", "unknown"]},
                    "quality": {"$ifNull": ["$phone_quality", "unknown"]},
                    "entity": "$entity",
                },
                "count": {"$sum": 1},
            }},
        ]
        pq_raw = await db.leads.aggregate(pq_pipe).to_list(500)

        # Also get previous period totals for trend
        prev_pipe = [
            {"$match": prev_base},
            {"$group": {
                "_id": {"source_type": {"$ifNull": ["$lead_source_type", "unknown"]}},
                "count": {"$sum": 1},
            }},
        ]
        prev_raw = await db.leads.aggregate(prev_pipe).to_list(50)
        prev_by_src = {r["_id"]["source_type"]: r["count"] for r in prev_raw}

        # Aggregate by source_type
        sources = {}
        for r in pq_raw:
            src = r["_id"]["source_type"]
            q = r["_id"]["quality"]
            if src not in sources:
                sources[src] = {"total": 0, "valid": 0, "suspicious": 0, "invalid": 0, "unknown": 0}
            sources[src]["total"] += r["count"]
            if q in sources[src]:
                sources[src][q] += r["count"]
            else:
                sources[src]["unknown"] += r["count"]

        phone_quality = []
        for src, s in sorted(sources.items()):
            t = s["total"] or 1
            prev_t = prev_by_src.get(src, 0)
            trend = round((s["total"] - prev_t) / prev_t * 100, 1) if prev_t > 0 else 0
            phone_quality.append({
                "source_type": src,
                "total_leads": s["total"],
                "valid_count": s["valid"],
                "suspicious_count": s["suspicious"],
                "invalid_count": s["invalid"],
                "valid_rate": round(s["valid"] / t * 100, 1),
                "suspicious_rate": round(s["suspicious"] / t * 100, 1),
                "invalid_rate": round(s["invalid"] / t * 100, 1),
                "trend_pct": trend,
            })
        result["phone_quality"] = phone_quality
    except Exception as e:
        logger.error(f"[MONITORING] phone_quality failed: {e}")
        result["phone_quality"] = []
        result["_errors"].append("phone_quality")

    # ═══════════════════════════════════════════════════════════
    # 2. DUPLICATE STATS
    # ═══════════════════════════════════════════════════════════
    try:
        # A. Duplicate rate by source
        dup_pipe = [
            {"$match": {**base, "status": {"$in": ["duplicate", "routed", "livre", "no_open_orders", "new", "lb"]}}},
            {"$group": {
                "_id": {"$ifNull": ["$source", "direct"]},
                "total": {"$sum": 1},
                "dup": {"$sum": {"$cond": [{"$eq": ["$status", "duplicate"]}, 1, 0]}},
            }},
            {"$sort": {"dup": -1}},
        ]
        dup_raw = await db.leads.aggregate(dup_pipe).to_list(100)
        dup_by_source = []
        for r in dup_raw:
            t = r["total"] or 1
            dup_by_source.append({
                "source": r["_id"],
                "total_leads": r["total"],
                "duplicate_count": r["dup"],
                "duplicate_rate": round(r["dup"] / t * 100, 1),
            })
        result["duplicate_by_source"] = dup_by_source

        # B. Cross-source duplicate matrix
        # Find leads with same phone that were submitted by different sources
        cross_pipe = [
            {"$match": {**ef, "phone": {"$exists": True, "$ne": ""}, "created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$phone",
                "sources": {"$addToSet": {"$ifNull": ["$source", "direct"]}},
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gte": 2}}},
            {"$limit": 500},
        ]
        cross_raw = await db.leads.aggregate(cross_pipe).to_list(500)

        # Build matrix
        cross_matrix = {}
        for r in cross_raw:
            srcs = sorted(r["sources"])
            for i, s1 in enumerate(srcs):
                for s2 in srcs[i+1:]:
                    key = f"{s1}|{s2}"
                    cross_matrix[key] = cross_matrix.get(key, 0) + 1

        result["duplicate_cross_matrix"] = [
            {"source_a": k.split("|")[0], "source_b": k.split("|")[1], "conflict_count": v}
            for k, v in sorted(cross_matrix.items(), key=lambda x: -x[1])
        ][:20]

        # C. Delay between duplicates (bucket)
        delay_pipe = [
            {"$match": {**ef, "status": "duplicate", "created_at": {"$gte": cutoff}}},
            {"$lookup": {
                "from": "leads",
                "let": {"ph": "$phone", "pr": "$produit"},
                "pipeline": [
                    {"$match": {"$expr": {"$and": [
                        {"$eq": ["$phone", "$$ph"]},
                        {"$eq": ["$produit", "$$pr"]},
                        {"$in": ["$status", ["routed", "livre"]]},
                    ]}}},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1},
                    {"$project": {"_id": 0, "created_at": 1}},
                ],
                "as": "original",
            }},
            {"$limit": 200},
        ]
        delay_raw = await db.leads.aggregate(delay_pipe).to_list(200)

        buckets = {"lt_24h": 0, "1d_7d": 0, "gt_7d": 0, "unknown": 0}
        for r in delay_raw:
            if not r.get("original"):
                buckets["unknown"] += 1
                continue
            try:
                dup_dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                orig_dt = datetime.fromisoformat(r["original"][0]["created_at"].replace("Z", "+00:00"))
                delta = abs((dup_dt - orig_dt).total_seconds()) / 3600
                if delta < 24:
                    buckets["lt_24h"] += 1
                elif delta < 168:
                    buckets["1d_7d"] += 1
                else:
                    buckets["gt_7d"] += 1
            except Exception:
                buckets["unknown"] += 1

        result["duplicate_delay_buckets"] = buckets
    except Exception as e:
        logger.error(f"[MONITORING] duplicates failed: {e}")
        result["duplicate_by_source"] = []
        result["duplicate_cross_matrix"] = []
        result["duplicate_delay_buckets"] = {}
        result["_errors"].append("duplicates")

    # ═══════════════════════════════════════════════════════════
    # 3. REJECTION STATS
    # ═══════════════════════════════════════════════════════════
    try:
        rej_pipe = [
            {"$match": {**ef, "created_at": {"$gte": cutoff}, "status": {"$in": [
                "invalid", "duplicate", "no_open_orders", "hold_source", "pending_config", "replaced_by_lb",
            ]}}},
            {"$group": {
                "_id": {
                    "source": {"$ifNull": ["$source", "direct"]},
                    "status": "$status",
                    "produit": {"$ifNull": ["$produit", "unknown"]},
                    "entity": "$entity",
                },
                "count": {"$sum": 1},
            }},
        ]
        rej_raw = await db.leads.aggregate(rej_pipe).to_list(500)

        rejections = {}
        for r in rej_raw:
            src = r["_id"]["source"]
            if src not in rejections:
                rejections[src] = {"total_rejected": 0, "by_reason": {}}
            rejections[src]["total_rejected"] += r["count"]
            reason = r["_id"]["status"]
            rejections[src]["by_reason"][reason] = rejections[src]["by_reason"].get(reason, 0) + r["count"]

        result["rejections_by_source"] = [
            {"source": src, **data}
            for src, data in sorted(rejections.items(), key=lambda x: -x[1]["total_rejected"])
        ]
    except Exception as e:
        logger.error(f"[MONITORING] rejections failed: {e}")
        result["rejections_by_source"] = []
        result["_errors"].append("rejections")

    # ═══════════════════════════════════════════════════════════
    # 4. LB REPLACEMENT STATS
    # ═══════════════════════════════════════════════════════════
    try:
        lb_match = {**ef, "created_at": {"$gte": cutoff}}
        if product:
            lb_match["produit"] = product.upper()

        susp_total = await db.leads.count_documents({**lb_match, "phone_quality": "suspicious"})
        lb_replaced = await db.leads.count_documents({**lb_match, "was_replaced": True})
        susp_delivered = await db.leads.count_documents({
            **lb_match, "phone_quality": "suspicious",
            "was_replaced": {"$ne": True},
            "status": {"$in": ["routed", "livre"]},
        })

        lb_stock = await db.leads.count_documents({
            **build_entity_filter(scope),
            "is_lb": True,
            "status": {"$in": ["lb", "new", "no_open_orders"]},
        })

        result["lb_stats"] = {
            "suspicious_total": susp_total,
            "lb_replaced_count": lb_replaced,
            "suspicious_delivered_count": susp_delivered,
            "lb_stock_available": lb_stock,
            "lb_usage_rate": round(lb_replaced / susp_total * 100, 1) if susp_total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"[MONITORING] lb_stats failed: {e}")
        result["lb_stats"] = {}
        result["_errors"].append("lb_stats")

    # ═══════════════════════════════════════════════════════════
    # 5. CORE BUSINESS KPIS
    # ═══════════════════════════════════════════════════════════
    try:
        total = await db.leads.count_documents(base)
        delivered = await db.leads.count_documents({**base, "status": {"$in": ["routed", "livre"]}})
        valid_total = await db.leads.count_documents({**base, "phone_quality": "valid"})
        delivered_valid = await db.leads.count_documents({
            **base, "phone_quality": "valid", "status": {"$in": ["routed", "livre"]},
        })

        t = total or 1
        result["kpis"] = {
            "total_leads": total,
            "delivered": delivered,
            "valid_total": valid_total,
            "delivered_valid": delivered_valid,
            "real_deliverability_rate": round(delivered / t * 100, 1),
            "clean_rate": round(valid_total / t * 100, 1),
            "economic_yield": round(delivered_valid / t * 100, 1),
        }
    except Exception as e:
        logger.error(f"[MONITORING] kpis failed: {e}")
        result["kpis"] = {}
        result["_errors"].append("kpis")

    if not result["_errors"]:
        del result["_errors"]

    return result
