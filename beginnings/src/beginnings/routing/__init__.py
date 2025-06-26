"""
Routing functionality for Beginnings framework.

This package provides HTML and API routing utilities with thoughtful
defaults for building web applications and REST APIs.
"""

from __future__ import annotations

from beginnings.routing.api import APIRouter, create_api_response, create_error_response
from beginnings.routing.html import HTMLRouter, create_html_response

__all__ = [
    "APIRouter",
    "HTMLRouter",
    "create_api_response",
    "create_error_response",
    "create_html_response",
]
