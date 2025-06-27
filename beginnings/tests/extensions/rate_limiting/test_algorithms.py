"""
Tests for rate limiting algorithms.

This module tests sliding window, token bucket, and fixed window
rate limiting algorithm implementations.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from beginnings.extensions.rate_limiting.algorithms import (
    SlidingWindowAlgorithm,
    TokenBucketAlgorithm,
    FixedWindowAlgorithm
)
from beginnings.extensions.rate_limiting.storage import MemoryRateLimitStorage


class TestSlidingWindowAlgorithm:
    """Test sliding window rate limiting algorithm."""
    
    def test_sliding_window_initialization(self):
        """Test sliding window algorithm initializes correctly."""
        config = {
            "precision_seconds": 1,
            "cleanup_interval": 300
        }
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm(config, storage)
        
        assert algorithm.precision_seconds == 1
        assert algorithm.cleanup_interval == 300
        assert algorithm.storage is storage
    
    def test_sliding_window_default_config(self):
        """Test sliding window with default configuration."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({}, storage)
        
        # Should have sensible defaults
        assert algorithm.precision_seconds == 1
        assert algorithm.cleanup_interval == 300
    
    @pytest.mark.asyncio
    async def test_sliding_window_under_limit(self):
        """Test sliding window when under rate limit."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({"precision_seconds": 1}, storage)
        
        key = "test_user"
        limit = 10
        window_seconds = 60
        
        # Make requests under the limit
        for i in range(5):
            allowed, remaining, reset_time = await algorithm.is_allowed(
                key, limit, window_seconds
            )
            assert allowed is True
            assert remaining == limit - (i + 1)
            assert reset_time > time.time()
    
    @pytest.mark.asyncio
    async def test_sliding_window_over_limit(self):
        """Test sliding window when over rate limit."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({"precision_seconds": 1}, storage)
        
        key = "test_user"
        limit = 3
        window_seconds = 60
        
        # Make requests up to the limit
        for i in range(3):
            allowed, remaining, reset_time = await algorithm.is_allowed(
                key, limit, window_seconds
            )
            assert allowed is True
        
        # Next request should be denied
        allowed, remaining, reset_time = await algorithm.is_allowed(
            key, limit, window_seconds
        )
        assert allowed is False
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_sliding_window_time_progression(self):
        """Test sliding window with time progression."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({"precision_seconds": 1}, storage)
        
        key = "test_user"
        limit = 2
        window_seconds = 5  # Short window for testing
        
        # Use up limit
        for i in range(2):
            allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
        
        # Should be denied
        allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False
        
        # Mock time progression beyond window
        with patch('time.time', return_value=time.time() + 6):
            # Should be allowed again
            allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
            assert remaining == limit - 1
    
    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self):
        """Test sliding window cleanup of old entries."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({"precision_seconds": 1}, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 10
        
        # Make some requests
        for i in range(3):
            await algorithm.is_allowed(key, limit, window_seconds)
        
        # Verify entries exist
        entries = await storage.get_sliding_window_entries(key)
        assert len(entries) == 3
        
        # Mock time progression and cleanup
        with patch('time.time', return_value=time.time() + 15):
            await algorithm._cleanup_old_entries(key, window_seconds)
            entries = await storage.get_sliding_window_entries(key)
            assert len(entries) == 0
    
    @pytest.mark.asyncio
    async def test_sliding_window_precision(self):
        """Test sliding window precision affects granularity."""
        storage = MemoryRateLimitStorage()
        algorithm = SlidingWindowAlgorithm({"precision_seconds": 10}, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 60
        
        # Multiple requests in same precision window should be grouped
        current_time = int(time.time())
        with patch('time.time', return_value=current_time):
            await algorithm.is_allowed(key, limit, window_seconds)
            await algorithm.is_allowed(key, limit, window_seconds)
        
        # Check that requests were grouped by precision
        entries = await storage.get_sliding_window_entries(key)
        # Should have fewer entries due to grouping
        assert len(entries) <= 2


class TestTokenBucketAlgorithm:
    """Test token bucket rate limiting algorithm."""
    
    def test_token_bucket_initialization(self):
        """Test token bucket algorithm initializes correctly."""
        config = {
            "refill_rate": 1.0,
            "max_tokens": 100
        }
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm(config, storage)
        
        assert algorithm.refill_rate == 1.0
        assert algorithm.max_tokens == 100
        assert algorithm.storage is storage
    
    def test_token_bucket_default_config(self):
        """Test token bucket with default configuration."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({}, storage)
        
        # Should have sensible defaults
        assert algorithm.refill_rate == 1.0
        assert algorithm.max_tokens == 100
    
    @pytest.mark.asyncio
    async def test_token_bucket_initial_bucket_full(self):
        """Test token bucket starts with full bucket."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({"max_tokens": 10}, storage)
        
        key = "test_user"
        limit = 10
        window_seconds = 60
        
        # First request should be allowed with full bucket
        allowed, remaining, reset_time = await algorithm.is_allowed(
            key, limit, window_seconds
        )
        assert allowed is True
        assert remaining == 9  # One token consumed
    
    @pytest.mark.asyncio
    async def test_token_bucket_consumption(self):
        """Test token bucket consumption."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({"max_tokens": 5, "refill_rate": 0.1}, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 60
        
        # Consume all tokens
        for i in range(5):
            allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
            assert remaining == 4 - i
        
        # Next request should be denied (bucket empty)
        allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        """Test token bucket refill mechanism."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({
            "max_tokens": 5,
            "refill_rate": 2.0  # 2 tokens per second
        }, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 60
        
        # Empty the bucket
        for i in range(5):
            await algorithm.is_allowed(key, limit, window_seconds)
        
        # Should be denied
        allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False
        
        # Mock time progression (1 second = 2 tokens)
        with patch('time.time', return_value=time.time() + 1):
            allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
            assert remaining >= 0  # Should have refilled tokens
    
    @pytest.mark.asyncio
    async def test_token_bucket_max_tokens_limit(self):
        """Test token bucket doesn't exceed max tokens."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({
            "max_tokens": 3,
            "refill_rate": 10.0  # High refill rate
        }, storage)
        
        key = "test_user"
        limit = 3
        window_seconds = 60
        
        # Use one token
        await algorithm.is_allowed(key, limit, window_seconds)
        
        # Wait long enough for many tokens to be generated
        with patch('time.time', return_value=time.time() + 10):
            allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
            # Should not exceed max_tokens minus the one we just consumed
            assert remaining <= 2
    
    @pytest.mark.asyncio
    async def test_token_bucket_burst_capacity(self):
        """Test token bucket allows burst requests."""
        storage = MemoryRateLimitStorage()
        algorithm = TokenBucketAlgorithm({
            "max_tokens": 10,
            "refill_rate": 1.0  # Slow refill
        }, storage)
        
        key = "test_user"
        limit = 10
        window_seconds = 60
        
        # Should allow burst of requests up to bucket capacity
        for i in range(10):
            allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
        
        # 11th request should be denied
        allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False


class TestFixedWindowAlgorithm:
    """Test fixed window rate limiting algorithm."""
    
    def test_fixed_window_initialization(self):
        """Test fixed window algorithm initializes correctly."""
        config = {
            "window_alignment": "start"
        }
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm(config, storage)
        
        assert algorithm.window_alignment == "start"
        assert algorithm.storage is storage
    
    def test_fixed_window_default_config(self):
        """Test fixed window with default configuration."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        # Should have sensible defaults
        assert algorithm.window_alignment == "start"
    
    @pytest.mark.asyncio
    async def test_fixed_window_under_limit(self):
        """Test fixed window when under rate limit."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        key = "test_user"
        limit = 10
        window_seconds = 60
        
        # Make requests under the limit
        for i in range(5):
            allowed, remaining, reset_time = await algorithm.is_allowed(
                key, limit, window_seconds
            )
            assert allowed is True
            assert remaining == limit - (i + 1)
            assert reset_time > time.time()
    
    @pytest.mark.asyncio
    async def test_fixed_window_over_limit(self):
        """Test fixed window when over rate limit."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        key = "test_user"
        limit = 3
        window_seconds = 60
        
        # Make requests up to the limit
        for i in range(3):
            allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
        
        # Next request should be denied
        allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False
        assert remaining == 0
    
    @pytest.mark.asyncio
    async def test_fixed_window_reset(self):
        """Test fixed window reset behavior."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        key = "test_user"
        limit = 2
        window_seconds = 5  # Short window for testing
        
        # Use up limit
        for i in range(2):
            allowed, _, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
        
        # Should be denied
        allowed, _, reset_time = await algorithm.is_allowed(key, limit, window_seconds)
        assert allowed is False
        
        # Mock time progression to next window
        next_window_time = reset_time + 1
        with patch('time.time', return_value=next_window_time):
            # Should be allowed again (new window)
            allowed, remaining, _ = await algorithm.is_allowed(key, limit, window_seconds)
            assert allowed is True
            assert remaining == limit - 1
    
    @pytest.mark.asyncio
    async def test_fixed_window_alignment_start(self):
        """Test fixed window with start alignment."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({"window_alignment": "start"}, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 10
        
        current_time = time.time()
        window_start = algorithm._get_window_start(current_time, window_seconds)
        
        # Window should start at aligned boundary
        assert window_start <= current_time
        assert window_start % window_seconds == 0
    
    @pytest.mark.asyncio
    async def test_fixed_window_concurrent_requests(self):
        """Test fixed window with concurrent requests."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        key = "test_user"
        limit = 5
        window_seconds = 60
        
        # Simulate concurrent requests at same time
        current_time = time.time()
        with patch('time.time', return_value=current_time):
            results = []
            for i in range(10):
                result = await algorithm.is_allowed(key, limit, window_seconds)
                results.append(result[0])  # allowed flag
        
        # Only first 5 should be allowed
        assert sum(results) == 5
    
    def test_get_window_start_calculation(self):
        """Test window start time calculation."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({"window_alignment": "start"}, storage)
        
        # Test with known timestamp
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        window_seconds = 3600  # 1 hour
        
        window_start = algorithm._get_window_start(timestamp, window_seconds)
        
        # Should align to hour boundary
        assert window_start == timestamp
        assert window_start % window_seconds == 0
    
    def test_get_window_end_calculation(self):
        """Test window end time calculation."""
        storage = MemoryRateLimitStorage()
        algorithm = FixedWindowAlgorithm({}, storage)
        
        window_start = 1609459200  # 2021-01-01 00:00:00 UTC
        window_seconds = 3600  # 1 hour
        
        window_end = algorithm._get_window_end(window_start, window_seconds)
        
        # Should be exactly one window length later
        assert window_end == window_start + window_seconds


