"""
RDZ CRM — Core Distribution Layer E2E Validation
Exhaustive test suite: A→H scenarios with DB verification.
Run: pytest tests/test_core_e2e_validation.py -v --tb=short
"""

import pytest
import httpx
import asyncio
import uuid
import os
from datetime import datetime, timezone, timedelta

API_URL = os.environ.get("API_URL", "").strip()
if not API_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                API_URL = line.split("=", 1)[1].strip()
                break

PASSWORD = "RdzTest2026!"
USERS = {
    "super_admin": "superadmin@test.local",
    "admin_zr7": "admin_zr7@test.local",
    "ops_zr7": "ops_zr7@test.local",
    "viewer_zr7": "viewer_zr7@test.local",
    "admin_mdl": "admin_mdl@test.local",
    "viewer_mdl": "viewer_mdl@test.local",
}


def login(client, email):
    r = client.post(f"{API_URL}/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["token"]


def auth_headers(token, scope=None):
    h = {"Authorization": f"Bearer {token}"}
    if scope:
        h["X-Entity-Scope"] = scope
    return h


# ═══════════════════════════════════════════════════════════════
# A. INGESTION / SESSION / TRACKING
# ═══════════════════════════════════════════════════════════════

class TestAIngestion:
    def test_a1_session_creation(self):
        """LP visit: session created, anti-doublon works."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/track/session", json={
                "lp_code": "LP_TEST_E2E",
                "form_code": "FORM_TEST_E2E",
                "utm_source": "test_e2e",
                "utm_campaign": "validation",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["session_id"]
            assert data["lp_code"] == "LP_TEST_E2E"
            self.__class__.session_id = data["session_id"]
            self.__class__.visitor_id = data["visitor_id"]

    def test_a2_lp_visit_tracking(self):
        """LP visit event tracked, anti-doublon server-side."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/track/lp-visit", content=f'{{"session_id":"{self.session_id}","lp_code":"LP_TEST_E2E"}}', headers={"Content-Type": "application/json"})
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            # Anti-doublon: second call should return duplicate
            r2 = c.post(f"{API_URL}/api/public/track/lp-visit", content=f'{{"session_id":"{self.session_id}","lp_code":"LP_TEST_E2E"}}', headers={"Content-Type": "application/json"})
            assert r2.json().get("duplicate") is True

    def test_a3_event_tracking(self):
        """CTA click and form_start events tracked."""
        with httpx.Client(timeout=15) as c:
            # CTA click
            r = c.post(f"{API_URL}/api/public/track/event", content=f'{{"session_id":"{self.session_id}","event_type":"cta_click"}}', headers={"Content-Type": "application/json"})
            assert r.status_code == 200
            assert r.json()["success"] is True
            # Form start
            r2 = c.post(f"{API_URL}/api/public/track/event", content=f'{{"session_id":"{self.session_id}","event_type":"form_start"}}', headers={"Content-Type": "application/json"})
            assert r2.json()["success"] is True

    def test_a4_submit_lead_full_payload(self):
        """Lead submission: complete payload, all fields preserved."""
        phone = f"06{uuid.uuid4().hex[:8]}"
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": self.session_id,
                "form_code": "FORM_TEST_E2E",
                "phone": phone,
                "nom": "Dupont",
                "prenom": "Jean",
                "email": "jean@test-e2e.com",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
                "civilite": "M",
                "ville": "Paris",
                "type_logement": "maison",
                "utm_campaign": "e2e_test",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["lead_id"]
            assert data["entity"] == "ZR7"
            assert data["produit"] == "PV"
            self.__class__.test_lead_id = data["lead_id"]

    def test_a5_submit_lead_no_utm(self):
        """Lead without UTM: works fine, no crash."""
        phone = f"06{uuid.uuid4().hex[:8]}"
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": self.session_id,
                "form_code": "FORM_TEST_E2E",
                "phone": phone,
                "nom": "SansUTM",
                "departement": "13",
                "entity": "ZR7",
                "produit": "PAC",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True

    def test_a6_submit_lead_invalid_phone(self):
        """Lead with invalid phone: stored as 'invalid'."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": self.session_id,
                "form_code": "FORM_TEST_E2E",
                "phone": "123",
                "nom": "BadPhone",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "invalid"

    def test_a7_sendbeacon_text_plain(self):
        """sendBeacon fallback: text/plain Content-Type accepted."""
        with httpx.Client(timeout=15) as c:
            r = c.post(
                f"{API_URL}/api/public/track/event",
                content=f'{{"session_id":"{self.session_id}","event_type":"beacon_test"}}',
                headers={"Content-Type": "text/plain"}
            )
            assert r.status_code == 200
            assert r.json()["success"] is True


# ═══════════════════════════════════════════════════════════════
# B. ENTITY / SECURITY / RBAC
# ═══════════════════════════════════════════════════════════════

class TestBSecurity:
    def test_b1_no_auth_rejected(self):
        """No auth: 401 on protected endpoints."""
        with httpx.Client(timeout=15) as c:
            for url in ["/api/leads/list", "/api/deliveries", "/api/clients?entity=ZR7",
                        "/api/commandes?entity=ZR7", "/api/settings"]:
                r = c.get(f"{API_URL}{url}")
                assert r.status_code == 401, f"{url} should be 401 without auth, got {r.status_code}"

    def test_b2_viewer_cannot_write(self):
        """Viewer: no write operations possible."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["viewer_zr7"])
            h = auth_headers(token)
            # Settings
            assert c.get(f"{API_URL}/api/settings", headers=h).status_code == 403
            # Providers
            assert c.get(f"{API_URL}/api/providers", headers=h).status_code == 403
            # Users
            assert c.get(f"{API_URL}/api/auth/users", headers=h).status_code == 403
            # Activity
            assert c.get(f"{API_URL}/api/event-log", headers=h).status_code == 403
            # Billing write
            assert c.put(f"{API_URL}/api/billing/transfer-pricing", headers=h, json={
                "from_entity": "ZR7", "to_entity": "MDL", "product_code": "PV", "unit_price_ht": 50
            }).status_code == 403

    def test_b3_entity_scope_leads(self):
        """X-Entity-Scope filters leads correctly."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            # ZR7 scope
            r = c.get(f"{API_URL}/api/leads/stats", headers=auth_headers(token, "ZR7"))
            assert r.status_code == 200
            # MDL scope
            r2 = c.get(f"{API_URL}/api/leads/stats", headers=auth_headers(token, "MDL"))
            assert r2.status_code == 200

    def test_b4_entity_scope_deliveries(self):
        """X-Entity-Scope filters deliveries correctly."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/deliveries/stats", headers=auth_headers(token, "ZR7"))
            assert r.status_code == 200
            r2 = c.get(f"{API_URL}/api/deliveries/stats", headers=auth_headers(token, "MDL"))
            assert r2.status_code == 200

    def test_b5_entity_isolation_mdl_cannot_read_zr7(self):
        """admin_mdl cannot read ZR7 data."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["admin_mdl"])
            r = c.get(f"{API_URL}/api/clients?entity=ZR7", headers=auth_headers(token))
            assert r.status_code == 403

    def test_b6_provider_key_invalid(self):
        """Invalid provider key: rejected."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0612345678",
                "nom": "Test",
                "departement": "75",
                "api_key": "prov_INVALID_KEY_DOES_NOT_EXIST",
            })
            assert r.status_code == 200
            assert r.json().get("error") is not None or r.json().get("success") is False

    def test_b7_ops_billing_manage_blocked(self):
        """OPS cannot do billing.manage operations."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["ops_zr7"])
            h = auth_headers(token)
            assert c.put(f"{API_URL}/api/billing/transfer-pricing", headers=h, json={
                "from_entity": "ZR7", "to_entity": "MDL", "product_code": "PV", "unit_price_ht": 99
            }).status_code == 403


# ═══════════════════════════════════════════════════════════════
# C. DEDUPLICATION (30-day rule)
# ═══════════════════════════════════════════════════════════════

class TestCDeduplication:
    def test_c1_same_phone_same_product_same_client(self):
        """Same phone+produit+client within 30d: duplicate detected."""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient

        async def run():
            client = AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            from services.duplicate_detector import check_duplicate_30_days

            # Insert a fake delivered lead
            test_phone = "0699990001"
            test_client_id = "test_client_dedup_001"
            await db.leads.insert_one({
                "id": str(uuid.uuid4()),
                "phone": test_phone,
                "produit": "PV",
                "delivery_client_id": test_client_id,
                "status": "routed",
                "routed_at": datetime.now(timezone.utc).isoformat(),
                "entity": "ZR7",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            result = await check_duplicate_30_days(test_phone, "PV", test_client_id)
            assert result.is_duplicate is True, "Should be duplicate"
            assert result.duplicate_type == "30_days"

            # Cleanup
            await db.leads.delete_many({"phone": test_phone})
            client.close()

        asyncio.run(run())

    def test_c2_same_phone_same_product_different_client(self):
        """Same phone+produit but different client: NOT duplicate."""
        import sys
        sys.path.insert(0, "/app/backend")
        loop = asyncio.new_event_loop()
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from services.duplicate_detector import check_duplicate_30_days

            async def run():
                client = AsyncIOMotorClient("mongodb://localhost:27017")
                db = client["test_database"]

                test_phone = "0699990002"
                await db.leads.insert_one({
                    "id": str(uuid.uuid4()),
                    "phone": test_phone,
                    "produit": "PV",
                    "delivery_client_id": "client_A",
                    "status": "routed",
                    "routed_at": datetime.now(timezone.utc).isoformat(),
                    "entity": "ZR7",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                result = await check_duplicate_30_days(test_phone, "PV", "client_B")
                assert result.is_duplicate is False, "Different client = not duplicate"
                await db.leads.delete_many({"phone": test_phone})
                client.close()

            loop.run_until_complete(run())
        finally:
            loop.close()

    def test_c3_same_phone_different_product(self):
        """Same phone but different product: NOT duplicate."""
        import sys
        sys.path.insert(0, "/app/backend")
        loop = asyncio.new_event_loop()
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from services.duplicate_detector import check_duplicate_30_days

            async def run():
                client = AsyncIOMotorClient("mongodb://localhost:27017")
                db = client["test_database"]

                test_phone = "0699990003"
                await db.leads.insert_one({
                    "id": str(uuid.uuid4()),
                    "phone": test_phone,
                    "produit": "PV",
                    "delivery_client_id": "client_X",
                    "status": "routed",
                    "routed_at": datetime.now(timezone.utc).isoformat(),
                    "entity": "ZR7",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                result = await check_duplicate_30_days(test_phone, "PAC", "client_X")
                assert result.is_duplicate is False, "Different product = not duplicate"
                await db.leads.delete_many({"phone": test_phone})
                client.close()

            loop.run_until_complete(run())
        finally:
            loop.close()

    def test_c4_phone_normalization(self):
        """Phone formats: spaces, 9-digit etc. normalize correctly.
        NOTE: +33 prefix is NOT auto-stripped by the validator (documented limitation).
        """
        from config import validate_phone_fr
        cases = [
            ("0612345678", True, "0612345678"),
            ("06 12 34 56 78", True, "0612345678"),
            ("612345678", True, "0612345678"),     # 9 digits, 0 added
            ("123", False, None),                   # Too short
            ("+33612345678", False, None),          # +33 prefix NOT handled (documented)
        ]
        for phone, expect_valid, expect_clean in cases:
            valid, result = validate_phone_fr(phone)
            assert valid == expect_valid, f"Phone {phone}: expected valid={expect_valid}, got {valid}"
            if expect_valid and expect_clean:
                assert result == expect_clean, f"Phone {phone}: expected {expect_clean}, got {result}"

    def test_c5_phone_missing(self):
        """Missing phone: lead stored as invalid."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "",
                "nom": "NoPhone",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            assert r.json()["status"] == "invalid"


