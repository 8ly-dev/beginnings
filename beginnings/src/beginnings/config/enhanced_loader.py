"""
Enhanced configuration loader with includes and environment variable interpolation.

This module provides advanced configuration loading capabilities including
file includes, conflict detection, and secure environment variable interpolation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from beginnings.config.environment import EnvironmentDetector
from beginnings.core.errors import (
    ConfigurationConflictError,
    ConfigurationIncludeError,
    ConfigurationInterpolationError,
)


def load_config_with_includes(
    config_dir: str,
    environment: str | None = None
) -> dict[str, Any]:
    """
    Load configuration with includes for the given environment.

    Args:
        config_dir: Directory containing configuration files
        environment: Environment name (auto-detected if None)

    Returns:
        Merged configuration dictionary
    """
    loader = EnhancedConfigLoader(config_dir, environment)
    return loader.load_config()


class EnhancedConfigLoader:
    """
    Enhanced configuration loader with includes and interpolation.

    Provides configuration loading with:
    - File include processing with conflict detection
    - Environment variable interpolation
    - Configuration caching
    - Security safeguards
    """

    def __init__(
        self,
        config_dir: str,
        environment: str | None = None
    ) -> None:
        """
        Initialize enhanced configuration loader.

        Args:
            config_dir: Directory containing configuration files
            environment: Environment name (auto-detected if None)
        """
        self._detector = EnvironmentDetector(config_dir, environment)
        self._cached_config: dict[str, Any] | None = None
        self._loaded_files: set[str] = set()

    def load_config(self, *, force_reload: bool = False) -> dict[str, Any]:
        """
        Load and merge configuration with all enhancements.

        Args:
            force_reload: Force reload even if config is cached

        Returns:
            Merged configuration dictionary
        """
        if self._cached_config is not None and not force_reload:
            return self._cached_config

        # Reset state for reload
        self._loaded_files.clear()

        # Resolve main configuration file
        config_file = self._detector.resolve_config_file()

        # Load base configuration
        base_config = self._load_yaml_file(config_file)

        # Process includes if present
        if "include" in base_config:
            included_configs = self._process_includes(
                base_config["include"],
                Path(config_file).parent
            )

            # Merge with conflict detection
            merged_config = self._merge_with_conflict_detection(
                base_config,
                included_configs
            )
        else:
            merged_config = base_config

        # Remove include directive from final config
        merged_config.pop("include", None)

        # Interpolate environment variables
        interpolated_config = self._interpolate_variables(merged_config)

        # Cache the result
        self._cached_config = interpolated_config

        return interpolated_config

    def _load_yaml_file(self, file_path: str) -> dict[str, Any]:
        """
        Load and parse a YAML file safely.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed configuration dictionary
        """
        abs_path = str(Path(file_path).absolute())

        # Prevent loading same file multiple times (circular includes)
        if abs_path in self._loaded_files:
            raise ConfigurationIncludeError(f"Circular include detected: {file_path}")

        self._loaded_files.add(abs_path)

        try:
            with Path(file_path).open(encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            if not isinstance(config, dict):
                raise ConfigurationIncludeError(
                    f"Configuration file must contain a dictionary: {file_path}"
                )

        except FileNotFoundError as e:
            raise ConfigurationIncludeError(f"Include file not found: {file_path}") from e
        except yaml.YAMLError as e:
            raise ConfigurationIncludeError(f"YAML parsing error in {file_path}: {e}") from e
        else:
            return config

    def _process_includes(
        self,
        include_list: list[str],
        config_dir: Path
    ) -> list[dict[str, Any]]:
        """
        Process include directives and load referenced files.

        Args:
            include_list: List of file paths to include
            config_dir: Base directory for relative paths

        Returns:
            List of loaded configuration dictionaries
        """
        included_configs = []

        for include_path in include_list:
            # Validate include path security
            self._validate_include_path(include_path, config_dir)

            # Resolve full path
            if Path(include_path).is_absolute():
                full_path = Path(include_path)
            else:
                full_path = config_dir / include_path

            # Load included configuration
            included_config = self._load_yaml_file(str(full_path))

            # Process nested includes recursively
            if "include" in included_config:
                nested_includes = self._process_includes(
                    included_config["include"],
                    full_path.parent
                )

                # Merge nested includes into this config
                nested_merged = self._merge_configs_simple(
                    included_config,
                    nested_includes
                )
                nested_merged.pop("include", None)
                included_configs.append(nested_merged)
            else:
                included_configs.append(included_config)

        return included_configs

    def _validate_include_path(self, include_path: str, config_dir: Path) -> None:
        """
        Validate include path for security (prevent path traversal).

        Args:
            include_path: Path to validate
            config_dir: Base configuration directory

        Raises:
            ConfigurationIncludeError: If path is invalid or unsafe
        """
        # Resolve the path
        if Path(include_path).is_absolute():
            resolved_path = Path(include_path).resolve()
        else:
            resolved_path = (config_dir / include_path).resolve()

        # Check if resolved path is within config directory
        config_dir_resolved = config_dir.resolve()

        try:
            resolved_path.relative_to(config_dir_resolved)
        except ValueError as e:
            raise ConfigurationIncludeError(
                f"Include path cannot escape configuration directory: {include_path}"
            ) from e

    def _merge_with_conflict_detection(
        self,
        base_config: dict[str, Any],
        included_configs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Merge configurations with top-level key conflict detection.

        Args:
            base_config: Base configuration dictionary
            included_configs: List of included configuration dictionaries

        Returns:
            Merged configuration dictionary

        Raises:
            ConfigurationConflictError: If top-level keys conflict
        """
        # Collect all top-level keys and their sources
        key_sources: dict[str, list[str]] = {}

        # Add base config keys
        for key in base_config:
            if key != "include":  # Exclude include directive
                key_sources.setdefault(key, []).append("base config")

        # Add included config keys with their file tracking
        for i, included_config in enumerate(included_configs):
            for key in included_config:
                if key != "include":
                    key_sources.setdefault(key, []).append(f"include file {i + 1}")

        # Check for conflicts (keys appearing in multiple sources)
        conflicts = {
            key: sources for key, sources in key_sources.items()
            if len(sources) > 1
        }

        if conflicts:
            conflict_messages = []
            for key, sources in conflicts.items():
                conflict_messages.append(
                    f"Key '{key}' found in multiple files: {', '.join(sources)}"
                )

            raise ConfigurationConflictError(
                "Configuration conflicts detected:\n" + "\n".join(conflict_messages)
            )

        # No conflicts, safe to merge
        return self._merge_configs_simple(base_config, included_configs)

    def _merge_configs_simple(
        self,
        base_config: dict[str, Any],
        included_configs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Simple merge of configurations using dict.update semantics.

        Args:
            base_config: Base configuration
            included_configs: Configurations to merge in

        Returns:
            Merged configuration
        """
        result = base_config.copy()

        for included_config in included_configs:
            result.update(included_config)

        return result

    def _interpolate_variables(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Interpolate environment variables in configuration values.

        Supports ${VAR} and ${VAR:-default} syntax.

        Args:
            config: Configuration dictionary to interpolate

        Returns:
            Configuration with interpolated values
        """
        def interpolate_value(value: Any) -> Any:  # noqa: ANN401
            if isinstance(value, str):
                return self._interpolate_string(value)
            if isinstance(value, dict):
                return {k: interpolate_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [interpolate_value(item) for item in value]
            return value

        result = interpolate_value(config)
        return result if isinstance(result, dict) else {}

    def _interpolate_string(self, value: str) -> str:
        """
        Interpolate environment variables in a string value.

        Args:
            value: String to interpolate

        Returns:
            String with variables interpolated
        """
        # Check for malformed syntax first
        if "${" in value:
            # Check for unclosed variables
            open_count = value.count("${")
            close_count = value.count("}")
            if open_count > close_count:
                raise ConfigurationInterpolationError(
                    f"Malformed variable interpolation in: {value}"
                )

        # Pattern for ${VAR} or ${VAR:-default}
        pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(3)

            # Security check: ensure var name is valid
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", var_name):
                raise ConfigurationInterpolationError(
                    f"Invalid environment variable name: {var_name}"
                )

            # Get environment variable value
            env_value = os.getenv(var_name)

            if env_value is not None:
                return env_value
            if default_value is not None:
                return default_value
            raise ConfigurationInterpolationError(
                f"Environment variable '{var_name}' not found and no default provided"
            )

        # Check for dangerous patterns (command substitution, etc.)
        dangerous_patterns = [
            r"\$\{`.*`\}",  # Command substitution
            r"\$\{\$\(.*\)\}",  # Command substitution
            r"\$\{.*[;<>&|].*\}",  # Shell operators
        ]

        for dangerous_pattern in dangerous_patterns:
            if re.search(dangerous_pattern, value):
                raise ConfigurationInterpolationError(
                    f"Dangerous interpolation pattern detected in: {value}"
                )

        try:
            return re.sub(pattern, replace_var, value)
        except Exception as e:
            if isinstance(e, ConfigurationInterpolationError):
                raise
            raise ConfigurationInterpolationError(
                f"Malformed variable interpolation in: {value}"
            ) from e

    def clear_cache(self) -> None:
        """Clear cached configuration to force reload on next access."""
        self._cached_config = None
        self._loaded_files.clear()


# Alias for planning document compatibility
ConfigLoader = EnhancedConfigLoader
