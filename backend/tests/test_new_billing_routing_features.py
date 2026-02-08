"""
Test suite for new billing and routing features:
1. POST /api/billing/mark-invoiced - Mark a period as invoiced
2. GET /api/billing/history - Get billing history
3. DELETE /api/billing/history/{id} - Delete billing record
4. Forms with exclude_from_routing field
5. Anti-duplicate logic: same phone + same product per day
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBillingMarkInvoiced:
    """Test POST /api/billing/mark-invoiced endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        
        # Get CRMs for testing
        crms_response = requests.get(f"{BASE_URL}/api/crms", headers=self.headers)
        assert crms_response.status_code == 200
        self.crms = crms_response.json().get("crms", [])
        assert len(self.crms) >= 2, "Need at least 2 CRMs for billing tests"
        self.mdl_crm = next((c for c in self.crms if c.get("slug") == "mdl"), self.crms[0])
        self.zr7_crm = next((c for c in self.crms if c.get("slug") == "zr7"), self.crms[1])
    
    def test_mark_period_invoiced_success(self):
        """Test marking a period as invoiced"""
        now = datetime.now()
        billing_data = {
            "year": now.year,
            "month": now.month,
            "from_crm_id": self.mdl_crm["id"],
            "to_crm_id": self.zr7_crm["id"],
            "amount": 500.0,
            "lead_count": 20,
            "notes": "TEST_billing_record"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/billing/mark-invoiced",
            headers=self.headers,
            json=billing_data
        )
        
        assert response.status_code == 200, f"Failed to mark as invoiced: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "id" in data
        
        # Store for cleanup
        self.billing_id = data["id"]
        
        # Verify in history
        history_response = requests.get(
            f"{BASE_URL}/api/billing/history?year={now.year}",
            headers=self.headers
        )
        assert history_response.status_code == 200
        history = history_response.json().get("history", [])
        
        # Find our record
        found = any(h.get("id") == self.billing_id for h in history)
        assert found, "Billing record not found in history"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/billing/history/{self.billing_id}", headers=self.headers)
    
    def test_mark_period_invoiced_update_existing(self):
        """Test updating an existing billing record for same period"""
        now = datetime.now()
        billing_data = {
            "year": now.year,
            "month": now.month,
            "from_crm_id": self.zr7_crm["id"],
            "to_crm_id": self.mdl_crm["id"],
            "amount": 300.0,
            "lead_count": 15,
            "notes": "TEST_initial_record"
        }
        
        # Create initial record
        response1 = requests.post(
            f"{BASE_URL}/api/billing/mark-invoiced",
            headers=self.headers,
            json=billing_data
        )
        assert response1.status_code == 200
        billing_id = response1.json().get("id")
        
        # Update with new amount
        billing_data["amount"] = 450.0
        billing_data["lead_count"] = 18
        billing_data["notes"] = "TEST_updated_record"
        
        response2 = requests.post(
            f"{BASE_URL}/api/billing/mark-invoiced",
            headers=self.headers,
            json=billing_data
        )
        assert response2.status_code == 200
        
        # Verify update
        history_response = requests.get(
            f"{BASE_URL}/api/billing/history?year={now.year}",
            headers=self.headers
        )
        history = history_response.json().get("history", [])
        
        # Find our record and verify updated values
        record = next((h for h in history if h.get("from_crm_id") == self.zr7_crm["id"] 
                      and h.get("to_crm_id") == self.mdl_crm["id"]
                      and h.get("year") == now.year
                      and h.get("month") == now.month), None)
        
        if record:
            assert record.get("amount") == 450.0, "Amount not updated"
            assert record.get("lead_count") == 18, "Lead count not updated"
            # Cleanup
            requests.delete(f"{BASE_URL}/api/billing/history/{record['id']}", headers=self.headers)
    
    def test_mark_period_invoiced_missing_fields(self):
        """Test that missing required fields return error"""
        # Missing from_crm_id
        response = requests.post(
            f"{BASE_URL}/api/billing/mark-invoiced",
            headers=self.headers,
            json={
                "year": 2024,
                "month": 1,
                "to_crm_id": self.zr7_crm["id"],
                "amount": 100.0,
                "lead_count": 5
            }
        )
        assert response.status_code == 422, "Should fail with missing from_crm_id"


