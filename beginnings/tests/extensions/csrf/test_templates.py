"""
Tests for CSRF template integration.

This module tests template function registration, hidden form field injection,
and meta tag token embedding features.
"""

import pytest
from unittest.mock import MagicMock, patch

from beginnings.extensions.csrf.extension import CSRFExtension
from beginnings.extensions.csrf.templates import CSRFTemplateIntegration


class TestCSRFTemplateIntegration:
    """Test CSRF template integration functionality."""
    
    def test_csrf_template_integration_initialization(self):
        """Test CSRF template integration initializes correctly."""
        config = {
            "template_integration": {
                "enabled": True,
                "template_function_name": "csrf_token",
                "form_field_name": "csrf_token",
                "meta_tag_name": "csrf-token"
            }
        }
        
        integration = CSRFTemplateIntegration(config)
        
        assert integration.enabled is True
        assert integration.template_function_name == "csrf_token"
        assert integration.form_field_name == "csrf_token"
        assert integration.meta_tag_name == "csrf-token"
    
    def test_csrf_template_integration_disabled(self):
        """Test CSRF template integration when disabled."""
        config = {
            "template_integration": {
                "enabled": False
            }
        }
        
        integration = CSRFTemplateIntegration(config)
        
        assert integration.enabled is False
    
    def test_csrf_template_integration_default_config(self):
        """Test CSRF template integration with default configuration."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Should have sensible defaults
        assert integration.enabled is True
        assert integration.template_function_name == "csrf_token"
        assert integration.form_field_name == "csrf_token"
        assert integration.meta_tag_name == "csrf-token"
    
    def test_generate_hidden_field(self):
        """Test generation of hidden CSRF field HTML."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        token = "test-csrf-token"
        field_html = integration.generate_hidden_field(token)
        
        expected = '<input type="hidden" name="csrf_token" value="test-csrf-token">'
        assert field_html == expected
    
    def test_generate_hidden_field_custom_name(self):
        """Test generation of hidden field with custom name."""
        config = {
            "template_integration": {
                "form_field_name": "custom_csrf"
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        token = "test-csrf-token"
        field_html = integration.generate_hidden_field(token)
        
        expected = '<input type="hidden" name="custom_csrf" value="test-csrf-token">'
        assert field_html == expected
    
    def test_generate_meta_tag(self):
        """Test generation of CSRF meta tag HTML."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        token = "test-csrf-token"
        meta_html = integration.generate_meta_tag(token)
        
        expected = '<meta name="csrf-token" content="test-csrf-token">'
        assert meta_html == expected
    
    def test_generate_meta_tag_custom_name(self):
        """Test generation of meta tag with custom name."""
        config = {
            "template_integration": {
                "meta_tag_name": "custom-csrf-token"
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        token = "test-csrf-token"
        meta_html = integration.generate_meta_tag(token)
        
        expected = '<meta name="custom-csrf-token" content="test-csrf-token">'
        assert meta_html == expected
    
    def test_create_template_function(self):
        """Test creation of template function."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Create template function
        csrf_token_func = integration.create_template_function(token_manager)
        
        # Test function returns token
        token = csrf_token_func()
        assert token == "test-csrf-token"
        
        # Verify token manager was called
        token_manager.generate_token.assert_called_once()
    
    def test_create_template_function_with_request_context(self):
        """Test template function with request context."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Mock request context
        request = MagicMock()
        
        # Create template function with request context
        csrf_token_func = integration.create_template_function(token_manager, request)
        
        # Test function returns token
        token = csrf_token_func()
        assert token == "test-csrf-token"
        
        # Verify token manager was called with request
        token_manager.generate_token.assert_called_once_with(request)
    
    def test_create_hidden_field_function(self):
        """Test creation of hidden field template function."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Create hidden field function
        csrf_field_func = integration.create_hidden_field_function(token_manager)
        
        # Test function returns HTML
        field_html = csrf_field_func()
        expected = '<input type="hidden" name="csrf_token" value="test-csrf-token">'
        assert field_html == expected
    
    def test_create_meta_tag_function(self):
        """Test creation of meta tag template function."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Create meta tag function
        csrf_meta_func = integration.create_meta_tag_function(token_manager)
        
        # Test function returns HTML
        meta_html = csrf_meta_func()
        expected = '<meta name="csrf-token" content="test-csrf-token">'
        assert meta_html == expected
    
    def test_register_with_jinja2(self):
        """Test registration with Jinja2 template engine."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock Jinja2 environment
        jinja_env = MagicMock()
        jinja_env.globals = {}
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Register with Jinja2
        integration.register_with_jinja2(jinja_env, token_manager)
        
        # Verify functions were registered
        assert "csrf_token" in jinja_env.globals
        assert "csrf_field" in jinja_env.globals
        assert "csrf_meta" in jinja_env.globals
        
        # Test registered functions work
        csrf_token_func = jinja_env.globals["csrf_token"]
        assert csrf_token_func() == "test-csrf-token"
        
        csrf_field_func = jinja_env.globals["csrf_field"]
        expected_field = '<input type="hidden" name="csrf_token" value="test-csrf-token">'
        assert csrf_field_func() == expected_field
        
        csrf_meta_func = jinja_env.globals["csrf_meta"]
        expected_meta = '<meta name="csrf-token" content="test-csrf-token">'
        assert csrf_meta_func() == expected_meta
    
    def test_register_with_custom_template_engine(self):
        """Test registration with custom template engine."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock custom template engine
        template_engine = MagicMock()
        template_engine.globals = {}
        
        # Mock token manager
        token_manager = MagicMock()
        
        # Register with custom engine
        functions = integration.get_template_functions(token_manager)
        
        # Verify functions dictionary structure
        assert "csrf_token" in functions
        assert "csrf_field" in functions
        assert "csrf_meta" in functions
        assert callable(functions["csrf_token"])
        assert callable(functions["csrf_field"])
        assert callable(functions["csrf_meta"])
    
    def test_inject_into_response_context(self):
        """Test injection of CSRF data into response context."""
        config = {}
        integration = CSRFTemplateIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "test-csrf-token"
        
        # Mock response context
        context = {}
        
        # Inject CSRF data
        integration.inject_into_context(context, token_manager)
        
        # Verify context contains CSRF data
        assert "csrf_token" in context
        assert context["csrf_token"] == "test-csrf-token"
        
        assert "csrf_field" in context
        expected_field = '<input type="hidden" name="csrf_token" value="test-csrf-token">'
        assert context["csrf_field"] == expected_field
        
        assert "csrf_meta" in context
        expected_meta = '<meta name="csrf-token" content="test-csrf-token">'
        assert context["csrf_meta"] == expected_meta
    
    def test_auto_inject_forms(self):
        """Test automatic injection of CSRF tokens into forms."""
        config = {
            "template_integration": {
                "auto_inject_forms": True
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        # Mock HTML with form
        html_content = '''
        <html>
        <body>
            <form method="post" action="/submit">
                <input type="text" name="username">
                <input type="password" name="password">
                <button type="submit">Submit</button>
            </form>
        </body>
        </html>
        '''
        
        token = "test-csrf-token"
        
        # Process HTML
        processed_html = integration.inject_csrf_into_forms(html_content, token)
        
        # Verify CSRF field was injected
        expected_field = '<input type="hidden" name="csrf_token" value="test-csrf-token">'
        assert expected_field in processed_html
        
        # Verify original content is preserved
        assert '<input type="text" name="username">' in processed_html
        assert '<button type="submit">Submit</button>' in processed_html
    
    def test_auto_inject_forms_disabled(self):
        """Test automatic form injection when disabled."""
        config = {
            "template_integration": {
                "auto_inject_forms": False
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        html_content = '<form method="post"><input type="text"></form>'
        token = "test-csrf-token"
        
        # Process HTML (should not modify)
        processed_html = integration.inject_csrf_into_forms(html_content, token)
        
        # Verify no CSRF field was injected
        assert 'name="csrf_token"' not in processed_html
        assert processed_html == html_content
    
    def test_skip_get_forms(self):
        """Test that GET forms are skipped for CSRF injection."""
        config = {
            "template_integration": {
                "auto_inject_forms": True
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        # HTML with GET form
        html_content = '''
        <form method="get" action="/search">
            <input type="text" name="query">
            <button type="submit">Search</button>
        </form>
        '''
        
        token = "test-csrf-token"
        
        # Process HTML
        processed_html = integration.inject_csrf_into_forms(html_content, token)
        
        # Verify CSRF field was NOT injected into GET form
        assert 'name="csrf_token"' not in processed_html
        assert processed_html == html_content
    
    def test_multiple_forms_injection(self):
        """Test CSRF injection into multiple forms."""
        config = {
            "template_integration": {
                "auto_inject_forms": True
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        # HTML with multiple POST forms
        html_content = '''
        <form method="post" action="/login">
            <input type="text" name="username">
        </form>
        <form method="POST" action="/register">
            <input type="email" name="email">
        </form>
        '''
        
        token = "test-csrf-token"
        
        # Process HTML
        processed_html = integration.inject_csrf_into_forms(html_content, token)
        
        # Count CSRF field occurrences
        csrf_field_count = processed_html.count('name="csrf_token"')
        assert csrf_field_count == 2
    
    def test_validate_config_valid(self):
        """Test template integration configuration validation."""
        config = {
            "template_integration": {
                "enabled": True,
                "template_function_name": "csrf_token",
                "form_field_name": "csrf_token",
                "meta_tag_name": "csrf-token"
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        errors = integration.validate_config()
        assert errors == []
    
    def test_validate_config_empty_function_name(self):
        """Test validation with empty function name."""
        config = {
            "template_integration": {
                "template_function_name": ""  # Empty function name
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        errors = integration.validate_config()
        assert len(errors) > 0
        assert any("template_function_name" in error for error in errors)
    
    def test_validate_config_invalid_field_name(self):
        """Test validation with invalid field name."""
        config = {
            "template_integration": {
                "form_field_name": "invalid-field-name!"  # Invalid characters
            }
        }
        integration = CSRFTemplateIntegration(config)
        
        errors = integration.validate_config()
        assert len(errors) > 0
        assert any("form_field_name" in error for error in errors)