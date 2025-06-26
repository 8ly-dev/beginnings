"""
Core application class for Beginnings framework.

This module contains the main App class that provides the foundation
for building web applications with Beginnings with configuration-driven enhancements.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

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
        # Initialize configuration system first
        self._environment_detector = EnvironmentDetector(config_dir, environment)
        self._config_loader = EnhancedConfigLoader(
            self._environment_detector.get_config_dir(),
            self._environment_detector.get_environment()
        )

        # Load configuration
        self._config = self._config_loader.load_config()

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
        return self._environment_detector.get_environment()

    def _load_extensions(self) -> None:
        """Load extensions from configuration."""
        extensions_config = self._config.get("extensions", {})
        if extensions_config:
            self._extension_manager.load_extensions_from_configuration(extensions_config)


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
