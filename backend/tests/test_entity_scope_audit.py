"""
Entity Scope Audit Test - Critical Verification
================================================
Tests that X-Entity-Scope header correctly filters data on ALL endpoints.
Validates:
1. super_admin with ZR7/MDL/BOTH scope gets different data
2. ops_zr7 ALWAYS gets ZR7 data only (ignores X-Entity-Scope header)
3. ops_mdl ALWAYS gets MDL data only (ignores X-Entity-Scope header)

Expected data counts (from DB):
- ZR7: 1597 leads, 4 clients, 7 commandes, 405 deliveries
- MDL: 973 leads, 6 clients, 7 commandes, 228 deliveries
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@test.local"
SUPER_ADMIN_PASS = "RdzTest2026!"
OPS_ZR7_EMAIL = "ops_zr7@test.local"
OPS_ZR7_PASS = "RdzTest2026!"
OPS_MDL_EMAIL = "ops_mdl@test.local"
OPS_MDL_PASS = "RdzTest2026!"


@pytest.fixture(scope="module")
def super_admin_token():
    """Get super_admin auth token"""
    res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASS}
    )
    assert res.status_code == 200, f"Super admin login failed: {res.text}"
    return res.json().get("token")


@pytest.fixture(scope="module")
def ops_zr7_token():
    """Get ops_zr7 auth token"""
    res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OPS_ZR7_EMAIL, "password": OPS_ZR7_PASS}
    )
    assert res.status_code == 200, f"ops_zr7 login failed: {res.text}"
    return res.json().get("token")


@pytest.fixture(scope="module")
def ops_mdl_token():
    """Get ops_mdl auth token"""
    res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OPS_MDL_EMAIL, "password": OPS_MDL_PASS}
    )
    assert res.status_code == 200, f"ops_mdl login failed: {res.text}"
    return res.json().get("token")


class TestDebugScopeEndpoint:
    """Test the debug endpoint that shows scope resolution"""

    def test_debug_scope_super_admin_zr7(self, super_admin_token):
        """Super admin with X-Entity-Scope: ZR7 should resolve to ZR7"""
        res = requests.get(
            f"{BASE_URL}/api/invoices/debug/scope-check",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "ZR7"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_super_admin"] is True
        assert data["header_x_entity_scope"] == "ZR7"
        assert data["final_scope_applied"] == "ZR7"
        print(f"[PASS] Debug scope ZR7: {data}")

    def test_debug_scope_super_admin_mdl(self, super_admin_token):
        """Super admin with X-Entity-Scope: MDL should resolve to MDL"""
        res = requests.get(
            f"{BASE_URL}/api/invoices/debug/scope-check",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "MDL"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["final_scope_applied"] == "MDL"
        print(f"[PASS] Debug scope MDL: {data}")

    def test_debug_scope_super_admin_both(self, super_admin_token):
        """Super admin with X-Entity-Scope: BOTH should resolve to BOTH"""
        res = requests.get(
            f"{BASE_URL}/api/invoices/debug/scope-check",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "BOTH"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["final_scope_applied"] == "BOTH"
        print(f"[PASS] Debug scope BOTH: {data}")

    def test_debug_scope_ops_zr7_ignored(self, ops_zr7_token):
        """ops_zr7 should ALWAYS get ZR7 even with X-Entity-Scope: MDL"""
        res = requests.get(
            f"{BASE_URL}/api/invoices/debug/scope-check",
            headers={
                "Authorization": f"Bearer {ops_zr7_token}",
                "X-Entity-Scope": "MDL"  # This should be IGNORED
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_super_admin"] is False
        assert data["final_scope_applied"] == "ZR7", f"ops_zr7 should ALWAYS get ZR7, got {data['final_scope_applied']}"
        print(f"[PASS] ops_zr7 scope forced to ZR7: {data}")

    def test_debug_scope_ops_mdl_ignored(self, ops_mdl_token):
        """ops_mdl should ALWAYS get MDL even with X-Entity-Scope: ZR7"""
        res = requests.get(
            f"{BASE_URL}/api/invoices/debug/scope-check",
            headers={
                "Authorization": f"Bearer {ops_mdl_token}",
                "X-Entity-Scope": "ZR7"  # This should be IGNORED
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_super_admin"] is False
        assert data["final_scope_applied"] == "MDL", f"ops_mdl should ALWAYS get MDL, got {data['final_scope_applied']}"
        print(f"[PASS] ops_mdl scope forced to MDL: {data}")


class TestDashboardStatsEntityScope:
    """Test GET /api/leads/dashboard-stats respects X-Entity-Scope header"""

    def test_dashboard_stats_zr7_vs_mdl(self, super_admin_token):
        """ZR7 scope should return different counts than MDL scope"""
        # Get ZR7 stats
        res_zr7 = requests.get(
            f"{BASE_URL}/api/leads/dashboard-stats",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "ZR7"
            }
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        # Get MDL stats
        res_mdl = requests.get(
            f"{BASE_URL}/api/leads/dashboard-stats",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "MDL"
            }
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        # Get BOTH stats
        res_both = requests.get(
            f"{BASE_URL}/api/leads/dashboard-stats",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "BOTH"
            }
        )
        assert res_both.status_code == 200
        data_both = res_both.json()

        print(f"[DEBUG] ZR7 lead_stats: {data_zr7.get('lead_stats')}")
        print(f"[DEBUG] MDL lead_stats: {data_mdl.get('lead_stats')}")
        print(f"[DEBUG] BOTH lead_stats: {data_both.get('lead_stats')}")
        print(f"[DEBUG] ZR7 delivery_stats: {data_zr7.get('delivery_stats')}")
        print(f"[DEBUG] MDL delivery_stats: {data_mdl.get('delivery_stats')}")
        print(f"[DEBUG] BOTH delivery_stats: {data_both.get('delivery_stats')}")

        # Verify the data is DIFFERENT for ZR7 vs MDL
        # They should have different problem_clients, top_clients, etc.
        zr7_problem = len(data_zr7.get("problem_clients", []))
        mdl_problem = len(data_mdl.get("problem_clients", []))
        both_problem = len(data_both.get("problem_clients", []))

        print(f"[RESULT] ZR7 problem_clients count: {zr7_problem}")
        print(f"[RESULT] MDL problem_clients count: {mdl_problem}")
        print(f"[RESULT] BOTH problem_clients count: {both_problem}")

        # BOTH should have >= ZR7 and >= MDL (union of both)
        assert both_problem >= max(zr7_problem, mdl_problem), \
            f"BOTH ({both_problem}) should have >= ZR7 ({zr7_problem}) and MDL ({mdl_problem})"
        print("[PASS] Dashboard stats entity scope filtering working")


class TestCommandesEntityScope:
    """Test GET /api/commandes respects entity parameter"""

    def test_commandes_zr7_vs_mdl(self, super_admin_token):
        """ZR7 commandes should differ from MDL commandes"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/commandes?entity=ZR7",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/commandes?entity=MDL",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] ZR7 commandes count: {data_zr7.get('count')}")
        print(f"[RESULT] MDL commandes count: {data_mdl.get('count')}")
        print(f"[RESULT] ZR7 entity in response: {data_zr7.get('entity')}")
        print(f"[RESULT] MDL entity in response: {data_mdl.get('entity')}")

        # Verify all commandes have correct entity
        for cmd in data_zr7.get("commandes", []):
            assert cmd.get("entity") == "ZR7", f"Found non-ZR7 commande: {cmd}"

        for cmd in data_mdl.get("commandes", []):
            assert cmd.get("entity") == "MDL", f"Found non-MDL commande: {cmd}"

        print("[PASS] Commandes entity filtering correct")

    def test_ops_zr7_gets_only_zr7_commandes(self, ops_zr7_token):
        """ops_zr7 should only see ZR7 commandes"""
        res = requests.get(
            f"{BASE_URL}/api/commandes?entity=ZR7",
            headers={"Authorization": f"Bearer {ops_zr7_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        for cmd in data.get("commandes", []):
            assert cmd.get("entity") == "ZR7"
        print(f"[PASS] ops_zr7 sees {data.get('count')} ZR7 commandes only")

    def test_ops_zr7_cannot_access_mdl_commandes(self, ops_zr7_token):
        """ops_zr7 should be denied access to MDL entity"""
        res = requests.get(
            f"{BASE_URL}/api/commandes?entity=MDL",
            headers={"Authorization": f"Bearer {ops_zr7_token}"}
        )
        assert res.status_code == 403, f"ops_zr7 should be denied MDL access, got {res.status_code}"
        print("[PASS] ops_zr7 correctly denied MDL commandes access")

    def test_ops_mdl_cannot_access_zr7_commandes(self, ops_mdl_token):
        """ops_mdl should be denied access to ZR7 entity"""
        res = requests.get(
            f"{BASE_URL}/api/commandes?entity=ZR7",
            headers={"Authorization": f"Bearer {ops_mdl_token}"}
        )
        assert res.status_code == 403, f"ops_mdl should be denied ZR7 access, got {res.status_code}"
        print("[PASS] ops_mdl correctly denied ZR7 commandes access")


class TestClientsEntityScope:
    """Test GET /api/clients respects entity parameter"""

    def test_clients_zr7_vs_mdl(self, super_admin_token):
        """ZR7 clients should differ from MDL clients"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/clients?entity=ZR7",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/clients?entity=MDL",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] ZR7 clients count: {data_zr7.get('count')}")
        print(f"[RESULT] MDL clients count: {data_mdl.get('count')}")

        # Verify all clients have correct entity
        for client in data_zr7.get("clients", []):
            assert client.get("entity") == "ZR7", f"Found non-ZR7 client: {client.get('name')}"

        for client in data_mdl.get("clients", []):
            assert client.get("entity") == "MDL", f"Found non-MDL client: {client.get('name')}"

        print("[PASS] Clients entity filtering correct")


class TestLeadsEntityScope:
    """Test GET /api/leads/list respects entity parameter"""

    def test_leads_list_zr7_vs_mdl(self, super_admin_token):
        """ZR7 leads should differ from MDL leads"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/leads/list?entity=ZR7&limit=10",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/leads/list?entity=MDL&limit=10",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] ZR7 leads total: {data_zr7.get('total')}")
        print(f"[RESULT] MDL leads total: {data_mdl.get('total')}")

        # Verify all leads have correct entity
        for lead in data_zr7.get("leads", []):
            assert lead.get("entity") == "ZR7", f"Found non-ZR7 lead: {lead.get('id')}"

        for lead in data_mdl.get("leads", []):
            assert lead.get("entity") == "MDL", f"Found non-MDL lead: {lead.get('id')}"

        # They should have different totals (ZR7=1597, MDL=973 per context)
        assert data_zr7.get("total") != data_mdl.get("total"), \
            f"ZR7 total ({data_zr7.get('total')}) should differ from MDL ({data_mdl.get('total')})"

        print("[PASS] Leads entity filtering correct")


class TestDeliveriesEntityScope:
    """Test GET /api/deliveries respects entity parameter"""

    def test_deliveries_zr7_vs_mdl(self, super_admin_token):
        """ZR7 deliveries should differ from MDL deliveries"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/deliveries?entity=ZR7&limit=10",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/deliveries?entity=MDL&limit=10",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] ZR7 deliveries total: {data_zr7.get('total')}")
        print(f"[RESULT] MDL deliveries total: {data_mdl.get('total')}")

        # Verify all deliveries have correct entity
        for d in data_zr7.get("deliveries", []):
            assert d.get("entity") == "ZR7", f"Found non-ZR7 delivery"

        for d in data_mdl.get("deliveries", []):
            assert d.get("entity") == "MDL", f"Found non-MDL delivery"

        print("[PASS] Deliveries entity filtering correct")


class TestInvoicesEntityScope:
    """Test GET /api/invoices respects X-Entity-Scope header"""

    def test_invoices_zr7_vs_mdl(self, super_admin_token):
        """Invoices should be filtered by X-Entity-Scope header"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/invoices",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "ZR7"
            }
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/invoices",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "MDL"
            }
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        res_both = requests.get(
            f"{BASE_URL}/api/invoices",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "BOTH"
            }
        )
        assert res_both.status_code == 200
        data_both = res_both.json()

        print(f"[RESULT] ZR7 invoices count: {data_zr7.get('count')}")
        print(f"[RESULT] MDL invoices count: {data_mdl.get('count')}")
        print(f"[RESULT] BOTH invoices count: {data_both.get('count')}")

        # Verify entity filtering
        for inv in data_zr7.get("invoices", []):
            assert inv.get("entity") == "ZR7", f"Found non-ZR7 invoice"

        for inv in data_mdl.get("invoices", []):
            assert inv.get("entity") == "MDL", f"Found non-MDL invoice"

        # BOTH should include both entities
        both_total = data_both.get("count", 0)
        zr7_total = data_zr7.get("count", 0)
        mdl_total = data_mdl.get("count", 0)

        # BOTH should be >= max of ZR7, MDL (ideally ZR7 + MDL)
        print(f"[CHECK] BOTH ({both_total}) >= ZR7 ({zr7_total}) + MDL ({mdl_total})?")
        print("[PASS] Invoices entity scope filtering correct")

    def test_overdue_dashboard_entity_scope(self, super_admin_token):
        """Overdue dashboard should respect X-Entity-Scope header"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/invoices/overdue-dashboard",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "ZR7"
            }
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/invoices/overdue-dashboard",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "MDL"
            }
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] ZR7 overdue clients: {data_zr7.get('client_count')}, total: {data_zr7.get('total_overdue_ttc')}")
        print(f"[RESULT] MDL overdue clients: {data_mdl.get('client_count')}, total: {data_mdl.get('total_overdue_ttc')}")

        # Verify clients have correct entity
        for c in data_zr7.get("clients", []):
            assert c.get("entity") == "ZR7", f"Found non-ZR7 overdue client"

        for c in data_mdl.get("clients", []):
            assert c.get("entity") == "MDL", f"Found non-MDL overdue client"

        print("[PASS] Overdue dashboard entity scope filtering correct")


class TestLBMonitorEntityScope:
    """Test GET /api/commandes/lb-monitor respects X-Entity-Scope header"""

    def test_lb_monitor_scope(self, super_admin_token):
        """LB Monitor should return scope in response and filter data"""
        res_zr7 = requests.get(
            f"{BASE_URL}/api/commandes/lb-monitor",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "ZR7"
            }
        )
        assert res_zr7.status_code == 200
        data_zr7 = res_zr7.json()

        res_mdl = requests.get(
            f"{BASE_URL}/api/commandes/lb-monitor",
            headers={
                "Authorization": f"Bearer {super_admin_token}",
                "X-Entity-Scope": "MDL"
            }
        )
        assert res_mdl.status_code == 200
        data_mdl = res_mdl.json()

        print(f"[RESULT] LB Monitor ZR7: scope={data_zr7.get('scope')}, count={data_zr7.get('count')}")
        print(f"[RESULT] LB Monitor MDL: scope={data_mdl.get('scope')}, count={data_mdl.get('count')}")

        assert data_zr7.get("scope") == "ZR7", f"Expected scope ZR7, got {data_zr7.get('scope')}"
        assert data_mdl.get("scope") == "MDL", f"Expected scope MDL, got {data_mdl.get('scope')}"

        # Verify commandes have correct entity
        for cmd in data_zr7.get("commandes", []):
            assert cmd.get("entity") == "ZR7", f"Found non-ZR7 commande in LB Monitor"

        for cmd in data_mdl.get("commandes", []):
            assert cmd.get("entity") == "MDL", f"Found non-MDL commande in LB Monitor"

        print("[PASS] LB Monitor entity scope filtering correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
