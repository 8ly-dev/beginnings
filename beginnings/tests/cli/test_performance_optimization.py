"""Test CLI performance optimizations."""

import time
import tempfile
import os
from unittest.mock import patch, MagicMock
import pytest

from beginnings.src.beginnings.cli.utils.performance import (
    cached_path_exists, cached_config_load, LazyImporter,
    performance_timer, PerformanceContext, setup_performance_optimizations,
    get_cache_stats, clear_performance_caches, FastCommandLoader
)


class TestPerformanceOptimizations:
    """Test performance optimization utilities."""
    
    def setup_method(self):
        """Set up test environment."""
        clear_performance_caches()
    
    def test_cached_path_exists(self):
        """Test cached path existence checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            
            # First call should hit filesystem
            start = time.perf_counter()
            result1 = cached_path_exists(test_file)
            first_call_time = time.perf_counter() - start
            
            assert result1 is False
            
            # Create the file
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Clear cache and check again
            clear_performance_caches()
            
            start = time.perf_counter()
            result2 = cached_path_exists(test_file)
            second_call_time = time.perf_counter() - start
            
            assert result2 is True
            
            # Third call should be cached (faster)
            start = time.perf_counter()
            result3 = cached_path_exists(test_file)
            cached_call_time = time.perf_counter() - start
            
            assert result3 is True
            assert cached_call_time < second_call_time
    
    def test_cached_config_load(self):
        """Test cached configuration loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
app:
  name: test-app
  debug: true
extensions:
  - test.extension
"""
            f.write(config_content)
            config_path = f.name
        
        try:
            # First load should hit filesystem
            start = time.perf_counter()
            config1 = cached_config_load(config_path)
            first_load_time = time.perf_counter() - start
            
            assert config1 is not None
            assert config1['app']['name'] == 'test-app'
            
            # Second load should be cached (faster)
            start = time.perf_counter()
            config2 = cached_config_load(config_path)
            cached_load_time = time.perf_counter() - start
            
            assert config2 == config1
            assert cached_load_time < first_load_time
            
            # Verify cache stats
            stats = get_cache_stats()
            assert stats['config_cache_size'] > 0
            
        finally:
            os.unlink(config_path)
    
    def test_lazy_importer(self):
        """Test lazy import functionality."""
        lazy_importer = LazyImporter()
        
        # Mock module
        mock_module = MagicMock()
        mock_module.test_function = lambda: "test_result"
        
        import_called = False
        def mock_import():
            nonlocal import_called
            import_called = True
            return mock_module
        
        # Register lazy import
        lazy_importer.register("test_module", mock_import)
        
        # Module should not be imported yet
        assert not import_called
        
        # Get module should trigger import
        module = lazy_importer.get("test_module")
        assert import_called
        assert module == mock_module
        assert module.test_function() == "test_result"
        
        # Second get should use cached version
        import_called = False
        module2 = lazy_importer.get("test_module")
        assert not import_called  # Should not import again
        assert module2 == mock_module
    
    def test_performance_timer_decorator(self):
        """Test performance timing decorator."""
        timing_results = []
        
        # Mock print to capture timing output
        with patch('builtins.print') as mock_print:
            @performance_timer
            def slow_function():
                time.sleep(0.15)  # 150ms - should trigger logging
                return "result"
            
            @performance_timer
            def fast_function():
                time.sleep(0.05)  # 50ms - should not trigger logging
                return "result"
            
            # Call slow function
            result1 = slow_function()
            assert result1 == "result"
            
            # Call fast function
            result2 = fast_function()
            assert result2 == "result"
            
            # Check that only slow function was logged
            assert mock_print.call_count == 1
            call_args = mock_print.call_args[0][0]
            assert "slow_function" in call_args
            assert "ms" in call_args
    
    def test_performance_context(self):
        """Test performance context manager."""
        with patch('builtins.print') as mock_print:
            with PerformanceContext("test operation", threshold_ms=50):
                time.sleep(0.1)  # 100ms - should trigger logging
            
            assert mock_print.call_count == 1
            call_args = mock_print.call_args[0][0]
            assert "test operation" in call_args
            assert "ms" in call_args
    
    def test_fast_command_loader(self):
        """Test fast command loading."""
        loader = FastCommandLoader()
        
        # Mock command
        mock_command = MagicMock()
        
        command_loaded = False
        def load_command():
            nonlocal command_loaded
            command_loaded = True
            return mock_command
        
        # Register command loader
        loader.register_command("test_cmd", load_command)
        
        # Command should not be loaded yet
        assert not command_loaded
        
        # Get command should trigger loading
        cmd = loader.get_command("test_cmd")
        assert command_loaded
        assert cmd == mock_command
        
        # Second get should use cached version
        command_loaded = False
        cmd2 = loader.get_command("test_cmd")
        assert not command_loaded  # Should not load again
        assert cmd2 == mock_command
    
    def test_cache_cleanup(self):
        """Test that caches are properly cleaned up."""
        # Fill cache beyond max size
        for i in range(1200):  # More than MAX_CACHE_SIZE (1000)
            cached_path_exists(f"/fake/path/{i}")
        
        stats = get_cache_stats()
        # Cache should be cleaned up automatically
        assert stats['path_cache_size'] <= 1000
    
    def test_setup_performance_optimizations(self):
        """Test performance optimization setup."""
        # Should not raise any exceptions
        setup_performance_optimizations()
        
        # Verify lazy imports are set up
        from beginnings.src.beginnings.cli.utils.performance import lazy_import
        
        # Should be able to register and get modules
        test_module = MagicMock()
        lazy_import.register("test", lambda: test_module)
        assert lazy_import.get("test") == test_module


class TestCLIStartupPerformance:
    """Test CLI startup performance improvements."""
    
    def test_lazy_command_registration(self):
        """Test that commands are loaded lazily."""
        from beginnings.src.beginnings.cli.main import fast_loader, _commands_registered
        
        # Commands should be registered in loader but not loaded
        assert hasattr(fast_loader, '_command_registry')
        
        # Commands should not be loaded until accessed
        with patch.object(fast_loader, 'get_command') as mock_get:
            mock_get.return_value = MagicMock()
            
            # Simulate command access
            from beginnings.src.beginnings.cli.main import _ensure_commands_registered
            _ensure_commands_registered()
            
            # Should have attempted to load commands
            assert mock_get.call_count > 0
    
    def test_performance_monitoring_option(self):
        """Test CLI performance monitoring option."""
        from click.testing import CliRunner
        from beginnings.src.beginnings.cli.main import cli
        
        runner = CliRunner()
        
        # Test with performance flag
        result = runner.invoke(cli, ['--performance', '--help'])
        assert result.exit_code == 0
        
        # Test without performance flag
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0


class TestConfigPerformanceOptimizations:
    """Test configuration command performance optimizations."""
    
    def test_config_validate_performance(self):
        """Test config validate command performance monitoring."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
