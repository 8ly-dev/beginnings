"""Configuration for auto-reload system."""

from __future__ import annotations

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ReloadConfig:
    """Configuration for auto-reload system."""
    
    enabled: bool = False
    watch_paths: List[str] = field(default_factory=lambda: ["."])
    include_patterns: List[str] = field(default_factory=lambda: [
        "*.py", "*.yaml", "*.yml", "*.json", "*.toml"
    ])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.pyc", "*.pyo", "*.pyd", "__pycache__/*", ".git/*", 
        ".pytest_cache/*", "*.log", "*.tmp", "*.swp", "*.swo"
    ])
    reload_delay: float = 1.0
    use_polling: bool = False
    max_reload_attempts: int = 3
    graceful_shutdown_timeout: float = 5.0
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if self.reload_delay <= 0:
            raise ValueError("reload_delay must be positive")
        
        if not self.watch_paths:
            raise ValueError("watch_paths cannot be empty")
        
        if not self.include_patterns:
            raise ValueError("include_patterns cannot be empty")
        
        if self.max_reload_attempts < 1:
            raise ValueError("max_reload_attempts must be at least 1")
        
        if self.graceful_shutdown_timeout < 0:
            raise ValueError("graceful_shutdown_timeout must be non-negative")
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> ReloadConfig:
        """Create ReloadConfig from dictionary.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            ReloadConfig instance
        """
        auto_reload_config = config_data.get("auto_reload", {})
        
        return cls(
            enabled=auto_reload_config.get("enabled", False),
            watch_paths=auto_reload_config.get("watch_paths", ["."]),
            include_patterns=auto_reload_config.get("include_patterns", [
                "*.py", "*.yaml", "*.yml", "*.json", "*.toml"
            ]),
            exclude_patterns=auto_reload_config.get("exclude_patterns", [
                "*.pyc", "*.pyo", "*.pyd", "__pycache__/*", ".git/*", 
                ".pytest_cache/*", "*.log", "*.tmp", "*.swp", "*.swo"
            ]),
            reload_delay=auto_reload_config.get("reload_delay", 1.0),
            use_polling=auto_reload_config.get("use_polling", False),
            max_reload_attempts=auto_reload_config.get("max_reload_attempts", 3),
            graceful_shutdown_timeout=auto_reload_config.get("graceful_shutdown_timeout", 5.0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ReloadConfig to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            "auto_reload": {
                "enabled": self.enabled,
                "watch_paths": self.watch_paths,
                "include_patterns": self.include_patterns,
                "exclude_patterns": self.exclude_patterns,
                "reload_delay": self.reload_delay,
                "use_polling": self.use_polling,
                "max_reload_attempts": self.max_reload_attempts,
                "graceful_shutdown_timeout": self.graceful_shutdown_timeout
            }
        }
    
    def get_effective_patterns(self) -> tuple[List[str], List[str]]:
        """Get effective include and exclude patterns.
        
        Returns:
            Tuple of (include_patterns, exclude_patterns)
        """
        return self.include_patterns.copy(), self.exclude_patterns.copy()
    
    def should_watch_file(self, file_path: str) -> bool:
        """Check if a file should be watched based on patterns.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be watched
        """
        import fnmatch
        
        # Check if file matches include patterns
        matches_include = any(
            fnmatch.fnmatch(file_path, pattern)
            for pattern in self.include_patterns
        )
        
        if not matches_include:
            return False
        
        # Check if file matches exclude patterns
        matches_exclude = any(
            fnmatch.fnmatch(file_path, pattern)
            for pattern in self.exclude_patterns
        )
        
        return not matches_exclude