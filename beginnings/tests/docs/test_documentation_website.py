"""Tests for documentation website generation.

This module tests the static site generation, PWA features, and website
functionality of the documentation system. Following TDD methodology.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Import the interfaces we'll implement (TDD - interfaces defined by tests)
from beginnings.docs.website.static_generator import (
    StaticSiteGenerator,
    BuildResult,
    PageMetadata
)
from beginnings.docs.website.pwa_manager import (
    PWAManager,
    PWAGenerationResult,
    ServiceWorkerConfig
)
from beginnings.docs.website.theme_manager import (
    ThemeManager,
    ThemeApplicationResult,
    ThemeConfig
)
from beginnings.docs.search.search_engine import (
    DocumentationSearchEngine,
    SearchResult,
    SearchQuery
)


class TestStaticSiteGenerator:
    """Test static site generator following SRP."""
    
    @pytest.fixture
    def site_generator(self, tmp_path):
        """Create static site generator for testing."""
        content_dir = tmp_path / "content"
        output_dir = tmp_path / "output"
        content_dir.mkdir()
        output_dir.mkdir()
        return StaticSiteGenerator(content_dir, output_dir)
    
    @pytest.fixture
    def site_config(self):
        """Sample site configuration."""
        return SiteConfig(
            title="Beginnings Documentation",
            base_url="https://docs.beginnings.dev",
            output_dir="dist",
            theme="default",
            enable_search=True,
            enable_pwa=True,
            languages=["en"],
            sections=[
                {"name": "getting-started", "title": "Getting Started"},
                {"name": "user-guide", "title": "User Guide"},
                {"name": "api-reference", "title": "API Reference"}
            ]
        )
    
    @pytest.fixture
    def sample_content(self, tmp_path):
        """Create sample content files for testing."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        
        # Create markdown files
        (content_dir / "index.md").write_text("""
# Welcome to Beginnings

Beginnings is a modern web framework for Python.

## Features

- Configuration-driven development
- Built-in security
- Extension system
""")
        
        (content_dir / "installation.md").write_text("""
# Installation

Install beginnings using pip:

```bash
pip install beginnings
```

## Requirements

- Python 3.8+
- Modern web browser
""")
        
        return content_dir
    
    def test_generator_initialization(self, site_generator):
        """Test site generator initializes correctly."""
        assert site_generator is not None
        assert hasattr(site_generator, 'generate_site')
        assert hasattr(site_generator, 'load_site_config')
        assert hasattr(site_generator, 'clean_output')
        assert hasattr(site_generator, 'get_page_by_path')
    
    def test_generate_site(self, site_generator, site_config, sample_content):
        """Test complete site generation."""
        result = site_generator.generate_site(site_config, sample_content)
        
        assert isinstance(result, GenerationResult)
        assert result.success is True
        assert result.pages_generated > 0
        assert result.assets_processed > 0
        assert result.output_path is not None
        
        # Check generated files exist
        output_path = Path(result.output_path)
        assert (output_path / "index.html").exists()
        assert (output_path / "installation.html").exists()
        assert (output_path / "assets").exists()
    
    def test_process_markdown_content(self, site_generator, sample_content):
        """Test markdown processing with code highlighting."""
        markdown_file = sample_content / "installation.md"
        
        result = site_generator.process_content(markdown_file)
        
        assert result.success is True
        assert "html_content" in result.data
        assert "metadata" in result.data
        
        html_content = result.data["html_content"]
        assert "<h1>Installation</h1>" in html_content
        assert "<code>pip install beginnings</code>" in html_content
        assert "language-bash" in html_content  # Code highlighting
    
    def test_build_navigation(self, site_generator, site_config, sample_content):
        """Test navigation structure generation."""
        result = site_generator.build_navigation(site_config, sample_content)
        
        assert result.success is True
        assert "navigation" in result.data
        assert "breadcrumbs" in result.data
        
        navigation = result.data["navigation"]
        assert len(navigation) >= 2  # At least index and installation
        assert any(item["title"] == "Installation" for item in navigation)
    
    def test_optimize_assets(self, site_generator, tmp_path):
        """Test asset optimization (CSS, JS, images)."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        
        # Create sample assets
        (assets_dir / "style.css").write_text("""
