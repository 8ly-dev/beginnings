"""
Session-based authentication provider implementation.

This module provides session-based authentication with secure session
management, cookie handling, and configurable storage backends.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import Request, Response
from passlib.context import CryptContext

from beginnings.extensions.auth.providers.base import (
    AuthenticationError,
    BaseAuthProvider,
    User,
)


class SessionStorage:
    """Abstract interface for session storage backends."""
    
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data by ID."""
        raise NotImplementedError
    
    async def set(self, session_id: str, data: dict[str, Any], expire_seconds: int) -> None:
        """Set session data with expiration."""
        raise NotImplementedError
    
    async def delete(self, session_id: str) -> None:
        """Delete session by ID."""
        raise NotImplementedError
    
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions and return count removed."""
        raise NotImplementedError


class MemorySessionStorage(SessionStorage):
    """In-memory session storage for development."""
    
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
    
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data by ID."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # Check expiration
        if session.get("expires", 0) < time.time():
            await self.delete(session_id)
            return None
        
        return session.get("data")
    
    async def set(self, session_id: str, data: dict[str, Any], expire_seconds: int) -> None:
        """Set session data with expiration."""
        self._sessions[session_id] = {
            "data": data,
            "expires": time.time() + expire_seconds,
            "created": time.time()
        }
    
    async def delete(self, session_id: str) -> None:
        """Delete session by ID."""
        self._sessions.pop(session_id, None)
    
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions and return count removed."""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if session.get("expires", 0) < current_time
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        return len(expired_sessions)