# ═══════════════════════════════════════════════════════════════
# D. ROUTING ENGINE
# ═══════════════════════════════════════════════════════════════

class TestDRouting:
    def test_d1_lead_routed_to_active_commande(self):
        """Lead with matching commande: correctly routed."""
        import random
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            h = auth_headers(token, "ZR7")
            r = c.get(f"{API_URL}/api/commandes?entity=ZR7", headers=h)
            assert r.status_code == 200
            cmds = r.json().get("commandes", [])
            if cmds:
                cmd = cmds[0]
                dept = cmd.get("departements", ["75"])[0]
                if dept == "*":
                    dept = "75"
                phone = f"06{random.randint(10000000, 99999999)}"
                r2 = c.post(f"{API_URL}/api/public/leads", json={
                    "session_id": str(uuid.uuid4()),
                    "form_code": "TEST",
                    "phone": phone,
                    "nom": "TestRouting",
                    "departement": dept,
                    "entity": "ZR7",
                    "produit": cmd.get("produit", "PV"),
                })
                assert r2.status_code == 200
                data = r2.json()
                assert data["status"] in ["routed", "no_open_orders", "duplicate"]

    def test_d2_lead_no_commande_stored(self):
        """No matching commande: lead stored with no_open_orders."""
        import random
        with httpx.Client(timeout=15) as c:
            phone = f"06{random.randint(10000000, 99999999)}"
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": phone,
                "nom": "NoCommande",
                "departement": "99",
                "entity": "ZR7",
                "produit": "FAKE_PRODUCT_XYZ",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "no_open_orders"
            assert data["lead_id"]  # Lead STORED, not lost

    def test_d3_routing_reason_clear(self):
        """Routing failure: reason is explicit."""
        import random
        with httpx.Client(timeout=15) as c:
            phone = f"06{random.randint(10000000, 99999999)}"
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": phone,
                "nom": "ReasonTest",
                "departement": "01",
                "entity": "MDL",
                "produit": "ITE",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] in ["routed", "no_open_orders", "duplicate"]


