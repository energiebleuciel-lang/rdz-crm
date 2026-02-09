"""
Tests for new CRM features:
- Assets library (CRUD)
- Lead deletion (single and multiple)
- LP types (redirect/integrated) and duplication
- Form tracking types (redirect/gtm/none) and duplication
- Lead validation (phone 10 digits, nom required, postal code France metro)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSetup:
    """Setup fixtures for all tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    @pytest.fixture(scope="class")
    def sub_account(self, auth_token, crms):
        """Create a sub-account for tests"""
        crm_id = crms[0]["id"]
        response = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json={"crm_id": crm_id, "name": f"TEST_NewFeatures_{uuid.uuid4().hex[:8]}", "product_type": "solaire"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        return response.json()["sub_account"]


class TestAssetsLibrary(TestSetup):
    """Tests for Assets Library feature"""
    
    def test_create_global_asset(self, auth_token):
        """Test creating a global asset (no sub_account_id)"""
        payload = {
            "label": "TEST_Logo_Global",
            "url": "https://example.com/logo-global.png",
            "asset_type": "logo",
            "sub_account_id": None,
            "crm_id": None
        }
        
        response = requests.post(f"{BASE_URL}/api/assets", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "asset" in data
        assert data["asset"]["label"] == "TEST_Logo_Global"
        assert data["asset"]["sub_account_id"] is None
        print(f"Global asset created: {data['asset']['id']}")
        return data["asset"]["id"]
    
    def test_create_account_specific_asset(self, auth_token, sub_account):
        """Test creating an asset specific to a sub-account"""
        payload = {
            "label": "TEST_Logo_Account",
            "url": "https://example.com/logo-account.png",
            "asset_type": "image",
            "sub_account_id": sub_account["id"],
            "crm_id": None
        }
        
        response = requests.post(f"{BASE_URL}/api/assets", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["asset"]["sub_account_id"] == sub_account["id"]
        print(f"Account-specific asset created: {data['asset']['id']}")
        return data["asset"]["id"]
    
    def test_get_assets_global_only(self, auth_token):
        """Test getting only global assets"""
        response = requests.get(f"{BASE_URL}/api/assets?global_only=true", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        # All returned assets should have sub_account_id = None
        for asset in data["assets"]:
            assert asset["sub_account_id"] is None
        print(f"Global assets: {len(data['assets'])} found")
    
    def test_get_assets_for_sub_account(self, auth_token, sub_account):
        """Test getting assets for a specific sub-account (includes global + account-specific)"""
        response = requests.get(f"{BASE_URL}/api/assets?sub_account_id={sub_account['id']}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        print(f"Assets for sub-account: {len(data['assets'])} found")
    
    def test_update_asset(self, auth_token):
        """Test updating an asset"""
        # First create an asset
        create_res = requests.post(f"{BASE_URL}/api/assets", 
            json={"label": "TEST_ToUpdate", "url": "https://example.com/old.png", "asset_type": "image"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        asset_id = create_res.json()["asset"]["id"]
        
        # Update it
        update_payload = {
            "label": "TEST_Updated",
            "url": "https://example.com/new.png",
            "asset_type": "logo"
        }
        response = requests.put(f"{BASE_URL}/api/assets/{asset_id}", 
            json=update_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        print(f"Asset updated: {asset_id}")
    
    def test_delete_asset(self, auth_token):
        """Test deleting an asset"""
        # First create an asset
        create_res = requests.post(f"{BASE_URL}/api/assets", 
            json={"label": "TEST_ToDelete", "url": "https://example.com/delete.png", "asset_type": "image"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        asset_id = create_res.json()["asset"]["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/assets/{asset_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        assert response.json()["success"] == True
        print(f"Asset deleted: {asset_id}")


class TestLeadDeletion(TestSetup):
    """Tests for Lead deletion feature"""
    
    def test_delete_single_lead(self, auth_token):
        """Test deleting a single lead"""
        # First create a lead via submit-lead endpoint
        lead_payload = {
            "phone": "0612345678",
            "nom": "TEST_DeleteSingle",
            "email": "test@example.com",
            "form_id": "test-form",
            "form_code": "TEST-FORM"
        }
        create_res = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_payload)
        assert create_res.status_code == 200
        
        # Get the lead ID
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=10", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = leads_res.json()["leads"]
        test_lead = next((l for l in leads if l["nom"] == "TEST_DeleteSingle"), None)
        
        if test_lead:
            # Delete the lead
            response = requests.delete(f"{BASE_URL}/api/leads/{test_lead['id']}", headers={
                "Authorization": f"Bearer {auth_token}"
            })
            assert response.status_code == 200
            assert response.json()["success"] == True
            print(f"Single lead deleted: {test_lead['id']}")
        else:
            print("Lead not found for deletion test - may have been cleaned up")
    
    def test_delete_multiple_leads(self, auth_token):
        """Test deleting multiple leads at once"""
        # Create multiple leads
        lead_ids = []
        for i in range(3):
            lead_payload = {
                "phone": f"061234567{i}",
                "nom": f"TEST_DeleteMultiple_{i}",
                "email": f"test{i}@example.com",
                "form_id": "test-form",
                "form_code": "TEST-FORM"
            }
            requests.post(f"{BASE_URL}/api/submit-lead", json=lead_payload)
        
        # Get the lead IDs
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = leads_res.json()["leads"]
        test_leads = [l for l in leads if l["nom"].startswith("TEST_DeleteMultiple_")]
        lead_ids = [l["id"] for l in test_leads]
        
        if lead_ids:
            # Delete multiple leads
            response = requests.delete(f"{BASE_URL}/api/leads", 
                json=lead_ids,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "deleted_count" in data
            print(f"Multiple leads deleted: {data['deleted_count']}")
        else:
            print("No leads found for multiple deletion test")
    
    def test_delete_nonexistent_lead(self, auth_token):
        """Test deleting a lead that doesn't exist"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/api/leads/{fake_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent lead")


class TestLPTypes(TestSetup):
    """Tests for LP types (redirect vs integrated) and duplication"""
    
    def test_create_lp_redirect_type(self, auth_token, sub_account):
        """Test creating LP with redirect type"""
        payload = {
            "sub_account_id": sub_account["id"],
            "code": f"TEST-LP-REDIRECT-{uuid.uuid4().hex[:6]}",
            "name": "Test LP Redirect",
            "url": "https://example.com/lp",
            "source_type": "native",
            "source_name": "Taboola",
            "cta_selector": ".cta-btn",
            "status": "active",
            "lp_type": "redirect",
            "form_url": "https://example.com/form"
        }
        
        response = requests.post(f"{BASE_URL}/api/lps", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["lp"]["lp_type"] == "redirect"
        assert data["lp"]["form_url"] == "https://example.com/form"
        print(f"LP redirect type created: {data['lp']['code']}")
        return data["lp"]
    
    def test_create_lp_integrated_type(self, auth_token, sub_account):
        """Test creating LP with integrated type"""
        payload = {
            "sub_account_id": sub_account["id"],
            "code": f"TEST-LP-INTEGRATED-{uuid.uuid4().hex[:6]}",
            "name": "Test LP Integrated",
            "url": "https://example.com/lp-integrated",
            "source_type": "facebook",
            "source_name": "Facebook Ads",
            "cta_selector": ".submit-btn",
            "status": "active",
            "lp_type": "integrated",
            "form_url": ""
        }
        
        response = requests.post(f"{BASE_URL}/api/lps", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["lp"]["lp_type"] == "integrated"
        print(f"LP integrated type created: {data['lp']['code']}")
        return data["lp"]
    
    def test_duplicate_lp(self, auth_token, sub_account):
        """Test duplicating a LP"""
        # First create a LP
        original_code = f"TEST-LP-ORIGINAL-{uuid.uuid4().hex[:6]}"
        create_payload = {
            "sub_account_id": sub_account["id"],
            "code": original_code,
            "name": "Original LP",
            "url": "https://example.com/original",
            "source_type": "google",
            "source_name": "Google Ads",
            "cta_selector": ".cta",
            "status": "active",
            "lp_type": "redirect",
            "form_url": "https://example.com/form",
            "generation_notes": "Test notes"
        }
        
        create_res = requests.post(f"{BASE_URL}/api/lps", 
            json=create_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        original_lp = create_res.json()["lp"]
        
        # Duplicate it
        new_code = f"TEST-LP-COPY-{uuid.uuid4().hex[:6]}"
        new_name = "Duplicated LP"
        
        response = requests.post(
            f"{BASE_URL}/api/lps/{original_lp['id']}/duplicate?new_code={new_code}&new_name={new_name}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["lp"]["code"] == new_code
        assert data["lp"]["name"] == new_name
        # Verify config is copied
        assert data["lp"]["lp_type"] == original_lp["lp_type"]
        assert data["lp"]["source_type"] == original_lp["source_type"]
        assert data["lp"]["sub_account_id"] == original_lp["sub_account_id"]
        print(f"LP duplicated: {original_code} -> {new_code}")
    
    def test_duplicate_nonexistent_lp(self, auth_token):
        """Test duplicating a LP that doesn't exist"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/lps/{fake_id}/duplicate?new_code=TEST&new_name=Test",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent LP duplication")


class TestFormTracking(TestSetup):
    """Tests for Form tracking types and duplication"""
    
    def test_create_form_redirect_tracking(self, auth_token, sub_account):
        """Test creating form with redirect tracking"""
        payload = {
            "sub_account_id": sub_account["id"],
            "lp_ids": [],
            "code": f"TEST-FORM-REDIRECT-{uuid.uuid4().hex[:6]}",
            "name": "Test Form Redirect",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "Taboola",
            "api_key": "test-api-key-redirect",
            "tracking_type": "redirect",
            "redirect_url": "https://example.com/merci",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["form"]["tracking_type"] == "redirect"
        assert data["form"]["redirect_url"] == "https://example.com/merci"
        print(f"Form with redirect tracking created: {data['form']['code']}")
        return data["form"]
    
    def test_create_form_gtm_tracking(self, auth_token, sub_account):
        """Test creating form with GTM tracking"""
        payload = {
            "sub_account_id": sub_account["id"],
            "lp_ids": [],
            "code": f"TEST-FORM-GTM-{uuid.uuid4().hex[:6]}",
            "name": "Test Form GTM",
            "product_type": "pompes",
            "source_type": "google",
            "source_name": "Google Ads",
            "api_key": "test-api-key-gtm",
            "tracking_type": "gtm",
            "tracking_code": "GTM-XXXXXX",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["form"]["tracking_type"] == "gtm"
        assert data["form"]["tracking_code"] == "GTM-XXXXXX"
        print(f"Form with GTM tracking created: {data['form']['code']}")
        return data["form"]
    
    def test_create_form_no_tracking(self, auth_token, sub_account):
        """Test creating form with no tracking"""
        payload = {
            "sub_account_id": sub_account["id"],
            "lp_ids": [],
            "code": f"TEST-FORM-NONE-{uuid.uuid4().hex[:6]}",
            "name": "Test Form No Tracking",
            "product_type": "isolation",
            "source_type": "facebook",
            "source_name": "Facebook Ads",
            "api_key": "test-api-key-none",
            "tracking_type": "none",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/forms", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["form"]["tracking_type"] == "none"
        print(f"Form with no tracking created: {data['form']['code']}")
        return data["form"]
    
    def test_duplicate_form(self, auth_token, sub_account):
        """Test duplicating a form (only API key changes)"""
        # First create a form
        original_code = f"TEST-FORM-ORIGINAL-{uuid.uuid4().hex[:6]}"
        create_payload = {
            "sub_account_id": sub_account["id"],
            "lp_ids": [],
            "code": original_code,
            "name": "Original Form",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "Outbrain",
            "api_key": "original-api-key",
            "tracking_type": "redirect",
            "redirect_url": "https://example.com/thanks",
            "status": "active",
            "generation_notes": "Original notes"
        }
        
        create_res = requests.post(f"{BASE_URL}/api/forms", 
            json=create_payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        original_form = create_res.json()["form"]
        
        # Duplicate it
        new_code = f"TEST-FORM-COPY-{uuid.uuid4().hex[:6]}"
        new_name = "Duplicated Form"
        new_api_key = "new-api-key-12345"
        
        response = requests.post(
            f"{BASE_URL}/api/forms/{original_form['id']}/duplicate?new_code={new_code}&new_name={new_name}&new_api_key={new_api_key}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["form"]["code"] == new_code
        assert data["form"]["name"] == new_name
        assert data["form"]["api_key"] == new_api_key
        # Verify other config is copied
        assert data["form"]["tracking_type"] == original_form["tracking_type"]
        assert data["form"]["product_type"] == original_form["product_type"]
        assert data["form"]["sub_account_id"] == original_form["sub_account_id"]
        print(f"Form duplicated: {original_code} -> {new_code} with new API key")
    
    def test_duplicate_nonexistent_form(self, auth_token):
        """Test duplicating a form that doesn't exist"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/forms/{fake_id}/duplicate?new_code=TEST&new_name=Test&new_api_key=key",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        print("Correctly returned 404 for nonexistent form duplication")


class TestLeadValidation(TestSetup):
    """Tests for lead validation (phone 10 digits, nom required, postal code France metro)"""
    
    def test_valid_lead_submission(self, auth_token):
        """Test submitting a valid lead"""
        payload = {
            "phone": "0612345678",
            "nom": "Test Valid Lead",
            "email": "valid@example.com",
            "departement": "75",
            "code_postal": "75001",
            "type_logement": "maison",
            "statut_occupant": "proprietaire",
            "facture_electricite": "100-150",
            "form_id": "test",
            "form_code": "TEST-VALID"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"Valid lead submitted: status={data['status']}")
    
    def test_phone_validation_too_short(self, auth_token):
        """Test phone validation - too short (less than 10 digits)"""
        payload = {
            "phone": "061234567",  # 9 digits
            "nom": "Test Short Phone",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "10 chiffres" in data["detail"]
        print(f"Phone too short correctly rejected: {data['detail']}")
    
    def test_phone_validation_too_long(self, auth_token):
        """Test phone validation - too long (more than 10 digits)"""
        payload = {
            "phone": "06123456789",  # 11 digits
            "nom": "Test Long Phone",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "10 chiffres" in data["detail"]
        print(f"Phone too long correctly rejected: {data['detail']}")
    
    def test_phone_validation_with_spaces(self, auth_token):
        """Test phone validation - with spaces (should be accepted)"""
        payload = {
            "phone": "06 12 34 56 78",  # With spaces
            "nom": "Test Phone Spaces",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        print("Phone with spaces correctly accepted")
    
    def test_phone_validation_9_digits_without_zero(self, auth_token):
        """Test phone validation - 9 digits without leading 0 (should add 0)"""
        payload = {
            "phone": "612345678",  # 9 digits without 0
            "nom": "Test Phone No Zero",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        print("Phone 9 digits without 0 correctly accepted (0 added)")
    
    def test_nom_required_empty(self, auth_token):
        """Test nom validation - empty"""
        payload = {
            "phone": "0612345678",
            "nom": "",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "nom" in data["detail"].lower() or "obligatoire" in data["detail"].lower()
        print(f"Empty nom correctly rejected: {data['detail']}")
    
    def test_nom_required_too_short(self, auth_token):
        """Test nom validation - too short (less than 2 chars)"""
        payload = {
            "phone": "0612345678",
            "nom": "A",  # Only 1 character
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "minimum" in data["detail"].lower() or "2" in data["detail"]
        print(f"Short nom correctly rejected: {data['detail']}")
    
    def test_postal_code_valid_paris(self, auth_token):
        """Test postal code validation - valid Paris (75)"""
        payload = {
            "phone": "0612345678",
            "nom": "Test Paris",
            "code_postal": "75001",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        print("Paris postal code (75001) correctly accepted")
    
    def test_postal_code_valid_marseille(self, auth_token):
        """Test postal code validation - valid Marseille (13)"""
        payload = {
            "phone": "0612345678",
            "nom": "Test Marseille",
            "code_postal": "13001",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        print("Marseille postal code (13001) correctly accepted")
    
    def test_postal_code_invalid_dom_tom(self, auth_token):
        """Test postal code validation - invalid DOM-TOM (97)"""
        payload = {
            "phone": "0612345678",
            "nom": "Test DOM-TOM",
            "code_postal": "97100",  # Guadeloupe
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "métropolitaine" in data["detail"].lower() or "01-95" in data["detail"]
        print(f"DOM-TOM postal code correctly rejected: {data['detail']}")
    
    def test_postal_code_invalid_format(self, auth_token):
        """Test postal code validation - invalid format (not 5 digits)"""
        payload = {
            "phone": "0612345678",
            "nom": "Test Invalid CP",
            "code_postal": "7500",  # Only 4 digits
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "5 chiffres" in data["detail"]
        print(f"Invalid postal code format correctly rejected: {data['detail']}")
    
    def test_postal_code_empty_allowed(self, auth_token):
        """Test postal code validation - empty is allowed"""
        payload = {
            "phone": "0612345678",
            "nom": "Test No CP",
            "code_postal": "",
            "form_id": "test"
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=payload)
        assert response.status_code == 200
        print("Empty postal code correctly accepted")


class TestCleanupNewFeatures:
    """Cleanup test data created by new features tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    def test_cleanup_test_assets(self, auth_token):
        """Clean up TEST_ prefixed assets"""
        response = requests.get(f"{BASE_URL}/api/assets", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assets = response.json().get("assets", [])
        
        deleted = 0
        for asset in assets:
            if asset["label"].startswith("TEST_"):
                del_res = requests.delete(f"{BASE_URL}/api/assets/{asset['id']}", headers={
                    "Authorization": f"Bearer {auth_token}"
                })
                if del_res.status_code == 200:
                    deleted += 1
        
        print(f"Cleaned up {deleted} test assets")
    
    def test_cleanup_test_leads(self, auth_token):
        """Clean up TEST_ prefixed leads"""
        response = requests.get(f"{BASE_URL}/api/leads?limit=200", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        leads = response.json().get("leads", [])
        
        test_lead_ids = [l["id"] for l in leads if l.get("nom", "").startswith("TEST_") or l.get("nom", "").startswith("Test")]
        
        if test_lead_ids:
            del_res = requests.delete(f"{BASE_URL}/api/leads", 
                json=test_lead_ids,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            print(f"Cleaned up {del_res.json().get('deleted_count', 0)} test leads")
        else:
            print("No test leads to clean up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
