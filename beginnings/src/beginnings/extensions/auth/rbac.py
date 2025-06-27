"""
Role-Based Access Control (RBAC) system for authentication extension.

This module provides role and permission management with inheritance,
route-based access control, and flexible permission checking.
"""

from __future__ import annotations

from typing import Any


class Permission:
    """Represents a single permission in the RBAC system."""
    
    def __init__(self, name: str, description: str = "") -> None:
        """
        Initialize permission.
        
        Args:
            name: Permission name (e.g., "read:profile")
            description: Human-readable description
        """
        self.name = name
        self.description = description
    
    def __str__(self) -> str:
        return self.name
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Permission):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False
    
    def __hash__(self) -> int:
        return hash(self.name)


class Role:
    """Represents a role with associated permissions and inheritance."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        permissions: list[str] | None = None,
        inherits: list[str] | None = None
    ) -> None:
        """
        Initialize role.
        
        Args:
            name: Role name (e.g., "admin")
            description: Human-readable description
            permissions: List of permission names assigned to this role
            inherits: List of role names this role inherits from
        """
        self.name = name
        self.description = description
        self.permissions = set(permissions or [])
        self.inherits = inherits or []
        self._resolved_permissions: set[str] | None = None
    
    def add_permission(self, permission: str) -> None:
        """Add a permission to this role."""
        self.permissions.add(permission)
        self._resolved_permissions = None  # Clear cache
    
    def remove_permission(self, permission: str) -> None:
        """Remove a permission from this role."""
        self.permissions.discard(permission)
        self._resolved_permissions = None  # Clear cache
    
    def has_permission(self, permission: str, rbac_manager: RBACManager) -> bool:
        """Check if this role has a specific permission (including inherited)."""
        resolved_permissions = self.get_all_permissions(rbac_manager)
        return permission in resolved_permissions or "*" in resolved_permissions
    
    def get_all_permissions(self, rbac_manager: RBACManager) -> set[str]:
        """Get all permissions including inherited ones."""
        if self._resolved_permissions is not None:
            return self._resolved_permissions
        
        all_permissions = self.permissions.copy()
        
        # Add inherited permissions
        for parent_role_name in self.inherits:
            parent_role = rbac_manager.get_role(parent_role_name)
            if parent_role:
                all_permissions.update(parent_role.get_all_permissions(rbac_manager))
        
        self._resolved_permissions = all_permissions
        return all_permissions
    
    def __str__(self) -> str:
        return self.name
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Role):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False
    
    def __hash__(self) -> int:
        return hash(self.name)


class RBACManager:
    """
    Role-Based Access Control manager.
    
    Manages roles, permissions, inheritance, and access control decisions.
    """
    
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize RBAC manager.
        
        Args:
            config: RBAC configuration dictionary
        """
        self.roles: dict[str, Role] = {}
        self.permissions: dict[str, Permission] = {}
        
        if config:
            self.load_from_config(config)
    
    def load_from_config(self, config: dict[str, Any]) -> None:
        """
        Load roles and permissions from configuration.
        
        Args:
            config: RBAC configuration dictionary
        """
        # Load permissions first
        permissions_config = config.get("permissions", {})
        for perm_name, perm_data in permissions_config.items():
            if isinstance(perm_data, str):
                description = perm_data
            else:
                description = perm_data.get("description", "")
            
            self.add_permission(perm_name, description)
        
        # Load roles
        roles_config = config.get("roles", {})
        for role_name, role_data in roles_config.items():
            if isinstance(role_data, dict):
                description = role_data.get("description", "")
                permissions = role_data.get("permissions", [])
                inherits = role_data.get("inherits", [])
            else:
                # Simple format: role_name: [permission1, permission2]
                description = ""
                permissions = role_data if isinstance(role_data, list) else []
                inherits = []
            
            self.add_role(role_name, description, permissions, inherits)
    
    def add_permission(self, name: str, description: str = "") -> Permission:
        """
        Add a permission to the system.
        
        Args:
            name: Permission name
            description: Permission description
            
        Returns:
            The created Permission object
        """
        permission = Permission(name, description)
        self.permissions[name] = permission
        return permission
    
    def get_permission(self, name: str) -> Permission | None:
        """Get a permission by name."""
        return self.permissions.get(name)
    
    def add_role(
        self,
        name: str,
        description: str = "",
        permissions: list[str] | None = None,
        inherits: list[str] | None = None
    ) -> Role:
        """
        Add a role to the system.
        
        Args:
            name: Role name
            description: Role description
            permissions: List of permissions for this role
            inherits: List of roles this role inherits from
            
        Returns:
            The created Role object
        """
        role = Role(name, description, permissions, inherits)
        self.roles[name] = role
        
        # Clear permission caches for all roles (inheritance might have changed)
        for existing_role in self.roles.values():
            existing_role._resolved_permissions = None
        
        return role
    
    def get_role(self, name: str) -> Role | None:
        """Get a role by name."""
        return self.roles.get(name)
    
    def check_permission(self, user_roles: list[str], required_permission: str) -> bool:
        """
        Check if user with given roles has required permission.
        
        Args:
            user_roles: List of role names the user has
            required_permission: Permission to check for
            
        Returns:
            True if user has the permission
        """
        for role_name in user_roles:
            role = self.get_role(role_name)
            if role and role.has_permission(required_permission, self):
                return True
        return False
    
    def check_role(self, user_roles: list[str], required_roles: list[str]) -> bool:
        """
        Check if user has any of the required roles.
        
        Args:
            user_roles: List of role names the user has
            required_roles: List of required role names
            
        Returns:
            True if user has at least one required role
        """
        return any(role in user_roles for role in required_roles)
    
    def check_all_roles(self, user_roles: list[str], required_roles: list[str]) -> bool:
        """
        Check if user has all of the required roles.
        
        Args:
            user_roles: List of role names the user has
            required_roles: List of required role names
            
        Returns:
            True if user has all required roles
        """
        return all(role in user_roles for role in required_roles)
    
    def get_user_permissions(self, user_roles: list[str]) -> set[str]:
        """
        Get all permissions for a user based on their roles.
        
        Args:
            user_roles: List of role names the user has
            
        Returns:
            Set of all permissions the user has
        """
        all_permissions: set[str] = set()
        
        for role_name in user_roles:
            role = self.get_role(role_name)
            if role:
                all_permissions.update(role.get_all_permissions(self))
        
        return all_permissions
    
    def validate_route_access(
        self,
        user_roles: list[str],
        route_config: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate if user can access a route based on configuration.
        
        Args:
            user_roles: List of role names the user has
            route_config: Route configuration with access requirements
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check if authentication is required
        if not route_config.get("required", False):
            return True, "No authentication required"
        
        # Check role requirements
        required_roles = route_config.get("roles", [])
        if required_roles:
            if not self.check_role(user_roles, required_roles):
                return False, f"Requires one of roles: {', '.join(required_roles)}"
        
        # Check permission requirements
        required_permissions = route_config.get("permissions", [])
        if required_permissions:
            for permission in required_permissions:
                if not self.check_permission(user_roles, permission):
                    return False, f"Missing required permission: {permission}"
        
        # Check if all required roles are present (if specified)
        required_all_roles = route_config.get("require_all_roles", [])
        if required_all_roles:
            if not self.check_all_roles(user_roles, required_all_roles):
                return False, f"Requires all roles: {', '.join(required_all_roles)}"
        
        return True, "Access granted"
    
    def validate_config(self) -> list[str]:
        """
        Validate RBAC configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check for circular role inheritance
        for role_name, role in self.roles.items():
            if self._has_circular_inheritance(role_name, set()):
                errors.append(f"Circular inheritance detected for role: {role_name}")
        
        # Check that inherited roles exist
        for role_name, role in self.roles.items():
            for inherited_role in role.inherits:
                if inherited_role not in self.roles:
                    errors.append(f"Role '{role_name}' inherits from non-existent role '{inherited_role}'")
        
        return errors
    
    def _has_circular_inheritance(self, role_name: str, visited: set[str]) -> bool:
        """Check for circular inheritance in role hierarchy."""
        if role_name in visited:
            return True
        
        role = self.get_role(role_name)
        if not role:
            return False
        
        visited.add(role_name)
        
        for inherited_role in role.inherits:
            if self._has_circular_inheritance(inherited_role, visited.copy()):
                return True
        
        return False
    
    def get_role_hierarchy(self) -> dict[str, Any]:
        """
        Get the complete role hierarchy for debugging/display.
        
        Returns:
            Dictionary representing the role hierarchy
        """
        hierarchy = {}
        
        for role_name, role in self.roles.items():
            hierarchy[role_name] = {
                "description": role.description,
                "direct_permissions": list(role.permissions),
                "inherits": role.inherits,
                "all_permissions": list(role.get_all_permissions(self))
            }
        
        return hierarchy