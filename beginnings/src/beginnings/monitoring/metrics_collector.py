"""Metrics collector for comprehensive monitoring."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from .config import MetricsConfig
from .exceptions import MetricsError


@dataclass
class MetricData:
    """Data structure for a metric."""
    
    name: str
    value: float
    metric_type: str
    labels: Dict[str, str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class MetricResult:
    """Result of metric recording operation."""
    
    success: bool
    metric_name: str
    metric_type: str
    value: float
    labels: Dict[str, str] = None
    bucket_counts: Optional[Dict[str, int]] = None
    message: str = ""
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class MetricsInitializationResult:
    """Result of metrics initialization."""
    
    success: bool
    backend: str
    labels_configured: bool = False
    registered_metrics: List[str] = None
    message: str = ""
    
    def __post_init__(self):
        if self.registered_metrics is None:
            self.registered_metrics = []


@dataclass
class MetricsExportResult:
    """Result of metrics export operation."""
    
    success: bool
    exported_metrics_count: int = 0
    export_timestamp: Optional[datetime] = None
    message: str = ""
    
    def __post_init__(self):
        if self.export_timestamp is None:
            self.export_timestamp = datetime.utcnow()


@dataclass
class MetricsSummary:
    """Summary of metrics collection."""
    
    total_metrics: int
    counter_metrics: int
    gauge_metrics: int
    histogram_metrics: int
    collection_interval: int
    retention_days: int
    last_collection: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_collection is None:
            self.last_collection = datetime.utcnow()


class MetricsCollector:
    """Collector for metrics and performance data."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self._config: Optional[MetricsConfig] = None
        self._metrics: Dict[str, MetricData] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._initialized = False
    
    async def initialize(self, config: MetricsConfig) -> MetricsInitializationResult:
        """Initialize metrics collection with configuration.
        
        Args:
            config: Metrics configuration
            
        Returns:
            Initialization result
        """
        try:
            # Validate configuration
            errors = config.validate()
            if errors:
                return MetricsInitializationResult(
                    success=False,
                    backend="",
                    message=f"Configuration invalid: {', '.join(errors)}"
                )
            
            self._config = config
            self._initialized = True
            
            # Set up default labels
            labels_configured = len(config.custom_labels) > 0
            
            # Register basic system metrics
            registered_metrics = [
                "cpu_usage_percent",
                "memory_usage_percent", 
                "disk_usage_percent",
                "http_requests_total",
                "response_time_seconds"
            ]
            
            return MetricsInitializationResult(
                success=True,
                backend=config.storage_backend,
                labels_configured=labels_configured,
                registered_metrics=registered_metrics,
                message=f"Metrics collector initialized with {config.storage_backend} backend"
            )
            
        except Exception as e:
            return MetricsInitializationResult(
                success=False,
                backend="",
                message=f"Failed to initialize metrics collector: {str(e)}"
            )
    
    async def record_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> MetricResult:
        """Record a counter metric.
        
        Args:
            name: Metric name
            value: Counter value to add
            labels: Optional labels for the metric
            
        Returns:
            Metric recording result
        """
        if not self._initialized:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="counter",
                value=value,
                message="Metrics collector not initialized"
            )
        
        try:
            # Build metric key with labels
            metric_key = self._build_metric_key(name, labels)
            
            # Update counter
            self._counters[metric_key] = self._counters.get(metric_key, 0) + value
            
            # Store metric data
            metric_data = MetricData(
                name=name,
                value=value,
                metric_type="counter",
                labels=labels or {}
            )
            self._metrics[metric_key] = metric_data
            
            return MetricResult(
                success=True,
                metric_name=name,
                metric_type="counter",
                value=value,
                labels=labels or {},
                message=f"Counter '{name}' recorded successfully"
            )
            
        except Exception as e:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="counter",
                value=value,
                message=f"Failed to record counter: {str(e)}"
            )
    
    async def record_gauge(
        self, 
        name: str, 
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> MetricResult:
        """Record a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels for the metric
            
        Returns:
            Metric recording result
        """
        if not self._initialized:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="gauge",
                value=value,
                message="Metrics collector not initialized"
            )
        
        try:
            # Build metric key with labels
            metric_key = self._build_metric_key(name, labels)
            
            # Set gauge value
            self._gauges[metric_key] = value
            
            # Store metric data
            metric_data = MetricData(
                name=name,
                value=value,
                metric_type="gauge",
                labels=labels or {}
            )
            self._metrics[metric_key] = metric_data
            
            return MetricResult(
                success=True,
                metric_name=name,
                metric_type="gauge",
                value=value,
                labels=labels or {},
                message=f"Gauge '{name}' recorded successfully"
            )
            
        except Exception as e:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="gauge",
                value=value,
                message=f"Failed to record gauge: {str(e)}"
            )
    
    async def record_histogram(
        self, 
        name: str, 
        value: float,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None
    ) -> MetricResult:
        """Record a histogram metric.
        
        Args:
            name: Metric name
            value: Histogram value
            labels: Optional labels for the metric
            buckets: Optional histogram buckets
            
        Returns:
            Metric recording result
        """
        if not self._initialized:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="histogram",
                value=value,
                message="Metrics collector not initialized"
            )
        
        try:
            # Build metric key with labels
            metric_key = self._build_metric_key(name, labels)
            
            # Add value to histogram
            if metric_key not in self._histograms:
                self._histograms[metric_key] = []
            self._histograms[metric_key].append(value)
            
            # Keep only last 1000 values to prevent memory growth
            if len(self._histograms[metric_key]) > 1000:
                self._histograms[metric_key] = self._histograms[metric_key][-1000:]
            
            # Calculate bucket counts if buckets provided
            bucket_counts = None
            if buckets:
                bucket_counts = {}
                for bucket in buckets:
                    count = sum(1 for v in self._histograms[metric_key] if v <= bucket)
                    bucket_counts[f"le_{bucket}"] = count
                bucket_counts["le_inf"] = len(self._histograms[metric_key])
            
            # Store metric data
            metric_data = MetricData(
                name=name,
                value=value,
                metric_type="histogram",
                labels=labels or {}
            )
            self._metrics[metric_key] = metric_data
            
            return MetricResult(
                success=True,
                metric_name=name,
                metric_type="histogram",
                value=value,
                labels=labels or {},
                bucket_counts=bucket_counts,
                message=f"Histogram '{name}' recorded successfully"
            )
            
        except Exception as e:
            return MetricResult(
                success=False,
                metric_name=name,
                metric_type="histogram",
                value=value,
                message=f"Failed to record histogram: {str(e)}"
            )
    
    async def collect_system_metrics(self) -> List[MetricData]:
        """Collect system-level metrics.
        
        Returns:
            List of system metrics
        """
        metrics = []
        
        try:
            # Mock system metrics collection
            # In real implementation, this would use psutil
            
            # CPU usage metric
            cpu_metric = MetricData(
                name="cpu_usage_percent",
                value=25.5,  # Mock value
                metric_type="gauge",
                labels={"component": "system"}
            )
            metrics.append(cpu_metric)
            
            # Memory usage metric
            memory_metric = MetricData(
                name="memory_usage_percent",
                value=67.8,  # Mock value
                metric_type="gauge",
                labels={"component": "system"}
            )
            metrics.append(memory_metric)
            
            # Disk usage metric
            disk_metric = MetricData(
                name="disk_usage_percent",
                value=45.2,  # Mock value
                metric_type="gauge",
                labels={"component": "system"}
            )
            metrics.append(disk_metric)
            
        except Exception as e:
            # Return empty list on error
            pass
        
        return metrics
    
    async def export_metrics(self, endpoint: str) -> MetricsExportResult:
        """Export metrics to external system.
        
        Args:
            endpoint: Export endpoint URL
            
        Returns:
            Export result
        """
        if not self._initialized:
            return MetricsExportResult(
                success=False,
                message="Metrics collector not initialized"
            )
        
        try:
            # Mock metrics export
            # In real implementation, this would send metrics to the endpoint
            
            exported_count = len(self._metrics)
            
            return MetricsExportResult(
                success=True,
                exported_metrics_count=exported_count,
                export_timestamp=datetime.utcnow(),
                message=f"Exported {exported_count} metrics to {endpoint}"
            )
            
        except Exception as e:
            return MetricsExportResult(
                success=False,
                message=f"Failed to export metrics: {str(e)}"
            )
    
    async def get_metrics_summary(self) -> MetricsSummary:
        """Get summary of collected metrics.
        
        Returns:
            Metrics summary
        """
        counter_count = sum(1 for m in self._metrics.values() if m.metric_type == "counter")
        gauge_count = sum(1 for m in self._metrics.values() if m.metric_type == "gauge")
        histogram_count = sum(1 for m in self._metrics.values() if m.metric_type == "histogram")
        
        collection_interval = self._config.collection_interval_seconds if self._config else 15
        retention_days = self._config.retention_days if self._config else 30
        
        return MetricsSummary(
            total_metrics=len(self._metrics),
            counter_metrics=counter_count,
            gauge_metrics=gauge_count,
            histogram_metrics=histogram_count,
            collection_interval=collection_interval,
            retention_days=retention_days,
            last_collection=datetime.utcnow()
        )
    
    def _build_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Build metric key with labels.
        
        Args:
            name: Metric name
            labels: Optional labels
            
        Returns:
            Metric key
        """
        if not labels:
            return name
        
        # Add custom labels from config
        all_labels = {}
        if self._config and self._config.custom_labels:
            all_labels.update(self._config.custom_labels)
        all_labels.update(labels)
        
        # Sort labels for consistent key generation
        sorted_labels = sorted(all_labels.items())
        label_string = ",".join(f"{k}={v}" for k, v in sorted_labels)
        
        return f"{name}[{label_string}]"