"""Unit tests for documentation renderers."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from beginnings.docs.renderers import BaseRenderer, HTMLRenderer, MarkdownRenderer, PDFRenderer


class TestBaseRenderer:
    """Test BaseRenderer abstract base class."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        class TestRenderer(BaseRenderer):
            async def render_documentation(self, documentation_data, cross_references, config):
                return {}
        
        renderer = TestRenderer()
        
        # Test normal filename
        assert renderer._sanitize_filename("normal_file.html") == "normal_file.html"
        
        # Test filename with invalid characters
        assert renderer._sanitize_filename("file<>:\"/\\|?*.html") == "file_________.html"
        
        # Test filename with multiple dots
        assert renderer._sanitize_filename("file...name.html") == "file.name.html"
        
        # Test filename with leading/trailing dots
        assert renderer._sanitize_filename(".file.") == "file"


class TestMarkdownRenderer:
    """Test MarkdownRenderer class."""
    
    @pytest.fixture
    def renderer(self):
        """Create MarkdownRenderer instance."""
        return MarkdownRenderer()
    
    @pytest.fixture
    def sample_documentation_data(self):
        """Create sample documentation data."""
        return {
            "metadata": {
                "project_name": "Test Project",
                "project_version": "1.0.0",
                "project_description": "Test project description",
                "author": "Test Author",
                "generated_at": "2023-01-01T00:00:00"
            },
            "code_documentation": {
                "test_module": Mock(
                    name="test_module",
                    docstring="Test module docstring",
                    classes={
                        "TestClass": Mock(
                            name="TestClass",
                            docstring="Test class docstring",
                            base_classes=["BaseClass"],
                            methods={
                                "test_method": Mock(
                                    name="test_method",
                                    docstring="Test method docstring",
                                    parameters=[{"name": "self"}, {"name": "param", "type": "str"}],
                                    return_type="bool"
                                )
                            }
                        )
                    },
                    functions={
                        "test_function": Mock(
                            name="test_function",
                            docstring="Test function docstring",
                            parameters=[{"name": "value", "type": "int"}],
                            return_type="str"
                        )
                    }
                )
            },
            "api": {
                "endpoints": {
                    "get_users": Mock(
                        path="/users",
                        method="GET",
                        summary="Get all users",
                        description="Retrieve list of all users",
                        parameters=[{"name": "limit", "type": "int", "required": False}],
                        responses={"200": {"description": "Success"}}
                    )
                },
                "models": {
                    "User": Mock(
                        name="User",
                        description="User model",
                        fields={"id": {"type": "int"}, "name": {"type": "str"}},
                        required_fields=["id", "name"]
                    )
                }
            }
        }
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration."""
        return Mock(
            project_name="Test Project",
            project_version="1.0.0",
            project_description="Test project description",
            author="Test Author"
        )
    
    @pytest.mark.asyncio
    async def test_render_readme(self, renderer, sample_documentation_data, sample_config):
        """Test README rendering."""
        readme_content = await renderer._render_readme(sample_documentation_data, sample_config)
        
        assert "# Test Project" in readme_content
        assert "Test project description" in readme_content
        assert "**Version:** 1.0.0" in readme_content
        assert "**Author:** Test Author" in readme_content
        assert "## Table of Contents" in readme_content
        assert "- [API Reference](API.md)" in readme_content
        assert "- [Code Documentation](CODE.md)" in readme_content
    
    @pytest.mark.asyncio
    async def test_render_api_markdown(self, renderer, sample_documentation_data, sample_config):
        """Test API documentation rendering in Markdown."""
        api_data = sample_documentation_data["api"]
        api_content = await renderer._render_api_markdown(api_data, {}, sample_config)
        
        assert "# API Reference" in api_content
        assert "## Endpoints" in api_content
        assert "### GET /users" in api_content
        assert "Get all users" in api_content
        assert "**Parameters:**" in api_content
        assert "**Responses:**" in api_content
        assert "## Data Models" in api_content
        assert "### User" in api_content
        assert "| Field | Type | Required | Description |" in api_content
    
    @pytest.mark.asyncio
    async def test_render_code_markdown(self, renderer, sample_documentation_data, sample_config):
        """Test code documentation rendering in Markdown."""
        code_data = sample_documentation_data["code_documentation"]
        code_content = await renderer._render_code_markdown(code_data, {}, sample_config)
        
        assert "# Code Documentation" in code_content
        assert "## Module: test_module" in code_content
        assert "Test module docstring" in code_content
        assert "### Classes" in code_content
        assert "#### TestClass" in code_content
        assert "**Inherits from:** BaseClass" in code_content
        assert "**Methods:**" in code_content
        assert "### Functions" in code_content
        assert "test_function(" in code_content
    
    @pytest.mark.asyncio
    async def test_render_documentation_full(self, renderer, sample_documentation_data, sample_config):
        """Test full documentation rendering."""
        cross_references = {}
        
        output_files = await renderer.render_documentation(
            sample_documentation_data, cross_references, sample_config
        )
        
        assert "README.md" in output_files
        assert "API.md" in output_files
        assert "CODE.md" in output_files
        
        readme_content = output_files["README.md"]
        assert "# Test Project" in readme_content


class TestHTMLRenderer:
    """Test HTMLRenderer class."""
    
    @pytest.fixture
    def mock_template_engine(self):
        """Create mock template engine."""
        engine = AsyncMock()
        engine.render_template = AsyncMock(return_value="<html>Mock HTML</html>")
        return engine
    
    @pytest.fixture
    def mock_theme_manager(self):
        """Create mock theme manager."""
        manager = AsyncMock()
        manager.load_theme = AsyncMock()
        manager.add_custom_css = AsyncMock()
        return manager
    
    @pytest.fixture
    def renderer(self, mock_template_engine, mock_theme_manager):
        """Create HTMLRenderer instance."""
        return HTMLRenderer(mock_template_engine, mock_theme_manager)
    
    @pytest.fixture
    def sample_documentation_data(self):
        """Create sample documentation data."""
        return {
            "metadata": {
                "project_name": "Test Project",
                "project_version": "1.0.0",
                "project_description": "Test project description",
                "author": "Test Author"
            },
            "code_documentation": {
                "test_module": Mock(
                    name="test_module",
                    docstring="Test module docstring",
                    classes={},
                    functions={}
                )
            },
            "api": {
                "endpoints": {
                    "test_endpoint": Mock(
                        method="GET",
                        path="/test",
                        summary="Test endpoint"
                    )
                }
            }
        }
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration."""
        return Mock(
            project_name="Test Project",
            project_version="1.0.0",
            project_description="Test project description",
            author="Test Author",
            theme="default"
        )
    
    @pytest.mark.asyncio
    async def test_set_theme(self, renderer, mock_theme_manager):
        """Test theme setting."""
        await renderer.set_theme("custom_theme")
        
        assert renderer.current_theme == "custom_theme"
        mock_theme_manager.load_theme.assert_called_once_with("custom_theme")
    
    @pytest.mark.asyncio
    async def test_add_custom_css(self, renderer, mock_theme_manager):
        """Test adding custom CSS."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as css_file:
            css_file.write("body { color: red; }")
            css_file_path = css_file.name
        
        try:
            await renderer.add_custom_css(css_file_path)
            mock_theme_manager.add_custom_css.assert_called_once()
        finally:
            Path(css_file_path).unlink()
    
    @pytest.mark.asyncio
    async def test_render_index_page(self, renderer, sample_documentation_data, sample_config):
        """Test index page rendering."""
        await renderer._render_index_page(sample_documentation_data, sample_config)
        
        # Check that template engine was called with correct template
        renderer.template_engine.render_template.assert_called_once()
        args, kwargs = renderer.template_engine.render_template.call_args
        assert args[0] == "index.html"
        assert kwargs["title"] == "Test Project Documentation"
        assert kwargs["project_name"] == "Test Project"
    
    @pytest.mark.asyncio
    async def test_get_available_sections(self, renderer, sample_documentation_data):
        """Test getting available sections."""
        sections = renderer._get_available_sections(sample_documentation_data)
        
        # Should have sections for API and code documentation
        section_names = [s["name"] for s in sections]
        assert "API Reference" in section_names
        assert "Code Documentation" in section_names
        
        # Check section structure
        api_section = next(s for s in sections if s["name"] == "API Reference")
        assert api_section["url"] == "api/index.html"
        assert api_section["description"] == "REST API endpoints and schemas"
        assert api_section["icon"] == "api"
    
    @pytest.mark.asyncio
    async def test_render_documentation_full(self, renderer, sample_documentation_data, sample_config):
        """Test full HTML documentation rendering."""
        cross_references = {}
        
        output_files = await renderer.render_documentation(
            sample_documentation_data, cross_references, sample_config
        )
        
        assert "index.html" in output_files
        assert isinstance(output_files["index.html"], str)
        
        # Should call template engine multiple times for different pages
        assert renderer.template_engine.render_template.call_count > 1


class TestPDFRenderer:
    """Test PDFRenderer class."""
    
    @pytest.fixture
    def renderer(self):
        """Create PDFRenderer instance."""
        return PDFRenderer()
    
    @pytest.fixture
    def sample_documentation_data(self):
        """Create sample documentation data."""
        return {
            "metadata": {
                "project_name": "Test Project",
                "project_version": "1.0.0",
                "project_description": "Test project description",
                "author": "Test Author"
            },
            "api": {
                "endpoints": {
                    "test_endpoint": Mock(
                        method="GET",
                        path="/test",
                        summary="Test endpoint",
                        description="Test endpoint description",
                        parameters=[{"name": "param1", "required": True}]
                    )
                }
            },
            "code_documentation": {
                "test_module": Mock(
                    name="test_module",
                    docstring="Test module docstring",
                    classes={},
                    functions={}
                )
            }
        }
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration."""
        return Mock(
            project_name="Test Project",
            project_version="1.0.0",
            project_description="Test project description",
            author="Test Author"
        )
    
    def test_get_pdf_css(self, renderer):
        """Test PDF CSS generation."""
        css = renderer._get_pdf_css()
        
        assert "body {" in css
        assert "font-family: Arial, sans-serif;" in css
        assert "h1 {" in css
        assert "table {" in css
        assert "code {" in css
    
    @pytest.mark.asyncio
    async def test_generate_pdf_html(self, renderer, sample_documentation_data, sample_config):
        """Test PDF HTML generation."""
        html_content = await renderer._generate_pdf_html(
            sample_documentation_data, {}, sample_config
        )
        
        assert "<!DOCTYPE html>" in html_content
        assert "<title>Test Project Documentation</title>" in html_content
        assert "<h1>Test Project</h1>" in html_content
        assert "Test project description" in html_content
        assert "Table of Contents" in html_content
        assert "</html>" in html_content
    
    @pytest.mark.asyncio
    async def test_generate_api_html_section(self, renderer, sample_documentation_data):
        """Test API section HTML generation."""
        api_data = sample_documentation_data["api"]
        html_section = await renderer._generate_api_html_section(api_data)
        
        assert '<h2 id="api">API Reference</h2>' in html_section
        assert "<h3>GET /test</h3>" in html_section
        assert "Test endpoint" in html_section
        assert "<table>" in html_section
        assert "<th>Name</th>" in html_section
    
    @pytest.mark.asyncio
    async def test_generate_code_html_section(self, renderer, sample_documentation_data):
        """Test code section HTML generation."""
        code_data = sample_documentation_data["code_documentation"]
        html_section = await renderer._generate_code_html_section(code_data)
        
        assert '<h2 id="code">Code Documentation</h2>' in html_section
        assert "<h3>Module: test_module</h3>" in html_section
        assert "Test module docstring" in html_section
    
    @pytest.mark.asyncio
    async def test_render_documentation_without_weasyprint(self, renderer, sample_documentation_data, sample_config):
        """Test PDF rendering without WeasyPrint."""
        # Mock the HTML and CSS classes to be None (simulating missing WeasyPrint)
        with patch('beginnings.docs.renderers.HTML', None), \
             patch('beginnings.docs.renderers.CSS', None):
            
            with pytest.raises(RuntimeError, match="PDF rendering requires WeasyPrint"):
                await renderer.render_documentation(
                    sample_documentation_data, {}, sample_config
                )
    
    @pytest.mark.asyncio
    async def test_render_documentation_with_weasyprint(self, renderer, sample_documentation_data, sample_config):
        """Test PDF rendering with WeasyPrint (mocked)."""
        mock_html_doc = Mock()
        mock_html_doc.write_pdf.return_value = b"PDF content"
        
        with patch('beginnings.docs.renderers.HTML') as mock_html_class, \
             patch('beginnings.docs.renderers.CSS') as mock_css_class:
            
            mock_html_class.return_value = mock_html_doc
            mock_css_class.return_value = Mock()
            
            output_files = await renderer.render_documentation(
                sample_documentation_data, {}, sample_config
            )
            
            assert "documentation.pdf" in output_files
            assert output_files["documentation.pdf"] == b"PDF content"
            
            # Verify HTML and CSS were called
            mock_html_class.assert_called_once()
            mock_css_class.assert_called_once()
            mock_html_doc.write_pdf.assert_called_once()


