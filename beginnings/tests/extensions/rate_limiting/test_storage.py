"""
Tests for rate limiting storage backends.

This module tests different storage backends including in-memory,
Redis, and Valkey storage implementations.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from beginnings.extensions.rate_limiting.storage import (
    MemoryRateLimitStorage,
    RedisRateLimitStorage,
    ValKeyRateLimitStorage,
    create_storage
)


class TestMemoryRateLimitStorage:
    """Test in-memory rate limit storage implementation."""
    
    @pytest.fixture
    def storage(self):
        """Create memory storage instance for testing."""
        return MemoryRateLimitStorage()
    
    @pytest.mark.asyncio
    async def test_memory_storage_initialization(self, storage):
        """Test memory storage initializes correctly."""
        assert storage._counters == {}
        assert storage._sliding_windows == {}
        assert storage._token_buckets == {}
    
    @pytest.mark.asyncio
    async def test_get_counter_nonexistent(self, storage):
        """Test getting counter for non-existent key."""
        count, window_start = await storage.get_counter("test_key")
        assert count == 0
        assert isinstance(window_start, float)
    
    @pytest.mark.asyncio
    async def test_increment_counter_first_time(self, storage):
        """Test incrementing counter for first time."""
        count, window_start = await storage.increment_counter("test_key", 60)
        assert count == 1
        assert isinstance(window_start, float)
    
    @pytest.mark.asyncio
    async def test_increment_counter_within_window(self, storage):
        """Test incrementing counter within same window."""
        # First increment
        count1, window_start1 = await storage.increment_counter("test_key", 60)
        assert count1 == 1
        
        # Second increment within window
        count2, window_start2 = await storage.increment_counter("test_key", 60)
        assert count2 == 2
        assert window_start2 == window_start1
    
    @pytest.mark.asyncio
    async def test_increment_counter_window_reset(self, storage):
        """Test counter reset when window expires."""
        # First increment
        count1, window_start1 = await storage.increment_counter("test_key", 1)
        assert count1 == 1
        
        # Wait for window to expire
        await asyncio.sleep(1.1)
        
        # Second increment should reset counter
        count2, window_start2 = await storage.increment_counter("test_key", 1)
        assert count2 == 1
        assert window_start2 > window_start1
    
    @pytest.mark.asyncio
    async def test_reset_counter(self, storage):
        """Test resetting counter."""
        # Create counter
        await storage.increment_counter("test_key", 60)
        
        # Reset counter
        await storage.reset_counter("test_key")
        
        # Verify counter is gone
        count, _ = await storage.get_counter("test_key")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_sliding_window_entries_empty(self, storage):
        """Test getting sliding window entries for empty key."""
        entries = await storage.get_sliding_window_entries("test_key")
        assert entries == []
    
    @pytest.mark.asyncio
    async def test_add_sliding_window_entry(self, storage):
        """Test adding sliding window entry."""
        timestamp = time.time()
        await storage.add_sliding_window_entry("test_key", timestamp)
        
        entries = await storage.get_sliding_window_entries("test_key")
        assert len(entries) == 1
        assert entries[0] == timestamp
    
    @pytest.mark.asyncio
    async def test_add_multiple_sliding_window_entries(self, storage):
        """Test adding multiple sliding window entries."""
        timestamps = [time.time() - 5, time.time() - 3, time.time() - 1]
        
        for ts in timestamps:
            await storage.add_sliding_window_entry("test_key", ts)
        
        entries = await storage.get_sliding_window_entries("test_key")
        assert len(entries) == 3
        assert entries == sorted(timestamps)  # Should be sorted
    
    @pytest.mark.asyncio
    async def test_cleanup_sliding_window_entries(self, storage):
        """Test cleaning up old sliding window entries."""
        current_time = time.time()
        old_timestamps = [current_time - 10, current_time - 8]
        new_timestamps = [current_time - 2, current_time - 1]
        
        # Add old and new entries
        for ts in old_timestamps + new_timestamps:
            await storage.add_sliding_window_entry("test_key", ts)
        
        # Cleanup entries older than 5 seconds
        cutoff_time = current_time - 5
        await storage.cleanup_sliding_window_entries("test_key", cutoff_time)
        
        entries = await storage.get_sliding_window_entries("test_key")
        assert len(entries) == 2
        assert all(ts >= cutoff_time for ts in entries)
    
    @pytest.mark.asyncio
    async def test_cleanup_sliding_window_entries_all_removed(self, storage):
        """Test cleanup removes all entries and cleans up key."""
        current_time = time.time()
        old_timestamps = [current_time - 10, current_time - 8]
        
        for ts in old_timestamps:
            await storage.add_sliding_window_entry("test_key", ts)
        
        # Cleanup all entries
        cutoff_time = current_time
        await storage.cleanup_sliding_window_entries("test_key", cutoff_time)
        
        # Key should be removed entirely
        assert "test_key" not in storage._sliding_windows
    
    @pytest.mark.asyncio
    async def test_get_token_bucket_nonexistent(self, storage):
        """Test getting non-existent token bucket."""
        bucket = await storage.get_token_bucket("test_key")
        assert bucket is None
    
    @pytest.mark.asyncio
    async def test_set_and_get_token_bucket(self, storage):
        """Test setting and getting token bucket."""
        bucket_data = {"tokens": 50.5, "last_refill": time.time()}
        await storage.set_token_bucket("test_key", bucket_data)
        
        retrieved_data = await storage.get_token_bucket("test_key")
        assert retrieved_data == bucket_data
        assert retrieved_data is not bucket_data  # Should be a copy


class TestRedisRateLimitStorage:
    """Test Redis rate limit storage implementation."""
    
    @pytest.fixture
    def storage(self):
        """Create Redis storage instance for testing."""
        return RedisRateLimitStorage("redis://localhost:6379", "test_rate_limit:")
    
    def test_redis_storage_initialization(self, storage):
        """Test Redis storage initializes correctly."""
        assert storage.redis_url == "redis://localhost:6379"
        assert storage.key_prefix == "test_rate_limit:"
        assert storage._redis is None
    
    def test_make_key(self, storage):
        """Test Redis key generation."""
        key = storage._make_key("test_key")
        assert key == "test_rate_limit:test_key"
    
    @pytest.mark.asyncio
    async def test_get_redis_lazy_initialization(self, storage):
        """Test lazy Redis connection initialization with connection pooling."""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool_from_url, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_pool_from_url.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            redis_conn = await storage._get_redis()
            
            assert redis_conn == mock_redis
            assert storage._redis == mock_redis
            assert storage._pool == mock_pool
            
            # Verify connection pool was created with correct parameters
            mock_pool_from_url.assert_called_once_with(
                "redis://localhost:6379",
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Verify Redis instance was created with the pool
            mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
    
    @pytest.mark.asyncio
    async def test_get_redis_import_error(self, storage):
        """Test Redis import error handling."""
        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(ImportError, match="redis package is required"):
                await storage._get_redis()
    
    @pytest.mark.asyncio
    async def test_get_counter(self, storage):
        """Test getting counter from Redis."""
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[b'5', b'1234567890.5'])
        
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            count, window_start = await storage.get_counter("test_key")
            
            assert count == 5
            assert window_start == 1234567890.5
            mock_pipeline.hget.assert_any_call("test_rate_limit:counter:test_key", "count")
            mock_pipeline.hget.assert_any_call("test_rate_limit:counter:test_key", "window_start")
    
    @pytest.mark.asyncio
    async def test_get_counter_nonexistent(self, storage):
        """Test getting non-existent counter from Redis."""
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, None])
        
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            with patch('time.time', return_value=1234567890.5):
                count, window_start = await storage.get_counter("test_key")
                
                assert count == 0
                assert window_start == 1234567890.5
    
    @pytest.mark.asyncio
    async def test_increment_counter_lua_script(self, storage):
        """Test counter increment using Lua script."""
        mock_redis = AsyncMock()
        mock_redis.eval.return_value = [6, 1234567890.5]
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            with patch('time.time', return_value=1234567890.5):
                count, window_start = await storage.increment_counter("test_key", 60)
                
                assert count == 6
                assert window_start == 1234567890.5
                mock_redis.eval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_counter(self, storage):
        """Test resetting counter in Redis."""
        mock_redis = AsyncMock()
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            await storage.reset_counter("test_key")
            
            mock_redis.delete.assert_called_once_with("test_rate_limit:counter:test_key")
    
    @pytest.mark.asyncio
    async def test_get_sliding_window_entries(self, storage):
        """Test getting sliding window entries from Redis."""
        mock_redis = AsyncMock()
        mock_redis.zrange.return_value = [b'1234567890.1', b'1234567890.2', b'1234567890.3']
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            entries = await storage.get_sliding_window_entries("test_key")
            
            assert entries == [1234567890.1, 1234567890.2, 1234567890.3]
            mock_redis.zrange.assert_called_once_with("test_rate_limit:sliding:test_key", 0, -1)
    
    @pytest.mark.asyncio
    async def test_add_sliding_window_entry(self, storage):
        """Test adding sliding window entry to Redis."""
        mock_redis = AsyncMock()
        timestamp = 1234567890.5
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            await storage.add_sliding_window_entry("test_key", timestamp)
            
            mock_redis.zadd.assert_called_once_with(
                "test_rate_limit:sliding:test_key", 
                {str(timestamp): timestamp}
            )
            mock_redis.expire.assert_called_once_with("test_rate_limit:sliding:test_key", 3600)
    
    @pytest.mark.asyncio
    async def test_cleanup_sliding_window_entries(self, storage):
        """Test cleaning up sliding window entries in Redis."""
        mock_redis = AsyncMock()
        cutoff_time = 1234567890.0
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            await storage.cleanup_sliding_window_entries("test_key", cutoff_time)
            
            mock_redis.zremrangebyscore.assert_called_once_with(
                "test_rate_limit:sliding:test_key", 0, cutoff_time
            )
    
    @pytest.mark.asyncio
    async def test_get_token_bucket(self, storage):
        """Test getting token bucket from Redis."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            b'tokens': b'50.5',
            b'last_refill': b'1234567890.5'
        }
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            bucket_data = await storage.get_token_bucket("test_key")
            
            assert bucket_data == {"tokens": 50.5, "last_refill": 1234567890.5}
            mock_redis.hgetall.assert_called_once_with("test_rate_limit:bucket:test_key")
    
    @pytest.mark.asyncio
    async def test_get_token_bucket_nonexistent(self, storage):
        """Test getting non-existent token bucket from Redis."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            bucket_data = await storage.get_token_bucket("test_key")
            
            assert bucket_data is None
    
    @pytest.mark.asyncio
    async def test_set_token_bucket(self, storage):
        """Test setting token bucket in Redis."""
        mock_redis = AsyncMock()
        bucket_data = {"tokens": 50.5, "last_refill": 1234567890.5}
        
        with patch.object(storage, '_get_redis', return_value=mock_redis):
            await storage.set_token_bucket("test_key", bucket_data)
            
            mock_redis.hset.assert_called_once_with(
                "test_rate_limit:bucket:test_key",
                mapping={"tokens": "50.5", "last_refill": "1234567890.5"}
            )
            mock_redis.expire.assert_called_once_with("test_rate_limit:bucket:test_key", 3600)


class TestValKeyRateLimitStorage:
    """Test Valkey rate limit storage implementation."""
    
    def test_valkey_storage_initialization(self):
        """Test Valkey storage initializes correctly."""
        storage = ValKeyRateLimitStorage("valkey://localhost:6379", "valkey_rate_limit:")
        
        assert storage.redis_url == "valkey://localhost:6379"
        assert storage.key_prefix == "valkey_rate_limit:"
        assert storage._redis is None
    
    def test_valkey_inherits_redis_functionality(self):
        """Test that Valkey storage inherits Redis functionality."""
        storage = ValKeyRateLimitStorage("valkey://localhost:6379")
        
        # Should have all Redis methods
        assert hasattr(storage, 'get_counter')
        assert hasattr(storage, 'increment_counter')
        assert hasattr(storage, 'reset_counter')
        assert hasattr(storage, 'get_sliding_window_entries')
        assert hasattr(storage, 'add_sliding_window_entry')
        assert hasattr(storage, 'cleanup_sliding_window_entries')
        assert hasattr(storage, 'get_token_bucket')
        assert hasattr(storage, 'set_token_bucket')


class TestStorageFactory:
    """Test storage factory function."""
    
    def test_create_memory_storage(self):
        """Test creating memory storage."""
        config = {"type": "memory"}
        storage = create_storage(config)
        
        assert isinstance(storage, MemoryRateLimitStorage)
    
    def test_create_memory_storage_default(self):
        """Test creating memory storage as default."""
        config = {}
        storage = create_storage(config)
        
        assert isinstance(storage, MemoryRateLimitStorage)
    
    def test_create_redis_storage(self):
        """Test creating Redis storage."""
        config = {
            "type": "redis",
            "redis_url": "redis://localhost:6379",
            "key_prefix": "custom_prefix:"
        }
        storage = create_storage(config)
        
        assert isinstance(storage, RedisRateLimitStorage)
        assert storage.redis_url == "redis://localhost:6379"
        assert storage.key_prefix == "custom_prefix:"
    
    def test_create_redis_storage_defaults(self):
        """Test creating Redis storage with defaults."""
        config = {"type": "redis"}
        storage = create_storage(config)
        
        assert isinstance(storage, RedisRateLimitStorage)
        assert storage.redis_url == "redis://localhost:6379"
        assert storage.key_prefix == "rate_limit:"
    
    def test_create_valkey_storage(self):
        """Test creating Valkey storage."""
        config = {
            "type": "valkey",
            "valkey_url": "redis://localhost:6380",
            "key_prefix": "valkey_prefix:"
        }
        storage = create_storage(config)
        
        assert isinstance(storage, ValKeyRateLimitStorage)
        assert storage.redis_url == "redis://localhost:6380"
        assert storage.key_prefix == "valkey_prefix:"
    
    def test_create_valkey_storage_defaults(self):
        """Test creating Valkey storage with defaults."""
        config = {"type": "valkey"}
        storage = create_storage(config)
        
        assert isinstance(storage, ValKeyRateLimitStorage)
        assert storage.redis_url == "redis://localhost:6379"
        assert storage.key_prefix == "rate_limit:"
    
    def test_create_unknown_storage_type(self):
        """Test creating storage with unknown type."""
        config = {"type": "unknown_storage"}
        
        with pytest.raises(ValueError, match="Unknown storage type: unknown_storage"):
            create_storage(config)


# Integration test imports (needed for async tests)
import asyncio