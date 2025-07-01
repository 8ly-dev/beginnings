"""Tests for enhanced project scaffolding functionality."""

import pytest
import tempfile
import os
import shutil
import yaml
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from beginnings.cli.main import cli


class TestProjectCreation:
    """Test project creation for all template types."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_minimal_template_creates_correct_structure(self):
        """Test minimal template creates correct project structure."""
        project_name = "test-minimal"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(project_path)
            
            # Check minimal structure
            assert os.path.exists(os.path.join(project_path, "config", "app.yaml"))
            assert os.path.exists(os.path.join(project_path, "main.py"))
            assert os.path.exists(os.path.join(project_path, "routes", "html.py"))
            assert os.path.exists(os.path.join(project_path, "templates", "base.html"))
            assert os.path.exists(os.path.join(project_path, "pyproject.toml"))
            
            # Check configuration is minimal
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                assert config["app"]["name"] == project_name
                assert "extensions" not in config or not config.get("extensions")
    
    def test_standard_template_includes_common_extensions(self):
        """Test standard template includes auth, CSRF, and security extensions."""
        project_name = "test-standard"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "standard",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check standard template includes extensions
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                extensions = config.get("extensions", [])
                assert "beginnings.extensions.auth:AuthExtension" in extensions
                assert "beginnings.extensions.csrf:CSRFExtension" in extensions
                assert "beginnings.extensions.security_headers:SecurityHeadersExtension" in extensions
            
            # Check auth templates are included
            assert os.path.exists(os.path.join(project_path, "templates", "auth"))
            
            # Check environment configs
            assert os.path.exists(os.path.join(project_path, "config", "app.dev.yaml"))
            assert os.path.exists(os.path.join(project_path, "config", "app.staging.yaml"))
    
    def test_api_template_optimized_for_apis(self):
        """Test API template is optimized for API-only applications."""
        project_name = "test-api"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "api",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check API-specific configuration
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                
                # Should have API router configured
                assert "api" in config.get("routers", {})
                
                # Should include rate limiting and auth for APIs
                extensions = config.get("extensions", [])
                assert any("rate_limiting" in ext for ext in extensions)
                assert any("auth" in ext for ext in extensions)
            
            # Should have API routes
            assert os.path.exists(os.path.join(project_path, "routes", "api.py"))
            
            # Should have minimal HTML templates (just for docs)
            templates_dir = os.path.join(project_path, "templates")
            if os.path.exists(templates_dir):
                # If templates exist, they should be minimal
                template_files = os.listdir(templates_dir)
                assert len(template_files) <= 2  # Just base and maybe index
    
    def test_full_template_includes_all_features(self):
        """Test full template includes all bundled extensions and features."""
        project_name = "test-full"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "full",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check full configuration includes all extensions
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                extensions = config.get("extensions", [])
                
                # Should include all major extensions
                extension_names = [ext.split(":")[-1] for ext in extensions]
                assert "AuthExtension" in extension_names
                assert "CSRFExtension" in extension_names
                assert "RateLimitExtension" in extension_names
                assert "SecurityHeadersExtension" in extension_names
            
            # Should have both HTML and API routes
            assert os.path.exists(os.path.join(project_path, "routes", "html.py"))
            assert os.path.exists(os.path.join(project_path, "routes", "api.py"))
            
            # Should have complete template structure
            assert os.path.exists(os.path.join(project_path, "templates", "auth"))
            
            # Should have all environment configurations
            assert os.path.exists(os.path.join(project_path, "config", "app.dev.yaml"))
            assert os.path.exists(os.path.join(project_path, "config", "app.staging.yaml"))
            
            # Should have comprehensive test structure
            assert os.path.exists(os.path.join(project_path, "tests", "test_routes.py"))
            assert os.path.exists(os.path.join(project_path, "tests", "conftest.py"))
    
    def test_custom_template_interactive_selection(self):
        """Test custom template allows interactive feature selection."""
        project_name = "test-custom"
        
        # Mock user input for interactive selection
        user_inputs = [
            "y",  # HTML routes?
            "y",  # API routes?
            "y",  # Authentication?
            "n",  # CSRF protection? (test selective inclusion)
            "y",  # Rate limiting?
            "n",  # Security headers?
            "y",  # Staging configuration?
            "n",  # HTML routes detected. Include CSRF protection? (validation)
        ]
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            with patch('click.confirm') as mock_confirm:
                mock_confirm.side_effect = [inp == "y" for inp in user_inputs]
                
                result = self.runner.invoke(cli, [
                    "new", project_name,
                    "--template", "custom",
                    "--output-dir", self.temp_dir,
                    "--no-deps"
                ])
                
                assert result.exit_code == 0
                
                project_path = os.path.join(self.temp_dir, project_name)
                
                # Check configuration reflects user choices
                with open(os.path.join(project_path, "config", "app.yaml")) as f:
                    config = yaml.safe_load(f)
                    extensions = config.get("extensions", [])
                    
                    # Should include auth and rate limiting
                    assert any("auth" in ext.lower() for ext in extensions)
                    assert any("rate_limiting" in ext.lower() for ext in extensions)
                    
                    # Should NOT include CSRF and security headers
                    assert not any("csrf" in ext.lower() for ext in extensions)
                    assert not any("security_headers" in ext.lower() for ext in extensions)
                
                # Should have both route types
                assert os.path.exists(os.path.join(project_path, "routes", "html.py"))
                assert os.path.exists(os.path.join(project_path, "routes", "api.py"))


class TestTemplateSystem:
    """Test template system functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_template_variable_substitution(self):
        """Test template variables are properly substituted."""
        project_name = "my-awesome-project"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check project name substitution in configuration
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                assert config["app"]["name"] == project_name
            
            # Check project name substitution in pyproject.toml
            with open(os.path.join(project_path, "pyproject.toml")) as f:
                content = f.read()
                assert f'name = "{project_name}"' in content
            
            # Check project name substitution in README
            with open(os.path.join(project_path, "README.md")) as f:
                content = f.read()
                assert project_name in content
    
    def test_conditional_file_inclusion(self):
        """Test files are conditionally included based on features."""
        project_name = "test-conditional"
        
        # Test with auth enabled
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "standard",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            project_path = os.path.join(self.temp_dir, project_name)
            
            # Auth templates should be included
            assert os.path.exists(os.path.join(project_path, "templates", "auth"))
            
        # Clean up for next test
        shutil.rmtree(project_path)
        
        # Test with minimal template (no auth)
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Auth templates should NOT be included
            auth_templates_path = os.path.join(project_path, "templates", "auth")
            assert not os.path.exists(auth_templates_path)
    
    def test_template_validation_and_syntax(self):
        """Test generated templates have valid syntax."""
        project_name = "test-validation"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "full",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check YAML configuration is valid
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)  # Should not raise exception
                assert isinstance(config, dict)
            
            # Check Python files have valid syntax
            main_py_path = os.path.join(project_path, "main.py")
            with open(main_py_path) as f:
                content = f.read()
                compile(content, main_py_path, "exec")  # Should not raise exception
            
            # Check pyproject.toml is valid TOML
            import tomllib
            with open(os.path.join(project_path, "pyproject.toml"), "rb") as f:
                toml_data = tomllib.load(f)  # Should not raise exception
                assert isinstance(toml_data, dict)
    
    def test_custom_template_directory_support(self):
        """Test support for custom template directories."""
        # This test will be implemented when custom template support is added
        # For now, ensure the framework can be extended
        pass
    
    def test_template_versioning_compatibility(self):
        """Test template versioning and compatibility checking."""
        # This test will be implemented when template versioning is added
        # For now, ensure basic version info is included
        project_name = "test-versioning"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check that framework version is referenced
            with open(os.path.join(project_path, "pyproject.toml")) as f:
                content = f.read()
                assert "beginnings" in content