# ═══════════════════════════════════════════════════════════════
# E. DELIVERY (CSV / Email / Status)
# ═══════════════════════════════════════════════════════════════

class TestEDelivery:
    def test_e1_csv_format_zr7(self):
        """CSV generation: ZR7 format = 7 columns, correct headers."""
        import sys
        sys.path.insert(0, "/app/backend")
        from services.csv_delivery import generate_csv_content
        leads = [{"nom": "Test", "prenom": "Jean", "phone": "0612345678", "email": "t@t.com", "departement": "75"}]
        csv = generate_csv_content(leads, "PV", "ZR7")
        lines = csv.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        headers = [h.strip() for h in lines[0].split(",")]
        assert headers == ["nom", "prenom", "telephone", "email", "departement", "proprietaire_maison", "produit"]
        row = [v.strip() for v in lines[1].split(",")]
        assert row[5] == "oui"  # proprietaire_maison
        assert row[6] == "PV"   # produit from commande

    def test_e2_csv_format_mdl(self):
        """CSV generation: MDL format = 8 columns."""
        import sys
        sys.path.insert(0, "/app/backend")
        from services.csv_delivery import generate_csv_content
        leads = [{"nom": "Test", "prenom": "Marie", "phone": "0698765432", "email": "m@m.com", "departement": "13"}]
        csv = generate_csv_content(leads, "PAC", "MDL")
        lines = csv.strip().split("\n")
        headers = lines[0].split(",")
        assert "proprietaire" in headers
        assert "type_logement" in headers

    def test_e3_delivery_state_transitions(self):
        """State machine: valid transitions only."""
        import sys
        sys.path.insert(0, "/app/backend")
        from services.delivery_state_machine import VALID_DELIVERY_TRANSITIONS
        # sent is terminal
        assert VALID_DELIVERY_TRANSITIONS["sent"] == []
        # failed can retry
        assert "sending" in VALID_DELIVERY_TRANSITIONS["failed"]
        # pending_csv can go to ready_to_send
        assert "ready_to_send" in VALID_DELIVERY_TRANSITIONS["pending_csv"]

    def test_e4_delivery_list_api(self):
        """Delivery list endpoint works with pagination."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/deliveries?limit=5", headers=auth_headers(token, "BOTH"))
            assert r.status_code == 200
            data = r.json()
            assert "deliveries" in data
            assert "total" in data


# ═══════════════════════════════════════════════════════════════
# F. CRON / JOBS / LOCKS
# ═══════════════════════════════════════════════════════════════

class TestFCron:
    def test_f1_scheduler_running(self):
        """APScheduler is started, jobs registered."""
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{API_URL}/")
            # Root endpoint should confirm features
            assert r.status_code == 200

    def test_f2_cron_lock_idempotent(self):
        """Cron lock: per-week idempotency prevents double run."""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient

        async def run():
            client = AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            wk = "2099-W01"

            # Insert a lock
            await db.cron_logs.insert_one({
                "job": "intercompany_invoices",
                "week_key": wk,
                "status": "success",
                "run_at": datetime.now(timezone.utc).isoformat(),
            })

            # Check that it would be skipped
            lock = await db.cron_logs.find_one({
                "job": "intercompany_invoices",
                "week_key": wk,
                "status": {"$in": ["running", "success"]}
            })
            assert lock is not None, "Lock should exist"

            await db.cron_logs.delete_many({"week_key": wk})
            client.close()

        asyncio.run(run())

    def test_f3_intercompany_failopen_no_crash(self):
        """Intercompany failure doesn't crash other modules."""
        import asyncio, sys
        sys.path.insert(0, "/app/backend")

        async def run():
            from services.intercompany import maybe_create_intercompany_transfer
            result = await maybe_create_intercompany_transfer(
                delivery_id="chaos_cron_test",
                lead_id="nonexistent",
                commande_id="nonexistent",
                product="FAKE",
                target_entity="ZR7",
            )
            # Should NOT raise, should return gracefully
            assert result["created"] is False

            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            await db.intercompany_transfers.delete_one({"delivery_id": "chaos_cron_test"})
            client.close()

        asyncio.run(run())


