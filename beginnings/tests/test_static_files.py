"""
Test static file serving integration with HTMLRouter.

Tests static file configuration, security, caching, and integration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.routing.static import (
    SecureStaticFiles,
    StaticFileError,
    StaticFileManager,
    create_static_manager_from_config,
    get_static_config_defaults,
)


class TestStaticFileManager:
    """Test the StaticFileManager functionality."""

    def _create_test_static_files(self, temp_dir: str) -> None:
        """Create test static files in the temporary directory."""
        static_dir = Path(temp_dir) / "static"
        static_dir.mkdir()
        
        # Create various file types
        (static_dir / "styles.css").write_text("body { color: blue; }")
        (static_dir / "script.js").write_text("console.log('hello');")
        (static_dir / "image.png").write_bytes(b"fake png data")
        (static_dir / "document.pdf").write_bytes(b"fake pdf data")
        
        # Create subdirectory
        (static_dir / "assets").mkdir()
        (static_dir / "assets" / "logo.svg").write_text("<svg></svg>")

    def test_static_manager_initialization(self) -> None:
        """Test static file manager initialization."""
        manager = StaticFileManager()
        
        assert manager.list_static_directories() == {}
        assert manager.get_static_handler("/static") is None

    def test_add_static_directory(self) -> None:
        """Test adding static directory configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_static_files(temp_dir)
            static_dir = str(Path(temp_dir) / "static")
            
            manager = StaticFileManager()
            manager.add_static_directory("/static", static_dir)
            
            # Check configuration
            configs = manager.list_static_directories()
            assert "/static" in configs
            assert configs["/static"]["directory"] == str(Path(static_dir).absolute())
            
            # Check handler
            handler = manager.get_static_handler("/static")
            assert handler is not None
            assert isinstance(handler, SecureStaticFiles)

    def test_add_static_directory_nonexistent(self) -> None:
        """Test adding non-existent static directory."""
        manager = StaticFileManager()
        
        with pytest.raises(StaticFileError, match="does not exist"):
            manager.add_static_directory("/static", "/nonexistent/directory")

    def test_add_static_directory_file_instead_of_dir(self) -> None:
        """Test adding file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            manager = StaticFileManager()
            
            with pytest.raises(StaticFileError, match="not a directory"):
                manager.add_static_directory("/static", temp_file.name)

    def test_remove_static_directory(self) -> None:
        """Test removing static directory configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_static_files(temp_dir)
            static_dir = str(Path(temp_dir) / "static")
            
            manager = StaticFileManager()
            manager.add_static_directory("/static", static_dir)
            
            # Verify it's added
            assert "/static" in manager.list_static_directories()
            
            # Remove it
            result = manager.remove_static_directory("/static")
            assert result is True
            assert "/static" not in manager.list_static_directories()
            
            # Try to remove again
            result = manager.remove_static_directory("/static")
            assert result is False

    def test_clear_static_directories(self) -> None:
        """Test clearing all static directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_static_files(temp_dir)
            static_dir = str(Path(temp_dir) / "static")
            
            manager = StaticFileManager()
            manager.add_static_directory("/static", static_dir)
            manager.add_static_directory("/assets", static_dir)
            
            # Verify they're added
            assert len(manager.list_static_directories()) == 2
            
            # Clear all
            manager.clear_static_directories()
            assert len(manager.list_static_directories()) == 0

    def test_static_manager_from_config_single_directory(self) -> None:
        """Test creating static manager from single directory configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_static_files(temp_dir)
            static_dir = str(Path(temp_dir) / "static")
            
            config = {
                "static": {
                    "directory": static_dir,
                    "url_path": "/static",
                    "max_file_size": 1024 * 1024,
                    "cache_control": "public, max-age=7200"
                }
            }
            
            manager = create_static_manager_from_config(config)
            
            configs = manager.list_static_directories()
            assert "/static" in configs
            assert configs["/static"]["max_file_size"] == 1024 * 1024
            assert configs["/static"]["cache_control"] == "public, max-age=7200"

    def test_static_manager_from_config_multiple_directories(self) -> None:
        """Test creating static manager from multiple directory configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_static_files(temp_dir)
            static_dir = str(Path(temp_dir) / "static")
            
            config = {
                "static": {
                    "directories": [
                        {
                            "url_path": "/static",
                            "directory": static_dir,
                            "max_file_size": 1024 * 1024
                        },
                        {
                            "url_path": "/assets",
                            "directory": static_dir,
                            "max_file_size": 512 * 1024
                        }
                    ]
                }
            }
            
            manager = create_static_manager_from_config(config)
            
            configs = manager.list_static_directories()
            assert "/static" in configs
            assert "/assets" in configs
            assert configs["/static"]["max_file_size"] == 1024 * 1024
            assert configs["/assets"]["max_file_size"] == 512 * 1024

    def test_static_manager_from_empty_config(self) -> None:
        """Test creating static manager from empty configuration."""
        config: dict[str, Any] = {}
        
        manager = create_static_manager_from_config(config)
        assert manager is None


class TestSecureStaticFiles:
    """Test SecureStaticFiles security features."""

    def test_static_config_defaults(self) -> None:
        """Test static configuration defaults for different security levels."""
        default_config = get_static_config_defaults("default")
        assert default_config["check_dir"] is True
        assert default_config["follow_symlink"] is False
        assert ".css" in default_config["allowed_extensions"]
        assert ".js" in default_config["allowed_extensions"]
        
        secure_config = get_static_config_defaults("secure")
        assert secure_config["max_file_size"] == 5 * 1024 * 1024  # 5MB
        assert ".css" in secure_config["allowed_extensions"]
        assert ".pdf" not in secure_config["allowed_extensions"]
        
        permissive_config = get_static_config_defaults("permissive")
        assert permissive_config["allowed_extensions"] is None  # Allow all
        assert permissive_config["max_file_size"] == 50 * 1024 * 1024  # 50MB


class TestHTMLRouterStaticIntegration:
    """Test HTMLRouter integration with static file serving."""

    def _create_test_app_with_static(self) -> tuple[App, str]:
        """Create test app with static file configuration."""
        temp_dir = tempfile.mkdtemp()
        
        # Create static files
        static_dir = Path(temp_dir) / "static"
        static_dir.mkdir()
        
        (static_dir / "styles.css").write_text("body { color: blue; }")
        (static_dir / "script.js").write_text("console.log('hello');")
        (static_dir / "image.png").write_bytes(b"fake png data")
        
        # Create assets subdirectory
        assets_dir = Path(temp_dir) / "assets"
        assets_dir.mkdir()
        (assets_dir / "logo.svg").write_text("<svg></svg>")
        
        # Create configuration
        config = {
            "app": {"name": "static_test_app"},
            "static": {
                "directories": [
                    {
                        "url_path": "/static",
                        "directory": str(static_dir),
                        "max_file_size": 1024 * 1024,
                        "cache_control": "public, max-age=3600"
                    },
                    {
                        "url_path": "/assets",
                        "directory": str(assets_dir),
                        "max_file_size": 512 * 1024
                    }
                ]
            },
            "routes": {
                "/": {"template": "home.html"}
            }
        }
        
        config_file = Path(temp_dir) / "app.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)
        
        app = App(config_dir=temp_dir, environment="development")
        return app, temp_dir

    def test_html_router_static_methods(self) -> None:
        """Test HTMLRouter static file methods."""
        app, temp_dir = self._create_test_app_with_static()
        
        try:
            html_router = app.create_html_router()
            
            # Test list_static_directories
            static_dirs = html_router.list_static_directories()
            assert "/static" in static_dirs
            assert "/assets" in static_dirs
            
            # Test static manager property
            assert html_router.static_manager is not None
            
            # Test add_static_directory
            new_static_dir = Path(temp_dir) / "new_static"
            new_static_dir.mkdir()
            (new_static_dir / "test.txt").write_text("test")
            
            html_router.add_static_directory("/new", str(new_static_dir))
            static_dirs = html_router.list_static_directories()
            assert "/new" in static_dirs
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_without_static_config(self) -> None:
        """Test HTMLRouter behavior without static configuration."""
        config = {
            "app": {"name": "no_static_test"},
            "routes": {"/": {}}
        }
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)
            
            app = App(config_dir=temp_dir, environment="development")
            html_router = app.create_html_router()
            
            # Static methods should handle missing static manager gracefully
            assert html_router.list_static_directories() == {}
            assert html_router.static_manager is None
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_static_file_serving_integration(self) -> None:
        """Test actual static file serving through the application."""
        app, temp_dir = self._create_test_app_with_static()
        
        try:
            html_router = app.create_html_router()
            
            # Add a simple route
            @html_router.get("/")
            def home():
                return "<h1>Home</h1>"
            
            # Include router (this should auto-mount static files)
            app.include_router(html_router)
            
            client = TestClient(app)
            
            # Test regular route
            response = client.get("/")
            assert response.status_code == 200
            assert "Home" in response.text
            
            # Test static file serving
            response = client.get("/static/styles.css")
            assert response.status_code == 200
            assert response.text == "body { color: blue; }"
            assert "text/css" in response.headers.get("content-type", "")
            
            response = client.get("/static/script.js")
            assert response.status_code == 200
            assert response.text == "console.log('hello');"
            assert "application/javascript" in response.headers.get("content-type", "") or \
                   "text/javascript" in response.headers.get("content-type", "")
            
            # Test assets directory
            response = client.get("/assets/logo.svg")
            assert response.status_code == 200
            assert response.text == "<svg></svg>"
            
            # Test non-existent file
            response = client.get("/static/nonexistent.txt")
            assert response.status_code == 404
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_static_file_security_headers(self) -> None:
        """Test security headers are applied to static files."""
        app, temp_dir = self._create_test_app_with_static()
        
        try:
            html_router = app.create_html_router()
            app.include_router(html_router)
            
            client = TestClient(app)
            
            # Test CSS file security headers
            response = client.get("/static/styles.css")
            assert response.status_code == 200
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert "Cache-Control" in response.headers
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_manual_static_directory_addition(self) -> None:
        """Test manually adding static directories after router creation."""
        app, temp_dir = self._create_test_app_with_static()
        
        try:
            html_router = app.create_html_router()
            
            # Create new static directory
            new_static_dir = Path(temp_dir) / "manual_static"
            new_static_dir.mkdir()
            (new_static_dir / "manual.txt").write_text("manually added")
            
            # Add it manually
            html_router.add_static_directory("/manual", str(new_static_dir))
            
            # Include router
            app.include_router(html_router)
            
            client = TestClient(app)
            
            # Test manually added static file
            response = client.get("/manual/manual.txt")
            assert response.status_code == 200
            assert response.text == "manually added"
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)