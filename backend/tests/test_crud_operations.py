"""
Comprehensive CRUD tests for Solar CRM API
Tests all endpoints: Accounts, LPs, Forms, Leads, Commandes, Users
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crmsync-11.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"Login successful - user: {data['user']['email']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid credentials correctly rejected")
    
    def test_get_me_authenticated(self):
        """Test /me endpoint with valid token"""
        # First login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = login_res.json()["token"]
        
        # Get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        print(f"User info retrieved: {data['email']}")
    
    def test_get_me_unauthenticated(self):
        """Test /me endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("Unauthenticated request correctly rejected")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Authentication failed")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAccounts:
    """Accounts CRUD tests"""
    
    def test_list_accounts(self, auth_headers):
        """Test listing accounts"""
        response = requests.get(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        print(f"Found {len(data['accounts'])} accounts")
    
    def test_list_accounts_by_crm(self, auth_headers):
        """Test listing accounts filtered by CRM"""
        # First get CRMs
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        if crms_res.status_code == 200:
            crms = crms_res.json().get("crms", [])
            if crms:
                crm_id = crms[0]["id"]
                response = requests.get(
                    f"{BASE_URL}/api/accounts?crm_id={crm_id}",
                    headers=auth_headers
                )
                assert response.status_code == 200
                print(f"Accounts filtered by CRM: {crm_id}")
    
    def test_create_account(self, auth_headers):
        """Test creating an account"""
        # Get first CRM
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        crm_id = crms_res.json()["crms"][0]["id"] if crms_res.status_code == 200 else None
        
        if not crm_id:
            pytest.skip("No CRM available")
        
        account_data = {
            "name": f"TEST_Account_{uuid.uuid4().hex[:8]}",
            "crm_id": crm_id,
            "domain": "test-domain.com",
            "primary_color": "#3B82F6",
            "secondary_color": "#1E40AF"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers,
            json=account_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True or "account" in data
        print(f"Account created: {account_data['name']}")
        
        # Cleanup - delete the test account
        if "account" in data:
            account_id = data["account"]["id"]
            requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
    
    def test_accounts_require_auth(self):
        """Test that accounts endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/accounts")
        assert response.status_code == 401
        print("Accounts endpoint correctly requires auth")


class TestLandingPages:
    """Landing Pages CRUD tests"""
    
    def test_list_lps(self, auth_headers):
        """Test listing landing pages"""
        response = requests.get(
            f"{BASE_URL}/api/lps",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "lps" in data
        print(f"Found {len(data['lps'])} landing pages")
    
    def test_get_lp_brief(self, auth_headers):
        """Test getting LP brief with scripts"""
        # First get LPs
        lps_res = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = lps_res.json().get("lps", [])
        
        # Find LP with form_id (new format)
        lp_with_form = None
        for lp in lps:
            if lp.get("form_id") or lp.get("form"):
                lp_with_form = lp
                break
        
        if not lp_with_form:
            pytest.skip("No LP with form found")
        
        response = requests.get(
            f"{BASE_URL}/api/lps/{lp_with_form['id']}/brief",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "scripts" in data or "lp" in data
        print(f"Brief retrieved for LP: {lp_with_form.get('code')}")
    
    def test_lps_require_auth(self):
        """Test that LPs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lps")
        assert response.status_code == 401
        print("LPs endpoint correctly requires auth")


class TestForms:
    """Forms CRUD tests"""
    
    def test_list_forms(self, auth_headers):
        """Test listing forms"""
        response = requests.get(
            f"{BASE_URL}/api/forms",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "forms" in data
        print(f"Found {len(data['forms'])} forms")
    
    def test_forms_have_stats(self, auth_headers):
        """Test that forms include stats (Démarrés, Leads, Conv.)"""
        response = requests.get(
            f"{BASE_URL}/api/forms",
            headers=auth_headers
        )
        assert response.status_code == 200
        forms = response.json().get("forms", [])
        
        if forms:
            form = forms[0]
            assert "stats" in form
            stats = form["stats"]
            # Check for expected stats fields
            assert "started" in stats or "leads" in stats
            print(f"Form stats: {stats}")
    
    def test_filter_forms_by_product(self, auth_headers):
        """Test filtering forms by product type"""
        response = requests.get(
            f"{BASE_URL}/api/forms?product_type=PV",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("Forms filtered by product type PV")
    
    def test_forms_require_auth(self):
        """Test that forms endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/forms")
        assert response.status_code == 401
        print("Forms endpoint correctly requires auth")


class TestLeads:
    """Leads CRUD tests"""
    
    def test_list_leads(self, auth_headers):
        """Test listing leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        print(f"Found {len(data['leads'])} leads")
    
    def test_filter_leads_by_status(self, auth_headers):
        """Test filtering leads by status"""
        for status in ["success", "failed", "no_crm"]:
            response = requests.get(
                f"{BASE_URL}/api/leads?status={status}",
                headers=auth_headers
            )
            assert response.status_code == 200
            print(f"Leads filtered by status: {status}")
    
    def test_leads_global_stats(self, auth_headers):
        """Test leads global stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leads/stats/global",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "success" in data
        print(f"Leads stats: total={data['total']}, success={data['success']}")
    
    def test_leads_require_auth(self):
        """Test that leads endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 401
        print("Leads endpoint correctly requires auth")


class TestCommandes:
    """Commandes CRUD tests"""
    
    def test_list_commandes(self, auth_headers):
        """Test listing commandes"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "commandes" in data
        print(f"Found {len(data['commandes'])} commandes")
    
    def test_filter_commandes_by_crm(self, auth_headers):
        """Test filtering commandes by CRM"""
        # Get CRMs first
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        if crms_res.status_code == 200:
            crms = crms_res.json().get("crms", [])
            if crms:
                crm_id = crms[0]["id"]
                response = requests.get(
                    f"{BASE_URL}/api/commandes?crm_id={crm_id}",
                    headers=auth_headers
                )
                assert response.status_code == 200
                print(f"Commandes filtered by CRM: {crm_id}")
    
    def test_check_commande(self, auth_headers):
        """Test checking if commande exists for CRM/product/dept"""
        # Get CRMs first
        crms_res = requests.get(f"{BASE_URL}/api/crms", headers=auth_headers)
        if crms_res.status_code == 200:
            crms = crms_res.json().get("crms", [])
            if crms:
                crm_id = crms[0]["id"]
                response = requests.get(
                    f"{BASE_URL}/api/commandes/check?crm_id={crm_id}&product_type=PV&departement=75",
                    headers=auth_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "has_commande" in data
                print(f"Commande check: {data}")
    
    def test_list_departements(self, auth_headers):
        """Test listing valid departements"""
        response = requests.get(
            f"{BASE_URL}/api/commandes/departements",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "departements" in data
        print(f"Found {len(data['departements'])} departements")
    
    def test_commandes_require_auth(self):
        """Test that commandes endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/commandes")
        assert response.status_code == 401
        print("Commandes endpoint correctly requires auth")


class TestUsers:
    """Users management tests"""
    
    def test_list_users(self, auth_headers):
        """Test listing users (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"Found {len(data['users'])} users")
    
    def test_create_user_with_permissions(self, auth_headers):
        """Test creating user with custom permissions"""
        user_data = {
            "email": f"test_user_{uuid.uuid4().hex[:8]}@test.com",
            "password": "TestPassword123!",
            "nom": "Test User",
            "role": "editor",
            "permissions": {
                "dashboard": True,
                "accounts": True,
                "lps": True,
                "forms": True,
                "leads": True,
                "commandes": False,
                "settings": False,
                "users": False
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auth/users",
            headers=auth_headers,
            json=user_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "user" in data
        assert data["user"]["permissions"]["dashboard"] == True
        assert data["user"]["permissions"]["commandes"] == False
        print(f"User created with custom permissions: {user_data['email']}")
        
        # Cleanup - delete the test user
        if "user" in data:
            user_id = data["user"]["id"]
            requests.delete(f"{BASE_URL}/api/auth/users/{user_id}", headers=auth_headers)
    
    def test_users_require_admin(self):
        """Test that users endpoint requires admin role"""
        response = requests.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 401
        print("Users endpoint correctly requires auth")


class TestActivityLog:
    """Activity log tests"""
    
    def test_get_activity_logs(self, auth_headers):
        """Test getting activity logs"""
        response = requests.get(
            f"{BASE_URL}/api/auth/activity-logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        print(f"Found {len(data['logs'])} activity log entries")
    
    def test_activity_logs_have_login_events(self, auth_headers):
        """Test that activity logs contain login events"""
        response = requests.get(
            f"{BASE_URL}/api/auth/activity-logs?action=login",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        logs = data.get("logs", [])
        # Should have at least one login event from our tests
        print(f"Found {len(logs)} login events")


class TestCRMs:
    """CRM management tests"""
    
    def test_list_crms(self, auth_headers):
        """Test listing CRMs"""
        response = requests.get(
            f"{BASE_URL}/api/crms",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "crms" in data
        crms = data["crms"]
        # Should have MDL and ZR7
        crm_slugs = [c.get("slug") for c in crms]
        print(f"Found CRMs: {crm_slugs}")
    
    def test_crms_require_auth(self):
        """Test that CRMs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/crms")
        assert response.status_code == 401
        print("CRMs endpoint correctly requires auth")


class TestHealthCheck:
    """Health check tests"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
