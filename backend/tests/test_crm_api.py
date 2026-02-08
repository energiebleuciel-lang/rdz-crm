"""
CRM Multi-tenant API Tests
Tests for: Auth, CRMs, Sub-accounts, LPs, Forms, Leads, Analytics
All endpoints with CRM filtering
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_api_root(self):
        """Test API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CRM API OK"
        print(f"API root OK: {data}")
    
    def test_init_admin(self):
        """Test init admin - may fail if already exists"""
        response = requests.post(f"{BASE_URL}/api/auth/init-admin")
        # Either 200 (created) or 400 (already exists)
        assert response.status_code in [200, 400]
        print(f"Init admin response: {response.json()}")
    
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
        print(f"Login success: user={data['user']['nom']}, role={data['user']['role']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("Invalid login correctly rejected")
    
    def test_auth_me(self):
        """Test get current user"""
        # First login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        token = login_res.json()["token"]
        
        # Get me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "energiebleuciel@gmail.com"
        print(f"Auth me OK: {data}")


class TestCRMs:
    """CRM endpoints tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    def test_init_crms(self, auth_token):
        """Test init CRMs - may already exist"""
        response = requests.post(f"{BASE_URL}/api/crms/init", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        # Either 200 (created) or 200 (already exists)
        assert response.status_code == 200
        print(f"Init CRMs response: {response.json()}")
    
    def test_get_crms(self, auth_token):
        """Test get all CRMs"""
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "crms" in data
        assert len(data["crms"]) >= 2  # Maison du Lead and ZR7 Digital
        
        crm_names = [c["name"] for c in data["crms"]]
        assert "Maison du Lead" in crm_names
        assert "ZR7 Digital" in crm_names
        print(f"CRMs found: {crm_names}")
        return data["crms"]


class TestSubAccounts:
    """Sub-account endpoints tests with CRM filtering"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    def test_get_sub_accounts_no_filter(self, auth_token):
        """Test get all sub-accounts without CRM filter"""
        response = requests.get(f"{BASE_URL}/api/sub-accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "sub_accounts" in data
        print(f"Sub-accounts (no filter): {len(data['sub_accounts'])} found")
    
    def test_get_sub_accounts_with_crm_filter(self, auth_token, crms):
        """Test get sub-accounts filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/sub-accounts?crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "sub_accounts" in data
        
        # Verify all returned sub-accounts belong to the filtered CRM
        for account in data["sub_accounts"]:
            assert account["crm_id"] == crm_id
        print(f"Sub-accounts for CRM {crms[0]['name']}: {len(data['sub_accounts'])} found")
    
    def test_create_sub_account(self, auth_token, crms):
        """Test create sub-account with all new fields"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        payload = {
            "crm_id": crm_id,
            "name": "TEST_SubAccount_Solaire",
            "domain": "test-solaire.fr",
            "product_type": "solaire",
            "logo_left_url": "https://example.com/logo-left.png",
            "logo_right_url": "https://example.com/logo-right.png",
            "favicon_url": "https://example.com/favicon.ico",
            "privacy_policy_text": "Politique de confidentialité test...",
            "legal_mentions_text": "Mentions légales test...",
            "layout": "center",
            "primary_color": "#3B82F6",
            "tracking_pixel_header": "<!-- Test Pixel -->",
            "tracking_cta_code": "",
            "tracking_conversion_type": "redirect",
            "tracking_conversion_code": "",
            "tracking_redirect_url": "https://example.com/merci",
            "notes": "Test sub-account"
        }
        
        response = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "sub_account" in data
        
        # Verify all fields
        account = data["sub_account"]
        assert account["name"] == payload["name"]
        assert account["product_type"] == "solaire"
        assert account["logo_left_url"] == payload["logo_left_url"]
        assert account["logo_right_url"] == payload["logo_right_url"]
        assert account["privacy_policy_text"] == payload["privacy_policy_text"]
        assert account["legal_mentions_text"] == payload["legal_mentions_text"]
        
        print(f"Sub-account created: {account['name']} with product_type={account['product_type']}")
        return account["id"]
    
    def test_get_sub_account_by_id(self, auth_token, crms):
        """Test get single sub-account"""
        # First create one
        crm_id = crms[0]["id"]
        create_res = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json={
                "crm_id": crm_id,
                "name": "TEST_GetById",
                "product_type": "pompe"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        account_id = create_res.json()["sub_account"]["id"]
        
        # Get by ID
        response = requests.get(f"{BASE_URL}/api/sub-accounts/{account_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == account_id
        assert data["product_type"] == "pompe"
        print(f"Get sub-account by ID OK: {data['name']}")


class TestLPs:
    """Landing Pages endpoints tests with CRM filtering"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    @pytest.fixture
    def sub_account(self, auth_token, crms):
        """Create a sub-account for LP tests"""
        crm_id = crms[0]["id"]
        response = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json={"crm_id": crm_id, "name": "TEST_LP_Account", "product_type": "solaire"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        return response.json()["sub_account"]
    
    def test_get_lps_no_filter(self, auth_token):
        """Test get all LPs without filter"""
        response = requests.get(f"{BASE_URL}/api/lps", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "lps" in data
        print(f"LPs (no filter): {len(data['lps'])} found")
    
    def test_get_lps_with_crm_filter(self, auth_token, crms):
        """Test get LPs filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/lps?crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "lps" in data
        print(f"LPs for CRM {crms[0]['name']}: {len(data['lps'])} found")
    
    def test_create_lp(self, auth_token, sub_account):
        """Test create LP"""
        payload = {
            "sub_account_id": sub_account["id"],
            "code": "TEST-LP-001",
            "name": "Test Landing Page",
            "url": "https://example.com/lp",
            "source_type": "native",
            "source_name": "Taboola",
            "cta_selector": ".cta-btn",
            "status": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/lps", 
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["lp"]["code"] == "TEST-LP-001"
        print(f"LP created: {data['lp']['code']}")


class TestForms:
    """Forms endpoints tests with CRM filtering"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    @pytest.fixture
    def sub_account(self, auth_token, crms):
        """Create a sub-account for Form tests"""
        crm_id = crms[0]["id"]
        response = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json={"crm_id": crm_id, "name": "TEST_Form_Account", "product_type": "solaire"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        return response.json()["sub_account"]
    
    def test_get_forms_no_filter(self, auth_token):
        """Test get all forms without filter"""
        response = requests.get(f"{BASE_URL}/api/forms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data
        print(f"Forms (no filter): {len(data['forms'])} found")
    
    def test_get_forms_with_crm_filter(self, auth_token, crms):
        """Test get forms filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/forms?crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data
        print(f"Forms for CRM {crms[0]['name']}: {len(data['forms'])} found")
    
    def test_create_form(self, auth_token, sub_account):
        """Test create form"""
        payload = {
            "sub_account_id": sub_account["id"],
            "lp_ids": [],
            "code": "TEST-FORM-001",
            "name": "Test Form",
            "product_type": "panneaux",
            "source_type": "native",
            "source_name": "Taboola",
            "api_key": "test-api-key",
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
        assert data["form"]["code"] == "TEST-FORM-001"
        print(f"Form created: {data['form']['code']}")


class TestLeads:
    """Leads endpoints tests with CRM filtering"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    def test_get_leads_no_filter(self, auth_token):
        """Test get all leads without filter"""
        response = requests.get(f"{BASE_URL}/api/leads", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert "count" in data
        print(f"Leads (no filter): {data['count']} found")
    
    def test_get_leads_with_crm_filter(self, auth_token, crms):
        """Test get leads filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/leads?crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        print(f"Leads for CRM {crms[0]['name']}: {data['count']} found")
    
    def test_get_leads_with_status_filter(self, auth_token):
        """Test get leads filtered by status"""
        response = requests.get(f"{BASE_URL}/api/leads?status=success", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        # Verify all returned leads have success status
        for lead in data["leads"]:
            assert lead["api_status"] == "success"
        print(f"Leads with status=success: {data['count']} found")


class TestAnalytics:
    """Analytics endpoints tests with CRM filtering"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    def test_get_analytics_stats_no_filter(self, auth_token):
        """Test get analytics stats without CRM filter"""
        response = requests.get(f"{BASE_URL}/api/analytics/stats?period=week", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "cta_clicks" in data
        assert "forms_started" in data
        assert "leads_total" in data
        print(f"Analytics stats (no filter): {data}")
    
    def test_get_analytics_stats_with_crm_filter(self, auth_token, crms):
        """Test get analytics stats filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/analytics/stats?period=week&crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        print(f"Analytics stats for CRM {crms[0]['name']}: leads_total={data['leads_total']}")
    
    def test_get_analytics_winners_no_filter(self, auth_token):
        """Test get analytics winners without CRM filter"""
        response = requests.get(f"{BASE_URL}/api/analytics/winners?period=week", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "lp_winners" in data
        assert "form_winners" in data
        print(f"Analytics winners (no filter): {len(data['lp_winners'])} LP winners, {len(data['form_winners'])} form winners")
    
    def test_get_analytics_winners_with_crm_filter(self, auth_token, crms):
        """Test get analytics winners filtered by CRM"""
        if not crms:
            pytest.skip("No CRMs available")
        
        crm_id = crms[0]["id"]
        response = requests.get(f"{BASE_URL}/api/analytics/winners?period=week&crm_id={crm_id}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        print(f"Analytics winners for CRM {crms[0]['name']}: {len(data['lp_winners'])} LP winners")


class TestScriptGenerator:
    """Script generator endpoints tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def crms(self, auth_token):
        response = requests.get(f"{BASE_URL}/api/crms", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        return response.json()["crms"]
    
    @pytest.fixture
    def lp(self, auth_token, crms):
        """Create a LP for script generation tests"""
        # First create sub-account
        crm_id = crms[0]["id"]
        sa_res = requests.post(f"{BASE_URL}/api/sub-accounts", 
            json={"crm_id": crm_id, "name": "TEST_Script_Account", "product_type": "solaire"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        sub_account_id = sa_res.json()["sub_account"]["id"]
        
        # Create LP
        lp_res = requests.post(f"{BASE_URL}/api/lps", 
            json={
                "sub_account_id": sub_account_id,
                "code": "TEST-SCRIPT-LP",
                "name": "Test Script LP",
                "source_type": "native",
                "source_name": "Taboola",
                "cta_selector": ".cta-btn",
                "status": "active"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        return lp_res.json()["lp"]
    
    def test_generate_lp_script(self, auth_token, lp):
        """Test generate LP tracking script"""
        response = requests.get(f"{BASE_URL}/api/generate-script/lp/{lp['id']}", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "script" in data
        assert "instructions" in data
        assert lp["code"] in data["script"]
        print(f"LP script generated for {lp['code']}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        return response.json()["token"]
    
    def test_cleanup_test_data(self, auth_token):
        """Clean up TEST_ prefixed data"""
        # Get all sub-accounts and delete TEST_ ones
        response = requests.get(f"{BASE_URL}/api/sub-accounts", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        accounts = response.json().get("sub_accounts", [])
        
        deleted = 0
        for account in accounts:
            if account["name"].startswith("TEST_"):
                del_res = requests.delete(f"{BASE_URL}/api/sub-accounts/{account['id']}", headers={
                    "Authorization": f"Bearer {auth_token}"
                })
                if del_res.status_code == 200:
                    deleted += 1
        
        print(f"Cleaned up {deleted} test sub-accounts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
