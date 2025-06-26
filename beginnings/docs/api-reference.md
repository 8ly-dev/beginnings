# API Reference

Complete reference for all public APIs in the Beginnings framework.

## App Class

The main application class that serves as the foundation for Beginnings applications.

### Constructor

```python
from beginnings import App

# Basic usage (no configuration required)
app = App()

# With configuration directory
app = App(config_dir="./config")

# With specific environment
app = App(config_dir="./config", environment="production")

# With FastAPI parameters
app = App(title="My API", version="1.0.0")
```

**Parameters:**
- `config_dir` (str, optional): Directory containing configuration files. Defaults to auto-detection.
- `environment` (str, optional): Environment name. Auto-detected if not provided.
- `**fastapi_kwargs`: Additional arguments passed to the underlying FastAPI application.

### Methods

#### `create_html_router(**router_kwargs) -> HTMLRouter`

Creates an HTML router for browser-facing pages.

```python
# Basic HTML router
html_router = app.create_html_router()

# With prefix and tags
html_router = app.create_html_router(prefix="/web", tags=["html"])

# Register routes
@html_router.get("/")
def home():
    return "<h1>Welcome!</h1>"

# Include in app
app.include_router(html_router)
```

#### `create_api_router(**router_kwargs) -> APIRouter`

Creates an API router for JSON APIs.

```python
# Basic API router
api_router = app.create_api_router()

# With prefix and tags
api_router = app.create_api_router(prefix="/api/v1", tags=["api"])

# Register routes
@api_router.get("/users")
def get_users():
    return {"users": []}

# Include in app
app.include_router(api_router)
```

#### `get_config() -> dict[str, Any]`

Returns the loaded configuration.

```python
config = app.get_config()
print(config["app"]["name"])  # Application name
print(config["routes"])       # Route configurations
```

#### `get_extension(extension_name: str) -> BaseExtension | None`

Retrieves a loaded extension by name.

```python
auth_extension = app.get_extension("AuthExtension")
if auth_extension:
    print(f"Extension loaded: {auth_extension.name}")
```

#### `get_environment() -> str`

Returns the detected environment.

```python
env = app.get_environment()  # "development", "production", etc.
```

#### `reload_configuration() -> None`

Reloads configuration from files (if configuration loader is available).

```python
app.reload_configuration()  # Reloads config files
```

#### `run(host: str = "127.0.0.1", port: int = 8000, **kwargs) -> None`

Runs the application using uvicorn.

```python
# Basic run
app.run()

# Custom host and port
app.run(host="0.0.0.0", port=3000)

# With uvicorn options
app.run(reload=True, workers=4)
```

### Properties

The App class inherits all FastAPI properties and methods, so you can use standard FastAPI features:

```python
# Add middleware
app.add_middleware(SomeMiddleware)

# Direct route registration
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Mount sub-applications
app.mount("/static", StaticFiles(directory="static"))
```

## HTMLRouter Class

Enhanced router for HTML responses with template and static file support.

### Template Methods

#### `render_template(template_name: str, context: dict = None, request: Request = None) -> str`

Renders a template to HTML string.

```python
html_router = app.create_html_router()

@html_router.get("/user/{user_id}")
def user_page(user_id: int, request: Request):
    context = {"user": {"id": user_id, "name": f"User {user_id}"}}
    return html_router.render_template("user.html", context, request)
```

#### `render_template_response(template_name: str, context: dict = None, status_code: int = 200, headers: dict = None, request: Request = None) -> HTMLResponse`

Renders a template and returns an HTMLResponse.

```python
@html_router.get("/")
def home(request: Request):
    context = {"title": "Home Page", "message": "Welcome!"}
    return html_router.render_template_response("home.html", context, request=request)
```

#### `template_exists(template_name: str) -> bool`

Checks if a template exists.

```python
if html_router.template_exists("special.html"):
    # Template is available
    pass
```

#### `list_templates() -> list[str]`

Lists all available templates.

```python
templates = html_router.list_templates()
print(f"Available templates: {templates}")
```

### Static File Methods

