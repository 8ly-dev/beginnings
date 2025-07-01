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
from .fixtures import ExtensionFixtures, BeginningsTestFixtures
from .mocks import MockBeginningsApp, MockHTTPClient, MockDatabase


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