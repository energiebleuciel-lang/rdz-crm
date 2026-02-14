"""
RDZ CRM - Monitoring Intelligence Layer v2
READ-ONLY aggregation. Fail-open per-widget. Strategic decision engine.
"""

import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict
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


def _safe_div(a, b, mult=100):
    return round(a / b * mult, 1) if b > 0 else 0


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, round(v, 1)))


@router.get("/intelligence")
async def monitoring_intelligence(
    request: Request,
    range: str = Query("7d", description="24h|7d|30d|90d"),
    product: Optional[str] = None,
    user: dict = Depends(require_permission("dashboard.view")),
):
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
                },
                "count": {"$sum": 1},
            }},
        ]
        pq_raw = await db.leads.aggregate(pq_pipe).to_list(500)

        prev_pipe = [
            {"$match": prev_base},
            {"$group": {
                "_id": {"source_type": {"$ifNull": ["$lead_source_type", "unknown"]}},
                "count": {"$sum": 1},
            }},
        ]
        prev_raw = await db.leads.aggregate(prev_pipe).to_list(50)
        prev_by_src = {r["_id"]["source_type"]: r["count"] for r in prev_raw}

        sources = {}
        for r in pq_raw:
            src = r["_id"]["source_type"]
            q = r["_id"]["quality"]
            if src not in sources:
                sources[src] = {"total": 0, "valid": 0, "suspicious": 0, "invalid": 0, "unknown": 0}
            sources[src]["total"] += r["count"]
            sources[src][q] = sources[src].get(q, 0) + r["count"]

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
                "valid_rate": _safe_div(s["valid"], t),
                "suspicious_rate": _safe_div(s["suspicious"], t),
                "invalid_rate": _safe_div(s["invalid"], t),
                "trend_pct": trend,
            })
        result["phone_quality"] = phone_quality
    except Exception as e:
        logger.error(f"[MONITORING] phone_quality failed: {e}")
        result["phone_quality"] = []
        result["_errors"].append("phone_quality")

    # ═══════════════════════════════════════════════════════════
    # 2. DUPLICATE INTELLIGENCE
    # ═══════════════════════════════════════════════════════════
    try:
        # A. Duplicate rate by source
        dup_pipe = [
            {"$match": base},
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
                "duplicate_rate": _safe_div(r["dup"], t),
            })
        result["duplicate_by_source"] = dup_by_source

        # B. Duplicate offenders by entity
        ent_list = ["ZR7", "MDL"] if scope == "BOTH" else [scope]
        offenders_by_entity = {}
        for ent in ent_list:
            ent_base = {"entity": ent, "created_at": {"$gte": cutoff}}
            if product:
                ent_base["produit"] = product.upper()
            e_total = await db.leads.count_documents(ent_base)
            e_dup = await db.leads.count_documents({**ent_base, "status": "duplicate"})

            # Duplicates against internal LP vs provider vs other entity
            dup_leads = await db.leads.find(
                {**ent_base, "status": "duplicate"},
                {"_id": 0, "phone": 1, "produit": 1, "source": 1}
            ).limit(500).to_list(500)

            against_internal = 0
            against_provider = 0
            against_other_entity = 0
            for dl in dup_leads:
                orig = await db.leads.find_one({
                    "phone": dl.get("phone"), "produit": dl.get("produit"),
                    "status": {"$in": ["routed", "livre"]},
                }, {"_id": 0, "lead_source_type": 1, "entity": 1})
                if orig:
                    if orig.get("lead_source_type") == "internal_lp":
                        against_internal += 1
                    elif orig.get("lead_source_type") == "provider":
                        against_provider += 1
                    if orig.get("entity") != ent:
                        against_other_entity += 1

            offenders_by_entity[ent] = {
                "total_leads": e_total,
                "duplicate_count": e_dup,
                "duplicate_rate": _safe_div(e_dup, e_total),
                "against_internal_lp": against_internal,
                "against_provider": against_provider,
                "against_other_entity": against_other_entity,
            }
        result["duplicate_offenders_by_entity"] = offenders_by_entity

        # C. Cross-source conflict matrix (enriched with entity)
        cross_pipe = [
            {"$match": {**ef, "phone": {"$exists": True, "$ne": ""}, "created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$phone",
                "entries": {"$push": {"source": {"$ifNull": ["$source", "direct"]}, "entity": "$entity"}},
                "count": {"$sum": 1},
            }},
            {"$match": {"count": {"$gte": 2}}},
            {"$limit": 300},
        ]
        cross_raw = await db.leads.aggregate(cross_pipe).to_list(300)

        cross_matrix = {}
        for r in cross_raw:
            entries = r["entries"]
            seen = set()
            for i, e1 in enumerate(entries):
                for e2 in entries[i+1:]:
                    s1, s2 = e1["source"], e2["source"]
                    ent1, ent2 = e1.get("entity", "?"), e2.get("entity", "?")
                    if s1 == s2 and ent1 == ent2:
                        continue
                    key = f"{min(s1,s2)}|{max(s1,s2)}|{min(ent1,ent2)}|{max(ent1,ent2)}"
                    if key not in seen:
                        cross_matrix[key] = cross_matrix.get(key, 0) + 1
                        seen.add(key)

        result["duplicate_cross_matrix"] = sorted([
            {
                "source_a": k.split("|")[0], "source_b": k.split("|")[1],
                "entity_a": k.split("|")[2], "entity_b": k.split("|")[3],
                "conflict_count": v,
            }
            for k, v in cross_matrix.items()
        ], key=lambda x: -x["conflict_count"])[:25]

        # D. Time buckets by source+entity
        dup_leads_for_buckets = await db.leads.find(
            {**ef, "status": "duplicate", "created_at": {"$gte": cutoff}},
            {"_id": 0, "phone": 1, "produit": 1, "created_at": 1, "source": 1, "entity": 1}
        ).limit(300).to_list(300)

        buckets = {"lt_1h": 0, "1h_24h": 0, "1d_7d": 0, "gt_7d": 0, "unknown": 0}
        for dl in dup_leads_for_buckets:
            orig = await db.leads.find_one({
                "phone": dl["phone"], "produit": dl.get("produit"),
                "status": {"$in": ["routed", "livre"]},
                "created_at": {"$lt": dl["created_at"]},
            }, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
            if not orig:
                buckets["unknown"] += 1
                continue
            try:
                d1 = datetime.fromisoformat(dl["created_at"].replace("Z", "+00:00"))
                d2 = datetime.fromisoformat(orig["created_at"].replace("Z", "+00:00"))
                hours = abs((d1 - d2).total_seconds()) / 3600
                if hours < 1:
                    buckets["lt_1h"] += 1
                elif hours < 24:
                    buckets["1h_24h"] += 1
                elif hours < 168:
                    buckets["1d_7d"] += 1
                else:
                    buckets["gt_7d"] += 1
            except Exception:
                buckets["unknown"] += 1

        result["duplicate_time_buckets"] = buckets
    except Exception as e:
        logger.error(f"[MONITORING] duplicates failed: {e}")
        result.setdefault("duplicate_by_source", [])
        result.setdefault("duplicate_offenders_by_entity", {})
        result.setdefault("duplicate_cross_matrix", [])
        result.setdefault("duplicate_time_buckets", {})
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

        result["rejections_by_source"] = sorted([
            {"source": src, **data}
            for src, data in rejections.items()
        ], key=lambda x: -x["total_rejected"])
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
            "is_lb": True, "status": {"$in": ["lb", "new", "no_open_orders"]},
        })
        result["lb_stats"] = {
            "suspicious_total": susp_total,
            "lb_replaced_count": lb_replaced,
            "suspicious_delivered_count": susp_delivered,
            "lb_stock_available": lb_stock,
            "lb_usage_rate": _safe_div(lb_replaced, susp_total),
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
        result["kpis"] = {
            "total_leads": total, "delivered": delivered,
            "valid_total": valid_total, "delivered_valid": delivered_valid,
            "real_deliverability_rate": _safe_div(delivered, total),
            "clean_rate": _safe_div(valid_total, total),
            "economic_yield": _safe_div(delivered_valid, total),
        }
    except Exception as e:
        logger.error(f"[MONITORING] kpis failed: {e}")
        result["kpis"] = {}
        result["_errors"].append("kpis")

    # ═══════════════════════════════════════════════════════════
    # 6. SOURCE ADVANCED METRICS + SCORES
    # ═══════════════════════════════════════════════════════════
    try:
        adv_pipe = [
            {"$match": base},
            {"$group": {
                "_id": {"$ifNull": ["$source", "direct"]},
                "total": {"$sum": 1},
                "valid": {"$sum": {"$cond": [{"$eq": ["$phone_quality", "valid"]}, 1, 0]}},
                "suspicious": {"$sum": {"$cond": [{"$eq": ["$phone_quality", "suspicious"]}, 1, 0]}},
                "invalid": {"$sum": {"$cond": [{"$eq": ["$phone_quality", "invalid"]}, 1, 0]}},
                "duplicate": {"$sum": {"$cond": [{"$eq": ["$status", "duplicate"]}, 1, 0]}},
                "delivered": {"$sum": {"$cond": [{"$in": ["$status", ["routed", "livre"]]}, 1, 0]}},
                "replaced": {"$sum": {"$cond": [{"$eq": ["$was_replaced", True]}, 1, 0]}},
                "rejected": {"$sum": {"$cond": [{"$in": ["$status", [
                    "invalid", "duplicate", "no_open_orders", "hold_source", "pending_config",
                ]]}, 1, 0]}},
            }},
            {"$sort": {"total": -1}},
            {"$limit": 50},
        ]
        adv_raw = await db.leads.aggregate(adv_pipe).to_list(50)

        source_scores = []
        for r in adv_raw:
            t = r["total"] or 1
            vr = _safe_div(r["valid"], t)
            sr = _safe_div(r["suspicious"], t)
            ir = _safe_div(r["invalid"], t)
            dr = _safe_div(r["duplicate"], t)
            delr = _safe_div(r["delivered"], t)
            rejr = _safe_div(r["rejected"], t)
            lbr = _safe_div(r["replaced"], t)

            # Toxicity Score (0-100, higher = more toxic)
            raw_tox = (dr * 2) + sr + rejr - delr
            toxicity = _clamp(raw_tox)

            # Trust Score (0-100, higher = more trustworthy)
            raw_trust = (vr * 0.4) + (delr * 0.4) - (dr * 0.1) - (sr * 0.1)
            trust = _clamp(raw_trust)

            source_scores.append({
                "source": r["_id"],
                "total": r["total"],
                "valid_rate": vr, "suspicious_rate": sr, "invalid_rate": ir,
                "duplicate_rate": dr, "deliverability_rate": delr,
                "rejection_rate": rejr, "lb_replacement_rate": lbr,
                "toxicity_score": toxicity,
                "toxicity_breakdown": {"dup_x2": round(dr * 2, 1), "susp": sr, "rej": rejr, "deliv_neg": round(-delr, 1)},
                "trust_score": trust,
                "trust_breakdown": {"valid_x04": round(vr * 0.4, 1), "deliv_x04": round(delr * 0.4, 1), "dup_neg": round(-dr * 0.1, 1), "susp_neg": round(-sr * 0.1, 1)},
            })

        source_scores.sort(key=lambda x: -x["trust_score"])
        result["source_scores"] = source_scores
    except Exception as e:
        logger.error(f"[MONITORING] source_scores failed: {e}")
        result["source_scores"] = []
        result["_errors"].append("source_scores")

    # ═══════════════════════════════════════════════════════════
    # 7. INTERNAL CANNIBALIZATION INDEX
    # ═══════════════════════════════════════════════════════════
    try:
        # Only meaningful when scope is BOTH or we compute for both entities
        cross_dup_pipe = [
            {"$match": {"created_at": {"$gte": cutoff}, "phone": {"$exists": True, "$ne": ""}}},
            {"$group": {
                "_id": "$phone",
                "entities": {"$addToSet": "$entity"},
                "count": {"$sum": 1},
            }},
            {"$match": {"entities": {"$size": 2}, "count": {"$gte": 2}}},
        ]
        cross_raw = await db.leads.aggregate(cross_dup_pipe).to_list(1000)
        cross_entity_count = len(cross_raw)

        total_unique_phones = len(await db.leads.aggregate([
            {"$match": {**ef, "created_at": {"$gte": cutoff}, "phone": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$phone"}},
        ]).to_list(50000))

        # First source distribution for cross-entity leads
        first_src = {"ZR7": 0, "MDL": 0}
        for cr in cross_raw[:200]:
            first = await db.leads.find_one(
                {"phone": cr["_id"], "status": {"$in": ["routed", "livre", "new"]}},
                {"_id": 0, "entity": 1},
                sort=[("created_at", 1)],
            )
            if first:
                ent = first.get("entity", "")
                if ent in first_src:
                    first_src[ent] += 1

        cann_rate = _safe_div(cross_entity_count, total_unique_phones)

        result["cannibalization"] = {
            "cross_entity_duplicate_count": cross_entity_count,
            "total_unique_phones": total_unique_phones,
            "cross_entity_duplicate_rate": cann_rate,
            "first_source_distribution": first_src,
            "cannibalization_index": _clamp(cann_rate),
        }
    except Exception as e:
        logger.error(f"[MONITORING] cannibalization failed: {e}")
        result["cannibalization"] = {}
        result["_errors"].append("cannibalization")

    # ═══════════════════════════════════════════════════════════
    # 8. CLIENT OVERLAP STATS
    # ═══════════════════════════════════════════════════════════
    try:
        from services.overlap_guard import compute_client_group_key

        # Shared clients: clients with emails present in both entities
        all_clients = await db.clients.find(
            {"active": True}, {"_id": 0, "id": 1, "entity": 1, "email": 1, "delivery_emails": 1}
        ).to_list(500)

        email_to_entities = defaultdict(set)
        client_keys = {}
        for c in all_clients:
            key = compute_client_group_key(c)
            if key:
                client_keys[c["id"]] = key
                for em in key.split("|"):
                    email_to_entities[em].add(c.get("entity", ""))

        shared_emails = {em for em, ents in email_to_entities.items() if len(ents) >= 2}
        shared_client_ids = set()
        for c in all_clients:
            key = client_keys.get(c["id"], "")
            for em in key.split("|"):
                if em in shared_emails:
                    shared_client_ids.add(c["id"])
                    break

        total_clients = len(all_clients) or 1
        shared_count = len(shared_client_ids)

        # Overlap deliveries (30d window from deliveries collection)
        del_base = {**ef, "created_at": {"$gte": cutoff}}
        total_dels = await db.deliveries.count_documents(del_base)
        shared_dels = await db.deliveries.count_documents({**del_base, "is_shared_client_30d": True})
        fallback_dels = await db.deliveries.count_documents({**del_base, "overlap_fallback_delivery": True})

        result["overlap_stats"] = {
            "shared_clients_count": shared_count,
            "shared_clients_rate": _safe_div(shared_count, total_clients),
            "shared_client_deliveries_30d_count": shared_dels,
            "shared_client_deliveries_30d_rate": _safe_div(shared_dels, total_dels) if total_dels else 0,
            "overlap_fallback_deliveries_30d_count": fallback_dels,
            "overlap_fallback_deliveries_30d_rate": _safe_div(fallback_dels, shared_dels) if shared_dels else 0,
        }
    except Exception as e:
        logger.error(f"[MONITORING] overlap_stats failed: {e}")
        result["overlap_stats"] = {}
        result["_errors"].append("overlap_stats")

    if not result["_errors"]:
        del result["_errors"]

    return result
