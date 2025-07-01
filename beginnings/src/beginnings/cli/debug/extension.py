"""Debug extension for Beginnings framework integration."""

from __future__ import annotations

from typing import Optional, Any

from .config import DebugConfig
from .middleware import DebugMiddleware


class DebugExtension:
    """Debug extension for Beginnings framework."""
    
    def __init__(self, config: Optional[DebugConfig] = None):
        """Initialize debug extension.
        
        Args:
            config: Debug configuration
        """
        self.config = config or DebugConfig()
        self.middleware: Optional[DebugMiddleware] = None
        self.app: Optional[Any] = None
    
    def init_app(self, app: Any):
        """Initialize extension with application instance.
        
        Args:
            app: Application instance
        """
        self.app = app
        
        if not self.config.enabled:
            return
        
        # Create debug middleware
        self.middleware = DebugMiddleware(
            config=self.config,
            enable_request_tracking=self.config.enable_request_tracking,
            enable_performance_monitoring=self.config.enable_performance_monitoring,
            enable_error_tracking=self.config.enable_error_tracking,
            max_request_history=self.config.max_request_history
        )
        
        # Register middleware with app (framework-specific)
        if hasattr(app, 'add_middleware'):
            app.add_middleware(self._create_middleware_wrapper())
        
        # Register debug routes if app supports it
        if hasattr(app, 'add_route'):
            self._register_debug_routes(app)
    
    def _create_middleware_wrapper(self):
        """Create middleware wrapper for framework integration.
        
        Returns:
            Middleware wrapper function
        """
        def debug_middleware_wrapper(request, call_next):
            """Middleware wrapper function."""
            if not self.middleware:
                return call_next(request)
            
            # Start request tracking
            request_id = self.middleware.before_request(request)
            
            try:
                # Process request
                response = call_next(request)
                
                # End request tracking
                self.middleware.after_request(request, response)
                
                return response
                
            except Exception as error:
                # Handle errors
                self.middleware.on_error(request, error)
                raise
        
        return debug_middleware_wrapper
    
    def _register_debug_routes(self, app: Any):
        """Register debug-specific routes with the application.
        
        Args:
            app: Application instance
        """
        # Debug info endpoint
        def debug_info():
            """Get debug information."""
            if not self.middleware:
                return {"error": "Debug middleware not available"}
            
            return self.middleware.get_debug_info()
        
        # Debug metrics endpoint
        def debug_metrics():
            """Get debug metrics."""
            if not self.middleware:
                return {"error": "Debug middleware not available"}
            
            return self.middleware.metrics_collector.get_metrics()
        
        # Debug requests endpoint
        def debug_requests():
            """Get debug request data."""
            if not self.middleware:
                return {"error": "Debug middleware not available"}
            
            return {
                "requests": self.middleware.get_tracked_requests(50),
                "statistics": self.middleware.request_tracker.get_statistics()
            }
        
        # Register routes (framework-specific implementation needed)
        if hasattr(app, 'add_route'):
            app.add_route("/_debug/info", debug_info, methods=["GET"])
            app.add_route("/_debug/metrics", debug_metrics, methods=["GET"])
            app.add_route("/_debug/requests", debug_requests, methods=["GET"])
    
    def get_debug_info(self) -> dict:
        """Get comprehensive debug information.
        
        Returns:
            Dictionary containing debug information
        """
        if not self.middleware:
            return {"error": "Debug middleware not initialized"}
        
        return self.middleware.get_debug_info()
    
    def clear_debug_data(self, data_type: str = "all"):
        """Clear debug data.
        
        Args:
            data_type: Type of data to clear
        """
        if self.middleware:
            self.middleware.clear_data(data_type)
    
    def is_enabled(self) -> bool:
        """Check if debug extension is enabled.
        
        Returns:
            True if debug extension is enabled
        """
        return self.config.enabled