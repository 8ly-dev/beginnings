"""Tests for extension scaffolding system."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from click.testing import CliRunner

from src.beginnings.cli.main import cli
from src.beginnings.cli.commands.extension import (
    ExtensionScaffolder, ExtensionValidator, ExtensionLister
)


class TestExtensionScaffolding:
    """Test extension scaffolding functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extension_new_command_exists(self):
        """Test extension new command is available."""
        result = self.runner.invoke(cli, ["extension", "new", "--help"])
        assert result.exit_code == 0
        assert "Create a new extension" in result.output
    
    def test_extension_validate_command_exists(self):
        """Test extension validate command is available."""
        result = self.runner.invoke(cli, ["extension", "validate", "--help"])
        assert result.exit_code == 0
        assert "Validate extension structure" in result.output
    
    def test_extension_list_command_exists(self):
        """Test extension list command is available."""
        result = self.runner.invoke(cli, ["extension", "list", "--help"])
        assert result.exit_code == 0
        assert "List available extensions" in result.output


class TestExtensionScaffolder:
    """Test ExtensionScaffolder class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scaffolder_initialization(self):
        """Test scaffolder can be initialized."""
        scaffolder = ExtensionScaffolder(
            name="test_extension",
            extension_type="middleware",
            output_dir=self.temp_dir,
            quiet=True
        )
        
        assert scaffolder.name == "test_extension"
        assert scaffolder.extension_type == "middleware"
        assert scaffolder.output_dir == self.temp_dir
    
    def test_create_middleware_extension(self):
        """Test creating a middleware extension."""
        scaffolder = ExtensionScaffolder(
            name="test_middleware",
            extension_type="middleware",
            output_dir=self.temp_dir,
            include_tests=True,
            include_docs=True,
            quiet=True
        )
        
        scaffolder.create_extension()
        
        # Check that extension directory was created
        ext_dir = Path(self.temp_dir) / "test_middleware"
        assert ext_dir.exists()
        
        # Check core files
        assert (ext_dir / "__init__.py").exists()
        assert (ext_dir / "extension.py").exists()
        assert (ext_dir / "pyproject.toml").exists()
        assert (ext_dir / "README.md").exists()
        
        # Check test files
        assert (ext_dir / "tests" / "__init__.py").exists()
        assert (ext_dir / "tests" / "conftest.py").exists()
        assert (ext_dir / "tests" / "test_test_middleware.py").exists()
        
        # Check documentation
        assert (ext_dir / "docs" / "user_guide.md").exists()
        assert (ext_dir / "docs" / "configuration.md").exists()
    
    def test_create_auth_provider_extension(self):
        """Test creating an auth provider extension."""
        scaffolder = ExtensionScaffolder(
            name="custom_auth",
            extension_type="auth_provider",
            provider_base="auth",
            output_dir=self.temp_dir,
            include_tests=False,
            include_docs=False,
            quiet=True
        )
        
        scaffolder.create_extension()
        
        # Check that extension directory was created
        ext_dir = Path(self.temp_dir) / "custom_auth"
        assert ext_dir.exists()
        
        # Check core files
        assert (ext_dir / "__init__.py").exists()
        assert (ext_dir / "extension.py").exists()
        
        # Check provider files
        assert (ext_dir / "providers" / "__init__.py").exists()
        assert (ext_dir / "providers" / "base.py").exists()
        
        # Should not have tests or docs
        assert not (ext_dir / "tests").exists()
        assert not (ext_dir / "docs").exists()
    
    def test_create_feature_extension(self):
        """Test creating a feature extension."""
        scaffolder = ExtensionScaffolder(
            name="blog_feature",
            extension_type="feature",
            output_dir=self.temp_dir,
            quiet=True
        )
        
        scaffolder.create_extension()
        
        # Check that extension directory was created
        ext_dir = Path(self.temp_dir) / "blog_feature"
        assert ext_dir.exists()
        
        # Check feature-specific files
        assert (ext_dir / "routes.py").exists()
        assert (ext_dir / "models.py").exists()
    
    def test_create_integration_extension(self):
        """Test creating an integration extension."""
        scaffolder = ExtensionScaffolder(
            name="stripe_integration",
            extension_type="integration",
            output_dir=self.temp_dir,
            quiet=True
        )
        
        scaffolder.create_extension()
        
        # Check that extension directory was created
        ext_dir = Path(self.temp_dir) / "stripe_integration"
        assert ext_dir.exists()
        
        # Check integration-specific files
        assert (ext_dir / "client.py").exists()
        assert (ext_dir / "webhooks.py").exists()
    
    def test_extension_content_is_valid(self):
        """Test that generated extension content is valid Python."""
        scaffolder = ExtensionScaffolder(
            name="valid_extension",
            extension_type="middleware",
            output_dir=self.temp_dir,
            quiet=True
        )
        
        scaffolder.create_extension()
        
        ext_dir = Path(self.temp_dir) / "valid_extension"
        
        # Check that main extension file can be parsed
        extension_file = ext_dir / "extension.py"
        assert extension_file.exists()
        
        # Try to compile the file to check syntax
        with open(extension_file) as f:
            content = f.read()
        
        try:
            compile(content, str(extension_file), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated extension.py has syntax error: {e}")
        
        # Check that it contains expected class
        assert "class ValidExtensionExtension" in content
        assert "BaseExtension" in content


class TestExtensionValidator:
    """Test ExtensionValidator class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_nonexistent_extension(self):
        """Test validation of non-existent extension."""
        validator = ExtensionValidator("/nonexistent/path")
        result = validator.validate()
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Extension directory not found" in result["errors"][0]
    
    def test_validate_valid_extension(self):
        """Test validation of valid extension."""
        # Create a basic valid extension
        ext_dir = Path(self.temp_dir) / "valid_ext"
        ext_dir.mkdir()
        
        # Create required files
        (ext_dir / "__init__.py").write_text("")
        (ext_dir / "extension.py").write_text("""
from beginnings.extensions.base import BaseExtension

class ValidExtExtension(BaseExtension):
    def get_middleware_factory(self):
        pass
""")
        
        validator = ExtensionValidator(str(ext_dir))
        result = validator.validate()
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_missing_required_files(self):
        """Test validation with missing required files."""
        # Create extension directory without required files
        ext_dir = Path(self.temp_dir) / "invalid_ext"
        ext_dir.mkdir()
        
        validator = ExtensionValidator(str(ext_dir))
        result = validator.validate()
        
        assert result["valid"] is False
        assert any("Required file missing: __init__.py" in error for error in result["errors"])
        assert any("Required file missing: extension.py" in error for error in result["errors"])
    
    def test_validate_invalid_extension_class(self):
        """Test validation with invalid extension class."""
        # Create extension with invalid class
        ext_dir = Path(self.temp_dir) / "invalid_class_ext"
        ext_dir.mkdir()
        
        (ext_dir / "__init__.py").write_text("")
        (ext_dir / "extension.py").write_text("""
# Missing BaseExtension inheritance and required methods
class InvalidExtension:
    pass
""")
        
        validator = ExtensionValidator(str(ext_dir))
        result = validator.validate()
        
        assert result["valid"] is False
        assert any("BaseExtension" in error for error in result["errors"])