class TestInteractiveWizard:
    """Test interactive project creation wizard."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_user_input_collection_and_validation(self):
        """Test wizard collects and validates user input."""
        project_name = "test-wizard"
        
        # Test valid inputs
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            with patch('click.confirm') as mock_confirm:
                with patch('click.prompt') as mock_prompt:
                    # Mock valid responses
                    mock_confirm.return_value = True
                    mock_prompt.return_value = "8000"  # Port number
                    
                    result = self.runner.invoke(cli, [
                        "new", project_name,
                        "--template", "custom",
                        "--output-dir", self.temp_dir,
                        "--no-git",
                        "--no-deps"
                    ])
                    
                    assert result.exit_code == 0
        
        # Test invalid project name validation
        invalid_names = ["123invalid", "invalid-name-!", ""]
        for invalid_name in invalid_names:
            result = self.runner.invoke(cli, [
                "new", invalid_name,
                "--output-dir", self.temp_dir
            ])
            assert result.exit_code != 0
    
    def test_feature_selection_and_dependency_resolution(self):
        """Test feature selection resolves dependencies correctly."""
        project_name = "test-dependencies"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            with patch('click.confirm') as mock_confirm:
                # Mock responses: HTML, API, Auth, CSRF, Rate limiting, Security headers, Staging config, and any dependency validation prompts
                mock_confirm.side_effect = [True, True, True, True, False, False, True] + [True] * 10
                
                result = self.runner.invoke(cli, [
                    "new", project_name,
                    "--template", "custom",
                    "--output-dir", self.temp_dir,
                    "--no-git",
                    "--no-deps"
                ])
                
                assert result.exit_code == 0
                
                project_path = os.path.join(self.temp_dir, project_name)
                with open(os.path.join(project_path, "config", "app.yaml")) as f:
                    config = yaml.safe_load(f)
                    
                    # Auth should be included
                    extensions = config.get("extensions", [])
                    assert any("auth" in ext.lower() for ext in extensions)
                    
                    # CSRF should be included (user selected)
                    assert any("csrf" in ext.lower() for ext in extensions)
    
    def test_extension_selection_and_configuration_generation(self):
        """Test extension selection generates proper configuration."""
        project_name = "test-extension-config"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            with patch('click.confirm') as mock_confirm:
                # Select specific extensions
                mock_confirm.side_effect = [
                    True,   # HTML routes
                    True,   # API routes
                    True,   # Authentication
                    False,  # CSRF
                    True,   # Rate limiting
                    True,   # Security headers
                    True,   # Staging config
                    True,   # HTML routes detected. Include CSRF protection? (validation)
                ]
                
                result = self.runner.invoke(cli, [
                    "new", project_name,
                    "--template", "custom",
                    "--output-dir", self.temp_dir,
                    "--no-deps"
                ])
                
                assert result.exit_code == 0
                
                project_path = os.path.join(self.temp_dir, project_name)
                
                # Check that configuration sections are generated for selected extensions
                config_files = ["app.yaml"]
                for env in ["dev", "staging"]:
                    env_file = f"app.{env}.yaml"
                    if os.path.exists(os.path.join(project_path, "config", env_file)):
                        config_files.append(env_file)
                
                # At least one config file should have extension-specific config
                found_auth_config = False
                found_rate_limit_config = False
                
                for config_file in config_files:
                    config_path = os.path.join(project_path, "config", config_file)
                    if os.path.exists(config_path):
                        with open(config_path) as f:
                            content = f.read()
                            if "auth:" in content:
                                found_auth_config = True
                            if "rate_limiting:" in content:
                                found_rate_limit_config = True
                
                # Configuration should be generated for selected extensions
                # Note: This might be in separate files or inline
                assert found_auth_config or found_rate_limit_config
    
    def test_environment_setup_and_configuration_generation(self):
        """Test environment-specific configuration generation."""
        project_name = "test-environments"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "standard",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            project_path = os.path.join(self.temp_dir, project_name)
            
            # Check environment-specific configurations exist
            assert os.path.exists(os.path.join(project_path, "config", "app.dev.yaml"))
            assert os.path.exists(os.path.join(project_path, "config", "app.staging.yaml"))
            
            # Check development config has debug enabled
            with open(os.path.join(project_path, "config", "app.dev.yaml")) as f:
                dev_config = yaml.safe_load(f)
                if "app" in dev_config:
                    assert dev_config["app"].get("debug", False) is True
    
    def test_progress_indication_and_user_feedback(self):
        """Test wizard provides progress indication and feedback."""
        project_name = "test-progress"
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check that output includes progress indicators
            output = result.output
            assert "Creating" in output or "Created" in output
            assert project_name in output
    
    def test_error_recovery_and_input_validation(self):
        """Test wizard handles errors gracefully and validates input."""
        # Test cleanup on failure
        project_name = "test-error-recovery"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            # Simulate subprocess failure
            mock_subprocess.side_effect = Exception("Git initialization failed")
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-deps"  # Only git should fail
            ])
            
            # Should handle error gracefully
            assert result.exit_code != 0
            
            # Project directory should be cleaned up on failure
            # (This behavior needs to be implemented)
        
        # Test invalid template name
        result = self.runner.invoke(cli, [
            "new", "test-project",
            "--template", "nonexistent",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "unknown" in result.output.lower()


class TestGeneratedProjectIntegration:
    """Test that generated projects actually work."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generated_project_imports_successfully(self):
        """Test generated project can be imported without errors."""
        project_name = "test-imports"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "minimal",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Test that main.py can be compiled
            main_py_path = os.path.join(project_path, "main.py")
            with open(main_py_path) as f:
                content = f.read()
                compile(content, main_py_path, "exec")
    
    def test_generated_project_configuration_valid(self):
        """Test generated project has valid configuration."""
        project_name = "test-config-valid"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "full",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Test configuration validation
            from beginnings.config.validator import ConfigValidator
            from beginnings.config.enhanced_loader import load_config_with_includes
            
            config_dir = os.path.join(project_path, "config")
            config = load_config_with_includes(config_dir, None)
            
            validator = ConfigValidator()
            result = validator.validate(config, include_security=True)
            
            # Should have no critical errors
            assert not result.get("errors"), f"Configuration errors: {result.get('errors')}"
    
    def test_generated_project_tests_executable(self):
        """Test generated project tests can be executed."""
        project_name = "test-tests"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "standard",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check that test files exist and are valid Python
            tests_dir = os.path.join(project_path, "tests")
            assert os.path.exists(tests_dir)
            
            for test_file in os.listdir(tests_dir):
                if test_file.endswith(".py"):
                    test_path = os.path.join(tests_dir, test_file)
                    with open(test_path) as f:
                        content = f.read()
                        compile(content, test_path, "exec")  # Should not raise
    
    def test_generated_project_security_defaults(self):
        """Test generated project has secure default configurations."""
        project_name = "test-security"
        project_path = os.path.join(self.temp_dir, project_name)
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            result = self.runner.invoke(cli, [
                "new", project_name,
                "--template", "full",
                "--output-dir", self.temp_dir,
                "--no-git",
                "--no-deps"
            ])
            
            assert result.exit_code == 0
            
            # Check configuration has security defaults
            with open(os.path.join(project_path, "config", "app.yaml")) as f:
                config = yaml.safe_load(f)
                
                # Debug should be False in base config
                assert config.get("app", {}).get("debug", False) is False
                
                # Should have secure auth settings
                assert "auth" in config
                auth_config = config["auth"]
                assert auth_config["providers"]["session"]["cookie_secure"] is True
                assert auth_config["providers"]["session"]["cookie_httponly"] is True
                assert auth_config["providers"]["session"]["cookie_samesite"] == "strict"
                
                # Should have CSRF protection
                assert "csrf" in config
                csrf_config = config["csrf"]
                assert csrf_config["enabled"] is True
                assert csrf_config["secure_cookie"] is True
                
                # Should have security headers
                assert "security" in config
                security_config = config["security"]
                assert "headers" in security_config
                assert security_config["headers"]["x_frame_options"] == "DENY"
                
            # Check generated secure secrets in .env.example
            with open(os.path.join(project_path, ".env.example")) as f:
                env_content = f.read()
                
                # Should have generated secrets (not placeholder values)
                assert "SESSION_SECRET=" in env_content
                assert "JWT_SECRET=" in env_content
                # Secrets should be longer than placeholder text
                for line in env_content.split('\n'):
                    if line.startswith('SESSION_SECRET=') or line.startswith('JWT_SECRET='):
                        secret_value = line.split('=')[1]
                        # Should be 32+ chars and not the default placeholder
                        assert len(secret_value) >= 32
                        assert "your-secret" not in secret_value