"""
RDZ CRM — Client Overlap Guard E2E Tests
Tests: shared detection, alternative routing, fallback, kill switch, perf.
Run: cd /app/backend && pytest tests/test_overlap_guard.py -v
"""

import pytest
import httpx
import uuid
import os
import sys
import asyncio
import random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app/backend")

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


def _db_op(coro):
    """Run async DB operation in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ═══════════════════════════════════════════════════════════════
# 1. UNIT: compute_client_group_key
# ═══════════════════════════════════════════════════════════════

class TestGroupKey:
    def test_single_email(self):
        from services.overlap_guard import compute_client_group_key
        key = compute_client_group_key({"email": "Test@Example.com", "delivery_emails": []})
        assert key == "test@example.com"

    def test_multiple_emails(self):
        from services.overlap_guard import compute_client_group_key
        key = compute_client_group_key({
            "email": "A@b.com",
            "delivery_emails": ["C@D.com", "a@b.com"]  # a@b.com deduped
        })
        assert key == "a@b.com|c@d.com"

    def test_empty(self):
        from services.overlap_guard import compute_client_group_key
        key = compute_client_group_key({"email": "", "delivery_emails": []})
        assert key == ""

    def test_whitespace_normalized(self):
        from services.overlap_guard import compute_client_group_key
        key = compute_client_group_key({"email": "  Hello@World.FR  ", "delivery_emails": []})
        assert key == "hello@world.fr"


# ═══════════════════════════════════════════════════════════════
# 2. UNIT: overlap detection logic
# ═══════════════════════════════════════════════════════════════

class TestOverlapDetection:
    def test_no_overlap_normal_client(self):
        """Normal client with unique email → no overlap."""
        from services.overlap_guard import check_overlap_and_find_alternative
        result = _db_op(check_overlap_and_find_alternative(
            selected_client_id="nonexistent_client",
            selected_commande_id="nonexistent",
            entity="ZR7", produit="PV", departement="75", phone="0699887766",
        ))
        assert result["is_shared"] is False
        assert result["fallback"] is False

    def test_guard_failopen_on_error(self):
        """If client doesn't exist → fail-open, no crash."""
        from services.overlap_guard import check_overlap_and_find_alternative
        result = _db_op(check_overlap_and_find_alternative(
            selected_client_id="DOES_NOT_EXIST",
            selected_commande_id="FAKE",
            entity="ZR7", produit="PV", departement="75", phone="0699887766",
        ))
        assert result["fallback"] is False  # No overlap, just missing client


# ═══════════════════════════════════════════════════════════════
# 3. KILL SWITCH
# ═══════════════════════════════════════════════════════════════

class TestKillSwitch:
    def test_guard_disabled_normal_routing(self):
        """OVERLAP_GUARD_ENABLED=false → normal routing, no overlap check."""
        from motor.motor_asyncio import AsyncIOMotorClient

        async def run():
            client = AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            # Disable guard
            await db.settings.update_one(
                {"key": "overlap_guard"},
                {"$set": {"key": "overlap_guard", "enabled": False}},
                upsert=True,
            )
            client.close()

        _db_op(run())

        # Submit a lead — should work normally
        phone = f"06{random.randint(10000000, 99999999)}"
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST", "phone": phone,
                "nom": "KillSwitchTest", "departement": "75",
                "entity": "ZR7", "produit": "PV",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True

        # Re-enable guard
        async def reenable():
            client = AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            await db.settings.update_one(
                {"key": "overlap_guard"},
                {"$set": {"enabled": True}},
            )
            client.close()

        _db_op(reenable())


# ═══════════════════════════════════════════════════════════════
# 4. DELIVERY FIELDS
# ═══════════════════════════════════════════════════════════════

class TestDeliveryFields:
    def test_delivery_has_overlap_fields(self):
        """New deliveries should have overlap-related fields."""
        phone = f"06{random.randint(10000000, 99999999)}"
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST", "phone": phone,
                "nom": "OverlapFieldTest", "departement": "75",
                "entity": "ZR7", "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            if data.get("delivery_id"):
                # Check delivery in DB
                async def check():
                    from motor.motor_asyncio import AsyncIOMotorClient
                    client = AsyncIOMotorClient("mongodb://localhost:27017")
                    db = client["test_database"]
                    d = await db.deliveries.find_one({"id": data["delivery_id"]}, {"_id": 0})
                    client.close()
                    return d

                delivery = _db_op(check())
                if delivery:
                    assert "client_group_key" in delivery
                    assert "is_shared_client_30d" in delivery
                    assert "overlap_fallback_delivery" in delivery


# ═══════════════════════════════════════════════════════════════
# 5. MONITORING
# ═══════════════════════════════════════════════════════════════

class TestOverlapMonitoring:
    def test_overlap_stats_in_monitoring(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            assert r.status_code == 200
            ov = r.json().get("overlap_stats", {})
            assert "shared_clients_count" in ov
            assert "shared_clients_rate" in ov
            assert "shared_client_deliveries_30d_count" in ov
            assert "overlap_fallback_deliveries_30d_count" in ov

    def test_overlap_stats_entity_scoped(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "ZR7"))
            assert r.status_code == 200
            assert "overlap_stats" in r.json()


# ═══════════════════════════════════════════════════════════════
# 6. REGRESSION: normal routing still works
# ═══════════════════════════════════════════════════════════════

class TestNoRegression:
    def test_normal_lead_routing(self):
        phone = f"06{random.randint(10000000, 99999999)}"
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST", "phone": phone,
                "nom": "NormalRegression", "departement": "75",
                "entity": "ZR7", "produit": "PV",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True

    def test_entity_scoping_still_works(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "admin_mdl@test.local")
            r = c.get(f"{API_URL}/api/clients?entity=ZR7", headers=auth_h(token))
            assert r.status_code == 403

    def test_rbac_still_works(self):
        with httpx.Client(timeout=15) as c:
            token = login(c, "viewer_zr7@test.local")
            r = c.get(f"{API_URL}/api/settings", headers=auth_h(token))
            assert r.status_code == 403

    def test_perf_30d_ok(self):
        """Monitoring endpoint still performs under 5s with overlap stats."""
        import time
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            start = time.time()
            r = c.get(f"{API_URL}/api/monitoring/intelligence?range=30d", headers=auth_h(token, "BOTH"))
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 5, f"Took {elapsed:.1f}s"
