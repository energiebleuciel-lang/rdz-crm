"""
Client 360 - Phase 3.2 Backend API Tests
Tests for client detail page endpoints: summary, crm, notes, activity
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test client ID (SIM_ZR7_Client_Alpha - has VIP status and existing data)
TEST_CLIENT_ID = "decc9722-8ab2-49c2-91d7-47c919913b65"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "energiebleuciel@gmail.com",
        "password": "92Ruemarxdormoy"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestClientDetailEndpoint:
    """Tests for GET /api/clients/{id} - enriched client data"""

    def test_get_client_detail_success(self, api_client):
        """Client detail returns enriched data with CRM fields"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "client" in data
        client = data["client"]
        
        # Basic fields
        assert client["id"] == TEST_CLIENT_ID
        assert client["entity"] == "ZR7"
        assert client["name"] == "SIM_ZR7_Client_Alpha"
        
        # Enriched fields (Phase 3.1)
        assert "has_valid_channel" in client
        assert "deliverable_reason" in client
        assert "auto_send_enabled" in client
        assert "total_leads_received" in client
        assert "total_leads_this_week" in client
        
        # CRM fields (Phase 3.2)
        assert "client_status" in client
        assert "global_rating" in client
        assert "internal_notes" in client
        assert isinstance(client["internal_notes"], list)

    def test_get_client_not_found(self, api_client):
        """Returns 404 for non-existent client"""
        response = api_client.get(f"{BASE_URL}/api/clients/non-existent-uuid")
        assert response.status_code == 404


class TestClientSummaryEndpoint:
    """Tests for GET /api/clients/{id}/summary - performance aggregation"""

    def test_summary_day_grouping(self, api_client):
        """Summary returns day-grouped performance data"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/summary?group_by=day")
        assert response.status_code == 200
        
        data = response.json()
        assert data["client_id"] == TEST_CLIENT_ID
        assert data["group_by"] == "day"
        
        # Totals
        assert "totals" in data
        totals = data["totals"]
        assert "sent" in totals
        assert "billable" in totals
        assert "rejected" in totals
        assert "failed" in totals
        assert "reject_rate" in totals
        
        # Periods array
        assert "periods" in data
        assert isinstance(data["periods"], list)
        
        # Metadata
        assert "from" in data
        assert "to" in data
        assert "next_delivery_day" in data
        assert "auto_send_enabled" in data

    def test_summary_week_grouping(self, api_client):
        """Summary works with week grouping"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/summary?group_by=week")
        assert response.status_code == 200
        assert response.json()["group_by"] == "week"

    def test_summary_month_grouping(self, api_client):
        """Summary works with month grouping"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/summary?group_by=month")
        assert response.status_code == 200
        assert response.json()["group_by"] == "month"

    def test_summary_period_has_produit_breakdown(self, api_client):
        """Period data includes produit breakdown"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/summary?group_by=day")
        assert response.status_code == 200
        
        data = response.json()
        if data["periods"]:
            period = data["periods"][0]
            assert "period" in period
            assert "sent" in period
            assert "billable" in period
            assert "by_produit" in period
            assert isinstance(period["by_produit"], dict)


class TestClientCRMEndpoint:
    """Tests for PUT /api/clients/{id}/crm - CRM field updates"""

    def test_update_global_rating(self, api_client):
        """Can update global rating via CRM endpoint"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"global_rating": 3}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["client"]["global_rating"] == 3
        
        # Reset to original value
        api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"global_rating": 4}
        )

    def test_update_client_status(self, api_client):
        """Can update client status (Normal/VIP/Watchlist/Blocked)"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"client_status": "Watchlist"}
        )
        assert response.status_code == 200
        assert response.json()["client"]["client_status"] == "Watchlist"
        
        # Reset to VIP
        api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"client_status": "VIP"}
        )

    def test_update_payment_rating(self, api_client):
        """Can update payment rating"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"payment_rating": 4}
        )
        assert response.status_code == 200
        assert response.json()["client"]["payment_rating"] == 4

    def test_update_accounting_status(self, api_client):
        """Can update accounting status"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"accounting_status": "up_to_date"}
        )
        assert response.status_code == 200
        assert response.json()["client"]["accounting_status"] == "up_to_date"

    def test_update_payment_terms(self, api_client):
        """Can update payment terms"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"payment_terms": "net_30"}
        )
        assert response.status_code == 200
        assert response.json()["client"]["payment_terms"] == "net_30"

    def test_update_tags(self, api_client):
        """Can update tags array"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"tags": ["VIP", "strategic"]}
        )
        assert response.status_code == 200
        client = response.json()["client"]
        assert "VIP" in client["tags"]
        assert "strategic" in client["tags"]

    def test_crm_update_invalid_field_rejected(self, api_client):
        """Invalid fields are rejected"""
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"invalid_field": "value"}
        )
        assert response.status_code == 400

    def test_crm_update_logs_activity(self, api_client):
        """CRM update creates activity log entry"""
        # Make an update
        api_client.put(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/crm",
            json={"lead_satisfaction_rating": 5}
        )
        
        # Check activity log
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        assert response.status_code == 200
        activities = response.json()["activities"]
        
        # Should have a crm_update entry
        crm_updates = [a for a in activities if a["action"] == "crm_update"]
        assert len(crm_updates) > 0


