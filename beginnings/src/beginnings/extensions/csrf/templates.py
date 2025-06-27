"""
CSRF template integration for Beginnings framework.

This module provides template integration capabilities including
automatic form token injection, meta tag embedding, and template
function registration for various template engines.
"""

import re
from typing import Any, Callable
from html import escape


class CSRFTemplateIntegration:
    """
    CSRF template integration manager.
    
    Handles template function registration, form token injection,
    and meta tag generation for CSRF protection.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CSRF template integration.
        
        Args:
            config: CSRF configuration dictionary
        """
        template_config = config.get("template_integration", {})
        
        self.enabled = template_config.get("enabled", True)
        self.template_function_name = template_config.get("template_function_name", "csrf_token")
        self.form_field_name = template_config.get("form_field_name", "csrf_token")
        self.meta_tag_name = template_config.get("meta_tag_name", "csrf-token")
        self.auto_inject_forms = template_config.get("auto_inject_forms", True)
    
    def generate_hidden_field(self, token: str) -> str:
        """
        Generate hidden input field HTML for CSRF token.
        
        Args:
            token: CSRF token value
            
        Returns:
            HTML string for hidden input field
        """
        escaped_token = escape(token)
        return f'<input type="hidden" name="{self.form_field_name}" value="{escaped_token}">'
    
    def generate_meta_tag(self, token: str) -> str:
        """
        Generate meta tag HTML for CSRF token.
        
        Args:
            token: CSRF token value
            
        Returns:
            HTML string for meta tag
        """
        escaped_token = escape(token)
        return f'<meta name="{self.meta_tag_name}" content="{escaped_token}">'
    
    def create_template_function(
        self, 
        token_manager: Any, 
        request: Any = None
    ) -> Callable[[], str]:
        """
        Create template function for token generation.
        
        Args:
            token_manager: CSRF token manager instance
            request: Optional request context
            
        Returns:
            Function that returns CSRF token
        """
        def csrf_token_func() -> str:
            if request:
                return token_manager.generate_token(request)
            else:
                return token_manager.generate_token()
        
        return csrf_token_func
    
    def create_hidden_field_function(
        self, 
        token_manager: Any, 
        request: Any = None
    ) -> Callable[[], str]:
        """
        Create template function for hidden field generation.
        
        Args:
            token_manager: CSRF token manager instance
            request: Optional request context
            
        Returns:
            Function that returns hidden field HTML
        """
        def csrf_field_func() -> str:
            if request:
                token = token_manager.generate_token(request)
            else:
                token = token_manager.generate_token()
            return self.generate_hidden_field(token)
        
        return csrf_field_func
    
    def create_meta_tag_function(
        self, 
        token_manager: Any, 
        request: Any = None
    ) -> Callable[[], str]:
        """
        Create template function for meta tag generation.
        
        Args:
            token_manager: CSRF token manager instance
            request: Optional request context
            
        Returns:
            Function that returns meta tag HTML
        """
        def csrf_meta_func() -> str:
            if request:
                token = token_manager.generate_token(request)
            else:
                token = token_manager.generate_token()
            return self.generate_meta_tag(token)
        
        return csrf_meta_func
    
    def register_with_jinja2(self, jinja_env: Any, token_manager: Any, request: Any = None) -> None:
        """
        Register CSRF functions with Jinja2 environment.
        
        Args:
            jinja_env: Jinja2 environment instance
            token_manager: CSRF token manager instance
            request: Optional request context
        """
        if not self.enabled:
            return
        
        # Register template functions
        jinja_env.globals[self.template_function_name] = self.create_template_function(
            token_manager, request
        )
        jinja_env.globals["csrf_field"] = self.create_hidden_field_function(
            token_manager, request
        )
        jinja_env.globals["csrf_meta"] = self.create_meta_tag_function(
            token_manager, request
        )
    
    def get_template_functions(self, token_manager: Any, request: Any = None) -> dict[str, Callable]:
        """
        Get dictionary of template functions for custom template engines.
        
        Args:
            token_manager: CSRF token manager instance
            request: Optional request context
            
        Returns:
            Dictionary of template function names to callables
        """
        if not self.enabled:
            return {}
        
        return {
            self.template_function_name: self.create_template_function(token_manager, request),
            "csrf_field": self.create_hidden_field_function(token_manager, request),
            "csrf_meta": self.create_meta_tag_function(token_manager, request)
        }
    
    def inject_into_context(self, context: dict[str, Any], token_manager: Any, request: Any = None) -> None:
        """
        Inject CSRF data into template context.
        
        Args:
            context: Template context dictionary to modify
            token_manager: CSRF token manager instance
            request: Optional request context
        """
        if not self.enabled:
            return
        
        # Generate token
        if request:
            token = token_manager.generate_token(request)
        else:
            token = token_manager.generate_token()
        
        # Add CSRF data to context
        context[self.template_function_name] = token
        context["csrf_field"] = self.generate_hidden_field(token)
        context["csrf_meta"] = self.generate_meta_tag(token)
    
    def inject_csrf_into_forms(self, html_content: str, token: str) -> str:
        """
        Automatically inject CSRF tokens into HTML forms.
        
        Args:
            html_content: HTML content to process
            token: CSRF token to inject
            
        Returns:
            Modified HTML with CSRF tokens injected
        """
        if not self.enabled or not self.auto_inject_forms:
            return html_content
        
        # Pattern to match form tags with method="post" (case insensitive)
        form_pattern = re.compile(
            r'<form\s+[^>]*method\s*=\s*["\']?post["\']?[^>]*>',
            re.IGNORECASE
        )
        
        def inject_token(match):
            form_tag = match.group(0)
            # Insert CSRF field after form opening tag
            csrf_field = self.generate_hidden_field(token)
            return f"{form_tag}\n    {csrf_field}"
        
        # Replace all POST forms with CSRF-protected versions
        return form_pattern.sub(inject_token, html_content)
    
    def extract_forms_for_injection(self, html_content: str) -> list[dict[str, Any]]:
        """
        Extract form information for manual CSRF injection.
        
        Args:
            html_content: HTML content to analyze
            
        Returns:
            List of form dictionaries with position and method info
        """
        forms = []
        
        # Pattern to match form tags
        form_pattern = re.compile(
            r'<form\s+([^>]*)>',
            re.IGNORECASE
        )
        
        for match in form_pattern.finditer(html_content):
            attributes = match.group(1)
            method_match = re.search(r'method\s*=\s*["\']?(\w+)["\']?', attributes, re.IGNORECASE)
            method = method_match.group(1).lower() if method_match else "get"
            
            forms.append({
                "start": match.start(),
                "end": match.end(),
                "method": method,
                "attributes": attributes,
                "requires_csrf": method in ["post", "put", "patch", "delete"]
            })
        
        return forms
    
    def validate_config(self) -> list[str]:
        """
        Validate template integration configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not self.enabled:
            return errors
        
        # Validate function name
        if not self.template_function_name or not self.template_function_name.strip():
            errors.append("CSRF template_function_name cannot be empty")
        
        # Validate field name (should be valid HTML attribute name)
        if not self.form_field_name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', self.form_field_name):
            errors.append("CSRF form_field_name must be a valid HTML attribute name")
        
        # Validate meta tag name
        if not self.meta_tag_name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', self.meta_tag_name):
            errors.append("CSRF meta_tag_name must be a valid HTML attribute name")
        
        return errors