/* Sample CSS */
.container {
    margin: 0 auto;
    padding: 20px;
}
""")
        
        (assets_dir / "app.js").write_text("""
// Sample JavaScript
console.log('Documentation loaded');
""")
        
        result = site_generator.optimize_assets(assets_dir)
        
        assert result.success is True
        assert result.optimized_files > 0
        assert result.size_reduction_percent > 0
    
    def test_responsive_generation(self, site_generator, site_config, sample_content):
        """Test responsive HTML generation for mobile."""
        site_config.mobile_optimized = True
        
        result = site_generator.generate_site(site_config, sample_content)
        
        assert result.success is True
        
        # Check mobile-friendly features
        index_file = Path(result.output_path) / "index.html"
        html_content = index_file.read_text()
        
        assert 'viewport' in html_content
        assert 'responsive' in html_content or 'mobile' in html_content
        assert 'media-query' in html_content or '@media' in html_content


class TestPWAManager:
    """Test Progressive Web App features following SRP."""
    
    @pytest.fixture
    def pwa_manager(self):
        """Create PWA manager for testing."""
        return PWAManager()
    
    @pytest.fixture
    def service_worker_config(self):
        """Sample service worker configuration."""
        return ServiceWorkerConfig(
            cache_strategy="cache_first",
            cache_version="v1",
            static_assets=["/css/", "/js/", "/images/"],
            dynamic_routes=["/api/search"],
            offline_page="/offline.html"
        )
    
    def test_pwa_manager_initialization(self, pwa_manager):
        """Test PWA manager initializes correctly."""
        assert pwa_manager is not None
        assert hasattr(pwa_manager, 'generate_manifest')
        assert hasattr(pwa_manager, 'generate_service_worker')
        assert hasattr(pwa_manager, 'enable_offline_support')
    
    def test_generate_web_app_manifest(self, pwa_manager):
        """Test web app manifest generation."""
        manifest_config = {
            "name": "Beginnings Documentation",
            "short_name": "Beginnings Docs",
            "description": "Documentation for the Beginnings framework",
            "start_url": "/",
            "display": "standalone",
            "theme_color": "#2563eb",
            "background_color": "#ffffff"
        }
        
        result = pwa_manager.generate_manifest(manifest_config)
        
        assert isinstance(result, PWAResult)
        assert result.success is True
        assert "manifest_json" in result.data
        
        manifest = json.loads(result.data["manifest_json"])
        assert manifest["name"] == "Beginnings Documentation"
        assert manifest["display"] == "standalone"
        assert "icons" in manifest
    
    def test_generate_service_worker(self, pwa_manager, service_worker_config):
        """Test service worker generation for offline support."""
        result = pwa_manager.generate_service_worker(service_worker_config)
        
        assert isinstance(result, PWAResult)
        assert result.success is True
        assert "service_worker_js" in result.data
        
        service_worker = result.data["service_worker_js"]
        assert "cache_first" in service_worker.lower()
        assert "install" in service_worker
        assert "fetch" in service_worker
        assert "/css/" in service_worker  # Static assets cached
    
    def test_enable_offline_support(self, pwa_manager, tmp_path):
        """Test offline support implementation."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        
        # Create sample HTML files
        (site_dir / "index.html").write_text("<html><body>Home</body></html>")
        (site_dir / "about.html").write_text("<html><body>About</body></html>")
        
        result = pwa_manager.enable_offline_support(site_dir)
        
        assert result.success is True
        assert "cached_pages" in result.data
        assert len(result.data["cached_pages"]) >= 2
        
        # Check offline page created
        assert (site_dir / "offline.html").exists()
    
    def test_pwa_validation(self, pwa_manager):
        """Test PWA requirements validation."""
        pwa_config = {
            "has_manifest": True,
            "has_service_worker": True,
            "is_https": True,
            "responsive_design": True,
            "offline_support": True
        }
        
        result = pwa_manager.validate_pwa_requirements(pwa_config)
        
        assert result.success is True
        assert result.data["pwa_score"] >= 90
        assert result.data["requirements_met"] == 5


