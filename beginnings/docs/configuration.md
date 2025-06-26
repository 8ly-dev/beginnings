# Configuration Guide

Complete guide to configuring Beginnings applications with YAML files, environment variables, and includes.

## Configuration Overview

Beginnings uses YAML configuration files with support for:
- Environment-specific configurations
- File includes for modular organization
- Environment variable interpolation
- Route-specific configuration
- Extension configuration

## Configuration File Structure

### Basic Configuration

```yaml
# config/app.yaml
app:
  name: "my-application"
  version: "1.0.0"
  description: "My Beginnings application"
  host: "0.0.0.0"
  port: 8000
  debug: false

routes:
  global_defaults:
    timeout: 30
    rate_limit: 100
  
  patterns:
    "/api/*":
      cors_enabled: true
      rate_limit: 200
    "/admin/*":
      auth_required: true
      timeout: 60
  
  exact:
    "/health":
      rate_limit: 1000
      timeout: 5

extensions:
  "my_package.auth:AuthExtension":
    secret_key: "${AUTH_SECRET_KEY:-default_secret}"
    token_expiry: 3600
  "my_package.logging:LoggingExtension":
    level: "INFO"
    format: "json"
```

## Configuration Sections

### App Section

Basic application configuration:

```yaml
app:
  name: "my-app"              # Application name
  version: "1.0.0"            # Version string
  description: "Description"   # App description
  host: "127.0.0.1"           # Bind host (default: 127.0.0.1)
  port: 8000                  # Bind port (default: 8000)
  debug: false                # Debug mode (default: false)
  title: "API Title"          # OpenAPI title (optional)
  docs_url: "/docs"           # OpenAPI docs URL (optional)
  redoc_url: "/redoc"         # ReDoc URL (optional)
```

### Routes Section

Route-specific configuration with pattern matching:

```yaml
routes:
  # Global defaults applied to all routes
  global_defaults:
    timeout: 30
    rate_limit: 100
    cors_enabled: false
    auth_required: false
    cache_ttl: 300
    
  # Pattern-based configuration (most specific wins)
  patterns:
    "/api/v1/*":              # API v1 routes
      cors_enabled: true
      rate_limit: 200
      auth_required: true
      
    "/api/public/*":          # Public API routes
      cors_enabled: true
      rate_limit: 500
      auth_required: false
      
    "/admin/*":               # Admin routes
      auth_required: true
      rate_limit: 50
      timeout: 60
      admin_only: true
      
    "/static/*":              # Static files
      cache_ttl: 86400
      gzip_enabled: true
      
  # Exact path configuration (highest priority)
  exact:
    "/health":
      rate_limit: 1000
      timeout: 5
      auth_required: false
      
    "/metrics":
      auth_required: true
      admin_only: true
      
    "/api/v1/upload":
      timeout: 120
      max_file_size: "10MB"
      
  # Method-specific configuration (highest priority)
  methods:
    "POST /api/v1/users":
      rate_limit: 10
      validation_strict: true
      
    "DELETE /api/v1/users/*":
      auth_required: true
      admin_only: true
```

### Extensions Section

Extension configuration with module:class format:

```yaml
extensions:
  # Authentication extension
  "my_package.auth:AuthExtension":
    name: "Authentication"
    enabled: true
    secret_key: "${JWT_SECRET_KEY}"
    algorithm: "HS256"
    token_expiry: 3600
    refresh_enabled: true
    
  # Rate limiting extension
  "my_package.ratelimit:RateLimitExtension":
    name: "RateLimit"
    enabled: true
    storage: "redis"
    redis_url: "${REDIS_URL:-redis://localhost:6379}"
    default_limit: 100
    burst_limit: 150
    
  # Logging extension
  "my_package.logging:LoggingExtension":
    name: "RequestLogger"
    enabled: true
    level: "${LOG_LEVEL:-INFO}"
    format: "json"
    include_request_body: false
    include_response_body: false
    
  # CORS extension
  "my_package.cors:CORSExtension":
    name: "CORS"
    enabled: true
    allow_origins: ["https://myapp.com", "https://app.myapp.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Content-Type", "Authorization"]
    allow_credentials: true
    max_age: 3600
```

## Environment Configuration

### Environment Detection

Beginnings automatically detects the environment using:

1. `BEGINNINGS_DEV_MODE` environment variable (highest priority)
2. `BEGINNINGS_ENV` environment variable
3. Defaults to "production"

```bash
# Force development mode
export BEGINNINGS_DEV_MODE=true

# Set specific environment
export BEGINNINGS_ENV=staging

# Custom config directory
export BEGINNINGS_CONFIG_DIR=/etc/myapp
```

### Environment-Specific Files

Configuration files are loaded based on environment:

- **Production**: `app.yaml`
- **Development**: `app.dev.yaml` (fallback to `app.yaml`)
- **Staging**: `app.staging.yaml` (fallback to `app.yaml`)
- **Custom**: `app.{environment}.yaml` (fallback to `app.yaml`)

### Environment Variables

Override configuration values using environment variables with `BEGINNINGS_` prefix:

```bash
# Override app configuration
export BEGINNINGS_APP_PORT=3000
export BEGINNINGS_APP_DEBUG=true
export BEGINNINGS_APP_HOST="0.0.0.0"

# Override nested configuration
export BEGINNINGS_DATABASE_URL="postgresql://user:pass@localhost/prod_db"
```

## Environment Variable Interpolation

Use environment variables in configuration files:

```yaml
app:
  name: "${APP_NAME:-my-app}"           # With default value
  secret: "${SECRET_KEY}"               # Required variable
  debug: "${DEBUG:-false}"              # Boolean with default
  port: "${PORT:-8000}"                 # Integer with default

database:
  url: "${DATABASE_URL}"
  pool_size: "${DB_POOL_SIZE:-10}"
  
redis:
  url: "${REDIS_URL:-redis://localhost:6379}"
  
extensions:
  "auth:AuthExtension":
    secret_key: "${JWT_SECRET}"
    issuer: "${JWT_ISSUER:-myapp}"
    audience: "${JWT_AUDIENCE:-api}"
```

**Syntax:**
- `${VAR_NAME}`: Required variable (fails if missing)
- `${VAR_NAME:-default}`: Optional with default value
- Variables are resolved after all files are merged

## Configuration Includes

Split configuration across multiple files for better organization:

### Main Configuration

```yaml
# config/app.yaml
app:
  name: "my-application"
  version: "1.0.0"

# Include other configuration files
include:
  - "database.yaml"
  - "extensions.yaml"
  - "routes.yaml"
```

### Database Configuration

```yaml
# config/database.yaml
database:
  url: "${DATABASE_URL}"
  pool_size: 10
  echo: false
  
cache:
  backend: "redis"
  url: "${REDIS_URL:-redis://localhost:6379}"
  ttl: 300
```

### Extensions Configuration

```yaml
# config/extensions.yaml
extensions:
  "auth:AuthExtension":
    secret_key: "${JWT_SECRET}"
    token_expiry: 3600
    
  "logging:LoggingExtension":
    level: "${LOG_LEVEL:-INFO}"
    format: "json"
```

### Routes Configuration

```yaml
# config/routes.yaml
routes:
  global_defaults:
    timeout: 30
    
  patterns:
    "/api/*":
      cors_enabled: true
      auth_required: true
```

### Include Rules

- Include paths are relative to configuration directory
- Included files processed in order specified
- Circular includes are detected and rejected
- Missing included files cause startup failure
- Top-level key conflicts between files cause startup failure

## Template Configuration

Configure template engines for HTMLRouter:

```yaml
templates:
  directory: "templates"        # Template directory
  auto_reload: true            # Auto-reload in development
  enable_async: true           # Enable async templates
  encoding: "utf-8"            # Template encoding
  
  # Jinja2-specific options
  jinja_options:
    trim_blocks: true
    lstrip_blocks: true
    keep_trailing_newline: false
    extensions:
      - "jinja2.ext.do"
      - "jinja2.ext.loopcontrols"
    
  # Template globals (available in all templates)
  globals:
    app_name: "${APP_NAME:-My App}"
    version: "1.0.0"
    
  # Template filters
  filters:
    currency: "my_filters.currency_filter"
    humanize: "my_filters.humanize_filter"
```

## Static File Configuration

Configure static file serving for HTMLRouter:

