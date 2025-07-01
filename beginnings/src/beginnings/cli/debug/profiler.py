"""Performance profiler for debugging dashboard."""

from __future__ import annotations

import time
import psutil
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, ContextManager
from dataclasses import dataclass, field
from threading import RLock
from contextlib import contextmanager

try:
    import cProfile
    import pstats
    import io
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False

try:
    from memory_profiler import profile as memory_profile
    MEMORY_PROFILING_AVAILABLE = True
except ImportError:
    MEMORY_PROFILING_AVAILABLE = False


@dataclass
class ProfileResult:
    """Result of a profiling operation."""
    name: str
    start_time: float
    end_time: float
    duration_ms: float
    memory_usage: Dict[str, float] = field(default_factory=dict)
    cpu_stats: Dict[str, Any] = field(default_factory=dict)
    call_stats: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration_ms / 1000.0


class PerformanceProfiler:
    """Performance profiler for tracking application performance."""
    
    def __init__(
        self,
        output_dir: str = "profiles",
        profile_cpu: bool = True,
        profile_memory: bool = True,
        profile_threshold_ms: float = 50.0
    ):
        """Initialize performance profiler.
        
        Args:
            output_dir: Directory to store profile outputs
            profile_cpu: Enable CPU profiling
            profile_memory: Enable memory profiling
            profile_threshold_ms: Minimum duration to record profile
        """
        self.output_dir = Path(output_dir)
        self.profile_cpu = profile_cpu and PROFILING_AVAILABLE
        self.profile_memory = profile_memory and MEMORY_PROFILING_AVAILABLE
        self.profile_threshold_ms = profile_threshold_ms
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._lock = RLock()
        self._profiles: List[ProfileResult] = []
        self._active_profiles: Dict[str, Dict] = {}
        
        # Get process for memory monitoring
        self._process = psutil.Process(os.getpid())
    
    @contextmanager
    def profile(self, name: str, context: Optional[Dict[str, Any]] = None) -> ContextManager[ProfileResult]:
        """Context manager for profiling a code block.
        
        Args:
            name: Name of the operation being profiled
            context: Additional context information
            
        Yields:
            ProfileResult that will be populated when context exits
        """
        profile_data = {
            "name": name,
            "start_time": time.time(),
            "context": context or {},
            "cpu_profiler": None,
            "memory_before": 0,
            "memory_peak": 0
        }
        
        # Start CPU profiling if enabled
        if self.profile_cpu:
            profiler = cProfile.Profile()
            profiler.enable()
            profile_data["cpu_profiler"] = profiler
        
        # Record initial memory if enabled
        if self.profile_memory:
            try:
                memory_info = self._process.memory_info()
                profile_data["memory_before"] = memory_info.rss / 1024 / 1024  # MB
                profile_data["memory_peak"] = profile_data["memory_before"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Create result object to yield
        result = ProfileResult(
            name=name,
            start_time=profile_data["start_time"],
            end_time=0,
            duration_ms=0,
            context=profile_data["context"]
        )
        
        try:
            yield result
        finally:
            # Stop profiling and calculate results
            end_time = time.time()
            duration_ms = (end_time - profile_data["start_time"]) * 1000
            
            # Only record if duration exceeds threshold
            if duration_ms >= self.profile_threshold_ms:
                result.end_time = end_time
                result.duration_ms = duration_ms
                
                # Stop CPU profiling
                if self.profile_cpu and profile_data["cpu_profiler"]:
                    profiler = profile_data["cpu_profiler"]
                    profiler.disable()
                    result.call_stats = self._extract_cpu_stats(profiler)
                
                # Record final memory usage
                if self.profile_memory:
                    try:
                        memory_info = self._process.memory_info()
                        memory_after = memory_info.rss / 1024 / 1024  # MB
                        
                        result.memory_usage = {
                            "before_mb": profile_data["memory_before"],
                            "after_mb": memory_after,
                            "peak_mb": max(profile_data["memory_peak"], memory_after),
                            "delta_mb": memory_after - profile_data["memory_before"]
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Record CPU stats
                try:
                    cpu_percent = self._process.cpu_percent()
                    result.cpu_stats = {
                        "cpu_percent": cpu_percent,
                        "num_threads": self._process.num_threads()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                # Store the profile
                with self._lock:
                    self._profiles.append(result)
    
    def start_profiling(self, name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Start profiling an operation manually.
        
        Args:
            name: Name of the operation
            context: Additional context information
            
        Returns:
            Profile ID for stopping later
        """
        profile_id = f"{name}_{time.time()}"
        
        profile_data = {
            "name": name,
            "start_time": time.time(),
            "context": context or {},
            "cpu_profiler": None,
            "memory_before": 0
        }
        
        # Start CPU profiling if enabled
        if self.profile_cpu:
            profiler = cProfile.Profile()
            profiler.enable()
            profile_data["cpu_profiler"] = profiler
        
        # Record initial memory
        if self.profile_memory:
            try:
                memory_info = self._process.memory_info()
                profile_data["memory_before"] = memory_info.rss / 1024 / 1024  # MB
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        with self._lock:
            self._active_profiles[profile_id] = profile_data
        
        return profile_id
    
    def stop_profiling(self, profile_id: str) -> Optional[ProfileResult]:
        """Stop profiling an operation.
        
        Args:
            profile_id: Profile ID from start_profiling
            
        Returns:
            ProfileResult if profiling was active, None otherwise
        """
        with self._lock:
            if profile_id not in self._active_profiles:
                return None
            
            profile_data = self._active_profiles.pop(profile_id)
        
        end_time = time.time()
        duration_ms = (end_time - profile_data["start_time"]) * 1000
        
        # Only record if duration exceeds threshold
        if duration_ms < self.profile_threshold_ms:
            return None
        
        result = ProfileResult(
            name=profile_data["name"],
            start_time=profile_data["start_time"],
            end_time=end_time,
            duration_ms=duration_ms,
            context=profile_data["context"]
        )
        
        # Stop CPU profiling
        if self.profile_cpu and profile_data["cpu_profiler"]:
            profiler = profile_data["cpu_profiler"]
            profiler.disable()
            result.call_stats = self._extract_cpu_stats(profiler)
        
        # Record memory usage
        if self.profile_memory:
            try:
                memory_info = self._process.memory_info()
                memory_after = memory_info.rss / 1024 / 1024  # MB
                
                result.memory_usage = {
                    "before_mb": profile_data["memory_before"],
                    "after_mb": memory_after,
                    "delta_mb": memory_after - profile_data["memory_before"]
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Record CPU stats
        try:
            cpu_percent = self._process.cpu_percent()
            result.cpu_stats = {
                "cpu_percent": cpu_percent,
                "num_threads": self._process.num_threads()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Store the profile
        with self._lock:
            self._profiles.append(result)
        
        return result
    
    def get_profiles(self, limit: int = 50) -> List[ProfileResult]:
        """Get recent profile results.
        
        Args:
            limit: Maximum number of profiles to return
            
        Returns:
            List of ProfileResult objects
        """
        with self._lock:
            return self._profiles[-limit:] if self._profiles else []
    
    def get_profile_by_name(self, name: str, limit: int = 10) -> List[ProfileResult]:
        """Get profiles for a specific operation name.
        
        Args:
            name: Operation name to filter by
            limit: Maximum number of profiles to return
            
        Returns:
            List of ProfileResult objects
        """
        with self._lock:
            matching = [p for p in self._profiles if p.name == name]
            return matching[-limit:] if matching else []
    
    def get_slow_profiles(self, min_duration_ms: float = 1000, limit: int = 25) -> List[ProfileResult]:
        """Get profiles that exceeded a duration threshold.
        
        Args:
            min_duration_ms: Minimum duration threshold
            limit: Maximum number of profiles to return
            
        Returns:
            List of slow ProfileResult objects
        """
        with self._lock:
            slow_profiles = [p for p in self._profiles if p.duration_ms >= min_duration_ms]
            # Sort by duration (slowest first)
            slow_profiles.sort(key=lambda p: p.duration_ms, reverse=True)
            return slow_profiles[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get profiling statistics.
        
        Returns:
            Dictionary containing profiling statistics
        """
        with self._lock:
            if not self._profiles:
                return {
                    "total_profiles": 0,
                    "avg_duration_ms": 0,
                    "operations": {}
                }
            
            # Overall statistics
            durations = [p.duration_ms for p in self._profiles]
            total_profiles = len(self._profiles)
            avg_duration = sum(durations) / total_profiles
            min_duration = min(durations)
            max_duration = max(durations)
            
            # Group by operation name
            by_operation = {}
            for profile in self._profiles:
                if profile.name not in by_operation:
                    by_operation[profile.name] = []
                by_operation[profile.name].append(profile)
            
            # Calculate per-operation statistics
            operation_stats = {}
            for operation, profiles in by_operation.items():
                op_durations = [p.duration_ms for p in profiles]
                operation_stats[operation] = {
                    "count": len(profiles),
                    "avg_duration_ms": sum(op_durations) / len(op_durations),
                    "min_duration_ms": min(op_durations),
                    "max_duration_ms": max(op_durations)
                }
            
            return {
                "total_profiles": total_profiles,
                "avg_duration_ms": round(avg_duration, 2),
                "min_duration_ms": round(min_duration, 2),
                "max_duration_ms": round(max_duration, 2),
                "operations": operation_stats,
                "active_profiles": len(self._active_profiles),
                "settings": {
                    "profile_cpu": self.profile_cpu,
                    "profile_memory": self.profile_memory,
                    "threshold_ms": self.profile_threshold_ms
                }
            }
    
    def export_json(self, filename: str):
        """Export profiles to JSON file.
        
        Args:
            filename: Output filename
        """
        with self._lock:
            data = {
                "profiles": [
                    {
                        "name": p.name,
                        "start_time": p.start_time,
                        "end_time": p.end_time,
                        "duration_ms": p.duration_ms,
                        "memory_usage": p.memory_usage,
                        "cpu_stats": p.cpu_stats,
                        "call_stats": p.call_stats,
                        "context": p.context
                    }
                    for p in self._profiles
                ],
                "statistics": self.get_statistics(),
                "exported_at": time.time()
            }
        
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def export_html(self, filename: str):
        """Export profiles to HTML report.
        
        Args:
            filename: Output filename
        """
        html_content = self._generate_html_report()
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def clear_profiles(self):
        """Clear all stored profiles."""
        with self._lock:
            self._profiles.clear()
            self._active_profiles.clear()
    
    def _extract_cpu_stats(self, profiler: cProfile.Profile) -> Dict[str, Any]:
        """Extract statistics from CPU profiler.
        
        Args:
            profiler: cProfile.Profile instance
            
        Returns:
            Dictionary containing CPU profiling statistics
        """
        if not profiler:
            return {}
        
        # Capture profiler stats
        stats_stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stats_stream)
        stats.strip_dirs().sort_stats('cumulative')
        
        # Get top functions by cumulative time
        stats.print_stats(10)
        stats_output = stats_stream.getvalue()
        
        # Extract total calls and primitive calls
        total_calls = stats.total_calls
        prim_calls = stats.prim_calls
        
        return {
            "total_calls": total_calls,
            "primitive_calls": prim_calls,
            "top_functions": stats_output.split('\n')[5:15] if stats_output else []
        }
    
    def _generate_html_report(self) -> str:
        """Generate HTML report of profiling data.
        
        Returns:
            HTML string
        """
        statistics = self.get_statistics()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Profile Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; flex: 1; }}
                .profiles {{ margin: 20px 0; }}
                .profile {{ background: #fff; border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .profile-header {{ font-weight: bold; color: #333; }}
                .profile-details {{ margin-top: 10px; font-size: 0.9em; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Performance Profile Report</h1>
                <p>Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Profiles</h3>
                    <p>{statistics['total_profiles']}</p>
                </div>
                <div class="stat-box">
                    <h3>Average Duration</h3>
                    <p>{statistics['avg_duration_ms']:.2f} ms</p>
                </div>
                <div class="stat-box">
                    <h3>Max Duration</h3>
                    <p>{statistics['max_duration_ms']:.2f} ms</p>
                </div>
            </div>
            
            <h2>Operation Statistics</h2>
            <table>
                <tr>
                    <th>Operation</th>
                    <th>Count</th>
                    <th>Avg Duration (ms)</th>
                    <th>Min Duration (ms)</th>
                    <th>Max Duration (ms)</th>
                </tr>
        """
        
        for operation, stats in statistics['operations'].items():
            html += f"""
                <tr>
                    <td>{operation}</td>
                    <td>{stats['count']}</td>
                    <td>{stats['avg_duration_ms']:.2f}</td>
                    <td>{stats['min_duration_ms']:.2f}</td>
                    <td>{stats['max_duration_ms']:.2f}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html


def start_profiling(
    output_dir: str = "profiles",
    profile_cpu: bool = True,
    profile_memory: bool = True,
    duration_seconds: float = 60.0
) -> PerformanceProfiler:
    """Start application-wide profiling.
    
    Args:
        output_dir: Directory to store profile outputs
        profile_cpu: Enable CPU profiling
        profile_memory: Enable memory profiling
        duration_seconds: How long to profile for
        
    Returns:
        PerformanceProfiler instance
    """
    profiler = PerformanceProfiler(
        output_dir=output_dir,
        profile_cpu=profile_cpu,
        profile_memory=profile_memory
    )
    
    # This would typically start background profiling
    # For now, just return the profiler instance
    return profiler