"""
CORS (Cross-Origin Resource Sharing) support for APIRouter.

This module provides configuration-driven CORS handling with security
defaults and flexible per-route configuration.
"""

from __future__ import annotations

from typing import Any, Sequence

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCorSMiddleware
from starlette.types import ASGIApp

from beginnings.core.errors import BeginningsError


class CORSError(BeginningsError):
    """CORS configuration and processing errors."""


class CORSConfig:
    """
    CORS configuration container with validation and defaults.
    
    Provides a structured way to configure CORS settings with security
    defaults and validation.
    """

    def __init__(
        self,
        allow_origins: list[str] | None = None,
        allow_origin_regex: str | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool | None = None,
        expose_headers: list[str] | None = None,
        max_age: int | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize CORS configuration.

        Args:
            allow_origins: List of allowed origins
            allow_origin_regex: Regex pattern for allowed origins
            allow_methods: List of allowed HTTP methods
            allow_headers: List of allowed headers
            allow_credentials: Whether to allow credentials
            expose_headers: List of headers to expose to client
            max_age: Max age for preflight cache (seconds)
            **kwargs: Additional CORS parameters
        """
        # Store original parameters for merging (only non-None values)
        self._original_params = {}
        if allow_origins is not None:
            self._original_params['allow_origins'] = allow_origins
        if allow_origin_regex is not None:
            self._original_params['allow_origin_regex'] = allow_origin_regex
        if allow_methods is not None:
            self._original_params['allow_methods'] = allow_methods
        if allow_headers is not None:
            self._original_params['allow_headers'] = allow_headers
        if allow_credentials is not None:
            self._original_params['allow_credentials'] = allow_credentials
        if expose_headers is not None:
            self._original_params['expose_headers'] = expose_headers
        if max_age is not None:
            self._original_params['max_age'] = max_age
        self._original_params.update(kwargs)
        
        # Only apply defaults if None is explicitly passed
        self.allow_origins = ["*"] if allow_origins is None else allow_origins
        self.allow_origin_regex = allow_origin_regex
        self.allow_methods = (["GET", "POST", "PUT", "DELETE", "OPTIONS"] 
                             if allow_methods is None else allow_methods)
        self.allow_headers = ["*"] if allow_headers is None else allow_headers
        self.allow_credentials = False if allow_credentials is None else allow_credentials
        self.expose_headers = [] if expose_headers is None else expose_headers
        self.max_age = 600 if max_age is None else max_age
        self.additional_params = kwargs
        
        # Validate configuration
        self._validate()

    def _validate(self) -> None:
        """Validate CORS configuration for security and correctness."""
        # Security validation: warn about wildcard with credentials
        if self.allow_credentials and "*" in self.allow_origins:
            raise CORSError(
                "CORS security issue: allow_credentials=True cannot be used with "
                "allow_origins=['*']. Specify explicit origins for security.",
                context={
                    "allow_origins": self.allow_origins,
                    "allow_credentials": self.allow_credentials
                }
            )
        
        # Validate max_age
        if self.max_age < 0:
            raise CORSError(
                "CORS max_age must be non-negative",
                context={"max_age": self.max_age}
            )
        
        # Validate methods
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
        for method in self.allow_methods:
            if method.upper() not in valid_methods and method != "*":
                raise CORSError(
                    f"Invalid HTTP method in CORS configuration: {method}",
                    context={"method": method, "valid_methods": list(valid_methods)}
                )

    def to_middleware_kwargs(self) -> dict[str, Any]:
        """
        Convert to kwargs suitable for CORSMiddleware.

        Returns:
            Dictionary of parameters for CORSMiddleware
        """
        return {
            "allow_origins": self.allow_origins,
            "allow_origin_regex": self.allow_origin_regex,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "allow_credentials": self.allow_credentials,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age,
            **self.additional_params
        }

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> CORSConfig:
        """
        Create CORSConfig from dictionary.

        Args:
            config: Configuration dictionary

        Returns:
            CORSConfig instance
        """
        return cls(**config)



class CORSManager:
    """
    Manager for CORS configuration and middleware creation.
    
    Handles global and per-route CORS configuration with intelligent
    merging and validation.
    """

    def __init__(self, global_cors_config: CORSConfig | None = None) -> None:
        """
        Initialize CORS manager.

        Args:
            global_cors_config: Global CORS configuration
        """
        self.global_cors_config = global_cors_config
        self._route_cors_configs: dict[str, CORSConfig] = {}

    def set_global_cors(self, config: CORSConfig | dict[str, Any]) -> None:
        """
        Set global CORS configuration.

        Args:
            config: CORS configuration
        """
        if isinstance(config, dict):
            config = CORSConfig.from_dict(config)
        self.global_cors_config = config

    def set_route_cors(self, route_path: str, config: CORSConfig | dict[str, Any]) -> None:
        """
        Set CORS configuration for a specific route.

        Args:
            route_path: Route path
            config: CORS configuration
        """
        if isinstance(config, dict):
            config = CORSConfig.from_dict(config)
        self._route_cors_configs[route_path] = config

    def get_cors_config_for_route(self, route_path: str) -> CORSConfig | None:
        """
        Get effective CORS configuration for a route.

        Args:
            route_path: Route path

        Returns:
            Effective CORS configuration or None if no CORS
        """
        # Check for route-specific configuration first
        if route_path in self._route_cors_configs:
            route_config = self._route_cors_configs[route_path]
            if self.global_cors_config:
                # Merge global config with route config (route takes precedence)
                # Start with global config as base
                merged_kwargs = self.global_cors_config.to_middleware_kwargs()
                
                # Only override with values that were explicitly set in route config
                route_kwargs = route_config.to_middleware_kwargs()
                
                # For the merge, we need to know which values were explicitly set
                # This is tricky with the current design. Let's use a different approach:
                # Create a new config that inherits from global and overrides specific values
                
                # Get the original route config dict and only override those keys
                if hasattr(route_config, '_original_params'):
                    # If we stored the original parameters, use only those
                    for key, value in route_config._original_params.items():
                        merged_kwargs[key] = value
                else:
                    # Fallback: override with all route config values
                    merged_kwargs.update(route_kwargs)
                
                return CORSConfig(**merged_kwargs)
            return route_config
        
        # Fall back to global configuration
        return self.global_cors_config

    def create_cors_middleware(self, app: ASGIApp, config: CORSConfig) -> StarletteCorSMiddleware:
        """
        Create CORS middleware with the given configuration.

        Args:
            app: ASGI application
            config: CORS configuration

        Returns:
            Configured CORS middleware
        """
        return StarletteCorSMiddleware(app, **config.to_middleware_kwargs())

    def has_cors_for_route(self, route_path: str) -> bool:
        """
        Check if CORS is configured for a route.

        Args:
            route_path: Route path

        Returns:
            True if CORS is configured, False otherwise
        """
        return (route_path in self._route_cors_configs or 
                self.global_cors_config is not None)


def create_cors_manager_from_config(config: dict[str, Any]) -> CORSManager | None:
    """
    Create CORS manager from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        CORSManager instance or None if no CORS configuration
    """
    cors_config = config.get("cors", {})
    
    # If no CORS configuration, return None
    if not cors_config:
        return None
    
    manager = CORSManager()
    
    # Set global CORS configuration if present
    if "global" in cors_config:
        try:
            global_config = CORSConfig.from_dict(cors_config["global"])
            manager.set_global_cors(global_config)
        except Exception as e:
            raise CORSError(f"Invalid global CORS configuration: {e}") from e
    
    # Set per-route CORS configuration if present
    if "routes" in cors_config:
        for route_path, route_cors_config in cors_config["routes"].items():
            try:
                route_config = CORSConfig.from_dict(route_cors_config)
                manager.set_route_cors(route_path, route_config)
            except Exception as e:
                raise CORSError(
                    f"Invalid CORS configuration for route {route_path}: {e}"
                ) from e
    
    return manager


# Security preset configurations
CORS_SECURITY_PRESETS = {
    "strict": {
        "allow_origins": [],  # Must be explicitly set
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"],
        "allow_credentials": False,
        "max_age": 300,  # 5 minutes
    },
    "development": {
        "allow_origins": ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"],
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "allow_credentials": True,
        "max_age": 600,  # 10 minutes
    },
    "production": {
        "allow_origins": [],  # Must be explicitly configured
        "allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "allow_credentials": True,
        "max_age": 3600,  # 1 hour
    },
    "public_api": {
        "allow_origins": ["*"],
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"],
        "allow_credentials": False,  # Required for wildcard origins
        "max_age": 86400,  # 24 hours
    },
}


def get_cors_preset(preset_name: str) -> dict[str, Any]:
    """
    Get a CORS security preset configuration.

    Args:
        preset_name: Name of the preset (strict, development, production, public_api)

    Returns:
        CORS configuration dictionary

    Raises:
        CORSError: If preset name is invalid
    """
    if preset_name not in CORS_SECURITY_PRESETS:
        available_presets = list(CORS_SECURITY_PRESETS.keys())
        raise CORSError(
            f"Unknown CORS preset: {preset_name}",
            context={
                "requested_preset": preset_name,
                "available_presets": available_presets
            }
        )
    
    return CORS_SECURITY_PRESETS[preset_name].copy()


def apply_cors_headers_manually(
    response: Response,
    request: Request,
    cors_config: CORSConfig
) -> Response:
    """
    Manually apply CORS headers to a response.

    This function is useful for custom CORS handling or when the
    standard middleware isn't suitable.

    Args:
        response: Response to modify
        request: Incoming request
        cors_config: CORS configuration

    Returns:
        Response with CORS headers applied
    """
    origin = request.headers.get("origin")
    
    # Check if origin is allowed
    if origin and (
        "*" in cors_config.allow_origins or 
        origin in cors_config.allow_origins or
        (cors_config.allow_origin_regex and 
         __import__("re").match(cors_config.allow_origin_regex, origin))
    ):
        response.headers["Access-Control-Allow-Origin"] = origin
    elif "*" in cors_config.allow_origins:
        response.headers["Access-Control-Allow-Origin"] = "*"
    
    # Add other CORS headers
    if cors_config.allow_credentials and origin:
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    if cors_config.expose_headers:
        response.headers["Access-Control-Expose-Headers"] = ", ".join(cors_config.expose_headers)
    
    # Handle preflight request
    if request.method == "OPTIONS":
        if cors_config.allow_methods:
            response.headers["Access-Control-Allow-Methods"] = ", ".join(cors_config.allow_methods)
        
        if cors_config.allow_headers:
            headers = cors_config.allow_headers
            if "*" in headers:
                # Echo back requested headers for wildcard
                requested_headers = request.headers.get("access-control-request-headers")
                if requested_headers:
                    response.headers["Access-Control-Allow-Headers"] = requested_headers
            else:
                response.headers["Access-Control-Allow-Headers"] = ", ".join(headers)
        
        response.headers["Access-Control-Max-Age"] = str(cors_config.max_age)
    
    return response