class SessionProvider(BaseAuthProvider):
    """
    Session-based authentication provider.
    
    Provides authentication using server-side sessions with configurable
    storage backends and secure cookie handling.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize session provider.
        
        Args:
            config: Session configuration dictionary
        """
        super().__init__(config)
        
        # Password context for hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Session settings
        self.secret_key = config.get("secret_key")
        self.session_timeout = config.get("session_timeout", 3600)  # 1 hour
        self.cookie_name = config.get("cookie_name", "session_id")
        self.cookie_secure = config.get("cookie_secure", True)
        self.cookie_httponly = config.get("cookie_httponly", True)
        self.cookie_samesite = config.get("cookie_samesite", "strict")
        self.cookie_domain = config.get("cookie_domain")
        self.cookie_path = config.get("cookie_path", "/")
        
        # Storage backend
        storage_type = config.get("storage", {}).get("type", "memory")
        if storage_type == "memory":
            self._storage = MemorySessionStorage()
        else:
            raise ValueError(f"Unsupported session storage type: {storage_type}")
        
        # User lookup function (to be set by extension)
        self._user_lookup_func = None
    
    def set_user_lookup_function(self, func: Any) -> None:
        """Set the function used to lookup users."""
        self._user_lookup_func = func
    
    async def authenticate(self, request: Request) -> User | None:
        """
        Authenticate request using session cookie.
        
        Args:
            request: The incoming request
            
        Returns:
            User object if authentication successful, None if no session
            
        Raises:
            AuthenticationError: If session is invalid
        """
        # Get session ID from cookie
        session_id = request.cookies.get(self.cookie_name)
        if not session_id:
            return None  # No session cookie
        
        # Retrieve session data
        session_data = await self._storage.get(session_id)
        if not session_data:
            return None  # Session not found or expired
        
        # Extract user information from session
        user_id = session_data.get("user_id")
        if not user_id:
            raise AuthenticationError("Session missing user ID")
        
        username = session_data.get("username")
        email = session_data.get("email")
        roles = session_data.get("roles", [])
        permissions = session_data.get("permissions", [])
        
        # Create user object
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles,
            permissions=permissions,
            metadata={
                "provider": "session",
                "session_id": session_id,
                "session_created": session_data.get("created")
            }
        )
        
        # Update session last accessed time
        session_data["last_accessed"] = time.time()
        await self._storage.set(session_id, session_data, self.session_timeout)
        
        return user
    
    async def login(self, request: Request, username: str, password: str) -> tuple[User, dict[str, Any]]:
        """
        Perform login with username and password.
        
        Args:
            request: The incoming request
            username: Username to authenticate
            password: Password to authenticate
            
        Returns:
            Tuple of (User object, session data dictionary)
            
        Raises:
            AuthenticationError: If login fails
        """
        # Look up user (this would typically query a database)
        user_data = await self._lookup_user(username)
        if not user_data:
            raise AuthenticationError("Invalid username or password")
        
        # Verify password
        if not self.verify_password(password, user_data.get("password_hash", "")):
            raise AuthenticationError("Invalid username or password")
        
        # Generate new session ID
        session_id = self._generate_session_id()
        
        # Create session data
        session_data = {
            "user_id": str(user_data["id"]),
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "roles": user_data.get("roles", []),
            "permissions": user_data.get("permissions", []),
            "created": time.time(),
            "last_accessed": time.time(),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "")
        }
        
        # Store session
        await self._storage.set(session_id, session_data, self.session_timeout)
        
        # Create user object
        user = User(
            user_id=str(user_data["id"]),
            username=user_data.get("username"),
            email=user_data.get("email"),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", []),
            metadata={"provider": "session", "session_id": session_id}
        )
        
        # Prepare response data with cookie settings
        response_data = {
            "session_id": session_id,
            "cookie_settings": {
                "key": self.cookie_name,
                "value": session_id,
                "max_age": self.session_timeout,
                "secure": self.cookie_secure,
                "httponly": self.cookie_httponly,
                "samesite": self.cookie_samesite,
                "domain": self.cookie_domain,
                "path": self.cookie_path
            }
        }
        
        return user, response_data
    
    async def logout(self, request: Request, user: User) -> dict[str, Any]:
        """
        Perform logout for a user.
        
        Args:
            request: The incoming request
            user: The user to log out
            
        Returns:
            Dictionary with logout response data
        """
        # Get session ID from user metadata or cookie
        session_id = user.metadata.get("session_id")
        if not session_id:
            session_id = request.cookies.get(self.cookie_name)
        
        # Delete session if found
        if session_id:
            await self._storage.delete(session_id)
        
        return {
            "message": "Logged out successfully",
            "clear_cookies": [self.cookie_name]
        }
    
    async def refresh_session(self, request: Request, user: User) -> dict[str, Any]:
        """
        Refresh session for a user (extend expiration).
        
        Args:
            request: The incoming request
            user: The current user
            
        Returns:
            Dictionary with refresh response data
        """
        session_id = user.metadata.get("session_id")
        if not session_id:
            raise AuthenticationError("No session to refresh")
        
        # Get current session data
        session_data = await self._storage.get(session_id)
        if not session_data:
            raise AuthenticationError("Session not found")
        
        # Update last accessed time
        session_data["last_accessed"] = time.time()
        
        # Extend session
        await self._storage.set(session_id, session_data, self.session_timeout)
        
        return {
            "message": "Session refreshed",
            "expires_in": self.session_timeout
        }
    
    def _generate_session_id(self) -> str:
        """Generate a cryptographically secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def hash_password(self, password: str) -> str:
        """Hash a password for secure storage."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def _lookup_user(self, username: str) -> dict[str, Any] | None:
        """Look up user by username."""
        if self._user_lookup_func:
            return await self._user_lookup_func(username=username)
        
        # Default implementation for testing/development
        return None
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self._storage.cleanup_expired()
    
    def validate_config(self) -> list[str]:
        """
        Validate session provider configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.secret_key:
            errors.append("Session secret_key is required")
        elif len(self.secret_key) < 32:
            errors.append("Session secret_key should be at least 32 characters long")
        
        if self.session_timeout <= 0:
            errors.append("Session timeout must be positive")
        
        if not self.cookie_name:
            errors.append("Session cookie_name is required")
        
        if self.cookie_samesite not in ["strict", "lax", "none"]:
            errors.append("Session cookie_samesite must be 'strict', 'lax', or 'none'")
        
        return errors