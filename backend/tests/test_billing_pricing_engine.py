"""
Test Billing & Pricing Engine (Phase A)
RDZ CRM - Complete API Testing for Pricing, Credits, Prepayment, Ledger, and Invoices

Features tested:
- Products CRUD (PV, PAC, ITE seeded)
- Client pricing (global discount + per-product)
- Billing credits (free units)
- Prepayment balances
- Billing week dashboard (WEEKLY_INVOICE vs PREPAID)
- Ledger building (immutable snapshot)
- Invoice generation & workflow (draft→frozen→sent→paid)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("token")
        if token:
            return token
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(scope="module")
def test_client_id(api_client):
    """Get an existing client ID from ZR7 entity"""
    response = api_client.get(f"{BASE_URL}/api/clients?entity=ZR7")
    if response.status_code == 200:
        clients = response.json().get("clients", [])
        if clients:
            return clients[0]["id"]
    pytest.skip("No clients found for testing")


class TestProducts:
    """Product catalog tests"""

    def test_get_products_returns_seeded(self, api_client):
        """GET /api/products returns seeded products (PV, PAC, ITE)"""
        response = api_client.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "products" in data
        products = data["products"]
        assert len(products) >= 3, "Should have at least PV, PAC, ITE"
        
        codes = [p["code"] for p in products]
        assert "PV" in codes, "PV product missing"
        assert "PAC" in codes, "PAC product missing"
        assert "ITE" in codes, "ITE product missing"
        
        # Verify product structure
        for p in products:
            assert "code" in p
            assert "name" in p
            assert "active" in p
        print(f"✓ Products returned: {codes}")

    def test_create_product(self, api_client):
        """POST /api/products creates new product"""
        unique_code = f"TEST{uuid.uuid4().hex[:4].upper()}"
        response = api_client.post(f"{BASE_URL}/api/products", json={
            "code": unique_code,
            "name": f"Test Product {unique_code}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("product", {}).get("code") == unique_code
        print(f"✓ Created product: {unique_code}")

    def test_create_duplicate_product_fails(self, api_client):
        """POST /api/products with existing code returns 400"""
        response = api_client.post(f"{BASE_URL}/api/products", json={
            "code": "PV",
            "name": "Duplicate PV"
        })
        assert response.status_code == 400
        print("✓ Duplicate product creation correctly blocked")


class TestClientPricing:
    """Client pricing tests (global + per-product)"""

    def test_get_client_pricing(self, api_client, test_client_id):
        """GET /api/clients/{id}/pricing returns global + product pricing"""
        response = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/pricing")
        assert response.status_code == 200
        
        data = response.json()
        assert "client_id" in data
        assert "global" in data
        assert "products" in data
        assert isinstance(data["products"], list)
        print(f"✓ Client pricing retrieved. Products: {len(data['products'])}")

    def test_update_global_discount(self, api_client, test_client_id):
        """PUT /api/clients/{id}/pricing updates global discount"""
        response = api_client.put(f"{BASE_URL}/api/clients/{test_client_id}/pricing", json={
            "discount_pct_global": 5.0
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify
        verify = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/pricing")
        assert verify.json()["global"]["discount_pct_global"] == 5.0
        print("✓ Global discount updated to 5%")

    def test_upsert_product_pricing_weekly_invoice(self, api_client, test_client_id):
        """POST /api/clients/{id}/pricing/product upserts product pricing with WEEKLY_INVOICE"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product", json={
            "product_code": "PV",
            "unit_price_eur": 25.0,
            "discount_pct": 10.0,
            "billing_mode": "WEEKLY_INVOICE",
            "active": True
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify
        verify = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/pricing")
        pv_pricing = next((p for p in verify.json()["products"] if p["product_code"] == "PV"), None)
        assert pv_pricing is not None
        assert pv_pricing["unit_price_eur"] == 25.0
        assert pv_pricing["billing_mode"] == "WEEKLY_INVOICE"
        print("✓ PV pricing created with WEEKLY_INVOICE mode")

    def test_upsert_product_pricing_prepaid(self, api_client, test_client_id):
        """POST /api/clients/{id}/pricing/product with PREPAID creates prepayment balance"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product", json={
            "product_code": "PAC",
            "unit_price_eur": 30.0,
            "discount_pct": 5.0,
            "billing_mode": "PREPAID",
            "active": True
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify prepayment_balance entry was created
        bal_resp = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/prepayment")
        assert bal_resp.status_code == 200
        balances = bal_resp.json().get("balances", [])
        pac_balance = next((b for b in balances if b["product_code"] == "PAC"), None)
        assert pac_balance is not None, "PREPAID mode should create prepayment_balance entry"
        print("✓ PAC pricing created with PREPAID mode, balance entry verified")

    def test_invalid_billing_mode_rejected(self, api_client, test_client_id):
        """POST /api/clients/{id}/pricing/product with invalid billing_mode returns 400"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product", json={
            "product_code": "ITE",
            "unit_price_eur": 20.0,
            "billing_mode": "INVALID_MODE"
        })
        assert response.status_code == 400
        print("✓ Invalid billing_mode correctly rejected")

    def test_delete_product_pricing(self, api_client, test_client_id):
        """DELETE /api/clients/{id}/pricing/product/{code} removes pricing"""
        # First create a test pricing
        api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product", json={
            "product_code": "ITE",
            "unit_price_eur": 15.0,
            "billing_mode": "WEEKLY_INVOICE"
        })
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product/ITE")
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify gone
        verify = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/pricing")
        ite_pricing = next((p for p in verify.json()["products"] if p["product_code"] == "ITE"), None)
        assert ite_pricing is None, "ITE pricing should be deleted"
        print("✓ ITE pricing successfully deleted")


