"""
Tests for CORS functionality.

This module tests CORS request handling, preflight responses,
and origin validation features.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from beginnings.extensions.security_headers.extension import SecurityHeadersExtension
from beginnings.extensions.security_headers.cors import CORSManager


class TestCORSManager:
    """Test CORS manager functionality."""
    
    def test_cors_manager_initialization(self):
        """Test CORS manager initializes correctly."""
        config = {
            "enabled": True,
            "allow_origins": ["https://app.example.com", "https://admin.example.com"],
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["X-Request-ID"],
            "allow_credentials": True,
            "max_age": 86400
        }
        
        cors_manager = CORSManager(config)
        
        assert cors_manager.enabled is True
        assert cors_manager.allow_origins == ["https://app.example.com", "https://admin.example.com"]
        assert cors_manager.allow_methods == ["GET", "POST", "PUT", "DELETE"]
        assert cors_manager.allow_headers == ["Content-Type", "Authorization"]
        assert cors_manager.expose_headers == ["X-Request-ID"]
        assert cors_manager.allow_credentials is True
        assert cors_manager.max_age == 86400
    
    def test_cors_manager_disabled(self):
        """Test CORS manager when disabled."""
        config = {"enabled": False}
        cors_manager = CORSManager(config)
        
        assert cors_manager.enabled is False
    
    def test_cors_manager_default_config(self):
        """Test CORS manager with default configuration."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        assert cors_manager.allow_origins == ["*"]
        assert cors_manager.allow_methods == ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        assert cors_manager.allow_credentials is False
    
    def test_is_cors_request_with_origin(self):
        """Test CORS request detection with Origin header."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        request = MagicMock(spec=Request)
        request.headers = {"origin": "https://app.example.com"}
        
        assert cors_manager.is_cors_request(request) is True
    
    def test_is_cors_request_without_origin(self):
        """Test CORS request detection without Origin header."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        request = MagicMock(spec=Request)
        request.headers = {}
        
        assert cors_manager.is_cors_request(request) is False
    
    def test_is_preflight_request(self):
        """Test preflight request detection."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {
            "origin": "https://app.example.com",
            "access-control-request-method": "POST"
        }
        
        assert cors_manager.is_preflight_request(request) is True
    
    def test_is_not_preflight_request_wrong_method(self):
        """Test preflight request detection with wrong method."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        request = MagicMock(spec=Request)
        request.method = "GET"  # Not OPTIONS
        request.headers = {
            "origin": "https://app.example.com",
            "access-control-request-method": "POST"
        }
        
        assert cors_manager.is_preflight_request(request) is False
    
    def test_is_not_preflight_request_missing_headers(self):
        """Test preflight request detection with missing headers."""
        config = {"enabled": True}
        cors_manager = CORSManager(config)
        
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {"origin": "https://app.example.com"}  # Missing request method
        
        assert cors_manager.is_preflight_request(request) is False
    
    def test_is_origin_allowed_wildcard(self):
        """Test origin validation with wildcard."""
        config = {
            "enabled": True,
            "allow_origins": ["*"]
        }
        cors_manager = CORSManager(config)
        
        assert cors_manager.is_origin_allowed("https://any-domain.com") is True
        assert cors_manager.is_origin_allowed("http://localhost:3000") is True
    
    def test_is_origin_allowed_specific_origins(self):
        """Test origin validation with specific origins."""
        config = {
            "enabled": True,
            "allow_origins": ["https://app.example.com", "https://admin.example.com"]
        }
        cors_manager = CORSManager(config)
        
        assert cors_manager.is_origin_allowed("https://app.example.com") is True
        assert cors_manager.is_origin_allowed("https://admin.example.com") is True
        assert cors_manager.is_origin_allowed("https://evil.com") is False
    
    def test_is_origin_allowed_pattern_matching(self):
        """Test origin validation with pattern matching."""
        config = {
            "enabled": True,
            "allow_origins": ["https://*.example.com"]
        }
        cors_manager = CORSManager(config)
        
        assert cors_manager.is_origin_allowed("https://app.example.com") is True
        assert cors_manager.is_origin_allowed("https://admin.example.com") is True
        assert cors_manager.is_origin_allowed("https://example.com") is False  # No subdomain
        assert cors_manager.is_origin_allowed("https://evil.com") is False
    
    def test_create_preflight_response(self):
        """Test preflight response creation."""
        config = {
            "enabled": True,
            "allow_origins": ["https://app.example.com"],
            "allow_methods": ["GET", "POST", "PUT"],
            "allow_headers": ["Content-Type", "Authorization"],
            "max_age": 86400,
            "allow_credentials": True
        }
        cors_manager = CORSManager(config)
        
        origin = "https://app.example.com"
        requested_method = "POST"
        requested_headers = ["Content-Type", "X-Custom-Header"]
        
        response = cors_manager.create_preflight_response(
            origin, requested_method, requested_headers
        )
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT"
        assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
        assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
        assert response.headers["Access-Control-Max-Age"] == "86400"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
    
    def test_add_cors_headers_to_response(self):
        """Test adding CORS headers to response."""
        config = {
            "enabled": True,
            "allow_origins": ["https://app.example.com"],
            "expose_headers": ["X-Request-ID", "X-Rate-Limit"],
            "allow_credentials": True
        }
        cors_manager = CORSManager(config)
        
        origin = "https://app.example.com"
        response = Response(content="test", status_code=200)
        
        cors_manager.add_cors_headers_to_response(response, origin)
        
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Expose-Headers"] == "X-Request-ID, X-Rate-Limit"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
    
    def test_validate_cors_config_valid(self):
        """Test CORS configuration validation with valid config."""
        config = {
            "enabled": True,
            "allow_origins": ["https://app.example.com"],
            "allow_methods": ["GET", "POST"],
            "max_age": 86400
        }
        cors_manager = CORSManager(config)
        
        errors = cors_manager.validate_config()
        assert errors == []
    
    def test_validate_cors_config_invalid_max_age(self):
        """Test CORS configuration validation with invalid max_age."""
        config = {
            "enabled": True,
            "max_age": -1  # Invalid negative value
        }
        cors_manager = CORSManager(config)
        
        errors = cors_manager.validate_config()
        assert len(errors) > 0
        assert any("max_age" in error for error in errors)


