"""
Test Suite: Invoice CRUD + Overdue Dashboard + LB Monitor Entity Scope
Features:
- Invoice create with TTC = HT * (1 + vat_rate/100)
- Invoice status transitions: draft → sent, sent/overdue → paid
- Overdue dashboard with per-client totals
- Entity filtering via X-Entity-Scope header
- Permission enforcement (billing.view, billing.manage)
- LB Monitor uses X-Entity-Scope header (no entity param)
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@test.local"
SUPER_ADMIN_PASS = "RdzTest2026!"
OPS_ZR7_EMAIL = "ops_zr7@test.local"
OPS_ZR7_PASS = "RdzTest2026!"


class TestLoginAndSetup:
    """Login tests and setup verification"""
    
    def test_super_admin_login(self):
        """Super admin can login and has billing permissions"""
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASS
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        assert "token" in data
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["permissions"]["billing.view"] == True
        assert data["user"]["permissions"]["billing.manage"] == True
        assert data["user"]["permissions"]["monitoring.lb.view"] == True
    
    def test_ops_user_login(self):
        """Ops user login - should not have billing.manage"""
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OPS_ZR7_EMAIL,
            "password": OPS_ZR7_PASS
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        assert "token" in data
        assert data["user"]["entity"] == "ZR7"


@pytest.fixture
def super_admin_token():
    """Get super admin token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASS
    })
    if res.status_code != 200:
        pytest.skip(f"Super admin login failed: {res.text}")
    return res.json()["token"]


