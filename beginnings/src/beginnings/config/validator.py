"""
Configuration validation functionality for Beginnings framework.

This module provides utilities for validating configuration values
and detecting conflicts or security issues.
"""

from __future__ import annotations

from typing import Any


class ConfigurationValidationError(Exception):
    """Raised when configuration validation fails."""


class ConfigurationSecurityError(ConfigurationValidationError):
    """Raised when configuration contains security issues."""


def validate_configuration_structure(config: dict[str, Any]) -> None:
    """
    Validate the basic structure of a configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ConfigurationValidationError: If the configuration structure is invalid
    """
    if not isinstance(config, dict):
        msg = "Configuration must be a dictionary"
        raise ConfigurationValidationError(msg)

    # Add more structural validation as needed


def detect_configuration_conflicts(config: dict[str, Any]) -> list[str]:
    """
    Detect potential conflicts in configuration values.

    Args:
        config: Configuration dictionary to analyze

    Returns:
        List of conflict descriptions
    """
    conflicts = []

    # Example conflict detection - add more as needed
    if config.get("debug") and config.get("production"):
        conflicts.append("Debug mode and production mode cannot both be enabled")

    return conflicts


def scan_for_security_issues(config: dict[str, Any]) -> list[str]:
    """
    Scan configuration for potential security issues.

    Args:
        config: Configuration dictionary to scan

    Returns:
        List of security issue descriptions
    """
    issues = []

    # Core security checks
    if config.get("secret_key") == "default" or config.get("secret_key") == "":
        issues.append("Secret key should not be default or empty")

    if config.get("debug") and config.get("host") == "0.0.0.0":  # nosec B104
        issues.append("Debug mode with public host binding is a security risk")

    # Authentication extension security checks
    auth_config = config.get("auth", {})
    if auth_config:
        issues.extend(_validate_auth_security(auth_config))
    
    # CSRF extension security checks  
    csrf_config = config.get("csrf", {})
    if csrf_config:
        issues.extend(_validate_csrf_security(csrf_config))
    
    # Rate limiting extension security checks
    rate_limit_config = config.get("rate_limiting", {})
    if rate_limit_config:
        issues.extend(_validate_rate_limiting_security(rate_limit_config))
    
    # Security headers extension checks
    security_config = config.get("security", {})
    if security_config:
        issues.extend(_validate_security_headers(security_config))

    return issues


def _validate_auth_security(auth_config: dict[str, Any]) -> list[str]:
    """Validate authentication configuration security."""
    issues = []
    
    # JWT security checks
    providers = auth_config.get("providers", {})
    jwt_config = providers.get("jwt", {})
    if jwt_config:
        secret_key = jwt_config.get("secret_key", "")
        if len(secret_key) < 32:
            issues.append("JWT secret key should be at least 32 characters long")
        
        algorithm = jwt_config.get("algorithm", "HS256")
        if algorithm not in ["HS256", "HS512", "RS256", "RS512"]:
            issues.append(f"JWT algorithm '{algorithm}' is not recommended")
        
        expire_minutes = jwt_config.get("token_expire_minutes", 30)
        if expire_minutes > 1440:  # 24 hours
            issues.append("JWT token expiration longer than 24 hours is risky")
    
    # Session security checks
    session_config = providers.get("session", {})
    if session_config:
        session_secret = session_config.get("secret_key", "")
        if len(session_secret) < 32:
            issues.append("Session secret key should be at least 32 characters long")
        
        if not session_config.get("cookie_secure", False):
            issues.append("Session cookies should be secure in production")
        
        if not session_config.get("cookie_httponly", True):
            issues.append("Session cookies should be HttpOnly")
    
    # OAuth security checks
    oauth_config = providers.get("oauth", {})
    if oauth_config:
        for provider_name, provider_config in oauth_config.items():
            if not provider_config.get("client_secret"):
                issues.append(f"OAuth provider '{provider_name}' missing client_secret")
    
    # Password policy checks
    security = auth_config.get("security", {})
    if security:
        min_length = security.get("password_min_length", 8)
        if min_length < 8:
            issues.append("Password minimum length should be at least 8 characters")
        
        lockout_attempts = security.get("account_lockout_attempts", 5)
        if lockout_attempts > 10:
            issues.append("Account lockout attempts should be 10 or fewer")
    
    return issues


