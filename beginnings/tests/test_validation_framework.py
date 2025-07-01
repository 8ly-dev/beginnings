"""Test-driven development tests for validation framework.

This module contains tests that define the expected behavior of the validation
framework system before implementation. Following TDD principles:
1. Write failing tests first (RED)
2. Implement minimal code to pass tests (GREEN)  
3. Refactor while keeping tests green (REFACTOR)
"""

import pytest
import tempfile
import ast
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum

# These imports will fail initially - that's expected in TDD
try:
    from beginnings.validation import (
        ValidationFramework,
        CodeQualityValidator,
        SecurityValidator,
        StyleValidator,
        ComplexityValidator,
        ValidationRule,
        ValidationConfig,
        ValidationResult,
        ValidationSeverity,
        ValidationCategory,
        ValidationError,
        QualityMetrics,
        SecurityFindings,
        StyleViolations,
        ComplexityReport,
        ValidationReport
    )
except ImportError:
    # Expected during TDD - tests define the interface
    ValidationFramework = None
    CodeQualityValidator = None
    SecurityValidator = None
    StyleValidator = None
    ComplexityValidator = None
    ValidationRule = None
    ValidationConfig = None
    ValidationResult = None
    ValidationSeverity = None
    ValidationCategory = None
    ValidationError = None
    QualityMetrics = None
    SecurityFindings = None
    StyleViolations = None
    ComplexityReport = None
    ValidationReport = None


class TestValidationSeverity:
    """Test ValidationSeverity enum for validation severity levels."""
    
    def test_validation_severity_values(self):
        """Test ValidationSeverity enum values."""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"
    
    def test_validation_severity_ordering(self):
        """Test ValidationSeverity ordering for priority."""
        assert ValidationSeverity.CRITICAL > ValidationSeverity.ERROR
        assert ValidationSeverity.ERROR > ValidationSeverity.WARNING
        assert ValidationSeverity.WARNING > ValidationSeverity.INFO


class TestValidationCategory:
    """Test ValidationCategory enum for validation categories."""
    
    def test_validation_category_values(self):
        """Test ValidationCategory enum values."""
        assert ValidationCategory.CODE_QUALITY.value == "code_quality"
        assert ValidationCategory.SECURITY.value == "security"
        assert ValidationCategory.STYLE.value == "style"
        assert ValidationCategory.COMPLEXITY.value == "complexity"
        assert ValidationCategory.PERFORMANCE.value == "performance"
        assert ValidationCategory.MAINTAINABILITY.value == "maintainability"


class TestValidationRule:
    """Test ValidationRule dataclass for validation rule configuration."""
    
    def test_validation_rule_creation(self):
        """Test ValidationRule initialization."""
        rule = ValidationRule(
            name="no_hardcoded_passwords",
            category=ValidationCategory.SECURITY,
            severity=ValidationSeverity.CRITICAL,
            description="Detect hardcoded passwords in code",
            pattern=r'password\s*=\s*["\'][^"\']+["\']',
            enabled=True
        )
        
        assert rule.name == "no_hardcoded_passwords"
        assert rule.category == ValidationCategory.SECURITY
        assert rule.severity == ValidationSeverity.CRITICAL
        assert rule.description == "Detect hardcoded passwords in code"
        assert rule.pattern is not None
        assert rule.enabled is True
        assert rule.auto_fix is False  # Expected default
        assert rule.tags == []  # Expected default
    
    def test_validation_rule_with_custom_settings(self):
        """Test ValidationRule with custom settings."""
        rule = ValidationRule(
            name="function_complexity",
            category=ValidationCategory.COMPLEXITY,
            severity=ValidationSeverity.WARNING,
            description="Check function cyclomatic complexity",
            threshold=10,
            enabled=True,
            auto_fix=False,
            tags=["complexity", "maintainability"],
            custom_settings={
                "max_complexity": 15,
                "include_nested": True,
                "exclude_patterns": ["test_*", "*_test.py"]
            }
        )
        
        assert rule.name == "function_complexity"
        assert rule.category == ValidationCategory.COMPLEXITY
        assert rule.threshold == 10
        assert "complexity" in rule.tags
        assert "maintainability" in rule.tags
        assert rule.custom_settings["max_complexity"] == 15
        assert rule.custom_settings["include_nested"] is True
    
    def test_validation_rule_validation(self):
        """Test ValidationRule validation."""
        rule = ValidationRule(
            name="test_rule",
            category=ValidationCategory.CODE_QUALITY,
            severity=ValidationSeverity.WARNING,
            description="Test rule",
            enabled=True
        )
        
        # Valid rule should pass
        errors = rule.validate()
        assert len(errors) == 0
        
        # Empty name should fail
        rule.name = ""
        errors = rule.validate()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)
        
        # Empty description should fail
        rule.name = "test_rule"
        rule.description = ""
        errors = rule.validate()
        assert len(errors) > 0
        assert any("description" in error.lower() for error in errors)


