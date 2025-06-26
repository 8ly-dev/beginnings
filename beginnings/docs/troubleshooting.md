# Troubleshooting Guide

Comprehensive guide for diagnosing and resolving common issues with Beginnings applications.

## Common Issues and Solutions

### Configuration Issues

#### Configuration File Not Found

**Error**: `EnvironmentError: Configuration directory does not exist`

**Cause**: Beginnings can't find your configuration directory.

**Solutions**:
1. Create the configuration directory:
   ```bash
   mkdir config
   ```

2. Set custom configuration directory:
   ```bash
   export BEGINNINGS_CONFIG_DIR=/path/to/config
   ```

3. Specify in code:
   ```python
   app = App(config_dir="./my-config")
   ```

#### YAML Syntax Errors

**Error**: `yaml.scanner.ScannerError: mapping values are not allowed here`

**Cause**: Invalid YAML syntax in configuration files.

**Solutions**:
1. Validate YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/app.yaml'))"
   ```

2. Common YAML issues:
   ```yaml
   # Wrong: missing quotes around values with special characters
   password: my:password!
   
   # Correct: quote values with special characters
   password: "my:password!"
   
   # Wrong: inconsistent indentation
   routes:
     patterns:
       "/api/*":
       cors_enabled: true
   
   # Correct: consistent indentation
   routes:
     patterns:
       "/api/*":
         cors_enabled: true
   ```

#### Environment Variable Issues

**Error**: `KeyError: 'REQUIRED_VAR'` or variables not interpolated

**Cause**: Missing environment variables or interpolation syntax errors.

**Solutions**:
1. Check environment variables:
   ```bash
   echo $REQUIRED_VAR
   env | grep BEGINNINGS
   ```

2. Use default values in configuration:
   ```yaml
   # Wrong: required variable without default
   secret_key: "${SECRET_KEY}"
   
   # Correct: provide default or make optional
   secret_key: "${SECRET_KEY:-default_secret}"
   debug: "${DEBUG:-false}"
   ```

3. Set missing environment variables:
   ```bash
   export SECRET_KEY="your-secret-key"
   export BEGINNINGS_ENV="development"
   ```

#### Include File Conflicts

**Error**: `ConfigurationError: Key 'database' found in both config/app.yaml and config/database.yaml`

**Cause**: Duplicate top-level keys across included files.

**Solutions**:
1. Remove duplicate keys from one of the files
2. Reorganize configuration structure:
   ```yaml
   # config/app.yaml
   app:
     name: "my-app"
   include:
     - "database.yaml"
     - "extensions.yaml"
   
   # config/database.yaml (not config/app.yaml)
   database:
     url: "${DATABASE_URL}"
   
   # Don't repeat 'database' key in app.yaml
   ```

### Extension Issues

#### Extension Import Errors

**Error**: `ModuleNotFoundError: No module named 'my_extensions'`

**Cause**: Extension modules not in Python path.

**Solutions**:
1. Install extension package:
   ```bash
   pip install my-extensions-package
   ```

2. Add to Python path:
   ```python
   import sys
   sys.path.append('/path/to/extensions')
   ```

3. Use proper module path in configuration:
   ```yaml
   extensions:
     # Wrong: relative import
     "extensions.auth:AuthExtension": {}
     
     # Correct: full module path
     "my_package.extensions.auth:AuthExtension": {}
   ```

#### Extension Class Not Found

**Error**: `AttributeError: module 'my_extensions.auth' has no attribute 'AuthExtension'`

**Cause**: Extension class name doesn't match configuration.

**Solutions**:
1. Check class name in module:
   ```python
   # In my_extensions/auth.py
   class AuthExtension(BaseExtension):  # Must match config
       pass
   ```

2. Verify configuration syntax:
   ```yaml
   extensions:
     "my_extensions.auth:AuthExtension":  # module:class format
       secret_key: "${SECRET_KEY}"
   ```

#### Extension Configuration Errors

**Error**: Extension validation fails with configuration errors.

**Cause**: Invalid extension configuration.

**Solutions**:
1. Check extension's `validate_config()` method:
   ```python
   extension = MyExtension(config)
   errors = extension.validate_config()
   print(errors)  # Shows specific validation errors
   ```

2. Review extension documentation for required configuration
3. Use environment variables for missing values:
   ```yaml
   extensions:
     "auth:AuthExtension":
       secret_key: "${JWT_SECRET:-default_secret}"
       token_expiry: 3600
   ```

### Routing Issues

#### Routes Not Found

**Error**: `404 Not Found` for routes that should exist.

**Cause**: Router not included in main application.

**Solutions**:
1. Include router in main app:
   ```python
   app = App()
   html_router = app.create_html_router()
   api_router = app.create_api_router()
   
   # Define routes
   @html_router.get("/")
   def home():
       return "<h1>Home</h1>"
   
   # Include routers
   app.include_router(html_router)
   app.include_router(api_router)
   ```

2. Check route registration:
   ```python
   # Print registered routes
   for route in app.routes:
       print(f"{route.methods} {route.path}")
   ```

#### Middleware Not Executing

**Error**: Extension middleware not running on requests.

**Cause**: Extension not applying to routes or middleware errors.

**Solutions**:
1. Check extension applicability:
   ```python
   extension = MyExtension(config)
   route_config = {"auth_required": True}
   applies = extension.should_apply_to_route("/api/users", ["GET"], route_config)
   print(f"Extension applies: {applies}")
   ```

2. Verify route configuration:
   ```yaml
   routes:
     patterns:
       "/api/*":
         auth_required: true  # Required for auth extension
   ```

3. Check middleware factory:
   ```python
   # Extension middleware should wrap endpoint properly
   def get_middleware_factory(self):
       def middleware_factory(route_config):
           def middleware(endpoint):
               @functools.wraps(endpoint)
               async def wrapper(*args, **kwargs):
                   # Process request
                   result = await endpoint(*args, **kwargs)
                   # Process response
                   return result
               return wrapper
           return middleware
       return middleware_factory
   ```

### Template Issues

#### Template Not Found

**Error**: `TemplateNotFound: home.html`

**Cause**: Template directory not configured or template doesn't exist.

**Solutions**:
1. Configure template directory:
   ```yaml
   templates:
     directory: "templates"  # Relative to app root
   ```

2. Create template directory and files:
   ```bash
   mkdir templates
   echo "<h1>Home</h1>" > templates/home.html
   ```

3. Check template exists:
   ```python
   html_router = app.create_html_router()
   print(html_router.list_templates())  # Shows available templates
   ```

#### Template Rendering Errors

**Error**: `UndefinedError: 'user' is undefined`

**Cause**: Missing variables in template context.

**Solutions**:
1. Provide all required variables:
   ```python
   @html_router.get("/user/{user_id}")
   def user_page(user_id: int, request: Request):
       context = {
           "user": {"id": user_id, "name": f"User {user_id}"},
           "title": "User Profile"  # Add missing variables
       }
       return html_router.render_template_response("user.html", context, request=request)
   ```

2. Use template defaults:
   ```html
   <!-- In template -->
   <h1>{{ title | default("Default Title") }}</h1>
   <p>User: {{ user.name | default("Unknown") }}</p>
   ```

### Static File Issues

#### Static Files Not Served

**Error**: `404 Not Found` for static files like CSS/JS.

**Cause**: Static directories not configured or mounted.

**Solutions**:
1. Configure static directories:
   ```yaml
   static:
     directories:
       - url_path: "/static"
         directory: "static"
   ```

2. Ensure HTMLRouter is included:
   ```python
   html_router = app.create_html_router()
   app.include_router(html_router)  # Mounts static files automatically
   ```

3. Check static directory exists:
   ```bash
   ls -la static/
   ```

4. Verify static file URLs:
   ```html
   <!-- Correct static file URL -->
   <link rel="stylesheet" href="/static/css/style.css">
   ```

### Performance Issues

#### Slow Application Startup

**Cause**: Large configuration files, many extensions, or slow I/O operations.

**Solutions**:
1. Profile startup time:
   ```python
   import time
   start = time.time()
   app = App()
   print(f"App startup took: {time.time() - start:.3f}s")
   ```

2. Optimize configuration:
   ```yaml
   # Use fewer includes
   include:
     - "essential.yaml"  # Combine smaller files
     
   # Reduce extension count
   extensions:
     # Only load necessary extensions
   ```

3. Use lazy loading in extensions:
   ```python
   class MyExtension(BaseExtension):
       def __init__(self, config):
           super().__init__(config)
           self._expensive_resource = None
           
       def get_expensive_resource(self):
           if self._expensive_resource is None:
               self._expensive_resource = create_expensive_resource()
           return self._expensive_resource
   ```

#### High Request Latency

**Cause**: Inefficient middleware, database queries, or extension overhead.

**Solutions**:
1. Profile middleware execution:
   ```python
   import time
   
   def timing_middleware(endpoint):
       @functools.wraps(endpoint)
       async def wrapper(*args, **kwargs):
           start = time.time()
           result = await endpoint(*args, **kwargs)
           duration = time.time() - start
           print(f"{endpoint.__name__}: {duration:.3f}s")
           return result
       return wrapper
   ```

2. Optimize database queries:
   ```python
   # Use connection pooling
   engine = create_engine(url, pool_size=20, max_overflow=0)
   
   # Optimize queries
   users = session.query(User).options(joinedload(User.profile)).all()
   ```

3. Cache expensive operations:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def expensive_computation(param):
       return complex_calculation(param)
   ```

