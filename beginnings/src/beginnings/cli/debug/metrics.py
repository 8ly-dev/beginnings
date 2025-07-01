"""Metrics collection for debugging dashboard."""

from __future__ import annotations

import time
from collections import deque, defaultdict
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class RequestMetric:
    """Individual request metric."""
    timestamp: float
    path: str
    method: str
    status_code: int
    duration_ms: float
    response_size: int = 0
    user_agent: str = ""
    ip_address: str = ""


@dataclass
class ErrorMetric:
    """Individual error metric."""
    timestamp: float
    error_type: str
    error_message: str
    path: str
    traceback: str = ""
    user_agent: str = ""
    ip_address: str = ""


@dataclass
class PerformanceMetric:
    """Performance metric for specific operation."""
    timestamp: float
    operation: str
    duration_ms: float
    memory_mb: float = 0
    cpu_percent: float = 0
    context: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages application metrics."""
    
    def __init__(self, max_requests: int = 1000, max_errors: int = 500, max_performance: int = 500):
        """Initialize metrics collector.
        
        Args:
            max_requests: Maximum request metrics to keep
            max_errors: Maximum error metrics to keep
            max_performance: Maximum performance metrics to keep
        """
        self.max_requests = max_requests
        self.max_errors = max_errors
        self.max_performance = max_performance
        
        # Thread-safe collections
        self._lock = RLock()
        self._requests: deque[RequestMetric] = deque(maxlen=max_requests)
        self._errors: deque[ErrorMetric] = deque(maxlen=max_errors)
        self._performance: deque[PerformanceMetric] = deque(maxlen=max_performance)
        
        # Aggregated statistics
        self._request_counts = defaultdict(int)
        self._status_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
        self._response_times = []
        
        # Real-time counters
        self._total_requests = 0
        self._total_errors = 0
        self._start_time = time.time()
    
    def record_request(
        self,
        path: str,
        method: str,
        status_code: int,
        duration_ms: float,
        response_size: int = 0,
        user_agent: str = "",
        ip_address: str = ""
    ):
        """Record a request metric.
        
        Args:
            path: Request path
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            response_size: Response size in bytes
            user_agent: User agent string
            ip_address: Client IP address
        """
        with self._lock:
            metric = RequestMetric(
                timestamp=time.time(),
                path=path,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                response_size=response_size,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            self._requests.append(metric)
            
            # Update aggregated statistics
            self._request_counts[f"{method} {path}"] += 1
            self._status_counts[status_code] += 1
            self._response_times.append(duration_ms)
            self._total_requests += 1
            
            # Keep response times list manageable
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-500:]
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        path: str,
        traceback: str = "",
        user_agent: str = "",
        ip_address: str = ""
    ):
        """Record an error metric.
        
        Args:
            error_type: Type of error
            error_message: Error message
            path: Request path where error occurred
            traceback: Error traceback
            user_agent: User agent string
            ip_address: Client IP address
        """
        with self._lock:
            metric = ErrorMetric(
                timestamp=time.time(),
                error_type=error_type,
                error_message=error_message,
                path=path,
                traceback=traceback,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            self._errors.append(metric)
            
            # Update aggregated statistics
            self._error_counts[error_type] += 1
            self._total_errors += 1
    
    def record_performance(
        self,
        operation: str,
        duration_ms: float,
        memory_mb: float = 0,
        cpu_percent: float = 0,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric.
        
        Args:
            operation: Operation name
            duration_ms: Operation duration in milliseconds
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage
            context: Additional context data
        """
        with self._lock:
            metric = PerformanceMetric(
                timestamp=time.time(),
                operation=operation,
                duration_ms=duration_ms,
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                context=context or {}
            )
            
            self._performance.append(metric)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.
        
        Returns:
            Dictionary containing all metrics
        """
        with self._lock:
            current_time = time.time()
            uptime_seconds = current_time - self._start_time
            
            # Calculate averages and statistics
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times else 0
            )
            
            requests_per_minute = (
                self._total_requests / (uptime_seconds / 60)
                if uptime_seconds > 0 else 0
            )
            
            error_rate = (
                (self._total_errors / self._total_requests * 100)
                if self._total_requests > 0 else 0
            )
            
            return {
                "summary": {
                    "uptime_seconds": uptime_seconds,
                    "total_requests": self._total_requests,
                    "total_errors": self._total_errors,
                    "requests_per_minute": round(requests_per_minute, 2),
                    "error_rate_percent": round(error_rate, 2),
                    "avg_response_time_ms": round(avg_response_time, 2)
                },
                "requests": [
                    {
                        "timestamp": r.timestamp,
                        "path": r.path,
                        "method": r.method,
                        "status_code": r.status_code,
                        "duration_ms": r.duration_ms,
                        "response_size": r.response_size,
                        "user_agent": r.user_agent,
                        "ip_address": r.ip_address
                    }
                    for r in list(self._requests)
                ],
                "errors": [
                    {
                        "timestamp": e.timestamp,
                        "error_type": e.error_type,
                        "error_message": e.error_message,
                        "path": e.path,
                        "traceback": e.traceback,
                        "user_agent": e.user_agent,
                        "ip_address": e.ip_address
                    }
                    for e in list(self._errors)
                ],
                "performance": [
                    {
                        "timestamp": p.timestamp,
                        "operation": p.operation,
                        "duration_ms": p.duration_ms,
                        "memory_mb": p.memory_mb,
                        "cpu_percent": p.cpu_percent,
                        "context": p.context
                    }
                    for p in list(self._performance)
                ],
                "aggregated": {
                    "request_counts": dict(self._request_counts),
                    "status_counts": dict(self._status_counts),
                    "error_counts": dict(self._error_counts)
                },
                "response_times": list(self._response_times)
            }
    
    def get_recent_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent request metrics.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of recent request metrics
        """
        with self._lock:
            recent = list(self._requests)[-limit:]
            return [
                {
                    "timestamp": r.timestamp,
                    "path": r.path,
                    "method": r.method,
                    "status_code": r.status_code,
                    "duration_ms": r.duration_ms,
                    "response_size": r.response_size,
                    "user_agent": r.user_agent,
                    "ip_address": r.ip_address
                }
                for r in recent
            ]
    
    def get_recent_errors(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent error metrics.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error metrics
        """
        with self._lock:
            recent = list(self._errors)[-limit:]
            return [
                {
                    "timestamp": e.timestamp,
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                    "path": e.path,
                    "traceback": e.traceback,
                    "user_agent": e.user_agent,
                    "ip_address": e.ip_address
                }
                for e in recent
            ]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary containing performance statistics
        """
        with self._lock:
            if not self._performance:
                return {"operations": {}, "summary": {}}
            
            # Group by operation
            by_operation = defaultdict(list)
            for perf in self._performance:
                by_operation[perf.operation].append(perf)
            
            operation_stats = {}
            for operation, metrics in by_operation.items():
                durations = [m.duration_ms for m in metrics]
                memory_usage = [m.memory_mb for m in metrics if m.memory_mb > 0]
                
                operation_stats[operation] = {
                    "count": len(metrics),
                    "avg_duration_ms": sum(durations) / len(durations),
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                    "avg_memory_mb": sum(memory_usage) / len(memory_usage) if memory_usage else 0
                }
            
            # Overall stats
            all_durations = [p.duration_ms for p in self._performance]
            all_memory = [p.memory_mb for p in self._performance if p.memory_mb > 0]
            
            summary = {
                "total_operations": len(self._performance),
                "avg_duration_ms": sum(all_durations) / len(all_durations),
                "avg_memory_mb": sum(all_memory) / len(all_memory) if all_memory else 0
            }
            
            return {
                "operations": operation_stats,
                "summary": summary
            }
    
    def clear_metrics(self):
        """Clear all collected metrics."""
        with self._lock:
            self._requests.clear()
            self._errors.clear()
            self._performance.clear()
            self._request_counts.clear()
            self._status_counts.clear()
            self._error_counts.clear()
            self._response_times.clear()
            self._total_requests = 0
            self._total_errors = 0
            self._start_time = time.time()