def _validate_csrf_security(csrf_config: dict[str, Any]) -> list[str]:
    """Validate CSRF configuration security."""
    issues = []
    
    token_length = csrf_config.get("token_length", 32)
    if token_length < 16:
        issues.append("CSRF token length should be at least 16 characters")
    
    expire_minutes = csrf_config.get("token_expire_minutes", 60)
    if expire_minutes > 480:  # 8 hours
        issues.append("CSRF token expiration longer than 8 hours is risky")
    
    if not csrf_config.get("double_submit_cookie", True):
        issues.append("CSRF double submit cookie pattern is recommended")
    
    return issues


def _validate_rate_limiting_security(rate_limit_config: dict[str, Any]) -> list[str]:
    """Validate rate limiting configuration security."""
    issues = []
    
    global_config = rate_limit_config.get("global", {})
    if global_config.get("enabled", False):
        requests = global_config.get("requests", 1000)
        window_seconds = global_config.get("window_seconds", 3600)
        
        # Check for overly permissive rate limits
        rate_per_minute = (requests * 60) / window_seconds
        if rate_per_minute > 100:
            issues.append("Global rate limit may be too permissive (>100 requests/minute)")
    
    # Check route-specific rate limits
    routes = rate_limit_config.get("routes", {})
    for route_pattern, route_config in routes.items():
        if "/api/" in route_pattern:
            requests = route_config.get("requests", 100)
            window_seconds = route_config.get("window_seconds", 60)
            rate_per_minute = (requests * 60) / window_seconds
            
            if rate_per_minute > 200:
                issues.append(f"API route '{route_pattern}' rate limit may be too permissive")
    
    return issues


def _validate_security_headers(security_config: dict[str, Any]) -> list[str]:
    """Validate security headers configuration."""
    issues = []
    
    headers = security_config.get("headers", {})
    
    # Check for missing or weak security headers
    if headers.get("x_frame_options") not in ["DENY", "SAMEORIGIN"]:
        issues.append("X-Frame-Options should be DENY or SAMEORIGIN")
    
    hsts = headers.get("strict_transport_security", {})
    if isinstance(hsts, dict):
        max_age = hsts.get("max_age", 0)
        if max_age < 31536000:  # 1 year
            issues.append("HSTS max-age should be at least 1 year (31536000 seconds)")
    
    # CSP validation
    csp = security_config.get("csp", {})
    if csp.get("enabled", True):
        directives = csp.get("directives", {})
        
        # Check for unsafe CSP directives
        script_src = directives.get("script_src", [])
        if "'unsafe-eval'" in script_src:
            issues.append("CSP script-src contains unsafe-eval which is dangerous")
        
        if "'unsafe-inline'" in script_src:
            issues.append("CSP script-src contains unsafe-inline, consider using nonces")
    
    return issues


def validate_configuration_with_security_check(config: dict[str, Any]) -> None:
    """
    Perform complete configuration validation including security checks.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ConfigurationValidationError: If validation fails
        ConfigurationSecurityError: If security issues are found
    """
    validate_configuration_structure(config)

    conflicts = detect_configuration_conflicts(config)
    if conflicts:
        raise ConfigurationValidationError(f"Configuration conflicts: {', '.join(conflicts)}")

    security_issues = scan_for_security_issues(config)
    if security_issues:
        raise ConfigurationSecurityError(f"Security issues: {', '.join(security_issues)}")


class ConfigValidator:
    """Configuration validator for CLI commands."""
    
    def validate(self, config: dict[str, Any], include_security: bool = False) -> dict[str, list[str]]:
        """
        Validate configuration and return results.
        
        Args:
            config: Configuration dictionary to validate
            include_security: Whether to include security audit
            
        Returns:
            Dictionary with 'errors', 'warnings', and 'info' lists
        """
        result = {"errors": [], "warnings": [], "info": []}
        
        try:
            validate_configuration_structure(config)
        except ConfigurationValidationError as e:
            result["errors"].append(str(e))
        
        # Check for conflicts
        conflicts = detect_configuration_conflicts(config)
        result["warnings"].extend(conflicts)
        
        # Security checks if requested
        if include_security:
            try:
                security_issues = scan_for_security_issues(config)
                if security_issues:
                    # Treat as warnings for CLI validation unless critical
                    result["warnings"].extend(security_issues)
            except Exception as e:
                result["errors"].append(f"Security validation failed: {e}")
        
        # Add informational items
        result["info"].append(f"Configuration contains {len(config)} top-level sections")
        
        if config.get("extensions"):
            result["info"].append(f"Configuration loads {len(config['extensions'])} extensions")
        
        return result
