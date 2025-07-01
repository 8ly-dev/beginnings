"""Tests for the extension testing framework."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from beginnings.testing.extension_test import (
    ExtensionTestMixin, 
    ExtensionTestCase, 
    AsyncExtensionTestCase
)
from beginnings.testing.fixtures import ExtensionFixtures, BeginningsTestFixtures
from beginnings.testing.mocks import (
    MockRequest, MockResponse, MockExtension, MockMiddleware,
    MockBeginningsApp, MockHTTPClient, MockDatabase, MockLogger
)
from beginnings.testing.assertions import ExtensionAssertions
from beginnings.testing.runners import ExtensionTestRunner, IntegrationTestRunner
from beginnings.extensions.base import BaseExtension


class ExtensionForTesting(BaseExtension):
    """Test extension class for testing."""
    
    def __init__(self, config):
        super().__init__(config)
    
    def validate_config(self):
        errors = []
        if not self.config.get('enabled', True):
            errors.append("Extension must be enabled")
        return errors
    
    def get_middleware_factory(self):
        def create_middleware(route_config):
            return MockMiddleware(
                extension_config=self.config,
                route_config=route_config
            )
        return create_middleware
    
    def should_apply_to_route(self, path, methods, route_config):
        return True


class ExtensionForTestingFixtures:
    """Test extension fixtures."""
    
    def test_default_config(self):
        fixtures = ExtensionFixtures()
        config = fixtures.get_default_config()
        
        assert config['enabled'] is True
        assert config['debug'] is True
    
    def test_middleware_config(self):
        fixtures = ExtensionFixtures()
        config = fixtures.get_middleware_config()
        
        assert config['enabled'] is True
        assert 'option1' in config
        assert 'timeout' in config
    
    def test_auth_config(self):
        fixtures = ExtensionFixtures()
        config = fixtures.get_auth_config()
        
        assert 'api_key' in config
        assert 'protected_routes' in config
        assert 'provider' in config
    
    def test_invalid_config(self):
        fixtures = ExtensionFixtures()
        config = fixtures.get_invalid_config()
        
        assert config['enabled'] == "not_a_boolean"
        assert config['timeout'] == -1


class TestMockObjects:
    """Test mock objects functionality."""
    
    def test_mock_request(self):
        request = MockRequest(
            method="POST",
            path="/api/test",
            headers={"Content-Type": "application/json"},
            body=b'{"test": "data"}'
        )
        
        assert request.method == "POST"
        assert request.url.path == "/api/test"
        assert request.headers["Content-Type"] == "application/json"
    
    async def test_mock_request_json(self):
        request = MockRequest(
            body=b'{"test": "data"}'
        )
        
        json_data = await request.json()
        assert json_data["test"] == "data"
    
    def test_mock_response(self):
        response = MockResponse(
            status_code=201,
            headers={"Location": "/api/test/123"},
            json_data={"id": 123, "status": "created"}
        )
        
        assert response.status_code == 201
        assert response.headers["Location"] == "/api/test/123"
        assert response.json()["id"] == 123
    
    def test_mock_extension(self):
        extension = MockExtension(
            config={"enabled": True},
            should_apply=True
        )
        
        assert extension.should_apply_to_route("/test", ["GET"], {}) is True
        assert extension.validate_config.return_value == []
    
    def test_mock_middleware(self):
        middleware = MockMiddleware(
            extension_config={"timeout": 30},
            route_config={"auth_required": True}
        )
        
        assert middleware.extension_config["timeout"] == 30
        assert middleware.route_config["auth_required"] is True
        assert middleware.calls == []
    
    async def test_mock_middleware_dispatch(self):
        middleware = MockMiddleware()
        request = MockRequest()
        call_next = AsyncMock(return_value=MockResponse())
        
        response = await middleware.dispatch(request, call_next)
        
        assert len(middleware.calls) == 1
        assert middleware.calls[0][0] == 'dispatch'
        call_next.assert_called_once_with(request)
    
    def test_mock_app(self):
        app = MockBeginningsApp()
        
        # Test route addition
        app.add_route("/test", lambda: "test", ["GET"])
        assert len(app.routes) == 1
        assert app.routes[0]["path"] == "/test"
        
        # Test middleware addition
        app.add_middleware(MockMiddleware)
        assert len(app.middleware) == 1
        assert app.middleware[0]["class"] == MockMiddleware
    
    async def test_mock_http_client(self):
        client = MockHTTPClient()
        
        # Set up response
        expected_response = MockResponse(status_code=200, json_data={"test": "data"})
        client.set_response("GET", "https://api.test.com/data", expected_response)
        
        # Make request
        response = await client.get("https://api.test.com/data")
        
        assert response.status_code == 200
        assert response.json()["test"] == "data"
        assert len(client.get_request_history()) == 1
    
    async def test_mock_database(self):
        db = MockDatabase()
        
        # Test operations
        await db.execute("INSERT INTO test VALUES (?)", {"value": "test"})
        result = await db.fetch_one("SELECT * FROM test")
        
        operations = db.get_operations()
        assert len(operations) == 2
        assert operations[0]["type"] == "execute"
        assert operations[1]["type"] == "fetch_one"
    
    def test_mock_logger(self):
        logger = MockLogger("test_logger")
        
        logger.info("Test message")
        logger.error("Error message")
        
        logs = logger.get_logs()
        assert len(logs) == 2
        assert logs[0]["level"] == "INFO"
        assert logs[1]["level"] == "ERROR"


class ExtensionForTestingAssertions:
    """Test extension assertions."""
    
    def test_assert_config_valid(self):
        assertions = ExtensionAssertions()
        extension = ExtensionForTesting({"enabled": True})
        
        # Should not raise
        assertions.assert_config_valid(extension)
    
    def test_assert_config_invalid(self):
        assertions = ExtensionAssertions()
        extension = ExtensionForTesting({"enabled": False})
        
        with pytest.raises(AssertionError, match="Extension must be enabled"):
            assertions.assert_config_valid(extension)
    
    def test_assert_middleware_called(self):
        assertions = ExtensionAssertions()
        middleware = MockMiddleware()
        middleware.calls = [('dispatch', 'GET', '/test')]
        
        assertions.assert_middleware_called(middleware, 'dispatch')
    
    def test_assert_middleware_not_called(self):
        assertions = ExtensionAssertions()
        middleware = MockMiddleware()
        
        assertions.assert_middleware_not_called(middleware, 'dispatch')
    
    def test_assert_response_status(self):
        assertions = ExtensionAssertions()
        response = MockResponse(status_code=200)
        
        assertions.assert_response_status(response, 200)
        
        with pytest.raises(AssertionError):
            assertions.assert_response_status(response, 404)
    
    def test_assert_response_json(self):
        assertions = ExtensionAssertions()
        response = MockResponse(json_data={"test": "data"})
        
        assertions.assert_response_json(response, {"test": "data"})
        
        with pytest.raises(AssertionError):
            assertions.assert_response_json(response, {"test": "other"})
    
    def test_assert_route_applies(self):
        assertions = ExtensionAssertions()
        extension = ExtensionForTesting({"enabled": True})
        
        assertions.assert_route_applies(extension, "/test", ["GET"])
    
    def test_assert_authentication_required(self):
        assertions = ExtensionAssertions()
        response = MockResponse(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )
        
        assertions.assert_authentication_required(response)


class ExtensionForTestingTestRunner:
    """Test extension test runner."""
    
    def test_runner_initialization(self):
        runner = ExtensionTestRunner(
            extension_class=ExtensionForTesting,
            verbose=True
        )
        
        assert runner.extension_class == ExtensionForTesting
        assert runner.verbose is True
        assert runner.fixtures is not None
    
    def test_configuration_tests(self):
        runner = ExtensionTestRunner(ExtensionForTesting)
        results = runner.run_configuration_tests()
        
        assert "passed" in results
        assert "failed" in results
        assert "errors" in results
        assert results["passed"] >= 1  # Should pass valid config test
    
    def test_middleware_tests(self):
        runner = ExtensionTestRunner(ExtensionForTesting)
        results = runner.run_middleware_tests()
        
        assert "passed" in results
        assert "failed" in results
        assert results["passed"] >= 1  # Should pass middleware factory test
    
    def test_lifecycle_tests(self):
        runner = ExtensionTestRunner(ExtensionForTesting)
        results = runner.run_lifecycle_tests()
        
        assert "passed" in results
        assert "failed" in results
        assert results["passed"] >= 1  # Should pass lifecycle tests
    
    def test_run_all_tests(self):
        runner = ExtensionTestRunner(ExtensionForTesting, verbose=True)
        results = runner.run_all_tests()
        
        assert "extension_class" in results
        assert "total_passed" in results
        assert "total_failed" in results
        assert "config_tests" in results
        assert "middleware_tests" in results
        assert "lifecycle_tests" in results
        assert "timestamp" in results
        
        assert results["extension_class"] == "ExtensionForTesting"
        assert results["total_passed"] > 0


class TestIntegrationTestRunner:
    """Test integration test runner."""
    
    @pytest.mark.asyncio
    async def test_runner_initialization(self):
        runner = IntegrationTestRunner(
            extensions=[ExtensionForTesting],
            verbose=True
        )
        
        assert runner.extensions == [ExtensionForTesting]
        assert runner.verbose is True
    
    @pytest.mark.asyncio
    async def test_single_extension_integration(self):
        runner = IntegrationTestRunner([ExtensionForTesting])
        results = await runner.run_extension_integration_test(ExtensionForTesting)
        
        assert "extension" in results
        assert "passed" in results
        assert "failed" in results
        assert results["extension"] == "ExtensionForTesting"
    
    @pytest.mark.asyncio
    async def test_all_integration_tests(self):
        runner = IntegrationTestRunner([ExtensionForTesting], verbose=True)
        results = await runner.run_all_integration_tests()
        
        assert "total_passed" in results
        assert "total_failed" in results
        assert "extension_results" in results
        assert "timestamp" in results
        
        assert len(results["extension_results"]) == 1


class ExtensionForTestingTestMixin:
    """Test extension test mixin functionality."""
    
    def test_mixin_methods(self):
        # Create a test class that uses the mixin
        class TestClass(ExtensionTestMixin):
            def __init__(self):
                self.fixtures = None
                self.assertions = None
                self.mock_app = None
            
            def setUp(self):
                super().setUp()
        
        test_instance = TestClass()
        test_instance.setUp()
        
        # Test extension creation
        extension = test_instance.create_extension(ExtensionForTesting)
        assert isinstance(extension, ExtensionForTesting)
        
        # Test mock request creation
        request = test_instance.create_mock_request(
            method="POST",
            path="/api/test"
        )
        assert request.method == "POST"
        assert request.url.path == "/api/test"
        
        # Test mock response creation
        response = test_instance.create_mock_response(status_code=201)
        assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_mixin_middleware_running(self):
        class TestClass(ExtensionTestMixin):
            def __init__(self):
                self.fixtures = None
                self.assertions = None
                self.mock_app = None
            
            def setUp(self):
                super().setUp()
        
        test_instance = TestClass()
        test_instance.setUp()
        
        middleware = MockMiddleware()
        request = test_instance.create_mock_request()
        
        response = await test_instance.run_middleware(middleware, request)
        
        assert len(middleware.calls) == 1
        assert middleware.calls[0][0] == 'dispatch'


class TestBeginningsTestFixtures:
    """Test main fixtures class."""
    
    def test_fixtures_initialization(self):
        fixtures = BeginningsTestFixtures()
        
        assert fixtures.extensions is not None
        assert fixtures.config is not None
        assert fixtures.requests is not None
        assert fixtures.responses is not None
    
    def test_test_user_data(self):
        fixtures = BeginningsTestFixtures()
        user_data = fixtures.get_test_user_data()
        
        assert "user_id" in user_data
        assert "username" in user_data
        assert "roles" in user_data
        assert isinstance(user_data["roles"], list)
    
    def test_test_api_data(self):
        fixtures = BeginningsTestFixtures()
        api_data = fixtures.get_test_api_data()
        
        assert "resources" in api_data
        assert "pagination" in api_data
        assert len(api_data["resources"]) == 2
    
    def test_test_webhook_data(self):
        fixtures = BeginningsTestFixtures()
        webhook_data = fixtures.get_test_webhook_data()
        
        assert "id" in webhook_data
        assert "type" in webhook_data
        assert "data" in webhook_data
        assert webhook_data["type"] == "test.event"


# Integration tests using pytest fixtures

@pytest.fixture
def test_extension_class():
    """Provide test extension class."""
    return ExtensionForTesting


@pytest.fixture
def test_extension_config():
    """Provide test extension configuration."""
    return {"enabled": True, "debug": True}


def test_pytest_fixtures_work(beginnings_fixtures, extension_assertions, mock_app):
    """Test that pytest fixtures work correctly."""
    assert beginnings_fixtures is not None
    assert extension_assertions is not None
    assert mock_app is not None
    
    config = beginnings_fixtures.extensions.get_default_config()
    assert config["enabled"] is True


def test_extension_creation_with_fixtures(test_extension_class, test_extension_config):
    """Test extension creation using fixtures."""
    extension = test_extension_class(test_extension_config)
    assert extension.config["enabled"] is True
    
    errors = extension.validate_config()
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_async_extension_testing(test_extension_class, mock_request):
    """Test async extension functionality."""
    extension = test_extension_class({"enabled": True})
    factory = extension.get_middleware_factory()
    
    middleware = factory({})
    call_next = AsyncMock(return_value=MockResponse())
    
    response = await middleware.dispatch(mock_request, call_next)
    assert response.status_code == 200
    call_next.assert_called_once()