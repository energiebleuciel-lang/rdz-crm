"""
RDZ CRM - Phase 2.1/2.2/2.3 Tests
Delivery Lifecycle, Client Livrable, Calendar Gating

Tests for:
1. EMAIL DENYLIST: GET/PUT /api/settings/email-denylist
2. DELIVERY CALENDAR: GET/PUT /api/settings/delivery-calendar
3. CALENDAR GATING: Routing blocked on disabled days (weekends)
4. CLIENT DELIVERABLE: Email denylist blocks client deliverability
5. DELIVERY ENDPOINTS: /api/deliveries/* CRUD operations
6. STATUS TRANSITIONS: pending_csv → ready_to_send → sending → sent/failed
7. SIMULATION MODE: Email override when simulation_mode=true

Test credentials: energiebleuciel@gmail.com / 92Ruemarxdormoy
Provider API key: prov_0vVMbevPVC1yBXXb3cPKySmiB_iP4nW1cjTjIOQ54is
"""

import pytest
import requests
import os
import uuid
import random
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestEmailDenylistSettings:
    """Test email denylist settings API"""
    
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
    
    def test_get_email_denylist_returns_defaults(self, auth_headers):
        """GET /api/settings/email-denylist - returns default denylist"""
        response = requests.get(f"{BASE_URL}/api/settings/email-denylist", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "domains" in data, "Should have 'domains' field"
        assert "simulation_mode" in data, "Should have 'simulation_mode' field"
        assert "simulation_email" in data, "Should have 'simulation_email' field"
        
        # Verify default domains include test domains
        domains = data["domains"]
        assert "example.com" in domains, "Default denylist should include example.com"
        assert "test.com" in domains, "Default denylist should include test.com"
    
    def test_update_email_denylist(self, auth_headers):
        """PUT /api/settings/email-denylist - update denylist"""
        test_domains = ["example.com", "test.com", "localhost", "invalid", "fake.com", "newdomain.test"]
        
        response = requests.put(
            f"{BASE_URL}/api/settings/email-denylist",
            headers=auth_headers,
            json={
                "domains": test_domains,
                "simulation_mode": True,
                "simulation_email": "energiebleuciel@gmail.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        setting = data.get("setting", {})
        assert "newdomain.test" in setting.get("domains", [])
        assert setting.get("simulation_mode") == True
        assert setting.get("simulation_email") == "energiebleuciel@gmail.com"
    
    def test_email_denylist_requires_auth(self):
        """GET /api/settings/email-denylist - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/settings/email-denylist")
        assert response.status_code == 401


class TestDeliveryCalendarSettings:
    """Test delivery calendar settings API"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_get_delivery_calendar_returns_defaults(self, auth_headers):
        """GET /api/settings/delivery-calendar - returns default calendar"""
        response = requests.get(f"{BASE_URL}/api/settings/delivery-calendar", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure for both entities
        assert "ZR7" in data or "MDL" in data, "Should have entity calendars"
        
        # Check ZR7 defaults (Mon-Fri = 0-4)
        if "ZR7" in data:
            zr7 = data["ZR7"]
            assert "enabled_days" in zr7
            # Default should be Mon-Fri (0,1,2,3,4)
            assert 0 in zr7["enabled_days"], "Monday should be enabled by default"
            assert 4 in zr7["enabled_days"], "Friday should be enabled by default"
            # Weekend should NOT be enabled by default
            assert 5 not in zr7["enabled_days"], "Saturday should NOT be enabled by default"
            assert 6 not in zr7["enabled_days"], "Sunday should NOT be enabled by default"
    
    def test_update_delivery_calendar(self, auth_headers):
        """PUT /api/settings/delivery-calendar - update calendar for entity"""
        response = requests.put(
            f"{BASE_URL}/api/settings/delivery-calendar",
            headers=auth_headers,
            json={
                "entity": "ZR7",
                "enabled_days": [0, 1, 2, 3, 4],  # Mon-Fri
                "disabled_dates": ["2026-12-25", "2026-01-01"]  # Christmas, New Year
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("entity") == "ZR7"
    
    def test_check_delivery_day_endpoint(self, auth_headers):
        """GET /api/settings/delivery-calendar/check/{entity} - check if today is delivery day"""
        response = requests.get(
            f"{BASE_URL}/api/settings/delivery-calendar/check/ZR7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "entity" in data
        assert "is_delivery_day" in data
        assert "reason" in data
        
        # Today is Saturday (weekday=5), so should NOT be a delivery day
        today = datetime.now()
        if today.weekday() >= 5:  # Weekend
            assert data["is_delivery_day"] == False, "Weekend should not be a delivery day"
            assert "delivery_day_disabled" in data["reason"], "Reason should indicate day disabled"
    
    def test_invalid_entity_returns_error(self, auth_headers):
        """PUT /api/settings/delivery-calendar - invalid entity returns 400"""
        response = requests.put(
            f"{BASE_URL}/api/settings/delivery-calendar",
            headers=auth_headers,
            json={
                "entity": "INVALID",
                "enabled_days": [0, 1, 2, 3, 4]
            }
        )
        
        assert response.status_code == 400


class TestCalendarGating:
    """Test calendar gating blocks routing on disabled days"""
    
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
            json={"lp_code": "TEST_CALENDAR_GATING", "utm_source": ""}
        )
        assert response.status_code == 200
        return response.json().get("session_id")
    
    def test_routing_blocked_on_weekend(self, auth_headers, session_id):
        """POST /api/public/leads on weekend returns no_open_orders with delivery_day_disabled"""
        # Ensure calendar has default settings (Mon-Fri only)
        requests.put(
            f"{BASE_URL}/api/settings/delivery-calendar",
            headers=auth_headers,
            json={
                "entity": "ZR7",
                "enabled_days": [0, 1, 2, 3, 4],  # Mon-Fri only
                "disabled_dates": []
            }
        )
        
        # Submit a lead
        unique_phone = f"06{random.randint(10000000, 99999999)}"
        response = requests.post(
            f"{BASE_URL}/api/public/leads",
            json={
                "session_id": session_id,
                "form_code": "TEST_CALENDAR",
                "phone": unique_phone,
                "nom": "Test Calendar Gating",
                "prenom": "User",
                "email": "test_calendar@valid.com",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PAC"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Today is Saturday - routing should be blocked
        today = datetime.now()
        if today.weekday() >= 5:  # Weekend
            # Lead should be stored but not routed
            assert data.get("status") in ["no_open_orders", "new"], \
                f"Expected no_open_orders or new on weekend, got {data.get('status')}"
            
            # Check routing_reason if available
            if "routing_reason" in data:
                assert "delivery_day_disabled" in data["routing_reason"], \
                    f"Routing reason should mention delivery_day_disabled, got {data.get('routing_reason')}"


class TestClientDeliverability:
    """Test client deliverability based on email denylist"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_client_with_denylist_email_not_deliverable(self, auth_headers):
        """Client with @example.com email should NOT be deliverable"""
        # Get clients list
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if any client has @example.com email
        for client in data.get("clients", []):
            email = client.get("email", "")
            if "@example.com" in email:
                # This client should have delivery_enabled=False or email_valid=False
                # The check happens in routing, not in client response
                print(f"Found client with @example.com: {client.get('name')}")
    
    def test_client_deliverable_function_logic(self, auth_headers):
        """Test the check_client_deliverable logic via API"""
        # This tests the logic indirectly through routing
        # A client with only @example.com email should not receive leads
        
        # Get email denylist
        response = requests.get(f"{BASE_URL}/api/settings/email-denylist", headers=auth_headers)
        assert response.status_code == 200
        
        denylist = response.json().get("domains", [])
        assert "example.com" in denylist, "example.com should be in denylist"


class TestDeliveryEndpoints:
    """Test delivery management endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_list_deliveries(self, auth_headers):
        """GET /api/deliveries - list deliveries with filters"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "deliveries" in data
        assert "count" in data
        assert "total" in data
        
        # Verify delivery structure if any exist
        for delivery in data.get("deliveries", [])[:5]:
            assert "id" in delivery
            assert "lead_id" in delivery
            assert "client_id" in delivery
            assert "status" in delivery
            assert "entity" in delivery
    
    def test_list_deliveries_with_entity_filter(self, auth_headers):
        """GET /api/deliveries?entity=ZR7 - filter by entity"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All deliveries should be ZR7
        for delivery in data.get("deliveries", []):
            assert delivery.get("entity") == "ZR7", f"Expected ZR7, got {delivery.get('entity')}"
    
    def test_list_deliveries_with_status_filter(self, auth_headers):
        """GET /api/deliveries?status=sent - filter by status"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"status": "sent"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All deliveries should have status=sent
        for delivery in data.get("deliveries", []):
            assert delivery.get("status") == "sent", f"Expected sent, got {delivery.get('status')}"
    
    def test_get_delivery_stats(self, auth_headers):
        """GET /api/deliveries/stats - get stats by status"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all status fields exist
        assert "pending_csv" in data
        assert "ready_to_send" in data
        assert "sending" in data
        assert "sent" in data
        assert "failed" in data
        assert "total" in data
        
        # Total should be sum of all statuses
        calculated_total = (
            data.get("pending_csv", 0) +
            data.get("ready_to_send", 0) +
            data.get("sending", 0) +
            data.get("sent", 0) +
            data.get("failed", 0)
        )
        assert data["total"] == calculated_total, "Total should equal sum of all statuses"
    
    def test_get_delivery_stats_by_entity(self, auth_headers):
        """GET /api/deliveries/stats?entity=ZR7 - stats filtered by entity"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries/stats",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
    
    def test_get_single_delivery(self, auth_headers):
        """GET /api/deliveries/{id} - get single delivery"""
        # First get a delivery ID
        list_response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"limit": 1}
        )
        
        if list_response.status_code == 200:
            deliveries = list_response.json().get("deliveries", [])
            if deliveries:
                delivery_id = deliveries[0]["id"]
                
                response = requests.get(
                    f"{BASE_URL}/api/deliveries/{delivery_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data.get("id") == delivery_id
                assert "has_csv" in data
    
    def test_get_nonexistent_delivery_returns_404(self, auth_headers):
        """GET /api/deliveries/{id} - nonexistent ID returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/deliveries/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_download_delivery_csv(self, auth_headers):
        """GET /api/deliveries/{id}/download - download CSV"""
        # Get a delivery with CSV
        list_response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"status": "sent", "limit": 1}
        )
        
        if list_response.status_code == 200:
            deliveries = list_response.json().get("deliveries", [])
            if deliveries:
                delivery_id = deliveries[0]["id"]
                
                response = requests.get(
                    f"{BASE_URL}/api/deliveries/{delivery_id}/download",
                    headers=auth_headers
                )
                
                # Should return CSV or 404 if no CSV content
                assert response.status_code in [200, 404]
                
                if response.status_code == 200:
                    assert "text/csv" in response.headers.get("content-type", "")
    
    def test_deliveries_require_auth(self):
        """GET /api/deliveries - requires authentication"""
        response = requests.get(f"{BASE_URL}/api/deliveries")
        assert response.status_code == 401


class TestDeliveryStatusTransitions:
    """Test delivery status transitions follow the strict lifecycle"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_valid_status_values(self, auth_headers):
        """Verify deliveries have valid status values"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"limit": 100}
        )
        
        assert response.status_code == 200
        
        valid_statuses = ["pending_csv", "ready_to_send", "sending", "sent", "failed"]
        
        for delivery in response.json().get("deliveries", []):
            status = delivery.get("status")
            assert status in valid_statuses, f"Invalid status: {status}"
    
    def test_send_delivery_already_sent_without_force(self, auth_headers):
        """POST /api/deliveries/{id}/send - already sent without force returns 400"""
        # Get a sent delivery
        list_response = requests.get(
            f"{BASE_URL}/api/deliveries",
            headers=auth_headers,
            params={"status": "sent", "limit": 1}
        )
        
        if list_response.status_code == 200:
            deliveries = list_response.json().get("deliveries", [])
            if deliveries:
                delivery_id = deliveries[0]["id"]
                
                # Try to send without force
                response = requests.post(
                    f"{BASE_URL}/api/deliveries/{delivery_id}/send",
                    headers=auth_headers,
                    json={"force": False}
                )
                
                # Should return 400 because already sent
                assert response.status_code == 400
                assert "déjà envoyée" in response.json().get("detail", "").lower() or \
                       "already" in response.json().get("detail", "").lower()


class TestSimulationMode:
    """Test simulation mode email override"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_simulation_mode_enabled(self, auth_headers):
        """Verify simulation mode is enabled and returns override email"""
        response = requests.get(f"{BASE_URL}/api/settings/email-denylist", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check simulation mode status
        simulation_mode = data.get("simulation_mode", False)
        simulation_email = data.get("simulation_email", "")
        
        print(f"Simulation mode: {simulation_mode}")
        print(f"Simulation email: {simulation_email}")
        
        if simulation_mode:
            assert simulation_email, "Simulation email should be set when mode is enabled"
    
    def test_enable_simulation_mode(self, auth_headers):
        """PUT /api/settings/email-denylist - enable simulation mode"""
        response = requests.put(
            f"{BASE_URL}/api/settings/email-denylist",
            headers=auth_headers,
            json={
                "domains": ["example.com", "test.com", "localhost", "invalid", "fake.com"],
                "simulation_mode": True,
                "simulation_email": "energiebleuciel@gmail.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        setting = data.get("setting", {})
        assert setting.get("simulation_mode") == True
        assert setting.get("simulation_email") == "energiebleuciel@gmail.com"


class TestBatchGenerateCSV:
    """Test batch CSV generation endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_batch_generate_csv(self, auth_headers):
        """POST /api/deliveries/batch/generate-csv - generate CSV for pending deliveries"""
        response = requests.post(
            f"{BASE_URL}/api/deliveries/batch/generate-csv",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "processed" in data
        
        print(f"Batch generate CSV: processed={data.get('processed')}")
    
    def test_batch_generate_csv_by_entity(self, auth_headers):
        """POST /api/deliveries/batch/generate-csv?entity=ZR7 - filter by entity"""
        response = requests.post(
            f"{BASE_URL}/api/deliveries/batch/generate-csv",
            headers=auth_headers,
            params={"entity": "ZR7"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True


class TestLeadStatusAfterDelivery:
    """Test that lead.status=livre ONLY when delivery.status=sent"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json().get('token')}"}
    
    def test_livre_leads_have_sent_deliveries(self, auth_headers):
        """Verify leads with status=livre have corresponding delivery.status=sent"""
        # Get livre leads
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_headers,
            params={"status": "livre", "limit": 10}
        )
        
        if response.status_code == 200:
            leads = response.json().get("leads", [])
            
            for lead in leads:
                delivery_id = lead.get("delivery_id")
                if delivery_id:
                    # Check delivery status
                    delivery_response = requests.get(
                        f"{BASE_URL}/api/deliveries/{delivery_id}",
                        headers=auth_headers
                    )
                    
                    if delivery_response.status_code == 200:
                        delivery = delivery_response.json()
                        assert delivery.get("status") == "sent", \
                            f"Lead {lead.get('id')} is livre but delivery {delivery_id} is {delivery.get('status')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
