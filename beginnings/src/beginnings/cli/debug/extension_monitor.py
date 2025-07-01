"""Extension status monitoring for debugging."""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from threading import RLock


class ExtensionDependencyTracker:
    """Tracks extension dependencies and loading status."""
    
    def __init__(self, max_history: int = 500):
        """Initialize extension dependency tracker.
        
        Args:
            max_history: Maximum number of events to keep in history
        """
        self.max_history = max_history
        self._extensions: Dict[str, Dict[str, Any]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._loading_events: List[Dict[str, Any]] = []
        self._lock = RLock()
    
    def register_extension(
        self, 
        name: str, 
        version: str = None,
        dependencies: List[str] = None,
        config: Dict[str, Any] = None,
        file_path: str = None
    ) -> None:
        """Register an extension.
        
        Args:
            name: Extension name
            version: Extension version
            dependencies: List of required extensions
            config: Extension configuration
            file_path: Path to extension file
        """
        with self._lock:
            self._extensions[name] = {
                "name": name,
                "version": version,
                "dependencies": dependencies or [],
                "config": config or {},
                "file_path": file_path,
                "status": "registered",
                "registration_time": time.time(),
                "loading_time": None,
                "error": None,
                "hot_reload_count": 0,
                "config_validation": None
            }
            
            # Update dependency graph
            self._dependency_graph[name] = set(dependencies or [])
            
            self._add_event("registered", name, {"version": version, "dependencies": dependencies})
    
    def start_extension_loading(self, name: str) -> None:
        """Mark extension as starting to load.
        
        Args:
            name: Extension name
        """
        with self._lock:
            if name in self._extensions:
                self._extensions[name]["status"] = "loading"
                self._extensions[name]["loading_start_time"] = time.time()
                self._add_event("loading_started", name)
    
    def complete_extension_loading(
        self, 
        name: str, 
        success: bool = True, 
        error: str = None,
        config_validation_result: Dict[str, Any] = None
    ) -> None:
        """Mark extension loading as complete.
        
        Args:
            name: Extension name
            success: Whether loading was successful
            error: Error message if loading failed
            config_validation_result: Configuration validation results
        """
        with self._lock:
            if name in self._extensions:
                ext = self._extensions[name]
                ext["status"] = "loaded" if success else "failed"
                ext["loading_time"] = time.time() - ext.get("loading_start_time", time.time())
                ext["error"] = error
                ext["config_validation"] = config_validation_result
                
                event_type = "loaded" if success else "failed"
                event_data = {"loading_time": ext["loading_time"]}
                if error:
                    event_data["error"] = error
                if config_validation_result:
                    event_data["config_validation"] = config_validation_result
                
                self._add_event(event_type, name, event_data)
    
    def track_hot_reload(
        self, 
        name: str, 
        success: bool = True, 
        reload_time: float = None,
        changes_detected: List[str] = None
    ) -> None:
        """Track extension hot reload.
        
        Args:
            name: Extension name
            success: Whether reload was successful
            reload_time: Time taken for reload
            changes_detected: List of detected changes
        """
        with self._lock:
            if name in self._extensions:
                ext = self._extensions[name]
                ext["hot_reload_count"] += 1
                
                self._add_event("hot_reload", name, {
                    "success": success,
                    "reload_time": reload_time,
                    "changes_detected": changes_detected or [],
                    "reload_count": ext["hot_reload_count"]
                })
    
    def track_configuration_change(
        self, 
        name: str, 
        old_config: Dict[str, Any], 
        new_config: Dict[str, Any],
        validation_result: Dict[str, Any] = None
    ) -> None:
        """Track extension configuration changes.
        
        Args:
            name: Extension name
            old_config: Previous configuration
            new_config: New configuration
            validation_result: Configuration validation results
        """
        with self._lock:
            if name in self._extensions:
                self._extensions[name]["config"] = new_config
                self._extensions[name]["config_validation"] = validation_result
                
                # Calculate config diff
                config_diff = self._calculate_config_diff(old_config, new_config)
                
                self._add_event("config_changed", name, {
                    "config_diff": config_diff,
                    "validation_result": validation_result
                })
    
    def get_extension_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific extension.
        
        Args:
            name: Extension name
            
        Returns:
            Extension status data or None if not found
        """
        with self._lock:
            return self._extensions.get(name)
    
    def get_all_extensions(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all extensions.
        
        Returns:
            Dictionary of all extension status data
        """
        with self._lock:
            return dict(self._extensions)
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """Get extension dependency graph.
        
        Returns:
            Dictionary mapping extension names to their dependencies
        """
        with self._lock:
            return {name: deps.copy() for name, deps in self._dependency_graph.items()}
    
    def get_loading_order(self) -> List[str]:
        """Get optimal loading order based on dependencies.
        
        Returns:
            List of extension names in loading order
        """
        with self._lock:
            return self._topological_sort()
    
    def get_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies.
        
        Returns:
            List of circular dependency chains
        """
        with self._lock:
            return self._find_cycles()
    
    def get_loading_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent loading events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of loading events
        """
        with self._lock:
            return self._loading_events[-limit:]
    
    def get_extension_health_summary(self) -> Dict[str, Any]:
        """Get overall extension health summary.
        
        Returns:
            Summary of extension health and statistics
        """
        with self._lock:
            total_extensions = len(self._extensions)
            loaded = len([ext for ext in self._extensions.values() if ext["status"] == "loaded"])
            failed = len([ext for ext in self._extensions.values() if ext["status"] == "failed"])
            loading = len([ext for ext in self._extensions.values() if ext["status"] == "loading"])
            
            # Calculate average loading time
            loading_times = [ext["loading_time"] for ext in self._extensions.values() 
                           if ext["loading_time"] is not None]
            avg_loading_time = sum(loading_times) / len(loading_times) if loading_times else 0
            
            # Get extension with most hot reloads
            hot_reload_counts = [(ext["name"], ext["hot_reload_count"]) 
                               for ext in self._extensions.values()]
            most_reloaded = max(hot_reload_counts, key=lambda x: x[1]) if hot_reload_counts else None
            
            return {
                "total_extensions": total_extensions,
                "loaded": loaded,
                "failed": failed,
                "loading": loading,
                "success_rate": loaded / total_extensions if total_extensions > 0 else 0,
                "average_loading_time": avg_loading_time,
                "circular_dependencies": len(self.get_circular_dependencies()),
                "most_hot_reloaded": most_reloaded,
                "recent_events": len(self._loading_events)
            }
    
    def _add_event(self, event_type: str, extension_name: str, data: Dict[str, Any] = None) -> None:
        """Add a loading event to history."""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "extension_name": extension_name,
            "data": data or {}
        }
        
        self._loading_events.append(event)
        
        # Maintain max history limit
        if len(self._loading_events) > self.max_history:
            self._loading_events = self._loading_events[-self.max_history:]
    
    def _calculate_config_diff(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate difference between configurations."""
        diff = {
            "added": {},
            "removed": {},
            "changed": {}
        }
        
        # Find added and changed keys
        for key, value in new_config.items():
            if key not in old_config:
                diff["added"][key] = value
            elif old_config[key] != value:
                diff["changed"][key] = {"old": old_config[key], "new": value}
        
        # Find removed keys
        for key, value in old_config.items():
            if key not in new_config:
                diff["removed"][key] = value
        
        return diff
    
    def _topological_sort(self) -> List[str]:
        """Perform topological sort for dependency resolution."""
        in_degree = {name: 0 for name in self._extensions.keys()}
        
        # Calculate in-degrees (how many dependencies each extension has)
        for name, deps in self._dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[name] += 1
        
        # Find nodes with no dependencies (in-degree = 0)
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # For each extension that depends on current, reduce its in-degree
            for name, deps in self._dependency_graph.items():
                if current in deps and name in in_degree:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        return result
    
    def _find_cycles(self) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        cycles = []
        visited = set()
        path = []
        
        def dfs(node: str) -> None:
            if node in path:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dep in self._dependency_graph.get(node, set()):
                if dep in self._extensions:
                    dfs(dep)
            
            path.pop()
        
        for ext_name in self._extensions.keys():
            if ext_name not in visited:
                dfs(ext_name)
        
        return cycles


class ExtensionDevelopmentTools:
    """Development tools for extension debugging."""
    
    def __init__(self, extension_tracker: ExtensionDependencyTracker):
        """Initialize extension development tools.
        
        Args:
            extension_tracker: Extension dependency tracker instance
        """
        self.tracker = extension_tracker
        self._file_watchers: Dict[str, Any] = {}
        self._lock = RLock()
    
    def watch_extension_files(self, extension_name: str, file_paths: List[str]) -> None:
        """Watch extension files for changes.
        
        Args:
            extension_name: Extension name
            file_paths: List of file paths to watch
        """
        # File watching implementation would depend on chosen library
        # For now, just track the intention
        with self._lock:
            self._file_watchers[extension_name] = {
                "file_paths": file_paths,
                "last_check": time.time(),
                "changes_detected": []
            }
    
    def generate_extension_scaffold(
        self, 
        extension_name: str, 
        output_dir: str,
        template_type: str = "basic"
    ) -> Dict[str, Any]:
        """Generate extension scaffold code.
        
        Args:
            extension_name: Name for the new extension
            output_dir: Output directory for scaffold
            template_type: Type of template (basic, auth, api, etc.)
            
        Returns:
            Scaffold generation results
        """
        scaffold_data = {
            "extension_name": extension_name,
            "template_type": template_type,
            "output_dir": output_dir,
            "files_created": [],
            "timestamp": time.time()
        }
        
        # Template generation logic would go here
        # For now, return the scaffold data structure
        return scaffold_data
    
    def validate_extension_config(
        self, 
        extension_name: str, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate extension configuration.
        
        Args:
            extension_name: Extension name
            config: Configuration to validate
            
        Returns:
            Validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Configuration validation logic would go here
        # For now, return basic validation structure
        return validation_result