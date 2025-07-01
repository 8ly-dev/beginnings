"""Configuration classes for monitoring system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    
    name: str
    check_type: str
    endpoint: str
    interval_seconds: int
    timeout_seconds: int = 10
    retries: int = 3
    enabled: bool = True
    critical: bool = False
    headers: Dict[str, str] = field(default_factory=dict)
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    dependencies: List[str] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """Validate health check configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Health check name cannot be empty")
        
        if not self.check_type or not self.check_type.strip():
            errors.append("Check type cannot be empty")
        
        if not self.endpoint or not self.endpoint.strip():
            errors.append("Endpoint cannot be empty")
        
        if self.interval_seconds <= 0:
            errors.append("Interval must be positive")
        
        if self.timeout_seconds <= 0:
            errors.append("Timeout must be positive")
        
        if self.retries < 0:
            errors.append("Retries cannot be negative")
        
        valid_check_types = ["http", "https", "database", "redis", "custom"]
        if self.check_type not in valid_check_types:
            errors.append(f"Check type must be one of: {', '.join(valid_check_types)}")
        
        return errors


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    
    name: str
    collection_interval_seconds: int
    retention_days: int
    storage_backend: str
    enabled: bool = True
    export_enabled: bool = True
    aggregation_enabled: bool = True
    export_endpoint: Optional[str] = None
    custom_labels: Dict[str, str] = field(default_factory=dict)
    metric_types: List[str] = field(default_factory=lambda: ["counter", "gauge", "histogram"])
    sampling_rate: float = 1.0
    
    def validate(self) -> List[str]:
        """Validate metrics configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Metrics name cannot be empty")
        
        if self.collection_interval_seconds <= 0:
            errors.append("Collection interval must be positive")
        
        if self.retention_days <= 0:
            errors.append("Retention days must be positive")
        
        if not self.storage_backend or not self.storage_backend.strip():
            errors.append("Storage backend cannot be empty")
        
        valid_backends = ["prometheus", "influxdb", "statsd", "memory"]
        if self.storage_backend not in valid_backends:
            errors.append(f"Storage backend must be one of: {', '.join(valid_backends)}")
        
        if not (0.0 <= self.sampling_rate <= 1.0):
            errors.append("Sampling rate must be between 0.0 and 1.0")
        
        return errors


@dataclass
class MonitoringConfig:
    """Overall monitoring configuration."""
    
    project_name: str
    environment: str
    health_checks: List[HealthCheckConfig] = field(default_factory=list)
    metrics_configs: List[MetricsConfig] = field(default_factory=list)
    dashboard_enabled: bool = True
    alerting_enabled: bool = True
    reporting_enabled: bool = True
    log_level: str = "INFO"
    
    def validate(self) -> List[str]:
        """Validate monitoring configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.project_name or not self.project_name.strip():
            errors.append("project_name cannot be empty")
        
        if not self.environment or not self.environment.strip():
            errors.append("Environment cannot be empty")
        
        # Validate health checks
        for i, health_check in enumerate(self.health_checks):
            hc_errors = health_check.validate()
            errors.extend([f"health_check[{i}]: {error}" for error in hc_errors])
        
        # Validate metrics configs
        for i, metrics_config in enumerate(self.metrics_configs):
            mc_errors = metrics_config.validate()
            errors.extend([f"metrics_config[{i}]: {error}" for error in mc_errors])
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")
        
        return errors