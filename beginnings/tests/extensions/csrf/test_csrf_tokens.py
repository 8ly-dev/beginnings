"""Tests for CSRF token generation and validation."""

import pytest
import time
from unittest.mock import patch

from beginnings.extensions.csrf.tokens import CSRFTokenError, CSRFTokenManager


@pytest.fixture
def csrf_config():
    """CSRF token manager configuration for testing."""
    return {
        "secret_key": "test-secret-key-for-csrf-that-is-long-enough-for-security",
        "token_name": "csrf_token",
        "token_length": 32,
        "token_expire_minutes": 60,
        "double_submit_cookie": True
    }


@pytest.fixture
def token_manager(csrf_config):
    """Create CSRF token manager for testing."""
    return CSRFTokenManager(csrf_config)


class TestCSRFTokenManager:
    """Test CSRF token manager."""
    
    def test_token_manager_initialization(self, csrf_config):
        """Test CSRF token manager initialization."""
        manager = CSRFTokenManager(csrf_config)
        
        assert manager.secret_key == csrf_config["secret_key"]
        assert manager.token_name == csrf_config["token_name"]
        assert manager.token_length == csrf_config["token_length"]
        assert manager.token_expire_minutes == csrf_config["token_expire_minutes"]
        assert manager.double_submit_cookie == csrf_config["double_submit_cookie"]
    
    def test_token_manager_missing_secret_key(self):
        """Test token manager initialization with missing secret key."""
        config = {"token_name": "csrf_token"}
        
        with pytest.raises(ValueError, match="secret key is required"):
            CSRFTokenManager(config)
    
    def test_generate_stateless_token(self, token_manager):
        """Test stateless token generation."""
        token = token_manager.generate_token()
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Stateless token should have 3 parts separated by colons
        parts = token.split(":")
        assert len(parts) == 3
        
        random_data, timestamp, signature = parts
        assert len(random_data) > 0
        assert timestamp.isdigit()
        assert len(signature) > 0
    
    def test_generate_stateful_token(self, token_manager):
        """Test stateful token generation."""
        # Disable double submit cookie for stateful tokens
        token_manager.double_submit_cookie = False
        
        token = token_manager.generate_token(session_id="test_session")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Stateful token should be just random data (no colons)
        assert ":" not in token
    
    def test_validate_stateless_token_success(self, token_manager):
        """Test successful stateless token validation."""
        token = token_manager.generate_token()
        
        # Should validate successfully
        assert token_manager.validate_token(token) is True
    
    def test_validate_stateless_token_invalid_format(self, token_manager):
        """Test stateless token validation with invalid format."""
        with pytest.raises(CSRFTokenError, match="Invalid token format"):
            token_manager.validate_token("invalid-token")
    
    def test_validate_stateless_token_invalid_signature(self, token_manager):
        """Test stateless token validation with invalid signature."""
        # Generate valid token and tamper with signature
        token = token_manager.generate_token()
        parts = token.split(":")
        tampered_token = f"{parts[0]}:{parts[1]}:invalid_signature"
        
        assert token_manager.validate_token(tampered_token) is False
    
    def test_validate_stateless_token_expired(self, token_manager):
        """Test stateless token validation with expired token."""
        # Create token with past timestamp
        past_time = time.time() - 7200  # 2 hours ago
        current_time = time.time()
        
        with patch('beginnings.extensions.csrf.tokens.time.time') as mock_time:
            # Generate token 2 hours ago
            mock_time.return_value = past_time
            token = token_manager.generate_token()
            
            # Reset time to current for validation
            mock_time.return_value = current_time
            
            # Should raise expiration error
            with pytest.raises(CSRFTokenError, match="expired"):
                token_manager.validate_token(token)
    
    def test_validate_stateful_token_success(self, token_manager):
        """Test successful stateful token validation."""
        # Disable double submit cookie for stateful validation
        token_manager.double_submit_cookie = False
        
        session_token = "test_session_token_123"
        
        # Should validate successfully with matching tokens
        assert token_manager.validate_token(
            session_token, 
            session_token=session_token,
            session_id="test_session"
        ) is True
    
    def test_validate_stateful_token_mismatch(self, token_manager):
        """Test stateful token validation with mismatched tokens."""
        token_manager.double_submit_cookie = False
        
        with pytest.raises(CSRFTokenError):
            token_manager.validate_token(
                "token1",
                session_token="token2",
                session_id="test_session"
            )
    
    def test_validate_stateful_token_missing_session(self, token_manager):
        """Test stateful token validation with missing session token."""
        token_manager.double_submit_cookie = False
        
        with pytest.raises(CSRFTokenError, match="No session token"):
            token_manager.validate_token(
                "test_token",
                session_token=None,
                session_id="test_session"
            )
    
    def test_validate_token_empty(self, token_manager):
        """Test token validation with empty token."""
        with pytest.raises(CSRFTokenError, match="token is required"):
            token_manager.validate_token("")
    
    def test_double_submit_cookie_creation(self, token_manager):
        """Test double-submit cookie value creation."""
        token = "test_token_123"
        cookie_value = token_manager.create_double_submit_cookie_value(token)
        
        assert isinstance(cookie_value, str)
        assert len(cookie_value) == 16  # Should be truncated to 16 characters
    
    def test_double_submit_cookie_validation_success(self, token_manager):
        """Test successful double-submit cookie validation."""
        token = "test_token_123"
        cookie_value = token_manager.create_double_submit_cookie_value(token)
        
        assert token_manager.validate_double_submit_cookie(token, cookie_value) is True
    
    def test_double_submit_cookie_validation_failure(self, token_manager):
        """Test double-submit cookie validation failure."""
        token = "test_token_123"
        wrong_cookie = "wrong_cookie_value"
        
        assert token_manager.validate_double_submit_cookie(token, wrong_cookie) is False
    
    def test_get_token_for_template(self, token_manager):
        """Test getting token for template rendering."""
        token = token_manager.get_token_for_template()
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_config_validation_success(self, token_manager):
        """Test successful configuration validation."""
        errors = token_manager.validate_config()
        assert errors == []
    
    def test_config_validation_missing_secret(self):
        """Test configuration validation with missing secret key."""
        config = {"token_name": "csrf_token"}
        
        # Should raise during initialization
        with pytest.raises(ValueError):
            CSRFTokenManager(config)
    
    def test_config_validation_short_secret(self):
        """Test configuration validation with short secret key."""
        config = {"secret_key": "short"}
        manager = CSRFTokenManager(config)
        
        errors = manager.validate_config()
        assert any("at least 32 characters" in error for error in errors)
    
    def test_config_validation_short_token_length(self):
        """Test configuration validation with short token length."""
        config = {
            "secret_key": "test-secret-key-for-csrf-that-is-long-enough-for-security",
            "token_length": 8
        }
        manager = CSRFTokenManager(config)
        
        errors = manager.validate_config()
        assert any("at least 16" in error for error in errors)
    
    def test_config_validation_invalid_expiration(self):
        """Test configuration validation with invalid expiration."""
        config = {
            "secret_key": "test-secret-key-for-csrf-that-is-long-enough-for-security",
            "token_expire_minutes": -1
        }
        manager = CSRFTokenManager(config)
        
        errors = manager.validate_config()
        assert any("must be positive" in error for error in errors)
    
    def test_config_validation_empty_token_name(self):
        """Test configuration validation with empty token name."""
        config = {
            "secret_key": "test-secret-key-for-csrf-that-is-long-enough-for-security",
            "token_name": ""
        }
        manager = CSRFTokenManager(config)
        
        errors = manager.validate_config()
        assert any("token_name is required" in error for error in errors)