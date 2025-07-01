"""Alerting system for the Beginnings framework.

This module provides comprehensive alerting capabilities including:
- Alert rule management and evaluation
- Multi-channel notification delivery
- Alert suppression and correlation
- Integration with monitoring metrics
"""

from .enums import (
    AlertSeverity,
    AlertState
)

from .models import (
    AlertCondition,
    AlertRule,
    AlertConfig,
    NotificationConfig,
    AlertResult,
    NotificationResult
)

from .exceptions import (
    AlertingError,
    NotificationError
)

from .alert_manager import AlertManager
from .notification_manager import NotificationManager

__all__ = [
    # Enums
    "AlertSeverity",
    "AlertState",
    
    # Models
    "AlertCondition",
    "AlertRule",
    "AlertConfig", 
    "NotificationConfig",
    "AlertResult",
    "NotificationResult",
    
    # Exceptions
    "AlertingError",
    "NotificationError",
    
    # Managers
    "AlertManager",
    "NotificationManager"
]