"""
Environment detection and configuration file resolution.

This module handles environment detection from environment variables
and resolves the appropriate configuration file based on the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

from beginnings.core.errors import EnvironmentError as BeginningsEnvironmentError


def detect_environment() -> str:
    """
    Detect the current environment from environment variables.

    Returns:
        Environment name (development, staging, production, etc.)
    """
    # Check BEGINNINGS_DEV_MODE first (highest precedence)
    dev_mode = os.getenv("BEGINNINGS_DEV_MODE", "").lower()
    if dev_mode in ("true", "1", "yes"):
        return "development"
    if dev_mode in ("false", "0", "no"):
        # Dev mode explicitly disabled, check BEGINNINGS_ENV
        env = os.getenv("BEGINNINGS_ENV", "production")
        return _normalize_environment(env)

    # Check BEGINNINGS_ENV
    beginnings_env = os.getenv("BEGINNINGS_ENV")
    if beginnings_env:
        return _normalize_environment(beginnings_env)

    # Default to production
    return "production"


def resolve_config_file(config_dir: str, environment: str) -> str:
    """
    Resolve the configuration file path for the given environment.

    Args:
        config_dir: Directory containing configuration files
        environment: Environment name

    Returns:
        Absolute path to the configuration file

    Raises:
        EnvironmentError: If no configuration file is found
    """
    config_path = Path(config_dir)

    if not config_path.exists():
        raise BeginningsEnvironmentError(f"Configuration directory does not exist: {config_dir}")

    if not config_path.is_dir():
        raise BeginningsEnvironmentError(f"Configuration path is not a directory: {config_dir}")

    # For production, use clean app.yaml
    if environment == "production":
        base_config = config_path / "app.yaml"
        if base_config.exists():
            return str(base_config.absolute())
    else:
        # For other environments, try environment-specific file first
        env_config = config_path / f"app.{environment}.yaml"
        if env_config.exists():
            return str(env_config.absolute())

        # Fall back to base config
        base_config = config_path / "app.yaml"
        if base_config.exists():
            return str(base_config.absolute())

    raise BeginningsEnvironmentError(
        f"No configuration file found for environment '{environment}' in {config_dir}"
    )


def _normalize_environment(env: str) -> str:
    """
    Normalize environment name variations.

    Args:
        env: Raw environment name

    Returns:
        Normalized environment name
    """
    env = env.lower().strip()

    # Normalize common variations
    if env in ("dev", "develop"):
        return "development"
    if env in ("stage", "stg"):
        return "staging"
    if env in ("prod", "production"):
        return "production"
    if env in ("test", "testing"):
        return "test"
    # Return custom environment names as-is
    return env


class EnvironmentDetector:
    """
    Environment detector with configuration caching and overrides.

    Provides environment detection with caching and allows for
    explicit environment and config directory overrides.
    """

    def __init__(
        self,
        config_dir: str | None = None,
        environment: str | None = None
    ) -> None:
        """
        Initialize environment detector.

        Args:
            config_dir: Override default config directory detection
            environment: Override environment detection
        """
        self._config_dir = config_dir
        self._environment = environment
        self._cached_environment: str | None = None
        self._cached_config_dir: str | None = None

    def get_environment(self) -> str:
        """
        Get the detected or overridden environment.

        Returns:
            Environment name
        """
        if self._cached_environment is None:
            if self._environment is not None:
                self._cached_environment = self._environment
            else:
                self._cached_environment = detect_environment()

        return self._cached_environment

    def get_config_dir(self) -> str:
        """
        Get the configuration directory path.

        Returns:
            Absolute path to configuration directory
        """
        if self._cached_config_dir is None:
            if self._config_dir is not None:
                self._cached_config_dir = str(Path(self._config_dir).absolute())
            else:
                # Check environment variable
                env_config_dir = os.getenv("BEGINNINGS_CONFIG_DIR")
                if env_config_dir:
                    self._cached_config_dir = str(Path(env_config_dir).absolute())
                else:
                    # Default to ./config
                    self._cached_config_dir = str(Path.cwd() / "config")

        return self._cached_config_dir

    def resolve_config_file(self, environment: str | None = None) -> str:
        """
        Resolve configuration file for the environment.

        Args:
            environment: Override environment for this resolution

        Returns:
            Absolute path to configuration file
        """
        env = environment or self.get_environment()
        config_dir = self.get_config_dir()

        return resolve_config_file(config_dir, env)

    def clear_cache(self) -> None:
        """Clear cached values to force re-detection."""
        self._cached_environment = None
        self._cached_config_dir = None
