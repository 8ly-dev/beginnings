"""Exception classes for monitoring system."""

from typing import Dict, Any, Optional


class MonitoringError(Exception):
    """Base exception for monitoring errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class HealthCheckError(MonitoringError):
    """Exception for health check errors."""
    
    def __init__(self, check_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.check_name = check_name


class MetricsError(MonitoringError):
    """Exception for metrics collection errors."""
    
    def __init__(self, metric_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.metric_name = metric_name