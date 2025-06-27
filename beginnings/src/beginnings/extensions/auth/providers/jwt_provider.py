"""
JWT authentication provider implementation.

This module provides JWT-based authentication with token generation,
validation, and refresh capabilities.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from jose import JWTError, jwt
from passlib.context import CryptContext

from beginnings.extensions.auth.providers.base import (
    AuthenticationError,
    BaseAuthProvider,
    User,
)


class JWTProvider(BaseAuthProvider):
    """
    JWT authentication provider.
    
    Provides authentication using JSON Web Tokens with configurable
    algorithms, expiration, and security settings.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize JWT provider.
        
        Args:
            config: JWT configuration dictionary
        """
        super().__init__(config)
        
        # Password context for hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT settings
        self.secret_key = config.get("secret_key")
        self.algorithm = config.get("algorithm", "HS256")
        self.token_expire_minutes = config.get("token_expire_minutes", 30)
        self.issuer = config.get("issuer", "beginnings-app")
        self.audience = config.get("audience", "beginnings-users")
        self.refresh_token_expire_days = config.get("refresh_token_expire_days", 7)
        
        # User lookup function (to be set by extension)
        self._user_lookup_func = None
    
    def set_user_lookup_function(self, func: Any) -> None:
        """Set the function used to lookup users."""
        self._user_lookup_func = func
    
    async def authenticate(self, request: Request) -> User | None:
        """
        Authenticate request using JWT token.
        
        Args:
            request: The incoming request
            
        Returns:
            User object if authentication successful, None if no token
            
        Raises:
            AuthenticationError: If token is invalid
        """
        # Try to get token from Authorization header
        auth_header = request.headers.get("authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Try to get token from cookie if not in header
        if not token:
            token = request.cookies.get("access_token")
        
        if not token:
            return None  # No token provided
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )
            
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing user ID")
            
            # Extract user information from token
            username = payload.get("username")
            email = payload.get("email")
            roles = payload.get("roles", [])
            permissions = payload.get("permissions", [])
            
            # Create user object
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                roles=roles,
                permissions=permissions,
                metadata={"provider": "jwt", "token_type": "access"}
            )
            
            return user
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid JWT token: {e}") from e
    
    async def login(self, request: Request, username: str, password: str) -> tuple[User, dict[str, Any]]:
        """
        Perform login with username and password.
        
        Args:
            request: The incoming request
            username: Username to authenticate
            password: Password to authenticate
            
        Returns:
            Tuple of (User object, tokens dictionary)
            
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
        
        # Create user object
        user = User(
            user_id=str(user_data["id"]),
            username=user_data.get("username"),
            email=user_data.get("email"),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", []),
            metadata={"provider": "jwt"}
        )
        
        # Generate tokens
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.token_expire_minutes * 60
        }
        
        return user, tokens
    
    async def logout(self, request: Request, user: User) -> dict[str, Any]:
        """
        Perform logout for a user.
        
        Args:
            request: The incoming request
            user: The user to log out
            
        Returns:
            Dictionary with logout response data
        """
        # For JWT, logout is typically handled client-side by discarding tokens
        # In a more sophisticated implementation, you might maintain a token blacklist
        return {
            "message": "Logged out successfully",
            "clear_cookies": ["access_token", "refresh_token"]
        }
    
    def create_access_token(self, user: User) -> str:
        """
        Create an access token for a user.
        
        Args:
            user: User to create token for
            
        Returns:
            JWT access token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.token_expire_minutes)
        
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
            "iat": now,
            "exp": expire,
            "iss": self.issuer,
            "aud": self.audience,
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """
        Create a refresh token for a user.
        
        Args:
            user: User to create token for
            
        Returns:
            JWT refresh token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user.user_id,
            "iat": now,
            "exp": expire,
            "iss": self.issuer,
            "aud": self.audience,
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # Unique token ID for revocation
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def refresh_token(self, refresh_token: str) -> tuple[str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )
            
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing user ID")
            
            # Look up current user data
            user_data = await self._lookup_user_by_id(user_id)
            if not user_data:
                raise AuthenticationError("User not found")
            
            # Create user object
            user = User(
                user_id=str(user_data["id"]),
                username=user_data.get("username"),
                email=user_data.get("email"),
                roles=user_data.get("roles", []),
                permissions=user_data.get("permissions", [])
            )
            
            # Generate new tokens
            new_access_token = self.create_access_token(user)
            new_refresh_token = self.create_refresh_token(user)
            
            return new_access_token, new_refresh_token
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid refresh token: {e}") from e
    
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
        # In production, this should be replaced with actual user lookup
        return None
    
    async def _lookup_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Look up user by ID."""
        if self._user_lookup_func:
            return await self._user_lookup_func(user_id=user_id)
        
        # Default implementation for testing/development
        return None
    
    def validate_config(self) -> list[str]:
        """
        Validate JWT provider configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.secret_key:
            errors.append("JWT secret_key is required")
        elif len(self.secret_key) < 32:
            errors.append("JWT secret_key should be at least 32 characters long")
        
        if self.algorithm not in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]:
            errors.append(f"Unsupported JWT algorithm: {self.algorithm}")
        
        if self.token_expire_minutes <= 0:
            errors.append("JWT token_expire_minutes must be positive")
        
        if self.refresh_token_expire_days <= 0:
            errors.append("JWT refresh_token_expire_days must be positive")
        
        return errors