## Debugging Tools

### Enable Debug Mode

```python
# In code
app = App()
app.debug = True

# Via environment
export BEGINNINGS_ENV=development
```

```yaml
# In configuration
app:
  debug: true
```

### Logging Configuration

```yaml
logging:
  level: "DEBUG"
  format: "detailed"
  handlers:
    - console
    - file
  file_path: "logs/app.log"
```

### Request Tracing

```python
from beginnings.extensions.base import BaseExtension

class TracingExtension(BaseExtension):
    def get_middleware_factory(self):
        def middleware_factory(route_config):
            def tracing_middleware(endpoint):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    print(f"→ {endpoint.__name__} called with args={args}, kwargs={kwargs}")
                    result = await endpoint(*args, **kwargs)
                    print(f"← {endpoint.__name__} returned: {type(result)}")
                    return result
                return wrapper
            return tracing_middleware
        return middleware_factory
```

### Configuration Inspection

```python
app = App()

# Print loaded configuration
import json
print(json.dumps(app.get_config(), indent=2))

# Print registered routes
for route in app.routes:
    print(f"{route.methods} {route.path} -> {route.endpoint}")

# Print loaded extensions
for name in app._extension_manager.get_extension_names():
    ext = app._extension_manager.get_extension(name)
    print(f"Extension: {name} ({type(ext).__name__})")
```

