"""
Enhanced API routing functionality for Beginnings framework.

This module provides configuration-aware API routing with middleware integration
and thoughtful defaults for JSON APIs and REST endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from fastapi import APIRouter as FastAPIRouter
from fastapi.responses import JSONResponse

from beginnings.config.route_resolver import RouteConfigResolver
from beginnings.routing.cors import CORSManager, create_cors_manager_from_config
from beginnings.routing.middleware import MiddlewareChainBuilder

if TYPE_CHECKING:
    from beginnings.config.enhanced_loader import ConfigLoader
    from beginnings.extensions.loader import ExtensionManager


class APIRouter(FastAPIRouter):
    """
    Enhanced API router with configuration and middleware integration.

    Extends FastAPI's APIRouter with configuration-driven middleware application,
    JSON-specific defaults, and extension integration.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        extension_manager: ExtensionManager,
        **router_kwargs: Any
    ) -> None:
        """
        Initialize the API router.

        Args:
            config_loader: Configuration loader for route resolution
            extension_manager: Extension manager for middleware
            **router_kwargs: Additional arguments passed to APIRouter
        """
        # Set API-specific defaults
        super().__init__(default_response_class=JSONResponse, **router_kwargs)

        # Create route resolver from config loader
        config = config_loader.load_config()
        self._route_resolver = RouteConfigResolver(config)
        self._extension_manager = extension_manager
        self._middleware_builder = MiddlewareChainBuilder(extension_manager)
        self._registered_routes: dict[str, list[str]] = {}
        
        # Initialize CORS manager if configured
        self._cors_manager: CORSManager | None = None
        self._init_cors_manager(config)

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        """
        Override add_api_route to apply configuration and middleware.

        Args:
            path: Route path
            endpoint: Route handler function
            methods: HTTP methods
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

    def _init_cors_manager(self, config: dict[str, Any]) -> None:
        """
        Initialize CORS manager from configuration.

        Args:
            config: Application configuration
        """
        try:
            self._cors_manager = create_cors_manager_from_config(config)
        except Exception:
            # CORS manager is optional - if it fails to initialize,
            # continue without it (CORS will not work but router still functions)
            self._cors_manager = None

    def _apply_route_config(self, kwargs: dict[str, Any], route_config: dict[str, Any]) -> None:
        """
        Apply route configuration to route parameters.

        Args:
            kwargs: Route parameters to modify
            route_config: Configuration for this route
        """
        # Apply API-specific configuration
        if "response_class" not in kwargs:
            response_class = route_config.get("response_class", JSONResponse)
            if isinstance(response_class, str):
                # Handle string references to response classes
                if response_class == "JSONResponse":
                    kwargs["response_class"] = JSONResponse
                # Add more response class mappings as needed
            else:
                kwargs["response_class"] = response_class

        # Apply OpenAPI configuration
        for config_key in ["tags", "summary", "description", "response_description"]:
            if config_key in route_config and config_key not in kwargs:
                kwargs[config_key] = route_config[config_key]

        # Apply API-specific settings
        if "include_in_schema" not in kwargs and "include_in_schema" in route_config:
            kwargs["include_in_schema"] = route_config["include_in_schema"]

    def mount_cors_middleware(self, app: Any) -> None:
        """
        Mount CORS middleware on the given FastAPI app if CORS is configured.

        Args:
            app: FastAPI application instance to mount CORS middleware on
        """
        if self._cors_manager is None:
            return
        
        # Add global CORS middleware if configured
        if self._cors_manager.global_cors_config:
            from fastapi.middleware.cors import CORSMiddleware
            
            cors_config = self._cors_manager.global_cors_config
            app.add_middleware(
                CORSMiddleware,
                **cors_config.to_middleware_kwargs()
            )

    def has_cors_for_route(self, route_path: str) -> bool:
        """
        Check if CORS is configured for a route.

        Args:
            route_path: Route path

        Returns:
            True if CORS is configured, False otherwise
        """
        if self._cors_manager is None:
            return False
        
        return self._cors_manager.has_cors_for_route(route_path)

    def get_cors_config_for_route(self, route_path: str) -> dict[str, Any] | None:
        """
        Get CORS configuration for a specific route.

        Args:
            route_path: Route path

        Returns:
            CORS configuration dictionary or None
        """
        if self._cors_manager is None:
            return None
        
        cors_config = self._cors_manager.get_cors_config_for_route(route_path)
        if cors_config:
            return cors_config.to_middleware_kwargs()
        return None

    def add_cors_for_route(
        self, 
        route_path: str, 
        cors_config: dict[str, Any]
    ) -> None:
        """
        Add CORS configuration for a specific route.

        Args:
            route_path: Route path
            cors_config: CORS configuration dictionary
        """
        if self._cors_manager is None:
            from beginnings.routing.cors import CORSManager
            self._cors_manager = CORSManager()
        
        self._cors_manager.set_route_cors(route_path, cors_config)

    @property
    def cors_manager(self) -> CORSManager | None:
        """
        Get the CORS manager instance.

        Returns:
            CORSManager instance or None if not configured
        """
        return self._cors_manager


def create_api_response(
    data: Any = None,
    message: str | None = None,
    status_code: int = 200
) -> JSONResponse:
    """
    Create a standardized API response.

    Args:
        data: Response data payload
        message: Optional response message
        status_code: HTTP status code

    Returns:
        JSONResponse with standardized format
    """
    response_data = {}
    if data is not None:
        response_data["data"] = data
    if message is not None:
        response_data["message"] = message

    return JSONResponse(content=response_data, status_code=status_code)


def create_error_response(
    message: str,
    error_code: str | None = None,
    status_code: int = 400
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        message: Error message
        error_code: Optional error code for client handling
        status_code: HTTP status code

    Returns:
        JSONResponse with standardized error format
    """
    response_data = {"error": {"message": message}}
    if error_code is not None:
        response_data["error"]["code"] = error_code

    return JSONResponse(content=response_data, status_code=status_code)
