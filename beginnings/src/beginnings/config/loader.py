"""
Configuration loading functionality for Beginnings framework.

This module provides utilities for loading configuration from various sources,
including YAML files, environment variables, and Python dictionaries.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigurationLoadError(Exception):
    """Raised when configuration loading fails."""


def load_configuration_from_file(file_path: str | Path) -> dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        file_path: Path to the configuration file

    Returns:
        Dictionary containing the loaded configuration

    Raises:
        ConfigurationLoadError: If the file cannot be loaded or parsed
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise ConfigurationLoadError(f"Configuration file not found: {file_path}")

        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except yaml.YAMLError as e:
        raise ConfigurationLoadError(f"Failed to parse YAML configuration: {e}") from e
    except Exception as e:
        raise ConfigurationLoadError(f"Failed to load configuration: {e}") from e


def load_configuration_from_environment(prefix: str = "BEGINNINGS_") -> dict[str, Any]:
    """
    Load configuration from environment variables.

    Args:
        prefix: Prefix for environment variables to include

    Returns:
        Dictionary containing environment-based configuration
    """
    config = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix):].lower()
            config[config_key] = value
    return config


def merge_configurations(*configs: dict[str, Any]) -> dict[str, Any]:
    """
    Merge multiple configuration dictionaries.

    Later configurations override earlier ones for conflicting keys.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration dictionary
    """
    result = {}
    for config in configs:
        result.update(config)
    return result
