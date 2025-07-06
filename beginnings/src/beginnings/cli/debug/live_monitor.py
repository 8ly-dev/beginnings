"""Live monitoring components for real-time debug dashboard updates."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable, Set
from threading import Thread, Event, RLock
from collections import deque

from .middleware import DebugMiddleware


class LiveMetricsCollector:
    """Collects real-time metrics for the debug dashboard."""
    
    def __init__(self, max_data_points: int = 1000):
        """Initialize live metrics collector.
        
        Args:
            max_data_points: Maximum number of data points to keep
        """
        self.max_data_points = max_data_points
        self._lock = RLock()
        
        # Time-series data storage
        self._request_rates = deque(maxlen=max_data_points)  # Requests per second
        self._response_times = deque(maxlen=max_data_points)  # Average response times
        self._error_rates = deque(maxlen=max_data_points)  # Error rates
        self._memory_usage = deque(maxlen=max_data_points)  # Memory usage samples
        self._cpu_usage = deque(maxlen=max_data_points)  # CPU usage samples
        
        # Current metrics
        self._current_request_count = 0
        self._current_error_count = 0
        self._last_sample_time = time.time()
        
        # Listeners for real-time updates
        self._listeners: Set[Callable[[Dict[str, Any]], None]] = set()
    
    def add_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Add a listener for real-time metric updates.
        
        Args:
            listener: Callback function that receives metric updates
        """
        with self._lock:
            self._listeners.add(listener)
    
    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a listener for real-time metric updates.
        
        Args:
            listener: Callback function to remove
        """
        with self._lock:
            self._listeners.discard(listener)
    
    def record_request(self, duration_ms: float, status_code: int) -> None:
        """Record a request for metrics collection.
        
        Args:
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
        """
        with self._lock:
            self._current_request_count += 1
            
            if status_code >= 400:
                self._current_error_count += 1
            
            # Add to response time tracking
            current_time = time.time()
            self._response_times.append({
                "timestamp": current_time,
                "duration_ms": duration_ms,
                "status_code": status_code
            })
    
    def sample_system_metrics(self) -> None:
        """Sample system metrics (CPU, memory, etc.)."""
        try:
            import psutil
            
            current_time = time.time()
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            memory_usage_mb = memory_info.used / (1024 * 1024)
            
            with self._lock:
                self._cpu_usage.append({
                    "timestamp": current_time,
                    "cpu_percent": cpu_percent
                })
                
                self._memory_usage.append({
                    "timestamp": current_time,
                    "memory_mb": memory_usage_mb,
                    "memory_percent": memory_info.percent
                })
                
        except ImportError:
            # psutil not available, skip system metrics
            pass
    
    def calculate_rates(self) -> Dict[str, float]:
        """Calculate current rates (requests/sec, errors/sec).
        
        Returns:
            Dictionary with calculated rates
        """
        with self._lock:
            current_time = time.time()
            time_elapsed = current_time - self._last_sample_time
            
            if time_elapsed <= 0:
                return {"requests_per_second": 0.0, "errors_per_second": 0.0}
            
            request_rate = self._current_request_count / time_elapsed
            error_rate = self._current_error_count / time_elapsed
            
            # Store rates
            self._request_rates.append({
                "timestamp": current_time,
                "requests_per_second": request_rate
            })
            
            self._error_rates.append({
                "timestamp": current_time,
                "errors_per_second": error_rate
            })
            
            # Reset counters
            self._current_request_count = 0
            self._current_error_count = 0
            self._last_sample_time = current_time
            
            return {
                "requests_per_second": request_rate,
                "errors_per_second": error_rate
            }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary.
        
        Returns:
            Dictionary with current metrics
        """
        with self._lock:
            rates = self.calculate_rates()
            
            # Calculate averages
            avg_response_time = 0.0
            if self._response_times:
                recent_times = list(self._response_times)[-100:]  # Last 100 requests
                avg_response_time = sum(r["duration_ms"] for r in recent_times) / len(recent_times)
            
            current_cpu = 0.0
            current_memory = 0.0
            if self._cpu_usage:
                current_cpu = self._cpu_usage[-1]["cpu_percent"]
            if self._memory_usage:
                current_memory = self._memory_usage[-1]["memory_mb"]
            
            return {
                "timestamp": time.time(),
                "requests_per_second": rates["requests_per_second"],
                "errors_per_second": rates["errors_per_second"],
                "avg_response_time_ms": avg_response_time,
                "current_cpu_percent": current_cpu,
                "current_memory_mb": current_memory,
                "total_data_points": {
                    "request_rates": len(self._request_rates),
                    "response_times": len(self._response_times),
                    "error_rates": len(self._error_rates),
                    "cpu_usage": len(self._cpu_usage),
                    "memory_usage": len(self._memory_usage)
                }
            }
    
    def get_time_series_data(self, metric_type: str, duration_seconds: int = 300) -> List[Dict[str, Any]]:
        """Get time series data for a specific metric.
        
        Args:
            metric_type: Type of metric ("request_rates", "response_times", "error_rates", "cpu_usage", "memory_usage")
            duration_seconds: How far back to look in seconds
            
        Returns:
            List of data points for the specified metric
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - duration_seconds
            
            data_source = None
            if metric_type == "request_rates":
                data_source = self._request_rates
            elif metric_type == "response_times":
                data_source = self._response_times
            elif metric_type == "error_rates":
                data_source = self._error_rates
            elif metric_type == "cpu_usage":
                data_source = self._cpu_usage
            elif metric_type == "memory_usage":
                data_source = self._memory_usage
            else:
                return []
            
            # Filter data by time range
            filtered_data = [
                data_point for data_point in data_source
                if data_point["timestamp"] >= cutoff_time
            ]
            
            return filtered_data
    
    def notify_listeners(self, metrics: Dict[str, Any]) -> None:
        """Notify all listeners of metric updates.
        
        Args:
            metrics: Metrics data to send to listeners
        """
        with self._lock:
            for listener in self._listeners.copy():  # Copy to avoid modification during iteration
                try:
                    listener(metrics)
                except Exception:
                    # Remove broken listeners
                    self._listeners.discard(listener)


class ConfigurationMonitor:
    """Monitors configuration changes in real-time."""
    
    def __init__(self, config_paths: List[str] = None):
        """Initialize configuration monitor.
        
        Args:
            config_paths: List of configuration file paths to monitor
        """
        self.config_paths = config_paths or []
        self._lock = RLock()
        self._file_mtimes: Dict[str, float] = {}
        self._last_configs: Dict[str, Dict[str, Any]] = {}
        self._change_listeners: Set[Callable[[str, Dict[str, Any], Dict[str, Any]], None]] = set()
        
        # Initialize file modification times
        self._update_file_mtimes()
    
    def add_config_path(self, path: str) -> None:
        """Add a configuration file path to monitor.
        
        Args:
            path: Path to configuration file
        """
        with self._lock:
            if path not in self.config_paths:
                self.config_paths.append(path)
                self._update_file_mtimes()
    
    def add_change_listener(self, listener: Callable[[str, Dict[str, Any], Dict[str, Any]], None]) -> None:
        """Add a listener for configuration changes.
        
        Args:
            listener: Callback function that receives (path, old_config, new_config)
        """
        with self._lock:
            self._change_listeners.add(listener)
    
    def remove_change_listener(self, listener: Callable[[str, Dict[str, Any], Dict[str, Any]], None]) -> None:
        """Remove a configuration change listener.
        
        Args:
            listener: Callback function to remove
        """
        with self._lock:
            self._change_listeners.discard(listener)
    
    def check_for_changes(self) -> List[Dict[str, Any]]:
        """Check for configuration file changes.
        
        Returns:
            List of change events
        """
        changes = []
        
        with self._lock:
            for path in self.config_paths:
                try:
                    import os
                    import yaml
                    
                    if not os.path.exists(path):
                        continue
                    
                    current_mtime = os.path.getmtime(path)
                    previous_mtime = self._file_mtimes.get(path, 0)
                    
                    if current_mtime > previous_mtime:
                        # File has been modified
                        self._file_mtimes[path] = current_mtime
                        
                        # Load new configuration
                        try:
                            with open(path, 'r') as f:
                                new_config = yaml.safe_load(f)
                            
                            old_config = self._last_configs.get(path, {})
                            self._last_configs[path] = new_config
                            
                            change_event = {
                                "path": path,
                                "old_config": old_config,
                                "new_config": new_config,
                                "timestamp": current_mtime,
                                "change_type": "modified"
                            }
                            
                            changes.append(change_event)
                            
                            # Notify listeners
                            for listener in self._change_listeners.copy():
                                try:
                                    listener(path, old_config, new_config)
                                except Exception:
                                    self._change_listeners.discard(listener)
                        
                        except Exception as e:
                            # Configuration file is invalid
                            change_event = {
                                "path": path,
                                "error": str(e),
                                "timestamp": current_mtime,
                                "change_type": "error"
                            }
                            changes.append(change_event)
                
                except Exception:
                    # Error accessing file
                    continue
        
        return changes
    
    def _update_file_mtimes(self) -> None:
        """Update file modification times."""
        import os
        
        for path in self.config_paths:
            try:
                if os.path.exists(path):
                    self._file_mtimes[path] = os.path.getmtime(path)
            except Exception:
                continue


class LiveMonitorManager:
    """Manages all live monitoring components."""
    
    def __init__(self, debug_middleware: Optional[DebugMiddleware] = None):
        """Initialize live monitor manager.
        
        Args:
            debug_middleware: Debug middleware instance
        """
        self.debug_middleware = debug_middleware
        
        # Initialize monitoring components
        self.metrics_collector = LiveMetricsCollector()
        self.config_monitor = ConfigurationMonitor()
        
        # Monitoring thread control
        self._monitoring_active = False
        self._monitoring_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Update interval
        self.update_interval_seconds = 1.0
    
    def start_monitoring(self) -> None:
        """Start live monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._stop_event.clear()
        
        self._monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop live monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_event.set()
        
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
    
    def set_debug_middleware(self, debug_middleware: DebugMiddleware) -> None:
        """Set debug middleware instance.
        
        Args:
            debug_middleware: Debug middleware instance
        """
        self.debug_middleware = debug_middleware
    
    def add_config_path(self, path: str) -> None:
        """Add configuration path to monitor.
        
        Args:
            path: Configuration file path
        """
        self.config_monitor.add_config_path(path)
    
    def get_live_data(self) -> Dict[str, Any]:
        """Get current live monitoring data.
        
        Returns:
            Dictionary with all live monitoring data
        """
        # Get metrics summary
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        # Get configuration changes
        config_changes = self.config_monitor.check_for_changes()
        
        # Get debug middleware data if available
        middleware_data = {}
        if self.debug_middleware:
            try:
                middleware_data = {
                    "recent_requests": self.debug_middleware.get_tracked_requests(10),
                    "recent_errors": self.debug_middleware.get_tracked_errors(5),
                    "debug_info": self.debug_middleware.get_debug_info(),
                    "timeline_count": len(self.debug_middleware.get_all_timeline_data())
                }
            except Exception:
                # Handle middleware access errors gracefully
                middleware_data = {"error": "Unable to access middleware data"}
        
        return {
            "timestamp": time.time(),
            "metrics": metrics_summary,
            "config_changes": config_changes,
            "middleware": middleware_data,
            "monitoring_active": self._monitoring_active
        }
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring_active and not self._stop_event.is_set():
            try:
                # Sample system metrics
                self.metrics_collector.sample_system_metrics()
                
                # Check for configuration changes
                self.config_monitor.check_for_changes()
                
                # Wait for next update
                self._stop_event.wait(self.update_interval_seconds)
                
            except Exception:
                # Continue monitoring even if individual updates fail
                continue