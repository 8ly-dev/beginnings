"""Automatic performance bottleneck detection and analysis."""

from __future__ import annotations

import time
import statistics
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, deque
from threading import RLock
from dataclasses import dataclass
from enum import Enum


class BottleneckType(Enum):
    """Types of performance bottlenecks."""
    SLOW_MIDDLEWARE = "slow_middleware"
    SLOW_ROUTE = "slow_route"
    HIGH_ERROR_RATE = "high_error_rate"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    DATABASE_SLOW = "database_slow"
    TEMPLATE_RENDERING = "template_rendering"
    EXTENSION_CONFLICT = "extension_conflict"


@dataclass
class BottleneckAlert:
    """Represents a detected performance bottleneck."""
    type: BottleneckType
    severity: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    affected_component: str
    detected_at: float
    metrics: Dict[str, Any]
    recommendations: List[str]
    auto_fixable: bool = False


class PerformanceAnalyzer:
    """Analyzes performance data to detect bottlenecks."""
    
    def __init__(self, analysis_window_seconds: int = 300):
        """Initialize performance analyzer.
        
        Args:
            analysis_window_seconds: Time window for analysis in seconds
        """
        self.analysis_window = analysis_window_seconds
        self._lock = RLock()
        
        # Performance thresholds
        self.thresholds = {
            "slow_request_ms": 1000,  # Requests slower than 1 second
            "very_slow_request_ms": 5000,  # Requests slower than 5 seconds
            "high_error_rate_percent": 5.0,  # Error rate above 5%
            "critical_error_rate_percent": 15.0,  # Error rate above 15%
            "memory_growth_mb_per_min": 10.0,  # Memory growth over 10MB/min
            "high_cpu_percent": 80.0,  # CPU usage above 80%
            "critical_cpu_percent": 95.0,  # CPU usage above 95%
        }
        
        # Data storage for analysis
        self._request_data = deque(maxlen=10000)
        self._memory_samples = deque(maxlen=1000)
        self._cpu_samples = deque(maxlen=1000)
        self._error_data = deque(maxlen=1000)
        
        # Component performance tracking
        self._middleware_performance: Dict[str, List[float]] = defaultdict(list)
        self._route_performance: Dict[str, List[float]] = defaultdict(list)
        self._extension_performance: Dict[str, List[float]] = defaultdict(list)
    
    def record_request(
        self, 
        path: str, 
        method: str, 
        duration_ms: float, 
        status_code: int,
        middleware_timings: Dict[str, float] = None,
        route_handler: str = None,
        memory_usage_mb: float = None
    ) -> None:
        """Record request performance data.
        
        Args:
            path: Request path
            method: HTTP method
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            middleware_timings: Timing data for individual middleware
            route_handler: Route handler name
            memory_usage_mb: Memory usage during request
        """
        with self._lock:
            request_data = {
                "timestamp": time.time(),
                "path": path,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "middleware_timings": middleware_timings or {},
                "route_handler": route_handler,
                "memory_usage_mb": memory_usage_mb
            }
            
            self._request_data.append(request_data)
            
            # Track middleware performance
            if middleware_timings:
                for middleware_name, timing in middleware_timings.items():
                    self._middleware_performance[middleware_name].append(timing)
                    # Keep only recent data
                    if len(self._middleware_performance[middleware_name]) > 1000:
                        self._middleware_performance[middleware_name] = self._middleware_performance[middleware_name][-500:]
            
            # Track route performance
            if route_handler:
                route_key = f"{method} {path}"
                self._route_performance[route_key].append(duration_ms)
                if len(self._route_performance[route_key]) > 1000:
                    self._route_performance[route_key] = self._route_performance[route_key][-500:]
            
            # Track errors
            if status_code >= 400:
                self._error_data.append({
                    "timestamp": time.time(),
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": duration_ms
                })
    
    def record_system_metrics(self, cpu_percent: float, memory_mb: float) -> None:
        """Record system performance metrics.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
        """
        with self._lock:
            current_time = time.time()
            
            self._cpu_samples.append({
                "timestamp": current_time,
                "cpu_percent": cpu_percent
            })
            
            self._memory_samples.append({
                "timestamp": current_time,
                "memory_mb": memory_mb
            })
    
    def analyze_bottlenecks(self) -> List[BottleneckAlert]:
        """Analyze current data for performance bottlenecks.
        
        Returns:
            List of detected bottleneck alerts
        """
        with self._lock:
            alerts = []
            current_time = time.time()
            cutoff_time = current_time - self.analysis_window
            
            # Analyze recent data only
            recent_requests = [r for r in self._request_data if r["timestamp"] >= cutoff_time]
            recent_memory = [m for m in self._memory_samples if m["timestamp"] >= cutoff_time]
            recent_cpu = [c for c in self._cpu_samples if c["timestamp"] >= cutoff_time]
            recent_errors = [e for e in self._error_data if e["timestamp"] >= cutoff_time]
            
            # Detect slow requests
            alerts.extend(self._detect_slow_requests(recent_requests))
            
            # Detect high error rates
            alerts.extend(self._detect_high_error_rates(recent_requests, recent_errors))
            
            # Detect middleware bottlenecks
            alerts.extend(self._detect_slow_middleware())
            
            # Detect route bottlenecks
            alerts.extend(self._detect_slow_routes())
            
            # Detect memory issues
            alerts.extend(self._detect_memory_issues(recent_memory))
            
            # Detect CPU issues
            alerts.extend(self._detect_cpu_issues(recent_cpu))
            
            # Detect template rendering issues
            alerts.extend(self._detect_template_issues(recent_requests))
            
            return alerts
    
    def _detect_slow_requests(self, requests: List[Dict[str, Any]]) -> List[BottleneckAlert]:
        """Detect slow request patterns."""
        alerts = []
        
        if not requests:
            return alerts
        
        durations = [r["duration_ms"] for r in requests]
        avg_duration = statistics.mean(durations)
        p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations)
        
        # Check for generally slow requests
        if avg_duration > self.thresholds["slow_request_ms"]:
            severity = "high" if avg_duration > self.thresholds["very_slow_request_ms"] else "medium"
            
            alerts.append(BottleneckAlert(
                type=BottleneckType.SLOW_ROUTE,
                severity=severity,
                title="Slow Request Performance",
                description=f"Average request time is {avg_duration:.1f}ms, which exceeds the {self.thresholds['slow_request_ms']}ms threshold",
                affected_component="Overall Application",
                detected_at=time.time(),
                metrics={
                    "avg_duration_ms": avg_duration,
                    "p95_duration_ms": p95_duration,
                    "total_requests": len(requests),
                    "threshold_ms": self.thresholds["slow_request_ms"]
                },
                recommendations=[
                    "Profile slow endpoints to identify bottlenecks",
                    "Optimize database queries",
                    "Review middleware performance",
                    "Consider caching strategies",
                    "Check for blocking I/O operations"
                ]
            ))
        
        return alerts
    
    def _detect_high_error_rates(
        self, 
        requests: List[Dict[str, Any]], 
        errors: List[Dict[str, Any]]
    ) -> List[BottleneckAlert]:
        """Detect high error rate patterns."""
        alerts = []
        
        if not requests:
            return alerts
        
        total_requests = len(requests)
        error_count = len(errors)
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        if error_rate > self.thresholds["high_error_rate_percent"]:
            severity = "critical" if error_rate > self.thresholds["critical_error_rate_percent"] else "high"
            
            # Analyze error patterns
            error_codes = defaultdict(int)
            error_paths = defaultdict(int)
            
            for error in errors:
                error_codes[error["status_code"]] += 1
                error_paths[error["path"]] += 1
            
            most_common_code = max(error_codes.items(), key=lambda x: x[1]) if error_codes else (None, 0)
            most_common_path = max(error_paths.items(), key=lambda x: x[1]) if error_paths else (None, 0)
            
            alerts.append(BottleneckAlert(
                type=BottleneckType.HIGH_ERROR_RATE,
                severity=severity,
                title=f"High Error Rate: {error_rate:.1f}%",
                description=f"Error rate of {error_rate:.1f}% exceeds threshold of {self.thresholds['high_error_rate_percent']}%",
                affected_component="Error Handling",
                detected_at=time.time(),
                metrics={
                    "error_rate_percent": error_rate,
                    "total_requests": total_requests,
                    "error_count": error_count,
                    "most_common_error_code": most_common_code[0],
                    "most_common_error_path": most_common_path[0],
                    "error_code_distribution": dict(error_codes),
                    "error_path_distribution": dict(error_paths)
                },
                recommendations=[
                    "Review application logs for error patterns",
                    "Check input validation and error handling",
                    "Verify external service dependencies",
                    "Monitor database connection health",
                    "Review recent configuration changes"
                ]
            ))
        
        return alerts
    
    def _detect_slow_middleware(self) -> List[BottleneckAlert]:
        """Detect slow middleware components."""
        alerts = []
        
        for middleware_name, timings in self._middleware_performance.items():
            if len(timings) < 10:  # Need sufficient data
                continue
            
            avg_timing = statistics.mean(timings)
            p95_timing = statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else max(timings)
            
            # Consider middleware slow if it consistently takes more than 100ms
            if avg_timing > 100:
                severity = "high" if avg_timing > 500 else "medium"
                
                alerts.append(BottleneckAlert(
                    type=BottleneckType.SLOW_MIDDLEWARE,
                    severity=severity,
                    title=f"Slow Middleware: {middleware_name}",
                    description=f"Middleware '{middleware_name}' has average execution time of {avg_timing:.1f}ms",
                    affected_component=middleware_name,
                    detected_at=time.time(),
                    metrics={
                        "avg_timing_ms": avg_timing,
                        "p95_timing_ms": p95_timing,
                        "sample_count": len(timings),
                        "max_timing_ms": max(timings),
                        "min_timing_ms": min(timings)
                    },
                    recommendations=[
                        f"Profile {middleware_name} middleware for bottlenecks",
                        "Check for blocking database queries in middleware",
                        "Review middleware configuration for optimization",
                        "Consider caching in middleware if applicable",
                        "Verify middleware dependencies are healthy"
                    ]
                ))
        
        return alerts
    
    def _detect_slow_routes(self) -> List[BottleneckAlert]:
        """Detect slow route handlers."""
        alerts = []
        
        for route_key, timings in self._route_performance.items():
            if len(timings) < 5:  # Need sufficient data
                continue
            
            avg_timing = statistics.mean(timings)
            p95_timing = statistics.quantiles(timings, n=20)[18] if len(timings) >= 20 else max(timings)
            
            # Consider route slow if it consistently takes more than 1 second
            if avg_timing > 1000:
                severity = "high" if avg_timing > 3000 else "medium"
                
                alerts.append(BottleneckAlert(
                    type=BottleneckType.SLOW_ROUTE,
                    severity=severity,
                    title=f"Slow Route: {route_key}",
                    description=f"Route '{route_key}' has average response time of {avg_timing:.1f}ms",
                    affected_component=route_key,
                    detected_at=time.time(),
                    metrics={
                        "avg_response_time_ms": avg_timing,
                        "p95_response_time_ms": p95_timing,
                        "request_count": len(timings),
                        "max_response_time_ms": max(timings),
                        "min_response_time_ms": min(timings)
                    },
                    recommendations=[
                        f"Profile route handler for {route_key}",
                        "Optimize database queries in route handler",
                        "Review business logic for performance",
                        "Consider implementing caching",
                        "Check for N+1 query problems"
                    ]
                ))
        
        return alerts
    
    def _detect_memory_issues(self, memory_samples: List[Dict[str, Any]]) -> List[BottleneckAlert]:
        """Detect memory-related issues."""
        alerts = []
        
        if len(memory_samples) < 10:
            return alerts
        
        # Calculate memory growth rate
        if len(memory_samples) >= 2:
            first_sample = memory_samples[0]
            last_sample = memory_samples[-1]
            time_diff_minutes = (last_sample["timestamp"] - first_sample["timestamp"]) / 60
            memory_diff_mb = last_sample["memory_mb"] - first_sample["memory_mb"]
            
            if time_diff_minutes > 0:
                growth_rate_mb_per_min = memory_diff_mb / time_diff_minutes
                
                if growth_rate_mb_per_min > self.thresholds["memory_growth_mb_per_min"]:
                    alerts.append(BottleneckAlert(
                        type=BottleneckType.MEMORY_LEAK,
                        severity="high",
                        title="Potential Memory Leak",
                        description=f"Memory usage growing at {growth_rate_mb_per_min:.1f}MB/min",
                        affected_component="Memory Management",
                        detected_at=time.time(),
                        metrics={
                            "growth_rate_mb_per_min": growth_rate_mb_per_min,
                            "current_memory_mb": last_sample["memory_mb"],
                            "initial_memory_mb": first_sample["memory_mb"],
                            "time_window_minutes": time_diff_minutes
                        },
                        recommendations=[
                            "Review code for memory leaks",
                            "Check for unclosed resources",
                            "Monitor object creation patterns",
                            "Use memory profiling tools",
                            "Review caching strategies"
                        ]
                    ))
        
        return alerts
    
    def _detect_cpu_issues(self, cpu_samples: List[Dict[str, Any]]) -> List[BottleneckAlert]:
        """Detect CPU-related issues."""
        alerts = []
        
        if len(cpu_samples) < 5:
            return alerts
        
        cpu_values = [sample["cpu_percent"] for sample in cpu_samples]
        avg_cpu = statistics.mean(cpu_values)
        max_cpu = max(cpu_values)
        
        if avg_cpu > self.thresholds["high_cpu_percent"]:
            severity = "critical" if avg_cpu > self.thresholds["critical_cpu_percent"] else "high"
            
            alerts.append(BottleneckAlert(
                type=BottleneckType.CPU_SPIKE,
                severity=severity,
                title=f"High CPU Usage: {avg_cpu:.1f}%",
                description=f"Average CPU usage of {avg_cpu:.1f}% exceeds threshold",
                affected_component="CPU",
                detected_at=time.time(),
                metrics={
                    "avg_cpu_percent": avg_cpu,
                    "max_cpu_percent": max_cpu,
                    "sample_count": len(cpu_samples),
                    "threshold_percent": self.thresholds["high_cpu_percent"]
                },
                recommendations=[
                    "Profile application for CPU-intensive operations",
                    "Review algorithmic complexity of hot code paths",
                    "Check for infinite loops or excessive computation",
                    "Consider optimizing database queries",
                    "Review concurrent processing patterns"
                ]
            ))
        
        return alerts
    
    def _detect_template_issues(self, requests: List[Dict[str, Any]]) -> List[BottleneckAlert]:
        """Detect template rendering performance issues."""
        alerts = []
        
        # Look for patterns that suggest template rendering issues
        html_requests = [r for r in requests if "text/html" in str(r.get("response_headers", {}))]
        
        if not html_requests:
            return alerts
        
        html_durations = [r["duration_ms"] for r in html_requests]
        avg_html_duration = statistics.mean(html_durations)
        
        # Compare HTML response times to API response times
        api_requests = [r for r in requests if r["path"].startswith("/api")]
        if api_requests:
            api_durations = [r["duration_ms"] for r in api_requests]
            avg_api_duration = statistics.mean(api_durations)
            
            # If HTML requests are significantly slower than API requests
            if avg_html_duration > avg_api_duration * 2 and avg_html_duration > 500:
                alerts.append(BottleneckAlert(
                    type=BottleneckType.TEMPLATE_RENDERING,
                    severity="medium",
                    title="Slow Template Rendering",
                    description=f"HTML responses ({avg_html_duration:.1f}ms) significantly slower than API responses ({avg_api_duration:.1f}ms)",
                    affected_component="Template Engine",
                    detected_at=time.time(),
                    metrics={
                        "avg_html_duration_ms": avg_html_duration,
                        "avg_api_duration_ms": avg_api_duration,
                        "html_request_count": len(html_requests),
                        "api_request_count": len(api_requests)
                    },
                    recommendations=[
                        "Profile template rendering performance",
                        "Optimize template complexity",
                        "Implement template caching",
                        "Review template context data size",
                        "Consider template pre-compilation"
                    ]
                ))
        
        return alerts


