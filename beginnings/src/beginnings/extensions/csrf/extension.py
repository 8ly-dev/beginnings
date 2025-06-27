"""
CSRF protection extension for Beginnings framework.

This module provides the main CSRF extension that integrates token generation,
validation, template functions, and AJAX support into the framework.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from beginnings.extensions.base import BaseExtension
from beginnings.extensions.csrf.tokens import CSRFTokenError, CSRFTokenManager
from beginnings.extensions.csrf.template_hooks import CSRFTemplateHooks


class CSRFExtension(BaseExtension):
    """
    CSRF protection extension.
    
    Provides Cross-Site Request Forgery protection with token generation,
    validation, template integration, and AJAX support.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CSRF extension.
        
        Args:
            config: CSRF configuration dictionary
        """
        super().__init__(config)
        
        # Initialize token manager
        self.token_manager = CSRFTokenManager(config)
        
        # CSRF protection settings
        self.enabled = config.get("enabled", True)
        self.protected_methods = config.get("protected_methods", ["POST", "PUT", "PATCH", "DELETE"])
        self.protected_routes_config = config.get("protected_routes", {})
        
        # Template integration settings
        template_config = config.get("template_integration", {})
        self.template_integration_enabled = template_config.get("enabled", True)
        self.template_function_name = template_config.get("template_function_name", "csrf_token")
        self.form_field_name = template_config.get("form_field_name", "csrf_token")
        self.meta_tag_name = template_config.get("meta_tag_name", "csrf-token")
        
        # AJAX support settings
        ajax_config = config.get("ajax", {})
        self.ajax_header_name = ajax_config.get("header_name", "X-CSRFToken")
        self.ajax_cookie_name = ajax_config.get("cookie_name", "csrftoken")
        self.ajax_js_function = ajax_config.get("javascript_function", "getCSRFToken")
        
        # Error handling settings
        error_config = config.get("error_handling", {})
        self.error_template = error_config.get("template", "errors/csrf_error.html")
        self.error_json_response = error_config.get(
            "json_response",
            {"error": "CSRF token validation failed"}
        )
        self.error_status_code = error_config.get("status_code", 403)
        
        # Configuration cache for performance
        self._route_config_cache: dict[str, dict[str, Any]] = {}
        
        # Template integration hooks
        self.template_hooks = CSRFTemplateHooks(self)
    
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for CSRF protection.
        
        Returns:
            Middleware factory function
        """
        def create_middleware(route_config: dict[str, Any]) -> Callable[..., Any]:
            # Cache the parsed configuration for this route
            route_path = route_config.get("path", "unknown")
            cached_config = self._get_cached_route_config(route_path, route_config)
            
            async def csrf_middleware(request: Request, call_next: Callable[..., Any]) -> Any:
                # Skip if CSRF protection is disabled
                if not self.enabled:
                    return await call_next(request)
                
                # Use cached configuration
                csrf_config = cached_config
                
                # Skip if explicitly disabled for this route
                if csrf_config.get("enabled", True) is False:
                    return await call_next(request)
                
                # Check if request method requires CSRF protection
                if request.method not in self.protected_methods:
                    response = await call_next(request)
                    return await self._add_csrf_headers_to_response(request, response, csrf_config)
                
                try:
                    # Validate CSRF token
                    await self._validate_csrf_token(request, csrf_config)
                    
                    # Continue to route handler
                    response = await call_next(request)
                    
                    # Add CSRF headers to response
                    return await self._add_csrf_headers_to_response(request, response, csrf_config)
                    
                except CSRFTokenError as e:
                    return await self._handle_csrf_error(request, csrf_config, str(e))
                except Exception as e:
                    # Log the error in production
                    return await self._handle_csrf_error(
                        request, csrf_config, "CSRF validation error"
                    )
            
            return csrf_middleware
        
        return create_middleware
    
    def should_apply_to_route(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> bool:
        """
        Determine if CSRF protection should apply to a route.
        
        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Returns:
            True if CSRF protection should apply
        """
        # Skip if CSRF is disabled globally
        if not self.enabled:
            return False
        
        # Check if route has explicit CSRF configuration
        csrf_config = route_config.get("csrf", {})
        if csrf_config:
            return csrf_config.get("enabled", True)
        
        # Check if route matches any protected route patterns
        for pattern, pattern_config in self.protected_routes_config.items():
            if self._path_matches_pattern(path, pattern):
                return pattern_config.get("enabled", True)
        
        # Apply to routes with protected methods by default
        return any(method in self.protected_methods for method in methods)
    
    async def _validate_csrf_token(self, request: Request, csrf_config: dict[str, Any]) -> None:
        """Validate CSRF token from request."""
        # Try to get token from form data first
        token = None
        
        # Check form data for POST requests
        if request.method in self.protected_methods:
            try:
                form_data = await request.form()
                token = form_data.get(self.form_field_name)
            except Exception:
                # Form data not available or already consumed
                pass
        
        # Check headers (for AJAX requests)
        if not token:
            token = request.headers.get(self.ajax_header_name)
        
        # Check custom header name if configured
        custom_header = csrf_config.get("header_name")
        if not token and custom_header:
            token = request.headers.get(custom_header)
        
        if not token:
            raise CSRFTokenError("CSRF token not found in request")
        
        # Get session information if available
        session_id = None
        session_token = None
        
        # Try to get session from request context (if auth extension is enabled)
        if hasattr(request.state, "user") and request.state.user and hasattr(request.state.user, "metadata"):
            if isinstance(request.state.user.metadata, dict):
                session_id = request.state.user.metadata.get("session_id")
        
        # For double-submit cookie pattern
        if self.token_manager.double_submit_cookie:
            cookie_value = request.cookies.get(self.ajax_cookie_name)
            if cookie_value:
                if not self.token_manager.validate_double_submit_cookie(token, cookie_value):
                    raise CSRFTokenError("CSRF cookie validation failed")
        
        # Validate the token
        self.token_manager.validate_token(token, session_token, session_id)
    
    async def _add_csrf_headers_to_response(
        self,
        request: Request,
        response: Response,
        csrf_config: dict[str, Any]
    ) -> Response:
        """Add CSRF-related headers and meta tags to response."""
        # Generate token for response
        session_id = None
        if hasattr(request.state, "user") and request.state.user and hasattr(request.state.user, "metadata"):
            if isinstance(request.state.user.metadata, dict):
                session_id = request.state.user.metadata.get("session_id")
        
        token = self.token_manager.get_token_for_template(session_id)
        
        # Add CSRF token header
        response.headers["X-CSRF-Token"] = token
        
        # Set double-submit cookie if enabled
        if self.token_manager.double_submit_cookie:
            cookie_value = self.token_manager.create_double_submit_cookie_value(token)
            response.set_cookie(
                key=self.ajax_cookie_name,
                value=cookie_value,
                httponly=False,  # JavaScript needs access
                secure=request.url.scheme == "https",
                samesite="strict"
            )
        
        # Inject meta tag for HTML responses using proper template engine integration
        if isinstance(response, HTMLResponse) and self.template_integration_enabled:
            content = response.body.decode() if response.body else ""
            if "</head>" in content and content.strip():
                from html import escape
                meta_tag = f'<meta name="{escape(self.meta_tag_name)}" content="{escape(token)}">'
                
                # Use more robust HTML injection
                if "<!-- CSRF_META_TAG -->" in content:
                    # Replace placeholder if it exists
                    content = content.replace("<!-- CSRF_META_TAG -->", meta_tag)
                elif "</head>" in content:
                    # Fallback to head injection
                    content = content.replace("</head>", f"    {meta_tag}\n</head>")
                
                response.body = content.encode()
                
                # Update content length header if present
                if "content-length" in response.headers:
                    response.headers["content-length"] = str(len(response.body))
        
        return response
    
    async def _handle_csrf_error(
        self,
        request: Request,
        csrf_config: dict[str, Any],
        error_message: str
    ) -> Response:
        """Handle CSRF validation errors."""
        # Check if this is an API request
        if self._is_api_request(request):
            error_response = csrf_config.get("error_json", self.error_json_response)
            if isinstance(error_response, dict):
                error_response = error_response.copy()
                error_response["message"] = error_message
            
            return JSONResponse(
                status_code=self.error_status_code,
                content=error_response
            )
        
        # For HTML requests, return error page or raise HTTP exception
        custom_error_message = csrf_config.get("custom_error", error_message)
        raise HTTPException(
            status_code=self.error_status_code,
            detail=custom_error_message
        )
    
    def _is_api_request(self, request: Request) -> bool:
        """Determine if request expects JSON response."""
        # Check Accept header
        accept_header = request.headers.get("accept", "").lower()
        if "application/json" in accept_header:
            return True
        
        # Check if path starts with /api
        if request.url.path.startswith("/api"):
            return True
        
        # Check Content-Type for non-GET requests
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            return True
        
        return False
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern (simple wildcard matching)."""
        if pattern == path:
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)
        
        return False
    
    def _get_cached_route_config(self, route_path: str, route_config: dict[str, Any]) -> dict[str, Any]:
        """Get or create cached route configuration for performance."""
        if route_path not in self._route_config_cache:
            # Extract CSRF configuration for this route
            base_csrf_config = route_config.get("csrf", {})
            
            # Apply route pattern-based configuration
            for pattern, pattern_config in self.protected_routes_config.items():
                if self._path_matches_pattern(route_path, pattern):
                    # Merge pattern config as defaults, route config as overrides
                    merged_config = {**pattern_config, **base_csrf_config}
                    self._route_config_cache[route_path] = merged_config
                    return merged_config
            
            # No pattern match, use base config with defaults
            merged_config = {
                "enabled": base_csrf_config.get("enabled", True),
                **base_csrf_config  # Include any additional config
            }
            self._route_config_cache[route_path] = merged_config
        
        return self._route_config_cache[route_path]
    
    def get_csrf_token_for_template(self, request: Request) -> str:
        """
        Get CSRF token for template rendering.
        
        Args:
            request: The request object
            
        Returns:
            CSRF token for templates
        """
        session_id = None
        if hasattr(request.state, "user") and request.state.user and hasattr(request.state.user, "metadata"):
            if isinstance(request.state.user.metadata, dict):
                session_id = request.state.user.metadata.get("session_id")
        
        return self.token_manager.get_token_for_template(session_id)
    
    def create_csrf_form_field(self, request: Request) -> str:
        """
        Create HTML form field for CSRF token.
        
        Args:
            request: The request object
            
        Returns:
            HTML input field for CSRF token
        """
        token = self.get_csrf_token_for_template(request)
        return f'<input type="hidden" name="{self.form_field_name}" value="{token}">'
    
    def create_csrf_meta_tag(self, request: Request) -> str:
        """
        Create HTML meta tag for CSRF token.
        
        Args:
            request: The request object
            
        Returns:
            HTML meta tag for CSRF token
        """
        token = self.get_csrf_token_for_template(request)
        return f'<meta name="{self.meta_tag_name}" content="{token}">'
    
    def get_template_functions(self) -> dict[str, Callable[..., Any]]:
        """
        Get template functions for CSRF integration.
        
        Returns:
            Dictionary of template functions
        """
        def csrf_token_func(request: Request) -> str:
            return self.get_csrf_token_for_template(request)
        
        def csrf_form_field_func(request: Request) -> str:
            return self.create_csrf_form_field(request)
        
        def csrf_meta_tag_func(request: Request) -> str:
            return self.create_csrf_meta_tag(request)
        
        return {
            self.template_function_name: csrf_token_func,
            "csrf_form_field": csrf_form_field_func,
            "csrf_meta_tag": csrf_meta_tag_func
        }
    
    def validate_config(self) -> list[str]:
        """
        Validate CSRF extension configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate token manager configuration
        token_errors = self.token_manager.validate_config()
        errors.extend(token_errors)
        
        # Validate protected methods
        if not self.protected_methods:
            errors.append("CSRF protected_methods cannot be empty")
        
        # Validate status code
        if not (400 <= self.error_status_code < 600):
            errors.append("CSRF error_status_code must be a valid HTTP status code")
        
        return errors