"""
Metrics collection for Beginnings framework.

Provides performance metrics and counters for extensions
and core framework components.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Optional


class MetricsCollector:
    """Thread-safe metrics collector for performance monitoring."""
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, list[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._lock = Lock()
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            metric_name = self._build_metric_name(name, tags)
            self._counters[metric_name] += value
    
    def record_histogram(self, name: str, value: float, tags: Optional[dict[str, str]] = None):
        """Record a histogram value (for duration/timing metrics)."""
        with self._lock:
            metric_name = self._build_metric_name(name, tags)
            self._histograms[metric_name].append(value)
            
            # Keep only last 1000 values to prevent memory growth
            if len(self._histograms[metric_name]) > 1000:
                self._histograms[metric_name] = self._histograms[metric_name][-1000:]
    
    def set_gauge(self, name: str, value: float, tags: Optional[dict[str, str]] = None):
        """Set a gauge metric (current value).""" 
        with self._lock:
            metric_name = self._build_metric_name(name, tags)
            self._gauges[metric_name] = value
    
    def _build_metric_name(self, name: str, tags: Optional[dict[str, str]] = None) -> str:
        """Build metric name with tags."""
        if not tags:
            return name
        
        tag_string = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_string}]"
    
    def get_counter(self, name: str, tags: Optional[dict[str, str]] = None) -> int:
        """Get counter value."""
        metric_name = self._build_metric_name(name, tags)
        return self._counters.get(metric_name, 0)
    
    def get_histogram_stats(self, name: str, tags: Optional[dict[str, str]] = None) -> dict[str, float]:
        """Get histogram statistics."""
        metric_name = self._build_metric_name(name, tags)
        values = self._histograms.get(metric_name, [])
        
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0,
        }
    
    def get_gauge(self, name: str, tags: Optional[dict[str, str]] = None) -> float:
        """Get gauge value."""
        metric_name = self._build_metric_name(name, tags)
        return self._gauges.get(metric_name, 0.0)
    
    def get_all_metrics(self) -> dict[str, any]:
        """Get all metrics for debugging/monitoring."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "histograms": {name: self.get_histogram_stats(name.split('[')[0]) 
                              for name in self._histograms.keys()},
                "gauges": dict(self._gauges)
            }
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, metrics: MetricsCollector, metric_name: str, tags: Optional[dict[str, str]] = None):
        self.metrics = metrics
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.metrics.record_histogram(self.metric_name, duration_ms, self.tags)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector