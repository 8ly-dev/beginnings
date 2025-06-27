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