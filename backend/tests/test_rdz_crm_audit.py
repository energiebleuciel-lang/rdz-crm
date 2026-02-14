"""
RDZ CRM - Backend Tests Post-Audit
Version 4.0 - Validates all API endpoints after technical cleanup

Tests:
- Auth: login, me endpoint
- Clients: list by entity, create
- Commandes: list with enriched data, create with produit field
- Public: lead submission with entity/produit, anti double-submit, session tracking
- Legacy: verify old endpoints return 404
- Naming: confirm 'produit' field (not 'product_type')
"""

import pytest
import requests
import os
import time
import uuid

# API base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rdz-crm-hub-1.preview.emergentagent.com')
if BASE_URL.endswith('/'):
    BASE_URL = BASE_URL.rstrip('/')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """POST /api/auth/login - valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "token" in data, "Missing token in response"
        assert "user" in data, "Missing user in response"
        assert len(data["token"]) > 0, "Token is empty"
        
        # Validate user data
        user = data["user"]
        assert user.get("email") == TEST_EMAIL, f"Unexpected email: {user.get('email')}"
        assert "id" in user, "Missing user id"
        assert "role" in user, "Missing user role"
        assert "permissions" in user, "Missing user permissions"
        
        print(f"✓ Login successful - user: {user.get('nom', user.get('email'))}, role: {user.get('role')}")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login - invalid credentials should return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_me_endpoint(self, auth_token):
        """GET /api/auth/me - get current user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Me endpoint failed: {response.text}"
        data = response.json()
        
        assert "email" in data, "Missing email in /me response"
        assert data["email"] == TEST_EMAIL, f"Unexpected email: {data['email']}"
        assert "permissions" in data, "Missing permissions in /me response"
        
        print(f"✓ /me endpoint works - user: {data.get('nom', 'Unknown')}")
    
    def test_me_without_auth(self):
        """GET /api/auth/me - without token should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /me correctly requires authentication")


class TestClientsEndpoints:
    """Test clients CRUD endpoints"""
    
    def test_list_clients_zr7(self, auth_token):
        """GET /api/clients?entity=ZR7 - list ZR7 clients"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            params={"entity": "ZR7"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"List clients failed: {response.text}"
        data = response.json()
        
        assert "clients" in data, "Missing 'clients' key in response"
        assert "count" in data, "Missing 'count' key in response"
        assert data.get("entity") == "ZR7", f"Entity mismatch: {data.get('entity')}"
        assert isinstance(data["clients"], list), "clients should be a list"
        
        print(f"✓ ZR7 clients: {data['count']} found")
        return data["clients"]
    
    def test_list_clients_mdl(self, auth_token):
        """GET /api/clients?entity=MDL - list MDL clients"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            params={"entity": "MDL"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"List clients failed: {response.text}"
        data = response.json()
        
        assert "clients" in data, "Missing 'clients' key in response"
        assert data.get("entity") == "MDL", f"Entity mismatch: {data.get('entity')}"
        
        print(f"✓ MDL clients: {data['count']} found")
    
    def test_list_clients_requires_entity(self, auth_token):
        """GET /api/clients - without entity should fail"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 422 (validation error) as entity is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Entity parameter correctly required")
    
    def test_list_clients_invalid_entity(self, auth_token):
        """GET /api/clients?entity=INVALID - should fail"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            params={"entity": "INVALID"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid entity correctly rejected")
    
    def test_create_client_mdl(self, auth_token):
        """POST /api/clients - create a new MDL client"""
        unique_id = str(uuid.uuid4())[:8]
        client_data = {
            "entity": "MDL",
            "name": f"TEST_Client_MDL_{unique_id}",
            "email": f"test_mdl_{unique_id}@example.com",
            "contact_name": "Test Contact",
            "phone": "0612345678",
            "default_prix_lead": 25.0,
            "remise_percent": 5.0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/clients",
            json=client_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Create client failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "client" in data, "Missing client in response"
        
        client = data["client"]
        assert client.get("entity") == "MDL", f"Entity mismatch: {client.get('entity')}"
        assert client.get("name") == client_data["name"], "Name mismatch"
        assert "id" in client, "Missing client id"
        
        print(f"✓ MDL client created: {client['id'][:8]}...")
        return client["id"]


class TestCommandesEndpoints:
    """Test commandes CRUD endpoints"""
    
    def test_list_commandes_zr7(self, auth_token):
        """GET /api/commandes?entity=ZR7 - list with enriched data"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            params={"entity": "ZR7"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"List commandes failed: {response.text}"
        data = response.json()
        
        assert "commandes" in data, "Missing 'commandes' key"
        assert "count" in data, "Missing 'count' key"
        assert data.get("entity") == "ZR7", f"Entity mismatch"
        
        # Check if commandes have enriched fields
        if data["commandes"]:
            cmd = data["commandes"][0]
            assert "client_name" in cmd, "Missing 'client_name' enrichment"
            assert "produit" in cmd, "Missing 'produit' field"
            # Verify NO product_type field
            assert "product_type" not in cmd, "LEGACY ERROR: Found 'product_type' instead of 'produit'"
        
        print(f"✓ ZR7 commandes: {data['count']} found (produit field verified)")
    
    def test_list_departements(self, auth_token):
        """GET /api/commandes/departements - list valid departments"""
        response = requests.get(
            f"{BASE_URL}/api/commandes/departements",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"List departements failed: {response.text}"
        data = response.json()
        
        assert "departements" in data, "Missing 'departements' key"
        depts = data["departements"]
        assert len(depts) > 0, "No departements returned"
        assert "75" in depts, "Paris (75) should be in list"
        assert "20" not in depts, "Corse (20) should NOT be in list"
        
        print(f"✓ Departements: {data['count']} available")
    
    def test_list_products(self, auth_token):
        """GET /api/commandes/products - list valid products"""
        response = requests.get(
            f"{BASE_URL}/api/commandes/products",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"List products failed: {response.text}"
        data = response.json()
        
        assert "products" in data, "Missing 'products' key"
        products = data["products"]
        assert "PV" in products, "PV should be in products"
        assert "PAC" in products, "PAC should be in products"
        assert "ITE" in products, "ITE should be in products"
        
        print(f"✓ Products available: {products}")
    
    def test_create_commande_with_produit(self, auth_token, test_client_id):
        """POST /api/commandes - create with 'produit' field (not product_type)"""
        commande_data = {
            "entity": "MDL",
            "client_id": test_client_id,
            "produit": "PV",  # Using 'produit' NOT 'product_type'
            "departements": ["75", "92", "93", "94"],
            "quota_semaine": 10,
            "prix_lead": 25.0,
            "lb_percent_max": 20,
            "priorite": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commandes",
            json=commande_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Create commande failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "commande" in data, "Missing commande in response"
        
        cmd = data["commande"]
        # KEY VALIDATION: Must have 'produit', NOT 'product_type'
        assert "produit" in cmd, "Missing 'produit' in response"
        assert cmd.get("produit") == "PV", f"Produit mismatch: {cmd.get('produit')}"
        assert "product_type" not in cmd, "LEGACY ERROR: Found 'product_type'"
        assert "client_name" in cmd, "Missing client_name enrichment"
        
        print(f"✓ Commande created with 'produit' field: {cmd['id'][:8]}...")
        return cmd["id"]


class TestPublicEndpoints:
    """Test public API endpoints (no auth required)"""
    
    def test_create_tracking_session(self):
        """POST /api/public/track/session - create visitor session"""
        session_data = {
            "lp_code": "LP_TEST_001",
            "form_code": "FORM_TEST_001",
            "referrer": "https://google.com",
            "utm_source": "test",
            "utm_medium": "pytest",
            "utm_campaign": "audit_test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/track/session",
            json=session_data
        )
        
        assert response.status_code == 200, f"Create session failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "session_id" in data, "Missing session_id"
        assert "visitor_id" in data, "Missing visitor_id"
        
        print(f"✓ Session created: {data['session_id'][:8]}...")
        return data["session_id"]
    
    def test_submit_lead_with_entity_produit(self, test_session_id):
        """POST /api/public/leads - submit lead with entity and produit"""
        unique_phone = f"06{str(uuid.uuid4().int)[:8]}"
        lead_data = {
            "session_id": test_session_id,
            "form_code": "FORM_TEST_001",
            "phone": unique_phone,
            "nom": "TestNom",
            "prenom": "TestPrenom",
            "email": "test_lead@example.com",
            "departement": "75",
            "entity": "ZR7",  # KEY: entity field
            "produit": "PV"   # KEY: produit field (not product_type)
        }
        
        response = requests.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        
        assert response.status_code == 200, f"Submit lead failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Lead submission failed: {data}"
        assert "lead_id" in data, "Missing lead_id"
        assert data.get("status") == "new", f"Unexpected status: {data.get('status')}"
        
        print(f"✓ Lead submitted with entity={lead_data['entity']} produit={lead_data['produit']}")
        return data["lead_id"]
    
    def test_anti_double_submit(self, test_session_id):
        """POST /api/public/leads - anti double-submit within 5 seconds"""
        unique_phone = f"06{str(uuid.uuid4().int)[:8]}"
        lead_data = {
            "session_id": test_session_id,
            "form_code": "FORM_TEST_001",
            "phone": unique_phone,
            "nom": "DoubleTest",
            "prenom": "Test",
            "departement": "92"
        }
        
        # First submission
        response1 = requests.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert response1.status_code == 200, f"First submit failed: {response1.text}"
        data1 = response1.json()
        assert data1.get("status") == "new", "First submit should be new"
        
        # Second submission (immediate - should be caught as double_submit)
        response2 = requests.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert response2.status_code == 200, f"Second submit failed: {response2.text}"
        data2 = response2.json()
        
        # Should be marked as double_submit
        assert data2.get("status") == "double_submit", f"Expected double_submit, got: {data2.get('status')}"
        assert data2.get("lead_id") == data1.get("lead_id"), "Should return original lead_id"
        
        print(f"✓ Anti double-submit working - same lead_id returned")


class TestLegacyEndpoints404:
    """Verify old/deleted endpoints return 404"""
    
    def test_accounts_endpoint_404(self, auth_token):
        """GET /api/accounts - should 404 (deleted)"""
        response = requests.get(
            f"{BASE_URL}/api/accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404, f"Legacy /api/accounts should 404, got {response.status_code}"
        print("✓ /api/accounts correctly returns 404")
    
    def test_crms_endpoint_404(self, auth_token):
        """GET /api/crms - should 404 (deleted)"""
        response = requests.get(
            f"{BASE_URL}/api/crms",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404, f"Legacy /api/crms should 404, got {response.status_code}"
        print("✓ /api/crms correctly returns 404")
    
    def test_forms_endpoint_404(self, auth_token):
        """GET /api/forms - should 404 (deleted)"""
        response = requests.get(
            f"{BASE_URL}/api/forms",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404, f"Legacy /api/forms should 404, got {response.status_code}"
        print("✓ /api/forms correctly returns 404")


class TestNamingConventions:
    """Verify correct naming: 'produit' everywhere, NOT 'product_type'"""
    
    def test_commandes_response_has_produit(self, auth_token):
        """Verify commande response uses 'produit' field"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            params={"entity": "ZR7"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        for cmd in data.get("commandes", []):
            assert "produit" in cmd, f"Commande {cmd.get('id')} missing 'produit' field"
            assert "product_type" not in cmd, f"Commande {cmd.get('id')} has legacy 'product_type' field!"
        
        print(f"✓ All {len(data.get('commandes', []))} commandes use 'produit' (not product_type)")


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def test_client_id(auth_token):
    """Create a test client and return its ID"""
    unique_id = str(uuid.uuid4())[:8]
    client_data = {
        "entity": "MDL",
        "name": f"TEST_Fixture_Client_{unique_id}",
        "email": f"test_fixture_{unique_id}@example.com",
        "default_prix_lead": 20.0,
        "remise_percent": 0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/clients",
        json=client_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to create test client: {response.text}")
    
    return response.json()["client"]["id"]


@pytest.fixture(scope="module")
def test_session_id():
    """Create a test session and return its ID"""
    response = requests.post(
        f"{BASE_URL}/api/public/track/session",
        json={"lp_code": "LP_FIXTURE", "form_code": "FORM_FIXTURE"}
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to create test session: {response.text}")
    
    return response.json()["session_id"]


# ==================== MAIN ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
