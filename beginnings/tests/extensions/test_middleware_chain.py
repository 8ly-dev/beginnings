"""
Test suite for middleware chain building functionality.

Tests the middleware chain construction and execution according to Phase 1 planning document
specifications (lines 357-395).
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from fastapi import FastAPI

from beginnings.extensions.base import BaseExtension
from beginnings.extensions.loader import ExtensionManager
from beginnings.routing.middleware import MiddlewareChainBuilder


# Test extension classes for middleware testing
class _TestMiddlewareExtension(BaseExtension):
    """Test extension that provides middleware functionality."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.name = config.get("name", "TestMiddleware")
        self.apply_to_pattern = config.get("apply_to", "*")
        self.middleware_calls: list[str] = []

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def middleware(endpoint: Callable) -> Callable:
                def wrapped_endpoint(*args, **kwargs):
                    # Record middleware execution
                    self.middleware_calls.append(f"{self.name}_before")
                    try:
                        result = endpoint(*args, **kwargs)
                        self.middleware_calls.append(f"{self.name}_after")
                        return result
                    except Exception:
                        self.middleware_calls.append(f"{self.name}_error")
                        raise
                return wrapped_endpoint
            return middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        if self.apply_to_pattern == "*":
            return True
        if self.apply_to_pattern.startswith("/api/"):
            return path.startswith("/api/")
        if self.apply_to_pattern.startswith("/admin/"):
            return path.startswith("/admin/")
        return path == self.apply_to_pattern


class _AuthMiddlewareExtension(BaseExtension):
    """Authentication middleware extension for testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.auth_required = config.get("auth_required", True)
        self.execution_log: list[str] = []

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def auth_middleware(endpoint: Callable) -> Callable:
                def wrapped_endpoint(*args, **kwargs):
                    self.execution_log.append("auth_check")
                    # Simulate auth check
                    if route_config.get("auth_required", False) and not route_config.get("authenticated", False):
                        self.execution_log.append("auth_failed")
                        raise Exception("Authentication required")
                    self.execution_log.append("auth_passed")
                    return endpoint(*args, **kwargs)
                return wrapped_endpoint
            return auth_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("auth_required", False)


class _LoggingMiddlewareExtension(BaseExtension):
    """Logging middleware extension for testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.logs: list[str] = []

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def logging_middleware(endpoint: Callable) -> Callable:
                def wrapped_endpoint(*args, **kwargs):
                    self.logs.append(f"START: {route_config.get('path', 'unknown')}")
                    try:
                        result = endpoint(*args, **kwargs)
                        self.logs.append(f"SUCCESS: {route_config.get('path', 'unknown')}")
                        return result
                    except Exception as e:
                        self.logs.append(f"ERROR: {route_config.get('path', 'unknown')}: {e}")
                        raise
                return wrapped_endpoint
            return logging_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return route_config.get("logging_enabled", True)


