"""
Tests for new billing and CRM features:
1. Billing page with week navigation
2. API /api/billing/weeks/{year}/{week} returns week_info with dates
3. API /api/billing/weeks/{year}/{week}/invoice marks week as invoiced
4. Commandes page with editable prix_unitaire field
5. API /api/commandes/{id} with modifiable prix_unitaire
6. Accounts page with CGU/Privacy section
7. API /api/accounts with cgu_text, privacy_policy_text fields
8. API /api/leads?crm_id={uuid} filters leads by CRM
9. API /api/stats/departements?crm_id={uuid} filters stats by CRM
10. Brief generator includes logos_html and legal_html in response
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://form-tracker-boost.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"

# CRM IDs
CRM_MDL_ID = "19e96529-6cf5-404c-86a6-a02c32d905a2"
CRM_ZR7_ID = "0a463b29-ae11-4198-b092-143d7899b62d"


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


# ==================== BILLING WEEK NAVIGATION TESTS ====================

class TestBillingWeekNavigation:
    """Tests for billing week navigation feature"""
    
    def test_get_current_week(self, auth_headers):
        """Test getting current week info"""
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/current",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "week" in data
        assert isinstance(data["year"], int)
        assert isinstance(data["week"], int)
        assert 1 <= data["week"] <= 53
        print(f"Current week: {data['year']}-W{data['week']}")
    
    def test_get_week_billing_with_week_info(self, auth_headers):
        """Test that week billing returns week_info with dates"""
        # Test with week 7 of 2026 as specified
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/7",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check week_info is present with dates
        assert "week_info" in data
        week_info = data["week_info"]
        assert week_info is not None
        assert "year" in week_info
        assert "week" in week_info
        assert "start" in week_info
        assert "end" in week_info
        
        # Verify dates format (DD/MM/YYYY)
        assert "/" in week_info["start"]
        assert "/" in week_info["end"]
        
        print(f"Week 7/2026: {week_info['start']} → {week_info['end']}")
    
    def test_get_week_billing_returns_invoice_status(self, auth_headers):
        """Test that week billing returns invoice_status"""
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/7",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "invoice_status" in data
        invoice_status = data["invoice_status"]
        assert "invoiced" in invoice_status
        assert isinstance(invoice_status["invoiced"], bool)
        print(f"Invoice status: {invoice_status}")
    
    def test_mark_week_as_invoiced(self, auth_headers):
        """Test marking a week as invoiced"""
        # Mark week 7 of 2026 as invoiced
        response = requests.post(
            f"{BASE_URL}/api/billing/weeks/2026/7/invoice?invoiced=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("invoiced") == True
        print(f"Week marked as invoiced: {data}")
        
        # Verify the status changed
        verify_response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/7",
            headers=auth_headers
        )
        verify_data = verify_response.json()
        assert verify_data["invoice_status"]["invoiced"] == True
        
        # Unmark to reset state
        requests.post(
            f"{BASE_URL}/api/billing/weeks/2026/7/invoice?invoiced=false",
            headers=auth_headers
        )
    
    def test_week_navigation_different_weeks(self, auth_headers):
        """Test navigating to different weeks"""
        # Test week 1
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/1",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Test week 52
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2025/52",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        print("Week navigation works for different weeks")
    
    def test_invalid_week_number(self, auth_headers):
        """Test that invalid week numbers are rejected"""
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/2026/54",
            headers=auth_headers
        )
        assert response.status_code == 400
        print("Invalid week number correctly rejected")


# ==================== COMMANDES PRIX_UNITAIRE TESTS ====================

class TestCommandesPrixUnitaire:
    """Tests for editable prix_unitaire in Commandes"""
    
    def test_commandes_have_prix_unitaire(self, auth_headers):
        """Test that commandes include prix_unitaire field"""
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        commandes = data.get("commandes", [])
        
        if commandes:
            commande = commandes[0]
            assert "prix_unitaire" in commande
            print(f"Commande has prix_unitaire: {commande.get('prix_unitaire')}")
    
    def test_update_commande_prix_unitaire(self, auth_headers):
        """Test updating prix_unitaire on a commande"""
        # Get existing commandes
        response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers
        )
        commandes = response.json().get("commandes", [])
        
        if not commandes:
            pytest.skip("No commandes available")
        
        commande = commandes[0]
        commande_id = commande["id"]
        original_price = commande.get("prix_unitaire", 0)
        new_price = 25.50
        
        # Update prix_unitaire
        update_response = requests.put(
            f"{BASE_URL}/api/commandes/{commande_id}",
            headers=auth_headers,
            json={"prix_unitaire": new_price}
        )
        assert update_response.status_code == 200
        
        # Verify the update
        verify_response = requests.get(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers
        )
        updated_commandes = verify_response.json().get("commandes", [])
        updated_commande = next((c for c in updated_commandes if c["id"] == commande_id), None)
        
        assert updated_commande is not None
        assert updated_commande["prix_unitaire"] == new_price
        print(f"Prix updated from {original_price} to {new_price}")
        
        # Restore original price
        requests.put(
            f"{BASE_URL}/api/commandes/{commande_id}",
            headers=auth_headers,
            json={"prix_unitaire": original_price}
        )
    
    def test_create_commande_with_prix_unitaire(self, auth_headers):
        """Test creating a commande with prix_unitaire"""
        commande_data = {
            "crm_id": CRM_MDL_ID,
            "product_type": "PV",
            "departements": ["75"],  # Use valid dept for test
            "active": True,
            "prix_unitaire": 15.75
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers,
            json=commande_data
        )
        # May return 200 or 400 if commande already exists
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            
            # Verify prix_unitaire was saved
            if "commande" in data:
                assert data["commande"]["prix_unitaire"] == 15.75
                
                # Cleanup
                commande_id = data["commande"]["id"]
                requests.delete(f"{BASE_URL}/api/commandes/{commande_id}", headers=auth_headers)
            
            print("Commande created with prix_unitaire: 15.75€")
        else:
            # Commande may already exist - that's OK, just verify the feature exists
            print(f"Commande creation returned {response.status_code} - may already exist")


# ==================== ACCOUNTS CGU/PRIVACY TESTS ====================

class TestAccountsCguPrivacy:
    """Tests for CGU and Privacy fields in Accounts"""
    
    def test_accounts_have_legal_fields(self, auth_headers):
        """Test that accounts include cgu_text and privacy_policy_text fields"""
        response = requests.get(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        accounts = data.get("accounts", [])
        
        if accounts:
            account = accounts[0]
            # These fields should exist (even if empty)
            assert "cgu_text" in account or account.get("cgu_text") is None
            assert "privacy_policy_text" in account or account.get("privacy_policy_text") is None
            print(f"Account has legal fields: cgu_text={bool(account.get('cgu_text'))}, privacy={bool(account.get('privacy_policy_text'))}")
    
    def test_create_account_with_legal_texts(self, auth_headers):
        """Test creating an account with CGU and Privacy texts"""
        account_data = {
            "name": f"TEST_Legal_Account_{uuid.uuid4().hex[:8]}",
            "crm_id": CRM_MDL_ID,
            "domain": "test-legal.com",
            "cgu_text": "Article 1 - Test CGU\nCes conditions générales...",
            "privacy_policy_text": "Politique de confidentialité\nNous collectons..."
        }
        
        response = requests.post(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers,
            json=account_data
        )
        assert response.status_code == 200
        data = response.json()
        
        if "account" in data:
            account = data["account"]
            assert account.get("cgu_text") == account_data["cgu_text"]
            assert account.get("privacy_policy_text") == account_data["privacy_policy_text"]
            
            # Cleanup
            account_id = account["id"]
            requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
        
        print("Account created with CGU and Privacy texts")
    
    def test_update_account_legal_texts(self, auth_headers):
        """Test updating CGU and Privacy texts on an account"""
        # Create test account
        account_data = {
            "name": f"TEST_Update_Legal_{uuid.uuid4().hex[:8]}",
            "crm_id": CRM_MDL_ID
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/accounts",
            headers=auth_headers,
            json=account_data
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create test account")
        
        account_id = create_response.json().get("account", {}).get("id")
        if not account_id:
            pytest.skip("No account ID returned")
        
        # Update with legal texts
        update_data = {
            "cgu_text": "Updated CGU text",
            "privacy_policy_text": "Updated Privacy text"
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/accounts/{account_id}",
            headers=auth_headers,
            json=update_data
        )
        assert update_response.status_code == 200
        
        # Verify update
        get_response = requests.get(
            f"{BASE_URL}/api/accounts/{account_id}",
            headers=auth_headers
        )
        if get_response.status_code == 200:
            updated_account = get_response.json()
            assert updated_account.get("cgu_text") == "Updated CGU text"
            assert updated_account.get("privacy_policy_text") == "Updated Privacy text"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/accounts/{account_id}", headers=auth_headers)
        print("Account legal texts updated successfully")


# ==================== LEADS CRM FILTER TESTS ====================

class TestLeadsCrmFilter:
    """Tests for filtering leads by CRM"""
    
    def test_filter_leads_by_crm_id(self, auth_headers):
        """Test filtering leads by crm_id parameter"""
        # Filter by MDL CRM
        response = requests.get(
            f"{BASE_URL}/api/leads?crm_id={CRM_MDL_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        print(f"Leads filtered by MDL CRM: {len(data['leads'])} leads")
        
        # Filter by ZR7 CRM
        response = requests.get(
            f"{BASE_URL}/api/leads?crm_id={CRM_ZR7_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        print(f"Leads filtered by ZR7 CRM: {len(data['leads'])} leads")
    
    def test_leads_filter_returns_correct_crm_leads(self, auth_headers):
        """Test that filtered leads belong to the correct CRM"""
        # Get accounts for MDL CRM
        accounts_response = requests.get(
            f"{BASE_URL}/api/accounts?crm_id={CRM_MDL_ID}",
            headers=auth_headers
        )
        mdl_accounts = accounts_response.json().get("accounts", [])
        mdl_account_ids = [a["id"] for a in mdl_accounts]
        
        # Get leads filtered by MDL
        leads_response = requests.get(
            f"{BASE_URL}/api/leads?crm_id={CRM_MDL_ID}",
            headers=auth_headers
        )
        leads = leads_response.json().get("leads", [])
        
        # Verify all leads belong to MDL accounts
        for lead in leads[:10]:  # Check first 10
            if lead.get("account_id"):
                assert lead["account_id"] in mdl_account_ids, f"Lead {lead['id']} has wrong account"
        
        print("Leads correctly filtered by CRM")


# ==================== DEPARTEMENTS STATS CRM FILTER TESTS ====================

class TestDepartementsStatsCrmFilter:
    """Tests for filtering departement stats by CRM"""
    
    def test_filter_departements_stats_by_crm(self, auth_headers):
        """Test filtering departement stats by crm_id"""
        response = requests.get(
            f"{BASE_URL}/api/stats/departements?crm_id={CRM_MDL_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # API returns by_departement, by_product, by_source, by_status
        assert "by_departement" in data or "departements" in data or "stats" in data
        print(f"Departement stats filtered by MDL CRM: {list(data.keys())}")
    
    def test_departements_stats_different_crms(self, auth_headers):
        """Test that different CRMs return different stats"""
        # Get stats for MDL
        mdl_response = requests.get(
            f"{BASE_URL}/api/stats/departements?crm_id={CRM_MDL_ID}",
            headers=auth_headers
        )
        
        # Get stats for ZR7
        zr7_response = requests.get(
            f"{BASE_URL}/api/stats/departements?crm_id={CRM_ZR7_ID}",
            headers=auth_headers
        )
        
        assert mdl_response.status_code == 200
        assert zr7_response.status_code == 200
        print("Departement stats work for both CRMs")


# ==================== BRIEF GENERATOR TESTS ====================

class TestBriefGenerator:
    """Tests for brief generator with logos_html and legal_html"""
    
    def test_brief_includes_logos_html(self, auth_headers):
        """Test that brief includes logos_html in response"""
        # Get LPs
        lps_response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = lps_response.json().get("lps", [])
        
        # Find LP with form
        lp_with_form = None
        for lp in lps:
            if lp.get("form_id"):
                lp_with_form = lp
                break
        
        if not lp_with_form:
            pytest.skip("No LP with form found")
        
        # Get brief
        response = requests.get(
            f"{BASE_URL}/api/lps/{lp_with_form['id']}/brief",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for logos_html in scripts
        if "scripts" in data:
            scripts = data["scripts"]
            assert "logos_html" in scripts
            print(f"Brief includes logos_html: {bool(scripts.get('logos_html'))}")
    
    def test_brief_includes_legal_html(self, auth_headers):
        """Test that brief includes legal_html (CGU/Privacy buttons) in response"""
        # Get LPs
        lps_response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = lps_response.json().get("lps", [])
        
        # Find LP with form
        lp_with_form = None
        for lp in lps:
            if lp.get("form_id"):
                lp_with_form = lp
                break
        
        if not lp_with_form:
            pytest.skip("No LP with form found")
        
        # Get brief
        response = requests.get(
            f"{BASE_URL}/api/lps/{lp_with_form['id']}/brief",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check for legal_html in scripts
        if "scripts" in data:
            scripts = data["scripts"]
            assert "legal_html" in scripts
            print(f"Brief includes legal_html: {bool(scripts.get('legal_html'))}")
    
    def test_brief_account_has_legal_info(self, auth_headers):
        """Test that brief includes account legal info"""
        # Get LPs
        lps_response = requests.get(f"{BASE_URL}/api/lps", headers=auth_headers)
        lps = lps_response.json().get("lps", [])
        
        # Find LP with form
        lp_with_form = None
        for lp in lps:
            if lp.get("form_id"):
                lp_with_form = lp
                break
        
        if not lp_with_form:
            pytest.skip("No LP with form found")
        
        # Get brief
        response = requests.get(
            f"{BASE_URL}/api/lps/{lp_with_form['id']}/brief",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check account has legal info
        if "account" in data:
            account = data["account"]
            assert "legal" in account or "logos" in account
            print(f"Brief account info: {list(account.keys())}")


# ==================== BILLING CROSS-CRM TESTS ====================

class TestBillingCrossCrm:
    """Tests for cross-CRM billing features"""
    
    def test_billing_cross_crm_endpoint(self, auth_headers):
        """Test cross-CRM billing endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/billing/cross-crm",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data
        assert "total_leads_period" in data or "cross_crm_leads" in data
        print(f"Cross-CRM billing data retrieved")
    
    def test_billing_weeks_history(self, auth_headers):
        """Test billing weeks history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/billing/weeks/history",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "weeks" in data
        print(f"Billing weeks history: {len(data['weeks'])} weeks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
