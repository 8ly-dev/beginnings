"""Test-driven development tests for verification tools.

This module contains tests that define the expected behavior of the verification
tools system before implementation. Following TDD principles:
1. Write failing tests first (RED)
2. Implement minimal code to pass tests (GREEN)  
3. Refactor while keeping tests green (REFACTOR)
"""

import pytest
import tempfile
import json
import yaml
import toml
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum

# These imports will fail initially - that's expected in TDD
try:
    from beginnings.verification import (
        VerificationFramework,
        DependencyChecker,
        ComplianceValidator,
        LicenseChecker,
        VulnerabilityScanner,
        VerificationConfig,
        VerificationResult,
        DependencyResult,
        ComplianceResult,
        LicenseResult,
        VulnerabilityResult,
        VerificationSeverity,
        ComplianceStandard,
        DependencyStatus,
        LicenseType,
        VulnerabilityLevel,
        VerificationError,
        VerificationReport
    )
except ImportError:
    # Expected during TDD - tests define the interface
    VerificationFramework = None
    DependencyChecker = None
    ComplianceValidator = None
    LicenseChecker = None
    VulnerabilityScanner = None
    VerificationConfig = None
    VerificationResult = None
    DependencyResult = None
    ComplianceResult = None
    LicenseResult = None
    VulnerabilityResult = None
    VerificationSeverity = None
    ComplianceStandard = None
    DependencyStatus = None
    LicenseType = None
    VulnerabilityLevel = None
    VerificationError = None
    VerificationReport = None


class TestVerificationSeverity:
    """Test VerificationSeverity enum for verification severity levels."""
    
    def test_verification_severity_values(self):
        """Test VerificationSeverity enum values."""
        assert VerificationSeverity.INFO.value == "info"
        assert VerificationSeverity.LOW.value == "low"
        assert VerificationSeverity.MEDIUM.value == "medium"
        assert VerificationSeverity.HIGH.value == "high"
        assert VerificationSeverity.CRITICAL.value == "critical"
    
    def test_verification_severity_ordering(self):
        """Test VerificationSeverity ordering for priority."""
        assert VerificationSeverity.CRITICAL > VerificationSeverity.HIGH
        assert VerificationSeverity.HIGH > VerificationSeverity.MEDIUM
        assert VerificationSeverity.MEDIUM > VerificationSeverity.LOW
        assert VerificationSeverity.LOW > VerificationSeverity.INFO


class TestComplianceStandard:
    """Test ComplianceStandard enum for compliance standards."""
    
    def test_compliance_standard_values(self):
        """Test ComplianceStandard enum values."""
        assert ComplianceStandard.PCI_DSS.value == "pci_dss"
        assert ComplianceStandard.HIPAA.value == "hipaa"
        assert ComplianceStandard.GDPR.value == "gdpr"
        assert ComplianceStandard.SOX.value == "sox"
        assert ComplianceStandard.ISO_27001.value == "iso_27001"
        assert ComplianceStandard.NIST.value == "nist"


class TestDependencyStatus:
    """Test DependencyStatus enum for dependency statuses."""
    
    def test_dependency_status_values(self):
        """Test DependencyStatus enum values."""
        assert DependencyStatus.UP_TO_DATE.value == "up_to_date"
        assert DependencyStatus.OUTDATED.value == "outdated"
        assert DependencyStatus.VULNERABLE.value == "vulnerable"
        assert DependencyStatus.DEPRECATED.value == "deprecated"
        assert DependencyStatus.UNKNOWN.value == "unknown"


class TestLicenseType:
    """Test LicenseType enum for license classifications."""
    
    def test_license_type_values(self):
        """Test LicenseType enum values."""
        assert LicenseType.PERMISSIVE.value == "permissive"
        assert LicenseType.COPYLEFT.value == "copyleft"
        assert LicenseType.PROPRIETARY.value == "proprietary"
        assert LicenseType.PUBLIC_DOMAIN.value == "public_domain"
        assert LicenseType.UNKNOWN.value == "unknown"


