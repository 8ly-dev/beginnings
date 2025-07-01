"""Log manager for comprehensive logging system."""

from __future__ import annotations

import asyncio
import json
import time
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

from .enums import LogLevel, LogFormat
from .models import LogConfig, LogEntry, LogResult
from .exceptions import LoggingError


class LogManager:
    """Manager for log configuration and processing."""
    
    def __init__(self):
        """Initialize log manager."""
        self._loggers: Dict[str, logging.Logger] = {}
        self._configs: Dict[str, LogConfig] = {}
        self._log_queues: Dict[str, asyncio.Queue] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize_logging(self, config: LogConfig) -> LogResult:
        """Initialize logging configuration.
        
        Args:
            config: Logging configuration
            
        Returns:
            Initialization result
        """
        try:
            # Validate configuration
            errors = config.validate()
            if errors:
                return LogResult(
                    success=False,
                    message=f"Configuration validation failed: {', '.join(errors)}"
                )
            
            # Create logger
            logger = logging.getLogger(config.name)
            logger.setLevel(config.level.numeric_value)
            
            # Clear existing handlers
            logger.handlers.clear()
            
            # Create file handler with rotation
            output_path = Path(config.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if config.max_file_size_mb > 0 and config.backup_count > 0:
                handler = logging.handlers.RotatingFileHandler(
                    filename=str(output_path),
                    maxBytes=config.max_file_size_mb * 1024 * 1024,
                    backupCount=config.backup_count
                )
            else:
                handler = logging.FileHandler(str(output_path))
            
            # Set formatter based on format
            if config.format == LogFormat.JSON:
                formatter = JsonFormatter()
            elif config.format == LogFormat.STRUCTURED:
                formatter = StructuredFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Store configuration and logger
            self._configs[config.name] = config
            self._loggers[config.name] = logger
            
            # Setup async processing if enabled
            if config.async_logging:
                self._log_queues[config.name] = asyncio.Queue(maxsize=config.buffer_size)
                self._processing_tasks[config.name] = asyncio.create_task(
                    self._process_log_queue(config.name)
                )
            
            return LogResult(
                success=True,
                logger_name=config.name,
                output_file=config.output_file,
                level=config.level,
                message=f"Logging initialized for '{config.name}'"
            )
            
        except Exception as e:
            return LogResult(
                success=False,
                message=f"Failed to initialize logging: {str(e)}"
            )
    
    async def log(
        self, 
        level: LogLevel, 
        message: str, 
        logger_name: str = "default",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        exception_info: Optional[Dict[str, Any]] = None
    ) -> LogResult:
        """Log a message.
        
        Args:
            level: Log level
            message: Log message
            logger_name: Name of logger to use
            context: Additional context data
            trace_id: Trace ID for distributed tracing
            span_id: Span ID for distributed tracing
            exception_info: Exception information
            
        Returns:
            Logging result
        """
        start_time = time.time()
        
        try:
            # Get logger and config
            if logger_name not in self._loggers:
                return LogResult(
                    success=False,
                    message=f"Logger '{logger_name}' not found"
                )
            
            logger = self._loggers[logger_name]
            config = self._configs[logger_name]
            
            # Check if message should be filtered
            if not self._should_log(config, level, logger_name, message):
                return LogResult(
                    success=True,
                    logger_name=logger_name,
                    message="Message filtered"
                )
            
            # Create log entry
            log_entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=level,
                message=message,
                logger_name=logger_name,
                context=context or {},
                trace_id=trace_id,
                span_id=span_id,
                exception_info=exception_info
            )
            
            # Process log entry
            if config.async_logging and logger_name in self._log_queues:
                # Add to async queue
                try:
                    self._log_queues[logger_name].put_nowait(log_entry)
                except asyncio.QueueFull:
                    # Fallback to synchronous logging
                    self._write_log_entry(logger, log_entry, config)
            else:
                # Synchronous logging
                self._write_log_entry(logger, log_entry, config)
            
            processing_time = (time.time() - start_time) * 1000
            
            return LogResult(
                success=True,
                logger_name=logger_name,
                log_entry=log_entry,
                processing_time_ms=processing_time,
                message="Log entry processed successfully"
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return LogResult(
                success=False,
                logger_name=logger_name,
                processing_time_ms=processing_time,
                message=f"Failed to log message: {str(e)}"
            )
    
    def _should_log(self, config: LogConfig, level: LogLevel, logger_name: str, message: str) -> bool:
        """Check if message should be logged based on filters.
        
        Args:
            config: Log configuration
            level: Log level
            logger_name: Logger name
            message: Log message
            
        Returns:
            True if message should be logged
        """
        # Level filter
        if level.numeric_value < config.level.numeric_value:
            return False
        
        # Module filters
        if config.include_modules:
            module_parts = logger_name.split('.')
            if not any(module in module_parts for module in config.include_modules):
                return False
        
        if config.exclude_modules:
            module_parts = logger_name.split('.')
            if any(module in module_parts for module in config.exclude_modules):
                return False
        
        # Logger filters
        if config.include_loggers:
            import re
            if not any(re.match(pattern, logger_name) for pattern in config.include_loggers):
                return False
        
        if config.exclude_loggers:
            import re
            if any(re.match(pattern, logger_name) for pattern in config.exclude_loggers):
                return False
        
        return True
    
    def _write_log_entry(self, logger: logging.Logger, entry: LogEntry, config: LogConfig):
        """Write log entry to logger.
        
        Args:
            logger: Logger instance
            entry: Log entry to write
            config: Log configuration
        """
        # Create log record
        if config.structured_logging:
            # Use structured data
            extra = {
                'structured_data': entry.to_dict(),
                'trace_id': entry.trace_id,
                'span_id': entry.span_id,
                'context': entry.context
            }
        else:
            extra = {}
        
        # Log the message
        logger.log(entry.level.numeric_value, entry.message, extra=extra)
    
    async def _process_log_queue(self, logger_name: str):
        """Process async log queue.
        
        Args:
            logger_name: Name of logger
        """
        try:
            logger = self._loggers[logger_name]
            config = self._configs[logger_name]
            queue = self._log_queues[logger_name]
            
            while True:
                try:
                    # Get log entry from queue
                    log_entry = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Write to logger
                    self._write_log_entry(logger, log_entry, config)
                    
                    # Mark task as done
                    queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Continue processing
                    continue
                except Exception as e:
                    # Log error and continue
                    print(f"Error processing log queue for {logger_name}: {e}")
                    
        except asyncio.CancelledError:
            # Cleanup
            pass
    
    async def shutdown(self):
        """Shutdown log manager and cleanup resources."""
        try:
            # Cancel processing tasks
            for task in self._processing_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self._processing_tasks:
                await asyncio.gather(*self._processing_tasks.values(), return_exceptions=True)
            
            # Clear resources
            self._loggers.clear()
            self._configs.clear()
            self._log_queues.clear()
            self._processing_tasks.clear()
            
        except Exception as e:
            print(f"Error during log manager shutdown: {e}")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module if hasattr(record, 'module') else None,
            'function': record.funcName if hasattr(record, 'funcName') else None,
            'line': record.lineno if hasattr(record, 'lineno') else None
        }
        
        # Add structured data if available
        if hasattr(record, 'structured_data'):
            log_data.update(record.structured_data)
        
        # Add trace information
        if hasattr(record, 'trace_id') and record.trace_id:
            log_data['trace_id'] = record.trace_id
        
        if hasattr(record, 'span_id') and record.span_id:
            log_data['span_id'] = record.span_id
        
        # Add context
        if hasattr(record, 'context') and record.context:
            log_data['context'] = record.context
        
        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """Structured formatter for human-readable structured logs."""
    
    def format(self, record):
        """Format log record with structured data."""
        base_format = f"{datetime.utcnow().isoformat()} [{record.levelname}] {record.name}: {record.getMessage()}"
        
        # Add structured data
        if hasattr(record, 'context') and record.context:
            context_str = ", ".join(f"{k}={v}" for k, v in record.context.items())
            base_format += f" | {context_str}"
        
        if hasattr(record, 'trace_id') and record.trace_id:
            base_format += f" | trace_id={record.trace_id}"
        
        return base_format