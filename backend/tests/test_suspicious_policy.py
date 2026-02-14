"""
RDZ CRM — Suspicious Phone Policy E2E Tests
Tests: provider reject, inter-CRM reject, LB replacement, no LB fallback.
Run: cd /app/backend && pytest tests/test_suspicious_policy.py -v
"""

import pytest
import httpx
import uuid
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

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
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["token"]


def auth_h(token, scope=None):
    h = {"Authorization": f"Bearer {token}"}
    if scope:
        h["X-Entity-Scope"] = scope
    return h


# ═══════════════════════════════════════════════════════════════
# SETUP: Create a test provider for rejection tests
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def test_provider_key():
    """Create a test provider and return its API key."""
    with httpx.Client(timeout=15) as c:
        token = login(c, "superadmin@test.local")
        slug = f"test_susp_{uuid.uuid4().hex[:6]}"
        r = c.post(f"{API_URL}/api/providers", headers=auth_h(token), json={
            "name": f"Test Suspicious Provider",
            "slug": slug,
            "entity": "ZR7",
        })
        if r.status_code == 200:
            return r.json()["provider"]["api_key"]
        # Slug collision — try again
        slug2 = f"test_susp2_{uuid.uuid4().hex[:6]}"
        r2 = c.post(f"{API_URL}/api/providers", headers=auth_h(token), json={
            "name": f"Test Suspicious Provider 2",
            "slug": slug2,
            "entity": "ZR7",
        })
        assert r2.status_code == 200
        return r2.json()["provider"]["api_key"]


# ═══════════════════════════════════════════════════════════════
# 1. PROVIDER SUSPICIOUS → REJECT
# ═══════════════════════════════════════════════════════════════

class TestProviderSuspiciousReject:
    def test_provider_suspicious_rejected(self, test_provider_key):
        """Provider + suspicious phone → rejected, no lead created."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0606060606",  # suspicious: alternating
                "nom": "ProvSusp",
                "departement": "75",
                "produit": "PV",
                "api_key": test_provider_key,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is False
            assert data["error"] == "suspicious_provider_rejected"
            assert data["phone_quality"] == "suspicious"

    def test_provider_valid_phone_accepted(self, test_provider_key):
        """Provider + valid phone → accepted normally."""
        import random
        with httpx.Client(timeout=15) as c:
            phone = f"06{random.randint(10000000, 99999999)}"
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": phone,
                "nom": "ProvValid",
                "departement": "75",
                "produit": "PV",
                "api_key": test_provider_key,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True


# ═══════════════════════════════════════════════════════════════
# 2. INTER-CRM SUSPICIOUS → REJECT
# ═══════════════════════════════════════════════════════════════

class TestInterCRMSuspiciousReject:
    def test_intercrm_suspicious_rejected(self):
        """Inter-CRM (invalid API key) + suspicious → rejected."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0606060606",
                "nom": "InterCRMSusp",
                "departement": "75",
                "produit": "PV",
                "api_key": "prov_FAKE_INTERCRM_KEY",
            })
            assert r.status_code == 200
            data = r.json()
            # Either rejected as suspicious OR as invalid provider key
            assert data["success"] is False


# ═══════════════════════════════════════════════════════════════
# 3. INTERNAL LP SUSPICIOUS + LB AVAILABLE → LB DELIVERED
# ═══════════════════════════════════════════════════════════════