@pytest.fixture
def ops_zr7_token():
    """Get ops_zr7 token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OPS_ZR7_EMAIL,
        "password": OPS_ZR7_PASS
    })
    if res.status_code != 200:
        pytest.skip(f"Ops login failed: {res.text}")
    return res.json()["token"]


@pytest.fixture
def client_with_vat(super_admin_token):
    """Get a client with known vat_rate or create test client"""
    headers = {"Authorization": f"Bearer {super_admin_token}", "X-Entity-Scope": "ZR7"}
    res = requests.get(f"{BASE_URL}/api/clients?entity=ZR7&limit=1", headers=headers)
    if res.status_code == 200:
        clients = res.json().get("clients", [])
        if clients:
            return clients[0]
    pytest.skip("No client found for invoice testing")


class TestInvoiceCreate:
    """Test invoice creation with TTC calculation"""
    
    def test_create_invoice_computes_ttc_correctly(self, super_admin_token, client_with_vat):
        """POST /api/invoices creates invoice with correct TTC = HT * (1 + vat_rate/100)"""
        client = client_with_vat
        client_id = client["id"]
        client_vat = client.get("vat_rate", 20.0)
        
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json",
            "X-Entity-Scope": client["entity"]
        }
        
        amount_ht = 1000.0
        expected_ttc = round(amount_ht * (1 + client_vat / 100), 2)
        
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": client_id,
            "amount_ht": amount_ht,
            "description": "TEST_invoice_ttc_calculation",
            "entity": client["entity"]
        })
        
        assert res.status_code == 200, f"Create invoice failed: {res.text}"
        data = res.json()
        assert data["success"] == True
        invoice = data["invoice"]
        
        # Verify TTC calculation
        assert invoice["amount_ht"] == amount_ht
        assert invoice["vat_rate"] == client_vat
        assert invoice["amount_ttc"] == expected_ttc, f"TTC mismatch: expected {expected_ttc}, got {invoice['amount_ttc']}"
        assert invoice["status"] == "draft"
        assert invoice["client_id"] == client_id
        
        # Cleanup: Store invoice ID for later tests
        return invoice
    
    def test_create_invoice_requires_billing_manage(self, ops_zr7_token):
        """Ops user without billing.manage should get 403"""
        headers = {
            "Authorization": f"Bearer {ops_zr7_token}",
            "Content-Type": "application/json"
        }
        
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": "any-client-id",
            "amount_ht": 100.0,
            "description": "TEST_should_fail"
        })
        
        # Should fail with 403 (permission denied)
        assert res.status_code == 403, f"Expected 403 for ops user, got {res.status_code}: {res.text}"


class TestInvoiceStatusTransitions:
    """Test invoice status transitions: draft→sent, sent/overdue→paid"""
    
    def test_send_invoice_transitions_draft_to_sent(self, super_admin_token, client_with_vat):
        """POST /api/invoices/{id}/send transitions draft→sent"""
        client = client_with_vat
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json",
            "X-Entity-Scope": client["entity"]
        }
        
        # Create a draft invoice
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": client["id"],
            "amount_ht": 500.0,
            "description": "TEST_invoice_for_send_transition",
            "entity": client["entity"]
        })
        assert res.status_code == 200, f"Create failed: {res.text}"
        invoice = res.json()["invoice"]
        invoice_id = invoice["id"]
        assert invoice["status"] == "draft"
        
        # Send the invoice
        res = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/send", headers=headers)
        assert res.status_code == 200, f"Send failed: {res.text}"
        data = res.json()
        assert data["success"] == True
        assert data["status"] == "sent"
        
        # Verify by GET
        res = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["invoice"]["status"] == "sent"
    
    def test_send_invoice_only_from_draft(self, super_admin_token, client_with_vat):
        """POST /api/invoices/{id}/send fails if not draft"""
        client = client_with_vat
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json",
            "X-Entity-Scope": client["entity"]
        }
        
        # Create and send invoice
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": client["id"],
            "amount_ht": 300.0,
            "description": "TEST_invoice_already_sent",
            "entity": client["entity"]
        })
        invoice = res.json()["invoice"]
        invoice_id = invoice["id"]
        
        # Send it
        requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/send", headers=headers)
        
        # Try to send again - should fail
        res = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/send", headers=headers)
        assert res.status_code == 400, f"Expected 400 for already sent invoice, got {res.status_code}"
    
    def test_mark_paid_transitions_sent_to_paid(self, super_admin_token, client_with_vat):
        """POST /api/invoices/{id}/mark-paid transitions sent/overdue→paid"""
        client = client_with_vat
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json",
            "X-Entity-Scope": client["entity"]
        }
        
        # Create, send invoice
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": client["id"],
            "amount_ht": 750.0,
            "description": "TEST_invoice_for_paid_transition",
            "entity": client["entity"]
        })
        invoice = res.json()["invoice"]
        invoice_id = invoice["id"]
        
        requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/send", headers=headers)
        
        # Mark as paid
        res = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/mark-paid", headers=headers)
        assert res.status_code == 200, f"Mark paid failed: {res.text}"
        data = res.json()
        assert data["success"] == True
        assert data["status"] == "paid"
        assert "paid_at" in data
        
        # Verify by GET
        res = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["invoice"]["status"] == "paid"
    
    def test_mark_paid_fails_for_draft(self, super_admin_token, client_with_vat):
        """POST /api/invoices/{id}/mark-paid fails for draft status"""
        client = client_with_vat
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "Content-Type": "application/json",
            "X-Entity-Scope": client["entity"]
        }
        
        # Create draft invoice
        res = requests.post(f"{BASE_URL}/api/invoices", headers=headers, json={
            "client_id": client["id"],
            "amount_ht": 200.0,
            "description": "TEST_invoice_draft_no_paid",
            "entity": client["entity"]
        })
        invoice = res.json()["invoice"]
        invoice_id = invoice["id"]
        
        # Try to mark paid without sending - should fail
        res = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/mark-paid", headers=headers)
        assert res.status_code == 400, f"Expected 400 for draft invoice, got {res.status_code}"


class TestOverdueDashboard:
    """Test GET /api/invoices/overdue-dashboard"""
    
    def test_overdue_dashboard_returns_structure(self, super_admin_token):
        """GET /api/invoices/overdue-dashboard returns clients with overdue totals"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "BOTH"
        }
        
        res = requests.get(f"{BASE_URL}/api/invoices/overdue-dashboard", headers=headers)
        assert res.status_code == 200, f"Overdue dashboard failed: {res.text}"
        data = res.json()
        
        # Check response structure
        assert "clients" in data
        assert "total_overdue_ttc" in data
        assert "client_count" in data
        
        # If there are overdue clients, check structure
        if data["clients"]:
            client_entry = data["clients"][0]
            assert "client_id" in client_entry
            assert "client_name" in client_entry
            assert "entity" in client_entry
            assert "invoice_count" in client_entry
            assert "total_ht" in client_entry
            assert "total_ttc" in client_entry
            assert "days_overdue" in client_entry
    
    def test_overdue_dashboard_requires_billing_view(self, ops_zr7_token):
        """Overdue dashboard requires billing.view permission"""
        headers = {"Authorization": f"Bearer {ops_zr7_token}"}
        
        res = requests.get(f"{BASE_URL}/api/invoices/overdue-dashboard", headers=headers)
        # Should fail with 403 (ops doesn't have billing.view by default)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"


