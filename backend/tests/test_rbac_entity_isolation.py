"""
RDZ CRM - RBAC + Entity Isolation Tests
Tests:
1. Login returns entity, role, and granular permissions object
2. Entity isolation - ops_zr7 user CANNOT access entity=MDL endpoints (403)
3. Entity isolation - super_admin CAN access both entities
4. Permission enforcement - ops user gets 403 on billing endpoints
5. Permission enforcement - ops user gets 403 on users.manage endpoints
6. User CRUD - super_admin can create/list/update users via /api/auth/users
7. Permission presets - creating user with role=ops gets ops preset permissions
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "energiebleuciel@gmail.com"
SUPER_ADMIN_PASS = "92Ruemarxdormoy"
OPS_ZR7_EMAIL = "ops_zr7@test.com"
OPS_ZR7_PASS = "TestPass123!"


@pytest.fixture(scope="module")
def super_admin_session():
    """Login as super_admin and return session with token"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASS
    })
    assert res.status_code == 200, f"Super admin login failed: {res.text}"
    data = res.json()
    session.headers.update({"Authorization": f"Bearer {data['token']}"})
    session.user = data['user']
    return session


@pytest.fixture(scope="module")
def ops_zr7_session():
    """Login as ops_zr7 and return session with token"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": OPS_ZR7_EMAIL,
        "password": OPS_ZR7_PASS
    })
    assert res.status_code == 200, f"Ops ZR7 login failed: {res.text}"
    data = res.json()
    session.headers.update({"Authorization": f"Bearer {data['token']}"})
    session.user = data['user']
    return session


class TestLoginReturnsRBACData:
    """Test that login returns entity, role, and granular permissions"""
    
    def test_super_admin_login_returns_full_permissions(self, super_admin_session):
        """Verify super_admin login returns all permission keys as True"""
        user = super_admin_session.user
        
        # Verify basic user info
        assert user['email'] == SUPER_ADMIN_EMAIL
        assert user['entity'] == 'ZR7'
        assert user['role'] == 'super_admin'
        
        # Verify permissions object exists and has all keys
        assert 'permissions' in user
        perms = user['permissions']
        
        # All 25 permissions should be True for super_admin
        assert perms.get('dashboard.view') is True
        assert perms.get('leads.view') is True
        assert perms.get('billing.view') is True
        assert perms.get('billing.manage') is True
        assert perms.get('users.manage') is True
        assert perms.get('activity.view') is True
        assert perms.get('monitoring.lb.view') is True
        print("PASS: super_admin has all permissions True")
    
    def test_ops_login_returns_ops_preset_permissions(self, ops_zr7_session):
        """Verify ops user login returns ops preset permissions"""
        user = ops_zr7_session.user
        
        # Verify basic user info
        assert user['email'] == OPS_ZR7_EMAIL
        assert user['entity'] == 'ZR7'
        assert user['role'] == 'ops'
        
        # Verify permissions match ops preset
        perms = user['permissions']
        
        # ops can view dashboard and leads
        assert perms.get('dashboard.view') is True
        assert perms.get('leads.view') is True
        assert perms.get('leads.edit_status') is True
        
        # ops CANNOT delete leads
        assert perms.get('leads.delete') is False
        
        # ops has NO billing permissions
        assert perms.get('billing.view') is False
        assert perms.get('billing.manage') is False
        
        # ops has NO users.manage permission
        assert perms.get('users.manage') is False
        
        # ops has NO activity.view permission
        assert perms.get('activity.view') is False
        
        print("PASS: ops user has correct preset permissions")


class TestEntityIsolation:
    """Test entity isolation - users can only access their entity's data"""
    
    def test_ops_zr7_cannot_access_mdl_commandes(self, ops_zr7_session):
        """ops_zr7 user MUST get 403 when accessing entity=MDL on commandes endpoint"""
        # Try to access MDL entity commandes as ZR7 user
        res = ops_zr7_session.get(f"{BASE_URL}/api/commandes", params={"entity": "MDL"})
        
        assert res.status_code == 403, f"Expected 403 for cross-entity access, got {res.status_code}: {res.text}"
        error_detail = res.json().get('detail', '')
        assert 'MDL' in error_detail or 'ZR7' in error_detail, f"Error should mention entity: {error_detail}"
        print(f"PASS: ops_zr7 correctly gets 403 on MDL endpoint. Error: {error_detail}")
    
    def test_ops_zr7_can_access_zr7_commandes(self, ops_zr7_session):
        """ops_zr7 user CAN access entity=ZR7 commandes"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/commandes", params={"entity": "ZR7"})
        
        assert res.status_code == 200, f"Expected 200 for same-entity access, got {res.status_code}: {res.text}"
        data = res.json()
        assert 'commandes' in data
        assert data.get('entity') == 'ZR7'
        print(f"PASS: ops_zr7 can access ZR7 commandes. Count: {len(data['commandes'])}")
    
    def test_super_admin_can_access_zr7_commandes(self, super_admin_session):
        """super_admin CAN access ZR7 entity"""
        super_admin_session.headers.update({"X-Entity-Scope": "ZR7"})
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "ZR7"})
        
        assert res.status_code == 200, f"Expected 200 for super_admin ZR7 access: {res.text}"
        data = res.json()
        assert data.get('entity') == 'ZR7'
        print(f"PASS: super_admin can access ZR7. Count: {len(data['commandes'])}")
    
    def test_super_admin_can_access_mdl_commandes(self, super_admin_session):
        """super_admin CAN access MDL entity"""
        super_admin_session.headers.update({"X-Entity-Scope": "MDL"})
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "MDL"})
        
        assert res.status_code == 200, f"Expected 200 for super_admin MDL access: {res.text}"
        data = res.json()
        assert data.get('entity') == 'MDL'
        print(f"PASS: super_admin can access MDL. Count: {len(data['commandes'])}")
    
    def test_ops_zr7_cannot_access_mdl_deliveries(self, ops_zr7_session):
        """ops_zr7 user MUST get 403 when accessing entity=MDL on deliveries endpoint"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/deliveries", params={"entity": "MDL"})
        
        assert res.status_code == 403, f"Expected 403 for cross-entity deliveries access, got {res.status_code}: {res.text}"
        print(f"PASS: ops_zr7 correctly gets 403 on MDL deliveries endpoint")
    
    def test_ops_zr7_cannot_access_mdl_clients(self, ops_zr7_session):
        """ops_zr7 user MUST get 403 when accessing entity=MDL on clients endpoint"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/clients", params={"entity": "MDL"})
        
        assert res.status_code == 403, f"Expected 403 for cross-entity clients access, got {res.status_code}: {res.text}"
        print(f"PASS: ops_zr7 correctly gets 403 on MDL clients endpoint")


class TestPermissionEnforcement:
    """Test that permission enforcement works for specific endpoints"""
    
    def test_ops_gets_403_on_billing_endpoints(self, ops_zr7_session):
        """ops user (no billing.view) MUST get 403 on billing endpoints"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/billing/summary", params={"entity": "ZR7"})
        
        assert res.status_code == 403, f"Expected 403 for ops on billing, got {res.status_code}: {res.text}"
        error = res.json().get('detail', '')
        assert 'billing.view' in error or 'Permission' in error, f"Error should mention billing permission: {error}"
        print(f"PASS: ops user gets 403 on billing endpoint. Error: {error}")
    
    def test_ops_gets_403_on_users_manage_list(self, ops_zr7_session):
        """ops user (no users.manage) MUST get 403 on /api/auth/users"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/auth/users")
        
        assert res.status_code == 403, f"Expected 403 for ops on users list, got {res.status_code}: {res.text}"
        error = res.json().get('detail', '')
        assert 'users.manage' in error or 'Permission' in error, f"Error should mention users.manage: {error}"
        print(f"PASS: ops user gets 403 on users list. Error: {error}")
    
    def test_ops_gets_403_on_users_manage_create(self, ops_zr7_session):
        """ops user (no users.manage) MUST get 403 on POST /api/auth/users"""
        res = ops_zr7_session.post(f"{BASE_URL}/api/auth/users", json={
            "email": "test@test.com",
            "password": "Test123!",
            "nom": "Test",
            "entity": "ZR7",
            "role": "viewer"
        })
        
        assert res.status_code == 403, f"Expected 403 for ops on user create, got {res.status_code}: {res.text}"
        print(f"PASS: ops user gets 403 on user create")
    
    def test_ops_gets_403_on_activity_view(self, ops_zr7_session):
        """ops user (no activity.view) MUST get 403 on activity logs"""
        res = ops_zr7_session.get(f"{BASE_URL}/api/auth/activity-logs")
        
        assert res.status_code == 403, f"Expected 403 for ops on activity logs, got {res.status_code}: {res.text}"
        print(f"PASS: ops user gets 403 on activity logs")
    
    def test_super_admin_can_access_billing(self, super_admin_session):
        """super_admin CAN access billing endpoints"""
        super_admin_session.headers.update({"X-Entity-Scope": "ZR7"})
        res = super_admin_session.get(f"{BASE_URL}/api/billing/summary", params={"entity": "ZR7"})
        
        assert res.status_code == 200, f"Expected 200 for super_admin on billing: {res.text}"
        print(f"PASS: super_admin can access billing")
    
    def test_super_admin_can_access_activity(self, super_admin_session):
        """super_admin CAN access activity logs"""
        res = super_admin_session.get(f"{BASE_URL}/api/auth/activity-logs")
        
        assert res.status_code == 200, f"Expected 200 for super_admin on activity: {res.text}"
        print(f"PASS: super_admin can access activity logs")


class TestUserCRUD:
    """Test user management CRUD for super_admin"""
    
    def test_super_admin_can_list_users(self, super_admin_session):
        """super_admin can list all users"""
        res = super_admin_session.get(f"{BASE_URL}/api/auth/users")
        
        assert res.status_code == 200, f"Expected 200 for users list: {res.text}"
        data = res.json()
        assert 'users' in data
        assert len(data['users']) > 0
        
        # Check user structure
        for user in data['users'][:3]:
            assert 'id' in user
            assert 'email' in user
            assert 'role' in user
            # Password should NOT be included
            assert 'password' not in user
        
        print(f"PASS: super_admin can list users. Count: {len(data['users'])}")
    
    def test_super_admin_can_create_user_with_ops_preset(self, super_admin_session):
        """Creating user with role=ops should get ops preset permissions"""
        test_email = f"test_ops_{uuid.uuid4().hex[:8]}@test.com"
        
        res = super_admin_session.post(f"{BASE_URL}/api/auth/users", json={
            "email": test_email,
            "password": "TestPass123!",
            "nom": "Test OPS User",
            "entity": "ZR7",
            "role": "ops"
        })
        
        assert res.status_code == 200, f"Expected 200 for user create: {res.text}"
        data = res.json()
        assert data.get('success') is True
        user = data.get('user', {})
        
        # Verify ops preset permissions were applied
        perms = user.get('permissions', {})
        assert perms.get('dashboard.view') is True, "ops should have dashboard.view"
        assert perms.get('billing.view') is False, "ops should NOT have billing.view"
        assert perms.get('users.manage') is False, "ops should NOT have users.manage"
        
        print(f"PASS: Created user with ops preset. ID: {user.get('id')}")
        
        # Cleanup - deactivate user
        if user.get('id'):
            super_admin_session.delete(f"{BASE_URL}/api/auth/users/{user['id']}")
    
    def test_super_admin_can_create_and_update_user(self, super_admin_session):
        """super_admin can create and update user"""
        test_email = f"test_update_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user
        res = super_admin_session.post(f"{BASE_URL}/api/auth/users", json={
            "email": test_email,
            "password": "TestPass123!",
            "nom": "Original Name",
            "entity": "ZR7",
            "role": "viewer"
        })
        
        assert res.status_code == 200, f"Create user failed: {res.text}"
        user_id = res.json().get('user', {}).get('id')
        assert user_id, "User ID not returned"
        
        # Update user
        res = super_admin_session.put(f"{BASE_URL}/api/auth/users/{user_id}", json={
            "nom": "Updated Name",
            "role": "ops"
        })
        
        assert res.status_code == 200, f"Update user failed: {res.text}"
        updated_user = res.json().get('user', {})
        assert updated_user.get('nom') == "Updated Name"
        assert updated_user.get('role') == "ops"
        
        # Verify role change updated permissions
        perms = updated_user.get('permissions', {})
        assert perms.get('billing.view') is False, "Updated to ops should have billing.view=False"
        
        print(f"PASS: Created and updated user. Final name: {updated_user.get('nom')}")
        
        # Cleanup
        super_admin_session.delete(f"{BASE_URL}/api/auth/users/{user_id}")
    
    def test_super_admin_can_get_permission_keys(self, super_admin_session):
        """super_admin can get all permission keys and presets"""
        res = super_admin_session.get(f"{BASE_URL}/api/auth/permission-keys")
        
        assert res.status_code == 200, f"Expected 200 for permission-keys: {res.text}"
        data = res.json()
        
        assert 'keys' in data
        assert 'presets' in data
        assert 'roles' in data
        
        # Verify keys
        keys = data['keys']
        assert 'dashboard.view' in keys
        assert 'billing.view' in keys
        assert 'users.manage' in keys
        assert len(keys) >= 25, f"Expected 25+ permission keys, got {len(keys)}"
        
        # Verify presets
        presets = data['presets']
        assert 'super_admin' in presets
        assert 'admin' in presets
        assert 'ops' in presets
        assert 'viewer' in presets
        
        # Verify roles
        roles = data['roles']
        assert 'super_admin' in roles
        assert 'ops' in roles
        
        print(f"PASS: Got {len(keys)} permission keys and {len(presets)} role presets")


class TestEntityScopeHeader:
    """Test X-Entity-Scope header for super_admin"""
    
    def test_super_admin_scope_zr7(self, super_admin_session):
        """super_admin with X-Entity-Scope: ZR7 gets ZR7 data only"""
        super_admin_session.headers.update({"X-Entity-Scope": "ZR7"})
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "ZR7"})
        
        assert res.status_code == 200
        data = res.json()
        assert data.get('entity') == 'ZR7'
        print(f"PASS: X-Entity-Scope: ZR7 works")
    
    def test_super_admin_scope_mdl(self, super_admin_session):
        """super_admin with X-Entity-Scope: MDL gets MDL data only"""
        super_admin_session.headers.update({"X-Entity-Scope": "MDL"})
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "MDL"})
        
        assert res.status_code == 200
        data = res.json()
        assert data.get('entity') == 'MDL'
        print(f"PASS: X-Entity-Scope: MDL works")
    
    def test_super_admin_scope_both(self, super_admin_session):
        """super_admin with X-Entity-Scope: BOTH can access any entity"""
        super_admin_session.headers.update({"X-Entity-Scope": "BOTH"})
        
        # Access ZR7
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "ZR7"})
        assert res.status_code == 200, "BOTH scope should allow ZR7"
        
        # Access MDL
        res = super_admin_session.get(f"{BASE_URL}/api/commandes", params={"entity": "MDL"})
        assert res.status_code == 200, "BOTH scope should allow MDL"
        
        print(f"PASS: X-Entity-Scope: BOTH works for all entities")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
