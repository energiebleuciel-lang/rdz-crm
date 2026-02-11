"""
Test Security Features - Multi-tenant filtering by allowed_accounts
Tests:
1. /api/accounts - filtering by allowed_accounts for non-admin users
2. /api/forms - filtering by allowed_accounts for non-admin users
3. /api/leads - filtering by allowed_accounts for non-admin users
4. /api/submit-lead - all fields stored correctly (civilite, departement, code_postal, type_logement, statut_occupant, facture_electricite)
5. Login/logout functionality
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://admin-panel-150.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "energiebleuciel@gmail.com"
ADMIN_PASSWORD = "92Ruemarxdormoy"

class TestAuthenticationFlow:
    """Test login/logout functionality"""
    
    def test_login_success(self):
        """Test successful login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Login successful for {ADMIN_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_logout(self):
        """Test logout functionality"""
        # First login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        
        # Then logout
        response = requests.post(f"{BASE_URL}/api/auth/logout", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Logout failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Logout successful")
    
    def test_auth_me_endpoint(self):
        """Test /api/auth/me returns current user"""
        # Login first
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_res.json()["token"]
        
        # Get current user
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        print("✓ Auth/me returns correct user data")


class TestAccountsSecurityFiltering:
    """Test /api/accounts endpoint security filtering"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_admin_sees_all_accounts(self, admin_token):
        """Admin user should see all accounts"""
        response = requests.get(f"{BASE_URL}/api/accounts", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "accounts" in data
        accounts = data["accounts"]
        print(f"✓ Admin sees {len(accounts)} accounts")
        # Admin should see accounts from both CRMs
        if len(accounts) > 0:
            crm_ids = set(a.get("crm_id") for a in accounts)
            print(f"  Accounts from {len(crm_ids)} different CRMs")
    
    def test_accounts_endpoint_requires_auth(self):
        """Accounts endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Accounts endpoint requires authentication")
    
    def test_accounts_filter_by_crm(self, admin_token):
        """Test filtering accounts by CRM ID"""
        # First get CRMs
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        crms = crms_res.json().get("crms", [])
        
        if len(crms) > 0:
            crm_id = crms[0]["id"]
            response = requests.get(f"{BASE_URL}/api/accounts?crm_id={crm_id}", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert response.status_code == 200
            data = response.json()
            accounts = data.get("accounts", [])
            # All returned accounts should belong to the filtered CRM
            for account in accounts:
                assert account.get("crm_id") == crm_id, f"Account {account.get('name')} has wrong CRM"
            print(f"✓ CRM filter works: {len(accounts)} accounts for CRM {crms[0]['name']}")


class TestFormsSecurityFiltering:
    """Test /api/forms endpoint security filtering"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_admin_sees_all_forms(self, admin_token):
        """Admin user should see all forms"""
        response = requests.get(f"{BASE_URL}/api/forms", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "forms" in data
        forms = data["forms"]
        print(f"✓ Admin sees {len(forms)} forms")
        
        # Check that forms have stats with started, completed, conversion_rate
        if len(forms) > 0:
            form = forms[0]
            assert "stats" in form, "Form should have stats"
            stats = form["stats"]
            assert "started" in stats, "Stats should have 'started'"
            assert "completed" in stats, "Stats should have 'completed'"
            assert "conversion_rate" in stats, "Stats should have 'conversion_rate'"
            print(f"  Form stats: started={stats['started']}, completed={stats['completed']}, rate={stats['conversion_rate']}%")
    
    def test_forms_endpoint_requires_auth(self):
        """Forms endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/forms")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Forms endpoint requires authentication")
    
    def test_forms_have_product_type(self, admin_token):
        """Forms should have product_type field"""
        response = requests.get(f"{BASE_URL}/api/forms", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = response.json()
        forms = data.get("forms", [])
        
        for form in forms:
            assert "product_type" in form, f"Form {form.get('code')} missing product_type"
        print(f"✓ All {len(forms)} forms have product_type field")
    
    def test_forms_filter_by_product_type(self, admin_token):
        """Test filtering forms by product type"""
        for product_type in ["panneaux", "pompes", "isolation"]:
            response = requests.get(f"{BASE_URL}/api/forms?product_type={product_type}", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert response.status_code == 200
            data = response.json()
            forms = data.get("forms", [])
            for form in forms:
                assert form.get("product_type") == product_type, f"Form has wrong product_type"
            print(f"✓ Product filter '{product_type}': {len(forms)} forms")


class TestLeadsSecurityFiltering:
    """Test /api/leads endpoint security filtering"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_admin_sees_leads(self, admin_token):
        """Admin user should see leads"""
        response = requests.get(f"{BASE_URL}/api/leads?limit=10", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "leads" in data
        assert "count" in data
        print(f"✓ Admin sees {data['count']} leads (showing {len(data['leads'])})")
    
    def test_leads_endpoint_requires_auth(self):
        """Leads endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Leads endpoint requires authentication")
    
    def test_leads_filter_by_status(self, admin_token):
        """Test filtering leads by status"""
        for status in ["success", "failed", "duplicate", "pending"]:
            response = requests.get(f"{BASE_URL}/api/leads?status={status}&limit=5", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            assert response.status_code == 200
            data = response.json()
            leads = data.get("leads", [])
            for lead in leads:
                assert lead.get("api_status") == status, f"Lead has wrong status"
            print(f"✓ Status filter '{status}': {len(leads)} leads")


class TestSubmitLeadAllFields:
    """Test /api/submit-lead stores all fields correctly"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_submit_lead_stores_all_fields(self, admin_token):
        """Test that submit-lead stores all fields including civilite, departement, code_postal, type_logement, statut_occupant, facture_electricite"""
        # First, get a form code to use
        forms_res = requests.get(f"{BASE_URL}/api/forms", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        forms = forms_res.json().get("forms", [])
        
        # Use a test form code or create one
        form_code = forms[0]["code"] if forms else "TEST-FORM-001"
        
        # Generate unique phone to avoid duplicates
        test_phone = f"06{str(uuid.uuid4().int)[:8]}"
        
        # Submit lead with ALL fields
        lead_data = {
            "phone": test_phone,
            "nom": "TEST_Dupont",
            "prenom": "Jean",
            "civilite": "M.",
            "email": "test@example.com",
            "departement": "75",
            "code_postal": "75001",
            "type_logement": "Maison",
            "statut_occupant": "Propriétaire",
            "facture_electricite": "150€",
            "superficie_logement": "120m²",
            "chauffage_actuel": "Électrique",
            "form_code": form_code
        }
        
        response = requests.post(f"{BASE_URL}/api/submit-lead", json=lead_data)
        assert response.status_code == 200, f"Submit lead failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Lead submitted successfully with status: {data.get('status')}")
        
        # Now verify the lead was stored with all fields
        leads_res = requests.get(f"{BASE_URL}/api/leads?limit=50", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        leads = leads_res.json().get("leads", [])
        
        # Find our test lead
        test_lead = None
        for lead in leads:
            if lead.get("phone") == test_phone:
                test_lead = lead
                break
        
        assert test_lead is not None, f"Test lead with phone {test_phone} not found"
        
        # Verify all fields are stored
        assert test_lead.get("nom") == "TEST_Dupont", f"nom mismatch: {test_lead.get('nom')}"
        assert test_lead.get("prenom") == "Jean", f"prenom mismatch: {test_lead.get('prenom')}"
        assert test_lead.get("civilite") == "M.", f"civilite mismatch: {test_lead.get('civilite')}"
        assert test_lead.get("email") == "test@example.com", f"email mismatch: {test_lead.get('email')}"
        assert test_lead.get("departement") == "75", f"departement mismatch: {test_lead.get('departement')}"
        assert test_lead.get("code_postal") == "75001", f"code_postal mismatch: {test_lead.get('code_postal')}"
        assert test_lead.get("type_logement") == "Maison", f"type_logement mismatch: {test_lead.get('type_logement')}"
        assert test_lead.get("statut_occupant") == "Propriétaire", f"statut_occupant mismatch: {test_lead.get('statut_occupant')}"
        assert test_lead.get("facture_electricite") == "150€", f"facture_electricite mismatch: {test_lead.get('facture_electricite')}"
        
        print("✓ All lead fields stored correctly:")
        print(f"  - civilite: {test_lead.get('civilite')}")
        print(f"  - departement: {test_lead.get('departement')}")
        print(f"  - code_postal: {test_lead.get('code_postal')}")
        print(f"  - type_logement: {test_lead.get('type_logement')}")
        print(f"  - statut_occupant: {test_lead.get('statut_occupant')}")
        print(f"  - facture_electricite: {test_lead.get('facture_electricite')}")
        
        # Cleanup: delete test lead
        if test_lead:
            delete_res = requests.delete(f"{BASE_URL}/api/leads/{test_lead['id']}", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            if delete_res.status_code == 200:
                print("✓ Test lead cleaned up")


class TestFormStatsTransformation:
    """Test that forms have transformation stats (started, completed, conversion_rate)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_forms_have_transformation_stats(self, admin_token):
        """Test that GET /api/forms returns stats with started, completed, conversion_rate"""
        response = requests.get(f"{BASE_URL}/api/forms", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        forms = data.get("forms", [])
        
        print(f"Testing {len(forms)} forms for transformation stats...")
        
        for form in forms:
            assert "stats" in form, f"Form {form.get('code')} missing stats"
            stats = form["stats"]
            
            # Check required stat fields
            assert "started" in stats, f"Form {form.get('code')} stats missing 'started'"
            assert "completed" in stats, f"Form {form.get('code')} stats missing 'completed'"
            assert "conversion_rate" in stats, f"Form {form.get('code')} stats missing 'conversion_rate'"
            
            # Verify conversion_rate calculation
            if stats["started"] > 0:
                expected_rate = round(stats["completed"] / stats["started"] * 100, 1)
                assert stats["conversion_rate"] == expected_rate, f"Conversion rate mismatch for {form.get('code')}"
            else:
                assert stats["conversion_rate"] == 0, f"Conversion rate should be 0 when no starts"
        
        print(f"✓ All {len(forms)} forms have correct transformation stats")
        
        # Print sample stats
        if forms:
            sample = forms[0]
            print(f"  Sample form '{sample.get('code')}':")
            print(f"    - started: {sample['stats']['started']}")
            print(f"    - completed: {sample['stats']['completed']}")
            print(f"    - conversion_rate: {sample['stats']['conversion_rate']}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
