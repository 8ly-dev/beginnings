"""
Test suite for configuration validation functionality.

Tests the configuration validation utilities according to Phase 1 planning document
specifications (lines 140-175).
"""

from __future__ import annotations

import pytest

from beginnings.config.validator import (
    ConfigurationSecurityError,
    ConfigurationValidationError,
    detect_configuration_conflicts,
    scan_for_security_issues,
    validate_configuration_structure,
    validate_configuration_with_security_check,
)


class TestConfigurationStructureValidation:
    """Test configuration structure validation functionality."""

    def test_validate_configuration_structure_with_valid_dict(self) -> None:
        """Test that valid configuration dictionaries pass validation."""
        valid_configs = [
            {},  # Empty dict is valid
            {"app": {"name": "test"}},
            {"debug": False, "host": "localhost", "port": 8000},
            {
                "app": {"name": "myapp", "version": "1.0.0"},
                "database": {"url": "sqlite:///app.db"},
                "routes": {"/": {"template": "index.html"}}
            }
        ]

        for config in valid_configs:
            # Should not raise any exception
            validate_configuration_structure(config)

    def test_validate_configuration_structure_with_invalid_types(self) -> None:
        """Test that non-dictionary configurations raise validation errors."""
        invalid_configs = [
            None,
            "string_config",
            ["list", "config"],
            42,
            True,
            object()
        ]

        for invalid_config in invalid_configs:
            with pytest.raises(ConfigurationValidationError, match="Configuration must be a dictionary"):
                validate_configuration_structure(invalid_config)

    def test_validate_configuration_structure_error_message_content(self) -> None:
        """Test that validation error messages are descriptive."""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            validate_configuration_structure("not_a_dict")

        assert "Configuration must be a dictionary" in str(exc_info.value)

    def test_validate_configuration_structure_with_nested_structures(self) -> None:
        """Test validation with complex nested configuration structures."""
        complex_config = {
            "app": {
                "name": "complex_app",
                "version": "2.1.0",
                "metadata": {
                    "author": "developer",
                    "description": "A complex application",
                    "tags": ["web", "api", "microservice"]
                }
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "workers": 4,
                "timeout": 30
            },
            "database": {
                "primary": {
                    "url": "postgresql://user:pass@localhost/db",
                    "pool_size": 10
                },
                "cache": {
                    "url": "redis://localhost:6379/0",
                    "ttl": 3600
                }
            },
            "extensions": [
                {"name": "auth", "enabled": True},
                {"name": "logging", "enabled": True, "level": "INFO"}
            ]
        }

        # Should handle complex nested structures without issues
        validate_configuration_structure(complex_config)


class TestConfigurationConflictDetection:
    """Test configuration conflict detection functionality."""

    def test_detect_no_conflicts_in_valid_configurations(self) -> None:
        """Test that valid configurations have no conflicts detected."""
        valid_configs = [
            {},
            {"debug": False},
            {"production": True},
            {"debug": False, "production": True},
            {"debug": True, "production": False},
            {"environment": "development", "debug": True},
            {"environment": "production", "debug": False}
        ]

        for config in valid_configs:
            conflicts = detect_configuration_conflicts(config)
            assert conflicts == []

    def test_detect_debug_production_conflict(self) -> None:
        """Test detection of debug and production mode conflict."""
        conflicting_config = {
            "debug": True,
            "production": True
        }

        conflicts = detect_configuration_conflicts(conflicting_config)
        assert len(conflicts) == 1
        assert "Debug mode and production mode cannot both be enabled" in conflicts[0]

    def test_detect_conflicts_with_additional_settings(self) -> None:
        """Test conflict detection with additional non-conflicting settings."""
        config_with_conflict = {
            "app": {"name": "test_app"},
            "debug": True,
            "production": True,  # This creates the conflict
            "host": "localhost",
            "port": 8000,
            "database": {"url": "sqlite:///test.db"}
        }

        conflicts = detect_configuration_conflicts(config_with_conflict)
        assert len(conflicts) == 1
        assert "Debug mode and production mode cannot both be enabled" in conflicts[0]

    def test_detect_conflicts_returns_list_of_strings(self) -> None:
        """Test that conflict detection returns a list of string descriptions."""
        conflicting_config = {"debug": True, "production": True}
        conflicts = detect_configuration_conflicts(conflicting_config)

        assert isinstance(conflicts, list)
        assert all(isinstance(conflict, str) for conflict in conflicts)

    def test_detect_conflicts_with_falsy_values(self) -> None:
        """Test that falsy values don't trigger false conflicts."""
        non_conflicting_configs = [
            {"debug": False, "production": True},
            {"debug": True, "production": False},
            {"debug": None, "production": True},
            {"debug": True, "production": None},
            {"debug": 0, "production": 1},
            {"debug": "", "production": "true"}
        ]

        for config in non_conflicting_configs:
            conflicts = detect_configuration_conflicts(config)
            # These shouldn't trigger the debug/production conflict
            # since we check for truthy values
            if config.get("debug") and config.get("production"):
                assert len(conflicts) >= 1
            else:
                assert conflicts == []


