"""
Extension loading and management functionality for Beginnings framework.

This module provides functionality for dynamically loading extensions
and managing their lifecycle throughout the application.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from beginnings.extensions.base import (
    BaseExtension,
    ExtensionError,
    ExtensionInitializationError,
    ExtensionLoadError,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


class ExtensionManager:
    """
    Manages the loading and lifecycle of Beginnings extensions.

    Handles extension discovery, dependency resolution, initialization,
    and cleanup operations.
    """

    def __init__(self, app: FastAPI, config: dict[str, Any]) -> None:
        """
        Initialize the extension manager.

        Args:
            app: FastAPI application instance
            config: Application configuration
        """
        self._app = app
        self._config = config
        self._extensions: dict[str, BaseExtension] = {}
        self._load_order: list[str] = []

    def load_extensions_from_configuration(self, extensions_config: dict[str, Any]) -> None:
        """
        Load multiple extensions from configuration.

        Args:
            extensions_config: Dictionary mapping extension paths to their configurations
        """
        for extension_path, config in extensions_config.items():
            try:
                self.load_extension(extension_path, config)
            except Exception as e:
                # Log error but continue with other extensions
                # In production, use proper logging: logger.error(f"Failed to load extension {extension_path}: {e}")
                print(f"Warning: Failed to load extension {extension_path}: {e}")

    def load_extension(
        self,
        extension_class_path: str,
        config: dict[str, Any] | None = None
    ) -> None:
        """
        Load and initialize a single extension.

        Args:
            extension_class_path: Full path to extension class (e.g. 'my_extension.MyExtension')
            config: Optional configuration for the extension

        Raises:
            ExtensionLoadError: If the extension cannot be loaded
            ExtensionInitializationError: If the extension cannot be initialized
        """
        if config is None:
            config = {}

        try:
            # Import the extension class (module.path:ClassName format)
            if ":" not in extension_class_path:
                raise ValueError("Extension path must be in format 'module.path:ClassName'")
            module_path, class_name = extension_class_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            extension_class = getattr(module, class_name)

            # Check if already loaded (use class name as identifier) - before instantiation
            extension_name = extension_class.__name__
            if extension_name in self._extensions:
                raise ExtensionLoadError(f"Extension {extension_name} is already loaded")

            # Create extension instance with configuration
            extension = extension_class(config)

            if not isinstance(extension, BaseExtension):
                raise ExtensionLoadError(
                    f"Extension {extension_class_path} must inherit from BaseExtension"
                )

            # Validate configuration
            validation_errors = extension.validate_config()
            if validation_errors:
                raise ExtensionInitializationError(
                    f"Extension {extension_name} configuration validation failed: {'; '.join(validation_errors)}"
                )

            # Register the extension
            self._extensions[extension_name] = extension
            self._load_order.append(extension_name)

        except ImportError as e:
            raise ExtensionLoadError(f"Failed to import extension {extension_class_path}: {e}") from e
        except AttributeError as e:
            raise ExtensionLoadError(f"Extension class not found: {extension_class_path}: {e}") from e
        except ValueError as e:
            if "Extension path must be in format" in str(e):
                raise ExtensionLoadError(f"Invalid extension path format: {extension_class_path}") from e
            raise ExtensionInitializationError(f"Failed to initialize extension: {e}") from e
        except ExtensionLoadError:
            # Re-raise ExtensionLoadError as-is (including duplicate loading)
            raise
        except ExtensionInitializationError:
            # Re-raise ExtensionInitializationError as-is
            raise
        except Exception as e:
            raise ExtensionInitializationError(f"Failed to initialize extension: {e}") from e

    def get_extension(self, name: str) -> BaseExtension:
        """
        Get a loaded extension by name.

        Args:
            name: Name of the extension

        Returns:
            Extension instance

        Raises:
            ExtensionError: If extension is not found
        """
        if name not in self._extensions:
            raise ExtensionError(f"Extension {name} is not loaded")
        return self._extensions[name]

    def is_extension_loaded(self, name: str) -> bool:
        """
        Check if an extension is loaded.

        Args:
            name: Name of the extension

        Returns:
            True if extension is loaded, False otherwise
        """
        return name in self._extensions

    def get_loaded_extensions(self) -> list[BaseExtension]:
        """
        Get list of loaded extension instances.

        Returns:
            List of extension instances in load order
        """
        return [self._extensions[name] for name in self._load_order]

    def get_loaded_extension_names(self) -> list[str]:
        """
        Get list of loaded extension names.

        Returns:
            List of extension names in load order
        """
        return self._load_order.copy()

    async def startup(self) -> None:
        """Execute startup handlers for all extensions."""
        for extension_name in self._load_order:
            try:
                extension = self._extensions[extension_name]
                startup_handler = extension.get_startup_handler()
                if startup_handler:
                    await startup_handler()
            except Exception as e:
                # Log error but continue
                print(f"Warning: Extension startup handler failed for {extension_name}: {e}")

    async def shutdown(self) -> None:
        """Execute shutdown handlers for all extensions in reverse order."""
        for extension_name in reversed(self._load_order):
            try:
                extension = self._extensions[extension_name]
                shutdown_handler = extension.get_shutdown_handler()
                if shutdown_handler:
                    await shutdown_handler()
            except Exception as e:
                # Log error but continue cleanup
                print(f"Warning: Extension shutdown handler failed for {extension_name}: {e}")

    def update_configuration(self, new_config: dict[str, Any]) -> None:
        """
        Update configuration and reload extensions if needed.

        Args:
            new_config: New configuration dictionary
        """
        self._config = new_config
        # In a full implementation, we might reload extensions here

