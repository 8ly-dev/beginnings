"""
Middleware chain building functionality for Beginnings framework.

This module provides middleware chain construction from extensions
and route configuration with proper execution ordering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from beginnings.extensions.loader import ExtensionManager


class MiddlewareChainBuilder:
    """
    Builds middleware chains for routes based on extensions and configuration.

    Coordinates with the extension manager to build appropriate middleware
    chains for each route based on extension applicability and configuration.
    """

    def __init__(self, extension_manager: ExtensionManager) -> None:
        """
        Initialize middleware chain builder.

        Args:
            extension_manager: Extension manager for accessing loaded extensions
        """
        self._extension_manager = extension_manager

    def build_middleware_chain(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]] | None:
        """
        Build middleware chain for a specific route.

        Args:
            path: Route path
            methods: HTTP methods for the route
            route_config: Resolved configuration for the route

        Returns:
            Composed middleware function or None if no middleware applies
        """
        # Get applicable extensions for this route
        applicable_extensions = self._get_applicable_extensions(path, methods, route_config)

        if not applicable_extensions:
            return None

        # Build middleware functions from extensions with security-first ordering
        middleware_functions = []
        
        # Define security extension types that must execute first
        security_extensions = ['RateLimitExtension', 'SecurityHeadersExtension', 'AuthExtension']
        
        # Sort extensions: security extensions first, then others
        security_middleware = []
        other_middleware = []
        
        for extension in applicable_extensions:
            try:
                middleware_factory = extension.get_middleware_factory()
                if middleware_factory:
                    middleware = middleware_factory(route_config)
                    if middleware:
                        if extension.__class__.__name__ in security_extensions:
                            security_middleware.append(middleware)
                        else:
                            other_middleware.append(middleware)
            except Exception as e:
                # Log error but continue with other middleware
                # In a real implementation, we'd use proper logging
                print(f"Warning: Middleware factory failed for extension: {e}")
        
        # Combine: security middleware first (execute first), then other middleware (execute last)
        # Remember: chain is reversed, so first added = last executed
        middleware_functions = security_middleware + other_middleware

        if not middleware_functions:
            return None
        # Compose middleware functions into a chain
        return self._compose_middleware_chain(middleware_functions)

    def _get_applicable_extensions(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> list[Any]:
        """
        Get extensions that apply to the given route.

        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration

        Returns:
            List of applicable extension instances
        """
        applicable = []

        for extension in self._extension_manager.get_loaded_extensions():
            try:
                if extension.should_apply_to_route(path, methods, route_config):
                    applicable.append(extension)
            except Exception as e:
                # Log error but continue
                print(f"Warning: Extension applicability check failed: {e}")

        return applicable

    def _compose_middleware_chain(
        self,
        middleware_functions: list[Callable[..., Any]]
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Compose multiple middleware functions into a single chain.

        Args:
            middleware_functions: List of middleware functions

        Returns:
            Composed middleware function
        """
        def compose_middleware(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            # Apply middleware in reverse order (LIFO execution)
            result = endpoint
            for middleware in reversed(middleware_functions):
                result = middleware(result)
            return result

        return compose_middleware
