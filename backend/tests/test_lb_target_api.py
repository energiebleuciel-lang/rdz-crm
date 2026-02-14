"""
Tests for LB Target PCT API Feature
Tests the lb_target_pct field in commandes CRUD operations
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


class TestCommandesLbTargetPct:
    """Test lb_target_pct field in commandes CRUD"""

    def test_list_commandes_returns_lb_target_pct(self, auth_headers):
        """GET /api/commandes?entity=ZR7 returns lb_target_pct field for all commandes"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "commandes" in data
        
        # Check that at least some commandes exist
        if len(data["commandes"]) > 0:
            cmd = data["commandes"][0]
            # Verify lb_target_pct field exists
            assert "lb_target_pct" in cmd, f"lb_target_pct not in commande: {cmd.keys()}"
            # Verify it's a float
            assert isinstance(cmd["lb_target_pct"], (int, float)), f"lb_target_pct is not numeric: {type(cmd['lb_target_pct'])}"
            # Verify it's in 0-1 range (if > 0)
            if cmd["lb_target_pct"] > 0:
                assert 0 <= cmd["lb_target_pct"] <= 1, f"lb_target_pct out of range: {cmd['lb_target_pct']}"
            print(f"✓ Found commande with lb_target_pct={cmd['lb_target_pct']}")

    def test_list_commandes_mdl_returns_lb_target_pct(self, auth_headers):
        """GET /api/commandes?entity=MDL returns lb_target_pct field"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=MDL", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "commandes" in data
        
        if len(data["commandes"]) > 0:
            cmd = data["commandes"][0]
            assert "lb_target_pct" in cmd, f"lb_target_pct not in commande"
            print(f"✓ MDL commande has lb_target_pct={cmd['lb_target_pct']}")


class TestCommandeUpdateLbTargetPct:
    """Test updating lb_target_pct field"""

    @pytest.fixture
    def existing_commande_id(self, auth_headers):
        """Get an existing commande ID to test with"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if len(data["commandes"]) == 0:
            pytest.skip("No commandes available for testing")
        return data["commandes"][0]["id"]

    def test_update_lb_target_pct_valid(self, auth_headers, existing_commande_id):
        """PUT /api/commandes/{id} updates lb_target_pct field"""
        # First get current value
        response = requests.get(f"{BASE_URL}/api/commandes/{existing_commande_id}", headers=auth_headers)
        assert response.status_code == 200
        original_value = response.json()["commande"].get("lb_target_pct", 0)
        
        # Update to a new value (0.25 = 25%)
        new_value = 0.25
        response = requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": new_value}
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "commande" in data
        assert data["commande"]["lb_target_pct"] == new_value, f"lb_target_pct not updated: {data['commande']['lb_target_pct']}"
        
        # Verify by GET
        response = requests.get(f"{BASE_URL}/api/commandes/{existing_commande_id}", headers=auth_headers)
        assert response.status_code == 200
        cmd = response.json()["commande"]
        assert cmd["lb_target_pct"] == new_value, f"GET shows different value: {cmd['lb_target_pct']}"
        
        # Restore original value
        requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": original_value}
        )
        print(f"✓ Successfully updated lb_target_pct to {new_value} and restored to {original_value}")


