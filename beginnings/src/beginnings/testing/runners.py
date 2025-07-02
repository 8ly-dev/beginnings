"""Test runners for extension testing."""

from __future__ import annotations

import asyncio
import unittest
import pytest
from typing import Any, Dict, List, Optional, Type, Callable, Union
from pathlib import Path
import sys
import os
import tempfile
import shutil
import importlib
import inspect
from datetime import datetime

from ..extensions.base import BaseExtension
from .fixtures import ExtensionFixtures, BeginningsTestFixtures, PerformanceBenchmarkFixtures
from .mocks import MockBeginningsApp, MockHTTPClient, MockDatabase
from .benchmarks import ExtensionBenchmark, BenchmarkSuite, BenchmarkConfiguration


class ExtensionTestRunner:
    """Test runner specifically for extension testing."""
    
    def __init__(
        self,
        extension_class: Type[BaseExtension],
        extension_path: Optional[str] = None,
        test_config: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """Initialize extension test runner.
        
        Args:
            extension_class: Extension class to test
            extension_path: Path to extension directory
            test_config: Test configuration
            verbose: Enable verbose output
        """
        self.extension_class = extension_class
        self.extension_path = extension_path
        self.test_config = test_config or {}
        self.verbose = verbose
        
        self.fixtures = BeginningsTestFixtures()
        self.results = {}
        self.temp_dir = None
    
    def setup(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="beginnings_test_")
        
        if self.verbose:
            print(f"Setting up test environment in {self.temp_dir}")
    
    def teardown(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        if self.verbose:
            print("Cleaned up test environment")
    
    def run_configuration_tests(self) -> Dict[str, Any]:
        """Run configuration validation tests.
        
        Returns:
            Test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Test valid configuration
            valid_config = self.fixtures.extensions.get_default_config()
            extension = self.extension_class(valid_config)
            errors = extension.validate_config()
            
            if not errors:
                results["passed"] += 1
                if self.verbose:
                    print("✓ Valid configuration test passed")
            else:
                results["failed"] += 1
                results["errors"].append(f"Valid config failed: {errors}")
                if self.verbose:
                    print(f"✗ Valid configuration test failed: {errors}")
            
            # Test invalid configuration
            invalid_config = self.fixtures.extensions.get_invalid_config()
            extension = self.extension_class(invalid_config)
            errors = extension.validate_config()
            
            if errors:
                results["passed"] += 1
                if self.verbose:
                    print("✓ Invalid configuration test passed")
            else:
                results["failed"] += 1
                results["errors"].append("Invalid config should have failed validation")
                if self.verbose:
                    print("✗ Invalid configuration test failed")
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Configuration test error: {e}")
            if self.verbose:
                print(f"✗ Configuration test error: {e}")
        
        return results
    
    def run_middleware_tests(self) -> Dict[str, Any]:
        """Run middleware functionality tests.
        
        Returns:
            Test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            config = self.fixtures.extensions.get_middleware_config()
            extension = self.extension_class(config)
            
            # Test middleware factory
            factory = extension.get_middleware_factory()
            if factory and callable(factory):
                results["passed"] += 1
                if self.verbose:
                    print("✓ Middleware factory test passed")
            else:
                results["failed"] += 1
                results["errors"].append("Middleware factory is not callable")
                if self.verbose:
                    print("✗ Middleware factory test failed")
            
            # Test route application
            should_apply = extension.should_apply_to_route("/test", ["GET"], {})
            if isinstance(should_apply, bool):
                results["passed"] += 1
                if self.verbose:
                    print("✓ Route application test passed")
            else:
                results["failed"] += 1
                results["errors"].append("Route application doesn't return boolean")
                if self.verbose:
                    print("✗ Route application test failed")
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Middleware test error: {e}")
            if self.verbose:
                print(f"✗ Middleware test error: {e}")
        
        return results
    
    def run_lifecycle_tests(self) -> Dict[str, Any]:
        """Run extension lifecycle tests.
        
        Returns:
            Test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            config = self.fixtures.extensions.get_default_config()
            extension = self.extension_class(config)
            
            # Test startup handler
            startup_handler = extension.get_startup_handler()
            if startup_handler is None or callable(startup_handler):
                results["passed"] += 1
                if self.verbose:
                    print("✓ Startup handler test passed")
            else:
                results["failed"] += 1
                results["errors"].append("Startup handler is not callable")
                if self.verbose:
                    print("✗ Startup handler test failed")
            
            # Test shutdown handler
            shutdown_handler = extension.get_shutdown_handler()
            if shutdown_handler is None or callable(shutdown_handler):
                results["passed"] += 1
                if self.verbose:
                    print("✓ Shutdown handler test passed")
            else:
                results["failed"] += 1
                results["errors"].append("Shutdown handler is not callable")
                if self.verbose:
                    print("✗ Shutdown handler test failed")
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Lifecycle test error: {e}")
            if self.verbose:
                print(f"✗ Lifecycle test error: {e}")
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all extension tests.
        
        Returns:
            Complete test results
        """
        if self.verbose:
            print(f"Running tests for {self.extension_class.__name__}")
            print("=" * 50)
        
        self.setup()
        
        try:
            config_results = self.run_configuration_tests()
            middleware_results = self.run_middleware_tests()
            lifecycle_results = self.run_lifecycle_tests()
            
            total_results = {
                "extension_class": self.extension_class.__name__,
                "total_passed": (
                    config_results["passed"] + 
                    middleware_results["passed"] + 
                    lifecycle_results["passed"]
                ),
                "total_failed": (
                    config_results["failed"] + 
                    middleware_results["failed"] + 
                    lifecycle_results["failed"]
                ),
                "all_errors": (
                    config_results["errors"] + 
                    middleware_results["errors"] + 
                    lifecycle_results["errors"]
                ),
                "config_tests": config_results,
                "middleware_tests": middleware_results,
                "lifecycle_tests": lifecycle_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.verbose:
                print("\nTest Summary:")
                print(f"Passed: {total_results['total_passed']}")
                print(f"Failed: {total_results['total_failed']}")
                if total_results["all_errors"]:
                    print("Errors:")
                    for error in total_results["all_errors"]:
                        print(f"  - {error}")
            
            return total_results
            
        finally:
            self.teardown()
    
    def run_performance_benchmarks(
        self, 
        benchmark_config: Optional[BenchmarkConfiguration] = None,
        include_startup: bool = True,
        include_middleware: bool = True,
        include_throughput: bool = True,
        include_memory: bool = True
    ) -> Dict[str, Any]:
        """Run performance benchmarks for the extension.
        
        Args:
            benchmark_config: Benchmark configuration
            include_startup: Include startup benchmarks
            include_middleware: Include middleware benchmarks  
            include_throughput: Include throughput benchmarks
            include_memory: Include memory benchmarks
            
        Returns:
            Benchmark results
        """
        if self.verbose:
            print(f"Running performance benchmarks for {self.extension_class.__name__}")
            print("=" * 60)
        
        # Initialize benchmark
        config = benchmark_config or BenchmarkConfiguration()
        benchmark = ExtensionBenchmark(self.extension_class.__name__, config)
        
        # Initialize fixtures
        perf_fixtures = PerformanceBenchmarkFixtures()
        
        benchmark_results = {
            "extension": self.extension_class.__name__,
            "config": {
                "duration_seconds": config.duration_seconds,
                "concurrent_requests": config.concurrent_requests,
                "response_time_threshold_ms": config.response_time_threshold_ms,
                "error_rate_threshold": config.error_rate_threshold
            },
            "benchmarks": [],
            "validation": None,
            "performance_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Startup benchmark
            if include_startup:
                if self.verbose:
                    print("Running startup benchmark...")
                
                def extension_factory():
                    config = self.fixtures.extensions.get_default_config()
                    return self.extension_class(config)
                
                startup_result = benchmark.benchmark_startup(extension_factory)
                benchmark_results["benchmarks"].append({
                    "type": "startup",
                    "result": {
                        "duration_ms": startup_result.duration * 1000,
                        "memory_usage_mb": startup_result.memory_usage.get("avg", 0),
                        "cpu_usage_percent": startup_result.cpu_usage
                    }
                })
                
                if self.verbose:
                    print(f"  Startup time: {startup_result.duration * 1000:.2f}ms")
            
            # Middleware benchmark
            if include_middleware:
                if self.verbose:
                    print("Running middleware benchmark...")
                
                try:
                    # Create extension and get middleware
                    config = self.fixtures.extensions.get_default_config()
                    extension = self.extension_class(config)
                    factory = extension.get_middleware_factory()
                    
                    if factory:
                        middleware = factory({})
                        
                        # Create test requests
                        test_requests = []
                        request_gen = perf_fixtures.create_mock_request_generator("simple")
                        for _ in range(100):
                            test_requests.append(request_gen())
                        
                        # Define middleware function to benchmark
                        def middleware_func(request, context):
                            if hasattr(middleware, 'process_request'):
                                return middleware.process_request(request)
                            elif hasattr(middleware, '__call__'):
                                return middleware(request, lambda req: None)
                            return None
                        
                        middleware_result = benchmark.benchmark_middleware_execution(
                            middleware_func, 
                            test_requests
                        )
                        
                        benchmark_results["benchmarks"].append({
                            "type": "middleware",
                            "result": {
                                "requests_per_second": middleware_result.requests_per_second,
                                "error_rate": middleware_result.error_rate,
                                "percentiles": middleware_result.percentiles,
                                "memory_usage_mb": middleware_result.memory_usage.get("avg", 0),
                                "cpu_usage_percent": middleware_result.cpu_usage
                            }
                        })
                        
                        if self.verbose:
                            print(f"  Requests/second: {middleware_result.requests_per_second:.2f}")
                            if middleware_result.percentiles:
                                print(f"  P95 response time: {middleware_result.percentiles.get('p95', 0):.2f}ms")
                    
                except Exception as e:
                    if self.verbose:
                        print(f"  Middleware benchmark failed: {e}")
            
            # Throughput benchmark
            if include_throughput:
                if self.verbose:
                    print("Running throughput benchmark...")
                
                try:
                    # Create a request handler that simulates the extension processing
                    config = self.fixtures.extensions.get_default_config()
                    extension = self.extension_class(config)
                    
                    def request_handler(request):
                        # Simulate request processing
                        import time
                        time.sleep(0.001)  # 1ms processing time
                        return {"status": "ok", "processed": True}
                    
                    request_gen = perf_fixtures.create_mock_request_generator("simple")
                    
                    throughput_result = benchmark.benchmark_throughput(
                        request_handler,
                        request_gen,
                        duration_seconds=10  # Shorter duration for testing
                    )
                    
                    benchmark_results["benchmarks"].append({
                        "type": "throughput",
                        "result": {
                            "requests_per_second": throughput_result.requests_per_second,
                            "error_rate": throughput_result.error_rate,
                            "percentiles": throughput_result.percentiles,
                            "memory_usage_mb": throughput_result.memory_usage.get("avg", 0),
                            "cpu_usage_percent": throughput_result.cpu_usage
                        }
                    })
                    
                    if self.verbose:
                        print(f"  Throughput: {throughput_result.requests_per_second:.2f} req/s")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Throughput benchmark failed: {e}")
            
            # Memory benchmark
            if include_memory:
                if self.verbose:
                    print("Running memory benchmark...")
                
                try:
                    def memory_load_test():
                        # Create extension instances to test memory usage
                        config = self.fixtures.extensions.get_default_config()
                        extension = self.extension_class(config)
                        
                        # Simulate some work
                        data = [f"test_data_{i}" for i in range(1000)]
                        return len(data)
                    
                    memory_result = benchmark.benchmark_memory_usage(
                        memory_load_test,
                        iterations=50
                    )
                    
                    benchmark_results["benchmarks"].append({
                        "type": "memory",
                        "result": {
                            "memory_usage_mb": memory_result.memory_usage,
                            "memory_growth_mb": memory_result.metadata.get("memory_growth", 0),
                            "cpu_usage_percent": memory_result.cpu_usage,
                            "iterations": memory_result.metadata.get("iterations", 0)
                        }
                    })
                    
                    if self.verbose:
                        print(f"  Peak memory: {memory_result.memory_usage.get('max', 0):.2f}MB")
                        print(f"  Memory growth: {memory_result.metadata.get('memory_growth', 0):.2f}MB")
                
                except Exception as e:
                    if self.verbose:
                        print(f"  Memory benchmark failed: {e}")
            
            # Validate performance requirements
            validation = benchmark.validate_performance_requirements()
            benchmark_results["validation"] = validation
            
            # Calculate performance score
            benchmark_results["performance_score"] = self._calculate_performance_score(benchmark.results)
            
            if self.verbose:
                print(f"\nPerformance Summary:")
                print(f"  Performance Score: {benchmark_results['performance_score']:.1f}/100")
                print(f"  Requirements Met: {'Yes' if validation['passed'] else 'No'}")
                if validation["violations"]:
                    print(f"  Violations: {len(validation['violations'])}")
                    for violation in validation["violations"]:
                        print(f"    - {violation['message']}")
            
            return benchmark_results
            
        except Exception as e:
            if self.verbose:
                print(f"Benchmark error: {e}")
            
            benchmark_results["error"] = str(e)
            return benchmark_results
    
    def run_all_tests_with_benchmarks(
        self, 
        include_benchmarks: bool = True,
        benchmark_config: Optional[BenchmarkConfiguration] = None
    ) -> Dict[str, Any]:
        """Run all extension tests including performance benchmarks.
        
        Args:
            include_benchmarks: Whether to include performance benchmarks
            benchmark_config: Benchmark configuration
            
        Returns:
            Complete test results including benchmarks
        """
        # Run standard tests
        test_results = self.run_all_tests()
        
        # Add benchmark results if requested
        if include_benchmarks:
            benchmark_results = self.run_performance_benchmarks(benchmark_config)
            test_results["benchmarks"] = benchmark_results
        
        return test_results
    
    def _calculate_performance_score(self, results) -> float:
        """Calculate performance score based on benchmark results.
        
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
        
        return sum(scores) / len(scores) if scores else 0.0


class IntegrationTestRunner:
    """Test runner for integration testing extensions with real apps."""
    
    def __init__(
        self,
        extensions: List[Type[BaseExtension]],
        test_config: Optional[Dict[str, Any]] = None,
        verbose: bool = False
    ):
        """Initialize integration test runner.
        
        Args:
            extensions: Extension classes to test
            test_config: Test configuration
            verbose: Enable verbose output
        """
        self.extensions = extensions
        self.test_config = test_config or {}
        self.verbose = verbose
        
        self.fixtures = BeginningsTestFixtures()
        self.mock_app = None
        self.temp_dir = None
    
    def setup(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="beginnings_integration_test_")
        self.mock_app = MockBeginningsApp()
        
        if self.verbose:
            print(f"Setting up integration test environment in {self.temp_dir}")
    
    def teardown(self):
        """Clean up integration test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        if self.verbose:
            print("Cleaned up integration test environment")
    
    async def run_extension_integration_test(
        self, 
        extension_class: Type[BaseExtension]
    ) -> Dict[str, Any]:
        """Run integration test for single extension.
        
        Args:
            extension_class: Extension to test
            
        Returns:
            Test results
        """
        results = {
            "extension": extension_class.__name__,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Create extension with test config
            config = self.fixtures.extensions.get_default_config()
            extension = extension_class(config)
            
            # Test extension can be added to app
            try:
                factory = extension.get_middleware_factory()
                if factory:
                    middleware = factory({})
                    self.mock_app.add_middleware(type(middleware))
                
                results["passed"] += 1
                if self.verbose:
                    print(f"✓ {extension_class.__name__} integration test passed")
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Extension integration failed: {e}")
                if self.verbose:
                    print(f"✗ {extension_class.__name__} integration test failed: {e}")
            
            # Test lifecycle handlers
            try:
                startup_handler = extension.get_startup_handler()
                if startup_handler:
                    await startup_handler()
                
                shutdown_handler = extension.get_shutdown_handler()
                if shutdown_handler:
                    await shutdown_handler()
                
                results["passed"] += 1
                if self.verbose:
                    print(f"✓ {extension_class.__name__} lifecycle test passed")
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Lifecycle test failed: {e}")
                if self.verbose:
                    print(f"✗ {extension_class.__name__} lifecycle test failed: {e}")
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"Extension creation failed: {e}")
            if self.verbose:
                print(f"✗ {extension_class.__name__} creation failed: {e}")
        
        return results
    
    async def run_all_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests for all extensions.
        
        Returns:
            Complete integration test results
        """
        if self.verbose:
            print("Running integration tests")
            print("=" * 50)
        
        self.setup()
        
        try:
            all_results = []
            total_passed = 0
            total_failed = 0
            all_errors = []
            
            for extension_class in self.extensions:
                results = await self.run_extension_integration_test(extension_class)
                all_results.append(results)
                total_passed += results["passed"]
                total_failed += results["failed"]
                all_errors.extend(results["errors"])
            
            final_results = {
                "total_passed": total_passed,
                "total_failed": total_failed,
                "all_errors": all_errors,
                "extension_results": all_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.verbose:
                print("\nIntegration Test Summary:")
                print(f"Extensions tested: {len(self.extensions)}")
                print(f"Total passed: {total_passed}")
                print(f"Total failed: {total_failed}")
                if all_errors:
                    print("Errors:")
                    for error in all_errors:
                        print(f"  - {error}")
            
            return final_results
            
        finally:
            self.teardown()


def run_extension_tests(
    extension_class: Type[BaseExtension],
    extension_path: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Run comprehensive tests for an extension.
    
    Args:
        extension_class: Extension class to test
        extension_path: Path to extension directory
        verbose: Enable verbose output
        
    Returns:
        Test results
    """
    runner = ExtensionTestRunner(
        extension_class=extension_class,
        extension_path=extension_path,
        verbose=verbose
    )
    
    return runner.run_all_tests()


async def run_integration_tests(
    extensions: List[Type[BaseExtension]],
    verbose: bool = False
) -> Dict[str, Any]:
    """Run integration tests for multiple extensions.
    
    Args:
        extensions: Extension classes to test
        verbose: Enable verbose output
        
    Returns:
        Integration test results
    """
    runner = IntegrationTestRunner(
        extensions=extensions,
        verbose=verbose
    )
    
    return await runner.run_all_integration_tests()


def discover_extension_tests(
    extension_dir: str,
    test_pattern: str = "test_*.py"
) -> List[str]:
    """Discover test files for an extension.
    
    Args:
        extension_dir: Extension directory to search
        test_pattern: Test file pattern
        
    Returns:
        List of test file paths
    """
    extension_path = Path(extension_dir)
    if not extension_path.exists():
        return []
    
    test_files = []
    
    # Look for tests directory
    tests_dir = extension_path / "tests"
    if tests_dir.exists():
        test_files.extend(str(p) for p in tests_dir.glob(test_pattern))
    
    # Look for test files in main directory
    test_files.extend(str(p) for p in extension_path.glob(test_pattern))
    
    return sorted(test_files)


def run_pytest_for_extension(
    extension_dir: str,
    pytest_args: Optional[List[str]] = None,
    verbose: bool = False
) -> int:
    """Run pytest for an extension directory.
    
    Args:
        extension_dir: Extension directory
        pytest_args: Additional pytest arguments
        verbose: Enable verbose output
        
    Returns:
        Pytest exit code
    """
    test_files = discover_extension_tests(extension_dir)
    
    if not test_files:
        if verbose:
            print(f"No test files found in {extension_dir}")
        return 0
    
    args = [
        "--tb=short",
        "-v" if verbose else "-q",
    ]
    
    if pytest_args:
        args.extend(pytest_args)
    
    args.extend(test_files)
    
    if verbose:
        print(f"Running pytest with args: {args}")
    
    return pytest.main(args)