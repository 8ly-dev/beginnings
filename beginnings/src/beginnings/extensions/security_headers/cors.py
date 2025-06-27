"""
Cross-Origin Resource Sharing (CORS) management for security headers extension.

This module provides CORS request handling, preflight responses,
and origin validation capabilities.
"""

import fnmatch
from typing import Any

from fastapi import Request, Response


class CORSManager:
    """
    CORS manager for handling cross-origin requests.
    
    Provides origin validation, preflight request handling,
    and CORS header management.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CORS manager.
        
        Args:
            config: CORS configuration dictionary
        """
        self.enabled = config.get("enabled", False)
        
        if not self.enabled:
            return
        
        self.allow_origins = config.get("allow_origins", ["*"])
        self.allow_methods = config.get(
            "allow_methods", 
            ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        )
        self.allow_headers = config.get(
            "allow_headers", 
            ["Content-Type", "Authorization", "X-Requested-With"]
        )
        self.expose_headers = config.get("expose_headers", [])
        self.allow_credentials = config.get("allow_credentials", False)
        self.max_age = config.get("max_age", 86400)  # 24 hours
    
    def is_cors_request(self, request: Request) -> bool:
        """
        Determine if request is a CORS request.
        
        Args:
            request: The request object
            
        Returns:
            True if request has Origin header
        """
        return "origin" in request.headers
    
    def is_preflight_request(self, request: Request) -> bool:
        """
        Determine if request is a CORS preflight request.
        
        Args:
            request: The request object
            
        Returns:
            True if request is OPTIONS with CORS preflight headers
        """
        return (
            request.method == "OPTIONS" and
            "origin" in request.headers and
            "access-control-request-method" in request.headers
        )
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed by CORS policy.
        
        Args:
            origin: Origin to validate
            
        Returns:
            True if origin is allowed
        """
        if "*" in self.allow_origins:
            return True
        
        for allowed_origin in self.allow_origins:
            # Support wildcard patterns like https://*.example.com
            if fnmatch.fnmatch(origin, allowed_origin):
                return True
            
            # Exact match
            if origin == allowed_origin:
                return True
        
        return False
    
    def create_preflight_response(
        self,
        origin: str,
        requested_method: str,
        requested_headers: list[str] | None = None
    ) -> Response:
        """
        Create preflight response for CORS request.
        
        Args:
            origin: Request origin
            requested_method: Requested method from access-control-request-method
            requested_headers: Requested headers from access-control-request-headers
            
        Returns:
            Preflight response with appropriate CORS headers
        """
        response = Response(status_code=200)
        
        # Add basic CORS headers
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        
        # Handle allowed headers
        allowed_headers = self.allow_headers.copy()
        if requested_headers:
            # Add requested headers that are in our allow list
            for header in requested_headers:
                if header.lower() not in [h.lower() for h in allowed_headers]:
                    # Only add if it's a simple header or explicitly allowed
                    if self._is_simple_header(header):
                        allowed_headers.append(header)
        
        response.headers["Access-Control-Allow-Headers"] = ", ".join(allowed_headers)
        
        # Add max age for preflight caching
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        # Add credentials header if enabled
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    def add_cors_headers_to_response(self, response: Response, origin: str) -> None:
        """
        Add CORS headers to response for simple requests.
        
        Args:
            response: Response to add headers to
            origin: Request origin
        """
        response.headers["Access-Control-Allow-Origin"] = origin
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
    
    def _is_simple_header(self, header: str) -> bool:
        """
        Check if header is a CORS simple header.
        
        Args:
            header: Header name to check
            
        Returns:
            True if header is a simple header
        """
        simple_headers = {
            "accept",
            "accept-language",
            "content-language",
            "content-type"
        }
        return header.lower() in simple_headers
    
    def validate_config(self) -> list[str]:
        """
        Validate CORS configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.enabled:
            return errors
        
        # Validate max_age
        if self.max_age < 0:
            errors.append("CORS max_age must be non-negative")
        
        # Validate methods
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        for method in self.allow_methods:
            if method.upper() not in valid_methods:
                errors.append(f"Invalid CORS method: {method}")
        
        # Validate origins format
        for origin in self.allow_origins:
            if origin != "*" and not self._is_valid_origin_pattern(origin):
                errors.append(f"Invalid CORS origin pattern: {origin}")
        
        return errors
    
    def _is_valid_origin_pattern(self, origin: str) -> bool:
        """
        Validate origin pattern format.
        
        Args:
            origin: Origin pattern to validate
            
        Returns:
            True if origin pattern is valid
        """
        # Basic validation - should start with http:// or https://
        # or be a wildcard pattern
        if origin.startswith(("http://", "https://")):
            return True
        
        # Allow wildcard patterns like https://*.example.com
        if "*" in origin and origin.startswith(("http://", "https://")):
            return True
        
        return False