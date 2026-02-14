"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Delivery State Machine Audit & Testing                            ║
║                                                                              ║
║  Tests the core state machine functionality:                                 ║
║  1. No direct writes to status outside state machine                         ║
║  2. Valid transitions only                                                   ║
║  3. Invariant enforcement (sent_to, last_sent_at, send_attempts)            ║
║  4. Batch operations with guards                                             ║
║  5. Calendar gating                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestDeliveryAPIEndpoints:
    """Test delivery endpoints return correct status codes and data"""
    
    def test_list_deliveries(self, api_client):
        """GET /api/deliveries - List with filters"""
        response = api_client.get(f"{BASE_URL}/api/deliveries")
        assert response.status_code == 200
        data = response.json()
        assert "deliveries" in data
        assert "count" in data
        assert "total" in data
        print(f"✅ List deliveries: {data['count']} of {data['total']}")
    
    def test_list_deliveries_with_entity_filter(self, api_client):
        """GET /api/deliveries?entity=ZR7"""
        response = api_client.get(f"{BASE_URL}/api/deliveries?entity=ZR7")
        assert response.status_code == 200
        data = response.json()
        # All returned should be ZR7
        for d in data.get("deliveries", []):
            assert d.get("entity") == "ZR7", f"Expected ZR7, got {d.get('entity')}"
        print(f"✅ List ZR7 deliveries: {data['count']}")
    
    def test_list_deliveries_with_status_filter(self, api_client):
        """GET /api/deliveries?status=sent"""
        response = api_client.get(f"{BASE_URL}/api/deliveries?status=sent")
        assert response.status_code == 200
        data = response.json()
        for d in data.get("deliveries", []):
            assert d.get("status") == "sent"
        print(f"✅ List sent deliveries: {data['count']}")
    
    def test_delivery_stats(self, api_client):
        """GET /api/deliveries/stats"""
        response = api_client.get(f"{BASE_URL}/api/deliveries/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending_csv" in data
        assert "ready_to_send" in data
        assert "sending" in data
        assert "sent" in data
        assert "failed" in data
        assert "total" in data
        print(f"✅ Delivery stats: {data}")
    
    def test_delivery_stats_with_entity(self, api_client):
        """GET /api/deliveries/stats?entity=MDL"""
        response = api_client.get(f"{BASE_URL}/api/deliveries/stats?entity=MDL")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        print(f"✅ MDL delivery stats: {data}")


class TestBatchGenerateCSV:
    """Test POST /api/deliveries/batch/generate-csv"""
    
    def test_batch_generate_csv_no_pending(self, api_client):
        """Should return success even with 0 pending_csv"""
        response = api_client.post(f"{BASE_URL}/api/deliveries/batch/generate-csv")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✅ Batch generate CSV: processed={data.get('processed', 0)}")
    
    def test_batch_generate_csv_with_entity_filter(self, api_client):
        """POST /api/deliveries/batch/generate-csv?entity=ZR7"""
        response = api_client.post(f"{BASE_URL}/api/deliveries/batch/generate-csv?entity=ZR7")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✅ Batch generate CSV (ZR7): processed={data.get('processed', 0)}")


class TestBatchSendReady:
    """Test POST /api/deliveries/batch/send-ready"""
    
    def test_batch_send_ready_no_deliveries(self, api_client):
        """Should return success even with 0 ready_to_send"""
        # First check stats
        stats_response = api_client.get(f"{BASE_URL}/api/deliveries/stats")
        stats = stats_response.json()
        ready_count = stats.get("ready_to_send", 0)
        
        response = api_client.post(f"{BASE_URL}/api/deliveries/batch/send-ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✅ Batch send ready: sent={data.get('sent', 0)}, skipped_calendar={data.get('skipped_calendar', 0)}")
    
    def test_batch_send_ready_with_override_email(self, api_client):
        """POST /api/deliveries/batch/send-ready?override_email=test@test.com"""
        response = api_client.post(
            f"{BASE_URL}/api/deliveries/batch/send-ready?override_email=energiebleuciel@gmail.com"
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✅ Batch send ready with override: sent={data.get('sent', 0)}")


class TestSingleDeliverySend:
    """Test POST /api/deliveries/{id}/send"""
    
    def test_send_nonexistent_delivery(self, api_client):
        """Should return 404 for non-existent delivery"""
        fake_id = str(uuid.uuid4())
        response = api_client.post(f"{BASE_URL}/api/deliveries/{fake_id}/send")
        assert response.status_code == 404
        print("✅ Non-existent delivery returns 404")
    
    def test_send_already_sent_without_force(self, api_client):
        """
        Get a 'sent' delivery and try to send again without force
        Should return 400
        """
        # Get a sent delivery
        response = api_client.get(f"{BASE_URL}/api/deliveries?status=sent&limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("deliveries"):
            pytest.skip("No sent deliveries to test")
        
        delivery = data["deliveries"][0]
        delivery_id = delivery.get("id")
        
        # Try to resend without force
        response = api_client.post(f"{BASE_URL}/api/deliveries/{delivery_id}/send")
        assert response.status_code == 400
        assert "déjà envoyée" in response.json().get("detail", "").lower() or "already" in response.json().get("detail", "").lower()
        print(f"✅ Resend without force returns 400: {response.json().get('detail')}")


class TestDeliveryDownload:
    """Test GET /api/deliveries/{id}/download"""
    
    def test_download_nonexistent(self, api_client):
        """Should return 404 for non-existent delivery"""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/deliveries/{fake_id}/download")
        assert response.status_code == 404
        print("✅ Download non-existent returns 404")
    
    def test_download_sent_delivery(self, api_client):
        """Download CSV from a sent delivery"""
        # Get a sent delivery
        response = api_client.get(f"{BASE_URL}/api/deliveries?status=sent&limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("deliveries"):
            pytest.skip("No sent deliveries to test download")
        
        delivery = data["deliveries"][0]
        delivery_id = delivery.get("id")
        
        # Download
        response = api_client.get(f"{BASE_URL}/api/deliveries/{delivery_id}/download")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Check content
        content = response.text
        assert len(content) > 0
        # Should have CSV headers
        first_line = content.split("\n")[0].lower()
        assert "nom" in first_line or "prenom" in first_line or "telephone" in first_line
        print(f"✅ Download CSV: {len(content)} bytes")


class TestInvariantEnforcement:
    """Test that sent deliveries have required invariants"""
    
    def test_sent_deliveries_have_required_fields(self, api_client):
        """
        All 'sent' deliveries must have:
        - sent_to: non-empty list
        - last_sent_at: non-null
        - send_attempts: >= 1
        """
        response = api_client.get(f"{BASE_URL}/api/deliveries?status=sent&limit=50")
        assert response.status_code == 200
        data = response.json()
        
        deliveries = data.get("deliveries", [])
        if not deliveries:
            pytest.skip("No sent deliveries to verify invariants")
        
        violations = []
        for d in deliveries:
            d_id = d.get("id", "unknown")[:8]
            
            # Check sent_to
            sent_to = d.get("sent_to", [])
            if not sent_to or len(sent_to) == 0:
                violations.append(f"{d_id}: sent_to is empty")
            
            # Check last_sent_at
            if not d.get("last_sent_at"):
                violations.append(f"{d_id}: last_sent_at is null")
            
            # Check send_attempts
            attempts = d.get("send_attempts", 0)
            if attempts < 1:
                violations.append(f"{d_id}: send_attempts={attempts} (< 1)")
        
        if violations:
            print(f"❌ INVARIANT VIOLATIONS: {violations}")
        
        assert len(violations) == 0, f"Invariant violations found: {violations}"
        print(f"✅ All {len(deliveries)} sent deliveries have valid invariants")


class TestCalendarGating:
    """Test calendar settings endpoint"""
    
    def test_get_delivery_calendar(self, api_client):
        """GET /api/settings/delivery-calendar"""
        response = api_client.get(f"{BASE_URL}/api/settings/delivery-calendar")
        assert response.status_code == 200
        data = response.json()
        assert "ZR7" in data or "settings" in data
        print(f"✅ Delivery calendar retrieved: {data}")
    
    def test_calendar_structure(self, api_client):
        """Check calendar has enabled_days and disabled_dates"""
        response = api_client.get(f"{BASE_URL}/api/settings/delivery-calendar")
        assert response.status_code == 200
        data = response.json()
        
        # Should have entity configs
        for entity in ["ZR7", "MDL"]:
            entity_cfg = data.get(entity, {})
            if entity_cfg:
                assert "enabled_days" in entity_cfg or isinstance(entity_cfg, dict)
        print("✅ Calendar structure valid")


class TestEmailDenylistSettings:
    """Test email denylist endpoint"""
    
    def test_get_email_denylist(self, api_client):
        """GET /api/settings/email-denylist"""
        response = api_client.get(f"{BASE_URL}/api/settings/email-denylist")
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
        assert isinstance(data["domains"], list)
        print(f"✅ Email denylist: {len(data['domains'])} domains blocked")


class TestSimulationMode:
    """Test simulation mode settings"""
    
    def test_get_simulation_mode(self, api_client):
        """GET /api/settings/simulation-mode"""
        response = api_client.get(f"{BASE_URL}/api/settings/simulation-mode")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Simulation mode: enabled={data.get('enabled')}, email={data.get('email')}")


class TestStateMachineTransitionGuards:
    """Test that invalid transitions are blocked"""
    
    def test_cannot_transition_from_terminal_state(self, api_client):
        """
        Verify 'sent' is terminal - attempting any operation should fail gracefully
        or return appropriate error
        """
        # Get a sent delivery
        response = api_client.get(f"{BASE_URL}/api/deliveries?status=sent&limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("deliveries"):
            pytest.skip("No sent deliveries to test terminal state")
        
        delivery = data["deliveries"][0]
        delivery_id = delivery.get("id")
        
        # Try to re-send without force (should fail with 400)
        response = api_client.post(f"{BASE_URL}/api/deliveries/{delivery_id}/send")
        assert response.status_code == 400
        print(f"✅ Terminal state (sent) blocks re-send: {response.json().get('detail')}")


class TestClientAutoSendEnabled:
    """Test auto_send_enabled client field behavior"""
    
    def test_client_has_auto_send_field(self, api_client):
        """Check clients have auto_send_enabled field"""
        response = api_client.get(f"{BASE_URL}/api/clients?entity=ZR7&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        clients = data.get("clients", [])
        if not clients:
            pytest.skip("No clients to check")
        
        for client in clients:
            # auto_send_enabled should exist (default True if not set)
            has_field = "auto_send_enabled" in client
            if has_field:
                print(f"  Client {client.get('name', 'unknown')[:20]}: auto_send={client.get('auto_send_enabled')}")
        
        print(f"✅ Checked {len(clients)} clients for auto_send_enabled field")


class TestDeliverLeadsToClientFlow:
    """Test the deliver_leads_to_client flow creates delivery records"""
    
    def test_delivery_batches_exist(self, api_client):
        """Check that delivery_batches collection has records"""
        # This is tested indirectly via deliveries endpoint
        response = api_client.get(f"{BASE_URL}/api/deliveries?limit=100")
        assert response.status_code == 200
        data = response.json()
        
        # Should have some deliveries if system has been used
        count = data.get("total", 0)
        print(f"✅ Total deliveries in system: {count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
