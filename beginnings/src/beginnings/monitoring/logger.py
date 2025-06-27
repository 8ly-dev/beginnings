"""
Structured logging for Beginnings framework.

Provides security and performance event logging for extensions
and core framework components.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional
from uuid import uuid4


@dataclass
class SecurityEvent:
    """Security-related event for logging."""
    event_type: str  # auth_failed, rate_limited, csrf_violation, etc.
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    severity: str = "warning"  # info, warning, error, critical
    
    def __post_init__(self):
        self.timestamp = time.time()
        self.event_id = str(uuid4())


@dataclass 
class PerformanceEvent:
    """Performance-related event for logging."""
    operation: str  # rate_limit_check, csrf_validation, auth_check, etc.
    duration_ms: float
    extension: str
    request_path: Optional[str] = None
    status: str = "success"  # success, error, timeout
    details: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        self.timestamp = time.time()
        self.event_id = str(uuid4())


class StructuredLogger:
    """Structured logger for Beginnings framework."""
    
    def __init__(self, name: str = "beginnings"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup JSON formatted logging."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_security_event(self, event: SecurityEvent):
        """Log a security event."""
        event_data = asdict(event)
        message = f"Security Event: {event.event_type}"
        
        if event.severity == "critical":
            self.logger.critical(f"{message} | {json.dumps(event_data)}")
        elif event.severity == "error":
            self.logger.error(f"{message} | {json.dumps(event_data)}")
        elif event.severity == "warning":
            self.logger.warning(f"{message} | {json.dumps(event_data)}")
        else:
            self.logger.info(f"{message} | {json.dumps(event_data)}")
    
    def log_performance_event(self, event: PerformanceEvent):
        """Log a performance event."""
        event_data = asdict(event)
        message = f"Performance: {event.operation} ({event.duration_ms:.2f}ms)"
        
        if event.status == "error":
            self.logger.error(f"{message} | {json.dumps(event_data)}")
        elif event.duration_ms > 1000:  # Log slow operations as warnings
            self.logger.warning(f"SLOW {message} | {json.dumps(event_data)}")
        else:
            self.logger.info(f"{message} | {json.dumps(event_data)}")
    
    def log_extension_startup(self, extension_name: str, config: dict[str, Any]):
        """Log extension startup."""
        self.logger.info(f"Extension Started: {extension_name} | config_keys: {list(config.keys())}")
    
    def log_extension_error(self, extension_name: str, error: Exception, context: dict[str, Any] = None):
        """Log extension error."""
        error_data = {
            "extension": extension_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self.logger.error(f"Extension Error: {extension_name} | {json.dumps(error_data)}")


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_structured_logger(name: str = "beginnings") -> StructuredLogger:
    """Get the structured logger instance."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger