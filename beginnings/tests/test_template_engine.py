"""
Test template engine integration with HTMLRouter.

Tests template rendering, configuration, and integration with the HTMLRouter.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import Request
from fastapi.testclient import TestClient

from beginnings import App
from beginnings.routing.templates import TemplateEngine, TemplateError, create_template_engine_from_config


class TestTemplateEngine:
    """Test the TemplateEngine functionality."""

    def _create_test_templates(self, temp_dir: str) -> None:
        """Create test templates in the temporary directory."""
        templates_dir = Path(temp_dir) / "templates"
        templates_dir.mkdir()
        
        # Create a simple template
        (templates_dir / "home.html").write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ heading }}</h1>
    <p>Welcome {{ user.name }}!</p>
</body>
</html>
        """.strip())
        
        # Create a template with includes
        (templates_dir / "base.html").write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
        """.strip())
        
        (templates_dir / "page.html").write_text("""
{% extends "base.html" %}
{% block title %}{{ page_title }}{% endblock %}
{% block content %}
    <h1>{{ content_heading }}</h1>
    <p>{{ content_text }}</p>
{% endblock %}
        """.strip())

    def test_template_engine_initialization(self) -> None:
        """Test template engine initialization with valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            assert engine.template_directory == Path(templates_dir)
            assert not engine.auto_reload  # Default
            assert engine.enable_async  # Default

    def test_template_engine_invalid_directory(self) -> None:
        """Test template engine with invalid directory."""
        with pytest.raises(TemplateError, match="Template directory does not exist"):
            TemplateEngine(template_directory="/nonexistent/directory")

    def test_template_engine_directory_is_file(self) -> None:
        """Test template engine with file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(TemplateError, match="not a directory"):
                TemplateEngine(template_directory=temp_file.name)

    def test_render_template_basic(self) -> None:
        """Test basic template rendering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            context = {
                "title": "Test Page",
                "heading": "Welcome",
                "user": {"name": "Alice"}
            }
            
            result = engine.render_template("home.html", context)
            
            assert "Test Page" in result
            assert "<h1>Welcome</h1>" in result
            assert "Welcome Alice!" in result

    def test_render_template_with_inheritance(self) -> None:
        """Test template rendering with template inheritance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            context = {
                "page_title": "My Page",
                "content_heading": "Page Content",
                "content_text": "This is the content."
            }
            
            result = engine.render_template("page.html", context)
            
            assert "<title>My Page</title>" in result
            assert "<h1>Page Content</h1>" in result
            assert "This is the content." in result

    def test_render_template_not_found(self) -> None:
        """Test rendering non-existent template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            with pytest.raises(TemplateError, match="Template not found: nonexistent.html"):
                engine.render_template("nonexistent.html")

    def test_template_exists(self) -> None:
        """Test template existence checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            assert engine.template_exists("home.html")
            assert engine.template_exists("page.html")
            assert not engine.template_exists("nonexistent.html")

    def test_list_templates(self) -> None:
        """Test listing available templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            engine = TemplateEngine(template_directory=templates_dir)
            
            templates = engine.list_templates()
            
            assert "home.html" in templates
            assert "base.html" in templates
            assert "page.html" in templates
            assert len(templates) == 3

    def test_create_template_engine_from_config(self) -> None:
        """Test creating template engine from configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            self._create_test_templates(temp_dir)
            templates_dir = str(Path(temp_dir) / "templates")
            
            config = {
                "templates": {
                    "directory": templates_dir,
                    "auto_reload": True,
                    "enable_async": False,
                    "jinja_options": {
                        "trim_blocks": True,
                        "lstrip_blocks": True
                    }
                }
            }
            
            engine = create_template_engine_from_config(config)
            
            assert str(engine.template_directory) == templates_dir
            assert engine.auto_reload is True
            assert engine.enable_async is False

    def test_create_template_engine_from_empty_config(self) -> None:
        """Test creating template engine with default configuration."""
        config: dict[str, Any] = {}
        
        # This should fail because default templates directory doesn't exist
        with pytest.raises(TemplateError):
            create_template_engine_from_config(config)


class TestHTMLRouterTemplateIntegration:
    """Test HTMLRouter integration with template engine."""

    def _create_test_app_with_templates(self) -> tuple[App, str]:
        """Create test app with template configuration."""
        temp_dir = tempfile.mkdtemp()
        
        # Create templates
        templates_dir = Path(temp_dir) / "templates"
        templates_dir.mkdir()
        
        (templates_dir / "home.html").write_text("""
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body><h1>{{ message }}</h1></body>
</html>
        """.strip())
        
        (templates_dir / "user.html").write_text("""
