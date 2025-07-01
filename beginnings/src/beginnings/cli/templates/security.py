"""Security configuration generation and validation."""

import secrets
import string
from typing import Dict, Any, List, Tuple
import click


def generate_secure_defaults(selections: Dict[str, Any]) -> Dict[str, Any]:
    """Generate secure configuration defaults based on user selections.
    
    Args:
        selections: User feature selections
        
    Returns:
        Dictionary with security defaults
    """
    defaults = {}
    
    # Generate secure secrets
    if selections.get("include_auth", False):
        defaults["SESSION_SECRET"] = generate_secure_secret(32)
        defaults["JWT_SECRET"] = generate_secure_secret(32)
    
    # CSRF token settings
    if selections.get("include_csrf", False):
        defaults["CSRF_SECRET"] = generate_secure_secret(32)
    
    # Rate limiting defaults based on app type
    if selections.get("include_rate_limiting", False):
        if selections.get("include_api", False):
            # API-focused rate limits
            defaults["RATE_LIMIT_GLOBAL"] = 5000
            defaults["RATE_LIMIT_API"] = 100
        else:
            # Web app rate limits
            defaults["RATE_LIMIT_GLOBAL"] = 1000
            defaults["RATE_LIMIT_WEB"] = 50
    
    # Security headers based on app type
    if selections.get("include_security_headers", False):
        if selections.get("include_api", False):
            # API-specific CORS settings
            defaults["CORS_ENABLED"] = True
            defaults["CORS_ORIGINS"] = ["http://localhost:3000", "http://localhost:3001"]
        else:
            defaults["CORS_ENABLED"] = False
    
    return defaults


