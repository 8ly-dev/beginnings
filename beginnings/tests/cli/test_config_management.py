"""Tests for advanced configuration management."""

import pytest
import tempfile
import os
import yaml
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from beginnings.cli.main import cli
from beginnings.config.enhanced_loader import load_config_with_includes


class TestConfigurationValidation:
    """Test configuration validation and schema checking."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_validate_valid_configuration(self):
        """Test validation of valid configuration."""
        # Create valid config
        config_content = {
            "app": {
                "name": "test-app",
                "debug": False,
                "host": "127.0.0.1",
                "port": 8000
            },
            "extensions": [
                "beginnings.extensions.auth:AuthExtension"
            ]
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_path
        ])
        
        assert result.exit_code == 0
        assert "✓ Configuration is valid" in result.output
    
    def test_config_validate_invalid_schema(self):
        """Test validation of invalid configuration schema."""
        # Create invalid config - missing required fields
        config_content = {
            "invalid_field": "value"
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_path
        ])
        
        assert result.exit_code != 0
        assert "✗ Configuration validation failed" in result.output
    
    def test_config_validate_security_issues(self):
        """Test detection of security issues in configuration."""
        # Create config with security issues
        config_content = {
            "app": {
                "name": "test-app",
                "debug": True,  # Debug enabled in production
                "host": "0.0.0.0",  # Insecure host binding
                "port": 8000
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak",  # Weak secret
                        "cookie_secure": False  # Insecure cookies
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", config_path,
            "--security-audit"
        ])
        
        assert result.exit_code != 0
        assert "Security issues detected" in result.output
        assert "weak" in result.output.lower() or "secret" in result.output.lower()
    
    def test_config_validate_with_includes(self):
        """Test validation of configuration with includes."""
        # Create base config
        base_config = {
            "app": {
                "name": "test-app",
                "debug": False
            }
        }
        
        # Create override config
        override_config = {
            "include": ["base.yaml"],
            "app": {
                "debug": True
            }
        }
        
        base_path = os.path.join(self.temp_dir, "base.yaml")
        override_path = os.path.join(self.temp_dir, "override.yaml")
        
        with open(base_path, "w") as f:
            yaml.dump(base_config, f)
        
        with open(override_path, "w") as f:
            yaml.dump(override_config, f)
        
        result = self.runner.invoke(cli, [
            "config", "validate",
            "--config", override_path
        ])
        
        assert result.exit_code == 0
    
    def test_config_show_merged_configuration(self):
        """Test showing merged configuration."""
        config_content = {
            "app": {
                "name": "test-app",
                "debug": False
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "show",
            "--config", config_path
        ])
        
        assert result.exit_code == 0
        assert "test-app" in result.output
    
    def test_config_show_with_format_json(self):
        """Test showing configuration in JSON format."""
        config_content = {
            "app": {
                "name": "test-app"
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "show",
            "--config", config_path,
            "--format", "json"
        ])
        
        assert result.exit_code == 0
        # Should be valid JSON
        try:
            json.loads(result.output.strip())
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


class TestConfigurationAudit:
    """Test configuration security auditing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_audit_security_scan(self):
        """Test comprehensive security audit."""
        config_content = {
            "app": {
                "name": "test-app",
                "debug": False,
                "host": "127.0.0.1",
                "port": 8000
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "a" * 32,  # Valid secret
                        "cookie_secure": True,
                        "cookie_httponly": True
                    }
                }
            },
            "security": {
                "headers": {
                    "x_frame_options": "DENY",
                    "strict_transport_security": {
                        "max_age": 31536000
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "audit",
            "--config", config_path
        ])
        
        # Should succeed since no issues found
        assert result.exit_code == 0
        assert "Security Audit Results" in result.output
    
    def test_config_audit_finds_vulnerabilities(self):
        """Test audit detects security vulnerabilities."""
        config_content = {
            "app": {
                "debug": True,  # Security issue
                "host": "0.0.0.0"  # Security issue
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak",  # Security issue
                        "cookie_secure": False  # Security issue
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "audit",
            "--config", config_path
        ])
        
        assert result.exit_code != 0
        assert "issues found" in result.output.lower()
    
    def test_config_audit_with_severity_filter(self):
        """Test audit with severity filtering."""
        config_content = {
            "app": {
                "debug": True,  # Warning
                "host": "127.0.0.1"
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak"  # Error
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        # Test showing only errors
        result = self.runner.invoke(cli, [
            "config", "audit",
            "--config", config_path,
            "--severity", "error"
        ])
        
        assert "secret" in result.output.lower()
    
    def test_config_audit_compliance_check(self):
        """Test compliance checking against security standards."""
        config_content = {
            "app": {
                "name": "test-app",
                "debug": False
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "audit",
            "--config", config_path,
            "--compliance", "owasp"
        ])
        
        assert result.exit_code == 0
        assert "OWASP" in result.output or "compliance" in result.output.lower()


class TestConfigurationAutoFix:
    """Test configuration auto-fix capabilities."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_fix_security_issues(self):
        """Test auto-fixing security issues."""
        config_content = {
            "app": {
                "name": "test-app",
                "debug": True,  # Should be fixed to False in production
                "host": "0.0.0.0"  # Should be fixed to 127.0.0.1
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak",  # Should generate strong secret
                        "cookie_secure": False  # Should be True in production
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", config_path,
            "--backup"
        ], input="y\n")  # Confirm fixes
        
        print(f"Result output: {result.output}")
        print(f"Result exit code: {result.exit_code}")
        print(f"Files in temp dir: {os.listdir(self.temp_dir)}")
        
        assert result.exit_code == 0
        assert "Fixed" in result.output or "updated" in result.output.lower()
        
        # Verify backup was created (contains timestamp)
        backup_files = [f for f in os.listdir(self.temp_dir) if '.backup.' in f]
        assert len(backup_files) > 0
    
    def test_config_fix_dry_run(self):
        """Test dry-run mode for config fixes."""
        config_content = {
            "app": {
                "debug": True
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        original_content = yaml.dump(config_content)
        with open(config_path, "w") as f:
            f.write(original_content)
        
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", config_path,
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        assert "would fix" in result.output.lower() or "dry run" in result.output.lower()
        
        # Verify file wasn't actually changed
        with open(config_path) as f:
            current_content = f.read()
        assert current_content == original_content
    
    def test_config_fix_specific_issues(self):
        """Test fixing specific types of issues."""
        config_content = {
            "app": {
                "debug": True
            },
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "weak"
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        # Fix only security issues
        result = self.runner.invoke(cli, [
            "config", "fix",
            "--config", config_path,
            "--type", "security"
        ], input="y\n")
        
        assert result.exit_code == 0


class TestConfigurationGeneration:
    """Test configuration generation and templates."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_generate_from_template(self):
        """Test generating configuration from template."""
        result = self.runner.invoke(cli, [
            "config", "generate",
            "--template", "production",
            "--output", os.path.join(self.temp_dir, "prod.yaml")
        ])
        
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(self.temp_dir, "prod.yaml"))
    
    def test_config_generate_with_environment(self):
        """Test generating configuration for specific environment."""
        result = self.runner.invoke(cli, [
            "config", "generate",
            "--environment", "staging",
            "--output", os.path.join(self.temp_dir, "staging.yaml")
        ])
        
        assert result.exit_code == 0
        
        # Verify staging-specific settings
        with open(os.path.join(self.temp_dir, "staging.yaml")) as f:
            config = yaml.safe_load(f)
            
        # Should have production-like security but with some staging accommodations
        assert config.get("app", {}).get("debug", True) is False
    
    def test_config_generate_with_features(self):
        """Test generating configuration with specific features."""
        result = self.runner.invoke(cli, [
            "config", "generate",
            "--features", "auth,csrf,rate-limiting",
            "--output", os.path.join(self.temp_dir, "features.yaml")
        ])
        
        assert result.exit_code == 0
        
        with open(os.path.join(self.temp_dir, "features.yaml")) as f:
            config = yaml.safe_load(f)
        
        # Should have auth configuration
        assert "auth" in config
        assert "csrf" in config
        assert "rate_limiting" in config
    
    def test_config_diff_configurations(self):
        """Test comparing configurations."""
        # Create two configs
        config1_content = {
            "app": {
                "name": "test-app",
                "debug": True
            }
        }
        
        config2_content = {
            "app": {
                "name": "test-app",
                "debug": False,
                "port": 8000
            }
        }
        
        config1_path = os.path.join(self.temp_dir, "config1.yaml")
        config2_path = os.path.join(self.temp_dir, "config2.yaml")
        
        with open(config1_path, "w") as f:
            yaml.dump(config1_content, f)
        
        with open(config2_path, "w") as f:
            yaml.dump(config2_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "diff",
            config1_path,
            config2_path
        ])
        
        assert result.exit_code == 0
        assert "debug" in result.output
        assert "port" in result.output


class TestEnvironmentSpecificConfig:
    """Test environment-specific configuration handling."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_environment_detection(self):
        """Test automatic environment detection."""
        config_content = {
            "app": {
                "name": "test-app"
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        with patch.dict(os.environ, {"BEGINNINGS_ENV": "production"}):
            result = self.runner.invoke(cli, [
                "config", "show",
                "--config", config_path
            ])
            
            assert result.exit_code == 0
            # Should detect production environment
    
    def test_config_environment_override(self):
        """Test environment-specific overrides."""
        # Create base config
        base_config = {
            "app": {
                "debug": True,
                "port": 8000
            }
        }
        
        # Create production override
        prod_config = {
            "include": ["app.yaml"],
            "app": {
                "debug": False
            }
        }
        
        base_path = os.path.join(self.temp_dir, "app.yaml")
        prod_path = os.path.join(self.temp_dir, "app.production.yaml")
        
        with open(base_path, "w") as f:
            yaml.dump(base_config, f)
        
        with open(prod_path, "w") as f:
            yaml.dump(prod_config, f)
        
        result = self.runner.invoke(cli, [
            "config", "show",
            "--config", prod_path
        ])
        
        assert result.exit_code == 0
        # Should show merged configuration with debug=False
    
    def test_config_secrets_masking(self):
        """Test masking of secrets in config output."""
        config_content = {
            "auth": {
                "providers": {
                    "session": {
                        "secret_key": "very-secret-key"
                    }
                }
            }
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "config", "show",
            "--config", config_path
        ])
        
        assert result.exit_code == 0
        # Secret should be masked
        assert "very-secret-key" not in result.output
        assert "***" in result.output or "[MASKED]" in result.output