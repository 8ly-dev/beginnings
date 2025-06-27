# Enhanced Beginnings Framework Examples

This directory contains comprehensive examples showcasing the full power of the Beginnings web framework. Each example demonstrates different aspects of the framework's capabilities while following security best practices.

## 🚀 Framework Features Demonstrated

All enhanced examples showcase these core Beginnings framework features:

- **Configuration-Driven Architecture**: Everything configured through YAML
- **Multi-Provider Authentication**: Session, JWT, and OAuth support
- **CSRF Protection**: Automatic token injection and validation
- **Advanced Rate Limiting**: Multiple algorithms with distributed support
- **Comprehensive Security Headers**: CSP with nonces, CORS, and more
- **Template Engine Integration**: Secure template rendering with framework features
- **Role-Based Access Control**: Fine-grained permission management
- **Dual Interface Support**: HTML and API endpoints sharing the same backend

## 📂 Enhanced Examples

### 1. Blog Demo (`blog_demo/`)

**What it demonstrates**: Complete blog application with user authentication and content management.

**Key Features**:
- Session-based authentication for web interface
- CSRF protection on all forms (login, registration, post creation)
- Rate limiting (5 login attempts per 5 minutes, 10 posts per minute per user)
- Security headers with CSP nonces for inline scripts
- Template engine with framework integration
- User registration with password validation
- Role-based access (users can create posts, admins can manage all)

**Files**:
- `app_enhanced.py` - Enhanced blog application with full framework integration
- `blog_config.yaml` - Comprehensive configuration showcasing all features
- `templates/` - Framework-integrated templates with security features

**Run it**:
```bash
cd blog_demo
python app_enhanced.py
# Visit: http://localhost:8888
```

**Demo Users**: Any username/password combination works for demo purposes.

### 2. Microservice API (`microservice_api_enhanced.py`)

**What it demonstrates**: Secure API-only microservice with enterprise features.

**Key Features**:
- JWT authentication with token validation
- Role-based API access (user, admin roles)
- Advanced rate limiting (sliding window, token bucket algorithms)
- Comprehensive security headers optimized for APIs
- CORS configuration for cross-origin access
- Health checks and performance monitoring
- OpenAPI documentation with security schemas

**Configuration**: Entirely programmatic configuration demonstrating config-as-code approach.

**Run it**:
```bash
python microservice_api_enhanced.py
# API: http://localhost:8001/api/v1/
# Docs: http://localhost:8001/docs
```

**Authentication**:
```bash
# Get JWT token
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "any"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/v1/users
```

### 3. Mixed Web Application (`mixed_webapp_enhanced.py`)

**What it demonstrates**: The ultimate framework capability - dual HTML/API interfaces with shared backend.

**Key Features**:
- **Dual Authentication**: Session auth for HTML, JWT for API
- **Shared Backend**: Same data and business logic for both interfaces
- **Interface-Specific Security**: CSRF for forms, rate limiting optimized per interface
- **Role-Based Access**: Different permissions for web vs API access
- **Smart Routing**: Automatic route configuration based on interface type
- **Unified Monitoring**: Single health check and metrics for both interfaces

**Run it**:
```bash
python mixed_webapp_enhanced.py
# Web: http://localhost:8002/
# API: http://localhost:8002/api/v1/
# Docs: http://localhost:8002/docs
```

**Demo Users**: `admin`, `manager`, `user` (any password)

## 🔒 Security Features in Action

### CSRF Protection
All forms automatically include CSRF tokens:
```html
<!-- Auto-injected by framework -->
{{ csrf_token() }}

<!-- JavaScript access -->
<script>
const token = getCSRFToken(); // Provided by framework
</script>
```

### Rate Limiting
Different algorithms for different use cases:
```yaml
rate_limiting:
  routes:
    "/login":
      algorithm: "fixed_window"    # Prevent brute force
      requests: 5
      window_seconds: 300
    "/api/users":
      algorithm: "token_bucket"    # Allow bursts
      requests: 100
      burst_size: 10
```

### Security Headers
Comprehensive protection with CSP nonces:
```yaml
security:
  csp:
    nonce:
      enabled: true
      script_nonce: true  # <script nonce="...">
      style_nonce: true   # <style nonce="...">
```