class TestClientNotesEndpoint:
    """Tests for POST /api/clients/{id}/notes - internal notes"""

    def test_add_note_success(self, api_client):
        """Can add internal note"""
        response = api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/notes",
            json={"text": "TEST_pytest_note: Test note added by pytest"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        note = response.json()["note"]
        assert "id" in note
        assert note["text"] == "TEST_pytest_note: Test note added by pytest"
        assert "author" in note
        assert "created_at" in note

    def test_add_empty_note_rejected(self, api_client):
        """Empty note text is rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/notes",
            json={"text": ""}
        )
        assert response.status_code == 400

    def test_add_whitespace_note_rejected(self, api_client):
        """Whitespace-only note is rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/notes",
            json={"text": "   "}
        )
        assert response.status_code == 400

    def test_note_appears_in_activity(self, api_client):
        """Added note appears in activity timeline"""
        # Add a note
        note_text = "TEST_activity_note: Note for activity check"
        api_client.post(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/notes",
            json={"text": note_text}
        )
        
        # Check activity
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        activities = response.json()["activities"]
        
        note_activities = [a for a in activities if a["action"] == "note_added"]
        assert len(note_activities) > 0

    def test_note_appears_in_client_detail(self, api_client):
        """Added note appears in client internal_notes array"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}")
        client = response.json()["client"]
        
        assert "internal_notes" in client
        assert len(client["internal_notes"]) > 0
        # Notes should have correct structure
        note = client["internal_notes"][0]
        assert "id" in note
        assert "text" in note
        assert "author" in note
        assert "created_at" in note


class TestClientActivityEndpoint:
    """Tests for GET /api/clients/{id}/activity - activity timeline"""

    def test_activity_returns_array(self, api_client):
        """Activity endpoint returns activities array"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        assert response.status_code == 200
        
        data = response.json()
        assert "activities" in data
        assert isinstance(data["activities"], list)
        assert "count" in data

    def test_activity_includes_crm_updates(self, api_client):
        """Activity includes CRM update events"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        activities = response.json()["activities"]
        
        crm_updates = [a for a in activities if a["action"] == "crm_update"]
        assert len(crm_updates) > 0

    def test_activity_includes_notes(self, api_client):
        """Activity includes note_added events"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        activities = response.json()["activities"]
        
        notes = [a for a in activities if a["action"] == "note_added"]
        assert len(notes) > 0

    def test_activity_includes_delivery_rejects(self, api_client):
        """Activity includes delivery_rejected events (if any)"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        activities = response.json()["activities"]
        
        rejects = [a for a in activities if a["action"] == "delivery_rejected"]
        # This client has 1 rejected delivery
        assert len(rejects) >= 1
        
        # Verify reject structure
        if rejects:
            reject = rejects[0]
            assert "details" in reject
            assert "reason" in reject["details"]
            assert "produit" in reject["details"]

    def test_activity_sorted_by_date_desc(self, api_client):
        """Activities are sorted by date descending (newest first)"""
        response = api_client.get(f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/activity")
        activities = response.json()["activities"]
        
        if len(activities) > 1:
            dates = [a.get("created_at") for a in activities if a.get("created_at")]
            # Check descending order
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "Activities not sorted by date desc"


class TestClientListEnrichment:
    """Tests for GET /api/clients - list should include enriched fields"""

    def test_client_list_has_enriched_fields(self, api_client):
        """Client list includes Phase 3.1 enriched fields"""
        response = api_client.get(f"{BASE_URL}/api/clients?entity=ZR7")
        assert response.status_code == 200
        
        clients = response.json()["clients"]
        assert len(clients) > 0
        
        client = clients[0]
        assert "has_valid_channel" in client
        assert "auto_send_enabled" in client
        assert "total_leads_received" in client
        assert "total_leads_this_week" in client


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
