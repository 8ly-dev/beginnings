"""Integration tests for CLI commands."""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
import yaml

from beginnings.cli.main import cli
from click.testing import CliRunner


@pytest.fixture
def temp_project_dir():
    """Create temporary directory for project testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


class TestProjectScaffolding:
    """Test project scaffolding functionality."""
    
    def test_minimal_project_creation(self, runner, temp_project_dir):
        """Test creating a minimal project."""
        project_name = "test-minimal"
        result = runner.invoke(cli, [
            'new', project_name,
            '--template', 'minimal',
            '--no-git', '--no-deps',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        assert "Project created successfully" in result.output
        
        # Check project structure
        project_path = Path(temp_project_dir) / project_name
        assert project_path.exists()
        assert (project_path / "main.py").exists()
        assert (project_path / "config" / "app.yaml").exists()
        assert (project_path / "pyproject.toml").exists()
        assert (project_path / "README.md").exists()
        
        # Check configuration content
        with open(project_path / "config" / "app.yaml") as f:
            config = yaml.safe_load(f)
        
        assert config["app"]["name"] == project_name
        # Minimal template should have no extensions
        assert config.get("extensions", []) == []
    
    def test_standard_project_creation(self, runner, temp_project_dir):
        """Test creating a standard project."""
        project_name = "test-standard"
        result = runner.invoke(cli, [
            'new', project_name,
            '--template', 'standard',
            '--no-git', '--no-deps',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        assert "Project created successfully" in result.output
        
        # Check project structure
        project_path = Path(temp_project_dir) / project_name
        assert project_path.exists()
        
        # Check configuration includes extensions
        with open(project_path / "config" / "app.yaml") as f:
            config = yaml.safe_load(f)
        
        extensions = config.get("extensions", [])
        assert len(extensions) > 0
        assert any("auth" in ext for ext in extensions)
        assert any("csrf" in ext for ext in extensions)
    
    def test_api_project_creation(self, runner, temp_project_dir):
        """Test creating an API project."""
        project_name = "test-api"
        result = runner.invoke(cli, [
            'new', project_name,
            '--template', 'api',
            '--no-git', '--no-deps',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        
        # Check API-specific structure
        project_path = Path(temp_project_dir) / project_name
        assert (project_path / "routes" / "api.py").exists()
        
        # API template should not have CSRF (not needed for API)
        with open(project_path / "config" / "app.yaml") as f:
            config = yaml.safe_load(f)
        
        extensions = config.get("extensions", [])
        assert any("rate_limiting" in ext for ext in extensions)
        assert not any("csrf" in ext for ext in extensions)
    
    def test_invalid_project_name(self, runner, temp_project_dir):
        """Test validation of invalid project names."""
        result = runner.invoke(cli, [
            'new', 'invalid-project-name-with-@-symbols',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code != 0
        assert "Invalid project name" in result.output
    
    def test_existing_directory_error(self, runner, temp_project_dir):
        """Test error when directory already exists."""
        project_name = "existing-project"
        project_path = Path(temp_project_dir) / project_name
        project_path.mkdir()
        
        result = runner.invoke(cli, [
            'new', project_name,
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code != 0
        assert "Directory already exists" in result.output


class TestExtensionManagement:
    """Test extension management functionality."""
    
    def test_extension_creation_middleware(self, runner, temp_project_dir):
        """Test creating a middleware extension."""
        result = runner.invoke(cli, [
            'extension', 'new', 'test_middleware',
            '--type', 'middleware',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        assert "Extension 'test_middleware' created successfully" in result.output
        
        # Check extension structure
        ext_path = Path(temp_project_dir) / "test_middleware"
        assert ext_path.exists()
        assert (ext_path / "__init__.py").exists()
        assert (ext_path / "extension.py").exists()
        assert (ext_path / "README.md").exists()
        assert (ext_path / "tests").exists()
    
    def test_extension_creation_auth_provider(self, runner, temp_project_dir):
        """Test creating an auth provider extension."""
        result = runner.invoke(cli, [
            'extension', 'new', 'custom_auth',
            '--type', 'auth_provider',
            '--provider-base', 'auth',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        assert "Extension 'custom_auth' created successfully" in result.output
        
        # Check auth provider specific structure
        ext_path = Path(temp_project_dir) / "custom_auth"
        assert (ext_path / "providers").exists()
        assert (ext_path / "providers" / "base.py").exists()
    
    def test_extension_validation(self, runner, temp_project_dir):
        """Test extension validation."""
        # Create a basic extension first
        ext_path = Path(temp_project_dir) / "test_ext"
        ext_path.mkdir()
        (ext_path / "__init__.py").write_text("")
        (ext_path / "extension.py").write_text("""
from beginnings.extensions.base import BaseExtension

class TestExtension(BaseExtension):
    def get_middleware_factory(self):
        pass
