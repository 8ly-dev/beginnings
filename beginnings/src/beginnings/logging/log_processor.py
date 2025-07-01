"""Log processor for log analysis and filtering."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

from .enums import LogLevel, LogFormat
from .models import LogEntry, LogFilter, LogMetrics


class LogProcessor:
    """Processor for log analysis and filtering."""
    
    def __init__(self):
        """Initialize log processor."""
        pass
    
    async def parse_log_file(self, file_path: str, format: LogFormat) -> List[LogEntry]:
        """Parse log file and return log entries.
        
        Args:
            file_path: Path to log file
            format: Log format
            
        Returns:
            List of parsed log entries
        """
        entries = []
        
        try:
            log_file = Path(file_path)
            if not log_file.exists():
                return entries
            
            content = log_file.read_text()
            lines = content.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    if format == LogFormat.JSON:
                        entry = self._parse_json_log_line(line)
                    else:
                        entry = self._parse_text_log_line(line)
                    
                    if entry:
                        entries.append(entry)
                        
                except Exception:
                    # Skip malformed lines
                    continue
            
            return entries
            
        except Exception:
            return entries
    
    def _parse_json_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse JSON log line.
        
        Args:
            line: JSON log line
            
        Returns:
            Parsed log entry or None
        """
        try:
            data = json.loads(line)
            
            # Parse timestamp
            timestamp_str = data.get('timestamp', datetime.utcnow().isoformat())
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Parse level
            level_str = data.get('level', 'INFO')
            level = getattr(LogLevel, level_str, LogLevel.INFO)
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=data.get('message', ''),
                logger_name=data.get('logger', 'unknown'),
                module=data.get('module'),
                function=data.get('function'),
                line_number=data.get('line'),
                context=data.get('context', {}),
                trace_id=data.get('trace_id'),
                span_id=data.get('span_id'),
                exception_info=data.get('exception_info')
            )
            
        except Exception:
            return None
    
    def _parse_text_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse text log line.
        
        Args:
            line: Text log line
            
        Returns:
            Parsed log entry or None
        """
        try:
            # Simple text parsing (basic implementation)
            parts = line.split(' - ', 3)
            if len(parts) < 4:
                return None
            
            timestamp = datetime.utcnow()  # Simplified
            logger_name = parts[1] if len(parts) > 1 else 'unknown'
            level_str = parts[2] if len(parts) > 2 else 'INFO'
            message = parts[3] if len(parts) > 3 else ''
            
            level = getattr(LogLevel, level_str, LogLevel.INFO)
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                logger_name=logger_name
            )
            
        except Exception:
            return None
    
    async def filter_entries(
        self, 
        entries: List[LogEntry],
        level_filter: Optional[LogLevel] = None,
        logger_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        message_filter: Optional[str] = None
    ) -> List[LogEntry]:
        """Filter log entries by criteria.
        
        Args:
            entries: List of log entries
            level_filter: Minimum log level
            logger_filter: Logger name pattern
            start_time: Start time filter
            end_time: End time filter
            message_filter: Message pattern filter
            
        Returns:
            Filtered log entries
        """
        filtered = []
        
        for entry in entries:
            # Level filter
            if level_filter and entry.level.numeric_value < level_filter.numeric_value:
                continue
            
            # Logger filter
            if logger_filter and not re.search(logger_filter, entry.logger_name):
                continue
            
            # Time range filter
            if start_time and entry.timestamp < start_time:
                continue
            
            if end_time and entry.timestamp > end_time:
                continue
            
            # Message filter
            if message_filter and not re.search(message_filter, entry.message):
                continue
            
            filtered.append(entry)
        
        return filtered
    
    async def aggregate_logs(
        self, 
        entries: List[LogEntry],
        group_by: str,
        time_window_minutes: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate log data by various dimensions.
        
        Args:
            entries: List of log entries
            group_by: Grouping dimension (level, logger_name, etc.)
            time_window_minutes: Time window for aggregation
            
        Returns:
            Aggregated log data
        """
        aggregation = {}
        
        for entry in entries:
            # Get grouping key
            if group_by == "level":
                key = entry.level.name
            elif group_by == "logger_name":
                key = entry.logger_name
            elif group_by == "module":
                key = entry.module or "unknown"
            else:
                key = "unknown"
            
            # Initialize aggregation for key
            if key not in aggregation:
                aggregation[key] = {
                    "count": 0,
                    "first_seen": entry.timestamp,
                    "last_seen": entry.timestamp,
                    "messages": []
                }
            
            # Update aggregation
            agg = aggregation[key]
            agg["count"] += 1
            
            if entry.timestamp < agg["first_seen"]:
                agg["first_seen"] = entry.timestamp
            
            if entry.timestamp > agg["last_seen"]:
                agg["last_seen"] = entry.timestamp
            
            # Store sample messages
            if len(agg["messages"]) < 10:
                agg["messages"].append(entry.message)
        
        return aggregation
    
    async def detect_patterns(
        self, 
        entries: List[LogEntry],
        pattern_types: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Detect patterns in log data.
        
        Args:
            entries: List of log entries
            pattern_types: Types of patterns to detect
            
        Returns:
            Detected patterns
        """
        patterns = {}
        
        if "error_bursts" in pattern_types:
            patterns["error_bursts"] = self._detect_error_bursts(entries)
        
        if "repeated_messages" in pattern_types:
            patterns["repeated_messages"] = self._detect_repeated_messages(entries)
        
        if "anomalies" in pattern_types:
            patterns["anomalies"] = self._detect_anomalies(entries)
        
        return patterns
    
    def _detect_error_bursts(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect error bursts in log entries.
        
        Args:
            entries: List of log entries
            
        Returns:
            List of detected error bursts
        """
        bursts = []
        error_entries = [e for e in entries if e.level >= LogLevel.ERROR]
        
        if len(error_entries) < 2:
            return bursts
        
        # Sort by timestamp
        error_entries.sort(key=lambda x: x.timestamp)
        
        # Detect bursts (2+ errors within 5 minutes)
        for i in range(len(error_entries) - 1):
            current = error_entries[i]
            next_error = error_entries[i + 1]
            
            time_diff = (next_error.timestamp - current.timestamp).total_seconds()
            if time_diff <= 300:  # 5 minutes
                bursts.append({
                    "start_time": current.timestamp,
                    "end_time": next_error.timestamp,
                    "error_count": 2,
                    "duration_seconds": time_diff
                })
        
        return bursts
    
    def _detect_repeated_messages(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect repeated messages.
        
        Args:
            entries: List of log entries
            
        Returns:
            List of repeated message patterns
        """
        message_counts = {}
        
        for entry in entries:
            message = entry.message.strip()
            if message not in message_counts:
                message_counts[message] = {
                    "count": 0,
                    "first_seen": entry.timestamp,
                    "last_seen": entry.timestamp,
                    "loggers": set()
                }
            
            info = message_counts[message]
            info["count"] += 1
            info["loggers"].add(entry.logger_name)
            
            if entry.timestamp < info["first_seen"]:
                info["first_seen"] = entry.timestamp
            if entry.timestamp > info["last_seen"]:
                info["last_seen"] = entry.timestamp
        
        # Return messages that appear more than 5 times
        repeated = []
        for message, info in message_counts.items():
            if info["count"] > 5:
                repeated.append({
                    "message": message,
                    "count": info["count"],
                    "first_seen": info["first_seen"],
                    "last_seen": info["last_seen"],
                    "unique_loggers": len(info["loggers"])
                })
        
        return repeated
    
    def _detect_anomalies(self, entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns.
        
        Args:
            entries: List of log entries
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Simple anomaly detection: unusually high error rates
        if len(entries) > 100:
            error_count = sum(1 for e in entries if e.level >= LogLevel.ERROR)
            error_rate = error_count / len(entries)
            
            if error_rate > 0.1:  # More than 10% errors
                anomalies.append({
                    "type": "high_error_rate",
                    "error_rate": error_rate,
                    "threshold": 0.1,
                    "total_entries": len(entries),
                    "error_entries": error_count
                })
        
        return anomalies
    
    async def extract_metrics(self, entries: List[LogEntry]) -> LogMetrics:
        """Extract metrics from log entries.
        
        Args:
            entries: List of log entries
            
        Returns:
            Extracted metrics
        """
        total_entries = len(entries)
        
        if total_entries == 0:
            return LogMetrics(total_entries=0)
        
        # Count by level
        debug_count = sum(1 for e in entries if e.level == LogLevel.DEBUG)
        info_count = sum(1 for e in entries if e.level == LogLevel.INFO)
        warning_count = sum(1 for e in entries if e.level == LogLevel.WARNING)
        error_count = sum(1 for e in entries if e.level == LogLevel.ERROR)
        critical_count = sum(1 for e in entries if e.level == LogLevel.CRITICAL)
        
        error_rate = (error_count + critical_count) / total_entries
        
        # Top loggers
        logger_counts = {}
        for entry in entries:
            logger_counts[entry.logger_name] = logger_counts.get(entry.logger_name, 0) + 1
        
        top_loggers = [
            {"logger": logger, "count": count}
            for logger, count in sorted(logger_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Top errors
        error_messages = {}
        for entry in entries:
            if entry.level >= LogLevel.ERROR:
                msg = entry.message[:100]  # Truncate for grouping
                error_messages[msg] = error_messages.get(msg, 0) + 1
        
        top_errors = [
            {"message": message, "count": count}
            for message, count in sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Time range
        if entries:
            timestamps = [e.timestamp for e in entries]
            time_range = {
                "start": min(timestamps),
                "end": max(timestamps)
            }
        else:
            time_range = None
        
        return LogMetrics(
            total_entries=total_entries,
            debug_count=debug_count,
            info_count=info_count,
            warning_count=warning_count,
            error_count=error_count,
            critical_count=critical_count,
            error_rate=error_rate,
            top_loggers=top_loggers,
            top_errors=top_errors,
            time_range=time_range
        )