"""Tests for dependency migration and compatibility checking.

This module tests dependency analysis, conversion, and compatibility
validation during framework migration. Following TDD methodology.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import interfaces to be implemented (TDD)
from beginnings.migration.dependencies import (
    DependencyMigrator,
    DependencyMapping,
    CompatibilityResult,
    PackageConverter
)
from beginnings.migration.analyzers import (
    RequirementsAnalyzer,
    PackageAnalyzer,
    VersionAnalyzer
)


class TestDependencyMigrator:
    """Test dependency migration following SRP."""
    
    @pytest.fixture
    def dependency_migrator(self):
        """Create dependency migrator for testing."""
        return DependencyMigrator()
    
    @pytest.fixture
    def flask_requirements(self):
        """Sample Flask requirements.txt content."""
        return """
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.5
Flask-Login==0.6.3
Flask-WTF==1.1.1
Werkzeug==2.3.7
Jinja2==3.1.2
SQLAlchemy==2.0.21
WTForms==3.0.1
requests==2.31.0
gunicorn==21.2.0
pytest==7.4.2
pytest-cov==4.1.0
"""
    
    @pytest.fixture
    def django_requirements(self):
        """Sample Django requirements.txt content."""
        return """
Django==4.2.5
django-rest-framework==3.14.0
django-cors-headers==4.2.0
django-environ==0.10.0
psycopg2-binary==2.9.7
celery==5.3.1
redis==4.6.0
gunicorn==21.2.0
pillow==10.0.0
requests==2.31.0
pytest-django==4.5.2
"""
    
    @pytest.fixture
    def fastapi_requirements(self):
        """Sample FastAPI requirements.txt content."""
        return """
