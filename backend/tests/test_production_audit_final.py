"""
RDZ CRM - Production Audit Final Tests
Tests for the 12 fixes applied in the Ultimate Production Audit.

Test Categories:
1. Permission Enforcement Tests (viewer_zr7, ops_zr7)
2. Entity Scope Tests (X-Entity-Scope header)
3. System Health Endpoint Test
4. Dashboard Fail-Open Test
5. Intercompany Health/Retry Tests
6. RBAC Entity Isolation Tests
7. Invoice/Billing Dashboard Tests
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
PASSWORD = "RdzTest2026!"


class TestCredentials:
    """Test user credentials"""
    SUPER_ADMIN = "superadmin@test.local"
    ADMIN_ZR7 = "admin_zr7@test.local"
    OPS_ZR7 = "ops_zr7@test.local"
    VIEWER_ZR7 = "viewer_zr7@test.local"
    ADMIN_MDL = "admin_mdl@test.local"
    OPS_MDL = "ops_mdl@test.local"
    VIEWER_MDL = "viewer_mdl@test.local"


@pytest.fixture(scope="module")
def tokens():
    """Get auth tokens for all test users"""
    users = {
        "super_admin": TestCredentials.SUPER_ADMIN,
        "admin_zr7": TestCredentials.ADMIN_ZR7,
        "ops_zr7": TestCredentials.OPS_ZR7,
        "viewer_zr7": TestCredentials.VIEWER_ZR7,
        "admin_mdl": TestCredentials.ADMIN_MDL,
        "ops_mdl": TestCredentials.OPS_MDL,
        "viewer_mdl": TestCredentials.VIEWER_MDL,
    }
    
    result = {}
    for key, email in users.items():
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": PASSWORD}
        )
        if response.status_code == 200:
            result[key] = response.json().get("token")
        else:
            print(f"WARNING: Failed to login as {email}: {response.status_code}")
            result[key] = None
    
    return result


def auth_header(token):
    """Generate auth header"""
    return {"Authorization": f"Bearer {token}"} if token else {}


# ============================================================================
# 1. PERMISSION ENFORCEMENT TESTS
# ============================================================================

class TestViewerPermissions:
    """viewer_zr7 should get 403 on protected endpoints"""
    
    def test_viewer_blocked_from_settings(self, tokens):
        """viewer_zr7 should get 403 on /api/settings"""
        token = tokens.get("viewer_zr7")
        if not token:
            pytest.skip("viewer_zr7 token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/settings",
            headers=auth_header(token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: viewer_zr7 blocked from /api/settings (403)")
    
    def test_viewer_blocked_from_providers(self, tokens):
        """viewer_zr7 should get 403 on /api/providers"""
        token = tokens.get("viewer_zr7")
        if not token:
            pytest.skip("viewer_zr7 token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/providers",
            headers=auth_header(token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: viewer_zr7 blocked from /api/providers (403)")
    
    def test_viewer_blocked_from_users(self, tokens):
        """viewer_zr7 should get 403 on /api/auth/users"""
        token = tokens.get("viewer_zr7")
        if not token:
            pytest.skip("viewer_zr7 token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers=auth_header(token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: viewer_zr7 blocked from /api/auth/users (403)")
    
    def test_viewer_blocked_from_event_log(self, tokens):
        """viewer_zr7 should get 403 on /api/event-log"""
        token = tokens.get("viewer_zr7")
        if not token:
            pytest.skip("viewer_zr7 token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/event-log",
            headers=auth_header(token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: viewer_zr7 blocked from /api/event-log (403)")


class TestOpsPermissions:
    """ops_zr7 should get 403 on billing write operations"""
    
    def test_ops_blocked_from_billing_write(self, tokens):
        """ops_zr7 should get 403 on PUT /api/billing/transfer-pricing"""
        token = tokens.get("ops_zr7")
        if not token:
            pytest.skip("ops_zr7 token not available")
        
        response = requests.put(
            f"{BASE_URL}/api/billing/transfer-pricing",
            headers=auth_header(token),
            json={
                "from_entity": "ZR7",
                "to_entity": "MDL",
                "product_code": "PV",
                "unit_price_ht": 10.0
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: ops_zr7 blocked from PUT /api/billing/transfer-pricing (403)")


class TestNoAuthProtection:
    """Endpoints require authentication"""
    
    def test_no_auth_blocked_from_leads_list(self):
        """No auth should get 401 on /api/leads/list"""
        response = requests.get(f"{BASE_URL}/api/leads/list")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASS: No auth blocked from /api/leads/list (401)")


# ============================================================================
# 2. ENTITY SCOPE TESTS
# ============================================================================

class TestEntityScope:
    """Entity scope filtering via X-Entity-Scope header"""
    
    def test_super_admin_leads_stats_zr7_scope(self, tokens):
        """super_admin with X-Entity-Scope:ZR7 on /api/leads/stats should return scoped data"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/stats",
            headers={**auth_header(token), "X-Entity-Scope": "ZR7"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: /api/leads/stats with X-Entity-Scope:ZR7 returned data: {data}")
    
    def test_super_admin_deliveries_stats_mdl_scope(self, tokens):
        """super_admin with X-Entity-Scope:MDL on /api/deliveries/stats should return scoped data"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/deliveries/stats",
            headers={**auth_header(token), "X-Entity-Scope": "MDL"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: /api/deliveries/stats with X-Entity-Scope:MDL returned data: {data}")


# ============================================================================
# 3. SYSTEM HEALTH ENDPOINT TEST
# ============================================================================

class TestSystemHealth:
    """System health endpoint"""
    
    def test_system_health_returns_modules(self, tokens):
        """GET /api/system/health should return health status with modules"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/system/health",
            headers=auth_header(token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required keys
        assert "status" in data, "Response should contain 'status' key"
        assert "modules" in data, "Response should contain 'modules' key"
        assert "timestamp" in data, "Response should contain 'timestamp' key"
        
        # Verify modules structure
        modules = data["modules"]
        expected_modules = ["cron", "deliveries", "intercompany", "invoices"]
        for mod in expected_modules:
            assert mod in modules, f"modules should contain '{mod}'"
            assert "status" in modules[mod], f"modules.{mod} should contain 'status'"
        
        print(f"PASS: /api/system/health returned status: {data['status']}")
        print(f"  Modules: {list(modules.keys())}")


# ============================================================================
# 4. DASHBOARD FAIL-OPEN TEST
# ============================================================================

class TestDashboardFailOpen:
    """Dashboard stats fail-open behavior"""
    
    def test_dashboard_stats_future_week_no_crash(self, tokens):
        """GET /api/leads/dashboard-stats with future week should return all keys without crash"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        # Use a far future week to test fail-open
        response = requests.get(
            f"{BASE_URL}/api/leads/dashboard-stats",
            headers=auth_header(token),
            params={"week": "2030-W01"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return expected keys even for empty/future week
        expected_keys = ["lead_stats", "delivery_stats", "calendar", "top_clients_7d", 
                        "problem_clients", "low_quota_commandes", "blocked_stock"]
        for key in expected_keys:
            assert key in data, f"Response should contain '{key}' key"
        
        print(f"PASS: dashboard-stats with future week returned all keys: {list(data.keys())}")


# ============================================================================
# 5. INTERCOMPANY HEALTH/RETRY TESTS
# ============================================================================

class TestIntercompanyHealth:
    """Intercompany health and retry endpoints"""
    
    def test_intercompany_health_returns_status(self, tokens):
        """GET /api/intercompany/health should return status"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/intercompany/health",
            headers=auth_header(token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "status" in data, "Response should contain 'status' key"
        assert "transfers" in data, "Response should contain 'transfers' key"
        
        transfers = data["transfers"]
        assert "total" in transfers, "transfers should contain 'total'"
        assert "pending" in transfers, "transfers should contain 'pending'"
        assert "error" in transfers, "transfers should contain 'error'"
        
        print(f"PASS: /api/intercompany/health returned status: {data['status']}")
        print(f"  Transfers: {transfers}")
    
    def test_intercompany_retry_errors_works(self, tokens):
        """POST /api/intercompany/retry-errors should work without errors"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.post(
            f"{BASE_URL}/api/intercompany/retry-errors",
            headers=auth_header(token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return retry stats
        assert "retried" in data, "Response should contain 'retried' key"
        
        print(f"PASS: /api/intercompany/retry-errors worked. Retried: {data.get('retried', 0)}")


# ============================================================================
# 6. RBAC ENTITY ISOLATION TESTS
# ============================================================================

class TestRBACEntityIsolation:
    """RBAC entity isolation - admin_mdl should NOT see ZR7 data"""
    
    def test_admin_mdl_cannot_access_zr7_clients(self, tokens):
        """admin_mdl should NOT see ZR7 data when listing clients with entity=ZR7"""
        token = tokens.get("admin_mdl")
        if not token:
            pytest.skip("admin_mdl token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=auth_header(token),
            params={"entity": "ZR7"}
        )
        # Should either get 403 OR get empty results for ZR7 if filtered
        if response.status_code == 403:
            print("PASS: admin_mdl blocked from ZR7 clients (403)")
        elif response.status_code == 200:
            data = response.json()
            clients = data.get("clients", [])
            # If allowed to query, should only return MDL clients (empty for ZR7 filter)
            # or the endpoint should filter to user's entity
            zr7_clients = [c for c in clients if c.get("entity") == "ZR7"]
            if len(zr7_clients) == 0:
                print(f"PASS: admin_mdl got 0 ZR7 clients (filtered correctly)")
            else:
                pytest.fail(f"admin_mdl could see {len(zr7_clients)} ZR7 clients - entity isolation broken")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


# ============================================================================
# 7. INVOICE/BILLING DASHBOARD TESTS
# ============================================================================

class TestInvoiceDashboard:
    """Invoice overdue dashboard"""
    
    def test_invoice_overdue_dashboard_works(self, tokens):
        """GET /api/invoices/overdue-dashboard should work"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/invoices/overdue-dashboard",
            headers=auth_header(token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return expected keys
        assert "clients" in data, "Response should contain 'clients' key"
        assert "total_overdue_ttc" in data, "Response should contain 'total_overdue_ttc' key"
        
        print(f"PASS: /api/invoices/overdue-dashboard returned {len(data.get('clients', []))} clients")


class TestBillingWeek:
    """Billing week dashboard"""
    
    def test_billing_week_dashboard_works(self, tokens):
        """GET /api/billing/week should work"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/billing/week",
            headers=auth_header(token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return expected keys
        assert "week_key" in data, "Response should contain 'week_key' key"
        assert "summary" in data, "Response should contain 'summary' key"
        
        print(f"PASS: /api/billing/week returned data for week: {data.get('week_key')}")
        print(f"  Summary: {data.get('summary', {})}")


# ============================================================================
# SUMMARY TEST - RUN ALL
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
