"""Static site generator for documentation website.

This module provides static site generation with theme support,
optimization, and Progressive Web App features. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import shutil
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from enum import Enum

try:
    import markdown
except ImportError:
    markdown = None

try:
    from jinja2 import Environment, FileSystemLoader, Template
except ImportError:
    Environment = FileSystemLoader = Template = None


class BuildStatus(Enum):
    """Build status for site generation."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class PageMetadata:
    """Metadata for a documentation page."""
    
    title: str
    description: str = ""
    author: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    category: str = ""
    template: str = "page.html"
    sidebar_position: Optional[int] = None
    is_draft: bool = False
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedPage:
    """Represents a generated documentation page."""
    
    source_path: Path
    output_path: Path
    metadata: PageMetadata
    content: str = ""
    toc: List[Dict[str, Any]] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: int = 0
    last_modified: Optional[datetime] = None


@dataclass
class BuildResult:
    """Result of site generation."""
    
    success: bool
    status: BuildStatus = BuildStatus.SUCCESS
    pages_generated: int = 0
    assets_copied: int = 0
    build_time_seconds: float = 0
    output_directory: Optional[Path] = None
    pages: List[GeneratedPage] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    size_bytes: int = 0


class MarkdownProcessor:
    """Processes Markdown content to HTML.
    
    Follows Single Responsibility Principle - only handles Markdown processing.
    """
    
    def __init__(self):
        """Initialize Markdown processor."""
        self.extensions = [
            'toc',
            'codehilite',
            'fenced_code',
            'tables',
            'footnotes',
            'attr_list',
            'def_list'
        ]
        
        if markdown is not None:
            self.md = markdown.Markdown(
                extensions=self.extensions,
                extension_configs={
                    'toc': {'title': 'Table of Contents'},
                    'codehilite': {'css_class': 'highlight'}
                }
            )
        else:
            self.md = None
    
    def process_markdown(self, content: str, metadata: PageMetadata) -> str:
        """Process Markdown content to HTML.
        
        Args:
            content: Markdown content
            metadata: Page metadata
            
        Returns:
            Processed HTML content
        """
        if self.md is None:
            # Fallback basic processing
            return self._basic_markdown_processing(content)
        
        try:
            html = self.md.convert(content)
            
            # Extract table of contents if available
            if hasattr(self.md, 'toc_tokens'):
                metadata.custom_fields['toc'] = self.md.toc_tokens
            
            # Reset markdown instance for next use
            self.md.reset()
            
            return html
        except Exception:
            return self._basic_markdown_processing(content)
    
    def _basic_markdown_processing(self, content: str) -> str:
        """Basic Markdown processing without dependencies."""
        # Very basic Markdown-to-HTML conversion
        lines = content.split('\n')
        html_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('```'):
                html_lines.append('<pre><code>')
            elif line == '':
                html_lines.append('<br>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        return '\n'.join(html_lines)
    
    def extract_metadata(self, content: str) -> tuple[str, Dict[str, Any]]:
        """Extract frontmatter metadata from Markdown.
        
        Args:
            content: Markdown content with optional frontmatter
            
        Returns:
            Tuple of (content without frontmatter, metadata dict)
        """
        lines = content.split('\n')
        
        if len(lines) > 0 and lines[0].strip() == '---':
            # Find end of frontmatter
            end_idx = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_idx = i
                    break
            
            if end_idx:
                frontmatter = '\n'.join(lines[1:end_idx])
                content_without_frontmatter = '\n'.join(lines[end_idx + 1:])
                
                try:
                    import yaml
                    metadata = yaml.safe_load(frontmatter) or {}
                except ImportError:
                    # Parse basic key-value pairs
                    metadata = self._parse_simple_frontmatter(frontmatter)
                
                return content_without_frontmatter, metadata
        
        return content, {}
    
    def _parse_simple_frontmatter(self, frontmatter: str) -> Dict[str, Any]:
        """Parse simple key-value frontmatter without YAML."""
        metadata = {}
        
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Try to parse common types
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.startswith('[') and value.endswith(']'):
                    # Simple list parsing
                    value = [item.strip().strip('\'"') for item in value[1:-1].split(',')]
                
                metadata[key] = value
        
        return metadata


class TemplateRenderer:
    """Renders pages using templates.
    
    Follows Single Responsibility Principle - only handles template rendering.
    """
    
    def __init__(self, theme_directory: Optional[Path] = None):
        """Initialize template renderer.
        
        Args:
            theme_directory: Directory containing templates
        """
        self.theme_directory = theme_directory
        self.env = None
        
        if Environment and FileSystemLoader and theme_directory:
            try:
                loader = FileSystemLoader(str(theme_directory))
                self.env = Environment(loader=loader, autoescape=True)
            except Exception:
                self.env = None
    
    def render_page(
        self, 
        page: GeneratedPage, 
        site_config: Dict[str, Any],
        navigation: List[Dict[str, Any]]
    ) -> str:
        """Render page using template.
        
        Args:
            page: Generated page data
            site_config: Site-wide configuration
            navigation: Navigation structure
            
        Returns:
            Rendered HTML content
        """
        if self.env:
            try:
                template = self.env.get_template(page.metadata.template)
                
                context = {
                    'page': page,
                    'site': site_config,
                    'navigation': navigation,
                    'current_year': datetime.now().year,
                    'build_time': datetime.now(timezone.utc).isoformat()
                }
                
                return template.render(context)
            except Exception:
                return self._render_basic_template(page, site_config)
        
        return self._render_basic_template(page, site_config)
    
    def _render_basic_template(self, page: GeneratedPage, site_config: Dict[str, Any]) -> str:
        """Render page with basic template."""
        site_title = site_config.get('title', 'Documentation')
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{page.metadata.title} - {site_title}</title>
            <meta name="description" content="{page.metadata.description}">
        </head>
        <body>
            <header>
                <h1>{site_title}</h1>
            </header>
            <main>
                <article>
                    <h1>{page.metadata.title}</h1>
                    {page.content}
                </article>
            </main>
            <footer>
                <p>&copy; {datetime.now().year} {site_title}</p>
            </footer>
        </body>
        </html>
        """


class AssetOptimizer:
    """Optimizes static assets.
    
    Follows Single Responsibility Principle - only handles asset optimization.
    """
    
    def __init__(self):
        """Initialize asset optimizer."""
        self.supported_formats = {'.css', '.js', '.png', '.jpg', '.jpeg', '.svg'}
    
    def optimize_assets(self, assets_dir: Path, output_dir: Path) -> int:
        """Optimize and copy assets.
        
        Args:
            assets_dir: Source assets directory
            output_dir: Destination directory
            
        Returns:
            Number of assets processed
        """
        if not assets_dir.exists():
            return 0
        
        assets_copied = 0
        output_assets_dir = output_dir / "assets"
        output_assets_dir.mkdir(exist_ok=True)
        
        for asset_file in assets_dir.rglob('*'):
            if asset_file.is_file() and asset_file.suffix in self.supported_formats:
                relative_path = asset_file.relative_to(assets_dir)
                output_path = output_assets_dir / relative_path
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy and optionally optimize
                if asset_file.suffix == '.css':
                    self._optimize_css(asset_file, output_path)
                elif asset_file.suffix == '.js':
                    self._optimize_js(asset_file, output_path)
                else:
                    shutil.copy2(asset_file, output_path)
                
                assets_copied += 1
        
        return assets_copied
    
    def _optimize_css(self, input_path: Path, output_path: Path) -> None:
        """Basic CSS optimization."""
        content = input_path.read_text(encoding='utf-8')
        
        # Basic minification - remove comments and extra whitespace
        import re
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        output_path.write_text(content, encoding='utf-8')
    
    def _optimize_js(self, input_path: Path, output_path: Path) -> None:
        """Basic JavaScript optimization."""
        content = input_path.read_text(encoding='utf-8')
        
        # Basic minification - remove comments and extra whitespace
        import re
        content = re.sub(r'//.*?\n', '\n', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        output_path.write_text(content, encoding='utf-8')


class StaticSiteGenerator:
    """Generates static documentation website.
    
    Follows Single Responsibility Principle - orchestrates site generation.
    Uses Dependency Inversion - depends on processor and renderer abstractions.
    """
    
    def __init__(
        self, 
        content_directory: Path,
        output_directory: Path,
        theme_directory: Optional[Path] = None
    ):
        """Initialize static site generator.
        
        Args:
            content_directory: Directory containing source content
            output_directory: Directory for generated site
            theme_directory: Directory containing templates and themes
        """
        self.content_directory = Path(content_directory)
        self.output_directory = Path(output_directory)
        self.theme_directory = Path(theme_directory) if theme_directory else None
        
        self.markdown_processor = MarkdownProcessor()
        self.template_renderer = TemplateRenderer(self.theme_directory)
        self.asset_optimizer = AssetOptimizer()
        
        self.site_config = {}
        self.navigation = []
        self.generated_pages = []
    
    def load_site_config(self, config_path: Optional[Path] = None) -> None:
        """Load site configuration.
        
        Args:
            config_path: Path to configuration file
        """
        if config_path is None:
            config_path = self.content_directory / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.site_config = json.load(f)
            except Exception:
                self.site_config = {}
        
        # Set defaults
        self.site_config.setdefault('title', 'Documentation')
        self.site_config.setdefault('description', 'Generated documentation')
        self.site_config.setdefault('base_url', '/')
        self.site_config.setdefault('theme', 'default')
    
    def generate_site(self) -> BuildResult:
        """Generate complete static site.
        
        Returns:
            Build result with generation statistics
        """
        import time
        start_time = time.time()
        
        result = BuildResult(
            success=True,
            output_directory=self.output_directory
        )
        
        try:
            # Load configuration
            self.load_site_config()
            
            # Prepare output directory
            self.output_directory.mkdir(parents=True, exist_ok=True)
            
            # Generate pages
            markdown_files = list(self.content_directory.rglob('*.md'))
            
            for md_file in markdown_files:
                try:
                    page = self._process_markdown_file(md_file)
                    if page and not page.metadata.is_draft:
                        self.generated_pages.append(page)
                        result.pages_generated += 1
                except Exception as e:
                    result.errors.append(f"Error processing {md_file}: {str(e)}")
            
            # Build navigation
            self._build_navigation()
            
            # Render pages
            for page in self.generated_pages:
                try:
                    self._render_and_save_page(page)
                except Exception as e:
                    result.errors.append(f"Error rendering {page.source_path}: {str(e)}")
            
            # Copy and optimize assets
            assets_dir = self.content_directory / "assets"
            if assets_dir.exists():
                result.assets_copied = self.asset_optimizer.optimize_assets(
                    assets_dir, self.output_directory
                )
            
            # Generate additional files
            self._generate_sitemap()
            self._generate_search_index()
            
            # Calculate build statistics
            result.build_time_seconds = time.time() - start_time
            result.pages = self.generated_pages
            result.size_bytes = self._calculate_output_size()
            
            if result.errors:
                result.status = BuildStatus.PARTIAL if result.pages_generated > 0 else BuildStatus.ERROR
                result.success = len(result.errors) < len(markdown_files) / 2  # Allow some errors
            
        except Exception as e:
            result.success = False
            result.status = BuildStatus.ERROR
            result.errors.append(f"Build failed: {str(e)}")
            result.build_time_seconds = time.time() - start_time
        
        return result
    
    def _process_markdown_file(self, md_file: Path) -> Optional[GeneratedPage]:
        """Process single Markdown file."""
        try:
            content = md_file.read_text(encoding='utf-8')
            
            # Extract metadata
            content_without_frontmatter, frontmatter_data = self.markdown_processor.extract_metadata(content)
            
            # Create page metadata
            metadata = PageMetadata(
                title=frontmatter_data.get('title', md_file.stem.replace('-', ' ').title()),
                description=frontmatter_data.get('description', ''),
                author=frontmatter_data.get('author', ''),
                tags=frontmatter_data.get('tags', []),
                category=frontmatter_data.get('category', ''),
                template=frontmatter_data.get('template', 'page.html'),
                sidebar_position=frontmatter_data.get('sidebar_position'),
                is_draft=frontmatter_data.get('draft', False)
            )
            
            # Process Markdown to HTML
            html_content = self.markdown_processor.process_markdown(content_without_frontmatter, metadata)
            
            # Calculate reading stats
            word_count = len(content_without_frontmatter.split())
            reading_time = max(1, word_count // 200)  # ~200 words per minute
            
            # Determine output path
            relative_path = md_file.relative_to(self.content_directory)
            output_path = self.output_directory / relative_path.with_suffix('.html')
            
            return GeneratedPage(
                source_path=md_file,
                output_path=output_path,
                metadata=metadata,
                content=html_content,
                word_count=word_count,
                reading_time_minutes=reading_time,
                last_modified=datetime.fromtimestamp(md_file.stat().st_mtime, timezone.utc)
            )
            
        except Exception:
            return None
    
    def _build_navigation(self) -> None:
        """Build navigation structure from pages."""
        navigation = []
        
        # Group pages by category
        categories = {}
        for page in self.generated_pages:
            category = page.metadata.category or 'General'
            if category not in categories:
                categories[category] = []
            categories[category].append(page)
        
        # Sort categories and pages
        for category, pages in categories.items():
            pages.sort(key=lambda p: (p.metadata.sidebar_position or 999, p.metadata.title))
            
            navigation.append({
                'title': category,
                'pages': [{
                    'title': page.metadata.title,
                    'url': str(page.output_path.relative_to(self.output_directory)),
                    'description': page.metadata.description
                } for page in pages]
            })
        
        self.navigation = navigation
    
    def _render_and_save_page(self, page: GeneratedPage) -> None:
        """Render and save individual page."""
        # Ensure output directory exists
        page.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render page
        rendered_html = self.template_renderer.render_page(
            page, self.site_config, self.navigation
        )
        
        # Save rendered page
        page.output_path.write_text(rendered_html, encoding='utf-8')
    
    def _generate_sitemap(self) -> None:
        """Generate XML sitemap."""
        base_url = self.site_config.get('base_url', '/')
        if not base_url.endswith('/'):
            base_url += '/'
        
        sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        for page in self.generated_pages:
            url_path = str(page.output_path.relative_to(self.output_directory))
            last_mod = page.last_modified.strftime('%Y-%m-%d') if page.last_modified else ''
            
            sitemap_xml.extend([
                '  <url>',
                f'    <loc>{base_url}{url_path}</loc>',
                f'    <lastmod>{last_mod}</lastmod>' if last_mod else '',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>'
            ])
        
        sitemap_xml.append('</urlset>')
        
        sitemap_path = self.output_directory / 'sitemap.xml'
        sitemap_path.write_text('\n'.join(filter(None, sitemap_xml)), encoding='utf-8')
    
    def _generate_search_index(self) -> None:
        """Generate search index for client-side search."""
        search_index = []
        
        for page in self.generated_pages:
            # Extract text content (simplified)
            import re
            text_content = re.sub(r'<[^>]+>', '', page.content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            search_index.append({
                'title': page.metadata.title,
                'description': page.metadata.description,
                'url': str(page.output_path.relative_to(self.output_directory)),
                'content': text_content[:500],  # Truncate for index size
                'tags': page.metadata.tags,
                'category': page.metadata.category
            })
        
        search_index_path = self.output_directory / 'search-index.json'
        with open(search_index_path, 'w', encoding='utf-8') as f:
            json.dump(search_index, f, indent=2)
    
    def _calculate_output_size(self) -> int:
        """Calculate total size of generated output."""
        total_size = 0
        
        for file_path in self.output_directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def clean_output(self) -> bool:
        """Clean output directory.
        
        Returns:
            True if cleaned successfully
        """
        try:
            if self.output_directory.exists():
                shutil.rmtree(self.output_directory)
            return True
        except Exception:
            return False
    
    def get_page_by_path(self, path: str) -> Optional[GeneratedPage]:
        """Get page by source path.
        
        Args:
            path: Source file path
            
        Returns:
            Generated page or None
        """
        for page in self.generated_pages:
            if str(page.source_path).endswith(path):
                return page
        return None