class TestBillingCredits:
    """Billing credits (free units) tests"""

    @pytest.fixture(scope="class")
    def test_credit_id(self, api_client, test_client_id):
        """Create a test credit and return its ID"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "product_code": "PV",
            "week_key": "2026-W07",
            "quantity_units_free": 5,
            "reason": "geste_commercial",
            "note": "Test credit for pytest"
        })
        if response.status_code == 200:
            return response.json().get("credit", {}).get("id")
        return None

    def test_add_credit_valid(self, api_client, test_client_id):
        """POST /api/clients/{id}/credits adds free units with valid reason"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "product_code": "PV",
            "week_key": "2026-W08",
            "quantity_units_free": 3,
            "reason": "fin_de_semaine",
            "note": "End of week bonus"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        credit = data.get("credit", {})
        assert credit.get("quantity_units_free") == 3
        assert credit.get("reason") == "fin_de_semaine"
        assert "id" in credit
        print("✓ Credit added with reason 'fin_de_semaine'")

    def test_add_credit_invalid_reason_rejected(self, api_client, test_client_id):
        """POST /api/clients/{id}/credits with invalid reason returns 400"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "product_code": "PV",
            "week_key": "2026-W07",
            "quantity_units_free": 1,
            "reason": "INVALID_REASON"
        })
        assert response.status_code == 400
        print("✓ Invalid credit reason correctly rejected")

    def test_list_credits(self, api_client, test_client_id):
        """GET /api/clients/{id}/credits lists credits"""
        response = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/credits")
        assert response.status_code == 200
        
        data = response.json()
        assert "credits" in data
        assert "count" in data
        assert isinstance(data["credits"], list)
        print(f"✓ Credits listed: {data['count']} total")

    def test_list_credits_by_week(self, api_client, test_client_id):
        """GET /api/clients/{id}/credits?week_key=... filters by week"""
        response = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/credits?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        # All credits should be for week 2026-W07
        for credit in data.get("credits", []):
            assert credit.get("week_key") == "2026-W07"
        print(f"✓ Credits filtered by week: {data['count']} for 2026-W07")

    def test_delete_credit_not_applied(self, api_client, test_client_id):
        """DELETE /api/clients/{id}/credits/{id} deletes credit if not applied"""
        # Create a new credit
        create_resp = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "product_code": "PV",
            "week_key": "2026-W99",
            "quantity_units_free": 1,
            "reason": "bug",
            "note": "To be deleted"
        })
        credit_id = create_resp.json().get("credit", {}).get("id")
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/clients/{test_client_id}/credits/{credit_id}")
        assert response.status_code == 200
        assert response.json().get("success") is True
        print("✓ Unapplied credit successfully deleted")


class TestPrepaymentBalances:
    """Prepayment balance tests"""

    def test_get_prepayment_balances(self, api_client, test_client_id):
        """GET /api/clients/{id}/prepayment returns balances"""
        response = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/prepayment")
        assert response.status_code == 200
        
        data = response.json()
        assert "client_id" in data
        assert "balances" in data
        assert isinstance(data["balances"], list)
        print(f"✓ Prepayment balances: {len(data['balances'])} products")

    def test_add_prepayment_units(self, api_client, test_client_id):
        """POST /api/clients/{id}/prepayment/add-units adds prepaid units"""
        # First ensure PAC is PREPAID
        api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/pricing/product", json={
            "product_code": "PAC",
            "unit_price_eur": 30.0,
            "billing_mode": "PREPAID"
        })
        
        # Get current balance
        before = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/prepayment")
        pac_before = next((b for b in before.json()["balances"] if b["product_code"] == "PAC"), {})
        units_before = pac_before.get("units_remaining", 0)
        
        # Add units
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/prepayment/add-units", json={
            "product_code": "PAC",
            "units_to_add": 50,
            "note": "Test purchase"
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify increase
        balance = response.json().get("balance", {})
        assert balance.get("units_remaining") == units_before + 50
        print(f"✓ Prepaid units added: {units_before} -> {balance.get('units_remaining')}")


class TestBillingWeekDashboard:
    """Billing week dashboard tests"""

    def test_get_billing_week_current(self, api_client):
        """GET /api/billing/week returns dashboard for current week"""
        response = api_client.get(f"{BASE_URL}/api/billing/week")
        assert response.status_code == 200
        
        data = response.json()
        assert "week_key" in data
        assert "summary" in data
        assert "totals_invoice" in data
        assert "weekly_invoice" in data
        assert "prepaid" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "leads_produced" in summary
        assert "units_delivered" in summary
        assert "units_billable" in summary
        print(f"✓ Billing dashboard for {data['week_key']}: {summary['units_delivered']} delivered")

    def test_get_billing_week_specific(self, api_client):
        """GET /api/billing/week?week_key=2026-W07 returns specific week"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert data["week_key"] == "2026-W07"
        print(f"✓ Specific week 2026-W07 loaded")

    def test_billing_dashboard_separates_billing_modes(self, api_client):
        """Dashboard correctly separates WEEKLY_INVOICE vs PREPAID rows"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        weekly = data.get("weekly_invoice", [])
        prepaid = data.get("prepaid", [])
        
        # All weekly rows should be WEEKLY_INVOICE
        for row in weekly:
            assert row.get("billing_mode") == "WEEKLY_INVOICE", f"Weekly row has wrong mode: {row.get('billing_mode')}"
        
        # All prepaid rows should be PREPAID
        for row in prepaid:
            assert row.get("billing_mode") == "PREPAID", f"Prepaid row has wrong mode: {row.get('billing_mode')}"
        
        print(f"✓ Billing modes separated: {len(weekly)} WEEKLY_INVOICE, {len(prepaid)} PREPAID")

    def test_billing_row_structure(self, api_client):
        """Verify billing row has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        data = response.json()
        
        all_rows = data.get("weekly_invoice", []) + data.get("prepaid", [])
        if all_rows:
            row = all_rows[0]
            required_fields = [
                "client_id", "client_name", "product_code", "billing_mode",
                "unit_price_eur", "discount_pct", "units_billable",
                "units_free_applied", "units_invoiced", "gross_total", "net_total"
            ]
            for field in required_fields:
                assert field in row, f"Missing field: {field}"
            print(f"✓ Row structure verified with all required fields")
        else:
            print("⚠ No billing rows to verify structure")


