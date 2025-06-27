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
from beginnings.extensions.rate_limiting.algorithms import create_algorithm, RateLimitAlgorithm
from beginnings.extensions.rate_limiting.storage import create_storage, RateLimitStorage
from beginnings.extensions.rate_limiting.trusted_proxies import TrustedProxyManager
from beginnings.monitoring import get_structured_logger, get_metrics_collector, SecurityEvent, PerformanceEvent


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
        
        # Storage backend configuration and initialization
        storage_config = config.get("storage", {})
        self._storage = create_storage(storage_config)
        
        # Algorithm configuration
        algorithm_config = config.get("algorithms", {})
        self.default_algorithm_type = config.get("global", {}).get("algorithm", "fixed_window")
        
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
        
        # Algorithm instances cache (for performance)
        self._algorithm_cache: dict[str, RateLimitAlgorithm] = {}
        self._algorithm_configs = algorithm_config
        
        # Configuration cache for performance (parsed route configs)
        self._route_config_cache: dict[str, dict[str, Any]] = {}
        
        # Trusted proxy manager for IP validation
        proxy_config = config.get("trusted_proxies", {"enabled": True})
        self.proxy_manager = TrustedProxyManager(proxy_config)
        
        # Monitoring and observability
        self.logger = get_structured_logger()
        self.metrics = get_metrics_collector()
        
        # Log extension startup
        self.logger.log_extension_startup("rate_limiting", config)
    
    async def get_shutdown_handler(self) -> Callable[[], None] | None:
        """Get shutdown handler for cleanup."""
        async def shutdown():
            # Close storage connections if needed
            if hasattr(self._storage, 'close'):
                await self._storage.close()
        
        return shutdown
    
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for rate limiting.
        
        Returns:
            Middleware factory function
        """
        def create_middleware(route_config: dict[str, Any]) -> Callable[..., Any]:
            # Cache the parsed configuration for this route to avoid re-parsing
            route_path = route_config.get("path", "unknown")
            cached_config = self._get_cached_route_config(route_path, route_config)
            
            async def rate_limit_middleware(request: Request, call_next: Callable[..., Any]) -> Any:
                # Use cached configuration
                rate_limit_config = cached_config
                
                # Skip if rate limiting is disabled
                if not rate_limit_config.get("enabled", self.global_enabled):
                    return await call_next(request)
                
                try:
                    start_time = time.time()
                    
                    # Get pre-cached rate limit parameters (no need to resolve)
                    limit = rate_limit_config["requests"]
                    window_seconds = rate_limit_config["window_seconds"]
                    identifier_type = rate_limit_config["identifier"]
                    algorithm_type = rate_limit_config["algorithm"]
                    
                    # Get identifier for rate limiting
                    identifier = await self._get_identifier(request, identifier_type)
                    
                    # Create rate limit key
                    rate_limit_key = f"rate_limit:{identifier}:{request.url.path}"
                    
                    # Get algorithm instance for this configuration
                    algorithm = self._get_algorithm(algorithm_type)
                    
                    # Check rate limit using algorithm
                    allowed, remaining, reset_time = await algorithm.is_allowed(
                        rate_limit_key, limit, window_seconds
                    )
                    
                    # Record performance metrics
                    duration_ms = (time.time() - start_time) * 1000
                    self.metrics.record_histogram("rate_limit_check_duration", duration_ms, {
                        "algorithm": algorithm_type,
                        "identifier_type": identifier_type
                    })
                    self.metrics.increment_counter("rate_limit_checks_total", 1, {
                        "algorithm": algorithm_type,
                        "allowed": str(allowed)
                    })
                    
                    # Check if limit exceeded
                    if not allowed:
                        # Log security event
                        self.logger.log_security_event(SecurityEvent(
                            event_type="rate_limited",
                            ip_address=identifier if identifier_type == "ip" else None,
                            user_id=identifier if identifier_type == "user" else None,
                            request_path=str(request.url.path),
                            details={
                                "limit": limit,
                                "algorithm": algorithm_type,
                                "reset_time": int(reset_time)
                            },
                            severity="warning"
                        ))
                        
                        return await self._handle_rate_limit_exceeded(
                            request, rate_limit_config, int(reset_time)
                        )
                    
                    # Continue to route handler
                    response = await call_next(request)
                    
                    # Add rate limit headers
                    if self.include_headers:
                        response.headers[self.limit_header] = str(limit)
                        response.headers[self.remaining_header] = str(remaining)
                        response.headers[self.reset_header] = str(int(reset_time))
                    
                    return response
                    
                except Exception as e:
                    # Log error and continue without rate limiting
                    self.logger.log_extension_error("rate_limiting", e, {
                        "request_path": str(request.url.path),
                        "identifier_type": identifier_type if 'identifier_type' in locals() else "unknown"
                    })
                    self.metrics.increment_counter("rate_limit_errors_total", 1, {
                        "error_type": type(e).__name__
                    })
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
    
    def _get_algorithm(self, algorithm_type: str) -> RateLimitAlgorithm:
        """Get or create algorithm instance for given type."""
        if algorithm_type not in self._algorithm_cache:
            # Get algorithm-specific configuration
            algo_config = self._algorithm_configs.get(algorithm_type, {})
            algo_config["type"] = algorithm_type
            
            # Create algorithm instance with storage backend
            self._algorithm_cache[algorithm_type] = create_algorithm(algo_config, self._storage)
        
        return self._algorithm_cache[algorithm_type]
    
    def _get_cached_route_config(self, route_path: str, route_config: dict[str, Any]) -> dict[str, Any]:
        """Get or create cached route configuration for performance."""
        if route_path not in self._route_config_cache:
            # Extract and merge rate limiting configuration
            base_rate_config = route_config.get("rate_limiting", {})
            
            # Apply route pattern-based defaults
            for pattern, pattern_config in self.routes_config.items():
                if self._path_matches_pattern(route_path, pattern):
                    # Merge pattern config as defaults, route config as overrides
                    merged_config = {**pattern_config, **base_rate_config}
                    self._route_config_cache[route_path] = merged_config
                    return merged_config
            
            # No pattern match, use base config with global defaults
            merged_config = {
                "enabled": base_rate_config.get("enabled", self.global_enabled),
                "requests": base_rate_config.get("requests", self.global_requests),
                "window_seconds": base_rate_config.get("window_seconds", self.global_window_seconds),
                "identifier": base_rate_config.get("identifier", self.global_identifier),
                "algorithm": base_rate_config.get("algorithm", self.default_algorithm_type),
                **base_rate_config  # Include any additional config
            }
            self._route_config_cache[route_path] = merged_config
        
        return self._route_config_cache[route_path]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request with proxy validation."""
        # Get direct connection IP
        remote_addr = "unknown"
        if hasattr(request, "client") and request.client:
            remote_addr = request.client.host
        
        # Get forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = request.headers.get("x-real-ip")
        
        # Use trusted proxy manager to extract real IP
        real_ip_address = self.proxy_manager.extract_real_ip(
            remote_addr=remote_addr,
            forwarded_for=forwarded_for,
            real_ip=real_ip
        )
        
        return f"ip:{real_ip_address}"
    
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
        
        # Validate trusted proxy configuration
        proxy_errors = self.proxy_manager.validate_config()
        for error in proxy_errors:
            errors.append(f"Rate limiting trusted proxies: {error}")
        
        return errors