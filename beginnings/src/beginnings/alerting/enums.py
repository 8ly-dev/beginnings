"""Enums for alerting system."""

from enum import Enum, IntEnum


class AlertSeverity(Enum):
    """Alert severity levels with ordering support."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __gt__(self, other):
        """Greater than comparison for severity ordering."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return order[self.value] > order[other.value]
    
    def __lt__(self, other):
        """Less than comparison for severity ordering."""
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return order[self.value] < order[other.value]


class AlertState(Enum):
    """Alert state values."""
    
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"