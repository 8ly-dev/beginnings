"""Tests for JWT authentication provider."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request
from jose import jwt

from beginnings.extensions.auth.providers.base import AuthenticationError, User
from beginnings.extensions.auth.providers.jwt_provider import JWTProvider


@pytest.fixture
def jwt_config():
    """JWT provider configuration for testing."""
    return {
        "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security",
        "algorithm": "HS256",
        "token_expire_minutes": 30,
        "issuer": "test-app",
        "audience": "test-users"
    }


@pytest.fixture
def jwt_provider(jwt_config):
    """Create JWT provider instance for testing."""
    return JWTProvider(jwt_config)


@pytest.fixture
def mock_request():
    """Create mock request for testing."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.cookies = {}
    return request


@pytest.fixture
def test_user():
    """Create test user for testing."""
    return User(
        user_id="123",
        username="testuser",
        email="test@example.com",
        roles=["user"],
        permissions=["read:profile"]
    )


class TestJWTProvider:
    """Test JWT authentication provider."""
    
    def test_jwt_provider_initialization(self, jwt_config):
        """Test JWT provider initialization."""
        provider = JWTProvider(jwt_config)
        
        assert provider.secret_key == jwt_config["secret_key"]
        assert provider.algorithm == jwt_config["algorithm"]
        assert provider.token_expire_minutes == jwt_config["token_expire_minutes"]
        assert provider.issuer == jwt_config["issuer"]
        assert provider.audience == jwt_config["audience"]
    
    def test_create_access_token(self, jwt_provider, test_user):
        """Test access token creation."""
        token = jwt_provider.create_access_token(test_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(
            token,
            jwt_provider.secret_key,
            algorithms=[jwt_provider.algorithm],
            issuer=jwt_provider.issuer,
            audience=jwt_provider.audience
        )
        
        assert payload["sub"] == test_user.user_id
        assert payload["username"] == test_user.username
        assert payload["email"] == test_user.email
        assert payload["roles"] == test_user.roles
        assert payload["permissions"] == test_user.permissions
        assert payload["type"] == "access"
        assert payload["iss"] == jwt_provider.issuer
        assert payload["aud"] == jwt_provider.audience
    
    def test_create_refresh_token(self, jwt_provider, test_user):
        """Test refresh token creation."""
        token = jwt_provider.create_refresh_token(test_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(
            token,
            jwt_provider.secret_key,
            algorithms=[jwt_provider.algorithm],
            issuer=jwt_provider.issuer,
            audience=jwt_provider.audience
        )
        
        assert payload["sub"] == test_user.user_id
        assert payload["type"] == "refresh"
        assert payload["iss"] == jwt_provider.issuer
        assert payload["aud"] == jwt_provider.audience
        assert "jti" in payload  # Unique token ID
    
    async def test_authenticate_with_bearer_token(self, jwt_provider, mock_request, test_user):
        """Test authentication with Bearer token in Authorization header."""
        # Create a valid token
        token = jwt_provider.create_access_token(test_user)
        
        # Set Authorization header
        mock_request.headers = {"authorization": f"Bearer {token}"}
        
        # Authenticate
        authenticated_user = await jwt_provider.authenticate(mock_request)
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == test_user.user_id
        assert authenticated_user.username == test_user.username
        assert authenticated_user.email == test_user.email
        assert authenticated_user.roles == test_user.roles
        assert authenticated_user.permissions == test_user.permissions
    
    async def test_authenticate_with_cookie_token(self, jwt_provider, mock_request, test_user):
        """Test authentication with token in cookie."""
        # Create a valid token
        token = jwt_provider.create_access_token(test_user)
        
        # Set cookie
        mock_request.cookies = {"access_token": token}
        
        # Authenticate
        authenticated_user = await jwt_provider.authenticate(mock_request)
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == test_user.user_id
    
    async def test_authenticate_no_token(self, jwt_provider, mock_request):
        """Test authentication with no token provided."""
        # No token in headers or cookies
        authenticated_user = await jwt_provider.authenticate(mock_request)
        
        assert authenticated_user is None
    
    async def test_authenticate_invalid_token(self, jwt_provider, mock_request):
        """Test authentication with invalid token."""
        # Set invalid token
        mock_request.headers = {"authorization": "Bearer invalid-token"}
        
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError):
            await jwt_provider.authenticate(mock_request)
    
    async def test_authenticate_expired_token(self, jwt_provider, mock_request, test_user):
        """Test authentication with expired token."""
        # Create token with past expiration
        payload = {
            "sub": test_user.user_id,
            "exp": datetime.now(timezone.utc).timestamp() - 3600,  # Expired 1 hour ago
            "iss": jwt_provider.issuer,
            "aud": jwt_provider.audience
        }
        
        expired_token = jwt.encode(payload, jwt_provider.secret_key, algorithm=jwt_provider.algorithm)
        mock_request.headers = {"authorization": f"Bearer {expired_token}"}
        
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError):
            await jwt_provider.authenticate(mock_request)
    
    async def test_login_success(self, jwt_provider, mock_request):
        """Test successful login."""
        # Mock user lookup function
        user_data = {
            "id": 123,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": jwt_provider.hash_password("password123"),
            "roles": ["user"],
            "permissions": ["read:profile"]
        }
        
        jwt_provider._user_lookup_func = AsyncMock(return_value=user_data)
        
        # Perform login
        user, tokens = await jwt_provider.login(mock_request, "testuser", "password123")
        
        assert user.user_id == "123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["user"]
        assert user.permissions == ["read:profile"]
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert "expires_in" in tokens
    
    async def test_login_invalid_username(self, jwt_provider, mock_request):
        """Test login with invalid username."""
        # Mock user lookup function to return None
        jwt_provider._user_lookup_func = AsyncMock(return_value=None)
        
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            await jwt_provider.login(mock_request, "nonexistent", "password")
    
    async def test_login_invalid_password(self, jwt_provider, mock_request):
        """Test login with invalid password."""
        user_data = {
            "id": 123,
            "username": "testuser",
            "password_hash": jwt_provider.hash_password("correct_password")
        }
        
        jwt_provider._user_lookup_func = AsyncMock(return_value=user_data)
        
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            await jwt_provider.login(mock_request, "testuser", "wrong_password")
    
    async def test_logout(self, jwt_provider, mock_request, test_user):
        """Test user logout."""
        logout_data = await jwt_provider.logout(mock_request, test_user)
        
        assert "message" in logout_data
        assert "clear_cookies" in logout_data
        assert "access_token" in logout_data["clear_cookies"]
        assert "refresh_token" in logout_data["clear_cookies"]
    
    async def test_refresh_token_success(self, jwt_provider, test_user):
        """Test successful token refresh."""
        # Create refresh token
        refresh_token = jwt_provider.create_refresh_token(test_user)
        
        # Mock user lookup by ID
        user_data = {
            "id": 123,
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user"],
            "permissions": ["read:profile"]
        }
        
        jwt_provider._user_lookup_func = AsyncMock(return_value=user_data)
        
        # Refresh tokens
        new_access_token, new_refresh_token = await jwt_provider.refresh_token(refresh_token)
        
        assert isinstance(new_access_token, str)
        assert isinstance(new_refresh_token, str)
        assert new_access_token != refresh_token
        assert new_refresh_token != refresh_token
    
    async def test_refresh_token_invalid(self, jwt_provider):
        """Test token refresh with invalid refresh token."""
        with pytest.raises(AuthenticationError):
            await jwt_provider.refresh_token("invalid-token")
    
    async def test_refresh_token_wrong_type(self, jwt_provider, test_user):
        """Test token refresh with access token instead of refresh token."""
        # Create access token (wrong type)
        access_token = jwt_provider.create_access_token(test_user)
        
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            await jwt_provider.refresh_token(access_token)
    
    def test_password_hashing(self, jwt_provider):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed = jwt_provider.hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password
        
        # Verify correct password
        assert jwt_provider.verify_password(password, hashed)
        
        # Verify incorrect password
        assert not jwt_provider.verify_password("wrong_password", hashed)
    
    def test_config_validation_success(self, jwt_provider):
        """Test successful configuration validation."""
        errors = jwt_provider.validate_config()
        assert errors == []
    
    def test_config_validation_missing_secret(self):
        """Test configuration validation with missing secret key."""
        config = {"algorithm": "HS256"}
        provider = JWTProvider(config)
        
        errors = provider.validate_config()
        assert any("secret_key is required" in error for error in errors)
    
    def test_config_validation_short_secret(self):
        """Test configuration validation with short secret key."""
        config = {"secret_key": "short"}
        provider = JWTProvider(config)
        
        errors = provider.validate_config()
        assert any("at least 32 characters" in error for error in errors)
    
    def test_config_validation_invalid_algorithm(self):
        """Test configuration validation with invalid algorithm."""
        config = {
            "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security",
            "algorithm": "INVALID"
        }
        provider = JWTProvider(config)
        
        errors = provider.validate_config()
        assert any("Unsupported JWT algorithm" in error for error in errors)
    
    def test_config_validation_invalid_expiration(self):
        """Test configuration validation with invalid token expiration."""
        config = {
            "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security",
            "token_expire_minutes": -1
        }
        provider = JWTProvider(config)
        
        errors = provider.validate_config()
        assert any("token_expire_minutes must be positive" in error for error in errors)