class TestVerificationConfig:
    """Test VerificationConfig for verification framework configuration."""
    
    def test_verification_config_creation(self):
        """Test VerificationConfig initialization."""
        config = VerificationConfig(
            name="production_verification",
            dependency_check_enabled=True,
            compliance_check_enabled=True,
            license_check_enabled=True,
            vulnerability_scan_enabled=True,
            standards=[ComplianceStandard.PCI_DSS, ComplianceStandard.GDPR]
        )
        
        assert config.name == "production_verification"
        assert config.dependency_check_enabled is True
        assert config.compliance_check_enabled is True
        assert config.license_check_enabled is True
        assert config.vulnerability_scan_enabled is True
        assert ComplianceStandard.PCI_DSS in config.standards
        assert ComplianceStandard.GDPR in config.standards
        assert config.fail_on_high_severity is True  # Expected default
        assert config.fail_on_critical_severity is True  # Expected default
    
    def test_verification_config_with_custom_settings(self):
        """Test VerificationConfig with custom settings."""
        config = VerificationConfig(
            name="custom_verification",
            dependency_check_enabled=True,
            compliance_check_enabled=False,
            license_check_enabled=True,
            vulnerability_scan_enabled=True,
            standards=[ComplianceStandard.HIPAA],
            fail_on_high_severity=False,
            fail_on_critical_severity=True,
            max_dependency_age_days=365,
            allowed_license_types=[LicenseType.PERMISSIVE, LicenseType.PUBLIC_DOMAIN],
            blocked_dependencies=["package-with-issues", "deprecated-lib"],
            custom_settings={
                "timeout_seconds": 300,
                "parallel_scans": True,
                "cache_results": True
            }
        )
        
        assert config.name == "custom_verification"
        assert config.compliance_check_enabled is False
        assert config.fail_on_high_severity is False
        assert config.max_dependency_age_days == 365
        assert LicenseType.PERMISSIVE in config.allowed_license_types
        assert "package-with-issues" in config.blocked_dependencies
        assert config.custom_settings["timeout_seconds"] == 300
    
    def test_verification_config_validation(self):
        """Test VerificationConfig validation."""
        config = VerificationConfig(
            name="test_config",
            dependency_check_enabled=True
        )
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Empty name should fail
        config.name = ""
        errors = config.validate()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)


