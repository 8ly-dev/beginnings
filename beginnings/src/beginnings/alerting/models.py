"""Data models for alerting system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from .enums import AlertSeverity, AlertState


@dataclass
class AlertCondition:
    """Configuration for alert condition evaluation."""
    
    metric_name: str
    operator: str
    threshold_value: float
    duration_minutes: int
    aggregation_function: str = "avg"
    evaluation_window_minutes: int = 1
    labels_filter: Dict[str, str] = field(default_factory=dict)
    custom_query: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate alert condition configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.metric_name or not self.metric_name.strip():
            errors.append("Metric name cannot be empty")
        
        valid_operators = [
            "greater_than", "less_than", "equal_to", "not_equal_to",
            "greater_than_or_equal", "less_than_or_equal"
        ]
        if self.operator not in valid_operators:
            errors.append(f"Invalid operator '{self.operator}', must be one of: {', '.join(valid_operators)}")
        
        if self.duration_minutes <= 0:
            errors.append("Duration must be positive")
        
        if self.evaluation_window_minutes <= 0:
            errors.append("Evaluation window must be positive")
        
        valid_aggregations = ["avg", "min", "max", "sum", "count"]
        if self.aggregation_function not in valid_aggregations:
            errors.append(f"Invalid aggregation function '{self.aggregation_function}', must be one of: {', '.join(valid_aggregations)}")
        
        return errors


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    
    name: str
    description: str
    condition: AlertCondition
    severity: AlertSeverity
    enabled: bool
    notification_channels: List[str] = field(default_factory=list)
    cooldown_minutes: int = 60
    tags: List[str] = field(default_factory=list)
    runbook_url: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate alert rule configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Alert rule name cannot be empty")
        
        if not self.description or not self.description.strip():
            errors.append("Alert rule description cannot be empty")
        
        if self.cooldown_minutes < 0:
            errors.append("Cooldown minutes cannot be negative")
        
        # Validate condition
        condition_errors = self.condition.validate()
        errors.extend([f"condition: {error}" for error in condition_errors])
        
        return errors


@dataclass
class NotificationConfig:
    """Configuration for notification channel."""
    
    channel_type: str
    channel_name: str
    enabled: bool
    settings: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    retry_count: int = 3
    timeout_seconds: int = 30
    
    def validate(self) -> List[str]:
        """Validate notification configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.channel_type or not self.channel_type.strip():
            errors.append("Channel type cannot be empty")
        
        if not self.channel_name or not self.channel_name.strip():
            errors.append("Channel name cannot be empty")
        
        valid_channel_types = ["email", "slack", "pagerduty", "webhook", "sms"]
        if self.channel_type not in valid_channel_types:
            errors.append(f"Invalid channel type '{self.channel_type}', must be one of: {', '.join(valid_channel_types)}")
        
        if self.rate_limit_per_minute <= 0:
            errors.append("Rate limit must be positive")
        
        if self.retry_count < 0:
            errors.append("Retry count cannot be negative")
        
        if self.timeout_seconds <= 0:
            errors.append("Timeout must be positive")
        
        return errors


@dataclass
class AlertConfig:
    """Overall alerting configuration."""
    
    project_name: str
    environment: str
    alert_rules: List[AlertRule] = field(default_factory=list)
    notification_configs: List[NotificationConfig] = field(default_factory=list)
    global_cooldown_minutes: int = 5
    evaluation_interval_seconds: int = 60
    retention_days: int = 30
    
    def validate(self) -> List[str]:
        """Validate alerting configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.project_name or not self.project_name.strip():
            errors.append("Project name cannot be empty")
        
        if not self.environment or not self.environment.strip():
            errors.append("Environment cannot be empty")
        
        if self.global_cooldown_minutes < 0:
            errors.append("Global cooldown cannot be negative")
        
        if self.evaluation_interval_seconds <= 0:
            errors.append("Evaluation interval must be positive")
        
        if self.retention_days <= 0:
            errors.append("Retention days must be positive")
        
        # Validate alert rules
        for i, rule in enumerate(self.alert_rules):
            rule_errors = rule.validate()
            errors.extend([f"alert_rule[{i}]: {error}" for error in rule_errors])
        
        # Validate notification configs
        for i, config in enumerate(self.notification_configs):
            config_errors = config.validate()
            errors.extend([f"notification_config[{i}]: {error}" for error in config_errors])
        
        return errors


@dataclass
class AlertResult:
    """Result of alert operation."""
    
    success: bool
    alert_id: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    state: Optional[AlertState] = None
    enabled: Optional[bool] = None
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    suppressed_until: Optional[datetime] = None
    suppress_reason: Optional[str] = None
    resolution_reason: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    condition_met: Optional[bool] = None
    duration_exceeded: Optional[bool] = None
    message: str = ""


@dataclass
class NotificationResult:
    """Result of notification delivery."""
    
    success: bool
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    channel_type: Optional[str] = None
    message_id: Optional[str] = None
    delivery_time_ms: float = 0
    retry_count: int = 0
    error_message: str = ""


@dataclass
class EvaluationCycleResult:
    """Result of alert evaluation cycle."""
    
    success: bool
    rules_evaluated: int = 0
    alerts_triggered: int = 0
    alerts_resolved: int = 0
    evaluation_duration_ms: float = 0
    errors: List[str] = field(default_factory=list)