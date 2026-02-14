"""
Test suite for Departements feature (Pilotage industriel)

Tests:
- GET /api/departements/overview - Overview with filters
- GET /api/departements/{dept}/detail - Department detail with timeseries
- GET /api/clients/{id}/coverage - Client coverage by department
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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
        data = response.json()
        return data.get("token")
    pytest.fail(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(auth_token):
    """Requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(scope="module")
def test_client_id(authenticated_client):
    """Get a client ID for coverage tests"""
    # Get ZR7 clients
    response = authenticated_client.get(f"{BASE_URL}/api/clients?entity=ZR7&active_only=false")
    if response.status_code == 200:
        data = response.json()
        clients = data.get("clients", [])
        if clients:
            return clients[0]["id"]
    
    # Try MDL if no ZR7 clients
    response = authenticated_client.get(f"{BASE_URL}/api/clients?entity=MDL&active_only=false")
    if response.status_code == 200:
        data = response.json()
        clients = data.get("clients", [])
        if clients:
            return clients[0]["id"]
    
    pytest.skip("No clients found for coverage testing")


class TestDepartementsOverview:
    """Tests for GET /api/departements/overview"""

    def test_overview_returns_200(self, authenticated_client):
        """Overview endpoint returns 200 OK"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Overview returned 200 OK")

    def test_overview_response_structure(self, authenticated_client):
        """Overview returns correct response structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "results" in data, "Missing 'results' field"
        assert "count" in data, "Missing 'count' field"
        assert "week" in data, "Missing 'week' field"
        assert "period" in data, "Missing 'period' field"
        assert "product" in data, "Missing 'product' field"
        
        print(f"Overview returned {data['count']} results for week {data['week']}")

    def test_overview_result_fields(self, authenticated_client):
        """Overview results have correct fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        if results:
            result = results[0]
            required_fields = [
                "departement", "produit", "produced_current", "billable_current",
                "status", "clients_covering"
            ]
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Validate status is one of expected values
            valid_statuses = ["no_order", "on_remaining", "saturated", "inactive_blocked"]
            assert result["status"] in valid_statuses, f"Invalid status: {result['status']}"
            
            print(f"First result: {result['departement']} - {result['produit']} - status={result['status']}")
        else:
            print("No results returned - may be empty data")

    def test_overview_product_filter_all(self, authenticated_client):
        """Product filter ALL returns all products"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?product=ALL")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"] == "ALL"
        print(f"ALL products: {data['count']} results")

    def test_overview_product_filter_pv(self, authenticated_client):
        """Product filter PV filters results"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?product=PV")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        # All results should have produit = PV
        for r in results:
            assert r["produit"] == "PV", f"Expected PV, got {r['produit']}"
        
        print(f"PV filter: {data['count']} results")

    def test_overview_product_filter_pac(self, authenticated_client):
        """Product filter PAC filters results"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?product=PAC")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        for r in results:
            assert r["produit"] == "PAC", f"Expected PAC, got {r['produit']}"
        
        print(f"PAC filter: {data['count']} results")

    def test_overview_product_filter_ite(self, authenticated_client):
        """Product filter ITE filters results"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?product=ITE")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        for r in results:
            assert r["produit"] == "ITE", f"Expected ITE, got {r['produit']}"
        
        print(f"ITE filter: {data['count']} results")

    def test_overview_week_parameter(self, authenticated_client):
        """Week parameter is respected"""
        # Test with specific week format YYYY-W##
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?week=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert data["week"] == "2026-W07", f"Expected 2026-W07, got {data['week']}"
        print(f"Week parameter test: returned week={data['week']}")

    def test_overview_period_day(self, authenticated_client):
        """Period=day changes aggregation period"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview?period=day")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period"] == "day", f"Expected period=day, got {data['period']}"
        print(f"Period=day: {data['count']} results")

    def test_overview_clients_covering_structure(self, authenticated_client):
        """clients_covering has correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        for r in results:
            if r["clients_covering"]:
                client = r["clients_covering"][0]
                expected_fields = ["client_id", "name", "commande_id", "quota_week", "billable_week", "remaining_week"]
                for field in expected_fields:
                    assert field in client, f"Missing field in clients_covering: {field}"
                print(f"Dept {r['departement']} has {len(r['clients_covering'])} covering clients")
                break


class TestDeptDetail:
    """Tests for GET /api/departements/{dept}/detail"""

    def test_detail_returns_200(self, authenticated_client):
        """Detail endpoint returns 200 OK"""
        # First get a valid dept from overview
        overview = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        results = overview.json().get("results", [])
        
        if not results:
            pytest.skip("No departments in overview")
        
        dept = results[0]["departement"]
        response = authenticated_client.get(f"{BASE_URL}/api/departements/{dept}/detail")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Detail for dept {dept} returned 200 OK")

    def test_detail_response_structure(self, authenticated_client):
        """Detail returns correct response structure"""
        overview = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        results = overview.json().get("results", [])
        
        if not results:
            pytest.skip("No departments in overview")
        
        dept = results[0]["departement"]
        response = authenticated_client.get(f"{BASE_URL}/api/departements/{dept}/detail")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        required_fields = ["departement", "product", "week", "kpi", "timeseries", "clients_covering"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"Detail structure OK: dept={data['departement']}, week={data['week']}")

    def test_detail_kpi_structure(self, authenticated_client):
        """KPI has correct structure"""
        overview = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        results = overview.json().get("results", [])
        
        if not results:
            pytest.skip("No departments in overview")
        
        dept = results[0]["departement"]
        response = authenticated_client.get(f"{BASE_URL}/api/departements/{dept}/detail")
        assert response.status_code == 200
        
        data = response.json()
        kpi = data.get("kpi", {})
        
        expected_kpi_fields = ["produced_current", "produced_prev", "billable_current", "non_billable_current", "quota_week_total"]
        for field in expected_kpi_fields:
            assert field in kpi, f"Missing KPI field: {field}"
        
        print(f"KPI: produced={kpi['produced_current']}, billable={kpi['billable_current']}, quota={kpi['quota_week_total']}")

    def test_detail_timeseries_structure(self, authenticated_client):
        """Timeseries has correct structure (8 weeks)"""
        overview = authenticated_client.get(f"{BASE_URL}/api/departements/overview")
        results = overview.json().get("results", [])
        
        if not results:
            pytest.skip("No departments in overview")
        
        dept = results[0]["departement"]
        response = authenticated_client.get(f"{BASE_URL}/api/departements/{dept}/detail")
        assert response.status_code == 200
        
        data = response.json()
        timeseries = data.get("timeseries", [])
        
        # Should have 8 weeks
        assert len(timeseries) == 8, f"Expected 8 weeks, got {len(timeseries)}"
        
        if timeseries:
            week_entry = timeseries[0]
            expected_fields = ["week", "produced", "billable", "non_billable", "quota"]
            for field in expected_fields:
                assert field in week_entry, f"Missing timeseries field: {field}"
        
        print(f"Timeseries: {len(timeseries)} weeks")

    def test_detail_product_filter(self, authenticated_client):
        """Product filter works in detail"""
        overview = authenticated_client.get(f"{BASE_URL}/api/departements/overview?product=PV")
        results = overview.json().get("results", [])
        
        if not results:
            pytest.skip("No PV departments")
        
        dept = results[0]["departement"]
        response = authenticated_client.get(f"{BASE_URL}/api/departements/{dept}/detail?product=PV")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"] == "PV", f"Expected PV, got {data['product']}"
        print(f"Product filter PV works for dept {dept}")


class TestClientCoverage:
    """Tests for GET /api/clients/{id}/coverage"""

    def test_coverage_returns_200(self, authenticated_client, test_client_id):
        """Coverage endpoint returns 200 OK"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"Coverage for client {test_client_id} returned 200 OK")

    def test_coverage_response_structure(self, authenticated_client, test_client_id):
        """Coverage returns correct response structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage")
        assert response.status_code == 200
        
        data = response.json()
        
        required_fields = ["client_id", "client_name", "week", "product", "aggregates", "departements", "count"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        assert data["client_id"] == test_client_id
        print(f"Coverage structure OK: client={data['client_name']}, {data['count']} depts")

    def test_coverage_aggregates_structure(self, authenticated_client, test_client_id):
        """Aggregates have correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage")
        assert response.status_code == 200
        
        data = response.json()
        aggregates = data.get("aggregates", {})
        
        expected_fields = ["produced_week", "billable_week", "quota_week", "remaining_week"]
        for field in expected_fields:
            assert field in aggregates, f"Missing aggregate field: {field}"
        
        print(f"Aggregates: produced={aggregates['produced_week']}, billable={aggregates['billable_week']}, quota={aggregates['quota_week']}")

    def test_coverage_departements_structure(self, authenticated_client, test_client_id):
        """Departements in coverage have correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage")
        assert response.status_code == 200
        
        data = response.json()
        depts = data.get("departements", [])
        
        if depts:
            dept = depts[0]
            expected_fields = ["departement", "produit", "quota_week", "billable_week", "remaining_week", "status", "commandes"]
            for field in expected_fields:
                assert field in dept, f"Missing dept field: {field}"
            
            # Validate status
            valid_statuses = ["on_remaining", "saturated"]
            assert dept["status"] in valid_statuses, f"Invalid status: {dept['status']}"
            
            print(f"Coverage dept: {dept['departement']} - {dept['produit']} - status={dept['status']}")
        else:
            print("No departements in coverage - client may have no active commandes")

    def test_coverage_product_filter(self, authenticated_client, test_client_id):
        """Product filter works in coverage"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage?product=PV")
        assert response.status_code == 200
        
        data = response.json()
        assert data["product"] == "PV", f"Expected PV, got {data['product']}"
        
        # All depts should have produit = PV
        for dept in data.get("departements", []):
            assert dept["produit"] == "PV", f"Expected PV, got {dept['produit']}"
        
        print(f"Coverage product filter PV: {data['count']} depts")

    def test_coverage_week_parameter(self, authenticated_client, test_client_id):
        """Week parameter is respected"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/{test_client_id}/coverage?week=2026-W07")
        assert response.status_code == 200
        
        data = response.json()
        assert data["week"] == "2026-W07", f"Expected 2026-W07, got {data['week']}"
        print(f"Coverage week parameter: {data['week']}")

    def test_coverage_invalid_client(self, authenticated_client):
        """Invalid client ID returns 404"""
        response = authenticated_client.get(f"{BASE_URL}/api/clients/invalid-client-id-12345/coverage")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Invalid client returns 404 as expected")


class TestDepartementsAuth:
    """Authentication tests for departements endpoints"""

    def test_overview_requires_auth(self):
        """Overview requires authentication"""
        response = requests.get(f"{BASE_URL}/api/departements/overview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Overview requires auth - OK")

    def test_detail_requires_auth(self):
        """Detail requires authentication"""
        response = requests.get(f"{BASE_URL}/api/departements/75/detail")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Detail requires auth - OK")

    def test_coverage_requires_auth(self):
        """Coverage requires authentication"""
        response = requests.get(f"{BASE_URL}/api/clients/some-id/coverage")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Coverage requires auth - OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