fastapi==0.103.1
uvicorn[standard]==0.23.2
pydantic==2.4.0
sqlalchemy==2.0.21
alembic==1.12.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
requests==2.31.0
pytest==7.4.2
httpx==0.24.1
"""
    
    def test_migrator_initialization(self, dependency_migrator):
        """Test dependency migrator initializes correctly."""
        assert dependency_migrator is not None
        assert hasattr(dependency_migrator, 'analyze_dependencies')
        assert hasattr(dependency_migrator, 'map_dependencies')
        assert hasattr(dependency_migrator, 'check_compatibility')
        assert hasattr(dependency_migrator, 'generate_requirements')
    
    def test_analyze_flask_dependencies(self, dependency_migrator, flask_requirements):
        """Test Flask dependency analysis."""
        result = dependency_migrator.analyze_dependencies(flask_requirements, "flask")
        
        assert isinstance(result, dict)
        assert "framework_packages" in result
        assert "extension_packages" in result
        assert "utility_packages" in result
        
        # Should identify Flask framework packages
        framework_packages = result["framework_packages"]
        assert "Flask" in framework_packages
        assert "Flask-SQLAlchemy" in framework_packages
        assert "Flask-Migrate" in framework_packages
        
        # Should identify utility packages
        utility_packages = result["utility_packages"]
        assert "requests" in utility_packages
        assert "gunicorn" in utility_packages
    
    def test_analyze_django_dependencies(self, dependency_migrator, django_requirements):
        """Test Django dependency analysis."""
        result = dependency_migrator.analyze_dependencies(django_requirements, "django")
        
        assert isinstance(result, dict)
        framework_packages = result["framework_packages"]
        assert "Django" in framework_packages
        assert "django-rest-framework" in framework_packages
        
        # Should identify database packages
        assert "psycopg2-binary" in result["utility_packages"]
    
    def test_analyze_fastapi_dependencies(self, dependency_migrator, fastapi_requirements):
        """Test FastAPI dependency analysis."""
        result = dependency_migrator.analyze_dependencies(fastapi_requirements, "fastapi")
        
        assert isinstance(result, dict)
        framework_packages = result["framework_packages"]
        assert "fastapi" in framework_packages
        assert "uvicorn" in framework_packages
        assert "pydantic" in framework_packages
    
    def test_map_flask_dependencies(self, dependency_migrator, flask_requirements):
        """Test Flask dependency mapping to Beginnings."""
        analysis = dependency_migrator.analyze_dependencies(flask_requirements, "flask")
        mapping = dependency_migrator.map_dependencies(analysis, "beginnings")
        
        assert isinstance(mapping, DependencyMapping)
        assert len(mapping.direct_mappings) > 0
        assert len(mapping.extension_mappings) > 0
        
        # Should map Flask to Beginnings
        direct_mappings = mapping.direct_mappings
        assert "Flask" in direct_mappings
        assert "beginnings" in direct_mappings["Flask"].target_package
        
        # Should map Flask-SQLAlchemy to Beginnings database extension
        extension_mappings = mapping.extension_mappings
        sqlalchemy_mapping = next(
            (m for m in extension_mappings if "SQLAlchemy" in m.source_package), 
            None
        )
        assert sqlalchemy_mapping is not None
        assert "database" in sqlalchemy_mapping.target_extension.lower()
    
    def test_check_compatibility(self, dependency_migrator):
        """Test dependency compatibility checking."""
        test_dependencies = {
            "framework_packages": ["Flask==2.3.3"],
            "extension_packages": ["Flask-SQLAlchemy==3.0.5"],
            "utility_packages": ["requests==2.31.0"]
        }
        
        result = dependency_migrator.check_compatibility(test_dependencies)
        
        assert isinstance(result, CompatibilityResult)
        assert result.overall_compatibility is not None
        assert len(result.compatible_packages) >= 0
        assert len(result.incompatible_packages) >= 0
        assert len(result.migration_required) >= 0
        
        # Requests should be compatible
        compatible_names = [p.name for p in result.compatible_packages]
        assert "requests" in compatible_names
    
    def test_generate_beginnings_requirements(self, dependency_migrator, flask_requirements):
        """Test generating Beginnings requirements."""
        analysis = dependency_migrator.analyze_dependencies(flask_requirements, "flask")
        mapping = dependency_migrator.map_dependencies(analysis, "beginnings")
        
        requirements = dependency_migrator.generate_requirements(mapping)
        
        assert isinstance(requirements, str)
        assert "beginnings" in requirements
        assert "requests" in requirements  # Should preserve compatible packages
        
        # Should include extension packages
        assert "beginnings-database" in requirements or "beginnings[database]" in requirements


class TestRequirementsAnalyzer:
    """Test requirements.txt analysis following SRP."""
    
    @pytest.fixture
    def requirements_analyzer(self):
        """Create requirements analyzer for testing."""
        return RequirementsAnalyzer()
    
    @pytest.fixture
    def complex_requirements(self):
        """Complex requirements with various formats."""
        return """
# Web framework
Flask>=2.0.0,<3.0.0

# Database
Flask-SQLAlchemy~=3.0.0
psycopg2-binary==2.9.7  # PostgreSQL adapter

# Development dependencies
pytest>=7.0.0
pytest-cov
black==23.7.0
flake8>=6.0.0

# Optional dependencies
celery[redis]>=5.0.0
gunicorn; sys_platform != "win32"

# Git dependencies
-e git+https://github.com/example/package.git@v1.0.0#egg=example-package

# Local dependencies
-e ./local-package