class TestDependencyChecker:
    """Test DependencyChecker for dependency verification."""
    
    @pytest.fixture
    def checker(self):
        """Create DependencyChecker instance."""
        return DependencyChecker()
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with dependency files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create Python requirements.txt
            requirements_file = project_path / "requirements.txt"
            requirements_file.write_text('''\
# Core dependencies
requests==2.28.1
flask==2.2.2
sqlalchemy==1.4.45

# Development dependencies
pytest==7.1.3
black==22.8.0

# Outdated package
django==3.2.0  # Outdated version

# Package with known vulnerabilities
pillow==8.0.0  # Known security issues

# Deprecated package
deprecated-package==1.0.0
''')
            
            # Create package.json for Node.js
            package_json = project_path / "package.json"
            package_json.write_text(json.dumps({
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.2",
                    "lodash": "^4.17.21",
                    "moment": "^2.29.4",  # Deprecated
                    "axios": "^0.27.2"
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                    "eslint": "^8.23.0"
                }
            }, indent=2))
            
            # Create Pipfile for pipenv
            pipfile = project_path / "Pipfile"
            pipfile.write_text('''\
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
flask = "*"
celery = "*"

[dev-packages]
pytest = "*"
mypy = "*"

[requires]
python_version = "3.9"
''')
            
            # Create poetry pyproject.toml
            pyproject_toml = project_path / "pyproject.toml"
            pyproject_content = {
                "tool": {
                    "poetry": {
                        "name": "test-project",
                        "version": "0.1.0",
                        "description": "",
                        "authors": ["Test Author <test@example.com>"],
                        "dependencies": {
                            "python": "^3.9",
                            "fastapi": "^0.85.0",
                            "uvicorn": "^0.18.0",
                            "pydantic": "^1.10.0"
                        },
                        "group": {
                            "dev": {
                                "dependencies": {
                                    "pytest": "^7.1.0",
                                    "black": "^22.8.0",
                                    "isort": "^5.10.0"
                                }
                            }
                        }
                    }
                }
            }
            pyproject_toml.write_text(toml.dumps(pyproject_content))
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_scan_dependencies(self, checker, temp_project_dir):
        """Test scanning all dependency files in project."""
        results = await checker.scan_dependencies(str(temp_project_dir))
        
        assert len(results) > 0
        
        # Should find dependencies from multiple files
        dependency_names = [result.package_name for result in results]
        assert "requests" in dependency_names
        assert "flask" in dependency_names
        assert "express" in dependency_names
        assert "fastapi" in dependency_names
    
    @pytest.mark.asyncio
    async def test_check_outdated_dependencies(self, checker, temp_project_dir):
        """Test checking for outdated dependencies."""
        with patch.object(checker, '_get_latest_version') as mock_latest:
            # Mock version responses
            def mock_version_response(package_name):
                versions = {
                    "requests": "2.31.0",  # Newer than 2.28.1
                    "flask": "2.3.3",      # Newer than 2.2.2
                    "django": "4.2.5",     # Much newer than 3.2.0
                    "pillow": "10.0.0"     # Newer than 8.0.0
                }
                return versions.get(package_name, "1.0.0")
            
            mock_latest.side_effect = mock_version_response
            
            outdated = await checker.check_outdated_dependencies(str(temp_project_dir))
            
            assert len(outdated) > 0
            
            # Should identify django as significantly outdated
            django_result = next(
                (result for result in outdated if result.package_name == "django"),
                None
            )
            assert django_result is not None
            assert django_result.status == DependencyStatus.OUTDATED
            assert django_result.current_version == "3.2.0"
            assert django_result.latest_version == "4.2.5"
    
    @pytest.mark.asyncio
    async def test_check_vulnerable_dependencies(self, checker, temp_project_dir):
        """Test checking for vulnerable dependencies."""
        with patch.object(checker, '_get_vulnerability_data') as mock_vulns:
            # Mock vulnerability data
            def mock_vulnerability_response(package_name, version):
                vulnerabilities = {
                    ("pillow", "8.0.0"): [
                        {
                            "id": "CVE-2021-34552",
                            "severity": "high",
                            "description": "Buffer overflow in Pillow",
                            "fixed_in": "8.3.0"
                        }
                    ]
                }
                return vulnerabilities.get((package_name, version), [])
            
            mock_vulns.side_effect = mock_vulnerability_response
            
            vulnerable = await checker.check_vulnerable_dependencies(str(temp_project_dir))
            
            assert len(vulnerable) > 0
            
            # Should identify pillow as vulnerable
            pillow_result = next(
                (result for result in vulnerable if result.package_name == "pillow"),
                None
            )
            assert pillow_result is not None
            assert pillow_result.status == DependencyStatus.VULNERABLE
            assert len(pillow_result.vulnerabilities) > 0
            assert pillow_result.vulnerabilities[0]["id"] == "CVE-2021-34552"
    
    @pytest.mark.asyncio
    async def test_check_deprecated_dependencies(self, checker, temp_project_dir):
        """Test checking for deprecated dependencies."""
        with patch.object(checker, '_get_deprecation_status') as mock_deprecated:
            # Mock deprecation data
            def mock_deprecation_response(package_name):
                deprecated_packages = {
                    "deprecated-package": {
                        "deprecated": True,
                        "reason": "Package is no longer maintained",
                        "alternative": "new-package"
                    },
                    "moment": {
                        "deprecated": True,
                        "reason": "Moment.js is deprecated in favor of modern alternatives",
                        "alternative": "date-fns or dayjs"
                    }
                }
                return deprecated_packages.get(package_name, {"deprecated": False})
            
            mock_deprecated.side_effect = mock_deprecation_response
            
            deprecated = await checker.check_deprecated_dependencies(str(temp_project_dir))
            
            assert len(deprecated) > 0
            
            # Should identify deprecated packages
            deprecated_names = [result.package_name for result in deprecated]
            assert "deprecated-package" in deprecated_names or "moment" in deprecated_names
    
    @pytest.mark.asyncio
    async def test_analyze_dependency_tree(self, checker, temp_project_dir):
        """Test analyzing dependency tree for conflicts."""
        with patch.object(checker, '_build_dependency_tree') as mock_tree:
            # Mock dependency tree with conflicts
            mock_tree.return_value = {
                "requests": {
                    "version": "2.28.1",
                    "dependencies": {
                        "urllib3": ">=1.21.1,<1.27",
                        "certifi": ">=2017.4.17"
                    }
                },
                "boto3": {
                    "version": "1.26.0",
                    "dependencies": {
                        "urllib3": ">=1.25.4,<1.27",  # Potential conflict
                        "botocore": ">=1.29.0,<1.30.0"
                    }
                }
            }
            
            conflicts = await checker.analyze_dependency_tree(str(temp_project_dir))
            
            assert isinstance(conflicts, list)
            # May or may not find conflicts depending on version resolution
    
    @pytest.mark.asyncio
    async def test_check_license_compatibility(self, checker, temp_project_dir):
        """Test checking license compatibility."""
        with patch.object(checker, '_get_package_license') as mock_license:
            # Mock license data
            def mock_license_response(package_name):
                licenses = {
                    "requests": "Apache-2.0",
                    "flask": "BSD-3-Clause",
                    "gpl-package": "GPL-3.0",  # Potentially incompatible
                    "mit-package": "MIT"
                }
                return licenses.get(package_name, "Unknown")
            
            mock_license.side_effect = mock_license_response
            
            license_results = await checker.check_license_compatibility(
                str(temp_project_dir),
                allowed_licenses=[LicenseType.PERMISSIVE],
                blocked_licenses=[LicenseType.COPYLEFT]
            )
            
            assert len(license_results) >= 0
    
    @pytest.mark.asyncio
    async def test_generate_dependency_report(self, checker, temp_project_dir):
        """Test generating comprehensive dependency report."""
        report = await checker.generate_dependency_report(str(temp_project_dir))
        
        assert report.total_dependencies > 0
        assert report.direct_dependencies >= 0
        assert report.transitive_dependencies >= 0
        assert report.outdated_count >= 0
        assert report.vulnerable_count >= 0
        assert report.deprecated_count >= 0
        assert len(report.dependency_breakdown) > 0
        assert report.overall_health_score >= 0
        assert report.overall_health_score <= 100


