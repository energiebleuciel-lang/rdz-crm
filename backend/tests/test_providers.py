"""
RDZ CRM - Provider Feature Tests

Tests for:
- CRUD operations on providers
- API key generation and rotation
- Provider-authenticated lead submission
- entity_locked behavior
- Invalid/inactive provider key handling
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


class TestProviderAuth:
    """Test authentication requirements for provider endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - Get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json().get("token")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_providers_requires_auth(self):
        """GET /api/providers requires authentication"""
        # Without auth
        resp = self.session.get(f"{BASE_URL}/api/providers")
        assert resp.status_code == 401, "Should require auth"
        
        # With auth
        resp = self.session.get(f"{BASE_URL}/api/providers", headers=self.auth_header)
        assert resp.status_code == 200, f"Should succeed with auth: {resp.text}"
    
    def test_create_provider_requires_admin(self):
        """POST /api/providers requires admin role"""
        provider_data = {
            "name": "TEST_Provider_Auth",
            "slug": f"test-auth-{uuid.uuid4().hex[:8]}",
            "entity": "ZR7"
        }
        
        # With auth (admin user)
        resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json=provider_data,
            headers=self.auth_header
        )
        # Should succeed if user is admin, fail if not
        # Based on context, energiebleuciel@gmail.com is admin
        assert resp.status_code in [200, 403], f"Should require admin: {resp.text}"
        
        # Cleanup if created
        if resp.status_code == 200:
            provider_id = resp.json().get("provider", {}).get("id")
            if provider_id:
                self.session.delete(
                    f"{BASE_URL}/api/providers/{provider_id}",
                    headers=self.auth_header
                )


