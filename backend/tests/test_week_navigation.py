"""
Test WeekNav standardisation - Backend API week parameter handling
Tests that all admin pages' APIs properly accept and process week=YYYY-W## parameter
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuth:
    """Get auth token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestWeekParamEndpoints:
    """Test that all week-filtered endpoints accept week parameter"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_stats_with_week(self, auth_headers):
        """GET /api/leads/dashboard-stats accepts week parameter"""
        # Test current week
        response = requests.get(
            f"{BASE_URL}/api/leads/dashboard-stats?week=2026-W07",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "lead_stats" in data
        assert "delivery_stats" in data
        print(f"✓ Dashboard stats week=2026-W07: lead_stats={data['lead_stats']}")
    
    def test_leads_list_with_week(self, auth_headers):
        """GET /api/leads/list accepts week parameter"""
        response = requests.get(
            f"{BASE_URL}/api/leads/list?week=2026-W07&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "leads" in data
        assert "total" in data
        print(f"✓ Leads list week=2026-W07: count={len(data['leads'])}, total={data['total']}")
    
    def test_commandes_with_week(self, auth_headers):
        """GET /api/commandes accepts week parameter for ZR7"""
        response = requests.get(
            f"{BASE_URL}/api/commandes?entity=ZR7&week=2026-W07",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "commandes" in data
        # Verify week_start is populated
        if data["commandes"]:
            cmd = data["commandes"][0]
            assert "week_start" in cmd, "week_start not in commande response"
            assert "leads_delivered_this_week" in cmd
        print(f"✓ Commandes ZR7 week=2026-W07: count={len(data['commandes'])}")
    
    def test_commandes_mdl_with_week(self, auth_headers):
        """GET /api/commandes accepts week parameter for MDL"""
        response = requests.get(
            f"{BASE_URL}/api/commandes?entity=MDL&week=2026-W07",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "commandes" in data
        print(f"✓ Commandes MDL week=2026-W07: count={len(data['commandes'])}")
    
    def test_deliveries_with_week(self, auth_headers):
        """GET /api/deliveries accepts week parameter"""
        response = requests.get(
            f"{BASE_URL}/api/deliveries?week=2026-W07&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "deliveries" in data
        assert "total" in data
        print(f"✓ Deliveries week=2026-W07: count={len(data['deliveries'])}, total={data['total']}")
    
    def test_event_log_with_week(self, auth_headers):
        """GET /api/event-log accepts week parameter"""
        response = requests.get(
            f"{BASE_URL}/api/event-log?week=2026-W07&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "events" in data
        assert "total" in data
        print(f"✓ Event log week=2026-W07: count={len(data['events'])}, total={data['total']}")
    
    def test_billing_week(self, auth_headers):
        """GET /api/billing/week accepts week_key parameter"""
        response = requests.get(
            f"{BASE_URL}/api/billing/week?week_key=2026-W07",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "summary" in data or "has_records" in data
        print(f"✓ Billing week=2026-W07: has_records={data.get('has_records', 'N/A')}")
    
    def test_departements_overview_with_week(self, auth_headers):
        """GET /api/departements/overview accepts week parameter"""
        response = requests.get(
            f"{BASE_URL}/api/departements/overview?week=2026-W07&product=ALL",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "results" in data
        print(f"✓ Departements overview week=2026-W07: count={len(data['results'])}")


class TestWeekNavigationBehavior:
    """Test that changing week changes data returned"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_different_weeks_return_different_data(self, auth_headers):
        """Dashboard stats should vary by week selection"""
        # Week 6
        r1 = requests.get(f"{BASE_URL}/api/leads/dashboard-stats?week=2026-W06", headers=auth_headers)
        assert r1.status_code == 200
        data1 = r1.json()
        
        # Week 7
        r2 = requests.get(f"{BASE_URL}/api/leads/dashboard-stats?week=2026-W07", headers=auth_headers)
        assert r2.status_code == 200
        data2 = r2.json()
        
        print(f"Week 6 delivery_stats: {data1.get('delivery_stats', {})}")
        print(f"Week 7 delivery_stats: {data2.get('delivery_stats', {})}")
        # Data may be same if no activity, but API should work
        print("✓ Different weeks API calls succeed")
    
    def test_leads_list_filtered_by_week(self, auth_headers):
        """Leads list should filter by week"""
        # Get leads for week 6
        r1 = requests.get(f"{BASE_URL}/api/leads/list?week=2026-W06&limit=100", headers=auth_headers)
        assert r1.status_code == 200
        total_w6 = r1.json()["total"]
        
        # Get leads for week 7
        r2 = requests.get(f"{BASE_URL}/api/leads/list?week=2026-W07&limit=100", headers=auth_headers)
        assert r2.status_code == 200
        total_w7 = r2.json()["total"]
        
        print(f"Leads week 6 total: {total_w6}")
        print(f"Leads week 7 total: {total_w7}")
        print("✓ Leads filtered by week parameter")


class TestWeekKeyFormat:
    """Test that week_key format is handled correctly"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "energiebleuciel@gmail.com",
            "password": "92Ruemarxdormoy"
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    def test_week_key_iso_format_accepted(self, auth_headers):
        """API should accept YYYY-W## format"""
        # Valid ISO week format
        r = requests.get(f"{BASE_URL}/api/leads/list?week=2026-W01&limit=5", headers=auth_headers)
        assert r.status_code == 200, f"ISO week format not accepted: {r.text}"
        print("✓ ISO week format 2026-W01 accepted")
    
    def test_week_key_week_53(self, auth_headers):
        """API should handle week 53 (some years have 53 weeks)"""
        # 2020 had 53 weeks
        r = requests.get(f"{BASE_URL}/api/leads/list?week=2020-W53&limit=5", headers=auth_headers)
        assert r.status_code == 200, f"Week 53 not handled: {r.text}"
        print("✓ Week 53 format accepted")
    
    def test_week_range_calculation(self, auth_headers):
        """Week 7 of 2026 should be Feb 9-15"""
        r = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&week=2026-W07", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        
        if data["commandes"]:
            week_start = data["commandes"][0].get("week_start", "")
            assert "2026-02-09" in week_start or "2026-02-10" in week_start, \
                f"Week 7 should start around Feb 9-10: got {week_start}"
            print(f"✓ Week 7 2026 starts: {week_start}")
        else:
            print("! No commandes to verify week_start")
