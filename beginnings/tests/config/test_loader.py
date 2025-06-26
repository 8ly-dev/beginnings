"""Tests for configuration loading functionality."""

from __future__ import annotations

import os
import tempfile

import pytest

from beginnings.config.loader import (
    ConfigurationLoadError,
    load_configuration_from_environment,
    load_configuration_from_file,
    merge_configurations,
)


def test_load_configuration_from_file_success() -> None:
    """Test successful configuration loading from YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("debug: true\nport: 8080\n")
        temp_path = f.name

    try:
        config = load_configuration_from_file(temp_path)
        assert config["debug"] is True
        assert config["port"] == 8080
    finally:
        os.unlink(temp_path)


def test_load_configuration_from_file_not_found() -> None:
    """Test configuration loading from non-existent file."""
    with pytest.raises(ConfigurationLoadError, match="Configuration file not found"):
        load_configuration_from_file("/nonexistent/path.yml")


def test_load_configuration_from_environment() -> None:
    """Test loading configuration from environment variables."""
    os.environ["BEGINNINGS_TEST_VALUE"] = "test123"
    os.environ["BEGINNINGS_PORT"] = "9000"
    os.environ["OTHER_VAR"] = "ignored"

    try:
        config = load_configuration_from_environment("BEGINNINGS_")
        assert config["test_value"] == "test123"
        assert config["port"] == "9000"
        assert "other_var" not in config
    finally:
        os.environ.pop("BEGINNINGS_TEST_VALUE", None)
        os.environ.pop("BEGINNINGS_PORT", None)
        os.environ.pop("OTHER_VAR", None)


def test_merge_configurations() -> None:
    """Test merging multiple configuration dictionaries."""
    config1 = {"debug": True, "port": 8000, "host": "localhost"}
    config2 = {"port": 9000, "name": "test"}
    config3 = {"debug": False}

    merged = merge_configurations(config1, config2, config3)

    assert merged["debug"] is False  # overridden by config3
    assert merged["port"] == 9000    # overridden by config2
    assert merged["host"] == "localhost"  # from config1
    assert merged["name"] == "test"  # from config2


def test_load_empty_yaml_file() -> None:
    """Test loading an empty YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("")  # Empty file
        temp_path = f.name

    try:
        config = load_configuration_from_file(temp_path)
        assert config == {}
    finally:
        os.unlink(temp_path)
