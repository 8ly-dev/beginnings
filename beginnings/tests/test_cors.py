"""
Test CORS functionality for APIRouter.

Tests CORS configuration, security features, and integration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.routing.cors import (
    CORSConfig,
    CORSError,
    CORSManager,
    create_cors_manager_from_config,
    get_cors_preset,
)


class TestCORSConfig:
    """Test CORS configuration functionality."""

    def test_cors_config_initialization(self) -> None:
        """Test CORS configuration initialization with defaults."""
        config = CORSConfig()
        
        assert config.allow_origins == ["*"]
        assert config.allow_methods == ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        assert config.allow_headers == ["*"]
        assert config.allow_credentials is False
        assert config.max_age == 600

    def test_cors_config_custom_values(self) -> None:
        """Test CORS configuration with custom values."""
        config = CORSConfig(
            allow_origins=["https://example.com", "https://app.example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=3600
        )
        
        assert config.allow_origins == ["https://example.com", "https://app.example.com"]
        assert config.allow_methods == ["GET", "POST"]
        assert config.allow_headers == ["Content-Type", "Authorization"]
        assert config.allow_credentials is True
        assert config.max_age == 3600

    def test_cors_config_security_validation_credentials_with_wildcard(self) -> None:
        """Test security validation prevents credentials with wildcard origins."""
        with pytest.raises(CORSError, match="allow_credentials=True cannot be used"):
            CORSConfig(
                allow_origins=["*"],
                allow_credentials=True
            )

    def test_cors_config_invalid_max_age(self) -> None:
        """Test validation of negative max_age."""
        with pytest.raises(CORSError, match="max_age must be non-negative"):
            CORSConfig(max_age=-1)

    def test_cors_config_invalid_method(self) -> None:
        """Test validation of invalid HTTP methods."""
        with pytest.raises(CORSError, match="Invalid HTTP method"):
            CORSConfig(allow_methods=["GET", "INVALID"])

    def test_cors_config_from_dict(self) -> None:
        """Test creating CORS config from dictionary."""
        config_dict = {
            "allow_origins": ["https://example.com"],
            "allow_methods": ["GET", "POST"],
            "allow_credentials": True,
            "max_age": 1800
        }
        
        config = CORSConfig.from_dict(config_dict)
        
        assert config.allow_origins == ["https://example.com"]
        assert config.allow_methods == ["GET", "POST"]
        assert config.allow_credentials is True
        assert config.max_age == 1800

    def test_cors_config_to_middleware_kwargs(self) -> None:
        """Test converting CORS config to middleware kwargs."""
        config = CORSConfig(
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_credentials=True
        )
        
        kwargs = config.to_middleware_kwargs()
        
        assert kwargs["allow_origins"] == ["https://example.com"]
        assert kwargs["allow_methods"] == ["GET", "POST"]
        assert kwargs["allow_credentials"] is True



class TestCORSManager:
    """Test CORS manager functionality."""

    def test_cors_manager_initialization(self) -> None:
        """Test CORS manager initialization."""
        manager = CORSManager()
        
        assert manager.global_cors_config is None
        assert not manager.has_cors_for_route("/test")

    def test_cors_manager_global_config(self) -> None:
        """Test setting global CORS configuration."""
        manager = CORSManager()
        
        global_config = CORSConfig(
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"]
        )
        
        manager.set_global_cors(global_config)
        
        assert manager.global_cors_config == global_config
        assert manager.has_cors_for_route("/any/route")

    def test_cors_manager_route_config(self) -> None:
        """Test setting route-specific CORS configuration."""
        manager = CORSManager()
        
        route_config = CORSConfig(
            allow_origins=["https://api.example.com"],
            allow_methods=["GET", "POST", "PUT", "DELETE"]
        )
        
        manager.set_route_cors("/api/users", route_config)
        
        assert manager.has_cors_for_route("/api/users")
        assert not manager.has_cors_for_route("/api/posts")
        
        retrieved_config = manager.get_cors_config_for_route("/api/users")
        assert retrieved_config == route_config

    def test_cors_manager_config_merging(self) -> None:
        """Test merging global and route-specific configurations."""
        manager = CORSManager()
        
        # Set global config
        global_config = CORSConfig(
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            max_age=600
        )
        manager.set_global_cors(global_config)
        
        # Set route-specific config using dict (no defaults)
        route_config_dict = {
            "allow_origins": ["https://api.example.com"],
            "allow_credentials": True
        }
        manager.set_route_cors("/api/users", route_config_dict)
        
        # Get effective config for route
        effective_config = manager.get_cors_config_for_route("/api/users")
        
        # Should have route origins, global methods, and route credentials
        assert effective_config.allow_origins == ["https://api.example.com"]
        assert effective_config.allow_methods == ["GET", "POST"]
        assert effective_config.allow_credentials is True
        assert effective_config.max_age == 600

    def test_cors_manager_from_config(self) -> None:
        """Test creating CORS manager from configuration."""
        config = {
            "cors": {
                "global": {
                    "allow_origins": ["https://example.com"],
                    "allow_methods": ["GET", "POST"],
                    "max_age": 3600
                },
                "routes": {
                    "/api/public": {
                        "allow_origins": ["*"],
                        "allow_credentials": False
                    },
                    "/api/private": {
                        "allow_origins": ["https://app.example.com"],
                        "allow_credentials": True
                    }
                }
            }
        }
        
        manager = create_cors_manager_from_config(config)
        
        assert manager is not None
        assert manager.global_cors_config is not None
        assert manager.global_cors_config.allow_origins == ["https://example.com"]
        
        # Test route-specific configs
        public_config = manager.get_cors_config_for_route("/api/public")
        assert public_config.allow_origins == ["*"]
        assert public_config.allow_credentials is False
        
        private_config = manager.get_cors_config_for_route("/api/private")
        assert private_config.allow_origins == ["https://app.example.com"]
        assert private_config.allow_credentials is True

    def test_cors_manager_from_empty_config(self) -> None:
        """Test creating CORS manager from empty configuration."""
        config: dict[str, Any] = {}
        
        manager = create_cors_manager_from_config(config)
        assert manager is None

    def test_cors_presets(self) -> None:
        """Test CORS security presets."""
        # Test development preset
        dev_preset = get_cors_preset("development")
        assert "localhost" in str(dev_preset["allow_origins"])
        assert dev_preset["allow_credentials"] is True
        
        # Test production preset
        prod_preset = get_cors_preset("production")
        assert prod_preset["allow_origins"] == []  # Must be explicitly set
        assert "Authorization" in prod_preset["allow_headers"]
        
        # Test public API preset
        public_preset = get_cors_preset("public_api")
        assert public_preset["allow_origins"] == ["*"]
        assert public_preset["allow_credentials"] is False
        
        # Test strict preset
        strict_preset = get_cors_preset("strict")
        assert strict_preset["allow_origins"] == []
        assert strict_preset["allow_methods"] == ["GET", "POST"]

    def test_cors_preset_invalid(self) -> None:
        """Test invalid CORS preset."""
        with pytest.raises(CORSError, match="Unknown CORS preset"):
            get_cors_preset("invalid_preset")


class TestAPIRouterCORSIntegration:
    """Test APIRouter integration with CORS functionality."""

    def _create_test_app_with_cors(self) -> tuple[App, str]:
        """Create test app with CORS configuration."""
        temp_dir = tempfile.mkdtemp()
        
        # Create configuration with CORS
        config = {
            "app": {"name": "cors_test_app"},
            "cors": {
                "global": {
                    "allow_origins": ["https://example.com", "https://app.example.com"],
                    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization"],
                    "allow_credentials": True,
                    "max_age": 3600
                },
                "routes": {
                    "/api/public": {
                        "allow_origins": ["*"],
                        "allow_credentials": False
                    }
                }
            },
            "routes": {
                "/api/users": {"cors_enabled": True},
                "/api/public": {"cors_enabled": True}
            }
        }
        
        config_file = Path(temp_dir) / "app.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)
        
        app = App(config_dir=temp_dir, environment="development")
        return app, temp_dir

    def test_api_router_cors_methods(self) -> None:
        """Test APIRouter CORS-related methods."""
        app, temp_dir = self._create_test_app_with_cors()
        
        try:
            api_router = app.create_api_router()
            
            # Test CORS manager property
            assert api_router.cors_manager is not None
            
            # Test route CORS checking
            assert api_router.has_cors_for_route("/api/users")  # Global CORS
            assert api_router.has_cors_for_route("/api/public")  # Route-specific CORS
            
            # Test getting CORS config for routes
            users_cors = api_router.get_cors_config_for_route("/api/users")
            assert users_cors is not None
            assert "https://example.com" in users_cors["allow_origins"]
            
            public_cors = api_router.get_cors_config_for_route("/api/public")
            assert public_cors is not None
            assert public_cors["allow_origins"] == ["*"]
            assert public_cors["allow_credentials"] is False
            
            # Test adding CORS for route
            api_router.add_cors_for_route("/api/new", {
                "allow_origins": ["https://new.example.com"],
                "allow_methods": ["GET"]
            })
            
            assert api_router.has_cors_for_route("/api/new")
            new_cors = api_router.get_cors_config_for_route("/api/new")
            assert "https://new.example.com" in new_cors["allow_origins"]
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_api_router_without_cors_config(self) -> None:
        """Test APIRouter behavior without CORS configuration."""
        config = {
            "app": {"name": "no_cors_test"},
            "routes": {"/api/test": {}}
        }
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)
            
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()
            
            # CORS methods should handle missing CORS manager gracefully
            assert not api_router.has_cors_for_route("/api/test")
            assert api_router.get_cors_config_for_route("/api/test") is None
            assert api_router.cors_manager is None
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cors_integration_with_preflight_requests(self) -> None:
        """Test CORS preflight request handling."""
        app, temp_dir = self._create_test_app_with_cors()
        
        try:
            api_router = app.create_api_router()
            
            @api_router.get("/api/users")
            def get_users():
                return {"users": [{"id": 1, "name": "Alice"}]}
            
            @api_router.post("/api/users")
            def create_user():
                return {"user": {"id": 2, "name": "Bob"}, "created": True}
            
            # Include router (this should auto-mount CORS middleware)
            app.include_router(api_router)
            
            client = TestClient(app)
            
            # Test actual API request
            response = client.get("/api/users")
            assert response.status_code == 200
            data = response.json()
            assert "users" in data
            
            # Test preflight request
            response = client.options(
                "/api/users",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            assert response.status_code == 200
            
            # Check CORS headers
            assert "Access-Control-Allow-Origin" in response.headers
            assert "Access-Control-Allow-Methods" in response.headers
            assert "Access-Control-Allow-Headers" in response.headers
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cors_security_with_credentials(self) -> None:
        """Test CORS security with credentials."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Configuration with credentials enabled
            config = {
                "app": {"name": "cors_credentials_test"},
                "cors": {
                    "global": {
                        "allow_origins": ["https://app.example.com"],
                        "allow_credentials": True,
                        "allow_methods": ["GET", "POST"]
                    }
                }
            }
            
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)
            
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()
            
            @api_router.get("/api/secure")
            def secure_endpoint():
                return {"secure": True}
            
            app.include_router(api_router)
            client = TestClient(app)
            
            # Test request with allowed origin
            response = client.get(
                "/api/secure",
                headers={"Origin": "https://app.example.com"}
            )
            assert response.status_code == 200
            
            # In a real browser, CORS would be enforced, but TestClient doesn't enforce CORS
            # We're testing that the middleware is mounted correctly
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_manual_cors_configuration(self) -> None:
        """Test manually adding CORS configuration after router creation."""
        app, temp_dir = self._create_test_app_with_cors()
        
        try:
            api_router = app.create_api_router()
            
            # Add CORS manually
            api_router.add_cors_for_route("/api/manual", {
                "allow_origins": ["https://manual.example.com"],
                "allow_methods": ["GET", "POST"],
                "allow_credentials": False
            })
            
            # Verify it was added
            assert api_router.has_cors_for_route("/api/manual")
            cors_config = api_router.get_cors_config_for_route("/api/manual")
            assert "https://manual.example.com" in cors_config["allow_origins"]
            assert cors_config["allow_credentials"] is False
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cors_config_validation_in_app(self) -> None:
        """Test CORS configuration validation during app initialization."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Configuration with invalid CORS (credentials with wildcard)
            config = {
                "app": {"name": "invalid_cors_test"},
                "cors": {
                    "global": {
                        "allow_origins": ["*"],
                        "allow_credentials": True  # Invalid with wildcard
                    }
                }
            }
            
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)
            
            # App creation should succeed, but router creation might have no CORS
            # because the invalid config is caught during CORS manager initialization
            app = App(config_dir=temp_dir, environment="development")
            api_router = app.create_api_router()
            
            # CORS manager should be None due to invalid configuration
            assert api_router.cors_manager is None
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)