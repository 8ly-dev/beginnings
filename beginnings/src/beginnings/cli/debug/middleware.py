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


class MiddlewareTimelineTracker:
    """Tracks middleware execution timeline for visual debugging."""
    
    def __init__(self, max_timelines: int = 100):
        """Initialize middleware timeline tracker.
        
        Args:
            max_timelines: Maximum number of request timelines to keep
        """
        self.max_timelines = max_timelines
        self._timelines: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
    
    def start_timeline(self, request_id: str, middleware_stack: List[str]) -> None:
        """Start tracking a middleware execution timeline.
        
        Args:
            request_id: Unique request identifier
            middleware_stack: List of middleware names in execution order
        """
        with self._lock:
            self._timelines[request_id] = {
                "request_id": request_id,
                "middleware_stack": middleware_stack,
                "executions": [],
                "start_time": time.time(),
                "total_duration": None,
                "route_resolution": None,
                "configuration_used": {}
            }
            
            # Maintain max timeline limit
            if len(self._timelines) > self.max_timelines:
                oldest_key = min(self._timelines.keys(), 
                               key=lambda k: self._timelines[k]["start_time"])
                del self._timelines[oldest_key]
    
    def track_middleware_execution(
        self, 
        request_id: str, 
        middleware_name: str, 
        execution_type: str,  # 'before' or 'after'
        duration: float = None,
        configuration: Dict[str, Any] = None,
        decision_points: Dict[str, Any] = None
    ) -> None:
        """Track individual middleware execution.
        
        Args:
            request_id: Request identifier
            middleware_name: Name of the middleware
            execution_type: 'before' or 'after' request processing
            duration: Execution duration in seconds
            configuration: Middleware configuration used
            decision_points: Decision points (auth success, rate limit status, etc.)
        """
        with self._lock:
            if request_id not in self._timelines:
                return
            
            execution_data = {
                "middleware_name": middleware_name,
                "execution_type": execution_type,
                "timestamp": time.time(),
                "duration": duration,
                "configuration": configuration or {},
                "decision_points": decision_points or {}
            }
            
            self._timelines[request_id]["executions"].append(execution_data)
            
            # Update configuration tracking
            if configuration:
                self._timelines[request_id]["configuration_used"][middleware_name] = configuration
    
    def track_route_resolution(
        self, 
        request_id: str, 
        route_pattern: str, 
        route_handler: str,
        route_config: Dict[str, Any] = None,
        resolution_time: float = None
    ) -> None:
        """Track route resolution details.
        
        Args:
            request_id: Request identifier
            route_pattern: Matched route pattern
            route_handler: Handler function/method name
            route_config: Route configuration
            resolution_time: Time taken to resolve route
        """
        with self._lock:
            if request_id not in self._timelines:
                return
            
            self._timelines[request_id]["route_resolution"] = {
                "pattern": route_pattern,
                "handler": route_handler,
                "config": route_config or {},
                "resolution_time": resolution_time,
                "timestamp": time.time()
            }
    
    def complete_timeline(self, request_id: str) -> None:
        """Mark timeline as complete and calculate total duration.
        
        Args:
            request_id: Request identifier
        """
        with self._lock:
            if request_id not in self._timelines:
                return
            
            timeline = self._timelines[request_id]
            timeline["total_duration"] = time.time() - timeline["start_time"]
    
    def get_timeline(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get timeline data for a specific request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Timeline data or None if not found
        """
        with self._lock:
            return self._timelines.get(request_id)
    
    def get_all_timelines(self) -> Dict[str, Dict[str, Any]]:
        """Get all timeline data.
        
        Returns:
            Dictionary of all timeline data
        """
        with self._lock:
            return dict(self._timelines)
    
    def get_timeline_visualization_data(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get timeline data formatted for visualization.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Visualization-ready timeline data
        """
        timeline = self.get_timeline(request_id)
        if not timeline:
            return None
        
        # Organize executions into timeline format
        events = []
        base_time = timeline["start_time"]
        
        for execution in timeline["executions"]:
            events.append({
                "name": f"{execution['middleware_name']} ({execution['execution_type']})",
                "start": (execution["timestamp"] - base_time) * 1000,  # Convert to ms
                "duration": (execution.get("duration", 0)) * 1000,
                "type": execution["execution_type"],
                "middleware": execution["middleware_name"],
                "config": execution["configuration"],
                "decisions": execution["decision_points"]
            })
        
        # Add route resolution event
        if timeline["route_resolution"]:
            route_res = timeline["route_resolution"]
            resolution_time = route_res.get("resolution_time") or 0
            events.append({
                "name": f"Route: {route_res['pattern']}",
                "start": (route_res["timestamp"] - base_time) * 1000,
                "duration": resolution_time * 1000,
                "type": "route_resolution",
                "pattern": route_res["pattern"],
                "handler": route_res["handler"],
                "config": route_res["config"]
            })
        
        return {
            "request_id": request_id,
            "total_duration": timeline["total_duration"] * 1000 if timeline["total_duration"] else 0,
            "middleware_stack": timeline["middleware_stack"],
            "events": sorted(events, key=lambda x: x["start"]),
            "configuration_summary": timeline["configuration_used"]
        }


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
        
        # Initialize timeline tracker
        self.timeline_tracker = MiddlewareTimelineTracker(
            max_timelines=max_request_history
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
    
    # Timeline tracking methods
    def start_middleware_timeline(self, request_id: str, middleware_stack: List[str]) -> None:
        """Start tracking middleware execution timeline.
        
        Args:
            request_id: Unique request identifier
            middleware_stack: List of middleware names in execution order
        """
        self.timeline_tracker.start_timeline(request_id, middleware_stack)
    
    def track_middleware_execution(
        self, 
        request_id: str, 
        middleware_name: str, 
        execution_type: str,
        duration: float = None,
        configuration: Dict[str, Any] = None,
        decision_points: Dict[str, Any] = None
    ) -> None:
        """Track individual middleware execution.
        
        Args:
            request_id: Request identifier
            middleware_name: Name of the middleware
            execution_type: 'before' or 'after' request processing
            duration: Execution duration in seconds
            configuration: Middleware configuration used
            decision_points: Decision points (auth success, rate limit status, etc.)
        """
        self.timeline_tracker.track_middleware_execution(
            request_id, middleware_name, execution_type, 
            duration, configuration, decision_points
        )
    
    def track_route_resolution(
        self, 
        request_id: str, 
        route_pattern: str, 
        route_handler: str,
        route_config: Dict[str, Any] = None,
        resolution_time: float = None
    ) -> None:
        """Track route resolution details.
        
        Args:
            request_id: Request identifier
            route_pattern: Matched route pattern
            route_handler: Handler function/method name
            route_config: Route configuration
            resolution_time: Time taken to resolve route
        """
        self.timeline_tracker.track_route_resolution(
            request_id, route_pattern, route_handler, route_config, resolution_time
        )
    
    def complete_middleware_timeline(self, request_id: str) -> None:
        """Complete middleware timeline tracking.
        
        Args:
            request_id: Request identifier
        """
        self.timeline_tracker.complete_timeline(request_id)
    
    def get_timeline_data(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get timeline data for a specific request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Timeline data or None if not found
        """
        return self.timeline_tracker.get_timeline_visualization_data(request_id)
    
    def get_all_timeline_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all timeline data.
        
        Returns:
            Dictionary of all timeline data formatted for visualization
        """
        all_timelines = self.timeline_tracker.get_all_timelines()
        visualization_data = {}
        
        for request_id in all_timelines:
            viz_data = self.timeline_tracker.get_timeline_visualization_data(request_id)
            if viz_data:
                visualization_data[request_id] = viz_data
        
        return visualization_data