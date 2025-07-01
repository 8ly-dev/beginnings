"""Tests for advanced debugging features."""

import pytest
import time
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from beginnings.cli.debug.middleware import MiddlewareTimelineTracker, DebugMiddleware
from beginnings.cli.debug.extension_monitor import ExtensionDependencyTracker, ExtensionDevelopmentTools
from beginnings.cli.debug.template_debugger import TemplateContextInspector, DatabaseQueryDebugger


class TestMiddlewareTimelineTracker:
    """Test middleware timeline tracking functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.tracker = MiddlewareTimelineTracker(max_timelines=10)
    
    def test_start_timeline(self):
        """Test starting a middleware timeline."""
        request_id = "test-123"
        middleware_stack = ["auth", "logging", "cors"]
        
        self.tracker.start_timeline(request_id, middleware_stack)
        
        timeline = self.tracker.get_timeline(request_id)
        assert timeline is not None
        assert timeline["request_id"] == request_id
        assert timeline["middleware_stack"] == middleware_stack
        assert "start_time" in timeline
        assert timeline["total_duration"] is None
    
    def test_track_middleware_execution(self):
        """Test tracking middleware execution."""
        request_id = "test-123"
        self.tracker.start_timeline(request_id, ["auth", "logging"])
        
        # Track middleware execution
        self.tracker.track_middleware_execution(
            request_id, 
            "auth", 
            "before",
            duration=0.01,
            configuration={"enabled": True},
            decision_points={"authenticated": True}
        )
        
        timeline = self.tracker.get_timeline(request_id)
        assert len(timeline["executions"]) == 1
        
        execution = timeline["executions"][0]
        assert execution["middleware_name"] == "auth"
        assert execution["execution_type"] == "before"
        assert execution["duration"] == 0.01
        assert execution["configuration"]["enabled"] is True
        assert execution["decision_points"]["authenticated"] is True
    
    def test_track_route_resolution(self):
        """Test tracking route resolution."""
        request_id = "test-123"
        self.tracker.start_timeline(request_id, ["auth"])
        
        self.tracker.track_route_resolution(
            request_id,
            "/api/users/{id}",
            "get_user",
            route_config={"cache": True},
            resolution_time=0.005
        )
        
        timeline = self.tracker.get_timeline(request_id)
        route_res = timeline["route_resolution"]
        
        assert route_res["pattern"] == "/api/users/{id}"
        assert route_res["handler"] == "get_user"
        assert route_res["config"]["cache"] is True
        assert route_res["resolution_time"] == 0.005
    
    def test_complete_timeline(self):
        """Test completing a timeline."""
        request_id = "test-123"
        self.tracker.start_timeline(request_id, ["auth"])
        
        # Add some delay to test duration calculation
        time.sleep(0.01)
        
        self.tracker.complete_timeline(request_id)
        
        timeline = self.tracker.get_timeline(request_id)
        assert timeline["total_duration"] is not None
        assert timeline["total_duration"] > 0
    
    def test_timeline_visualization_data(self):
        """Test getting visualization-ready timeline data."""
        request_id = "test-123"
        self.tracker.start_timeline(request_id, ["auth", "logging"])
        
        # Add middleware executions
        self.tracker.track_middleware_execution(
            request_id, "auth", "before", duration=0.01
        )
        self.tracker.track_middleware_execution(
            request_id, "logging", "before", duration=0.005
        )
        
        # Add route resolution
        self.tracker.track_route_resolution(
            request_id, "/api/test", "test_handler", resolution_time=0.002
        )
        
        self.tracker.complete_timeline(request_id)
        
        viz_data = self.tracker.get_timeline_visualization_data(request_id)
        
        assert viz_data is not None
        assert viz_data["request_id"] == request_id
        assert len(viz_data["events"]) == 3
        assert viz_data["total_duration"] > 0
        
        # Check events are sorted by start time
        for i in range(len(viz_data["events"]) - 1):
            assert viz_data["events"][i]["start"] <= viz_data["events"][i + 1]["start"]
    
    def test_max_timelines_limit(self):
        """Test that timeline history is limited."""
        # Create more timelines than the limit
        for i in range(15):
            request_id = f"test-{i}"
            self.tracker.start_timeline(request_id, ["auth"])
        
        all_timelines = self.tracker.get_all_timelines()
        assert len(all_timelines) == 10  # Should be limited to max_timelines


class TestExtensionDependencyTracker:
    """Test extension dependency tracking functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.tracker = ExtensionDependencyTracker(max_history=20)
    
    def test_register_extension(self):
        """Test registering an extension."""
        self.tracker.register_extension(
            "auth_extension",
            version="1.0.0",
            dependencies=["base_extension"],
            config={"enabled": True},
            file_path="/path/to/auth.py"
        )
        
        extension = self.tracker.get_extension_status("auth_extension")
        assert extension is not None
        assert extension["name"] == "auth_extension"
        assert extension["version"] == "1.0.0"
        assert extension["dependencies"] == ["base_extension"]
        assert extension["status"] == "registered"
    
    def test_extension_loading_lifecycle(self):
        """Test complete extension loading lifecycle."""
        ext_name = "test_extension"
        
        # Register
        self.tracker.register_extension(ext_name, version="1.0.0")
        
        # Start loading
        self.tracker.start_extension_loading(ext_name)
        extension = self.tracker.get_extension_status(ext_name)
        assert extension["status"] == "loading"
        
        # Complete loading successfully
        self.tracker.complete_extension_loading(
            ext_name, 
            success=True,
            config_validation_result={"valid": True}
        )
        
        extension = self.tracker.get_extension_status(ext_name)
        assert extension["status"] == "loaded"
        assert extension["loading_time"] is not None
        assert extension["config_validation"]["valid"] is True
    
    def test_extension_loading_failure(self):
        """Test extension loading failure tracking."""
        ext_name = "failing_extension"
        
        self.tracker.register_extension(ext_name)
        self.tracker.start_extension_loading(ext_name)
        self.tracker.complete_extension_loading(
            ext_name, 
            success=False, 
            error="Import error: module not found"
        )
        
        extension = self.tracker.get_extension_status(ext_name)
        assert extension["status"] == "failed"
        assert extension["error"] == "Import error: module not found"
    
    def test_hot_reload_tracking(self):
        """Test hot reload tracking."""
        ext_name = "reloadable_extension"
        
        self.tracker.register_extension(ext_name)
        
        # Track hot reload
        self.tracker.track_hot_reload(
            ext_name,
            success=True,
            reload_time=0.05,
            changes_detected=["config.py", "handlers.py"]
        )
        
        extension = self.tracker.get_extension_status(ext_name)
        assert extension["hot_reload_count"] == 1
        
        # Check loading events
        events = self.tracker.get_loading_events()
        hot_reload_events = [e for e in events if e["event_type"] == "hot_reload"]
        assert len(hot_reload_events) == 1
        assert hot_reload_events[0]["data"]["changes_detected"] == ["config.py", "handlers.py"]
    
    def test_dependency_graph(self):
        """Test dependency graph functionality."""
        # Register extensions with dependencies
        self.tracker.register_extension("base", dependencies=[])
        self.tracker.register_extension("auth", dependencies=["base"])
        self.tracker.register_extension("admin", dependencies=["auth", "base"])
        
        dep_graph = self.tracker.get_dependency_graph()
        assert "base" in dep_graph
        assert "auth" in dep_graph
        assert "admin" in dep_graph
        
        assert len(dep_graph["base"]) == 0
        assert "base" in dep_graph["auth"]
        assert "auth" in dep_graph["admin"]
        assert "base" in dep_graph["admin"]
    
    def test_loading_order(self):
        """Test optimal loading order calculation."""
        # Register extensions with dependencies
        self.tracker.register_extension("base", dependencies=[])
        self.tracker.register_extension("auth", dependencies=["base"])
        self.tracker.register_extension("admin", dependencies=["auth"])
        
        loading_order = self.tracker.get_loading_order()
        
        # Base should come first
        assert loading_order.index("base") < loading_order.index("auth")
        assert loading_order.index("auth") < loading_order.index("admin")
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        # Create circular dependency: A -> B -> C -> A
        self.tracker.register_extension("ext_a", dependencies=["ext_c"])
        self.tracker.register_extension("ext_b", dependencies=["ext_a"])
        self.tracker.register_extension("ext_c", dependencies=["ext_b"])
        
        cycles = self.tracker.get_circular_dependencies()
        assert len(cycles) > 0
        
        # Should detect the cycle
        cycle_found = False
        for cycle in cycles:
            if set(cycle) == {"ext_a", "ext_b", "ext_c"}:
                cycle_found = True
                break
        
        assert cycle_found
    
    def test_health_summary(self):
        """Test extension health summary."""
        # Register some extensions
        self.tracker.register_extension("ext1")
        self.tracker.register_extension("ext2")
        self.tracker.register_extension("ext3")
        
        # Complete loading for some
        self.tracker.complete_extension_loading("ext1", success=True)
        self.tracker.complete_extension_loading("ext2", success=False, error="Failed")
        
        summary = self.tracker.get_extension_health_summary()
        
        assert summary["total_extensions"] == 3
        assert summary["loaded"] == 1
        assert summary["failed"] == 1
        assert summary["loading"] == 0
        assert summary["success_rate"] == 1/3