class TestLbTargetPctValidation:
    """Test lb_target_pct validation rules"""

    @pytest.fixture
    def existing_commande_id(self, auth_headers):
        """Get an existing commande ID to test with"""
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if len(data["commandes"]) == 0:
            pytest.skip("No commandes available for testing")
        return data["commandes"][0]["id"]

    def test_update_lb_target_pct_above_1_rejected(self, auth_headers, existing_commande_id):
        """PUT with lb_target_pct > 1 should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": 1.5}
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ lb_target_pct > 1 correctly rejected")

    def test_update_lb_target_pct_negative_rejected(self, auth_headers, existing_commande_id):
        """PUT with lb_target_pct < 0 should be rejected"""
        response = requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": -0.1}
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ lb_target_pct < 0 correctly rejected")

    def test_update_lb_target_pct_at_boundary_0(self, auth_headers, existing_commande_id):
        """PUT with lb_target_pct = 0 should succeed"""
        response = requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": 0}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ lb_target_pct = 0 accepted")

    def test_update_lb_target_pct_at_boundary_1(self, auth_headers, existing_commande_id):
        """PUT with lb_target_pct = 1 should succeed"""
        response = requests.put(
            f"{BASE_URL}/api/commandes/{existing_commande_id}",
            headers=auth_headers,
            json={"lb_target_pct": 1.0}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ lb_target_pct = 1 accepted")


class TestCommandeDetailLbTargetPct:
    """Test lb_target_pct in single commande endpoint"""

    def test_get_single_commande_has_lb_target_pct(self, auth_headers):
        """GET /api/commandes/{id} returns lb_target_pct"""
        # First get a commande ID
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if len(data["commandes"]) == 0:
            pytest.skip("No commandes available for testing")
        
        commande_id = data["commandes"][0]["id"]
        
        # Get single commande
        response = requests.get(f"{BASE_URL}/api/commandes/{commande_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        cmd = response.json()["commande"]
        assert "lb_target_pct" in cmd, f"lb_target_pct missing in single commande response"
        print(f"✓ Single commande {commande_id[:8]}... has lb_target_pct={cmd['lb_target_pct']}")


class TestCommandeCreateLbTargetPct:
    """Test creating commande with lb_target_pct"""

    def test_get_clients_for_creation(self, auth_headers):
        """Helper: Get a client ID for commande creation test"""
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if len(data["clients"]) == 0:
            pytest.skip("No clients available for testing")
        return data["clients"][0]

    def test_create_commande_with_lb_target_pct(self, auth_headers):
        """POST /api/commandes creates a commande with lb_target_pct"""
        # Get a client
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        clients = response.json()["clients"]
        if len(clients) == 0:
            pytest.skip("No clients available for testing")
        
        client = clients[0]
        
        # Check if active commande exists for this client/product
        response = requests.get(f"{BASE_URL}/api/commandes?entity=ZR7&client_id={client['id']}", headers=auth_headers)
        existing = response.json().get("commandes", [])
        existing_products = [c.get("produit") for c in existing if c.get("active")]
        
        # Find an available product
        available_products = ["ITE", "PAC", "PV"]
        test_product = None
        for p in available_products:
            if p not in existing_products:
                test_product = p
                break
        
        if not test_product:
            pytest.skip("All products already have active commandes for this client")
        
        # Create commande with lb_target_pct
        create_data = {
            "entity": "ZR7",
            "client_id": client["id"],
            "produit": test_product,
            "departements": ["75"],
            "quota_semaine": 10,
            "lb_target_pct": 0.20,  # 20%
            "priorite": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers,
            json=create_data
        )
        
        # If already exists, skip
        if response.status_code == 400:
            pytest.skip(f"Commande already exists: {response.text}")
        
        assert response.status_code == 200 or response.status_code == 201, f"Create failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "commande" in data
        created_cmd = data["commande"]
        
        # Verify lb_target_pct was saved
        assert created_cmd["lb_target_pct"] == 0.20, f"lb_target_pct not saved: {created_cmd['lb_target_pct']}"
        print(f"✓ Created commande with lb_target_pct=0.20")
        
        # Clean up - delete the test commande
        created_id = created_cmd["id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/commandes/{created_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Cleanup failed: {delete_response.text}"
        print(f"✓ Test commande cleaned up")


class TestCreateCommandeValidation:
    """Test lb_target_pct validation on create"""

    def test_create_commande_lb_target_pct_above_1_rejected(self, auth_headers):
        """POST with lb_target_pct > 1 should be rejected"""
        # Get a client
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        clients = response.json()["clients"]
        if len(clients) == 0:
            pytest.skip("No clients available for testing")
        
        client = clients[0]
        
        create_data = {
            "entity": "ZR7",
            "client_id": client["id"],
            "produit": "PV",
            "departements": ["75"],
            "quota_semaine": 10,
            "lb_target_pct": 1.5,  # Invalid - above 1
            "priorite": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers,
            json=create_data
        )
        
        # Should fail validation (400 or 422)
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}: {response.text}"
        print("✓ Create with lb_target_pct > 1 correctly rejected")

    def test_create_commande_lb_target_pct_negative_rejected(self, auth_headers):
        """POST with lb_target_pct < 0 should be rejected"""
        # Get a client
        response = requests.get(f"{BASE_URL}/api/clients?entity=ZR7", headers=auth_headers)
        assert response.status_code == 200
        clients = response.json()["clients"]
        if len(clients) == 0:
            pytest.skip("No clients available for testing")
        
        client = clients[0]
        
        create_data = {
            "entity": "ZR7",
            "client_id": client["id"],
            "produit": "PAC",
            "departements": ["75"],
            "quota_semaine": 10,
            "lb_target_pct": -0.5,  # Invalid - negative
            "priorite": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/commandes",
            headers=auth_headers,
            json=create_data
        )
        
        # Should fail validation (400 or 422)
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}: {response.text}"
        print("✓ Create with lb_target_pct < 0 correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
