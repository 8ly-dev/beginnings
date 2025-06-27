"""
Rate limiting algorithms for Beginnings framework.

This module provides different rate limiting algorithms including
sliding window, token bucket, and fixed window implementations.
"""

import time
from abc import ABC, abstractmethod
from typing import Any


class RateLimitAlgorithm(ABC):
    """Abstract base class for rate limiting algorithms."""
    
    def __init__(self, config: dict[str, Any], storage: Any) -> None:
        """
        Initialize rate limiting algorithm.
        
        Args:
            config: Algorithm-specific configuration
            storage: Storage backend for rate limit data
        """
        self.config = config
        self.storage = storage
    
    @abstractmethod
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int, float]:
        """
        Check if request is allowed within rate limit.
        
        Args:
            key: Unique identifier for rate limiting
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, remaining_requests, reset_time)
        """
        pass


class SlidingWindowAlgorithm(RateLimitAlgorithm):
    """
    Sliding window rate limiting algorithm.
    
    Provides precise rate limiting by tracking individual request timestamps
    within a sliding time window.
    """
    
    def __init__(self, config: dict[str, Any], storage: Any) -> None:
        """
        Initialize sliding window algorithm.
        
        Args:
            config: Algorithm configuration
            storage: Storage backend
        """
        super().__init__(config, storage)
        self.precision_seconds = config.get("precision_seconds", 1)
        self.cleanup_interval = config.get("cleanup_interval", 300)  # 5 minutes
        self._last_cleanup = time.time()
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int, float]:
        """
        Check if request is allowed using sliding window.
        
        Args:
            key: Rate limit identifier
            limit: Maximum requests in window
            window_seconds: Window size in seconds
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Get current request timestamps within window
        timestamps = await self.storage.get_sliding_window_entries(key)
        
        # Filter timestamps within current window
        valid_timestamps = [ts for ts in timestamps if ts >= window_start]
        
        # Check if limit exceeded
        if len(valid_timestamps) >= limit:
            # Find when the oldest request will expire
            oldest_timestamp = min(valid_timestamps) if valid_timestamps else current_time
            reset_time = oldest_timestamp + window_seconds
            return False, 0, reset_time
        
        # Add current request timestamp (rounded to precision)
        rounded_time = self._round_to_precision(current_time)
        await self.storage.add_sliding_window_entry(key, rounded_time)
        
        # Calculate remaining requests and reset time
        remaining = limit - len(valid_timestamps) - 1
        reset_time = current_time + window_seconds
        
        # Periodic cleanup
        if current_time - self._last_cleanup > self.cleanup_interval:
            await self._cleanup_old_entries(key, window_seconds)
            self._last_cleanup = current_time
        
        return True, remaining, reset_time
    
    def _round_to_precision(self, timestamp: float) -> float:
        """Round timestamp to configured precision."""
        return round(timestamp / self.precision_seconds) * self.precision_seconds
    
    async def _cleanup_old_entries(self, key: str, window_seconds: int) -> None:
        """Clean up old entries outside the window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        await self.storage.cleanup_sliding_window_entries(key, cutoff_time)


class TokenBucketAlgorithm(RateLimitAlgorithm):
    """
    Token bucket rate limiting algorithm.
    
    Allows burst requests up to bucket capacity while refilling
    tokens at a steady rate.
    """
    
    def __init__(self, config: dict[str, Any], storage: Any) -> None:
        """
        Initialize token bucket algorithm.
        
        Args:
            config: Algorithm configuration
            storage: Storage backend
        """
        super().__init__(config, storage)
        self.refill_rate = config.get("refill_rate", 1.0)  # tokens per second
        self.max_tokens = config.get("max_tokens", 100)
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int, float]:
        """
        Check if request is allowed using token bucket.
        
        Args:
            key: Rate limit identifier
            limit: Bucket capacity (max tokens)
            window_seconds: Not used in token bucket, included for interface compatibility
            
        Returns:
            Tuple of (allowed, remaining_tokens, reset_time)
        """
        current_time = time.time()
        
        # Get current bucket state
        bucket_data = await self.storage.get_token_bucket(key)
        
        if bucket_data is None:
            # Initialize new bucket (starts full)
            tokens = min(limit, self.max_tokens)
            last_refill = current_time
        else:
            tokens = bucket_data["tokens"]
            last_refill = bucket_data["last_refill"]
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        tokens = min(tokens + tokens_to_add, min(limit, self.max_tokens))
        
        # Check if request can be served
        if tokens < 1:
            # Calculate when next token will be available
            time_until_token = (1 - tokens) / self.refill_rate
            reset_time = current_time + time_until_token
            return False, 0, reset_time
        
        # Consume one token
        tokens -= 1
        
        # Update bucket state
        await self.storage.set_token_bucket(key, {
            "tokens": tokens,
            "last_refill": current_time
        })
        
        # Calculate reset time (when bucket will be full again)
        tokens_to_full = min(limit, self.max_tokens) - tokens
        time_to_full = tokens_to_full / self.refill_rate
        reset_time = current_time + time_to_full
        
        return True, int(tokens), reset_time


class FixedWindowAlgorithm(RateLimitAlgorithm):
    """
    Fixed window rate limiting algorithm.
    
    Divides time into fixed windows and enforces limits within each window.
    """
    
    def __init__(self, config: dict[str, Any], storage: Any) -> None:
        """
        Initialize fixed window algorithm.
        
        Args:
            config: Algorithm configuration
            storage: Storage backend
        """
        super().__init__(config, storage)
        self.window_alignment = config.get("window_alignment", "start")
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int, float]:
        """
        Check if request is allowed using fixed window.
        
        Args:
            key: Rate limit identifier
            limit: Maximum requests per window
            window_seconds: Window size in seconds
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        current_time = time.time()
        window_start = self._get_window_start(current_time, window_seconds)
        window_end = self._get_window_end(window_start, window_seconds)
        
        # Create window-specific key
        window_key = f"{key}:{int(window_start)}"
        
        # Get current count for this window
        count, window_start_stored = await self.storage.get_counter(window_key)
        
        # Reset counter if this is a new window
        if window_start_stored < window_start:
            count = 0
        
        # Check if limit exceeded
        if count >= limit:
            return False, 0, window_end
        
        # Increment counter
        new_count, _ = await self.storage.increment_counter(window_key, window_seconds)
        
        remaining = limit - new_count
        return True, remaining, window_end
    
    def _get_window_start(self, timestamp: float, window_seconds: int) -> float:
        """Calculate window start time for given timestamp."""
        return (int(timestamp) // window_seconds) * window_seconds
    
    def _get_window_end(self, window_start: float, window_seconds: int) -> float:
        """Calculate window end time."""
        return window_start + window_seconds


def create_algorithm(config: dict[str, Any], storage: Any) -> RateLimitAlgorithm:
    """
    Create rate limiting algorithm based on configuration.
    
    Args:
        config: Algorithm configuration
        storage: Storage backend
        
    Returns:
        Rate limiting algorithm instance
        
    Raises:
        ValueError: If algorithm type is unknown
    """
    algorithm_type = config.get("type", "fixed_window")
    
    if algorithm_type == "sliding_window":
        return SlidingWindowAlgorithm(config, storage)
    elif algorithm_type == "token_bucket":
        return TokenBucketAlgorithm(config, storage)
    elif algorithm_type == "fixed_window":
        return FixedWindowAlgorithm(config, storage)
    else:
        raise ValueError(f"Unknown rate limiting algorithm: {algorithm_type}")