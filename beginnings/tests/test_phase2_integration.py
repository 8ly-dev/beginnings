"""
Integration test for Phase 2 extensions working together.

This test demonstrates that the authentication, CSRF protection, and rate limiting
extensions work seamlessly together in a realistic application scenario.
"""

import pytest
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from beginnings.core.app import App
from beginnings.extensions.auth.extension import AuthExtension
from beginnings.extensions.csrf.extension import CSRFExtension
from beginnings.extensions.rate_limiting.extension import RateLimitExtension


@pytest.fixture
def phase2_config():
    """Configuration for Phase 2 integration test."""
    return {
        "app": {
            "name": "phase2-integration-test"
        },
        "routes": {
            "/admin/*": {
                "auth": {
                    "required": True,
                    "roles": ["admin"]
                },
                "csrf": {
                    "enabled": True
                },
                "rate_limiting": {
                    "enabled": True,
                    "requests": 10,
                    "window_seconds": 60,
                    "identifier": "user"
                }
            },
            "/api/*": {
                "auth": {
                    "required": True,
                    "roles": ["user", "admin"]
                },
                "csrf": {
                    "enabled": False  # APIs typically don't need CSRF
                },
                "rate_limiting": {
                    "enabled": True,
                    "requests": 100,
                    "window_seconds": 60,
                    "identifier": "user"
                }
            },
            "/public/*": {
                "auth": {
                    "required": False
                },
                "csrf": {
                    "enabled": False
                },
                "rate_limiting": {
                    "enabled": True,
                    "requests": 50,
                    "window_seconds": 60,
                    "identifier": "ip"
                }
            }
        },
        "extensions": {
            "beginnings.extensions.auth.extension:AuthExtension": {
                "provider": "jwt",
                "providers": {
                    "jwt": {
                        "secret_key": "test-secret-key-for-jwt-that-is-long-enough-for-security",
                        "algorithm": "HS256",
                        "token_expire_minutes": 30
                    }
                },
                "rbac": {
                    "roles": {
                        "user": {
                            "description": "Standard user",
                            "permissions": ["read:profile"]
                        },
                        "admin": {
                            "description": "Administrator", 
                            "permissions": ["*"],
                            "inherits": ["user"]
                        }
                    }
                }
            },
            "beginnings.extensions.csrf.extension:CSRFExtension": {
                "secret_key": "test-secret-key-for-csrf-that-is-long-enough-for-security",
                "enabled": True,
                "protected_methods": ["POST", "PUT", "PATCH", "DELETE"]
            },
            "beginnings.extensions.rate_limiting.extension:RateLimitExtension": {
                "storage": {
                    "type": "memory"
                },
                "global": {
                    "enabled": False  # Use per-route configuration
                }
            }
        }
    }


