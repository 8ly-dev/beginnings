"""Mock objects for extension testing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union
from unittest.mock import MagicMock, AsyncMock
import asyncio
from datetime import datetime
import json


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(
        self,
        method: str = "GET",
        path: str = "/test",
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, str]] = None,
        path_params: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        user: Optional[Dict[str, Any]] = None
    ):
        self.method = method
        self.url = MockURL(path)
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.path_params = path_params or {}
        self._body = body
        self.state = MockState()
        
        if user:
            self.state.user = user
    
    async def body(self) -> bytes:
        """Get request body."""
        return self._body or b""
    
    async def json(self) -> Any:
        """Get request JSON."""
        if not self._body:
            return None
        return json.loads(self._body.decode())
    
    def __getitem__(self, key: str) -> Any:
        """Get header value."""
        return self.headers.get(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get header value with default."""
        return self.headers.get(key, default)


class MockURL:
    """Mock URL object."""
    
    def __init__(self, path: str):
        self.path = path
        self.scheme = "http"
        self.hostname = "localhost"
        self.port = 8000
    
    def __str__(self) -> str:
        return f"{self.scheme}://{self.hostname}:{self.port}{self.path}"


class MockState:
    """Mock request state object."""
    
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_data'):
                super().__setattr__('_data', {})
            self._data[name] = value


class MockResponse:
    """Mock response object for testing."""
    
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self._json_data = json_data
    
    def json(self) -> Any:
        """Get response JSON."""
        if self._json_data is not None:
            return self._json_data
        if self.content:
            return json.loads(self.content.decode())
        return None
    
    @property
    def text(self) -> str:
        """Get response text."""
        if self.content:
            return self.content.decode()
        return ""


class MockExtension:
    """Mock extension for testing."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        should_apply: bool = True
    ):
        self.config = config or {}
        self.enabled = enabled
        self._should_apply = should_apply
        self.validate_config = MagicMock(return_value=[])
        self.get_middleware_factory = MagicMock()
        self.get_startup_handler = MagicMock(return_value=None)
        self.get_shutdown_handler = MagicMock(return_value=None)
    
    def should_apply_to_route(
        self, 
        path: str, 
        methods: List[str], 
        route_config: Dict[str, Any]
    ) -> bool:
        """Mock route application logic."""
        return self._should_apply and self.enabled


class MockMiddleware:
    """Mock middleware for testing."""
    
    def __init__(
        self,
        app: Any = None,
        extension_config: Optional[Dict[str, Any]] = None,
        route_config: Optional[Dict[str, Any]] = None
    ):
        self.app = app
        self.extension_config = extension_config or {}
        self.route_config = route_config or {}
        self.calls = []
    
    async def dispatch(self, request: MockRequest, call_next: Callable) -> MockResponse:
        """Mock middleware dispatch."""
        self.calls.append(('dispatch', request.method, request.url.path))
        
        # Call before_request if it exists
        if hasattr(self, '_before_request'):
            await self._before_request(request)
        
        # Call next middleware
        response = await call_next(request)
        
        # Call after_request if it exists
        if hasattr(self, '_after_request'):
            await self._after_request(request, response)
        
        return response


class MockBeginningsApp:
    """Mock Beginnings application for testing."""
    
    def __init__(self):
        self.routes = []
        self.middleware = []
        self.extensions = {}
        self.startup_handlers = []
        self.shutdown_handlers = []
        self.state = {}
        
        # Mock methods
        self.add_route = MagicMock(side_effect=self._add_route)
        self.add_middleware = MagicMock(side_effect=self._add_middleware)
        self.include_router = MagicMock()
        self.on_event = MagicMock()
    
    def _add_route(self, path: str, endpoint: Callable, methods: List[str] = None):
        """Mock add route."""
        self.routes.append({
            "path": path,
            "endpoint": endpoint,
            "methods": methods or ["GET"]
        })
    
    def _add_middleware(self, middleware_class: type, **kwargs):
        """Mock add middleware."""
        self.middleware.append({
            "class": middleware_class,
            "kwargs": kwargs
        })
    
    def get_route(self, path: str, method: str = "GET") -> Optional[Dict[str, Any]]:
        """Get route by path and method."""
        for route in self.routes:
            if route["path"] == path and method in route["methods"]:
                return route
        return None
    
    def get_middleware(self, middleware_class: type) -> List[Dict[str, Any]]:
        """Get middleware by class."""
        return [mw for mw in self.middleware if mw["class"] == middleware_class]


class MockHTTPClient:
    """Mock HTTP client for testing integrations."""
    
    def __init__(self):
        self.requests = []
        self.responses = {}
        self.default_response = MockResponse()
    
    def set_response(
        self, 
        method: str, 
        url: str, 
        response: MockResponse
    ):
        """Set response for specific request."""
        key = f"{method.upper()}:{url}"
        self.responses[key] = response
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> MockResponse:
        """Mock HTTP request."""
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow()
        })
        
        key = f"{method.upper()}:{url}"
        return self.responses.get(key, self.default_response)
    
    async def get(self, url: str, **kwargs) -> MockResponse:
        """Mock GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> MockResponse:
        """Mock POST request."""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> MockResponse:
        """Mock PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> MockResponse:
        """Mock DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    async def aclose(self):
        """Mock client close."""
        pass
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of requests made."""
        return self.requests.copy()
    
    def clear_history(self):
        """Clear request history."""
        self.requests.clear()


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.tables = {}
        self.operations = []
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Mock execute query."""
        self.operations.append({
            "type": "execute",
            "query": query,
            "params": params,
            "timestamp": datetime.utcnow()
        })
        return MockCursor()
    
    async def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Mock fetch one result."""
        self.operations.append({
            "type": "fetch_one",
            "query": query,
            "params": params,
            "timestamp": datetime.utcnow()
        })
        return None
    
    async def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Mock fetch all results."""
        self.operations.append({
            "type": "fetch_all",
            "query": query,
            "params": params,
            "timestamp": datetime.utcnow()
        })
        return []
    
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get history of database operations."""
        return self.operations.copy()
    
    def clear_operations(self):
        """Clear operation history."""
        self.operations.clear()


class MockCursor:
    """Mock database cursor."""
    
    def __init__(self):
        self.rowcount = 0
        self.lastrowid = None
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Mock fetch one."""
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        """Mock fetch all."""
        return []


