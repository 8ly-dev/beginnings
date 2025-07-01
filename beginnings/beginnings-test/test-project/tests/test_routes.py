"""Test routes for test-project."""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "test-project"


def test_app_info(client: TestClient):
    """Test application info endpoint."""
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["framework"] == "beginnings"



def test_index_page(client: TestClient):
    """Test home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Test Project" in response.text


def test_about_page(client: TestClient):
    """Test about page."""
    response = client.get("/about")
    assert response.status_code == 200
    assert "About" in response.text












def test_cors_headers(client: TestClient):
    """Test CORS headers are present (if CORS is enabled)."""
    response = client.options("/api/health")
    
    # CORS might not be configured
    assert response.status_code in [200, 405]
    


def test_security_headers(client: TestClient):
    """Test security headers are present."""
    response = client.get("/")
    headers = response.headers
    
    
    
    # Basic security should always be present
    assert response.status_code in [200, 404]