"""
End-to-end HTTP request tests for the Beginnings framework.

These tests demonstrate actual HTTP requests being processed through the complete
middleware stack, including configuration resolution, extension middleware, and
response handling.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml
from fastapi import HTTPException, Request, Response
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.extensions.base import BaseExtension


# Advanced test extensions for E2E testing
class RateLimitExtension(BaseExtension):
    """Rate limiting extension for E2E testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.request_counts: dict[str, int] = {}
        self.last_reset = time.time()
        self.window_size = config.get("window_size", 60)  # 1 minute window
    
    def reset_counts(self) -> None:
        """Reset rate limit counts for testing."""
        self.request_counts.clear()
        self.last_reset = time.time()

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def rate_limit_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    # Reset counts if window expired
                    current_time = time.time()
                    if current_time - self.last_reset > self.window_size:
                        self.request_counts.clear()
                        self.last_reset = current_time

                    # Get client identifier per endpoint (simplified for testing)
                    client_id = f"test_client_{endpoint.__name__}"

                    # Check rate limit
                    limit = route_config.get("rate_limit", 1000)
                    current_count = self.request_counts.get(client_id, 0)
                    
                    # Increment count first
                    new_count = current_count + 1
                    
                    if new_count > limit:
                        raise HTTPException(status_code=429, detail="Rate limit exceeded")

                    # Store the new count
                    self.request_counts[client_id] = new_count

                    return endpoint(*args, **kwargs)
                return wrapper
            return rate_limit_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return "rate_limit" in route_config


class CacheExtension(BaseExtension):
    """Caching extension for E2E testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.cache: dict[str, tuple[Any, float]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def cache_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    cache_ttl = route_config.get("cache_ttl", 0)
                    if cache_ttl <= 0:
                        return endpoint(*args, **kwargs)

                    # Create cache key (simplified)
                    cache_key = f"{endpoint.__name__}:{hash(str(args) + str(kwargs))}"
                    current_time = time.time()

                    # Check cache
                    if cache_key in self.cache:
                        cached_result, cached_time = self.cache[cache_key]
                        if current_time - cached_time < cache_ttl:
                            self.cache_hits += 1
                            return cached_result

                    # Cache miss - execute endpoint
                    self.cache_misses += 1
                    result = endpoint(*args, **kwargs)

                    # Store in cache
                    self.cache[cache_key] = (result, current_time)
                    return result
                return wrapper
            return cache_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("cache_ttl", 0) > 0


class SecurityHeadersExtension(BaseExtension):
    """Security headers extension for E2E testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.headers_applied = 0

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def security_headers_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    result = endpoint(*args, **kwargs)
                    
                    # If result is a Response object, add security headers
                    if isinstance(result, Response):
                        if route_config.get("security_headers", True):
                            result.headers["X-Frame-Options"] = "DENY"
                            result.headers["X-Content-Type-Options"] = "nosniff"
                            result.headers["X-XSS-Protection"] = "1; mode=block"
                            self.headers_applied += 1
                    
                    return result
                return wrapper
            return security_headers_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("security_headers", False)


