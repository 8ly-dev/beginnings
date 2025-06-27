"""
Tests for session authentication provider.

This module tests session management, secure session IDs,
and session storage backend integration.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beginnings.extensions.auth.providers.session_provider import SessionProvider
from beginnings.extensions.auth.providers.base import AuthenticationError, User


class TestSessionProvider:
    """Test session authentication provider."""
    
    def test_session_provider_initialization(self):
        """Test session provider initializes correctly."""
        config = {
            "session_timeout": 3600,
            "cookie_name": "session_id",
            "cookie_secure": True,
            "cookie_httponly": True,
            "cookie_samesite": "strict",
            "storage": {
                "type": "memory"
            }
        }
        
        provider = SessionProvider(config)
        
        assert provider.session_timeout == 3600
        assert provider.cookie_name == "session_id"
        assert provider.cookie_secure is True
        assert provider.cookie_httponly is True
        assert provider.cookie_samesite == "strict"
        assert provider.storage is not None
    
    def test_session_provider_default_configuration(self):
        """Test session provider with default configuration."""
        config = {}
        provider = SessionProvider(config)
        
        # Should have secure defaults
        assert provider.session_timeout == 3600  # 1 hour
        assert provider.cookie_name == "sessionid"
        assert provider.cookie_secure is True
        assert provider.cookie_httponly is True
        assert provider.cookie_samesite == "lax"
    
    def test_generate_session_id(self):
        """Test session ID generation."""
        config = {}
        provider = SessionProvider(config)
        
        session_id1 = provider.generate_session_id()
        session_id2 = provider.generate_session_id()
        
        # Session IDs should be different
        assert session_id1 != session_id2
        # Should be long enough for security
        assert len(session_id1) >= 32
        # Should be URL-safe
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=" for c in session_id1)
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        config = {}
        provider = SessionProvider(config)
        
        user = User(
            user_id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:profile"]
        )
        
        session_id = await provider.create_session(user)
        
        assert session_id is not None
        assert len(session_id) >= 32
        
        # Verify session was stored
        session_data = await provider.storage.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == "test-user-123"
        assert session_data["username"] == "testuser"
        assert session_data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_session_valid(self):
        """Test getting valid session data."""
        config = {}
        provider = SessionProvider(config)
        
        user = User(
            user_id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:profile"]
        )
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Retrieve session
        retrieved_data = await provider.get_session(session_id)
        
        assert retrieved_data is not None
        assert retrieved_data["user_id"] == "test-user-123"
        assert retrieved_data["username"] == "testuser"
        assert retrieved_data["roles"] == ["user"]
    
    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """Test getting expired session returns None."""
        config = {"session_timeout": 1}  # 1 second timeout
        provider = SessionProvider(config)
        
        user = User(user_id="test-user-123", username="testuser")
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should return None for expired session
        retrieved_data = await provider.get_session(session_id)
        assert retrieved_data is None
    
    @pytest.mark.asyncio
    async def test_get_session_nonexistent(self):
        """Test getting nonexistent session returns None."""
        config = {}
        provider = SessionProvider(config)
        
        retrieved_data = await provider.get_session("nonexistent-session-id")
        assert retrieved_data is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test session deletion."""
        config = {}
        provider = SessionProvider(config)
        
        user = User(user_id="test-user-123", username="testuser")
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Verify session exists
        session_data = await provider.get_session(session_id)
        assert session_data is not None
        
        # Delete session
        await provider.delete_session(session_id)
        
        # Verify session no longer exists
        session_data = await provider.get_session(session_id)
        assert session_data is None
    
    @pytest.mark.asyncio
    async def test_refresh_session(self):
        """Test session refresh extends expiration."""
        config = {"session_timeout": 3600}
        provider = SessionProvider(config)
        
        user = User(user_id="test-user-123", username="testuser")
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Get initial expiration
        initial_data = await provider.storage.get_session(session_id)
        initial_expires = initial_data["expires_at"]
        
        # Wait a moment
        time.sleep(0.1)
        
        # Refresh session
        await provider.refresh_session(session_id)
        
        # Get updated expiration
        updated_data = await provider.storage.get_session(session_id)
        updated_expires = updated_data["expires_at"]
        
        # Expiration should be extended
        assert updated_expires > initial_expires
    
    @pytest.mark.asyncio
    async def test_authenticate_with_valid_session(self):
        """Test authentication with valid session cookie."""
        config = {}
        provider = SessionProvider(config)
        
        user = User(
            user_id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:profile"]
        )
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Mock request with session cookie
        request = MagicMock()
        request.cookies = {"sessionid": session_id}
        
        # Authenticate
        authenticated_user = await provider.authenticate(request)
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == "test-user-123"
        assert authenticated_user.username == "testuser"
        assert authenticated_user.email == "test@example.com"
        assert authenticated_user.roles == ["user"]
        assert authenticated_user.permissions == ["read:profile"]
    
    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_session(self):
        """Test authentication with invalid session cookie."""
        config = {}
        provider = SessionProvider(config)
        
        # Mock request with invalid session cookie
        request = MagicMock()
        request.cookies = {"sessionid": "invalid-session-id"}
        
        # Authenticate
        authenticated_user = await provider.authenticate(request)
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_with_no_session(self):
        """Test authentication with no session cookie."""
        config = {}
        provider = SessionProvider(config)
        
        # Mock request without session cookie
        request = MagicMock()
        request.cookies = {}
        
        # Authenticate
        authenticated_user = await provider.authenticate(request)
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_with_expired_session(self):
        """Test authentication with expired session."""
        config = {"session_timeout": 1}  # 1 second timeout
        provider = SessionProvider(config)
        
        user = User(user_id="test-user-123", username="testuser")
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Mock request with expired session
        request = MagicMock()
        request.cookies = {"sessionid": session_id}
        
        # Authenticate
        authenticated_user = await provider.authenticate(request)
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_login_creates_session(self):
        """Test login creates and returns session."""
        config = {}
        provider = SessionProvider(config)
        
        # Mock user lookup function
        mock_user = User(
            user_id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:profile"]
        )
        
        async def mock_user_lookup(username, password):
            if username == "testuser" and password == "correct-password":
                return mock_user
            return None
        
        provider.set_user_lookup_function(mock_user_lookup)
        
        # Mock request
        request = MagicMock()
        
        # Perform login
        user, auth_data = await provider.login(request, "testuser", "correct-password")
        
        assert user is not None
        assert user.user_id == "test-user-123"
        assert user.username == "testuser"
        
        assert "session_id" in auth_data
        assert "expires_at" in auth_data
        assert len(auth_data["session_id"]) >= 32
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials raises error."""
        config = {}
        provider = SessionProvider(config)
        
        async def mock_user_lookup(username, password):
            return None  # Invalid credentials
        
        provider.set_user_lookup_function(mock_user_lookup)
        
        request = MagicMock()
        
        with pytest.raises(AuthenticationError) as exc_info:
            await provider.login(request, "testuser", "wrong-password")
        
        assert "Invalid username or password" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_logout_deletes_session(self):
        """Test logout deletes session."""
        config = {}
        provider = SessionProvider(config)
        
        user = User(user_id="test-user-123", username="testuser")
        
        # Create session
        session_id = await provider.create_session(user)
        
        # Verify session exists
        session_data = await provider.get_session(session_id)
        assert session_data is not None
        
        # Mock request
        request = MagicMock()
        
        # Logout
        logout_data = await provider.logout(request, user)
        
        assert logout_data["message"] == "Session logout successful"
        
        # Verify session was deleted (if session_id is in user metadata)
        if "session_id" in user.metadata:
            session_data = await provider.get_session(user.metadata["session_id"])
            assert session_data is None
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config = {
            "session_timeout": 3600,
            "cookie_name": "session_id",
            "cookie_secure": True
        }
        provider = SessionProvider(config)
        
        errors = provider.validate_config()
        assert errors == []
    
    def test_validate_config_invalid_timeout(self):
        """Test configuration validation with invalid timeout."""
        config = {
            "session_timeout": -1  # Invalid negative timeout
        }
        provider = SessionProvider(config)
        
        errors = provider.validate_config()
        assert len(errors) > 0
        assert any("session_timeout" in error for error in errors)
    
    def test_validate_config_empty_cookie_name(self):
        """Test configuration validation with empty cookie name."""
        config = {
            "cookie_name": ""  # Empty cookie name
        }
        provider = SessionProvider(config)
        
        errors = provider.validate_config()
        assert len(errors) > 0
        assert any("cookie_name" in error for error in errors)