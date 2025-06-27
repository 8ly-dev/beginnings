"""Tests for RBAC (Role-Based Access Control) system."""

import pytest

from beginnings.extensions.auth.rbac import Permission, Role, RBACManager


class TestPermission:
    """Test Permission class."""
    
    def test_permission_creation(self):
        """Test permission creation."""
        perm = Permission("read:profile", "Read user profile")
        
        assert perm.name == "read:profile"
        assert perm.description == "Read user profile"
        assert str(perm) == "read:profile"
    
    def test_permission_equality(self):
        """Test permission equality comparison."""
        perm1 = Permission("read:profile")
        perm2 = Permission("read:profile")
        perm3 = Permission("write:profile")
        
        assert perm1 == perm2
        assert perm1 != perm3
        assert perm1 == "read:profile"
        assert perm1 != "write:profile"
    
    def test_permission_hash(self):
        """Test permission hashing for use in sets."""
        perm1 = Permission("read:profile")
        perm2 = Permission("read:profile")
        
        # Should be able to use in sets
        perm_set = {perm1, perm2}
        assert len(perm_set) == 1


class TestRole:
    """Test Role class."""
    
    def test_role_creation(self):
        """Test role creation."""
        role = Role(
            "admin",
            "Administrator role",
            ["read:profile", "write:profile"],
            ["user"]
        )
        
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert "read:profile" in role.permissions
        assert "write:profile" in role.permissions
        assert "user" in role.inherits
    
    def test_role_add_remove_permission(self):
        """Test adding and removing permissions."""
        role = Role("user")
        
        role.add_permission("read:profile")
        assert "read:profile" in role.permissions
        
        role.remove_permission("read:profile")
        assert "read:profile" not in role.permissions
    
    def test_role_equality(self):
        """Test role equality comparison."""
        role1 = Role("admin")
        role2 = Role("admin")
        role3 = Role("user")
        
        assert role1 == role2
        assert role1 != role3
        assert role1 == "admin"
        assert role1 != "user"


