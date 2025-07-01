"""Specialized assertions for extension testing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union
import json
import re
from datetime import datetime, timedelta

from ..extensions.base import BaseExtension


class ExtensionAssertions:
    """Specialized assertions for extension testing."""
    
    def assert_config_valid(self, extension: BaseExtension):
        """Assert that extension configuration is valid.
        
        Args:
            extension: Extension to validate
            
        Raises:
            AssertionError: If configuration is invalid
        """
        errors = extension.validate_config()
        if errors:
            raise AssertionError(f"Extension configuration is invalid: {', '.join(errors)}")
    
    def assert_config_invalid(self, extension: BaseExtension, expected_errors: Optional[List[str]] = None):
        """Assert that extension configuration is invalid.
        
        Args:
            extension: Extension to validate
            expected_errors: Expected error messages
            
        Raises:
            AssertionError: If configuration is valid or errors don't match
        """
        errors = extension.validate_config()
        if not errors:
            raise AssertionError("Extension configuration should be invalid but validation passed")
        
        if expected_errors:
            for expected_error in expected_errors:
                if not any(expected_error in error for error in errors):
                    raise AssertionError(f"Expected error '{expected_error}' not found in validation errors: {errors}")
    
    def assert_middleware_called(self, middleware, method_name: str):
        """Assert that middleware method was called.
        
        Args:
            middleware: Middleware instance to check
            method_name: Name of method that should have been called
            
        Raises:
            AssertionError: If method was not called
        """
        if not hasattr(middleware, 'calls'):
            raise AssertionError("Middleware doesn't track calls")
        
        method_calls = [call for call in middleware.calls if call[0] == method_name]
        if not method_calls:
            raise AssertionError(f"Middleware method '{method_name}' was not called")
    
    def assert_middleware_not_called(self, middleware, method_name: str):
        """Assert that middleware method was not called.
        
        Args:
            middleware: Middleware instance to check
            method_name: Name of method that should not have been called
            
        Raises:
            AssertionError: If method was called
        """
        if not hasattr(middleware, 'calls'):
            return  # No calls tracked, so method wasn't called
        
        method_calls = [call for call in middleware.calls if call[0] == method_name]
        if method_calls:
            raise AssertionError(f"Middleware method '{method_name}' should not have been called but was called {len(method_calls)} times")
    
    def assert_request_has_header(self, request, header_name: str, expected_value: Optional[str] = None):
        """Assert that request has specific header.
        
        Args:
            request: Request object to check
            header_name: Name of header to check
            expected_value: Expected header value (if None, just checks presence)
            
        Raises:
            AssertionError: If header is missing or value doesn't match
        """
        if header_name not in request.headers:
            raise AssertionError(f"Request missing header '{header_name}'")
        
        if expected_value is not None:
            actual_value = request.headers[header_name]
            if actual_value != expected_value:
                raise AssertionError(f"Header '{header_name}' has value '{actual_value}', expected '{expected_value}'")
    
    def assert_request_missing_header(self, request, header_name: str):
        """Assert that request does not have specific header.
        
        Args:
            request: Request object to check
            header_name: Name of header that should not be present
            
        Raises:
            AssertionError: If header is present
        """
        if header_name in request.headers:
            raise AssertionError(f"Request should not have header '{header_name}' but it is present")
    
    def assert_response_status(self, response, expected_status: int):
        """Assert response status code.
        
        Args:
            response: Response object to check
            expected_status: Expected status code
            
        Raises:
            AssertionError: If status doesn't match
        """
        if response.status_code != expected_status:
            raise AssertionError(f"Response status is {response.status_code}, expected {expected_status}")
    
    def assert_response_json(self, response, expected_data: Dict[str, Any]):
        """Assert response JSON content.
        
        Args:
            response: Response object to check
            expected_data: Expected JSON data
            
        Raises:
            AssertionError: If JSON doesn't match
        """
        try:
            actual_data = response.json()
        except Exception as e:
            raise AssertionError(f"Response does not contain valid JSON: {e}")
        
        if actual_data != expected_data:
            raise AssertionError(f"Response JSON is {actual_data}, expected {expected_data}")
    
    def assert_response_json_contains(self, response, key: str, expected_value: Any = None):
        """Assert response JSON contains specific key.
        
        Args:
            response: Response object to check
            key: JSON key to check for
            expected_value: Expected value for the key (if None, just checks presence)
            
        Raises:
            AssertionError: If key is missing or value doesn't match
        """
        try:
            data = response.json()
        except Exception as e:
            raise AssertionError(f"Response does not contain valid JSON: {e}")
        
        if key not in data:
            raise AssertionError(f"Response JSON missing key '{key}'")
        
        if expected_value is not None:
            actual_value = data[key]
            if actual_value != expected_value:
                raise AssertionError(f"Response JSON key '{key}' has value {actual_value}, expected {expected_value}")
    
    def assert_response_header(self, response, header_name: str, expected_value: Optional[str] = None):
        """Assert response has specific header.
        
        Args:
            response: Response object to check
            header_name: Name of header to check
            expected_value: Expected header value (if None, just checks presence)
            
        Raises:
            AssertionError: If header is missing or value doesn't match
        """
        if header_name not in response.headers:
            raise AssertionError(f"Response missing header '{header_name}'")
        
        if expected_value is not None:
            actual_value = response.headers[header_name]
            if actual_value != expected_value:
                raise AssertionError(f"Header '{header_name}' has value '{actual_value}', expected '{expected_value}'")
    
    def assert_authentication_required(self, response):
        """Assert that response indicates authentication is required.
        
        Args:
            response: Response object to check
            
        Raises:
            AssertionError: If response doesn't indicate auth required
        """
        if response.status_code != 401:
            raise AssertionError(f"Expected 401 Unauthorized, got {response.status_code}")
        
        # Check for WWW-Authenticate header
        if "WWW-Authenticate" not in response.headers:
            raise AssertionError("Response missing WWW-Authenticate header")
    
    def assert_permission_denied(self, response):
        """Assert that response indicates permission denied.
        
        Args:
            response: Response object to check
            
        Raises:
            AssertionError: If response doesn't indicate permission denied
        """
        if response.status_code != 403:
            raise AssertionError(f"Expected 403 Forbidden, got {response.status_code}")
    
    def assert_route_applies(self, extension: BaseExtension, path: str, methods: List[str], route_config: Optional[Dict[str, Any]] = None):
        """Assert that extension applies to given route.
        
        Args:
            extension: Extension to test
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Raises:
            AssertionError: If extension doesn't apply to route
        """
        should_apply = extension.should_apply_to_route(path, methods, route_config or {})
        if not should_apply:
            raise AssertionError(f"Extension should apply to route {path} {methods}")
    
    def assert_route_skipped(self, extension: BaseExtension, path: str, methods: List[str], route_config: Optional[Dict[str, Any]] = None):
        """Assert that extension skips given route.
        
        Args:
            extension: Extension to test
            path: Route path
            methods: HTTP methods
            route_config: Route configuration
            
        Raises:
            AssertionError: If extension applies to route
        """
        should_apply = extension.should_apply_to_route(path, methods, route_config or {})
        if should_apply:
            raise AssertionError(f"Extension should not apply to route {path} {methods}")
    
    def assert_webhook_signature_valid(self, signature: str, body: bytes, secret: str):
        """Assert webhook signature is valid.
        
        Args:
            signature: Provided signature
            body: Request body
            secret: Webhook secret
            
        Raises:
            AssertionError: If signature is invalid
        """
        import hmac
        import hashlib
        
        # Remove prefix if present
        if "=" in signature:
            signature = signature.split("=", 1)[1]
        
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise AssertionError("Webhook signature is invalid")
    
    def assert_log_contains(self, logger, level: str, message_pattern: str):
        """Assert that logger contains log entry matching pattern.
        
        Args:
            logger: Mock logger to check
            level: Log level to check
            message_pattern: Regex pattern to match in log message
            
        Raises:
            AssertionError: If no matching log entry found
        """
        if not hasattr(logger, 'get_logs'):
            raise AssertionError("Logger doesn't support log checking")
        
        logs = logger.get_logs(level)
        pattern = re.compile(message_pattern)
        
        matching_logs = [log for log in logs if pattern.search(log["message"])]
        if not matching_logs:
            raise AssertionError(f"No {level} log entries matching pattern '{message_pattern}'")
    
    def assert_database_operation(self, db, operation_type: str, query_pattern: Optional[str] = None):
        """Assert that database operation was performed.
        
        Args:
            db: Mock database to check
            operation_type: Type of operation (execute, fetch_one, fetch_all)
            query_pattern: Optional regex pattern to match in query
            
        Raises:
            AssertionError: If operation was not performed
        """
        if not hasattr(db, 'get_operations'):
            raise AssertionError("Database doesn't support operation checking")
        
        operations = db.get_operations()
        matching_ops = [op for op in operations if op["type"] == operation_type]
        
        if not matching_ops:
            raise AssertionError(f"No {operation_type} database operations found")
        
        if query_pattern:
            pattern = re.compile(query_pattern)
            matching_queries = [op for op in matching_ops if pattern.search(op["query"])]
            if not matching_queries:
                raise AssertionError(f"No {operation_type} operations with query matching '{query_pattern}'")
    
    def assert_http_request_made(self, client, method: str, url_pattern: str):
        """Assert that HTTP request was made.
        
        Args:
            client: Mock HTTP client to check
            method: HTTP method
            url_pattern: Regex pattern to match URL
            
        Raises:
            AssertionError: If request was not made
        """
        if not hasattr(client, 'get_request_history'):
            raise AssertionError("HTTP client doesn't support request history")
        
        requests = client.get_request_history()
        pattern = re.compile(url_pattern)
        
        matching_requests = [
            req for req in requests 
            if req["method"].upper() == method.upper() and pattern.search(req["url"])
        ]
        
        if not matching_requests:
            raise AssertionError(f"No {method} requests made to URL matching '{url_pattern}'")
    
    def assert_timing_within_range(self, start_time: datetime, end_time: datetime, min_seconds: float, max_seconds: float):
        """Assert that timing is within expected range.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            min_seconds: Minimum expected duration
            max_seconds: Maximum expected duration
            
        Raises:
            AssertionError: If timing is outside range
        """
        duration = (end_time - start_time).total_seconds()
        
        if duration < min_seconds:
            raise AssertionError(f"Duration {duration:.3f}s is less than minimum {min_seconds}s")
        
        if duration > max_seconds:
            raise AssertionError(f"Duration {duration:.3f}s is greater than maximum {max_seconds}s")