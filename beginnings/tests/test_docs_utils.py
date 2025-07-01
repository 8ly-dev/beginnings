"""Unit tests for documentation utilities."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from beginnings.docs.utils import DocumentationUtils


class TestDocumentationUtils:
    """Test DocumentationUtils class."""
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Normal filename
        assert DocumentationUtils.sanitize_filename("normal_file.txt") == "normal_file.txt"
        
        # Filename with invalid characters
        assert DocumentationUtils.sanitize_filename("file<>:\"/\\|?*.txt") == "file_________.txt"
        
        # Filename with multiple dots
        assert DocumentationUtils.sanitize_filename("file...name.txt") == "file.name.txt"
        
        # Filename with leading/trailing dots and spaces
        assert DocumentationUtils.sanitize_filename("  .file.  ") == "file"
        
        # Very long filename
        long_name = "a" * 300 + ".txt"
        result = DocumentationUtils.sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")
    
    def test_generate_slug(self):
        """Test URL slug generation."""
        # Normal text
        assert DocumentationUtils.generate_slug("Hello World") == "hello-world"
        
        # Text with special characters
        assert DocumentationUtils.generate_slug("Hello, World!") == "hello-world"
        
        # Text with multiple spaces and hyphens
        assert DocumentationUtils.generate_slug("Hello   ---   World") == "hello-world"
        
        # Text with leading/trailing hyphens
        assert DocumentationUtils.generate_slug("---Hello World---") == "hello-world"
        
        # Empty text
        assert DocumentationUtils.generate_slug("") == ""
    
    def test_extract_code_blocks(self):
        """Test code block extraction from markdown."""
        content = """
This is some text.

```python
def hello():
    print("Hello, world!")
```

More text here.

```javascript
console.log("Hello, world!");
```

Final text.

```
plain code block
```
"""
        
        code_blocks = DocumentationUtils.extract_code_blocks(content)
        
        assert len(code_blocks) == 3
        
        # Python block
        python_block = code_blocks[0]
        assert python_block["language"] == "python"
        assert 'def hello():' in python_block["content"]
        assert 'print("Hello, world!")' in python_block["content"]
        
        # JavaScript block
        js_block = code_blocks[1]
        assert js_block["language"] == "javascript"
        assert 'console.log("Hello, world!");' in js_block["content"]
        
        # Plain block
        plain_block = code_blocks[2]
        assert plain_block["language"] == "text"
        assert "plain code block" in plain_block["content"]
    
    def test_generate_table_of_contents(self):
        """Test table of contents generation."""
        content = """
# Main Title

Some content here.

## Section 1

Content for section 1.

### Subsection 1.1

Content for subsection.

## Section 2

Content for section 2.

#### Deep Subsection

