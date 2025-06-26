"""Tests for enhanced configuration loading with includes and interpolation."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from beginnings.config.enhanced_loader import (
    ConfigurationConflictError,
    ConfigurationIncludeError,
    ConfigurationInterpolationError,
    EnhancedConfigLoader,
)


class TestIncludeProcessing:
    """Test configuration include directive processing."""

    def test_single_include_file_merge(self) -> None:
        """Test loading single included file and merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create base config with include
            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "database.yaml"
""")

            # Create included config
            db_config = config_dir / "database.yaml"
            db_config.write_text("""
database:
  host: "localhost"
  port: 5432
""")

            loader = EnhancedConfigLoader(str(config_dir))
            config = loader.load_config()

            assert config["app"]["name"] == "test-app"
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432

    def test_multiple_include_files_merge_order(self) -> None:
        """Test multiple included files merge in correct order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "database.yaml"
  - "cache.yaml"
""")

            db_config = config_dir / "database.yaml"
            db_config.write_text("""
database:
  host: "localhost"
""")

            cache_config = config_dir / "cache.yaml"
            cache_config.write_text("""
cache:
  type: "redis"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            config = loader.load_config()

            assert config["app"]["name"] == "test-app"
            assert config["database"]["host"] == "localhost"
            assert config["cache"]["type"] == "redis"

    def test_conflict_detection_between_files(self) -> None:
        """Test conflict detection when files have duplicate top-level keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "config1.yaml"
  - "config2.yaml"
""")

            config1 = config_dir / "config1.yaml"
            config1.write_text("""
shared:
  value: "from-config1"
""")

            config2 = config_dir / "config2.yaml"
            config2.write_text("""
shared:
  value: "from-config2"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            with pytest.raises(ConfigurationConflictError, match="Key 'shared' found in multiple files"):
                loader.load_config()

    def test_circular_include_detection(self) -> None:
        """Test detection of circular include dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "config1.yaml"
""")

            config1 = config_dir / "config1.yaml"
            config1.write_text("""
section1:
  value: "test"
include:
  - "config2.yaml"
""")

            config2 = config_dir / "config2.yaml"
            config2.write_text("""
section2:
  value: "test"
include:
  - "config1.yaml"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            with pytest.raises(ConfigurationIncludeError, match="Circular include detected"):
                loader.load_config()

    def test_missing_include_file_error(self) -> None:
        """Test clear error when included file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "nonexistent.yaml"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            with pytest.raises(ConfigurationIncludeError, match="Include file not found"):
                loader.load_config()

    def test_path_traversal_prevention(self) -> None:
        """Test prevention of path traversal in include directives."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "../../../etc/passwd"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            with pytest.raises(ConfigurationIncludeError, match="Include path cannot escape"):
                loader.load_config()

    def test_nested_includes_work_correctly(self) -> None:
        """Test that included files can themselves have includes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "test-app"
include:
  - "main.yaml"
""")

            main_config = config_dir / "main.yaml"
            main_config.write_text("""
main:
  section: "value"
include:
  - "nested.yaml"
""")

            nested_config = config_dir / "nested.yaml"
            nested_config.write_text("""
nested:
  value: "deep"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            config = loader.load_config()

            assert config["app"]["name"] == "test-app"
            assert config["main"]["section"] == "value"
            assert config["nested"]["value"] == "deep"


class TestEnvironmentVariableInterpolation:
    """Test environment variable interpolation in configuration."""

    def test_simple_variable_interpolation(self) -> None:
        """Test basic ${VAR} interpolation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  name: "${APP_NAME}"
  port: ${APP_PORT}
""")

            env_vars = {
                "APP_NAME": "test-application",
                "APP_PORT": "8080",
            }

            with self._mock_env(env_vars):
                loader = EnhancedConfigLoader(str(config_dir))
                config = loader.load_config()

                assert config["app"]["name"] == "test-application"
                assert config["app"]["port"] == "8080"

    def test_variable_with_default_value(self) -> None:
        """Test ${VAR:-default} syntax for default values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  name: "${APP_NAME:-default-app}"
  debug: "${DEBUG:-false}"
""")

            # Test with environment variable not set
            with self._mock_env({}):
                loader = EnhancedConfigLoader(str(config_dir))
                config = loader.load_config()

                assert config["app"]["name"] == "default-app"
                assert config["app"]["debug"] == "false"

            # Test with environment variable set
            with self._mock_env({"APP_NAME": "custom-app", "DEBUG": "true"}):
                loader = EnhancedConfigLoader(str(config_dir))
                config = loader.load_config()

                assert config["app"]["name"] == "custom-app"
                assert config["app"]["debug"] == "true"

    def test_nested_variable_interpolation(self) -> None:
        """Test interpolation in nested configuration structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
database:
  host: "${DB_HOST:-localhost}"
  credentials:
    username: "${DB_USER}"
    password: "${DB_PASS}"
""")

            env_vars = {
                "DB_USER": "testuser",
                "DB_PASS": "secret123",
            }

            with self._mock_env(env_vars):
                loader = EnhancedConfigLoader(str(config_dir))
                config = loader.load_config()

                assert config["database"]["host"] == "localhost"
                assert config["database"]["credentials"]["username"] == "testuser"
                assert config["database"]["credentials"]["password"] == "secret123"

    def test_missing_variable_without_default_error(self) -> None:
        """Test error when environment variable is missing and no default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  secret: "${MISSING_VAR}"
""")

            with self._mock_env({}):
                loader = EnhancedConfigLoader(str(config_dir))
                with pytest.raises(ConfigurationInterpolationError, match="Environment variable 'MISSING_VAR' not found"):
                    loader.load_config()

    def test_malformed_interpolation_syntax(self) -> None:
        """Test error handling for malformed interpolation syntax."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  invalid: "${UNCLOSED_VAR"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            with pytest.raises(ConfigurationInterpolationError, match="Malformed variable interpolation"):
                loader.load_config()

    def test_security_prevents_code_execution(self) -> None:
        """Test that interpolation prevents code execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  dangerous: "${`rm -rf /`}"
""")

            loader = EnhancedConfigLoader(str(config_dir))
            # Should not execute code, just treat as missing variable
            with pytest.raises(ConfigurationInterpolationError):
                loader.load_config()

    def _mock_env(self, env_vars: dict[str, str]):
        """Context manager to mock environment variables."""
        import unittest.mock
        return unittest.mock.patch.dict(os.environ, env_vars, clear=True)


class TestEnhancedConfigLoaderIntegration:
    """Test EnhancedConfigLoader integration functionality."""

    def test_complete_config_loading_flow(self) -> None:
        """Test complete configuration loading with all features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Main config with environment detection and includes
            base_config = config_dir / "app.yaml"
            base_config.write_text("""
app:
  name: "${APP_NAME:-beginnings-app}"
  environment: "${BEGINNINGS_ENV:-production}"
include:
  - "database.yaml"
  - "cache.yaml"
""")

            db_config = config_dir / "database.yaml"
            db_config.write_text("""
database:
  url: "${DATABASE_URL:-sqlite:///app.db}"
  pool_size: ${DB_POOL_SIZE:-5}
""")

            cache_config = config_dir / "cache.yaml"
            cache_config.write_text("""
cache:
  backend: "${CACHE_BACKEND:-memory}"
  ttl: ${CACHE_TTL:-300}
""")

            env_vars = {
                "APP_NAME": "test-application",
                "DATABASE_URL": "postgresql://localhost/testdb",
                "CACHE_BACKEND": "redis",
            }

            with self._mock_env(env_vars):
                loader = EnhancedConfigLoader(str(config_dir))
                config = loader.load_config()

                # Verify base configuration
                assert config["app"]["name"] == "test-application"
                assert config["app"]["environment"] == "production"

                # Verify included configurations
                assert config["database"]["url"] == "postgresql://localhost/testdb"
                assert config["database"]["pool_size"] == "5"  # Default used

                assert config["cache"]["backend"] == "redis"
                assert config["cache"]["ttl"] == "300"  # Default used

    def test_config_caching_functionality(self) -> None:
        """Test that configuration is cached after first load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  name: "test-app"
""")

            loader = EnhancedConfigLoader(str(config_dir))

            # First load
            config1 = loader.load_config()

            # Modify file after first load
            config_file.write_text("""
app:
  name: "modified-app"
""")

            # Second load should return cached config
            config2 = loader.load_config()

            assert config1 == config2
            assert config1["app"]["name"] == "test-app"

    def test_force_reload_bypasses_cache(self) -> None:
        """Test force_reload parameter bypasses cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            config_file = config_dir / "app.yaml"
            config_file.write_text("""
app:
  name: "test-app"
""")

            loader = EnhancedConfigLoader(str(config_dir))

            # First load
            config1 = loader.load_config()

            # Modify file
            config_file.write_text("""
app:
  name: "modified-app"
""")

            # Force reload should get new config
            config2 = loader.load_config(force_reload=True)

            assert config1["app"]["name"] == "test-app"
            assert config2["app"]["name"] == "modified-app"

    def _mock_env(self, env_vars: dict[str, str]):
        """Context manager to mock environment variables."""
        import unittest.mock
        return unittest.mock.patch.dict(os.environ, env_vars, clear=True)