class TestRendererIntegration:
    """Integration tests for renderers."""
    
    @pytest.mark.asyncio
    async def test_markdown_renderer_with_real_data(self):
        """Test MarkdownRenderer with real data structure."""
        renderer = MarkdownRenderer()
        
        # Create real documentation data structure
        documentation_data = {
            "metadata": {
                "project_name": "Integration Test Project",
                "project_version": "2.0.0",
                "project_description": "Integration test project",
                "author": "Integration Test Author"
            },
            "code_documentation": {},
            "api": {},
            "extensions": {},
            "configuration": {}
        }
        
        config = Mock(
            project_name="Integration Test Project",
            project_version="2.0.0",
            project_description="Integration test project",
            author="Integration Test Author"
        )
        
        output_files = await renderer.render_documentation(
            documentation_data, {}, config
        )
        
        assert "README.md" in output_files
        readme = output_files["README.md"]
        assert "# Integration Test Project" in readme
        assert "**Version:** 2.0.0" in readme
    
    @pytest.mark.asyncio
    async def test_renderer_error_handling(self):
        """Test renderer error handling."""
        class FailingRenderer(BaseRenderer):
            async def render_documentation(self, documentation_data, cross_references, config):
                raise Exception("Rendering failed")
        
        renderer = FailingRenderer()
        
        with pytest.raises(Exception, match="Rendering failed"):
            await renderer.render_documentation({}, {}, Mock())
    
    def test_renderer_filename_sanitization_edge_cases(self):
        """Test edge cases in filename sanitization."""
        class TestRenderer(BaseRenderer):
            async def render_documentation(self, documentation_data, cross_references, config):
                return {}
        
        renderer = TestRenderer()
        
        # Test very long filename
        long_name = "a" * 300 + ".html"
        sanitized = renderer._sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".html")
        
        # Test filename with only invalid characters
        invalid_name = "<>:\"/\\|?*"
        sanitized = renderer._sanitize_filename(invalid_name)
        assert sanitized == "_________"
        
        # Test empty filename
        sanitized = renderer._sanitize_filename("")
        assert sanitized == ""