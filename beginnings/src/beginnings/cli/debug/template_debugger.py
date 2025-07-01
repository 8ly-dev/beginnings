"""Template debugging and context inspection."""

from __future__ import annotations

import time
import json
from typing import Dict, Any, List, Optional, Callable
from threading import RLock


class TemplateContextInspector:
    """Inspects and tracks template rendering context."""
    
    def __init__(self, max_renders: int = 200):
        """Initialize template context inspector.
        
        Args:
            max_renders: Maximum number of render events to track
        """
        self.max_renders = max_renders
        self._render_history: List[Dict[str, Any]] = []
        self._context_cache: Dict[str, Dict[str, Any]] = {}
        self._template_errors: List[Dict[str, Any]] = []
        self._lock = RLock()
    
    def start_template_render(
        self, 
        template_name: str, 
        context: Dict[str, Any],
        request_id: str = None
    ) -> str:
        """Start tracking a template render.
        
        Args:
            template_name: Name of the template being rendered
            context: Template context variables
            request_id: Associated request ID
            
        Returns:
            Render ID for tracking
        """
        render_id = f"{template_name}_{int(time.time() * 1000)}"
        
        with self._lock:
            render_data = {
                "render_id": render_id,
                "template_name": template_name,
                "context": self._serialize_context(context),
                "context_summary": self._summarize_context(context),
                "request_id": request_id,
                "start_time": time.time(),
                "end_time": None,
                "duration": None,
                "error": None,
                "variables_accessed": [],
                "filters_applied": [],
                "includes_used": []
            }
            
            self._render_history.append(render_data)
            self._context_cache[render_id] = context
            
            # Maintain history limit
            if len(self._render_history) > self.max_renders:
                oldest = self._render_history.pop(0)
                self._context_cache.pop(oldest["render_id"], None)
        
        return render_id
    
    def track_variable_access(
        self, 
        render_id: str, 
        variable_name: str, 
        variable_value: Any,
        access_path: str = None
    ) -> None:
        """Track template variable access.
        
        Args:
            render_id: Render tracking ID
            variable_name: Name of the accessed variable
            variable_value: Value of the variable
            access_path: Full path to the variable (e.g., 'user.profile.name')
        """
        with self._lock:
            for render in self._render_history:
                if render["render_id"] == render_id:
                    render["variables_accessed"].append({
                        "name": variable_name,
                        "value": self._serialize_value(variable_value),
                        "access_path": access_path,
                        "timestamp": time.time()
                    })
                    break
    
    def track_filter_application(
        self, 
        render_id: str, 
        filter_name: str, 
        input_value: Any,
        output_value: Any,
        filter_args: List[Any] = None
    ) -> None:
        """Track template filter application.
        
        Args:
            render_id: Render tracking ID
            filter_name: Name of the filter
            input_value: Input value to the filter
            output_value: Output value from the filter
            filter_args: Arguments passed to the filter
        """
        with self._lock:
            for render in self._render_history:
                if render["render_id"] == render_id:
                    render["filters_applied"].append({
                        "filter_name": filter_name,
                        "input_value": self._serialize_value(input_value),
                        "output_value": self._serialize_value(output_value),
                        "filter_args": [self._serialize_value(arg) for arg in (filter_args or [])],
                        "timestamp": time.time()
                    })
                    break
    
    def track_template_include(
        self, 
        render_id: str, 
        included_template: str, 
        include_context: Dict[str, Any] = None
    ) -> None:
        """Track template includes.
        
        Args:
            render_id: Render tracking ID
            included_template: Name of the included template
            include_context: Context passed to the included template
        """
        with self._lock:
            for render in self._render_history:
                if render["render_id"] == render_id:
                    render["includes_used"].append({
                        "template_name": included_template,
                        "context": self._serialize_context(include_context or {}),
                        "timestamp": time.time()
                    })
                    break
    
    def complete_template_render(
        self, 
        render_id: str, 
        success: bool = True, 
        error: str = None
    ) -> None:
        """Complete template render tracking.
        
        Args:
            render_id: Render tracking ID
            success: Whether rendering was successful
            error: Error message if rendering failed
        """
        with self._lock:
            for render in self._render_history:
                if render["render_id"] == render_id:
                    render["end_time"] = time.time()
                    render["duration"] = render["end_time"] - render["start_time"]
                    render["error"] = error
                    
                    if not success and error:
                        self._template_errors.append({
                            "render_id": render_id,
                            "template_name": render["template_name"],
                            "error": error,
                            "context_summary": render["context_summary"],
                            "timestamp": time.time()
                        })
                    break
    
    def get_render_data(self, render_id: str) -> Optional[Dict[str, Any]]:
        """Get render data for a specific render.
        
        Args:
            render_id: Render tracking ID
            
        Returns:
            Render data or None if not found
        """
        with self._lock:
            for render in self._render_history:
                if render["render_id"] == render_id:
                    return dict(render)
            return None
    
    def get_recent_renders(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent template renders.
        
        Args:
            limit: Maximum number of renders to return
            
        Returns:
            List of recent render data
        """
        with self._lock:
            return self._render_history[-limit:]
    
    def get_template_renders(self, template_name: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get renders for a specific template.
        
        Args:
            template_name: Template name to filter by
            limit: Maximum number of renders to return
            
        Returns:
            List of render data for the specified template
        """
        with self._lock:
            template_renders = [
                render for render in self._render_history 
                if render["template_name"] == template_name
            ]
            return template_renders[-limit:]
    
    def get_context_for_render(self, render_id: str) -> Optional[Dict[str, Any]]:
        """Get full context for a specific render.
        
        Args:
            render_id: Render tracking ID
            
        Returns:
            Full context data or None if not found
        """
        with self._lock:
            return self._context_cache.get(render_id)
    
    def get_template_errors(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent template errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of template error data
        """
        with self._lock:
            return self._template_errors[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get template performance summary.
        
        Returns:
            Performance summary data
        """
        with self._lock:
            if not self._render_history:
                return {
                    "total_renders": 0,
                    "average_duration": 0,
                    "slowest_templates": [],
                    "most_used_templates": [],
                    "error_rate": 0
                }
            
            # Calculate average duration
            durations = [r["duration"] for r in self._render_history if r["duration"] is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Find slowest templates
            template_times = {}
            template_counts = {}
            for render in self._render_history:
                if render["duration"] is not None:
                    template = render["template_name"]
                    if template not in template_times:
                        template_times[template] = []
                        template_counts[template] = 0
                    template_times[template].append(render["duration"])
                    template_counts[template] += 1
            
            # Calculate average times per template
            template_avg_times = {
                template: sum(times) / len(times)
                for template, times in template_times.items()
            }
            
            slowest_templates = sorted(
                template_avg_times.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            most_used_templates = sorted(
                template_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            # Calculate error rate
            error_count = len(self._template_errors)
            total_renders = len(self._render_history)
            error_rate = error_count / total_renders if total_renders > 0 else 0
            
            return {
                "total_renders": total_renders,
                "average_duration": avg_duration,
                "slowest_templates": slowest_templates,
                "most_used_templates": most_used_templates,
                "error_rate": error_rate,
                "total_errors": error_count
            }
    
    def _serialize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize context for storage, handling complex objects."""
        serialized = {}
        for key, value in context.items():
            serialized[key] = self._serialize_value(value)
        return serialized
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value, handling complex objects."""
        try:
            # Try JSON serialization first
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # Fall back to string representation for complex objects
            if hasattr(value, '__dict__'):
                return {
                    "_type": type(value).__name__,
                    "_repr": repr(value),
                    "_attributes": {
                        k: self._serialize_value(v) 
                        for k, v in value.__dict__.items() 
                        if not k.startswith('_')
                    }
                }
            else:
                return {
                    "_type": type(value).__name__,
                    "_repr": repr(value)
                }
    
    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of context variables."""
        summary = {
            "variable_count": len(context),
            "variable_types": {},
            "large_objects": []
        }
        
        for key, value in context.items():
            value_type = type(value).__name__
            if value_type not in summary["variable_types"]:
                summary["variable_types"][value_type] = 0
            summary["variable_types"][value_type] += 1
            
            # Check for large objects (rough heuristic)
            try:
                if len(str(value)) > 1000:
                    summary["large_objects"].append(key)
            except:
                pass
        
        return summary


class DatabaseQueryDebugger:
    """Debugs database queries during template rendering."""
    
    def __init__(self, max_queries: int = 500):
        """Initialize database query debugger.
        
        Args:
            max_queries: Maximum number of queries to track
        """
        self.max_queries = max_queries
        self._query_history: List[Dict[str, Any]] = []
        self._lock = RLock()
    
    def track_query(
        self, 
        query: str, 
        parameters: List[Any] = None,
        render_id: str = None,
        request_id: str = None
    ) -> str:
        """Track a database query.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            render_id: Associated template render ID
            request_id: Associated request ID
            
        Returns:
            Query tracking ID
        """
        query_id = f"query_{int(time.time() * 1000)}"
        
        with self._lock:
            query_data = {
                "query_id": query_id,
                "query": query,
                "parameters": parameters or [],
                "render_id": render_id,
                "request_id": request_id,
                "start_time": time.time(),
                "end_time": None,
                "duration": None,
                "rows_affected": None,
                "error": None
            }
            
            self._query_history.append(query_data)
            
            # Maintain history limit
            if len(self._query_history) > self.max_queries:
                self._query_history.pop(0)
        
        return query_id
    
    def complete_query(
        self, 
        query_id: str, 
        rows_affected: int = None,
        error: str = None
    ) -> None:
        """Complete query tracking.
        
        Args:
            query_id: Query tracking ID
            rows_affected: Number of rows affected by the query
            error: Error message if query failed
        """
        with self._lock:
            for query in self._query_history:
                if query["query_id"] == query_id:
                    query["end_time"] = time.time()
                    query["duration"] = query["end_time"] - query["start_time"]
                    query["rows_affected"] = rows_affected
                    query["error"] = error
                    break
    
    def get_queries_for_render(self, render_id: str) -> List[Dict[str, Any]]:
        """Get all queries for a specific template render.
        
        Args:
            render_id: Template render ID
            
        Returns:
            List of query data for the render
        """
        with self._lock:
            return [
                query for query in self._query_history 
                if query["render_id"] == render_id
            ]
    
    def get_recent_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent database queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of recent query data
        """
        with self._lock:
            return self._query_history[-limit:]
    
    def get_slow_queries(self, threshold_ms: float = 100) -> List[Dict[str, Any]]:
        """Get slow database queries.
        
        Args:
            threshold_ms: Threshold in milliseconds for slow queries
            
        Returns:
            List of slow query data
        """
        threshold_sec = threshold_ms / 1000.0
        
        with self._lock:
            return [
                query for query in self._query_history 
                if query["duration"] is not None and query["duration"] > threshold_sec
            ]