"""Tests for documentation content validation.

This module tests content accuracy validation, link checking, and
quality assurance features of the documentation system. Following TDD.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Import interfaces to be implemented (TDD)
from beginnings.docs.validation.content_validator import (
    ContentValidator,
    ValidationResult,
    ValidationRule
)
from beginnings.docs.validation.link_checker import (
    LinkChecker,
    LinkCheckResult,
    LinkStatus
)
from beginnings.docs.validation.example_tester import (
    ExampleTester,
    TestResult,
    CodeExample
)
from beginnings.docs.validation.accessibility_checker import (
    AccessibilityChecker,
    AccessibilityResult,
    AccessibilityLevel
)


class TestContentValidator:
    """Test content validation following SRP."""
    
    @pytest.fixture
    def content_validator(self):
        """Create content validator for testing."""
        return ContentValidator()
    
    @pytest.fixture
    def validation_rules(self):
        """Sample validation rules."""
        return [
            ValidationRule(
                name="heading_structure",
                description="Check proper heading hierarchy",
                severity="error",
                pattern=r"^#{1,6}\s+",
                check_function="validate_heading_hierarchy"
            ),
            ValidationRule(
                name="code_block_language",
                description="Code blocks should specify language",
                severity="warning", 
                pattern=r"```(\w+)?",
                check_function="validate_code_language"
            ),
            ValidationRule(
                name="internal_links",
                description="Validate internal link format",
                severity="error",
                pattern=r"\[([^\]]+)\]\(([^)]+)\)",
                check_function="validate_internal_links"
            )
        ]
    
    @pytest.fixture
    def sample_markdown(self):
        """Sample markdown content for testing."""
        return """
# Getting Started

This guide will help you get started with Beginnings.

## Installation

Install using pip:

```bash
pip install beginnings
```

For more details, see the [configuration guide](./configuration.md).

### Requirements

- Python 3.8+
- Modern browser

#### Optional Dependencies

Some optional packages for enhanced features.

## Next Steps

Continue to [your first app](../tutorials/first-app.md).
"""
    
    def test_validator_initialization(self, content_validator):
        """Test content validator initializes correctly."""
        assert content_validator is not None
        assert hasattr(content_validator, 'validate_content')
        assert hasattr(content_validator, 'add_rule')
        assert hasattr(content_validator, 'check_accuracy')
        assert hasattr(content_validator, 'validate_structure')
    
    def test_validate_content_structure(self, content_validator, validation_rules, sample_markdown):
        """Test content structure validation."""
        for rule in validation_rules:
            content_validator.add_rule(rule)
        
        result = content_validator.validate_content(sample_markdown, "getting-started.md")
        
        assert isinstance(result, ValidationResult)
        assert result.file_path == "getting-started.md"
        assert result.total_rules_checked == len(validation_rules)
        
        # Should pass heading structure (proper hierarchy)
        heading_errors = [e for e in result.errors if "heading" in e.rule_name]
        assert len(heading_errors) == 0
    
    def test_validate_heading_hierarchy(self, content_validator):
        """Test heading hierarchy validation."""
        # Invalid hierarchy (skips H2)
        invalid_content = """
# Main Title

### Subsection (skips H2)

## This should be before H3
"""
        
        rule = ValidationRule(
            name="heading_hierarchy",
            description="Check heading hierarchy",
            severity="error",
            check_function="validate_heading_hierarchy"
        )
        content_validator.add_rule(rule)
        
        result = content_validator.validate_content(invalid_content, "test.md")
        
        assert not result.is_valid
        assert any("hierarchy" in error.message.lower() for error in result.errors)
    
    def test_validate_code_blocks(self, content_validator):
        """Test code block validation."""
        content_with_code = """
# Code Examples

Good code block:
```python
print("Hello World")
```

Bad code block (no language):
```
some code without language
```
"""
        
        rule = ValidationRule(
            name="code_language",
            description="Code blocks need language",
            severity="warning",
            check_function="validate_code_language"
        )
        content_validator.add_rule(rule)
        
        result = content_validator.validate_content(content_with_code, "code.md")
        
        # Should have warning for code block without language
        warnings = [w for w in result.warnings if "language" in w.message.lower()]
        assert len(warnings) > 0
    
    def test_validate_internal_links(self, content_validator):
        """Test internal link validation."""
        content_with_links = """
# Links Test