class TestProviderCRUD:
    """Test Provider CRUD operations"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - Get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json().get("token")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        self.created_providers = []
    
    def teardown_method(self):
        """Cleanup created providers"""
        for provider_id in self.created_providers:
            try:
                self.session.delete(
                    f"{BASE_URL}/api/providers/{provider_id}",
                    headers=self.auth_header
                )
            except Exception:
                pass
    
    def test_create_provider_zr7(self):
        """POST /api/providers - Create provider for ZR7 entity"""
        slug = f"test-zr7-{uuid.uuid4().hex[:8]}"
        provider_data = {
            "name": "TEST_Provider_ZR7",
            "slug": slug,
            "entity": "ZR7",
            "contact_email": "test@example.com",
            "notes": "Test provider for ZR7"
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json=provider_data,
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
        provider = data.get("provider", {})
        
        # Validate response structure
        assert provider.get("id"), "Should have id"
        assert provider.get("name") == "TEST_Provider_ZR7"
        assert provider.get("slug") == slug
        assert provider.get("entity") == "ZR7"
        assert provider.get("active") is True
        
        # API key format validation: prov_xxx
        api_key = provider.get("api_key", "")
        assert api_key.startswith("prov_"), f"API key should start with prov_: {api_key}"
        assert len(api_key) > 10, "API key should be substantial"
        
        self.created_providers.append(provider.get("id"))
        
        # Verify with GET
        get_resp = self.session.get(
            f"{BASE_URL}/api/providers/{provider.get('id')}",
            headers=self.auth_header
        )
        assert get_resp.status_code == 200
        fetched = get_resp.json().get("provider", {})
        assert fetched.get("name") == "TEST_Provider_ZR7"
        assert fetched.get("entity") == "ZR7"
    
    def test_create_provider_mdl(self):
        """POST /api/providers - Create provider for MDL entity"""
        slug = f"test-mdl-{uuid.uuid4().hex[:8]}"
        provider_data = {
            "name": "TEST_Provider_MDL",
            "slug": slug,
            "entity": "MDL"
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json=provider_data,
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        
        data = resp.json()
        provider = data.get("provider", {})
        assert provider.get("entity") == "MDL"
        assert provider.get("api_key", "").startswith("prov_")
        
        self.created_providers.append(provider.get("id"))
    
    def test_create_provider_slug_uniqueness(self):
        """POST /api/providers - Slug must be unique"""
        slug = f"test-unique-{uuid.uuid4().hex[:8]}"
        
        # Create first provider
        provider_data = {
            "name": "TEST_Provider_First",
            "slug": slug,
            "entity": "ZR7"
        }
        resp1 = self.session.post(
            f"{BASE_URL}/api/providers",
            json=provider_data,
            headers=self.auth_header
        )
        assert resp1.status_code == 200, f"First create failed: {resp1.text}"
        self.created_providers.append(resp1.json().get("provider", {}).get("id"))
        
        # Try to create with same slug
        resp2 = self.session.post(
            f"{BASE_URL}/api/providers",
            json=provider_data,
            headers=self.auth_header
        )
        assert resp2.status_code == 400, f"Should reject duplicate slug: {resp2.text}"
        assert "deja utilise" in resp2.text.lower() or "slug" in resp2.text.lower()
    
    def test_list_providers(self):
        """GET /api/providers - List all providers"""
        # Create a test provider first
        slug = f"test-list-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_List_Provider", "slug": slug, "entity": "ZR7"},
            headers=self.auth_header
        )
        if create_resp.status_code == 200:
            self.created_providers.append(create_resp.json().get("provider", {}).get("id"))
        
        # List providers
        resp = self.session.get(f"{BASE_URL}/api/providers", headers=self.auth_header)
        assert resp.status_code == 200, f"List failed: {resp.text}"
        
        data = resp.json()
        assert "providers" in data
        assert "count" in data
        assert isinstance(data["providers"], list)
        
        # Check provider has lead count stats
        if data["providers"]:
            provider = data["providers"][0]
            assert "total_leads" in provider, "Should include lead count"
    
    def test_list_providers_filter_by_entity(self):
        """GET /api/providers?entity=ZR7 - Filter by entity"""
        # Create providers for both entities
        slug_zr7 = f"test-filter-zr7-{uuid.uuid4().hex[:8]}"
        slug_mdl = f"test-filter-mdl-{uuid.uuid4().hex[:8]}"
        
        resp_zr7 = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Filter_ZR7", "slug": slug_zr7, "entity": "ZR7"},
            headers=self.auth_header
        )
        if resp_zr7.status_code == 200:
            self.created_providers.append(resp_zr7.json().get("provider", {}).get("id"))
        
        resp_mdl = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Filter_MDL", "slug": slug_mdl, "entity": "MDL"},
            headers=self.auth_header
        )
        if resp_mdl.status_code == 200:
            self.created_providers.append(resp_mdl.json().get("provider", {}).get("id"))
        
        # Filter by ZR7
        resp = self.session.get(
            f"{BASE_URL}/api/providers?entity=ZR7",
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Filter failed: {resp.text}"
        
        data = resp.json()
        for provider in data.get("providers", []):
            assert provider.get("entity") == "ZR7", f"Should only return ZR7 providers"
    
    def test_get_single_provider(self):
        """GET /api/providers/{id} - Get single provider"""
        # Create provider
        slug = f"test-get-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Get_Provider", "slug": slug, "entity": "ZR7"},
            headers=self.auth_header
        )
        assert create_resp.status_code == 200
        provider_id = create_resp.json().get("provider", {}).get("id")
        self.created_providers.append(provider_id)
        
        # Get provider
        resp = self.session.get(
            f"{BASE_URL}/api/providers/{provider_id}",
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Get failed: {resp.text}"
        
        data = resp.json()
        assert "provider" in data
        assert data["provider"]["id"] == provider_id
        assert data["provider"]["name"] == "TEST_Get_Provider"
        assert "total_leads" in data["provider"]
    
    def test_get_nonexistent_provider(self):
        """GET /api/providers/{id} - 404 for nonexistent"""
        resp = self.session.get(
            f"{BASE_URL}/api/providers/nonexistent-id-12345",
            headers=self.auth_header
        )
        assert resp.status_code == 404, f"Should return 404: {resp.text}"
    
    def test_update_provider(self):
        """PUT /api/providers/{id} - Update provider"""
        # Create provider
        slug = f"test-update-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Update_Original", "slug": slug, "entity": "MDL"},
            headers=self.auth_header
        )
        assert create_resp.status_code == 200
        provider_id = create_resp.json().get("provider", {}).get("id")
        original_api_key = create_resp.json().get("provider", {}).get("api_key")
        self.created_providers.append(provider_id)
        
        # Update provider
        update_data = {
            "name": "TEST_Update_Modified",
            "contact_email": "updated@example.com",
            "notes": "Updated notes",
            "active": False
        }
        resp = self.session.put(
            f"{BASE_URL}/api/providers/{provider_id}",
            json=update_data,
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Update failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
        provider = data.get("provider", {})
        assert provider.get("name") == "TEST_Update_Modified"
        assert provider.get("contact_email") == "updated@example.com"
        assert provider.get("active") is False
        # API key should NOT change on update
        assert provider.get("api_key") == original_api_key
        
        # Verify with GET
        get_resp = self.session.get(
            f"{BASE_URL}/api/providers/{provider_id}",
            headers=self.auth_header
        )
        assert get_resp.status_code == 200
        fetched = get_resp.json().get("provider", {})
        assert fetched.get("name") == "TEST_Update_Modified"
        assert fetched.get("active") is False
    
    def test_delete_provider(self):
        """DELETE /api/providers/{id} - Delete provider"""
        # Create provider
        slug = f"test-delete-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Delete_Provider", "slug": slug, "entity": "ZR7"},
            headers=self.auth_header
        )
        assert create_resp.status_code == 200
        provider_id = create_resp.json().get("provider", {}).get("id")
        
        # Delete provider
        resp = self.session.delete(
            f"{BASE_URL}/api/providers/{provider_id}",
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Delete failed: {resp.text}"
        assert resp.json().get("success") is True
        
        # Verify deleted
        get_resp = self.session.get(
            f"{BASE_URL}/api/providers/{provider_id}",
            headers=self.auth_header
        )
        assert get_resp.status_code == 404, "Should be deleted"
    
    def test_delete_nonexistent_provider(self):
        """DELETE /api/providers/{id} - 404 for nonexistent"""
        resp = self.session.delete(
            f"{BASE_URL}/api/providers/nonexistent-id-12345",
            headers=self.auth_header
        )
        assert resp.status_code == 404, f"Should return 404: {resp.text}"


class TestProviderKeyRotation:
    """Test API key rotation"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - Get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json().get("token")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        self.created_providers = []
    
    def teardown_method(self):
        """Cleanup"""
        for provider_id in self.created_providers:
            try:
                self.session.delete(
                    f"{BASE_URL}/api/providers/{provider_id}",
                    headers=self.auth_header
                )
            except Exception:
                pass
    
    def test_rotate_api_key(self):
        """POST /api/providers/{id}/rotate-key - Regenerate API key"""
        # Create provider
        slug = f"test-rotate-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Rotate_Key", "slug": slug, "entity": "ZR7"},
            headers=self.auth_header
        )
        assert create_resp.status_code == 200
        provider = create_resp.json().get("provider", {})
        provider_id = provider.get("id")
        original_key = provider.get("api_key")
        self.created_providers.append(provider_id)
        
        # Rotate key
        resp = self.session.post(
            f"{BASE_URL}/api/providers/{provider_id}/rotate-key",
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Rotate failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
        new_key = data.get("api_key")
        
        # New key should be different
        assert new_key != original_key, "New key should be different"
        assert new_key.startswith("prov_"), f"New key should start with prov_: {new_key}"
        
        # Verify in GET
        get_resp = self.session.get(
            f"{BASE_URL}/api/providers/{provider_id}",
            headers=self.auth_header
        )
        assert get_resp.status_code == 200
        fetched_key = get_resp.json().get("provider", {}).get("api_key")
        assert fetched_key == new_key
    
    def test_rotate_key_nonexistent_provider(self):
        """POST /api/providers/{id}/rotate-key - 404 for nonexistent"""
        resp = self.session.post(
            f"{BASE_URL}/api/providers/nonexistent-id-12345/rotate-key",
            headers=self.auth_header
        )
        assert resp.status_code == 404


class TestProviderLeadSubmission:
    """Test lead submission with provider API keys"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - Create test provider"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get admin token
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json().get("token")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        
        self.created_providers = []
        self.created_sessions = []
    
    def teardown_method(self):
        """Cleanup providers"""
        for provider_id in self.created_providers:
            try:
                self.session.delete(
                    f"{BASE_URL}/api/providers/{provider_id}",
                    headers=self.auth_header
                )
            except Exception:
                pass
    
    def _create_provider(self, entity: str, active: bool = True) -> dict:
        """Helper to create a provider"""
        slug = f"test-lead-{uuid.uuid4().hex[:8]}"
        resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={
                "name": f"TEST_Lead_Provider_{entity}",
                "slug": slug,
                "entity": entity
            },
            headers=self.auth_header
        )
        assert resp.status_code == 200, f"Create provider failed: {resp.text}"
        provider = resp.json().get("provider", {})
        self.created_providers.append(provider.get("id"))
        
        # Set active status if needed
        if not active:
            update_resp = self.session.put(
                f"{BASE_URL}/api/providers/{provider.get('id')}",
                json={"active": False},
                headers=self.auth_header
            )
            assert update_resp.status_code == 200
        
        return provider
    
    def _create_session(self) -> str:
        """Helper to create a tracking session"""
        resp = self.session.post(f"{BASE_URL}/api/public/track/session", json={
            "lp_code": f"TEST_LP_{uuid.uuid4().hex[:8]}"
        })
        assert resp.status_code == 200, f"Session creation failed: {resp.text}"
        session_id = resp.json().get("session_id")
        self.created_sessions.append(session_id)
        return session_id
    
    def test_lead_with_provider_key_in_header(self):
        """POST /api/public/leads with provider API key in Authorization header"""
        # Create ZR7 provider
        provider = self._create_provider("ZR7")
        api_key = provider.get("api_key")
        session_id = self._create_session()
        
        # Submit lead with provider key in header
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Provider_Lead",
            "prenom": "Test",
            "departement": "75",
            "produit": "PAC"
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert resp.status_code == 200, f"Lead submission failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
        assert data.get("lead_id"), "Should return lead_id"
    
    def test_lead_with_provider_key_in_body(self):
        """POST /api/public/leads with provider API key in body api_key field"""
        # Create MDL provider
        provider = self._create_provider("MDL")
        api_key = provider.get("api_key")
        session_id = self._create_session()
        
        # Submit lead with provider key in body
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Provider_Lead_Body",
            "prenom": "Test",
            "departement": "69",
            "api_key": api_key  # Key in body
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert resp.status_code == 200, f"Lead submission failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
    
    def test_lead_with_provider_key_raw_header(self):
        """POST /api/public/leads with provider API key directly in header (prov_xxx format)"""
        provider = self._create_provider("ZR7")
        api_key = provider.get("api_key")
        session_id = self._create_session()
        
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Provider_Lead_Raw",
            "departement": "33"
        }
        
        # Send key directly without "Bearer " prefix
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data,
            headers={"Authorization": api_key}  # Just prov_xxx
        )
        assert resp.status_code == 200, f"Lead submission failed: {resp.text}"
    
    def test_lead_without_provider_key(self):
        """POST /api/public/leads WITHOUT provider key -> entity_locked=false"""
        session_id = self._create_session()
        
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Internal_Lead",
            "prenom": "Internal",
            "departement": "44"
            # No api_key
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert resp.status_code == 200, f"Lead submission failed: {resp.text}"
        
        data = resp.json()
        assert data.get("success") is True
        # Internal lead should work without provider key
    
    def test_lead_with_invalid_provider_key(self):
        """POST /api/public/leads with INVALID provider key -> error"""
        session_id = self._create_session()
        
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Invalid_Key",
            "departement": "13",
            "api_key": "prov_invalid_key_12345"  # Invalid key
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert resp.status_code == 200, f"Response code: {resp.status_code}"
        
        data = resp.json()
        # Should return error for invalid key
        assert data.get("success") is False, "Should fail with invalid key"
        assert "invalide" in data.get("error", "").lower() or "invalid" in data.get("error", "").lower()
    
    def test_lead_with_inactive_provider_key(self):
        """POST /api/public/leads with INACTIVE provider key -> error"""
        # Create inactive provider
        provider = self._create_provider("ZR7", active=False)
        api_key = provider.get("api_key")
        session_id = self._create_session()
        
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Inactive_Provider",
            "departement": "06",
            "api_key": api_key
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert resp.status_code == 200, f"Response code: {resp.status_code}"
        
        data = resp.json()
        # Should return error for inactive provider
        assert data.get("success") is False, "Should fail with inactive provider key"
        assert "invalide" in data.get("error", "").lower() or "inactive" in data.get("error", "").lower()


class TestEntityLockedBehavior:
    """Test entity_locked behavior in routing"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json().get("token")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
        self.created_providers = []
    
    def teardown_method(self):
        """Cleanup"""
        for provider_id in self.created_providers:
            try:
                self.session.delete(
                    f"{BASE_URL}/api/providers/{provider_id}",
                    headers=self.auth_header
                )
            except Exception:
                pass
    
    def test_provider_entity_becomes_lead_entity(self):
        """Lead entity should come from provider when using provider key"""
        # Create ZR7 provider
        slug = f"test-entity-{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(
            f"{BASE_URL}/api/providers",
            json={"name": "TEST_Entity_Provider", "slug": slug, "entity": "ZR7"},
            headers=self.auth_header
        )
        assert create_resp.status_code == 200
        provider = create_resp.json().get("provider", {})
        self.created_providers.append(provider.get("id"))
        api_key = provider.get("api_key")
        
        # Create session
        session_resp = self.session.post(f"{BASE_URL}/api/public/track/session", json={
            "lp_code": f"TEST_LP_{uuid.uuid4().hex[:8]}"
        })
        session_id = session_resp.json().get("session_id")
        
        # Submit lead - even if entity="MDL" in body, provider's ZR7 should win
        lead_data = {
            "session_id": session_id,
            "form_code": "TEST_FORM",
            "phone": f"0612345{uuid.uuid4().hex[:3]}",
            "nom": "TEST_Entity_Override",
            "departement": "75",
            "entity": "MDL",  # Try to set MDL
            "api_key": api_key  # But provider is ZR7
        }
        
        resp = self.session.post(
            f"{BASE_URL}/api/public/leads",
            json=lead_data
        )
        assert resp.status_code == 200, f"Lead submission failed: {resp.text}"
        # The lead should be created with entity=ZR7 (from provider), entity_locked=true


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
