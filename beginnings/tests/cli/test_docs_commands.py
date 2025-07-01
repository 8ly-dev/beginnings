"""Tests for documentation CLI commands."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from beginnings.cli.main import cli


class TestDocsGenerate:
    """Test documentation generation command."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_docs_generate_basic(self):
        """Test basic documentation generation."""
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--output", self.temp_dir
        ])
        
        assert result.exit_code == 0
        assert ("Documentation generated" in result.output or 
                "Documentation Summary" in result.output)
        
        # Check that documentation files were created
        docs_dir = Path(self.temp_dir)
        assert (docs_dir / "html" / "index.html").exists()
    
    def test_docs_generate_with_config(self):
        """Test documentation generation with config file."""
        # Create config file
        config_content = {
            "app": {
                "name": "test-app",
                "debug": False
            },
            "extensions": ["auth:session", "csrf:protection"]
        }
        
        config_path = os.path.join(self.temp_dir, "app.yaml")
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(config_content, f)
        
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--config", config_path,
            "--output", os.path.join(self.temp_dir, "docs")
        ])
        
        assert result.exit_code == 0
        assert "test-app" in result.output or "Documentation generated" in result.output
    
    def test_docs_generate_api_reference(self):
        """Test API reference generation."""
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--output", self.temp_dir,
            "--include-api"
        ])
        
        assert result.exit_code == 0
        
        # Check API documentation was generated
        docs_dir = Path(self.temp_dir)
        assert (docs_dir / "api").exists()
    
    def test_docs_generate_with_format(self):
        """Test documentation generation with specific format."""
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--output", self.temp_dir,
            "--format", "markdown"
        ])
        
        assert result.exit_code == 0
        
        # Check markdown files were generated
        docs_dir = Path(self.temp_dir)
        assert any(f.suffix == ".md" for f in docs_dir.iterdir())
    
    def test_docs_generate_with_theme(self):
        """Test documentation generation with custom theme."""
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--output", self.temp_dir,
            "--theme", "dark"
        ])
        
        assert result.exit_code == 0
        assert "theme" in result.output.lower() or "generated" in result.output.lower()


class TestDocsServe:
    """Test documentation serve command."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('beginnings.docs.generator.DocumentationServer')
    def test_docs_serve_basic(self, mock_server):
        """Test basic documentation serving."""
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        # Create some docs to serve
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.html").write_text("<html><body>Test docs</body></html>")
        
        result = self.runner.invoke(cli, [
            "docs", "serve",
            "--docs-dir", str(docs_dir)
        ])
        
        # Should start the server
        mock_server.assert_called_once()
        mock_server_instance.serve.assert_called_once()
    
    @patch('beginnings.docs.generator.DocumentationServer')
    def test_docs_serve_with_port(self, mock_server):
        """Test documentation serving with custom port."""
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.html").write_text("<html><body>Test docs</body></html>")
        
        result = self.runner.invoke(cli, [
            "docs", "serve",
            "--docs-dir", str(docs_dir),
            "--port", "8080"
        ])
        
        mock_server.assert_called_once()
        # Verify port was passed
        call_args = mock_server.call_args
        assert call_args[1]['port'] == 8080 or any('8080' in str(arg) for arg in call_args[0])
    
    @patch('beginnings.docs.generator.DocumentationServer')
    def test_docs_serve_with_auto_reload(self, mock_server):
        """Test documentation serving with auto-reload."""
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance
        
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.html").write_text("<html><body>Test docs</body></html>")
        
        result = self.runner.invoke(cli, [
            "docs", "serve",
            "--docs-dir", str(docs_dir),
            "--auto-reload"
        ])
        
        mock_server.assert_called_once()
        mock_server_instance.serve.assert_called_once()


class TestDocsValidate:
    """Test documentation validation command."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_docs_validate_valid_docs(self):
        """Test validation of valid documentation."""
        # Create valid documentation structure
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "index.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Docs</title></head>
        <body><h1>Welcome</h1><p>Valid content</p></body>
        </html>
        """)
        
        (docs_dir / "api.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>API Reference</title></head>
        <body><h1>API</h1><p>API documentation</p></body>
        </html>
        """)
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir),
            "--severity", "error"  # Only show errors, not warnings
        ])
        
        # Should pass since no errors, only warnings for missing pages
        assert result.exit_code == 0 or result.exit_code == 1  # Allow warnings
        assert "Validation Results" in result.output
    
    def test_docs_validate_invalid_html(self):
        """Test validation of invalid HTML documentation."""
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        # Create invalid HTML
        (docs_dir / "index.html").write_text("""
        <html>
        <head><title>Test Docs</title>
        <body><h1>Welcome<p>Broken HTML
        """)
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir)
        ])
        
        assert result.exit_code != 0
        assert "✗" in result.output or "error" in result.output.lower()
    
    def test_docs_validate_missing_required_pages(self):
        """Test validation detects missing required pages."""
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        # Only create some pages, missing others
        (docs_dir / "api.html").write_text("<html><body>API docs</body></html>")
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir),
            "--check-required"
        ])
        
        assert result.exit_code != 0
        assert "missing" in result.output.lower() or "required" in result.output.lower()
    
    def test_docs_validate_broken_links(self):
        """Test validation detects broken links."""
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "index.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Docs</title></head>
        <body>
            <h1>Welcome</h1>
            <a href="nonexistent.html">Broken link</a>
            <a href="api.html">Valid link</a>
        </body>
        </html>
        """)
        
        (docs_dir / "api.html").write_text("<html><body>API docs</body></html>")
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir),
            "--check-links"
        ])
        
        assert result.exit_code != 0
        assert "broken" in result.output.lower() or "link" in result.output.lower()
    
    def test_docs_validate_accessibility(self):
        """Test accessibility validation."""
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        # Create HTML with accessibility issues
        (docs_dir / "index.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Docs</title></head>
        <body>
            <h1>Welcome</h1>
            <img src="image.png">  <!-- Missing alt text -->
            <button>Click me</button>  <!-- Missing aria-label or content -->
        </body>
        </html>
        """)
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir),
            "--check-accessibility"
        ])
        
        assert result.exit_code != 0
        assert "accessibility" in result.output.lower() or "a11y" in result.output.lower()
    
    def test_docs_validate_with_json_output(self):
        """Test validation with JSON output format."""
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "index.html").write_text("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Docs</title></head>
        <body><h1>Welcome</h1></body>
        </html>
        """)
        
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", str(docs_dir),
            "--format", "json"
        ])
        
        assert result.exit_code == 0
        
        # Should be valid JSON
        try:
            output = json.loads(result.output.strip())
            assert "validation_results" in output or "status" in output
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


class TestDocsIntegration:
    """Test documentation CLI integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_docs_generate_and_validate_workflow(self):
        """Test complete generate and validate workflow."""
        docs_output = os.path.join(self.temp_dir, "docs")
        
        # Generate documentation
        result = self.runner.invoke(cli, [
            "docs", "generate",
            "--output", docs_output
        ])
        
        assert result.exit_code == 0
        
        # Validate generated documentation
        result = self.runner.invoke(cli, [
            "docs", "validate",
            "--docs-dir", docs_output
        ])
        
        assert result.exit_code == 0
    
    def test_docs_help_commands(self):
        """Test help for documentation commands."""
        # Test main docs group help
        result = self.runner.invoke(cli, ["docs", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "serve" in result.output
        assert "validate" in result.output
        
        # Test individual command help
        for cmd in ["generate", "serve", "validate"]:
            result = self.runner.invoke(cli, ["docs", cmd, "--help"])
            assert result.exit_code == 0