"""
Test Simplified Billing Records - RDZ CRM
Testing the new billing_records workflow that replaces the old invoice system.

Features tested:
- POST /api/billing/week/{wk}/build-ledger creates ledger + billing_records
- build-ledger blocked if billing_record status is invoiced/paid
- GET /api/billing/week returns has_records flag and billing_records when built
- GET /api/billing/week returns preview from deliveries when no records
- PUT /api/billing/records/{id} updates external tracking
- GET /api/billing/records lists billing records with filters
- POST /api/clients/{id}/credits requires order_id and product_code
- billing_records contain vat_rate_snapshot, vat_amount, total_ttc_expected
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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


@pytest.fixture(scope="module")
def test_order_id(api_client, test_client_id):
    """Get an existing commande (order) ID for the test client"""
    response = api_client.get(f"{BASE_URL}/api/commandes?entity=ZR7&client_id={test_client_id}")
    if response.status_code == 200:
        commandes = response.json().get("commandes", [])
        if commandes:
            return commandes[0]["id"]
    # Try without client_id filter
    response = api_client.get(f"{BASE_URL}/api/commandes?entity=ZR7")
    if response.status_code == 200:
        commandes = response.json().get("commandes", [])
        if commandes:
            return commandes[0]["id"]
    return None  # No orders available


class TestBillingWeekDashboard:
    """Test GET /api/billing/week endpoint"""

    def test_billing_week_returns_has_records_flag(self, api_client):
        """GET /api/billing/week returns has_records boolean"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_records" in data, "Response should include has_records flag"
        assert isinstance(data["has_records"], bool)
        print(f"✓ has_records flag present: {data['has_records']}")

    def test_billing_week_with_records_returns_billing_records(self, api_client):
        """GET /api/billing/week with built ledger returns billing_records in weekly_invoice"""
        # Use a week we know has records (from context: 2026-W07 has records)
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        if data.get("has_records"):
            assert "weekly_invoice" in data
            # When has_records is True, rows should have billing record fields
            if data["weekly_invoice"]:
                row = data["weekly_invoice"][0]
                assert "id" in row, "Billing record should have id"
                assert "status" in row, "Billing record should have status"
                print(f"✓ Records returned with id and status fields")
        else:
            print("⚠ No records built for 2026-W07 yet")

    def test_billing_week_preview_when_no_records(self, api_client):
        """GET /api/billing/week returns preview from deliveries when no records"""
        # Use a future week that won't have records built
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W52")
        assert response.status_code == 200
        
        data = response.json()
        assert "week_key" in data
        assert "has_records" in data
        # If no records, should have preview rows with is_preview=True
        if not data.get("has_records") and data.get("weekly_invoice"):
            for row in data["weekly_invoice"]:
                assert row.get("is_preview") == True, "Preview rows should have is_preview=True"
            print("✓ Preview mode returns is_preview=True rows")
        else:
            print("⚠ Either has_records or no weekly_invoice rows")

    def test_billing_week_has_required_summary_fields(self, api_client):
        """Verify summary contains required KPI fields"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        summary = data["summary"]
        
        required_fields = ["leads_produced", "units_delivered", "units_billable", "units_non_billable"]
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
        print(f"✓ Summary fields present: {list(summary.keys())}")

    def test_billing_week_has_totals(self, api_client):
        """Verify totals contain net_ht and ttc"""
        response = api_client.get(f"{BASE_URL}/api/billing/week?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert "totals" in data
        totals = data["totals"]
        
        assert "net_ht" in totals, "Missing totals.net_ht"
        assert "ttc" in totals, "Missing totals.ttc"
        print(f"✓ Totals: net_ht={totals['net_ht']}, ttc={totals['ttc']}")


class TestBuildLedger:
    """Test POST /api/billing/week/{wk}/build-ledger endpoint"""

    def test_build_ledger_creates_entries_and_records(self, api_client):
        """POST /api/billing/week/{wk}/build-ledger creates ledger entries + billing_records"""
        # Use a test week
        test_week = "2026-W50"
        
        response = api_client.post(f"{BASE_URL}/api/billing/week/{test_week}/build-ledger")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "ledger_entries" in data
        assert "billing_records_created" in data
        print(f"✓ Ledger built: {data['ledger_entries']} entries, {data['billing_records_created']} records")

    def test_build_ledger_blocked_if_invoiced(self, api_client):
        """build-ledger blocked if billing_record status is 'invoiced'"""
        # First check if 2026-W07 has any invoiced records
        resp = api_client.get(f"{BASE_URL}/api/billing/records?week_key=2026-W07&status=invoiced")
        invoiced = resp.json().get("records", [])
        
        if invoiced:
            response = api_client.post(f"{BASE_URL}/api/billing/week/2026-W07/build-ledger")
            assert response.status_code == 400, "Should block rebuild when invoiced records exist"
            assert "invoiced" in response.text.lower() or "Cannot rebuild" in response.text
            print("✓ Build ledger correctly blocked due to invoiced record")
        else:
            print("⚠ No invoiced records in 2026-W07 to test block")

    def test_build_ledger_blocked_if_paid(self, api_client):
        """build-ledger blocked if billing_record status is 'paid'"""
        resp = api_client.get(f"{BASE_URL}/api/billing/records?week_key=2026-W07&status=paid")
        paid = resp.json().get("records", [])
        
        if paid:
            response = api_client.post(f"{BASE_URL}/api/billing/week/2026-W07/build-ledger")
            assert response.status_code == 400, "Should block rebuild when paid records exist"
            assert "paid" in response.text.lower() or "Cannot rebuild" in response.text
            print("✓ Build ledger correctly blocked due to paid record")
        else:
            print("⚠ No paid records in 2026-W07 to test block")


class TestBillingRecords:
    """Test GET/PUT /api/billing/records endpoints"""

    def test_list_billing_records(self, api_client):
        """GET /api/billing/records lists all billing records"""
        response = api_client.get(f"{BASE_URL}/api/billing/records")
        assert response.status_code == 200
        
        data = response.json()
        assert "records" in data
        assert "count" in data
        print(f"✓ Total billing records: {data['count']}")

    def test_list_billing_records_by_week(self, api_client):
        """GET /api/billing/records?week_key=... filters by week"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?week_key=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        for rec in data.get("records", []):
            assert rec.get("week_key") == "2026-W07"
        print(f"✓ Filtered records for 2026-W07: {data['count']}")

    def test_list_billing_records_by_status(self, api_client):
        """GET /api/billing/records?status=... filters by status"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=not_invoiced")
        assert response.status_code == 200
        
        data = response.json()
        for rec in data.get("records", []):
            assert rec.get("status") == "not_invoiced"
        print(f"✓ Filtered records by status: {data['count']} not_invoiced")

    def test_list_billing_records_by_client(self, api_client, test_client_id):
        """GET /api/billing/records?client_id=... filters by client"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?client_id={test_client_id}")
        assert response.status_code == 200
        
        data = response.json()
        for rec in data.get("records", []):
            assert rec.get("client_id") == test_client_id
        print(f"✓ Filtered records for client: {data['count']}")

    def test_billing_record_has_vat_fields(self, api_client):
        """Verify billing_records contain vat_rate_snapshot, vat_amount, total_ttc_expected"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?week_key=2026-W07")
        assert response.status_code == 200
        
        records = response.json().get("records", [])
        if records:
            rec = records[0]
            assert "vat_rate_snapshot" in rec, "Missing vat_rate_snapshot"
            assert "vat_amount" in rec, "Missing vat_amount"
            assert "total_ttc_expected" in rec, "Missing total_ttc_expected"
            print(f"✓ VAT fields present: vat_rate={rec['vat_rate_snapshot']}, vat_amount={rec['vat_amount']}, ttc={rec['total_ttc_expected']}")
        else:
            print("⚠ No records to verify VAT fields")


class TestUpdateBillingRecord:
    """Test PUT /api/billing/records/{id} for external tracking"""

    @pytest.fixture(scope="class")
    def test_record_id(self, api_client):
        """Get a billing record ID for testing"""
        # Get any not_invoiced record
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=not_invoiced")
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]
        # Fall back to any record
        response = api_client.get(f"{BASE_URL}/api/billing/records")
        records = response.json().get("records", [])
        if records:
            return records[0]["id"]
        return None

    def test_update_external_invoice_number(self, api_client, test_record_id):
        """PUT /api/billing/records/{id} updates external_invoice_number"""
        if not test_record_id:
            pytest.skip("No billing records available")
        
        test_number = "FAC-TEST-001"
        response = api_client.put(f"{BASE_URL}/api/billing/records/{test_record_id}", json={
            "external_invoice_number": test_number
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify
        verify = api_client.get(f"{BASE_URL}/api/billing/records")
        rec = next((r for r in verify.json()["records"] if r["id"] == test_record_id), None)
        assert rec is not None
        assert rec.get("external_invoice_number") == test_number
        print(f"✓ External invoice number updated to {test_number}")

    def test_update_status_to_invoiced(self, api_client, test_record_id):
        """PUT /api/billing/records/{id} can change status to invoiced"""
        if not test_record_id:
            pytest.skip("No billing records available")
        
        response = api_client.put(f"{BASE_URL}/api/billing/records/{test_record_id}", json={
            "status": "invoiced"
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        # Verify
        verify = api_client.get(f"{BASE_URL}/api/billing/records")
        rec = next((r for r in verify.json()["records"] if r["id"] == test_record_id), None)
        assert rec is not None
        assert rec.get("status") == "invoiced"
        print("✓ Status updated to invoiced")

    def test_update_due_date(self, api_client, test_record_id):
        """PUT /api/billing/records/{id} updates due_date"""
        if not test_record_id:
            pytest.skip("No billing records available")
        
        test_date = "2026-03-15"
        response = api_client.put(f"{BASE_URL}/api/billing/records/{test_record_id}", json={
            "due_date": test_date
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        print(f"✓ Due date updated to {test_date}")

    def test_update_paid_at(self, api_client, test_record_id):
        """PUT /api/billing/records/{id} updates paid_at"""
        if not test_record_id:
            pytest.skip("No billing records available")
        
        test_date = "2026-02-20"
        response = api_client.put(f"{BASE_URL}/api/billing/records/{test_record_id}", json={
            "paid_at": test_date,
            "status": "paid"
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        print(f"✓ Paid at updated to {test_date}")

    def test_update_invalid_status_rejected(self, api_client, test_record_id):
        """PUT /api/billing/records/{id} rejects invalid status"""
        if not test_record_id:
            pytest.skip("No billing records available")
        
        response = api_client.put(f"{BASE_URL}/api/billing/records/{test_record_id}", json={
            "status": "invalid_status"
        })
        assert response.status_code == 400
        print("✓ Invalid status correctly rejected")

    def test_update_nonexistent_record_404(self, api_client):
        """PUT /api/billing/records/{id} returns 404 for nonexistent"""
        response = api_client.put(f"{BASE_URL}/api/billing/records/nonexistent-id-12345", json={
            "status": "invoiced"
        })
        assert response.status_code == 404
        print("✓ Nonexistent record returns 404")


class TestCreditsRequireOrderId:
    """Test that credits now require order_id and product_code"""

    def test_add_credit_without_order_id_fails(self, api_client, test_client_id):
        """POST /api/clients/{id}/credits without order_id returns 400"""
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "order_id": "",  # Empty order_id
            "product_code": "PV",
            "week_key": "2026-W10",
            "quantity_units_free": 1,
            "reason": "geste_commercial"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "order_id" in response.text.lower()
        print("✓ Credit without order_id correctly rejected")

    def test_add_credit_without_product_code_fails(self, api_client, test_client_id, test_order_id):
        """POST /api/clients/{id}/credits without product_code returns 400"""
        if not test_order_id:
            pytest.skip("No order_id available for test")
        
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "order_id": test_order_id,
            "product_code": "",  # Empty product_code
            "week_key": "2026-W10",
            "quantity_units_free": 1,
            "reason": "geste_commercial"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "product_code" in response.text.lower()
        print("✓ Credit without product_code correctly rejected")

    def test_add_credit_with_order_id_succeeds(self, api_client, test_client_id, test_order_id):
        """POST /api/clients/{id}/credits with order_id succeeds"""
        if not test_order_id:
            pytest.skip("No order_id available for test")
        
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "order_id": test_order_id,
            "product_code": "PV",
            "week_key": "2026-W11",
            "quantity_units_free": 2,
            "reason": "geste_commercial",
            "note": "Test credit with order_id"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("credit", {}).get("order_id") == test_order_id
        print(f"✓ Credit with order_id created successfully")

    def test_add_credit_invalid_reason_fails(self, api_client, test_client_id, test_order_id):
        """POST /api/clients/{id}/credits with invalid reason returns 400"""
        if not test_order_id:
            pytest.skip("No order_id available for test")
        
        response = api_client.post(f"{BASE_URL}/api/clients/{test_client_id}/credits", json={
            "order_id": test_order_id,
            "product_code": "PV",
            "week_key": "2026-W10",
            "quantity_units_free": 1,
            "reason": "INVALID_REASON"
        })
        assert response.status_code == 400
        print("✓ Invalid credit reason correctly rejected")


class TestRecordStatuses:
    """Test all valid record statuses: not_invoiced, invoiced, paid, overdue"""

    def test_status_not_invoiced_valid(self, api_client):
        """Verify not_invoiced is a valid status"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=not_invoiced")
        assert response.status_code == 200
        print("✓ Status 'not_invoiced' is valid")

    def test_status_invoiced_valid(self, api_client):
        """Verify invoiced is a valid status"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=invoiced")
        assert response.status_code == 200
        print("✓ Status 'invoiced' is valid")

    def test_status_paid_valid(self, api_client):
        """Verify paid is a valid status"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=paid")
        assert response.status_code == 200
        print("✓ Status 'paid' is valid")

    def test_status_overdue_valid(self, api_client):
        """Verify overdue is a valid status"""
        response = api_client.get(f"{BASE_URL}/api/billing/records?status=overdue")
        assert response.status_code == 200
        print("✓ Status 'overdue' is valid")


class TestAuthenticationRequired:
    """Verify endpoints require authentication"""

    def test_billing_week_requires_auth(self):
        """GET /api/billing/week requires auth"""
        response = requests.get(f"{BASE_URL}/api/billing/week")
        assert response.status_code in [401, 403]

    def test_build_ledger_requires_auth(self):
        """POST /api/billing/week/{wk}/build-ledger requires auth"""
        response = requests.post(f"{BASE_URL}/api/billing/week/2026-W01/build-ledger")
        assert response.status_code in [401, 403]

    def test_billing_records_requires_auth(self):
        """GET /api/billing/records requires auth"""
        response = requests.get(f"{BASE_URL}/api/billing/records")
        assert response.status_code in [401, 403]

    def test_update_record_requires_auth(self):
        """PUT /api/billing/records/{id} requires auth"""
        response = requests.put(f"{BASE_URL}/api/billing/records/test-id", json={"status": "paid"})
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
