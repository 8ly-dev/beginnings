"""
Template engine integration hooks for CSRF protection.

Provides robust template integration that works with various template engines.
"""

from typing import Any, Dict, Protocol
from html import escape


class TemplateEngine(Protocol):
    """Protocol for template engine integration."""
    
    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable/function to template context."""
        ...
    
    def get_template(self, name: str) -> Any:
        """Get a template by name."""
        ...


class CSRFTemplateHooks:
    """CSRF template integration hooks."""
    
    def __init__(self, csrf_extension):
        self.csrf_extension = csrf_extension
        self._registered_engines = {}
    
    def register_template_engine(self, name: str, engine: TemplateEngine):
        """Register a template engine for CSRF integration."""
        self._registered_engines[name] = engine
        
        # Add CSRF functions to template globals
        self._add_csrf_functions(engine)
    
    def _add_csrf_functions(self, engine: TemplateEngine):
        """Add CSRF functions to template engine."""
        try:
            # Add CSRF token function
            engine.add_global(
                self.csrf_extension.template_function_name,
                self._create_token_function()
            )
            
            # Add CSRF form field function
            engine.add_global(
                "csrf_form_field",
                self._create_form_field_function()
            )
            
            # Add CSRF meta tag function
            engine.add_global(
                "csrf_meta_tag",
                self._create_meta_tag_function()
            )
        except AttributeError:
            # Engine doesn't support add_global, skip
            pass
    
    def _create_token_function(self):
        """Create CSRF token function for templates."""
        def csrf_token(request=None):
            if request:
                return self.csrf_extension.get_csrf_token_for_template(request)
            return ""
        return csrf_token
    
    def _create_form_field_function(self):
        """Create CSRF form field function for templates."""
        def csrf_form_field(request=None):
            if request:
                token = self.csrf_extension.get_csrf_token_for_template(request)
                field_name = escape(self.csrf_extension.form_field_name)
                token_value = escape(token)
                return f'<input type="hidden" name="{field_name}" value="{token_value}">'
            return ""
        return csrf_form_field
    
    def _create_meta_tag_function(self):
        """Create CSRF meta tag function for templates."""
        def csrf_meta_tag(request=None):
            if request:
                token = self.csrf_extension.get_csrf_token_for_template(request)
                tag_name = escape(self.csrf_extension.meta_tag_name)
                token_value = escape(token)
                return f'<meta name="{tag_name}" content="{token_value}">'
            return ""
        return csrf_meta_tag
    
    def inject_into_jinja2(self, jinja_env):
        """Specific integration for Jinja2 templates."""
        try:
            # Add functions to Jinja2 globals
            jinja_env.globals[self.csrf_extension.template_function_name] = self._create_token_function()
            jinja_env.globals["csrf_form_field"] = self._create_form_field_function()
            jinja_env.globals["csrf_meta_tag"] = self._create_meta_tag_function()
            
            # Add convenience filter
            def csrf_token_filter(request):
                return self.csrf_extension.get_csrf_token_for_template(request)
            
            jinja_env.filters["csrf_token"] = csrf_token_filter
            
        except Exception:
            # Jinja2 not available or error in setup
            pass
    
    def create_template_context(self, request) -> Dict[str, Any]:
        """Create template context with CSRF functions."""
        return {
            self.csrf_extension.template_function_name: lambda: self.csrf_extension.get_csrf_token_for_template(request),
            "csrf_form_field": lambda: self.csrf_extension.create_csrf_form_field(request),
            "csrf_meta_tag": lambda: self.csrf_extension.create_csrf_meta_tag(request),
        }
    
    def auto_inject_forms(self, html_content: str, request) -> str:
        """Automatically inject CSRF tokens into forms."""
        if not html_content or "<form" not in html_content:
            return html_content
        
        token = self.csrf_extension.get_csrf_token_for_template(request)
        field_name = escape(self.csrf_extension.form_field_name)
        token_value = escape(token)
        csrf_field = f'<input type="hidden" name="{field_name}" value="{token_value}">'
        
        # Find and inject into forms that don't already have CSRF protection
        import re
        
        def inject_csrf(match):
            form_tag = match.group(0)
            form_content = match.group(1) if match.lastindex else ""
            
            # Skip if form already has CSRF token
            if field_name in form_content or "csrf" in form_content.lower():
                return form_tag
            
            # Skip if form is GET method
            if 'method="get"' in form_tag.lower() or "method='get'" in form_tag.lower():
                return form_tag
            
            # Inject CSRF field after opening form tag
            if form_content:
                return form_tag.replace(form_content, f"{csrf_field}\n{form_content}", 1)
            else:
                return form_tag + csrf_field
        
        # Pattern to match form tags and their content
        pattern = r'<form[^>]*>([^<]*(?:<(?!/form>)[^<]*)*)'
        html_content = re.sub(pattern, inject_csrf, html_content, flags=re.IGNORECASE)
        
        return html_content