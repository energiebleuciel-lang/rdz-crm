"""
Tests for CRM Refactoring Features:
- API /api/accounts - returns 6 default accounts (MDL, ZR7, SPOOT, AZ, OBJECTIF ACADEMIE, AUDIT GREEN)
- API DELETE /api/leads/{id} - single lead deletion
- API POST /api/leads/bulk-delete - bulk lead deletion with body {lead_ids: [...]}
- Frontend terminology: 'Compte' instead of 'Sous-compte'
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "energiebleuciel@gmail.com"
        print("Login successful")


class TestAccountsAPI(TestAuth):
    """Tests for /api/accounts endpoint - should return 6 default accounts"""
    
    def test_get_accounts_returns_6_accounts(self, auth_token):
        """Test that /api/accounts returns exactly 6 default accounts"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        accounts = data["accounts"]
        
        # Should have exactly 6 accounts
        assert len(accounts) == 6, f"Expected 6 accounts, got {len(accounts)}"
        
        # Get account names
        account_names = [acc["name"] for acc in accounts]
        print(f"Found accounts: {account_names}")
        
        # Verify all expected accounts exist
        expected_accounts = ["MDL", "ZR7", "SPOOT", "AZ", "OBJECTIF ACADEMIE", "AUDIT GREEN"]
        for expected in expected_accounts:
            assert expected in account_names, f"Missing account: {expected}"
        
        print(f"All 6 expected accounts found: {expected_accounts}")
    
    def test_accounts_have_required_fields(self, auth_token):
        """Test that accounts have required fields"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        accounts = response.json()["accounts"]
        
        for account in accounts:
            assert "id" in account, f"Account missing 'id': {account}"
            assert "name" in account, f"Account missing 'name': {account}"
            assert "crm_id" in account, f"Account missing 'crm_id': {account}"
            assert "product_types" in account, f"Account missing 'product_types': {account}"
        
        print("All accounts have required fields")
    
    def test_accounts_linked_to_correct_crms(self, auth_token):
        """Test that accounts are linked to correct CRMs (MDL or ZR7)"""
        # Get CRMs first
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        crms = crms_res.json()["crms"]
        crm_map = {crm["id"]: crm["name"] for crm in crms}
        
        # Get accounts
        accounts_res = requests.get(f"{BASE_URL}/api/accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        accounts = accounts_res.json()["accounts"]
        
        # MDL accounts: MDL, SPOOT, OBJECTIF ACADEMIE, AUDIT GREEN
        # ZR7 accounts: ZR7, AZ
        mdl_accounts = ["MDL", "SPOOT", "OBJECTIF ACADEMIE", "AUDIT GREEN"]
        zr7_accounts = ["ZR7", "AZ"]
        
        for account in accounts:
            crm_name = crm_map.get(account["crm_id"], "Unknown")
            if account["name"] in mdl_accounts:
                assert "Maison du Lead" in crm_name or "mdl" in crm_name.lower(), \
                    f"Account {account['name']} should be linked to MDL CRM, got {crm_name}"
            elif account["name"] in zr7_accounts:
                assert "ZR7" in crm_name or "zr7" in crm_name.lower(), \
                    f"Account {account['name']} should be linked to ZR7 CRM, got {crm_name}"
        
        print("All accounts linked to correct CRMs")


class TestLeadDeletionAPI(TestAuth):
    """Tests for lead deletion APIs"""
    
    def test_delete_single_lead(self, auth_token):
        """Test DELETE /api/leads/{id} - single lead deletion"""
        # Create a test lead
        create_res = requests.post(f"{BASE_URL}/api/submit-lead", json={
            "phone": "0612345678",
            "nom": "TEST_SingleDelete",
            "email": "test@example.com",
            "form_id": "test",
            "form_code": "TEST-FORM"
        })
        assert create_res.status_code == 200, f"Failed to create lead: {create_res.text}"
        
        # Get the lead ID
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = leads_res.json()["leads"]
        test_lead = next((l for l in leads if l["nom"] == "TEST_SingleDelete"), None)
        assert test_lead is not None, "Test lead not found"
        
        lead_id = test_lead["id"]
        
        # Delete the lead
        delete_res = requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert delete_res.status_code == 200, f"Delete failed: {delete_res.text}"
        data = delete_res.json()
        assert data["success"] == True
        
        # Verify lead is deleted
        verify_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = verify_res.json()["leads"]
        deleted_lead = next((l for l in leads if l["id"] == lead_id), None)
        assert deleted_lead is None, "Lead was not deleted"
        
        print(f"Single lead deletion successful: {lead_id}")
    
    def test_delete_nonexistent_lead_returns_404(self, auth_token):
        """Test DELETE /api/leads/{id} with nonexistent ID returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/api/leads/{fake_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returned 404 for nonexistent lead")
    
    def test_bulk_delete_leads(self, auth_token):
        """Test POST /api/leads/bulk-delete with body {lead_ids: [...]}"""
        # Create multiple test leads
        lead_ids = []
        for i in range(3):
            create_res = requests.post(f"{BASE_URL}/api/submit-lead", json={
                "phone": f"061234567{i}",
                "nom": f"TEST_BulkDelete_{i}",
                "email": f"test{i}@example.com",
                "form_id": "test",
                "form_code": "TEST-FORM"
            })
            assert create_res.status_code == 200
        
        # Get the lead IDs
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = leads_res.json()["leads"]
        test_leads = [l for l in leads if l["nom"].startswith("TEST_BulkDelete_")]
        lead_ids = [l["id"] for l in test_leads]
        
        assert len(lead_ids) >= 3, f"Expected at least 3 test leads, got {len(lead_ids)}"
        
        # Bulk delete
        bulk_delete_res = requests.post(f"{BASE_URL}/api/leads/bulk-delete", 
            json={"lead_ids": lead_ids},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert bulk_delete_res.status_code == 200, f"Bulk delete failed: {bulk_delete_res.text}"
        data = bulk_delete_res.json()
        assert data["success"] == True
        assert "deleted_count" in data
        assert data["deleted_count"] >= 3
        
        # Verify leads are deleted
        verify_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = verify_res.json()["leads"]
        remaining = [l for l in leads if l["id"] in lead_ids]
        assert len(remaining) == 0, f"Some leads were not deleted: {remaining}"
        
        print(f"Bulk delete successful: {data['deleted_count']} leads deleted")
    
    def test_bulk_delete_empty_list(self, auth_token):
        """Test POST /api/leads/bulk-delete with empty list"""
        response = requests.post(f"{BASE_URL}/api/leads/bulk-delete", 
            json={"lead_ids": []},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["deleted_count"] == 0
        print("Bulk delete with empty list handled correctly")
    
    def test_bulk_delete_with_invalid_ids(self, auth_token):
        """Test POST /api/leads/bulk-delete with some invalid IDs"""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = requests.post(f"{BASE_URL}/api/leads/bulk-delete", 
            json={"lead_ids": fake_ids},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["deleted_count"] == 0  # No leads should be deleted
        print("Bulk delete with invalid IDs handled correctly")


class TestBackwardsCompatibility(TestAuth):
    """Tests for backwards compatibility with old sub-accounts endpoints"""
    
    def test_sub_accounts_endpoint_still_works(self, auth_token):
        """Test that /api/sub-accounts still works for backwards compatibility"""
        response = requests.get(f"{BASE_URL}/api/sub-accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        # Should return both sub_accounts and accounts for compatibility
        assert "accounts" in data or "sub_accounts" in data
        print("Backwards compatibility: /api/sub-accounts still works")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    def test_cleanup_test_leads(self, auth_token):
        """Clean up any remaining TEST_ prefixed leads"""
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=200", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = leads_res.json().get("leads", [])
        
        test_lead_ids = [l["id"] for l in leads if l.get("nom", "").startswith("TEST_")]
        
        if test_lead_ids:
            del_res = requests.post(f"{BASE_URL}/api/leads/bulk-delete", 
                json={"lead_ids": test_lead_ids},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            print(f"Cleaned up {del_res.json().get('deleted_count', 0)} test leads")
        else:
            print("No test leads to clean up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