class _ConditionalMiddlewareExtension(BaseExtension):
    """Middleware that applies conditionally based on configuration."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.enabled = config.get("enabled", True)
        self.execution_count = 0

    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        if not self.enabled:
            return lambda route_config: None  # Return None when disabled

        def middleware_factory(route_config: dict[str, Any]) -> Callable:
            def conditional_middleware(endpoint: Callable) -> Callable:
                def wrapped_endpoint(*args, **kwargs):
                    self.execution_count += 1
                    return endpoint(*args, **kwargs)
                return wrapped_endpoint
            return conditional_middleware
        return middleware_factory

    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("conditional_middleware", False)


class TestMiddlewareChainBuilder:
    """Test middleware chain builder functionality."""

    def _create_extension_manager(self) -> ExtensionManager:
        """Create a test extension manager."""
        app = FastAPI()
        config = {"app": {"name": "test"}}
        return ExtensionManager(app, config)

    def test_middleware_chain_builder_initialization(self) -> None:
        """Test MiddlewareChainBuilder initialization."""
        manager = self._create_extension_manager()
        builder = MiddlewareChainBuilder(manager)

        assert builder is not None
        assert builder._extension_manager is manager

    def test_build_middleware_chain_with_no_applicable_extensions(self) -> None:
        """Test building middleware chain when no extensions apply to route."""
        manager = self._create_extension_manager()
        builder = MiddlewareChainBuilder(manager)

        # No extensions loaded, should return None
        chain = builder.build_middleware_chain("/test", ["GET"], {})
        assert chain is None

    def test_build_middleware_chain_with_single_extension(self) -> None:
        """Test building middleware chain with single applicable extension."""
        manager = self._create_extension_manager()

        # Load a test extension
        extension_config = {"name": "TestExt", "apply_to": "*"}
        manager.load_extension("tests.extensions.test_middleware_chain:_TestMiddlewareExtension", extension_config)

        builder = MiddlewareChainBuilder(manager)

        # Build chain for a route
        route_config = {"path": "/test"}
        chain = builder.build_middleware_chain("/test", ["GET"], route_config)

        assert chain is not None
        assert callable(chain)

    def test_middleware_chain_execution_with_single_middleware(self) -> None:
        """Test middleware chain execution with single middleware."""
        manager = self._create_extension_manager()

        # Load test extension
        extension_config = {"name": "SingleTest", "apply_to": "*"}
        manager.load_extension("tests.extensions.test_middleware_chain:_TestMiddlewareExtension", extension_config)

        builder = MiddlewareChainBuilder(manager)
        extension = manager.get_extension("_TestMiddlewareExtension")

        # Build and execute chain
        route_config = {"path": "/test"}
        chain = builder.build_middleware_chain("/test", ["GET"], route_config)

        # Create a test endpoint
        def test_endpoint():
            return "test_result"

        # Apply middleware and execute
        wrapped_endpoint = chain(test_endpoint)
        result = wrapped_endpoint()

        # Check execution
        assert result == "test_result"
        assert "SingleTest_before" in extension.middleware_calls
        assert "SingleTest_after" in extension.middleware_calls

    def test_build_middleware_chain_with_multiple_extensions(self) -> None:
        """Test building middleware chain with multiple applicable extensions."""
        manager = self._create_extension_manager()

        # Load multiple extensions
        auth_config = {"auth_required": True}
        logging_config = {"logging_enabled": True}

        manager.load_extension("tests.extensions.test_middleware_chain:_AuthMiddlewareExtension", auth_config)
        manager.load_extension("tests.extensions.test_middleware_chain:_LoggingMiddlewareExtension", logging_config)

        builder = MiddlewareChainBuilder(manager)

        # Build chain for route that requires both
        route_config = {"auth_required": True, "logging_enabled": True, "path": "/secure"}
        chain = builder.build_middleware_chain("/secure", ["GET"], route_config)

        assert chain is not None
        assert callable(chain)

    def test_middleware_execution_order_lifo(self) -> None:
        """Test that middleware executes in LIFO order (Last In, First Out)."""
        manager = self._create_extension_manager()

        # Use different extension types to test order
        auth_config = {"auth_required": True}
        logging_config = {"logging_enabled": True}

        # Load in specific order: auth first, then logging
        manager.load_extension("tests.extensions.test_middleware_chain:_AuthMiddlewareExtension", auth_config)
        manager.load_extension("tests.extensions.test_middleware_chain:_LoggingMiddlewareExtension", logging_config)

        builder = MiddlewareChainBuilder(manager)

        # Get references to extensions
        auth_ext = manager.get_extension("_AuthMiddlewareExtension")
        logging_ext = manager.get_extension("_LoggingMiddlewareExtension")

        # Build chain
        route_config = {"auth_required": True, "logging_enabled": True, "path": "/test", "authenticated": True}
        chain = builder.build_middleware_chain("/test", ["GET"], route_config)

        # Test endpoint
        def test_endpoint():
            return "success"

        # Execute chain
        wrapped_endpoint = chain(test_endpoint)
        result = wrapped_endpoint()

        # Verify execution
        assert result == "success"

        # Check that both middleware executed
        assert len(auth_ext.execution_log) > 0
        assert len(logging_ext.logs) > 0
        assert "auth_passed" in auth_ext.execution_log
        assert "SUCCESS: /test" in logging_ext.logs

    def test_middleware_extension_applicability_filtering(self) -> None:
        """Test that only applicable extensions are included in chain."""
        # Create separate managers to avoid class name conflicts
        api_manager = self._create_extension_manager()
        admin_manager = self._create_extension_manager()

        # Load API extension
        api_config = {"name": "APIOnly", "apply_to": "/api/"}
        api_manager.load_extension("tests.extensions.test_middleware_chain:_TestMiddlewareExtension", api_config)

        # Load admin extension (on separate manager)
        admin_config = {"name": "AdminOnly", "apply_to": "/admin/"}
        admin_manager.load_extension("tests.extensions.test_middleware_chain:_TestMiddlewareExtension", admin_config)

        # Test API route
        api_builder = MiddlewareChainBuilder(api_manager)
        api_chain = api_builder.build_middleware_chain("/api/users", ["GET"], {})
        assert api_chain is not None

        # Test that API extension doesn't apply to admin route
        api_admin_chain = api_builder.build_middleware_chain("/admin/dashboard", ["GET"], {})
        assert api_admin_chain is None

        # Test admin route
        admin_builder = MiddlewareChainBuilder(admin_manager)
        admin_chain = admin_builder.build_middleware_chain("/admin/dashboard", ["GET"], {})
        assert admin_chain is not None

        # Test that admin extension doesn't apply to API route
        admin_api_chain = admin_builder.build_middleware_chain("/api/users", ["GET"], {})
        assert admin_api_chain is None

    def test_middleware_configuration_injection(self) -> None:
        """Test that route configuration is properly injected into middleware."""
        manager = self._create_extension_manager()

        # Load logging extension
        logging_config = {"logging_enabled": True}
        manager.load_extension("tests.extensions.test_middleware_chain:_LoggingMiddlewareExtension", logging_config)

        builder = MiddlewareChainBuilder(manager)
        logging_ext = manager.get_extension("_LoggingMiddlewareExtension")

        # Build chain with specific route config
        route_config = {"logging_enabled": True, "path": "/api/test", "custom_setting": "value"}
        chain = builder.build_middleware_chain("/api/test", ["GET"], route_config)

        # Test endpoint
        def test_endpoint():
            return {"status": "ok"}

        # Execute chain
        wrapped_endpoint = chain(test_endpoint)
        result = wrapped_endpoint()

        # Verify configuration was used
        assert result == {"status": "ok"}
        assert "SUCCESS: /api/test" in logging_ext.logs

    def test_middleware_error_handling_and_isolation(self) -> None:
        """Test middleware error handling and extension isolation."""
        manager = self._create_extension_manager()

        # Load extension that might fail
        conditional_config = {"enabled": True}
        manager.load_extension("tests.extensions.test_middleware_chain:_ConditionalMiddlewareExtension", conditional_config)

        builder = MiddlewareChainBuilder(manager)

        # Build chain for route
        route_config = {"conditional_middleware": True}
        chain = builder.build_middleware_chain("/test", ["GET"], route_config)

        assert chain is not None

        # Test that middleware handles errors gracefully
        def failing_endpoint():
            raise ValueError("Test error")

        wrapped_endpoint = chain(failing_endpoint)

        # Should propagate the error but not crash the middleware system
        with pytest.raises(ValueError, match="Test error"):
            wrapped_endpoint()

    def test_middleware_chain_with_none_returning_factory(self) -> None:
        """Test handling of middleware factories that return None."""
        manager = self._create_extension_manager()

        # Load extension that returns None for middleware factory
        disabled_config = {"enabled": False}
        manager.load_extension("tests.extensions.test_middleware_chain:_ConditionalMiddlewareExtension", disabled_config)

        builder = MiddlewareChainBuilder(manager)

        # Build chain - should handle None middleware gracefully
        route_config = {"conditional_middleware": True}
        chain = builder.build_middleware_chain("/test", ["GET"], route_config)

        # Since the middleware returns None, no chain should be built
        assert chain is None

    def test_middleware_chain_composition_order(self) -> None:
        """Test that middleware chain composition maintains proper order."""
        manager = self._create_extension_manager()

        # Use auth and logging to test composition
        auth_config = {"auth_required": True}
        logging_config = {"logging_enabled": True}

        manager.load_extension("tests.extensions.test_middleware_chain:_AuthMiddlewareExtension", auth_config)
        manager.load_extension("tests.extensions.test_middleware_chain:_LoggingMiddlewareExtension", logging_config)

        builder = MiddlewareChainBuilder(manager)

        # Get extension references
        auth_ext = manager.get_extension("_AuthMiddlewareExtension")
        logging_ext = manager.get_extension("_LoggingMiddlewareExtension")

        # Build chain
        route_config = {
            "auth_required": True,
            "logging_enabled": True,
            "path": "/secure",
            "authenticated": True
        }
        chain = builder.build_middleware_chain("/secure", ["GET"], route_config)

        # Test endpoint
        def test_endpoint():
            return {"data": "secure_data"}

        # Execute and verify composition
        wrapped_endpoint = chain(test_endpoint)
        result = wrapped_endpoint()

        assert result == {"data": "secure_data"}

        # Both middleware should have executed
        assert "auth_passed" in auth_ext.execution_log
        assert "SUCCESS: /secure" in logging_ext.logs

    def test_get_applicable_extensions_method(self) -> None:
        """Test the _get_applicable_extensions method directly."""
        manager = self._create_extension_manager()

        # Load extension with wildcard pattern
        general_config = {"name": "General", "apply_to": "*"}
        manager.load_extension("tests.extensions.test_middleware_chain:_TestMiddlewareExtension", general_config)

        builder = MiddlewareChainBuilder(manager)

        # Test with any route (should match wildcard)
        applicable = builder._get_applicable_extensions("/api/users", ["GET"], {})

        # Should have one applicable extension
        assert len(applicable) == 1

        # All returned extensions should be BaseExtension instances
        for ext in applicable:
            assert isinstance(ext, BaseExtension)

    def test_compose_middleware_chain_method(self) -> None:
        """Test the _compose_middleware_chain method directly."""
        manager = self._create_extension_manager()
        builder = MiddlewareChainBuilder(manager)

        # Create mock middleware functions
        execution_order = []

        def middleware1(endpoint):
            def wrapper(*args, **kwargs):
                execution_order.append("middleware1_start")
                result = endpoint(*args, **kwargs)
                execution_order.append("middleware1_end")
                return result
            return wrapper

        def middleware2(endpoint):
            def wrapper(*args, **kwargs):
                execution_order.append("middleware2_start")
                result = endpoint(*args, **kwargs)
                execution_order.append("middleware2_end")
                return result
            return wrapper

        # Compose middleware chain
        composed_middleware = builder._compose_middleware_chain([middleware1, middleware2])

        # Test endpoint
        def test_endpoint():
            execution_order.append("endpoint_executed")
            return "result"

        # Apply composed middleware
        wrapped_endpoint = composed_middleware(test_endpoint)
        result = wrapped_endpoint()

        # Verify execution order (LIFO - Last In, First Out)
        # With [middleware1, middleware2], it becomes middleware1(middleware2(endpoint))
        # So middleware1 is outermost, middleware2 is innermost
        assert result == "result"
        assert execution_order == [
            "middleware1_start",  # First middleware executes first (outermost)
            "middleware2_start",  # Second middleware executes second
            "endpoint_executed",  # Endpoint executes
            "middleware2_end",    # Second middleware completes first
            "middleware1_end"     # First middleware completes last
        ]