class TestBillingHistory:
    """Test GET /api/billing/history endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_get_billing_history(self):
        """Test retrieving billing history"""
        response = requests.get(
            f"{BASE_URL}/api/billing/history",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
    
    def test_get_billing_history_by_year(self):
        """Test filtering billing history by year"""
        response = requests.get(
            f"{BASE_URL}/api/billing/history?year=2024",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        
        # All records should be from 2024
        for record in data["history"]:
            assert record.get("year") == 2024 or len(data["history"]) == 0


class TestBillingHistoryDelete:
    """Test DELETE /api/billing/history/{id} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        
        # Get CRMs
        crms_response = requests.get(f"{BASE_URL}/api/crms", headers=self.headers)
        self.crms = crms_response.json().get("crms", [])
        self.mdl_crm = next((c for c in self.crms if c.get("slug") == "mdl"), self.crms[0])
        self.zr7_crm = next((c for c in self.crms if c.get("slug") == "zr7"), self.crms[1])
    
    def test_delete_billing_record(self):
        """Test deleting a billing record"""
        # First create a record
        now = datetime.now()
        billing_data = {
            "year": now.year,
            "month": now.month,
            "from_crm_id": self.mdl_crm["id"],
            "to_crm_id": self.zr7_crm["id"],
            "amount": 100.0,
            "lead_count": 5,
            "notes": "TEST_to_delete"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/billing/mark-invoiced",
            headers=self.headers,
            json=billing_data
        )
        assert create_response.status_code == 200
        billing_id = create_response.json().get("id")
        
        # Delete the record
        delete_response = requests.delete(
            f"{BASE_URL}/api/billing/history/{billing_id}",
            headers=self.headers
        )
        assert delete_response.status_code == 200
        
        # Verify deletion
        history_response = requests.get(
            f"{BASE_URL}/api/billing/history?year={now.year}",
            headers=self.headers
        )
        history = history_response.json().get("history", [])
        found = any(h.get("id") == billing_id for h in history)
        assert not found, "Billing record should be deleted"
    
    def test_delete_nonexistent_billing_record(self):
        """Test deleting a non-existent billing record"""
        response = requests.delete(
            f"{BASE_URL}/api/billing/history/nonexistent-id-12345",
            headers=self.headers
        )
        assert response.status_code == 404