class BottleneckDetector:
    """Main bottleneck detection system."""
    
    def __init__(self, analysis_interval_seconds: int = 60):
        """Initialize bottleneck detector.
        
        Args:
            analysis_interval_seconds: How often to run analysis
        """
        self.analysis_interval = analysis_interval_seconds
        self.analyzer = PerformanceAnalyzer()
        
        self._lock = RLock()
        self._recent_alerts: List[BottleneckAlert] = []
        self._alert_history: List[BottleneckAlert] = []
        self._alert_listeners: Set[Callable[[BottleneckAlert], None]] = set()
        
        # Tracking for alert suppression
        self._alert_counts: Dict[str, int] = defaultdict(int)
        self._last_alert_times: Dict[str, float] = {}
        
        # Auto-fix capabilities
        self._auto_fix_enabled = True
        self._auto_fix_history: List[Dict[str, Any]] = []
    
    def record_request_data(self, **kwargs) -> None:
        """Record request data for analysis."""
        self.analyzer.record_request(**kwargs)
    
    def record_system_metrics(self, cpu_percent: float, memory_mb: float) -> None:
        """Record system metrics for analysis."""
        self.analyzer.record_system_metrics(cpu_percent, memory_mb)
    
    def add_alert_listener(self, listener: Callable[[BottleneckAlert], None]) -> None:
        """Add listener for bottleneck alerts."""
        with self._lock:
            self._alert_listeners.add(listener)
    
    def remove_alert_listener(self, listener: Callable[[BottleneckAlert], None]) -> None:
        """Remove alert listener."""
        with self._lock:
            self._alert_listeners.discard(listener)
    
    def run_analysis(self) -> List[BottleneckAlert]:
        """Run bottleneck analysis and return new alerts."""
        alerts = self.analyzer.analyze_bottlenecks()
        
        with self._lock:
            new_alerts = []
            current_time = time.time()
            
            for alert in alerts:
                alert_key = f"{alert.type.value}:{alert.affected_component}"
                
                # Check if we should suppress this alert (avoid spam)
                last_alert_time = self._last_alert_times.get(alert_key, 0)
                if current_time - last_alert_time < 300:  # 5 minutes suppression
                    continue
                
                # Update alert tracking
                self._alert_counts[alert_key] += 1
                self._last_alert_times[alert_key] = current_time
                
                new_alerts.append(alert)
                self._recent_alerts.append(alert)
                self._alert_history.append(alert)
                
                # Notify listeners
                for listener in self._alert_listeners.copy():
                    try:
                        listener(alert)
                    except Exception:
                        self._alert_listeners.discard(listener)
                
                # Attempt auto-fix if enabled
                if self._auto_fix_enabled and alert.auto_fixable:
                    self._attempt_auto_fix(alert)
            
            # Clean up old alerts
            cutoff_time = current_time - 3600  # Keep alerts for 1 hour
            self._recent_alerts = [a for a in self._recent_alerts if a.detected_at >= cutoff_time]
            
            # Keep alert history manageable
            if len(self._alert_history) > 1000:
                self._alert_history = self._alert_history[-500:]
            
            return new_alerts
    
    def get_recent_alerts(self, severity_filter: Optional[str] = None) -> List[BottleneckAlert]:
        """Get recent alerts, optionally filtered by severity."""
        with self._lock:
            if severity_filter:
                return [a for a in self._recent_alerts if a.severity == severity_filter]
            return list(self._recent_alerts)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert statistics."""
        with self._lock:
            recent_count_by_severity = defaultdict(int)
            recent_count_by_type = defaultdict(int)
            
            for alert in self._recent_alerts:
                recent_count_by_severity[alert.severity] += 1
                recent_count_by_type[alert.type.value] += 1
            
            return {
                "total_recent_alerts": len(self._recent_alerts),
                "total_historical_alerts": len(self._alert_history),
                "alerts_by_severity": dict(recent_count_by_severity),
                "alerts_by_type": dict(recent_count_by_type),
                "auto_fix_enabled": self._auto_fix_enabled,
                "auto_fixes_applied": len(self._auto_fix_history)
            }
    
    def _attempt_auto_fix(self, alert: BottleneckAlert) -> None:
        """Attempt to automatically fix a bottleneck (placeholder)."""
        # This is a placeholder for auto-fix functionality
        # In a real implementation, this would contain specific fixes
        # for different types of bottlenecks
        
        fix_applied = False
        fix_description = "No auto-fix available"
        
        # Example auto-fixes (these would be implemented based on alert type)
        if alert.type == BottleneckType.HIGH_ERROR_RATE:
            # Could implement circuit breaker activation
            fix_description = "Circuit breaker activated to prevent cascade failures"
            fix_applied = True
        
        # Record auto-fix attempt
        self._auto_fix_history.append({
            "timestamp": time.time(),
            "alert_type": alert.type.value,
            "alert_component": alert.affected_component,
            "fix_applied": fix_applied,
            "fix_description": fix_description
        })
    
    def enable_auto_fix(self) -> None:
        """Enable automatic fix attempts."""
        self._auto_fix_enabled = True
    
    def disable_auto_fix(self) -> None:
        """Disable automatic fix attempts."""
        self._auto_fix_enabled = False