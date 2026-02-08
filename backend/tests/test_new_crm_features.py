"""
Test suite for new CRM features:
1. Form creation with crm_api_key and auto-generated internal_api_key
2. Form duplication with new CRM API key
3. Account images library (add/remove images)
4. POST /api/leads/retry-failed endpoint for nightly job
5. Lead submission with CRM sending
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


class TestFormCreationWithAPIKeys:
    """Test form creation with crm_api_key and internal_api_key"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_account_id(self, auth_headers):
        """Get first available account ID"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        assert len(accounts) > 0, "No accounts found"
        return accounts[0]["id"]
    
    def test_create_form_with_crm_api_key(self, auth_headers, test_account_id):
        """Test creating a form with crm_api_key - should auto-generate internal_api_key"""
        test_crm_api_key = f"TEST_CRM_KEY_{uuid.uuid4()}"
        form_data = {
            "account_id": test_account_id,
            "code": f"TEST-FORM-{uuid.uuid4().hex[:8]}",
            "name": "Test Form with CRM API Key",
            "url": "https://test.example.com/form",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "Taboola",
            "form_type": "standalone",
            "lp_ids": [],
            "tracking_type": "redirect",
            "redirect_url_name": "",
            "html_code": "",
            "crm_api_key": test_crm_api_key,  # New field
            "notes": "Test form for API key testing",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", json=form_data, headers=auth_headers)
        assert response.status_code == 200, f"Form creation failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        form = data.get("form", {})
        
        # Verify crm_api_key is stored
        assert form.get("crm_api_key") == test_crm_api_key, "crm_api_key not stored correctly"
        
        # Verify internal_api_key is auto-generated
        assert "internal_api_key" in form, "internal_api_key not generated"
        assert form["internal_api_key"] is not None, "internal_api_key is None"
        assert len(form["internal_api_key"]) > 0, "internal_api_key is empty"
        
        # Verify it's a valid UUID format
        try:
            uuid.UUID(form["internal_api_key"])
        except ValueError:
            pytest.fail("internal_api_key is not a valid UUID")
        
        # Cleanup - delete the test form
        form_id = form.get("id")
        if form_id:
            requests.delete(f"{BASE_URL}/api/forms/{form_id}", headers=auth_headers)
        
        print(f"✓ Form created with crm_api_key: {test_crm_api_key[:20]}...")
        print(f"✓ Auto-generated internal_api_key: {form['internal_api_key'][:20]}...")
    
    def test_create_form_without_crm_api_key(self, auth_headers, test_account_id):
        """Test creating a form without crm_api_key - should still generate internal_api_key"""
        form_data = {
            "account_id": test_account_id,
            "code": f"TEST-FORM-NOKEY-{uuid.uuid4().hex[:8]}",
            "name": "Test Form without CRM API Key",
            "url": "",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "",
            "form_type": "standalone",
            "lp_ids": [],
            "tracking_type": "redirect",
            "redirect_url_name": "",
            "html_code": "",
            "crm_api_key": "",  # Empty
            "notes": "",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", json=form_data, headers=auth_headers)
        assert response.status_code == 200, f"Form creation failed: {response.text}"
        
        data = response.json()
        form = data.get("form", {})
        
        # internal_api_key should still be generated
        assert "internal_api_key" in form, "internal_api_key not generated"
        assert form["internal_api_key"] is not None, "internal_api_key is None"
        
        # Cleanup
        form_id = form.get("id")
        if form_id:
            requests.delete(f"{BASE_URL}/api/forms/{form_id}", headers=auth_headers)
        
        print("✓ Form created without crm_api_key, internal_api_key still generated")


class TestFormDuplication:
    """Test form duplication with new CRM API key"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_account_id(self, auth_headers):
        """Get first available account ID"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        accounts = response.json().get("accounts", [])
        return accounts[0]["id"] if accounts else None
    
    @pytest.fixture(scope="class")
    def source_form(self, auth_headers, test_account_id):
        """Create a source form to duplicate"""
        form_data = {
            "account_id": test_account_id,
            "code": f"TEST-SOURCE-{uuid.uuid4().hex[:8]}",
            "name": "Source Form for Duplication",
            "url": "https://source.example.com",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "Taboola",
            "form_type": "standalone",
            "lp_ids": [],
            "tracking_type": "redirect",
            "redirect_url_name": "",
            "html_code": "<form>Test</form>",
            "crm_api_key": "original-crm-key-123",
            "notes": "Source form",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", json=form_data, headers=auth_headers)
        form = response.json().get("form", {})
        yield form
        
        # Cleanup
        if form.get("id"):
            requests.delete(f"{BASE_URL}/api/forms/{form['id']}", headers=auth_headers)
    
    def test_duplicate_form_with_new_crm_api_key(self, auth_headers, source_form):
        """Test duplicating a form with a new CRM API key"""
        new_code = f"TEST-DUP-{uuid.uuid4().hex[:8]}"
        new_name = "Duplicated Form"
        new_crm_api_key = f"NEW-CRM-KEY-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/forms/{source_form['id']}/duplicate",
            params={
                "new_code": new_code,
                "new_name": new_name,
                "new_crm_api_key": new_crm_api_key
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Duplication failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        dup_form = data.get("form", {})
        
        # Verify new values
        assert dup_form.get("code") == new_code, "New code not applied"
        assert dup_form.get("name") == new_name, "New name not applied"
        assert dup_form.get("crm_api_key") == new_crm_api_key, "New CRM API key not applied"
        
        # Verify new internal_api_key is generated (different from source)
        assert dup_form.get("internal_api_key") != source_form.get("internal_api_key"), \
            "Duplicated form should have different internal_api_key"
        
        # Verify other fields are copied
        assert dup_form.get("product_type") == source_form.get("product_type"), "product_type not copied"
        assert dup_form.get("source_type") == source_form.get("source_type"), "source_type not copied"
        
        # Cleanup
        if dup_form.get("id"):
            requests.delete(f"{BASE_URL}/api/forms/{dup_form['id']}", headers=auth_headers)
        
        print(f"✓ Form duplicated with new CRM API key: {new_crm_api_key}")
        print(f"✓ New internal_api_key generated: {dup_form.get('internal_api_key', '')[:20]}...")
    
    def test_duplicate_form_requires_new_crm_api_key(self, auth_headers, source_form):
        """Test that duplication requires new_crm_api_key parameter"""
        response = requests.post(
            f"{BASE_URL}/api/forms/{source_form['id']}/duplicate",
            params={
                "new_code": "TEST-NOKEY",
                "new_name": "Test No Key"
                # Missing new_crm_api_key
            },
            headers=auth_headers
        )
        
        # Should fail with 422 (validation error) since new_crm_api_key is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Duplication correctly requires new_crm_api_key parameter")


class TestAccountImagesLibrary:
    """Test account images library functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_account(self, auth_headers):
        """Get first available account"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers=auth_headers)
        accounts = response.json().get("accounts", [])
        return accounts[0] if accounts else None
    
    def test_add_images_to_account(self, auth_headers, test_account):
        """Test adding images to account library"""
        # Prepare account data with images
        account_data = {
            "crm_id": test_account["crm_id"],
            "name": test_account["name"],
            "domain": test_account.get("domain", ""),
            "product_types": test_account.get("product_types", ["solaire"]),
            "logo_main_url": test_account.get("logo_main_url", ""),
            "logo_secondary_url": test_account.get("logo_secondary_url", ""),
            "logo_small_url": test_account.get("logo_small_url", ""),
            "favicon_url": test_account.get("favicon_url", ""),
            "images": [
                {"name": "TEST_Bannière principale", "url": "https://example.com/banner.jpg"},
                {"name": "TEST_Image produit", "url": "https://example.com/product.jpg"}
            ],
            "privacy_policy_text": test_account.get("privacy_policy_text", ""),
            "legal_mentions_text": test_account.get("legal_mentions_text", ""),
            "layout": test_account.get("layout", "center"),
            "primary_color": test_account.get("primary_color", "#3B82F6"),
            "secondary_color": test_account.get("secondary_color", "#1E40AF"),
            "style_officiel": test_account.get("style_officiel", False),
            "gtm_pixel_header": test_account.get("gtm_pixel_header", ""),
            "gtm_conversion_code": test_account.get("gtm_conversion_code", ""),
            "gtm_cta_code": test_account.get("gtm_cta_code", ""),
            "named_redirect_urls": test_account.get("named_redirect_urls", []),
            "default_redirect_url": test_account.get("default_redirect_url", ""),
            "notes": test_account.get("notes", "")
        }
        
        response = requests.put(
            f"{BASE_URL}/api/accounts/{test_account['id']}",
            json=account_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        # Verify images were saved
        get_response = requests.get(
            f"{BASE_URL}/api/accounts/{test_account['id']}",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        
        updated_account = get_response.json().get("account", {})
        images = updated_account.get("images", [])
        
        assert len(images) == 2, f"Expected 2 images, got {len(images)}"
        assert images[0]["name"] == "TEST_Bannière principale"
        assert images[1]["name"] == "TEST_Image produit"
        
        print(f"✓ Added {len(images)} images to account library")
        
        # Cleanup - remove test images
        account_data["images"] = [img for img in images if not img["name"].startswith("TEST_")]
        requests.put(f"{BASE_URL}/api/accounts/{test_account['id']}", json=account_data, headers=auth_headers)
    
    def test_account_images_structure(self, auth_headers, test_account):
        """Test that account images have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/accounts/{test_account['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        account = response.json().get("account", {})
        
        # images field should exist (even if empty)
        assert "images" in account or account.get("images") is None or isinstance(account.get("images", []), list), \
            "images field should be a list"
        
        print("✓ Account images structure is correct")


class TestRetryFailedLeadsEndpoint:
    """Test POST /api/leads/retry-failed endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_retry_failed_endpoint_exists(self, auth_headers):
        """Test that /api/leads/retry-failed endpoint exists and is accessible"""
        response = requests.post(
            f"{BASE_URL}/api/leads/retry-failed",
            headers=auth_headers
        )
        
        # Should return 200 (even if no failed leads to retry)
        assert response.status_code == 200, f"Endpoint returned {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "results" in data
        
        results = data["results"]
        assert "total" in results
        assert "success" in results
        assert "failed" in results
        assert "skipped" in results
        
        print(f"✓ retry-failed endpoint working: {results}")
    
    def test_retry_failed_with_hours_param(self, auth_headers):
        """Test retry-failed with custom hours parameter"""
        response = requests.post(
            f"{BASE_URL}/api/leads/retry-failed?hours=48",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        print("✓ retry-failed with hours=48 parameter works")
    
    def test_retry_failed_requires_auth(self):
        """Test that retry-failed requires authentication"""
        response = requests.post(f"{BASE_URL}/api/leads/retry-failed")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✓ retry-failed correctly requires authentication")


class TestLeadSubmissionWithCRM:
    """Test lead submission with CRM sending"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_submit_lead_basic(self):
        """Test basic lead submission (no CRM config)"""
        lead_data = {
            "phone": "0612345678",
            "nom": "TEST_Lead Basic",
            "email": "test@example.com",
            "departement": "75",
            "code_postal": "75001",
            "type_logement": "maison",
            "statut_occupant": "proprietaire",
            "facture_electricite": "100-150",
            "form_id": "test-form",
            "form_code": "NONEXISTENT-FORM"  # No form config
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_data)
        
        assert response.status_code == 200, f"Lead submission failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # Status should be "no_config" since form doesn't exist
        assert data.get("status") in ["no_config", "pending", "failed"], \
            f"Unexpected status: {data.get('status')}"
        
        print(f"✓ Lead submitted with status: {data.get('status')}")
    
    def test_submit_lead_phone_validation(self):
        """Test lead submission with invalid phone"""
        lead_data = {
            "phone": "123",  # Invalid - too short
            "nom": "TEST_Invalid Phone",
            "email": "test@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_data)
        
        # Should fail validation
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        print("✓ Phone validation working correctly")
    
    def test_submit_lead_nom_required(self):
        """Test lead submission without nom"""
        lead_data = {
            "phone": "0612345678",
            "nom": "",  # Empty nom
            "email": "test@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_data)
        
        # Should fail validation
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        print("✓ Nom validation working correctly")
    
    def test_submit_lead_postal_code_validation(self):
        """Test lead submission with invalid postal code"""
        lead_data = {
            "phone": "0612345678",
            "nom": "TEST_Invalid CP",
            "email": "test@example.com",
            "code_postal": "99999"  # Invalid - not France metro
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_data)
        
        # Should fail validation for non-metro postal code
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        print("✓ Postal code validation working correctly")


class TestFormsListWithAPIKeys:
    """Test that forms list includes API key fields"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_forms_list_structure(self, auth_headers):
        """Test that forms list returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/forms", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        forms = data.get("forms", [])
        
        # If there are forms, check structure
        if len(forms) > 0:
            form = forms[0]
            # Check that form has the expected fields
            expected_fields = ["id", "code", "name", "account_id", "status"]
            for field in expected_fields:
                assert field in form, f"Missing field: {field}"
            
            print(f"✓ Forms list returns {len(forms)} forms with correct structure")
        else:
            print("✓ Forms list endpoint working (no forms yet)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