class TestTemplateContextInspector:
    """Test template context inspection functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.inspector = TemplateContextInspector(max_renders=50)
    
    def test_template_render_tracking(self):
        """Test basic template render tracking."""
        context = {"user": {"name": "John"}, "items": [1, 2, 3]}
        
        render_id = self.inspector.start_template_render(
            "user_profile.html", 
            context,
            request_id="req-123"
        )
        
        assert render_id is not None
        
        render_data = self.inspector.get_render_data(render_id)
        assert render_data is not None
        assert render_data["template_name"] == "user_profile.html"
        assert render_data["request_id"] == "req-123"
        assert "context_summary" in render_data
    
    def test_variable_access_tracking(self):
        """Test tracking template variable access."""
        context = {"user": {"name": "John"}}
        render_id = self.inspector.start_template_render("test.html", context)
        
        # Track variable access
        self.inspector.track_variable_access(
            render_id, 
            "user.name", 
            "John",
            access_path="user.name"
        )
        
        render_data = self.inspector.get_render_data(render_id)
        assert len(render_data["variables_accessed"]) == 1
        
        var_access = render_data["variables_accessed"][0]
        assert var_access["name"] == "user.name"
        assert var_access["access_path"] == "user.name"
    
    def test_filter_application_tracking(self):
        """Test tracking template filter applications."""
        context = {"title": "hello world"}
        render_id = self.inspector.start_template_render("test.html", context)
        
        # Track filter application
        self.inspector.track_filter_application(
            render_id,
            "title",
            "hello world",
            "Hello World"
        )
        
        render_data = self.inspector.get_render_data(render_id)
        assert len(render_data["filters_applied"]) == 1
        
        filter_app = render_data["filters_applied"][0]
        assert filter_app["filter_name"] == "title"
        assert filter_app["input_value"] == "hello world"
        assert filter_app["output_value"] == "Hello World"
    
    def test_template_include_tracking(self):
        """Test tracking template includes."""
        context = {"user": {"name": "John"}}
        render_id = self.inspector.start_template_render("main.html", context)
        
        # Track template include
        self.inspector.track_template_include(
            render_id,
            "header.html",
            {"title": "Dashboard"}
        )
        
        render_data = self.inspector.get_render_data(render_id)
        assert len(render_data["includes_used"]) == 1
        
        include = render_data["includes_used"][0]
        assert include["template_name"] == "header.html"
        assert "title" in include["context"]
    
    def test_render_completion(self):
        """Test completing template render."""
        context = {"data": "test"}
        render_id = self.inspector.start_template_render("test.html", context)
        
        # Complete successfully
        self.inspector.complete_template_render(render_id, success=True)
        
        render_data = self.inspector.get_render_data(render_id)
        assert render_data["end_time"] is not None
        assert render_data["duration"] is not None
        assert render_data["error"] is None
    
    def test_render_error_tracking(self):
        """Test tracking template render errors."""
        context = {"data": "test"}
        render_id = self.inspector.start_template_render("test.html", context)
        
        # Complete with error
        self.inspector.complete_template_render(
            render_id, 
            success=False, 
            error="Template syntax error"
        )
        
        render_data = self.inspector.get_render_data(render_id)
        assert render_data["error"] == "Template syntax error"
        
        # Check error tracking
        errors = self.inspector.get_template_errors()
        assert len(errors) == 1
        assert errors[0]["error"] == "Template syntax error"
    
    def test_performance_summary(self):
        """Test template performance summary."""
        # Create some template renders with different durations
        contexts = [{"data": f"test{i}"} for i in range(5)]
        
        for i, context in enumerate(contexts):
            render_id = self.inspector.start_template_render(f"test{i}.html", context)
            time.sleep(0.001)  # Small delay to create duration
            self.inspector.complete_template_render(render_id, success=True)
        
        summary = self.inspector.get_performance_summary()
        
        assert summary["total_renders"] == 5
        assert summary["average_duration"] > 0
        assert len(summary["most_used_templates"]) > 0
        assert summary["error_rate"] == 0


class TestDatabaseQueryDebugger:
    """Test database query debugging functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.debugger = DatabaseQueryDebugger(max_queries=100)
    
    def test_query_tracking(self):
        """Test basic query tracking."""
        query_id = self.debugger.track_query(
            "SELECT * FROM users WHERE id = ?",
            parameters=[123],
            render_id="render-123",
            request_id="req-456"
        )
        
        assert query_id is not None
        
        # Complete the query
        self.debugger.complete_query(query_id, rows_affected=1)
        
        recent_queries = self.debugger.get_recent_queries(10)
        assert len(recent_queries) == 1
        
        query = recent_queries[0]
        assert query["query"] == "SELECT * FROM users WHERE id = ?"
        assert query["parameters"] == [123]
        assert query["render_id"] == "render-123"
        assert query["rows_affected"] == 1
        assert query["duration"] is not None
    
    def test_query_error_tracking(self):
        """Test tracking query errors."""
        query_id = self.debugger.track_query("INVALID SQL")
        
        self.debugger.complete_query(
            query_id, 
            error="Syntax error near 'INVALID'"
        )
        
        recent_queries = self.debugger.get_recent_queries(10)
        query = recent_queries[0]
        
        assert query["error"] == "Syntax error near 'INVALID'"
    
    def test_queries_for_render(self):
        """Test getting queries for a specific render."""
        render_id = "render-123"
        
        # Track multiple queries for the same render
        for i in range(3):
            query_id = self.debugger.track_query(
                f"SELECT * FROM table{i}",
                render_id=render_id
            )
            self.debugger.complete_query(query_id)
        
        # Track query for different render
        other_query_id = self.debugger.track_query(
            "SELECT * FROM other_table",
            render_id="other-render"
        )
        self.debugger.complete_query(other_query_id)
        
        render_queries = self.debugger.get_queries_for_render(render_id)
        assert len(render_queries) == 3
        
        for query in render_queries:
            assert query["render_id"] == render_id
    
    def test_slow_queries(self):
        """Test identifying slow queries."""
        # Create fast query
        fast_query_id = self.debugger.track_query("SELECT 1")
        time.sleep(0.01)
        self.debugger.complete_query(fast_query_id)
        
        # Create slow query
        slow_query_id = self.debugger.track_query("SELECT * FROM large_table")
        time.sleep(0.15)  # 150ms
        self.debugger.complete_query(slow_query_id)
        
        # Get slow queries with 100ms threshold
        slow_queries = self.debugger.get_slow_queries(threshold_ms=100)
        
        assert len(slow_queries) == 1
        assert slow_queries[0]["query"] == "SELECT * FROM large_table"