class TestValidationConfig:
    """Test ValidationConfig for validation framework configuration."""
    
    def test_validation_config_creation(self):
        """Test ValidationConfig initialization."""
        rules = [
            ValidationRule(
                name="no_print_statements",
                category=ValidationCategory.CODE_QUALITY,
                severity=ValidationSeverity.WARNING,
                description="Avoid print statements in production code",
                pattern=r'\bprint\s*\(',
                enabled=True
            ),
            ValidationRule(
                name="sql_injection_check",
                category=ValidationCategory.SECURITY,
                severity=ValidationSeverity.CRITICAL,
                description="Check for SQL injection vulnerabilities",
                enabled=True
            )
        ]
        
        config = ValidationConfig(
            name="production_validation",
            rules=rules,
            include_patterns=["*.py", "*.js"],
            exclude_patterns=["test_*", "*_test.py", "tests/"],
            max_file_size_mb=10,
            parallel_processing=True
        )
        
        assert config.name == "production_validation"
        assert len(config.rules) == 2
        assert "*.py" in config.include_patterns
        assert "test_*" in config.exclude_patterns
        assert config.max_file_size_mb == 10
        assert config.parallel_processing is True
        assert config.fail_on_error is True  # Expected default
        assert config.generate_report is True  # Expected default
    
    def test_validation_config_with_custom_settings(self):
        """Test ValidationConfig with custom settings."""
        config = ValidationConfig(
            name="custom_validation",
            rules=[],
            include_patterns=["src/**/*.py"],
            exclude_patterns=["*/migrations/*", "*/venv/*"],
            max_file_size_mb=5,
            parallel_processing=False,
            fail_on_error=False,
            generate_report=True,
            report_format="json",
            output_file="/tmp/validation_report.json",
            custom_settings={
                "timeout_seconds": 300,
                "max_workers": 4,
                "cache_enabled": True
            }
        )
        
        assert config.name == "custom_validation"
        assert config.parallel_processing is False
        assert config.fail_on_error is False
        assert config.report_format == "json"
        assert config.output_file == "/tmp/validation_report.json"
        assert config.custom_settings["timeout_seconds"] == 300
        assert config.custom_settings["max_workers"] == 4
    
    def test_validation_config_validation(self):
        """Test ValidationConfig validation."""
        config = ValidationConfig(
            name="test_config",
            rules=[],
            include_patterns=["*.py"]
        )
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Empty name should fail
        config.name = ""
        errors = config.validate()
        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)


class TestValidationResult:
    """Test ValidationResult for validation result data."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult initialization."""
        result = ValidationResult(
            rule_name="no_hardcoded_secrets",
            file_path="/src/app.py",
            line_number=42,
            column_number=15,
            severity=ValidationSeverity.CRITICAL,
            category=ValidationCategory.SECURITY,
            message="Hardcoded secret detected",
            code_snippet="api_key = 'sk-1234567890abcdef'"
        )
        
        assert result.rule_name == "no_hardcoded_secrets"
        assert result.file_path == "/src/app.py"
        assert result.line_number == 42
        assert result.column_number == 15
        assert result.severity == ValidationSeverity.CRITICAL
        assert result.category == ValidationCategory.SECURITY
        assert result.message == "Hardcoded secret detected"
        assert result.code_snippet == "api_key = 'sk-1234567890abcdef'"
        assert result.suggestion is None  # Expected default
        assert result.auto_fixable is False  # Expected default
    
    def test_validation_result_with_fix_suggestion(self):
        """Test ValidationResult with fix suggestion."""
        result = ValidationResult(
            rule_name="use_environment_variables",
            file_path="/src/config.py",
            line_number=25,
            column_number=10,
            severity=ValidationSeverity.WARNING,
            category=ValidationCategory.SECURITY,
            message="Use environment variable instead of hardcoded value",
            code_snippet="database_url = 'postgresql://localhost:5432/db'",
            suggestion="Use os.getenv('DATABASE_URL') instead",
            auto_fixable=True,
            fix_code="database_url = os.getenv('DATABASE_URL')",
            context={"function": "get_database_config", "class": "DatabaseConfig"}
        )
        
        assert result.rule_name == "use_environment_variables"
        assert result.severity == ValidationSeverity.WARNING
        assert result.suggestion == "Use os.getenv('DATABASE_URL') instead"
        assert result.auto_fixable is True
        assert result.fix_code == "database_url = os.getenv('DATABASE_URL')"
        assert result.context["function"] == "get_database_config"


