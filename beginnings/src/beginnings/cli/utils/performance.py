"""Performance optimization utilities for CLI operations."""

import time
import functools
import importlib
from typing import Dict, Any, Optional, Callable, List
from threading import Lock
from pathlib import Path

# Global caches
_import_cache: Dict[str, Any] = {}
_path_cache: Dict[str, bool] = {}
_config_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = Lock()

# Performance settings
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_CACHE_SIZE = 1000


class LazyImporter:
    """Lazy import utility to speed up CLI startup."""
    
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._importers: Dict[str, Callable] = {}
    
    def register(self, name: str, import_func: Callable):
        """Register a lazy import function.
        
        Args:
            name: Module name
            import_func: Function that returns the imported module
        """
        self._importers[name] = import_func
    
    def get(self, name: str):
        """Get a lazily imported module.
        
        Args:
            name: Module name
            
        Returns:
            Imported module
        """
        if name not in self._modules:
            if name in self._importers:
                self._modules[name] = self._importers[name]()
            else:
                raise ImportError(f"No lazy importer registered for {name}")
        
        return self._modules[name]


# Global lazy importer instance
lazy_import = LazyImporter()


def setup_lazy_imports():
    """Set up common lazy imports for CLI performance."""
    
    # Register heavy imports that should be loaded on demand
    lazy_import.register("yaml", lambda: importlib.import_module("yaml"))
    lazy_import.register("jinja2", lambda: importlib.import_module("jinja2"))
    lazy_import.register("watchdog", lambda: importlib.import_module("watchdog"))
    lazy_import.register("psutil", lambda: importlib.import_module("psutil"))
    lazy_import.register("fastapi", lambda: importlib.import_module("fastapi"))
    lazy_import.register("uvicorn", lambda: importlib.import_module("uvicorn"))


def performance_timer(func):
    """Decorator to measure function execution time."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Only log slow operations (>100ms)
            if execution_time > 100:
                print(f"Performance: {func.__name__} took {execution_time:.2f}ms")
    
    return wrapper


def cached_path_exists(path: str, ttl_seconds: int = CACHE_TTL_SECONDS) -> bool:
    """Cached version of path existence check.
    
    Args:
        path: Path to check
        ttl_seconds: Cache time-to-live in seconds
        
    Returns:
        True if path exists, False otherwise
    """
    with _cache_lock:
        cache_key = f"path_exists:{path}"
        current_time = time.time()
        
        # Check if we have a cached result
        if cache_key in _path_cache:
            cached_time, exists = _path_cache[cache_key]
            if current_time - cached_time < ttl_seconds:
                return exists
        
        # Check path existence and cache result
        exists = Path(path).exists()
        _path_cache[cache_key] = (current_time, exists)
        
        # Clean cache if it gets too large
        if len(_path_cache) > MAX_CACHE_SIZE:
            # Remove oldest entries
            sorted_items = sorted(_path_cache.items(), key=lambda x: x[1][0])
            for key, _ in sorted_items[:MAX_CACHE_SIZE // 2]:
                del _path_cache[key]
        
        return exists


def cached_file_mtime(path: str, ttl_seconds: int = CACHE_TTL_SECONDS) -> Optional[float]:
    """Cached version of file modification time check.
    
    Args:
        path: Path to check
        ttl_seconds: Cache time-to-live in seconds
        
    Returns:
        Modification time or None if file doesn't exist
    """
    with _cache_lock:
        cache_key = f"file_mtime:{path}"
        current_time = time.time()
        
        # Check if we have a cached result
        if cache_key in _path_cache:
            cached_time, mtime = _path_cache[cache_key]
            if current_time - cached_time < ttl_seconds:
                return mtime
        
        # Get file mtime and cache result
        try:
            mtime = Path(path).stat().st_mtime
        except (OSError, FileNotFoundError):
            mtime = None
        
        _path_cache[cache_key] = (current_time, mtime)
        
        return mtime


def cached_config_load(config_path: str, ttl_seconds: int = CACHE_TTL_SECONDS) -> Optional[Dict[str, Any]]:
    """Cached configuration file loading.
    
    Args:
        config_path: Path to configuration file
        ttl_seconds: Cache time-to-live in seconds
        
    Returns:
        Loaded configuration or None if file doesn't exist
    """
    with _cache_lock:
        current_time = time.time()
        
        # Check if we have a cached result
        if config_path in _config_cache:
            cached_time, config_data = _config_cache[config_path]
            if current_time - cached_time < ttl_seconds:
                # Verify file hasn't changed
                try:
                    current_mtime = Path(config_path).stat().st_mtime
                    if current_mtime == config_data.get('_mtime'):
                        return config_data.get('data')
                except (OSError, FileNotFoundError):
                    pass
        
        # Load configuration file
        try:
            yaml = lazy_import.get("yaml")
            path_obj = Path(config_path)
            
            if not path_obj.exists():
                return None
            
            mtime = path_obj.stat().st_mtime
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Cache the result with metadata
            _config_cache[config_path] = (current_time, {
                'data': config_data,
                '_mtime': mtime
            })
            
            # Clean cache if it gets too large
            if len(_config_cache) > MAX_CACHE_SIZE:
                # Remove oldest entries
                sorted_items = sorted(_config_cache.items(), key=lambda x: x[1][0])
                for key, _ in sorted_items[:MAX_CACHE_SIZE // 2]:
                    del _config_cache[key]
            
            return config_data
            
        except Exception:
            return None


def batch_path_operations(paths: List[str]) -> Dict[str, bool]:
    """Batch multiple path existence checks for better performance.
    
    Args:
        paths: List of paths to check
        
    Returns:
        Dictionary mapping paths to their existence status
    """
    results = {}
    
    # Check cached results first
    uncached_paths = []
    with _cache_lock:
        current_time = time.time()
        for path in paths:
            cache_key = f"path_exists:{path}"
            if cache_key in _path_cache:
                cached_time, exists = _path_cache[cache_key]
                if current_time - cached_time < CACHE_TTL_SECONDS:
                    results[path] = exists
                    continue
            uncached_paths.append(path)
    
    # Batch check uncached paths
    for path in uncached_paths:
        exists = Path(path).exists()
        results[path] = exists
        
        # Cache the result
        with _cache_lock:
            cache_key = f"path_exists:{path}"
            _path_cache[cache_key] = (time.time(), exists)
    
    return results


def optimize_click_imports():
    """Optimize Click command imports for faster startup."""
    
    # Pre-import commonly used Click components
    import click
    
    # Pre-compile commonly used decorators
    _click_decorators = {
        'command': click.command,
        'group': click.group,
        'option': click.option,
        'argument': click.argument,
        'pass_context': click.pass_context,
        'pass_obj': click.pass_obj
    }
    
    return _click_decorators


def clear_performance_caches():
    """Clear all performance caches."""
    global _import_cache, _path_cache, _config_cache
    
    with _cache_lock:
        _import_cache.clear()
        _path_cache.clear()
        _config_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about cache usage.
    
    Returns:
        Dictionary with cache statistics
    """
    with _cache_lock:
        return {
            'import_cache_size': len(_import_cache),
            'path_cache_size': len(_path_cache),
            'config_cache_size': len(_config_cache),
            'total_cached_items': len(_import_cache) + len(_path_cache) + len(_config_cache)
        }


