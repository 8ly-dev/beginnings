"""
Configuration management for Beginnings framework.

This package provides configuration loading, validation, and management
functionality for Beginnings applications.
"""

from __future__ import annotations

from beginnings.config.loader import (
    ConfigurationLoadError,
    load_configuration_from_environment,
    load_configuration_from_file,
    merge_configurations,
)
from beginnings.config.validator import (
    ConfigurationSecurityError,
    ConfigurationValidationError,
    detect_configuration_conflicts,
    scan_for_security_issues,
    validate_configuration_structure,
    validate_configuration_with_security_check,
)

__all__ = [
    "ConfigurationLoadError",
    "ConfigurationSecurityError",
    "ConfigurationValidationError",
    "detect_configuration_conflicts",
    "load_configuration_from_environment",
    "load_configuration_from_file",
    "merge_configurations",
    "scan_for_security_issues",
    "validate_configuration_structure",
    "validate_configuration_with_security_check",
]
