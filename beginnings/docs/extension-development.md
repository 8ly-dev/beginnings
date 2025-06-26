# Extension Development Guide

Complete guide to creating extensions for the Beginnings framework, including patterns, best practices, and examples.

## Extension Overview

Extensions in Beginnings provide a modular way to add functionality to your application through:
- **Middleware**: Process requests and responses
- **Lifecycle hooks**: Startup and shutdown handlers
- **Configuration**: Route-specific and global settings
- **Dependency injection**: Access to app and configuration

## Extension Interface

All extensions must inherit from `BaseExtension` and implement required methods:

```python
from typing import Any, Callable, Optional, Awaitable
from beginnings.extensions.base import BaseExtension

class MyExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "MyExtension")
        
    def get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]:
        """Return middleware factory function"""
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        """Determine if extension applies to route"""
        
    def validate_config(self) -> list[str]:
        """Validate configuration and return errors"""
        
    def get_startup_handler(self) -> Optional[Callable[[], Awaitable[None]]]:
        """Return async startup handler"""
        
    def get_shutdown_handler(self) -> Optional[Callable[[], Awaitable[None]]]:
        """Return async shutdown handler"""
```

## Basic Extension Example

Here's a simple logging extension:

```python
import functools
import time
from typing import Any, Callable, Optional, Awaitable
from beginnings.extensions.base import BaseExtension

class LoggingExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "LoggingExtension")
        self.enabled = config.get("enabled", True)
        self.log_level = config.get("log_level", "INFO")
        self.log_requests = config.get("log_requests", True)
        self.log_responses = config.get("log_responses", False)
        
    def validate_config(self) -> list[str]:
        errors = []
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            errors.append(f"log_level must be one of: {valid_levels}")
        return errors
        
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def logging_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    if not self.enabled:
                        return await endpoint(*args, **kwargs)
                        
                    start_time = time.time()
                    
                    # Log request
                    if self.log_requests:
                        print(f"[{self.log_level}] Starting {endpoint.__name__}")
                    
                    try:
                        # Call the endpoint
                        result = await endpoint(*args, **kwargs)
                        
                        # Log successful response
                        duration = time.time() - start_time
                        if self.log_responses:
                            print(f"[{self.log_level}] Completed {endpoint.__name__} in {duration:.3f}s")
                            
                        return result
                        
                    except Exception as e:
                        # Log error
                        duration = time.time() - start_time
                        print(f"[ERROR] Failed {endpoint.__name__} in {duration:.3f}s: {e}")
                        raise
                        
                return wrapper
            return logging_middleware
        return middleware_factory
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        # Apply to all routes if enabled
        if not self.enabled:
            return False
            
        # Check if logging is disabled for this specific route
        return route_config.get("logging_enabled", True)
        
    def get_startup_handler(self):
        async def startup():
            print(f"LoggingExtension started with level: {self.log_level}")
        return startup if self.enabled else None
```

## Configuration

Configure the extension in your application:

```yaml
# config/app.yaml
extensions:
  "my_package.logging:LoggingExtension":
    name: "RequestLogger"
    enabled: true
    log_level: "INFO"
    log_requests: true
    log_responses: true

# Route-specific configuration
routes:
  patterns:
    "/api/*":
      logging_enabled: true
    "/health":
      logging_enabled: false  # Disable logging for health checks
```

## Advanced Extension Patterns

### Authentication Extension

```python
import jwt
import functools
from typing import Any, Callable, Optional, Awaitable
from fastapi import HTTPException, Request
from beginnings.extensions.base import BaseExtension

class AuthExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "AuthExtension")
        self.enabled = config.get("enabled", True)
        self.secret_key = config.get("secret_key")
        self.algorithm = config.get("algorithm", "HS256")
        self.token_expiry = config.get("token_expiry", 3600)
        
    def validate_config(self) -> list[str]:
        errors = []
        if not self.secret_key:
            errors.append("secret_key is required")
        if self.algorithm not in ["HS256", "HS384", "HS512", "RS256"]:
            errors.append("Invalid algorithm specified")
        return errors
        
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def auth_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    # Extract request from args (FastAPI passes it as first arg)
                    request = None
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                            
                    if not request:
                        raise HTTPException(500, "Request object not found")
                    
                    # Check if auth is required for this route
                    auth_required = route_config.get("auth_required", False)
                    if not auth_required:
                        return await endpoint(*args, **kwargs)
                    
                    # Extract token from Authorization header
                    authorization = request.headers.get("Authorization")
                    if not authorization or not authorization.startswith("Bearer "):
                        raise HTTPException(401, "Authentication required")
                        
                    token = authorization.replace("Bearer ", "")
                    
                    try:
                        # Verify JWT token
                        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                        
                        # Add user info to request state
                        request.state.user = payload
                        
                        return await endpoint(*args, **kwargs)
                        
                    except jwt.ExpiredSignatureError:
                        raise HTTPException(401, "Token has expired")
                    except jwt.InvalidTokenError:
                        raise HTTPException(401, "Invalid token")
                        
                return wrapper
            return auth_middleware
        return middleware_factory
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("auth_required", False)
        
    def create_token(self, user_data: dict[str, Any]) -> str:
        """Utility method to create JWT tokens"""
        import time
        payload = {
            **user_data,
            "exp": int(time.time()) + self.token_expiry,
            "iat": int(time.time())
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
```

