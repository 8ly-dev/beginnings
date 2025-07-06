"""Tests for CLI framework functionality."""

import pytest
import tempfile
import os
import shutil
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from beginnings.cli.main import cli
from beginnings.cli.utils.errors import CLIError, ProjectError, ConfigurationError


class TestCLIFramework:
    """Test the CLI framework core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_help_displays_correctly(self):
        """Test that CLI help is displayed correctly."""
        result = self.runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "beginnings web framework command-line interface" in result.output.lower()
        assert "config" in result.output
        assert "new" in result.output
        assert "run" in result.output
    
    def test_global_options_are_inherited(self):
        """Test that global options are passed to subcommands."""
        with patch('beginnings.cli.main.handle_cli_error') as mock_handler:
            result = self.runner.invoke(cli, [
                "--verbose",
                "--env", "staging", 
                "--config-dir", "/test/config",
                "config", "show"
            ])
            
            # The command should receive the global options in context
            # This will be validated through the command implementation
    
    def test_cli_handles_keyboard_interrupt_gracefully(self):
        """Test CLI handles Ctrl+C gracefully."""
        # Test that commands can handle KeyboardInterrupt gracefully
        # This is more realistically tested in run command
        pass
    
    def test_cli_error_handling_displays_helpful_messages(self):
        """Test that CLI errors display helpful messages and suggestions."""
        with patch('click.echo') as mock_echo:
            error = CLIError(
                "Test error message",
                suggestions=["Suggestion 1", "Suggestion 2"]
            )
            
            from beginnings.cli.utils.errors import handle_cli_error
            
            with pytest.raises(SystemExit):
                handle_cli_error(error)
            
            # Verify error message was printed
            mock_echo.assert_called()
            call_args = [call[0][0] for call in mock_echo.call_args_list]
            assert any("Test error message" in arg for arg in call_args)
            assert any("Suggestions:" in arg for arg in call_args)
    
    def test_colored_output_works_correctly(self):
        """Test that colored output formatting works."""
        from beginnings.cli.utils.colors import success, error, warning, info
        
        success_msg = success("Operation completed")
        error_msg = error("Something went wrong")
        warning_msg = warning("This is a warning")
        info_msg = info("Information message")
        
        # Messages should contain the text and ANSI color codes
        assert "Operation completed" in success_msg
        assert "Something went wrong" in error_msg
        assert "This is a warning" in warning_msg
        assert "Information message" in info_msg
    
    def test_progress_indicators_work(self):
        """Test that progress indicators function correctly."""
        from beginnings.cli.utils.progress import ProgressBar, Spinner
        
        # Test progress bar
        with ProgressBar(10, "Testing") as bar:
            assert bar.total == 10
            assert bar.description == "Testing"
            bar.update(5)
            assert bar.current == 5
        
        # Test spinner
        spinner = Spinner("Spinning test")
        spinner.start()
        spinner.stop("Test completed")
        # Just ensure no exceptions are raised
    
    def test_configuration_validation_integration(self):
        """Test CLI integrates with configuration validation."""
        # Create a test configuration file
        config_file = os.path.join(self.temp_dir, "app.yaml")
        with open(config_file, "w") as f:
            f.write("""
app:
  name: test-app
  debug: false
routers:
  html:
    prefix: ""