#### `add_static_directory(url_path: str, directory: str, **config) -> None`

Adds a static file directory.

```python
# Add static directory
html_router.add_static_directory("/static", "./static")

# With custom configuration
html_router.add_static_directory(
    "/assets", 
    "./assets", 
    max_file_size=5*1024*1024,  # 5MB limit
    cache_control="public, max-age=3600"
)
```

#### `list_static_directories() -> dict[str, dict[str, Any]]`

Lists configured static directories.

```python
static_dirs = html_router.list_static_directories()
for path, config in static_dirs.items():
    print(f"Static path: {path} -> {config['directory']}")
```

### Template Configuration

Configure templates in your configuration file:

```yaml
templates:
  directory: "templates"
  auto_reload: true  # For development
  enable_async: true
  jinja_options:
    trim_blocks: true
    lstrip_blocks: true
```

### Static File Configuration

Configure static files in your configuration file:

```yaml
static:
  directories:
    - url_path: "/static"
      directory: "static"
      max_file_size: 10485760  # 10MB
      cache_control: "public, max-age=3600"
    - url_path: "/assets"
      directory: "assets"
      allowed_extensions: [".css", ".js", ".png", ".jpg"]
```

## APIRouter Class

Enhanced router for JSON APIs with CORS and OpenAPI support.

### CORS Methods

#### `add_cors_for_route(route_path: str, cors_config: dict) -> None`

Adds CORS configuration for a specific route.

```python
api_router = app.create_api_router()

# Add CORS for specific route
api_router.add_cors_for_route("/api/public", {
    "allow_origins": ["*"],
    "allow_methods": ["GET", "POST"],
    "allow_credentials": False
})
```

#### `has_cors_for_route(route_path: str) -> bool`

Checks if CORS is configured for a route.

```python
if api_router.has_cors_for_route("/api/users"):
    print("CORS is configured for /api/users")
```

#### `get_cors_config_for_route(route_path: str) -> dict | None`

Gets CORS configuration for a route.

```python
cors_config = api_router.get_cors_config_for_route("/api/users")
if cors_config:
    print(f"Allowed origins: {cors_config['allow_origins']}")
```

### CORS Configuration

Configure CORS in your configuration file:

```yaml
cors:
  global:
    allow_origins: ["https://myapp.com", "https://app.myapp.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Content-Type", "Authorization"]
    allow_credentials: true
    max_age: 3600
  routes:
    "/api/public":
      allow_origins: ["*"]
      allow_credentials: false
```

### Standard FastAPI Features

Both HTMLRouter and APIRouter support all standard FastAPI router features:

```python
# Route parameters
@router.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

# Query parameters
@router.get("/search")
def search(q: str, limit: int = 10):
    return {"query": q, "limit": limit}

# Request body
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str

@router.post("/users")
def create_user(user: UserCreate):
    return {"created": user.dict()}

# Dependencies
from fastapi import Depends

def get_current_user():
    return {"user": "current"}

@router.get("/profile")
def get_profile(user=Depends(get_current_user)):
    return user

# Response models
@router.get("/users/{user_id}", response_model=UserCreate)
def get_user(user_id: int):
    return UserCreate(name="John", email="john@example.com")
```

## BaseExtension Class

Abstract base class for creating extensions.

### Required Methods

#### `__init__(self, config: dict[str, Any]) -> None`

Extension constructor that receives configuration.

```python
from beginnings.extensions.base import BaseExtension

class MyExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "MyExtension")
        self.enabled = config.get("enabled", True)
```

#### `get_middleware_factory(self) -> Callable[[dict[str, Any]], Callable]`

Returns a middleware factory function.

```python
def get_middleware_factory(self):
    def middleware_factory(route_config: dict[str, Any]):
        def middleware(endpoint: Callable):
            @functools.wraps(endpoint)
            def wrapper(*args, **kwargs):
                # Pre-processing
                result = endpoint(*args, **kwargs)
                # Post-processing
                return result
            return wrapper
        return middleware
    return middleware_factory
```

#### `should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool`