class FastCommandLoader:
    """Fast command loader that delays command registration until needed."""
    
    def __init__(self):
        self._command_registry: Dict[str, Callable] = {}
        self._loaded_commands: Dict[str, Any] = {}
    
    def register_command(self, name: str, loader_func: Callable):
        """Register a command loader.
        
        Args:
            name: Command name
            loader_func: Function that returns the command
        """
        self._command_registry[name] = loader_func
    
    def get_command(self, name: str):
        """Get a command, loading it if necessary.
        
        Args:
            name: Command name
            
        Returns:
            Click command object
        """
        if name not in self._loaded_commands:
            if name in self._command_registry:
                self._loaded_commands[name] = self._command_registry[name]()
            else:
                raise ValueError(f"No loader registered for command {name}")
        
        return self._loaded_commands[name]
    
    def preload_essential_commands(self):
        """Preload essential commands for better user experience."""
        essential_commands = ['new', 'run', 'config']
        
        for cmd_name in essential_commands:
            if cmd_name in self._command_registry:
                try:
                    self.get_command(cmd_name)
                except Exception:
                    # Don't fail startup if preloading fails
                    pass


# Global command loader
fast_loader = FastCommandLoader()


def setup_performance_optimizations():
    """Set up all performance optimizations."""
    setup_lazy_imports()
    optimize_click_imports()
    fast_loader.preload_essential_commands()


class PerformanceContext:
    """Context manager for performance monitoring."""
    
    def __init__(self, operation_name: str, threshold_ms: float = 100):
        self.operation_name = operation_name
        self.threshold_ms = threshold_ms
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            if duration_ms > self.threshold_ms:
                print(f"Performance: {self.operation_name} took {duration_ms:.2f}ms")


def monitor_performance(operation_name: str, threshold_ms: float = 100):
    """Decorator for monitoring operation performance.
    
    Args:
        operation_name: Name of the operation
        threshold_ms: Threshold in milliseconds for logging
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceContext(operation_name, threshold_ms):
                return func(*args, **kwargs)
        return wrapper
    return decorator