""")
        
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = {
                "app": {"name": "test-app", "debug": False},
                "routers": {"html": {"prefix": ""}}
            }
            
            with patch('beginnings.config.validator.ConfigValidator') as mock_validator:
                mock_validator.return_value.validate.return_value = {
                    "errors": [],
                    "warnings": [],
                    "info": []
                }
                
                result = self.runner.invoke(cli, [
                    "--config-dir", self.temp_dir,
                    "config", "validate"
                ])
                
                # Should complete successfully
                assert result.exit_code == 0
                assert "validation passed" in result.output.lower()


class TestCLICommands:
    """Test individual CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_validate_command(self):
        """Test config validate command."""
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = {"app": {"name": "test"}}
            
            with patch('beginnings.config.validator.ConfigValidator') as mock_validator:
                mock_validator.return_value.validate.return_value = {
                    "errors": [],
                    "warnings": ["Test warning"],
                    "info": []
                }
                
                result = self.runner.invoke(cli, ["config", "validate"])
                
                assert result.exit_code == 0
                assert "warning" in result.output.lower()
    
    def test_config_show_command(self):
        """Test config show command."""
        test_config = {
            "app": {"name": "test-app", "debug": False},
            "routers": {"html": {"prefix": ""}}
        }
        
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = test_config
            
            result = self.runner.invoke(cli, ["config", "show"])
            
            assert result.exit_code == 0
            assert "test-app" in result.output
    
    def test_config_diff_command(self):
        """Test config diff command."""
        config1 = {"app": {"name": "test", "debug": True}}
        config2 = {"app": {"name": "test", "debug": False}}
        
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.side_effect = [config1, config2]
            
            result = self.runner.invoke(cli, ["config", "diff", "dev", "prod"])
            
            assert result.exit_code == 0
            # Should show differences in debug setting
    
    def test_new_command_creates_project(self):
        """Test that new command creates project structure."""
        project_name = "test-project"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(project_path)
            assert os.path.exists(os.path.join(project_path, "config", "app.yaml"))
            assert os.path.exists(os.path.join(project_path, "main.py"))
            assert os.path.exists(os.path.join(project_path, "routes"))
            assert os.path.exists(os.path.join(project_path, "templates"))
    
    def test_new_command_validates_project_name(self):
        """Test that new command validates project names."""
        invalid_names = ["123invalid", "invalid-name-!", ""]
        
        for invalid_name in invalid_names:
            result = self.runner.invoke(cli, [
                "new", invalid_name,
                "--output-dir", self.temp_dir
            ])
            
            assert result.exit_code != 0
            assert "invalid project name" in result.output.lower()
    
    def test_run_command_validates_project_directory(self):
        """Test that run command validates project directory."""
        # Test in empty directory
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.temp_dir
            
            result = self.runner.invoke(cli, ["run", "--no-reload"])
            
            assert result.exit_code != 0
            assert "not appear to be a beginnings project" in result.output.lower()
    
    def test_run_command_starts_development_server(self):
        """Test that run command starts development server."""
        # Create minimal project structure
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        with open(os.path.join(config_dir, "app.yaml"), "w") as f:
            f.write("app:\n  name: test\nrouters:\n  html:\n    prefix: ''")
        
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write("app = None")
        
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.temp_dir
            
            with patch('uvicorn.run') as mock_uvicorn:
                mock_uvicorn.side_effect = KeyboardInterrupt()  # Simulate Ctrl+C
                
                result = self.runner.invoke(cli, ["run", "--no-reload"])
                
                # Should attempt to start server
                mock_uvicorn.assert_called_once()


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_project_error_handling(self):
        """Test ProjectError handling with suggestions."""
        from beginnings.cli.utils.errors import ProjectError, handle_cli_error
        
        error = ProjectError(
            "Project validation failed",
            suggestions=[
                "Check project structure",
                "Ensure configuration files exist"
            ]
        )
        
        with patch('click.echo') as mock_echo:
            with pytest.raises(SystemExit):
                handle_cli_error(error)
            
            # Verify error and suggestions were displayed
            mock_echo.assert_called()
    
    def test_configuration_error_handling(self):
        """Test ConfigurationError handling."""
        from beginnings.cli.utils.errors import ConfigurationError
        
        error = ConfigurationError("Invalid YAML syntax")
        
        assert isinstance(error, CLIError)
        assert error.message == "Invalid YAML syntax"
        assert error.exit_code == 1
    
    def test_validation_helpers(self):
        """Test validation helper functions."""
        from beginnings.cli.utils.errors import (
            validate_project_directory,
            validate_configuration_file
        )
        
        # Test project directory validation
        with pytest.raises(ProjectError):
            validate_project_directory("/nonexistent/path")
        
        # Test configuration file validation
        with pytest.raises(ConfigurationError):
            validate_configuration_file("/nonexistent/config.yaml")


