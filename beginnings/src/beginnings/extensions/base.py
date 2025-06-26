"""
Base extension interface for Beginnings framework.

This module defines the base extension interface that all
Beginnings extensions must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Awaitable


class ExtensionError(Exception):
    """Base exception for extension-related errors."""


class ExtensionLoadError(ExtensionError):
    """Raised when an extension fails to load."""


class ExtensionInitializationError(ExtensionError):
    """Raised when an extension fails to initialize."""


class BaseExtension(ABC):
    """
    Abstract base class for Beginnings extensions.

    All extensions must inherit from this class and implement
    the required methods to integrate with the framework.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the extension with its configuration.

        Args:
            config: Extension configuration dictionary
        """
        self.config = config

    @abstractmethod
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for this extension.

        Returns:
            Middleware factory function that takes route config and returns middleware
        """
        pass

    @abstractmethod
    def should_apply_to_route(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> bool:
        """
        Determine if this extension should apply to a specific route.

        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration

        Returns:
            True if extension applies to this route
        """
        pass

    def get_startup_handler(self) -> Callable[[], Awaitable[None]] | None:
        """
        Get startup handler for this extension.

        Returns:
            Async startup handler or None
        """
        return None

    def get_shutdown_handler(self) -> Callable[[], Awaitable[None]] | None:
        """
        Get shutdown handler for this extension.

        Returns:
            Async shutdown handler or None
        """
        return None

    def validate_config(self) -> list[str]:
        """
        Validate the extension configuration.

        Returns:
            List of error messages (empty if valid)
        """
        return []
