"""Pytest configuration for extension testing."""

import pytest
import asyncio
from typing import Any, Dict

from beginnings.testing.fixtures import BeginningsTestFixtures
from beginnings.testing.mocks import (
    MockBeginningsApp, MockRequest, MockResponse, 
    MockHTTPClient, MockDatabase, MockLogger
)
from beginnings.testing.assertions import ExtensionAssertions


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def beginnings_fixtures():
    """Provide comprehensive test fixtures."""
    return BeginningsTestFixtures()


@pytest.fixture
def extension_config(beginnings_fixtures):
    """Provide default extension configuration."""
    return beginnings_fixtures.extensions.get_default_config()


@pytest.fixture
def middleware_config(beginnings_fixtures):
    """Provide middleware extension configuration."""
    return beginnings_fixtures.extensions.get_middleware_config()


@pytest.fixture
def auth_config(beginnings_fixtures):
    """Provide auth extension configuration."""
    return beginnings_fixtures.extensions.get_auth_config()


@pytest.fixture
def integration_config(beginnings_fixtures):
    """Provide integration extension configuration."""
    return beginnings_fixtures.extensions.get_integration_config()


@pytest.fixture
def feature_config(beginnings_fixtures):
    """Provide feature extension configuration."""
    return beginnings_fixtures.extensions.get_feature_config()


@pytest.fixture
def invalid_config(beginnings_fixtures):
    """Provide invalid configuration for testing validation."""
    return beginnings_fixtures.extensions.get_invalid_config()


@pytest.fixture
def mock_app():
    """Provide mock Beginnings application."""
    return MockBeginningsApp()


@pytest.fixture
def mock_request():
    """Provide mock HTTP request."""
    return MockRequest()


@pytest.fixture
def mock_authenticated_request(beginnings_fixtures):
    """Provide mock authenticated HTTP request."""
    request_data = beginnings_fixtures.requests.get_authenticated_request_data()
    return MockRequest(
        method=request_data["method"],
        path=request_data["path"],
        headers=request_data["headers"],
        body=request_data["body"]
    )


@pytest.fixture
def mock_post_request(beginnings_fixtures):
    """Provide mock POST request."""
    request_data = beginnings_fixtures.requests.get_post_request_data()
    return MockRequest(
        method=request_data["method"],
        path=request_data["path"],
        headers=request_data["headers"],
        body=request_data["body"]
    )


@pytest.fixture
def mock_webhook_request(beginnings_fixtures):
    """Provide mock webhook request."""
    request_data = beginnings_fixtures.requests.get_webhook_request_data()
    return MockRequest(
        method=request_data["method"],
        path=request_data["path"],
        headers=request_data["headers"],
        body=request_data["body"]
    )


@pytest.fixture
def mock_response():
    """Provide mock HTTP response."""
    return MockResponse()


@pytest.fixture
def mock_success_response(beginnings_fixtures):
    """Provide mock successful response."""
    response_data = beginnings_fixtures.responses.get_success_response_data()
    return MockResponse(
        status_code=response_data["status_code"],
        headers=response_data["headers"],
        content=response_data["content"]
    )


@pytest.fixture
def mock_error_response(beginnings_fixtures):
    """Provide mock error response."""
    response_data = beginnings_fixtures.responses.get_error_response_data()
    return MockResponse(
        status_code=response_data["status_code"],
        headers=response_data["headers"],
        content=response_data["content"]
    )


@pytest.fixture
def mock_auth_error_response(beginnings_fixtures):
    """Provide mock authentication error response."""
    response_data = beginnings_fixtures.responses.get_auth_error_response_data()
    return MockResponse(
        status_code=response_data["status_code"],
        headers=response_data["headers"],
        content=response_data["content"]
    )


@pytest.fixture
def mock_http_client():
    """Provide mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def mock_database():
    """Provide mock database."""
    return MockDatabase()


@pytest.fixture
def mock_logger():
    """Provide mock logger."""
    return MockLogger("test")


@pytest.fixture
def extension_assertions():
    """Provide extension assertions."""
    return ExtensionAssertions()


@pytest.fixture
def test_user_data(beginnings_fixtures):
    """Provide test user data."""
    return beginnings_fixtures.get_test_user_data()


@pytest.fixture
def test_api_data(beginnings_fixtures):
    """Provide test API data."""
    return beginnings_fixtures.get_test_api_data()


@pytest.fixture
def test_webhook_data(beginnings_fixtures):
    """Provide test webhook data."""
    return beginnings_fixtures.get_test_webhook_data()


# Test configuration markers
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
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
        "markers", "feature: mark test as feature test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration_test: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    for item in items:
        # Add extension marker to all tests in extension testing
        if "test_extension" in str(item.fspath):
            item.add_marker(pytest.mark.extension)
        
        # Add slow marker to integration tests
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Custom pytest hooks for extension testing

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Setup hook for extension tests."""
    # Skip slow tests if --fast option is used
    if item.config.getoption("--fast", default=False):
        if "slow" in [mark.name for mark in item.iter_markers()]:
            pytest.skip("Skipping slow test in fast mode")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--fast",
        action="store_true",
        default=False,
        help="Skip slow tests"
    )
    parser.addoption(
        "--extension-type",
        action="store",
        default=None,
        help="Run tests for specific extension type only"
    )


def pytest_runtest_setup(item):
    """Custom test setup."""
    # Filter by extension type if specified
    extension_type = item.config.getoption("--extension-type")
    if extension_type:
        markers = [mark.name for mark in item.iter_markers()]
        if extension_type not in markers:
            pytest.skip(f"Test not for extension type: {extension_type}")