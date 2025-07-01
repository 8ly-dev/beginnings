"""Template engine and theme management for documentation generation."""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from abc import ABC, abstractmethod

try:
    from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
except ImportError:
    Environment = FileSystemLoader = Template = TemplateNotFound = None


class TemplateEngine:
    """Template engine for generating documentation."""
    
    def __init__(self, template_dirs: Optional[List[str]] = None):
        """Initialize template engine.
        
        Args:
            template_dirs: List of template directories
        """
        self.template_dirs = template_dirs or []
        self.environment = None
        self.custom_filters = {}
        self.global_context = {}
        
        if Environment and FileSystemLoader:
            self._initialize_jinja_environment()
    
    def _initialize_jinja_environment(self):
        """Initialize Jinja2 environment."""
        # Default template directories
        default_dirs = [
            Path(__file__).parent / "templates",
            Path.cwd() / "templates",
            Path.cwd() / "docs" / "templates"
        ]
        
        # Add user-specified directories
        all_dirs = [str(d) for d in default_dirs if d.exists()] + self.template_dirs
        
        if all_dirs:
            loader = FileSystemLoader(all_dirs)
            self.environment = Environment(
                loader=loader,
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            # Add custom filters
            self._register_default_filters()
    
    def _register_default_filters(self):
        """Register default template filters."""
        if not self.environment:
            return
        
        # Code highlighting filter
        def highlight_code(code: str, language: str = "python") -> str:
            """Highlight code syntax."""
            try:
                from pygments import highlight
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import HtmlFormatter
                
                lexer = get_lexer_by_name(language)
                formatter = HtmlFormatter(cssclass="highlight")
                return highlight(code, lexer, formatter)
            except ImportError:
                return f'<pre><code class="language-{language}">{code}</code></pre>'
        
        # Markdown processing filter
        def markdown_filter(text: str) -> str:
            """Process markdown text."""
            try:
                import markdown
                md = markdown.Markdown(extensions=['codehilite', 'tables', 'toc'])
                return md.convert(text)
            except ImportError:
                return text.replace('\n', '<br>')
        
        # URL generation filter
        def url_for(endpoint: str, **kwargs) -> str:
            """Generate URL for endpoint."""
            if endpoint.startswith('http'):
                return endpoint
            
            # Simple URL generation for documentation
            base_url = kwargs.get('base_url', '')
            if endpoint.endswith('.html'):
                return f"{base_url}/{endpoint}"
            return f"{base_url}/{endpoint}.html"
        
        # Text truncation filter
        def truncate_words(text: str, length: int = 50) -> str:
            """Truncate text to specified word count."""
            words = text.split()
            if len(words) <= length:
                return text
            return ' '.join(words[:length]) + '...'
        
        # Date formatting filter
        def format_date(date_obj, format_string: str = "%Y-%m-%d") -> str:
            """Format date object."""
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime(format_string)
            return str(date_obj)
        
        # Register filters
        self.environment.filters.update({
            'highlight': highlight_code,
            'markdown': markdown_filter,
            'url_for': url_for,
            'truncate_words': truncate_words,
            'format_date': format_date,
            **self.custom_filters
        })
    
    async def render_template(self, template_name: str, **context) -> str:
        """Render template with context.
        
        Args:
            template_name: Name of template file
            **context: Template context variables
            
        Returns:
            Rendered template content
        """
        if not self.environment:
            return self._render_fallback_template(template_name, **context)
        
        try:
            template = self.environment.get_template(template_name)
            
            # Merge global context with local context
            full_context = {**self.global_context, **context}
            
            return template.render(**full_context)
            
        except TemplateNotFound:
            return self._render_fallback_template(template_name, **context)
        except Exception as e:
            return f"<!-- Template rendering error: {e} -->"
    
    def _render_fallback_template(self, template_name: str, **context) -> str:
        """Render fallback template when Jinja2 is not available."""
        # Simple template rendering for basic cases
        if template_name == "index.html":
            return self._render_index_fallback(**context)
        elif template_name.startswith("api_"):
            return self._render_api_fallback(template_name, **context)
        elif template_name.startswith("code_"):
            return self._render_code_fallback(template_name, **context)
        else:
            return self._render_generic_fallback(template_name, **context)
    
    def _render_index_fallback(self, **context) -> str:
        """Render fallback index template."""
        title = context.get('title', 'Documentation')
        project_name = context.get('project_name', 'Project')
        sections = context.get('sections', [])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        h1 {{ color: #333; }}
        .section {{ margin: 1rem 0; padding: 1rem; border: 1px solid #ddd; }}
        .section h3 {{ margin-top: 0; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{project_name} Documentation</h1>
    <div class="sections">
"""
        
        for section in sections:
            html += f"""
        <div class="section">
            <h3><a href="{section.get('url', '#')}">{section.get('name', 'Section')}</a></h3>
            <p>{section.get('description', '')}</p>
        </div>
"""
        
        html += """
    </div>
</body>
</html>"""
        
        return html
    
    def _render_api_fallback(self, template_name: str, **context) -> str:
        """Render fallback API template."""
        title = context.get('title', 'API Documentation')
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        h1, h2, h3 {{ color: #333; }}
        .endpoint {{ margin: 2rem 0; padding: 1rem; border: 1px solid #ddd; }}
        .method {{ background: #007acc; color: white; padding: 0.2rem 0.5rem; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <!-- API documentation content would go here -->
</body>
</html>"""
    
    def _render_code_fallback(self, template_name: str, **context) -> str:
        """Render fallback code documentation template."""
        title = context.get('title', 'Code Documentation')
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        h1, h2, h3 {{ color: #333; }}
        .module {{ margin: 2rem 0; }}
        .class {{ margin: 1rem 0; padding: 1rem; background: #f9f9f9; }}
        .method {{ margin: 0.5rem 0; padding: 0.5rem; background: #ffffff; }}
        code {{ background: #f4f4f4; padding: 0.2rem; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <!-- Code documentation content would go here -->
</body>
</html>"""
    
    def _render_generic_fallback(self, template_name: str, **context) -> str:
        """Render generic fallback template."""
        title = context.get('title', 'Documentation')
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Template: {template_name}</p>
    <!-- Content would go here -->
</body>
</html>"""
    
    def add_filter(self, name: str, filter_func):
        """Add custom template filter.
        
        Args:
            name: Filter name
            filter_func: Filter function
        """
        self.custom_filters[name] = filter_func
        if self.environment:
            self.environment.filters[name] = filter_func
    
    def set_global_context(self, **context):
        """Set global template context variables.
        
        Args:
            **context: Global context variables
        """
        self.global_context.update(context)
    
    def add_template_directory(self, directory: str):
        """Add template directory.
        
        Args:
            directory: Path to template directory
        """
        if directory not in self.template_dirs:
            self.template_dirs.append(directory)
            # Reinitialize environment with new directory
            if Environment and FileSystemLoader:
                self._initialize_jinja_environment()


class ThemeManager:
    """Manager for documentation themes."""
    
    def __init__(self, theme_dirs: Optional[List[str]] = None):
        """Initialize theme manager.
        
        Args:
            theme_dirs: List of theme directories
        """
        self.theme_dirs = theme_dirs or []
        self.themes = {}
        self.current_theme = "default"
        self.custom_css = []
        
        # Default theme directories
        self.default_theme_dirs = [
            Path(__file__).parent / "themes",
            Path.cwd() / "themes",
            Path.cwd() / "docs" / "themes"
        ]
        
        self._load_available_themes()
    
    def _load_available_themes(self):
        """Load available themes from theme directories."""
        all_dirs = [d for d in self.default_theme_dirs if d.exists()] + [Path(d) for d in self.theme_dirs]
        
        for theme_dir in all_dirs:
            if theme_dir.exists():
                for theme_path in theme_dir.iterdir():
                    if theme_path.is_dir():
                        theme_config = self._load_theme_config(theme_path)
                        if theme_config:
                            self.themes[theme_path.name] = {
                                "name": theme_path.name,
                                "path": theme_path,
                                "config": theme_config
                            }
    
    def _load_theme_config(self, theme_path: Path) -> Optional[Dict[str, Any]]:
        """Load theme configuration.
        
        Args:
            theme_path: Path to theme directory
            
        Returns:
            Theme configuration or None
        """
        config_files = [
            theme_path / "theme.json",
            theme_path / "config.json",
            theme_path / "theme.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix == '.json':
                        return json.loads(config_file.read_text(encoding='utf-8'))
                    elif config_file.suffix in ['.yaml', '.yml']:
                        try:
                            import yaml
                            return yaml.safe_load(config_file.read_text(encoding='utf-8'))
                        except ImportError:
                            pass
                except Exception:
                    continue
        
        # Create default config if no config file exists
        return {
            "name": theme_path.name,
            "description": f"Theme: {theme_path.name}",
            "version": "1.0.0",
            "assets": []
        }
    
    async def load_theme(self, theme_name: str) -> bool:
        """Load theme by name.
        
        Args:
            theme_name: Name of theme to load
            
        Returns:
            True if theme loaded successfully
        """
        if theme_name in self.themes:
            self.current_theme = theme_name
            return True
        elif theme_name == "default":
            # Always allow default theme
            self.current_theme = "default"
            return True
        return False
    
    async def get_theme_assets(self, theme_name: Optional[str] = None) -> Dict[str, Union[str, bytes]]:
        """Get theme assets (CSS, JS, images).
        
        Args:
            theme_name: Theme name (uses current theme if None)
            
        Returns:
            Dictionary of asset paths to content
        """
        theme_name = theme_name or self.current_theme
        assets = {}
        
        if theme_name == "default":
            assets.update(self._get_default_theme_assets())
        elif theme_name in self.themes:
            theme_info = self.themes[theme_name]
            theme_path = theme_info["path"]
            
            # Load CSS files
            css_files = list(theme_path.glob("*.css"))
            for css_file in css_files:
                assets[f"css/{css_file.name}"] = css_file.read_text(encoding='utf-8')
            
            # Load JavaScript files
            js_files = list(theme_path.glob("*.js"))
            for js_file in js_files:
                assets[f"js/{js_file.name}"] = js_file.read_text(encoding='utf-8')
            
            # Load image files
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']
            for ext in image_extensions:
                image_files = list(theme_path.glob(f"*{ext}"))
                for image_file in image_files:
                    assets[f"images/{image_file.name}"] = image_file.read_bytes()
        
        return assets
    
    def _get_default_theme_assets(self) -> Dict[str, str]:
        """Get default theme assets."""
        default_css = """
/* Default Documentation Theme */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    margin: 0;
    padding: 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

h1, h2, h3, h4, h5, h6 {
    color: #2c3e50;
    margin-top: 2rem;
    margin-bottom: 1rem;
}

h1 {
    border-bottom: 3px solid #3498db;
    padding-bottom: 0.5rem;
}

h2 {
    border-bottom: 1px solid #bdc3c7;
    padding-bottom: 0.3rem;
}

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.nav {
    background: #34495e;
    color: white;
    padding: 1rem;
}

.nav a {
    color: white;
    margin-right: 2rem;
}

.section {
    margin: 2rem 0;
    padding: 1.5rem;
    border: 1px solid #ecf0f1;
    border-radius: 5px;
}

.endpoint {
    margin: 2rem 0;
    padding: 1rem;
    border-left: 4px solid #3498db;
    background: #f8f9fa;
}

.method {
    display: inline-block;
    padding: 0.2rem 0.5rem;
    border-radius: 3px;
    color: white;
    font-weight: bold;
    margin-right: 0.5rem;
}

.method.get { background: #2ecc71; }
.method.post { background: #f39c12; }
.method.put { background: #9b59b6; }
.method.delete { background: #e74c3c; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

th, td {
    border: 1px solid #bdc3c7;
    padding: 0.75rem;
    text-align: left;
}

th {
    background: #ecf0f1;
    font-weight: bold;
}

code {
    background: #f4f4f4;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-family: 'Monaco', 'Consolas', monospace;
}

pre {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
}

pre code {
    background: none;
    color: inherit;
    padding: 0;
}

.highlight {
    margin: 1rem 0;
}

.footer {
    margin-top: 4rem;
    padding: 2rem;
    border-top: 1px solid #bdc3c7;
    text-align: center;
    color: #7f8c8d;
}

@media (max-width: 768px) {
    .container {
        padding: 1rem;
    }
    
    .nav a {
        margin-right: 1rem;
    }
}
"""
        
        return {
            "css/default.css": default_css
        }
    
    async def add_custom_css(self, css_content: str):
        """Add custom CSS to current theme.
        
        Args:
            css_content: CSS content to add
        """
        self.custom_css.append(css_content)
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names.
        
        Returns:
            List of theme names
        """
        return list(self.themes.keys()) + ["default"]
    
    def get_theme_info(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Get theme information.
        
        Args:
            theme_name: Theme name
            
        Returns:
            Theme information or None
        """
        if theme_name == "default":
            return {
                "name": "default",
                "description": "Default documentation theme",
                "version": "1.0.0"
            }
        return self.themes.get(theme_name, {}).get("config")
    
    def create_theme_from_css(self, theme_name: str, css_content: str, theme_dir: Optional[str] = None) -> bool:
        """Create new theme from CSS content.
        
        Args:
            theme_name: Name for new theme
            css_content: CSS content for theme
            theme_dir: Directory to save theme (optional)
            
        Returns:
            True if theme created successfully
        """
        try:
            if theme_dir:
                theme_path = Path(theme_dir) / theme_name
            else:
                theme_path = Path.cwd() / "themes" / theme_name
            
            theme_path.mkdir(parents=True, exist_ok=True)
            
            # Save CSS file
            css_file = theme_path / f"{theme_name}.css"
            css_file.write_text(css_content, encoding='utf-8')
            
            # Create theme config
            config = {
                "name": theme_name,
                "description": f"Custom theme: {theme_name}",
                "version": "1.0.0",
                "assets": [f"{theme_name}.css"]
            }
            
            config_file = theme_path / "theme.json"
            config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
            
            # Add to available themes
            self.themes[theme_name] = {
                "name": theme_name,
                "path": theme_path,
                "config": config
            }
            
            return True
            
        except Exception:
            return False