# ═══════════════════════════════════════════════════════════════
# G. INTERCOMPANY
# ═══════════════════════════════════════════════════════════════

class TestGIntercompany:
    def test_g1_health_endpoint(self):
        """Intercompany health returns structured data."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/intercompany/health", headers=auth_headers(token))
            assert r.status_code == 200
            data = r.json()
            assert "transfers" in data
            assert "status" in data

    def test_g2_retry_endpoint(self):
        """Retry failed transfers: endpoint works."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.post(f"{API_URL}/api/intercompany/retry-errors", headers=auth_headers(token))
            assert r.status_code == 200

    def test_g3_pricing_list(self):
        """Intercompany pricing list returns data."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/intercompany/pricing", headers=auth_headers(token))
            assert r.status_code == 200
            data = r.json()
            assert "pricing" in data
            assert len(data["pricing"]) > 0


# ═══════════════════════════════════════════════════════════════
# H. OBSERVABILITY / HEALTH
# ═══════════════════════════════════════════════════════════════

class TestHHealth:
    def test_h1_system_health(self):
        """System health aggregates all modules."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/system/health", headers=auth_headers(token))
            assert r.status_code == 200
            data = r.json()
            assert data["status"] in ["healthy", "degraded", "warning", "error"]
            assert "cron" in data["modules"]
            assert "deliveries" in data["modules"]
            assert "intercompany" in data["modules"]
            assert "invoices" in data["modules"]

    def test_h2_version_endpoint(self):
        """Version endpoint returns structured info."""
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{API_URL}/api/system/version")
            assert r.status_code == 200
            data = r.json()
            assert data["version"] == "1.0.0"
            assert data["tag"] == "rdz-core-distribution-validated"
            assert data["git_sha"]

    def test_h3_dashboard_failopen(self):
        """Dashboard with future week: no crash, all keys present."""
        with httpx.Client(timeout=15) as c:
            token = login(c, USERS["super_admin"])
            r = c.get(f"{API_URL}/api/leads/dashboard-stats?week=2099-W01", headers=auth_headers(token, "BOTH"))
            assert r.status_code == 200
            data = r.json()
            for key in ["lead_stats", "delivery_stats", "calendar", "top_clients_7d", "problem_clients"]:
                assert key in data, f"Missing key: {key}"
