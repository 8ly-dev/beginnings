"""
CSRF protection extension for Beginnings framework.

This module provides Cross-Site Request Forgery (CSRF) protection with
token generation, validation, template integration, and AJAX support.
"""

from beginnings.extensions.csrf.extension import CSRFExtension

__all__ = ["CSRFExtension"]