Determines if the extension should apply to a route.

```python
def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
    # Apply to all routes if enabled
    if not self.enabled:
        return False
    
    # Apply only to specific paths
    return path.startswith("/api/")
```

### Optional Methods

#### `validate_config(self) -> list[str]`

Validates extension configuration and returns error messages.

```python
def validate_config(self) -> list[str]:
    errors = []
    if not isinstance(self.config.get("api_key"), str):
        errors.append("api_key must be a string")
    return errors
```

#### `get_startup_handler(self) -> Optional[Callable[[], Awaitable[None]]]`

Returns an async startup handler.

```python
def get_startup_handler(self):
    async def startup():
        print(f"Starting {self.name}")
        # Initialize resources
    return startup
```

#### `get_shutdown_handler(self) -> Optional[Callable[[], Awaitable[None]]]`

Returns an async shutdown handler.

```python
def get_shutdown_handler(self):
    async def shutdown():
        print(f"Shutting down {self.name}")
        # Clean up resources
    return shutdown
```

### Complete Extension Example

```python
import functools
from typing import Any, Callable, Optional, Awaitable
from beginnings.extensions.base import BaseExtension

class LoggingExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "LoggingExtension")
        self.enabled = config.get("enabled", True)
        self.log_level = config.get("log_level", "INFO")
    
    def validate_config(self) -> list[str]:
        errors = []
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if self.log_level not in valid_levels:
            errors.append(f"log_level must be one of: {valid_levels}")
        return errors
    
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def logging_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                def wrapper(*args, **kwargs):
                    print(f"[{self.log_level}] Calling {endpoint.__name__}")
                    result = endpoint(*args, **kwargs)
                    print(f"[{self.log_level}] Finished {endpoint.__name__}")
                    return result
                return wrapper
            return logging_middleware
        return middleware_factory
    
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("logging_enabled", True)
    
    def get_startup_handler(self):
        async def startup():
            print(f"LoggingExtension started with level: {self.log_level}")
        return startup
```

### Extension Configuration

Configure extensions in your configuration file:

```yaml
extensions:
  "my_package.logging:LoggingExtension":
    name: "RequestLogger"
    enabled: true
    log_level: "INFO"
  "my_package.auth:AuthExtension":
    name: "Authentication"
    enabled: true
    secret_key: "${AUTH_SECRET_KEY:-default_secret}"
```

## Error Classes

The framework provides structured error handling with context.

### BeginningsError

Base exception class for all framework errors.

```python
from beginnings.core.errors import BeginningsError

try:
    # Framework operation
    pass
except BeginningsError as e:
    print(f"Error: {e}")
    print(f"Context: {e.get_context()}")
```

### Specific Error Types

- **ConfigurationError**: Configuration loading and validation errors
- **ExtensionError**: Extension loading and runtime errors
- **RoutingError**: Router and middleware errors
- **ValidationError**: Schema and security validation errors

```python
from beginnings.core.errors import ConfigurationError, ExtensionError

try:
    app = App(config_dir="./invalid")
except ConfigurationError as e:
    print(f"Config error: {e.get_actionable_message()}")
```

## Utility Functions

### Response Helpers

```python
from beginnings.routing.html import create_html_response
from beginnings.routing.api import create_api_response, create_error_response

# HTML response
html_resp = create_html_response("<h1>Success</h1>", status_code=200)

# API success response
api_resp = create_api_response(
    data={"users": []}, 
    message="Users retrieved successfully"
)

# API error response
error_resp = create_error_response(
    message="User not found",
    error_code="USER_NOT_FOUND",
    status_code=404
)
```

### CORS Utilities

```python
from beginnings.routing.cors import get_cors_preset, CORSConfig

# Use security presets
dev_cors = get_cors_preset("development")
prod_cors = get_cors_preset("production")

# Create custom CORS config
cors_config = CORSConfig(
    allow_origins=["https://myapp.com"],
    allow_methods=["GET", "POST"],
    allow_credentials=True
)
```

This API reference covers all public APIs with practical examples. For more detailed information, see the other documentation sections.