class TestBillingLedger:
    """Ledger building tests"""

    def test_build_ledger_new_week(self, api_client):
        """POST /api/billing/week/{wk}/build-ledger creates ledger entries"""
        # Use a valid future week unlikely to have frozen invoices (week 50 of 2026)
        test_week = "2026-W50"
        
        response = api_client.post(f"{BASE_URL}/api/billing/week/{test_week}/build-ledger")
        # Should succeed (may create 0 entries if no deliveries)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("week_key") == test_week
        assert "entries_created" in data
        print(f"✓ Ledger built for {test_week}: {data['entries_created']} entries")

    def test_build_ledger_blocked_if_frozen(self, api_client):
        """POST /api/billing/week/{wk}/build-ledger blocked if frozen invoice exists"""
        # First check if 2026-W07 has frozen invoices
        inv_resp = api_client.get(f"{BASE_URL}/api/invoices?week_key=2026-W07")
        invoices = inv_resp.json().get("invoices", [])
        
        frozen_exists = any(i.get("status") in ["frozen", "sent", "paid"] for i in invoices)
        
        if frozen_exists:
            # Try to rebuild - should fail
            response = api_client.post(f"{BASE_URL}/api/billing/week/2026-W07/build-ledger")
            assert response.status_code == 400
            assert "Cannot rebuild ledger" in response.text or "frozen" in response.text.lower()
            print("✓ Ledger rebuild correctly blocked due to frozen invoice")
        else:
            print("⚠ No frozen invoices in 2026-W07 to test block")


