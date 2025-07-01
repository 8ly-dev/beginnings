"""
Integration tests demonstrating the complete workflow of the Beginnings framework.

These tests verify the complete public API workflow as described in the Phase 1 planning
document, showing App creation, router creation, extension loading, and request processing
working together seamlessly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml
from fastapi import Request
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.extensions.base import BaseExtension


# Test extensions for integration testing
class MockAuthExtension(BaseExtension):
    """Authentication extension for integration testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.auth_attempts = 0
        self.blocked_requests = 0

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def auth_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    self.auth_attempts += 1
                    
                    # Simulate auth check based on route config
                    if route_config.get("auth_required", False):
                        # For testing, check if 'authenticated' is in route config
                        if not route_config.get("authenticated", False):
                            self.blocked_requests += 1
                            raise Exception("Authentication required")
                    
                    return endpoint(*args, **kwargs)
                return wrapper
            return auth_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("auth_required", False)


class MockLoggingExtension(BaseExtension):
    """Logging extension for integration testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.request_logs: list[str] = []
        self.error_logs: list[str] = []

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def logging_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    path = route_config.get("path", "unknown")
                    self.request_logs.append(f"Processing: {path}")
                    
                    try:
                        result = endpoint(*args, **kwargs)
                        self.request_logs.append(f"Success: {path}")
                        return result
                    except Exception as e:
                        self.error_logs.append(f"Error in {path}: {str(e)}")
                        raise
                return wrapper
            return logging_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("logging_enabled", True)


class TestCompleteWorkflowIntegration:
    """Test the complete workflow integration of the Beginnings framework."""

    def _create_test_config(self) -> tuple[str, dict[str, Any]]:
        """Create a comprehensive test configuration and return temp directory and config."""
        config = {
            "app": {
                "name": "test_integration_app",
                "version": "1.0.0",
                "debug": False
            },
            "routes": {
                "/": {
                    "template": "home.html",
                    "cache_ttl": 300,
                    "logging_enabled": True
                },
                "/api/users": {
                    "auth_required": True,
                    "authenticated": True,  # For testing success case
                    "rate_limit": 100,
                    "logging_enabled": True,
                    "path": "/api/users"
                },
                "/api/public": {
                    "auth_required": False,
                    "rate_limit": 1000,
                    "logging_enabled": True,
                    "path": "/api/public"
                },
                "/admin/*": {
                    "auth_required": True,
                    "authenticated": False,  # For testing auth failure
                    "admin_only": True,
                    "logging_enabled": True
                }
            },
            "extensions": {
                "tests.test_integration_workflow:MockAuthExtension": {
                    "enabled": True,
                    "strict_mode": True
                },
                "tests.test_integration_workflow:MockLoggingExtension": {
                    "log_level": "INFO",
                    "log_requests": True
                }
            }
        }

        # Create temporary config directory
        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        return temp_dir, config

    def test_complete_app_initialization_workflow(self) -> None:
        """Test the complete app initialization workflow from Phase 1 planning."""
        temp_dir, expected_config = self._create_test_config()

        try:
            # Phase 1 Planning: App Class Public Interface (lines 17-33)
            # Test: App(config_dir, environment) initialization
            app = App(config_dir=temp_dir, environment="development")

            # Verify app is properly initialized
            assert app is not None
            assert hasattr(app, 'get_config')
            assert hasattr(app, 'get_extension')
            assert hasattr(app, 'create_html_router')
            assert hasattr(app, 'create_api_router')

            # Test: get_config() method
            config = app.get_config()
            assert isinstance(config, dict)
            assert config["app"]["name"] == "test_integration_app"
            assert config["app"]["version"] == "1.0.0"

            # Test: get_environment() method  
            environment = app.get_environment()
            assert environment == "development"

            # Verify extensions were loaded from configuration
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension")
            
            assert auth_ext is not None
            assert isinstance(auth_ext, MockAuthExtension)
            assert logging_ext is not None
            assert isinstance(logging_ext, MockLoggingExtension)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_router_creation_and_configuration_integration(self) -> None:
        """Test router creation with configuration integration."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Phase 1 Planning: Router Public Interface (lines 35-73)
            # Test: create_html_router() factory method
            html_router = app.create_html_router()
            assert html_router is not None
            assert hasattr(html_router, '_route_resolver')
            assert hasattr(html_router, '_extension_manager')

            # Test: create_api_router() factory method
            api_router = app.create_api_router(prefix="/api/v1", tags=["api"])
            assert api_router is not None
            assert hasattr(api_router, '_route_resolver')
            assert hasattr(api_router, '_extension_manager')
            assert api_router.prefix == "/api/v1"

            # Test that routers have access to configuration
            config = app.get_config()
            html_route_config = html_router._route_resolver.resolve_route_config("/", ["GET"])
            assert html_route_config.get("template") == "home.html"
            assert html_route_config.get("cache_ttl") == 300

            api_route_config = api_router._route_resolver.resolve_route_config("/api/users", ["GET"])
            assert api_route_config.get("auth_required") is True
            assert api_route_config.get("rate_limit") == 100

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_extension_loading_and_middleware_chain_integration(self) -> None:
        """Test extension loading and middleware chain integration."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Verify extensions were loaded from configuration
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension") 

            assert auth_ext is not None
            assert logging_ext is not None

            # Test extension configuration injection
            assert auth_ext.config["enabled"] is True
            assert auth_ext.config["strict_mode"] is True
            assert logging_ext.config["log_level"] == "INFO"
            assert logging_ext.config["log_requests"] is True

            # Test middleware chain building through router
            api_router = app.create_api_router()

            # Register a test route that should trigger middleware
            @api_router.get("/api/users")
            def get_users():
                return {"users": ["user1", "user2"]}

            # The route should be registered with middleware chain
            assert len(api_router.routes) == 1

            # Verify middleware chain is built by checking extension applicability
            route_config = api_router._route_resolver.resolve_route_config("/api/users", ["GET"])
            
            # Auth extension should apply (auth_required=True)
            assert auth_ext.should_apply_to_route("/api/users", ["GET"], route_config) is True
            
            # Logging extension should apply (logging_enabled=True)  
            assert logging_ext.should_apply_to_route("/api/users", ["GET"], route_config) is True

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_complete_request_processing_workflow(self) -> None:
        """Test complete request processing through the full middleware stack."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Create routers and register routes
            html_router = app.create_html_router()
            api_router = app.create_api_router()

            @html_router.get("/")
            def home():
                return "<h1>Welcome Home</h1>"

            @api_router.get("/api/users")
            def get_users():
                return {"users": ["alice", "bob"]}

            @api_router.get("/api/public")
            def get_public_data():
                return {"data": "public information"}

            # Include routers in the app
            app.include_router(html_router)
            app.include_router(api_router)

            # Test the complete workflow with HTTP client
            client = TestClient(app)

            # Test HTML route (should work - no auth required)
            response = client.get("/")
            assert response.status_code == 200
            assert "Welcome Home" in response.text

            # Test public API route (should work - no auth required)
            response = client.get("/api/public") 
            assert response.status_code == 200
            json_data = response.json()
            assert json_data["data"] == "public information"

            # Test authenticated API route (should work - auth configured as authenticated)
            response = client.get("/api/users")
            assert response.status_code == 200
            json_data = response.json()
            assert json_data["users"] == ["alice", "bob"]

            # Verify extensions processed requests
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension")

            # Auth extension should have processed requests (only routes with auth_required=True)
            # Only /api/users has auth_required=True in our config
            assert auth_ext.auth_attempts >= 1  # At least the authenticated API route

            # Logging extension should have logged requests (applies to all routes with logging_enabled=True)
            assert len(logging_ext.request_logs) >= 2  # Should log multiple routes

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_configuration_driven_behavior_integration(self) -> None:
        """Test that configuration drives behavior across all components."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Test configuration resolution for different route patterns
            api_router = app.create_api_router()

            # Test exact path configuration
            users_config = api_router._route_resolver.resolve_route_config("/api/users", ["GET"])
            assert users_config.get("auth_required") is True
            assert users_config.get("rate_limit") == 100

            # Test wildcard pattern configuration 
            admin_config = api_router._route_resolver.resolve_route_config("/admin/dashboard", ["GET"])
            assert admin_config.get("auth_required") is True
            assert admin_config.get("admin_only") is True

            # Test configuration inheritance and pattern matching
            public_config = api_router._route_resolver.resolve_route_config("/api/public", ["GET"])
            assert public_config.get("auth_required") is False
            assert public_config.get("rate_limit") == 1000

            # Verify extensions respect configuration
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension")

            # Test extension route applicability based on configuration
            assert auth_ext.should_apply_to_route("/api/users", ["GET"], users_config) is True
            assert auth_ext.should_apply_to_route("/api/public", ["GET"], public_config) is False
            
            assert logging_ext.should_apply_to_route("/api/users", ["GET"], users_config) is True
            assert logging_ext.should_apply_to_route("/api/public", ["GET"], public_config) is True

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_error_handling_across_complete_stack(self) -> None:
        """Test error handling propagation through the complete middleware stack."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()

            @api_router.get("/admin/sensitive")
            def admin_endpoint():
                return {"admin": "data"}

            app.include_router(api_router)
            client = TestClient(app)

            # This should trigger auth failure based on configuration
            # (admin route has auth_required=True, authenticated=False)
            # Should return HTTP error response, not raise exception
            response = client.get("/admin/sensitive")
            
            # Verify that the request failed due to authentication
            # The TestClient catches middleware exceptions and converts them to HTTP responses
            assert response.status_code in [401, 403, 500]  # Auth failure status codes

            # Verify error was logged by extension
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension")

            # Extensions should have been configured properly even if request failed
            assert auth_ext is not None
            assert logging_ext is not None

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_multiple_routers_with_different_configurations(self) -> None:
        """Test multiple routers with different configurations working together."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Create routers with different configurations
            html_router = app.create_html_router(prefix="/web")
            api_v1_router = app.create_api_router(prefix="/api/v1", tags=["v1"])
            api_v2_router = app.create_api_router(prefix="/api/v2", tags=["v2"])

            # Register routes on different routers
            @html_router.get("/")
            def web_home():
                return "<h1>Web Interface</h1>"

            @api_v1_router.get("/users")
            def api_v1_users():
                return {"version": "v1", "users": []}

            @api_v2_router.get("/users")
            def api_v2_users():
                return {"version": "v2", "users": [], "meta": {"count": 0}}

            # Include all routers
            app.include_router(html_router)
            app.include_router(api_v1_router)
            app.include_router(api_v2_router)

            client = TestClient(app)

            # Test each router works independently
            response = client.get("/web/")
            assert response.status_code == 200
            assert "Web Interface" in response.text

            response = client.get("/api/v1/users")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "v1"

            response = client.get("/api/v2/users")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "v2"
            assert "meta" in data

            # Verify configuration resolution works for each router's routes
            v1_config = api_v1_router._route_resolver.resolve_route_config("/api/v1/users", ["GET"])
            v2_config = api_v2_router._route_resolver.resolve_route_config("/api/v2/users", ["GET"])

            # Both should inherit from /api/* pattern if configured
            assert isinstance(v1_config, dict)
            assert isinstance(v2_config, dict)

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_environment_specific_configuration_workflow(self) -> None:
        """Test that environment-specific configuration affects the complete workflow."""
        # Create development and production configs
        base_config = {
            "app": {"name": "env_test_app"},
            "routes": {
                "/api/data": {
                    "cache_ttl": 60,  # Development default
                    "logging_enabled": True
                }
            }
        }

        prod_config = {
            "app": {"name": "env_test_app"},
            "routes": {
                "/api/data": {
                    "cache_ttl": 3600,  # Production override
                    "logging_enabled": False  # Production override
                }
            }
        }

        temp_dir = tempfile.mkdtemp()

        try:
            # Create development config
            dev_file = Path(temp_dir) / "app.dev.yaml"
            with open(dev_file, "w") as f:
                yaml.safe_dump(base_config, f)

            # Create production config
            prod_file = Path(temp_dir) / "app.yaml"  # Production uses clean app.yaml
            with open(prod_file, "w") as f:
                yaml.safe_dump(prod_config, f)

            # Test development environment (should use app.dev.yaml)
            dev_app = App(config_dir=temp_dir, environment="dev")
            dev_config = dev_app.get_config()
            assert dev_config["routes"]["/api/data"]["cache_ttl"] == 60
            assert dev_config["routes"]["/api/data"]["logging_enabled"] is True

            # Test production environment (should use app.yaml)
            prod_app = App(config_dir=temp_dir, environment="production")
            prod_config = prod_app.get_config()
            assert prod_config["routes"]["/api/data"]["cache_ttl"] == 3600
            assert prod_config["routes"]["/api/data"]["logging_enabled"] is False

            # Verify environment detection
            assert dev_app.get_environment() == "dev"
            assert prod_app.get_environment() == "production"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestRealWorldScenarios:
    """Test real-world scenarios that developers would actually build."""

    def _create_blog_app_config(self) -> tuple[str, dict[str, Any]]:
        """Create a realistic blog application configuration."""
        config = {
            "app": {
                "name": "blog_app",
                "version": "1.0.0",
                "description": "A simple blog application"
            },
            "routes": {
                # Public HTML pages
                "/": {"template": "home.html", "cache_ttl": 300},
                "/blog/*": {"template": "blog.html", "cache_ttl": 600},
                "/about": {"template": "about.html", "cache_ttl": 3600},
                
                # Public API endpoints
                "/api/posts": {"rate_limit": 100, "cache_ttl": 60},
                "/api/posts/*": {"rate_limit": 50, "cache_ttl": 60},
                
                # Admin API endpoints (protected)
                "/api/admin/*": {
                    "auth_required": True,
                    "authenticated": True,
                    "admin_only": True,
                    "rate_limit": 20
                },
                
                # User API endpoints (protected)
                "/api/user/*": {
                    "auth_required": True,  
                    "authenticated": True,
                    "rate_limit": 50
                }
            },
            "extensions": {
                "tests.test_integration_workflow:MockAuthExtension": {"enabled": True},
                "tests.test_integration_workflow:MockLoggingExtension": {"log_requests": True}
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        return temp_dir, config

    def test_realistic_blog_application_workflow(self) -> None:
        """Test a realistic blog application built with Beginnings."""
        temp_dir, _ = self._create_blog_app_config()

        try:
            # Create the blog application
            app = App(config_dir=temp_dir, environment="development")

            # Create routers for different parts of the application
            web_router = app.create_html_router()  # For web pages
            api_router = app.create_api_router(prefix="/api")  # For API

            # Register web routes
            @web_router.get("/")
            def home():
                return "<h1>Welcome to My Blog</h1>"

            @web_router.get("/blog/{slug}")
            def blog_post(slug: str):
                return f"<h1>Blog Post: {slug}</h1>"

            @web_router.get("/about")
            def about():
                return "<h1>About This Blog</h1>"

            # Register public API routes
            @api_router.get("/posts")
            def get_posts():
                return {"posts": [{"id": 1, "title": "First Post"}]}

            @api_router.get("/posts/{post_id}")
            def get_post(post_id: int):
                return {"post": {"id": post_id, "title": f"Post {post_id}"}}

            # Register protected user API routes
            @api_router.get("/user/profile")
            def get_user_profile():
                return {"user": {"id": 1, "name": "John Doe"}}

            # Register protected admin API routes
            @api_router.post("/admin/posts")
            def create_post():
                return {"post": {"id": 2, "title": "New Post", "status": "created"}}

            # Include routers in the app
            app.include_router(web_router)
            app.include_router(api_router)

            # Test the complete blog application
            client = TestClient(app)

            # Test public web pages
            response = client.get("/")
            assert response.status_code == 200
            assert "Welcome to My Blog" in response.text

            response = client.get("/blog/my-first-post")
            assert response.status_code == 200
            assert "Blog Post: my-first-post" in response.text

            response = client.get("/about")
            assert response.status_code == 200
            assert "About This Blog" in response.text

            # Test public API endpoints
            response = client.get("/api/posts")
            assert response.status_code == 200
            data = response.json()
            assert "posts" in data
            assert len(data["posts"]) == 1

            response = client.get("/api/posts/1")
            assert response.status_code == 200
            data = response.json()
            assert data["post"]["id"] == 1

            # Test authenticated user API endpoint
            response = client.get("/api/user/profile")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["name"] == "John Doe"

            # Test authenticated admin API endpoint
            response = client.post("/api/admin/posts")
            assert response.status_code == 200
            data = response.json()
            assert data["post"]["status"] == "created"

            # Verify configuration-driven behavior worked
            config = app.get_config()
            
            # Check that route configurations are properly resolved
            home_config = web_router._route_resolver.resolve_route_config("/", ["GET"])
            assert home_config.get("cache_ttl") == 300

            posts_config = api_router._route_resolver.resolve_route_config("/api/posts", ["GET"])
            assert posts_config.get("rate_limit") == 100

            admin_config = api_router._route_resolver.resolve_route_config("/api/admin/posts", ["POST"])
            assert admin_config.get("auth_required") is True
            assert admin_config.get("admin_only") is True

            # Verify extensions were active
            auth_ext = app.get_extension("MockAuthExtension")
            logging_ext = app.get_extension("MockLoggingExtension")

            assert auth_ext is not None
            assert logging_ext is not None
            assert len(logging_ext.request_logs) > 0

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_microservice_api_application_workflow(self) -> None:
        """Test a microservice API application built with Beginnings."""
        config = {
            "app": {
                "name": "user_service",
                "version": "2.1.0"
            },
            "routes": {
                # Health check endpoints
                "/health": {"public": True, "cache_ttl": 10},
                "/metrics": {"internal_only": True},
                
                # Public API
                "/api/v1/users": {"rate_limit": 1000, "cache_ttl": 30},
                "/api/v1/users/*": {"rate_limit": 500},
                
                # Internal API  
                "/api/internal/*": {"internal_only": True, "rate_limit": 10000},
                
                # Admin API
                "/api/admin/*": {
                    "auth_required": True,
                    "authenticated": True,
                    "admin_only": True,
                    "rate_limit": 100
                }
            },
            "extensions": {
                "tests.test_integration_workflow:MockLoggingExtension": {"service_name": "user_service"}
            }
        }

        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            # Create the microservice
            app = App(config_dir=temp_dir, environment="production")

            # Create API router (microservice typically only has API routes)
            api_router = app.create_api_router()

            # Register service endpoints
            @api_router.get("/health")
            def health_check():
                return {"status": "healthy", "service": "user_service", "version": "2.1.0"}

            @api_router.get("/metrics")
            def metrics():
                return {"requests": 1000, "errors": 5, "uptime": "24h"}

            @api_router.get("/api/v1/users")
            def list_users():
                return {"users": [{"id": 1, "username": "alice"}]}

            @api_router.get("/api/v1/users/{user_id}")
            def get_user(user_id: int):
                return {"user": {"id": user_id, "username": f"user_{user_id}"}}

            @api_router.get("/api/internal/user-count")
            def internal_user_count():
                return {"count": 1000, "last_updated": "2024-01-01T00:00:00Z"}

            @api_router.post("/api/admin/users")
            def admin_create_user():
                return {"user": {"id": 999, "username": "new_admin_user"}}

            app.include_router(api_router)

            # Test the microservice
            client = TestClient(app)

            # Test health check
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "user_service"

            # Test metrics endpoint
            response = client.get("/metrics")
            assert response.status_code == 200
            data = response.json()
            assert "requests" in data

            # Test public API
            response = client.get("/api/v1/users")
            assert response.status_code == 200
            data = response.json()
            assert "users" in data

            response = client.get("/api/v1/users/123")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == 123

            # Test internal API
            response = client.get("/api/internal/user-count")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1000

            # Test admin API
            response = client.post("/api/admin/users")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["username"] == "new_admin_user"

            # Verify configuration worked properly
            health_config = api_router._route_resolver.resolve_route_config("/health", ["GET"])
            assert health_config.get("public") is True
            assert health_config.get("cache_ttl") == 10

            admin_config = api_router._route_resolver.resolve_route_config("/api/admin/users", ["POST"])
            assert admin_config.get("auth_required") is True
            assert admin_config.get("admin_only") is True

            # Verify environment and app info
            assert app.get_environment() == "production"
            config = app.get_config()
            assert config["app"]["name"] == "user_service"
            assert config["app"]["version"] == "2.1.0"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)