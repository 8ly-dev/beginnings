"""
Enhanced HTML routing functionality for Beginnings framework.

This module provides configuration-aware HTML routing with middleware integration
and thoughtful defaults for web page rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from fastapi import APIRouter as FastAPIRouter
from fastapi.responses import HTMLResponse

from beginnings.config.route_resolver import RouteConfigResolver
from beginnings.routing.middleware import MiddlewareChainBuilder

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

        # Resolve route configuration
        route_config = self._route_resolver.resolve_route_config(path, methods)

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
