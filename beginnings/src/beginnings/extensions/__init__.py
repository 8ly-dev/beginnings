"""
Extension system for Beginnings framework.

This package provides the extension interface and loading mechanism
for building modular Beginnings applications.
"""

from __future__ import annotations

from beginnings.extensions.base import (
    BaseExtension,
    ExtensionError,
    ExtensionInitializationError,
    ExtensionLoadError,
)
from beginnings.extensions.loader import ExtensionManager

__all__ = [
    "BaseExtension",
    "ExtensionError",
    "ExtensionInitializationError",
    "ExtensionLoadError",
    "ExtensionManager",
]