class MockLogger:
    """Mock logger for testing."""
    
    def __init__(self, name: str = "test"):
        self.name = name
        self.logs = []
    
    def debug(self, message: str, *args, **kwargs):
        """Mock debug log."""
        self._log("DEBUG", message, args, kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Mock info log."""
        self._log("INFO", message, args, kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Mock warning log."""
        self._log("WARNING", message, args, kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Mock error log."""
        self._log("ERROR", message, args, kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Mock critical log."""
        self._log("CRITICAL", message, args, kwargs)
    
    def _log(self, level: str, message: str, args: tuple, kwargs: dict):
        """Record log entry."""
        self.logs.append({
            "level": level,
            "message": message,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow()
        })
    
    def get_logs(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logged entries."""
        if level:
            return [log for log in self.logs if log["level"] == level]
        return self.logs.copy()
    
    def clear_logs(self):
        """Clear log entries."""
        self.logs.clear()


# Factory functions for creating mock objects

def create_mock_app(**kwargs) -> MockBeginningsApp:
    """Create mock Beginnings app."""
    return MockBeginningsApp(**kwargs)


def create_mock_request(**kwargs) -> MockRequest:
    """Create mock request."""
    return MockRequest(**kwargs)


def create_mock_response(**kwargs) -> MockResponse:
    """Create mock response."""
    return MockResponse(**kwargs)


def create_mock_extension(**kwargs) -> MockExtension:
    """Create mock extension."""
    return MockExtension(**kwargs)


def create_mock_http_client(**kwargs) -> MockHTTPClient:
    """Create mock HTTP client."""
    return MockHTTPClient(**kwargs)


def create_mock_database(**kwargs) -> MockDatabase:
    """Create mock database."""
    return MockDatabase(**kwargs)


def create_mock_logger(name: str = "test") -> MockLogger:
    """Create mock logger."""
    return MockLogger(name)