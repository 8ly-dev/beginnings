"""Tests for extension benchmarking framework."""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from beginnings.testing.benchmarks import (
    ExtensionBenchmark,
    BenchmarkSuite,
    BenchmarkConfiguration,
    BenchmarkResult,
    ResourceMonitor
)
from beginnings.testing.fixtures import PerformanceBenchmarkFixtures
from beginnings.testing.runners import ExtensionTestRunner
from beginnings.testing.mocks import MockExtension


class TestBenchmarkConfiguration:
    """Test benchmark configuration."""
    
    def test_default_configuration(self):
        """Test default benchmark configuration values."""
        config = BenchmarkConfiguration()
        
        assert config.duration_seconds == 30
        assert config.warmup_seconds == 5
        assert config.concurrent_requests == 10
        assert config.response_time_threshold_ms == 1000.0
        assert config.error_rate_threshold == 0.01
    
    def test_custom_configuration(self):
        """Test custom benchmark configuration."""
        config = BenchmarkConfiguration(
            duration_seconds=60,
            concurrent_requests=50,
            response_time_threshold_ms=500.0,
            error_rate_threshold=0.005
        )
        
        assert config.duration_seconds == 60
        assert config.concurrent_requests == 50
        assert config.response_time_threshold_ms == 500.0
        assert config.error_rate_threshold == 0.005


class TestResourceMonitor:
    """Test resource monitoring functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test resource monitor initialization."""
        monitor = ResourceMonitor()
        
        assert monitor.process_pid is not None
        assert monitor.monitoring is False
        assert len(monitor.samples) == 0
    
    def test_resource_monitoring_lifecycle(self):
        """Test complete resource monitoring lifecycle."""
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start_monitoring(interval=0.01)
        assert monitor.monitoring is True
        
        # Let it collect a few samples
        time.sleep(0.05)
        
        # Stop monitoring and get stats
        stats = monitor.stop_monitoring()
        assert monitor.monitoring is False
        
        # Verify stats structure
        assert "memory_rss_mb" in stats
        assert "cpu_percent" in stats
        assert "num_threads" in stats
        
        for metric_stats in stats.values():
            assert "avg" in metric_stats
            assert "max" in metric_stats
            assert "min" in metric_stats
            assert "median" in metric_stats
    
    def test_empty_monitoring_stats(self):
        """Test stats when no samples collected."""
        monitor = ResourceMonitor()
        
        # Stop without starting
        stats = monitor.stop_monitoring()
        
        # Should return zero values
        for metric_stats in stats.values():
            assert metric_stats["avg"] == 0
            assert metric_stats["max"] == 0
            assert metric_stats["min"] == 0


