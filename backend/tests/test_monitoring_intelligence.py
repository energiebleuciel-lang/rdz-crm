"""
RDZ CRM — Monitoring Intelligence E2E Tests
Tests: entity scoping, ratio coherence, performance, structure.
Run: cd /app/backend && pytest tests/test_monitoring_intelligence.py -v
"""

import pytest
import httpx
import os
import sys
import time

sys.path.insert(0, "/app/backend")

API_URL = ""
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            API_URL = line.split("=", 1)[1].strip()
            break

PASSWORD = "RdzTest2026!"


def login(client, email):
    r = client.post(f"{API_URL}/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    return r.json()["token"]


def auth_h(token, scope=None):
    h = {"Authorization": f"Bearer {token}"}
    if scope:
        h["X-Entity-Scope"] = scope
    return h


class TestMonitoringEndpoint:
    """Structure and completeness of /api/monitoring/intelligence."""

    def test_returns_all_sections(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            d = r.json()
            for key in ["phone_quality", "duplicate_by_source", "duplicate_cross_matrix",
                        "duplicate_delay_buckets", "rejections_by_source", "lb_stats", "kpis"]:
                assert key in d, f"Missing key: {key}"

    def test_range_filter_24h(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=24h", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            assert r.json()["range"] == "24h"

    def test_range_filter_90d(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            assert r.json()["range"] == "90d"

    def test_product_filter(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d&product=PV", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            assert r.json()["product"] == "PV"


class TestEntityScoping:
    """X-Entity-Scope correctly filters monitoring data."""

    def test_scope_both(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            total_both = r.json()["kpis"]["total_leads"]
            assert total_both > 0

    def test_scope_zr7_smaller_than_both(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r_both = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            r_zr7 = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "ZR7"))
            both_total = r_both.json()["kpis"]["total_leads"]
            zr7_total = r_zr7.json()["kpis"]["total_leads"]
            assert zr7_total <= both_total

    def test_non_super_admin_scoped(self):
        """admin_zr7 sees only ZR7 data."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "admin_zr7@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token))
            assert r.status_code == 200
            assert r.json()["scope"] == "ZR7"

    def test_viewer_has_access(self):
        """Viewers with dashboard.view can access monitoring."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "viewer_zr7@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token))
            assert r.status_code == 200

    def test_no_auth_rejected(self):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{API_URL}/api/monitoring/intelligence")
            assert r.status_code == 401


class TestRatioCoherence:
    """Verify ratios match raw data."""

    def test_quality_rates_sum_to_100(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            for pq in r.json().get("phone_quality", []):
                total_rate = pq["valid_rate"] + pq["suspicious_rate"] + pq["invalid_rate"]
                # Allow small rounding errors
                assert 99 <= total_rate <= 101, f"Rates don't sum to ~100 for {pq['source_type']}: {total_rate}"

    def test_deliverability_rate_coherent(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            kpis = r.json()["kpis"]
            if kpis["total_leads"] > 0:
                expected = round(kpis["delivered"] / kpis["total_leads"] * 100, 1)
                assert abs(kpis["real_deliverability_rate"] - expected) <= 0.2

    def test_clean_rate_coherent(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            kpis = r.json()["kpis"]
            if kpis["total_leads"] > 0:
                expected = round(kpis["valid_total"] / kpis["total_leads"] * 100, 1)
                assert abs(kpis["clean_rate"] - expected) <= 0.2


class TestPerformance:
    """Ensure queries don't explode."""

    def test_response_time_under_5s(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            start = time.time()
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 5, f"Response took {elapsed:.1f}s (max 5s)"

    def test_90d_range_acceptable(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            start = time.time()
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=90d", headers=auth_h(token, "BOTH"))
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 10, f"90d range took {elapsed:.1f}s (max 10s)"
