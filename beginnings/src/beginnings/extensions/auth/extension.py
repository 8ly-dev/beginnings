"""
Authentication extension for Beginnings framework.

This module provides the main authentication extension that integrates
JWT, session-based authentication, OAuth, and RBAC into the framework.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from beginnings.extensions.auth.providers.base import (
    AuthenticationError,
    BaseAuthProvider,
    User,
)
from beginnings.extensions.auth.providers.jwt_provider import JWTProvider
from beginnings.extensions.auth.providers.session_provider import SessionProvider
from beginnings.extensions.auth.providers.oauth_provider import OAuthProvider
from beginnings.extensions.auth.rbac import RBACManager
from beginnings.extensions.base import BaseExtension


class AuthExtension(BaseExtension):
    """
    Authentication extension providing JWT, session, and RBAC authentication.
    
    This extension integrates multiple authentication providers with role-based
    access control and provides middleware for protecting routes.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize authentication extension.
        
        Args:
            config: Authentication configuration dictionary
        """
        super().__init__(config)
        
        # Initialize RBAC manager
        rbac_config = config.get("rbac", {})
        self.rbac_manager = RBACManager(rbac_config)
        
        # Initialize authentication providers
        self.providers: dict[str, BaseAuthProvider] = {}
        self.default_provider = config.get("provider", "jwt")
        
        # Initialize providers based on configuration
        providers_config = config.get("providers", {})
        
        if "jwt" in providers_config:
            self.providers["jwt"] = JWTProvider(providers_config["jwt"])
        
        if "session" in providers_config:
            self.providers["session"] = SessionProvider(providers_config["session"])
        
        if "oauth" in providers_config:
            self.providers["oauth"] = OAuthProvider(providers_config["oauth"])
        
        # Set user lookup function for providers if provided
        if hasattr(self, '_user_lookup_function'):
            for provider in self.providers.values():
                if hasattr(provider, 'set_user_lookup_function'):
                    provider.set_user_lookup_function(self._user_lookup_function)
        
        # Route protection configuration
        self.protected_routes_config = config.get("protected_routes", {})
        
        # Authentication pages configuration
        self.auth_routes_config = config.get("routes", {})
    
    def set_user_lookup_function(self, func: Callable[..., Any]) -> None:
        """
        Set the user lookup function for all providers.
        
        Args:
            func: Async function that takes username or user_id and returns user data
        """
        self._user_lookup_function = func
        for provider in self.providers.values():
            if hasattr(provider, 'set_user_lookup_function'):
                provider.set_user_lookup_function(func)
    
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable[..., Any]]:
        """
        Get middleware factory for authentication.
        
        Returns:
            Middleware factory function
        """
        def create_middleware(route_config: dict[str, Any]) -> Callable[..., Any]:
            async def auth_middleware(request: Request, call_next: Callable[..., Any]) -> Any:
                # Extract auth configuration for this route
                auth_config = route_config.get("auth", {})
                
                # Skip authentication if not required
                if not auth_config.get("required", False):
                    return await call_next(request)
                
                # Determine which provider to use
                provider_name = auth_config.get("provider", self.default_provider)
                provider = self.providers.get(provider_name)
                
                if not provider:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Authentication provider '{provider_name}' not configured"
                    )
                
                try:
                    # Attempt authentication
                    user = await provider.authenticate(request)
                    
                    if not user:
                        return await self._handle_authentication_required(request, auth_config)
                    
                    # Check role/permission requirements
                    access_allowed, reason = self.rbac_manager.validate_route_access(
                        user.roles, auth_config
                    )
                    
                    if not access_allowed:
                        return await self._handle_access_denied(request, auth_config, reason)
                    
                    # Inject user into request context
                    request.state.user = user
                    
                    # Continue to route handler
                    response = await call_next(request)
                    
                    # Add any auth-related headers to response
                    return await self._add_auth_headers(response, user, auth_config)
                    
                except AuthenticationError as e:
                    return await self._handle_authentication_error(request, auth_config, str(e))
                except Exception as e:
                    # Log the error in production
                    return await self._handle_authentication_error(
                        request, auth_config, "Authentication system error"
                    )
            
            return auth_middleware
        
        return create_middleware
    
    def should_apply_to_route(
        self,
        path: str,
        methods: list[str],
        route_config: dict[str, Any]
    ) -> bool:
        """
        Determine if authentication should apply to a route.
        
        Args:
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Returns:
            True if authentication should apply
        """
        # Check if auth is explicitly configured for this route
        auth_config = route_config.get("auth", {})
        if auth_config:
            return auth_config.get("required", False)
        
        # Check if route matches any protected route patterns
        for pattern, pattern_config in self.protected_routes_config.items():
            if self._path_matches_pattern(path, pattern):
                return pattern_config.get("required", False)
        
        return False
    
    async def _handle_authentication_required(
        self,
        request: Request,
        auth_config: dict[str, Any]
    ) -> Response:
        """Handle case where authentication is required but not provided."""
        # Check if this is an API request (JSON response expected)
        if self._is_api_request(request):
            error_response = auth_config.get(
                "error_unauthorized",
                {"error": "Authentication required"}
            )
            return JSONResponse(
                status_code=401,
                content=error_response
            )
        
        # For HTML requests, redirect to login page
        redirect_url = auth_config.get("redirect_unauthorized", "/login")
        
        # Add return URL parameter if configured
        if auth_config.get("add_return_url", True):
            return_url = str(request.url)
            redirect_url = f"{redirect_url}?return_url={return_url}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
    
    async def _handle_access_denied(
        self,
        request: Request,
        auth_config: dict[str, Any],
        reason: str
    ) -> Response:
        """Handle case where user is authenticated but access is denied."""
        if self._is_api_request(request):
            error_response = auth_config.get(
                "error_forbidden",
                {"error": "Access denied", "reason": reason}
            )
            return JSONResponse(
                status_code=403,
                content=error_response
            )
        
        # For HTML requests, show error page or redirect
        redirect_url = auth_config.get("redirect_forbidden")
        if redirect_url:
            return RedirectResponse(url=redirect_url, status_code=302)
        
        # Return 403 error page
        raise HTTPException(status_code=403, detail=reason)
    
    async def _handle_authentication_error(
        self,
        request: Request,
        auth_config: dict[str, Any],
        error_message: str
    ) -> Response:
        """Handle authentication errors."""
        if self._is_api_request(request):
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication failed", "message": error_message}
            )
        
        # For HTML requests, redirect to login with error
        redirect_url = auth_config.get("redirect_unauthorized", "/login")
        redirect_url = f"{redirect_url}?error=auth_failed"
        
        return RedirectResponse(url=redirect_url, status_code=302)
    
    async def _add_auth_headers(
        self,
        response: Response,
        user: User,
        auth_config: dict[str, Any]
    ) -> Response:
        """Add authentication-related headers to response."""
        # Add user info header if configured
        if auth_config.get("add_user_header", False):
            response.headers["X-User-ID"] = user.user_id
            if user.username:
                response.headers["X-Username"] = user.username
        
        return response
    
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
    
    def get_user_from_request(self, request: Request) -> User | None:
        """
        Get authenticated user from request context.
        
        Args:
            request: The request object
            
        Returns:
            User object if authenticated, None otherwise
        """
        return getattr(request.state, "user", None)
    
    async def login_user(
        self,
        request: Request,
        username: str,
        password: str,
        provider_name: str | None = None
    ) -> tuple[User, dict[str, Any]]:
        """
        Perform user login.
        
        Args:
            request: The request object
            username: Username to authenticate
            password: Password to authenticate
            provider_name: Provider to use (defaults to default provider)
            
        Returns:
            Tuple of (User object, authentication data)
            
        Raises:
            AuthenticationError: If login fails
        """
        provider = self.providers.get(provider_name or self.default_provider)
        if not provider:
            raise AuthenticationError("Authentication provider not available")
        
        return await provider.login(request, username, password)
    
    async def logout_user(
        self,
        request: Request,
        user: User | None = None
    ) -> dict[str, Any]:
        """
        Perform user logout.
        
        Args:
            request: The request object
            user: User to logout (uses request context if not provided)
            
        Returns:
            Dictionary with logout response data
        """
        if not user:
            user = self.get_user_from_request(request)
        
        if not user:
            return {"message": "No user to logout"}
        
        provider_name = user.metadata.get("provider", self.default_provider)
        provider = self.providers.get(provider_name)
        
        if not provider:
            return {"message": "Provider not available for logout"}
        
        return await provider.logout(request, user)
    
    def validate_config(self) -> list[str]:
        """
        Validate authentication extension configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate that at least one provider is configured
        if not self.providers:
            errors.append("At least one authentication provider must be configured")
        
        # Validate default provider exists
        if self.default_provider not in self.providers:
            errors.append(f"Default provider '{self.default_provider}' is not configured")
        
        # Validate each provider
        for provider_name, provider in self.providers.items():
            provider_errors = provider.validate_config()
            for error in provider_errors:
                errors.append(f"Provider '{provider_name}': {error}")
        
        # Validate RBAC configuration
        rbac_errors = self.rbac_manager.validate_config()
        for error in rbac_errors:
            errors.append(f"RBAC: {error}")
        
        return errors