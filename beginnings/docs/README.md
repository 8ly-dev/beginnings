# Beginnings Documentation

Complete documentation for the Beginnings web framework.

## Getting Started

- [**API Reference**](api-reference.md) - Complete reference for all public APIs
- [**Configuration Guide**](configuration.md) - Configuration files, patterns, and best practices
- [**Extension Development**](extension-development.md) - Creating custom extensions

## Guides

- [**Troubleshooting**](troubleshooting.md) - Common issues and solutions
- [**Performance Guide**](performance.md) - Optimization and monitoring

## Quick Links

### Core Concepts

- **App Class**: Main application class extending FastAPI
- **HTMLRouter**: Router for browser-facing pages with template support
- **APIRouter**: Router for JSON APIs with CORS support
- **Extensions**: Modular plugins for adding functionality

### Configuration

```yaml
app:
  name: "my-application"
  port: 8000

routes:
  patterns:
    "/api/*":
      cors_enabled: true
    "/admin/*":
      auth_required: true

extensions:
  "my_package.auth:AuthExtension":
    secret_key: "${SECRET_KEY}"
```

### Basic Usage

```python
from beginnings import App

# Create application
app = App()

# Create routers
html_router = app.create_html_router()
api_router = app.create_api_router()

# Define routes
@html_router.get("/")
def home():
    return "<h1>Welcome!</h1>"

@api_router.get("/users")
def get_users():
    return {"users": []}

# Include routers
app.include_router(html_router)
app.include_router(api_router)

# Run application
if __name__ == "__main__":
    app.run()
```

### Extension Example

```python
from beginnings.extensions.base import BaseExtension

class LoggingExtension(BaseExtension):
    def get_middleware_factory(self):
        def middleware_factory(route_config):
            def logging_middleware(endpoint):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    print(f"Calling {endpoint.__name__}")
                    result = await endpoint(*args, **kwargs)
                    print(f"Finished {endpoint.__name__}")
                    return result
                return wrapper
            return logging_middleware
        return middleware_factory
    
    def should_apply_to_route(self, path, methods, route_config):
        return route_config.get("logging_enabled", True)
```

## Framework Architecture

Beginnings is built on several key components:

1. **Configuration System**
   - Environment detection and loading
   - YAML configuration with includes
   - Environment variable interpolation
   - Route-specific configuration resolution

2. **Routing Infrastructure**
   - HTMLRouter for browser-facing pages
   - APIRouter for machine-to-machine APIs
   - Configuration-driven middleware chains
   - Template and static file support

3. **Extension System**
   - Plugin architecture for modularity
   - Middleware factories for request processing
   - Lifecycle hooks for startup/shutdown
   - Configuration validation and injection

4. **Error Handling**
   - Structured error hierarchy
   - Actionable error messages
   - Security-conscious error reporting
   - Development vs production error modes

## Documentation Structure

### [API Reference](api-reference.md)
Complete reference for all public APIs including:
- App class methods and properties
- HTMLRouter template and static file features
- APIRouter CORS and OpenAPI features
- BaseExtension interface and patterns
- Error classes and utility functions

### [Configuration Guide](configuration.md)
Comprehensive configuration documentation covering:
- Basic and advanced configuration patterns
- Environment-specific configurations
- Include system for modular organization
- Route configuration and pattern matching
- Extension configuration and validation
- Security and performance considerations

### [Extension Development Guide](extension-development.md)
Complete guide to creating extensions including:
- Extension interface and lifecycle
- Middleware patterns and best practices
- Configuration handling and validation
- Testing strategies for extensions
- Security and performance considerations
- Real-world extension examples

### [Troubleshooting Guide](troubleshooting.md)
Problem-solving resource covering:
- Common configuration issues
- Extension loading and runtime problems
- Routing and middleware issues
- Template and static file problems
- Performance and memory issues
- Debugging tools and techniques

### [Performance Guide](performance.md)
Optimization and monitoring documentation including:
- Framework performance characteristics
- Configuration and extension optimization
- Database and routing optimization
- Monitoring and profiling tools
- Production deployment best practices
- Performance testing strategies

## Community and Support

- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Join community discussions and get help
- **Contributing**: See CONTRIBUTING.md for development guidelines
- **Security**: Report security issues privately

## License

Beginnings is released under the MIT License. See LICENSE file for details.

---

*This documentation covers Beginnings v0.1.0. For the latest updates, see the project repository.*