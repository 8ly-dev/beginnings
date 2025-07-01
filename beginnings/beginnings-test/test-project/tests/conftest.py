"""Pytest configuration and fixtures for test-project."""

import pytest
from fastapi.testclient import TestClient
from main import create_app


@pytest.fixture
def app():
    """Create test application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Mock authentication headers for testing."""
    return {"Authorization": "Bearer test_token"}


