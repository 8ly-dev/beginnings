"""
Rate limiting extension for Beginnings framework.

This module provides the main rate limiting extension with support for
multiple algorithms, storage backends, and identifier resolution.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from beginnings.extensions.base import BaseExtension


class RateLimitStorage:
    """Abstract interface for rate limit storage backends."""
    
    async def get_counter(self, key: str) -> tuple[int, float]:
        """Get current count and window start time for key."""
        raise NotImplementedError
    
    async def increment_counter(self, key: str, window_seconds: int) -> tuple[int, float]:
        """Increment counter and return new count with window start."""
        raise NotImplementedError
    
    async def reset_counter(self, key: str) -> None:
        """Reset counter for key."""
        raise NotImplementedError


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage for single-instance applications."""
    
    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}
    
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


class RateLimitExtension(BaseExtension):
    """
    Rate limiting extension.
    
    Provides configurable rate limiting with multiple algorithms,
    storage backends, and identifier resolution strategies.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize rate limiting extension.
        
        Args:
            config: Rate limiting configuration dictionary
        """
        super().__init__(config)
        
        # Storage backend configuration
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "memory")
        
        if storage_type == "memory":
            self._storage = MemoryRateLimitStorage()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
        
        # Global rate limiting settings
        global_config = config.get("global", {})
        self.global_enabled = global_config.get("enabled", False)
        self.global_requests = global_config.get("requests", 1000)
        self.global_window_seconds = global_config.get("window_seconds", 3600)
        self.global_identifier = global_config.get("identifier", "ip")
        
        # Route-specific configuration
        self.routes_config = config.get("routes", {})
        
        # Response headers configuration
        headers_config = config.get("headers", {})
        self.include_headers = headers_config.get("include_headers", True)
        self.remaining_header = headers_config.get("remaining_header", "X-RateLimit-Remaining")
        self.limit_header = headers_config.get("limit_header", "X-RateLimit-Limit")
        self.reset_header = headers_config.get("reset_header", "X-RateLimit-Reset")
        self.retry_after_header = headers_config.get("retry_after_header", "Retry-After")
    
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for rate limiting.
        
        Returns:
            Middleware factory function
        """
        def create_middleware(route_config: dict[str, Any]) -> Callable[..., Any]:
            async def rate_limit_middleware(request: Request, call_next: Callable[..., Any]) -> Any:
                # Extract rate limit configuration for this route
                rate_limit_config = route_config.get("rate_limiting", {})
                
                # Skip if rate limiting is disabled
                if not rate_limit_config.get("enabled", self.global_enabled):
                    return await call_next(request)
                
                try:
                    # Resolve rate limit parameters
                    limit = rate_limit_config.get("requests", self.global_requests)
                    window_seconds = rate_limit_config.get("window_seconds", self.global_window_seconds)
                    identifier_type = rate_limit_config.get("identifier", self.global_identifier)
                    
                    # Get identifier for rate limiting
                    identifier = await self._get_identifier(request, identifier_type)
                    
                    # Create rate limit key
                    rate_limit_key = f"rate_limit:{identifier}:{request.url.path}"
                    
                    # Check and update rate limit
                    count, window_start = await self._storage.increment_counter(
                        rate_limit_key, window_seconds
                    )
                    
                    # Calculate remaining and reset time
                    remaining = max(0, limit - count)
                    reset_time = int(window_start + window_seconds)
                    
                    # Check if limit exceeded
                    if count > limit:
                        return await self._handle_rate_limit_exceeded(
                            request, rate_limit_config, reset_time
                        )
                    
                    # Continue to route handler
                    response = await call_next(request)
                    
                    # Add rate limit headers
                    if self.include_headers:
                        response.headers[self.limit_header] = str(limit)
                        response.headers[self.remaining_header] = str(remaining)
                        response.headers[self.reset_header] = str(reset_time)
                    
                    return response
                    
                except Exception as e:
                    # Log error in production, continue without rate limiting
                    return await call_next(request)
            
            return rate_limit_middleware
        
        return create_middleware
    
    def should_apply_to_route(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> bool:
        """
        Determine if rate limiting should apply to a route.
        
        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Returns:
            True if rate limiting should apply
        """
        # Check if route has explicit rate limiting configuration
        rate_limit_config = route_config.get("rate_limiting", {})
        if rate_limit_config:
            return rate_limit_config.get("enabled", True)
        
        # Check if route matches any configured route patterns
        for pattern, pattern_config in self.routes_config.items():
            if self._path_matches_pattern(path, pattern):
                return pattern_config.get("enabled", True)
        
        # Apply global rate limiting if enabled
        return self.global_enabled
    
    async def _get_identifier(self, request: Request, identifier_type: str) -> str:
        """Get rate limiting identifier from request."""
        if identifier_type == "ip":
            return self._get_client_ip(request)
        elif identifier_type == "user":
            # Try to get user ID from auth extension
            if hasattr(request.state, "user") and request.state.user:
                return f"user:{request.state.user.user_id}"
            else:
                # Fall back to IP if no user
                return self._get_client_ip(request)
        elif identifier_type == "api_key":
            # Look for API key in headers
            api_key = request.headers.get("x-api-key") or request.headers.get("authorization")
            if api_key:
                return f"api_key:{api_key}"
            else:
                # Fall back to IP if no API key
                return self._get_client_ip(request)
        else:
            # Default to IP
            return self._get_client_ip(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return f"ip:{real_ip}"
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return f"ip:{request.client.host}"
        
        return "ip:unknown"
    
    async def _handle_rate_limit_exceeded(
        self,
        request: Request,
        rate_limit_config: dict[str, Any],
        reset_time: int
    ) -> Response:
        """Handle rate limit exceeded scenarios."""
        retry_after = reset_time - int(time.time())
        
        # Check if this is an API request
        if self._is_api_request(request):
            error_response = rate_limit_config.get(
                "error_json",
                {
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after
                }
            )
            
            response = JSONResponse(
                status_code=429,
                content=error_response
            )
        else:
            # For HTML requests, raise HTTP exception
            error_message = rate_limit_config.get(
                "error_message",
                "Rate limit exceeded. Please try again later."
            )
            
            raise HTTPException(
                status_code=429,
                detail=error_message
            )
        
        # Add retry-after header
        if hasattr(response, 'headers'):
            response.headers[self.retry_after_header] = str(retry_after)
        
        return response
    
    def _is_api_request(self, request: Request) -> bool:
        """Determine if request expects JSON response."""
        # Check Accept header
        accept_header = request.headers.get("accept", "").lower()
        if "application/json" in accept_header:
            return True
        
        # Check if path starts with /api
        if request.url.path.startswith("/api"):
            return True
        
        return False
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern (simple wildcard matching)."""
        if pattern == path:
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)
        
        return False
    
    def validate_config(self) -> list[str]:
        """
        Validate rate limiting extension configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate global configuration
        if self.global_enabled:
            if self.global_requests <= 0:
                errors.append("Rate limiting global requests must be positive")
            
            if self.global_window_seconds <= 0:
                errors.append("Rate limiting global window_seconds must be positive")
        
        # Validate route configurations
        for route_pattern, route_config in self.routes_config.items():
            if route_config.get("enabled", True):
                requests = route_config.get("requests", self.global_requests)
                window_seconds = route_config.get("window_seconds", self.global_window_seconds)
                
                if requests <= 0:
                    errors.append(f"Route '{route_pattern}' requests must be positive")
                
                if window_seconds <= 0:
                    errors.append(f"Route '{route_pattern}' window_seconds must be positive")
        
        return errors