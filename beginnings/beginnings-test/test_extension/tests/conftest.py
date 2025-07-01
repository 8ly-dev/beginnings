"""Test configuration and fixtures for test_extension extension."""

import pytest
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_extension.extension import TestExtensionExtension


@pytest.fixture
def extension_config() -> Dict[str, Any]:
    """Basic extension configuration for testing."""
    return {
        "enabled": True,
        # Add your test configuration here
    }


@pytest.fixture
def extension(extension_config) -> TestExtensionExtension:
    """Create extension instance for testing."""
    return TestExtensionExtension(extension_config)


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app for testing."""
    return FastAPI()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Create mock request for testing."""
    from unittest.mock import MagicMock
    from fastapi import Request
    
    request = MagicMock(spec=Request)
    request.headers = {}
    request.query_params = {}
    request.path_params = {}
    request.state = MagicMock()
    
    return request


@pytest.fixture
def mock_response():
    """Create mock response for testing."""
    from unittest.mock import MagicMock
    from fastapi import Response
    
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    
    return response