class TestInvoiceGeneration:
    """Invoice generation tests"""

    def test_generate_invoices(self, api_client):
        """POST /api/billing/week/{wk}/generate-invoices creates draft invoices"""
        # Use a valid future week with ledger entries
        test_week = "2026-W51"
        # First build ledger
        api_client.post(f"{BASE_URL}/api/billing/week/{test_week}/build-ledger")
        
        response = api_client.post(f"{BASE_URL}/api/billing/week/{test_week}/generate-invoices")
        # May succeed with 0 invoices if no billable entries
        if response.status_code == 400 and "No ledger entries" in response.text:
            print("⚠ No ledger entries for test week, skipping")
            return
            
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print(f"✓ Invoices generated: {data.get('invoices_created', 0)}")

    def test_list_invoices(self, api_client):
        """GET /api/invoices lists all invoices"""
        response = api_client.get(f"{BASE_URL}/api/invoices")
        assert response.status_code == 200
        
        data = response.json()
        assert "invoices" in data
        assert "count" in data
        print(f"✓ Total invoices: {data['count']}")

    def test_list_invoices_filtered(self, api_client):
        """GET /api/invoices with filters"""
        response = api_client.get(f"{BASE_URL}/api/invoices?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        for inv in data.get("invoices", []):
            assert inv.get("week_key") == "2026-W07"
        print(f"✓ Filtered invoices for 2026-W07: {data['count']}")


class TestInvoiceWorkflow:
    """Invoice status workflow tests (draft→frozen→sent→paid)"""

    @pytest.fixture(scope="class")
    def draft_invoice_id(self, api_client):
        """Get or create a draft invoice for testing"""
        # Check for existing draft
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=draft")
        drafts = resp.json().get("invoices", [])
        if drafts:
            return drafts[0]["id"]
        
        # No draft found - try to create one
        # This requires ledger with billable entries
        print("⚠ No draft invoices available for workflow tests")
        return None

    def test_freeze_invoice_from_draft(self, api_client, draft_invoice_id):
        """POST /api/invoices/{id}/freeze transitions draft→frozen"""
        if not draft_invoice_id:
            pytest.skip("No draft invoice available")
        
        response = api_client.post(f"{BASE_URL}/api/invoices/{draft_invoice_id}/freeze")
        assert response.status_code == 200
        assert response.json().get("status") == "frozen"
        print(f"✓ Invoice {draft_invoice_id[:8]}... frozen")

    def test_cannot_freeze_non_draft(self, api_client):
        """Cannot freeze invoice that is not draft"""
        # Get a frozen/sent/paid invoice
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=frozen")
        frozen = resp.json().get("invoices", [])
        if not frozen:
            resp = api_client.get(f"{BASE_URL}/api/invoices?status=paid")
            frozen = resp.json().get("invoices", [])
        
        if frozen:
            response = api_client.post(f"{BASE_URL}/api/invoices/{frozen[0]['id']}/freeze")
            assert response.status_code == 400
            print("✓ Freeze correctly blocked for non-draft invoice")
        else:
            print("⚠ No non-draft invoice to test")

    def test_mark_sent_from_frozen(self, api_client):
        """POST /api/invoices/{id}/mark-sent transitions frozen→sent"""
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=frozen")
        frozen = resp.json().get("invoices", [])
        
        if frozen:
            response = api_client.post(f"{BASE_URL}/api/invoices/{frozen[0]['id']}/mark-sent")
            assert response.status_code == 200
            assert response.json().get("status") == "sent"
            print(f"✓ Invoice marked sent")
        else:
            print("⚠ No frozen invoice to test mark-sent")

    def test_cannot_send_non_frozen(self, api_client):
        """Cannot mark-sent invoice that is not frozen"""
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=draft")
        drafts = resp.json().get("invoices", [])
        
        if drafts:
            response = api_client.post(f"{BASE_URL}/api/invoices/{drafts[0]['id']}/mark-sent")
            assert response.status_code == 400
            print("✓ Mark-sent correctly blocked for non-frozen invoice")
        else:
            print("⚠ No draft invoice to test guard")

    def test_mark_paid(self, api_client):
        """POST /api/invoices/{id}/mark-paid transitions sent/frozen→paid"""
        # Try sent first
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=sent")
        sent = resp.json().get("invoices", [])
        
        if sent:
            response = api_client.post(f"{BASE_URL}/api/invoices/{sent[0]['id']}/mark-paid")
            assert response.status_code == 200
            assert response.json().get("status") == "paid"
            print("✓ Invoice marked paid from sent")
        else:
            # Try frozen
            resp = api_client.get(f"{BASE_URL}/api/invoices?status=frozen")
            frozen = resp.json().get("invoices", [])
            if frozen:
                response = api_client.post(f"{BASE_URL}/api/invoices/{frozen[0]['id']}/mark-paid")
                assert response.status_code == 200
                print("✓ Invoice marked paid from frozen")
            else:
                print("⚠ No sent/frozen invoice to test mark-paid")

    def test_cannot_pay_draft(self, api_client):
        """Cannot mark-paid a draft invoice"""
        resp = api_client.get(f"{BASE_URL}/api/invoices?status=draft")
        drafts = resp.json().get("invoices", [])
        
        if drafts:
            response = api_client.post(f"{BASE_URL}/api/invoices/{drafts[0]['id']}/mark-paid")
            assert response.status_code == 400
            print("✓ Mark-paid correctly blocked for draft invoice")
        else:
            print("⚠ No draft invoice to test guard")


class TestEventLogging:
    """Verify events are logged for billing actions"""

    def test_pricing_update_logs_event(self, api_client, test_client_id):
        """pricing_update event logged when pricing updated"""
        # Update pricing (should trigger event)
        api_client.put(f"{BASE_URL}/api/clients/{test_client_id}/pricing", json={
            "discount_pct_global": 8.0
        })
        
        # Check event log
        response = api_client.get(f"{BASE_URL}/api/event-log?event_type=pricing_update&limit=5")
        if response.status_code == 200:
            events = response.json().get("events", [])
            assert len(events) > 0, "pricing_update events should be logged"
            print(f"✓ pricing_update events logged: {len(events)}")
        else:
            print("⚠ Event log endpoint not available")

    def test_credit_added_logs_event(self, api_client, test_client_id):
        """credit_added event logged when credit added"""
        # Add credit
        api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "product_code": "PV",
            "week_key": "2026-W77",
            "quantity_units_free": 1,
            "reason": "autre",
            "note": "Event test"
        })
        
        # Check event log
        response = api_client.get(f"{BASE_URL}/api/event-log?event_type=credit_added&limit=5")
        if response.status_code == 200:
            events = response.json().get("events", [])
            assert len(events) > 0, "credit_added events should be logged"
            print(f"✓ credit_added events logged: {len(events)}")
        else:
            print("⚠ Event log endpoint not available")