app:
  name: test-app
  debug: false
"""
            f.write(config_content)
            config_path = f.name
        
        try:
            from click.testing import CliRunner
            from beginnings.src.beginnings.cli.commands.config import validate_command
            
            runner = CliRunner()
            
            # Should complete without performance warnings for small config
            result = runner.invoke(validate_command, ['--config', config_path])
            
            # Command should execute (may have validation errors but shouldn't crash)
            assert result.exit_code in [0, 1]  # 0 = success, 1 = validation issues
            
        finally:
            os.unlink(config_path)
    
    def test_config_show_performance(self):
        """Test config show command performance monitoring."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
app:
  name: test-app
  debug: false
extensions: []
"""
            f.write(config_content)
            config_path = f.name
        
        try:
            from click.testing import CliRunner
            from beginnings.src.beginnings.cli.commands.config import show_command
            
            runner = CliRunner()
            
            # Test JSON format
            result = runner.invoke(show_command, ['--config', config_path, '--format', 'json'])
            assert result.exit_code == 0
            assert 'test-app' in result.output
            
            # Test cached loading (second call should be faster)
            result2 = runner.invoke(show_command, ['--config', config_path, '--format', 'json'])
            assert result2.exit_code == 0
            assert result2.output == result.output
            
        finally:
            os.unlink(config_path)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_config_load_benchmark(self):
        """Benchmark configuration loading performance."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Create a larger config file for meaningful benchmarking
            config_content = """
app:
  name: benchmark-app
  debug: false
  host: 127.0.0.1
  port: 8000
  
extensions:
  - beginnings.extensions.auth:AuthExtension
  - beginnings.extensions.csrf:CSRFExtension
  - beginnings.extensions.rate_limiting:RateLimitExtension
  
auth:
  providers:
    session:
      secret_key: "benchmark-secret-key-for-testing"
      cookie_secure: true
      cookie_httponly: true
      cookie_samesite: strict
      
csrf:
  enabled: true
  secure_cookie: true
  
rate_limiting:
  global:
    requests: 1000
    window_seconds: 3600
  
security:
  headers:
    x_frame_options: DENY
    x_content_type_options: nosniff
    strict_transport_security:
      max_age: 31536000
      include_subdomains: true
"""
            f.write(config_content)
            config_path = f.name
        
        try:
            # Clear caches for fair benchmark
            clear_performance_caches()
            
            # Benchmark uncached loading
            start = time.perf_counter()
            config1 = cached_config_load(config_path)
            uncached_time = time.perf_counter() - start
            
            # Benchmark cached loading
            start = time.perf_counter()
            config2 = cached_config_load(config_path)
            cached_time = time.perf_counter() - start
            
            # Verify configs are identical
            assert config1 == config2
            
            # Cached should be significantly faster
            assert cached_time < uncached_time
            
            # For small configs, improvement might be minimal but should exist
            print(f"Uncached load: {uncached_time*1000:.2f}ms")
            print(f"Cached load: {cached_time*1000:.2f}ms")
            print(f"Speed improvement: {(uncached_time/cached_time):.1f}x")
            
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    # Run benchmarks when executed directly
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--benchmark":
        benchmark = TestPerformanceBenchmarks()
        benchmark.test_config_load_benchmark()
    else:
        pytest.main([__file__])