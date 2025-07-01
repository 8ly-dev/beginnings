"""Tests for security configuration generation."""

import pytest
from beginnings.cli.templates.security import (
    generate_secure_defaults,
    generate_secure_secret,
    validate_security_settings,
    get_security_recommendations
)


class TestSecurityDefaults:
    """Test security default generation."""
    
    def test_generate_secure_secret(self):
        """Test secure secret generation."""
        secret = generate_secure_secret(32)
        assert len(secret) == 32
        assert isinstance(secret, str)
        
        # Test different length
        secret_16 = generate_secure_secret(16)
        assert len(secret_16) == 16
        
        # Test uniqueness
        secret2 = generate_secure_secret(32)
        assert secret != secret2
    
    def test_generate_secure_defaults_auth(self):
        """Test secure defaults for auth features."""
        selections = {"include_auth": True}
        defaults = generate_secure_defaults(selections)
        
        assert "SESSION_SECRET" in defaults
        assert "JWT_SECRET" in defaults
        assert len(defaults["SESSION_SECRET"]) == 32
        assert len(defaults["JWT_SECRET"]) == 32
    
    def test_generate_secure_defaults_rate_limiting(self):
        """Test secure defaults for rate limiting."""
        # API app
        selections = {"include_rate_limiting": True, "include_api": True}
        defaults = generate_secure_defaults(selections)
        
        assert "RATE_LIMIT_GLOBAL" in defaults
        assert "RATE_LIMIT_API" in defaults
        assert defaults["RATE_LIMIT_GLOBAL"] == 5000  # API-focused
        assert defaults["RATE_LIMIT_API"] == 100
        
        # Web app
        selections = {"include_rate_limiting": True, "include_api": False}
        defaults = generate_secure_defaults(selections)
        
        assert defaults["RATE_LIMIT_GLOBAL"] == 1000  # Web-focused
        assert "RATE_LIMIT_API" not in defaults
    
    def test_generate_secure_defaults_cors(self):
        """Test CORS defaults."""
        # API app should enable CORS
        selections = {"include_security_headers": True, "include_api": True}
        defaults = generate_secure_defaults(selections)
        
        assert defaults["CORS_ENABLED"] is True
        assert isinstance(defaults["CORS_ORIGINS"], list)
        
        # Web app should disable CORS
        selections = {"include_security_headers": True, "include_api": False}
        defaults = generate_secure_defaults(selections)
        
        assert defaults["CORS_ENABLED"] is False


class TestSecurityValidation:
    """Test security configuration validation."""
    
    def test_validate_weak_secrets(self):
        """Test validation of weak secrets."""
        config = {
            "auth": {
                "providers": {
                    "session": {"secret_key": "weak"},
                    "jwt": {"secret_key": "also-weak"}
                }
            }
        }
        
        issues = validate_security_settings(config)
        
        # Should find 2 secret issues
        secret_issues = [issue for issue in issues if "secret" in issue[1]]
        assert len(secret_issues) == 2
        assert all(issue[0] == "error" for issue in secret_issues)
    
    def test_validate_session_timeout(self):
        """Test session timeout validation."""
        config = {
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "a" * 32,  # Valid secret
                        "session_timeout": 90000  # Over 24 hours
                    }
                }
            }
        }
        
        issues = validate_security_settings(config)
        timeout_issues = [issue for issue in issues if "timeout" in issue[1]]
        assert len(timeout_issues) == 1
        assert timeout_issues[0][0] == "warning"
    
    def test_validate_cookie_security(self):
        """Test cookie security validation."""
        config = {
            "app": {"debug": False},  # Production mode
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "a" * 32,
                        "cookie_secure": False  # Insecure in production
                    }
                }
            }
        }
        
        issues = validate_security_settings(config)
        cookie_issues = [issue for issue in issues if "cookie_secure" in issue[1]]
        assert len(cookie_issues) == 1
        assert cookie_issues[0][0] == "warning"
    
    def test_validate_rate_limits(self):
        """Test rate limit validation."""
        # Very high limit
        config = {
            "rate_limiting": {
                "global": {"requests": 50000}
            }
        }
        
        issues = validate_security_settings(config)
        rate_issues = [issue for issue in issues if "rate_limiting" in issue[1]]
        assert len(rate_issues) == 1
        assert rate_issues[0][0] == "warning"
        
        # Very low limit
        config["rate_limiting"]["global"]["requests"] = 50
        issues = validate_security_settings(config)
        rate_issues = [issue for issue in issues if "rate_limiting" in issue[1]]
        assert len(rate_issues) == 1
        assert rate_issues[0][0] == "info"
    
    def test_validate_csp(self):
        """Test CSP validation."""
        config = {
            "app": {"debug": False},  # Production mode
            "security": {
                "csp": {
                    "enabled": True,
                    "directives": {
                        "script_src": ["'self'", "'unsafe-inline'"]  # Unsafe in production
                    }
                }
            }
        }
        
        issues = validate_security_settings(config)
        csp_issues = [issue for issue in issues if "script_src" in issue[1]]
        assert len(csp_issues) == 1
        assert csp_issues[0][0] == "warning"


class TestSecurityRecommendations:
    """Test security recommendations."""
    
    def test_auth_recommendations(self):
        """Test auth-specific recommendations."""
        selections = {"include_auth": True}
        recommendations = get_security_recommendations(selections)
        
        auth_recs = [rec for rec in recommendations if any(word in rec.lower() 
                    for word in ["password", "2fa", "session", "bcrypt"])]
        assert len(auth_recs) >= 3
    
    def test_api_recommendations(self):
        """Test API-specific recommendations."""
        selections = {"include_api": True}
        recommendations = get_security_recommendations(selections)
        
        api_recs = [rec for rec in recommendations if any(word in rec.lower() 
                   for word in ["api", "versioning", "oauth", "validation"])]
        assert len(api_recs) >= 3
    
    def test_csrf_recommendations(self):
        """Test CSRF-specific recommendations."""
        selections = {"include_csrf": True}
        recommendations = get_security_recommendations(selections)
        
        csrf_recs = [rec for rec in recommendations if "csrf" in rec.lower()]
        assert len(csrf_recs) >= 2
    
    def test_general_recommendations(self):
        """Test general recommendations are always included."""
        selections = {}
        recommendations = get_security_recommendations(selections)
        
        general_recs = [rec for rec in recommendations if any(word in rec.lower() 
                       for word in ["https", "dependencies", "logging", "audit"])]
        assert len(general_recs) >= 4