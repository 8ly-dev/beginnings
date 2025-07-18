"""Debug dashboard web interface."""

from __future__ import annotations

import json
import time
import threading
from typing import Dict, Any, Optional
from pathlib import Path

# Use FastAPI directly for the debug dashboard
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse as APIResponse
    from fastapi.responses import HTMLResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .config import DebugConfig
from .metrics import MetricsCollector
from .logs import LogStreamer
from .requests import RequestTracker
from .profiler import PerformanceProfiler
from .websocket import WebSocketManager, DebugWebSocketHandler
from .extension_monitor import ExtensionDependencyTracker, ExtensionDevelopmentTools
from .template_debugger import TemplateContextInspector, DatabaseQueryDebugger


class DebugDashboard:
    """Web-based debugging dashboard."""
    
    def __init__(
        self,
        config: Optional[DebugConfig] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        enable_profiler: bool = False,
        monitor_app: Optional[str] = None
    ):
        """Initialize debug dashboard.
        
        Args:
            config: Debug configuration
            host: Host to bind dashboard to
            port: Port to bind dashboard to
            enable_profiler: Enable performance profiler
            monitor_app: Application file to monitor
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for debug dashboard")
        
        self.config = config or DebugConfig()
        self.host = host
        self.port = port
        self.enable_profiler = enable_profiler
        self.monitor_app = monitor_app
        
        # Initialize components
        self.metrics_collector = MetricsCollector()
        self.log_streamer = LogStreamer(max_lines=self.config.max_log_lines)
        self.request_tracker = RequestTracker(
            max_requests=self.config.max_request_history,
            track_headers=self.config.track_request_headers,
            track_body=self.config.track_request_body
        )
        
        if enable_profiler:
            self.profiler = PerformanceProfiler(
                profile_cpu=self.config.enable_cpu_profiling,
                profile_memory=self.config.enable_memory_profiling,
                profile_threshold_ms=self.config.profile_threshold_ms
            )
        else:
            self.profiler = None
        
        # WebSocket for real-time updates
        self.websocket_manager = WebSocketManager()
        self.websocket_handler = DebugWebSocketHandler(self.websocket_manager)
        
        # Advanced debugging components
        self.extension_tracker = ExtensionDependencyTracker()
        self.extension_tools = ExtensionDevelopmentTools(self.extension_tracker)
        self.template_inspector = TemplateContextInspector()
        self.db_debugger = DatabaseQueryDebugger()
        
        # Beginnings app
        self.app = None
        self.monitoring_active = False
        
        # Background update thread
        self._update_thread = None
        self._stop_event = threading.Event()
        
        # Debug middleware integration
        self._debug_middleware = None
    
    def create_app(self) -> FastAPI:
        """Create FastAPI application for dashboard.
        
        Returns:
            FastAPI application instance
        """
        app = FastAPI(title="Beginnings Debug Dashboard")
        
        # Configure template directory
        template_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"
        
        # Dashboard routes using FastAPI routing
        @app.get("/")
        def dashboard(request: Request):
            """Main dashboard page."""
            dashboard_html = self._render_dashboard_template()
            return HTMLResponse(dashboard_html)
        
        @app.get("/api/status")
        def api_status(request):
            """Get dashboard status."""
            data = {
                "status": "running",
                "timestamp": time.time(),
                "config": {
                    "profiler_enabled": self.enable_profiler,
                    "monitoring_app": self.monitor_app,
                    "real_time_updates": self.config.enable_real_time_updates
                }
            }
            return APIResponse(data)
        
        @app.get("/api/metrics")
        def api_metrics(request):
            """Get application metrics."""
            return APIResponse(self.metrics_collector.get_metrics())
        
        @app.get("/api/requests")
        def api_requests(request: Request, limit: int = 50):
            """Get request tracking data."""
            data = {
                "requests": self.request_tracker.get_recent_requests(limit),
                "statistics": self.request_tracker.get_statistics()
            }
            return APIResponse(data)
        
        @app.get("/api/requests/slow")
        def api_slow_requests(request: Request, min_duration: float = 1000, limit: int = 25):
            """Get slow requests."""
            data = {
                "slow_requests": self.request_tracker.get_slow_requests(min_duration, limit)
            }
            return APIResponse(data)
        
        @app.get("/api/requests/errors")
        def api_error_requests(request: Request, limit: int = 25):
            """Get error requests."""
            data = {
                "error_requests": self.request_tracker.get_error_requests(limit)
            }
            return APIResponse(data)
        
        @app.get("/api/logs")
        def api_logs(request: Request, limit: int = 100, level: str = None):
            """Get application logs."""
            level_filter = level
            
            data = {
                "logs": self.log_streamer.get_recent_logs(limit, level_filter),
                "statistics": self.log_streamer.get_log_statistics()
            }
            return APIResponse(data)
        
        @app.get("/api/logs/search")
        def api_logs_search(request: Request, q: str = "", level: str = None, limit: int = 50):
            """Search logs."""
            query = q
            level_filter = level
            
            if not query:
                return APIResponse({"logs": []})
            
            data = {
                "logs": self.log_streamer.search_logs(query, level_filter, limit)
            }
            return APIResponse(data)
        
        @app.get("/api/profiler")
        def api_profiler(request: Request, limit: int = 50):
            """Get profiler data."""
            if not self.profiler:
                return APIResponse({"error": "Profiler not enabled"}, status_code=400)
            data = {
                "profiles": [
                    {
                        "name": p.name,
                        "start_time": p.start_time,
                        "duration_ms": p.duration_ms,
                        "memory_usage": p.memory_usage,
                        "cpu_stats": p.cpu_stats,
                        "context": p.context
                    }
                    for p in self.profiler.get_profiles(limit)
                ],
                "statistics": self.profiler.get_statistics()
            }
            return APIResponse(data)
        
        @app.get("/api/profiler/slow")
        def api_slow_profiles(request: Request, min_duration: float = 1000, limit: int = 25):
            """Get slow profiles."""
            if not self.profiler:
                return APIResponse({"error": "Profiler not enabled"}, status_code=400)
            
            slow_profiles = self.profiler.get_slow_profiles(min_duration, limit)
            data = {
                "slow_profiles": [
                    {
                        "name": p.name,
                        "start_time": p.start_time,
                        "duration_ms": p.duration_ms,
                        "memory_usage": p.memory_usage,
                        "cpu_stats": p.cpu_stats
                    }
                    for p in slow_profiles
                ]
            }
            return APIResponse(data)
        
        @app.post("/api/clear")
        async def api_clear(request: Request):
            """Clear debug data."""
            try:
                import json
                body = await request.body()
                data = json.loads(body) if body else {}
                data_type = data.get("type", "all")
            except (json.JSONDecodeError, AttributeError):
                data_type = "all"
            
            if data_type in ("all", "metrics"):
                self.metrics_collector.clear_metrics()
            
            if data_type in ("all", "requests"):
                self.request_tracker.clear_requests()
            
            if data_type in ("all", "logs"):
                self.log_streamer.clear_logs()
            
            if data_type in ("all", "profiler") and self.profiler:
                self.profiler.clear_profiles()
            
            return APIResponse({"success": True, "cleared": data_type})
        
        @app.get("/api/export")
        def api_export(request):
            """Export debug data."""
            export_data = {
                "timestamp": time.time(),
                "metrics": self.metrics_collector.get_metrics(),
                "request_statistics": self.request_tracker.get_statistics(),
                "log_statistics": self.log_streamer.get_log_statistics(),
                "recent_requests": self.request_tracker.get_recent_requests(100),
                "recent_logs": self.log_streamer.get_recent_logs(100),
                "config": self.config.to_dict()
            }
            
            if self.profiler:
                export_data["profiler_statistics"] = self.profiler.get_statistics()
                export_data["recent_profiles"] = [
                    {
                        "name": p.name,
                        "start_time": p.start_time,
                        "duration_ms": p.duration_ms,
                        "memory_usage": p.memory_usage,
                        "cpu_stats": p.cpu_stats
                    }
                    for p in self.profiler.get_profiles(50)
                ]
            
            return APIResponse(export_data)
        
        # Static file serving
        @app.get("/static/{path:path}")
        def static_files(request: Request, path: str):
            """Serve static files."""
            file_path = static_dir / path
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Determine content type
                content_type = "text/plain"
                if file_path.suffix == ".css":
                    content_type = "text/css"
                elif file_path.suffix == ".js":
                    content_type = "application/javascript"
                elif file_path.suffix == ".html":
                    content_type = "text/html"
                
                return HTMLResponse(content, headers={"Content-Type": content_type})
            
            return APIResponse({"error": "File not found"}, status_code=404)
        
        # Advanced debugging API endpoints
        @app.get("/api/timeline/{request_id}")
        def api_timeline(request_id: str):
            """Get middleware timeline for a specific request."""
            if not hasattr(self, '_debug_middleware') or not self._debug_middleware:
                return APIResponse({
                    "request_id": request_id,
                    "timeline_available": False,
                    "message": "Timeline tracking requires debug middleware integration"
                })
            
            timeline_data = self._debug_middleware.get_timeline_data(request_id)
            
            if not timeline_data:
                return APIResponse({
                    "request_id": request_id,
                    "timeline_available": False,
                    "message": "No timeline data available for this request"
                })
            
            return APIResponse({
                "request_id": request_id,
                "timeline_available": True,
                "timeline": timeline_data
            })
        
        @app.get("/api/timeline")
        def api_all_timelines():
            """Get all available timeline data."""
            if not hasattr(self, '_debug_middleware') or not self._debug_middleware:
                return APIResponse({
                    "timelines": {},
                    "message": "Timeline tracking requires debug middleware integration"
                })
            
            all_timelines = self._debug_middleware.get_all_timeline_data()
            
            return APIResponse({
                "timelines": all_timelines,
                "count": len(all_timelines)
            })
        
        @app.get("/api/extensions")
        def api_extensions():
            """Get extension status and dependency information."""
            extensions = self.extension_tracker.get_all_extensions()
            dependency_graph = self.extension_tracker.get_dependency_graph()
            health_summary = self.extension_tracker.get_extension_health_summary()
            circular_deps = self.extension_tracker.get_circular_dependencies()
            
            return APIResponse({
                "extensions": extensions,
                "dependency_graph": {k: list(v) for k, v in dependency_graph.items()},
                "health_summary": health_summary,
                "circular_dependencies": circular_deps,
                "loading_order": self.extension_tracker.get_loading_order()
            })
        
        @app.get("/api/extensions/{extension_name}")
        def api_extension_details(extension_name: str):
            """Get detailed information about a specific extension."""
            extension = self.extension_tracker.get_extension_status(extension_name)
            if not extension:
                return APIResponse({"error": "Extension not found"}, status_code=404)
            
            return APIResponse({
                "extension": extension,
                "loading_events": [
                    event for event in self.extension_tracker.get_loading_events(50)
                    if event["extension_name"] == extension_name
                ]
            })
        
        @app.get("/api/templates")
        def api_templates():
            """Get template rendering information."""
            recent_renders = self.template_inspector.get_recent_renders(50)
            template_errors = self.template_inspector.get_template_errors(25)
            performance_summary = self.template_inspector.get_performance_summary()
            
            return APIResponse({
                "recent_renders": recent_renders,
                "template_errors": template_errors,
                "performance_summary": performance_summary
            })
        
        @app.get("/api/templates/{render_id}")
        def api_template_details(render_id: str):
            """Get detailed information about a specific template render."""
            render_data = self.template_inspector.get_render_data(render_id)
            if not render_data:
                return APIResponse({"error": "Render not found"}, status_code=404)
            
            context_data = self.template_inspector.get_context_for_render(render_id)
            queries = self.db_debugger.get_queries_for_render(render_id)
            
            return APIResponse({
                "render": render_data,
                "context": context_data,
                "database_queries": queries
            })
        
        @app.get("/api/templates/template/{template_name}")
        def api_template_renders(template_name: str, limit: int = 25):
            """Get renders for a specific template."""
            renders = self.template_inspector.get_template_renders(template_name, limit)
            return APIResponse({"renders": renders})
        
        @app.get("/api/database/queries")
        def api_database_queries(limit: int = 50):
            """Get recent database queries."""
            recent_queries = self.db_debugger.get_recent_queries(limit)
            slow_queries = self.db_debugger.get_slow_queries(100)  # 100ms threshold
            
            return APIResponse({
                "recent_queries": recent_queries,
                "slow_queries": slow_queries
            })
        
        @app.post("/api/extensions/validate")
        async def api_validate_extension(request: Request):
            """Validate extension configuration."""
            try:
                body = await request.body()
                data = json.loads(body)
                extension_name = data.get("extension_name")
                config = data.get("config", {})
                
                if not extension_name:
                    return APIResponse({"error": "extension_name required"}, status_code=400)
                
                validation_result = self.extension_tools.validate_extension_config(
                    extension_name, config
                )
                
                return APIResponse({
                    "validation_result": validation_result
                })
            except json.JSONDecodeError:
                return APIResponse({"error": "Invalid JSON"}, status_code=400)
        
        @app.post("/api/extensions/scaffold")
        async def api_scaffold_extension(request: Request):
            """Generate extension scaffold."""
            try:
                body = await request.body()
                data = json.loads(body)
                extension_name = data.get("extension_name")
                output_dir = data.get("output_dir")
                template_type = data.get("template_type", "basic")
                
                if not extension_name or not output_dir:
                    return APIResponse({
                        "error": "extension_name and output_dir required"
                    }, status_code=400)
                
                scaffold_result = self.extension_tools.generate_extension_scaffold(
                    extension_name, output_dir, template_type
                )
                
                return APIResponse({
                    "scaffold_result": scaffold_result
                })
            except json.JSONDecodeError:
                return APIResponse({"error": "Invalid JSON"}, status_code=400)
        
        self.app = app
        return app
    
    def set_debug_middleware(self, debug_middleware):
        """Set the debug middleware instance for timeline tracking.
        
        Args:
            debug_middleware: DebugMiddleware instance
        """
        self._debug_middleware = debug_middleware
    
    def get_debug_middleware(self):
        """Get the debug middleware instance.
        
        Returns:
            DebugMiddleware instance or None
        """
        return self._debug_middleware
    
    def _render_dashboard_template(self) -> str:
        """Render the dashboard HTML template.
        
        Returns:
            HTML content as string
        """
        # Read the template file
        template_path = Path(__file__).parent / "templates" / "dashboard.html"
        
        if not template_path.exists():
            # Return a simple fallback HTML if template is missing
            return """