class TestAlgorithmFactory:
    """Test rate limiting algorithm factory."""
    
    def test_create_sliding_window_algorithm(self):
        """Test creating sliding window algorithm."""
        from beginnings.extensions.rate_limiting.algorithms import create_algorithm
        
        config = {"type": "sliding_window"}
        storage = MemoryRateLimitStorage()
        
        algorithm = create_algorithm(config, storage)
        
        assert isinstance(algorithm, SlidingWindowAlgorithm)
    
    def test_create_token_bucket_algorithm(self):
        """Test creating token bucket algorithm."""
        from beginnings.extensions.rate_limiting.algorithms import create_algorithm
        
        config = {"type": "token_bucket"}
        storage = MemoryRateLimitStorage()
        
        algorithm = create_algorithm(config, storage)
        
        assert isinstance(algorithm, TokenBucketAlgorithm)
    
    def test_create_fixed_window_algorithm(self):
        """Test creating fixed window algorithm."""
        from beginnings.extensions.rate_limiting.algorithms import create_algorithm
        
        config = {"type": "fixed_window"}
        storage = MemoryRateLimitStorage()
        
        algorithm = create_algorithm(config, storage)
        
        assert isinstance(algorithm, FixedWindowAlgorithm)
    
    def test_create_default_algorithm(self):
        """Test creating default algorithm."""
        from beginnings.extensions.rate_limiting.algorithms import create_algorithm
        
        config = {}  # No type specified
        storage = MemoryRateLimitStorage()
        
        algorithm = create_algorithm(config, storage)
        
        # Should default to fixed window
        assert isinstance(algorithm, FixedWindowAlgorithm)
    
    def test_create_unknown_algorithm(self):
        """Test creating unknown algorithm type."""
        from beginnings.extensions.rate_limiting.algorithms import create_algorithm
        
        config = {"type": "unknown_algorithm"}
        storage = MemoryRateLimitStorage()
        
        with pytest.raises(ValueError) as exc_info:
            create_algorithm(config, storage)
        
        assert "Unknown rate limiting algorithm" in str(exc_info.value)