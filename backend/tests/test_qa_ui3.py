"""
QA UI3 - Full Regression Test Suite
Testing: Navigation, Deliveries, Leads, Clients, Commandes, Activity, Settings
Counter Coherence: billable = sent - rejected - removed
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        print(f"Auth token obtained: {auth_token[:20]}...")


class TestDeliveryStats:
    """Delivery stats and counter coherence tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_delivery_stats_endpoint(self, headers):
        """Test GET /api/deliveries/stats returns correct fields"""
        response = requests.get(f"{BASE_URL}/api/deliveries/stats", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"Delivery Stats: {data}")
        
        # Check required fields
        required_fields = ["sent", "billable", "rejected", "removed", "pending_csv", "ready_to_send", "failed"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_counter_coherence(self, headers):
        """CRITICAL: Verify billable = sent - rejected - removed"""
        response = requests.get(f"{BASE_URL}/api/deliveries/stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        sent = data.get("sent", 0)
        rejected = data.get("rejected", 0)
        removed = data.get("removed", 0)
        billable = data.get("billable", 0)
        
        expected_billable = sent - rejected - removed
        
        print(f"Counter Coherence Check:")
        print(f"  sent={sent}, rejected={rejected}, removed={removed}")
        print(f"  billable={billable}, expected={expected_billable}")
        
        assert billable == expected_billable, \
            f"Counter mismatch! billable={billable} != sent({sent}) - rejected({rejected}) - removed({removed}) = {expected_billable}"
    
    def test_delivery_list(self, headers):
        """Test GET /api/deliveries returns list"""
        response = requests.get(f"{BASE_URL}/api/deliveries?limit=10", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "deliveries" in data
        assert "total" in data
        print(f"Total deliveries: {data['total']}, showing {len(data['deliveries'])}")


class TestEventLog:
    """Event log tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_event_log_list(self, headers):
        """Test GET /api/event-log returns events"""
        response = requests.get(f"{BASE_URL}/api/event-log?limit=50", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "total" in data
        print(f"Total events: {data['total']}")
        
        # Print recent events
        for e in data.get("events", [])[:5]:
            print(f"  - {e.get('action')}: {e.get('entity_type')} by {e.get('user')}")
    
    def test_event_log_actions(self, headers):
        """Test GET /api/event-log/actions returns action types"""
        response = requests.get(f"{BASE_URL}/api/event-log/actions", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "actions" in data
        print(f"Available actions: {data['actions']}")
    
    def test_event_log_filters(self, headers):
        """Test event log filters"""
        # Filter by entity_type
        response = requests.get(f"{BASE_URL}/api/event-log?entity_type=delivery", headers=headers)
        assert response.status_code == 200
        
        # Filter by entity
        response = requests.get(f"{BASE_URL}/api/event-log?entity=ZR7", headers=headers)
        assert response.status_code == 200
        print("Event log filters working")


class TestCommandes:
    """Commandes CRUD and detail tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_commandes_list_zr7(self, headers):
        """Test GET /api/commandes?entity=ZR7"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "commandes" in data
        print(f"ZR7 commandes: {data['count']}")
        
        # Each commande should have client_name
        for cmd in data.get("commandes", [])[:3]:
            assert "client_name" in cmd
            print(f"  - {cmd.get('client_name')} | {cmd.get('produit')} | active={cmd.get('active')}")
    
    def test_commandes_list_mdl(self, headers):
        """Test GET /api/commandes?entity=MDL"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=MDL", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"MDL commandes: {data['count']}")
    
    def test_commande_stats(self, headers):
        """Test GET /api/commandes/{id}/stats"""
        # First get a commande ID
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&active_only=false", headers=headers)
        assert response.status_code == 200
        
        commandes = response.json().get("commandes", [])
        if not commandes:
            pytest.skip("No commandes found")
        
        cmd_id = commandes[0].get("id")
        
        # Get stats
        stats_response = requests.get(f"{BASE_URL}/api/commandes/{cmd_id}/stats", headers=headers)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert "current_week" in stats
        assert "total_delivered" in stats
        print(f"Commande stats: current_week={stats.get('current_week')}, total={stats.get('total_delivered')}")
    
    def test_commande_deliveries(self, headers):
        """Test GET /api/commandes/{id}/deliveries"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&active_only=false", headers=headers)
        assert response.status_code == 200
        
        commandes = response.json().get("commandes", [])
        if not commandes:
            pytest.skip("No commandes found")
        
        cmd_id = commandes[0].get("id")
        
        # Get deliveries
        del_response = requests.get(f"{BASE_URL}/api/commandes/{cmd_id}/deliveries?limit=10", headers=headers)
        assert del_response.status_code == 200
        
        data = del_response.json()
        assert "deliveries" in data
        assert "total" in data
        print(f"Commande deliveries: {data['total']}")
    
    def test_commande_toggle(self, headers):
        """Test POST /api/commandes/{id}/toggle logs event"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&active_only=false", headers=headers)
        commandes = response.json().get("commandes", [])
        if not commandes:
            pytest.skip("No commandes found")
        
        cmd_id = commandes[0].get("id")
        original_active = commandes[0].get("active", True)
        
        # Toggle
        toggle_response = requests.post(f"{BASE_URL}/api/commandes/{cmd_id}/toggle", headers=headers)
        assert toggle_response.status_code == 200
        
        result = toggle_response.json()
        assert "active" in result
        assert result["active"] != original_active
        print(f"Toggle result: active={result['active']}")
        
        # Toggle back
        requests.post(f"{BASE_URL}/api/commandes/{cmd_id}/toggle", headers=headers)


class TestClients:
    """Clients tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_clients_list(self, headers):
        """Test GET /api/clients?entity=ZR7"""
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "clients" in data
        print(f"ZR7 clients: {len(data['clients'])}")
        
        for c in data.get("clients", [])[:3]:
            print(f"  - {c.get('name')} | phone={c.get('phone')} | auto_send={c.get('auto_send_enabled')}")
    
    def test_client_detail_360(self, headers):
        """Test client 360 view endpoints"""
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=headers)
        clients = response.json().get("clients", [])
        if not clients:
            pytest.skip("No clients found")
        
        client_id = clients[0].get("id")
        
        # Get detail
        detail_response = requests.get(f"{BASE_URL}/api/clients/{client_id}", headers=headers)
        assert detail_response.status_code == 200
        
        # Get summary
        summary_response = requests.get(f"{BASE_URL}/api/clients/{client_id}/summary?group_by=day", headers=headers)
        assert summary_response.status_code == 200
        print(f"Client summary: {summary_response.json().get('totals', {})}")
        
        # Get activity
        activity_response = requests.get(f"{BASE_URL}/api/clients/{client_id}/activity", headers=headers)
        assert activity_response.status_code == 200


class TestLeads:
    """Leads tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_leads_list(self, headers):
        """Test GET /api/leads/list"""
        response = requests.get(f"{BASE_URL}/api/leads/list?limit=10", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "leads" in data
        assert "total" in data
        print(f"Total leads: {data['total']}")
    
    def test_leads_stats(self, headers):
        """Test GET /api/leads/stats"""
        response = requests.get(f"{BASE_URL}/api/leads/stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"Lead stats: {data}")
    
    def test_leads_dashboard_stats(self, headers):
        """Test GET /api/leads/dashboard-stats"""
        response = requests.get(f"{BASE_URL}/api/leads/dashboard-stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "delivery_stats" in data
        assert "lead_stats" in data
        print(f"Dashboard stats: delivery={data.get('delivery_stats')}")


class TestDeliveryActions:
    """Test delivery actions: reject, remove, idempotence"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_find_sent_delivery(self, headers):
        """Find a sent delivery for testing"""
        response = requests.get(f"{BASE_URL}/api/deliveries?status=sent&limit=50", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        deliveries = data.get("deliveries", [])
        
        # Find one with outcome=accepted (not rejected/removed)
        for d in deliveries:
            if d.get("outcome") not in ["rejected", "removed"]:
                print(f"Found available delivery: {d.get('id')[:8]}... status={d.get('status')} outcome={d.get('outcome')}")
                return d
        
        print("No available delivery for action tests (all are rejected/removed)")
        return None
    
    def test_reject_idempotence(self, headers):
        """Test rejecting an already rejected delivery returns already_rejected"""
        # Find a rejected delivery
        response = requests.get(f"{BASE_URL}/api/deliveries?status=sent&limit=100", headers=headers)
        deliveries = response.json().get("deliveries", [])
        
        rejected = [d for d in deliveries if d.get("outcome") == "rejected"]
        if not rejected:
            pytest.skip("No rejected deliveries to test idempotence")
        
        delivery_id = rejected[0].get("id")
        
        # Try to reject again
        reject_response = requests.post(
            f"{BASE_URL}/api/deliveries/{delivery_id}/reject-leads",
            json={"reason": "test idempotence"},
            headers=headers
        )
        assert reject_response.status_code == 200
        
        result = reject_response.json()
        assert result.get("already_rejected") == True, "Should return already_rejected=True"
        print(f"Idempotence test passed: already_rejected=True")
    
    def test_remove_idempotence(self, headers):
        """Test removing an already removed delivery returns already_removed"""
        response = requests.get(f"{BASE_URL}/api/deliveries?status=sent&limit=100", headers=headers)
        deliveries = response.json().get("deliveries", [])
        
        removed = [d for d in deliveries if d.get("outcome") == "removed"]
        if not removed:
            pytest.skip("No removed deliveries to test idempotence")
        
        delivery_id = removed[0].get("id")
        
        # Try to remove again
        remove_response = requests.post(
            f"{BASE_URL}/api/deliveries/{delivery_id}/remove-lead",
            json={"reason": "test", "reason_detail": "idempotence test"},
            headers=headers
        )
        assert remove_response.status_code == 200
        
        result = remove_response.json()
        assert result.get("already_removed") == True
        print(f"Idempotence test passed: already_removed=True")


class TestSettings:
    """Settings API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_delivery_calendar(self, headers):
        """Test GET /api/settings/delivery-calendar"""
        response = requests.get(f"{BASE_URL}/api/settings/delivery-calendar", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "ZR7" in data
        assert "MDL" in data
        print(f"Calendar: ZR7={data.get('ZR7')}, MDL={data.get('MDL')}")
    
    def test_delivery_calendar_check(self, headers):
        """Test GET /api/settings/delivery-calendar/check/{entity}"""
        for entity in ["ZR7", "MDL"]:
            response = requests.get(f"{BASE_URL}/api/settings/delivery-calendar/check/{entity}", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            print(f"{entity} calendar check: is_delivery_day={data.get('is_delivery_day')}, reason={data.get('reason')}")
    
    def test_email_denylist(self, headers):
        """Test GET /api/settings/email-denylist"""
        response = requests.get(f"{BASE_URL}/api/settings/email-denylist", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"Denylist: simulation_mode={data.get('simulation_mode')}, domains={len(data.get('domains', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
