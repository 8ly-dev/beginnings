"""Hot reload manager for live code updates."""

from __future__ import annotations

import time
import importlib
import sys
from pathlib import Path
from typing import List, Optional, Callable, Dict, Set, Any
from threading import Thread, Event

from .watcher import FileChangeEvent, create_file_watcher


class ModuleReloader:
    """Manages reloading of Python modules."""
    
    def __init__(self):
        self.module_mtimes: Dict[str, float] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
    
    def reload_module(self, module_name: str) -> bool:
        """Reload a specific module.
        
        Args:
            module_name: Name of module to reload
            
        Returns:
            True if reload was successful
        """
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                importlib.reload(module)
                print(f"Reloaded module: {module_name}")
                return True
            else:
                print(f"Module not loaded: {module_name}")
                return False
        except Exception as e:
            print(f"Failed to reload module {module_name}: {e}")
            return False
    
    def reload_module_from_file(self, file_path: str) -> bool:
        """Reload module based on file path.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            True if reload was successful
        """
        module_name = self._file_path_to_module_name(file_path)
        if module_name:
            return self.reload_module(module_name)
        return False
    
    def _file_path_to_module_name(self, file_path: str) -> Optional[str]:
        """Convert file path to module name."""
        try:
            path = Path(file_path).resolve()
            
            # Find the module name by checking sys.modules
            for module_name, module in sys.modules.items():
                if hasattr(module, '__file__') and module.__file__:
                    module_path = Path(module.__file__).resolve()
                    if module_path == path:
                        return module_name
            
            return None
        except Exception:
            return None
    
    def get_dependent_modules(self, module_name: str) -> Set[str]:
        """Get modules that depend on the given module."""
        dependents = set()
        
        for name, deps in self.dependency_graph.items():
            if module_name in deps:
                dependents.add(name)
        
        return dependents
    
    def build_dependency_graph(self):
        """Build dependency graph of loaded modules."""
        self.dependency_graph.clear()
        
        for module_name, module in sys.modules.items():
            if not hasattr(module, '__file__') or not module.__file__:
                continue
            
            dependencies = set()
            
            # Simple dependency detection based on imports
            # This is a basic implementation - more sophisticated
            # dependency tracking could be added
            if hasattr(module, '__dict__'):
                for attr_name, attr_value in module.__dict__.items():
                    if hasattr(attr_value, '__module__'):
                        dep_module = attr_value.__module__
                        if dep_module and dep_module in sys.modules:
                            dependencies.add(dep_module)
            
            self.dependency_graph[module_name] = dependencies