### Multi-Provider Authentication
Flexible authentication options:
```yaml
auth:
  providers:
    session:  # For HTML interface
      cookie_secure: true
      cookie_httponly: true
    jwt:      # For API interface
      algorithm: "HS256"
      token_expire_minutes: 60
```

## 🛠️ Development Workflow

### Configuration-First Development
1. **Define your requirements** in YAML configuration
2. **Write route handlers** using standard FastAPI decorators
3. **Security is automatic** - framework applies configured security
4. **Templates integrate seamlessly** with security features

### Extension Integration
All examples use the same extension pattern:
```python
# Load extensions
auth_ext = AuthExtension(config.get('auth', {}))
csrf_ext = CSRFExtension(config.get('csrf', {}))
rate_limit_ext = RateLimitExtension(config.get('rate_limiting', {}))
security_ext = SecurityHeadersExtension(config.get('security', {}))

# Add to app
app.add_extension("auth", auth_ext)
app.add_extension("csrf", csrf_ext)
app.add_extension("rate_limiting", rate_limit_ext)
app.add_extension("security", security_ext)
```

### Template Security Integration
Templates automatically get security features:
```html
<!DOCTYPE html>
<html>
<head>
    <!-- CSRF token for AJAX -->
    <meta name="csrf-token" content="{{ csrf_token() }}">
    
    <!-- CSP nonce for inline styles -->
    <style nonce="{{ request.state.csp_style_nonce }}">
        /* Secure inline styles */
    </style>
</head>
<body>
    <form method="post">
        <!-- CSRF token auto-injected -->
        {{ csrf_token() }}
        <!-- Form fields -->
    </form>
    
    <!-- CSP nonce for inline scripts -->
    <script nonce="{{ request.state.csp_script_nonce }}">
        // Secure inline JavaScript
    </script>
</body>
</html>
```

## 🧪 Testing the Examples

### Security Feature Testing

**CSRF Protection**:
1. Open browser developer tools
2. Submit any form and check console for CSRF token logging
3. Try submitting without token (should fail)

**Rate Limiting**:
1. Make rapid requests to `/login` endpoint
2. Check response headers for rate limit information
3. Exceed limit and observe 429 status code

**Authentication**:
1. Access protected routes without authentication
2. Login and access the same routes
3. Try accessing admin routes with user account

**Security Headers**:
1. Check response headers in browser developer tools
2. Verify CSP headers include nonces
3. Test CORS headers with cross-origin requests

### API Testing

**JWT Authentication**:
```bash
# Login to get token
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "test"}' | jq -r .access_token)

# Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/v1/users
```

**Rate Limiting**:
```bash
# Test rate limits
for i in {1..15}; do 
  curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/v1/users
  echo "Request $i"
done
```

## 📊 Performance Considerations

### Production Recommendations

**Rate Limiting Storage**:
```yaml
# Use Redis for distributed applications
rate_limiting:
  storage:
    type: "redis"
    redis_url: "redis://localhost:6379"
```

**Session Storage**:
```yaml
# Use Redis for session storage in production
auth:
  providers:
    session:
      storage: "redis"
```

**Security Headers**:
```yaml
# Enable HSTS preload in production
security:
  headers:
    strict_transport_security:
      preload: true
```

### Monitoring

All examples include health checks and metrics:
- `/health` - Application health status
- `/metrics` - Performance and usage metrics

## 🚀 Next Steps

1. **Explore the Configuration**: Study the YAML files to understand configuration patterns
2. **Modify Examples**: Change settings and see how behavior adapts
3. **Build Your App**: Use these examples as starting points for your applications
4. **Add Extensions**: Create custom extensions following the framework patterns
5. **Deploy to Production**: Use production configurations for real deployments

## 📚 Documentation

- **Framework Documentation**: [beginnings.8ly.xyz/docs](https://beginnings.8ly.xyz/docs)
- **Configuration Reference**: See `blog_config.yaml` for comprehensive examples
- **API Documentation**: Available at `/docs` endpoint in each example
- **Security Guide**: Review security configurations in each example

These enhanced examples demonstrate the Beginnings framework's philosophy: **powerful by configuration, secure by default, and extensible by design**.