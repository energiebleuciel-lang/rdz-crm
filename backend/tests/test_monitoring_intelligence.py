"""
RDZ CRM — Monitoring Intelligence v2 E2E Tests
Tests: structure, entity scoping, scores, cannibalization, performance.
Run: cd /app/backend && pytest tests/test_monitoring_intelligence.py -v
"""

import pytest
import httpx
import os
import time

API_URL = ""
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            API_URL = line.split("=", 1)[1].strip()
            break

PASSWORD = "RdzTest2026!"


def login(c, email):
    r = c.post(f"{API_URL}/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    return r.json()["token"]


def auth_h(token, scope=None):
    h = {"Authorization": f"Bearer {token}"}
    if scope:
        h["X-Entity-Scope"] = scope
    return h


class TestStructure:
    """All v2 sections present in response."""

    def test_all_sections_present(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            d = r.json()
            required = [
                "phone_quality", "duplicate_by_source", "duplicate_cross_matrix",
                "duplicate_time_buckets", "duplicate_offenders_by_entity",
                "rejections_by_source", "lb_stats", "kpis",
                "source_scores", "cannibalization",
            ]
            for key in required:
                assert key in d, f"Missing: {key}"

    def test_range_24h(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=24h", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            assert r.json()["range"] == "24h"

    def test_range_90d(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200

    def test_product_filter(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d&product=PV", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            assert r.json()["product"] == "PV"


class TestEntityScoping:
    def test_scope_both(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            assert r.json()["scope"] == "BOTH"
            assert r.json()["kpis"]["total_leads"] > 0

    def test_scope_zr7_smaller(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r_both = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            r_zr7 = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "ZR7"))
            assert r_zr7.json()["kpis"]["total_leads"] <= r_both.json()["kpis"]["total_leads"]

    def test_non_super_admin_forced(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "admin_zr7@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token))
            assert r.json()["scope"] == "ZR7"

    def test_viewer_can_access(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "viewer_zr7@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token))
            assert r.status_code == 200

    def test_no_auth_401(self):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{API_URL}/api/monitoring/intelligence")
            assert r.status_code == 401

    def test_offenders_both_entities(self):
        """Mode BOTH shows offenders for both ZR7 and MDL."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            off = r.json().get("duplicate_offenders_by_entity", {})
            assert "ZR7" in off
            assert "MDL" in off


class TestScores:
    """Toxicity and trust scores are coherent."""

    def test_scores_present(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            scores = r.json().get("source_scores", [])
            assert len(scores) > 0
            s = scores[0]
            assert "toxicity_score" in s
            assert "trust_score" in s
            assert "toxicity_breakdown" in s
            assert "trust_breakdown" in s

    def test_scores_bounded_0_100(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            for s in r.json().get("source_scores", []):
                assert 0 <= s["toxicity_score"] <= 100, f"Toxicity out of bounds: {s}"
                assert 0 <= s["trust_score"] <= 100, f"Trust out of bounds: {s}"

    def test_no_division_by_zero(self):
        """Even with 0 leads for a source, no crash."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=24h&product=ITE", headers=auth_h(token, "ZR7"))
            assert r.status_code == 200
            kpis = r.json()["kpis"]
            # All rates should be 0 if no data, not error
            for key in ["real_deliverability_rate", "clean_rate", "economic_yield"]:
                assert isinstance(kpis.get(key, 0), (int, float))


class TestCannibalization:
    def test_cannibalization_structure(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            cann = r.json().get("cannibalization", {})
            for key in ["cross_entity_duplicate_count", "total_unique_phones",
                        "cross_entity_duplicate_rate", "first_source_distribution",
                        "cannibalization_index"]:
                assert key in cann, f"Missing cannibalization key: {key}"

    def test_cannibalization_index_bounded(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            idx = r.json()["cannibalization"]["cannibalization_index"]
            assert 0 <= idx <= 100


class TestCoherence:
    def test_quality_rates_sum_100(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            for pq in r.json().get("phone_quality", []):
                total_rate = pq["valid_rate"] + pq["suspicious_rate"] + pq["invalid_rate"]
                assert 99 <= total_rate <= 101, f"Rates don't sum ~100: {pq}"

    def test_deliverability_coherent(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            k = r.json()["kpis"]
            if k["total_leads"] > 0:
                expected = round(k["delivered"] / k["total_leads"] * 100, 1)
                assert abs(k["real_deliverability_rate"] - expected) <= 0.2


class TestPerformance:
    def test_30d_under_5s(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            start = time.time()
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 5, f"Took {elapsed:.1f}s"

    def test_90d_under_10s(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            start = time.time()
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 10, f"Took {elapsed:.1f}s"
