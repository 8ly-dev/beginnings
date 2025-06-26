"""
Enhanced HTML routing functionality for Beginnings framework.

This module provides configuration-aware HTML routing with middleware integration,
template engine support, and thoughtful defaults for web page rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from fastapi import APIRouter as FastAPIRouter, Request
from fastapi.responses import HTMLResponse

from beginnings.config.route_resolver import RouteConfigResolver
from beginnings.routing.middleware import MiddlewareChainBuilder
from beginnings.routing.static import StaticFileManager, create_static_manager_from_config
from beginnings.routing.templates import TemplateEngine, TemplateResponse, create_template_engine_from_config

if TYPE_CHECKING:
    from beginnings.config.enhanced_loader import ConfigLoader
    from beginnings.extensions.loader import ExtensionManager


class HTMLRouter(FastAPIRouter):
    """
    Enhanced HTML router with configuration and middleware integration.

    Extends FastAPI's APIRouter with configuration-driven middleware application,
    HTML-specific defaults, and extension integration.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        extension_manager: ExtensionManager,
        **router_kwargs: Any
    ) -> None:
        """
        Initialize the HTML router.

        Args:
            config_loader: Configuration loader for route resolution
            extension_manager: Extension manager for middleware
            **router_kwargs: Additional arguments passed to APIRouter
        """
        # Set HTML-specific defaults
        super().__init__(default_response_class=HTMLResponse, **router_kwargs)

        # Create route resolver from config loader
        config = config_loader.load_config()
        self._route_resolver = RouteConfigResolver(config)
        self._extension_manager = extension_manager
        self._middleware_builder = MiddlewareChainBuilder(extension_manager)
        self._registered_routes: dict[str, list[str]] = {}
        
        # Initialize template engine if configured
        self._template_engine: TemplateEngine | None = None
        self._init_template_engine(config)
        
        # Initialize static file manager if configured
        self._static_manager: StaticFileManager | None = None
        self._init_static_manager(config)

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        """
        Override add_api_route to apply configuration and middleware.

        Args:
            path: Route path
            endpoint: Route handler function
            methods: HTTP methods (defaults to GET for HTML routes)
            **kwargs: Additional route parameters
        """
        methods = kwargs.pop("methods", ["GET"])
        if isinstance(methods, str):
            methods = [methods]

        # Construct full path including prefix for configuration resolution
        full_path = path
        if hasattr(self, 'prefix') and self.prefix:
            # Remove leading slash from path if prefix ends with slash
            prefix = self.prefix.rstrip('/')
            path_part = path.lstrip('/')  
            full_path = f"{prefix}/{path_part}"
        
        # Resolve route configuration using full path
        route_config = self._route_resolver.resolve_route_config(full_path, methods)

        # Build middleware chain for this route
        middleware_chain = self._middleware_builder.build_middleware_chain(
            path, methods, route_config
        )

        # Apply middleware chain to endpoint
        enhanced_endpoint = middleware_chain(endpoint) if middleware_chain else endpoint

        # Apply route configuration to kwargs
        self._apply_route_config(kwargs, route_config)

        # Store route registration for tracking
        self._registered_routes[path] = methods

        # Call parent method with enhanced endpoint
        super().add_api_route(path, enhanced_endpoint, methods=methods, **kwargs)

    def _init_template_engine(self, config: dict[str, Any]) -> None:
        """
        Initialize template engine from configuration.

        Args:
            config: Application configuration
        """
        try:
            self._template_engine = create_template_engine_from_config(config)
        except Exception:
            # Template engine is optional - if it fails to initialize,
            # continue without it (templates will not work but router still functions)
            self._template_engine = None

    def _init_static_manager(self, config: dict[str, Any]) -> None:
        """
        Initialize static file manager from configuration.

        Args:
            config: Application configuration
        """
        try:
            self._static_manager = create_static_manager_from_config(config)
        except Exception:
            # Static file manager is optional - if it fails to initialize,
            # continue without it (static files will not work but router still functions)
            self._static_manager = None

    def _apply_route_config(self, kwargs: dict[str, Any], route_config: dict[str, Any]) -> None:
        """
        Apply route configuration to route parameters.

        Args:
            kwargs: Route parameters to modify
            route_config: Configuration for this route
        """
        # Apply HTML-specific configuration
        if "response_class" not in kwargs:
            response_class = route_config.get("response_class", HTMLResponse)
            if isinstance(response_class, str):
                # Handle string references to response classes
                if response_class == "HTMLResponse":
                    kwargs["response_class"] = HTMLResponse
                # Add more response class mappings as needed
            else:
                kwargs["response_class"] = response_class

        # Apply other route configuration
        for config_key in ["tags", "summary", "description", "response_description"]:
            if config_key in route_config and config_key not in kwargs:
                kwargs[config_key] = route_config[config_key]

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any] | None = None,
        request: Request | None = None
    ) -> str:
        """
        Render a template with context.

        Args:
            template_name: Name of template to render
            context: Template context variables
            request: FastAPI request object

        Returns:
            Rendered HTML string

        Raises:
            RuntimeError: If template engine is not available
        """
        if self._template_engine is None:
            raise RuntimeError(
                "Template engine not available. "
                "Check your configuration has a 'templates' section."
            )
        
        return self._template_engine.render_template(template_name, context, request)

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
            template_name: Name of template to render
            context: Template context variables
            status_code: HTTP status code
            headers: Additional response headers
            request: FastAPI request object

        Returns:
            HTMLResponse with rendered template
        """
        if self._template_engine is None:
            raise RuntimeError(
                "Template engine not available. "
                "Check your configuration has a 'templates' section."
            )
        
        return self._template_engine.render_template_response(
            template_name, context, status_code, headers, request
        )

    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Name of template to check

        Returns:
            True if template exists, False otherwise
        """
        if self._template_engine is None:
            return False
        
        return self._template_engine.template_exists(template_name)

    def list_templates(self) -> list[str]:
        """
        List all available templates.

        Returns:
            List of template names, empty if no template engine
        """
        if self._template_engine is None:
            return []
        
        return self._template_engine.list_templates()

    @property
    def template_engine(self) -> TemplateEngine | None:
        """
        Get the template engine instance.

        Returns:
            TemplateEngine instance or None if not configured
        """
        return self._template_engine

    def mount_static_files(self, app: Any) -> None:
        """
        Mount static file handlers on the given FastAPI app.

        Args:
            app: FastAPI application instance to mount static handlers on
        """
        if self._static_manager is None:
            return
        
        for url_path, handler in self._static_manager._static_handlers.items():
            # Mount the static file handler
            app.mount(url_path, handler, name=f"static_{url_path.replace('/', '_')}")

    def list_static_directories(self) -> dict[str, dict[str, Any]]:
        """
        List all configured static directories.

        Returns:
            Dictionary of URL paths and their configurations
        """
        if self._static_manager is None:
            return {}
        
        return self._static_manager.list_static_directories()

    def add_static_directory(
        self,
        url_path: str,
        directory: str,
        **config: Any
    ) -> None:
        """
        Add a static file directory configuration.

        Args:
            url_path: URL path prefix for static files
            directory: Directory containing static files
            **config: Additional static file configuration
        """
        if self._static_manager is None:
            self._static_manager = StaticFileManager()
        
        self._static_manager.add_static_directory(url_path, directory, **config)

    @property
    def static_manager(self) -> StaticFileManager | None:
        """
        Get the static file manager instance.

        Returns:
            StaticFileManager instance or None if not configured
        """
        return self._static_manager



def create_html_response(content: str, status_code: int = 200) -> HTMLResponse:
    """
    Create an HTML response with proper headers.

    Args:
        content: HTML content to return
        status_code: HTTP status code

    Returns:
        HTMLResponse instance
    """
    return HTMLResponse(content=content, status_code=status_code)
