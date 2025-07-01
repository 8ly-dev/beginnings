"""Exception classes for alerting system."""

from typing import Dict, Any, Optional


class AlertingError(Exception):
    """Base exception for alerting errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotificationError(AlertingError):
    """Exception for notification delivery errors."""
    
    def __init__(self, channel_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.channel_name = channel_name