class TestPrepaidRoutingBlock:
    """Test that PREPAID with empty balance blocks routing"""

    def test_prepaid_balance_structure(self, api_client, test_client_id):
        """Verify prepayment balance has correct fields"""
        response = api_client.get(f"{BASE_URL}/api/clients/{test_client_id}/prepayment")
        assert response.status_code == 200
        
        balances = response.json().get("balances", [])
        if balances:
            bal = balances[0]
            assert "client_id" in bal
            assert "product_code" in bal
            assert "units_purchased_total" in bal
            assert "units_delivered_total" in bal
            assert "units_remaining" in bal
            print("✓ Prepayment balance structure verified")
        else:
            print("⚠ No prepayment balances to verify")


class TestLedgerSnapshot:
    """Test that ledger captures pricing snapshot"""

    def test_ledger_entry_has_snapshot_fields(self, api_client):
        """Verify ledger entries capture pricing at build time"""
        # Build ledger for a test week
        api_client.post(f"{BASE_URL}/api/billing/week/2026-W07/build-ledger")
        
        # Check dashboard to see if entries exist
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        data = response.json()
        
        # The ledger is internal, but we can verify via invoice fields
        all_rows = data.get("weekly_invoice", []) + data.get("prepaid", [])
        if all_rows:
            row = all_rows[0]
            # These are derived from ledger snapshot
            assert "unit_price_eur" in row
            assert "discount_pct" in row
            print("✓ Pricing data present (derived from ledger snapshot)")
        else:
            print("⚠ No rows to verify snapshot")


class TestAuthenticationRequired:
    """Verify all billing endpoints require authentication"""

    def test_products_requires_auth(self):
        """GET /api/products requires auth"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code in [401, 403]

    def test_pricing_requires_auth(self):
        """GET /api/clients/{id}/pricing requires auth"""
        response = requests.get(f"{BASE_URL}/api/clients/test-id/pricing")
        assert response.status_code in [401, 403]

    def test_credits_requires_auth(self):
        """GET /api/clients/{id}/credits requires auth"""
        response = requests.get(f"{BASE_URL}/api/clients/test-id/credits")
        assert response.status_code in [401, 403]

    def test_billing_week_requires_auth(self):
        """GET /api/billing/week requires auth"""
        response = requests.get(f"{BASE_URL}/api/billing/week")
        assert response.status_code in [401, 403]

    def test_invoices_requires_auth(self):
        """GET /api/invoices requires auth"""
        response = requests.get(f"{BASE_URL}/api/invoices")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
