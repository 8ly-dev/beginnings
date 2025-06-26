"""
Test suite for extension loading and management.

Tests the extension loading functionality according to Phase 1 planning document
specifications (lines 331-356).
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from fastapi import FastAPI

from beginnings.extensions.base import (
    BaseExtension,
    ExtensionError,
    ExtensionInitializationError,
    ExtensionLoadError,
)
from beginnings.extensions.loader import ExtensionManager


# Test extension classes for testing
class ValidTestExtension(BaseExtension):
    """A valid test extension for testing purposes."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.initialized = False
        self.startup_called = False
        self.shutdown_called = False

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def middleware(endpoint: Callable) -> Callable:
                return endpoint
            return middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return path.startswith("/api/")

    def validate_config(self) -> list[str]:
        errors = []
        if not isinstance(self.config, dict):
            errors.append("Config must be a dictionary")
        return errors


class InvalidTestExtension:
    """An invalid extension that doesn't inherit from BaseExtension."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config


class BrokenTestExtension(BaseExtension):
    """An extension that raises errors during initialization."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        raise ValueError("Initialization failed")

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        return lambda x: lambda y: y

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return False


class ConfigValidationExtension(BaseExtension):
    """Extension that validates its configuration."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        return lambda x: lambda y: y

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return True

    def validate_config(self) -> list[str]:
        errors = []
        if "required_setting" not in self.config:
            errors.append("Missing required_setting")
        if self.config.get("invalid_value") == "bad":
            errors.append("Invalid value for invalid_value")
        return errors


class TestExtensionDiscoveryAndLoading:
    """Test extension discovery and loading functionality."""

    def _create_extension_manager(self) -> ExtensionManager:
        """Create a test extension manager."""
        app = FastAPI()
        config = {"app": {"name": "test"}}
        return ExtensionManager(app, config)

    def test_load_extension_from_module_path_specification(self) -> None:
        """Test loading extension from module.path:ClassName specification."""
        manager = self._create_extension_manager()

        # Load the ValidTestExtension using module path
        config = {"test_setting": "value"}
        manager.load_extension(
            "tests.extensions.test_loader:ValidTestExtension",
            config
        )

        # Check that extension was loaded
        assert manager.is_extension_loaded("ValidTestExtension")
        extension = manager.get_extension("ValidTestExtension")
        assert isinstance(extension, ValidTestExtension)
        assert extension.config == config

    def test_handle_invalid_import_paths_with_clear_error_messages(self) -> None:
        """Test handling invalid import paths with clear error messages."""
        manager = self._create_extension_manager()

        # Test non-existent module
        with pytest.raises(ExtensionLoadError, match="Failed to import extension"):
            manager.load_extension("nonexistent.module:SomeExtension", {})

        # Test malformed path (no colon)
        with pytest.raises(ExtensionLoadError, match="Invalid extension path format"):
            manager.load_extension("malformed_path", {})

        # Test module exists but class doesn't
        with pytest.raises(ExtensionLoadError, match="Extension class not found"):
            manager.load_extension("tests.extensions.test_loader:NonExistentExtension", {})

    def test_extension_module_not_found_scenarios(self) -> None:
        """Test extension module not found scenarios."""
        manager = self._create_extension_manager()

        with pytest.raises(ExtensionLoadError) as exc_info:
            manager.load_extension("definitely.does.not.exist:SomeExtension", {})

        assert "Failed to import extension" in str(exc_info.value)
        assert "definitely.does.not.exist:SomeExtension" in str(exc_info.value)

    def test_validate_extension_class_exists_in_specified_module(self) -> None:
        """Test that extension class exists in specified module."""
        manager = self._create_extension_manager()

        # This should work - class exists
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        assert manager.is_extension_loaded("ValidTestExtension")

        # This should fail - class doesn't exist
        with pytest.raises(ExtensionLoadError, match="Extension class not found"):
            manager.load_extension("tests.extensions.test_loader:NonExistentClass", {})

    def test_extension_instantiation_with_configuration(self) -> None:
        """Test extension instantiation with configuration."""
        manager = self._create_extension_manager()

        config = {
            "setting1": "value1",
            "setting2": 42,
            "nested": {"key": "value"}
        }

        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", config)

        extension = manager.get_extension("ValidTestExtension")
        assert extension.config == config
        assert extension.config["setting1"] == "value1"
        assert extension.config["setting2"] == 42
        assert extension.config["nested"]["key"] == "value"

    def test_handle_extension_constructor_errors_gracefully(self) -> None:
        """Test handling extension constructor errors gracefully."""
        manager = self._create_extension_manager()

        # Extension that raises error in constructor
        with pytest.raises(ExtensionInitializationError, match="Failed to initialize extension"):
            manager.load_extension("tests.extensions.test_loader:BrokenTestExtension", {})

        # Extension should not be registered if initialization fails
        assert not manager.is_extension_loaded("BrokenTestExtension")


class TestExtensionInterfaceValidation:
    """Test extension interface validation functionality."""

    def _create_extension_manager(self) -> ExtensionManager:
        """Create a test extension manager."""
        app = FastAPI()
        config = {"app": {"name": "test"}}
        return ExtensionManager(app, config)

    def test_verify_extension_inherits_from_base_extension(self) -> None:
        """Test that extension inherits from BaseExtension."""
        manager = self._create_extension_manager()

        # Valid extension should work
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        assert manager.is_extension_loaded("ValidTestExtension")

        # Invalid extension should fail (doesn't inherit from BaseExtension)
        with pytest.raises(ExtensionLoadError, match="must inherit from BaseExtension"):
            manager.load_extension("tests.extensions.test_loader:InvalidTestExtension", {})

    def test_check_all_required_abstract_methods_are_implemented(self) -> None:
        """Test that all required abstract methods are implemented."""
        manager = self._create_extension_manager()

        # ValidTestExtension implements all required methods
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        extension = manager.get_extension("ValidTestExtension")

        # Check that required methods exist and are callable
        assert hasattr(extension, "get_middleware_factory")
        assert callable(extension.get_middleware_factory)

        assert hasattr(extension, "should_apply_to_route")
        assert callable(extension.should_apply_to_route)

        # Test that methods return expected types
        middleware_factory = extension.get_middleware_factory()
        assert callable(middleware_factory)

        route_applies = extension.should_apply_to_route("/api/test", ["GET"], {})
        assert isinstance(route_applies, bool)

    def test_validate_method_signatures_match_interface_specification(self) -> None:
        """Test that method signatures match interface specification."""
        manager = self._create_extension_manager()
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        extension = manager.get_extension("ValidTestExtension")

        # Test get_middleware_factory signature
        middleware_factory = extension.get_middleware_factory()
        assert callable(middleware_factory)

        # Test middleware factory can be called with route config
        route_config = {"test": "config"}
        middleware = middleware_factory(route_config)
        assert callable(middleware)

        # Test should_apply_to_route signature
        result = extension.should_apply_to_route("/test/path", ["GET", "POST"], {"config": "value"})
        assert isinstance(result, bool)

    def test_extension_configuration_validation_method(self) -> None:
        """Test extension configuration validation method."""
        manager = self._create_extension_manager()

        # Test extension with valid config
        valid_config = {"required_setting": "present"}
        manager.load_extension("tests.extensions.test_loader:ConfigValidationExtension", valid_config)
        extension = manager.get_extension("ConfigValidationExtension")

        errors = extension.validate_config()
        assert errors == []  # No validation errors

        # Test extension with invalid config (use new manager to avoid duplicate loading)
        invalid_manager = self._create_extension_manager()
        with pytest.raises(ExtensionInitializationError, match="configuration validation failed"):
            invalid_config = {"invalid_value": "bad"}  # Missing required_setting
            invalid_manager.load_extension("tests.extensions.test_loader:ConfigValidationExtension", invalid_config)

    def test_verify_optional_startup_shutdown_handler_implementation(self) -> None:
        """Test optional startup/shutdown handler implementation."""
        manager = self._create_extension_manager()
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        extension = manager.get_extension("ValidTestExtension")

        # Test that optional methods exist and return correct types
        startup_handler = extension.get_startup_handler()
        shutdown_handler = extension.get_shutdown_handler()

        # These can be None (optional) or callables
        assert startup_handler is None or callable(startup_handler)
        assert shutdown_handler is None or callable(shutdown_handler)


class TestExtensionLifecycleManagement:
    """Test extension lifecycle management functionality."""

    def _create_extension_manager(self) -> ExtensionManager:
        """Create a test extension manager."""
        app = FastAPI()
        config = {"app": {"name": "test"}}
        return ExtensionManager(app, config)

    def test_extension_initialization_during_application_startup(self) -> None:
        """Test extension initialization during application startup."""
        manager = self._create_extension_manager()

        # Load extension
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})

        # Check that extension is loaded and available
        assert manager.is_extension_loaded("ValidTestExtension")
        extension = manager.get_extension("ValidTestExtension")
        assert isinstance(extension, ValidTestExtension)

    def test_configuration_injection_during_extension_creation(self) -> None:
        """Test configuration injection during extension creation."""
        manager = self._create_extension_manager()

        config = {
            "database_url": "sqlite:///test.db",
            "cache_ttl": 300,
            "features": ["auth", "logging"]
        }

        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", config)
        extension = manager.get_extension("ValidTestExtension")

        # Verify configuration was properly injected
        assert extension.config == config
        assert extension.config["database_url"] == "sqlite:///test.db"
        assert extension.config["cache_ttl"] == 300
        assert extension.config["features"] == ["auth", "logging"]

    def test_startup_handler_execution_order_and_error_handling(self) -> None:
        """Test startup handler execution and error handling."""
        manager = self._create_extension_manager()

        # Load an extension
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})

        # Test that startup can be called without errors
        # Note: ValidTestExtension returns None for startup handler
        import asyncio
        asyncio.run(manager.startup())

        # Extension should still be loaded even if startup handler is None
        assert manager.is_extension_loaded("ValidTestExtension")

    def test_shutdown_handler_execution_and_cleanup(self) -> None:
        """Test shutdown handler execution and cleanup."""
        manager = self._create_extension_manager()

        # Load an extension
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})

        # Test that shutdown can be called without errors
        import asyncio
        asyncio.run(manager.shutdown())

        # Extension should still be registered after shutdown
        # (shutdown doesn't unload extensions, just calls their cleanup)
        assert manager.is_extension_loaded("ValidTestExtension")

    def test_extension_failure_isolation_from_other_extensions(self) -> None:
        """Test that extension failures don't affect other extensions."""
        manager = self._create_extension_manager()

        # Load a valid extension first
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        assert manager.is_extension_loaded("ValidTestExtension")

        # Try to load a broken extension - should fail but not affect the first one
        with pytest.raises(ExtensionInitializationError):
            manager.load_extension("tests.extensions.test_loader:BrokenTestExtension", {})

        # First extension should still be loaded and functional
        assert manager.is_extension_loaded("ValidTestExtension")
        extension = manager.get_extension("ValidTestExtension")
        assert isinstance(extension, ValidTestExtension)

    def test_multiple_extension_loading_and_management(self) -> None:
        """Test loading and managing multiple extensions."""
        manager = self._create_extension_manager()

        # Load multiple extensions with different configs
        config1 = {"name": "extension1", "priority": 1}
        config2 = {"name": "extension2", "priority": 2, "required_setting": "present"}

        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", config1)
        manager.load_extension("tests.extensions.test_loader:ConfigValidationExtension", config2)

        # Both should be loaded
        assert manager.is_extension_loaded("ValidTestExtension")
        assert manager.is_extension_loaded("ConfigValidationExtension")

        # Check that each has its own config
        ext1 = manager.get_extension("ValidTestExtension")
        ext2 = manager.get_extension("ConfigValidationExtension")

        assert ext1.config == config1
        assert ext2.config == config2

        # Check extension names list
        loaded_names = manager.get_loaded_extension_names()
        assert "ValidTestExtension" in loaded_names
        assert "ConfigValidationExtension" in loaded_names
        assert len(loaded_names) == 2

    def test_extension_duplicate_loading_prevention(self) -> None:
        """Test that duplicate extension loading is prevented."""
        manager = self._create_extension_manager()

        # Load extension first time
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})
        assert manager.is_extension_loaded("ValidTestExtension")

        # Try to load same extension again - should fail
        with pytest.raises(ExtensionLoadError, match="is already loaded"):
            manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {})

        # Should still have only one instance
        extensions = manager.get_loaded_extensions()
        assert len(extensions) == 1

    def test_extension_registry_access_methods(self) -> None:
        """Test extension registry access methods."""
        manager = self._create_extension_manager()

        # Initially empty
        assert manager.get_loaded_extension_names() == []
        assert manager.get_loaded_extensions() == []
        assert not manager.is_extension_loaded("any_name")

        # Load some extensions
        manager.load_extension("tests.extensions.test_loader:ValidTestExtension", {"id": 1})
        manager.load_extension("tests.extensions.test_loader:ConfigValidationExtension", {"id": 2, "required_setting": "present"})

        # Test registry access
        names = manager.get_loaded_extension_names()
        assert len(names) == 2
        assert "ValidTestExtension" in names
        assert "ConfigValidationExtension" in names

        extensions = manager.get_loaded_extensions()
        assert len(extensions) == 2
        assert all(isinstance(ext, BaseExtension) for ext in extensions)

        # Test individual access
        assert manager.is_extension_loaded("ValidTestExtension")
        assert manager.is_extension_loaded("ConfigValidationExtension")
        assert not manager.is_extension_loaded("NonExistentExtension")

        # Test get_extension method
        ext = manager.get_extension("ValidTestExtension")
        assert isinstance(ext, ValidTestExtension)
        assert ext.config["id"] == 1

        # Test error when getting non-existent extension
        with pytest.raises(ExtensionError, match="is not loaded"):
            manager.get_extension("NonExistentExtension")
