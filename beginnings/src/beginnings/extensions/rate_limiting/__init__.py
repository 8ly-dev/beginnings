"""
Rate limiting extension for Beginnings framework.

This module provides rate limiting capabilities with multiple algorithms,
storage backends, and configurable enforcement policies.
"""

from beginnings.extensions.rate_limiting.extension import RateLimitExtension

__all__ = ["RateLimitExtension"]