"""Extension performance benchmarking utilities."""

from __future__ import annotations

import time
import psutil
import threading
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from threading import Lock
from pathlib import Path
import json
import statistics


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    name: str
    duration: float  # seconds
    memory_usage: Dict[str, float]  # MB
    cpu_usage: float  # percentage
    requests_per_second: Optional[float] = None
    error_rate: Optional[float] = None
    percentiles: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkConfiguration:
    """Configuration for performance benchmarks."""
    duration_seconds: int = 30
    warmup_seconds: int = 5
    concurrent_requests: int = 10
    request_rate_limit: Optional[int] = None  # requests per second
    memory_limit_mb: Optional[float] = None
    cpu_limit_percent: Optional[float] = None
    response_time_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.01  # 1%


class ResourceMonitor:
    """Monitors system resource usage during benchmarks."""
    
    def __init__(self, process_pid: Optional[int] = None):
        """Initialize resource monitor.
        
        Args:
            process_pid: Process ID to monitor, defaults to current process
        """
        self.process_pid = process_pid or psutil.Process().pid
        self.process = psutil.Process(self.process_pid)
        self.monitoring = False
        self.samples: List[Dict[str, Any]] = []
        self._lock = Lock()
        self._monitor_thread: Optional[threading.Thread] = None
    
    def start_monitoring(self, interval: float = 0.1) -> None:
        """Start resource monitoring.
        
        Args:
            interval: Sampling interval in seconds
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.samples.clear()
        
        def monitor():
            while self.monitoring:
                try:
                    # Get memory info
                    memory_info = self.process.memory_info()
                    memory_percent = self.process.memory_percent()
                    
                    # Get CPU usage
                    cpu_percent = self.process.cpu_percent()
                    
                    # Get thread count
                    num_threads = self.process.num_threads()
                    
                    sample = {
                        "timestamp": time.time(),
                        "memory_rss_mb": memory_info.rss / 1024 / 1024,
                        "memory_vms_mb": memory_info.vms / 1024 / 1024,
                        "memory_percent": memory_percent,
                        "cpu_percent": cpu_percent,
                        "num_threads": num_threads
                    }
                    
                    with self._lock:
                        self.samples.append(sample)
                    
                    time.sleep(interval)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary statistics.
        
        Returns:
            Dictionary with resource usage statistics
        """
        self.monitoring = False
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        with self._lock:
            if not self.samples:
                return {
                    "memory_rss_mb": {"avg": 0, "max": 0, "min": 0},
                    "memory_vms_mb": {"avg": 0, "max": 0, "min": 0},
                    "memory_percent": {"avg": 0, "max": 0, "min": 0},
                    "cpu_percent": {"avg": 0, "max": 0, "min": 0},
                    "num_threads": {"avg": 0, "max": 0, "min": 0}
                }
            
            # Calculate statistics
            stats = {}
            for metric in ["memory_rss_mb", "memory_vms_mb", "memory_percent", "cpu_percent", "num_threads"]:
                values = [sample[metric] for sample in self.samples]
                stats[metric] = {
                    "avg": statistics.mean(values),
                    "max": max(values),
                    "min": min(values),
                    "median": statistics.median(values)
                }
            
            return stats


