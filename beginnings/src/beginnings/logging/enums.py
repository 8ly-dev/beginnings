"""Enums for logging system."""

from enum import Enum, IntEnum


class LogLevel(Enum):
    """Log level definitions with ordering support."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    def __gt__(self, other):
        """Greater than comparison for log level ordering."""
        if not isinstance(other, LogLevel):
            return NotImplemented
        
        order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return order[self.value] > order[other.value]
    
    def __lt__(self, other):
        """Less than comparison for log level ordering."""
        if not isinstance(other, LogLevel):
            return NotImplemented
        
        order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return order[self.value] < order[other.value]
    
    @property
    def numeric_value(self) -> int:
        """Get numeric value for compatibility."""
        order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return order[self.value]


class LogFormat(Enum):
    """Log format options."""
    
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"
    CUSTOM = "custom"