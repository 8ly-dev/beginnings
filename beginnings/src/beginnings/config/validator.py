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

    # Example security checks - add more as needed
    if config.get("secret_key") == "default" or config.get("secret_key") == "":
        issues.append("Secret key should not be default or empty")

    if config.get("debug") and config.get("host") == "0.0.0.0":  # nosec B104
        issues.append("Debug mode with public host binding is a security risk")

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
