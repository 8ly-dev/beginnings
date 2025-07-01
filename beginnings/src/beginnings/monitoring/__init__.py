"""
Monitoring and observability module for Beginnings framework.

This module provides comprehensive monitoring capabilities including:
- Health checks for system and application components
- Metrics collection and aggregation
- Performance monitoring and profiling
- System resource monitoring
- Alerting and reporting
- Structured logging and security events
"""

# Legacy monitoring components
from beginnings.monitoring.logger import get_structured_logger, SecurityEvent, PerformanceEvent
from beginnings.monitoring.metrics import MetricsCollector as LegacyMetricsCollector, get_metrics_collector
from beginnings.monitoring.health import HealthCheck, get_health_check

# New comprehensive monitoring components
from .config import (
    HealthCheckConfig,
    MetricsConfig,
    MonitoringConfig
)

from .exceptions import (
    MonitoringError,
    HealthCheckError,
    MetricsError
)

from .health_manager import (
    HealthCheckManager,
    HealthCheckResult
)

from .metrics_collector import (
    MetricsCollector,
    MetricData
)

from .performance import (
    PerformanceMonitor,
    PerformanceReport
)

from .system import (
    SystemMonitor,
    SystemStatus
)

__all__ = [
    # Legacy components
    "get_structured_logger",
    "SecurityEvent", 
    "PerformanceEvent",
    "LegacyMetricsCollector",
    "get_metrics_collector",
    "HealthCheck",
    "get_health_check",
    
    # Configuration
    "HealthCheckConfig",
    "MetricsConfig", 
    "MonitoringConfig",
    
    # Exceptions
    "MonitoringError",
    "HealthCheckError",
    "MetricsError",
    
    # Health checks
    "HealthCheckManager",
    "HealthCheckResult",
    
    # Metrics
    "MetricsCollector",
    "MetricData",
    
    # Performance
    "PerformanceMonitor",
    "PerformanceReport",
    
    # System monitoring
    "SystemMonitor",
    "SystemStatus"
]