"""Configuration for debugging system."""

from __future__ import annotations

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DebugConfig:
    """Configuration for debugging system."""
    
    enabled: bool = False
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8000
    enable_profiler: bool = False
    enable_request_tracking: bool = True
    enable_performance_monitoring: bool = True
    enable_error_tracking: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    max_log_lines: int = 500
    enable_websocket_streaming: bool = True
    
    # Profiling configuration
    enable_cpu_profiling: bool = False
    enable_memory_profiling: bool = False
    profile_threshold_ms: float = 50.0
    max_profile_history: int = 100
    
    # Request tracking configuration
    max_request_history: int = 200
    track_request_headers: bool = True
    track_response_headers: bool = True
    track_request_body: bool = False  # Security: disabled by default
    track_response_body: bool = False  # Performance: disabled by default
    
    # Dashboard configuration
    dashboard_title: str = "Beginnings Debug Dashboard"
    enable_real_time_updates: bool = True
    update_interval_ms: int = 1000
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if not (1 <= self.dashboard_port <= 65535):
            raise ValueError("Dashboard port must be between 1 and 65535")
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}")
        
        if self.profile_threshold_ms <= 0:
            raise ValueError("profile_threshold_ms must be positive")
        
        if self.max_log_lines <= 0:
            raise ValueError("max_log_lines must be positive")
        
        if self.max_request_history <= 0:
            raise ValueError("max_request_history must be positive")
        
        if self.max_profile_history <= 0:
            raise ValueError("max_profile_history must be positive")
        
        if self.update_interval_ms <= 0:
            raise ValueError("update_interval_ms must be positive")
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> DebugConfig:
        """Create DebugConfig from dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            DebugConfig instance
        """
        debug_config = config_data.get("debug", {})
        dashboard_config = debug_config.get("dashboard", {})
        logging_config = debug_config.get("logging", {})
        profiling_config = debug_config.get("profiling", {})
        
        return cls(
            enabled=debug_config.get("enabled", False),
            dashboard_host=dashboard_config.get("host", "127.0.0.1"),
            dashboard_port=dashboard_config.get("port", 8000),
            enable_profiler=dashboard_config.get("enable_profiler", False),
            enable_request_tracking=dashboard_config.get("enable_request_tracking", True),
            enable_performance_monitoring=dashboard_config.get("enable_performance_monitoring", True),
            enable_error_tracking=dashboard_config.get("enable_error_tracking", True),
            
            log_level=logging_config.get("level", "INFO"),
            max_log_lines=logging_config.get("max_lines", 500),
            enable_websocket_streaming=logging_config.get("enable_websocket_streaming", True),
            
            enable_cpu_profiling=profiling_config.get("enable_cpu_profiling", False),
            enable_memory_profiling=profiling_config.get("enable_memory_profiling", False),
            profile_threshold_ms=profiling_config.get("profile_threshold_ms", 50.0),
            max_profile_history=profiling_config.get("max_profile_history", 100),
            
            max_request_history=debug_config.get("max_request_history", 200),
            track_request_headers=debug_config.get("track_request_headers", True),
            track_response_headers=debug_config.get("track_response_headers", True),
            track_request_body=debug_config.get("track_request_body", False),
            track_response_body=debug_config.get("track_response_body", False),
            
            dashboard_title=dashboard_config.get("title", "Beginnings Debug Dashboard"),
            enable_real_time_updates=dashboard_config.get("enable_real_time_updates", True),
            update_interval_ms=dashboard_config.get("update_interval_ms", 1000)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DebugConfig to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "debug": {
                "enabled": self.enabled,
                "dashboard": {
                    "host": self.dashboard_host,
                    "port": self.dashboard_port,
                    "enable_profiler": self.enable_profiler,
                    "enable_request_tracking": self.enable_request_tracking,
                    "enable_performance_monitoring": self.enable_performance_monitoring,
                    "enable_error_tracking": self.enable_error_tracking,
                    "title": self.dashboard_title,
                    "enable_real_time_updates": self.enable_real_time_updates,
                    "update_interval_ms": self.update_interval_ms
                },
                "logging": {
                    "level": self.log_level,
                    "max_lines": self.max_log_lines,
                    "enable_websocket_streaming": self.enable_websocket_streaming
                },
                "profiling": {
                    "enable_cpu_profiling": self.enable_cpu_profiling,
                    "enable_memory_profiling": self.enable_memory_profiling,
                    "profile_threshold_ms": self.profile_threshold_ms,
                    "max_profile_history": self.max_profile_history
                },
                "max_request_history": self.max_request_history,
                "track_request_headers": self.track_request_headers,
                "track_response_headers": self.track_response_headers,
                "track_request_body": self.track_request_body,
                "track_response_body": self.track_response_body
            }
        }
    
    def get_dashboard_url(self) -> str:
        """Get the dashboard URL.
        
        Returns:
            Dashboard URL string
        """
        return f"http://{self.dashboard_host}:{self.dashboard_port}"
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a debug feature is enabled.
        
        Args:
            feature: Feature name to check
            
        Returns:
            True if feature is enabled
        """
        feature_map = {
            "profiler": self.enable_profiler,
            "request_tracking": self.enable_request_tracking,
            "performance_monitoring": self.enable_performance_monitoring,
            "error_tracking": self.enable_error_tracking,
            "cpu_profiling": self.enable_cpu_profiling,
            "memory_profiling": self.enable_memory_profiling,
            "websocket_streaming": self.enable_websocket_streaming,
            "real_time_updates": self.enable_real_time_updates
        }
        
        return self.enabled and feature_map.get(feature, False)