This should not be included (level 4).
"""
        
        toc = DocumentationUtils.generate_table_of_contents(content, max_depth=3)
        
        assert len(toc) == 4  # Main Title, Section 1, Subsection 1.1, Section 2
        
        # Check structure
        assert toc[0]["level"] == 1
        assert toc[0]["title"] == "Main Title"
        assert toc[0]["anchor"] == "main-title"
        
        assert toc[1]["level"] == 2
        assert toc[1]["title"] == "Section 1"
        assert toc[1]["anchor"] == "section-1"
        
        assert toc[2]["level"] == 3
        assert toc[2]["title"] == "Subsection 1.1"
        assert toc[2]["anchor"] == "subsection-11"
        
        assert toc[3]["level"] == 2
        assert toc[3]["title"] == "Section 2"
        assert toc[3]["anchor"] == "section-2"
    
    def test_build_breadcrumb_path(self):
        """Test breadcrumb path building."""
        # Simple path
        breadcrumbs = DocumentationUtils.build_breadcrumb_path("api/endpoints/users.html")
        
        assert len(breadcrumbs) == 4
        assert breadcrumbs[0]["title"] == "Home"
        assert breadcrumbs[0]["url"] == "/"
        assert breadcrumbs[0]["is_current"] is False
        
        assert breadcrumbs[1]["title"] == "Api"
        assert breadcrumbs[1]["url"] == "api"
        assert breadcrumbs[1]["is_current"] is False
        
        assert breadcrumbs[2]["title"] == "Endpoints"
        assert breadcrumbs[2]["url"] == "api/endpoints"
        assert breadcrumbs[2]["is_current"] is False
        
        assert breadcrumbs[3]["title"] == "Users"
        assert breadcrumbs[3]["url"] == "api/endpoints/users.html"
        assert breadcrumbs[3]["is_current"] is True
        
        # Path with base URL
        breadcrumbs = DocumentationUtils.build_breadcrumb_path(
            "docs/api/users.html", 
            base_path="/docs"
        )
        
        assert breadcrumbs[0]["url"] == "/docs"
        assert breadcrumbs[1]["url"] == "/docs/api"
    
    def test_calculate_reading_time(self):
        """Test reading time calculation."""
        # Short text
        short_text = "Hello world."
        assert DocumentationUtils.calculate_reading_time(short_text) == 1  # Minimum 1 minute
        
        # Medium text (approximately 225 words)
        medium_text = " ".join(["word"] * 225)
        assert DocumentationUtils.calculate_reading_time(medium_text) == 1
        
        # Long text (approximately 450 words)
        long_text = " ".join(["word"] * 450)
        assert DocumentationUtils.calculate_reading_time(long_text) == 2
        
        # Text with code blocks (should be excluded)
        text_with_code = f"""
{medium_text}

```python
{" ".join(["code"] * 100)}
```

{medium_text}
"""
        # Should still be around 2 minutes since code is excluded
        assert DocumentationUtils.calculate_reading_time(text_with_code) == 2
    
    def test_extract_metadata_from_content(self):
        """Test metadata extraction from content."""
        # Content with YAML front matter
        content_with_yaml = """---
title: Test Document
author: Test Author
tags: [test, documentation]
published: true
---

# Main Content

This is the main content of the document.

This is another paragraph.
"""
        
        with patch('yaml.safe_load') as mock_yaml:
            mock_yaml.return_value = {
                "title": "Test Document",
                "author": "Test Author",
                "tags": ["test", "documentation"],
                "published": True
            }
            
            metadata = DocumentationUtils.extract_metadata_from_content(content_with_yaml)
            
            assert metadata["title"] == "Test Document"
            assert metadata["author"] == "Test Author"
            assert metadata["tags"] == ["test", "documentation"]
    
    def test_extract_metadata_without_yaml(self):
        """Test metadata extraction without YAML library."""
        content_with_yaml = """---
title: Test Document
author: Test Author
description: A test document
---

# Main Content

This is the main content.
"""
        
        # Simulate missing YAML library by making import fail
        def mock_import(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError("No module named 'yaml'")
            return __builtins__['__import__'](name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            metadata = DocumentationUtils.extract_metadata_from_content(content_with_yaml)
            
            # Should fallback to simple parsing
            assert "title" in metadata
            assert "author" in metadata
            assert metadata["title"] == "Test Document"
            assert metadata["author"] == "Test Author"
    
    def test_extract_metadata_from_headers(self):
        """Test metadata extraction from headers and content."""
        content_without_frontmatter = """
# Document Title

This is the first paragraph that should be used as description. It's long enough to be meaningful.

## Section 1

More content here.
"""
        
        metadata = DocumentationUtils.extract_metadata_from_content(content_without_frontmatter)
        
        assert metadata["title"] == "Document Title"
        assert "first paragraph" in metadata["description"]
        assert len(metadata["description"]) <= 203  # Should be truncated
    
    def test_validate_links(self):
        """Test link validation."""
        content = """
