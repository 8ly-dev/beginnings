"""
Base authentication provider interface.

This module defines the base interface that all authentication providers
must implement to integrate with the authentication extension.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class User:
    """
    User context object representing an authenticated user.
    
    This class provides a consistent interface for user information
    regardless of the authentication provider used.
    """
    
    def __init__(
        self,
        user_id: str,
        username: str | None = None,
        email: str | None = None,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize user context.
        
        Args:
            user_id: Unique identifier for the user
            username: Username if available
            email: Email address if available
            roles: List of roles assigned to the user
            permissions: List of permissions for the user
            metadata: Additional provider-specific metadata
        """
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles or []
        self.permissions = permissions or []
        self.metadata = metadata or {}
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_roles(self, roles: list[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)


class BaseAuthProvider(ABC):
    """
    Abstract base class for authentication providers.
    
    All authentication providers must inherit from this class and implement
    the required methods to integrate with the authentication extension.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the authentication provider.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
    
    @abstractmethod
    async def authenticate(self, request: Request) -> User | None:
        """
        Authenticate a request and return user information.
        
        Args:
            request: The incoming request
            
        Returns:
            User object if authentication successful, None if no authentication
            
        Raises:
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def login(self, request: Request, username: str, password: str) -> tuple[User, dict[str, Any]]:
        """
        Perform login with username and password.
        
        Args:
            request: The incoming request
            username: Username to authenticate
            password: Password to authenticate
            
        Returns:
            Tuple of (User object, authentication data for response)
            
        Raises:
            AuthenticationError: If login fails
        """
        pass
    
    @abstractmethod
    async def logout(self, request: Request, user: User) -> dict[str, Any]:
        """
        Perform logout for a user.
        
        Args:
            request: The incoming request
            user: The user to log out
            
        Returns:
            Dictionary with logout response data
        """
        pass
    
    def validate_config(self) -> list[str]:
        """
        Validate provider configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        return []