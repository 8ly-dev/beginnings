"""
Tests for basic security headers functionality.

This module tests the core security headers implementation including
X-Frame-Options, HSTS, Content-Type-Options, and other basic headers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from beginnings.extensions.security_headers.extension import SecurityHeadersExtension


class TestSecurityHeadersBasic:
    """Test basic security headers functionality."""
    
    def test_security_headers_extension_initialization(self):
        """Test security headers extension initializes correctly."""
        config = {
            "headers": {
                "x_frame_options": "DENY",
                "x_content_type_options": "nosniff",
                "strict_transport_security": {
                    "max_age": 31536000,
                    "include_subdomains": True,
                    "preload": False
                },
                "referrer_policy": "strict-origin-when-cross-origin"
            }
        }
        
        extension = SecurityHeadersExtension(config)
        
        assert extension.headers_config["x_frame_options"] == "DENY"
        assert extension.headers_config["x_content_type_options"] == "nosniff"
        assert extension.headers_config["referrer_policy"] == "strict-origin-when-cross-origin"
        
        hsts_config = extension.headers_config["strict_transport_security"]
        assert hsts_config["max_age"] == 31536000
        assert hsts_config["include_subdomains"] is True
        assert hsts_config["preload"] is False
    
    def test_security_headers_default_configuration(self):
        """Test security headers extension with default configuration."""
        config = {}
        extension = SecurityHeadersExtension(config)
        
        # Should have secure defaults
        assert extension.headers_config["x_frame_options"] == "DENY"
        assert extension.headers_config["x_content_type_options"] == "nosniff"
        assert extension.headers_config["x_xss_protection"] == "0"  # Deprecated, disabled
    
    def test_should_apply_to_route_global_headers(self):
        """Test that security headers apply to all routes by default."""
        config = {"headers": {"x_frame_options": "DENY"}}
        extension = SecurityHeadersExtension(config)
        
        # Should apply to all routes by default
        assert extension.should_apply_to_route("/", ["GET"], {})
        assert extension.should_apply_to_route("/api/data", ["POST"], {})
        assert extension.should_apply_to_route("/admin/users", ["PUT"], {})
    
    def test_should_apply_to_route_disabled_for_specific_route(self):
        """Test security headers can be disabled for specific routes."""
        config = {"headers": {"x_frame_options": "DENY"}}
        extension = SecurityHeadersExtension(config)
        
        route_config = {"security": {"headers": {"enabled": False}}}
        
        assert not extension.should_apply_to_route("/api/data", ["GET"], route_config)
    
    def test_should_apply_to_route_with_route_specific_config(self):
        """Test security headers with route-specific configuration."""
        config = {"headers": {"x_frame_options": "DENY"}}
        extension = SecurityHeadersExtension(config)
        
        route_config = {
            "security": {
                "headers": {
                    "x_frame_options": "SAMEORIGIN"
                }
            }
        }
        
        assert extension.should_apply_to_route("/embed/widget", ["GET"], route_config)
    
    @pytest.mark.asyncio
    async def test_middleware_adds_basic_security_headers(self):
        """Test middleware adds basic security headers to response."""
        config = {
            "headers": {
                "x_frame_options": "DENY",
                "x_content_type_options": "nosniff",
                "referrer_policy": "strict-origin-when-cross-origin"
            }
        }
        extension = SecurityHeadersExtension(config)
        
        # Create middleware
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        # Mock request and response
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        
        call_next = AsyncMock(return_value=response)
        
        # Execute middleware
        result = await middleware(request, call_next)
        
        # Verify headers were added
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    @pytest.mark.asyncio
    async def test_middleware_adds_hsts_header(self):
        """Test middleware adds HSTS header correctly."""
        config = {
            "headers": {
                "strict_transport_security": {
                    "max_age": 31536000,
                    "include_subdomains": True,
                    "preload": True
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        expected_hsts = "max-age=31536000; includeSubDomains; preload"
        assert result.headers["Strict-Transport-Security"] == expected_hsts
    
    @pytest.mark.asyncio
    async def test_middleware_route_specific_header_override(self):
        """Test middleware applies route-specific header overrides."""
        config = {
            "headers": {
                "x_frame_options": "DENY"
            }
        }
        extension = SecurityHeadersExtension(config)
        
        route_config = {
            "security": {
                "headers": {
                    "x_frame_options": "SAMEORIGIN"
                }
            }
        }
        
        factory = extension.get_middleware_factory()
        middleware = factory(route_config)
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        assert result.headers["X-Frame-Options"] == "SAMEORIGIN"
    
    @pytest.mark.asyncio
    async def test_middleware_header_removal(self):
        """Test middleware can remove headers by setting to null."""
        config = {
            "headers": {
                "x_frame_options": "DENY",
                "x_content_type_options": "nosniff"
            }
        }
        extension = SecurityHeadersExtension(config)
        
        route_config = {
            "security": {
                "headers": {
                    "x_frame_options": None  # Remove this header
                }
            }
        }
        
        factory = extension.get_middleware_factory()
        middleware = factory(route_config)
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        # X-Frame-Options should not be present
        assert "X-Frame-Options" not in result.headers
        # But other headers should still be there
        assert result.headers["X-Content-Type-Options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_middleware_permissions_policy_header(self):
        """Test middleware adds Permissions-Policy header correctly."""
        config = {
            "headers": {
                "permissions_policy": {
                    "geolocation": [],  # No origins allowed
                    "camera": ["self"],
                    "microphone": ["self"],
                    "payment": ["self", "https://payment.example.com"]
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        permissions_policy = result.headers["Permissions-Policy"]
        assert "geolocation=()" in permissions_policy
        assert "camera=(self)" in permissions_policy
        assert "microphone=(self)" in permissions_policy
        assert "payment=(self \"https://payment.example.com\")" in permissions_policy
    
    def test_validate_config_valid_configuration(self):
        """Test configuration validation with valid configuration."""
        config = {
            "headers": {
                "x_frame_options": "DENY",
                "strict_transport_security": {
                    "max_age": 31536000,
                    "include_subdomains": True
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        errors = extension.validate_config()
        assert errors == []
    
    def test_validate_config_invalid_x_frame_options(self):
        """Test configuration validation with invalid X-Frame-Options."""
        config = {
            "headers": {
                "x_frame_options": "INVALID_VALUE"
            }
        }
        extension = SecurityHeadersExtension(config)
        
        errors = extension.validate_config()
        assert len(errors) > 0
        assert any("x_frame_options" in error for error in errors)
    
    def test_validate_config_invalid_hsts_max_age(self):
        """Test configuration validation with invalid HSTS max-age."""
        config = {
            "headers": {
                "strict_transport_security": {
                    "max_age": -1  # Invalid negative value
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        errors = extension.validate_config()
        assert len(errors) > 0
        assert any("max_age" in error for error in errors)