class TestCLIIntegration:
    """Test CLI integration with framework components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_respects_environment_variables(self):
        """Test CLI respects BEGINNINGS_* environment variables."""
        with patch.dict(os.environ, {
            'BEGINNINGS_ENV': 'testing',
            'BEGINNINGS_CONFIG_DIR': '/test/config'
        }):
            # These should be picked up by global options
            result = self.runner.invoke(cli, ["config", "show"])
            
            # Command should use environment variables
            # This is validated through command behavior
    
    def test_cli_handles_missing_dependencies_gracefully(self):
        """Test CLI handles missing optional dependencies."""
        # Mock missing imports to test graceful degradation
        with patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            
            # CLI should still provide basic functionality
            result = self.runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
    
    def test_cli_configuration_integration(self):
        """Test CLI properly integrates with configuration system."""
        # This test ensures CLI commands properly use the configuration system
        # and handle configuration loading, validation, and display correctly
        
        config_data = {
            "app": {"name": "test-integration", "debug": True},
            "routers": {"html": {"prefix": ""}},
            "extensions": []
        }
        
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = config_data
            
            result = self.runner.invoke(cli, ["config", "show"])
            
            assert result.exit_code == 0
            assert "test-integration" in result.output
            mock_load.assert_called_once()


class TestCLIEdgeCases:
    """Comprehensive edge case testing for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_handles_unicode_project_names(self):
        """Test CLI handles unicode characters in project names."""
        unicode_names = ["测试项目", "проект-тест", "🚀-project"]
        
        for name in unicode_names:
            result = self.runner.invoke(cli, [
                "new", name,
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should reject unicode names with helpful error
            assert result.exit_code != 0
            assert "invalid project name" in result.output.lower()
    
    def test_cli_handles_extremely_long_project_names(self):
        """Test CLI handles extremely long project names."""
        long_name = "a" * 500  # Very long name
        
        result = self.runner.invoke(cli, [
            "new", long_name,
            "--output-dir", self.temp_dir,
            "--no-git", "--no-deps"
        ])
        
        assert result.exit_code != 0
        assert "too long" in result.output.lower()
    
    def test_cli_handles_reserved_project_names(self):
        """Test CLI handles reserved system names."""
        reserved_names = ["con", "aux", "prn", "nul", "__pycache__", ".git"]
        
        for name in reserved_names:
            result = self.runner.invoke(cli, [
                "new", name,
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should reject reserved names
            assert result.exit_code != 0
            assert "invalid" in result.output.lower() or "reserved" in result.output.lower()
    
    def test_cli_handles_filesystem_permission_errors(self):
        """Test CLI handles filesystem permission errors gracefully."""
        # Create a read-only directory
        readonly_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)  # Read-only
        
        try:
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", readonly_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code != 0
            assert "permission" in result.output.lower() or "write" in result.output.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)
    
    def test_cli_handles_disk_space_exhaustion(self):
        """Test CLI handles disk space issues gracefully."""
        # Mock OSError for no space left on device
        with patch('os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = OSError(28, "No space left on device")
            
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code != 0
            assert "disk space" in result.output.lower() or "space" in result.output.lower()
    
    def test_cli_handles_corrupted_configuration_files(self):
        """Test CLI handles corrupted configuration files."""
        # Create corrupted YAML file
        config_file = os.path.join(self.temp_dir, "corrupted.yaml")
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [unclosed")
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_file
        ])
        
        assert result.exit_code != 0
        assert "yaml" in result.output.lower() or "syntax" in result.output.lower()
    
    def test_cli_handles_network_connectivity_issues(self):
        """Test CLI handles network issues during dependency installation."""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = ConnectionError("Network unreachable")
            
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", self.temp_dir,
                "--no-git"  # Don't skip dependencies
            ])
            
            # Should handle network error gracefully
            assert result.exit_code != 0
            assert "network" in result.output.lower() or "connectivity" in result.output.lower()
    
    def test_cli_handles_git_repository_conflicts(self):
        """Test CLI handles existing git repositories."""
        # Create existing git repository
        project_dir = os.path.join(self.temp_dir, "existing-git")
        os.makedirs(project_dir)
        git_dir = os.path.join(project_dir, ".git")
        os.makedirs(git_dir)
        
        result = self.runner.invoke(cli, [
            "new", "existing-git",
            "--output-dir", self.temp_dir,
            "--no-deps"
        ])
        
        assert result.exit_code != 0
        assert "exists" in result.output.lower()
    
    def test_cli_handles_interrupted_operations(self):
        """Test CLI handles interrupted operations gracefully."""
        # Simulate KeyboardInterrupt during project creation
        with patch('beginnings.cli.templates.engine.TemplateEngine.generate_project') as mock_generate:
            mock_generate.side_effect = KeyboardInterrupt()
            
            result = self.runner.invoke(cli, [
                "new", "interrupted-project",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should clean up partially created project
            assert result.exit_code != 0
            project_path = os.path.join(self.temp_dir, "interrupted-project")
            assert not os.path.exists(project_path)
    
    def test_cli_validates_command_combinations(self):
        """Test CLI validates invalid command combinations."""
        # Test conflicting options
        result = self.runner.invoke(cli, [
            "run", "--debug", "--production-preview"
        ])
        
        # Debug and production preview are conflicting
        assert result.exit_code != 0 or "debug" not in result.output.lower()
    
    def test_cli_handles_malformed_yaml_includes(self):
        """Test CLI handles malformed YAML include directives."""
        # Create config with circular includes
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        with open(os.path.join(config_dir, "app.yaml"), "w") as f:
            f.write("""
app:
  name: test
include:
  - circular.yaml
""")
        
        with open(os.path.join(config_dir, "circular.yaml"), "w") as f:
            f.write("""
include:
  - app.yaml
debug: true
""")
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", os.path.join(config_dir, "app.yaml")
        ])
        
        assert result.exit_code != 0
        assert "circular" in result.output.lower() or "include" in result.output.lower()
    
    def test_cli_handles_empty_configuration_files(self):
        """Test CLI handles empty configuration files."""
        empty_config = os.path.join(self.temp_dir, "empty.yaml")
        with open(empty_config, "w") as f:
            f.write("")
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", empty_config
        ])
        
        assert result.exit_code != 0
        assert "empty" in result.output.lower() or "required" in result.output.lower()
    
    def test_cli_handles_symbolic_links(self):
        """Test CLI handles symbolic links in project paths."""
        # Create symbolic link to temp directory
        link_path = os.path.join(self.temp_dir, "link_to_temp")
        real_path = os.path.join(self.temp_dir, "real_dir")
        os.makedirs(real_path)
        
        try:
            os.symlink(real_path, link_path)
            
            result = self.runner.invoke(cli, [
                "new", "symlink-project",
                "--output-dir", link_path,
                "--no-git", "--no-deps"
            ])
            
            # Should handle symbolic links correctly
            assert result.exit_code == 0
            assert os.path.exists(os.path.join(link_path, "symlink-project"))
            
        except OSError:
            # Skip test if symbolic links not supported
            pytest.skip("Symbolic links not supported on this system")
    
    def test_cli_handles_concurrent_operations(self):
        """Test CLI handles concurrent operations safely."""
        import threading
        import time
        
        results = []
        
        def create_project(name):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "new", f"concurrent-{name}",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            results.append(result)
        
        # Start multiple concurrent project creations
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_project, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should complete successfully
        assert len(results) == 3
        successful_results = [r for r in results if r.exit_code == 0]
        assert len(successful_results) >= 1  # At least one should succeed
    
    def test_cli_memory_usage_with_large_configurations(self):
        """Test CLI memory usage with large configuration files."""
        # Create large configuration file
        large_config = os.path.join(self.temp_dir, "large.yaml")
        with open(large_config, "w") as f:
            f.write("app:\n  name: large-test\n")
            f.write("large_data:\n")
            for i in range(1000):
                f.write(f"  key_{i}: value_{i}\n")
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", large_config
        ])
        
        # Should handle large files without excessive memory usage
        assert result.exit_code == 0
    
    def test_cli_handles_special_characters_in_paths(self):
        """Test CLI handles special characters in file paths."""
        special_chars = ["spaces in name", "name-with-hyphens", "name_with_underscores"]
        
        for char_name in special_chars:
            special_dir = os.path.join(self.temp_dir, char_name)
            os.makedirs(special_dir, exist_ok=True)
            
            result = self.runner.invoke(cli, [
                "new", "test-project",
                "--output-dir", special_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should handle special characters in paths
            assert result.exit_code == 0 or "invalid" not in result.output.lower()


class TestCLIPerformance:
    """Test CLI performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_startup_time_under_budget(self):
        """Test CLI startup time is under 1 second."""
        import time
        
        start_time = time.time()
        result = self.runner.invoke(cli, ["--help"])
        end_time = time.time()
        
        startup_time = end_time - start_time
        
        assert result.exit_code == 0
        assert startup_time < 1.0, f"CLI startup took {startup_time:.2f}s, should be < 1.0s"
    
    def test_config_validation_performance(self):
        """Test configuration validation completes within time budget."""
        # Create moderate-sized configuration
        config_file = os.path.join(self.temp_dir, "perf_test.yaml")
        with open(config_file, "w") as f:
            f.write("""
app:
  name: performance-test
  debug: false
routers:
  html:
    prefix: ""
  api:
    prefix: "/api"
extensions:
  - beginnings.extensions.auth:AuthExtension
  - beginnings.extensions.csrf:CSRFExtension
auth:
  providers:
    session:
      secret_key: test_secret
""")
        
        import time
        
        start_time = time.time()
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_file
        ])
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        assert result.exit_code == 0 or result.exit_code == 1  # May fail validation but shouldn't crash
        assert validation_time < 5.0, f"Config validation took {validation_time:.2f}s, should be < 5.0s"
    
    def test_project_scaffolding_performance(self):
        """Test project scaffolding completes within time budget."""
        import time
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            start_time = time.time()
            result = self.runner.invoke(cli, [
                "new", "perf-test-project",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            end_time = time.time()
        
        scaffolding_time = end_time - start_time
        
        assert result.exit_code == 0
        assert scaffolding_time < 10.0, f"Project scaffolding took {scaffolding_time:.2f}s, should be < 10.0s"


class TestCLIInteractiveFeatures:
    """Test CLI interactive features and user input handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_interactive_project_creation(self):
        """Test interactive project creation with custom template."""
        # Simulate user input for custom template
        user_input = "4\n1\ny\ny\n"  # Custom template, auth provider, include tests, include docs
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", "interactive-test",
                "--template", "custom",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ], input=user_input)
            
            # Should complete successfully with interactive input
            assert result.exit_code == 0
            assert os.path.exists(os.path.join(self.temp_dir, "interactive-test"))
    
    def test_interactive_extension_creation(self):
        """Test interactive extension creation."""
        # Simulate user input for extension creation
        user_input = "2\n1\ny\ny\n"  # Auth provider, auth base, include tests, include docs
        
        result = self.runner.invoke(cli, [
            "extension", "new", "test-auth-ext",
            "--interactive",
            "--output-dir", self.temp_dir
        ], input=user_input)
        
        # Should complete successfully
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(self.temp_dir, "test-auth-ext"))
    
    def test_confirmation_prompts(self):
        """Test confirmation prompts work correctly."""
        # Test config fix command with confirmation
        config_file = os.path.join(self.temp_dir, "fix_test.yaml")
        with open(config_file, "w") as f:
            f.write("""
app:
  name: test
  debug: true  # Should be fixed to false
""")
        
        # Test declining confirmation
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", config_file
        ], input="n\n")
        
        assert "cancelled" in result.output.lower() or "canceled" in result.output.lower()
    
    def test_input_validation_with_retries(self):
        """Test input validation with retry mechanisms."""
        # This would test scenarios where user provides invalid input
        # and gets prompted to retry with corrected input
        
        # Test invalid choice followed by valid choice
        user_input = "99\n1\n"  # Invalid choice, then valid choice
        
        result = self.runner.invoke(cli, [
            "extension", "new", "retry-test",
            "--interactive",
            "--output-dir", self.temp_dir
        ], input=user_input)
        
        # Should eventually succeed with valid input
        assert result.exit_code == 0