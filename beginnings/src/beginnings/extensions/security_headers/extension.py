"""
Security headers extension for Beginnings framework.

This module provides comprehensive security headers including CSP, CORS,
and standard security headers with route-specific customization.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from beginnings.extensions.base import BaseExtension
from beginnings.extensions.security_headers.csp import CSPManager
from beginnings.extensions.security_headers.cors import CORSManager


class SecurityHeadersExtension(BaseExtension):
    """
    Security headers extension.
    
    Provides comprehensive security headers including Content Security Policy,
    CORS handling, and standard security headers with route-specific customization.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize security headers extension.
        
        Args:
            config: Security headers configuration dictionary
        """
        super().__init__(config)
        
        # Basic security headers configuration with secure defaults
        self.headers_config = {
            "x_frame_options": "DENY",
            "x_content_type_options": "nosniff",
            "x_xss_protection": "0",  # Deprecated, disabled by default
            "strict_transport_security": {
                "max_age": 31536000,  # 1 year
                "include_subdomains": True,
                "preload": False
            },
            "referrer_policy": "strict-origin-when-cross-origin",
            "permissions_policy": {},
            "cross_origin_embedder_policy": None,
            "cross_origin_opener_policy": None,
            "cross_origin_resource_policy": None
        }
        
        # Update with user configuration
        user_headers = config.get("headers", {})
        self.headers_config.update(user_headers)
        
        # Initialize CSP manager
        csp_config = config.get("csp", {"enabled": False})
        self.csp_manager = CSPManager(csp_config)
        
        # Initialize CORS manager
        cors_config = config.get("cors", {"enabled": False})
        self.cors_manager = CORSManager(cors_config)
        
        # Route-specific configuration
        self.routes_config = config.get("routes", {})
    
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for security headers.
        
        Returns:
            Middleware factory function
        """
        def create_middleware(route_config: dict[str, Any]) -> Callable[..., Any]:
            async def security_headers_middleware(
                request: Request, 
                call_next: Callable[..., Any]
            ) -> Any:
                # Extract security configuration for this route
                security_config = route_config.get("security", {})
                
                # Handle CORS preflight requests first
                if self.cors_manager.enabled:
                    cors_route_config = security_config.get("cors", {})
                    
                    # Check if CORS is disabled for this route
                    if cors_route_config.get("enabled", True):
                        if self.cors_manager.is_cors_request(request):
                            origin = request.headers.get("origin", "")
                            
                            # Validate origin
                            if not self.cors_manager.is_origin_allowed(origin):
                                return JSONResponse(
                                    status_code=403,
                                    content={"error": "CORS request from unauthorized origin"}
                                )
                            
                            # Handle preflight request
                            if self.cors_manager.is_preflight_request(request):
                                requested_method = request.headers.get("access-control-request-method", "")
                                requested_headers_str = request.headers.get("access-control-request-headers", "")
                                requested_headers = [h.strip() for h in requested_headers_str.split(",")] if requested_headers_str else []
                                
                                return self.cors_manager.create_preflight_response(
                                    origin, requested_method, requested_headers
                                )
                
                # Continue to route handler
                response = await call_next(request)
                
                # Add security headers to response
                await self._add_security_headers(request, response, security_config)
                
                return response
            
            return security_headers_middleware
        
        return create_middleware
    
    def should_apply_to_route(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> bool:
        """
        Determine if security headers should apply to a route.
        
        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Returns:
            True if security headers should apply (applies to all routes by default)
        """
        # Check if security headers are explicitly disabled for this route
        security_config = route_config.get("security", {})
        headers_config = security_config.get("headers", {})
        
        if headers_config.get("enabled", True) is False:
            return False
        
        # Security headers apply to all routes by default
        return True
    
    async def _add_security_headers(
        self,
        request: Request,
        response: Response,
        security_config: dict[str, Any]
    ) -> None:
        """
        Add security headers to response based on configuration.
        
        Args:
            request: The request object
            response: The response object to add headers to
            security_config: Security configuration for this route
        """
        # Get route-specific headers configuration
        headers_config = security_config.get("headers", {})
        
        # Merge global and route-specific headers
        final_headers = self.headers_config.copy()
        final_headers.update(headers_config)
        
        # Add basic security headers
        await self._add_basic_headers(response, final_headers)
        
        # Add CSP headers
        await self._add_csp_headers(request, response, security_config)
        
        # Add CORS headers for simple requests
        await self._add_cors_headers(request, response, security_config)
    
    async def _add_basic_headers(
        self,
        response: Response,
        headers_config: dict[str, Any]
    ) -> None:
        """Add basic security headers to response."""
        
        # X-Frame-Options
        x_frame_options = headers_config.get("x_frame_options")
        if x_frame_options is not None:
            response.headers["X-Frame-Options"] = x_frame_options
        
        # X-Content-Type-Options
        x_content_type_options = headers_config.get("x_content_type_options")
        if x_content_type_options is not None:
            response.headers["X-Content-Type-Options"] = x_content_type_options
        
        # X-XSS-Protection (deprecated but sometimes required)
        x_xss_protection = headers_config.get("x_xss_protection")
        if x_xss_protection is not None:
            response.headers["X-XSS-Protection"] = x_xss_protection
        
        # Strict-Transport-Security
        hsts_config = headers_config.get("strict_transport_security")
        if hsts_config is not None:
            hsts_value = f"max-age={hsts_config['max_age']}"
            if hsts_config.get("include_subdomains"):
                hsts_value += "; includeSubDomains"
            if hsts_config.get("preload"):
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # Referrer-Policy
        referrer_policy = headers_config.get("referrer_policy")
        if referrer_policy is not None:
            response.headers["Referrer-Policy"] = referrer_policy
        
        # Permissions-Policy
        permissions_policy = headers_config.get("permissions_policy")
        if permissions_policy:
            policy_parts = []
            for directive, origins in permissions_policy.items():
                if not origins:  # Empty list means no origins allowed
                    policy_parts.append(f"{directive.replace('_', '-')}=()")
                elif origins == ["self"]:
                    policy_parts.append(f"{directive.replace('_', '-')}=(self)")
                else:
                    origins_str = " ".join(f'"{origin}"' if origin != "self" else origin for origin in origins)
                    policy_parts.append(f"{directive.replace('_', '-')}=({origins_str})")
            
            if policy_parts:
                response.headers["Permissions-Policy"] = ", ".join(policy_parts)
        
        # Cross-Origin-* headers
        coep = headers_config.get("cross_origin_embedder_policy")
        if coep is not None:
            response.headers["Cross-Origin-Embedder-Policy"] = coep
        
        coop = headers_config.get("cross_origin_opener_policy")
        if coop is not None:
            response.headers["Cross-Origin-Opener-Policy"] = coop
        
        corp = headers_config.get("cross_origin_resource_policy")
        if corp is not None:
            response.headers["Cross-Origin-Resource-Policy"] = corp
    
    async def _add_csp_headers(
        self,
        request: Request,
        response: Response,
        security_config: dict[str, Any]
    ) -> None:
        """Add Content Security Policy headers to response."""
        if not self.csp_manager.enabled:
            return
        
        # Check if CSP is disabled for this route
        csp_route_config = security_config.get("csp", {})
        if csp_route_config.get("enabled", True) is False:
            return
        
        # Generate nonces if enabled
        script_nonce = None
        style_nonce = None
        
        if self.csp_manager.nonce_enabled:
            if self.csp_manager.script_nonce:
                script_nonce = self.csp_manager.generate_nonce()
                # Store nonce in request state for template access
                if hasattr(request, "state"):
                    request.state.csp_script_nonce = script_nonce
            
            if self.csp_manager.style_nonce:
                style_nonce = self.csp_manager.generate_nonce()
                # Store nonce in request state for template access
                if hasattr(request, "state"):
                    request.state.csp_style_nonce = style_nonce
        
        # Get route-specific CSP directives
        route_directives = csp_route_config.get("directives")
        
        # Build and add CSP header
        header_name, header_value = self.csp_manager.build_csp_header_with_name(
            script_nonce, style_nonce, route_directives
        )
        
        if header_value:
            response.headers[header_name] = header_value
    
    async def _add_cors_headers(
        self,
        request: Request,
        response: Response,
        security_config: dict[str, Any]
    ) -> None:
        """Add CORS headers for simple requests."""
        if not self.cors_manager.enabled:
            return
        
        # Check if CORS is disabled for this route
        cors_route_config = security_config.get("cors", {})
        if cors_route_config.get("enabled", True) is False:
            return
        
        # Only add CORS headers for actual CORS requests (not preflight)
        if self.cors_manager.is_cors_request(request) and not self.cors_manager.is_preflight_request(request):
            origin = request.headers.get("origin", "")
            
            if self.cors_manager.is_origin_allowed(origin):
                self.cors_manager.add_cors_headers_to_response(response, origin)
    
    def validate_config(self) -> list[str]:
        """
        Validate security headers extension configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate basic headers
        x_frame_options = self.headers_config.get("x_frame_options")
        if x_frame_options and x_frame_options not in ["DENY", "SAMEORIGIN"]:
            if not x_frame_options.startswith("ALLOW-FROM "):
                errors.append("x_frame_options must be DENY, SAMEORIGIN, or ALLOW-FROM uri")
        
        # Validate HSTS configuration
        hsts_config = self.headers_config.get("strict_transport_security")
        if hsts_config and isinstance(hsts_config, dict):
            max_age = hsts_config.get("max_age", 0)
            if max_age < 0:
                errors.append("HSTS max_age must be non-negative")
        
        # Validate CSP configuration
        csp_errors = self.csp_manager.validate_config()
        errors.extend(csp_errors)
        
        # Validate CORS configuration
        cors_errors = self.cors_manager.validate_config()
        errors.extend(cors_errors)
        
        return errors