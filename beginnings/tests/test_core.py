"""Tests for the core App class."""

from __future__ import annotations

from fastapi import FastAPI

from beginnings import App
from beginnings.core import App as CoreApp


def test_app_creation() -> None:
    """Test basic App instantiation."""
    app = App()
    assert app is not None
    assert isinstance(app, CoreApp)


def test_app_with_config_dir() -> None:
    """Test App creation with config directory."""
    app = App(config_dir="./config")
    assert app is not None


def test_app_is_fastapi() -> None:
    """Test that App is a FastAPI instance."""
    app = App()
    assert isinstance(app, FastAPI)


def test_app_version_available() -> None:
    """Test that version is accessible."""
    from beginnings import __version__
    assert __version__ == "0.1.0"