class TestEndToEndHTTPRequests:
    """Test end-to-end HTTP request processing through the complete stack."""

    def _create_e2e_test_config(self) -> tuple[str, dict[str, Any]]:
        """Create configuration for comprehensive E2E testing."""
        config = {
            "app": {
                "name": "e2e_test_app",
                "version": "1.0.0"
            },
            "routes": {
                # High-traffic public endpoint with caching and rate limiting
                "/api/popular": {
                    "rate_limit": 1000,
                    "cache_ttl": 60,
                    "logging_enabled": True
                },
                
                # Low-limit endpoint for rate limiting tests
                "/api/limited": {
                    "rate_limit": 2,  # Very low for testing
                    "logging_enabled": True
                },
                
                # Secure endpoint with all protections
                "/api/secure": {
                    "auth_required": True,
                    "authenticated": True,
                    "security_headers": True,
                    "rate_limit": 10,
                    "logging_enabled": True
                },
                
                # Fast endpoint with aggressive caching
                "/api/cached": {
                    "cache_ttl": 300,  # 5 minutes
                    "rate_limit": 100
                },
                
                # Admin endpoint with full protection
                "/admin/*": {
                    "auth_required": True,
                    "authenticated": True,
                    "security_headers": True,
                    "rate_limit": 5,
                    "admin_only": True
                },
                
                # Default for all other API endpoints
                "/api/*": {
                    "rate_limit": 100,
                    "cache_ttl": 30
                }
            },
            "extensions": {
                "tests.test_e2e_requests:RateLimitExtension": {"window_size": 3600},  # 1 hour - don't reset during tests
                "tests.test_e2e_requests:CacheExtension": {"max_size": 1000},
                "tests.test_e2e_requests:SecurityHeadersExtension": {"strict_mode": True}
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        return temp_dir, config

    def test_http_request_through_complete_middleware_stack(self) -> None:
        """Test HTTP requests processed through the complete middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            # Register endpoints with different middleware requirements
            @api_router.get("/api/popular")
            def popular_endpoint():
                return {"data": "popular content", "timestamp": time.time()}

            @api_router.get("/api/limited") 
            def limited_endpoint():
                return {"message": "rate limited endpoint"}

            @api_router.get("/api/secure")
            def secure_endpoint():
                return {"secure": "data", "user": "authenticated"}

            @api_router.get("/api/cached")
            def cached_endpoint():
                return {"cached": "content", "generated_at": time.time()}

            @api_router.get("/admin/dashboard")
            def admin_dashboard():
                return {"admin": "dashboard", "stats": {"users": 100}}

            app.include_router(api_router)
            client = TestClient(app)

            # Test popular endpoint (rate limiting + caching + logging)
            response = client.get("/api/popular")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert data["data"] == "popular content"

            # Test rate limited endpoint (limit is 2)
            response1 = client.get("/api/limited")
            assert response1.status_code == 200

            response2 = client.get("/api/limited")
            assert response2.status_code == 200

            # Third request should be rate limited (limit is 2)
            response3 = client.get("/api/limited")
            assert response3.status_code == 429  # Rate limit exceeded

            # Test secure endpoint (auth + security headers + rate limiting)
            response = client.get("/api/secure")
            assert response.status_code == 200
            data = response.json()
            assert data["secure"] == "data"

            # Test cached endpoint
            response1 = client.get("/api/cached")
            assert response1.status_code == 200
            data1 = response1.json()

            # Second request should be served from cache
            response2 = client.get("/api/cached")
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should be identical due to caching
            assert data1 == data2

            # Test admin endpoint (full protection stack)
            response = client.get("/admin/dashboard")
            assert response.status_code == 200
            data = response.json()
            assert data["admin"] == "dashboard"

            # Verify extensions were active
            rate_limiter = app.get_extension("RateLimitExtension")
            cache_ext = app.get_extension("CacheExtension")
            security_ext = app.get_extension("SecurityHeadersExtension")

            assert rate_limiter is not None
            assert cache_ext is not None
            assert security_ext is not None

            # Verify rate limiting worked
            assert len(rate_limiter.request_counts) > 0

            # Verify caching worked
            assert cache_ext.cache_hits >= 1

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_middleware_execution_order_and_composition(self) -> None:
        """Test that middleware executes in the correct order with proper composition."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            # Create an endpoint that will trigger multiple middleware
            @api_router.get("/api/secure")
            def multi_middleware_endpoint():
                return {"processed": True, "middleware_chain": "complete"}

            app.include_router(api_router)
            client = TestClient(app)

            # Make request that should trigger all middleware
            response = client.get("/api/secure")
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] is True

            # Verify all extensions processed the request
            rate_limiter = app.get_extension("RateLimitExtension")
            cache_ext = app.get_extension("CacheExtension") 
            security_ext = app.get_extension("SecurityHeadersExtension")

            # All extensions should have been involved
            assert rate_limiter is not None
            assert cache_ext is not None
            assert security_ext is not None

            # Verify middleware chain was built and executed
            secure_config = api_router._route_resolver.resolve_route_config("/api/secure", ["GET"])
            
            # Check that each extension would apply to this route
            assert rate_limiter.should_apply_to_route("/api/secure", ["GET"], secure_config)
            # Cache extension now applies (cache_ttl from wildcard pattern /api/*)
            assert cache_ext.should_apply_to_route("/api/secure", ["GET"], secure_config)
            assert security_ext.should_apply_to_route("/api/secure", ["GET"], secure_config)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_error_handling_through_middleware_stack(self) -> None:
        """Test error handling propagation through the middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            @api_router.get("/api/error")
            def error_endpoint():
                raise HTTPException(status_code=500, detail="Internal server error")

            @api_router.get("/api/not-found")
            def not_found_endpoint():
                raise HTTPException(status_code=404, detail="Resource not found")

            app.include_router(api_router)
            client = TestClient(app)

            # Test 500 error handling
            response = client.get("/api/error")
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]

            # Test 404 error handling
            response = client.get("/api/not-found")
            assert response.status_code == 404
            data = response.json()
            assert "Resource not found" in data["detail"]

            # Test non-existent route
            response = client.get("/api/does-not-exist")
            assert response.status_code == 404

            # Verify extensions handled errors gracefully
            rate_limiter = app.get_extension("RateLimitExtension")
            assert rate_limiter is not None
            # Even with errors, rate limiting should still track requests

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_different_http_methods_through_stack(self) -> None:
        """Test different HTTP methods processed through the middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            # Register endpoints for different HTTP methods
            @api_router.get("/api/resource")
            def get_resource():
                return {"method": "GET", "resource": "data"}

            @api_router.post("/api/resource")
            def create_resource():
                return {"method": "POST", "created": True}

            @api_router.put("/api/resource/{resource_id}")
            def update_resource(resource_id: int):
                return {"method": "PUT", "updated": resource_id}

            @api_router.delete("/api/resource/{resource_id}")
            def delete_resource(resource_id: int):
                return {"method": "DELETE", "deleted": resource_id}

            @api_router.patch("/api/resource/{resource_id}")
            def patch_resource(resource_id: int):
                return {"method": "PATCH", "patched": resource_id}

            app.include_router(api_router)
            client = TestClient(app)

            # Test all HTTP methods
            response = client.get("/api/resource")
            assert response.status_code == 200
            assert response.json()["method"] == "GET"

            response = client.post("/api/resource")
            assert response.status_code == 200
            assert response.json()["method"] == "POST"

            response = client.put("/api/resource/123")
            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "PUT"
            assert data["updated"] == 123

            response = client.delete("/api/resource/456")
            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "DELETE"
            assert data["deleted"] == 456

            response = client.patch("/api/resource/789")
            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "PATCH"
            assert data["patched"] == 789

            # Verify middleware applied to all methods
            rate_limiter = app.get_extension("RateLimitExtension")
            assert rate_limiter is not None
            assert len(rate_limiter.request_counts) > 0

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_request_response_data_flow_through_stack(self) -> None:
        """Test request/response data flow through the middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            @api_router.post("/api/data")
            def process_data():
                # Simulate processing request data
                return {
                    "processed": True,
                    "received_data": "request_payload",
                    "response_id": "12345"
                }

            @api_router.get("/api/query")
            def query_data(q: str = "default"):
                return {
                    "query": q,
                    "results": ["item1", "item2", "item3"],
                    "total": 3
                }

            app.include_router(api_router)
            client = TestClient(app)

            # Test POST with JSON data
            response = client.post("/api/data", json={"input": "test data"})
            assert response.status_code == 200
            data = response.json()
            assert data["processed"] is True
            assert data["response_id"] == "12345"

            # Test GET with query parameters
            response = client.get("/api/query?q=search_term")
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "search_term"
            assert data["total"] == 3

            # Test headers and content types
            response = client.get("/api/query")
            assert response.headers["content-type"] == "application/json"

            # Verify extensions processed the data correctly
            cache_ext = app.get_extension("CacheExtension")
            assert cache_ext is not None
            # Cache should have recorded cache misses for non-cached endpoints

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_requests_through_stack(self) -> None:
        """Test concurrent requests processed through the middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            @api_router.get("/api/concurrent")
            def concurrent_endpoint():
                # Simulate some processing time
                time.sleep(0.01)
                return {"processed": True, "timestamp": time.time()}

            app.include_router(api_router)
            client = TestClient(app)

            import concurrent.futures
            import threading

            results = []
            errors = []

            def make_request(request_id: int) -> dict:
                try:
                    response = client.get(f"/api/concurrent")
                    if response.status_code == 200:
                        data = response.json()
                        data["request_id"] = request_id
                        return data
                    else:
                        return {"error": f"HTTP {response.status_code}", "request_id": request_id}
                except Exception as e:
                    return {"error": str(e), "request_id": request_id}

            # Make concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(20)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if "error" not in result:
                            results.append(result)
                        else:
                            errors.append(result)
                    except Exception as e:
                        errors.append({"error": str(e)})

            # Verify concurrent processing worked
            assert len(results) > 0, f"No successful results. Errors: {errors}"
            
            # Verify all successful requests got processed
            successful_ids = {r["request_id"] for r in results}
            assert len(successful_ids) >= 10  # At least half should succeed

            # Verify middleware handled concurrent requests properly
            rate_limiter = app.get_extension("RateLimitExtension")
            assert rate_limiter is not None
            
            # Should have tracked requests from concurrent execution
            total_requests = sum(rate_limiter.request_counts.values())
            assert total_requests >= len(results)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_large_response_handling_through_stack(self) -> None:
        """Test handling of large responses through the middleware stack."""
        temp_dir, _ = self._create_e2e_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            @api_router.get("/api/large")
            def large_response():
                # Generate a large response
                large_data = {
                    "items": [{"id": i, "data": f"item_{i}" * 100} for i in range(1000)],
                    "metadata": {
                        "total": 1000,
                        "generated_at": time.time(),
                        "description": "Large dataset for testing" * 50
                    }
                }
                return large_data

            app.include_router(api_router)
            client = TestClient(app)

            # Test large response handling
            response = client.get("/api/large")
            assert response.status_code == 200
            
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1000
            assert data["metadata"]["total"] == 1000

            # Verify middleware handled large response properly
            cache_ext = app.get_extension("CacheExtension")
            rate_limiter = app.get_extension("RateLimitExtension")
            
            assert cache_ext is not None
            assert rate_limiter is not None
            
            # Extensions should still function with large responses
            assert len(rate_limiter.request_counts) > 0

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestComplexScenarioE2E:
    """Test complex real-world scenarios end-to-end."""

    def test_api_with_authentication_flow_e2e(self) -> None:
        """Test a complete API with authentication flow end-to-end."""
        config = {
            "app": {"name": "auth_api", "version": "1.0.0"},
            "routes": {
                "/auth/login": {"rate_limit": 10, "security_headers": True},
                "/auth/logout": {"rate_limit": 5, "security_headers": True},
                "/api/profile": {
                    "auth_required": True,
                    "authenticated": True,
                    "rate_limit": 100,
                    "cache_ttl": 60
                },
                "/api/admin/*": {
                    "auth_required": True,
                    "authenticated": True,
                    "admin_only": True,
                    "rate_limit": 10,
                    "security_headers": True
                }
            },
            "extensions": {
                "tests.test_e2e_requests:RateLimitExtension": {"window_size": 60},
                "tests.test_e2e_requests:CacheExtension": {"max_size": 100},
                "tests.test_e2e_requests:SecurityHeadersExtension": {"strict_mode": True}
            }
        }

        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            app = App(config_dir=temp_dir, environment="production")
            api_router = app.create_api_router()

            # Authentication endpoints
            @api_router.post("/auth/login")
            def login():
                return {"token": "jwt_token_123", "expires_in": 3600}

            @api_router.post("/auth/logout")
            def logout():
                return {"message": "Logged out successfully"}

            # Protected user endpoints
            @api_router.get("/api/profile")
            def get_profile():
                return {
                    "user": {"id": 1, "username": "testuser", "email": "test@example.com"},
                    "preferences": {"theme": "dark", "notifications": True}
                }

            # Protected admin endpoints  
            @api_router.get("/api/admin/users")
            def admin_list_users():
                return {"users": [{"id": 1, "username": "user1"}, {"id": 2, "username": "user2"}]}

            @api_router.post("/api/admin/users")
            def admin_create_user():
                return {"user": {"id": 3, "username": "newuser"}, "created": True}

            app.include_router(api_router)
            client = TestClient(app)

            # Test authentication flow
            login_response = client.post("/auth/login")
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "token" in login_data
            assert login_data["expires_in"] == 3600

            # Test user profile access (protected)
            profile_response = client.get("/api/profile")
            assert profile_response.status_code == 200
            profile_data = profile_response.json()
            assert profile_data["user"]["username"] == "testuser"

            # Test cached profile access (should hit cache)
            profile_response2 = client.get("/api/profile")
            assert profile_response2.status_code == 200
            # Should be identical due to caching
            assert profile_response2.json() == profile_data

            # Test admin endpoints
            admin_users_response = client.get("/api/admin/users")
            assert admin_users_response.status_code == 200
            admin_data = admin_users_response.json()
            assert len(admin_data["users"]) == 2

            admin_create_response = client.post("/api/admin/users")
            assert admin_create_response.status_code == 200
            create_data = admin_create_response.json()
            assert create_data["created"] is True

            # Test logout
            logout_response = client.post("/auth/logout")
            assert logout_response.status_code == 200
            assert logout_response.json()["message"] == "Logged out successfully"

            # Verify all middleware was active
            rate_limiter = app.get_extension("RateLimitExtension")
            cache_ext = app.get_extension("CacheExtension")
            security_ext = app.get_extension("SecurityHeadersExtension")

            assert all([rate_limiter, cache_ext, security_ext])
            assert len(rate_limiter.request_counts) > 0
            assert cache_ext.cache_hits >= 1  # Profile should have been cached

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mixed_html_api_application_e2e(self) -> None:
        """Test a mixed HTML and API application end-to-end."""
        config = {
            "app": {"name": "mixed_app", "version": "1.0.0"},
            "routes": {
                # HTML routes  
                "/": {"cache_ttl": 300, "security_headers": True},
                "/dashboard": {
                    "auth_required": True, 
                    "authenticated": True,
                    "cache_ttl": 60,
                    "security_headers": True
                },
                
                # API routes (router adds /api prefix, so config should match actual paths)
                "/api/data": {"rate_limit": 1000, "cache_ttl": 120},
                "/api/user/*": {
                    "auth_required": True,
                    "authenticated": True, 
                    "rate_limit": 100
                }
            },
            "extensions": {
                "tests.test_e2e_requests:RateLimitExtension": {},
                "tests.test_e2e_requests:CacheExtension": {},
                "tests.test_e2e_requests:SecurityHeadersExtension": {}
            }
        }

        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            app = App(config_dir=temp_dir, environment="development")
            
            # Create separate routers for HTML and API
            html_router = app.create_html_router()
            api_router = app.create_api_router(prefix="/api")

            # HTML routes
            @html_router.get("/")
            def home():
                return "<html><body><h1>Welcome Home</h1></body></html>"

            @html_router.get("/dashboard")
            def dashboard():
                return "<html><body><h1>User Dashboard</h1><p>Welcome back!</p></body></html>"

            # API routes
            @api_router.get("/data")
            def get_api_data():
                return {"data": [1, 2, 3, 4, 5], "timestamp": time.time()}

            @api_router.get("/user/profile")
            def get_user_api_profile():
                return {"user": {"id": 1, "name": "API User"}}

            @api_router.post("/user/update")
            def update_user_api():
                return {"updated": True, "timestamp": time.time()}

            # Include both routers
            app.include_router(html_router)
            app.include_router(api_router)

            client = TestClient(app)

            # Test HTML routes
            html_response = client.get("/")
            assert html_response.status_code == 200
            assert "Welcome Home" in html_response.text
            assert html_response.headers["content-type"] == "text/html; charset=utf-8"

            dashboard_response = client.get("/dashboard")
            assert dashboard_response.status_code == 200
            assert "User Dashboard" in dashboard_response.text

            # Test API routes
            data_response = client.get("/api/data")
            assert data_response.status_code == 200
            data_json = data_response.json()
            assert data_json["data"] == [1, 2, 3, 4, 5]
            assert data_response.headers["content-type"] == "application/json"

            profile_response = client.get("/api/user/profile")
            assert profile_response.status_code == 200
            profile_json = profile_response.json()
            assert profile_json["user"]["name"] == "API User"

            update_response = client.post("/api/user/update")
            assert update_response.status_code == 200
            update_json = update_response.json()
            assert update_json["updated"] is True

            # Verify middleware worked for both types of routes
            rate_limiter = app.get_extension("RateLimitExtension")
            cache_ext = app.get_extension("CacheExtension")
            security_ext = app.get_extension("SecurityHeadersExtension")

            assert all([rate_limiter, cache_ext, security_ext])
            
            # Should have processed requests from both HTML and API routes
            assert len(rate_limiter.request_counts) > 0
            
            # Cache should have been used for routes with cache_ttl
            assert len(cache_ext.cache) > 0

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)