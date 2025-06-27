"""
CSRF token generation and validation.

This module provides secure CSRF token generation, validation, and management
with support for stateless and stateful token patterns.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any


class CSRFTokenError(Exception):
    """Raised when CSRF token validation fails."""


class CSRFTokenManager:
    """
    CSRF token manager for generating and validating tokens.
    
    Supports both stateless (HMAC-based) and stateful (session-based) 
    token validation patterns.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CSRF token manager.
        
        Args:
            config: CSRF configuration dictionary
        """
        self.secret_key = config.get("secret_key", "")
        self.token_name = config.get("token_name", "csrf_token")
        self.token_length = config.get("token_length", 32)
        self.token_expire_minutes = config.get("token_expire_minutes", 60)
        self.double_submit_cookie = config.get("double_submit_cookie", True)
        
        if not self.secret_key:
            raise ValueError("CSRF secret key is required")
    
    def generate_token(self, session_id: str | None = None) -> str:
        """
        Generate a CSRF token.
        
        Args:
            session_id: Session ID for stateful tokens (optional)
            
        Returns:
            Generated CSRF token
        """
        # Generate random token data
        random_data = secrets.token_urlsafe(self.token_length)
        current_time = str(int(time.time()))
        
        if self.double_submit_cookie or not session_id:
            # Stateless token - HMAC-based validation
            token_data = f"{random_data}:{current_time}"
            signature = self._generate_signature(token_data)
            return f"{token_data}:{signature}"
        else:
            # Stateful token - just random data for session storage
            return random_data
    
    def validate_token(
        self,
        token: str,
        session_token: str | None = None,
        session_id: str | None = None
    ) -> bool:
        """
        Validate a CSRF token.
        
        Args:
            token: Token to validate
            session_token: Expected token from session (for stateful validation)
            session_id: Session ID (for stateful validation)
            
        Returns:
            True if token is valid
            
        Raises:
            CSRFTokenError: If token validation fails
        """
        if not token:
            raise CSRFTokenError("CSRF token is required")
        
        try:
            if self.double_submit_cookie or not session_id:
                return self._validate_stateless_token(token)
            else:
                return self._validate_stateful_token(token, session_token)
        except Exception as e:
            raise CSRFTokenError(f"Token validation failed: {e}") from e
    
    def _validate_stateless_token(self, token: str) -> bool:
        """Validate HMAC-based stateless token."""
        try:
            parts = token.split(":")
            if len(parts) != 3:
                raise CSRFTokenError("Invalid token format")
            
            random_data, timestamp_str, signature = parts
            token_data = f"{random_data}:{timestamp_str}"
            
            # Verify signature
            expected_signature = self._generate_signature(token_data)
            if not hmac.compare_digest(signature, expected_signature):
                return False
            
            # Check expiration
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            token_age_minutes = (current_time - timestamp) // 60
            
            if token_age_minutes > self.token_expire_minutes:
                raise CSRFTokenError("CSRF token expired")
            
            return True
            
        except (ValueError, IndexError) as e:
            raise CSRFTokenError("Invalid token format") from e
    
    def _validate_stateful_token(self, token: str, session_token: str | None) -> bool:
        """Validate session-based stateful token."""
        if not session_token:
            raise CSRFTokenError("No session token available")
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(token, session_token):
            raise CSRFTokenError("CSRF token mismatch")
        
        return True
    
    def _generate_signature(self, data: str) -> str:
        """Generate HMAC signature for token data."""
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def create_double_submit_cookie_value(self, token: str) -> str:
        """
        Create value for double-submit cookie.
        
        Args:
            token: The CSRF token
            
        Returns:
            Cookie value for double-submit pattern
        """
        # For double-submit pattern, we can use a hash of the token
        return hashlib.sha256(
            f"{token}:{self.secret_key}".encode()
        ).hexdigest()[:16]  # Use first 16 characters
    
    def validate_double_submit_cookie(
        self,
        token: str,
        cookie_value: str
    ) -> bool:
        """
        Validate double-submit cookie pattern.
        
        Args:
            token: CSRF token from form/header
            cookie_value: Value from CSRF cookie
            
        Returns:
            True if cookie matches token
        """
        expected_cookie = self.create_double_submit_cookie_value(token)
        return hmac.compare_digest(cookie_value, expected_cookie)
    
    def get_token_for_template(self, session_id: str | None = None) -> str:
        """
        Get CSRF token for template rendering.
        
        Args:
            session_id: Session ID if using stateful tokens
            
        Returns:
            CSRF token for inclusion in templates
        """
        return self.generate_token(session_id)
    
    def validate_config(self) -> list[str]:
        """
        Validate CSRF configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.secret_key:
            errors.append("CSRF secret_key is required")
        elif len(self.secret_key) < 32:
            errors.append("CSRF secret_key should be at least 32 characters long")
        
        if self.token_length < 16:
            errors.append("CSRF token_length should be at least 16")
        
        if self.token_expire_minutes <= 0:
            errors.append("CSRF token_expire_minutes must be positive")
        
        if not self.token_name:
            errors.append("CSRF token_name is required")
        
        return errors