class TestCORSIntegration:
    """Test CORS integration with security headers extension."""
    
    def test_security_headers_extension_with_cors(self):
        """Test security headers extension with CORS enabled."""
        config = {
            "cors": {
                "enabled": True,
                "allow_origins": ["https://app.example.com"],
                "allow_methods": ["GET", "POST", "PUT", "DELETE"]
            }
        }
        
        extension = SecurityHeadersExtension(config)
        
        assert extension.cors_manager.enabled is True
        assert extension.cors_manager.allow_origins == ["https://app.example.com"]
    
    @pytest.mark.asyncio
    async def test_middleware_handles_simple_cors_request(self):
        """Test middleware handles simple CORS request."""
        config = {
            "cors": {
                "enabled": True,
                "allow_origins": ["https://app.example.com"],
                "expose_headers": ["X-Request-ID"]
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        request.headers = {"origin": "https://app.example.com"}
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        assert result.headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        assert result.headers["Access-Control-Expose-Headers"] == "X-Request-ID"
    
    @pytest.mark.asyncio
    async def test_middleware_handles_preflight_request(self):
        """Test middleware handles CORS preflight request."""
        config = {
            "cors": {
                "enabled": True,
                "allow_origins": ["https://app.example.com"],
                "allow_methods": ["GET", "POST", "PUT"],
                "allow_headers": ["Content-Type", "Authorization"],
                "max_age": 86400
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {
            "origin": "https://app.example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "Content-Type"
        }
        
        call_next = AsyncMock()  # Should not be called for preflight
        
        result = await middleware(request, call_next)
        
        # Should return preflight response without calling next middleware
        call_next.assert_not_called()
        
        assert result.status_code == 200
        assert result.headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        assert result.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT"
        assert "Content-Type" in result.headers["Access-Control-Allow-Headers"]
        assert result.headers["Access-Control-Max-Age"] == "86400"
    
    @pytest.mark.asyncio
    async def test_middleware_rejects_invalid_origin(self):
        """Test middleware rejects requests from invalid origins."""
        config = {
            "cors": {
                "enabled": True,
                "allow_origins": ["https://app.example.com"]
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {
            "origin": "https://evil.com",  # Not in allowed origins
            "access-control-request-method": "POST"
        }
        
        call_next = AsyncMock()
        
        result = await middleware(request, call_next)
        
        # Should return 403 Forbidden
        assert result.status_code == 403
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_cors_disabled_for_route(self):
        """Test middleware can disable CORS for specific routes."""
        config = {
            "cors": {
                "enabled": True,
                "allow_origins": ["https://app.example.com"]
            }
        }
        extension = SecurityHeadersExtension(config)
        
        route_config = {
            "security": {
                "cors": {
                    "enabled": False
                }
            }
        }
        
        factory = extension.get_middleware_factory()
        middleware = factory(route_config)
        
        request = MagicMock(spec=Request)
        request.headers = {"origin": "https://app.example.com"}
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        # CORS headers should not be present
        assert "Access-Control-Allow-Origin" not in result.headers