# Index options
--index-url https://pypi.org/simple/
--extra-index-url https://test.pypi.org/simple/
"""
    
    def test_analyzer_initialization(self, requirements_analyzer):
        """Test requirements analyzer initializes correctly."""
        assert requirements_analyzer is not None
        assert hasattr(requirements_analyzer, 'parse_requirements')
        assert hasattr(requirements_analyzer, 'extract_packages')
        assert hasattr(requirements_analyzer, 'analyze_versions')
        assert hasattr(requirements_analyzer, 'detect_conflicts')
    
    def test_parse_simple_requirements(self, requirements_analyzer):
        """Test parsing simple requirements."""
        simple_req = "Flask==2.3.3\nrequests>=2.25.0\n"
        
        packages = requirements_analyzer.parse_requirements(simple_req)
        
        assert len(packages) == 2
        
        flask_pkg = next(p for p in packages if p.name == "Flask")
        assert flask_pkg.version == "2.3.3"
        assert flask_pkg.operator == "=="
        
        requests_pkg = next(p for p in packages if p.name == "requests")
        assert requests_pkg.version == "2.25.0"
        assert requests_pkg.operator == ">="
    
    def test_parse_complex_requirements(self, requirements_analyzer, complex_requirements):
        """Test parsing complex requirements with comments and options."""
        packages = requirements_analyzer.parse_requirements(complex_requirements)
        
        # Should extract main packages
        package_names = [p.name for p in packages]
        assert "Flask" in package_names
        assert "Flask-SQLAlchemy" in package_names
        assert "pytest" in package_names
        assert "celery" in package_names
        
        # Should handle version specifiers
        flask_pkg = next(p for p in packages if p.name == "Flask")
        assert flask_pkg.version_spec == ">=2.0.0,<3.0.0"
        
        # Should handle extras
        celery_pkg = next(p for p in packages if p.name == "celery")
        assert "redis" in celery_pkg.extras
        
        # Should handle environment markers
        gunicorn_pkg = next((p for p in packages if p.name == "gunicorn"), None)
        if gunicorn_pkg:
            assert gunicorn_pkg.environment_marker is not None
    
    def test_extract_package_categories(self, requirements_analyzer, complex_requirements):
        """Test extracting package categories."""
        packages = requirements_analyzer.parse_requirements(complex_requirements)
        categories = requirements_analyzer.extract_packages(packages)
        
        assert isinstance(categories, dict)
        assert "web_framework" in categories
        assert "database" in categories
        assert "testing" in categories
        assert "development" in categories
        
        # Should categorize correctly
        web_packages = categories["web_framework"]
        assert any("Flask" in p.name for p in web_packages)
        
        test_packages = categories["testing"]
        assert any("pytest" in p.name for p in test_packages)
    
    def test_analyze_version_constraints(self, requirements_analyzer):
        """Test version constraint analysis."""
        version_req = "Flask>=2.0.0,<3.0.0,!=2.1.0"
        packages = requirements_analyzer.parse_requirements(version_req)
        
        analysis = requirements_analyzer.analyze_versions(packages)
        
        assert isinstance(analysis, dict)
        flask_analysis = analysis["Flask"]
        assert flask_analysis["min_version"] == "2.0.0"
        assert flask_analysis["max_version"] == "3.0.0"
        assert "2.1.0" in flask_analysis["excluded_versions"]
    
    def test_detect_version_conflicts(self, requirements_analyzer):
        """Test detection of version conflicts."""
        conflicting_req = """
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
SQLAlchemy==1.4.0  # This conflicts with Flask-SQLAlchemy 3.0.5
"""
        
        packages = requirements_analyzer.parse_requirements(conflicting_req)
        conflicts = requirements_analyzer.detect_conflicts(packages)
        
        assert len(conflicts) > 0
        # Should detect SQLAlchemy version conflict
        sqlalchemy_conflict = next(
            (c for c in conflicts if "SQLAlchemy" in c.package_name), 
            None
        )
        assert sqlalchemy_conflict is not None


class TestPackageConverter:
    """Test package conversion utilities following SRP."""
    
    @pytest.fixture
    def package_converter(self):
        """Create package converter for testing."""
        return PackageConverter()
    
    @pytest.fixture
    def conversion_mappings(self):
        """Sample conversion mappings."""
        return {
            "flask_to_beginnings": {
                "Flask": "beginnings",
                "Flask-SQLAlchemy": "beginnings[database]",
                "Flask-Login": "beginnings[auth]",
                "Flask-WTF": "beginnings[forms]",
                "Flask-Migrate": "beginnings[migrations]"
            },
            "django_to_beginnings": {
                "Django": "beginnings",
                "django-rest-framework": "beginnings[api]",
                "django-cors-headers": "beginnings[cors]",
                "psycopg2-binary": "psycopg2-binary"  # Keep as-is
            },
            "fastapi_to_beginnings": {
                "fastapi": "beginnings",
                "uvicorn": "beginnings[server]",
                "pydantic": "beginnings[validation]",
                "sqlalchemy": "beginnings[database]",
                "alembic": "beginnings[migrations]"
            }
        }
    
    def test_converter_initialization(self, package_converter):
        """Test package converter initializes correctly."""
        assert package_converter is not None
        assert hasattr(package_converter, 'convert_package')
        assert hasattr(package_converter, 'convert_requirements')
        assert hasattr(package_converter, 'load_mappings')
        assert hasattr(package_converter, 'validate_conversion')
    
    def test_load_conversion_mappings(self, package_converter, conversion_mappings):
        """Test loading conversion mappings."""
        package_converter.load_mappings(conversion_mappings)
        
        assert hasattr(package_converter, 'mappings')
        assert "flask_to_beginnings" in package_converter.mappings
        assert "django_to_beginnings" in package_converter.mappings
        assert "fastapi_to_beginnings" in package_converter.mappings
    
    def test_convert_flask_package(self, package_converter, conversion_mappings):
        """Test converting individual Flask package."""
        package_converter.load_mappings(conversion_mappings)
        
        # Test Flask conversion
        result = package_converter.convert_package("Flask==2.3.3", "flask_to_beginnings")
        assert result.target_package == "beginnings"
        assert result.target_version is not None
        
        # Test Flask extension conversion
        result = package_converter.convert_package("Flask-SQLAlchemy==3.0.5", "flask_to_beginnings")
        assert "beginnings" in result.target_package
        assert "database" in result.target_package
    
    def test_convert_requirements_file(self, package_converter, conversion_mappings):
        """Test converting entire requirements file."""
        package_converter.load_mappings(conversion_mappings)
        
        flask_requirements = """
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
requests==2.31.0
gunicorn==21.2.0
"""
        
        converted = package_converter.convert_requirements(flask_requirements, "flask_to_beginnings")
        
        assert "beginnings" in converted
        assert "requests==2.31.0" in converted  # Should preserve unmapped packages
        assert "gunicorn==21.2.0" in converted
        
        # Should convert extensions to extras or separate packages
        assert "beginnings[database]" in converted or "beginnings-database" in converted
        assert "beginnings[auth]" in converted or "beginnings-auth" in converted
    
    def test_validate_conversion(self, package_converter, conversion_mappings):
        """Test conversion validation."""
        package_converter.load_mappings(conversion_mappings)
        
        original = "Flask==2.3.3\nFlask-SQLAlchemy==3.0.5\n"
        converted = package_converter.convert_requirements(original, "flask_to_beginnings")
        
        validation = package_converter.validate_conversion(original, converted)
        
        assert validation.is_valid is not None
        assert len(validation.missing_functionality) >= 0
        assert len(validation.additional_functionality) >= 0
        assert len(validation.warnings) >= 0
        
        if validation.is_valid:
            # Should maintain core functionality
            assert validation.functionality_coverage >= 0.8  # 80% coverage minimum
    
    def test_handle_version_compatibility(self, package_converter, conversion_mappings):
        """Test version compatibility handling."""
        package_converter.load_mappings(conversion_mappings)
        
        # Test with version constraints
        result = package_converter.convert_package("Flask>=2.0.0,<3.0.0", "flask_to_beginnings")
        
        assert result.target_package == "beginnings"
        assert result.version_constraints is not None
        # Should map version constraints appropriately
        assert ">= "in str(result.version_constraints) or result.target_version is not None
    
    def test_handle_unknown_packages(self, package_converter, conversion_mappings):
        """Test handling of unknown/unmapped packages."""
        package_converter.load_mappings(conversion_mappings)
        
        # Test with unmapped package
        result = package_converter.convert_package("some-unknown-package==1.0.0", "flask_to_beginnings")
        
        # Should preserve unknown packages or mark for manual review
        assert result.target_package == "some-unknown-package" or result.requires_manual_review is True
        assert result.conversion_status in ["preserved", "manual_review_required"]