"""Base test classes for extension testing."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, Dict, List, Optional, Type, Callable
from unittest.mock import MagicMock, AsyncMock
import pytest

from ..core.app import App
from ..extensions.base import BaseExtension
from .fixtures import ExtensionFixtures
from .mocks import MockBeginningsApp, MockRequest, MockResponse
from .assertions import ExtensionAssertions


class ExtensionTestMixin:
    """Mixin providing extension testing utilities."""
    
    def setUp(self):
        """Set up extension test environment."""
        super().setUp()
        self.fixtures = ExtensionFixtures()
        self.assertions = ExtensionAssertions()
        self.mock_app = MockBeginningsApp()
        
    def create_extension(
        self, 
        extension_class: Type[BaseExtension], 
        config: Optional[Dict[str, Any]] = None
    ) -> BaseExtension:
        """Create extension instance with test configuration.
        
        Args:
            extension_class: Extension class to instantiate
            config: Extension configuration (uses defaults if None)
            
        Returns:
            Configured extension instance
        """
        if config is None:
            config = self.fixtures.get_default_config()
        
        return extension_class(config)
    
    def create_mock_request(
        self,
        method: str = "GET",
        path: str = "/test",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> MockRequest:
        """Create mock request for testing.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            query_params: Query parameters
            body: Request body
            
        Returns:
            Mock request object
        """
        return MockRequest(
            method=method,
            path=path,
            headers=headers or {},
            query_params=query_params or {},
            body=body
        )
    
    def create_mock_response(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[bytes] = None
    ) -> MockResponse:
        """Create mock response for testing.
        
        Args:
            status_code: HTTP status code
            headers: Response headers
            content: Response content
            
        Returns:
            Mock response object
        """
        return MockResponse(
            status_code=status_code,
            headers=headers or {},
            content=content
        )
    
    async def run_middleware(
        self,
        middleware_instance,
        request: MockRequest,
        call_next: Optional[Callable] = None
    ):
        """Run middleware with mock request.
        
        Args:
            middleware_instance: Middleware instance to test
            request: Mock request
            call_next: Mock call_next function
            
        Returns:
            Middleware response
        """
        if call_next is None:
            call_next = AsyncMock(return_value=self.create_mock_response())
        
        return await middleware_instance.dispatch(request, call_next)
    
    def assert_extension_config_valid(self, extension: BaseExtension):
        """Assert that extension configuration is valid.
        
        Args:
            extension: Extension to validate
        """
        self.assertions.assert_config_valid(extension)
    
    def assert_middleware_applies_to_route(
        self, 
        extension: BaseExtension,
        path: str,
        methods: List[str],
        route_config: Optional[Dict[str, Any]] = None
    ):
        """Assert that middleware applies to given route.
        
        Args:
            extension: Extension to test
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
        """
        should_apply = extension.should_apply_to_route(
            path, methods, route_config or {}
        )
        assert should_apply, f"Extension should apply to route {path} {methods}"
    
    def assert_middleware_skips_route(
        self, 
        extension: BaseExtension,
        path: str,
        methods: List[str],
        route_config: Optional[Dict[str, Any]] = None
    ):
        """Assert that middleware skips given route.
        
        Args:
            extension: Extension to test
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
        """
        should_apply = extension.should_apply_to_route(
            path, methods, route_config or {}
        )
        assert not should_apply, f"Extension should not apply to route {path} {methods}"


class ExtensionTestCase(unittest.TestCase, ExtensionTestMixin):
    """Base test case for extension testing with unittest."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()


class AsyncExtensionTestCase(unittest.IsolatedAsyncioTestCase, ExtensionTestMixin):
    """Base async test case for extension testing."""
    
    async def asyncSetUp(self):
        """Set up async test case."""
        self.fixtures = ExtensionFixtures()
        self.assertions = ExtensionAssertions()
        self.mock_app = MockBeginningsApp()


# Pytest fixtures for extension testing

@pytest.fixture
def extension_fixtures():
    """Provide extension test fixtures."""
    return ExtensionFixtures()


@pytest.fixture
def extension_assertions():
    """Provide extension assertions."""
    return ExtensionAssertions()


@pytest.fixture
def mock_app():
    """Provide mock Beginnings app."""
    return MockBeginningsApp()


@pytest.fixture
def mock_request():
    """Provide mock request."""
    return MockRequest()


@pytest.fixture
def mock_response():
    """Provide mock response."""
    return MockResponse()


@pytest.fixture
def extension_config():
    """Provide default extension configuration."""
    return ExtensionFixtures().get_default_config()


@pytest.fixture
def auth_extension_config():
    """Provide auth extension configuration."""
    return ExtensionFixtures().get_auth_config()


@pytest.fixture
def middleware_extension_config():
    """Provide middleware extension configuration."""
    return ExtensionFixtures().get_middleware_config()


@pytest.fixture
def integration_extension_config():
    """Provide integration extension configuration."""
    return ExtensionFixtures().get_integration_config()


# Pytest markers for extension testing

pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with extension testing markers."""
    config.addinivalue_line(
        "markers", "extension: mark test as extension test"
    )
    config.addinivalue_line(
        "markers", "middleware: mark test as middleware test"
    )
    config.addinivalue_line(
        "markers", "auth_provider: mark test as auth provider test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Decorators for extension testing

def extension_test(extension_type: str = "middleware"):
    """Decorator to mark and configure extension tests.
    
    Args:
        extension_type: Type of extension being tested
    """
    def decorator(func):
        func = pytest.mark.extension(func)
        func = getattr(pytest.mark, extension_type)(func)
        return func
    return decorator


def async_extension_test(extension_type: str = "middleware"):
    """Decorator for async extension tests.
    
    Args:
        extension_type: Type of extension being tested
    """
    def decorator(func):
        func = pytest.mark.asyncio(func)
        func = pytest.mark.extension(func)
        func = getattr(pytest.mark, extension_type)(func)
        return func
    return decorator


def slow_test(func):
    """Decorator to mark slow tests."""
    return pytest.mark.slow(func)


def skip_if_missing_deps(*deps):
    """Skip test if dependencies are missing.
    
    Args:
        *deps: Required dependencies
    """
    def decorator(func):
        for dep in deps:
            try:
                __import__(dep)
            except ImportError:
                return pytest.mark.skip(f"Missing dependency: {dep}")(func)
        return func
    return decorator