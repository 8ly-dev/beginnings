"""
Core application class for Beginnings framework.

This module contains the main App class that provides the foundation
for building web applications with Beginnings with configuration-driven enhancements.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from beginnings.config.enhanced_loader import EnhancedConfigLoader
from beginnings.config.environment import EnvironmentDetector
from beginnings.config.route_resolver import RouteConfigResolver
from beginnings.extensions.base import BaseExtension
from beginnings.extensions.loader import ExtensionManager
from beginnings.routing.api import APIRouter
from beginnings.routing.html import HTMLRouter


class App(FastAPI):
    """
    The main application class for Beginnings framework.

    Extends FastAPI with configuration-driven enhancements, extension management,
    and thoughtful defaults for web application development.
    """

    def __init__(
        self,
        config_dir: str | None = None,
        environment: str | None = None,
        **fastapi_kwargs: Any
    ) -> None:
        """
        Initialize the Beginnings application.

        Args:
            config_dir: Directory containing configuration files
            environment: Environment name (auto-detected if None)
            **fastapi_kwargs: Additional arguments passed to FastAPI
        """
        # Initialize configuration system with graceful fallback
        try:
            self._environment_detector = EnvironmentDetector(config_dir, environment)
            self._config_loader = EnhancedConfigLoader(
                self._environment_detector.get_config_dir(),
                self._environment_detector.get_environment()
            )
            # Load configuration
            self._config = self._config_loader.load_config()
        except Exception:
            # Graceful fallback: use minimal default configuration when config loading fails
            self._environment_detector = None
            self._config_loader = None
            self._config = self._get_default_config()

        # Initialize route configuration resolver
        self._route_resolver = RouteConfigResolver(self._config)

        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            # Startup
            await self._extension_manager.startup()
            yield
            # Shutdown
            await self._extension_manager.shutdown()

        # Initialize FastAPI with lifespan
        fastapi_kwargs["lifespan"] = lifespan
        super().__init__(**fastapi_kwargs)

        # Initialize extension manager (after FastAPI init to avoid circular reference)
        self._extension_manager = ExtensionManager(self, self._config)

        # Load extensions from configuration
        self._load_extensions()
        
        # Set up content-aware error handling
        self._setup_error_handlers()

    def get_config(self) -> dict[str, Any]:
        """
        Get the loaded configuration.

        Returns:
            Complete configuration dictionary
        """
        import copy
        return copy.deepcopy(self._config)

    def get_extension(self, extension_name: str) -> BaseExtension | None:
        """
        Get a loaded extension by name.

        Args:
            extension_name: Name of the extension

        Returns:
            Extension instance or None if not found
        """
        try:
            return self._extension_manager.get_extension(extension_name)
        except Exception:
            return None

    def create_html_router(self, **router_kwargs: Any) -> HTMLRouter:
        """
        Create an HTML router with configuration integration.

        Args:
            **router_kwargs: Additional arguments passed to APIRouter

        Returns:
            Configured HTML router
        """
        return HTMLRouter(
            config_loader=self._config_loader,
            extension_manager=self._extension_manager,
            **router_kwargs
        )

    def create_api_router(self, **router_kwargs: Any) -> APIRouter:
        """
        Create an API router with configuration integration.

        Args:
            **router_kwargs: Additional arguments passed to APIRouter

        Returns:
            Configured API router
        """
        return APIRouter(
            config_loader=self._config_loader,
            extension_manager=self._extension_manager,
            **router_kwargs
        )

    def reload_configuration(self) -> None:
        """
        Reload configuration from files.

        This forces a reload of all configuration files and updates
        the route resolver and extension manager.
        """
        if self._config_loader is None:
            # No configuration loader available - cannot reload
            return
        
        # Clear caches and reload
        self._config_loader.clear_cache()
        self._config = self._config_loader.load_config(force_reload=True)

        # Update route resolver
        self._route_resolver.update_configuration(self._config)

        # Update extension manager
        self._extension_manager.update_configuration(self._config)

    def get_environment(self) -> str:
        """
        Get the detected environment.

        Returns:
            Environment name
        """
        if self._environment_detector:
            return self._environment_detector.get_environment()
        return "development"  # Default when no configuration

    def include_router(self, router: Any, **kwargs: Any) -> None:
        """
        Include a router and automatically mount features based on router type.

        Args:
            router: Router to include
            **kwargs: Additional arguments passed to FastAPI include_router
        """
        # Include the router first
        super().include_router(router, **kwargs)
        
        # If it's an HTMLRouter with static file management, mount static files
        if isinstance(router, HTMLRouter) and hasattr(router, 'mount_static_files'):
            router.mount_static_files(self)
        
        # If it's an APIRouter with CORS management, mount CORS middleware
        if isinstance(router, APIRouter) and hasattr(router, 'mount_cors_middleware'):
            router.mount_cors_middleware(self)

    def _get_default_config(self) -> dict[str, Any]:
        """
        Get minimal default configuration for operation without config files.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "app": {
                "name": "beginnings-app",
                "version": "0.1.0",
                "description": "A Beginnings application"
            },
            "routes": {},
            "extensions": {}
        }

    def _load_extensions(self) -> None:
        """Load extensions from configuration."""
        extensions_config = self._config.get("extensions", {})
        if extensions_config:
            self._extension_manager.load_extensions_from_configuration(extensions_config)

    def _setup_error_handlers(self) -> None:
        """Set up content-aware error handling."""
        
        @self.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
            """Handle HTTP exceptions with content-aware responses."""
            return await self._handle_http_exception(request, exc)
        
        # Handle 404 errors for non-existent routes
        @self.exception_handler(404)
        async def not_found_handler(request: Request, exc: Any) -> Any:
            """Handle 404 errors with content-aware responses."""
            # Create HTTPException if we don't have one
            if not isinstance(exc, HTTPException):
                exc = HTTPException(status_code=404, detail="Page not found")
            return await self._handle_http_exception(request, exc)

    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> Any:
        """
        Handle HTTP exceptions with content negotiation.
        
        Args:
            request: The incoming request
            exc: The HTTP exception
            
        Returns:
            Either HTMLResponse or JSONResponse based on request Accept header
        """
        # Check Accept header to determine response format
        accept_header = request.headers.get("accept", "").lower()
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Determine if this should be an HTML response
        wants_html = (
            # Explicit HTML accept header
            "text/html" in accept_header or
            # Browser user agents that don't specify JSON
            (("mozilla" in user_agent or "webkit" in user_agent) and 
             "application/json" not in accept_header) or
            # Non-API paths (don't start with /api)
            not str(request.url.path).startswith("/api")
        ) and "application/json" not in accept_header

        if wants_html:
            # Try to find an HTML router that can render error pages
            html_router = self._find_html_router()
            if html_router and hasattr(html_router, 'render_error_page'):
                return html_router.render_error_page(exc.status_code, exc.detail, request)
            else:
                # Fallback to basic HTML error page
                return self._create_basic_html_error(exc.status_code, exc.detail)
        else:
            # Return JSON error response for API requests
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

    def _find_html_router(self) -> Any:
        """Find the first HTML router in the application."""
        from beginnings.routing.html import HTMLRouter
        
        # Look through registered routers to find an HTMLRouter
        for route in self.routes:
            if hasattr(route, 'router') and isinstance(route.router, HTMLRouter):
                return route.router
        return None

    def _create_basic_html_error(self, status_code: int, detail: str) -> Any:
        """Create a basic HTML error page when no HTML router is available."""
        from fastapi.responses import HTMLResponse
        
        status_messages = {
            404: "Page Not Found",
            500: "Internal Server Error", 
            403: "Forbidden",
            401: "Unauthorized",
            400: "Bad Request"
        }
        
        title = status_messages.get(status_code, "Error")
        
        # Clear, friendly error messages
        friendly_messages = {
            404: "The page you're looking for isn't here",
            500: "Something went wrong on our end",
            403: "You don't have permission to access this page",
            401: "Please log in to continue",
            400: "The request couldn't be processed"
        }
        
        friendly_detail = friendly_messages.get(status_code, "An unexpected error occurred")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} - {title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #f8f9fa;
            color: #000000;
            padding: 20px;
        }}
        
        .error-container {{
            width: auto;
            max-width: 90vw;
        }}
        
        .error-code {{
            font-size: clamp(4rem, 20vw, 8rem);
            font-weight: 900;
            margin-bottom: 0.5rem;
            color: #000000;
            text-align: left;
        }}
        
        .error-message {{
            font-size: clamp(1.2rem, 4vw, 2rem);
            margin-bottom: 1rem;
            color: #404040;
            font-weight: 500;
            text-align: left;
        }}
        
        .error-detail {{
            font-size: clamp(0.9rem, 2.5vw, 1.1rem);
            margin-bottom: 2rem;
            color: #666666;
            line-height: 1.5;
            text-align: left;
        }}
        
        .back-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 12px 24px;
            background: #000000;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.2s ease;
            float: right;
        }}
        
        .back-link:hover {{
            background: #333333;
            text-decoration: none;
            color: white;
        }}
        
        .button-container {{
            text-align: right;
            clear: both;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">{status_code}</div>
        <div class="error-message">{friendly_detail}</div>
        <div class="error-detail">{detail}</div>
        <div class="button-container">
            <a href="#" onclick="history.back(); return false;" class="back-link">
                <span>←</span>
                <span>Back</span>
            </a>
        </div>
    </div>
</body>
</html>"""
        
        return HTMLResponse(content=html_content, status_code=status_code)

    def run(self, host: str = "127.0.0.1", port: int = 8000, **kwargs: Any) -> None:
        """
        Run the application using uvicorn.

        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional arguments passed to uvicorn
        """
        import uvicorn

        # Override with configuration values if available
        app_config = self._config.get("app", {})
        final_host = app_config.get("host", host)
        final_port = app_config.get("port", port)

        uvicorn.run(self, host=final_host, port=final_port, **kwargs)