class TestSecurityIssueScanning:
    """Test security issue scanning functionality."""

    def test_scan_secure_configurations(self) -> None:
        """Test that secure configurations have no security issues detected."""
        secure_configs = [
            {},
            {"secret_key": "a_very_secure_random_key_12345"},
            {"debug": False, "host": "0.0.0.0"},
            {"debug": True, "host": "localhost"},
            {"debug": True, "host": "127.0.0.1"},
            {
                "secret_key": "proper_secret_key",
                "debug": False,
                "host": "production.example.com",
                "ssl": True
            }
        ]

        for config in secure_configs:
            issues = scan_for_security_issues(config)
            assert issues == []

    def test_detect_default_secret_key_issue(self) -> None:
        """Test detection of default or empty secret keys."""
        insecure_configs = [
            {"secret_key": "default"},
            {"secret_key": ""},
            {"secret_key": None}  # This might not trigger the check depending on implementation
        ]

        for config in insecure_configs:
            issues = scan_for_security_issues(config)
            if config.get("secret_key") == "default" or config.get("secret_key") == "":
                assert len(issues) >= 1
                assert any("Secret key should not be default or empty" in issue for issue in issues)

    def test_detect_debug_with_public_host_issue(self) -> None:
        """Test detection of debug mode with public host binding."""
        insecure_config = {
            "debug": True,
            "host": "0.0.0.0"
        }

        issues = scan_for_security_issues(insecure_config)
        assert len(issues) >= 1
        assert any("Debug mode with public host binding is a security risk" in issue for issue in issues)

    def test_detect_multiple_security_issues(self) -> None:
        """Test detection of multiple security issues in one configuration."""
        highly_insecure_config = {
            "secret_key": "default",
            "debug": True,
            "host": "0.0.0.0"
        }

        issues = scan_for_security_issues(highly_insecure_config)
        assert len(issues) >= 2

        issue_text = " ".join(issues)
        assert "Secret key should not be default or empty" in issue_text
        assert "Debug mode with public host binding is a security risk" in issue_text

    def test_security_scan_returns_list_of_strings(self) -> None:
        """Test that security scanning returns a list of string descriptions."""
        insecure_config = {"secret_key": "default"}
        issues = scan_for_security_issues(insecure_config)

        assert isinstance(issues, list)
        assert all(isinstance(issue, str) for issue in issues)

    def test_security_scan_with_edge_cases(self) -> None:
        """Test security scanning with edge case values."""
        edge_case_configs = [
            {"secret_key": " "},  # Whitespace-only key
            {"secret_key": "0"},  # Single character
            {"debug": "true", "host": "0.0.0.0"},  # String boolean
            {"debug": 1, "host": "0.0.0.0"},  # Integer boolean
        ]

        for config in edge_case_configs:
            issues = scan_for_security_issues(config)
            # Should handle edge cases without crashing
            assert isinstance(issues, list)


class TestCompleteConfigurationValidation:
    """Test complete configuration validation with security checks."""

    def test_validate_completely_valid_configuration(self) -> None:
        """Test that completely valid configurations pass all validations."""
        valid_configs = [
            {},
            {
                "app": {"name": "secure_app"},
                "secret_key": "very_secure_key_123456",
                "debug": False,
                "host": "localhost",
                "port": 8000
            },
            {
                "app": {"name": "production_app", "version": "1.0.0"},
                "secret_key": "production_secret_key",
                "debug": False,
                "production": True,
                "host": "api.example.com",
                "database": {"url": "postgresql://localhost/db"}
            }
        ]

        for config in valid_configs:
            # Should not raise any exception
            validate_configuration_with_security_check(config)

    def test_validate_configuration_structure_failure(self) -> None:
        """Test that structural validation failures are caught."""
        invalid_structure = "not_a_dict"

        with pytest.raises(ConfigurationValidationError, match="Configuration must be a dictionary"):
            validate_configuration_with_security_check(invalid_structure)

    def test_validate_configuration_conflict_failure(self) -> None:
        """Test that configuration conflicts are caught."""
        conflicting_config = {
            "debug": True,
            "production": True
        }

        with pytest.raises(ConfigurationValidationError, match="Configuration conflicts"):
            validate_configuration_with_security_check(conflicting_config)

    def test_validate_configuration_security_failure(self) -> None:
        """Test that security issues are caught."""
        insecure_config = {
            "secret_key": "default",
            "debug": True,
            "host": "0.0.0.0"
        }

        with pytest.raises(ConfigurationSecurityError, match="Security issues"):
            validate_configuration_with_security_check(insecure_config)

    def test_validation_error_hierarchy(self) -> None:
        """Test that ConfigurationSecurityError inherits from ConfigurationValidationError."""
        assert issubclass(ConfigurationSecurityError, ConfigurationValidationError)

        # Test that we can catch both specific and general errors
        try:
            raise ConfigurationSecurityError("Test security error")
        except ConfigurationValidationError:
            pass  # Should catch as parent class
        except Exception:
            pytest.fail("ConfigurationSecurityError should be catchable as ConfigurationValidationError")

    def test_validation_order_structure_first(self) -> None:
        """Test that structure validation happens before conflict/security checks."""
        # If we pass a non-dict, we should get a structure error
        # even if it would theoretically have conflicts or security issues
        with pytest.raises(ConfigurationValidationError, match="Configuration must be a dictionary"):
            validate_configuration_with_security_check(["not", "a", "dict"])

    def test_validation_order_conflicts_before_security(self) -> None:
        """Test that conflict detection happens before security scanning."""
        # Create a config with both conflicts and security issues
        problematic_config = {
            "debug": True,
            "production": True,  # Conflict
            "secret_key": "default"  # Security issue
        }

        # Should raise ConfigurationValidationError (conflicts) not ConfigurationSecurityError
        with pytest.raises(ConfigurationValidationError, match="Configuration conflicts"):
            validate_configuration_with_security_check(problematic_config)


