"""Exception classes for logging system."""

from typing import Dict, Any, Optional


class LoggingError(Exception):
    """Base exception for logging errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}