class TestExtensionBenchmark:
    """Test extension benchmark functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.config = BenchmarkConfiguration(
            duration_seconds=1,  # Short duration for testing
            warmup_seconds=0,
            concurrent_requests=5,
            response_time_threshold_ms=100.0
        )
        self.benchmark = ExtensionBenchmark("test_extension", self.config)
    
    def test_benchmark_startup(self):
        """Test extension startup benchmarking."""
        def mock_extension_factory():
            # Simulate some startup time
            time.sleep(0.01)
            return MockExtension()
        
        result = self.benchmark.benchmark_startup(mock_extension_factory)
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "test_extension_startup"
        assert result.duration > 0
        assert "memory_usage" in result.__dict__
        assert result.cpu_usage >= 0
    
    def test_benchmark_startup_with_error(self):
        """Test startup benchmarking with error."""
        def failing_factory():
            raise ValueError("Test error")
        
        result = self.benchmark.benchmark_startup(failing_factory)
        
        assert result.name == "test_extension_startup_error"
        assert result.metadata["error"] == "Test error"
    
    def test_benchmark_middleware_execution(self):
        """Test middleware execution benchmarking."""
        def mock_middleware(request, context):
            # Simulate some processing time
            time.sleep(0.001)
            return {"processed": True}
        
        # Create test requests
        test_requests = []
        for i in range(10):
            mock_request = Mock()
            mock_request.path = f"/test/{i}"
            test_requests.append(mock_request)
        
        result = self.benchmark.benchmark_middleware_execution(
            mock_middleware, 
            test_requests
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "test_extension_middleware"
        assert result.requests_per_second > 0
        assert result.error_rate == 0  # No errors expected
        assert result.percentiles is not None
        assert "p50" in result.percentiles
        assert "p95" in result.percentiles
    
    def test_benchmark_middleware_with_errors(self):
        """Test middleware benchmarking with errors."""
        def failing_middleware(request, context):
            if hasattr(request, 'path') and 'error' in request.path:
                raise RuntimeError("Simulated error")
            return {"processed": True}
        
        # Create test requests (some will cause errors)
        test_requests = []
        for i in range(10):
            mock_request = Mock()
            mock_request.path = f"/test/error/{i}" if i < 2 else f"/test/{i}"
            test_requests.append(mock_request)
        
        result = self.benchmark.benchmark_middleware_execution(
            failing_middleware, 
            test_requests
        )
        
        assert result.error_rate > 0  # Some errors expected
        assert result.metadata["errors"] == 2
    
    def test_benchmark_throughput(self):
        """Test throughput benchmarking."""
        def mock_request_handler(request):
            time.sleep(0.001)  # 1ms processing
            return {"status": "ok"}
        
        def mock_request_generator():
            return Mock(method="GET", path="/test")
        
        result = self.benchmark.benchmark_throughput(
            mock_request_handler,
            mock_request_generator,
            duration_seconds=1
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "test_extension_throughput"
        assert result.requests_per_second > 0
        assert result.duration > 0
        assert result.metadata["total_requests"] > 0
    
    def test_benchmark_memory_usage(self):
        """Test memory usage benchmarking."""
        def memory_intensive_test():
            # Create some data to use memory
            data = [f"test_data_{i}" * 100 for i in range(1000)]
            return len(data)
        
        result = self.benchmark.benchmark_memory_usage(
            memory_intensive_test,
            iterations=10
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.name == "test_extension_memory"
        assert result.metadata["iterations"] == 10
        assert "memory_growth" in result.metadata
    
    def test_performance_validation_pass(self):
        """Test performance validation when requirements are met."""
        # Add a benchmark result that meets requirements
        self.benchmark.results.append(BenchmarkResult(
            name="test_benchmark",
            duration=0.1,
            memory_usage={"avg": 10, "max": 15},
            cpu_usage=20.0,
            requests_per_second=100.0,
            error_rate=0.005,
            percentiles={"p95": 50.0}
        ))
        
        validation = self.benchmark.validate_performance_requirements()
        
        assert validation["passed"] is True
        assert len(validation["violations"]) == 0
    
    def test_performance_validation_fail(self):
        """Test performance validation when requirements are not met."""
        # Add a benchmark result that violates requirements
        self.benchmark.results.append(BenchmarkResult(
            name="test_benchmark",
            duration=0.1,
            memory_usage={"avg": 300, "max": 400},  # Exceeds limit
            cpu_usage=90.0,  # High CPU usage
            requests_per_second=10.0,
            error_rate=0.02,  # High error rate
            percentiles={"p95": 200.0}  # Exceeds threshold
        ))
        
        validation = self.benchmark.validate_performance_requirements()
        
        assert validation["passed"] is False
        assert len(validation["violations"]) > 0
        
        # Check for specific violations
        violation_types = [v["type"] for v in validation["violations"]]
        assert "response_time" in violation_types
        assert "error_rate" in violation_types
    
    def test_export_results(self):
        """Test exporting benchmark results."""
        # Add a test result
        self.benchmark.results.append(BenchmarkResult(
            name="test_benchmark",
            duration=0.1,
            memory_usage={"avg": 10},
            cpu_usage=20.0
        ))
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
        
        try:
            self.benchmark.export_results(export_path)
            
            # Verify file was created and contains expected data
            import json
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            assert data["extension_name"] == "test_extension"
            assert "results" in data
            assert "validation" in data
            assert "timestamp" in data
            assert len(data["results"]) == 1
        
        finally:
            Path(export_path).unlink(missing_ok=True)


class TestBenchmarkSuite:
    """Test benchmark suite functionality."""
    
    def test_benchmark_suite_initialization(self):
        """Test benchmark suite initialization."""
        config = BenchmarkConfiguration(duration_seconds=5)
        suite = BenchmarkSuite(config)
        
        assert suite.config.duration_seconds == 5
        assert len(suite.benchmarks) == 0
    
    def test_add_extension_to_suite(self):
        """Test adding extensions to benchmark suite."""
        suite = BenchmarkSuite()
        
        benchmark = suite.add_extension("test_extension")
        
        assert "test_extension" in suite.benchmarks
        assert isinstance(benchmark, ExtensionBenchmark)
        assert benchmark.extension_name == "test_extension"
    
    def test_run_all_benchmarks(self):
        """Test running all benchmarks in suite."""
        suite = BenchmarkSuite()
        
        # Add extensions
        suite.add_extension("ext1")
        suite.add_extension("ext2")
        
        # Create mock factories
        extension_factories = {
            "ext1": lambda: MockExtension(),
            "ext2": lambda: MockExtension()
        }
        
        results = suite.run_all_benchmarks(extension_factories)
        
        assert "ext1" in results
        assert "ext2" in results
        assert len(results["ext1"]) > 0  # Should have startup benchmark
        assert len(results["ext2"]) > 0
    
    def test_generate_report(self):
        """Test generating comprehensive benchmark report."""
        suite = BenchmarkSuite()
        
        # Add extension and run a benchmark
        benchmark = suite.add_extension("test_extension")
        benchmark.results.append(BenchmarkResult(
            name="test_benchmark",
            duration=0.1,
            memory_usage={"avg": 10},
            cpu_usage=20.0,
            requests_per_second=100.0,
            error_rate=0.001
        ))
        
        report = suite.generate_report()
        
        assert "summary" in report
        assert "extensions" in report
        assert "performance_comparison" in report
        assert "recommendations" in report
        
        assert report["summary"]["total_extensions"] == 1
        assert "test_extension" in report["extensions"]
        
        ext_report = report["extensions"]["test_extension"]
        assert "results" in ext_report
        assert "validation" in ext_report
        assert "performance_score" in ext_report


class TestPerformanceBenchmarkFixtures:
    """Test performance benchmark fixtures."""
    
    def setup_method(self):
        """Set up test environment."""
        self.fixtures = PerformanceBenchmarkFixtures()
    
    def test_benchmark_config_fixture(self):
        """Test benchmark configuration fixture."""
        config = self.fixtures.get_benchmark_config()
        
        assert isinstance(config, dict)
        assert "duration_seconds" in config
        assert "concurrent_requests" in config
        assert "response_time_threshold_ms" in config
        assert "error_rate_threshold" in config
    
    def test_load_testing_scenarios(self):
        """Test load testing scenarios fixture."""
        scenarios = self.fixtures.get_load_testing_scenarios()
        
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 4  # light, moderate, heavy, stress
        
        for scenario in scenarios:
            assert "name" in scenario
            assert "concurrent_requests" in scenario
            assert "duration_seconds" in scenario
            assert "description" in scenario
    
    def test_performance_test_requests(self):
        """Test performance test requests fixture."""
        requests = self.fixtures.get_performance_test_requests()
        
        assert isinstance(requests, list)
        assert len(requests) == 100  # 50 GET + 25 POST + 25 PUT
        
        # Check request structure
        for request in requests:
            assert "method" in request
            assert "path" in request
            assert "headers" in request
            assert "expected_status" in request
    
    def test_memory_stress_scenarios(self):
        """Test memory stress scenarios fixture."""
        scenarios = self.fixtures.get_memory_stress_scenarios()
        
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 4
        
        for scenario in scenarios:
            assert "name" in scenario
            assert "object_count" in scenario
            assert "description" in scenario
    
    def test_baseline_performance_data(self):
        """Test baseline performance data fixture."""
        baseline = self.fixtures.get_baseline_performance_data()
        
        assert isinstance(baseline, dict)
        assert "startup_time_ms" in baseline
        assert "response_time_ms" in baseline
        assert "memory_usage_mb" in baseline
        assert "cpu_usage_percent" in baseline
        assert "requests_per_second" in baseline
        assert "error_rate" in baseline
        
        # Check response time structure
        response_times = baseline["response_time_ms"]
        assert "p50" in response_times
        assert "p95" in response_times
        assert "p99" in response_times
    
    def test_mock_extension_factory(self):
        """Test mock extension factory creation."""
        factory = self.fixtures.create_mock_extension_factory("middleware")
        
        # Test factory creates extension
        extension = factory()
        assert extension.name == "test_middleware_extension"
        assert extension.version == "1.0.0"
    
    def test_mock_request_generator(self):
        """Test mock request generator creation."""
        generator = self.fixtures.create_mock_request_generator("simple")
        
        # Test generator creates requests
        request = generator()
        assert hasattr(request, 'method')
        assert hasattr(request, 'url')
        assert hasattr(request.url, 'path')
        assert hasattr(request, 'headers')


class TestExtensionTestRunnerBenchmarks:
    """Test extension test runner benchmark integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_extension = MockExtension
        self.runner = ExtensionTestRunner(self.mock_extension, verbose=False)
    
    def test_run_performance_benchmarks(self):
        """Test running performance benchmarks through test runner."""
        config = BenchmarkConfiguration(
            duration_seconds=1,  # Short duration for testing
            concurrent_requests=5
        )
        
        results = self.runner.run_performance_benchmarks(
            benchmark_config=config,
            include_startup=True,
            include_middleware=False,  # Skip to avoid middleware complexity
            include_throughput=False,
            include_memory=True
        )
        
        assert "extension" in results
        assert "benchmarks" in results
        assert "validation" in results
        assert "performance_score" in results
        
        # Should have startup and memory benchmarks
        benchmark_types = [b["type"] for b in results["benchmarks"]]
        assert "startup" in benchmark_types
        assert "memory" in benchmark_types
    
    def test_run_all_tests_with_benchmarks(self):
        """Test running all tests with benchmarks included."""
        config = BenchmarkConfiguration(duration_seconds=1)
        
        results = self.runner.run_all_tests_with_benchmarks(
            include_benchmarks=True,
            benchmark_config=config
        )
        
        # Should have both standard test results and benchmarks
        assert "total_passed" in results
        assert "total_failed" in results
        assert "benchmarks" in results
        
        benchmarks = results["benchmarks"]
        assert "performance_score" in benchmarks
        assert "validation" in benchmarks


