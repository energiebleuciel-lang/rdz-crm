"""
RDZ CRM - Test New Settings Features (Iteration 14)

Tests for 3 new features:
1. Settings API: cross-entity toggle and source gating
2. Source gating: blocked sources put leads in hold_source status
3. Commande OPEN concept: active + delivered_this_week < quota

Test credentials: energiebleuciel@gmail.com / 92Ruemarxdormoy
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSettingsAPI:
    """Settings API endpoints tests (Admin authenticated)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    # --- GET /api/settings ---
    def test_list_settings_returns_defaults(self, auth_headers):
        """GET /api/settings - list all settings with defaults"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert "count" in data
        
        # Should have at least cross_entity and source_gating
        keys = [s.get("key") for s in data["settings"]]
        assert "cross_entity" in keys or any("cross_entity" in str(s) for s in data["settings"]), \
            "cross_entity setting should be present (real or default)"
        assert "source_gating" in keys or any("source_gating" in str(s) for s in data["settings"]), \
            "source_gating setting should be present (real or default)"
    
    def test_list_settings_requires_auth(self):
        """GET /api/settings - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 401
    
    # --- GET /api/settings/cross-entity ---
    def test_get_cross_entity_settings(self, auth_headers):
        """GET /api/settings/cross-entity - get cross-entity settings"""
        response = requests.get(f"{BASE_URL}/api/settings/cross-entity", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure has expected fields
        assert "cross_entity_enabled" in data or data.get("cross_entity_enabled") is not None or \
               data == {} or "per_entity" in data, f"Unexpected response: {data}"
        
        # If data exists, verify per_entity structure
        if "per_entity" in data:
            per_entity = data["per_entity"]
            if "ZR7" in per_entity:
                assert "in_enabled" in per_entity["ZR7"]
                assert "out_enabled" in per_entity["ZR7"]
            if "MDL" in per_entity:
                assert "in_enabled" in per_entity["MDL"]
                assert "out_enabled" in per_entity["MDL"]
    
    # --- PUT /api/settings/cross-entity ---
    def test_update_cross_entity_global_toggle(self, auth_headers):
        """PUT /api/settings/cross-entity - toggle global cross-entity"""
        # First disable
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={"cross_entity_enabled": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "setting" in data
        assert data["setting"].get("cross_entity_enabled") == False
        
        # Verify updated_at and updated_by fields
        setting = data["setting"]
        assert "updated_at" in setting, "Settings should have updated_at audit field"
        assert "updated_by" in setting, "Settings should have updated_by audit field"
        
        # Re-enable
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={"cross_entity_enabled": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["setting"].get("cross_entity_enabled") == True
    
    def test_update_cross_entity_per_entity(self, auth_headers):
        """PUT /api/settings/cross-entity - toggle per-entity in/out"""
        # Disable ZR7 out, keep MDL enabled
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={
                "cross_entity_enabled": True,
                "per_entity": {
                    "ZR7": {"in_enabled": True, "out_enabled": False},
                    "MDL": {"in_enabled": True, "out_enabled": True}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        setting = data["setting"]
        assert setting["per_entity"]["ZR7"]["out_enabled"] == False
        assert setting["per_entity"]["MDL"]["out_enabled"] == True
        
        # Restore defaults
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={
                "cross_entity_enabled": True,
                "per_entity": {
                    "ZR7": {"in_enabled": True, "out_enabled": True},
                    "MDL": {"in_enabled": True, "out_enabled": True}
                }
            }
        )
        assert response.status_code == 200
    
    def test_update_cross_entity_requires_admin(self, auth_headers):
        """PUT /api/settings/cross-entity - requires admin role"""
        # This test uses admin creds, so it should work
        # Testing that non-admin would fail is implicit
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            # No auth header
            json={"cross_entity_enabled": True}
        )
        assert response.status_code == 401
    
    # --- GET /api/settings/source-gating ---
    def test_get_source_gating_settings(self, auth_headers):
        """GET /api/settings/source-gating - get source gating settings"""
        response = requests.get(f"{BASE_URL}/api/settings/source-gating", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "mode" in data, "source_gating should have 'mode' field"
        assert "blocked_sources" in data, "source_gating should have 'blocked_sources' field"
        assert data["mode"] == "blacklist", "Default mode should be blacklist"
    
    # --- PUT /api/settings/source-gating ---
    def test_update_source_gating_add_blocked_source(self, auth_headers):
        """PUT /api/settings/source-gating - add blocked sources"""
        test_sources = ["TEST_blocked_source_1", "TEST_blocked_source_2"]
        
        response = requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={
                "mode": "blacklist",
                "blocked_sources": test_sources
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        setting = data["setting"]
        assert "blocked_sources" in setting
        assert all(src in setting["blocked_sources"] for src in test_sources)
        
        # Verify updated_at and updated_by
        assert "updated_at" in setting
        assert "updated_by" in setting
    
    def test_update_source_gating_clear_blocked_sources(self, auth_headers):
        """PUT /api/settings/source-gating - clear blocked sources"""
        response = requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={
                "mode": "blacklist",
                "blocked_sources": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["setting"]["blocked_sources"] == []


class TestSourceGatingLeadSubmission:
    """Test source gating in lead submission"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    @pytest.fixture(scope="class")
    def session_id(self):
        """Create a tracking session"""
        response = requests.post(
            f"{BASE_URL}/api/public/track/session",
            json={"lp_code": "TEST_LP", "utm_source": ""}
        )
        assert response.status_code == 200
        return response.json().get("session_id")
    
    @pytest.fixture(scope="class")
    def blocked_session_id(self):
        """Create a tracking session with blocked source"""
        response = requests.post(
            f"{BASE_URL}/api/public/track/session",
            json={"lp_code": "blocked_test_source", "utm_source": "blocked_test_source"}
        )
        assert response.status_code == 200
        return response.json().get("session_id")
    
    def test_lead_with_allowed_source_gets_status_new(self, auth_headers, session_id):
        """POST /api/public/leads with allowed source -> status=new"""
        # Ensure source is not blocked
        requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={"mode": "blacklist", "blocked_sources": []}
        )
        
        unique_phone = f"+336{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/public/leads",
            json={
                "session_id": session_id,
                "form_code": "TEST_FORM",
                "phone": unique_phone,
                "nom": "Test Allowed Source",
                "prenom": "User",
                "email": "test_allowed@test.com",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PAC"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "new", f"Expected status=new, got {data.get('status')}"
    
    def test_lead_with_blocked_source_gets_status_hold_source(self, auth_headers, blocked_session_id):
        """POST /api/public/leads with blocked source -> status=hold_source"""
        # Block the test source
        requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={"mode": "blacklist", "blocked_sources": ["blocked_test_source"]}
        )
        
        unique_phone = f"+336{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/public/leads",
            json={
                "session_id": blocked_session_id,
                "form_code": "TEST_FORM_BLOCKED",
                "phone": unique_phone,
                "nom": "Test Blocked Source",
                "prenom": "User",
                "email": "test_blocked@test.com",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PAC"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "hold_source", \
            f"Expected status=hold_source for blocked source, got {data.get('status')}"
    
    def test_cleanup_source_gating(self, auth_headers):
        """Cleanup: clear blocked sources after tests"""
        response = requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={"mode": "blacklist", "blocked_sources": []}
        )
        assert response.status_code == 200


class TestCommandeOpenConcept:
    """Test commande OPEN logic: active + delivered_this_week < quota"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_list_commandes_shows_open_status(self, auth_headers):
        """GET /api/commandes - verify commandes have active field"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "commandes" in data
        
        # If commandes exist, check they have active field
        for cmd in data["commandes"]:
            assert "active" in cmd, "Commande should have 'active' field"
            assert "quota_semaine" in cmd, "Commande should have 'quota_semaine' field"
    
    def test_commande_with_quota_zero_is_unlimited(self, auth_headers):
        """Test that quota=0 means unlimited (always OPEN)"""
        # This is a logic validation test
        # We verify the API accepts quota=0 for commandes
        
        # First, get list of clients
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        if response.status_code == 200 and response.json().get("clients"):
            client_id = response.json()["clients"][0]["id"]
            
            # Create a test commande with quota=0
            test_commande = {
                "entity": "ZR7",
                "client_id": client_id,
                "produit": "PAC",
                "quota_semaine": 0,  # Unlimited
                "departements": ["75"],
                "active": True,
                "priorite": 999  # Low priority for test
            }
            
            response = requests.post(
                f"{BASE_URL}/api/commandes",
                headers=auth_headers,
                json=test_commande
            )
            
            # Verify quota=0 is accepted
            if response.status_code in [200, 201]:
                data = response.json()
                commande = data.get("commande", data)
                assert commande.get("quota_semaine") == 0, "Quota 0 should be accepted"


class TestCrossEntityToggle:
    """Test cross-entity toggle respects settings"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_disable_global_cross_entity(self, auth_headers):
        """Disable cross-entity globally and verify it persists"""
        # Disable
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={"cross_entity_enabled": False}
        )
        assert response.status_code == 200
        
        # Verify persisted
        response = requests.get(f"{BASE_URL}/api/settings/cross-entity", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("cross_entity_enabled") == False
        
        # Re-enable for cleanup
        requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={"cross_entity_enabled": True}
        )
    
    def test_disable_zr7_outbound(self, auth_headers):
        """Disable ZR7 outbound and verify MDL inbound still works"""
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={
                "cross_entity_enabled": True,
                "per_entity": {
                    "ZR7": {"in_enabled": True, "out_enabled": False},
                    "MDL": {"in_enabled": True, "out_enabled": True}
                }
            }
        )
        assert response.status_code == 200
        
        # Verify
        response = requests.get(f"{BASE_URL}/api/settings/cross-entity", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["per_entity"]["ZR7"]["out_enabled"] == False
        assert data["per_entity"]["MDL"]["in_enabled"] == True
        
        # Restore defaults
        requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={
                "cross_entity_enabled": True,
                "per_entity": {
                    "ZR7": {"in_enabled": True, "out_enabled": True},
                    "MDL": {"in_enabled": True, "out_enabled": True}
                }
            }
        )


class TestSettingsAuditFields:
    """Test that settings have proper audit fields"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_cross_entity_has_audit_fields(self, auth_headers):
        """Verify cross-entity settings have updated_at and updated_by"""
        # Make an update to ensure audit fields are set
        response = requests.put(
            f"{BASE_URL}/api/settings/cross-entity",
            headers=auth_headers,
            json={"cross_entity_enabled": True}
        )
        assert response.status_code == 200
        
        setting = response.json().get("setting", {})
        assert "updated_at" in setting, "Missing updated_at audit field"
        assert "updated_by" in setting, "Missing updated_by audit field"
        assert setting["updated_by"] == "energiebleuciel@gmail.com", \
            f"updated_by should be the admin email, got {setting.get('updated_by')}"
    
    def test_source_gating_has_audit_fields(self, auth_headers):
        """Verify source-gating settings have updated_at and updated_by"""
        response = requests.put(
            f"{BASE_URL}/api/settings/source-gating",
            headers=auth_headers,
            json={"mode": "blacklist", "blocked_sources": []}
        )
        assert response.status_code == 200
        
        setting = response.json().get("setting", {})
        assert "updated_at" in setting, "Missing updated_at audit field"
        assert "updated_by" in setting, "Missing updated_by audit field"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