class TestRBACManager:
    """Test RBAC Manager."""
    
    @pytest.fixture
    def rbac_config(self):
        """RBAC configuration for testing."""
        return {
            "permissions": {
                "read:profile": "Read user profile",
                "write:profile": "Write user profile",
                "read:admin": "Read admin data",
                "write:admin": "Write admin data"
            },
            "roles": {
                "user": {
                    "description": "Standard user",
                    "permissions": ["read:profile", "write:profile"]
                },
                "admin": {
                    "description": "Administrator",
                    "permissions": ["read:admin", "write:admin"],
                    "inherits": ["user"]
                },
                "superadmin": {
                    "description": "Super administrator",
                    "permissions": ["*"],
                    "inherits": ["admin"]
                }
            }
        }
    
    @pytest.fixture
    def rbac_manager(self, rbac_config):
        """Create RBAC manager for testing."""
        return RBACManager(rbac_config)
    
    def test_rbac_manager_initialization(self, rbac_manager):
        """Test RBAC manager initialization."""
        assert "read:profile" in rbac_manager.permissions
        assert "user" in rbac_manager.roles
        assert "admin" in rbac_manager.roles
    
    def test_add_permission(self):
        """Test adding permissions."""
        manager = RBACManager()
        
        perm = manager.add_permission("test:permission", "Test permission")
        
        assert perm.name == "test:permission"
        assert perm.description == "Test permission"
        assert "test:permission" in manager.permissions
    
    def test_get_permission(self, rbac_manager):
        """Test getting permissions."""
        perm = rbac_manager.get_permission("read:profile")
        
        assert perm is not None
        assert perm.name == "read:profile"
        
        # Non-existent permission
        assert rbac_manager.get_permission("nonexistent") is None
    
    def test_add_role(self):
        """Test adding roles."""
        manager = RBACManager()
        
        role = manager.add_role(
            "test_role",
            "Test role",
            ["read:test"],
            ["parent_role"]
        )
        
        assert role.name == "test_role"
        assert role.description == "Test role"
        assert "read:test" in role.permissions
        assert "parent_role" in role.inherits
        assert "test_role" in manager.roles
    
    def test_get_role(self, rbac_manager):
        """Test getting roles."""
        role = rbac_manager.get_role("user")
        
        assert role is not None
        assert role.name == "user"
        
        # Non-existent role
        assert rbac_manager.get_role("nonexistent") is None
    
    def test_role_inheritance(self, rbac_manager):
        """Test role inheritance."""
        admin_role = rbac_manager.get_role("admin")
        all_permissions = admin_role.get_all_permissions(rbac_manager)
        
        # Should have own permissions
        assert "read:admin" in all_permissions
        assert "write:admin" in all_permissions
        
        # Should inherit user permissions
        assert "read:profile" in all_permissions
        assert "write:profile" in all_permissions
    
    def test_check_permission(self, rbac_manager):
        """Test permission checking."""
        # User should have user permissions
        assert rbac_manager.check_permission(["user"], "read:profile")
        assert rbac_manager.check_permission(["user"], "write:profile")
        assert not rbac_manager.check_permission(["user"], "read:admin")
        
        # Admin should have both user and admin permissions
        assert rbac_manager.check_permission(["admin"], "read:profile")
        assert rbac_manager.check_permission(["admin"], "read:admin")
        
        # Superadmin should have all permissions (wildcard)
        assert rbac_manager.check_permission(["superadmin"], "read:profile")
        assert rbac_manager.check_permission(["superadmin"], "read:admin")
        assert rbac_manager.check_permission(["superadmin"], "any:permission")
    
    def test_check_role(self, rbac_manager):
        """Test role checking."""
        user_roles = ["user"]
        admin_roles = ["admin"]
        
        # Check single role
        assert rbac_manager.check_role(user_roles, ["user"])
        assert not rbac_manager.check_role(user_roles, ["admin"])
        
        # Check multiple roles (any match)
        assert rbac_manager.check_role(admin_roles, ["user", "admin"])
        assert rbac_manager.check_role(user_roles, ["user", "admin"])
    
    def test_check_all_roles(self, rbac_manager):
        """Test checking all roles."""
        user_admin_roles = ["user", "admin"]
        user_roles = ["user"]
        
        # User with both roles should pass
        assert rbac_manager.check_all_roles(user_admin_roles, ["user", "admin"])
        
        # User with only one role should fail
        assert not rbac_manager.check_all_roles(user_roles, ["user", "admin"])
    
    def test_get_user_permissions(self, rbac_manager):
        """Test getting all user permissions."""
        user_permissions = rbac_manager.get_user_permissions(["user"])
        admin_permissions = rbac_manager.get_user_permissions(["admin"])
        
        assert "read:profile" in user_permissions
        assert "write:profile" in user_permissions
        assert "read:admin" not in user_permissions
        
        assert "read:profile" in admin_permissions
        assert "read:admin" in admin_permissions
    
    def test_validate_route_access_no_auth_required(self, rbac_manager):
        """Test route access validation when no auth required."""
        route_config = {"required": False}
        
        allowed, reason = rbac_manager.validate_route_access([], route_config)
        
        assert allowed
        assert "No authentication required" in reason
    
    def test_validate_route_access_role_required(self, rbac_manager):
        """Test route access validation with role requirements."""
        route_config = {"required": True, "roles": ["admin"]}
        
        # User should be denied
        allowed, reason = rbac_manager.validate_route_access(["user"], route_config)
        assert not allowed
        assert "admin" in reason
        
        # Admin should be allowed
        allowed, reason = rbac_manager.validate_route_access(["admin"], route_config)
        assert allowed
    
    def test_validate_route_access_permission_required(self, rbac_manager):
        """Test route access validation with permission requirements."""
        route_config = {"required": True, "permissions": ["read:admin"]}
        
        # User should be denied
        allowed, reason = rbac_manager.validate_route_access(["user"], route_config)
        assert not allowed
        assert "read:admin" in reason
        
        # Admin should be allowed
        allowed, reason = rbac_manager.validate_route_access(["admin"], route_config)
        assert allowed
    
    def test_validate_route_access_all_roles_required(self, rbac_manager):
        """Test route access validation requiring all roles."""
        route_config = {"required": True, "require_all_roles": ["user", "admin"]}
        
        # User with only one role should be denied
        allowed, reason = rbac_manager.validate_route_access(["user"], route_config)
        assert not allowed
        
        # User with both roles should be allowed
        allowed, reason = rbac_manager.validate_route_access(["user", "admin"], route_config)
        assert allowed
    
    def test_config_validation_success(self, rbac_manager):
        """Test successful configuration validation."""
        errors = rbac_manager.validate_config()
        assert errors == []
    
    def test_config_validation_circular_inheritance(self):
        """Test configuration validation with circular inheritance."""
        config = {
            "roles": {
                "role1": {"inherits": ["role2"]},
                "role2": {"inherits": ["role1"]}
            }
        }
        
        manager = RBACManager(config)
        errors = manager.validate_config()
        
        assert any("Circular inheritance" in error for error in errors)
    
    def test_config_validation_nonexistent_inherited_role(self):
        """Test configuration validation with non-existent inherited role."""
        config = {
            "roles": {
                "role1": {"inherits": ["nonexistent_role"]}
            }
        }
        
        manager = RBACManager(config)
        errors = manager.validate_config()
        
        assert any("non-existent role" in error for error in errors)
    
    def test_get_role_hierarchy(self, rbac_manager):
        """Test getting role hierarchy."""
        hierarchy = rbac_manager.get_role_hierarchy()
        
        assert "user" in hierarchy
        assert "admin" in hierarchy
        
        user_info = hierarchy["user"]
        assert "description" in user_info
        assert "direct_permissions" in user_info
        assert "all_permissions" in user_info
        
        admin_info = hierarchy["admin"]
        assert "user" in admin_info["inherits"]
        # Admin should have both direct and inherited permissions
        assert len(admin_info["all_permissions"]) > len(admin_info["direct_permissions"])