class ExtensionBenchmark:
    """Performance benchmarking for extensions."""
    
    def __init__(self, extension_name: str, config: Optional[BenchmarkConfiguration] = None):
        """Initialize extension benchmark.
        
        Args:
            extension_name: Name of the extension to benchmark
            config: Benchmark configuration
        """
        self.extension_name = extension_name
        self.config = config or BenchmarkConfiguration()
        self.resource_monitor = ResourceMonitor()
        self.results: List[BenchmarkResult] = []
    
    def benchmark_startup(self, extension_factory: Callable, *args, **kwargs) -> BenchmarkResult:
        """Benchmark extension startup time.
        
        Args:
            extension_factory: Function that creates the extension
            *args: Arguments for extension factory
            **kwargs: Keyword arguments for extension factory
            
        Returns:
            Benchmark result
        """
        self.resource_monitor.start_monitoring()
        
        start_time = time.time()
        
        try:
            extension = extension_factory(*args, **kwargs)
            if hasattr(extension, 'startup'):
                if asyncio.iscoroutinefunction(extension.startup):
                    asyncio.run(extension.startup())
                else:
                    extension.startup()
        except Exception as e:
            end_time = time.time()
            resource_stats = self.resource_monitor.stop_monitoring()
            
            return BenchmarkResult(
                name=f"{self.extension_name}_startup_error",
                duration=end_time - start_time,
                memory_usage=resource_stats.get("memory_rss_mb", {}),
                cpu_usage=resource_stats.get("cpu_percent", {}).get("avg", 0),
                metadata={"error": str(e)}
            )
        
        end_time = time.time()
        resource_stats = self.resource_monitor.stop_monitoring()
        
        result = BenchmarkResult(
            name=f"{self.extension_name}_startup",
            duration=end_time - start_time,
            memory_usage=resource_stats.get("memory_rss_mb", {}),
            cpu_usage=resource_stats.get("cpu_percent", {}).get("avg", 0),
            metadata={"extension_type": type(extension).__name__}
        )
        
        self.results.append(result)
        return result
    
    def benchmark_middleware_execution(
        self, 
        middleware_func: Callable, 
        test_requests: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> BenchmarkResult:
        """Benchmark middleware execution performance.
        
        Args:
            middleware_func: Middleware function to benchmark
            test_requests: List of test request objects
            context: Additional context for middleware
            
        Returns:
            Benchmark result
        """
        if not test_requests:
            raise ValueError("test_requests cannot be empty")
        
        execution_times = []
        errors = 0
        
        self.resource_monitor.start_monitoring()
        start_time = time.time()
        
        # Warmup
        warmup_requests = test_requests[:min(10, len(test_requests))]
        for request in warmup_requests:
            try:
                if asyncio.iscoroutinefunction(middleware_func):
                    asyncio.run(middleware_func(request, context or {}))
                else:
                    middleware_func(request, context or {})
            except:
                pass
        
        # Actual benchmark
        for request in test_requests:
            req_start = time.time()
            try:
                if asyncio.iscoroutinefunction(middleware_func):
                    asyncio.run(middleware_func(request, context or {}))
                else:
                    middleware_func(request, context or {})
                
                execution_times.append((time.time() - req_start) * 1000)  # Convert to ms
            except Exception:
                errors += 1
                execution_times.append((time.time() - req_start) * 1000)
        
        end_time = time.time()
        resource_stats = self.resource_monitor.stop_monitoring()
        
        total_duration = end_time - start_time
        total_requests = len(test_requests)
        rps = total_requests / total_duration if total_duration > 0 else 0
        error_rate = errors / total_requests if total_requests > 0 else 0
        
        # Calculate percentiles
        percentiles = {}
        if execution_times:
            execution_times.sort()
            percentiles = {
                "p50": self._percentile(execution_times, 50),
                "p95": self._percentile(execution_times, 95),
                "p99": self._percentile(execution_times, 99),
                "avg": statistics.mean(execution_times),
                "min": min(execution_times),
                "max": max(execution_times)
            }
        
        result = BenchmarkResult(
            name=f"{self.extension_name}_middleware",
            duration=total_duration,
            memory_usage=resource_stats.get("memory_rss_mb", {}),
            cpu_usage=resource_stats.get("cpu_percent", {}).get("avg", 0),
            requests_per_second=rps,
            error_rate=error_rate,
            percentiles=percentiles,
            metadata={
                "total_requests": total_requests,
                "errors": errors
            }
        )
        
        self.results.append(result)
        return result
    
    def benchmark_throughput(
        self, 
        request_handler: Callable,
        request_generator: Callable[[], Any],
        duration_seconds: Optional[int] = None
    ) -> BenchmarkResult:
        """Benchmark request throughput.
        
        Args:
            request_handler: Function that processes requests
            request_generator: Function that generates test requests
            duration_seconds: Duration to run benchmark (uses config default if None)
            
        Returns:
            Benchmark result
        """
        duration = duration_seconds or self.config.duration_seconds
        
        requests_processed = 0
        errors = 0
        response_times = []
        
        self.resource_monitor.start_monitoring()
        start_time = time.time()
        end_time = start_time + duration
        
        # Warmup
        warmup_end = start_time + self.config.warmup_seconds
        while time.time() < warmup_end:
            try:
                request = request_generator()
                if asyncio.iscoroutinefunction(request_handler):
                    asyncio.run(request_handler(request))
                else:
                    request_handler(request)
            except:
                pass
        
        # Actual benchmark
        benchmark_start = time.time()
        while time.time() < end_time:
            request_start = time.time()
            try:
                request = request_generator()
                if asyncio.iscoroutinefunction(request_handler):
                    asyncio.run(request_handler(request))
                else:
                    request_handler(request)
                
                response_time = (time.time() - request_start) * 1000  # ms
                response_times.append(response_time)
                requests_processed += 1
            except Exception:
                errors += 1
        
        benchmark_end = time.time()
        resource_stats = self.resource_monitor.stop_monitoring()
        
        actual_duration = benchmark_end - benchmark_start
        rps = requests_processed / actual_duration if actual_duration > 0 else 0
        error_rate = errors / (requests_processed + errors) if (requests_processed + errors) > 0 else 0
        
        # Calculate percentiles
        percentiles = {}
        if response_times:
            response_times.sort()
            percentiles = {
                "p50": self._percentile(response_times, 50),
                "p95": self._percentile(response_times, 95),
                "p99": self._percentile(response_times, 99),
                "avg": statistics.mean(response_times),
                "min": min(response_times),
                "max": max(response_times)
            }
        
        result = BenchmarkResult(
            name=f"{self.extension_name}_throughput",
            duration=actual_duration,
            memory_usage=resource_stats.get("memory_rss_mb", {}),
            cpu_usage=resource_stats.get("cpu_percent", {}).get("avg", 0),
            requests_per_second=rps,
            error_rate=error_rate,
            percentiles=percentiles,
            metadata={
                "total_requests": requests_processed,
                "errors": errors,
                "target_duration": duration
            }
        )
        
        self.results.append(result)
        return result
    
    def benchmark_memory_usage(
        self, 
        load_test: Callable,
        iterations: int = 100
    ) -> BenchmarkResult:
        """Benchmark memory usage under load.
        
        Args:
            load_test: Function that creates load on the extension
            iterations: Number of iterations to run
            
        Returns:
            Benchmark result
        """
        self.resource_monitor.start_monitoring()
        start_time = time.time()
        
        for i in range(iterations):
            try:
                if asyncio.iscoroutinefunction(load_test):
                    asyncio.run(load_test())
                else:
                    load_test()
            except Exception:
                pass
        
        end_time = time.time()
        resource_stats = self.resource_monitor.stop_monitoring()
        
        result = BenchmarkResult(
            name=f"{self.extension_name}_memory",
            duration=end_time - start_time,
            memory_usage=resource_stats.get("memory_rss_mb", {}),
            cpu_usage=resource_stats.get("cpu_percent", {}).get("avg", 0),
            metadata={
                "iterations": iterations,
                "memory_growth": resource_stats.get("memory_rss_mb", {}).get("max", 0) - 
                               resource_stats.get("memory_rss_mb", {}).get("min", 0)
            }
        )
        
        self.results.append(result)
        return result
    
    def validate_performance_requirements(self) -> Dict[str, Any]:
        """Validate extension performance against requirements.
        
        Returns:
            Validation results
        """
        validation_results = {
            "passed": True,
            "violations": [],
            "summary": {}
        }
        
        for result in self.results:
            violations = []
            
            # Check response time requirements
            if result.percentiles and "p95" in result.percentiles:
                if result.percentiles["p95"] > self.config.response_time_threshold_ms:
                    violations.append({
                        "type": "response_time",
                        "metric": "p95",
                        "value": result.percentiles["p95"],
                        "threshold": self.config.response_time_threshold_ms,
                        "message": f"P95 response time {result.percentiles['p95']:.2f}ms exceeds threshold {self.config.response_time_threshold_ms}ms"
                    })
            
            # Check error rate requirements
            if result.error_rate is not None:
                if result.error_rate > self.config.error_rate_threshold:
                    violations.append({
                        "type": "error_rate",
                        "value": result.error_rate,
                        "threshold": self.config.error_rate_threshold,
                        "message": f"Error rate {result.error_rate:.2%} exceeds threshold {self.config.error_rate_threshold:.2%}"
                    })
            
            # Check memory usage requirements
            if self.config.memory_limit_mb and result.memory_usage:
                max_memory = result.memory_usage.get("max", 0)
                if max_memory > self.config.memory_limit_mb:
                    violations.append({
                        "type": "memory_usage",
                        "value": max_memory,
                        "threshold": self.config.memory_limit_mb,
                        "message": f"Memory usage {max_memory:.2f}MB exceeds limit {self.config.memory_limit_mb}MB"
                    })
            
            # Check CPU usage requirements
            if self.config.cpu_limit_percent and result.cpu_usage > self.config.cpu_limit_percent:
                violations.append({
                    "type": "cpu_usage",
                    "value": result.cpu_usage,
                    "threshold": self.config.cpu_limit_percent,
                    "message": f"CPU usage {result.cpu_usage:.2f}% exceeds limit {self.config.cpu_limit_percent}%"
                })
            
            if violations:
                validation_results["passed"] = False
                validation_results["violations"].extend([
                    {**violation, "benchmark": result.name} 
                    for violation in violations
                ])
        
        # Generate summary
        validation_results["summary"] = {
            "total_benchmarks": len(self.results),
            "violations_count": len(validation_results["violations"]),
            "passed_benchmarks": len(self.results) - len([r for r in self.results if any(
                v["benchmark"] == r.name for v in validation_results["violations"]
            )])
        }
        
        return validation_results
    
    def export_results(self, file_path: Union[str, Path]) -> None:
        """Export benchmark results to JSON file.
        
        Args:
            file_path: Path to export file
        """
        export_data = {
            "extension_name": self.extension_name,
            "config": {
                "duration_seconds": self.config.duration_seconds,
                "concurrent_requests": self.config.concurrent_requests,
                "response_time_threshold_ms": self.config.response_time_threshold_ms,
                "error_rate_threshold": self.config.error_rate_threshold
            },
            "results": [
                {
                    "name": result.name,
                    "duration": result.duration,
                    "memory_usage": result.memory_usage,
                    "cpu_usage": result.cpu_usage,
                    "requests_per_second": result.requests_per_second,
                    "error_rate": result.error_rate,
                    "percentiles": result.percentiles,
                    "metadata": result.metadata
                }
                for result in self.results
            ],
            "validation": self.validate_performance_requirements(),
            "timestamp": time.time()
        }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value.
        
        Args:
            data: Sorted list of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not data:
            return 0.0
        
        index = (percentile / 100) * (len(data) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(data) - 1)
        
        if lower_index == upper_index:
            return data[lower_index]
        
        # Linear interpolation
        weight = index - lower_index
        return data[lower_index] * (1 - weight) + data[upper_index] * weight


class BenchmarkSuite:
    """Suite of benchmarks for multiple extensions."""
    
    def __init__(self, config: Optional[BenchmarkConfiguration] = None):
        """Initialize benchmark suite.
        
        Args:
            config: Default benchmark configuration
        """
        self.config = config or BenchmarkConfiguration()
        self.benchmarks: Dict[str, ExtensionBenchmark] = {}
    
    def add_extension(self, extension_name: str, config: Optional[BenchmarkConfiguration] = None) -> ExtensionBenchmark:
        """Add extension to benchmark suite.
        
        Args:
            extension_name: Name of the extension
            config: Extension-specific configuration (uses suite default if None)
            
        Returns:
            Extension benchmark instance
        """
        benchmark_config = config or self.config
        benchmark = ExtensionBenchmark(extension_name, benchmark_config)
        self.benchmarks[extension_name] = benchmark
        return benchmark
    
    def run_all_benchmarks(self, extension_factories: Dict[str, Callable]) -> Dict[str, List[BenchmarkResult]]:
        """Run benchmarks for all extensions.
        
        Args:
            extension_factories: Dictionary mapping extension names to factory functions
            
        Returns:
            Dictionary mapping extension names to benchmark results
        """
        results = {}
        
        for extension_name, benchmark in self.benchmarks.items():
            if extension_name in extension_factories:
                factory = extension_factories[extension_name]
                
                # Run startup benchmark
                try:
                    benchmark.benchmark_startup(factory)
                except Exception as e:
                    print(f"Failed to benchmark startup for {extension_name}: {e}")
                
                results[extension_name] = benchmark.results
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report.
        
        Returns:
            Benchmark report
        """
        report = {
            "summary": {
                "total_extensions": len(self.benchmarks),
                "total_benchmarks": sum(len(b.results) for b in self.benchmarks.values()),
                "overall_performance": "good"  # Will be calculated based on results
            },
            "extensions": {},
            "performance_comparison": {},
            "recommendations": []
        }
        
        for extension_name, benchmark in self.benchmarks.items():
            validation = benchmark.validate_performance_requirements()
            
            report["extensions"][extension_name] = {
                "results": [
                    {
                        "name": result.name,
                        "duration": result.duration,
                        "requests_per_second": result.requests_per_second,
                        "error_rate": result.error_rate,
                        "memory_usage_mb": result.memory_usage.get("avg", 0) if result.memory_usage else 0,
                        "cpu_usage_percent": result.cpu_usage
                    }
                    for result in benchmark.results
                ],
                "validation": validation,
                "performance_score": self._calculate_performance_score(benchmark.results)
            }
        
        # Generate performance comparison
        if len(self.benchmarks) > 1:
            report["performance_comparison"] = self._generate_performance_comparison()
        
        # Generate recommendations
        report["recommendations"] = self._generate_recommendations()
        
        return report
    
    def _calculate_performance_score(self, results: List[BenchmarkResult]) -> float:
        """Calculate performance score for an extension.
        
        Args:
            results: List of benchmark results
            
        Returns:
            Performance score (0-100)
        """
        if not results:
            return 0.0
        
        scores = []
        
        for result in results:
            score = 100.0  # Start with perfect score
            
            # Penalize high error rates
            if result.error_rate is not None:
                score -= result.error_rate * 1000  # 10 points per 1% error rate
            
            # Penalize slow response times
            if result.percentiles and "p95" in result.percentiles:
                if result.percentiles["p95"] > 100:  # 100ms baseline
                    score -= (result.percentiles["p95"] - 100) / 10
            
            # Penalize high CPU usage
            if result.cpu_usage > 50:  # 50% baseline
                score -= (result.cpu_usage - 50) * 2
            
            scores.append(max(0, min(100, score)))
        
        return statistics.mean(scores)
    
    def _generate_performance_comparison(self) -> Dict[str, Any]:
        """Generate performance comparison between extensions.
        
        Returns:
            Performance comparison data
        """
        comparison = {
            "fastest_startup": None,
            "highest_throughput": None,
            "lowest_memory_usage": None,
            "most_stable": None
        }
        
        startup_times = {}
        throughput_rates = {}
        memory_usage = {}
        error_rates = {}
        
        for extension_name, benchmark in self.benchmarks.items():
            for result in benchmark.results:
                if "startup" in result.name:
                    startup_times[extension_name] = result.duration
                elif "throughput" in result.name and result.requests_per_second:
                    throughput_rates[extension_name] = result.requests_per_second
                
                if result.memory_usage and "avg" in result.memory_usage:
                    memory_usage[extension_name] = result.memory_usage["avg"]
                
                if result.error_rate is not None:
                    if extension_name not in error_rates:
                        error_rates[extension_name] = []
                    error_rates[extension_name].append(result.error_rate)
        
        # Find best performers
        if startup_times:
            comparison["fastest_startup"] = min(startup_times.items(), key=lambda x: x[1])
        
        if throughput_rates:
            comparison["highest_throughput"] = max(throughput_rates.items(), key=lambda x: x[1])
        
        if memory_usage:
            comparison["lowest_memory_usage"] = min(memory_usage.items(), key=lambda x: x[1])
        
        if error_rates:
            avg_error_rates = {name: statistics.mean(rates) for name, rates in error_rates.items()}
            comparison["most_stable"] = min(avg_error_rates.items(), key=lambda x: x[1])
        
        return comparison
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for extension_name, benchmark in self.benchmarks.items():
            validation = benchmark.validate_performance_requirements()
            
            if not validation["passed"]:
                for violation in validation["violations"]:
                    if violation["type"] == "response_time":
                        recommendations.append(
                            f"Consider optimizing {extension_name} to reduce response times. "
                            f"Current P95: {violation['value']:.2f}ms, Target: {violation['threshold']}ms"
                        )
                    elif violation["type"] == "memory_usage":
                        recommendations.append(
                            f"Review memory usage in {extension_name}. "
                            f"Current peak: {violation['value']:.2f}MB, Limit: {violation['threshold']}MB"
                        )
                    elif violation["type"] == "error_rate":
                        recommendations.append(
                            f"Investigate error handling in {extension_name}. "
                            f"Current error rate: {violation['value']:.2%}, Target: <{violation['threshold']:.2%}"
                        )
        
        return recommendations