<!DOCTYPE html>
<html>
<head><title>User: {{ user.name }}</title></head>
<body>
    <h1>User Profile</h1>
    <p>Name: {{ user.name }}</p>
    <p>Email: {{ user.email }}</p>
</body>
</html>
        """.strip())
        
        # Create configuration
        config = {
            "app": {"name": "template_test_app"},
            "templates": {
                "directory": str(templates_dir),
                "auto_reload": True
            },
            "routes": {
                "/": {"template": "home.html"},
                "/user/{user_id}": {"template": "user.html"}
            }
        }
        
        config_file = Path(temp_dir) / "app.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f)
        
        app = App(config_dir=temp_dir, environment="development")
        return app, temp_dir

    def test_html_router_template_methods(self) -> None:
        """Test HTMLRouter template rendering methods."""
        app, temp_dir = self._create_test_app_with_templates()
        
        try:
            html_router = app.create_html_router()
            
            # Test template_exists
            assert html_router.template_exists("home.html")
            assert html_router.template_exists("user.html")
            assert not html_router.template_exists("nonexistent.html")
            
            # Test list_templates
            templates = html_router.list_templates()
            assert "home.html" in templates
            assert "user.html" in templates
            
            # Test render_template
            context = {"title": "Test", "message": "Hello World"}
            result = html_router.render_template("home.html", context)
            assert "Test" in result
            assert "Hello World" in result
            
            # Test render_template_response
            response = html_router.render_template_response("home.html", context)
            assert response.status_code == 200
            assert "Hello World" in response.body.decode()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_without_template_config(self) -> None:
        """Test HTMLRouter behavior without template configuration."""
        config = {
            "app": {"name": "no_template_test"},
            "routes": {"/": {}}
        }
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            config_file = Path(temp_dir) / "app.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump(config, f)
            
            app = App(config_dir=temp_dir, environment="development")
            html_router = app.create_html_router()
            
            # Template methods should handle missing template engine gracefully
            assert not html_router.template_exists("any.html")
            assert html_router.list_templates() == []
            assert html_router.template_engine is None
            
            # Template rendering should raise appropriate errors
            with pytest.raises(RuntimeError, match="Template engine not available"):
                html_router.render_template("test.html")
                
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_html_router_template_in_route_handler(self) -> None:
        """Test using templates in actual route handlers."""
        app, temp_dir = self._create_test_app_with_templates()
        
        try:
            html_router = app.create_html_router()
            
            @html_router.get("/")
            def home_page():
                context = {"title": "Home", "message": "Welcome to our site!"}
                return html_router.render_template_response("home.html", context)
            
            @html_router.get("/user/{user_id}")
            def user_page(user_id: int):
                # Simulate getting user data
                user_data = {"name": f"User {user_id}", "email": f"user{user_id}@example.com"}
                context = {"user": user_data}
                return html_router.render_template_response("user.html", context)
            
            app.include_router(html_router)
            client = TestClient(app)
            
            # Test home page
            response = client.get("/")
            assert response.status_code == 200
            assert "Welcome to our site!" in response.text
            assert "Home" in response.text
            
            # Test user page
            response = client.get("/user/42")
            assert response.status_code == 200
            assert "User 42" in response.text
            assert "user42@example.com" in response.text
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_template_engine_security(self) -> None:
        """Test template engine security features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir) / "templates"
            templates_dir.mkdir()
            
            # Create template with potential XSS
            (templates_dir / "unsafe.html").write_text("""
<h1>{{ title }}</h1>
<p>{{ user_input }}</p>
            """.strip())
            
            engine = TemplateEngine(template_directory=str(templates_dir))
            
            # Test that HTML is escaped by default
            context = {
                "title": "Safe Title",
                "user_input": "<script>alert('xss')</script>"
            }
            
            result = engine.render_template("unsafe.html", context)
            
            # Script should be escaped
            assert "&lt;script&gt;" in result
            assert "<script>" not in result
            assert "Safe Title" in result