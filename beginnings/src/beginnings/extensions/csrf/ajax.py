"""
CSRF AJAX and SPA integration for Beginnings framework.

This module provides AJAX request handling, JavaScript utility generation,
and single-page application token management for CSRF protection.
"""

import re
from typing import Any
from html import escape


class CSRFAjaxIntegration:
    """
    CSRF AJAX integration manager.
    
    Handles AJAX token extraction, JavaScript generation,
    and SPA token refresh mechanisms.
    """
    
    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize CSRF AJAX integration.
        
        Args:
            config: CSRF configuration dictionary
        """
        ajax_config = config.get("ajax", {})
        
        self.header_name = ajax_config.get("header_name", "X-CSRFToken")
        self.cookie_name = ajax_config.get("cookie_name", "csrftoken")
        self.javascript_function = ajax_config.get("javascript_function", "getCSRFToken")
        self.refresh_endpoint = ajax_config.get("refresh_endpoint", "/csrf/refresh")
    
    def extract_token_from_request(self, request: Any) -> str | None:
        """
        Extract CSRF token from AJAX request.
        
        Args:
            request: Request object
            
        Returns:
            CSRF token if found, None otherwise
        """
        # Check custom header first (preferred method)
        token = request.headers.get(self.header_name)
        if token:
            return token
        
        # Fallback to cookie
        token = request.cookies.get(self.cookie_name)
        if token:
            return token
        
        return None
    
    def generate_javascript_function(self, token: str) -> str:
        """
        Generate JavaScript function for CSRF token access.
        
        Args:
            token: Current CSRF token
            
        Returns:
            JavaScript code string
        """
        escaped_token = escape(token, quote=True)
        
        return f"""
// CSRF Token Management
function {self.javascript_function}() {{
    // Try to get token from meta tag first
    var metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {{
        return metaTag.getAttribute('content');
    }}
    
    // Fallback to hardcoded token
    return '{escaped_token}';
}}

// Alternative function to get token from cookie
function getCSRFTokenFromCookie() {{
    var name = '{self.cookie_name}=';
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for (var i = 0; i < ca.length; i++) {{
        var c = ca[i];
        while (c.charAt(0) == ' ') {{
            c = c.substring(1);
        }}
        if (c.indexOf(name) == 0) {{
            return c.substring(name.length, c.length);
        }}
    }}
    return '';
}}
"""
    
    def generate_cookie_setting_code(self, token: str) -> str:
        """
        Generate JavaScript code to set CSRF cookie.
        
        Args:
            token: CSRF token to set
            
        Returns:
            JavaScript code string
        """
        escaped_token = escape(token, quote=True)
        
        return f"""
// Set CSRF token cookie
document.cookie = '{self.cookie_name}={escaped_token}; path=/; secure; samesite=lax';

function setCSRFToken(token) {{
    document.cookie = '{self.cookie_name}=' + token + '; path=/; secure; samesite=lax';
}}
"""
    
    def generate_axios_configuration(self) -> str:
        """
        Generate Axios configuration for CSRF tokens.
        
        Returns:
            JavaScript code for Axios setup
        """
        return f"""
// Configure Axios for CSRF protection
if (typeof axios !== 'undefined') {{
    axios.defaults.headers.common['{self.header_name}'] = {self.javascript_function}();
    
    // Update token on each request
    axios.interceptors.request.use(function (config) {{
        config.headers['{self.header_name}'] = {self.javascript_function}();
        return config;
    }});
}}
"""
    
    def generate_fetch_configuration(self) -> str:
        """
        Generate Fetch API configuration for CSRF tokens.
        
        Returns:
            JavaScript code for Fetch setup
        """
        return f"""
// Configure Fetch API for CSRF protection
function csrfFetch(url, options = {{}}) {{
    options.headers = options.headers || {{}};
    options.headers = {{
        ...options.headers,
        '{self.header_name}': {self.javascript_function}()
    }};
    return fetch(url, options);
}}

// Override default fetch with CSRF-aware version
window.originalFetch = window.fetch;
window.fetch = csrfFetch;
"""
    
    def generate_jquery_configuration(self) -> str:
        """
        Generate jQuery configuration for CSRF tokens.
        
        Returns:
            JavaScript code for jQuery setup
        """
        return f"""
// Configure jQuery for CSRF protection
if (typeof $ !== 'undefined') {{
    $.ajaxSetup({{
        headers: {{
            '{self.header_name}': {self.javascript_function}()
        }},
        beforeSend: function(xhr, settings) {{
            if (!this.crossDomain) {{
                xhr.setRequestHeader('{self.header_name}', {self.javascript_function}());
            }}
        }}
    }});
}}
"""
    
    def generate_xhr_interceptor(self) -> str:
        """
        Generate XMLHttpRequest interceptor for CSRF tokens.
        
        Returns:
            JavaScript code for XHR interception
        """
        return f"""