class TestThemeManager:
    """Test theme management following OCP (Open/Closed Principle)."""
    
    @pytest.fixture
    def theme_manager(self):
        """Create theme manager for testing."""
        return ThemeManager()
    
    @pytest.fixture
    def default_theme(self):
        """Default theme configuration."""
        return Theme(
            name="default",
            display_name="Default Theme",
            css_files=["main.css", "components.css"],
            js_files=["app.js"],
            templates_dir="templates/default",
            colors={
                "primary": "#2563eb",
                "secondary": "#64748b",
                "background": "#ffffff",
                "text": "#1e293b"
            },
            fonts={
                "heading": "Inter, sans-serif",
                "body": "Inter, sans-serif",
                "code": "JetBrains Mono, monospace"
            }
        )
    
    def test_theme_manager_initialization(self, theme_manager):
        """Test theme manager initializes correctly."""
        assert theme_manager is not None
        assert hasattr(theme_manager, 'load_theme')
        assert hasattr(theme_manager, 'apply_theme')
        assert hasattr(theme_manager, 'customize_theme')
        assert hasattr(theme_manager, 'validate_theme')
    
    def test_load_default_theme(self, theme_manager, default_theme):
        """Test loading default theme."""
        result = theme_manager.load_theme("default")
        
        assert isinstance(result, ThemeResult)
        assert result.success is True
        assert result.theme.name == "default"
        assert len(result.theme.css_files) > 0
        assert "primary" in result.theme.colors
    
    def test_apply_theme_to_site(self, theme_manager, default_theme, tmp_path):
        """Test applying theme to generated site."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        
        # Create sample HTML file
        (site_dir / "index.html").write_text("""
        <html>
        <head><title>Test</title></head>
        <body><h1>{{title}}</h1></body>
        </html>
        """)
        
        result = theme_manager.apply_theme(default_theme, site_dir)
        
        assert result.success is True
        assert result.files_modified > 0
        
        # Check theme assets were copied
        assert (site_dir / "assets" / "css").exists()
        assert (site_dir / "assets" / "js").exists()
    
    def test_customize_theme(self, theme_manager, default_theme):
        """Test theme customization."""
        customizations = {
            "colors": {
                "primary": "#dc2626",  # Red instead of blue
                "background": "#f8fafc"
            },
            "fonts": {
                "heading": "Poppins, sans-serif"
            }
        }
        
        result = theme_manager.customize_theme(default_theme, customizations)
        
        assert result.success is True
        assert result.theme.colors["primary"] == "#dc2626"
        assert result.theme.fonts["heading"] == "Poppins, sans-serif"
        # Other properties should remain unchanged
        assert result.theme.colors["secondary"] == "#64748b"
    
    def test_validate_theme(self, theme_manager):
        """Test theme validation."""
        # Valid theme
        valid_theme = Theme(
            name="valid",
            display_name="Valid Theme",
            css_files=["main.css"],
            js_files=["app.js"],
            templates_dir="templates/valid"
        )
        
        result = theme_manager.validate_theme(valid_theme)
        assert result.success is True
        assert len(result.validation_errors) == 0
        
        # Invalid theme
        invalid_theme = Theme(
            name="",  # Empty name
            display_name="Invalid Theme",
            css_files=[],  # No CSS files
            js_files=None,  # Invalid JS files
            templates_dir=""  # Empty templates dir
        )
        
        result = theme_manager.validate_theme(invalid_theme)
        assert result.success is False
        assert len(result.validation_errors) > 0
    
    def test_theme_extensibility(self, theme_manager):
        """Test theme system is extensible (OCP)."""
        # Custom theme that extends default
        custom_theme = Theme(
            name="custom",
            display_name="Custom Theme",
            extends="default",
            css_files=["main.css", "custom.css"],
            js_files=["app.js", "custom.js"],
            templates_dir="templates/custom"
        )
        
        result = theme_manager.load_theme("custom", custom_theme)
        
        assert result.success is True
        assert result.theme.extends == "default"
        assert "custom.css" in result.theme.css_files


class TestDocumentationSearchEngine:
    """Test documentation search functionality following SRP."""
    
    @pytest.fixture
    def search_engine(self):
        """Create search engine for testing."""
        return DocumentationSearchEngine()
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for search indexing."""
        return [
            {
                "id": "installation",
                "title": "Installation Guide",
                "content": "Install beginnings using pip install beginnings. Python 3.8+ required.",
                "url": "/installation/",
                "section": "getting-started"
            },
            {
                "id": "configuration",
                "title": "Configuration System",
                "content": "Beginnings uses YAML configuration files. Configure app settings, extensions, and routing.",
                "url": "/user-guide/configuration/",
                "section": "user-guide"
            },
            {
                "id": "api-routes",
                "title": "API Routes",
                "content": "Create API routes using the APIRouter class. Supports REST endpoints and OpenAPI documentation.",
                "url": "/api-reference/routes/",
                "section": "api-reference"
            }
        ]
    
    def test_search_engine_initialization(self, search_engine):
        """Test search engine initializes correctly."""
        assert search_engine is not None
        assert hasattr(search_engine, 'index_documents')
        assert hasattr(search_engine, 'search')
        assert hasattr(search_engine, 'build_index')
        assert hasattr(search_engine, 'update_index')
    
    def test_build_search_index(self, search_engine, sample_documents):
        """Test search index building."""
        result = search_engine.build_index(sample_documents)
        
        assert isinstance(result, SearchResult)
        assert result.success is True
        assert result.documents_indexed == len(sample_documents)
        assert result.index_size > 0
    
    def test_search_functionality(self, search_engine, sample_documents):
        """Test search functionality."""
        # Build index first
        search_engine.build_index(sample_documents)
        
        # Test search
        search_result = search_engine.search("configuration YAML")
        
        assert search_result.success is True
        assert len(search_result.results) > 0
        
        # Should find configuration document
        config_result = search_result.results[0]
        assert "configuration" in config_result["title"].lower()
        assert config_result["score"] > 0
    
    def test_search_ranking(self, search_engine, sample_documents):
        """Test search result ranking."""
        # Build index
        search_engine.build_index(sample_documents)
        
        # Search for "API"
        search_result = search_engine.search("API")
        
        assert search_result.success is True
        assert len(search_result.results) > 0
        
        # Results should be ranked by relevance
        results = search_result.results
        assert results[0]["score"] >= results[-1]["score"]
        
        # API Routes document should rank highly for "API" search
        assert "api" in results[0]["title"].lower()
    
    def test_faceted_search(self, search_engine, sample_documents):
        """Test search with facets/filters."""
        # Build index
        search_engine.build_index(sample_documents)
        
        # Search with section filter
        search_result = search_engine.search("guide", filters={"section": "user-guide"})
        
        assert search_result.success is True
        assert len(search_result.results) > 0
        
        # All results should be from user-guide section
        for result in search_result.results:
            assert result["section"] == "user-guide"
    
    def test_search_suggestions(self, search_engine, sample_documents):
        """Test search suggestions for typos."""
        # Build index
        search_engine.build_index(sample_documents)
        
        # Search with typo
        search_result = search_engine.search("instalation")  # Missing 'l'
        
        assert search_result.success is True
        
        # Should provide suggestions
        if "suggestions" in search_result.data:
            suggestions = search_result.data["suggestions"]
            assert "installation" in [s.lower() for s in suggestions]
    
    def test_update_search_index(self, search_engine, sample_documents):
        """Test incremental index updates."""
        # Build initial index
        search_engine.build_index(sample_documents)
        
        # Add new document
        new_document = {
            "id": "deployment",
            "title": "Deployment Guide",
            "content": "Deploy your beginnings application to production using Docker or cloud platforms.",
            "url": "/deployment/",
            "section": "getting-started"
        }
        
        result = search_engine.update_index([new_document])
        
        assert result.success is True
        assert result.documents_indexed == 1
        
        # Search should find new document
        search_result = search_engine.search("deployment")
        assert search_result.success is True
        assert len(search_result.results) > 0
        assert "deployment" in search_result.results[0]["title"].lower()