class HotReloadManager:
    """Manages hot reloading of application components."""
    
    def __init__(
        self,
        watch_paths: List[str],
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        reload_callback: Optional[Callable[[str, str], None]] = None
    ):
        """Initialize hot reload manager.
        
        Args:
            watch_paths: Paths to watch for changes
            include_patterns: File patterns to include
            exclude_patterns: File patterns to exclude
            reload_callback: Callback for reload events (change_type, file_path)
        """
        self.watch_paths = watch_paths
        self.include_patterns = include_patterns or ['*.py', '*.yaml', '*.yml']
        self.exclude_patterns = exclude_patterns or [
            '*.pyc', '__pycache__/*', '.git/*'
        ]
        self.reload_callback = reload_callback
        
        self.module_reloader = ModuleReloader()
        self.watchers: List = []
        self.monitoring = False
        self.stop_event = Event()
        
        # Track file modification times to avoid duplicate reloads
        self.file_mtimes: Dict[str, float] = {}
        
    def start_monitoring(self):
        """Start monitoring files for changes."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.stop_event.clear()
        
        # Build initial dependency graph
        self.module_reloader.build_dependency_graph()
        
        # Start watchers for each path
        for watch_path in self.watch_paths:
            try:
                watcher = create_file_watcher(
                    path=watch_path,
                    patterns=self.include_patterns,
                    ignore_patterns=self.exclude_patterns,
                    callback=self._on_file_changed
                )
                
                watcher_thread = Thread(
                    target=watcher.start_watching,
                    daemon=True
                )
                watcher_thread.start()
                
                self.watchers.append((watcher, watcher_thread))
                
            except Exception as e:
                print(f"Failed to start hot reload watcher for {watch_path}: {e}")
        
        print(f"Hot reload monitoring started for {len(self.watchers)} paths")
    
    def stop_monitoring(self):
        """Stop monitoring files for changes."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        
        # Stop all watchers
        for watcher, thread in self.watchers:
            try:
                watcher.stop_watching()
            except Exception as e:
                print(f"Error stopping hot reload watcher: {e}")
        
        self.watchers.clear()
        print("Hot reload monitoring stopped")
    
    def _on_file_changed(self, event: FileChangeEvent):
        """Handle file change events."""
        if not self.monitoring or self.stop_event.is_set():
            return
        
        file_path = event.file_path
        
        # Check if we've already processed this file recently
        current_time = time.time()
        if file_path in self.file_mtimes:
            if current_time - self.file_mtimes[file_path] < 1.0:  # 1 second debounce
                return
        
        self.file_mtimes[file_path] = current_time
        
        # Handle different file types
        if file_path.endswith('.py'):
            self._handle_python_file_change(file_path, event.event_type)
        elif file_path.endswith(('.yaml', '.yml', '.json')):
            self._handle_config_file_change(file_path, event.event_type)
        
        # Notify callback
        if self.reload_callback:
            try:
                self.reload_callback(event.event_type, file_path)
            except Exception as e:
                print(f"Error in reload callback: {e}")
    
    def _handle_python_file_change(self, file_path: str, change_type: str):
        """Handle changes to Python files."""
        if change_type in ['modified', 'created']:
            print(f"Python file {change_type}: {file_path}")
            
            # Try to reload the module
            success = self.module_reloader.reload_module_from_file(file_path)
            
            if success:
                # Rebuild dependency graph after successful reload
                self.module_reloader.build_dependency_graph()
                print(f"Successfully hot-reloaded: {file_path}")
            else:
                print(f"Hot reload failed for: {file_path}")
        
        elif change_type == 'deleted':
            print(f"Python file deleted: {file_path}")
            # Handle module cleanup if needed
    
    def _handle_config_file_change(self, file_path: str, change_type: str):
        """Handle changes to configuration files."""
        if change_type in ['modified', 'created']:
            print(f"Configuration file {change_type}: {file_path}")
            
            # Configuration changes typically require application restart
            # This could be enhanced to reload specific config sections
            print(f"Configuration change detected: {file_path}")
            print("Note: Configuration changes may require application restart")
        
        elif change_type == 'deleted':
            print(f"Configuration file deleted: {file_path}")
    
    def set_reload_callback(self, callback: Callable[[str, str], None]):
        """Set callback for reload events.
        
        Args:
            callback: Function to call on reload (change_type, file_path)
        """
        self.reload_callback = callback
    
    def force_reload_module(self, module_name: str) -> bool:
        """Force reload of a specific module.
        
        Args:
            module_name: Name of module to reload
            
        Returns:
            True if reload was successful
        """
        return self.module_reloader.reload_module(module_name)
    
    def get_watched_files(self) -> List[str]:
        """Get list of files being watched."""
        watched_files = []
        
        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if path.is_file():
                watched_files.append(str(path))
            elif path.is_dir():
                for pattern in self.include_patterns:
                    watched_files.extend(str(p) for p in path.rglob(pattern))
        
        return watched_files
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status.
        
        Returns:
            Dictionary with monitoring information
        """
        return {
            'monitoring': self.monitoring,
            'watch_paths': self.watch_paths,
            'include_patterns': self.include_patterns,
            'exclude_patterns': self.exclude_patterns,
            'active_watchers': len(self.watchers),
            'tracked_files': len(self.file_mtimes),
            'loaded_modules': len(sys.modules)
        }


def create_hot_reload_manager(
    watch_paths: List[str],
    patterns: List[str] = None,
    ignore_patterns: List[str] = None
) -> HotReloadManager:
    """Create hot reload manager with default settings.
    
    Args:
        watch_paths: Paths to watch
        patterns: File patterns to include
        ignore_patterns: File patterns to ignore
        
    Returns:
        HotReloadManager instance
    """
    return HotReloadManager(
        watch_paths=watch_paths,
        include_patterns=patterns or ['*.py', '*.yaml', '*.yml'],
        exclude_patterns=ignore_patterns or [
            '*.pyc', '*.pyo', '__pycache__/*', '.git/*', '*.log'
        ]
    )