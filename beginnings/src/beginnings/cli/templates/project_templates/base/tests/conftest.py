"""Pytest configuration and fixtures for {{ project_name }}."""

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


{% if include_auth %}
@pytest.fixture
def mock_user():
    """Mock user data for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"]
    }
{% endif %}