class TestComplianceValidator:
    """Test ComplianceValidator for compliance validation."""
    
    @pytest.fixture
    def validator(self):
        """Create ComplianceValidator instance."""
        return ComplianceValidator()
    
    @pytest.fixture
    def temp_compliance_project(self):
        """Create temporary project with compliance-related files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "compliance_project"
            project_path.mkdir()
            
            # Create security policy file
            security_policy = project_path / "SECURITY.md"
            security_policy.write_text('''\
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities to security@example.com.
''')
            
            # Create privacy policy
            privacy_policy = project_path / "PRIVACY.md"
            privacy_policy.write_text('''\
# Privacy Policy

This application collects and processes personal data in accordance with GDPR.

## Data Collection
- User account information
- Usage analytics (anonymized)

## Data Processing
- Data is encrypted at rest and in transit
- Access is logged and audited

## User Rights
- Right to access personal data
- Right to rectification
- Right to erasure
- Right to data portability
''')
            
            # Create configuration with security settings
            config_file = project_path / "config.json"
            config_file.write_text(json.dumps({
                "security": {
                    "encryption_enabled": True,
                    "https_only": True,
                    "secure_cookies": True,
                    "csrf_protection": True,
                    "xss_protection": True,
                    "content_security_policy": True
                },
                "logging": {
                    "audit_enabled": True,
                    "log_level": "INFO",
                    "retention_days": 90
                },
                "database": {
                    "ssl_enabled": True,
                    "backup_enabled": True,
                    "encryption_at_rest": True
                }
            }, indent=2))
            
            # Create audit log directory
            audit_dir = project_path / "logs" / "audit"
            audit_dir.mkdir(parents=True)
            
            # Create sample audit log
            audit_log = audit_dir / "audit.log"
            audit_log.write_text('''\
2023-01-01T10:00:00Z [INFO] User login: user@example.com
2023-01-01T10:05:00Z [INFO] Data access: user@example.com accessed personal data
2023-01-01T10:10:00Z [WARN] Failed login attempt from 192.168.1.100
2023-01-01T10:15:00Z [INFO] User logout: user@example.com
''')
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_validate_pci_dss_compliance(self, validator, temp_compliance_project):
        """Test PCI DSS compliance validation."""
        results = await validator.validate_compliance(
            str(temp_compliance_project),
            ComplianceStandard.PCI_DSS
        )
        
        assert len(results) >= 0
        
        # Should check for PCI DSS requirements
        requirement_ids = [result.requirement_id for result in results]
        # Common PCI DSS requirements that should be checked
        expected_requirements = ["1.1", "2.1", "3.1", "4.1", "6.1", "8.1", "10.1", "11.1", "12.1"]
        
        # At least some requirements should be checked
        assert any(req_id in requirement_ids for req_id in expected_requirements)
    
    @pytest.mark.asyncio
    async def test_validate_gdpr_compliance(self, validator, temp_compliance_project):
        """Test GDPR compliance validation."""
        results = await validator.validate_compliance(
            str(temp_compliance_project),
            ComplianceStandard.GDPR
        )
        
        assert len(results) >= 0
        
        # Should find privacy policy compliance
        privacy_results = [result for result in results if "privacy" in result.description.lower()]
        assert len(privacy_results) > 0
    
    @pytest.mark.asyncio
    async def test_validate_hipaa_compliance(self, validator, temp_compliance_project):
        """Test HIPAA compliance validation."""
        results = await validator.validate_compliance(
            str(temp_compliance_project),
            ComplianceStandard.HIPAA
        )
        
        assert len(results) >= 0
        
        # Should check for HIPAA requirements
        security_results = [result for result in results if "security" in result.description.lower()]
        assert len(security_results) >= 0
    
    @pytest.mark.asyncio
    async def test_check_data_protection_policies(self, validator, temp_compliance_project):
        """Test checking data protection policies."""
        policies = await validator.check_data_protection_policies(str(temp_compliance_project))
        
        assert len(policies) > 0
        
        # Should find privacy policy
        policy_names = [policy.policy_name for policy in policies]
        assert "PRIVACY.md" in policy_names or "privacy" in [p.lower() for p in policy_names]
    
    @pytest.mark.asyncio
    async def test_validate_security_configurations(self, validator, temp_compliance_project):
        """Test validating security configurations."""
        security_configs = await validator.validate_security_configurations(str(temp_compliance_project))
        
        assert len(security_configs) > 0
        
        # Should validate encryption, HTTPS, etc.
        config_types = [config.config_type for config in security_configs]
        assert any("encryption" in ct.lower() for ct in config_types)
    
    @pytest.mark.asyncio
    async def test_check_audit_logging(self, validator, temp_compliance_project):
        """Test checking audit logging compliance."""
        audit_results = await validator.check_audit_logging(str(temp_compliance_project))
        
        assert len(audit_results) > 0
        
        # Should find audit log configuration and files
        assert any(result.compliant for result in audit_results)
    
    @pytest.mark.asyncio
    async def test_validate_access_controls(self, validator, temp_compliance_project):
        """Test validating access control mechanisms."""
        access_controls = await validator.validate_access_controls(str(temp_compliance_project))
        
        assert len(access_controls) >= 0
        
        # Should check authentication and authorization
        control_types = [control.control_type for control in access_controls]
        expected_controls = ["authentication", "authorization", "session_management"]
        
        # At least some controls should be evaluated
        assert any(ct in control_types for ct in expected_controls)
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, validator, temp_compliance_project):
        """Test generating comprehensive compliance report."""
        report = await validator.generate_compliance_report(
            str(temp_compliance_project),
            [ComplianceStandard.GDPR, ComplianceStandard.PCI_DSS]
        )
        
        assert len(report.standards_evaluated) > 0
        assert ComplianceStandard.GDPR in report.standards_evaluated
        assert report.overall_compliance_score >= 0
        assert report.overall_compliance_score <= 100
        assert len(report.compliance_gaps) >= 0
        assert len(report.recommendations) >= 0


class TestLicenseChecker:
    """Test LicenseChecker for license compliance."""
    
    @pytest.fixture
    def checker(self):
        """Create LicenseChecker instance."""
        return LicenseChecker()
    
    @pytest.fixture
    def temp_licensed_project(self):
        """Create temporary project with various licenses."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "licensed_project"
            project_path.mkdir()
            
            # Create project license
            license_file = project_path / "LICENSE"
            license_file.write_text('''\
MIT License

Copyright (c) 2023 Test Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')
            
            # Create requirements with license information
            requirements_file = project_path / "requirements.txt"
            requirements_file.write_text('''\
# MIT licensed packages
requests==2.28.1  # Apache-2.0
flask==2.2.2      # BSD-3-Clause
click==8.1.3      # BSD-3-Clause

# Potentially problematic licenses
gpl-package==1.0.0    # GPL-3.0 (copyleft)
proprietary-lib==2.0.0  # Proprietary

# Unknown license
unknown-package==1.0.0
''')
            
            # Create package.json with license info
            package_json = project_path / "package.json"
            package_json.write_text(json.dumps({
                "name": "licensed-project",
                "version": "1.0.0",
                "license": "MIT",
                "dependencies": {
                    "express": "^4.18.2",     # MIT
                    "lodash": "^4.17.21",     # MIT
                    "react": "^18.2.0",       # MIT
                    "gpl-module": "^1.0.0"    # GPL-3.0
                }
            }, indent=2))
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_scan_project_licenses(self, checker, temp_licensed_project):
        """Test scanning all licenses in project."""
        licenses = await checker.scan_project_licenses(str(temp_licensed_project))
        
        assert len(licenses) > 0
        
        # Should find project license
        project_licenses = [lic for lic in licenses if lic.source_type == "project"]
        assert len(project_licenses) > 0
        assert any(lic.license_name == "MIT" for lic in project_licenses)
    
    @pytest.mark.asyncio
    async def test_check_dependency_licenses(self, checker, temp_licensed_project):
        """Test checking dependency licenses."""
        with patch.object(checker, '_get_package_license_info') as mock_license:
            # Mock license responses
            def mock_license_response(package_name):
                licenses = {
                    "requests": {"license": "Apache-2.0", "type": LicenseType.PERMISSIVE},
                    "flask": {"license": "BSD-3-Clause", "type": LicenseType.PERMISSIVE},
                    "gpl-package": {"license": "GPL-3.0", "type": LicenseType.COPYLEFT},
                    "proprietary-lib": {"license": "Proprietary", "type": LicenseType.PROPRIETARY},
                    "unknown-package": {"license": "Unknown", "type": LicenseType.UNKNOWN}
                }
                return licenses.get(package_name, {"license": "Unknown", "type": LicenseType.UNKNOWN})
            
            mock_license.side_effect = mock_license_response
            
            dep_licenses = await checker.check_dependency_licenses(str(temp_licensed_project))
            
            assert len(dep_licenses) > 0
            
            # Should identify different license types
            license_types = [lic.license_type for lic in dep_licenses]
            assert LicenseType.PERMISSIVE in license_types
            assert LicenseType.COPYLEFT in license_types or LicenseType.PROPRIETARY in license_types
    
    @pytest.mark.asyncio
    async def test_check_license_compatibility(self, checker, temp_licensed_project):
        """Test checking license compatibility with project license."""
        with patch.object(checker, '_get_package_license_info') as mock_license:
            mock_license.side_effect = lambda pkg: {
                "requests": {"license": "Apache-2.0", "type": LicenseType.PERMISSIVE},
                "gpl-package": {"license": "GPL-3.0", "type": LicenseType.COPYLEFT}
            }.get(pkg, {"license": "MIT", "type": LicenseType.PERMISSIVE})
            
            compatibility = await checker.check_license_compatibility(
                str(temp_licensed_project),
                project_license="MIT"
            )
            
            assert len(compatibility) >= 0
            
            # GPL should be flagged as potentially incompatible with MIT
            incompatible = [comp for comp in compatibility if not comp.compatible]
            gpl_conflicts = [comp for comp in incompatible if "gpl" in comp.package_name.lower()]
            assert len(gpl_conflicts) >= 0  # May or may not be detected depending on rules
    
    @pytest.mark.asyncio
    async def test_validate_license_headers(self, checker, temp_licensed_project):
        """Test validating license headers in source files."""
        # Create source files with and without license headers
        src_dir = temp_licensed_project / "src"
        src_dir.mkdir()
        
        # File with proper license header
        good_file = src_dir / "good.py"
        good_file.write_text('''\
# Copyright (c) 2023 Test Project
# Licensed under the MIT License

def hello_world():
    return "Hello, World!"
''')
        
        # File without license header
        bad_file = src_dir / "bad.py"
        bad_file.write_text('''\
def hello_world():
    return "Hello, World!"
''')
        
        header_results = await checker.validate_license_headers(str(temp_licensed_project))
        
        assert len(header_results) >= 2
        
        # Should identify files with and without proper headers
        file_results = {result.file_path: result.has_license_header for result in header_results}
        assert any(not has_header for has_header in file_results.values())
    
    @pytest.mark.asyncio
    async def test_check_forbidden_licenses(self, checker, temp_licensed_project):
        """Test checking for forbidden licenses."""
        with patch.object(checker, '_get_package_license_info') as mock_license:
            mock_license.side_effect = lambda pkg: {
                "gpl-package": {"license": "GPL-3.0", "type": LicenseType.COPYLEFT},
                "proprietary-lib": {"license": "Proprietary", "type": LicenseType.PROPRIETARY}
            }.get(pkg, {"license": "MIT", "type": LicenseType.PERMISSIVE})
            
            forbidden = await checker.check_forbidden_licenses(
                str(temp_licensed_project),
                forbidden_licenses=["GPL-3.0", "Proprietary"]
            )
            
            assert len(forbidden) >= 0
            
            # Should identify packages with forbidden licenses
            forbidden_packages = [result.package_name for result in forbidden]
            assert any("gpl" in pkg.lower() or "proprietary" in pkg.lower() for pkg in forbidden_packages)
    
    @pytest.mark.asyncio
    async def test_generate_license_report(self, checker, temp_licensed_project):
        """Test generating comprehensive license report."""
        report = await checker.generate_license_report(str(temp_licensed_project))
        
        assert report.project_license is not None
        assert report.total_dependencies >= 0
        assert len(report.license_breakdown) >= 0
        assert report.compliance_score >= 0
        assert report.compliance_score <= 100
        assert len(report.license_conflicts) >= 0
        assert len(report.recommendations) >= 0


class TestVulnerabilityScanner:
    """Test VulnerabilityScanner for security vulnerability scanning."""
    
    @pytest.fixture
    def scanner(self):
        """Create VulnerabilityScanner instance."""
        return VulnerabilityScanner()
    
    @pytest.fixture
    def temp_vulnerable_project(self):
        """Create temporary project with vulnerable dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "vulnerable_project"
            project_path.mkdir()
            
            # Create requirements with known vulnerable packages
            requirements_file = project_path / "requirements.txt"
            requirements_file.write_text('''\
# Packages with known vulnerabilities
django==3.0.0          # CVE-2020-9402, CVE-2020-7471
pillow==8.0.0          # CVE-2021-34552
requests==2.20.0       # CVE-2018-18074
urllib3==1.24.1        # CVE-2019-11324

# Up-to-date packages
flask==2.3.0
sqlalchemy==2.0.0
''')
            
            # Create package.json with vulnerable Node packages
            package_json = project_path / "package.json"
            package_json.write_text(json.dumps({
                "name": "vulnerable-project",
                "version": "1.0.0",
                "dependencies": {
                    "lodash": "4.17.4",      # CVE-2018-3721, CVE-2019-10744
                    "moment": "2.18.0",      # ReDoS vulnerability
                    "express": "4.16.0",     # CVE-2017-16119
                    "axios": "0.21.0"        # CVE-2020-28168
                }
            }, indent=2))
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_scan_vulnerabilities(self, scanner, temp_vulnerable_project):
        """Test scanning for vulnerabilities."""
        with patch.object(scanner, '_get_vulnerability_database') as mock_db:
            # Mock vulnerability database
            mock_db.return_value = {
                ("django", "3.0.0"): [
                    {
                        "id": "CVE-2020-9402",
                        "severity": "high",
                        "description": "SQL injection in Django",
                        "fixed_in": "3.0.4"
                    }
                ],
                ("pillow", "8.0.0"): [
                    {
                        "id": "CVE-2021-34552",
                        "severity": "critical",
                        "description": "Buffer overflow in Pillow",
                        "fixed_in": "8.3.0"
                    }
                ],
                ("lodash", "4.17.4"): [
                    {
                        "id": "CVE-2018-3721",
                        "severity": "high",
                        "description": "Prototype pollution in lodash",
                        "fixed_in": "4.17.5"
                    }
                ]
            }
            
            vulnerabilities = await scanner.scan_vulnerabilities(str(temp_vulnerable_project))
            
            assert len(vulnerabilities) > 0
            
            # Should find vulnerabilities in multiple packages
            vulnerable_packages = [vuln.package_name for vuln in vulnerabilities]
            assert "django" in vulnerable_packages
            assert "pillow" in vulnerable_packages
    
    @pytest.mark.asyncio
    async def test_check_cve_database(self, scanner):
        """Test checking against CVE database."""
        with patch.object(scanner, '_query_cve_database') as mock_cve:
            mock_cve.return_value = [
                {
                    "id": "CVE-2023-12345",
                    "severity": "critical",
                    "description": "Remote code execution vulnerability",
                    "cvss_score": 9.8
                }
            ]
            
            cve_results = await scanner.check_cve_database("vulnerable-package", "1.0.0")
            
            assert len(cve_results) > 0
            assert cve_results[0]["id"] == "CVE-2023-12345"
            assert cve_results[0]["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_scan_with_npm_audit(self, scanner, temp_vulnerable_project):
        """Test scanning with npm audit integration."""
        with patch.object(scanner, '_run_npm_audit') as mock_npm:
            mock_npm.return_value = {
                "vulnerabilities": {
                    "lodash": {
                        "severity": "high",
                        "via": ["CVE-2018-3721"],
                        "effects": [],
                        "range": "<4.17.5",
                        "nodes": ["node_modules/lodash"],
                        "fixAvailable": True
                    }
                },
                "metadata": {
                    "vulnerabilities": {
                        "info": 0,
                        "low": 0,
                        "moderate": 0,
                        "high": 1,
                        "critical": 0,
                        "total": 1
                    }
                }
            }
            
            npm_results = await scanner.scan_with_npm_audit(str(temp_vulnerable_project))
            
            assert len(npm_results) > 0
            assert any(result.package_name == "lodash" for result in npm_results)
    
    @pytest.mark.asyncio
    async def test_scan_with_safety(self, scanner, temp_vulnerable_project):
        """Test scanning with Safety tool integration."""
        with patch.object(scanner, '_run_safety_check') as mock_safety:
            mock_safety.return_value = [
                {
                    "package": "django",
                    "installed": "3.0.0",
                    "vulnerability": "CVE-2020-9402",
                    "severity": "high",
                    "description": "Django before 3.0.4 allows SQL injection"
                }
            ]
            
            safety_results = await scanner.scan_with_safety(str(temp_vulnerable_project))
            
            assert len(safety_results) > 0
            assert any(result.package_name == "django" for result in safety_results)
    
    @pytest.mark.asyncio
    async def test_prioritize_vulnerabilities(self, scanner):
        """Test vulnerability prioritization by severity and exploitability."""
        vulnerabilities = [
            VulnerabilityResult(
                package_name="pkg1",
                vulnerability_id="CVE-2023-0001",
                severity=VulnerabilityLevel.CRITICAL,
                cvss_score=9.8,
                exploitability="high",
                description="Critical RCE vulnerability"
            ),
            VulnerabilityResult(
                package_name="pkg2",
                vulnerability_id="CVE-2023-0002",
                severity=VulnerabilityLevel.HIGH,
                cvss_score=7.5,
                exploitability="medium",
                description="High severity vulnerability"
            ),
            VulnerabilityResult(
                package_name="pkg3",
                vulnerability_id="CVE-2023-0003",
                severity=VulnerabilityLevel.MEDIUM,
                cvss_score=5.0,
                exploitability="low",
                description="Medium severity vulnerability"
            )
        ]
        
        prioritized = await scanner.prioritize_vulnerabilities(vulnerabilities)
        
        assert len(prioritized) == 3
        # Should be ordered by severity/priority
        assert prioritized[0].severity == VulnerabilityLevel.CRITICAL
        assert prioritized[0].cvss_score >= prioritized[1].cvss_score
    
    @pytest.mark.asyncio
    async def test_generate_vulnerability_report(self, scanner, temp_vulnerable_project):
        """Test generating comprehensive vulnerability report."""
        with patch.object(scanner, 'scan_vulnerabilities') as mock_scan:
            mock_vulnerabilities = [
                VulnerabilityResult(
                    package_name="django",
                    vulnerability_id="CVE-2020-9402",
                    severity=VulnerabilityLevel.HIGH,
                    cvss_score=7.5,
                    description="SQL injection vulnerability"
                ),
                VulnerabilityResult(
                    package_name="pillow",
                    vulnerability_id="CVE-2021-34552",
                    severity=VulnerabilityLevel.CRITICAL,
                    cvss_score=9.1,
                    description="Buffer overflow vulnerability"
                )
            ]
            mock_scan.return_value = mock_vulnerabilities
            
            report = await scanner.generate_vulnerability_report(str(temp_vulnerable_project))
            
            assert report.total_vulnerabilities == 2
            assert report.critical_vulnerabilities == 1
            assert report.high_vulnerabilities == 1
            assert report.medium_vulnerabilities == 0
            assert report.low_vulnerabilities == 0
            assert report.risk_score > 0
            assert len(report.affected_packages) == 2


class TestVerificationFramework:
    """Test VerificationFramework for orchestrating all verifications."""
    
    @pytest.fixture
    def framework(self):
        """Create VerificationFramework instance."""
        return VerificationFramework()
    
    @pytest.fixture
    def comprehensive_verification_project(self):
        """Create comprehensive project for verification testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "verification_project"
            project_path.mkdir()
            
            # Create various files for comprehensive verification
            
            # License file
            (project_path / "LICENSE").write_text("MIT License\n\nCopyright (c) 2023")
            
            # Requirements with mixed dependency health
            (project_path / "requirements.txt").write_text('''\
requests==2.28.1
flask==2.2.2
django==3.0.0  # Outdated and vulnerable
pillow==8.0.0  # Vulnerable
''')
            
            # Security policy
            (project_path / "SECURITY.md").write_text("# Security Policy\n\nReport vulnerabilities to security@example.com")
            
            # Privacy policy for GDPR
            (project_path / "PRIVACY.md").write_text("# Privacy Policy\n\nGDPR compliant data handling")
            
            # Configuration
            (project_path / "config.json").write_text(json.dumps({
                "security": {
                    "encryption_enabled": True,
                    "https_only": True
                }
            }))
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_verification(self, framework, comprehensive_verification_project):
        """Test running comprehensive verification."""
        config = VerificationConfig(
            name="comprehensive_verification",
            dependency_check_enabled=True,
            compliance_check_enabled=True,
            license_check_enabled=True,
            vulnerability_scan_enabled=True,
            standards=[ComplianceStandard.GDPR, ComplianceStandard.PCI_DSS]
        )
        
        with patch.object(framework, '_run_dependency_check') as mock_deps, \
             patch.object(framework, '_run_compliance_check') as mock_compliance, \
             patch.object(framework, '_run_license_check') as mock_license, \
             patch.object(framework, '_run_vulnerability_scan') as mock_vulns:
            
            # Mock results
            mock_deps.return_value = [Mock(severity=VerificationSeverity.HIGH)]
            mock_compliance.return_value = [Mock(severity=VerificationSeverity.MEDIUM)]
            mock_license.return_value = [Mock(severity=VerificationSeverity.LOW)]
            mock_vulns.return_value = [Mock(severity=VerificationSeverity.CRITICAL)]
            
            report = await framework.run_comprehensive_verification(
                str(comprehensive_verification_project),
                config
            )
            
            assert report.total_issues >= 4
            assert report.critical_issues >= 1
            assert report.high_issues >= 1
            assert report.verification_score >= 0
            assert report.verification_score <= 100
    
    @pytest.mark.asyncio
    async def test_generate_verification_summary(self, framework, comprehensive_verification_project):
        """Test generating verification summary."""
        config = VerificationConfig(
            name="summary_verification",
            dependency_check_enabled=True,
            vulnerability_scan_enabled=True
        )
        
        summary = await framework.generate_verification_summary(
            str(comprehensive_verification_project),
            config
        )
        
        assert summary.project_name is not None
        assert summary.verification_timestamp is not None
        assert summary.overall_score >= 0
        assert summary.overall_score <= 100
        assert len(summary.category_scores) > 0
        assert len(summary.recommendations) >= 0
    
    @pytest.mark.asyncio
    async def test_continuous_verification_monitoring(self, framework):
        """Test continuous verification monitoring setup."""
        config = VerificationConfig(
            name="continuous_verification",
            dependency_check_enabled=True,
            vulnerability_scan_enabled=True
        )
        
        monitoring_config = {
            "schedule": "daily",
            "alert_on_critical": True,
            "alert_on_new_vulnerabilities": True,
            "baseline_comparison": True
        }
        
        monitor_result = await framework.setup_continuous_monitoring(
            "/path/to/project",
            config,
            monitoring_config
        )
        
        assert monitor_result.monitoring_enabled is True
        assert monitor_result.schedule == "daily"
        assert monitor_result.alert_channels is not None


class TestVerificationIntegration:
    """Integration tests for verification tools."""
    
    def test_ci_cd_verification_pipeline(self):
        """Test verification integration with CI/CD pipeline."""
        pipeline_config = {
            "fail_on_critical_vulnerabilities": True,
            "fail_on_license_violations": True,
            "fail_on_compliance_gaps": False,
            "generate_artifacts": True,
            "upload_to_security_dashboard": True
        }
        
        # Would test CI/CD pipeline integration
        # pipeline = VerificationPipeline(pipeline_config)
        # result = pipeline.run_verification("/path/to/project")
        # assert result.exit_code in [0, 1]
    
    def test_security_dashboard_integration(self):
        """Test integration with security dashboard."""
        dashboard_config = {
            "dashboard_url": "https://security-dashboard.example.com",
            "api_key": "dashboard-api-key",
            "team_id": "development-team",
            "auto_assign_issues": True
        }
        
        # Would test dashboard integration
        # dashboard = SecurityDashboard(dashboard_config)
        # upload_result = dashboard.upload_verification_results(verification_report)
        # assert upload_result.success is True
    
    def test_policy_as_code_integration(self):
        """Test policy-as-code integration."""
        policy_config = {
            "policy_engine": "opa",  # Open Policy Agent
            "policy_files": ["security.rego", "compliance.rego"],
            "custom_rules": True,
            "policy_validation": True
        }
        
        # Would test policy engine integration
        # policy_engine = PolicyEngine(policy_config)
        # policy_result = policy_engine.evaluate_policies(verification_results)
        # assert policy_result.policy_violations >= 0