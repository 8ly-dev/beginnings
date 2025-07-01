"""Test fixtures for extension testing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import json


class ExtensionFixtures:
    """Fixtures for extension testing."""
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default extension configuration."""
        return {
            "enabled": True,
            "debug": True
        }
    
    def get_middleware_config(self) -> Dict[str, Any]:
        """Get middleware extension configuration."""
        return {
            **self.get_default_config(),
            "option1": "test_value",
            "option2": True,
            "timeout": 30,
            "max_retries": 3
        }
    
    def get_auth_config(self) -> Dict[str, Any]:
        """Get auth provider extension configuration."""
        return {
            **self.get_default_config(),
            "api_key": "test_api_key",
            "api_secret": "test_api_secret", 
            "endpoint_url": "https://test-auth.example.com",
            "require_auth": True,
            "protected_routes": ["/admin/*", "/api/private/*"],
            "public_routes": ["/health", "/public/*"],
            "provider": {
                "type": "test",
                "config": {
                    "test_mode": True
                }
            }
        }
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get integration extension configuration."""
        return {
            **self.get_default_config(),
            "api_key": "test_integration_key",
            "api_secret": "test_integration_secret",
            "base_url": "https://api.test-service.com",
            "timeout": 60,
            "webhook_path": "/webhooks/test_service",
            "webhook_secret": "test_webhook_secret",
            "enable_webhooks": True,
            "enable_events": True,
            "event_queue_size": 100,
            "retry_config": {
                "max_retries": 3,
                "retry_delay": 1.0,
                "backoff_factor": 2.0
            }
        }
    
    def get_feature_config(self) -> Dict[str, Any]:
        """Get feature extension configuration."""
        return {
            **self.get_default_config(),
            "api_prefix": "/api/test_feature",
            "enable_api": True,
            "enable_ui": False,
            "db_table_prefix": "test_feature_",
            "auto_migrate": False,  # Don't auto-migrate in tests
            "pagination": {
                "default_limit": 10,
                "max_limit": 100
            },
            "permissions": {
                "create": ["admin", "editor"],
                "read": ["admin", "editor", "viewer"],
                "update": ["admin", "editor"],
                "delete": ["admin"]
            }
        }
    
    def get_invalid_config(self) -> Dict[str, Any]:
        """Get invalid configuration for testing validation."""
        return {
            "enabled": "not_a_boolean",
            "timeout": -1,
            "api_key": None,
            "invalid_field": "should_not_exist"
        }


class ConfigFixtures:
    """Configuration fixtures for testing."""
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get test application configuration."""
        return {
            "app": {
                "name": "test_app",
                "debug": True,
                "environment": "test"
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000
            },
            "database": {
                "url": "sqlite:///:memory:",
                "echo": False
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
    
    def get_extension_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get configurations for multiple extensions."""
        extension_fixtures = ExtensionFixtures()
        
        return {
            "auth": extension_fixtures.get_auth_config(),
            "middleware": extension_fixtures.get_middleware_config(),
            "integration": extension_fixtures.get_integration_config(),
            "feature": extension_fixtures.get_feature_config()
        }
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get full application configuration with extensions."""
        config = self.get_app_config()
        config["extensions"] = self.get_extension_configs()
        return config


class RequestFixtures:
    """HTTP request fixtures for testing."""
    
    def get_basic_request_data(self) -> Dict[str, Any]:
        """Get basic request data."""
        return {
            "method": "GET",
            "path": "/test",
            "headers": {
                "User-Agent": "test-client/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            "query_params": {},
            "body": None
        }
    
    def get_authenticated_request_data(self) -> Dict[str, Any]:
        """Get authenticated request data."""
        data = self.get_basic_request_data()
        data["headers"]["Authorization"] = "Bearer test_token_123"
        return data
    
    def get_post_request_data(self) -> Dict[str, Any]:
        """Get POST request data."""
        return {
            "method": "POST",
            "path": "/api/resources",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer test_token_123"
            },
            "query_params": {},
            "body": json.dumps({
                "name": "Test Resource",
                "description": "A test resource",
                "tags": ["test", "example"]
            }).encode()
        }
    
    def get_webhook_request_data(self) -> Dict[str, Any]:
        """Get webhook request data."""
        webhook_data = {
            "id": str(uuid.uuid4()),
            "type": "resource.created",
            "data": {
                "resource_id": "res_123",
                "name": "New Resource",
                "created_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "method": "POST",
            "path": "/webhooks/test_service",
            "headers": {
                "Content-Type": "application/json",
                "X-Test-Service-Signature": "test_signature_123",
                "X-Test-Service-Event": "resource.created"
            },
            "query_params": {},
            "body": json.dumps(webhook_data).encode()
        }
    
    def get_file_upload_request_data(self) -> Dict[str, Any]:
        """Get file upload request data."""
        return {
            "method": "POST",
            "path": "/api/files",
            "headers": {
                "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
                "Authorization": "Bearer test_token_123"
            },
            "query_params": {},
            "body": b'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\nTest file content\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n'
        }


class ResponseFixtures:
    """HTTP response fixtures for testing."""
    
    def get_success_response_data(self) -> Dict[str, Any]:
        """Get successful response data."""
        return {
            "status_code": 200,
            "headers": {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            },
            "content": json.dumps({
                "status": "success",
                "data": {
                    "id": "123",
                    "name": "Test Resource"
                }
            }).encode()
        }
    
    def get_error_response_data(self) -> Dict[str, Any]:
        """Get error response data."""
        return {
            "status_code": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "content": json.dumps({
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request data",
                    "details": {
                        "field": "name",
                        "issue": "required"
                    }
                }
            }).encode()
        }
    
    def get_auth_error_response_data(self) -> Dict[str, Any]:
        """Get authentication error response data."""
        return {
            "status_code": 401,
            "headers": {
                "Content-Type": "application/json",
                "WWW-Authenticate": "Bearer"
            },
            "content": json.dumps({
                "status": "error",
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required"
                }
            }).encode()
        }
    
    def get_not_found_response_data(self) -> Dict[str, Any]:
        """Get not found response data."""
        return {
            "status_code": 404,
            "headers": {
                "Content-Type": "application/json"
            },
            "content": json.dumps({
                "status": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Resource not found"
                }
            }).encode()
        }


class BeginningsTestFixtures:
    """Main fixtures class combining all fixture types."""
    
    def __init__(self):
        self.extensions = ExtensionFixtures()
        self.config = ConfigFixtures()
        self.requests = RequestFixtures()
        self.responses = ResponseFixtures()
    
    def get_test_user_data(self) -> Dict[str, Any]:
        """Get test user data."""
        return {
            "user_id": "test_user_123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user", "tester"],
            "permissions": ["read", "write"],
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "last_login": (datetime.utcnow() - timedelta(hours=1)).isoformat()
            }
        }
    
    def get_test_api_data(self) -> Dict[str, Any]:
        """Get test API data."""
        return {
            "resources": [
                {
                    "id": "res_1",
                    "name": "Resource 1",
                    "type": "test",
                    "status": "active"
                },
                {
                    "id": "res_2", 
                    "name": "Resource 2",
                    "type": "test",
                    "status": "inactive"
                }
            ],
            "pagination": {
                "total": 2,
                "limit": 10,
                "offset": 0,
                "has_more": False
            }
        }
    
    def get_test_webhook_data(self) -> Dict[str, Any]:
        """Get test webhook data."""
        return {
            "id": str(uuid.uuid4()),
            "type": "test.event",
            "data": {
                "test_field": "test_value",
                "timestamp": datetime.utcnow().isoformat()
            },
            "delivery_attempt": 1,
            "created_at": datetime.utcnow().isoformat()
        }