Valid link: [config guide](./configuration.md)
Invalid link: [broken](./nonexistent.md)
External link: [Python](https://python.org)
"""
        
        rule = ValidationRule(
            name="internal_links",
            description="Validate internal links exist",
            severity="error", 
            check_function="validate_internal_links"
        )
        content_validator.add_rule(rule)
        
        # Mock file existence
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: "configuration.md" in str(path)
            
            result = content_validator.validate_content(content_with_links, "links.md")
            
            # Should have error for broken internal link
            link_errors = [e for e in result.errors if "nonexistent" in e.message]
            assert len(link_errors) > 0
    
    def test_check_content_accuracy(self, content_validator):
        """Test content accuracy checking against code."""
        # Content claiming function exists
        content = """
# API Reference

Use the `create_app()` function to initialize your application:

```python
from beginnings import create_app
app = create_app()
```
"""
        
        # Mock code inspection
        with patch('inspect.getmembers') as mock_inspect:
            mock_inspect.return_value = [('create_app', lambda: None)]
            
            result = content_validator.check_accuracy(content, "api.md")
            
            assert result.accuracy_score > 80
            assert len(result.inaccuracies) == 0
    
    def test_custom_validation_rules(self, content_validator):
        """Test adding custom validation rules."""
        # Custom rule for checking configuration examples
        custom_rule = ValidationRule(
            name="config_examples",
            description="Configuration examples should be valid YAML",
            severity="error",
            check_function="validate_yaml_examples"
        )
        
        content_validator.add_rule(custom_rule)
        
        content_with_yaml = """
# Configuration

Example configuration:

```yaml
app:
  name: my-app
  debug: true
  invalid_yaml: [unclosed
```
"""
        
        with patch.object(content_validator, 'validate_yaml_examples') as mock_validate:
            mock_validate.return_value = [ValidationResult.Error("Invalid YAML syntax")]
            
            result = content_validator.validate_content(content_with_yaml, "config.md")
            
            yaml_errors = [e for e in result.errors if "yaml" in e.message.lower()]
            assert len(yaml_errors) > 0


class TestLinkChecker:
    """Test link checking functionality following SRP."""
    
    @pytest.fixture
    def link_checker(self):
        """Create link checker for testing."""
        return LinkChecker()
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML with various link types."""
        return """
        <html>
        <body>
            <a href="./installation.html">Installation</a>
            <a href="/api/reference.html">API Reference</a>
            <a href="https://example.com">External Link</a>
            <a href="mailto:support@beginnings.dev">Email</a>
            <a href="./nonexistent.html">Broken Link</a>
        </body>
        </html>
        """
    
    def test_link_checker_initialization(self, link_checker):
        """Test link checker initializes correctly."""
        assert link_checker is not None
        assert hasattr(link_checker, 'check_links')
        assert hasattr(link_checker, 'check_internal_links')
        assert hasattr(link_checker, 'check_external_links')
        assert hasattr(link_checker, 'validate_anchors')
    
    @pytest.mark.asyncio
    async def test_check_internal_links(self, link_checker, tmp_path):
        """Test internal link checking."""
        # Create test files
        (tmp_path / "installation.html").write_text("<html><body>Installation</body></html>")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "reference.html").write_text("<html><body>API</body></html>")
        
        html_file = tmp_path / "index.html"
        html_file.write_text("""
        <html>
        <body>
            <a href="./installation.html">Installation</a>
            <a href="./api/reference.html">API Reference</a>
            <a href="./nonexistent.html">Broken Link</a>
        </body>
        </html>
        """)
        
        result = await link_checker.check_internal_links(html_file)
        
        assert isinstance(result, LinkCheckResult)
        assert result.total_links_checked >= 3
        assert result.valid_links >= 2
        assert result.broken_links >= 1
        
        # Check specific link statuses
        broken_links = [link for link in result.link_details if link.status == LinkStatus.BROKEN]
        assert any("nonexistent.html" in link.url for link in broken_links)
    
    @pytest.mark.asyncio
    async def test_check_external_links(self, link_checker):
        """Test external link checking."""
        external_links = [
            "https://httpbin.org/status/200",  # Should be valid
            "https://httpbin.org/status/404",  # Should be broken
            "https://this-domain-does-not-exist-12345.com"  # Should fail
        ]
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock responses
            async def mock_response(url):
                mock_resp = AsyncMock()
                if "200" in url:
                    mock_resp.status = 200
                elif "404" in url:
                    mock_resp.status = 404
                else:
                    raise aiohttp.ClientError("Connection failed")
                return mock_resp
            
            mock_get.side_effect = mock_response
            
            result = await link_checker.check_external_links(external_links)
            
            assert result.total_links_checked == 3
            assert result.valid_links >= 1
            assert result.broken_links >= 2
    
    def test_validate_anchors(self, link_checker):
        """Test anchor link validation."""
        html_content = """
        <html>
        <body>
            <h1 id="installation">Installation</h1>
            <h2 id="requirements">Requirements</h2>
            <a href="#installation">Go to Installation</a>
            <a href="#nonexistent">Broken Anchor</a>
        </body>
        </html>
        """
        
        result = link_checker.validate_anchors(html_content)
        
        assert result.total_anchors_checked >= 2
        assert result.valid_anchors >= 1
        assert result.broken_anchors >= 1
        
        broken_anchors = [anchor for anchor in result.anchor_details if anchor.status == LinkStatus.BROKEN]
        assert any("nonexistent" in anchor.target for anchor in broken_anchors)
    
    @pytest.mark.asyncio
    async def test_comprehensive_link_check(self, link_checker, tmp_path):
        """Test comprehensive link checking for entire site."""
        # Create test site structure
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.html").write_text("""
        <html>
        <body>
            <a href="./guide.html">Guide</a>
            <a href="https://example.com">External</a>
            <a href="#section1">Section 1</a>
            <h2 id="section1">Section 1</h2>
        </body>
        </html>
        """)
        (tmp_path / "docs" / "guide.html").write_text("<html><body>Guide</body></html>")
        
        result = await link_checker.check_links(tmp_path / "docs")
        
        assert result.success is True
        assert result.total_links_checked > 0
        assert result.total_files_checked >= 2
        
        # Should have summary by link type
        assert "internal_links" in result.summary
        assert "external_links" in result.summary
        assert "anchor_links" in result.summary


class TestExampleTester:
    """Test code example testing following SRP."""
    
    @pytest.fixture
    def example_tester(self):
        """Create example tester for testing."""
        return ExampleTester()
    
    @pytest.fixture
    def code_examples(self):
        """Sample code examples from documentation."""
        return [
            CodeExample(
                id="basic_app",
                language="python",
                code="""