class TestBenchmarkingIntegration:
    """Test full benchmarking integration."""
    
    def test_end_to_end_benchmarking(self):
        """Test complete end-to-end benchmarking workflow."""
        # Create benchmark configuration
        config = BenchmarkConfiguration(
            duration_seconds=1,
            concurrent_requests=3,
            response_time_threshold_ms=50.0,
            error_rate_threshold=0.01
        )
        
        # Create benchmark suite
        suite = BenchmarkSuite(config)
        
        # Add extension to suite
        benchmark = suite.add_extension("test_extension", config)
        
        # Run startup benchmark
        def fast_extension_factory():
            return MockExtension()
        
        startup_result = benchmark.benchmark_startup(fast_extension_factory)
        
        # Validate results
        assert startup_result.duration > 0
        assert startup_result.memory_usage is not None
        
        # Run validation
        validation = benchmark.validate_performance_requirements()
        
        # Generate report
        report = suite.generate_report()
        
        assert report["summary"]["total_extensions"] == 1
        assert "test_extension" in report["extensions"]
    
    def test_benchmark_result_serialization(self):
        """Test that benchmark results can be serialized."""
        result = BenchmarkResult(
            name="test_benchmark",
            duration=0.1,
            memory_usage={"avg": 10, "max": 15},
            cpu_usage=20.0,
            requests_per_second=100.0,
            error_rate=0.001,
            percentiles={"p50": 10.0, "p95": 50.0},
            metadata={"test": "data"}
        )
        
        # Should be able to convert to dict for JSON serialization
        import json
        serialized = json.dumps(result.__dict__)
        
        # Should be able to deserialize
        deserialized = json.loads(serialized)
        
        assert deserialized["name"] == "test_benchmark"
        assert deserialized["duration"] == 0.1
        assert deserialized["memory_usage"]["avg"] == 10
        assert deserialized["percentiles"]["p95"] == 50.0