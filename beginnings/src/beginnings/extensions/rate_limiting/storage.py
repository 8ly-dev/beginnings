"""
Storage backends for rate limiting.

This module provides different storage backends for rate limiting data
including in-memory and Redis/Valkey distributed storage.
"""

import time
from abc import ABC, abstractmethod
from typing import Any


class RateLimitStorage(ABC):
    """Abstract interface for rate limit storage backends."""
    
    @abstractmethod
    async def get_counter(self, key: str) -> tuple[int, float]:
        """Get current count and window start time for key."""
        pass
    
    @abstractmethod
    async def increment_counter(self, key: str, window_seconds: int) -> tuple[int, float]:
        """Increment counter and return new count with window start."""
        pass
    
    @abstractmethod
    async def reset_counter(self, key: str) -> None:
        """Reset counter for key."""
        pass
    
    # Sliding window specific methods
    @abstractmethod
    async def get_sliding_window_entries(self, key: str) -> list[float]:
        """Get list of timestamps for sliding window."""
        pass
    
    @abstractmethod
    async def add_sliding_window_entry(self, key: str, timestamp: float) -> None:
        """Add timestamp to sliding window."""
        pass
    
    @abstractmethod
    async def cleanup_sliding_window_entries(self, key: str, cutoff_time: float) -> None:
        """Remove timestamps older than cutoff_time."""
        pass
    
    # Token bucket specific methods
    @abstractmethod
    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Get token bucket state."""
        pass
    
    @abstractmethod
    async def set_token_bucket(self, key: str, data: dict[str, Any]) -> None:
        """Set token bucket state."""
        pass


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage for single-instance applications."""
    
    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}
        self._sliding_windows: dict[str, list[float]] = {}
        self._token_buckets: dict[str, dict[str, Any]] = {}
    
    async def get_counter(self, key: str) -> tuple[int, float]:
        """Get current count and window start time for key."""
        return self._counters.get(key, (0, time.time()))
    
    async def increment_counter(self, key: str, window_seconds: int) -> tuple[int, float]:
        """Increment counter and return new count with window start."""
        current_time = time.time()
        count, window_start = self._counters.get(key, (0, current_time))
        
        # Reset if window has expired
        if current_time - window_start >= window_seconds:
            count = 0
            window_start = current_time
        
        count += 1
        self._counters[key] = (count, window_start)
        return count, window_start
    
    async def reset_counter(self, key: str) -> None:
        """Reset counter for key."""
        self._counters.pop(key, None)
    
    async def get_sliding_window_entries(self, key: str) -> list[float]:
        """Get list of timestamps for sliding window."""
        return self._sliding_windows.get(key, []).copy()
    
    async def add_sliding_window_entry(self, key: str, timestamp: float) -> None:
        """Add timestamp to sliding window."""
        if key not in self._sliding_windows:
            self._sliding_windows[key] = []
        
        self._sliding_windows[key].append(timestamp)
        
        # Keep entries sorted for efficient cleanup
        self._sliding_windows[key].sort()
    
    async def cleanup_sliding_window_entries(self, key: str, cutoff_time: float) -> None:
        """Remove timestamps older than cutoff_time."""
        if key not in self._sliding_windows:
            return
        
        # Filter out old timestamps
        self._sliding_windows[key] = [
            ts for ts in self._sliding_windows[key] if ts >= cutoff_time
        ]
        
        # Remove empty entries
        if not self._sliding_windows[key]:
            del self._sliding_windows[key]
    
    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Get token bucket state."""
        return self._token_buckets.get(key)
    
    async def set_token_bucket(self, key: str, data: dict[str, Any]) -> None:
        """Set token bucket state."""
        self._token_buckets[key] = data.copy()


class RedisRateLimitStorage(RateLimitStorage):
    """Redis-based rate limit storage for distributed applications."""
    
    def __init__(self, redis_url: str, key_prefix: str = "rate_limit:") -> None:
        """
        Initialize Redis storage.
        
        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all Redis keys
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis connection (lazy initialization)."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                raise ImportError("redis package is required for Redis storage backend")
        return self._redis
    
    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"
    
    async def get_counter(self, key: str) -> tuple[int, float]:
        """Get current count and window start time for key."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"counter:{key}")
        
        pipeline = redis.pipeline()
        pipeline.hget(redis_key, "count")
        pipeline.hget(redis_key, "window_start")
        results = await pipeline.execute()
        
        count = int(results[0]) if results[0] else 0
        window_start = float(results[1]) if results[1] else time.time()
        
        return count, window_start
    
    async def increment_counter(self, key: str, window_seconds: int) -> tuple[int, float]:
        """Increment counter and return new count with window start."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"counter:{key}")
        current_time = time.time()
        
        # Use Lua script for atomic increment with window reset
        lua_script = """
        local key = KEYS[1]
        local current_time = tonumber(ARGV[1])
        local window_seconds = tonumber(ARGV[2])
        
        local count = redis.call('HGET', key, 'count') or 0
        local window_start = redis.call('HGET', key, 'window_start') or current_time
        
        count = tonumber(count)
        window_start = tonumber(window_start)
        
        -- Reset if window expired
        if current_time - window_start >= window_seconds then
            count = 0
            window_start = current_time
        end
        
        count = count + 1
        
        redis.call('HSET', key, 'count', count, 'window_start', window_start)
        redis.call('EXPIRE', key, window_seconds * 2)  -- TTL safety margin
        
        return {count, window_start}
        """
        
        result = await redis.eval(lua_script, 1, redis_key, current_time, window_seconds)
        return int(result[0]), float(result[1])
    
    async def reset_counter(self, key: str) -> None:
        """Reset counter for key."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"counter:{key}")
        await redis.delete(redis_key)
    
    async def get_sliding_window_entries(self, key: str) -> list[float]:
        """Get list of timestamps for sliding window."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"sliding:{key}")
        
        # Use sorted set to store timestamps
        timestamps = await redis.zrange(redis_key, 0, -1)
        return [float(ts) for ts in timestamps]
    
    async def add_sliding_window_entry(self, key: str, timestamp: float) -> None:
        """Add timestamp to sliding window."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"sliding:{key}")
        
        # Add timestamp to sorted set (score = timestamp, value = timestamp)
        await redis.zadd(redis_key, {str(timestamp): timestamp})
        
        # Set expiration (cleanup after reasonable time)
        await redis.expire(redis_key, 3600)  # 1 hour
    
    async def cleanup_sliding_window_entries(self, key: str, cutoff_time: float) -> None:
        """Remove timestamps older than cutoff_time."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"sliding:{key}")
        
        # Remove entries with score less than cutoff_time
        await redis.zremrangebyscore(redis_key, 0, cutoff_time)
    
    async def get_token_bucket(self, key: str) -> dict[str, Any] | None:
        """Get token bucket state."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"bucket:{key}")
        
        data = await redis.hgetall(redis_key)
        if not data:
            return None
        
        return {
            "tokens": float(data.get(b"tokens", 0)),
            "last_refill": float(data.get(b"last_refill", time.time()))
        }
    
    async def set_token_bucket(self, key: str, data: dict[str, Any]) -> None:
        """Set token bucket state."""
        redis = await self._get_redis()
        redis_key = self._make_key(f"bucket:{key}")
        
        await redis.hset(redis_key, mapping={
            "tokens": str(data["tokens"]),
            "last_refill": str(data["last_refill"])
        })
        
        # Set reasonable expiration
        await redis.expire(redis_key, 3600)  # 1 hour


class ValKeyRateLimitStorage(RedisRateLimitStorage):
    """
    Valkey-based rate limit storage.
    
    Valkey is Redis-compatible, so we inherit from Redis storage
    with potentially different connection parameters.
    """
    
    def __init__(self, valkey_url: str, key_prefix: str = "rate_limit:") -> None:
        """
        Initialize Valkey storage.
        
        Args:
            valkey_url: Valkey connection URL
            key_prefix: Prefix for all Valkey keys
        """
        # Valkey is Redis-compatible
        super().__init__(valkey_url, key_prefix)


def create_storage(config: dict[str, Any]) -> RateLimitStorage:
    """
    Create storage backend based on configuration.
    
    Args:
        config: Storage configuration
        
    Returns:
        Storage backend instance
        
    Raises:
        ValueError: If storage type is unknown
    """
    storage_type = config.get("type", "memory")
    
    if storage_type == "memory":
        return MemoryRateLimitStorage()
    elif storage_type == "redis":
        redis_url = config.get("redis_url", "redis://localhost:6379")
        key_prefix = config.get("key_prefix", "rate_limit:")
        return RedisRateLimitStorage(redis_url, key_prefix)
    elif storage_type == "valkey":
        valkey_url = config.get("valkey_url", "redis://localhost:6379")
        key_prefix = config.get("key_prefix", "rate_limit:")
        return ValKeyRateLimitStorage(valkey_url, key_prefix)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")