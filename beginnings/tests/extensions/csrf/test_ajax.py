"""
Tests for CSRF AJAX and SPA support.

This module tests AJAX token handling, JavaScript integration,
and single-page application token management.
"""

import pytest
from unittest.mock import MagicMock

from beginnings.extensions.csrf.extension import CSRFExtension
from beginnings.extensions.csrf.ajax import CSRFAjaxIntegration


class TestCSRFAjaxIntegration:
    """Test CSRF AJAX integration functionality."""
    
    def test_csrf_ajax_integration_initialization(self):
        """Test CSRF AJAX integration initializes correctly."""
        config = {
            "ajax": {
                "header_name": "X-CSRFToken",
                "cookie_name": "csrftoken",
                "javascript_function": "getCSRFToken"
            }
        }
        
        integration = CSRFAjaxIntegration(config)
        
        assert integration.header_name == "X-CSRFToken"
        assert integration.cookie_name == "csrftoken"
        assert integration.javascript_function == "getCSRFToken"
    
    def test_csrf_ajax_integration_default_config(self):
        """Test CSRF AJAX integration with default configuration."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Should have sensible defaults
        assert integration.header_name == "X-CSRFToken"
        assert integration.cookie_name == "csrftoken"
        assert integration.javascript_function == "getCSRFToken"
    
    def test_generate_javascript_function(self):
        """Test generation of JavaScript CSRF token function."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        token = "test-csrf-token"
        js_code = integration.generate_javascript_function(token)
        
        # Verify JavaScript function is generated
        assert "function getCSRFToken()" in js_code
        assert "return 'test-csrf-token'" in js_code
        
        # Verify meta tag extraction function
        assert "document.querySelector('meta[name=\"csrf-token\"]')" in js_code
    
    def test_generate_javascript_function_custom_name(self):
        """Test JavaScript function generation with custom name."""
        config = {
            "ajax": {
                "javascript_function": "getCsrfToken"
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        token = "test-csrf-token"
        js_code = integration.generate_javascript_function(token)
        
        assert "function getCsrfToken()" in js_code
    
    def test_generate_cookie_setting_code(self):
        """Test generation of cookie setting JavaScript code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        token = "test-csrf-token"
        js_code = integration.generate_cookie_setting_code(token)
        
        # Verify cookie setting code
        assert "document.cookie = 'csrftoken=test-csrf-token;" in js_code
        assert "path=/;" in js_code
        assert "secure;" in js_code
        assert "samesite=lax'" in js_code
    
    def test_generate_cookie_setting_code_custom_name(self):
        """Test cookie setting code with custom cookie name."""
        config = {
            "ajax": {
                "cookie_name": "custom_csrf"
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        token = "test-csrf-token"
        js_code = integration.generate_cookie_setting_code(token)
        
        assert "document.cookie = 'custom_csrf=test-csrf-token;" in js_code
    
    def test_extract_token_from_header(self):
        """Test token extraction from request header."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock request with CSRF header
        request = MagicMock()
        request.headers = {"X-CSRFToken": "test-csrf-token"}
        
        token = integration.extract_token_from_request(request)
        assert token == "test-csrf-token"
    
    def test_extract_token_from_custom_header(self):
        """Test token extraction from custom header name."""
        config = {
            "ajax": {
                "header_name": "X-Custom-CSRF"
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {"X-Custom-CSRF": "test-csrf-token"}
        
        token = integration.extract_token_from_request(request)
        assert token == "test-csrf-token"
    
    def test_extract_token_from_cookie(self):
        """Test token extraction from cookie fallback."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock request with CSRF cookie but no header
        request = MagicMock()
        request.headers = {}
        request.cookies = {"csrftoken": "test-csrf-token"}
        
        token = integration.extract_token_from_request(request)
        assert token == "test-csrf-token"
    
    def test_extract_token_header_priority(self):
        """Test that header takes priority over cookie."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock request with both header and cookie
        request = MagicMock()
        request.headers = {"X-CSRFToken": "header-token"}
        request.cookies = {"csrftoken": "cookie-token"}
        
        token = integration.extract_token_from_request(request)
        assert token == "header-token"  # Header should take priority
    
    def test_extract_token_no_token(self):
        """Test token extraction when no token is present."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock request without CSRF token
        request = MagicMock()
        request.headers = {}
        request.cookies = {}
        
        token = integration.extract_token_from_request(request)
        assert token is None
    
    def test_generate_axios_configuration(self):
        """Test generation of Axios configuration code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_axios_configuration()
        
        # Verify Axios configuration
        assert "axios.defaults.headers.common['X-CSRFToken']" in js_code
        assert "getCSRFToken()" in js_code
    
    def test_generate_fetch_configuration(self):
        """Test generation of Fetch API configuration code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_fetch_configuration()
        
        # Verify Fetch configuration
        assert "'X-CSRFToken': getCSRFToken()" in js_code
        assert "options.headers" in js_code
    
    def test_generate_jquery_configuration(self):
        """Test generation of jQuery configuration code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_jquery_configuration()
        
        # Verify jQuery configuration
        assert "$.ajaxSetup({" in js_code
        assert "setRequestHeader('X-CSRFToken', getCSRFToken())" in js_code
        assert "beforeSend:" in js_code
    
    def test_generate_spa_refresh_code(self):
        """Test generation of SPA token refresh code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_spa_refresh_code()
        
        # Verify SPA refresh functionality
        assert "function refreshCSRFToken()" in js_code
        assert "fetch('/csrf/refresh'" in js_code
        assert "updateCSRFToken" in js_code
    
    def test_generate_spa_refresh_code_custom_endpoint(self):
        """Test SPA refresh code with custom endpoint."""
        config = {
            "ajax": {
                "refresh_endpoint": "/api/csrf/refresh"
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_spa_refresh_code()
        
        assert "fetch('/api/csrf/refresh'" in js_code
    
    def test_generate_error_handling_code(self):
        """Test generation of CSRF error handling code."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_error_handling_code()
        
        # Verify error handling
        assert "function handleCSRFError" in js_code
        assert "response.status === 403" in js_code
        assert "refreshCSRFToken()" in js_code
    
    def test_generate_complete_integration_script(self):
        """Test generation of complete AJAX integration script."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        token = "test-csrf-token"
        script = integration.generate_complete_script(token)
        
        # Verify all components are included
        assert "function getCSRFToken()" in script
        assert "axios.defaults.headers.common" in script
        assert "$.ajaxSetup" in script
        assert "function refreshCSRFToken()" in script
        assert "function handleCSRFError" in script
    
    def test_create_xhr_interceptor(self):
        """Test creation of XMLHttpRequest interceptor."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        js_code = integration.generate_xhr_interceptor()
        
        # Verify XHR interceptor
        assert "XMLHttpRequest.prototype.open" in js_code
        assert "XMLHttpRequest.prototype.send" in js_code
        assert "setRequestHeader('X-CSRFToken'" in js_code
    
    def test_token_refresh_mechanism(self):
        """Test token refresh mechanism for SPAs."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.generate_token.return_value = "new-csrf-token"
        
        # Mock request for refresh
        request = MagicMock()
        
        # Generate refresh response
        refresh_data = integration.create_refresh_response(request, token_manager)
        
        assert "token" in refresh_data
        assert refresh_data["token"] == "new-csrf-token"
        assert "expires_at" in refresh_data
    
    def test_validate_ajax_request(self):
        """Test validation of AJAX CSRF requests."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        # Mock valid AJAX request
        request = MagicMock()
        request.headers = {
            "X-CSRFToken": "valid-token",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.validate_token.return_value = True
        
        is_valid = integration.validate_ajax_request(request, token_manager)
        assert is_valid is True
    
    def test_validate_ajax_request_invalid_token(self):
        """Test validation with invalid CSRF token."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {
            "X-CSRFToken": "invalid-token",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Mock token manager
        token_manager = MagicMock()
        token_manager.validate_token.return_value = False
        
        is_valid = integration.validate_ajax_request(request, token_manager)
        assert is_valid is False
    
    def test_validate_ajax_request_missing_token(self):
        """Test validation with missing CSRF token."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {"X-Requested-With": "XMLHttpRequest"}
        request.cookies = {}
        
        token_manager = MagicMock()
        
        is_valid = integration.validate_ajax_request(request, token_manager)
        assert is_valid is False
    
    def test_is_ajax_request_xhr_header(self):
        """Test AJAX request detection via XHR header."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {"X-Requested-With": "XMLHttpRequest"}
        
        assert integration.is_ajax_request(request) is True
    
    def test_is_ajax_request_content_type(self):
        """Test AJAX request detection via content type."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        assert integration.is_ajax_request(request) is True
    
    def test_is_not_ajax_request(self):
        """Test non-AJAX request detection."""
        config = {}
        integration = CSRFAjaxIntegration(config)
        
        request = MagicMock()
        request.headers = {}
        
        assert integration.is_ajax_request(request) is False
    
    def test_validate_config_valid(self):
        """Test AJAX integration configuration validation."""
        config = {
            "ajax": {
                "header_name": "X-CSRFToken",
                "cookie_name": "csrftoken",
                "javascript_function": "getCSRFToken"
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        errors = integration.validate_config()
        assert errors == []
    
    def test_validate_config_invalid_header_name(self):
        """Test validation with invalid header name."""
        config = {
            "ajax": {
                "header_name": "invalid header name"  # Spaces not allowed
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        errors = integration.validate_config()
        assert len(errors) > 0
        assert any("header_name" in error for error in errors)
    
    def test_validate_config_invalid_function_name(self):
        """Test validation with invalid JavaScript function name."""
        config = {
            "ajax": {
                "javascript_function": "invalid-function-name!"  # Invalid JS identifier
            }
        }
        integration = CSRFAjaxIntegration(config)
        
        errors = integration.validate_config()
        assert len(errors) > 0
        assert any("javascript_function" in error for error in errors)