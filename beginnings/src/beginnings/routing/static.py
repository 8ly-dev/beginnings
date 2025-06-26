"""
Static file serving functionality for HTMLRouter.

This module provides secure static file serving with proper MIME types,
caching headers, and security protections against path traversal.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

from beginnings.core.errors import BeginningsError


class StaticFileError(BeginningsError):
    """Static file serving and configuration errors."""


class SecureStaticFiles(StaticFiles):
    """
    Secure static file handler with additional security checks.
    
    Extends Starlette's StaticFiles with enhanced security and configuration.
    """

    def __init__(
        self,
        directory: str | Path,
        packages: list[str] | None = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
        allowed_extensions: set[str] | None = None,
        cache_control: str = "public, max-age=3600",
    ) -> None:
        """
        Initialize secure static file handler.

        Args:
            directory: Directory containing static files
            packages: Package names for resource loading
            html: Whether to serve HTML files
            check_dir: Whether to check directory exists
            follow_symlink: Whether to follow symbolic links
            max_file_size: Maximum file size to serve (bytes)
            allowed_extensions: Set of allowed file extensions (None = all)
            cache_control: Cache-Control header value
        """
        super().__init__(
            directory=directory,
            packages=packages,
            html=html,
            check_dir=check_dir,
            follow_symlink=follow_symlink
        )
        
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions
        self.cache_control = cache_control
        
        # Set up MIME types
        mimetypes.init()

    def file_response(
        self,
        full_path: str,
        stat_result: os.stat_result,
        scope: dict[str, Any],
        status_code: int = 200
    ) -> Response:
        """
        Create file response with security checks and proper headers.

        Args:
            full_path: Full path to file
            stat_result: File stat result
            scope: ASGI scope
            status_code: HTTP status code

        Returns:
            FileResponse with proper headers

        Raises:
            HTTPException: If file fails security checks
        """
        # Check file size
        if stat_result.st_size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {stat_result.st_size} bytes"
            )
        
        # Check file extension if restrictions are set
        if self.allowed_extensions is not None:
            file_ext = Path(full_path).suffix.lower()
            if file_ext not in self.allowed_extensions:
                raise HTTPException(
                    status_code=403,
                    detail=f"File type not allowed: {file_ext}"
                )
        
        # Get MIME type
        content_type, _ = mimetypes.guess_type(full_path)
        if content_type is None:
            content_type = "application/octet-stream"
        
        # Create response with security headers
        response = FileResponse(
            full_path,
            status_code=status_code,
            media_type=content_type
        )
        
        # Add cache control
        response.headers["Cache-Control"] = self.cache_control
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Add CSP for HTML files
        if content_type == "text/html":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'"
            )
        
        return response


class StaticFileManager:
    """
    Manager for static file configurations and serving.
    
    Handles multiple static file directories with different configurations
    and provides a unified interface for serving static content.
    """

    def __init__(self) -> None:
        """Initialize static file manager."""
        self._static_configs: dict[str, dict[str, Any]] = {}
        self._static_handlers: dict[str, SecureStaticFiles] = {}

    def add_static_directory(
        self,
        url_path: str,
        directory: str | Path,
        **config: Any
    ) -> None:
        """
        Add a static file directory configuration.

        Args:
            url_path: URL path prefix for static files
            directory: Directory containing static files
            **config: Additional static file configuration
        """
        # Validate directory
        dir_path = Path(directory)
        if not dir_path.exists():
            raise StaticFileError(
                f"Static directory does not exist: {directory}",
                context={"directory": str(directory), "url_path": url_path}
            )
        
        if not dir_path.is_dir():
            raise StaticFileError(
                f"Static path is not a directory: {directory}",
                context={"directory": str(directory), "url_path": url_path}
            )
        
        # Store configuration
        self._static_configs[url_path] = {
            "directory": str(dir_path.absolute()),
            **config
        }
        
        # Create static file handler
        self._static_handlers[url_path] = SecureStaticFiles(
            directory=dir_path,
            **config
        )

    def get_static_handler(self, url_path: str) -> SecureStaticFiles | None:
        """
        Get static file handler for URL path.

        Args:
            url_path: URL path prefix

        Returns:
            SecureStaticFiles handler or None if not found
        """
        return self._static_handlers.get(url_path)

    def list_static_directories(self) -> dict[str, dict[str, Any]]:
        """
        List all configured static directories.

        Returns:
            Dictionary of URL paths and their configurations
        """
        return self._static_configs.copy()

    def remove_static_directory(self, url_path: str) -> bool:
        """
        Remove a static directory configuration.

        Args:
            url_path: URL path prefix to remove

        Returns:
            True if removed, False if not found
        """
        if url_path in self._static_configs:
            del self._static_configs[url_path]
            del self._static_handlers[url_path]
            return True
        return False

    def clear_static_directories(self) -> None:
        """Clear all static directory configurations."""
        self._static_configs.clear()
        self._static_handlers.clear()


def create_static_manager_from_config(config: dict[str, Any]) -> StaticFileManager | None:
    """
    Create static file manager from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured StaticFileManager instance, or None if no static config
    """
    # Get static file configuration
    static_config = config.get("static", {})
    
    # If no static configuration, return None
    if not static_config:
        return None
    
    manager = StaticFileManager()
    
    # Handle single directory configuration
    if "directory" in static_config:
        url_path = static_config.get("url_path", "/static")
        directory = static_config["directory"]
        
        # Extract handler options
        handler_config = {
            key: value for key, value in static_config.items()
            if key not in ("directory", "url_path")
        }
        
        manager.add_static_directory(url_path, directory, **handler_config)
    
    # Handle multiple directory configuration
    if "directories" in static_config:
        for dir_config in static_config["directories"]:
            url_path = dir_config["url_path"]
            directory = dir_config["directory"]
            
            # Extract handler options
            handler_config = {
                key: value for key, value in dir_config.items()
                if key not in ("directory", "url_path")
            }
            
            manager.add_static_directory(url_path, directory, **handler_config)
    
    # If no directories were configured, return None
    if not manager.list_static_directories():
        return None
    
    return manager


# Common static file configurations
COMMON_STATIC_EXTENSIONS = {
    # Web assets
    ".css", ".js", ".map",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Documents
    ".pdf", ".txt", ".md",
    # Data
    ".json", ".xml", ".csv",
    # Media
    ".mp3", ".mp4", ".webm", ".ogg",
}

SECURE_STATIC_EXTENSIONS = {
    # Only web assets and images
    ".css", ".js", ".map",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

WEB_ASSET_EXTENSIONS = {
    # Only CSS and JS
    ".css", ".js", ".map"
}


def get_static_config_defaults(security_level: str = "default") -> dict[str, Any]:
    """
    Get default static file configuration based on security level.

    Args:
        security_level: Security level (secure, default, permissive)

    Returns:
        Default configuration dictionary
    """
    base_config = {
        "check_dir": True,
        "follow_symlink": False,
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "cache_control": "public, max-age=3600",
    }
    
    if security_level == "secure":
        return {
            **base_config,
            "allowed_extensions": SECURE_STATIC_EXTENSIONS,
            "max_file_size": 5 * 1024 * 1024,  # 5MB
            "cache_control": "public, max-age=1800",  # 30 minutes
        }
    elif security_level == "permissive":
        return {
            **base_config,
            "allowed_extensions": None,  # Allow all
            "max_file_size": 50 * 1024 * 1024,  # 50MB
            "cache_control": "public, max-age=7200",  # 2 hours
        }
    else:  # default
        return {
            **base_config,
            "allowed_extensions": COMMON_STATIC_EXTENSIONS,
        }