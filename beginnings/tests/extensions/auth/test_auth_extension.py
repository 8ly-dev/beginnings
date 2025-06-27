"""Tests for the main authentication extension."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from beginnings.extensions.auth.extension import AuthExtension
from beginnings.extensions.auth.providers.base import User


@pytest.fixture
def auth_config():
    """Authentication extension configuration for testing."""
    return {
        "provider": "jwt",
        "providers": {
            "jwt": {
                "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security",
                "algorithm": "HS256",
                "token_expire_minutes": 30,
                "issuer": "test-app",
                "audience": "test-users"
            }
        },
        "rbac": {
            "roles": {
                "user": {
                    "description": "Standard user",
                    "permissions": ["read:profile"]
                },
                "admin": {
                    "description": "Administrator",
                    "permissions": ["*"],
                    "inherits": ["user"]
                }
            }
        },
        "protected_routes": {
            "/admin/*": {
                "required": True,
                "roles": ["admin"]
            },
            "/api/*": {
                "required": True,
                "roles": ["user", "admin"]
            }
        }
    }


@pytest.fixture
def auth_extension(auth_config):
    """Create authentication extension for testing."""
    return AuthExtension(auth_config)


@pytest.fixture
def mock_request():
    """Create mock request for testing."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.cookies = {}
    request.url.path = "/test"
    
    # Create a proper state object that behaves like getattr would
    class MockState:
        pass
    
    request.state = MockState()
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


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
    return User(
        user_id="456",
        username="adminuser",
        email="admin@example.com",
        roles=["admin"],
        permissions=["*"]
    )


class TestAuthExtension:
    """Test authentication extension."""
    
    def test_auth_extension_initialization(self, auth_extension):
        """Test authentication extension initialization."""
        assert "jwt" in auth_extension.providers
        assert auth_extension.default_provider == "jwt"
        assert auth_extension.rbac_manager is not None
    
    def test_should_apply_to_route_protected_pattern(self, auth_extension):
        """Test route applicability for protected patterns."""
        # Should apply to admin routes
        assert auth_extension.should_apply_to_route("/admin/users", ["GET"], {})
        
        # Should apply to API routes
        assert auth_extension.should_apply_to_route("/api/data", ["POST"], {})
        
        # Should not apply to public routes
        assert not auth_extension.should_apply_to_route("/public", ["GET"], {})
    
    def test_should_apply_to_route_explicit_config(self, auth_extension):
        """Test route applicability with explicit auth config."""
        route_config = {"auth": {"required": True}}
        
        assert auth_extension.should_apply_to_route("/any/path", ["GET"], route_config)
    
    async def test_middleware_no_auth_required(self, auth_extension, mock_request):
        """Test middleware when authentication is not required."""
        route_config = {"auth": {"required": False}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        # Mock call_next
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware(mock_request, call_next)
        
        # Should call next middleware
        call_next.assert_called_once_with(mock_request)
        assert response == mock_response
    
    async def test_middleware_auth_required_no_token(self, auth_extension, mock_request):
        """Test middleware when auth required but no token provided."""
        route_config = {"auth": {"required": True}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        # Mock call_next (should not be called)
        call_next = AsyncMock()
        
        response = await middleware(mock_request, call_next)
        
        # Should not call next middleware
        call_next.assert_not_called()
        
        # Should return redirect for HTML requests
        assert isinstance(response, RedirectResponse)
    
    async def test_middleware_auth_required_api_no_token(self, auth_extension, mock_request):
        """Test middleware for API request when auth required but no token provided."""
        # Set request as API request
        mock_request.url.path = "/api/data"
        mock_request.headers = {"accept": "application/json"}
        
        route_config = {"auth": {"required": True}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        call_next = AsyncMock()
        
        response = await middleware(mock_request, call_next)
        
        # Should return JSON error for API requests
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
    
    async def test_middleware_successful_auth(self, auth_extension, mock_request, test_user):
        """Test middleware with successful authentication."""
        # Mock the JWT provider to return a user
        jwt_provider = auth_extension.providers["jwt"]
        jwt_provider.authenticate = AsyncMock(return_value=test_user)
        
        route_config = {"auth": {"required": True}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware(mock_request, call_next)
        
        # Should inject user into request state
        assert mock_request.state.user == test_user
        
        # Should call next middleware
        call_next.assert_called_once_with(mock_request)
        assert response == mock_response
    
    async def test_middleware_insufficient_permissions(self, auth_extension, mock_request, test_user):
        """Test middleware when user lacks required permissions."""
        # Mock the JWT provider to return a user
        jwt_provider = auth_extension.providers["jwt"]
        jwt_provider.authenticate = AsyncMock(return_value=test_user)
        
        # Require admin role
        route_config = {"auth": {"required": True, "roles": ["admin"]}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        call_next = AsyncMock()
        
        response = await middleware(mock_request, call_next)
        
        # Should not call next middleware
        call_next.assert_not_called()
        
        # Should return access denied response
        assert isinstance(response, RedirectResponse)
    
    async def test_middleware_admin_access_granted(self, auth_extension, mock_request, admin_user):
        """Test middleware when admin user accesses admin route."""
        # Mock the JWT provider to return admin user
        jwt_provider = auth_extension.providers["jwt"]
        jwt_provider.authenticate = AsyncMock(return_value=admin_user)
        
        route_config = {"auth": {"required": True, "roles": ["admin"]}}
        middleware_factory = auth_extension.get_middleware_factory()
        middleware = middleware_factory(route_config)
        
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware(mock_request, call_next)
        
        # Should call next middleware
        call_next.assert_called_once_with(mock_request)
        assert response == mock_response
    
    def test_get_user_from_request(self, auth_extension, mock_request, test_user):
        """Test getting user from request context."""
        # No user in state
        assert auth_extension.get_user_from_request(mock_request) is None
        
        # User in state
        mock_request.state.user = test_user
        assert auth_extension.get_user_from_request(mock_request) == test_user
    
    async def test_login_user(self, auth_extension, mock_request):
        """Test user login."""
        # Mock the JWT provider login method
        jwt_provider = auth_extension.providers["jwt"]
        user_data = {
            "id": 123,
            "username": "testuser",
            "password_hash": jwt_provider.hash_password("password123")
        }
        jwt_provider._user_lookup_func = AsyncMock(return_value=user_data)
        
        user, tokens = await auth_extension.login_user(mock_request, "testuser", "password123")
        
        assert user.username == "testuser"
        assert "access_token" in tokens
    
    async def test_logout_user(self, auth_extension, mock_request, test_user):
        """Test user logout."""
        logout_data = await auth_extension.logout_user(mock_request, test_user)
        
        assert "message" in logout_data
    
    def test_validate_config_success(self, auth_extension):
        """Test successful configuration validation."""
        errors = auth_extension.validate_config()
        assert errors == []
    
    def test_validate_config_no_providers(self):
        """Test configuration validation with no providers."""
        config = {"provider": "jwt", "providers": {}}
        extension = AuthExtension(config)
        
        errors = extension.validate_config()
        assert any("at least one authentication provider" in error.lower() for error in errors)
    
    def test_validate_config_invalid_default_provider(self):
        """Test configuration validation with invalid default provider."""
        config = {
            "provider": "nonexistent",
            "providers": {
                "jwt": {
                    "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security"
                }
            }
        }
        extension = AuthExtension(config)
        
        errors = extension.validate_config()
        assert any("default provider" in error.lower() for error in errors)