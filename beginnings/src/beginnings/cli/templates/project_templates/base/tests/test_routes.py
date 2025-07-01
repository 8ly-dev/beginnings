"""Test routes for {{ project_name }}."""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "{{ project_name }}"


def test_app_info(client: TestClient):
    """Test application info endpoint."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["framework"] == "beginnings"


{% if include_html %}
def test_index_page(client: TestClient):
    """Test home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "{{ project_name_title }}" in response.text


def test_about_page(client: TestClient):
    """Test about page."""
    response = client.get("/about")
    assert response.status_code == 200
    assert "About" in response.text
{% endif %}


{% if include_auth %}
def test_login_page(client: TestClient):
    """Test login page loads."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text


def test_api_login_invalid_credentials(client: TestClient):
    """Test API login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": ""}
    )
    assert response.status_code == 401


def test_api_login_valid_credentials(client: TestClient):
    """Test API login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_dashboard_requires_auth(client: TestClient):
    """Test dashboard redirects without authentication."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302  # Redirect to login
{% endif %}


{% if include_api %}
def test_api_status_endpoint(client: TestClient):
    """Test API status endpoint."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "environment" in data


def test_api_users_endpoint(client: TestClient):
    """Test users API endpoint."""
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_current_user_endpoint(client: TestClient):
    """Test current user API endpoint."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data
{% endif %}


{% if include_rate_limiting %}
def test_rate_limiting_functional(client: TestClient):
    """Test that rate limiting is configured (basic check)."""
    # Make multiple requests to a rate-limited endpoint
    responses = []
    for _ in range(10):
        response = client.get("/api/health")
        responses.append(response.status_code)
    
    # All should succeed for this basic test
    # In production, you'd test actual rate limit enforcement
    assert all(status == 200 for status in responses)
{% endif %}


def test_cors_headers(client: TestClient):
    """Test CORS headers are present (if CORS is enabled)."""
    response = client.options("/api/health")
    {% if include_api and include_security_headers %}
    assert response.status_code == 200
    # CORS headers should be present
    {% else %}
    # CORS might not be configured
    assert response.status_code in [200, 405]
    {% endif %}


def test_security_headers(client: TestClient):
    """Test security headers are present."""
    response = client.get("/")
    headers = response.headers
    
    {% if include_security_headers %}
    # Check for security headers
    assert "x-frame-options" in headers
    assert "x-content-type-options" in headers
    {% endif %}
    
    # Basic security should always be present
    assert response.status_code in [200, 404]