### Rate Limiting Extension

```python
import time
from collections import defaultdict
from typing import Any, Callable, Optional, Awaitable
from fastapi import HTTPException, Request
from beginnings.extensions.base import BaseExtension

class RateLimitExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "RateLimitExtension")
        self.enabled = config.get("enabled", True)
        self.default_limit = config.get("default_limit", 100)
        self.window_size = config.get("window_size", 60)  # seconds
        self.storage = config.get("storage", "memory")
        
        # In-memory storage (use Redis in production)
        self._requests = defaultdict(list)
        
    def validate_config(self) -> list[str]:
        errors = []
        if self.default_limit <= 0:
            errors.append("default_limit must be positive")
        if self.window_size <= 0:
            errors.append("window_size must be positive")
        return errors
        
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def rate_limit_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    if not self.enabled:
                        return await endpoint(*args, **kwargs)
                    
                    # Extract request
                    request = None
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                    
                    if not request:
                        return await endpoint(*args, **kwargs)
                    
                    # Get rate limit for this route
                    rate_limit = route_config.get("rate_limit", self.default_limit)
                    if rate_limit <= 0:  # Unlimited
                        return await endpoint(*args, **kwargs)
                    
                    # Create key for rate limiting (IP + route)
                    client_ip = request.client.host if request.client else "unknown"
                    key = f"{client_ip}:{request.url.path}"
                    
                    # Check rate limit
                    if self._is_rate_limited(key, rate_limit):
                        raise HTTPException(429, "Rate limit exceeded")
                    
                    return await endpoint(*args, **kwargs)
                    
                return wrapper
            return rate_limit_middleware
        return middleware_factory
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("rate_limit", self.default_limit) > 0
        
    def _is_rate_limited(self, key: str, limit: int) -> bool:
        """Check if request should be rate limited"""
        now = time.time()
        window_start = now - self.window_size
        
        # Clean old requests
        self._requests[key] = [req_time for req_time in self._requests[key] if req_time > window_start]
        
        # Check if limit exceeded
        if len(self._requests[key]) >= limit:
            return True
            
        # Record this request
        self._requests[key].append(now)
        return False
```

### Database Extension

```python
from typing import Any, Callable, Optional, Awaitable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from beginnings.extensions.base import BaseExtension

class DatabaseExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "DatabaseExtension")
        self.enabled = config.get("enabled", True)
        self.database_url = config.get("url")
        self.pool_size = config.get("pool_size", 10)
        self.echo = config.get("echo", False)
        
        self.engine = None
        self.SessionLocal = None
        
    def validate_config(self) -> list[str]:
        errors = []
        if not self.database_url:
            errors.append("database url is required")
        return errors
        
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def database_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    if not self.enabled or not route_config.get("database_enabled", True):
                        return await endpoint(*args, **kwargs)
                    
                    # Create database session for this request
                    db = self.SessionLocal()
                    try:
                        # Add db session to kwargs if endpoint expects it
                        if "db" in endpoint.__code__.co_varnames:
                            kwargs["db"] = db
                            
                        result = await endpoint(*args, **kwargs)
                        db.commit()
                        return result
                        
                    except Exception as e:
                        db.rollback()
                        raise
                    finally:
                        db.close()
                        
                return wrapper
            return database_middleware
        return middleware_factory
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("database_enabled", True)
        
    def get_startup_handler(self):
        async def startup():
            if self.enabled:
                self.engine = create_engine(
                    self.database_url,
                    pool_size=self.pool_size,
                    echo=self.echo
                )
                self.SessionLocal = sessionmaker(bind=self.engine)
                print(f"Database connected: {self.database_url}")
        return startup
        
    def get_shutdown_handler(self):
        async def shutdown():
            if self.engine:
                self.engine.dispose()
                print("Database connection closed")
        return shutdown
```

## Extension Registration

### Module Structure

```
my_extensions/
├── __init__.py
├── auth.py          # AuthExtension
├── logging.py       # LoggingExtension
├── ratelimit.py     # RateLimitExtension
└── database.py      # DatabaseExtension
```

### Configuration

```yaml
extensions:
  # Local extensions
  "my_extensions.auth:AuthExtension":
    secret_key: "${JWT_SECRET}"
    
  "my_extensions.logging:LoggingExtension":
    log_level: "INFO"
    
  # Third-party extensions
  "beginnings_auth.jwt:JWTExtension":
    secret_key: "${JWT_SECRET}"
    algorithm: "HS256"
    
  # Extensions with custom names
  "my_extensions.ratelimit:RateLimitExtension":
    name: "APIRateLimit"
    default_limit: 1000
```