## Error Analysis

### Configuration Errors

```python
try:
    app = App(config_dir="./config")
except Exception as e:
    print(f"Configuration error: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Check specific error types
    if "Configuration directory does not exist" in str(e):
        print("Create config directory: mkdir config")
    elif "YAML" in str(e):
        print("Check YAML syntax in configuration files")
```

### Extension Errors

```python
# Check extension loading
try:
    app = App()
except Exception as e:
    if "Extension" in str(e):
        print("Extension loading failed:")
        print(f"Error: {e}")
        
        # Check individual extensions
        config = app.get_config()
        for ext_spec, ext_config in config.get("extensions", {}).items():
            try:
                module_path, class_name = ext_spec.split(":")
                module = __import__(module_path, fromlist=[class_name])
                ext_class = getattr(module, class_name)
                ext = ext_class(ext_config)
                errors = ext.validate_config()
                if errors:
                    print(f"{ext_spec} validation errors: {errors}")
            except Exception as ext_error:
                print(f"{ext_spec} error: {ext_error}")
```

### Runtime Errors

```python
# Add global exception handler
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled error on {request.url}: {exc}")
    print(f"Error type: {type(exc).__name__}")
    
    if app.debug:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "type": type(exc).__name__}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
```

## Environment-Specific Issues

### Development Environment

```bash
# Check environment detection
export BEGINNINGS_DEV_MODE=true
export BEGINNINGS_ENV=development

# Enable detailed logging
export LOG_LEVEL=DEBUG

# Use auto-reload
python -m uvicorn main:app --reload --port 3000
```

### Production Environment

```bash
# Set production environment
export BEGINNINGS_ENV=production

# Use production configuration
export BEGINNINGS_CONFIG_DIR=/etc/myapp

# Set secrets
export SECRET_KEY="production-secret"
export DATABASE_URL="postgresql://user:pass@prod-db/app"

# Use production server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Common Patterns and Solutions

### Graceful Degradation

```python
# Extension with fallback behavior
class CacheExtension(BaseExtension):
    def __init__(self, config):
        super().__init__(config)
        self.redis_client = None
        try:
            import redis
            self.redis_client = redis.Redis(host=config.get("host", "localhost"))
            self.redis_client.ping()  # Test connection
        except:
            print("Redis unavailable, using in-memory cache")
            self._memory_cache = {}
    
    def get(self, key):
        if self.redis_client:
            return self.redis_client.get(key)
        else:
            return self._memory_cache.get(key)
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    status = {"status": "healthy", "checks": {}}
    
    # Check database
    try:
        # Test database connection
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {e}"
        status["status"] = "unhealthy"
    
    # Check extensions
    for name in app._extension_manager.get_extension_names():
        try:
            ext = app._extension_manager.get_extension(name)
            if hasattr(ext, "health_check"):
                ext.health_check()
            status["checks"][name] = "ok"
        except Exception as e:
            status["checks"][name] = f"error: {e}"
            status["status"] = "unhealthy"
    
    return status
```

### Configuration Validation

```python
def validate_app_config(config: dict):
    """Validate application configuration"""
    errors = []
    
    # Check required sections
    if "app" not in config:
        errors.append("Missing 'app' section")
    
    # Validate app section
    app_config = config.get("app", {})
    if not isinstance(app_config.get("port"), int):
        errors.append("app.port must be an integer")
    
    if app_config.get("port", 0) < 1 or app_config.get("port", 0) > 65535:
        errors.append("app.port must be between 1 and 65535")
    
    # Validate extensions
    extensions = config.get("extensions", {})
    for ext_spec in extensions:
        if ":" not in ext_spec:
            errors.append(f"Invalid extension spec: {ext_spec}")
    
    return errors

# Use in application
try:
    app = App()
    errors = validate_app_config(app.get_config())
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
except Exception as e:
    print(f"Failed to load configuration: {e}")
```

This troubleshooting guide provides comprehensive coverage of common issues and their solutions, along with debugging tools and patterns for maintaining healthy Beginnings applications.