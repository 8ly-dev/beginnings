"""
Core components of the Beginnings framework.

This package contains the fundamental components that make up
the Beginnings framework including the main App class and
error handling system.
"""

from __future__ import annotations

from beginnings.core.app import App
from beginnings.core.errors import (
    BeginningsError,
    ConfigurationConflictError,
    ConfigurationError,
    ConfigurationIncludeError,
    ConfigurationInterpolationError,
    EnvironmentError as BeginningsEnvironmentError,
    ExtensionError,
    RoutingError,
    ValidationError,
)

__all__ = [
    "App",
    "BeginningsError",
    "ConfigurationConflictError",
    "ConfigurationError",
    "ConfigurationIncludeError",
    "ConfigurationInterpolationError",
    "EnvironmentError",
    "ExtensionError",
    "RoutingError",
    "ValidationError",
]
