"""
Complete framework demonstration test showing the full Beginnings workflow.

This test demonstrates the complete public API as described in the Phase 1 planning
document, showing how developers would actually use the framework to build applications.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.extensions.base import BaseExtension


class LoggingExtension(BaseExtension):
    """Simple logging extension for demonstration."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.request_logs: list[str] = []

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def logging_middleware(endpoint: Callable) -> Callable:
                import functools
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    path = route_config.get("path", endpoint.__name__)
                    self.request_logs.append(f"Processing: {path}")
                    return endpoint(*args, **kwargs)
                return wrapper
            return logging_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("logging_enabled", True)


def test_complete_beginnings_framework_workflow():
    """Demonstrate the complete Beginnings framework workflow."""
    
    # Step 1: Create a comprehensive application configuration
    app_config = {
        "app": {
            "name": "My Web Application",
            "version": "1.0.0",
            "description": "A full-featured web application built with Beginnings"
        },
        "routes": {
            # HTML pages
            "/": {
                "template": "home.html",
                "cache_ttl": 300,
                "logging_enabled": True,
                "path": "/"
            },
            "/about": {
                "template": "about.html", 
                "cache_ttl": 3600,
                "logging_enabled": True,
                "path": "/about"
            },
            
            # Public API endpoints
            "/api/posts": {
                "rate_limit": 1000,
                "cache_ttl": 60,
                "logging_enabled": True,
                "path": "/api/posts"
            },
            "/api/posts/*": {
                "rate_limit": 500,
                "logging_enabled": True
            },
            
            # Protected admin endpoints
            "/admin/*": {
                "auth_required": True,
                "admin_only": True,
                "rate_limit": 50,
                "logging_enabled": True
            }
        },
        "extensions": {
            "tests.test_complete_framework_demo:LoggingExtension": {
                "log_level": "INFO",
                "enabled": True
            }
        }
    }
    
    # Step 2: Create temporary configuration
    temp_dir = tempfile.mkdtemp()
    
    try:
        config_file = Path(temp_dir) / "app.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(app_config, f)
        
        # Step 3: Initialize the Beginnings application
        # This demonstrates the main App class public interface
        app = App(config_dir=temp_dir, environment="development")
        
        # Verify app initialization worked
        assert app.get_environment() == "development"
        config = app.get_config()
        assert config["app"]["name"] == "My Web Application"
        
        # Verify extension loading worked
        logging_ext = app.get_extension("LoggingExtension")
        assert logging_ext is not None
        assert isinstance(logging_ext, LoggingExtension)
        
        # Step 4: Create routers for different parts of the application
        # This demonstrates the router factory methods
        web_router = app.create_html_router()  # For web pages
        api_router = app.create_api_router(prefix="/api", tags=["api"])  # For API
        admin_router = app.create_api_router(prefix="/admin", tags=["admin"])  # For admin
        
        # Step 5: Register routes using standard FastAPI decorators
        # HTML routes
        @web_router.get("/")
        def home():
            return "<html><body><h1>Welcome to My Application</h1></body></html>"
        
        @web_router.get("/about")
        def about():
            return "<html><body><h1>About Us</h1><p>Built with Beginnings!</p></body></html>"
        
        # Public API routes
        @api_router.get("/posts")
        def get_posts():
            return {
                "posts": [
                    {"id": 1, "title": "First Post", "content": "Hello world!"},
                    {"id": 2, "title": "Second Post", "content": "Using Beginnings framework"}
                ]
            }
        
        @api_router.get("/posts/{post_id}")
        def get_post(post_id: int):
            return {
                "post": {
                    "id": post_id,
                    "title": f"Post {post_id}",
                    "content": f"Content for post {post_id}"
                }
            }
        
        @api_router.post("/posts")
        def create_post():
            return {
                "post": {"id": 3, "title": "New Post", "content": "Created via API"},
                "created": True
            }
        
        # Protected admin routes
        @admin_router.get("/users")
        def admin_get_users():
            return {
                "users": [
                    {"id": 1, "username": "admin", "role": "administrator"},
                    {"id": 2, "username": "user1", "role": "user"}
                ]
            }
        
        @admin_router.post("/users")
        def admin_create_user():
            return {
                "user": {"id": 3, "username": "newuser", "role": "user"},
                "created": True
            }
        
        # Step 6: Include routers in the application
        app.include_router(web_router)
        app.include_router(api_router)
        app.include_router(admin_router)
        
        # Step 7: Test the complete application
        client = TestClient(app)
        
        # Test HTML pages
        response = client.get("/")
        assert response.status_code == 200
        assert "Welcome to My Application" in response.text
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        
        response = client.get("/about")
        assert response.status_code == 200
        assert "Built with Beginnings!" in response.text
        
        # Test public API endpoints
        response = client.get("/api/posts")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "posts" in data
        assert len(data["posts"]) == 2
        assert data["posts"][0]["title"] == "First Post"
        
        response = client.get("/api/posts/42")
        assert response.status_code == 200
        data = response.json()
        assert data["post"]["id"] == 42
        assert data["post"]["title"] == "Post 42"
        
        response = client.post("/api/posts")
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert data["post"]["title"] == "New Post"
        
        # Test admin endpoints
        response = client.get("/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) == 2
        
        response = client.post("/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        
        # Step 8: Verify configuration-driven behavior
        # Check that route configurations were resolved correctly
        home_config = web_router._route_resolver.resolve_route_config("/", ["GET"])
        assert home_config.get("template") == "home.html"
        assert home_config.get("cache_ttl") == 300
        
        posts_config = api_router._route_resolver.resolve_route_config("/api/posts", ["GET"])
        assert posts_config.get("rate_limit") == 1000
        assert posts_config.get("cache_ttl") == 60
        
        admin_config = admin_router._route_resolver.resolve_route_config("/admin/users", ["GET"])
        assert admin_config.get("auth_required") is True
        assert admin_config.get("admin_only") is True
        
        # Step 9: Verify extension integration
        # The logging extension should have processed requests
        assert len(logging_ext.request_logs) > 0
        
        # Verify that the extension applies to the right routes
        assert logging_ext.should_apply_to_route("/", ["GET"], home_config)
        assert logging_ext.should_apply_to_route("/api/posts", ["GET"], posts_config)
        
        # Step 10: Verify OpenAPI documentation generation
        openapi_schema = app.openapi()
        assert "openapi" in openapi_schema
        assert "/api/posts" in openapi_schema["paths"]
        assert "/admin/users" in openapi_schema["paths"]
        
        # The schema should include tags and descriptions
        posts_spec = openapi_schema["paths"]["/api/posts"]["get"]
        assert "api" in posts_spec["tags"]
        
        users_spec = openapi_schema["paths"]["/admin/users"]["get"] 
        assert "admin" in users_spec["tags"]
        
        print("✅ Complete Beginnings Framework Workflow Demonstration Successful!")
        print(f"   🏠 HTML pages served with proper content types")
        print(f"   🔗 API endpoints returning JSON responses")
        print(f"   🔐 Admin endpoints with configuration-driven behavior")
        print(f"   ⚙️  Configuration resolution working correctly")
        print(f"   🔌 Extensions processing requests through middleware")
        print(f"   📚 OpenAPI documentation generated automatically")
        print(f"   🌍 Environment detection: {app.get_environment()}")
        print(f"   📋 Extension logs: {len(logging_ext.request_logs)} requests processed")
        
        return True
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_developer_quick_start_workflow():
    """Demonstrate the developer quick-start workflow."""
    
    # Minimal configuration for getting started quickly
    config = {
        "app": {"name": "quick_start_app"},
        "routes": {
            "/": {"cache_ttl": 60},
            "/api/*": {"rate_limit": 100}
        }
    }
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        config_file = Path(temp_dir) / "app.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)
        
        # Quick start: Create app and routers
        app = App(config_dir=temp_dir)
        web = app.create_html_router()
        api = app.create_api_router(prefix="/api")
        
        # Simple routes
        @web.get("/")
        def home():
            return "<h1>Quick Start App</h1>"
        
        @api.get("/hello")
        def hello():
            return {"message": "Hello from Beginnings!"}
        
        # Include routers
        app.include_router(web)
        app.include_router(api)
        
        # Test it works
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 200
        assert "Quick Start App" in response.text
        
        response = client.get("/api/hello")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello from Beginnings!"
        
        print("✅ Developer Quick Start Workflow Successful!")
        print("   🚀 Minimal configuration")
        print("   ⚡ Fast setup and testing")
        print("   🎯 Focused on essential features")
        
        return True
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_complete_beginnings_framework_workflow()
    test_developer_quick_start_workflow()
    print("\n🎉 All framework demonstrations completed successfully!")