def generate_secure_secret(length: int = 32) -> str:
    """Generate cryptographically secure random secret.
    
    Args:
        length: Length of secret to generate
        
    Returns:
        Secure random string
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_security_settings(config: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """Validate security configuration and return recommendations.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of (level, setting, message) tuples where level is 'error', 'warning', or 'info'
    """
    issues = []
    
    # Check authentication settings
    auth_config = config.get("auth", {})
    if auth_config:
        # Check for weak secrets
        session_secret = auth_config.get("providers", {}).get("session", {}).get("secret_key", "")
        if isinstance(session_secret, str) and len(session_secret) < 32:
            issues.append(("error", "auth.providers.session.secret_key", 
                          "Session secret must be at least 32 characters for security"))
        
        jwt_config = auth_config.get("providers", {}).get("jwt", {})
        if jwt_config:  # Only validate if JWT is configured
            jwt_secret = jwt_config.get("secret_key", "")
            if isinstance(jwt_secret, str) and len(jwt_secret) < 32:
                issues.append(("error", "auth.providers.jwt.secret_key", 
                              "JWT secret must be at least 32 characters for security"))
        
        # Check session timeout
        session_timeout = auth_config.get("providers", {}).get("session", {}).get("session_timeout", 0)
        if session_timeout > 86400:  # 24 hours
            issues.append(("warning", "auth.providers.session.session_timeout",
                          "Session timeout over 24 hours may pose security risk"))
        
        # Check cookie security
        cookie_secure = auth_config.get("providers", {}).get("session", {}).get("cookie_secure", False)
        if not cookie_secure and config.get("app", {}).get("debug", False) is False:
            issues.append(("warning", "auth.providers.session.cookie_secure",
                          "Cookie secure should be true in production"))
    
    # Check CSRF settings
    csrf_config = config.get("csrf", {})
    if csrf_config and csrf_config.get("enabled", True):
        token_length = csrf_config.get("token_length", 0)
        if token_length < 16:
            issues.append(("warning", "csrf.token_length",
                          "CSRF token length should be at least 16 characters"))
    
    # Check rate limiting
    rate_config = config.get("rate_limiting", {})
    if rate_config:
        global_limit = rate_config.get("global", {}).get("requests", 0)
        if global_limit > 10000:
            issues.append(("warning", "rate_limiting.global.requests",
                          "Very high global rate limit may not provide adequate protection"))
        elif global_limit < 100:
            issues.append(("info", "rate_limiting.global.requests",
                          "Low global rate limit may impact legitimate users"))
    
    # Check security headers
    security_config = config.get("security", {})
    if security_config:
        headers = security_config.get("headers", {})
        
        # Check HSTS
        hsts = headers.get("strict_transport_security", {})
        if isinstance(hsts, dict):
            max_age = hsts.get("max_age", 0)
            if max_age < 31536000 and not config.get("app", {}).get("debug", False):  # 1 year
                issues.append(("warning", "security.headers.strict_transport_security.max_age",
                              "HSTS max-age should be at least 1 year in production"))
        
        # Check CSP
        csp = security_config.get("csp", {})
        if csp and csp.get("enabled", False):
            directives = csp.get("directives", {})
            script_src = directives.get("script_src", [])
            if "'unsafe-inline'" in script_src and not config.get("app", {}).get("debug", False):
                issues.append(("warning", "security.csp.directives.script_src",
                              "unsafe-inline in script-src reduces CSP effectiveness"))
    
    return issues


def get_security_recommendations(selections: Dict[str, Any]) -> List[str]:
    """Get security recommendations based on feature selections.
    
    Args:
        selections: User selections
        
    Returns:
        List of security recommendation strings
    """
    recommendations = []
    
    if selections.get("include_auth", False):
        recommendations.extend([
            "Use environment variables for all secrets in production",
            "Enable 2FA for admin accounts",
            "Implement password complexity requirements",
            "Consider adding account lockout mechanisms",
            "Use secure password hashing (bcrypt, scrypt, or Argon2)"
        ])
    
    if selections.get("include_api", False):
        recommendations.extend([
            "Implement API versioning from the start",
            "Use API rate limiting per user/IP",
            "Validate all input data with schemas",
            "Implement proper error handling without information leakage",
            "Consider API authentication (OAuth2, API keys)"
        ])
    
    if selections.get("include_csrf", False):
        recommendations.extend([
            "Use double-submit cookie pattern for enhanced CSRF protection",
            "Validate CSRF tokens on all state-changing requests",
            "Consider SameSite cookie attribute for additional protection"
        ])
    
    if selections.get("include_rate_limiting", False):
        recommendations.extend([
            "Monitor rate limit metrics to adjust thresholds",
            "Implement different limits for authenticated vs anonymous users",
            "Consider distributed rate limiting for multi-instance deployments"
        ])
    
    if selections.get("include_security_headers", False):
        recommendations.extend([
            "Regularly review and update Content Security Policy",
            "Test security headers with online tools",
            "Consider implementing security.txt file",
            "Monitor for security header compliance"
        ])
    
    # General recommendations
    recommendations.extend([
        "Keep all dependencies updated regularly",
        "Implement comprehensive logging and monitoring",
        "Use HTTPS everywhere in production",
        "Regular security audits and penetration testing",
        "Implement proper backup and disaster recovery procedures"
    ])
    
    return recommendations


def generate_security_checklist(selections: Dict[str, Any]) -> Dict[str, List[str]]:
    """Generate deployment security checklist.
    
    Args:
        selections: User selections
        
    Returns:
        Dictionary with categorized security checklist items
    """
    checklist = {
        "environment": [
            "Set BEGINNINGS_ENV=production",
            "Use environment variables for all secrets",
            "Enable HTTPS with valid SSL certificates",
            "Configure secure reverse proxy (nginx/Apache)",
            "Disable debug mode in production"
        ],
        "authentication": [],
        "network": [
            "Configure firewall rules",
            "Disable unused services and ports",
            "Use secure protocols (TLS 1.2+)",
            "Implement network monitoring"
        ],
        "application": [
            "Update all dependencies to latest versions",
            "Run security linters and scanners",
            "Implement proper error handling",
            "Enable audit logging"
        ],
        "monitoring": [
            "Set up application monitoring",
            "Configure security event alerting",
            "Implement health checks",
            "Set up log aggregation"
        ]
    }
    
    if selections.get("include_auth", False):
        checklist["authentication"].extend([
            "Generate strong session and JWT secrets",
            "Configure secure session settings",
            "Enable account lockout protection",
            "Implement password policies",
            "Set appropriate token expiration times"
        ])
    
    if selections.get("include_rate_limiting", False):
        checklist["application"].extend([
            "Configure appropriate rate limits",
            "Set up rate limit monitoring",
            "Test rate limiting effectiveness"
        ])
    
    if selections.get("include_security_headers", False):
        checklist["application"].extend([
            "Validate Content Security Policy",
            "Test security headers with online tools",
            "Configure CORS appropriately"
        ])
    
    return checklist


def show_security_summary(selections: Dict[str, Any], config_defaults: Dict[str, Any]):
    """Display security configuration summary to user.
    
    Args:
        selections: User selections
        config_defaults: Generated security defaults
    """
    click.echo(f"\n{click.style('Security Configuration Summary', fg='green', bold=True)}")
    click.echo("=" * 50)
    
    # Show enabled security features
    features = []
    if selections.get("include_auth", False):
        features.append("✓ Authentication & Session Management")
    if selections.get("include_csrf", False):
        features.append("✓ CSRF Protection")
    if selections.get("include_rate_limiting", False):
        features.append("✓ Rate Limiting")
    if selections.get("include_security_headers", False):
        features.append("✓ Security Headers & CSP")
    
    if features:
        click.echo(f"\n{click.style('Enabled Security Features:', fg='cyan')}")
        for feature in features:
            click.echo(f"  {feature}")
    
    # Show generated secrets (truncated)
    if config_defaults:
        click.echo(f"\n{click.style('Generated Secure Defaults:', fg='cyan')}")
        for key, value in config_defaults.items():
            if "SECRET" in key:
                click.echo(f"  {key}: {value[:8]}... (32 chars)")
            else:
                click.echo(f"  {key}: {value}")
    
    # Show important security notes
    click.echo(f"\n{click.style('Important Security Notes:', fg='yellow', bold=True)}")
    click.echo("  • All secrets are generated randomly and stored in .env.example")
    click.echo("  • Copy .env.example to .env and update values for production")
    click.echo("  • Review config/app.yaml for security settings")
    click.echo("  • Run 'beginnings config validate' to check security compliance")
    
    # Show next steps
    click.echo(f"\n{click.style('Next Steps:', fg='blue', bold=True)}")
    click.echo("  1. Review and customize security settings in config/")
    click.echo("  2. Set strong production secrets in environment variables")  
    click.echo("  3. Enable HTTPS and security headers in production")
    click.echo("  4. Regular security audits and dependency updates")