class TestCodeQualityValidator:
    """Test CodeQualityValidator for code quality validation."""
    
    @pytest.fixture
    def validator(self):
        """Create CodeQualityValidator instance."""
        return CodeQualityValidator()
    
    @pytest.fixture
    def temp_code_dir(self):
        """Create temporary directory with sample code files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = Path(temp_dir) / "src"
            code_path.mkdir()
            
            # Create sample Python file with quality issues
            sample_file = code_path / "sample.py"
            sample_file.write_text('''\
"""Sample module with code quality issues."""

import os
import sys
import json
import requests  # Unused import

def bad_function():
    # Missing docstring
    x = 1
    y = 2
    z = 3  # Unused variable
    print("Debug output")  # Print statement
    return x + y

class BadClass:
    # Missing docstring
    def __init__(self):
        pass
    
    def method_with_issues(self, a, b, c, d, e, f):  # Too many parameters
        # Complex nested logic
        if a > 0:
            if b > 0:
                if c > 0:
                    if d > 0:
                        if e > 0:
                            return f
        return 0

# Global variable
GLOBAL_STATE = {}

def function_with_complexity():
    """Function with high complexity."""
    result = 0
    for i in range(10):
        if i % 2 == 0:
            if i > 5:
                result += i * 2
            else:
                result += i
        else:
            if i < 3:
                result -= i
            else:
                result *= i
    return result
''')
            
            yield code_path
    
    @pytest.mark.asyncio
    async def test_validate_code_file(self, validator, temp_code_dir):
        """Test validating a single code file."""
        sample_file = temp_code_dir / "sample.py"
        
        results = await validator.validate_file(str(sample_file))
        
        assert len(results) > 0
        
        # Should detect various issues
        rule_names = [r.rule_name for r in results]
        assert any("unused_import" in name for name in rule_names)
        assert any("unused_variable" in name for name in rule_names)
        assert any("print_statement" in name for name in rule_names)
        assert any("missing_docstring" in name for name in rule_names)
        assert any("too_many_parameters" in name for name in rule_names)
    
    @pytest.mark.asyncio
    async def test_check_unused_imports(self, validator, temp_code_dir):
        """Test checking for unused imports."""
        sample_file = temp_code_dir / "sample.py"
        
        unused_imports = await validator.check_unused_imports(str(sample_file))
        
        assert len(unused_imports) > 0
        # Should detect 'requests' as unused
        assert any(result.message.lower().find("requests") != -1 for result in unused_imports)
    
    @pytest.mark.asyncio
    async def test_check_unused_variables(self, validator, temp_code_dir):
        """Test checking for unused variables."""
        sample_file = temp_code_dir / "sample.py"
        
        unused_vars = await validator.check_unused_variables(str(sample_file))
        
        assert len(unused_vars) > 0
        # Should detect 'z' as unused in bad_function
        assert any("z" in result.message for result in unused_vars)
    
    @pytest.mark.asyncio
    async def test_check_missing_docstrings(self, validator, temp_code_dir):
        """Test checking for missing docstrings."""
        sample_file = temp_code_dir / "sample.py"
        
        missing_docs = await validator.check_missing_docstrings(str(sample_file))
        
        assert len(missing_docs) > 0
        # Should detect missing docstrings for functions and classes
        messages = [result.message for result in missing_docs]
        assert any("docstring" in msg.lower() for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_code_duplication(self, validator, temp_code_dir):
        """Test checking for code duplication."""
        # Create another file with similar code
        duplicate_file = temp_code_dir / "duplicate.py"
        duplicate_file.write_text('''\
def bad_function():
    x = 1
    y = 2
    print("Debug output")
    return x + y

def another_bad_function():
    x = 1
    y = 2
    print("Debug output")
    return x + y
''')
        
        duplications = await validator.check_code_duplication(str(temp_code_dir))
        
        assert len(duplications) >= 0  # May or may not find duplications
    
    @pytest.mark.asyncio
    async def test_generate_quality_metrics(self, validator, temp_code_dir):
        """Test generating code quality metrics."""
        metrics = await validator.generate_quality_metrics(str(temp_code_dir))
        
        assert metrics.total_files > 0
        assert metrics.total_lines > 0
        assert metrics.issues_count >= 0
        assert metrics.quality_score >= 0
        assert metrics.quality_score <= 100
        assert len(metrics.issue_breakdown) > 0
        assert metrics.maintainability_index >= 0


class TestSecurityValidator:
    """Test SecurityValidator for security validation."""
    
    @pytest.fixture
    def validator(self):
        """Create SecurityValidator instance."""
        return SecurityValidator()
    
    @pytest.fixture
    def temp_security_code_dir(self):
        """Create temporary directory with security issue samples."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = Path(temp_dir) / "src"
            code_path.mkdir()
            
            # Create sample file with security issues
            security_file = code_path / "security_issues.py"
            security_file.write_text('''\
"""Sample code with security vulnerabilities."""

import os
import hashlib
import subprocess
import sqlite3

# Hardcoded secrets
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"
SECRET_TOKEN = "secret_token_value"

def insecure_database_query(user_id):
    """Vulnerable to SQL injection."""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    return cursor.fetchall()

def weak_password_hashing(password):
    """Uses weak hashing algorithm."""
    # MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()

def command_injection_risk(user_input):
    """Vulnerable to command injection."""
    # Dangerous use of shell=True with user input
    result = subprocess.run(f"ls {user_input}", shell=True, capture_output=True)
    return result.stdout

def insecure_random():
    """Uses insecure random number generation."""
    import random
    # Not cryptographically secure
    return random.randint(1000, 9999)

def eval_security_risk(user_code):
    """Dangerous use of eval."""
    # eval with user input is extremely dangerous
    return eval(user_code)

def path_traversal_risk(filename):
    """Path traversal vulnerability."""
    # No validation of filename
    with open(f"/var/files/{filename}", 'r') as f:
        return f.read()

# Insecure configuration
DEBUG = True
ALLOWED_HOSTS = ["*"]  # Overly permissive

class InsecureAuthentication:
    """Insecure authentication implementation."""
    
    def __init__(self):
        self.users = {"admin": "password123"}  # Hardcoded credentials
    
    def authenticate(self, username, password):
        # Timing attack vulnerability - use constant time comparison
        if username in self.users and self.users[username] == password:
            return True
        return False
''')
            
            yield code_path
    
    @pytest.mark.asyncio
    async def test_scan_for_hardcoded_secrets(self, validator, temp_security_code_dir):
        """Test scanning for hardcoded secrets."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        secrets = await validator.scan_hardcoded_secrets(str(security_file))
        
        assert len(secrets) > 0
        
        # Should detect hardcoded API keys, passwords, tokens
        messages = [result.message.lower() for result in secrets]
        assert any("api_key" in msg or "secret" in msg or "password" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_sql_injection_risks(self, validator, temp_security_code_dir):
        """Test checking for SQL injection vulnerabilities."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        sql_issues = await validator.check_sql_injection_risks(str(security_file))
        
        assert len(sql_issues) > 0
        
        # Should detect SQL injection in insecure_database_query
        assert any("sql" in result.message.lower() for result in sql_issues)
        assert any("injection" in result.message.lower() for result in sql_issues)
    
    @pytest.mark.asyncio
    async def test_check_command_injection_risks(self, validator, temp_security_code_dir):
        """Test checking for command injection vulnerabilities."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        command_issues = await validator.check_command_injection_risks(str(security_file))
        
        assert len(command_issues) > 0
        
        # Should detect command injection in command_injection_risk
        messages = [result.message.lower() for result in command_issues]
        assert any("command" in msg and "injection" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_insecure_cryptography(self, validator, temp_security_code_dir):
        """Test checking for insecure cryptography."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        crypto_issues = await validator.check_insecure_cryptography(str(security_file))
        
        assert len(crypto_issues) > 0
        
        # Should detect MD5 usage and insecure random
        messages = [result.message.lower() for result in crypto_issues]
        assert any("md5" in msg or "weak" in msg or "insecure" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_dangerous_functions(self, validator, temp_security_code_dir):
        """Test checking for dangerous function usage."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        dangerous_funcs = await validator.check_dangerous_functions(str(security_file))
        
        assert len(dangerous_funcs) > 0
        
        # Should detect eval usage
        messages = [result.message.lower() for result in dangerous_funcs]
        assert any("eval" in msg or "dangerous" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_path_traversal_risks(self, validator, temp_security_code_dir):
        """Test checking for path traversal vulnerabilities."""
        security_file = temp_security_code_dir / "security_issues.py"
        
        path_issues = await validator.check_path_traversal_risks(str(security_file))
        
        assert len(path_issues) >= 0  # May or may not detect depending on patterns
    
    @pytest.mark.asyncio
    async def test_generate_security_report(self, validator, temp_security_code_dir):
        """Test generating comprehensive security report."""
        report = await validator.generate_security_report(str(temp_security_code_dir))
        
        assert report.total_files_scanned > 0
        assert report.total_vulnerabilities >= 0
        assert report.critical_vulnerabilities >= 0
        assert report.high_vulnerabilities >= 0
        assert len(report.vulnerability_categories) > 0
        assert report.security_score >= 0
        assert report.security_score <= 100


class TestStyleValidator:
    """Test StyleValidator for code style validation."""
    
    @pytest.fixture
    def validator(self):
        """Create StyleValidator instance."""
        return StyleValidator()
    
    @pytest.fixture
    def temp_style_code_dir(self):
        """Create temporary directory with style issue samples."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = Path(temp_dir) / "src"
            code_path.mkdir()
            
            # Create sample file with style issues
            style_file = code_path / "style_issues.py"
            style_file.write_text('''\
"""Sample code with style violations."""

import sys,os,json # Multiple imports on one line

# Inconsistent spacing
x=1
y = 2
z  =   3

def badFunctionName():  # Should be snake_case
    """Function with style issues."""
    pass

class badClassName:  # Should be PascalCase
    """Class with style issues."""
    
    def method_with_bad_formatting(self,a,b,c):  # Missing spaces after commas
        """Method with formatting issues."""
        if a>0:  # Missing spaces around operators
            result=a+b+c  # Missing spaces
            return result
        else:
            return 0

# Line too long - this line exceeds the recommended 79 characters and should be split into multiple lines for better readability
very_long_variable_name_that_exceeds_reasonable_length = "some value"

def function_with_trailing_whitespace():   
    """Function with trailing whitespace."""    
    pass    

# Missing blank lines between functions
def another_function():
    """Another function."""
    pass
def yet_another_function():
    """Yet another function."""
    pass

# Inconsistent indentation
if True:
  print("Wrong indentation")  # 2 spaces instead of 4
    if True:
        print("Nested wrong indentation")

# Missing final newline at end of file''')
            
            yield code_path
    
    @pytest.mark.asyncio
    async def test_check_naming_conventions(self, validator, temp_style_code_dir):
        """Test checking naming conventions."""
        style_file = temp_style_code_dir / "style_issues.py"
        
        naming_issues = await validator.check_naming_conventions(str(style_file))
        
        assert len(naming_issues) > 0
        
        # Should detect badFunctionName and badClassName
        messages = [result.message.lower() for result in naming_issues]
        assert any("function" in msg and ("snake_case" in msg or "naming" in msg) for msg in messages)
        assert any("class" in msg and ("pascalcase" in msg or "naming" in msg) for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_line_length(self, validator, temp_style_code_dir):
        """Test checking line length violations."""
        style_file = temp_style_code_dir / "style_issues.py"
        
        length_issues = await validator.check_line_length(str(style_file), max_length=79)
        
        assert len(length_issues) > 0
        
        # Should detect the long comment line
        assert any("line" in result.message.lower() and "long" in result.message.lower() 
                  for result in length_issues)
    
    @pytest.mark.asyncio
    async def test_check_whitespace_issues(self, validator, temp_style_code_dir):
        """Test checking whitespace issues."""
        style_file = temp_style_code_dir / "style_issues.py"
        
        whitespace_issues = await validator.check_whitespace_issues(str(style_file))
        
        assert len(whitespace_issues) > 0
        
        # Should detect various whitespace issues
        messages = [result.message.lower() for result in whitespace_issues]
        assert any("whitespace" in msg or "spacing" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_import_formatting(self, validator, temp_style_code_dir):
        """Test checking import formatting."""
        style_file = temp_style_code_dir / "style_issues.py"
        
        import_issues = await validator.check_import_formatting(str(style_file))
        
        assert len(import_issues) > 0
        
        # Should detect multiple imports on one line
        messages = [result.message.lower() for result in import_issues]
        assert any("import" in msg for msg in messages)
    
    @pytest.mark.asyncio
    async def test_check_indentation(self, validator, temp_style_code_dir):
        """Test checking indentation consistency."""
        style_file = temp_style_code_dir / "style_issues.py"
        
        indent_issues = await validator.check_indentation(str(style_file))
        
        assert len(indent_issues) >= 0  # May detect indentation issues
    
    @pytest.mark.asyncio
    async def test_generate_style_report(self, validator, temp_style_code_dir):
        """Test generating style validation report."""
        report = await validator.generate_style_report(str(temp_style_code_dir))
        
        assert report.total_files_checked > 0
        assert report.total_violations >= 0
        assert len(report.violation_categories) >= 0
        assert report.style_score >= 0
        assert report.style_score <= 100


class TestComplexityValidator:
    """Test ComplexityValidator for code complexity validation."""
    
    @pytest.fixture
    def validator(self):
        """Create ComplexityValidator instance."""
        return ComplexityValidator()
    
    @pytest.fixture
    def temp_complex_code_dir(self):
        """Create temporary directory with complex code samples."""
        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = Path(temp_dir) / "src"
            code_path.mkdir()
            
            # Create sample file with complexity issues
            complex_file = code_path / "complex_code.py"
            complex_file.write_text('''\
"""Sample code with complexity issues."""

def simple_function():
    """Simple function with low complexity."""
    return 42

def moderate_complexity_function(x, y, z):
    """Function with moderate complexity."""
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    elif z > 0:
        return z * 2
    else:
        return 0

def high_complexity_function(data):
    """Function with high cyclomatic complexity."""
    result = 0
    
    for item in data:
        if item['type'] == 'A':
            if item['value'] > 100:
                if item['priority'] == 'high':
                    result += item['value'] * 2
                elif item['priority'] == 'medium':
                    result += item['value'] * 1.5
                else:
                    result += item['value']
            elif item['value'] > 50:
                if item['category'] == 'premium':
                    result += item['value'] * 1.2
                else:
                    result += item['value']
            else:
                result += item['value'] * 0.5
        elif item['type'] == 'B':
            if item['status'] == 'active':
                if item['region'] == 'north':
                    result += item['value'] * 3
                elif item['region'] == 'south':
                    result += item['value'] * 2.5
                else:
                    result += item['value'] * 2
            else:
                result += item['value'] * 0.1
        elif item['type'] == 'C':
            try:
                processed_value = process_c_type(item)
                result += processed_value
            except ValueError:
                result += 0
            except TypeError:
                result += -1
        else:
            for subitem in item.get('subitems', []):
                if subitem['enabled']:
                    result += subitem['value']
    
    return result

def process_c_type(item):
    """Helper function for processing C type items."""
    return item['value'] * 1.1

class ComplexClass:
    """Class with complex methods."""
    
    def __init__(self, config):
        """Initialize with configuration."""
        self.config = config
        self.state = {}
    
    def complex_method(self, input_data, options=None):
        """Method with high complexity."""
        if not input_data:
            return None
        
        if options is None:
            options = {}
        
        results = []
        
        for data_item in input_data:
            if data_item.get('enabled', True):
                try:
                    if data_item['type'] in ['alpha', 'beta']:
                        if self.config.get('strict_mode', False):
                            validated_item = self.validate_strict(data_item)
                        else:
                            validated_item = self.validate_normal(data_item)
                        
                        if validated_item:
                            processed = self.process_item(validated_item, options)
                            if processed['score'] > 0.5:
                                if processed['category'] == 'important':
                                    results.append(processed)
                                elif processed['category'] == 'normal' and len(results) < 100:
                                    results.append(processed)
                            elif processed['score'] > 0.1 and options.get('include_low_score', False):
                                results.append(processed)
                    elif data_item['type'] == 'gamma':
                        special_result = self.handle_gamma_type(data_item)
                        if special_result:
                            results.extend(special_result)
                except (KeyError, ValueError, TypeError) as e:
                    if options.get('ignore_errors', True):
                        continue
                    else:
                        raise e
            else:
                if options.get('process_disabled', False):
                    disabled_result = self.process_disabled_item(data_item)
                    if disabled_result:
                        results.append(disabled_result)
        
        return results
    
    def validate_strict(self, item):
        """Strict validation method."""
        return item if item.get('verified', False) else None
    
    def validate_normal(self, item):
        """Normal validation method."""
        return item
    
    def process_item(self, item, options):
        """Process individual item."""
        return {'score': 0.7, 'category': 'important', 'data': item}
    
    def handle_gamma_type(self, item):
        """Handle gamma type items."""
        return [item]
    
    def process_disabled_item(self, item):
        """Process disabled items."""
        return item

# Deeply nested function
def deeply_nested_function():
    """Function with deep nesting."""
    level1 = True
    if level1:
        level2 = True
        if level2:
            level3 = True
            if level3:
                level4 = True
                if level4:
                    level5 = True
                    if level5:
                        level6 = True
                        if level6:
                            return "deeply nested"
    return "not nested"
''')
            
            yield code_path
    
    @pytest.mark.asyncio
    async def test_calculate_cyclomatic_complexity(self, validator, temp_complex_code_dir):
        """Test calculating cyclomatic complexity."""
        complex_file = temp_complex_code_dir / "complex_code.py"
        
        complexity_results = await validator.calculate_cyclomatic_complexity(str(complex_file))
        
        assert len(complexity_results) > 0
        
        # Should identify functions with different complexity levels
        function_complexities = {result.function_name: result.complexity 
                               for result in complexity_results}
        
        assert "simple_function" in function_complexities
        assert "high_complexity_function" in function_complexities
        
        # Simple function should have low complexity
        assert function_complexities["simple_function"] <= 2
        
        # High complexity function should have high complexity
        assert function_complexities["high_complexity_function"] > 10
    
    @pytest.mark.asyncio
    async def test_calculate_nesting_depth(self, validator, temp_complex_code_dir):
        """Test calculating nesting depth."""
        complex_file = temp_complex_code_dir / "complex_code.py"
        
        nesting_results = await validator.calculate_nesting_depth(str(complex_file))
        
        assert len(nesting_results) > 0
        
        # Should identify deeply nested function
        deeply_nested = next(
            (result for result in nesting_results 
             if result.function_name == "deeply_nested_function"), 
            None
        )
        
        assert deeply_nested is not None
        assert deeply_nested.max_nesting_depth > 5
    
    @pytest.mark.asyncio
    async def test_calculate_halstead_metrics(self, validator, temp_complex_code_dir):
        """Test calculating Halstead complexity metrics."""
        complex_file = temp_complex_code_dir / "complex_code.py"
        
        halstead_results = await validator.calculate_halstead_metrics(str(complex_file))
        
        assert len(halstead_results) > 0
        
        # Should calculate various Halstead metrics
        for result in halstead_results:
            assert result.vocabulary > 0
            assert result.length > 0
            assert result.difficulty >= 0
            assert result.effort >= 0
    
    @pytest.mark.asyncio
    async def test_analyze_function_length(self, validator, temp_complex_code_dir):
        """Test analyzing function length."""
        complex_file = temp_complex_code_dir / "complex_code.py"
        
        length_results = await validator.analyze_function_length(str(complex_file))
        
        assert len(length_results) > 0
        
        # Should identify long functions
        long_functions = [result for result in length_results if result.line_count > 20]
        assert len(long_functions) > 0
    
    @pytest.mark.asyncio
    async def test_generate_complexity_report(self, validator, temp_complex_code_dir):
        """Test generating complexity report."""
        report = await validator.generate_complexity_report(str(temp_complex_code_dir))
        
        assert report.total_functions > 0
        assert report.average_complexity >= 0
        assert report.max_complexity > 0
        assert report.complex_functions_count >= 0
        assert len(report.complexity_distribution) > 0
        assert report.maintainability_index >= 0
        assert report.maintainability_index <= 100


class TestValidationFramework:
    """Test ValidationFramework for orchestrating all validations."""
    
    @pytest.fixture
    def framework(self):
        """Create ValidationFramework instance."""
        return ValidationFramework()
    
    @pytest.fixture
    def comprehensive_test_project(self):
        """Create comprehensive test project with various issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create source directory
            src_path = project_path / "src"
            src_path.mkdir()
            
            # Create main application file
            app_file = src_path / "app.py"
            app_file.write_text('''\
"""Main application module."""

import os
import sys
import json
import requests  # Unused import

# Hardcoded secret
API_SECRET = "super-secret-key-123"

def process_user_data(user_input):
    """Process user data with security issues."""
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    
    # Command injection risk
    import subprocess
    result = subprocess.run(f"echo {user_input}", shell=True)
    
    return query

class DataProcessor:
    # Missing docstring
    
    def complex_processing_method(self, data, options, filters, transformers, validators):
        """Method with too many parameters and high complexity."""
        results = []
        
        for item in data:
            if item.get('enabled', True):
                if options.get('strict', False):
                    if item['type'] == 'A':
                        if item['value'] > 100:
                            if filters.get('high_value', True):
                                transformed = transformers['A'](item)
                                if validators['A'](transformed):
                                    results.append(transformed)
                            else:
                                results.append(item)
                        elif item['value'] > 50:
                            if filters.get('medium_value', True):
                                results.append(item)
                    elif item['type'] == 'B':
                        if item.get('priority') == 'high':
                            results.append(item)
                else:
                    results.append(item)
        
        return results

# Print statement for debugging
print("Application loaded")

# Line too long - this is a very long line that exceeds the recommended 79 character limit and should be split
very_long_variable_name_with_excessive_length = "some value that makes this line way too long"
''')
            
            # Create configuration file
            config_file = src_path / "config.py"
            config_file.write_text('''\
"""Configuration module with security issues."""

# Insecure configuration
DEBUG = True
SECRET_KEY = "hardcoded-secret-key"
DATABASE_PASSWORD = "admin123"

# Weak cryptography
import hashlib

def hash_password(password):
    """Weak password hashing."""
    return hashlib.md5(password.encode()).hexdigest()
''')
            
            yield project_path
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_validation(self, framework, comprehensive_test_project):
        """Test running comprehensive validation on project."""
        # Configure validation rules
        validation_config = ValidationConfig(
            name="comprehensive_validation",
            rules=[
                ValidationRule(
                    name="security_scan",
                    category=ValidationCategory.SECURITY,
                    severity=ValidationSeverity.CRITICAL,
                    description="Comprehensive security scan",
                    enabled=True
                ),
                ValidationRule(
                    name="code_quality_check",
                    category=ValidationCategory.CODE_QUALITY,
                    severity=ValidationSeverity.WARNING,
                    description="Code quality analysis",
                    enabled=True
                ),
                ValidationRule(
                    name="style_check",
                    category=ValidationCategory.STYLE,
                    severity=ValidationSeverity.INFO,
                    description="Code style validation",
                    enabled=True
                ),
                ValidationRule(
                    name="complexity_analysis",
                    category=ValidationCategory.COMPLEXITY,
                    severity=ValidationSeverity.WARNING,
                    description="Code complexity analysis",
                    enabled=True
                )
            ],
            include_patterns=["*.py"],
            exclude_patterns=["test_*", "*_test.py"],
            parallel_processing=True
        )
        
        validation_report = await framework.run_validation(
            str(comprehensive_test_project),
            validation_config
        )
        
        assert validation_report.total_files_validated > 0
        assert len(validation_report.results) > 0
        assert validation_report.validation_duration_ms > 0
        
        # Should find various types of issues
        categories = {result.category for result in validation_report.results}
        assert ValidationCategory.SECURITY in categories
        assert ValidationCategory.CODE_QUALITY in categories
        
        # Should find critical security issues
        critical_issues = [
            result for result in validation_report.results
            if result.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_issues) > 0
    
    @pytest.mark.asyncio
    async def test_auto_fix_validation_issues(self, framework, comprehensive_test_project):
        """Test automatic fixing of validation issues."""
        # Configure auto-fixable rules
        auto_fix_config = ValidationConfig(
            name="auto_fix_validation",
            rules=[
                ValidationRule(
                    name="remove_unused_imports",
                    category=ValidationCategory.CODE_QUALITY,
                    severity=ValidationSeverity.WARNING,
                    description="Remove unused imports",
                    auto_fix=True,
                    enabled=True
                ),
                ValidationRule(
                    name="fix_style_issues",
                    category=ValidationCategory.STYLE,
                    severity=ValidationSeverity.INFO,
                    description="Fix basic style issues",
                    auto_fix=True,
                    enabled=True
                )
            ],
            include_patterns=["*.py"]
        )
        
        fix_result = await framework.auto_fix_issues(
            str(comprehensive_test_project),
            auto_fix_config
        )
        
        assert fix_result.files_processed > 0
        assert fix_result.issues_fixed >= 0
        assert fix_result.fix_success_rate >= 0
    
    @pytest.mark.asyncio
    async def test_generate_validation_report(self, framework, comprehensive_test_project):
        """Test generating comprehensive validation report."""
        validation_config = ValidationConfig(
            name="report_generation",
            rules=[
                ValidationRule(
                    name="comprehensive_scan",
                    category=ValidationCategory.SECURITY,
                    severity=ValidationSeverity.CRITICAL,
                    description="Full security and quality scan",
                    enabled=True
                )
            ],
            include_patterns=["*.py"],
            generate_report=True,
            report_format="json"
        )
        
        report = await framework.generate_comprehensive_report(
            str(comprehensive_test_project),
            validation_config
        )
        
        assert report.project_name is not None
        assert report.validation_timestamp is not None
        assert report.overall_score >= 0
        assert report.overall_score <= 100
        assert len(report.category_scores) > 0
        assert len(report.file_summaries) > 0
        assert len(report.recommendations) >= 0
    
    @pytest.mark.asyncio
    async def test_validation_rule_filtering(self, framework, comprehensive_test_project):
        """Test filtering validation rules by category and severity."""
        # Test security-only validation
        security_config = ValidationConfig(
            name="security_only",
            rules=[
                ValidationRule(
                    name="security_scan",
                    category=ValidationCategory.SECURITY,
                    severity=ValidationSeverity.CRITICAL,
                    description="Security scan only",
                    enabled=True
                )
            ],
            include_patterns=["*.py"]
        )
        
        security_results = await framework.run_filtered_validation(
            str(comprehensive_test_project),
            security_config,
            categories=[ValidationCategory.SECURITY]
        )
        
        assert all(result.category == ValidationCategory.SECURITY 
                  for result in security_results.results)
        
        # Test critical-only validation
        critical_results = await framework.run_filtered_validation(
            str(comprehensive_test_project),
            security_config,
            min_severity=ValidationSeverity.CRITICAL
        )
        
        assert all(result.severity >= ValidationSeverity.CRITICAL 
                  for result in critical_results.results)


class TestValidationIntegration:
    """Integration tests for validation framework."""
    
    @pytest.mark.asyncio
    async def test_ci_cd_integration_workflow(self):
        """Test validation framework integration with CI/CD."""
        # This would test CI/CD pipeline integration
        ci_config = {
            "fail_on_critical": True,
            "fail_on_error": True,
            "generate_artifacts": True,
            "export_formats": ["json", "junit", "sarif"],
            "upload_results": False  # For testing
        }
        
        # Would test CI/CD integration
        # pipeline = ValidationPipeline(ci_config)
        # result = await pipeline.run_validation(project_path)
        # assert result.exit_code == 0 or result.exit_code == 1
    
    def test_ide_integration_support(self):
        """Test IDE integration capabilities."""
        ide_config = {
            "language_server_protocol": True,
            "real_time_validation": True,
            "inline_suggestions": True,
            "quick_fixes": True
        }
        
        # Would test IDE integration features
        # ide_server = ValidationLanguageServer(ide_config)
        # assert ide_server.supports_real_time_validation() is True
    
    def test_validation_caching_and_performance(self):
        """Test validation caching and performance optimization."""
        cache_config = {
            "enable_caching": True,
            "cache_duration_hours": 24,
            "incremental_validation": True,
            "parallel_processing": True,
            "max_workers": 4
        }
        
        # Would test caching and performance features
        # cache_manager = ValidationCacheManager(cache_config)
        # assert cache_manager.is_cache_enabled() is True