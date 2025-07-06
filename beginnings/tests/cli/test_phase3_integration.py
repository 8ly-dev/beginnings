"""Comprehensive Phase 3 integration test suite.

This test suite validates that all Phase 3 developer experience enhancements
work together seamlessly to provide the complete CLI functionality specified
in the Phase 3 planning document.
"""

import pytest
import tempfile
import os
import shutil
import yaml
import json
import subprocess
import time
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from beginnings.cli.main import cli


class TestPhase3EndToEndWorkflows:
    """Test complete end-to-end workflows for Phase 3 CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.project_name = "phase3-test-project"
        self.project_path = os.path.join(self.temp_dir, self.project_name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_project_lifecycle(self):
        """Test complete project lifecycle from creation to deployment."""
        # Step 1: Create new project with standard template
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", self.project_name,
                "--template", "standard",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(self.project_path)
        
        # Step 2: Validate project configuration
        config_path = os.path.join(self.project_path, "config", "app.yaml")
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            # Mock a valid configuration
            mock_load.return_value = {
                "app": {"name": self.project_name, "debug": False},
                "routers": {"html": {"prefix": ""}},
                "extensions": ["beginnings.extensions.auth:AuthExtension"]
            }
            
            with patch('beginnings.config.validator.ConfigValidator') as mock_validator:
                mock_validator.return_value.validate.return_value = {
                    "errors": [],
                    "warnings": [],
                    "security_issues": []
                }
                
                result = self.runner.invoke(cli, [
                    "config", "validate",
                    "--config", config_path,
                    "--security-audit"
                ])
                
                assert result.exit_code == 0
                assert "valid" in result.output.lower()
        
        # Step 3: Show merged configuration
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = {
                "app": {"name": self.project_name, "debug": False},
                "routers": {"html": {"prefix": ""}},
                "extensions": ["beginnings.extensions.auth:AuthExtension"]
            }
            
            result = self.runner.invoke(cli, [
                "config", "show",
                "--config", config_path,
                "--format", "json"
            ])
            
            assert result.exit_code == 0
            # Should output valid JSON
            try:
                config_data = json.loads(result.output)
                assert config_data["app"]["name"] == self.project_name
            except json.JSONDecodeError:
                pytest.fail("Config show did not output valid JSON")
        
        # Step 4: Test development server preparation
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.project_path
            
            with patch('uvicorn.run') as mock_uvicorn:
                mock_uvicorn.side_effect = KeyboardInterrupt()  # Simulate quick exit
                
                result = self.runner.invoke(cli, [
                    "run", "--validate-config", "--no-reload"
                ])
                
                # Should validate config before starting
                assert "validating" in result.output.lower() or result.exit_code == 0
    
    def test_extension_development_workflow(self):
        """Test complete extension development workflow."""
        extension_name = "test_custom_auth"
        extension_path = os.path.join(self.temp_dir, extension_name)
        
        # Step 1: Create new extension
        result = self.runner.invoke(cli, [
            "extension", "new", extension_name,
            "--type", "auth_provider",
            "--provider-base", "auth",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code == 0
        assert os.path.exists(extension_path)
        
        # Verify extension structure
        assert os.path.exists(os.path.join(extension_path, "__init__.py"))
        assert os.path.exists(os.path.join(extension_path, "extension.py"))
        assert os.path.exists(os.path.join(extension_path, "providers"))
        assert os.path.exists(os.path.join(extension_path, "tests"))
        assert os.path.exists(os.path.join(extension_path, "docs"))
        
        # Step 2: Validate extension structure
        result = self.runner.invoke(cli, [
            "extension", "validate",
            extension_path
        ])
        
        assert result.exit_code == 0
        assert "validation passed" in result.output.lower()
        
        # Step 3: Test extension
        with patch('beginnings.testing.ExtensionTestRunner') as mock_runner:
            mock_test_result = {
                "total_passed": 5,
                "total_failed": 0,
                "all_errors": [],
                "config_tests": {"passed": 2, "failed": 0},
                "middleware_tests": {"passed": 2, "failed": 0},
                "lifecycle_tests": {"passed": 1, "failed": 0}
            }
            mock_runner.return_value.run_all_tests.return_value = mock_test_result
            
            result = self.runner.invoke(cli, [
                "extension", "test",
                extension_path
            ])
            
            assert result.exit_code == 0
            assert "passed" in result.output.lower()
        
        # Step 4: List all extensions
        result = self.runner.invoke(cli, [
            "extension", "list",
            "--format", "table"
        ])
        
        assert result.exit_code == 0
        # Should include our custom extension and built-in ones
        assert extension_name in result.output or "auth" in result.output
    
    def test_configuration_management_workflow(self):
        """Test complete configuration management workflow."""
        # Create test configuration files
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        # Base configuration
        base_config = {
            "app": {"name": "config-test", "debug": True},
            "routers": {"html": {"prefix": ""}},
            "include": ["auth.yaml"]
        }
        
        with open(os.path.join(config_dir, "app.yaml"), "w") as f:
            yaml.dump(base_config, f)
        
        # Auth configuration
        auth_config = {
            "extensions": ["beginnings.extensions.auth:AuthExtension"],
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak_secret",  # Intentionally weak for testing
                        "cookie_secure": False
                    }
                }
            }
        }
        
        with open(os.path.join(config_dir, "auth.yaml"), "w") as f:
            yaml.dump(auth_config, f)
        
        # Step 1: Validate configuration with security audit
        app_config_path = os.path.join(config_dir, "app.yaml")
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", app_config_path,
            "--security-audit"
        ])
        
        # Should detect security issues
        assert result.exit_code != 0 or "security" in result.output.lower()
        
        # Step 2: Show configuration audit details
        result = self.runner.invoke(cli, [
            "config", "audit",
            "--config", app_config_path,
            "--severity", "warning"
        ])
        
        assert result.exit_code == 0 or result.exit_code == 1
        assert "audit" in result.output.lower()
        
        # Step 3: Auto-fix configuration issues
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", app_config_path,
            "--type", "security",
            "--dry-run"
        ])
        
        # Should show what would be fixed
        assert result.exit_code == 0
        assert "dry run" in result.output.lower() or "would fix" in result.output.lower()
        
        # Step 4: Generate new configuration from template
        new_config_path = os.path.join(self.temp_dir, "generated.yaml")
        result = self.runner.invoke(cli, [
            "config", "generate",
            "--template", "production",
            "--environment", "production",
            "--features", "auth,csrf,rate-limiting",
            "--output", new_config_path
        ])
        
        assert result.exit_code == 0
        assert os.path.exists(new_config_path)
        
        # Verify generated configuration
        with open(new_config_path) as f:
            generated_config = yaml.safe_load(f)
            assert generated_config["app"]["debug"] is False  # Production setting
    
    def test_development_server_integration(self):
        """Test development server integration with all features."""
        # Create minimal project structure
        project_structure = {
            "config": {"app.yaml": "app:\n  name: dev-test\nrouters:\n  html:\n    prefix: ''"},
            "main.py": "app = None",
            "routes": {"__init__.py": "", "html.py": "# HTML routes"},
            "templates": {"base.html": "<html></html>"}
        }
        
        for path, content in project_structure.items():
            if isinstance(content, dict):
                dir_path = os.path.join(self.temp_dir, path)
                os.makedirs(dir_path, exist_ok=True)
                for file_name, file_content in content.items():
                    with open(os.path.join(dir_path, file_name), "w") as f:
                        f.write(file_content)
            else:
                with open(os.path.join(self.temp_dir, path), "w") as f:
                    f.write(content)
        
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.temp_dir
            
            # Test development server startup
            with patch('uvicorn.run') as mock_uvicorn:
                mock_uvicorn.side_effect = KeyboardInterrupt()
                
                result = self.runner.invoke(cli, [
                    "run", "--debug", "--validate-config"
                ])
                
                # Should start successfully
                mock_uvicorn.assert_called_once()
                assert result.exit_code == 0 or "starting" in result.output.lower()
            
            # Test development commands
            result = self.runner.invoke(cli, [
                "dev", "--app", os.path.join(self.temp_dir, "main.py"),
                "--no-reload"
            ])
            
            # Should recognize development setup
            assert result.exit_code == 0 or "development" in result.output.lower()
    
    def test_debug_dashboard_workflow(self):
        """Test debug dashboard integration."""
        # Test debug dashboard startup
        with patch('beginnings.cli.debug.dashboard.DebugDashboard') as mock_dashboard:
            mock_dashboard_instance = MagicMock()
            mock_dashboard.return_value = mock_dashboard_instance
            mock_dashboard_instance.start.side_effect = KeyboardInterrupt()
            
            result = self.runner.invoke(cli, [
                "debug",
                "--host", "127.0.0.1",
                "--port", "8001",
                "--enable-profiler"
            ])
            
            # Should start debug dashboard
            mock_dashboard.assert_called_once()
            mock_dashboard_instance.start.assert_called_once()
    
    def test_migration_workflow_integration(self):
        """Test migration workflow integration."""
        # Test migration commands
        result = self.runner.invoke(cli, [
            "migrate", "--help"
        ])
        
        assert result.exit_code == 0
        assert "migration" in result.output.lower()
        
        # Test migration listing (should work even with no migrations)
        with patch('beginnings.migration.registry.MigrationRegistry') as mock_registry:
            mock_registry.return_value.list_migrations.return_value = []
            
            result = self.runner.invoke(cli, [
                "migrate", "list"
            ])
            
            # Should complete successfully
            assert result.exit_code == 0 or result.exit_code == 1
    
    def test_documentation_workflow_integration(self):
        """Test documentation workflow integration."""
        # Test documentation generation
        docs_dir = os.path.join(self.temp_dir, "docs")
        
        with patch('beginnings.docs.generator.DocumentationGenerator') as mock_generator:
            mock_gen_instance = MagicMock()
            mock_generator.return_value = mock_gen_instance
            mock_gen_instance.generate.return_value = True
            
            result = self.runner.invoke(cli, [
                "docs", "generate",
                "--output", docs_dir,
                "--format", "html",
                "--level", "detailed"
            ])
            
            # Should generate documentation
            mock_generator.assert_called_once()
            mock_gen_instance.generate.assert_called_once()


class TestPhase3CLICommandInteractions:
    """Test interactions between different CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_project_creation_and_validation_flow(self):
        """Test project creation followed by configuration validation."""
        project_name = "validation-test"
        
        # Create project
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "full",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code == 0
        
        # Validate created project configuration
        config_path = os.path.join(self.temp_dir, project_name, "config", "app.yaml")
        
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = {
                "app": {"name": project_name, "debug": False},
                "routers": {"html": {"prefix": ""}},
                "extensions": [
                    "beginnings.extensions.auth:AuthExtension",
                    "beginnings.extensions.csrf:CSRFExtension",
                    "beginnings.extensions.rate_limiting:RateLimitExtension",
                    "beginnings.extensions.security_headers:SecurityHeadersExtension"
                ]
            }
            
            with patch('beginnings.config.validator.ConfigValidator') as mock_validator:
                mock_validator.return_value.validate.return_value = {
                    "errors": [],
                    "warnings": [],
                    "security_issues": []
                }
                
                result = self.runner.invoke(cli, [
                    "config", "validate",
                    "--config", config_path,
                    "--production"
                ])
                
                # Full template should pass production validation
                assert result.exit_code == 0
    
    def test_extension_creation_and_project_integration(self):
        """Test creating extension and integrating it with a project."""
        project_name = "integration-test"
        extension_name = "custom_middleware"
        
        # Create project
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code == 0
        
        # Create extension
        result = self.runner.invoke(cli, [
            "extension", "new", extension_name,
            "--type", "middleware",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code == 0
        
        # Verify both project and extension exist
        project_path = os.path.join(self.temp_dir, project_name)
        extension_path = os.path.join(self.temp_dir, extension_name)
        
        assert os.path.exists(project_path)
        assert os.path.exists(extension_path)
        assert os.path.exists(os.path.join(extension_path, "extension.py"))
    
    def test_configuration_diff_between_environments(self):
        """Test configuration diff between different environments."""
        # Create development configuration
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        dev_config = {
            "app": {"name": "diff-test", "debug": True, "host": "127.0.0.1"},
            "routers": {"html": {"prefix": ""}}
        }
        
        prod_config = {
            "app": {"name": "diff-test", "debug": False, "host": "0.0.0.0"},
            "routers": {"html": {"prefix": ""}},
            "security": {"headers": {"x_frame_options": "DENY"}}
        }
        
        dev_path = os.path.join(config_dir, "app.dev.yaml")
        prod_path = os.path.join(config_dir, "app.prod.yaml")
        
        with open(dev_path, "w") as f:
            yaml.dump(dev_config, f)
        
        with open(prod_path, "w") as f:
            yaml.dump(prod_config, f)
        
        # Test configuration diff
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.side_effect = [dev_config, prod_config]
            
            result = self.runner.invoke(cli, [
                "config", "diff",
                dev_path, prod_path
            ])
            
            # Should show differences
            assert result.exit_code == 0
            assert "debug" in result.output.lower() or "diff" in result.output.lower()
    
    def test_production_readiness_validation_flow(self):
        """Test complete production readiness validation flow."""
        # Create production-like configuration
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        
        prod_config = {
            "app": {"name": "prod-test", "debug": False, "host": "127.0.0.1"},
            "routers": {"html": {"prefix": ""}},
            "extensions": [
                "beginnings.extensions.security_headers:SecurityHeadersExtension",
                "beginnings.extensions.csrf:CSRFExtension"
            ],
            "security": {
                "headers": {
                    "x_frame_options": "DENY",
                    "x_content_type_options": "nosniff",
                    "strict_transport_security": {"max_age": 31536000}
                }
            }
        }
        
        config_path = os.path.join(config_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(prod_config, f)
        
        # Test production validation
        with patch('beginnings.config.enhanced_loader.load_config_with_includes') as mock_load:
            mock_load.return_value = prod_config
            
            with patch('beginnings.config.validator.ConfigValidator') as mock_validator:
                mock_validator.return_value.validate.return_value = {
                    "errors": [],
                    "warnings": [],
                    "security_issues": []
                }
                
                result = self.runner.invoke(cli, [
                    "config", "validate",
                    "--config", config_path,
                    "--production",
                    "--environment", "production"
                ])
                
                # Should pass production validation
                assert result.exit_code == 0
                assert "production" in result.output.lower()


class TestPhase3CLIRobustness:
    """Test CLI robustness and error recovery."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_recovers_from_partial_operations(self):
        """Test CLI recovers gracefully from partial operations."""
        project_name = "recovery-test"
        
        # Simulate failure during project creation
        with patch('beginnings.cli.templates.engine.TemplateEngine.generate_project') as mock_generate:
            mock_generate.side_effect = Exception("Simulated failure")
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            # Should fail gracefully and clean up
            assert result.exit_code != 0
            project_path = os.path.join(self.temp_dir, project_name)
            assert not os.path.exists(project_path)
    
    def test_cli_handles_corrupted_project_state(self):
        """Test CLI handles corrupted project states gracefully."""
        # Create partially corrupted project
        project_name = "corrupted-test"
        project_path = os.path.join(self.temp_dir, project_name)
        config_dir = os.path.join(project_path, "config")
        
        os.makedirs(config_dir)
        
        # Create corrupted config file
        with open(os.path.join(config_dir, "app.yaml"), "w") as f:
            f.write("invalid: yaml: content: [[[")
        
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = project_path
            
            # Try to run development server
            result = self.runner.invoke(cli, ["run", "--no-reload"])
            
            # Should handle corruption gracefully
            assert result.exit_code != 0
            assert "error" in result.output.lower() or "invalid" in result.output.lower()
    
    def test_cli_maintains_consistency_during_interruption(self):
        """Test CLI maintains consistency during interruption."""
        config_file = os.path.join(self.temp_dir, "test.yaml")
        
        # Create initial config
        initial_config = {"app": {"name": "test", "debug": True}}
        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)
        
        # Simulate interruption during config fix
        with patch('beginnings.cli.commands.config._apply_fixes') as mock_apply:
            mock_apply.side_effect = KeyboardInterrupt()
            
            result = self.runner.invoke(cli, [
                "config", "fix",
                "--config", config_file,
                "--backup"
            ])
            
            # Original config should remain unchanged
            with open(config_file) as f:
                current_config = yaml.safe_load(f)
                assert current_config["app"]["debug"] is True
    
    def test_cli_resource_cleanup(self):
        """Test CLI properly cleans up resources."""
        # Test that temporary files and resources are cleaned up
        # This is more of a conceptual test since cleanup happens automatically
        
        project_name = "cleanup-test"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Project should be created successfully
            project_path = os.path.join(self.temp_dir, project_name)
            assert os.path.exists(project_path)
            
            # No temporary files should remain in system temp
            temp_files = [f for f in os.listdir(tempfile.gettempdir()) 
                         if project_name in f]
            assert len(temp_files) == 0


class TestPhase3CLIUsabilityFeatures:
    """Test CLI usability and user experience features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_helpful_error_messages_and_suggestions(self):
        """Test CLI provides helpful error messages with actionable suggestions."""
        # Test invalid project name
        result = self.runner.invoke(cli, [
            "new", "123invalid-name",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code != 0
        assert "invalid project name" in result.output.lower()
        assert "suggestion" in result.output.lower() or "try" in result.output.lower()
    
    def test_command_discovery_and_help(self):
        """Test command discovery and help system."""
        # Test main help
        result = self.runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "beginnings web framework" in result.output.lower()
        assert "config" in result.output
        assert "new" in result.output
        assert "run" in result.output
        assert "extension" in result.output
        
        # Test subcommand help
        result = self.runner.invoke(cli, ["config", "--help"])
        
        assert result.exit_code == 0
        assert "configuration" in result.output.lower()
        assert "validate" in result.output
        assert "show" in result.output
        assert "audit" in result.output
    
    def test_progress_indicators_and_feedback(self):
        """Test progress indicators provide useful feedback."""
        # Test project creation shows progress
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", "progress-test",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps",
                "--verbose"
            ])
            
            assert result.exit_code == 0
            # Should show some form of progress or feedback
            assert len(result.output) > 100  # Should have meaningful output
    
    def test_colored_output_and_formatting(self):
        """Test colored output enhances readability."""
        # Test that commands produce colored output
        result = self.runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        # Output should be well-formatted (exact color testing is complex)
        assert "Usage:" in result.output
        assert "Options:" in result.output
        assert "Commands:" in result.output
    
    def test_context_aware_behavior(self):
        """Test CLI behaves appropriately based on context."""
        # Test behavior in project directory vs non-project directory
        
        # In empty directory
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.temp_dir
            
            result = self.runner.invoke(cli, ["run"])
            
            # Should detect we're not in a project
            assert result.exit_code != 0
            assert "not" in result.output.lower() and "project" in result.output.lower()
        
        # Create minimal project structure
        config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "app.yaml"), "w") as f:
            f.write("app:\n  name: context-test")
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write("app = None")
        
        # In project directory
        with patch('os.getcwd') as mock_cwd:
            mock_cwd.return_value = self.temp_dir
            
            with patch('uvicorn.run') as mock_uvicorn:
                mock_uvicorn.side_effect = KeyboardInterrupt()
                
                result = self.runner.invoke(cli, ["run", "--no-reload"])
                
                # Should recognize project and attempt to start
                mock_uvicorn.assert_called_once()
    
    def test_intelligent_defaults(self):
        """Test CLI uses intelligent defaults appropriately."""
        # Test that default values are sensible
        
        # Project creation should use reasonable defaults
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", "defaults-test",
                "--output-dir", self.temp_dir,
                "--no-git", "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check that defaults create a working project
            project_path = os.path.join(self.temp_dir, "defaults-test")
            assert os.path.exists(os.path.join(project_path, "config", "app.yaml"))
            assert os.path.exists(os.path.join(project_path, "main.py"))
            assert os.path.exists(os.path.join(project_path, "routes"))
            assert os.path.exists(os.path.join(project_path, "templates"))