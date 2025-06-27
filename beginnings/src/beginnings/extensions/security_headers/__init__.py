"""
Security headers extension for Beginnings framework.

This module provides comprehensive security headers including CSP, CORS,
and standard security headers with route-specific customization.
"""

from beginnings.extensions.security_headers.extension import SecurityHeadersExtension

__all__ = ["SecurityHeadersExtension"]