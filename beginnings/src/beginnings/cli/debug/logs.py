"""Log streaming for debugging dashboard."""

from __future__ import annotations

import time
import logging
from collections import deque
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from threading import RLock


@dataclass
class LogEntry:
    """Individual log entry."""
    timestamp: float
    level: str
    message: str
    logger_name: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class LogStreamer:
    """Streams and manages log entries for the debug dashboard."""
    
    def __init__(self, max_lines: int = 1000):
        """Initialize log streamer.
        
        Args:
            max_lines: Maximum number of log lines to keep in memory
        """
        self.max_lines = max_lines
        self._lock = RLock()
        self._logs: deque[LogEntry] = deque(maxlen=max_lines)
        
        # Log level counters
        self._level_counts = {
            "DEBUG": 0,
            "INFO": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0
        }
        
        # Setup custom log handler
        self._handler = DebugLogHandler(self)
        self._handler.setLevel(logging.DEBUG)
        
        # Format for log messages
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self._handler.setFormatter(formatter)
    
    def add_log(
        self,
        level: str,
        message: str,
        logger_name: str = "root",
        module: str = "",
        function: str = "",
        line_number: int = 0,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Add a log entry.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            logger_name: Name of the logger
            module: Module name where log occurred
            function: Function name where log occurred
            line_number: Line number where log occurred
            extra: Additional context data
        """
        with self._lock:
            entry = LogEntry(
                timestamp=time.time(),
                level=level,
                message=message,
                logger_name=logger_name,
                module=module,
                function=function,
                line_number=line_number,
                extra=extra or {}
            )
            
            self._logs.append(entry)
            
            # Update level counters
            if level in self._level_counts:
                self._level_counts[level] += 1
    
    def get_recent_logs(self, limit: int = 100, level_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent log entries.
        
        Args:
            limit: Maximum number of logs to return
            level_filter: Optional log level filter
            
        Returns:
            List of log entries as dictionaries
        """
        with self._lock:
            logs = list(self._logs)
            
            # Filter by level if specified
            if level_filter:
                logs = [log for log in logs if log.level == level_filter]
            
            # Get most recent entries
            recent_logs = logs[-limit:]
            
            return [
                {
                    "timestamp": log.timestamp,
                    "level": log.level,
                    "message": log.message,
                    "logger_name": log.logger_name,
                    "module": log.module,
                    "function": log.function,
                    "line_number": log.line_number,
                    "extra": log.extra,
                    "formatted_time": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(log.timestamp)
                    )
                }
                for log in recent_logs
            ]
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get log statistics.
        
        Returns:
            Dictionary containing log statistics
        """
        with self._lock:
            total_logs = sum(self._level_counts.values())
            
            # Calculate percentages
            level_percentages = {}
            for level, count in self._level_counts.items():
                percentage = (count / total_logs * 100) if total_logs > 0 else 0
                level_percentages[level] = round(percentage, 2)
            
            # Recent activity (last 5 minutes)
            five_minutes_ago = time.time() - 300
            recent_logs = [log for log in self._logs if log.timestamp > five_minutes_ago]
            recent_by_level = {}
            for level in self._level_counts.keys():
                recent_by_level[level] = len([log for log in recent_logs if log.level == level])
            
            return {
                "total_logs": total_logs,
                "level_counts": dict(self._level_counts),
                "level_percentages": level_percentages,
                "recent_activity": {
                    "last_5_minutes": len(recent_logs),
                    "by_level": recent_by_level
                },
                "memory_usage": {
                    "current_entries": len(self._logs),
                    "max_entries": self.max_lines
                }
            }
    
    def search_logs(
        self,
        query: str,
        level_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search log entries.
        
        Args:
            query: Search query string
            level_filter: Optional log level filter
            limit: Maximum number of results
            
        Returns:
            List of matching log entries
        """
        with self._lock:
            query_lower = query.lower()
            matches = []
            
            for log in self._logs:
                # Check level filter
                if level_filter and log.level != level_filter:
                    continue
                
                # Check if query matches message or logger name
                if (query_lower in log.message.lower() or 
                    query_lower in log.logger_name.lower() or
                    query_lower in log.module.lower()):
                    
                    matches.append({
                        "timestamp": log.timestamp,
                        "level": log.level,
                        "message": log.message,
                        "logger_name": log.logger_name,
                        "module": log.module,
                        "function": log.function,
                        "line_number": log.line_number,
                        "extra": log.extra,
                        "formatted_time": time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(log.timestamp)
                        )
                    })
                
                if len(matches) >= limit:
                    break
            
            return matches
    
    def clear_logs(self):
        """Clear all log entries."""
        with self._lock:
            self._logs.clear()
            self._level_counts = {
                "DEBUG": 0,
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "CRITICAL": 0
            }
    
    def attach_to_logger(self, logger_name: str = ""):
        """Attach log streamer to a logger.
        
        Args:
            logger_name: Name of logger to attach to (empty for root logger)
        """
        logger = logging.getLogger(logger_name)
        logger.addHandler(self._handler)
    
    def detach_from_logger(self, logger_name: str = ""):
        """Detach log streamer from a logger.
        
        Args:
            logger_name: Name of logger to detach from (empty for root logger)
        """
        logger = logging.getLogger(logger_name)
        logger.removeHandler(self._handler)
    
    def get_handler(self) -> 'DebugLogHandler':
        """Get the log handler for manual attachment.
        
        Returns:
            DebugLogHandler instance
        """
        return self._handler


class DebugLogHandler(logging.Handler):
    """Custom log handler that sends logs to the debug dashboard."""
    
    def __init__(self, log_streamer: LogStreamer):
        """Initialize debug log handler.
        
        Args:
            log_streamer: LogStreamer instance to send logs to
        """
        super().__init__()
        self.log_streamer = log_streamer
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to the debug dashboard.
        
        Args:
            record: Log record to emit
        """
        try:
            # Extract extra information
            extra = {}
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                    'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                    'thread', 'threadName', 'processName', 'process', 'message'
                ]:
                    extra[key] = str(value)
            
            # Add log entry to streamer
            self.log_streamer.add_log(
                level=record.levelname,
                message=self.format(record),
                logger_name=record.name,
                module=record.module,
                function=record.funcName,
                line_number=record.lineno,
                extra=extra
            )
            
        except Exception:
            # Don't let logging errors break the application
            self.handleError(record)


def create_log_streamer(max_lines: int = 1000, attach_to_root: bool = True) -> LogStreamer:
    """Create and optionally attach a log streamer.
    
    Args:
        max_lines: Maximum number of log lines to keep
        attach_to_root: Whether to attach to root logger
        
    Returns:
        LogStreamer instance
    """
    streamer = LogStreamer(max_lines)
    
    if attach_to_root:
        streamer.attach_to_logger()
    
    return streamer