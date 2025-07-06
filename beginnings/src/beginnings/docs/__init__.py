"""Documentation generation system for Beginnings framework.

This module provides comprehensive documentation generation tools for:
- API documentation from code annotations
- Configuration documentation
- Extension documentation
- Deployment guides
- Tutorial generation
- Interactive documentation with live examples
- Progressive Web App documentation sites
- Search functionality

The documentation system supports:
- Multiple output formats (HTML, Markdown, PDF)
- Interactive documentation with examples
- Auto-updating from code changes
- Cross-referencing and linking
- Custom themes and templates
- Progressive Web App features
- Offline support
- Fast search indexing
- Real-time configuration editing
- Code playground with security sandbox
- Tutorial progress tracking
"""

from .generator import DocumentationGenerator, DocumentationConfig, OutputFormat, DocumentationLevel
from .parsers import CodeParser, ConfigParser, ExtensionParser
from .renderers import HTMLRenderer, MarkdownRenderer, PDFRenderer
from .extractors import APIExtractor, RouteExtractor, ExtensionExtractor
from .templates import TemplateEngine, ThemeManager
from .utils import DocumentationUtils

# Interactive components
from .interactive import (
    InteractiveConfigEditor,
    ConfigEditorResult,
    ValidationResult,
    CodePlayground,
    PlaygroundResult,
    ExecutionContext,
    TutorialProgressTracker,
    ProgressResult,
    CompletionStatus
)

# Website generation
from .website import (
    StaticSiteGenerator,
    BuildResult,
    GeneratedPage,
    PWAManager,
    PWAConfig,
    ThemeManager as WebsiteThemeManager,
    ThemeConfig
)

# Search functionality
from .search import (
    DocumentationSearchEngine,
    SearchDocument,
    SearchResult,
    SearchQuery,
    SearchResponse
)

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
    
    # Interactive components
    'InteractiveConfigEditor',
    'ConfigEditorResult',
    'ValidationResult',
    'CodePlayground',
    'PlaygroundResult',
    'ExecutionContext',
    'TutorialProgressTracker',
    'ProgressResult',
    'CompletionStatus',
    
    # Website generation
    'StaticSiteGenerator',
    'BuildResult',
    'GeneratedPage',
    'PWAManager',
    'PWAConfig',
    'WebsiteThemeManager',
    'ThemeConfig',
    
    # Search functionality
    'DocumentationSearchEngine',
    'SearchDocument',
    'SearchResult',
    'SearchQuery',
    'SearchResponse',
]