class TestDebugMiddlewareIntegration:
    """Test integration of debug middleware with timeline tracking."""
    
    def setup_method(self):
        """Set up test environment."""
        from beginnings.cli.debug.config import DebugConfig
        config = DebugConfig()
        self.middleware = DebugMiddleware(config=config)
    
    def test_timeline_integration(self):
        """Test that debug middleware includes timeline tracking."""
        assert hasattr(self.middleware, 'timeline_tracker')
        assert self.middleware.timeline_tracker is not None
    
    def test_timeline_methods(self):
        """Test timeline tracking methods on debug middleware."""
        request_id = "test-req-123"
        middleware_stack = ["auth", "logging"]
        
        # Test starting timeline
        self.middleware.start_middleware_timeline(request_id, middleware_stack)
        
        # Test tracking execution
        self.middleware.track_middleware_execution(
            request_id, "auth", "before", duration=0.01
        )
        
        # Test route resolution tracking
        self.middleware.track_route_resolution(
            request_id, "/api/test", "test_handler"
        )
        
        # Test completion
        self.middleware.complete_middleware_timeline(request_id)
        
        # Verify timeline data
        timeline_data = self.middleware.get_timeline_data(request_id)
        assert timeline_data is not None
        assert timeline_data["request_id"] == request_id
        assert len(timeline_data["events"]) == 2  # middleware + route resolution