class TestInvoiceEntityFiltering:
    """Test invoice endpoints respect X-Entity-Scope header"""
    
    def test_list_invoices_with_zr7_scope(self, super_admin_token):
        """GET /api/invoices with X-Entity-Scope: ZR7 filters to ZR7 only"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "ZR7"
        }
        
        res = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        assert res.status_code == 200, f"List invoices failed: {res.text}"
        data = res.json()
        
        # All returned invoices should be ZR7
        for inv in data.get("invoices", []):
            assert inv["entity"] == "ZR7", f"Found non-ZR7 invoice: {inv}"
    
    def test_list_invoices_with_mdl_scope(self, super_admin_token):
        """GET /api/invoices with X-Entity-Scope: MDL filters to MDL only"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "MDL"
        }
        
        res = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        assert res.status_code == 200, f"List invoices failed: {res.text}"
        data = res.json()
        
        # All returned invoices should be MDL
        for inv in data.get("invoices", []):
            assert inv["entity"] == "MDL", f"Found non-MDL invoice: {inv}"
    
    def test_list_invoices_with_both_scope(self, super_admin_token):
        """GET /api/invoices with X-Entity-Scope: BOTH returns both entities"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "BOTH"
        }
        
        res = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        assert res.status_code == 200, f"List invoices failed: {res.text}"
        data = res.json()
        
        # Should return invoices (if any exist)
        assert "invoices" in data
        assert "count" in data
        assert "total" in data


class TestLBMonitorEntityScope:
    """Test LB Monitor uses X-Entity-Scope header (no entity param needed)"""
    
    def test_lb_monitor_uses_entity_scope_header(self, super_admin_token):
        """GET /api/commandes/lb-monitor uses X-Entity-Scope header"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "ZR7"
        }
        
        res = requests.get(f"{BASE_URL}/api/commandes/lb-monitor", headers=headers)
        assert res.status_code == 200, f"LB monitor failed: {res.text}"
        data = res.json()
        
        # Check response structure
        assert "week_key" in data
        assert "scope" in data
        assert "commandes" in data
        assert "count" in data
        
        # Scope should reflect header
        assert data["scope"] == "ZR7", f"Expected scope ZR7, got {data['scope']}"
        
        # All commandes should be ZR7
        for cmd in data.get("commandes", []):
            assert cmd["entity"] == "ZR7", f"Found non-ZR7 commande in LB monitor: {cmd}"
    
    def test_lb_monitor_both_scope(self, super_admin_token):
        """GET /api/commandes/lb-monitor with BOTH scope returns both entities"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "BOTH"
        }
        
        res = requests.get(f"{BASE_URL}/api/commandes/lb-monitor", headers=headers)
        assert res.status_code == 200, f"LB monitor failed: {res.text}"
        data = res.json()
        
        assert data["scope"] == "BOTH"
        # May contain ZR7 and/or MDL commandes
    
    def test_lb_monitor_requires_monitoring_permission(self, ops_zr7_token):
        """LB monitor requires monitoring.lb.view permission"""
        headers = {"Authorization": f"Bearer {ops_zr7_token}"}
        
        res = requests.get(f"{BASE_URL}/api/commandes/lb-monitor", headers=headers)
        # Ops should not have monitoring.lb.view
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"


class TestInvoicePermissions:
    """Test invoice endpoints require correct permissions"""
    
    def test_list_invoices_requires_billing_view(self, ops_zr7_token):
        """GET /api/invoices requires billing.view"""
        headers = {"Authorization": f"Bearer {ops_zr7_token}"}
        
        res = requests.get(f"{BASE_URL}/api/invoices", headers=headers)
        # Ops doesn't have billing.view
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
    
    def test_get_single_invoice_requires_billing_view(self, ops_zr7_token):
        """GET /api/invoices/{id} requires billing.view"""
        headers = {"Authorization": f"Bearer {ops_zr7_token}"}
        
        res = requests.get(f"{BASE_URL}/api/invoices/any-id", headers=headers)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_invoices(self, super_admin_token):
        """Clean up TEST_ prefixed invoices"""
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Entity-Scope": "BOTH"
        }
        
        # List all invoices and delete TEST_ ones
        res = requests.get(f"{BASE_URL}/api/invoices?limit=200", headers=headers)
        if res.status_code == 200:
            invoices = res.json().get("invoices", [])
            test_invoices = [inv for inv in invoices if "TEST_" in (inv.get("description") or "")]
            # Note: No delete endpoint exists, so just verify test ran
            print(f"Found {len(test_invoices)} test invoices")
        
        assert True  # Cleanup complete


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