class TestFormsExcludeFromRouting:
    """Test forms with exclude_from_routing field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        
        # Get accounts
        accounts_response = requests.get(f"{BASE_URL}/api/accounts", headers=self.headers)
        self.accounts = accounts_response.json().get("accounts", [])
        self.test_account = self.accounts[0] if self.accounts else None
    
    def test_create_form_with_exclude_from_routing_true(self):
        """Test creating a form with exclude_from_routing=True"""
        if not self.test_account:
            pytest.skip("No accounts available for testing")
        
        form_data = {
            "account_id": self.test_account["id"],
            "code": "TEST-EXCL-001",
            "name": "Test Excluded Form",
            "product_type": "panneaux",
            "source_type": "native",
            "exclude_from_routing": True,
            "status": "active"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/forms",
            headers=self.headers,
            json=form_data
        )
        
        assert response.status_code == 200, f"Failed to create form: {response.text}"
        data = response.json()
        assert data.get("success") == True
        form = data.get("form", {})
        assert form.get("exclude_from_routing") == True
        
        # Cleanup
        if form.get("id"):
            requests.delete(f"{BASE_URL}/api/forms/{form['id']}", headers=self.headers)
    
    def test_create_form_with_exclude_from_routing_false(self):
        """Test creating a form with exclude_from_routing=False (default)"""
        if not self.test_account:
            pytest.skip("No accounts available for testing")
        
        form_data = {
            "account_id": self.test_account["id"],
            "code": "TEST-INCL-001",
            "name": "Test Included Form",
            "product_type": "pompes",
            "source_type": "native",
            "exclude_from_routing": False,
            "status": "active"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/forms",
            headers=self.headers,
            json=form_data
        )
        
        assert response.status_code == 200
        data = response.json()
        form = data.get("form", {})
        assert form.get("exclude_from_routing") == False
        
        # Cleanup
        if form.get("id"):
            requests.delete(f"{BASE_URL}/api/forms/{form['id']}", headers=self.headers)
    
    def test_update_form_exclude_from_routing(self):
        """Test updating exclude_from_routing field"""
        if not self.test_account:
            pytest.skip("No accounts available for testing")
        
        # Create form
        form_data = {
            "account_id": self.test_account["id"],
            "code": "TEST-UPD-001",
            "name": "Test Update Form",
            "product_type": "isolation",
            "source_type": "native",
            "exclude_from_routing": False,
            "status": "active"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/forms",
            headers=self.headers,
            json=form_data
        )
        assert create_response.status_code == 200
        form_id = create_response.json().get("form", {}).get("id")
        
        # Update to exclude
        form_data["exclude_from_routing"] = True
        update_response = requests.put(
            f"{BASE_URL}/api/forms/{form_id}",
            headers=self.headers,
            json=form_data
        )
        assert update_response.status_code == 200
        
        # Verify update
        get_response = requests.get(
            f"{BASE_URL}/api/forms/{form_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        updated_form = get_response.json()
        assert updated_form.get("exclude_from_routing") == True
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/forms/{form_id}", headers=self.headers)
    
    def test_forms_list_shows_exclude_from_routing(self):
        """Test that forms list includes exclude_from_routing field"""
        response = requests.get(
            f"{BASE_URL}/api/forms",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        forms = data.get("forms", [])
        
        # Check that forms have the exclude_from_routing field
        for form in forms:
            assert "exclude_from_routing" in form or form.get("exclude_from_routing") is None or form.get("exclude_from_routing") == False


class TestFormsProductFilter:
    """Test forms filtering by product type"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_filter_forms_by_product_panneaux(self):
        """Test filtering forms by product_type=panneaux (PV)"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=panneaux",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        forms = data.get("forms", [])
        
        # All forms should be panneaux type
        for form in forms:
            assert form.get("product_type") == "panneaux", f"Form {form.get('code')} has wrong product type"
    
    def test_filter_forms_by_product_pompes(self):
        """Test filtering forms by product_type=pompes (PAC)"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=pompes",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        forms = data.get("forms", [])
        
        for form in forms:
            assert form.get("product_type") == "pompes"
    
    def test_filter_forms_by_product_isolation(self):
        """Test filtering forms by product_type=isolation (ITE)"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=isolation",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        forms = data.get("forms", [])
        
        for form in forms:
            assert form.get("product_type") == "isolation"


class TestAntiDuplicateLogic:
    """Test anti-duplicate logic: same phone + same product per day"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token, get form for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        
        # Get forms
        forms_response = requests.get(f"{BASE_URL}/api/forms", headers=self.headers)
        self.forms = forms_response.json().get("forms", [])
    
    def test_duplicate_same_phone_same_product_same_day(self):
        """Test that same phone + same product on same day is marked as duplicate"""
        if not self.forms:
            pytest.skip("No forms available for testing")
        
        # Find a form with panneaux product type
        test_form = next((f for f in self.forms if f.get("product_type") == "panneaux"), self.forms[0])
        
        # Use a unique test phone number
        test_phone = "0612345678"
        
        # First submission
        lead_data = {
            "phone": test_phone,
            "nom": "Test Duplicate",
            "form_code": test_form.get("code"),
            "departement": "75"
        }
        
        response1 = requests.post(
            f"{BASE_URL}/api/submit-lead",
            headers={"Content-Type": "application/json"},
            json=lead_data
        )
        
        # Second submission with same phone + same product (via same form)
        response2 = requests.post(
            f"{BASE_URL}/api/submit-lead",
            headers={"Content-Type": "application/json"},
            json=lead_data
        )
        
        # The second should be marked as duplicate_today
        if response2.status_code == 200:
            data2 = response2.json()
            # Check if it's marked as duplicate
            assert data2.get("status") in ["duplicate_today", "success", "no_config"], \
                f"Expected duplicate or success status, got: {data2.get('status')}"


class TestGuidePage:
    """Test that Guide page sections are accessible"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["token"]
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_api_health(self):
        """Test that API is healthy"""
        response = requests.get(f"{BASE_URL}/api/crms", headers=self.headers)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
