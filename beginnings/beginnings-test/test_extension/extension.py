"""TestExtension middleware extension."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from beginnings.extensions.base import BaseExtension


class TestExtensionExtension(BaseExtension):
    """TestExtension middleware extension.
    
    This extension provides test_extension functionality through middleware
    that processes requests and responses.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize test_extension extension.
        
        Args:
            config: Extension configuration
        """
        super().__init__(config)
        self.enabled = config.get("enabled", True)
        
        # Add your configuration options here
        self.option1 = config.get("option1", "default_value")
        self.option2 = config.get("option2", False)
    
    def validate_config(self) -> List[str]:
        """Validate extension configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Add your validation logic here
        if not isinstance(self.enabled, bool):
            errors.append("enabled must be a boolean")
        
        if not isinstance(self.option2, bool):
            errors.append("option2 must be a boolean")
        
        return errors
    
    def should_apply_to_route(
        self, 
        path: str, 
        methods: List[str], 
        route_config: Dict[str, Any]
    ) -> bool:
        """Determine if this extension should apply to the given route.
        
        Args:
            path: Route path
            methods: HTTP methods for the route
            route_config: Route-specific configuration
            
        Returns:
            True if extension should apply to this route
        """
        if not self.enabled:
            return False
        
        # Add your route matching logic here
        # Example: Skip for health check endpoints
        if path.startswith("/health"):
            return False
        
        # Check route-specific configuration
        route_enabled = route_config.get("test_extension", {}).get("enabled", True)
        return route_enabled
    
    def get_middleware_factory(self) -> Callable[[Dict[str, Any]], BaseHTTPMiddleware]:
        """Get middleware factory for this extension.
        
        Returns:
            Factory function that creates middleware instances
        """
        def create_middleware(route_config: Dict[str, Any]) -> BaseHTTPMiddleware:
            return TestExtensionMiddleware(
                extension_config=self.config,
                route_config=route_config
            )
        
        return create_middleware


class TestExtensionMiddleware(BaseHTTPMiddleware):
    """TestExtension middleware implementation."""
    
    def __init__(
        self, 
        app,
        extension_config: Dict[str, Any],
        route_config: Dict[str, Any]
    ):
        """Initialize middleware.
        
        Args:
            app: ASGI application
            extension_config: Extension-level configuration
            route_config: Route-specific configuration
        """
        super().__init__(app)
        self.extension_config = extension_config
        self.route_config = route_config
        
        # Extract configuration options
        self.option1 = extension_config.get("option1", "default_value")
        self.option2 = extension_config.get("option2", False)
        
        # Route-specific overrides
        route_test_extension_config = route_config.get("test_extension", {})
        self.route_option1 = route_test_extension_config.get("option1", self.option1)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response object
        """
        # Pre-process request
        await self._before_request(request)
        
        try:
            # Call next middleware/endpoint
            response = await call_next(request)
            
            # Post-process response
            await self._after_request(request, response)
            
            return response
            
        except Exception as exc:
            # Handle errors
            await self._on_error(request, exc)
            raise
    
    async def _before_request(self, request: Request) -> None:
        """Process request before calling next middleware.
        
        Args:
            request: Incoming request
        """
        # Add your request processing logic here
        # Example: Add headers, validate request, etc.
        pass
    
    async def _after_request(self, request: Request, response: Response) -> None:
        """Process response after calling next middleware.
        
        Args:
            request: Original request
            response: Response from downstream
        """
        # Add your response processing logic here
        # Example: Add headers, log response, etc.
        pass
    
    async def _on_error(self, request: Request, exc: Exception) -> None:
        """Handle errors during request processing.
        
        Args:
            request: Original request
            exc: Exception that occurred
        """
        # Add your error handling logic here
        # Example: Log errors, send notifications, etc.
        pass