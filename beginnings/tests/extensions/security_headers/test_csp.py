"""
Tests for Content Security Policy functionality.

This module tests CSP directive generation, nonce generation,
and template integration features.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request, Response

from beginnings.extensions.security_headers.extension import SecurityHeadersExtension
from beginnings.extensions.security_headers.csp import CSPManager


class TestCSPManager:
    """Test Content Security Policy manager."""
    
    def test_csp_manager_initialization(self):
        """Test CSP manager initializes correctly."""
        config = {
            "enabled": True,
            "directives": {
                "default_src": ["'self'"],
                "script_src": ["'self'", "'unsafe-inline'"],
                "style_src": ["'self'", "https://fonts.googleapis.com"]
            },
            "nonce": {
                "enabled": True,
                "script_nonce": True,
                "style_nonce": True,
                "nonce_length": 16
            }
        }
        
        csp_manager = CSPManager(config)
        
        assert csp_manager.enabled is True
        assert csp_manager.directives["default_src"] == ["'self'"]
        assert csp_manager.nonce_enabled is True
        assert csp_manager.nonce_length == 16
    
    def test_csp_manager_disabled(self):
        """Test CSP manager when disabled."""
        config = {"enabled": False}
        csp_manager = CSPManager(config)
        
        assert csp_manager.enabled is False
    
    def test_generate_nonce(self):
        """Test nonce generation."""
        config = {
            "enabled": True,
            "nonce": {
                "enabled": True,
                "nonce_length": 16
            }
        }
        csp_manager = CSPManager(config)
        
        nonce1 = csp_manager.generate_nonce()
        nonce2 = csp_manager.generate_nonce()
        
        # Nonces should be different
        assert nonce1 != nonce2
        # Should be base64 encoded (length will be longer than raw bytes)
        assert len(nonce1) > 16
        # Should be URL-safe base64
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=" for c in nonce1)
    
    def test_generate_nonce_custom_length(self):
        """Test nonce generation with custom length."""
        config = {
            "enabled": True,
            "nonce": {
                "enabled": True,
                "nonce_length": 32
            }
        }
        csp_manager = CSPManager(config)
        
        nonce = csp_manager.generate_nonce()
        # Base64 encoding of 32 bytes should be longer
        assert len(nonce) > 32
    
    def test_build_csp_header_basic(self):
        """Test building basic CSP header."""
        config = {
            "enabled": True,
            "directives": {
                "default_src": ["'self'"],
                "script_src": ["'self'"],
                "style_src": ["'self'", "https://fonts.googleapis.com"]
            }
        }
        csp_manager = CSPManager(config)
        
        csp_header = csp_manager.build_csp_header()
        
        assert "default-src 'self'" in csp_header
        assert "script-src 'self'" in csp_header
        assert "style-src 'self' https://fonts.googleapis.com" in csp_header
    
    def test_build_csp_header_with_nonces(self):
        """Test building CSP header with nonces."""
        config = {
            "enabled": True,
            "directives": {
                "default_src": ["'self'"],
                "script_src": ["'self'"],
                "style_src": ["'self'"]
            },
            "nonce": {
                "enabled": True,
                "script_nonce": True,
                "style_nonce": True
            }
        }
        csp_manager = CSPManager(config)
        
        script_nonce = "test-script-nonce"
        style_nonce = "test-style-nonce"
        
        csp_header = csp_manager.build_csp_header(
            script_nonce=script_nonce,
            style_nonce=style_nonce
        )
        
        assert f"script-src 'self' 'nonce-{script_nonce}'" in csp_header
        assert f"style-src 'self' 'nonce-{style_nonce}'" in csp_header
    
    def test_build_csp_header_report_only(self):
        """Test building CSP header in report-only mode."""
        config = {
            "enabled": True,
            "report_only": True,
            "directives": {
                "default_src": ["'self'"]
            }
        }
        csp_manager = CSPManager(config)
        
        header_name, csp_header = csp_manager.build_csp_header_with_name()
        
        assert header_name == "Content-Security-Policy-Report-Only"
        assert "default-src 'self'" in csp_header
    
    def test_build_csp_header_with_report_uri(self):
        """Test building CSP header with report URI."""
        config = {
            "enabled": True,
            "directives": {
                "default_src": ["'self'"]
            },
            "report_uri": "/csp-report"
        }
        csp_manager = CSPManager(config)
        
        csp_header = csp_manager.build_csp_header()
        
        assert "default-src 'self'" in csp_header
        assert "report-uri /csp-report" in csp_header
    
    def test_validate_csp_config_valid(self):
        """Test CSP configuration validation with valid config."""
        config = {
            "enabled": True,
            "directives": {
                "default_src": ["'self'"],
                "script_src": ["'self'", "'unsafe-inline'"]
            }
        }
        csp_manager = CSPManager(config)
        
        errors = csp_manager.validate_config()
        assert errors == []
    
    def test_validate_csp_config_invalid_directive(self):
        """Test CSP configuration validation with invalid directive."""
        config = {
            "enabled": True,
            "directives": {
                "invalid_directive": ["'self'"]
            }
        }
        csp_manager = CSPManager(config)
        
        errors = csp_manager.validate_config()
        assert len(errors) > 0
        assert any("invalid_directive" in error for error in errors)


class TestCSPIntegration:
    """Test CSP integration with security headers extension."""
    
    def test_security_headers_extension_with_csp(self):
        """Test security headers extension with CSP enabled."""
        config = {
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"],
                    "script_src": ["'self'"]
                }
            }
        }
        
        extension = SecurityHeadersExtension(config)
        
        assert extension.csp_manager.enabled is True
        assert extension.csp_manager.directives["default_src"] == ["'self'"]
    
    @pytest.mark.asyncio
    async def test_middleware_adds_csp_header(self):
        """Test middleware adds CSP header to response."""
        config = {
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"],
                    "script_src": ["'self'", "'unsafe-inline'"]
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
        
        assert "Content-Security-Policy" in result.headers
        csp_header = result.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp_header
        assert "script-src 'self' 'unsafe-inline'" in csp_header
    
    @pytest.mark.asyncio
    async def test_middleware_adds_csp_with_nonces(self):
        """Test middleware adds CSP header with nonces."""
        config = {
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"],
                    "script_src": ["'self'"],
                    "style_src": ["'self'"]
                },
                "nonce": {
                    "enabled": True,
                    "script_nonce": True,
                    "style_nonce": True
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        factory = extension.get_middleware_factory()
        middleware = factory({})
        
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        assert "Content-Security-Policy" in result.headers
        csp_header = result.headers["Content-Security-Policy"]
        
        # Should include nonces
        assert "'nonce-" in csp_header
        assert "script-src 'self' 'nonce-" in csp_header
        assert "style-src 'self' 'nonce-" in csp_header
        
        # Nonces should be available in request state
        assert hasattr(request.state, "csp_script_nonce")
        assert hasattr(request.state, "csp_style_nonce")
    
    @pytest.mark.asyncio
    async def test_middleware_csp_route_override(self):
        """Test middleware applies route-specific CSP overrides."""
        config = {
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"],
                    "script_src": ["'self'", "'unsafe-inline'"]
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        # Route config with stricter CSP
        route_config = {
            "security": {
                "csp": {
                    "directives": {
                        "script_src": ["'self'"]  # Remove unsafe-inline
                    }
                }
            }
        }
        
        factory = extension.get_middleware_factory()
        middleware = factory(route_config)
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        csp_header = result.headers["Content-Security-Policy"]
        # Should use stricter policy
        assert "script-src 'self'" in csp_header
        assert "'unsafe-inline'" not in csp_header
    
    @pytest.mark.asyncio
    async def test_middleware_csp_disabled_for_route(self):
        """Test middleware can disable CSP for specific routes."""
        config = {
            "csp": {
                "enabled": True,
                "directives": {
                    "default_src": ["'self'"]
                }
            }
        }
        extension = SecurityHeadersExtension(config)
        
        route_config = {
            "security": {
                "csp": {
                    "enabled": False
                }
            }
        }
        
        factory = extension.get_middleware_factory()
        middleware = factory(route_config)
        
        request = MagicMock(spec=Request)
        response = Response(content="test", status_code=200)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware(request, call_next)
        
        # CSP header should not be present
        assert "Content-Security-Policy" not in result.headers