This is a [markdown link](http://example.com).

This is a [relative link](../other-page.html).

This is an [anchor link](#section-1).

This is <a href="https://example.org">HTML link</a>.

This is an <a href="broken-link.html">broken link</a>.
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a file for the relative link test
            (temp_path.parent / "other-page.html").touch()
            
            results = DocumentationUtils.validate_links(content, str(temp_path))
            
            assert len(results) == 5
            
            # Check external links (should be valid)
            external_links = [r for r in results if r["is_external"]]
            assert len(external_links) == 2
            for link in external_links:
                assert link["is_valid"] is True
            
            # Check anchor link
            anchor_links = [r for r in results if r["url"].startswith("#")]
            assert len(anchor_links) == 1
            assert anchor_links[0]["is_valid"] is True
    
    def test_generate_search_index(self):
        """Test search index generation."""
        # Create mock objects that behave like the actual data structures
        endpoint_mock = Mock()
        endpoint_mock.method = "GET"
        endpoint_mock.path = "/users"
        endpoint_mock.summary = "Get all users"
        endpoint_mock.description = "Retrieve list of users"
        endpoint_mock.tags = ["users", "api"]
        
        module_mock = Mock()
        module_mock.get.return_value = "User management module"
        # Configure the mock to return the expected data
        classes_dict = {"User": Mock(get=lambda x, default='': "User class" if x == 'docstring' else default)}
        functions_dict = {"create_user": Mock(get=lambda x, default='': "Create a new user" if x == 'docstring' else default)}
        
        def mock_get_side_effect(key, default=None):
            if key == 'docstring':
                return "User management module"
            elif key == 'classes':
                return classes_dict
            elif key == 'functions':
                return functions_dict
            return default
        
        module_mock.get.side_effect = mock_get_side_effect
        # Also set attributes for direct access
        module_mock.classes = classes_dict
        module_mock.functions = functions_dict
        module_mock.docstring = "User management module"
        
        documentation_data = {
            "api": {
                "endpoints": {
                    "get_users": endpoint_mock
                }
            },
            "code_documentation": {
                "user_module": module_mock
            },
            "extensions": {
                "auth_extension": {
                    "metadata": {
                        "description": "Authentication extension"
                    }
                }
            }
        }
        
        search_index = DocumentationUtils.generate_search_index(documentation_data)
        
        assert len(search_index) >= 4  # API endpoint, module, class, function, extension
        
        # Check API endpoint entry
        api_entries = [e for e in search_index if e["type"] == "api_endpoint"]
        assert len(api_entries) == 1
        assert api_entries[0]["title"] == "GET /users"
        assert "users" in api_entries[0]["tags"]
        
        # Check module entry
        module_entries = [e for e in search_index if e["type"] == "module"]
        assert len(module_entries) == 1
        assert module_entries[0]["title"] == "Module: user_module"
        
        # Check class entry
        class_entries = [e for e in search_index if e["type"] == "class"]
        assert len(class_entries) == 1
        assert class_entries[0]["title"] == "Class: user_module.User"
    
    def test_generate_sitemap(self):
        """Test sitemap generation."""
        documentation_data = {
            "api": {
                "endpoints": {
                    "get_users": {},
                    "create_user": {}
                }
            },
            "code_documentation": {
                "user_module": {},
                "auth_module": {}
            },
            "extensions": {
                "auth_extension": {}
            }
        }
        
        sitemap = DocumentationUtils.generate_sitemap(
            documentation_data, 
            "https://docs.example.com"
        )
        
        assert '<?xml version="1.0" encoding="UTF-8"?>' in sitemap
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in sitemap
        assert '<loc>https://docs.example.com</loc>' in sitemap
        assert '<loc>https://docs.example.com/api/endpoints/get_users.html</loc>' in sitemap
        assert '<loc>https://docs.example.com/code/modules/user_module.html</loc>' in sitemap
        assert '<loc>https://docs.example.com/extensions/auth_extension.html</loc>' in sitemap
        assert '</urlset>' in sitemap
    
    def test_create_documentation_manifest(self):
        """Test documentation manifest creation."""
        # Create proper mock objects for modules
        module1_mock = Mock()
        module1_mock.classes = {"Class1": {}, "Class2": {}}
        module1_mock.functions = {"func1": {}}
        
        module2_mock = Mock()
        module2_mock.classes = {}
        module2_mock.functions = {"func2": {}, "func3": {}}
        
        documentation_data = {
            "metadata": {
                "project_name": "Test Project",
                "project_version": "1.0.0",
                "generated_at": "2023-01-01T00:00:00"
            },
            "api": {
                "endpoints": {"endpoint1": {}, "endpoint2": {}}
            },
            "code_documentation": {
                "module1": module1_mock,
                "module2": module2_mock
            },
            "extensions": {
                "ext1": {}, "ext2": {}
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = DocumentationUtils.create_documentation_manifest(
                documentation_data, temp_dir
            )
            
            assert Path(manifest_path).exists()
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            assert manifest["name"] == "Test Project"
            assert manifest["version"] == "1.0.0"
            assert manifest["generated_at"] == "2023-01-01T00:00:00"
            
            # Check section statistics
            assert manifest["sections"]["api"]["endpoint_count"] == 2
            assert manifest["sections"]["code"]["module_count"] == 2
            assert manifest["sections"]["code"]["class_count"] == 2
            assert manifest["sections"]["code"]["function_count"] == 3
            assert manifest["sections"]["extensions"]["extension_count"] == 2
    
    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        content1 = "Hello, world!"
        content2 = "Hello, world!"
        content3 = "Hello, universe!"
        
        hash1 = DocumentationUtils.calculate_content_hash(content1)
        hash2 = DocumentationUtils.calculate_content_hash(content2)
        hash3 = DocumentationUtils.calculate_content_hash(content3)
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        assert hash1 != hash3
        
        # Hash should be SHA-256 (64 characters)
        assert len(hash1) == 64
        assert len(hash3) == 64
    
    def test_get_file_info(self):
        """Test file information retrieval."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test content")
            temp_file_path = temp_file.name
        
        try:
            file_info = DocumentationUtils.get_file_info(temp_file_path)
            
            assert file_info["exists"] is True
            assert file_info["size"] > 0
            assert "modified" in file_info
            assert file_info["is_binary"] is False
            
            # Test non-existent file
            nonexistent_info = DocumentationUtils.get_file_info("/nonexistent/file.txt")
            assert nonexistent_info["exists"] is False
            
        finally:
            Path(temp_file_path).unlink()
    
    def test_optimize_images_for_docs_without_pil(self):
        """Test image optimization without PIL."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_image:
            temp_image.write(b"fake image data")
            temp_image_path = temp_image.name
        
        with tempfile.TemporaryDirectory() as output_dir:
            try:
                # Mock PIL to be unavailable by making import fail
                original_import = __builtins__['__import__']
                def mock_import(name, *args, **kwargs):
                    if name == 'PIL' or 'PIL' in name:
                        raise ImportError("No module named 'PIL'")
                    return original_import(name, *args, **kwargs)
                
                with patch('builtins.__import__', side_effect=mock_import):
                    result_path = DocumentationUtils.optimize_images_for_docs(
                        temp_image_path, output_dir
                    )
                    
                    # Should copy the file as fallback
                    assert Path(result_path).exists()
                    assert Path(result_path).read_bytes() == b"fake image data"
                    
            finally:
                Path(temp_image_path).unlink()
    
    def test_is_binary_file(self):
        """Test binary file detection."""
        # Create text file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as text_file:
            text_file.write("This is text content")
            text_file_path = text_file.name
        
        # Create binary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as binary_file:
            binary_file.write(b'\x00\x01\x02\x03\x04\x05')
            binary_file_path = binary_file.name
        
        try:
            # Test text file
            assert DocumentationUtils._is_binary_file(Path(text_file_path)) is False
            
            # Test binary file
            assert DocumentationUtils._is_binary_file(Path(binary_file_path)) is True
            
        finally:
            Path(text_file_path).unlink()
            Path(binary_file_path).unlink()