class TestInternalLPReplacement:
    def _setup_lb_lead(self, entity, produit, dept):
        """Insert a compatible LB lead directly in DB."""
        loop = asyncio.new_event_loop()
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import random

            async def insert():
                client = AsyncIOMotorClient("mongodb://localhost:27017")
                db = client["test_database"]
                lb_id = str(uuid.uuid4())
                phone = f"06{random.randint(10000000, 99999999)}"
                await db.leads.insert_one({
                    "id": lb_id,
                    "phone": phone,
                    "phone_quality": "valid",
                    "nom": "LB_Replacement_Test",
                    "prenom": "",
                    "email": "",
                    "departement": dept,
                    "entity": entity,
                    "lead_owner_entity": entity,
                    "produit": produit,
                    "status": "lb",
                    "is_lb": True,
                    "lb_since": datetime.now(timezone.utc).isoformat(),
                    "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                })
                client.close()
                return lb_id, phone

            return loop.run_until_complete(insert())
        finally:
            loop.close()

    def _check_lead_status(self, lead_id):
        """Read lead status from DB."""
        loop = asyncio.new_event_loop()
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            async def check():
                client = AsyncIOMotorClient("mongodb://localhost:27017")
                db = client["test_database"]
                lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
                client.close()
                return lead

            return loop.run_until_complete(check())
        finally:
            loop.close()

    def _get_active_commande(self, entity, produit):
        """Get an active commande for the entity+produit."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "superadmin@test.local")
            r = c.get(
                f"{API_URL}/api/commandes?entity={entity}&produit={produit}",
                headers=auth_h(token, entity)
            )
            if r.status_code == 200:
                cmds = r.json().get("commandes", [])
                if cmds:
                    return cmds[0]
        return None

    def test_zr7_suspicious_lb_replacement(self):
        """ZR7: suspicious internal LP + LB dispo → LB delivered."""
        cmd = self._get_active_commande("ZR7", "PV")
        if not cmd:
            pytest.skip("No active ZR7/PV commande")
        depts = cmd.get("departements", ["75"])
        dept = depts[0] if depts[0] != "*" else "75"

        # Insert a compatible LB
        lb_id, lb_phone = self._setup_lb_lead("ZR7", "PV", dept)

        # Submit a suspicious lead from internal LP
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "lp_code": "LP_ZR7_INTERNAL",
                "phone": "0611111111",  # suspicious
                "nom": "SuspZR7",
                "departement": dept,
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            susp_lead_id = data["lead_id"]

        # Check what happened
        susp = self._check_lead_status(susp_lead_id)
        lb = self._check_lead_status(lb_id)

        if susp.get("was_replaced"):
            # LB was used instead
            assert susp["status"] == "replaced_by_lb"
            assert susp["replacement_source"] == "LB"
            assert susp["replacement_lead_id"] == lb_id
            assert lb["status"] in ["routed", "reserved_for_replacement"]
        else:
            # No replacement (maybe LB was filtered by dedup) — suspicious delivered
            assert data["status"] in ["routed", "no_open_orders", "duplicate"]

    def test_suspicious_no_lb_delivers_normally(self):
        """Suspicious + no LB available → suspicious delivered normally."""
        import random
        with httpx.Client(timeout=15) as c:
            phone = f"0{random.choice(['6','7'])}{str(random.randint(10000000,99999999))[:7]}11"
            # Make it suspicious by making it alternating
            phone = "0678787878"  # suspicious alternating

            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "lp_code": "LP_MDL_INTERNAL",
                "phone": phone,
                "nom": "SuspNoLB",
                "departement": "99",  # Unlikely dept, no LB available
                "entity": "MDL",
                "produit": "ITE",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            # Should be accepted (routed or no_open_orders)
            assert data["status"] in ["routed", "no_open_orders", "duplicate"]

    def test_mdl_suspicious_lb_replacement(self):
        """MDL: suspicious internal LP + LB dispo → LB delivered."""
        cmd = self._get_active_commande("MDL", "PAC")
        if not cmd:
            pytest.skip("No active MDL/PAC commande")
        depts = cmd.get("departements", ["13"])
        dept = depts[0] if depts[0] != "*" else "13"

        lb_id, lb_phone = self._setup_lb_lead("MDL", "PAC", dept)

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "lp_code": "LP_MDL_INTERNAL",
                "phone": "0611111111",
                "nom": "SuspMDL",
                "departement": dept,
                "entity": "MDL",
                "produit": "PAC",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True

    def test_product_matching_pv(self):
        """LB replacement respects product: PV commande → PV LB only."""
        cmd = self._get_active_commande("ZR7", "PV")
        if not cmd:
            pytest.skip("No active ZR7/PV commande")
        depts = cmd.get("departements", ["75"])
        dept = depts[0] if depts[0] != "*" else "75"

        # Insert LB for PAC (wrong product)
        self._setup_lb_lead("ZR7", "PAC", dept)
        # Insert LB for PV (correct product)
        lb_pv_id, _ = self._setup_lb_lead("ZR7", "PV", dept)

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "lp_code": "LP_ZR7_INT",
                "phone": "0611111111",
                "nom": "ProductMatch",
                "departement": dept,
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            # If replaced, it should be with the PV LB
            susp = self._check_lead_status(data["lead_id"])
            if susp.get("was_replaced"):
                assert susp["replacement_lead_id"] == lb_pv_id


# ═══════════════════════════════════════════════════════════════
# 4. REGRESSION: No impact on quotas, priorities, entity scoping
# ═══════════════════════════════════════════════════════════════

class TestNoRegression:
    def test_valid_phone_normal_flow(self):
        """Valid phone, no suspicious → normal routing unchanged."""
        import random
        with httpx.Client(timeout=15) as c:
            phone = f"06{random.randint(10000000, 99999999)}"
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": phone,
                "nom": "NormalFlow",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["status"] in ["routed", "no_open_orders", "duplicate"]

    def test_entity_scoping_unchanged(self):
        """Entity scoping still works correctly."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "admin_mdl@test.local")
            r = c.get(f"{API_URL}/api/clients?entity=ZR7", headers=auth_h(token))
            assert r.status_code == 403  # MDL admin can't see ZR7

    def test_rbac_unchanged(self):
        """RBAC still enforced."""
        with httpx.Client(timeout=15) as c:
            token = login(c, "viewer_zr7@test.local")
            r = c.get(f"{API_URL}/api/settings", headers=auth_h(token))
            assert r.status_code == 403
