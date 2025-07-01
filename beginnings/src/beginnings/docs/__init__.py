"""Documentation generation system for Beginnings framework.

This module provides comprehensive documentation generation tools for:
- API documentation from code annotations
- Configuration documentation
- Extension documentation
- Deployment guides
- Tutorial generation

The documentation system supports:
- Multiple output formats (HTML, Markdown, PDF)
- Interactive documentation with examples
- Auto-updating from code changes
- Cross-referencing and linking
- Custom themes and templates
"""

from .generator import DocumentationGenerator, DocumentationConfig, OutputFormat, DocumentationLevel
from .parsers import CodeParser, ConfigParser, ExtensionParser
from .renderers import HTMLRenderer, MarkdownRenderer, PDFRenderer
from .extractors import APIExtractor, RouteExtractor, ExtensionExtractor
from .templates import TemplateEngine, ThemeManager
from .utils import DocumentationUtils

__all__ = [
    # Core classes
    'DocumentationGenerator',
    'DocumentationConfig',
    'OutputFormat',
    'DocumentationLevel',
    
    # Parsers
    'CodeParser',
    'ConfigParser', 
    'ExtensionParser',
    
    # Renderers
    'HTMLRenderer',
    'MarkdownRenderer',
    'PDFRenderer',
    
    # Extractors
    'APIExtractor',
    'RouteExtractor',
    'ExtensionExtractor',
    
    # Templates and themes
    'TemplateEngine',
    'ThemeManager',
    
    # Utilities
    'DocumentationUtils',
]