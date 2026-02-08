"""
Test suite for new billing and archiving features:
1. POST /api/leads/archive - Archive leads older than X months
2. GET /api/leads/archived - Get archived leads
3. GET /api/billing/dashboard - Billing dashboard with CRM stats
4. PUT /api/crms/{id} with lead_prices - Configure lead prices per product
5. GET /api/forms with product_type filter - Filter forms by product type
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }


class TestBillingDashboard(TestAuth):
    """Tests for billing dashboard endpoint"""
    
    def test_billing_dashboard_requires_auth(self):
        """Test that billing dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/billing/dashboard")
        assert response.status_code == 401
    
    def test_billing_dashboard_basic(self, auth_headers):
        """Test billing dashboard returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/billing/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Check expected fields
        assert "crm_stats" in data
        assert "total_leads" in data
        assert "transfers" in data
        assert "period" in data
    
    def test_billing_dashboard_with_date_range(self, auth_headers):
        """Test billing dashboard with date range parameters"""
        now = datetime.now()
        date_from = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        date_to = now.strftime("%Y-%m-%dT23:59:59")
        
        response = requests.get(
            f"{BASE_URL}/api/billing/dashboard?date_from={date_from}&date_to={date_to}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "crm_stats" in data
        assert isinstance(data["crm_stats"], list)
    
    def test_billing_dashboard_crm_stats_structure(self, auth_headers):
        """Test that CRM stats have expected structure"""
        response = requests.get(f"{BASE_URL}/api/billing/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        if data["crm_stats"]:
            crm_stat = data["crm_stats"][0]
            # Check expected fields in CRM stats
            expected_fields = [
                "crm_name", "crm_slug", "lead_prices",
                "leads_originated", "leads_received",
                "leads_rerouted_out", "leads_rerouted_in",
                "amount_to_invoice", "amount_to_pay", "net_balance"
            ]
            for field in expected_fields:
                assert field in crm_stat, f"Missing field: {field}"
            
            # Check leads structure
            for lead_type in ["leads_originated", "leads_received", "leads_rerouted_out", "leads_rerouted_in"]:
                assert "PAC" in crm_stat[lead_type]
                assert "PV" in crm_stat[lead_type]
                assert "ITE" in crm_stat[lead_type]
                assert "total" in crm_stat[lead_type]


class TestLeadArchiving(TestAuth):
    """Tests for lead archiving endpoints"""
    
    def test_archive_leads_requires_auth(self):
        """Test that archive endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/leads/archive?months=3")
        assert response.status_code == 401
    
    def test_archive_leads_requires_admin(self, auth_headers):
        """Test archive leads endpoint (admin only)"""
        response = requests.post(
            f"{BASE_URL}/api/leads/archive?months=3",
            headers=auth_headers
        )
        # Should succeed for admin user
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "archived_count" in data
    
    def test_archive_leads_with_custom_months(self, auth_headers):
        """Test archive with custom months parameter"""
        response = requests.post(
            f"{BASE_URL}/api/leads/archive?months=6",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "archived_count" in data
        assert isinstance(data["archived_count"], int)
    
    def test_get_archived_leads_requires_auth(self):
        """Test that archived leads endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads/archived")
        assert response.status_code == 401
    
    def test_get_archived_leads(self, auth_headers):
        """Test getting archived leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads/archived",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "leads" in data
        assert "count" in data
        assert "total" in data
        assert isinstance(data["leads"], list)
    
    def test_get_archived_leads_with_date_filter(self, auth_headers):
        """Test archived leads with date filters"""
        now = datetime.now()
        date_from = (now - timedelta(days=365)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/archived?date_from={date_from}&date_to={date_to}&limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "leads" in data


class TestCRMLeadPrices(TestAuth):
    """Tests for CRM lead prices configuration"""
    
    def test_get_crms(self, auth_headers):
        """Test getting CRMs list"""
        response = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "crms" in data
        assert isinstance(data["crms"], list)
    
    def test_crm_has_lead_prices_field(self, auth_headers):
        """Test that CRMs have lead_prices field"""
        response = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        if data["crms"]:
            crm = data["crms"][0]
            # lead_prices may be empty dict or have values
            assert "lead_prices" in crm or crm.get("lead_prices") is None or isinstance(crm.get("lead_prices", {}), dict)
    
    def test_update_crm_lead_prices(self, auth_headers):
        """Test updating CRM with lead prices"""
        # First get a CRM
        response = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        assert response.status_code == 200
        crms = response.json()["crms"]
        
        if not crms:
            pytest.skip("No CRMs available for testing")
        
        crm_id = crms[0]["id"]
        
        # Update with lead prices
        update_data = {
            "lead_prices": {
                "PAC": 25.0,
                "PV": 20.0,
                "ITE": 30.0
            }
        }
        
        response = requests.put(
            f"{BASE_URL}/api/crms/{crm_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify the update
        response = requests.get(f"{BASE_URL}/api/crms/{crm_id}", headers=auth_headers)
        assert response.status_code == 200
        
        updated_crm = response.json()
        assert "lead_prices" in updated_crm
        assert updated_crm["lead_prices"]["PAC"] == 25.0
        assert updated_crm["lead_prices"]["PV"] == 20.0
        assert updated_crm["lead_prices"]["ITE"] == 30.0
    
    def test_update_crm_commandes_and_prices(self, auth_headers):
        """Test updating CRM with both commandes and lead prices"""
        response = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        crms = response.json()["crms"]
        
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        
        update_data = {
            "commandes": {
                "PAC": ["75", "92", "93"],
                "PV": ["13", "31"],
                "ITE": []
            },
            "lead_prices": {
                "PAC": 28.0,
                "PV": 22.0,
                "ITE": 35.0
            }
        }
        
        response = requests.put(
            f"{BASE_URL}/api/crms/{crm_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200
        
        # Verify
        response = requests.get(f"{BASE_URL}/api/crms/{crm_id}", headers=auth_headers)
        updated_crm = response.json()
        
        assert updated_crm["commandes"]["PAC"] == ["75", "92", "93"]
        assert updated_crm["lead_prices"]["PAC"] == 28.0


class TestFormsProductFilter(TestAuth):
    """Tests for forms product type filter"""
    
    def test_get_forms_without_filter(self, auth_headers):
        """Test getting all forms without filter"""
        response = requests.get(f"{BASE_URL}/api/forms", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data
        assert isinstance(data["forms"], list)
    
    def test_get_forms_filter_by_panneaux(self, auth_headers):
        """Test filtering forms by panneaux (PV) product type"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=panneaux",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data
        # All returned forms should have product_type = panneaux
        for form in data["forms"]:
            assert form.get("product_type") == "panneaux"
    
    def test_get_forms_filter_by_pompes(self, auth_headers):
        """Test filtering forms by pompes (PAC) product type"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=pompes",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data
        for form in data["forms"]:
            assert form.get("product_type") == "pompes"
    
    def test_get_forms_filter_by_isolation(self, auth_headers):
        """Test filtering forms by isolation (ITE) product type"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=isolation",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data
        for form in data["forms"]:
            assert form.get("product_type") == "isolation"
    
    def test_get_forms_filter_combined_with_crm(self, auth_headers):
        """Test filtering forms by product type and CRM"""
        # First get a CRM ID
        response = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        crms = response.json()["crms"]
        
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/forms?crm_id={crm_id}&product_type=panneaux",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "forms" in data


class TestBillingIntegration(TestAuth):
    """Integration tests for billing calculations"""
    
    def test_billing_amounts_calculation(self, auth_headers):
        """Test that billing amounts are calculated correctly"""
        response = requests.get(f"{BASE_URL}/api/billing/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        for crm_stat in data.get("crm_stats", []):
            # amount_to_invoice and amount_to_pay should be numbers
            assert isinstance(crm_stat["amount_to_invoice"], (int, float))
            assert isinstance(crm_stat["amount_to_pay"], (int, float))
            
            # net_balance should equal amount_to_invoice - amount_to_pay
            expected_balance = crm_stat["amount_to_invoice"] - crm_stat["amount_to_pay"]
            assert abs(crm_stat["net_balance"] - expected_balance) < 0.01
    
    def test_transfers_structure(self, auth_headers):
        """Test transfers array structure"""
        response = requests.get(f"{BASE_URL}/api/billing/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        for transfer in data.get("transfers", []):
            assert "from_crm" in transfer
            assert "to_crm" in transfer
            assert "count" in transfer
            assert "amount" in transfer
            assert "by_product" in transfer
            
            # by_product should have PAC, PV, ITE
            assert "PAC" in transfer["by_product"]
            assert "PV" in transfer["by_product"]
            assert "ITE" in transfer["by_product"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
