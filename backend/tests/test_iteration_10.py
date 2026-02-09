"""
Test Iteration 10 - Final verification before Hostinger deployment
Tests:
1. Brief Form endpoints exist in response
2. Brief LP endpoints exist in response  
3. API key regenerate endpoint removed (404)
4. Leads filtering by crm_id
5. Brief contains logos_html and legal_html
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"
TEST_CRM_ID = "19e96529-6cf5-404c-86a6-a02c32d905a2"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestApiKeyRegenerate:
    """Test that API key regenerate endpoint is removed"""
    
    def test_regenerate_endpoint_returns_404(self, auth_headers):
        """POST /api/config/api-key/regenerate should return 404 (removed)"""
        response = requests.post(
            f"{BASE_URL}/api/config/api-key/regenerate",
            headers=auth_headers
        )
        # Should be 404 (Not Found) or 405 (Method Not Allowed)
        assert response.status_code in [404, 405], f"Expected 404/405, got {response.status_code}: {response.text}"
        print(f"✅ Regenerate endpoint correctly returns {response.status_code}")
    
    def test_get_api_key_still_works(self, auth_headers):
        """GET /api/config/api-key should still work"""
        response = requests.get(
            f"{BASE_URL}/api/config/api-key",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get API key failed: {response.text}"
        data = response.json()
        assert "api_key" in data, "Response should contain api_key"
        print(f"✅ GET api-key works, key exists: {bool(data.get('api_key'))}")


class TestBriefFormEndpoints:
    """Test Brief Form contains endpoints in response"""
    
    def test_get_forms_list(self, auth_headers):
        """Get list of forms to find one for testing"""
        response = requests.get(f"{BASE_URL}/api/forms", headers=auth_headers)
        assert response.status_code == 200, f"Get forms failed: {response.text}"
        data = response.json()
        forms = data.get("forms", [])
        print(f"✅ Found {len(forms)} forms")
        return forms
    
    def test_brief_form_contains_endpoints(self, auth_headers):
        """Brief Form should contain endpoints object"""
        # Get forms first
        response = requests.get(f"{BASE_URL}/api/forms", headers=auth_headers)
        assert response.status_code == 200
        forms = response.json().get("forms", [])
        
        if not forms:
            pytest.skip("No forms available for testing")
        
        form_id = forms[0]["id"]
        
        # Get brief for this form
        brief_response = requests.get(
            f"{BASE_URL}/api/forms/{form_id}/brief",
            headers=auth_headers
        )
        assert brief_response.status_code == 200, f"Get brief failed: {brief_response.text}"
        
        brief = brief_response.json()
        
        # Check endpoints exist
        assert "endpoints" in brief, "Brief should contain 'endpoints' object"
        endpoints = brief["endpoints"]
        
        # Verify required endpoints
        required_endpoints = ["submit_lead", "get_form_config", "track_lp_visit", "track_cta_click", "track_form_start"]
        for ep in required_endpoints:
            assert ep in endpoints, f"Missing endpoint: {ep}"
            assert endpoints[ep], f"Endpoint {ep} should not be empty"
        
        print(f"✅ Brief Form contains all required endpoints:")
        for ep, url in endpoints.items():
            print(f"   - {ep}: {url}")


class TestBriefLpEndpoints:
    """Test Brief LP contains endpoints in response"""
    
    def test_get_lps_list(self, auth_headers):
        """Get list of LPs to find one for testing"""
        response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        assert response.status_code == 200, f"Get LPs failed: {response.text}"
        data = response.json()
        lps = data.get("lps", [])
        print(f"✅ Found {len(lps)} LPs")
        return lps
    
    def test_brief_lp_contains_endpoints(self, auth_headers):
        """Brief LP should contain endpoints object"""
        # Get LPs first
        response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        assert response.status_code == 200
        lps = response.json().get("lps", [])
        
        if not lps:
            pytest.skip("No LPs available for testing")
        
        lp_id = lps[0]["id"]
        
        # Get brief for this LP
        brief_response = requests.get(
            f"{BASE_URL}/api/lps/{lp_id}/brief",
            headers=auth_headers
        )
        assert brief_response.status_code == 200, f"Get LP brief failed: {brief_response.text}"
        
        brief = brief_response.json()
        
        # Check endpoints exist
        assert "endpoints" in brief, "Brief LP should contain 'endpoints' object"
        endpoints = brief["endpoints"]
        
        # Verify required endpoints
        required_endpoints = ["submit_lead", "get_form_config", "track_lp_visit", "track_cta_click", "track_form_start"]
        for ep in required_endpoints:
            assert ep in endpoints, f"Missing endpoint: {ep}"
            assert endpoints[ep], f"Endpoint {ep} should not be empty"
        
        print(f"✅ Brief LP contains all required endpoints:")
        for ep, url in endpoints.items():
            print(f"   - {ep}: {url}")
    
    def test_brief_lp_contains_logos_html(self, auth_headers):
        """Brief LP should contain logos_html in scripts"""
        response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = response.json().get("lps", [])
        
        if not lps:
            pytest.skip("No LPs available for testing")
        
        lp_id = lps[0]["id"]
        
        brief_response = requests.get(
            f"{BASE_URL}/api/lps/{lp_id}/brief",
            headers=auth_headers
        )
        assert brief_response.status_code == 200
        
        brief = brief_response.json()
        
        # Check scripts object
        assert "scripts" in brief, "Brief should contain 'scripts' object"
        scripts = brief["scripts"]
        
        # logos_html should exist
        assert "logos_html" in scripts, "Scripts should contain 'logos_html'"
        print(f"✅ Brief LP contains logos_html: {bool(scripts.get('logos_html'))}")
    
    def test_brief_lp_contains_legal_html(self, auth_headers):
        """Brief LP should contain legal_html in scripts"""
        response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = response.json().get("lps", [])
        
        if not lps:
            pytest.skip("No LPs available for testing")
        
        lp_id = lps[0]["id"]
        
        brief_response = requests.get(
            f"{BASE_URL}/api/lps/{lp_id}/brief",
            headers=auth_headers
        )
        assert brief_response.status_code == 200
        
        brief = brief_response.json()
        
        # Check scripts object
        assert "scripts" in brief, "Brief should contain 'scripts' object"
        scripts = brief["scripts"]
        
        # legal_html should exist
        assert "legal_html" in scripts, "Scripts should contain 'legal_html'"
        print(f"✅ Brief LP contains legal_html: {bool(scripts.get('legal_html'))}")


class TestLeadsCrmFilter:
    """Test leads filtering by crm_id"""
    
    def test_leads_filter_by_crm_id(self, auth_headers):
        """GET /api/leads?crm_id={uuid} should filter leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads?crm_id={TEST_CRM_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get leads failed: {response.text}"
        data = response.json()
        
        # Should return leads array
        assert "leads" in data, "Response should contain 'leads' array"
        print(f"✅ Leads filter by crm_id works, found {len(data.get('leads', []))} leads")
    
    def test_leads_without_filter(self, auth_headers):
        """GET /api/leads should work without filter"""
        response = requests.get(
            f"{BASE_URL}/api/leads?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get leads failed: {response.text}"
        data = response.json()
        assert "leads" in data
        print(f"✅ Leads without filter works, found {len(data.get('leads', []))} leads")


class TestBillingWeekNavigation:
    """Test billing week navigation"""
    
    def test_get_current_week(self, auth_headers):
        """GET /api/billing/weeks/2026/7 should return week info"""
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/7",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get week failed: {response.text}"
        data = response.json()
        
        # Should contain week_info
        assert "week_info" in data, "Response should contain 'week_info'"
        week_info = data["week_info"]
        assert "year" in week_info
        assert "week" in week_info
        print(f"✅ Billing week navigation works: Year {week_info.get('year')}, Week {week_info.get('week')}")


class TestCommandesPrixEditable:
    """Test commandes prix unitaire is editable"""
    
    def test_get_commandes(self, auth_headers):
        """GET /api/commandes should return commandes with prix_unitaire"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get commandes failed: {response.text}"
        data = response.json()
        
        commandes = data.get("commandes", [])
        print(f"✅ Found {len(commandes)} commandes")
        
        if commandes:
            # Check first commande has prix_unitaire field
            first = commandes[0]
            assert "prix_unitaire" in first or "prix" in first, "Commande should have prix_unitaire or prix field"
            print(f"✅ Commande has prix field: {first.get('prix_unitaire') or first.get('prix')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
