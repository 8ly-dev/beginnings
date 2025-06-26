"""
Template engine integration for HTMLRouter with Jinja2 support.

This module provides template rendering capabilities for HTML routes,
including auto-reload for development and secure template handling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

from beginnings.core.errors import BeginningsError


class TemplateError(BeginningsError):
    """Template rendering and configuration errors."""


class TemplateEngine:
    """
    Jinja2 template engine with configuration-driven setup.
    
    Provides template rendering with auto-reload support for development,
    secure template loading, and flexible configuration.
    """

    def __init__(
        self,
        template_directory: str | Path = "templates",
        auto_reload: bool = False,
        enable_async: bool = True,
        **jinja_options: Any
    ) -> None:
        """
        Initialize template engine.

        Args:
            template_directory: Directory containing templates
            auto_reload: Enable template auto-reload for development
            enable_async: Enable async template rendering
            **jinja_options: Additional Jinja2 environment options
        """
        self.template_directory = Path(template_directory)
        self.auto_reload = auto_reload
        self.enable_async = enable_async
        
        # Validate template directory
        if not self.template_directory.exists():
            raise TemplateError(
                f"Template directory does not exist: {self.template_directory}",
                context={"template_directory": str(self.template_directory)}
            )
        
        if not self.template_directory.is_dir():
            raise TemplateError(
                f"Template directory is not a directory: {self.template_directory}",
                context={"template_directory": str(self.template_directory)}
            )

        # Set up Jinja2 environment with security defaults
        default_options = {
            "autoescape": select_autoescape(["html", "xml"]),
            "auto_reload": auto_reload,
            "enable_async": enable_async,
        }
        
        # Merge with user options (user options take precedence)
        jinja_options = {**default_options, **jinja_options}
        
        # Create filesystem loader
        self.loader = FileSystemLoader(str(self.template_directory))
        
        # Create Jinja2 environment
        self.env = Environment(loader=self.loader, **jinja_options)
        
        # Add global template functions
        self._setup_template_globals()

    def _setup_template_globals(self) -> None:
        """Set up global template functions and variables."""
        # Add useful global functions
        self.env.globals["url_for"] = self._url_for_stub
        self.env.globals["request"] = None  # Will be set per request
        
        # Add utility filters
        self.env.filters["datetimeformat"] = self._datetime_format
        
    def _url_for_stub(self, name: str, **path_params: Any) -> str:
        """
        Stub for URL generation (to be replaced with actual implementation).
        
        Args:
            name: Route name
            **path_params: Path parameters
            
        Returns:
            URL string (placeholder for now)
        """
        # This would be replaced with actual URL generation logic
        # For now, return a placeholder
        return f"/{name}"
    
    def _datetime_format(self, value: Any, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format datetime objects in templates.
        
        Args:
            value: Datetime-like object
            format_string: Format string
            
        Returns:
            Formatted datetime string
        """
        if hasattr(value, "strftime"):
            return value.strftime(format_string)
        return str(value)

    def render_template(
        self, 
        template_name: str, 
        context: dict[str, Any] | None = None,
        request: Request | None = None
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of template file
            context: Template context variables
            request: FastAPI request object (optional)

        Returns:
            Rendered HTML string

        Raises:
            TemplateError: If template cannot be rendered
        """
        context = context or {}
        
        try:
            # Set request in global context if provided
            if request:
                self.env.globals["request"] = request
            
            # Load and render template
            template = self.env.get_template(template_name)
            return template.render(**context)
            
        except TemplateNotFound as e:
            raise TemplateError(
                f"Template not found: {template_name}",
                context={
                    "template_name": template_name,
                    "template_directory": str(self.template_directory),
                    "available_templates": self.list_templates()
                }
            ) from e
            
        except TemplateSyntaxError as e:
            raise TemplateError(
                f"Template syntax error in {template_name}: {e}",
                context={
                    "template_name": template_name,
                    "line_number": e.lineno,
                    "error": str(e)
                }
            ) from e
            
        except Exception as e:
            raise TemplateError(
                f"Template rendering error in {template_name}: {e}",
                context={
                    "template_name": template_name,
                    "error": str(e)
                }
            ) from e
        finally:
            # Clean up request global
            self.env.globals["request"] = None

    async def render_template_async(
        self, 
        template_name: str, 
        context: dict[str, Any] | None = None,
        request: Request | None = None
    ) -> str:
        """
        Render a template asynchronously.

        Args:
            template_name: Name of template file
            context: Template context variables
            request: FastAPI request object (optional)

        Returns:
            Rendered HTML string

        Raises:
            TemplateError: If template cannot be rendered
        """
        if not self.enable_async:
            # Fall back to sync rendering
            return self.render_template(template_name, context, request)
            
        context = context or {}
        
        try:
            # Set request in global context if provided
            if request:
                self.env.globals["request"] = request
            
            # Load template and render asynchronously
            template = self.env.get_template(template_name)
            return await template.render_async(**context)
            
        except TemplateNotFound as e:
            raise TemplateError(
                f"Template not found: {template_name}",
                context={
                    "template_name": template_name,
                    "template_directory": str(self.template_directory),
                    "available_templates": self.list_templates()
                }
            ) from e
            
        except TemplateSyntaxError as e:
            raise TemplateError(
                f"Template syntax error in {template_name}: {e}",
                context={
                    "template_name": template_name,
                    "line_number": e.lineno,
                    "error": str(e)
                }
            ) from e
            
        except Exception as e:
            raise TemplateError(
                f"Template rendering error in {template_name}: {e}",
                context={
                    "template_name": template_name,
                    "error": str(e)
                }
            ) from e
        finally:
            # Clean up request global
            self.env.globals["request"] = None

    def render_template_response(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        request: Request | None = None
    ) -> HTMLResponse:
        """
        Render a template and return an HTMLResponse.

        Args:
            template_name: Name of template file
            context: Template context variables
            status_code: HTTP status code
            headers: Additional response headers
            request: FastAPI request object (optional)

        Returns:
            HTMLResponse with rendered template
        """
        content = self.render_template(template_name, context, request)
        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers
        )

    def list_templates(self) -> list[str]:
        """
        List all available templates.

        Returns:
            List of template names
        """
        templates = []
        for root, dirs, files in os.walk(self.template_directory):
            for file in files:
                if file.endswith(('.html', '.htm', '.j2', '.jinja', '.jinja2')):
                    # Get relative path from template directory
                    rel_path = os.path.relpath(
                        os.path.join(root, file), 
                        self.template_directory
                    )
                    templates.append(rel_path)
        return sorted(templates)

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Name of template to check

        Returns:
            True if template exists, False otherwise
        """
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False

    def get_template_mtime(self, template_name: str) -> float | None:
        """
        Get template modification time.

        Args:
            template_name: Name of template

        Returns:
            Modification time as timestamp, or None if template not found
        """
        try:
            source, filename = self.loader.get_source(self.env, template_name)
            if filename:
                return os.path.getmtime(filename)
        except (TemplateNotFound, OSError):
            pass
        return None


class TemplateResponse(HTMLResponse):
    """
    Response class that renders templates with context.
    
    Provides a convenient way to return template responses
    from route handlers.
    """
    
    def __init__(
        self,
        template_engine: TemplateEngine,
        template_name: str,
        context: dict[str, Any] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        request: Request | None = None
    ) -> None:
        """
        Initialize template response.

        Args:
            template_engine: Template engine to use for rendering
            template_name: Name of template to render
            context: Template context variables
            status_code: HTTP status code
            headers: Additional response headers
            request: FastAPI request object (optional)
        """
        # Render template content
        content = template_engine.render_template(template_name, context, request)
        
        # Initialize HTMLResponse with rendered content
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers
        )


def create_template_engine_from_config(config: dict[str, Any]) -> TemplateEngine:
    """
    Create a template engine from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured TemplateEngine instance
    """
    template_config = config.get("templates", {})
    
    # Extract configuration values with defaults
    template_directory = template_config.get("directory", "templates")
    auto_reload = template_config.get("auto_reload", False)
    enable_async = template_config.get("enable_async", True)
    
    # Extract additional Jinja2 options
    jinja_options = template_config.get("jinja_options", {})
    
    return TemplateEngine(
        template_directory=template_directory,
        auto_reload=auto_reload,
        enable_async=enable_async,
        **jinja_options
    )