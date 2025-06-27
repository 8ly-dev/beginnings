"""
Public API demonstration tests for the Beginnings framework.

These tests verify that all public APIs described in the Phase 1 planning document
work correctly and demonstrate their intended usage patterns for developers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.extensions.base import BaseExtension
from beginnings.routing.api import APIRouter
from beginnings.routing.html import HTMLRouter


# Simple test extension for public API demonstration
class DemoExtension(BaseExtension):
    """Simple extension for demonstrating public API usage."""

    def __init__(self, config: dict[str, Any]) -> None:
        # Store original config for validation testing
        self._original_config = config
        # Validate config is a dict for testing
        if not isinstance(config, dict):
            config = {}  # Use default empty dict for invalid input
        super().__init__(config)
        self.name = config.get("name", "DemoExtension")
        self.enabled = config.get("enabled", True)
        self.middleware_calls = 0

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def demo_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    self.middleware_calls += 1
                    return endpoint(*args, **kwargs)
                return wrapper
            return demo_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("demo_enabled", True)

    def validate_config(self) -> list[str]:
        errors = []
        if not isinstance(self._original_config, dict):
            errors.append("Config must be a dictionary")
        return errors


class TestAppClassPublicInterface:
    """Test the App class public interface as specified in Phase 1 planning (lines 17-33)."""

    def _create_test_config(self) -> tuple[str, dict[str, Any]]:
        """Create a test configuration for App class testing."""
        config = {
            "app": {
                "name": "public_api_test",
                "version": "1.0.0",
                "description": "Testing public API"
            },
            "routes": {
                "/": {"template": "home.html", "demo_enabled": True},
                "/api/test": {"rate_limit": 100, "demo_enabled": True}
            },
            "extensions": {
                "tests.test_public_api:DemoExtension": {"name": "PublicAPIDemo", "enabled": True}
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        return temp_dir, config

    def test_app_constructor_public_interface(self) -> None:
        """Test: App(config_dir: Optional[str] = None, environment: Optional[str] = None)"""
        temp_dir, _ = self._create_test_config()

        try:
            # Test with explicit config_dir and environment
            app1 = App(config_dir=temp_dir, environment="development")
            assert isinstance(app1, FastAPI)
            assert app1.get_environment() == "development"

            # Test with config_dir only (environment auto-detected)
            app2 = App(config_dir=temp_dir)
            assert isinstance(app2, FastAPI)
            assert app2.get_environment() in ["development", "production"]

            # Test with no arguments (should work with defaults)
            # Note: This would fail without a config, so we skip this case
            # app3 = App()

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_html_router_public_interface(self) -> None:
        """Test: def create_html_router(**router_kwargs) -> HTMLRouter"""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Test basic HTML router creation
            html_router = app.create_html_router()
            assert isinstance(html_router, HTMLRouter)
            assert html_router.default_response_class == HTMLResponse

            # Test with additional FastAPI router parameters
            html_router_with_prefix = app.create_html_router(prefix="/web", tags=["html"])
            assert isinstance(html_router_with_prefix, HTMLRouter)
            assert html_router_with_prefix.prefix == "/web"

            # Verify router has configuration integration
            assert hasattr(html_router, '_route_resolver')
            assert hasattr(html_router, '_extension_manager')

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_api_router_public_interface(self) -> None:
        """Test: def create_api_router(**router_kwargs) -> APIRouter"""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Test basic API router creation
            api_router = app.create_api_router()
            assert isinstance(api_router, APIRouter)
            assert api_router.default_response_class == JSONResponse

            # Test with additional FastAPI router parameters
            api_router_with_config = app.create_api_router(
                prefix="/api/v1", 
                tags=["api", "v1"],
                dependencies=[]
            )
            assert isinstance(api_router_with_config, APIRouter)
            assert api_router_with_config.prefix == "/api/v1"

            # Verify router has configuration integration
            assert hasattr(api_router, '_route_resolver')
            assert hasattr(api_router, '_extension_manager')

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_config_public_interface(self) -> None:
        """Test: def get_config() -> Dict[str, Any]"""
        temp_dir, expected_config = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Test get_config method
            config = app.get_config()
            
            # Verify return type and structure
            assert isinstance(config, dict)
            assert "app" in config
            assert "routes" in config
            assert "extensions" in config

            # Verify configuration content
            assert config["app"]["name"] == "public_api_test"
            assert config["app"]["version"] == "1.0.0"
            
            # Verify routes configuration
            assert "/" in config["routes"]
            assert "/api/test" in config["routes"]
            
            # Verify extensions configuration  
            assert "tests.test_public_api:DemoExtension" in config["extensions"]

            # Verify returned config is a copy (modifications don't affect internal state)
            config["app"]["name"] = "modified"
            original_config = app.get_config()
            assert original_config["app"]["name"] == "public_api_test"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_extension_public_interface(self) -> None:
        """Test: def get_extension(extension_name: str) -> Optional[BaseExtension]"""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Test getting an existing extension
            extension = app.get_extension("DemoExtension")
            assert extension is not None
            assert isinstance(extension, DemoExtension)
            assert extension.name == "PublicAPIDemo"

            # Test getting a non-existent extension
            missing_extension = app.get_extension("NonExistentExtension")
            assert missing_extension is None

            # Test with empty/invalid extension name
            empty_extension = app.get_extension("")
            assert empty_extension is None

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_app_inherits_from_fastapi(self) -> None:
        """Test that App extends FastAPI as specified in planning document."""
        temp_dir, _ = self._create_test_config()

        try:
            app = App(config_dir=temp_dir, environment="development")

            # Verify inheritance
            assert isinstance(app, FastAPI)

            # Verify FastAPI methods are available
            assert hasattr(app, 'include_router')
            assert hasattr(app, 'add_middleware')
            assert hasattr(app, 'mount')
            assert hasattr(app, 'get')
            assert hasattr(app, 'post')

            # Test that FastAPI functionality works
            @app.get("/direct")
            def direct_route():
                return {"direct": True}

            client = TestClient(app)
            response = client.get("/direct")
            assert response.status_code == 200
            assert response.json()["direct"] is True

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestHTMLRouterPublicInterface:
    """Test HTMLRouter public interface as specified in Phase 1 planning (lines 35-53)."""

    def _create_test_app(self) -> tuple[App, str]:
        """Create a test app with configuration."""
        config = {
            "app": {"name": "html_test"},
            "routes": {
                "/": {"template": "home.html", "cache_ttl": 300},
                "/users/{user_id}": {"template": "user.html", "auth_required": False}
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        app = App(config_dir=temp_dir, environment="development")
        return app, temp_dir

    def test_html_router_constructor_interface(self) -> None:
        """Test: HTMLRouter(config_loader: ConfigLoader, **fastapi_kwargs)"""
        app, temp_dir = self._create_test_app()

        try:
            # Test basic router creation through App factory method
            html_router = app.create_html_router()
            assert isinstance(html_router, HTMLRouter)

            # Test with FastAPI router parameters
            html_router_with_params = app.create_html_router(
                prefix="/html",
                tags=["html", "pages"],
                dependencies=[]
            )
            assert html_router_with_params.prefix == "/html"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_fastapi_decorators(self) -> None:
        """Test standard FastAPI decorators work on HTMLRouter."""
        app, temp_dir = self._create_test_app()

        try:
            html_router = app.create_html_router()

            # Test @router.get() decorator
            @html_router.get("/")
            def home():
                return HTMLResponse("<h1>Home Page</h1>")

            # Test @router.post() decorator (supported for HTML forms)
            @html_router.post("/submit")
            def submit_form():
                return HTMLResponse("<h1>Form Submitted</h1>")

            # Note: PUT/PATCH/DELETE decorators are not supported for HTMLRouter
            # These methods are intended for REST APIs, not form-based HTML applications
            # Use create_api_router() for REST operations that require these methods

            # Verify routes were registered (GET + POST)
            assert len(html_router.routes) == 2

            # Test with FastAPI app
            app.include_router(html_router)
            client = TestClient(app)

            # Test each route
            response = client.get("/")
            assert response.status_code == 200
            assert "Home Page" in response.text

            response = client.post("/submit")
            assert response.status_code == 200
            assert "Form Submitted" in response.text

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_default_response_class(self) -> None:
        """Test that HTMLRouter automatically applies HTMLResponse as default."""
        app, temp_dir = self._create_test_app()

        try:
            html_router = app.create_html_router()

            # Verify default response class
            assert html_router.default_response_class == HTMLResponse

            # Test that responses are HTML by default
            @html_router.get("/test")
            def test_endpoint():
                return "<h1>Test HTML</h1>"

            app.include_router(html_router)
            client = TestClient(app)

            response = client.get("/test")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
            assert response.text == "<h1>Test HTML</h1>"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_path_parameters(self) -> None:
        """Test route parameter handling and path variables."""
        app, temp_dir = self._create_test_app()

        try:
            html_router = app.create_html_router()

            @html_router.get("/users/{user_id}")
            def get_user(user_id: int):
                return HTMLResponse(f"<h1>User {user_id}</h1>")

            @html_router.get("/posts/{post_id}/comments/{comment_id}")
            def get_comment(post_id: int, comment_id: int):
                return HTMLResponse(f"<p>Post {post_id}, Comment {comment_id}</p>")

            app.include_router(html_router)
            client = TestClient(app)

            # Test single parameter
            response = client.get("/users/42")
            assert response.status_code == 200
            assert "User 42" in response.text

            # Test multiple parameters
            response = client.get("/posts/123/comments/456")
            assert response.status_code == 200
            assert "Post 123, Comment 456" in response.text

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAPIRouterPublicInterface:
    """Test APIRouter public interface as specified in Phase 1 planning (lines 55-73)."""

    def _create_test_app(self) -> tuple[App, str]:
        """Create a test app with configuration."""
        config = {
            "app": {"name": "api_test"},
            "routes": {
                "/api/users": {"rate_limit": 100, "format": "json"},
                "/api/admin/*": {"auth_required": True, "admin_only": True}
            }
        }

        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "app.yaml"
        
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)

        app = App(config_dir=temp_dir, environment="development")
        return app, temp_dir

    def test_api_router_constructor_interface(self) -> None:
        """Test: APIRouter(config_loader: ConfigLoader, **fastapi_kwargs)"""
        app, temp_dir = self._create_test_app()

        try:
            # Test basic router creation through App factory method
            api_router = app.create_api_router()
            assert isinstance(api_router, APIRouter)

            # Test with FastAPI router parameters
            api_router_with_params = app.create_api_router(
                prefix="/api/v1",
                tags=["api", "v1"],
                dependencies=[]
            )
            assert api_router_with_params.prefix == "/api/v1"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_api_router_fastapi_decorators(self) -> None:
        """Test standard FastAPI decorators work on APIRouter."""
        app, temp_dir = self._create_test_app()

        try:
            api_router = app.create_api_router()

            # Test @router.get() decorator
            @api_router.get("/users")
            def get_users():
                return {"users": [{"id": 1, "name": "Alice"}]}

            # Test @router.post() decorator
            @api_router.post("/users")
            def create_user():
                return {"user": {"id": 2, "name": "Bob"}, "created": True}

            # Test @router.put() decorator
            @api_router.put("/users/{user_id}")
            def update_user(user_id: int):
                return {"user": {"id": user_id, "name": "Updated"}, "updated": True}

            # Test @router.delete() decorator
            @api_router.delete("/users/{user_id}")
            def delete_user(user_id: int):
                return {"user": {"id": user_id}, "deleted": True}

            # Verify routes were registered
            assert len(api_router.routes) == 4

            # Test with FastAPI app
            app.include_router(api_router)
            client = TestClient(app)

            # Test each route
            response = client.get("/users")
            assert response.status_code == 200
            data = response.json()
            assert "users" in data
            assert data["users"][0]["name"] == "Alice"

            response = client.post("/users")
            assert response.status_code == 200
            data = response.json()
            assert data["created"] is True

            response = client.put("/users/123")
            assert response.status_code == 200
            data = response.json()
            assert data["updated"] is True
            assert data["user"]["id"] == 123

            response = client.delete("/users/456")
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            assert data["user"]["id"] == 456

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_api_router_default_response_class(self) -> None:
        """Test that APIRouter automatically applies JSONResponse as default."""
        app, temp_dir = self._create_test_app()

        try:
            api_router = app.create_api_router()

            # Verify default response class
            assert api_router.default_response_class == JSONResponse

            # Test that responses are JSON by default
            @api_router.get("/test")
            def test_endpoint():
                return {"message": "test", "status": "success"}

            app.include_router(api_router)
            client = TestClient(app)

            response = client.get("/test")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            
            data = response.json()
            assert data["message"] == "test"
            assert data["status"] == "success"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_api_router_openapi_integration(self) -> None:
        """Test OpenAPI documentation generation."""
        app, temp_dir = self._create_test_app()

        try:
            api_router = app.create_api_router(tags=["users"])

            @api_router.get("/users", summary="Get all users", description="Retrieve list of users")
            def get_users():
                """Get all users from the system."""
                return {"users": []}

            @api_router.post("/users", summary="Create user", description="Create a new user")
            def create_user():
                """Create a new user in the system."""
                return {"created": True}

            app.include_router(api_router)

            # Get OpenAPI schema
            openapi_schema = app.openapi()

            # Verify routes are documented
            assert "/users" in openapi_schema["paths"]
            
            users_path = openapi_schema["paths"]["/users"]
            assert "get" in users_path
            assert "post" in users_path

            # Verify documentation details
            get_spec = users_path["get"]
            assert get_spec["summary"] == "Get all users"
            assert get_spec["description"] == "Retrieve list of users"
            assert "users" in get_spec["tags"]

            post_spec = users_path["post"]
            assert post_spec["summary"] == "Create user"
            assert post_spec["description"] == "Create a new user"

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestBaseExtensionPublicInterface:
    """Test BaseExtension public interface as specified in Phase 1 planning (lines 75-97)."""

    def test_base_extension_constructor_interface(self) -> None:
        """Test: BaseExtension.__init__(self, config: Dict[str, Any]) -> None"""
        config = {"setting1": "value1", "setting2": 42}
        
        extension = DemoExtension(config)
        
        # Verify config is stored
        assert extension.config == config
        assert extension.config["setting1"] == "value1"
        assert extension.config["setting2"] == 42

    def test_get_middleware_factory_interface(self) -> None:
        """Test: @abstractmethod def get_middleware_factory(self) -> Callable[[Dict[str, Any]], Callable]"""
        extension = DemoExtension({"enabled": True})
        
        # Test middleware factory
        middleware_factory = extension.get_middleware_factory()
        assert callable(middleware_factory)

        # Test middleware creation
        route_config = {"demo_enabled": True}
        middleware = middleware_factory(route_config)
        assert callable(middleware)

        # Test middleware execution
        def test_endpoint():
            return "test_result"

        wrapped_endpoint = middleware(test_endpoint)
        result = wrapped_endpoint()
        
        assert result == "test_result"
        assert extension.middleware_calls == 1

    def test_should_apply_to_route_interface(self) -> None:
        """Test: @abstractmethod def should_apply_to_route(self, path: str, methods: List[str], route_config: Dict[str, Any]) -> bool"""
        extension = DemoExtension({"enabled": True})

        # Test with route that should match
        route_config_enabled = {"demo_enabled": True}
        result = extension.should_apply_to_route("/test", ["GET"], route_config_enabled)
        assert result is True

        # Test with route that shouldn't match
        route_config_disabled = {"demo_enabled": False}
        result = extension.should_apply_to_route("/test", ["GET"], route_config_disabled)
        assert result is False

        # Test with disabled extension
        disabled_extension = DemoExtension({"enabled": False})
        result = disabled_extension.should_apply_to_route("/test", ["GET"], route_config_enabled)
        assert result is False

    def test_validate_config_interface(self) -> None:
        """Test: def validate_config(self) -> List[str]"""
        # Test with valid config
        valid_extension = DemoExtension({"name": "test", "enabled": True})
        errors = valid_extension.validate_config()
        assert isinstance(errors, list)
        assert len(errors) == 0

        # Test with invalid config (this is a simple test since DemoExtension is basic)
        invalid_extension = DemoExtension("not_a_dict")  # type: ignore
        errors = invalid_extension.validate_config()
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert "Config must be a dictionary" in errors

    def test_optional_startup_shutdown_handlers_interface(self) -> None:
        """Test: def get_startup_handler(self) -> Optional[Callable[[], Awaitable[None]]]"""
        extension = DemoExtension({"enabled": True})

        # Test optional methods exist and return correct types
        startup_handler = extension.get_startup_handler()
        shutdown_handler = extension.get_shutdown_handler()

        # These can be None (optional) or callables
        assert startup_handler is None or callable(startup_handler)
        assert shutdown_handler is None or callable(shutdown_handler)


class TestCompletePublicAPIWorkflow:
    """Test the complete public API workflow working together."""

    def test_complete_public_api_workflow_demo(self) -> None:
        """Demonstrate the complete public API working together as intended."""
        # Create comprehensive configuration
        config = {
            "app": {
                "name": "complete_demo_app",
                "version": "2.0.0",
                "description": "Complete public API demonstration"
            },
            "routes": {
                # HTML routes
                "/": {"template": "home.html", "cache_ttl": 300, "demo_enabled": True},
                "/about": {"template": "about.html", "cache_ttl": 600, "demo_enabled": True},
                
                # API routes
                "/api/users": {"rate_limit": 100, "format": "json", "demo_enabled": True},
                "/api/users/{user_id}": {"rate_limit": 50, "demo_enabled": True},
                
                # Protected routes
                "/admin/dashboard": {
                    "auth_required": True,
                    "admin_only": True,
                    "demo_enabled": True
                }
            },
            "extensions": {
                "tests.test_public_api:DemoExtension": {
                    "name": "CompleteDemo",
                    "enabled": True,
                    "feature_flags": ["logging", "monitoring"]
                }
            }
        }

        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            # PHASE 1: App Creation and Configuration (Planning lines 17-33)
            app = App(config_dir=temp_dir, environment="development")
            
            # Verify app is properly initialized
            assert isinstance(app, FastAPI)
            assert app.get_environment() == "development"

            # Test get_config() public method
            loaded_config = app.get_config()
            assert loaded_config["app"]["name"] == "complete_demo_app"
            assert loaded_config["app"]["version"] == "2.0.0"

            # Test get_extension() public method
            demo_ext = app.get_extension("DemoExtension")
            assert demo_ext is not None
            assert isinstance(demo_ext, DemoExtension)
            assert demo_ext.name == "CompleteDemo"

            # PHASE 2: Router Creation (Planning lines 35-73)
            # Test create_html_router() public method
            html_router = app.create_html_router(prefix="/web")
            assert isinstance(html_router, HTMLRouter)
            assert html_router.prefix == "/web"
            assert html_router.default_response_class == HTMLResponse

            # Test create_api_router() public method
            api_router = app.create_api_router(prefix="/api", tags=["api"])
            assert isinstance(api_router, APIRouter)
            assert api_router.prefix == "/api"
            assert api_router.default_response_class == JSONResponse

            # PHASE 3: Route Registration with Standard FastAPI Decorators
            # Register HTML routes
            @html_router.get("/")
            def home_page():
                return HTMLResponse("<h1>Welcome to Complete Demo</h1>")

            @html_router.get("/about")
            def about_page():
                return HTMLResponse("<h1>About Our Application</h1>")

            # Register API routes
            @api_router.get("/users")
            def list_users():
                return {"users": [{"id": 1, "username": "demo_user"}]}

            @api_router.get("/users/{user_id}")
            def get_user(user_id: int):
                return {"user": {"id": user_id, "username": f"user_{user_id}"}}

            @api_router.post("/users")
            def create_user():
                return {"user": {"id": 2, "username": "new_user"}, "created": True}

            # Register protected route directly on app
            @app.get("/admin/dashboard")
            def admin_dashboard():
                return {"admin": "dashboard", "protected": True}

            # PHASE 4: Router Integration with FastAPI
            app.include_router(html_router)
            app.include_router(api_router)

            # PHASE 5: Complete Workflow Testing
            client = TestClient(app)

            # Test HTML routes (should return HTML responses)
            response = client.get("/web/")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
            assert "Welcome to Complete Demo" in response.text

            response = client.get("/web/about")
            assert response.status_code == 200
            assert "About Our Application" in response.text

            # Test API routes (should return JSON responses)
            response = client.get("/api/users")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert "users" in data
            assert data["users"][0]["username"] == "demo_user"

            response = client.get("/api/users/42")
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == 42
            assert data["user"]["username"] == "user_42"

            response = client.post("/api/users")
            assert response.status_code == 200
            data = response.json()
            assert data["created"] is True

            # Test direct app route
            response = client.get("/admin/dashboard")
            assert response.status_code == 200
            data = response.json()
            assert data["admin"] == "dashboard"

            # PHASE 6: Verify Extension Integration
            # Extensions should have processed requests
            assert demo_ext.middleware_calls > 0

            # Verify configuration resolution worked
            user_config = api_router._route_resolver.resolve_route_config("/api/users", ["GET"])
            assert user_config.get("rate_limit") == 100
            assert user_config.get("format") == "json"

            # Verify extension applicability
            assert demo_ext.should_apply_to_route("/api/users", ["GET"], user_config)

            # PHASE 7: Verify OpenAPI Documentation
            openapi_schema = app.openapi()
            assert "/api/users" in openapi_schema["paths"]
            assert "/admin/dashboard" in openapi_schema["paths"]

            # Verify all public APIs worked as specified in Phase 1 planning
            print("✅ Complete Public API Workflow Demonstration Successful!")
            print(f"   App Environment: {app.get_environment()}")
            print(f"   App Name: {app.get_config()['app']['name']}")
            print(f"   Extension Loaded: {demo_ext.name}")
            print(f"   HTML Router Prefix: {html_router.prefix}")
            print(f"   API Router Prefix: {api_router.prefix}")
            print(f"   Middleware Calls: {demo_ext.middleware_calls}")

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_developer_usage_patterns(self) -> None:
        """Test typical usage patterns that developers would use."""
        # Simple configuration for common use case
        config = {
            "app": {"name": "my_blog", "version": "1.0.0"},
            "routes": {
                "/": {"cache_ttl": 300},
                "/api/*": {"rate_limit": 1000}
            }
        }

        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)

            # Typical developer workflow
            # 1. Create the app
            app = App(config_dir=temp_dir)

            # 2. Create routers for different parts of the application
            web = app.create_html_router()
            api = app.create_api_router(prefix="/api")

            # 3. Define routes using familiar FastAPI decorators
            @web.get("/")
            def home():
                return "<h1>My Blog</h1>"

            @web.get("/posts/{slug}")
            def blog_post(slug: str):
                return f"<article><h1>Post: {slug}</h1></article>"

            @api.get("/posts")
            def get_posts():
                return {"posts": [{"id": 1, "title": "First Post"}]}

            @api.post("/posts")
            def create_post():
                return {"post": {"id": 2, "title": "New Post"}}

            # 4. Include routers in the app
            app.include_router(web)
            app.include_router(api)

            # 5. Test the application
            client = TestClient(app)

            # Test web routes
            response = client.get("/")
            assert response.status_code == 200
            assert "My Blog" in response.text

            response = client.get("/posts/my-first-post")
            assert response.status_code == 200
            assert "Post: my-first-post" in response.text

            # Test API routes
            response = client.get("/api/posts")
            assert response.status_code == 200
            data = response.json()
            assert "posts" in data

            response = client.post("/api/posts")
            assert response.status_code == 200
            data = response.json()
            assert data["post"]["title"] == "New Post"

            # Verify framework features work transparently
            config = app.get_config()
            assert config["app"]["name"] == "my_blog"

            print("✅ Developer Usage Patterns Work Correctly!")

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)