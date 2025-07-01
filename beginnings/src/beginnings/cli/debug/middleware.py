"""Debug middleware for request tracking and performance monitoring."""

from __future__ import annotations

import time
import traceback
from typing import Dict, Any, List, Optional, Callable
from threading import RLock

from .metrics import MetricsCollector
from .requests import RequestTracker
from .profiler import PerformanceProfiler
from .config import DebugConfig


class DebugMiddleware:
    """Middleware for debugging and performance monitoring."""
    
    def __init__(
        self,
        config: Optional[DebugConfig] = None,
        enable_request_tracking: bool = True,
        enable_performance_monitoring: bool = True,
        enable_error_tracking: bool = True,
        max_request_history: int = 1000
    ):
        """Initialize debug middleware.
        
        Args:
            config: Debug configuration
            enable_request_tracking: Enable request tracking
            enable_performance_monitoring: Enable performance monitoring
            enable_error_tracking: Enable error tracking
            max_request_history: Maximum requests to keep in history
        """
        self.config = config or DebugConfig()
        self.enable_request_tracking = enable_request_tracking
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_error_tracking = enable_error_tracking
        self.max_request_history = max_request_history
        
        # Initialize components
        self.metrics_collector = MetricsCollector(
            max_requests=max_request_history,
            max_errors=500,
            max_performance=500
        )
        
        self.request_tracker = RequestTracker(
            max_requests=max_request_history,
            track_headers=self.config.track_request_headers,
            track_body=self.config.track_request_body
        )
        
        self.profiler = PerformanceProfiler(
            profile_cpu=self.config.enable_cpu_profiling,
            profile_memory=self.config.enable_memory_profiling,
            profile_threshold_ms=self.config.profile_threshold_ms
        )
        
        # Request context storage
        self._lock = RLock()
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        
        # Performance data
        self._tracked_requests: List[Dict[str, Any]] = []
        self._tracked_errors: List[Dict[str, Any]] = []
        self._performance_metrics: List[Dict[str, Any]] = []
    
    def before_request(self, request: Any) -> Optional[str]:
        """Process request before handling.
        
        Args:
            request: Request object (framework-specific)
            
        Returns:
            Request ID for tracking
        """
        if not self.config.enabled:
            return None
        
        request_id = None
        current_time = time.time()
        
        # Extract request information
        path = getattr(request, 'path', '')
        method = getattr(request, 'method', 'GET')
        headers = self._extract_headers(request)
        query_params = self._extract_query_params(request)
        body = self._extract_body(request) if self.config.track_request_body else ""
        user_agent = headers.get('user-agent', '')
        ip_address = self._extract_ip_address(request)
        
        # Start request tracking
        if self.enable_request_tracking:
            request_id = self.request_tracker.start_request(
                path=path,
                method=method,
                headers=headers,
                query_params=query_params,
                body=body,
                user_agent=user_agent,
                ip_address=ip_address
            )
        
        # Store request context
        with self._lock:
            context = {
                "request_id": request_id,
                "start_time": current_time,
                "path": path,
                "method": method,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "profiler_id": None
            }
            
            # Start performance profiling if enabled
            if self.enable_performance_monitoring and self.config.enable_profiler:
                profiler_id = self.profiler.start_profiling(
                    name=f"{method} {path}",
                    context={"request_id": request_id}
                )
                context["profiler_id"] = profiler_id
            
            # Use request object as key (assuming it's hashable)
            # In practice, this might need to be adapted based on the framework
            request_key = id(request)
            self._active_requests[request_key] = context
        
        return request_id
    
    def after_request(self, request: Any, response: Any) -> None:
        """Process request after handling.
        
        Args:
            request: Request object
            response: Response object
        """
        if not self.config.enabled:
            return
        
        request_key = id(request)
        
        with self._lock:
            context = self._active_requests.pop(request_key, {})
        
        if not context:
            return
        
        end_time = time.time()
        duration_ms = (end_time - context["start_time"]) * 1000
        
        # Extract response information
        status_code = getattr(response, 'status_code', 200)
        response_headers = self._extract_response_headers(response)
        response_size = self._calculate_response_size(response)
        response_body = self._extract_response_body(response) if self.config.track_response_body else ""
        
        # End request tracking
        if self.enable_request_tracking and context.get("request_id"):
            self.request_tracker.end_request(
                request_id=context["request_id"],
                status_code=status_code,
                response_headers=response_headers,
                response_body=response_body
            )
        
        # Record metrics
        self.metrics_collector.record_request(
            path=context["path"],
            method=context["method"],
            status_code=status_code,
            duration_ms=duration_ms,
            response_size=response_size,
            user_agent=context["user_agent"],
            ip_address=context["ip_address"]
        )
        
        # End performance profiling
        if self.enable_performance_monitoring and context.get("profiler_id"):
            self.profiler.stop_profiling(context["profiler_id"])
        
        # Store request data for retrieval
        with self._lock:
            request_data = {
                "timestamp": context["start_time"],
                "path": context["path"],
                "method": context["method"],
                "status_code": status_code,
                "duration_ms": duration_ms,
                "response_size": response_size,
                "user_agent": context["user_agent"],
                "ip_address": context["ip_address"]
            }
            
            self._tracked_requests.append(request_data)
            
            # Keep list size manageable
            if len(self._tracked_requests) > self.max_request_history:
                self._tracked_requests = self._tracked_requests[-self.max_request_history//2:]
    
    def on_error(self, request: Any, error: Exception) -> None:
        """Handle request errors.
        
        Args:
            request: Request object
            error: Exception that occurred
        """
        if not self.config.enabled or not self.enable_error_tracking:
            return
        
        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()
        path = getattr(request, 'path', '')
        headers = self._extract_headers(request)
        user_agent = headers.get('user-agent', '')
        ip_address = self._extract_ip_address(request)
        
        # Record error metric
        self.metrics_collector.record_error(
            error_type=error_type,
            error_message=error_message,
            path=path,
            traceback=error_traceback,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Store error data
        with self._lock:
            error_data = {
                "timestamp": time.time(),
                "error_type": error_type,
                "error_message": error_message,
                "path": path,
                "traceback": error_traceback,
                "user_agent": user_agent,
                "ip_address": ip_address
            }
            
            self._tracked_errors.append(error_data)
            
            # Keep list size manageable
            if len(self._tracked_errors) > 500:
                self._tracked_errors = self._tracked_errors[-250:]
    
    def get_tracked_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tracked requests.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of request data
        """
        with self._lock:
            return self._tracked_requests[-limit:]
    
    def get_tracked_errors(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get tracked errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of error data
        """
        with self._lock:
            return self._tracked_errors[-limit:]
    
    def get_performance_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get performance metrics.
        
        Args:
            limit: Maximum number of metrics to return
            
        Returns:
            List of performance data
        """
        return [
            {
                "timestamp": req["timestamp"],
                "path": req["path"],
                "method": req["method"],
                "duration_ms": req["duration_ms"],
                "status_code": req["status_code"]
            }
            for req in self.get_tracked_requests(limit)
        ]
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debug information.
        
        Returns:
            Dictionary containing all debug data
        """
        return {
            "config": self.config.to_dict(),
            "metrics": self.metrics_collector.get_metrics(),
            "request_stats": self.request_tracker.get_statistics(),
            "performance_stats": self.profiler.get_statistics(),
            "active_requests": len(self._active_requests),
            "middleware_stats": {
                "tracked_requests": len(self._tracked_requests),
                "tracked_errors": len(self._tracked_errors),
                "request_tracking_enabled": self.enable_request_tracking,
                "performance_monitoring_enabled": self.enable_performance_monitoring,
                "error_tracking_enabled": self.enable_error_tracking
            }
        }
    
    def clear_data(self, data_type: str = "all"):
        """Clear stored debug data.
        
        Args:
            data_type: Type of data to clear ("all", "requests", "errors", "metrics")
        """
        with self._lock:
            if data_type in ("all", "requests"):
                self._tracked_requests.clear()
                self.request_tracker.clear_requests()
            
            if data_type in ("all", "errors"):
                self._tracked_errors.clear()
            
            if data_type in ("all", "metrics"):
                self.metrics_collector.clear_metrics()
                self.profiler.clear_profiles()
    
    def _extract_headers(self, request: Any) -> Dict[str, str]:
        """Extract headers from request object.
        
        Args:
            request: Request object
            
        Returns:
            Dictionary of headers
        """
        if hasattr(request, 'headers'):
            # Convert headers to dict (handling different header types)
            if hasattr(request.headers, 'items'):
                return dict(request.headers.items())
            elif hasattr(request.headers, '__iter__'):
                return dict(request.headers)
        
        return {}
    
    def _extract_query_params(self, request: Any) -> Dict[str, str]:
        """Extract query parameters from request.
        
        Args:
            request: Request object
            
        Returns:
            Dictionary of query parameters
        """
        if hasattr(request, 'query_params'):
            return dict(request.query_params)
        elif hasattr(request, 'args'):
            return dict(request.args)
        
        return {}
    
    def _extract_body(self, request: Any) -> str:
        """Extract body from request.
        
        Args:
            request: Request object
            
        Returns:
            Request body as string
        """
        if hasattr(request, 'body'):
            body = request.body
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='ignore')
            return str(body)
        elif hasattr(request, 'data'):
            return str(request.data)
        
        return ""
    
    def _extract_ip_address(self, request: Any) -> str:
        """Extract IP address from request.
        
        Args:
            request: Request object
            
        Returns:
            Client IP address
        """
        # Try common attributes/headers for IP address
        if hasattr(request, 'remote_addr'):
            return request.remote_addr
        
        headers = self._extract_headers(request)
        
        # Check common proxy headers
        for header in ['x-forwarded-for', 'x-real-ip', 'x-client-ip']:
            if header in headers:
                return headers[header].split(',')[0].strip()
        
        return "unknown"
    
    def _extract_response_headers(self, response: Any) -> Dict[str, str]:
        """Extract headers from response object.
        
        Args:
            response: Response object
            
        Returns:
            Dictionary of response headers
        """
        if hasattr(response, 'headers'):
            if hasattr(response.headers, 'items'):
                return dict(response.headers.items())
            elif hasattr(response.headers, '__iter__'):
                return dict(response.headers)
        
        return {}
    
    def _calculate_response_size(self, response: Any) -> int:
        """Calculate response size in bytes.
        
        Args:
            response: Response object
            
        Returns:
            Response size in bytes
        """
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, bytes):
                return len(content)
            elif isinstance(content, str):
                return len(content.encode('utf-8'))
        
        return 0
    
    def _extract_response_body(self, response: Any) -> str:
        """Extract body from response.
        
        Args:
            response: Response object
            
        Returns:
            Response body as string
        """
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, bytes):
                return content.decode('utf-8', errors='ignore')
            return str(content)
        elif hasattr(response, 'data'):
            return str(response.data)
        
        return ""