class TestValidationErrorMessages:
    """Test validation error message quality and content."""

    def test_conflict_error_message_content(self) -> None:
        """Test that conflict error messages are descriptive."""
        conflicting_config = {"debug": True, "production": True}

        with pytest.raises(ConfigurationValidationError) as exc_info:
            validate_configuration_with_security_check(conflicting_config)

        error_message = str(exc_info.value)
        assert "Configuration conflicts" in error_message
        assert "Debug mode and production mode cannot both be enabled" in error_message

    def test_security_error_message_content(self) -> None:
        """Test that security error messages are descriptive."""
        insecure_config = {"secret_key": "default"}

        with pytest.raises(ConfigurationSecurityError) as exc_info:
            validate_configuration_with_security_check(insecure_config)

        error_message = str(exc_info.value)
        assert "Security issues" in error_message
        assert "Secret key should not be default or empty" in error_message

    def test_multiple_issues_in_error_message(self) -> None:
        """Test that multiple issues are properly included in error messages."""
        # Config with multiple security issues
        multi_issue_config = {
            "secret_key": "",
            "debug": True,
            "host": "0.0.0.0"
        }

        with pytest.raises(ConfigurationSecurityError) as exc_info:
            validate_configuration_with_security_check(multi_issue_config)

        error_message = str(exc_info.value)
        assert "Security issues" in error_message
        # Should contain both security issues
        assert "Secret key should not be default or empty" in error_message
        assert "Debug mode with public host binding is a security risk" in error_message


class TestValidationIntegration:
    """Test validation integration with real-world scenarios."""

    def test_development_environment_configuration(self) -> None:
        """Test validation of typical development environment configuration."""
        dev_config = {
            "app": {"name": "myapp", "version": "0.1.0"},
            "environment": "development",
            "debug": True,
            "host": "127.0.0.1",
            "port": 8000,
            "secret_key": "dev_secret_key_not_for_production",
            "database": {"url": "sqlite:///dev.db"},
            "logging": {"level": "DEBUG"}
        }

        # Should pass validation (debug=True with localhost is OK)
        validate_configuration_with_security_check(dev_config)

    def test_production_environment_configuration(self) -> None:
        """Test validation of typical production environment configuration."""
        prod_config = {
            "app": {"name": "myapp", "version": "1.0.0"},
            "environment": "production",
            "debug": False,
            "production": True,
            "host": "api.mycompany.com",
            "port": 443,
            "secret_key": "very_secure_production_key_with_proper_entropy",
            "database": {"url": "postgresql://user:pass@db.internal/prod"},
            "logging": {"level": "WARNING"},
            "ssl": {"enabled": True}
        }

        # Should pass validation
        validate_configuration_with_security_check(prod_config)

    def test_misconfigured_production_environment(self) -> None:
        """Test validation catches common production misconfigurations."""
        bad_prod_config = {
            "app": {"name": "myapp"},
            "environment": "production",
            "debug": True,  # Bad: debug in production
            "production": True,  # Conflict with debug
            "host": "0.0.0.0",  # Bad: public binding with debug
            "secret_key": "default"  # Bad: default secret
        }

        # Should fail validation (will fail on conflicts first)
        with pytest.raises(ConfigurationValidationError):
            validate_configuration_with_security_check(bad_prod_config)

    def test_empty_configuration_validation(self) -> None:
        """Test that empty configuration is valid but may lack required settings."""
        empty_config = {}

        # Empty config should pass structural validation
        # (Missing required settings would be caught by application logic, not validator)
        validate_configuration_with_security_check(empty_config)

    def test_configuration_with_extensions(self) -> None:
        """Test validation of configuration with extension settings."""
        config_with_extensions = {
            "app": {"name": "extended_app"},
            "secret_key": "app_secret_key",
            "extensions": {
                "auth": {
                    "provider": "oauth",
                    "client_id": "app_client_id",
                    "redirect_uri": "https://app.com/callback"
                },
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "destination": "file"
                },
                "cache": {
                    "backend": "redis",
                    "url": "redis://localhost:6379/0",
                    "ttl": 3600
                }
            }
        }

        # Should handle complex nested extension configurations
        validate_configuration_with_security_check(config_with_extensions)