from beginnings import create_app

app = create_app()

@app.route("/")
def home():
    return "Hello World"
""",
                expected_output=None,
                file_path="getting-started.md"
            ),
            CodeExample(
                id="config_example",
                language="yaml",
                code="""
app:
  name: my-app
  debug: true
extensions:
  - beginnings.extensions.auth:AuthExtension
""",
                expected_output=None,
                file_path="configuration.md"
            ),
            CodeExample(
                id="invalid_code",
                language="python",
                code="""
# This has syntax error
print("Hello World"  # Missing closing parenthesis
""",
                expected_output=None,
                file_path="broken.md"
            )
        ]
    
    def test_example_tester_initialization(self, example_tester):
        """Test example tester initializes correctly."""
        assert example_tester is not None
        assert hasattr(example_tester, 'test_example')
        assert hasattr(example_tester, 'test_all_examples')
        assert hasattr(example_tester, 'validate_syntax')
        assert hasattr(example_tester, 'extract_examples')
    
    def test_validate_python_syntax(self, example_tester, code_examples):
        """Test Python syntax validation."""
        # Valid Python code
        valid_example = code_examples[0]
        result = example_tester.validate_syntax(valid_example)
        
        assert isinstance(result, TestResult)
        assert result.success is True
        assert len(result.errors) == 0
        
        # Invalid Python code
        invalid_example = code_examples[2]
        result = example_tester.validate_syntax(invalid_example)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert any("syntax" in error.lower() for error in result.errors)
    
    def test_validate_yaml_syntax(self, example_tester, code_examples):
        """Test YAML syntax validation."""
        yaml_example = code_examples[1]
        result = example_tester.validate_syntax(yaml_example)
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_test_code_execution(self, example_tester, code_examples):
        """Test code execution in sandbox."""
        python_example = code_examples[0]
        
        # Mock execution environment
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Code executed successfully"
            mock_run.return_value.stderr = ""
            
            result = example_tester.test_example(python_example)
            
            assert result.success is True
            assert result.execution_time > 0
    
    def test_extract_examples_from_markdown(self, example_tester):
        """Test extracting code examples from markdown."""
        markdown_content = """
# Example Documentation

Here's a Python example:

```python
print("Hello World")
```

And a YAML example:

```yaml
app:
  name: test
```

Some bash commands:

```bash
pip install beginnings
```
"""
        
        examples = example_tester.extract_examples(markdown_content, "test.md")
        
        assert len(examples) == 3
        assert examples[0].language == "python"
        assert examples[1].language == "yaml" 
        assert examples[2].language == "bash"
        assert "Hello World" in examples[0].code
    
    def test_test_all_examples(self, example_tester, code_examples):
        """Test testing all examples in batch."""
        with patch.object(example_tester, 'test_example') as mock_test:
            # Mock successful tests
            mock_test.side_effect = [
                TestResult(success=True, example_id="basic_app"),
                TestResult(success=True, example_id="config_example"),
                TestResult(success=False, example_id="invalid_code", errors=["Syntax error"])
            ]
            
            result = example_tester.test_all_examples(code_examples)
            
            assert result.total_examples == 3
            assert result.successful_examples == 2
            assert result.failed_examples == 1
            assert len(result.failures) == 1


class TestAccessibilityChecker:
    """Test accessibility validation following SRP."""
    
    @pytest.fixture
    def accessibility_checker(self):
        """Create accessibility checker for testing."""
        return AccessibilityChecker()
    
    @pytest.fixture
    def sample_html_good(self):
        """Sample HTML with good accessibility."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Accessible Page</title>
        </head>
        <body>
            <main>
                <h1>Main Heading</h1>
                <img src="image.jpg" alt="Descriptive alt text">
                <a href="https://example.com" aria-label="Visit example website">Link</a>
                <button type="button">Accessible Button</button>
            </main>
        </body>
        </html>
        """
    
    @pytest.fixture
    def sample_html_bad(self):
        """Sample HTML with accessibility issues."""
        return """
        <html>
        <head>
            <title></title>
        </head>
        <body>
            <div>
                <div>Not a proper heading</div>
                <img src="image.jpg">
                <a href="https://example.com">Click here</a>
                <div onclick="doSomething()">Fake button</div>
            </div>
        </body>
        </html>
        """
    
    def test_accessibility_checker_initialization(self, accessibility_checker):
        """Test accessibility checker initializes correctly."""
        assert accessibility_checker is not None
        assert hasattr(accessibility_checker, 'check_accessibility')
        assert hasattr(accessibility_checker, 'check_semantic_html')
        assert hasattr(accessibility_checker, 'check_alt_text')
        assert hasattr(accessibility_checker, 'check_color_contrast')
    
    def test_check_semantic_html(self, accessibility_checker, sample_html_good, sample_html_bad):
        """Test semantic HTML validation."""
        # Good HTML
        result_good = accessibility_checker.check_semantic_html(sample_html_good)
        assert isinstance(result_good, AccessibilityResult)
        assert result_good.level >= AccessibilityLevel.AA
        
        # Bad HTML
        result_bad = accessibility_checker.check_semantic_html(sample_html_bad)
        assert result_bad.level < AccessibilityLevel.AA
        assert len(result_bad.violations) > 0
        
        # Should detect missing semantic elements
        semantic_violations = [v for v in result_bad.violations if "semantic" in v.description.lower()]
        assert len(semantic_violations) > 0
    
    def test_check_alt_text(self, accessibility_checker, sample_html_bad):
        """Test alt text validation."""
        result = accessibility_checker.check_alt_text(sample_html_bad)
        
        assert len(result.violations) > 0
        
        # Should detect missing alt text
        alt_violations = [v for v in result.violations if "alt" in v.description.lower()]
        assert len(alt_violations) > 0
    
    def test_check_heading_structure(self, accessibility_checker):
        """Test heading structure validation."""
        html_bad_headings = """
        <html>
        <body>
            <h3>Wrong level - should start with h1</h3>
            <h1>Main heading in wrong order</h1>
            <h4>Skips h2 and h3</h4>
        </body>
        </html>
        """
        
        result = accessibility_checker.check_accessibility(html_bad_headings)
        
        heading_violations = [v for v in result.violations if "heading" in v.description.lower()]
        assert len(heading_violations) > 0
    
    def test_check_color_contrast(self, accessibility_checker):
        """Test color contrast validation."""
        html_with_styles = """
        <html>
        <head>
            <style>
                .low-contrast { color: #ccc; background: #fff; }
                .good-contrast { color: #000; background: #fff; }
            </style>
        </head>
        <body>
            <p class="low-contrast">Hard to read text</p>
            <p class="good-contrast">Easy to read text</p>
        </body>
        </html>
        """
        
        result = accessibility_checker.check_color_contrast(html_with_styles)
        
        # Should detect low contrast issues
        contrast_violations = [v for v in result.violations if "contrast" in v.description.lower()]
        assert len(contrast_violations) > 0
    
    def test_comprehensive_accessibility_check(self, accessibility_checker, sample_html_good):
        """Test comprehensive accessibility checking."""
        result = accessibility_checker.check_accessibility(
            sample_html_good,
            level=AccessibilityLevel.AAA  # Strict checking
        )
        
        assert isinstance(result, AccessibilityResult)
        assert result.total_checks > 0
        assert result.score >= 80  # Should score well
        
        # Should include summary by category
        assert "semantic_html" in result.summary
        assert "images" in result.summary
        assert "links" in result.summary
        assert "forms" in result.summary if "form" in sample_html_good else True