""")
        
        result = runner.invoke(cli, [
            'extension', 'validate', str(ext_path)
        ])
        
        assert result.exit_code == 0
        assert "Extension validation passed" in result.output
    
    def test_extension_list(self, runner):
        """Test listing extensions."""
        result = runner.invoke(cli, ['extension', 'list'])
        
        assert result.exit_code == 0
        # Should include built-in extensions
        assert "auth" in result.output
        assert "csrf" in result.output
        assert "rate_limiting" in result.output
    
    def test_invalid_extension_name(self, runner, temp_project_dir):
        """Test validation of invalid extension names."""
        result = runner.invoke(cli, [
            'extension', 'new', 'Invalid-Extension-Name',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code != 0
        assert "Invalid extension name" in result.output


class TestConfigurationManagement:
    """Test configuration management functionality."""
    
    def test_config_generate(self, runner, temp_project_dir):
        """Test configuration generation."""
        config_path = Path(temp_project_dir) / "test_config.yaml"
        
        result = runner.invoke(cli, [
            'config', 'generate',
            '--template', 'development',
            '--features', 'auth,csrf',
            '--output', str(config_path)
        ])
        
        assert result.exit_code == 0
        assert "Configuration generated" in result.output
        assert config_path.exists()
        
        # Check generated configuration
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        assert config["app"]["debug"] is True  # Development template
        assert "auth" in config
        assert "csrf" in config
    
    def test_config_validation_valid(self, runner, temp_project_dir):
        """Test validation of valid configuration."""
        # Create a valid config file
        config_path = Path(temp_project_dir) / "valid_config.yaml"
        config_data = {
            "app": {
                "name": "test-app",
                "debug": False
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        result = runner.invoke(cli, [
            'config', 'validate',
            '--config', str(config_path)
        ])
        
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output
    
    def test_config_validation_invalid(self, runner, temp_project_dir):
        """Test validation of invalid configuration."""
        # Create an invalid config file (missing required fields)
        config_path = Path(temp_project_dir) / "invalid_config.yaml"
        config_data = {
            "invalid": "config"
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        result = runner.invoke(cli, [
            'config', 'validate',
            '--config', str(config_path)
        ])
        
        assert result.exit_code != 0
        assert "Configuration validation failed" in result.output or "Missing required" in result.output
    
    def test_config_show(self, runner, temp_project_dir):
        """Test configuration display."""
        # Create a config file
        config_path = Path(temp_project_dir) / "show_config.yaml"
        config_data = {
            "app": {
                "name": "test-app",
                "debug": True
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        result = runner.invoke(cli, [
            'config', 'show',
            '--config', str(config_path),
            '--format', 'yaml'
        ])
        
        assert result.exit_code == 0
        assert "test-app" in result.output
    
    def test_config_audit(self, runner, temp_project_dir):
        """Test security audit functionality."""
        # Create a config with potential security issues
        config_path = Path(temp_project_dir) / "audit_config.yaml"
        config_data = {
            "app": {
                "name": "test-app",
                "debug": True  # Debug mode in production is a security issue
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "short",  # Too short secret
                        "cookie_secure": False
                    }
                }
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        result = runner.invoke(cli, [
            'config', 'audit',
            '--config', str(config_path)
        ])
        
        # Should detect security issues
        assert "secret" in result.output.lower() or "issues found" in result.output


class TestDevelopmentServer:
    """Test development server commands."""
    
    def test_run_command_help(self, runner):
        """Test run command help."""
        result = runner.invoke(cli, ['run', '--help'])
        
        assert result.exit_code == 0
        assert "Start the development server" in result.output
        assert "--host" in result.output
        assert "--port" in result.output
    
    def test_debug_command_help(self, runner):
        """Test debug command help."""
        result = runner.invoke(cli, ['debug', '--help'])
        
        assert result.exit_code == 0
        assert "debugging dashboard" in result.output
    
    def test_profile_command_help(self, runner):
        """Test profile command help."""
        result = runner.invoke(cli, ['profile', '--help'])
        
        assert result.exit_code == 0
        assert "performance profiling" in result.output


class TestCLIHelp:
    """Test CLI help and documentation."""
    
    def test_main_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Beginnings web framework" in result.output
        assert "config" in result.output
        assert "new" in result.output
        assert "extension" in result.output
        assert "run" in result.output
    
    def test_global_options(self, runner):
        """Test global CLI options."""
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "--config-dir" in result.output
        assert "--env" in result.output
        assert "--verbose" in result.output
        assert "--quiet" in result.output


class TestSecurityFeatures:
    """Test security-related CLI features."""
    
    def test_security_template_generation(self, runner, temp_project_dir):
        """Test that security defaults are generated properly."""
        project_name = "secure-test"
        result = runner.invoke(cli, [
            'new', project_name,
            '--template', 'full',
            '--no-git', '--no-deps',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        
        # Check .env.example was created with secure defaults
        project_path = Path(temp_project_dir) / project_name
        env_example = project_path / ".env.example"
        assert env_example.exists()
        
        env_content = env_example.read_text()
        # Should have secure secrets generated
        assert "SESSION_SECRET=" in env_content
        assert "JWT_SECRET=" in env_content
        # Secrets should be properly length (32+ chars after =)
        for line in env_content.split('\n'):
            if "SECRET=" in line:
                secret = line.split('=')[1]
                assert len(secret) >= 32
    
    def test_security_recommendations_display(self, runner, temp_project_dir):
        """Test that security recommendations are displayed."""
        result = runner.invoke(cli, [
            'new', 'security-test',
            '--template', 'standard',
            '--no-git', '--no-deps',
            '--output-dir', temp_project_dir
        ])
        
        assert result.exit_code == 0
        assert "Security Configuration Summary" in result.output
        assert "Next Steps:" in result.output
        assert "HTTPS" in result.output