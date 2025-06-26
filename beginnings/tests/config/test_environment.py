"""Tests for environment detection functionality."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from beginnings.config.environment import (
    EnvironmentDetector,
    detect_environment,
    resolve_config_file,
)
from beginnings.core.errors import EnvironmentError


class TestEnvironmentDetection:
    """Test environment detection logic."""

    def test_dev_mode_override_takes_precedence(self) -> None:
        """Test BEGINNINGS_DEV_MODE overrides all other settings."""
        env_vars = {
            "BEGINNINGS_DEV_MODE": "true",
            "BEGINNINGS_ENV": "production",
        }

        with self._mock_env(env_vars):
            env = detect_environment()
            assert env == "development"

    def test_dev_mode_false_uses_beginnings_env(self) -> None:
        """Test BEGINNINGS_DEV_MODE=false falls back to BEGINNINGS_ENV."""
        env_vars = {
            "BEGINNINGS_DEV_MODE": "false",
            "BEGINNINGS_ENV": "staging",
        }

        with self._mock_env(env_vars):
            env = detect_environment()
            assert env == "staging"

    def test_beginnings_env_used_when_dev_mode_not_set(self) -> None:
        """Test BEGINNINGS_ENV used when DEV_MODE not set."""
        env_vars = {
            "BEGINNINGS_ENV": "development",
        }

        with self._mock_env(env_vars):
            env = detect_environment()
            assert env == "development"

    def test_default_to_production_when_no_env_vars(self) -> None:
        """Test defaults to production when no environment variables set."""
        with self._mock_env({}):
            env = detect_environment()
            assert env == "production"

    def test_dev_mode_case_insensitive(self) -> None:
        """Test DEV_MODE handles various true/false values."""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes"]
        false_values = ["false", "False", "FALSE", "0", "no", "No"]

        for true_val in true_values:
            with self._mock_env({"BEGINNINGS_DEV_MODE": true_val}):
                env = detect_environment()
                assert env == "development", f"Failed for: {true_val}"

        for false_val in false_values:
            with self._mock_env({"BEGINNINGS_DEV_MODE": false_val, "BEGINNINGS_ENV": "staging"}):
                env = detect_environment()
                assert env == "staging", f"Failed for: {false_val}"

    def test_environment_normalization(self) -> None:
        """Test environment name normalization."""
        normalization_cases = [
            ("dev", "development"),
            ("stage", "staging"),
            ("prod", "production"),
            ("test", "test"),
            ("custom", "custom"),
        ]

        for input_env, expected in normalization_cases:
            with self._mock_env({"BEGINNINGS_ENV": input_env}):
                env = detect_environment()
                assert env == expected

    def _mock_env(self, env_vars: dict[str, str]):
        """Context manager to mock environment variables."""
        import unittest.mock
        return unittest.mock.patch.dict(os.environ, env_vars, clear=True)


class TestConfigFileResolution:
    """Test configuration file resolution logic."""

    def test_production_uses_base_config_file(self) -> None:
        """Test production environment uses app.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            app_config = config_dir / "app.yaml"
            app_config.write_text("app: {}")

            config_file = resolve_config_file(str(config_dir), "production")
            assert config_file == str(app_config)

    def test_development_tries_env_specific_then_fallback(self) -> None:
        """Test development tries app.development.yaml then app.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Test with environment-specific file
            dev_config = config_dir / "app.development.yaml"
            dev_config.write_text("app: {}")

            config_file = resolve_config_file(str(config_dir), "development")
            assert config_file == str(dev_config)

            # Test fallback to base file
            dev_config.unlink()
            base_config = config_dir / "app.yaml"
            base_config.write_text("app: {}")

            config_file = resolve_config_file(str(config_dir), "development")
            assert config_file == str(base_config)

    def test_custom_environment_file_resolution(self) -> None:
        """Test custom environment names resolve correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            custom_config = config_dir / "app.custom.yaml"
            custom_config.write_text("app: {}")

            config_file = resolve_config_file(str(config_dir), "custom")
            assert config_file == str(custom_config)

    def test_missing_config_files_raises_error(self) -> None:
        """Test missing configuration files raise appropriate error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            with pytest.raises(EnvironmentError, match="No configuration file found"):
                resolve_config_file(str(config_dir), "development")

    def test_custom_config_dir_from_env_var(self) -> None:
        """Test BEGINNINGS_CONFIG_DIR changes configuration directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "custom_config"
            config_dir.mkdir()
            app_config = config_dir / "app.yaml"
            app_config.write_text("app: {}")

            with self._mock_env({"BEGINNINGS_CONFIG_DIR": str(config_dir)}):
                detector = EnvironmentDetector()
                config_file = detector.resolve_config_file("production")
                assert config_file == str(app_config)

    def test_nonexistent_config_dir_raises_error(self) -> None:
        """Test nonexistent config directory raises error."""
        with pytest.raises(EnvironmentError, match="Configuration directory does not exist"):
            resolve_config_file("/nonexistent/path", "production")

    def _mock_env(self, env_vars: dict[str, str]):
        """Context manager to mock environment variables."""
        import unittest.mock
        return unittest.mock.patch.dict(os.environ, env_vars, clear=True)


class TestEnvironmentDetectorClass:
    """Test EnvironmentDetector class functionality."""

    def test_detector_caches_environment(self) -> None:
        """Test EnvironmentDetector caches detected environment."""
        with self._mock_env({"BEGINNINGS_ENV": "staging"}):
            detector = EnvironmentDetector()
            env1 = detector.get_environment()
            env2 = detector.get_environment()
            assert env1 == env2 == "staging"

    def test_detector_config_dir_override(self) -> None:
        """Test EnvironmentDetector respects config_dir parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            app_config = config_dir / "app.yaml"
            app_config.write_text("app: {}")

            detector = EnvironmentDetector(config_dir=str(config_dir))
            config_file = detector.resolve_config_file("production")
            assert config_file == str(app_config)

    def test_detector_environment_override(self) -> None:
        """Test EnvironmentDetector respects environment parameter."""
        detector = EnvironmentDetector(environment="test")
        env = detector.get_environment()
        assert env == "test"

    def _mock_env(self, env_vars: dict[str, str]):
        """Context manager to mock environment variables."""
        import unittest.mock
        return unittest.mock.patch.dict(os.environ, env_vars, clear=True)
