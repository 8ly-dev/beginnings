"""Data models for logging system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Pattern
import re

from .enums import LogLevel, LogFormat


@dataclass
class LogEntry:
    """Structure for a log entry."""
    
    timestamp: datetime
    level: LogLevel
    message: str
    logger_name: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    exception_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.name,
            "message": self.message,
            "logger_name": self.logger_name,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "context": self.context,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "exception_info": self.exception_info
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class LogConfig:
    """Configuration for logging."""
    
    name: str
    level: LogLevel
    format: LogFormat
    output_file: str
    max_file_size_mb: int = 100
    backup_count: int = 5
    structured_logging: bool = True
    async_logging: bool = True
    include_modules: List[str] = field(default_factory=list)
    exclude_modules: List[str] = field(default_factory=list)
    include_loggers: List[str] = field(default_factory=list)
    exclude_loggers: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 10000
    buffer_size: int = 1000
    compression: bool = False
    
    def validate(self) -> List[str]:
        """Validate logging configuration.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Log configuration name cannot be empty")
        
        if not self.output_file or not self.output_file.strip():
            errors.append("Output file cannot be empty")
        
        if self.max_file_size_mb <= 0:
            errors.append("Max file size must be positive")
        
        if self.backup_count < 0:
            errors.append("Backup count cannot be negative")
        
        if self.rate_limit_per_minute <= 0:
            errors.append("Rate limit must be positive")
        
        if self.buffer_size <= 0:
            errors.append("Buffer size must be positive")
        
        return errors


@dataclass
class LogFilter:
    """Filter for log entries."""
    
    level_filter: Optional[LogLevel] = None
    logger_filter: Optional[str] = None  # Regex pattern
    module_filter: Optional[str] = None  # Regex pattern
    message_filter: Optional[str] = None  # Regex pattern
    context_filters: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def matches(self, entry: LogEntry) -> bool:
        """Check if log entry matches filter criteria.
        
        Args:
            entry: Log entry to check
            
        Returns:
            True if entry matches filter
        """
        # Level filter
        if self.level_filter and entry.level < self.level_filter:
            return False
        
        # Logger filter
        if self.logger_filter:
            if not re.search(self.logger_filter, entry.logger_name):
                return False
        
        # Module filter
        if self.module_filter and entry.module:
            if not re.search(self.module_filter, entry.module):
                return False
        
        # Message filter
        if self.message_filter:
            if not re.search(self.message_filter, entry.message):
                return False
        
        # Context filters
        for key, value in self.context_filters.items():
            if key not in entry.context or entry.context[key] != value:
                return False
        
        # Time range filter
        if self.start_time and entry.timestamp < self.start_time:
            return False
        
        if self.end_time and entry.timestamp > self.end_time:
            return False
        
        return True


@dataclass
class LogResult:
    """Result of logging operation."""
    
    success: bool
    logger_name: Optional[str] = None
    output_file: Optional[str] = None
    level: Optional[LogLevel] = None
    log_entry: Optional[LogEntry] = None
    bytes_written: int = 0
    processing_time_ms: float = 0
    message: str = ""


@dataclass
class LogMetrics:
    """Metrics extracted from log entries."""
    
    total_entries: int
    debug_count: int = 0
    info_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    critical_count: int = 0
    error_rate: float = 0.0
    top_loggers: List[Dict[str, Any]] = field(default_factory=list)
    top_errors: List[Dict[str, Any]] = field(default_factory=list)
    time_range: Optional[Dict[str, datetime]] = None


@dataclass
class LogAnalysisResult:
    """Result of log analysis."""
    
    total_entries_analyzed: int
    time_range: Dict[str, datetime]
    metrics: LogMetrics
    patterns: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    trends: Dict[str, str] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_health_score: int = 100


@dataclass
class TrendAnalysis:
    """Analysis of trends in data."""
    
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    projected_errors_next_hour: int
    anomaly_periods: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CorrelationAnalysis:
    """Analysis of correlations between logs and metrics."""
    
    cpu_correlation: float
    memory_correlation: float
    disk_correlation: float = 0.0
    network_correlation: float = 0.0
    significant_correlations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LogInsights:
    """Insights generated from log analysis."""
    
    critical_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_health_score: int = 100
    trend_analysis: Optional[TrendAnalysis] = None
    correlation_analysis: Optional[CorrelationAnalysis] = None