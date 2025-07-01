"""Tests for debugging dashboard and web interface."""

import pytest
import tempfile
import os
import json
import time
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from beginnings.cli.main import cli


class TestDebugDashboard:
    """Test debugging dashboard functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_command_exists(self):
        """Test debug command is available."""
        result = self.runner.invoke(cli, ["debug", "--help"])
        assert result.exit_code == 0
        assert "debugging dashboard" in result.output.lower()
    
    def test_debug_dashboard_start(self):
        """Test starting debug dashboard."""
        with patch('src.beginnings.cli.debug.dashboard.DebugDashboard') as mock_dashboard:
            mock_instance = MagicMock()
            mock_dashboard.return_value = mock_instance
            
            result = self.runner.invoke(cli, [
                "debug",
                "--port", "8001",
                "--host", "127.0.0.1"
            ])
            
            assert result.exit_code == 0
            mock_dashboard.assert_called_once()
            mock_instance.start.assert_called_once()
    
    def test_debug_dashboard_with_app_monitoring(self):
        """Test debug dashboard with application monitoring."""
        app_file = os.path.join(self.temp_dir, "app.py")
        with open(app_file, "w") as f:
            f.write("# Test app")
        
        with patch('src.beginnings.cli.debug.dashboard.DebugDashboard') as mock_dashboard:
            mock_instance = MagicMock()
            mock_dashboard.return_value = mock_instance
            
            result = self.runner.invoke(cli, [
                "debug",
                "--monitor-app", app_file,
                "--enable-profiler"
            ])
            
            assert result.exit_code == 0
            mock_dashboard.assert_called_once()
    
    def test_profile_command_exists(self):
        """Test profile command is available."""
        result = self.runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0
        assert "performance profiling" in result.output.lower()
    
    def test_profile_command_with_output(self):
        """Test profile command with output file."""
        output_file = os.path.join(self.temp_dir, "profile.json")
        
        with patch('src.beginnings.cli.debug.profiler.start_profiling') as mock_profiler:
            result = self.runner.invoke(cli, [
                "profile",
                "--output", output_file,
                "--duration", "5"
            ])
            
            assert result.exit_code == 0
            mock_profiler.assert_called_once()


class TestDebugWebInterface:
    """Test debug web interface functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_dashboard_initialization(self):
        """Test debug dashboard can be initialized."""
        from beginnings.cli.debug.dashboard import DebugDashboard
        
        dashboard = DebugDashboard(
            host="127.0.0.1",
            port=8001,
            enable_profiler=True,
            monitor_app=None
        )
        
        assert dashboard.host == "127.0.0.1"
        assert dashboard.port == 8001
        assert dashboard.enable_profiler is True
        assert dashboard.monitor_app is None
    
    def test_debug_dashboard_route_registration(self):
        """Test debug dashboard registers routes correctly."""
        from beginnings.cli.debug.dashboard import DebugDashboard
        
        dashboard = DebugDashboard()
        app = dashboard.create_app()
        
        # Check that routes are registered (FastAPI stores routes differently)
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        assert "/" in routes  # Main dashboard
        assert "/api/status" in routes  # Status API
        assert "/api/metrics" in routes  # Metrics API
        assert "/api/logs" in routes  # Logs API
        assert "/api/requests" in routes  # Request tracking
    
    def test_debug_dashboard_metrics_collection(self):
        """Test debug dashboard collects metrics."""
        from beginnings.cli.debug.metrics import MetricsCollector
        
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_request("/test", "GET", 200, 0.1)
        collector.record_request("/api/data", "POST", 201, 0.2)
        collector.record_error("ValueError", "test error", "/test")
        
        metrics = collector.get_metrics()
        
        assert "requests" in metrics
        assert "errors" in metrics
        assert "response_times" in metrics
        assert len(metrics["requests"]) == 2
        assert len(metrics["errors"]) == 1
    
    def test_debug_dashboard_log_streaming(self):
        """Test debug dashboard streams logs."""
        from beginnings.cli.debug.logs import LogStreamer
        
        streamer = LogStreamer(max_lines=100)
        
        # Add some log entries
        streamer.add_log("INFO", "Test message 1")
        streamer.add_log("ERROR", "Test error message")
        streamer.add_log("DEBUG", "Debug information")
        
        logs = streamer.get_recent_logs(limit=10)
        
        assert len(logs) == 3
        assert logs[0]["level"] == "INFO"
        assert logs[1]["level"] == "ERROR"
        assert logs[2]["level"] == "DEBUG"
    
    def test_debug_dashboard_request_tracking(self):
        """Test debug dashboard tracks requests."""
        from beginnings.cli.debug.requests import RequestTracker
        
        tracker = RequestTracker(max_requests=50)
        
        # Track some requests
        request1 = tracker.start_request("/api/users", "GET", {"user-agent": "test"})
        time.sleep(0.01)  # Small delay
        tracker.end_request(request1, 200, {"content-type": "application/json"})
        
        request2 = tracker.start_request("/api/posts", "POST", {})
        tracker.end_request(request2, 500, {})
        
        requests = tracker.get_recent_requests(limit=10)
        
        assert len(requests) == 2
        assert requests[0]["path"] == "/api/users"
        assert requests[0]["status_code"] == 200
        assert requests[1]["path"] == "/api/posts"
        assert requests[1]["status_code"] == 500
    
    def test_debug_dashboard_real_time_updates(self):
        """Test debug dashboard provides real-time updates."""
        from beginnings.cli.debug.websocket import WebSocketManager
        
        manager = WebSocketManager()
        
        # Simulate websocket connections
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        
        manager.add_connection(mock_ws1)
        manager.add_connection(mock_ws2)
        
        assert len(manager.connections) == 2
        
        # Broadcast update
        update_data = {"type": "metrics", "data": {"requests": 5}}
        manager.broadcast(update_data)
        
        # Both connections should receive the update
        mock_ws1.send.assert_called_once()
        mock_ws2.send.assert_called_once()
        
        # Remove connection
        manager.remove_connection(mock_ws1)
        assert len(manager.connections) == 1