// Intercept XMLHttpRequest for CSRF protection
(function() {{
    var originalOpen = XMLHttpRequest.prototype.open;
    var originalSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url) {{
        this._method = method;
        this._url = url;
        return originalOpen.apply(this, arguments);
    }};
    
    XMLHttpRequest.prototype.send = function(data) {{
        // Add CSRF header for state-changing requests
        if (this._method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(this._method.toUpperCase())) {{
            this.setRequestHeader('{self.header_name}', {self.javascript_function}());
        }}
        return originalSend.apply(this, arguments);
    }};
}})();
"""
    
    def generate_spa_refresh_code(self) -> str:
        """
        Generate SPA token refresh functionality.
        
        Returns:
            JavaScript code for token refresh
        """
        return f"""
// SPA Token Refresh Functionality
function refreshCSRFToken() {{
    return fetch('{self.refresh_endpoint}', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json'
        }}
    }})
    .then(response => response.json())
    .then(data => {{
        if (data.token) {{
            updateCSRFToken(data.token);
            return data.token;
        }}
        throw new Error('Failed to refresh CSRF token');
    }});
}}

function updateCSRFToken(newToken) {{
    // Update meta tag
    var metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {{
        metaTag.setAttribute('content', newToken);
    }}
    
    // Update cookie
    setCSRFToken(newToken);
    
    // Update Axios default header
    if (typeof axios !== 'undefined') {{
        axios.defaults.headers.common['{self.header_name}'] = newToken;
    }}
}}

// Auto-refresh token periodically (every 30 minutes)
setInterval(refreshCSRFToken, 30 * 60 * 1000);
"""
    
    def generate_error_handling_code(self) -> str:
        """
        Generate CSRF error handling code.
        
        Returns:
            JavaScript code for error handling
        """
        return f"""
// CSRF Error Handling
function handleCSRFError(response) {{
    if (response.status === 403) {{
        console.warn('CSRF token validation failed, refreshing token...');
        return refreshCSRFToken().then(() => {{
            // Retry the original request
            console.log('CSRF token refreshed, please retry your request');
        }});
    }}
    return Promise.reject(response);
}}

// Add error handling to fetch
if (window.originalFetch) {{
    window.fetch = function(url, options = {{}}) {{
        options.headers = options.headers || {{}};
        options.headers['{self.header_name}'] = {self.javascript_function}();
        
        return window.originalFetch(url, options)
            .then(response => {{
                if (response.status === 403) {{
                    return handleCSRFError(response);
                }}
                return response;
            }});
    }};
}}

// Add error handling to Axios
if (typeof axios !== 'undefined') {{
    axios.interceptors.response.use(
        response => response,
        error => {{
            if (error.response && error.response.status === 403) {{
                return handleCSRFError(error.response);
            }}
            return Promise.reject(error);
        }}
    );
}}
"""
    
    def generate_complete_script(self, token: str) -> str:
        """
        Generate complete CSRF AJAX integration script.
        
        Args:
            token: Current CSRF token
            
        Returns:
            Complete JavaScript code
        """
        script_parts = [
            "// CSRF AJAX Integration - Auto-generated",
            self.generate_javascript_function(token),
            self.generate_cookie_setting_code(token),
            self.generate_axios_configuration(),
            self.generate_fetch_configuration(),
            self.generate_jquery_configuration(),
            self.generate_xhr_interceptor(),
            self.generate_spa_refresh_code(),
            self.generate_error_handling_code()
        ]
        
        return "\n\n".join(script_parts)
    
    def create_refresh_response(self, request: Any, token_manager: Any) -> dict[str, Any]:
        """
        Create response for token refresh endpoint.
        
        Args:
            request: Request object
            token_manager: CSRF token manager
            
        Returns:
            Dictionary with refresh response data
        """
        new_token = token_manager.generate_token(request)
        
        return {
            "token": new_token,
            "expires_at": None,  # Token manager should provide expiration if applicable
            "header_name": self.header_name,
            "cookie_name": self.cookie_name
        }
    
    def validate_ajax_request(self, request: Any, token_manager: Any) -> bool:
        """
        Validate AJAX CSRF request.
        
        Args:
            request: Request object
            token_manager: CSRF token manager
            
        Returns:
            True if request is valid
        """
        token = self.extract_token_from_request(request)
        if not token:
            return False
        
        return token_manager.validate_token(token, request)
    
    def is_ajax_request(self, request: Any) -> bool:
        """
        Determine if request is an AJAX request.
        
        Args:
            request: Request object
            
        Returns:
            True if request appears to be AJAX
        """
        # Check X-Requested-With header
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        
        # Check content type and accept headers
        content_type = request.headers.get("Content-Type", "").lower()
        accept = request.headers.get("Accept", "").lower()
        
        if "application/json" in content_type or "application/json" in accept:
            return True
        
        return False
    
    def validate_config(self) -> list[str]:
        """
        Validate AJAX integration configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate header name (should be valid HTTP header)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', self.header_name):
            errors.append("AJAX header_name must be a valid HTTP header name")
        
        # Validate cookie name (should be valid cookie name)
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.cookie_name):
            errors.append("AJAX cookie_name must be a valid cookie name")
        
        # Validate JavaScript function name (should be valid JS identifier)
        if not re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', self.javascript_function):
            errors.append("AJAX javascript_function must be a valid JavaScript identifier")
        
        return errors