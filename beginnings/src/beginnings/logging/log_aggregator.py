"""Log aggregator for log data aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import LogEntry
from .enums import LogLevel


class LogAggregator:
    """Aggregator for log data aggregation and summarization."""
    
    def __init__(self):
        """Initialize log aggregator."""
        pass
    
    async def aggregate_by_time_window(
        self, 
        entries: List[LogEntry],
        window_minutes: int = 60
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate log entries by time windows.
        
        Args:
            entries: List of log entries
            window_minutes: Size of time window in minutes
            
        Returns:
            Aggregated data by time windows
        """
        if not entries:
            return {}
        
        aggregation = {}
        
        # Sort entries by timestamp
        sorted_entries = sorted(entries, key=lambda x: x.timestamp)
        
        # Define time windows
        start_time = sorted_entries[0].timestamp
        end_time = sorted_entries[-1].timestamp
        
        current_window = start_time
        while current_window <= end_time:
            window_end = current_window + timedelta(minutes=window_minutes)
            window_key = current_window.strftime("%Y-%m-%d %H:%M")
            
            # Filter entries in this window
            window_entries = [
                e for e in sorted_entries 
                if current_window <= e.timestamp < window_end
            ]
            
            if window_entries:
                aggregation[window_key] = {
                    "start_time": current_window,
                    "end_time": window_end,
                    "total_count": len(window_entries),
                    "level_counts": self._count_by_level(window_entries),
                    "logger_counts": self._count_by_logger(window_entries),
                    "error_rate": self._calculate_error_rate(window_entries)
                }
            
            current_window = window_end
        
        return aggregation
    
    async def aggregate_by_logger(
        self, 
        entries: List[LogEntry]
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate log entries by logger.
        
        Args:
            entries: List of log entries
            
        Returns:
            Aggregated data by logger
        """
        aggregation = defaultdict(lambda: {
            "total_count": 0,
            "level_counts": defaultdict(int),
            "first_seen": None,
            "last_seen": None,
            "sample_messages": []
        })
        
        for entry in entries:
            logger_data = aggregation[entry.logger_name]
            
            # Update counts
            logger_data["total_count"] += 1
            logger_data["level_counts"][entry.level.name] += 1
            
            # Update timestamps
            if logger_data["first_seen"] is None or entry.timestamp < logger_data["first_seen"]:
                logger_data["first_seen"] = entry.timestamp
            
            if logger_data["last_seen"] is None or entry.timestamp > logger_data["last_seen"]:
                logger_data["last_seen"] = entry.timestamp
            
            # Store sample messages
            if len(logger_data["sample_messages"]) < 5:
                logger_data["sample_messages"].append({
                    "timestamp": entry.timestamp,
                    "level": entry.level.name,
                    "message": entry.message[:200]  # Truncate long messages
                })
        
        # Convert defaultdict to regular dict
        return {k: dict(v) for k, v in aggregation.items()}
    
    async def aggregate_by_error_type(
        self, 
        entries: List[LogEntry]
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate error entries by error type.
        
        Args:
            entries: List of log entries
            
        Returns:
            Aggregated error data by type
        """
        error_entries = [e for e in entries if e.level >= LogLevel.ERROR]
        
        if not error_entries:
            return {}
        
        # Group by error patterns
        error_patterns = defaultdict(lambda: {
            "count": 0,
            "first_seen": None,
            "last_seen": None,
            "loggers": set(),
            "sample_contexts": []
        })
        
        for entry in error_entries:
            # Simplify error message for grouping
            error_key = self._extract_error_pattern(entry.message)
            
            pattern_data = error_patterns[error_key]
            pattern_data["count"] += 1
            pattern_data["loggers"].add(entry.logger_name)
            
            # Update timestamps
            if pattern_data["first_seen"] is None or entry.timestamp < pattern_data["first_seen"]:
                pattern_data["first_seen"] = entry.timestamp
            
            if pattern_data["last_seen"] is None or entry.timestamp > pattern_data["last_seen"]:
                pattern_data["last_seen"] = entry.timestamp
            
            # Store sample context
            if len(pattern_data["sample_contexts"]) < 3:
                pattern_data["sample_contexts"].append({
                    "timestamp": entry.timestamp,
                    "logger": entry.logger_name,
                    "context": entry.context,
                    "full_message": entry.message
                })
        
        # Convert sets to lists for JSON serialization
        result = {}
        for pattern, data in error_patterns.items():
            result[pattern] = {
                "count": data["count"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"],
                "unique_loggers": len(data["loggers"]),
                "loggers": list(data["loggers"]),
                "sample_contexts": data["sample_contexts"]
            }
        
        return result
    
    def _count_by_level(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Count entries by log level.
        
        Args:
            entries: List of log entries
            
        Returns:
            Count by log level
        """
        counts = defaultdict(int)
        for entry in entries:
            counts[entry.level.name] += 1
        return dict(counts)
    
    def _count_by_logger(self, entries: List[LogEntry]) -> Dict[str, int]:
        """Count entries by logger.
        
        Args:
            entries: List of log entries
            
        Returns:
            Count by logger
        """
        counts = defaultdict(int)
        for entry in entries:
            counts[entry.logger_name] += 1
        return dict(counts)
    
    def _calculate_error_rate(self, entries: List[LogEntry]) -> float:
        """Calculate error rate for entries.
        
        Args:
            entries: List of log entries
            
        Returns:
            Error rate (0.0 to 1.0)
        """
        if not entries:
            return 0.0
        
        error_count = sum(1 for e in entries if e.level >= LogLevel.ERROR)
        return error_count / len(entries)
    
    def _extract_error_pattern(self, message: str) -> str:
        """Extract error pattern from message for grouping.
        
        Args:
            message: Error message
            
        Returns:
            Error pattern key
        """
        # Simplify error message by removing variable parts
        import re
        
        # Remove numbers and common variable patterns
        pattern = re.sub(r'\d+', 'N', message)
        pattern = re.sub(r'[a-f0-9]{8,}', 'HASH', pattern)  # Remove long hex strings
        pattern = re.sub(r'https?://[^\s]+', 'URL', pattern)  # Remove URLs
        pattern = re.sub(r'/[^\s]*', '/PATH', pattern)  # Remove file paths
        
        # Take first 100 characters for grouping
        return pattern[:100]