class TestPerformanceProfiler:
    """Test performance profiling functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_profiler_initialization(self):
        """Test profiler can be initialized."""
        from beginnings.cli.debug.profiler import PerformanceProfiler
        
        profiler = PerformanceProfiler(
            output_dir=self.temp_dir,
            profile_memory=True,
            profile_cpu=True
        )
        
        assert profiler.output_dir == self.temp_dir
        assert profiler.profile_memory is True
        assert profiler.profile_cpu is True
    
    def test_profiler_context_manager(self):
        """Test profiler works as context manager."""
        from beginnings.cli.debug.profiler import PerformanceProfiler
        
        profiler = PerformanceProfiler(output_dir=self.temp_dir)
        
        with profiler.profile("test_operation"):
            # Simulate some work
            time.sleep(0.01)
        
        # Check that profile was recorded
        profiles = profiler.get_profiles()
        assert len(profiles) > 0
        assert "test_operation" in [p["name"] for p in profiles]
    
    def test_profiler_memory_tracking(self):
        """Test profiler tracks memory usage."""
        from beginnings.cli.debug.profiler import PerformanceProfiler
        
        profiler = PerformanceProfiler(
            output_dir=self.temp_dir,
            profile_memory=True
        )
        
        with profiler.profile("memory_test"):
            # Allocate some memory
            data = [i for i in range(1000)]
        
        profiles = profiler.get_profiles()
        memory_profile = next(p for p in profiles if p["name"] == "memory_test")
        
        assert "memory_usage" in memory_profile
        assert memory_profile["memory_usage"]["peak_mb"] > 0
    
    def test_profiler_cpu_timing(self):
        """Test profiler tracks CPU timing."""
        from beginnings.cli.debug.profiler import PerformanceProfiler
        
        profiler = PerformanceProfiler(
            output_dir=self.temp_dir,
            profile_cpu=True
        )
        
        with profiler.profile("cpu_test"):
            # Simulate CPU work
            sum(i * i for i in range(1000))
        
        profiles = profiler.get_profiles()
        cpu_profile = next(p for p in profiles if p["name"] == "cpu_test")
        
        assert "timing" in cpu_profile
        assert cpu_profile["timing"]["duration_ms"] > 0
    
    def test_profiler_export_formats(self):
        """Test profiler can export different formats."""
        from beginnings.cli.debug.profiler import PerformanceProfiler
        
        profiler = PerformanceProfiler(output_dir=self.temp_dir)
        
        with profiler.profile("export_test"):
            time.sleep(0.01)
        
        # Export as JSON
        json_file = os.path.join(self.temp_dir, "profile.json")
        profiler.export_json(json_file)
        assert os.path.exists(json_file)
        
        # Verify JSON content
        with open(json_file) as f:
            data = json.load(f)
        assert "profiles" in data
        assert len(data["profiles"]) > 0
        
        # Export as HTML report
        html_file = os.path.join(self.temp_dir, "profile.html")
        profiler.export_html(html_file)
        assert os.path.exists(html_file)


class TestDebugMiddleware:
    """Test debug middleware for request tracking."""
    
    def test_debug_middleware_initialization(self):
        """Test debug middleware can be initialized."""
        from beginnings.cli.debug.middleware import DebugMiddleware
        
        middleware = DebugMiddleware(
            enable_request_tracking=True,
            enable_performance_monitoring=True,
            max_request_history=100
        )
        
        assert middleware.enable_request_tracking is True
        assert middleware.enable_performance_monitoring is True
        assert middleware.max_request_history == 100
    
    def test_debug_middleware_request_tracking(self):
        """Test debug middleware tracks requests."""
        from beginnings.cli.debug.middleware import DebugMiddleware
        
        middleware = DebugMiddleware(enable_request_tracking=True)
        
        # Mock request and response
        mock_request = MagicMock()
        mock_request.path = "/api/test"
        mock_request.method = "GET"
        mock_request.headers = {"user-agent": "test"}
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        
        # Process request
        middleware.before_request(mock_request)
        middleware.after_request(mock_request, mock_response)
        
        # Check request was tracked
        requests = middleware.get_tracked_requests()
        assert len(requests) == 1
        assert requests[0]["path"] == "/api/test"
        assert requests[0]["method"] == "GET"
        assert requests[0]["status_code"] == 200
    
    def test_debug_middleware_performance_monitoring(self):
        """Test debug middleware monitors performance."""
        from beginnings.cli.debug.middleware import DebugMiddleware
        
        middleware = DebugMiddleware(enable_performance_monitoring=True)
        
        mock_request = MagicMock()
        mock_request.path = "/slow-endpoint"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # Simulate request processing with delay
        middleware.before_request(mock_request)
        time.sleep(0.01)  # Small delay
        middleware.after_request(mock_request, mock_response)
        
        # Check performance was monitored
        metrics = middleware.get_performance_metrics()
        assert len(metrics) == 1
        assert metrics[0]["path"] == "/slow-endpoint"
        assert metrics[0]["duration_ms"] > 0
    
    def test_debug_middleware_error_tracking(self):
        """Test debug middleware tracks errors."""
        from beginnings.cli.debug.middleware import DebugMiddleware
        
        middleware = DebugMiddleware()
        
        mock_request = MagicMock()
        mock_request.path = "/error-endpoint"
        
        # Simulate error during request
        test_error = ValueError("Test error")
        middleware.on_error(mock_request, test_error)
        
        # Check error was tracked
        errors = middleware.get_tracked_errors()
        assert len(errors) == 1
        assert errors[0]["path"] == "/error-endpoint"
        assert errors[0]["error_type"] == "ValueError"
        assert errors[0]["error_message"] == "Test error"


class TestDebugConfiguration:
    """Test debug configuration options."""
    
    def test_debug_config_from_dict(self):
        """Test loading debug configuration from dictionary."""
        from beginnings.cli.debug.config import DebugConfig
        
        config_data = {
            "debug": {
                "enabled": True,
                "dashboard": {
                    "host": "0.0.0.0",
                    "port": 8080,
                    "enable_profiler": True,
                    "enable_request_tracking": True
                },
                "logging": {
                    "level": "DEBUG",
                    "max_lines": 1000,
                    "enable_websocket_streaming": True
                },
                "profiling": {
                    "enable_cpu_profiling": True,
                    "enable_memory_profiling": True,
                    "profile_threshold_ms": 100
                }
            }
        }
        
        debug_config = DebugConfig.from_dict(config_data)
        
        assert debug_config.enabled is True
        assert debug_config.dashboard_host == "0.0.0.0"
        assert debug_config.dashboard_port == 8080
        assert debug_config.enable_profiler is True
        assert debug_config.log_level == "DEBUG"
        assert debug_config.max_log_lines == 1000
        assert debug_config.enable_cpu_profiling is True
        assert debug_config.profile_threshold_ms == 100
    
    def test_debug_config_defaults(self):
        """Test debug configuration with default values."""
        from beginnings.cli.debug.config import DebugConfig
        
        debug_config = DebugConfig()
        
        assert debug_config.enabled is False  # Default disabled
        assert debug_config.dashboard_host == "127.0.0.1"
        assert debug_config.dashboard_port == 8000
        assert debug_config.enable_profiler is False
        assert debug_config.log_level == "INFO"
        assert debug_config.max_log_lines == 500
        assert debug_config.profile_threshold_ms == 50
    
    def test_debug_config_validation(self):
        """Test debug configuration validation."""
        from beginnings.cli.debug.config import DebugConfig
        
        # Test invalid port
        with pytest.raises(ValueError, match="port must be between"):
            DebugConfig(dashboard_port=70000)
        
        # Test invalid log level
        with pytest.raises(ValueError, match="Invalid log level"):
            DebugConfig(log_level="INVALID")
        
        # Test invalid threshold
        with pytest.raises(ValueError, match="profile_threshold_ms must be positive"):
            DebugConfig(profile_threshold_ms=-1)


class TestDebugIntegration:
    """Test debug system integration with framework."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_extension_registration(self):
        """Test debug extension can be registered with framework."""
        from beginnings.cli.debug.extension import DebugExtension
        
        extension = DebugExtension()
        
        # Mock app instance
        mock_app = MagicMock()
        
        # Register extension
        extension.init_app(mock_app)
        
        # Verify middleware was added
        assert mock_app.add_middleware.called
        
        # Verify routes were registered
        assert mock_app.add_route.called
    
    def test_debug_extension_with_config(self):
        """Test debug extension with configuration."""
        from beginnings.cli.debug.extension import DebugExtension
        from beginnings.cli.debug.config import DebugConfig
        
        config = DebugConfig(
            enabled=True,
            enable_profiler=True,
            enable_request_tracking=True
        )
        
        extension = DebugExtension(config=config)
        mock_app = MagicMock()
        
        extension.init_app(mock_app)
        
        # Verify configuration was applied
        assert extension.config.enabled is True
        assert extension.config.enable_profiler is True
    
    def test_debug_dashboard_integration(self):
        """Test debug dashboard integrates with application."""
        from beginnings.cli.debug.dashboard import DebugDashboard
        
        dashboard = DebugDashboard()
        
        # Mock application monitoring
        mock_app_process = MagicMock()
        dashboard.monitor_app = mock_app_process
        
        # Start monitoring
        dashboard.start_monitoring()
        
        # Verify monitoring started
        assert dashboard.monitoring_active is True
        
        # Stop monitoring
        dashboard.stop_monitoring()
        assert dashboard.monitoring_active is False