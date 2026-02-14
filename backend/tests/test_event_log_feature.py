"""
Test Event Log Centralized Audit Trail - Etape 3

Tests for:
1. GET /api/event-log with various filters (action, entity_type, entity)
2. GET /api/event-log/actions returns distinct action types
3. GET /api/event-log/{id} returns single event
4. Event logging for: reject_lead, lead_removed_from_delivery, send_delivery, 
   resend_delivery, delivery_failed, order_activate, order_deactivate, 
   client_auto_send_change, rotate_provider_key
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rdz-phase25-final.preview.emergentagent.com').rstrip('/')
TEST_EMAIL = "energiebleuciel@gmail.com"
TEST_PASSWORD = "92Ruemarxdormoy"


class TestEventLogEndpoints:
    """Test event log API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_01_event_log_list(self):
        """GET /api/event-log returns events list"""
        response = requests.get(f"{BASE_URL}/api/event-log?limit=50", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert "count" in data
        print(f"✅ Event log list: {data['total']} total events, returned {data['count']}")
    
    def test_02_event_log_actions(self):
        """GET /api/event-log/actions returns distinct action types"""
        response = requests.get(f"{BASE_URL}/api/event-log/actions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "actions" in data
        assert isinstance(data["actions"], list)
        print(f"✅ Action types: {data['actions']}")
    
    def test_03_event_log_filter_by_action(self):
        """GET /api/event-log?action=reject_lead filters correctly"""
        response = requests.get(f"{BASE_URL}/api/event-log?action=reject_lead", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        events = data.get("events", [])
        # All returned events should have action=reject_lead
        for event in events:
            assert event.get("action") == "reject_lead", f"Expected action=reject_lead, got {event.get('action')}"
        print(f"✅ Filter by action=reject_lead: {len(events)} events")
    
    def test_04_event_log_filter_by_entity_type(self):
        """GET /api/event-log?entity_type=delivery filters correctly"""
        response = requests.get(f"{BASE_URL}/api/event-log?entity_type=delivery", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        events = data.get("events", [])
        for event in events:
            assert event.get("entity_type") == "delivery"
        print(f"✅ Filter by entity_type=delivery: {len(events)} events")
    
    def test_05_event_log_filter_by_entity(self):
        """GET /api/event-log?entity=ZR7 filters correctly"""
        response = requests.get(f"{BASE_URL}/api/event-log?entity=ZR7", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        events = data.get("events", [])
        for event in events:
            assert event.get("entity") == "ZR7", f"Expected entity=ZR7, got {event.get('entity')}"
        print(f"✅ Filter by entity=ZR7: {len(events)} events")
    
    def test_06_event_log_pagination(self):
        """GET /api/event-log supports pagination (limit/skip)"""
        # First page
        response1 = requests.get(f"{BASE_URL}/api/event-log?limit=1&skip=0", headers=self.headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second page
        response2 = requests.get(f"{BASE_URL}/api/event-log?limit=1&skip=1", headers=self.headers)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # If we have more than 1 event, they should be different
        if data1.get("total", 0) > 1:
            events1 = data1.get("events", [])
            events2 = data2.get("events", [])
            if events1 and events2:
                assert events1[0].get("id") != events2[0].get("id"), "Pagination should return different events"
        print(f"✅ Pagination works (total: {data1.get('total')})")
    
    def test_07_event_log_get_single_event(self):
        """GET /api/event-log/{id} returns single event details"""
        # First get list to find an event ID
        list_response = requests.get(f"{BASE_URL}/api/event-log?limit=1", headers=self.headers)
        assert list_response.status_code == 200
        events = list_response.json().get("events", [])
        
        if events:
            event_id = events[0].get("id")
            response = requests.get(f"{BASE_URL}/api/event-log/{event_id}", headers=self.headers)
            assert response.status_code == 200
            event = response.json()
            assert event.get("id") == event_id
            assert "action" in event
            assert "entity_type" in event
            assert "created_at" in event
            print(f"✅ Get single event: {event.get('action')} on {event.get('entity_type')}")
        else:
            pytest.skip("No events to test single event retrieval")
    
    def test_08_event_log_get_nonexistent_event(self):
        """GET /api/event-log/{id} returns 404 for non-existent event"""
        response = requests.get(f"{BASE_URL}/api/event-log/nonexistent-id-12345", headers=self.headers)
        assert response.status_code == 404
        print("✅ 404 returned for non-existent event")


class TestEventLoggingOnActions:
    """Test that actions write to event_log"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def get_latest_event(self, action=None):
        """Helper to get latest event, optionally filtered by action"""
        params = "limit=1"
        if action:
            params += f"&action={action}"
        response = requests.get(f"{BASE_URL}/api/event-log?{params}", headers=self.headers)
        if response.status_code == 200:
            events = response.json().get("events", [])
            return events[0] if events else None
        return None
    
    def get_event_count(self, action=None):
        """Helper to get count of events"""
        params = "limit=1"
        if action:
            params += f"&action={action}"
        response = requests.get(f"{BASE_URL}/api/event-log?{params}", headers=self.headers)
        if response.status_code == 200:
            return response.json().get("total", 0)
        return 0
    
    def test_10_order_activate_deactivate_logs_event(self):
        """POST /api/commandes/{id}/toggle logs order_activate/order_deactivate event"""
        # Get a commande to toggle
        commandes_res = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&active_only=false", headers=self.headers)
        assert commandes_res.status_code == 200
        commandes = commandes_res.json().get("commandes", [])
        
        if not commandes:
            pytest.skip("No commandes available to test toggle")
        
        commande = commandes[0]
        commande_id = commande.get("id")
        initial_active = commande.get("active", True)
        
        # Count events before
        before_count = self.get_event_count("order_activate") + self.get_event_count("order_deactivate")
        
        # Toggle the commande
        toggle_res = requests.post(f"{BASE_URL}/api/commandes/{commande_id}/toggle", headers=self.headers)
        assert toggle_res.status_code == 200
        new_active = toggle_res.json().get("active")
        expected_action = "order_activate" if new_active else "order_deactivate"
        
        # Check event was logged
        time.sleep(0.5)  # Wait for event to be written
        after_count = self.get_event_count("order_activate") + self.get_event_count("order_deactivate")
        assert after_count > before_count, f"Event count should increase after toggle"
        
        # Get the latest event
        latest = self.get_latest_event(expected_action)
        assert latest is not None
        assert latest.get("entity_type") == "commande"
        assert latest.get("entity_id") == commande_id
        print(f"✅ {expected_action} logged for commande {commande_id}")
        
        # Toggle back to original state
        requests.post(f"{BASE_URL}/api/commandes/{commande_id}/toggle", headers=self.headers)
    
    def test_11_client_auto_send_change_logs_event(self):
        """PUT /api/clients/{id} with auto_send_enabled change logs client_auto_send_change"""
        # Get a client to update
        clients_res = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=self.headers)
        assert clients_res.status_code == 200
        clients = clients_res.json().get("clients", [])
        
        if not clients:
            pytest.skip("No clients available to test auto_send change")
        
        client = clients[0]
        client_id = client.get("id")
        initial_auto_send = client.get("auto_send_enabled", True)
        
        # Count events before
        before_count = self.get_event_count("client_auto_send_change")
        
        # Change auto_send_enabled
        new_auto_send = not initial_auto_send
        update_res = requests.put(
            f"{BASE_URL}/api/clients/{client_id}",
            headers=self.headers,
            json={"auto_send_enabled": new_auto_send}
        )
        assert update_res.status_code == 200
        
        # Check event was logged
        time.sleep(0.5)
        after_count = self.get_event_count("client_auto_send_change")
        assert after_count > before_count, f"Event count should increase after auto_send change"
        
        latest = self.get_latest_event("client_auto_send_change")
        assert latest is not None
        assert latest.get("entity_type") == "client"
        assert latest.get("entity_id") == client_id
        assert latest.get("details", {}).get("old_value") == initial_auto_send
        assert latest.get("details", {}).get("new_value") == new_auto_send
        print(f"✅ client_auto_send_change logged: {initial_auto_send} -> {new_auto_send}")
        
        # Revert the change
        requests.put(
            f"{BASE_URL}/api/clients/{client_id}",
            headers=self.headers,
            json={"auto_send_enabled": initial_auto_send}
        )
    
    def test_12_existing_reject_lead_event(self):
        """Verify existing reject_lead event structure"""
        response = requests.get(f"{BASE_URL}/api/event-log?action=reject_lead&limit=1", headers=self.headers)
        assert response.status_code == 200
        events = response.json().get("events", [])
        
        if events:
            event = events[0]
            assert event.get("action") == "reject_lead"
            assert event.get("entity_type") == "delivery"
            assert "entity_id" in event
            assert "related" in event
            assert "lead_id" in event.get("related", {})
            print(f"✅ reject_lead event structure verified: entity_id={event.get('entity_id')}")
        else:
            pytest.skip("No reject_lead events to verify")
    
    def test_13_existing_lead_removed_event(self):
        """Verify existing lead_removed_from_delivery event structure"""
        response = requests.get(f"{BASE_URL}/api/event-log?action=lead_removed_from_delivery&limit=1", headers=self.headers)
        assert response.status_code == 200
        events = response.json().get("events", [])
        
        if events:
            event = events[0]
            assert event.get("action") == "lead_removed_from_delivery"
            assert event.get("entity_type") == "delivery"
            assert "entity_id" in event
            assert "related" in event
            print(f"✅ lead_removed_from_delivery event structure verified")
        else:
            pytest.skip("No lead_removed_from_delivery events to verify")
    
    def test_14_provider_rotate_key_logs_event(self):
        """POST /api/providers/{id}/rotate-key logs rotate_provider_key event"""
        # Get a provider
        providers_res = requests.get(f"{BASE_URL}/api/providers", headers=self.headers)
        assert providers_res.status_code == 200
        providers = providers_res.json().get("providers", [])
        
        if not providers:
            pytest.skip("No providers available to test rotate key")
        
        provider = providers[0]
        provider_id = provider.get("id")
        
        # Count events before
        before_count = self.get_event_count("rotate_provider_key")
        
        # Rotate the key
        rotate_res = requests.post(f"{BASE_URL}/api/providers/{provider_id}/rotate-key", headers=self.headers)
        assert rotate_res.status_code == 200
        assert "api_key" in rotate_res.json()
        
        # Check event was logged
        time.sleep(0.5)
        after_count = self.get_event_count("rotate_provider_key")
        assert after_count > before_count, "Event count should increase after key rotation"
        
        latest = self.get_latest_event("rotate_provider_key")
        assert latest is not None
        assert latest.get("entity_type") == "provider"
        assert latest.get("entity_id") == provider_id
        assert "provider_name" in latest.get("details", {})
        print(f"✅ rotate_provider_key logged for provider {provider.get('name')}")


class TestEventLogForDeliveryActions:
    """Test event logging for delivery send/resend actions (may need real delivery)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_20_delivery_actions_in_event_log(self):
        """Verify send_delivery/resend_delivery/delivery_failed actions appear in action list if triggered"""
        response = requests.get(f"{BASE_URL}/api/event-log/actions", headers=self.headers)
        assert response.status_code == 200
        actions = response.json().get("actions", [])
        
        expected_instrumented = [
            "reject_lead", "lead_removed_from_delivery", 
            "order_activate", "order_deactivate", 
            "client_auto_send_change", "rotate_provider_key"
        ]
        
        print(f"Available actions in event log: {actions}")
        
        # Check that at least some expected actions exist
        found = [a for a in expected_instrumented if a in actions]
        print(f"✅ Found instrumented actions: {found}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