## Extension Utilities

### Helper Base Classes

```python
from typing import Any, Callable
from beginnings.extensions.base import BaseExtension

class SimpleMiddlewareExtension(BaseExtension):
    """Base class for simple middleware extensions"""
    
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def middleware(endpoint: Callable):
                return self.wrap_endpoint(endpoint, route_config)
            return middleware
        return middleware_factory
    
    def wrap_endpoint(self, endpoint: Callable, route_config: dict[str, Any]) -> Callable:
        """Override this method to implement middleware logic"""
        raise NotImplementedError

class ConditionalExtension(BaseExtension):
    """Base class for extensions with simple enable/disable logic"""
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.enabled = config.get("enabled", True)
        
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and self._should_apply(path, methods, route_config)
        
    def _should_apply(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        """Override this method to implement custom logic"""
        return True
```

### Extension Decorators

```python
import functools
from typing import Any, Callable

def extension_middleware(config_key: str = None):
    """Decorator to simplify middleware creation"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(endpoint: Callable, route_config: dict[str, Any], extension_config: dict[str, Any]):
            # Get configuration value
            config_value = route_config.get(config_key) if config_key else None
            return func(endpoint, route_config, extension_config, config_value)
        return wrapper
    return decorator

# Usage:
class MyExtension(BaseExtension):
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            @extension_middleware("timeout")
            def timeout_middleware(endpoint, route_config, extension_config, timeout_value):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    # Implement timeout logic
                    return await endpoint(*args, **kwargs)
                return wrapper
            return timeout_middleware(route_config, self.config)
        return middleware_factory
```

## Testing Extensions

### Unit Testing

```python
import pytest
from my_extensions.logging import LoggingExtension

def test_logging_extension_config():
    config = {
        "name": "TestLogger",
        "log_level": "DEBUG",
        "enabled": True
    }
    extension = LoggingExtension(config)
    assert extension.name == "TestLogger"
    assert extension.log_level == "DEBUG"
    assert extension.enabled is True

def test_logging_extension_validation():
    config = {"log_level": "INVALID"}
    extension = LoggingExtension(config)
    errors = extension.validate_config()
    assert len(errors) == 1
    assert "log_level must be one of" in errors[0]

def test_logging_extension_route_filtering():
    config = {"enabled": True}
    extension = LoggingExtension(config)
    
    # Should apply to routes with logging enabled
    assert extension.should_apply_to_route("/api/users", ["GET"], {"logging_enabled": True})
    
    # Should not apply to routes with logging disabled
    assert not extension.should_apply_to_route("/health", ["GET"], {"logging_enabled": False})
```

### Integration Testing

```python
import pytest
from beginnings import App
from fastapi.testclient import TestClient

@pytest.fixture
def app_with_extensions():
    app = App(config_dir="tests/config")
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
        
    return app

def test_extension_middleware_execution(app_with_extensions):
    client = TestClient(app_with_extensions)
    response = client.get("/test")
    assert response.status_code == 200
    
    # Verify extension effects (logs, headers, etc.)
    # This depends on your specific extension behavior
```

## Best Practices

### Design Principles

1. **Single Responsibility**: Each extension should have one clear purpose
2. **Configuration-Driven**: Make behavior configurable rather than hard-coded
3. **Graceful Degradation**: Extensions should fail gracefully if misconfigured
4. **Performance Conscious**: Minimize overhead in request processing
5. **Security First**: Validate all inputs and handle errors securely

### Configuration

1. **Validate Configuration**: Always implement `validate_config()` method
2. **Provide Defaults**: Use sensible defaults for optional configuration
3. **Document Schema**: Clearly document expected configuration format
4. **Environment Variables**: Support environment variable substitution
5. **Route-Specific Config**: Allow route-level configuration overrides

### Middleware

1. **Preserve Function Signatures**: Use `functools.wraps` for proper introspection
2. **Handle Async/Sync**: Support both async and sync endpoints
3. **Exception Handling**: Properly handle and re-raise exceptions
4. **Request Context**: Extract request objects properly from FastAPI
5. **Performance**: Minimize processing time in middleware

### Lifecycle Management

1. **Resource Cleanup**: Always implement shutdown handlers for resources
2. **Error Isolation**: Don't let extension failures break the application
3. **Logging**: Log extension lifecycle events for debugging
4. **Dependencies**: Handle extension dependencies and load order
5. **Health Checks**: Implement health checks for external dependencies

### Security

1. **Input Validation**: Validate all configuration and request data
2. **Secret Management**: Never log or expose secrets
3. **Path Safety**: Validate file paths and prevent traversal
4. **Rate Limiting**: Implement reasonable limits on resource usage
5. **Error Messages**: Don't expose sensitive information in errors

This guide provides comprehensive coverage of extension development in Beginnings, from basic concepts to advanced patterns and best practices.