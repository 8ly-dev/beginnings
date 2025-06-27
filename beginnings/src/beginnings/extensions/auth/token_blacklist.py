"""
Token blacklist management for JWT authentication.

This module provides secure token blacklisting with configurable storage backends
for JWT token revocation and security.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any


class TokenBlacklistStorage(ABC):
    """Abstract interface for token blacklist storage backends."""
    
    @abstractmethod
    async def add_token(self, token_id: str, expiry_timestamp: float) -> None:
        """Add a token to the blacklist with expiry timestamp."""
        pass
    
    @abstractmethod
    async def is_blacklisted(self, token_id: str) -> bool:
        """Check if a token is blacklisted."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired tokens and return count removed."""
        pass


class MemoryTokenBlacklistStorage(TokenBlacklistStorage):
    """In-memory token blacklist storage for single-instance applications."""
    
    def __init__(self) -> None:
        self._blacklisted_tokens: dict[str, float] = {}
    
    async def add_token(self, token_id: str, expiry_timestamp: float) -> None:
        """Add a token to the blacklist with expiry timestamp."""
        self._blacklisted_tokens[token_id] = expiry_timestamp
    
    async def is_blacklisted(self, token_id: str) -> bool:
        """Check if a token is blacklisted."""
        if token_id not in self._blacklisted_tokens:
            return False
        
        # Check if token has expired and remove it
        expiry = self._blacklisted_tokens[token_id]
        current_time = time.time()
        
        if current_time > expiry:
            del self._blacklisted_tokens[token_id]
            return False
        
        return True
    
    async def cleanup_expired(self) -> int:
        """Remove expired tokens and return count removed."""
        current_time = time.time()
        expired_tokens = [
            token_id for token_id, expiry in self._blacklisted_tokens.items()
            if current_time > expiry
        ]
        
        for token_id in expired_tokens:
            del self._blacklisted_tokens[token_id]
        
        return len(expired_tokens)


class TokenBlacklistManager:
    """
    JWT token blacklist manager.
    
    Provides secure token revocation with configurable storage backends
    and automatic cleanup of expired tokens.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize token blacklist manager.
        
        Args:
            config: Blacklist configuration dictionary
        """
        self.enabled = config.get("enabled", True)
        
        # Storage backend configuration
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "memory")
        
        if storage_type == "memory":
            self._storage = MemoryTokenBlacklistStorage()
        else:
            raise ValueError(f"Unsupported blacklist storage type: {storage_type}")
        
        # Cleanup configuration
        self.cleanup_interval = config.get("cleanup_interval_minutes", 60)
        self.last_cleanup = time.time()
    
    async def blacklist_token(self, token_payload: dict[str, Any]) -> None:
        """
        Add a token to the blacklist.
        
        Args:
            token_payload: Decoded JWT payload containing 'jti' and 'exp'
        """
        if not self.enabled:
            return
        
        # Use JTI (JWT ID) if available, otherwise fall back to sub + iat
        token_id = token_payload.get("jti")
        if not token_id:
            # Generate consistent ID from user and issued time
            user_id = token_payload.get("sub", "")
            issued_at = token_payload.get("iat", 0)
            token_id = f"{user_id}:{issued_at}"
        
        # Get expiration timestamp
        expiry_timestamp = token_payload.get("exp", 0)
        
        if not token_id or not expiry_timestamp:
            raise ValueError("Token missing required fields for blacklisting")
        
        await self._storage.add_token(token_id, expiry_timestamp)
    
    async def is_token_blacklisted(self, token_payload: dict[str, Any]) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token_payload: Decoded JWT payload containing 'jti'
            
        Returns:
            True if token is blacklisted
        """
        if not self.enabled:
            return False
        
        # Periodic cleanup
        await self._maybe_cleanup()
        
        # Use JTI if available, otherwise fall back to sub + iat
        token_id = token_payload.get("jti")
        if not token_id:
            user_id = token_payload.get("sub", "")
            issued_at = token_payload.get("iat", 0)
            token_id = f"{user_id}:{issued_at}"
        
        if not token_id:
            return False
        
        return await self._storage.is_blacklisted(token_id)
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from blacklist.
        
        Returns:
            Number of tokens removed
        """
        if not self.enabled:
            return 0
        
        count = await self._storage.cleanup_expired()
        self.last_cleanup = time.time()
        return count
    
    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if interval has passed."""
        current_time = time.time()
        if current_time - self.last_cleanup > (self.cleanup_interval * 60):
            await self.cleanup_expired_tokens()
    
    def validate_config(self) -> list[str]:
        """
        Validate blacklist configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if self.cleanup_interval <= 0:
            errors.append("Token blacklist cleanup_interval_minutes must be positive")
        
        return errors