<!DOCTYPE html>
<html>
<head>
    <title>Beginnings Debug Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; }
        .error { color: red; background: #ffe6e6; padding: 1rem; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Beginnings Debug Dashboard</h1>
    <div class="error">Template file not found. Please ensure dashboard.html exists in templates directory.</div>
</body>
</html>
            """
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Simple template variable replacement
            # In a real implementation, you'd use a proper template engine like Jinja2
            template_content = template_content.replace(
                '{{ title or "Beginnings Debug Dashboard" }}', 
                'Beginnings Debug Dashboard'
            )
            
            # Replace config variables with actual values
            template_content = template_content.replace(
                '{% if config.debug.enable_profiler %}',
                '<!-- Profiler section -->' if self.enable_profiler else '<!-- Profiler disabled -->'
            )
            template_content = template_content.replace(
                '{% endif %}', 
                ''
            )
            
            # Replace update interval
            template_content = template_content.replace(
                '{{ config.debug.update_interval_ms or 5000 }}',
                str(getattr(self.config, 'update_interval_ms', 5000))
            )
            
            # Replace real-time updates check
            enable_updates = getattr(self.config, 'enable_real_time_updates', True)
            if not enable_updates:
                # Remove the auto-refresh interval code
                template_content = template_content.replace(
                    '{% if config.debug.enable_real_time_updates %}',
                    '// Real-time updates disabled'
                )
            else:
                template_content = template_content.replace(
                    '{% if config.debug.enable_real_time_updates %}', 
                    ''
                )
            
            return template_content
            
        except Exception as e:
            # Return error template if rendering fails
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Beginnings Debug Dashboard - Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        .error {{ color: red; background: #ffe6e6; padding: 1rem; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Beginnings Debug Dashboard</h1>
    <div class="error">Template rendering error: {e}</div>
</body>
</html>
            """
    
    def start(self):
        """Start the debug dashboard."""
        if not self.app:
            self.create_app()
        
        # Attach log streamer to capture application logs
        self.log_streamer.attach_to_logger()
        
        # Start real-time update thread if enabled
        if self.config.enable_real_time_updates:
            self.start_real_time_updates()
        
        # Start monitoring if app specified
        if self.monitor_app:
            self.start_monitoring()
        
        print(f"Debug Dashboard starting on http://{self.host}:{self.port}")
        print(f"Dashboard features:")
        print(f"  - Request tracking: {self.config.enable_request_tracking}")
        print(f"  - Performance monitoring: {self.config.enable_performance_monitoring}")
        print(f"  - Error tracking: {getattr(self.config, 'enable_error_tracking', True)}")
        print(f"  - Profiler: {self.enable_profiler}")
        print(f"  - Real-time updates: {getattr(self.config, 'enable_real_time_updates', True)}")
        
        try:
            # Use Beginnings' native server instead of Flask
            import uvicorn
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
        except KeyboardInterrupt:
            print("\nShutting down debug dashboard...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the debug dashboard."""
        self._stop_event.set()
        
        # Stop real-time updates
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Detach log streamer
        self.log_streamer.detach_from_logger()
    
    def start_monitoring(self):
        """Start monitoring the target application."""
        if not self.monitor_app:
            return
        
        self.monitoring_active = True
        print(f"Monitoring application: {self.monitor_app}")
        
        # This would typically involve process monitoring
        # For now, just set the flag
    
    def stop_monitoring(self):
        """Stop monitoring the target application."""
        self.monitoring_active = False
    
    def start_real_time_updates(self):
        """Start real-time update broadcasting."""
        def update_worker():
            while not self._stop_event.is_set():
                try:
                    # Broadcast periodic updates to connected clients
                    update_data = {
                        "type": "dashboard_update",
                        "timestamp": time.time(),
                        "data": {
                            "metrics_summary": self._get_metrics_summary(),
                            "recent_requests": len(self.request_tracker.get_recent_requests(10)),
                            "recent_errors": len(self.request_tracker.get_error_requests(5)),
                            "log_counts": self.log_streamer.get_log_statistics()["level_counts"]
                        }
                    }
                    
                    self.websocket_manager.broadcast(update_data, "dashboard")
                    
                    # Wait for next update interval
                    self._stop_event.wait(self.config.update_interval_ms / 1000.0)
                    
                except Exception as e:
                    print(f"Error in real-time update worker: {e}")
                    time.sleep(1.0)
        
        self._update_thread = threading.Thread(target=update_worker, daemon=True)
        self._update_thread.start()
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary metrics for real-time updates.
        
        Returns:
            Dictionary containing summary metrics
        """
        metrics = self.metrics_collector.get_metrics()
        summary = metrics.get("summary", {})
        
        return {
            "total_requests": summary.get("total_requests", 0),
            "total_errors": summary.get("total_errors", 0),
            "requests_per_minute": summary.get("requests_per_minute", 0),
            "error_rate_percent": summary.get("error_rate_percent", 0),
            "avg_response_time_ms": summary.get("avg_response_time_ms", 0)
        }


def create_dashboard(
    config: Optional[DebugConfig] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    enable_profiler: bool = False
) -> DebugDashboard:
    """Create debug dashboard with default settings.
    
    Args:
        config: Debug configuration
        host: Host to bind to
        port: Port to bind to
        enable_profiler: Enable performance profiler
        
    Returns:
        DebugDashboard instance
    """
    return DebugDashboard(
        config=config,
        host=host,
        port=port,
        enable_profiler=enable_profiler
    )