class TestPhase2Integration:
    """Test Phase 2 extensions integration."""
    
    def test_extension_initialization(self, phase2_config):
        """Test that all Phase 2 extensions initialize correctly."""
        # Test auth extension
        auth_config = phase2_config["extensions"]["beginnings.extensions.auth.extension:AuthExtension"]
        auth_extension = AuthExtension(auth_config)
        
        assert "jwt" in auth_extension.providers
        assert auth_extension.rbac_manager is not None
        
        # Test CSRF extension
        csrf_config = phase2_config["extensions"]["beginnings.extensions.csrf.extension:CSRFExtension"]
        csrf_extension = CSRFExtension(csrf_config)
        
        assert csrf_extension.enabled is True
        assert csrf_extension.token_manager is not None
        
        # Test rate limiting extension
        rate_limit_config = phase2_config["extensions"]["beginnings.extensions.rate_limiting.extension:RateLimitExtension"]
        rate_limit_extension = RateLimitExtension(rate_limit_config)
        
        assert rate_limit_extension._storage is not None
    
    def test_extension_route_applicability(self, phase2_config):
        """Test that extensions correctly determine route applicability."""
        # Initialize extensions
        auth_config = phase2_config["extensions"]["beginnings.extensions.auth.extension:AuthExtension"]
        auth_extension = AuthExtension(auth_config)
        
        csrf_config = phase2_config["extensions"]["beginnings.extensions.csrf.extension:CSRFExtension"]
        csrf_extension = CSRFExtension(csrf_config)
        
        rate_limit_config = phase2_config["extensions"]["beginnings.extensions.rate_limiting.extension:RateLimitExtension"]
        rate_limit_extension = RateLimitExtension(rate_limit_config)
        
        # Test admin route configuration
        admin_route_config = {
            "auth": {"required": True, "roles": ["admin"]},
            "csrf": {"enabled": True},
            "rate_limiting": {"enabled": True, "requests": 10}
        }
        
        assert auth_extension.should_apply_to_route("/admin/users", ["GET"], admin_route_config)
        assert csrf_extension.should_apply_to_route("/admin/users", ["POST"], admin_route_config)
        assert rate_limit_extension.should_apply_to_route("/admin/users", ["GET"], admin_route_config)
        
        # Test API route configuration
        api_route_config = {
            "auth": {"required": True, "roles": ["user", "admin"]},
            "csrf": {"enabled": False},
            "rate_limiting": {"enabled": True, "requests": 100}
        }
        
        assert auth_extension.should_apply_to_route("/api/data", ["GET"], api_route_config)
        assert not csrf_extension.should_apply_to_route("/api/data", ["POST"], api_route_config)
        assert rate_limit_extension.should_apply_to_route("/api/data", ["GET"], api_route_config)
        
        # Test public route configuration
        public_route_config = {
            "auth": {"required": False},
            "csrf": {"enabled": False},
            "rate_limiting": {"enabled": True, "requests": 50}
        }
        
        assert not auth_extension.should_apply_to_route("/public/info", ["GET"], public_route_config)
        assert not csrf_extension.should_apply_to_route("/public/info", ["GET"], public_route_config)
        assert rate_limit_extension.should_apply_to_route("/public/info", ["GET"], public_route_config)
    
    def test_extension_configuration_validation(self, phase2_config):
        """Test that all extensions validate their configuration correctly."""
        # Test auth extension validation
        auth_config = phase2_config["extensions"]["beginnings.extensions.auth.extension:AuthExtension"]
        auth_extension = AuthExtension(auth_config)
        auth_errors = auth_extension.validate_config()
        assert auth_errors == []  # Should have no errors
        
        # Test CSRF extension validation
        csrf_config = phase2_config["extensions"]["beginnings.extensions.csrf.extension:CSRFExtension"]
        csrf_extension = CSRFExtension(csrf_config)
        csrf_errors = csrf_extension.validate_config()
        assert csrf_errors == []  # Should have no errors
        
        # Test rate limiting extension validation
        rate_limit_config = phase2_config["extensions"]["beginnings.extensions.rate_limiting.extension:RateLimitExtension"]
        rate_limit_extension = RateLimitExtension(rate_limit_config)
        rate_limit_errors = rate_limit_extension.validate_config()
        assert rate_limit_errors == []  # Should have no errors
    
    def test_middleware_factory_creation(self, phase2_config):
        """Test that all extensions can create middleware factories."""
        # Test auth extension middleware factory
        auth_config = phase2_config["extensions"]["beginnings.extensions.auth.extension:AuthExtension"]
        auth_extension = AuthExtension(auth_config)
        auth_factory = auth_extension.get_middleware_factory()
        
        assert callable(auth_factory)
        
        # Create middleware for a route
        route_config = {"auth": {"required": True, "roles": ["admin"]}}
        auth_middleware = auth_factory(route_config)
        assert callable(auth_middleware)
        
        # Test CSRF extension middleware factory
        csrf_config = phase2_config["extensions"]["beginnings.extensions.csrf.extension:CSRFExtension"]
        csrf_extension = CSRFExtension(csrf_config)
        csrf_factory = csrf_extension.get_middleware_factory()
        
        assert callable(csrf_factory)
        
        route_config = {"csrf": {"enabled": True}}
        csrf_middleware = csrf_factory(route_config)
        assert callable(csrf_middleware)
        
        # Test rate limiting extension middleware factory
        rate_limit_config = phase2_config["extensions"]["beginnings.extensions.rate_limiting.extension:RateLimitExtension"]
        rate_limit_extension = RateLimitExtension(rate_limit_config)
        rate_limit_factory = rate_limit_extension.get_middleware_factory()
        
        assert callable(rate_limit_factory)
        
        route_config = {"rate_limiting": {"enabled": True, "requests": 10}}
        rate_limit_middleware = rate_limit_factory(route_config)
        assert callable(rate_limit_middleware)
    
    def test_phase2_extension_compatibility(self, phase2_config):
        """Test that Phase 2 extensions are compatible with each other."""
        # This test verifies that extensions don't have conflicting configurations
        # or incompatible interfaces
        
        extensions = []
        
        # Initialize all extensions
        for extension_path, extension_config in phase2_config["extensions"].items():
            if "auth" in extension_path:
                extensions.append(AuthExtension(extension_config))
            elif "csrf" in extension_path:
                extensions.append(CSRFExtension(extension_config))
            elif "rate_limiting" in extension_path:
                extensions.append(RateLimitExtension(extension_config))
        
        # Verify all extensions implement the BaseExtension interface correctly
        for extension in extensions:
            assert hasattr(extension, "get_middleware_factory")
            assert hasattr(extension, "should_apply_to_route")
            assert hasattr(extension, "validate_config")
            
            # Test that each extension can create middleware
            factory = extension.get_middleware_factory()
            assert callable(factory)
            
            # Test configuration validation
            errors = extension.validate_config()
            assert isinstance(errors, list)
    
    def test_realistic_application_scenario(self, phase2_config):
        """Test a realistic application scenario with all extensions enabled."""
        # This test simulates a real application with:
        # - Public routes with rate limiting only
        # - API routes with auth + rate limiting
        # - Admin routes with auth + CSRF + rate limiting
        
        # Initialize extensions
        auth_extension = AuthExtension(
            phase2_config["extensions"]["beginnings.extensions.auth.extension:AuthExtension"]
        )
        csrf_extension = CSRFExtension(
            phase2_config["extensions"]["beginnings.extensions.csrf.extension:CSRFExtension"]
        )
        rate_limit_extension = RateLimitExtension(
            phase2_config["extensions"]["beginnings.extensions.rate_limiting.extension:RateLimitExtension"]
        )
        
        # Test route scenarios
        scenarios = [
            {
                "path": "/public/info",
                "methods": ["GET"],
                "expected_extensions": ["rate_limiting"]
            },
            {
                "path": "/api/users",
                "methods": ["GET"],
                "expected_extensions": ["auth", "rate_limiting"]
            },
            {
                "path": "/admin/dashboard",
                "methods": ["POST"],
                "expected_extensions": ["auth", "csrf", "rate_limiting"]
            }
        ]
        
        for scenario in scenarios:
            path = scenario["path"]
            methods = scenario["methods"]
            expected = scenario["expected_extensions"]
            
            # Determine which extensions should apply
            route_config = phase2_config["routes"].get(
                self._find_matching_route_pattern(path, phase2_config["routes"]),
                {}
            )
            
            # Check auth extension
            auth_applies = auth_extension.should_apply_to_route(path, methods, route_config)
            if "auth" in expected:
                assert auth_applies, f"Auth should apply to {path}"
            else:
                assert not auth_applies, f"Auth should not apply to {path}"
            
            # Check CSRF extension for POST requests
            if "POST" in methods:
                csrf_applies = csrf_extension.should_apply_to_route(path, methods, route_config)
                if "csrf" in expected:
                    assert csrf_applies, f"CSRF should apply to {path}"
                else:
                    assert not csrf_applies, f"CSRF should not apply to {path}"
            
            # Check rate limiting extension
            rate_limit_applies = rate_limit_extension.should_apply_to_route(path, methods, route_config)
            if "rate_limiting" in expected:
                assert rate_limit_applies, f"Rate limiting should apply to {path}"
            else:
                assert not rate_limit_applies, f"Rate limiting should not apply to {path}"
    
    def _find_matching_route_pattern(self, path: str, routes_config: dict[str, Any]) -> str:
        """Find matching route pattern for a path."""
        # Check exact match first
        if path in routes_config:
            return path
        
        # Check wildcard patterns
        for pattern in routes_config:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if path.startswith(prefix):
                    return pattern
        
        return ""  # No match found