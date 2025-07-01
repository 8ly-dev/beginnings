"""Template engine for project scaffolding."""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, BaseLoader, meta
import yaml

def title_filter(s):
    """Custom title filter that handles underscores properly."""
    return s.replace('_', ' ').title().replace(' ', '')

from ..utils.colors import info, success
from ..utils.progress import ProgressBar
from .security import generate_secure_defaults, show_security_summary


class TemplateEngine:
    """Jinja2-based template engine for project generation."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template engine.
        
        Args:
            template_dir: Custom template directory path
        """
        self.template_dir = template_dir or self._get_default_template_dir()
        self.env = Environment(loader=BaseLoader())
        self.env.filters['title'] = title_filter
    
    def _get_default_template_dir(self) -> str:
        """Get default template directory."""
        return os.path.join(os.path.dirname(__file__), "project_templates")
    
    def _get_extension_template_dir(self) -> str:
        """Get extension template directory."""
        return os.path.join(os.path.dirname(__file__), "extension_templates")
    
    def generate_project(
        self,
        template_name: str,
        project_path: str,
        context: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> None:
        """Generate project from template.
        
        Args:
            template_name: Name of template to use
            project_path: Path where project will be created
            context: Template context variables
            progress_callback: Optional progress callback function
        """
        template_path = os.path.join(self.template_dir, template_name)
        
        if not os.path.exists(template_path):
            raise ValueError(f"Template '{template_name}' not found at {template_path}")
        
        # Get all files to process
        files_to_process = self._get_template_files(template_path)
        
        if progress_callback:
            progress_callback(f"Processing {len(files_to_process)} template files...")
        
        with ProgressBar(len(files_to_process), "Generating files") as progress:
            for template_file in files_to_process:
                self._process_template_file(
                    template_file,
                    template_path,
                    project_path,
                    context
                )
                progress.update(1)
    
    def _get_template_files(self, template_path: str) -> List[str]:
        """Get list of template files to process."""
        files = []
        for root, dirs, filenames in os.walk(template_path):
            # Skip __pycache__ and .git directories
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__'))]
            
            for filename in filenames:
                # Include .env.example and .gitignore but skip other dot files and pyc files
                if (not filename.startswith('.') or filename in ['.env.example', '.gitignore']) and not filename.endswith('.pyc'):
                    rel_path = os.path.relpath(os.path.join(root, filename), template_path)
                    files.append(rel_path)
        
        return files
    
    def _process_template_file(
        self,
        rel_path: str,
        template_path: str,
        project_path: str,
        context: Dict[str, Any]
    ) -> None:
        """Process a single template file."""
        # Check if file should be conditionally included first
        if not self._should_include_file(rel_path, context):
            return
            
        source_path = os.path.join(template_path, rel_path)
        
        # Process path template variables
        processed_rel_path = self._render_template_string(rel_path, context)
        target_path = os.path.join(project_path, processed_rel_path)
        
        # Create target directory
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Process file content
        if self._is_template_file(source_path):
            self._render_template_file(source_path, target_path, context)
        else:
            # Copy binary files as-is
            shutil.copy2(source_path, target_path)
    
    def _should_include_file(self, rel_path: str, context: Dict[str, Any]) -> bool:
        """Check if file should be included based on context."""
        # Extension-specific files (check auth first to avoid duplicates)
        if rel_path.startswith("templates/auth") and not context.get("include_auth", False):
            return False
            
        if "dashboard.html" in rel_path and not context.get("include_auth", False):
            return False
        
        # Route files
        if "routes/api.py" in rel_path and not context.get("include_api", False):
            return False
        
        if "routes/html.py" in rel_path and not context.get("include_html", False):
            return False
        
        # Configuration files
        if "config/app.staging.yaml" in rel_path and not context.get("include_staging_config", False):
            return False
        
        # HTML-specific templates for API-only apps
        if not context.get("include_html", False):
            html_only_templates = [
                "templates/index.html",
                "templates/about.html", 
                "templates/dashboard.html",
                "templates/base.html"
            ]
            if any(template in rel_path for template in html_only_templates):
                return False
        
        return True
    
    def _is_template_file(self, file_path: str) -> bool:
        """Check if file should be processed as template."""
        # Process text files as templates
        text_extensions = {
            '.py', '.yaml', '.yml', '.md', '.txt', '.toml', 
            '.html', '.css', '.js', '.json', '.cfg', '.ini'
        }
        
        # Special files that should be processed as templates
        template_files = {'.env.example', '.gitignore', 'Dockerfile', 'Makefile'}
        
        filename = os.path.basename(file_path)
        _, ext = os.path.splitext(file_path)
        
        return ext.lower() in text_extensions or filename in template_files
    
    def _render_template_file(
        self,
        source_path: str,
        target_path: str,
        context: Dict[str, Any]
    ) -> None:
        """Render template file with context."""
        with open(source_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        rendered_content = self._render_template_string(template_content, context)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
    
    def _render_template_string(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render template string with context."""
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            # If template rendering fails, return original string
            return template_str
    
    def get_template_variables(self, template_name: str) -> List[str]:
        """Get list of variables used in template."""
        template_path = os.path.join(self.template_dir, template_name)
        variables = set()
        
        for root, dirs, files in os.walk(template_path):
            for file in files:
                if self._is_template_file(os.path.join(root, file)):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        ast = self.env.parse(content)
                        file_vars = meta.find_undeclared_variables(ast)
                        variables.update(file_vars)
                    except Exception:
                        # Skip files that can't be parsed
                        continue
        
        return sorted(list(variables))
    
    def render_template(self, template_name: str, **context) -> str:
        """Render a single template with context.
        
        Args:
            template_name: Name of template file to render
            **context: Template context variables
            
        Returns:
            Rendered template content
        """
        # Check extension templates first
        extension_template_path = os.path.join(self._get_extension_template_dir(), template_name)
        if os.path.exists(extension_template_path):
            with open(extension_template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        else:
            # Fall back to project templates
            project_template_path = os.path.join(self.template_dir, template_name)
            if os.path.exists(project_template_path):
                with open(project_template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            else:
                raise ValueError(f"Template '{template_name}' not found")
        
        return self._render_template_string(template_content, context)


def create_template_context(
    project_name: str,
    template_config: Dict[str, Any],
    user_selections: Dict[str, Any]
) -> Dict[str, Any]:
    """Create template context from project info and user selections.
    
    Args:
        project_name: Name of the project
        template_config: Template configuration
        user_selections: User's feature selections
        
    Returns:
        Template context dictionary
    """
    # Base context
    context = {
        "project_name": project_name,
        "project_name_snake": project_name.replace("-", "_"),
        "project_name_title": project_name.replace("-", " ").title(),
    }
    
    # Add template configuration
    context.update(template_config.get("context", {}))
    
    # Add user selections
    context.update(user_selections)
    
    # Generate secure defaults
    security_defaults = generate_secure_defaults(user_selections)
    context["security_defaults"] = security_defaults
    
    # Generate extension list
    extensions = []
    if user_selections.get("include_auth", False):
        extensions.append("beginnings.extensions.auth:AuthExtension")
    if user_selections.get("include_csrf", False):
        extensions.append("beginnings.extensions.csrf:CSRFExtension")
    if user_selections.get("include_rate_limiting", False):
        extensions.append("beginnings.extensions.rate_limiting:RateLimitExtension")
    if user_selections.get("include_security_headers", False):
        extensions.append("beginnings.extensions.security_headers:SecurityHeadersExtension")
    
    context["extensions"] = extensions
    context["has_extensions"] = len(extensions) > 0
    
    # Router configuration
    routers = {}
    if user_selections.get("include_html", True):
        routers["html"] = {
            "prefix": "",
            "default_response_class": "HTMLResponse"
        }
    if user_selections.get("include_api", False):
        routers["api"] = {
            "prefix": "/api",
            "default_response_class": "JSONResponse"
        }
    
    context["routers"] = routers
    
    return context