class TestExtensionLister:
    """Test ExtensionLister class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_list_builtin_extensions(self):
        """Test listing builtin extensions."""
        lister = ExtensionLister()
        extensions = lister.list_extensions(installed_only=False)
        
        # Should include builtin extensions
        builtin_names = [ext["name"] for ext in extensions]
        assert "auth" in builtin_names
        assert "csrf" in builtin_names
        assert "rate_limiting" in builtin_names
        assert "security_headers" in builtin_names
    
    def test_list_empty_extensions_directory(self):
        """Test listing with empty extensions directory."""
        # Change to temp directory so no extensions are found
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            
            lister = ExtensionLister()
            extensions = lister.list_extensions(installed_only=True)
            
            # Should only include builtin extensions marked as installed
            assert len(extensions) == 0
        finally:
            os.chdir(original_cwd)
    
    def test_list_with_local_extensions(self):
        """Test listing with local extensions directory."""
        # Create mock extensions directory
        extensions_dir = Path(self.temp_dir) / "extensions"
        extensions_dir.mkdir()
        
        # Create a mock extension
        (extensions_dir / "custom_ext").mkdir()
        (extensions_dir / "custom_ext" / "__init__.py").write_text("")
        (extensions_dir / "custom_ext" / "extension.py").write_text("# Custom extension")
        
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            
            lister = ExtensionLister()
            extensions = lister.list_extensions(installed_only=False)
            
            # Should include our custom extension plus builtins
            names = [ext["name"] for ext in extensions]
            assert "custom_ext" in names
            assert "auth" in names  # builtin
        finally:
            os.chdir(original_cwd)


class TestExtensionCLIIntegration:
    """Test CLI integration for extension commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extension_new_creates_extension(self):
        """Test that 'extension new' command creates extension."""
        result = self.runner.invoke(cli, [
            "extension", "new", "test_cli_ext",
            "--type", "middleware",
            "--output-dir", self.temp_dir
        ])
        
        assert result.exit_code == 0
        assert "Extension 'test_cli_ext' created successfully" in result.output
        
        # Check that extension was created
        ext_dir = Path(self.temp_dir) / "test_cli_ext"
        assert ext_dir.exists()
        assert (ext_dir / "extension.py").exists()
    
    def test_extension_validate_valid_extension(self):
        """Test that 'extension validate' works on valid extension."""
        # First create an extension
        self.runner.invoke(cli, [
            "extension", "new", "valid_ext",
            "--type", "middleware",
            "--output-dir", self.temp_dir
        ])
        
        ext_path = os.path.join(self.temp_dir, "valid_ext")
        
        # Then validate it
        result = self.runner.invoke(cli, [
            "extension", "validate", ext_path
        ])
        
        assert result.exit_code == 0
        assert "Extension validation passed" in result.output
    
    def test_extension_list_shows_builtins(self):
        """Test that 'extension list' shows builtin extensions."""
        result = self.runner.invoke(cli, ["extension", "list"])
        
        assert result.exit_code == 0
        assert "auth" in result.output
        assert "csrf" in result.output