```yaml
static:
  directories:
    - url_path: "/static"
      directory: "static"
      max_file_size: 10485760    # 10MB
      cache_control: "public, max-age=3600"
      
    - url_path: "/assets"
      directory: "assets"
      allowed_extensions: [".css", ".js", ".png", ".jpg", ".gif"]
      max_file_size: 5242880     # 5MB
      cache_control: "public, max-age=86400"
      gzip: true
      
    - url_path: "/uploads"
      directory: "uploads"
      auth_required: true
      max_file_size: 52428800    # 50MB
      allowed_extensions: [".pdf", ".doc", ".docx"]
```

## CORS Configuration

Configure Cross-Origin Resource Sharing:

```yaml
cors:
  # Global CORS settings
  global:
    allow_origins: ["https://myapp.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Content-Type", "Authorization"]
    allow_credentials: true
    expose_headers: ["X-Total-Count"]
    max_age: 3600
    
  # Route-specific CORS
  routes:
    "/api/public/*":
      allow_origins: ["*"]
      allow_credentials: false
      
    "/api/webhook":
      allow_origins: ["https://webhook-provider.com"]
      allow_methods: ["POST"]
```

## Security Configuration

Security-related configuration options:

```yaml
security:
  # Secret key for cryptographic operations
  secret_key: "${SECRET_KEY}"
  
  # HTTPS enforcement
  force_https: true
  hsts_max_age: 31536000
  
  # Content Security Policy
  csp:
    default_src: "'self'"
    script_src: "'self' 'unsafe-inline'"
    style_src: "'self' 'unsafe-inline'"
    
  # File upload security
  upload:
    max_file_size: "10MB"
    allowed_mime_types:
      - "image/jpeg"
      - "image/png"
      - "application/pdf"
    scan_uploads: true
    
  # Rate limiting
  rate_limit:
    enabled: true
    default_limit: 100
    burst_multiplier: 1.5
    
  # Authentication
  auth:
    session_timeout: 3600
    max_login_attempts: 5
    lockout_duration: 900
```

## Development Configuration

Development-specific settings:

```yaml
# config/app.dev.yaml
app:
  debug: true
  port: 3000
  
templates:
  auto_reload: true
  
static:
  directories:
    - url_path: "/static"
      directory: "static"
      cache_control: "no-cache"
      
logging:
  level: "DEBUG"
  format: "colored"
  
security:
  force_https: false
  
extensions:
  "dev_tools:DevToolsExtension":
    enabled: true
    profiler: true
    debugger: true
```

## Production Configuration

Production-optimized settings:

```yaml
# config/app.yaml (production)
app:
  debug: false
  host: "0.0.0.0"
  port: 8000
  
templates:
  auto_reload: false
  
static:
  directories:
    - url_path: "/static"
      directory: "static"
      cache_control: "public, max-age=86400"
      gzip: true
      
logging:
  level: "WARNING"
  format: "json"
  
security:
  force_https: true
  hsts_max_age: 31536000
  
rate_limit:
  enabled: true
  storage: "redis"
  redis_url: "${REDIS_URL}"
```

## Configuration Validation

Beginnings validates configuration at startup:

### Schema Validation
- Required sections: `app`
- Optional sections: `routes`, `extensions`, `templates`, `static`, etc.
- Type checking for all configuration values
- Range validation for numeric values

### Security Validation
- Prevents dangerous YAML constructs
- Validates file paths for safety
- Checks extension import paths
- Prevents path traversal in includes
- Validates environment variable syntax

### Conflict Detection
- Detects duplicate keys in included files
- Validates route pattern conflicts
- Checks extension name conflicts
- Reports configuration inconsistencies

## Best Practices

### Organization
1. **Use includes** to split configuration logically
2. **Environment-specific files** for environment differences
3. **Environment variables** for secrets and deployment-specific values
4. **Clear naming** for configuration keys

### Security
1. **Never commit secrets** to configuration files
2. **Use environment variables** for sensitive data
3. **Validate all inputs** in extension configurations
4. **Restrict file paths** in includes and static directories

### Performance
1. **Cache configurations** in production
2. **Minimize pattern complexity** in route configuration
3. **Use specific patterns** over broad wildcards
4. **Optimize extension order** for performance

### Maintenance
1. **Document custom configurations** for extensions
2. **Version configuration schemas** when changing structure
3. **Test configuration changes** in staging environments
4. **Monitor configuration loading** performance

This configuration guide covers all aspects of Beginnings configuration management, from basic setup to advanced patterns and security considerations.