# Phase 2: Bundled Extensions Development - Detailed Implementation Plan

## Overview
Implement the core security and functionality extensions that ship with beginnings. These extensions demonstrate best practices for extension development while providing essential features for production applications. Each extension follows the BaseExtension interface established in Phase 1 and integrates seamlessly with the configuration and routing systems.

## Prerequisites from Previous Phases
- ✅ **Phase 0**: Project foundation with uv, testing framework, code quality tools
- ✅ **Phase 1**: Core infrastructure fully operational
  - Configuration loading with include system and conflict detection
  - Environment detection and override system
  - HTMLRouter and APIRouter classes with configuration integration
  - Extension loading mechanism with BaseExtension interface
  - Route configuration resolution system with pattern matching
  - Middleware chain building and execution framework

## Phase 2 Detailed Architecture Goals

### Public Extension Interfaces

#### Extension Configuration Interface
Each bundled extension exposes its configuration through a well-defined schema that integrates with the framework's configuration system:

**Configuration Section Structure**:
- Extension configuration lives in dedicated top-level section (e.g., `auth:`, `csrf:`, `rate_limiting:`)
- Route-specific overrides supported through route configuration patterns
- Environment variable interpolation supported throughout extension configuration
- Configuration validation happens during extension initialization
- Schema definitions provided for IDE support and validation tools

**Configuration Application Behavior**:
- Global extension settings provide defaults for all applicable routes
- Route pattern matching allows targeted configuration (e.g., `/admin/*` gets different auth settings)
- Exact route paths can override pattern-based configuration
- Method-specific configuration supported where relevant (GET vs POST behavior)
- Configuration inheritance follows same rules as core framework

#### Extension Middleware Interface
Extensions provide middleware through a factory pattern that allows route-specific customization:

**Middleware Factory Contract**:
```python
def get_middleware_factory(self) -> Callable[[Dict[str, Any]], Callable]:
    """Returns function that creates middleware for specific route configuration"""
    
def create_middleware(route_config: Dict[str, Any]) -> Callable:
    """Created by factory, receives merged route configuration"""
    
async def middleware(request: Request, call_next: Callable) -> Response:
    """Actual middleware function with FastAPI signature"""
```

**Middleware Behavior Expectations**:
- Middleware receives request and call_next function following FastAPI patterns
- Route-specific configuration available through route_config parameter
- Middleware should call call_next(request) to continue processing
- Middleware can modify request before calling next middleware
- Middleware can modify response after next middleware returns
- Middleware should handle exceptions gracefully and not crash application

#### Extension Lifecycle Interface
Extensions can participate in application startup and shutdown:

**Lifecycle Handler Contract**:
```python
def get_startup_handler(self) -> Optional[Callable[[], Awaitable[None]]]
def get_shutdown_handler(self) -> Optional[Callable[[], Awaitable[None]]]
```

**Lifecycle Behavior**:
- Startup handlers called during application initialization, after configuration loaded
- Shutdown handlers called during application shutdown, before process termination
- Handlers are async functions that can perform I/O operations
- Startup handler failures prevent application from starting
- Shutdown handlers run even if startup failed (for cleanup)
- Handlers should be idempotent (safe to call multiple times)

### Complex Extension System Specifications

#### Authentication Extension Architecture
**Multi-Provider Authentication System**:
The authentication extension supports multiple authentication mechanisms simultaneously, with route-specific provider selection and unified user context.

**Provider Selection Logic**:
- Routes can specify which authentication provider to use
- Default provider used if route doesn't specify
- Multiple providers can be configured simultaneously
- Provider fallback chain supported (try JWT, fall back to session)
- Per-route provider configuration overrides global defaults

**User Context Injection**:
- Successful authentication injects user information into request context
- User context available to route handlers as request.user
- User context includes identity, roles, permissions, and provider metadata
- User context follows consistent structure regardless of authentication provider
- User context persists through middleware chain and route handler execution

**Role-Based Access Control Integration**:
- Roles defined in configuration with associated permissions
- Routes can require specific roles or permissions
- Role inheritance supported (admin inherits user permissions)
- Role checking happens after authentication, before route handler
- Role failures return configured error responses (JSON for APIs, redirects for HTML)

#### CSRF Protection Extension Architecture
**Token Management System**:
The CSRF extension provides stateless and stateful token validation with template integration.

**Token Generation and Validation**:
- Tokens generated using cryptographically secure random data
- HMAC-based validation for stateless operation
- Session-based storage for stateful operation
- Double-submit cookie pattern supported for single-page applications
- Token expiration configurable per route or globally

**Template Integration Behavior**:
- Template functions automatically registered with template engine
- Forms automatically receive CSRF tokens through template context
- Hidden input fields generated automatically for form protection
- Meta tags injected for AJAX and single-page application access
- Template integration works with any template engine (Jinja2, etc.)

**AJAX and API Support**:
- CSRF tokens available through meta tags for JavaScript access
- Custom header support for AJAX request validation
- API routes can be exempted from CSRF protection
- JSON error responses for API endpoints
- HTML error pages for browser-based requests

#### Rate Limiting Extension Architecture
**Multi-Algorithm Rate Limiting System**:
The rate limiting extension supports multiple algorithms with different characteristics for various use cases.

**Algorithm Selection and Behavior**:
- Sliding window: Precise rate limiting with timestamp-based tracking
- Token bucket: Burst-friendly limiting with token replenishment
- Fixed window: Simple time-window based limiting with reset points
- Algorithm selection per route or globally configurable
- Algorithm parameters (window size, bucket capacity) configurable

**Storage Backend Abstraction**:
- In-memory storage for single-instance applications
- Redis/Valkey storage for distributed applications
- Storage backend selection through configuration
- Automatic failover between storage backends
- Storage backend interface allows custom implementations

**Rate Limit Identifier Resolution**:
- IP address-based limiting for anonymous requests
- User-based limiting for authenticated requests
- API key-based limiting for API access
- Custom identifier extraction through configuration
- Identifier fallback chain (user -> IP -> default)

#### Security Headers Extension Architecture
**Comprehensive Header Management System**:
The security headers extension provides configurable security headers with route-specific customization.

**Content Security Policy Integration**:
- CSP directives built from configuration
- Nonce generation for inline scripts and styles
- Hash-based CSP for static inline content
- Violation reporting endpoint configuration
- Report-only mode for testing CSP policies

**Header Customization System**:
- Global headers applied to all responses
- Route-specific header overrides supported
- Header removal supported for specific routes (set to null)
- Environment-specific header values supported
- Header value templating with dynamic content

**CORS Integration**:
- Cross-origin request handling integrated with security headers
- Preflight request handling for complex CORS requests
- Origin validation against configured whitelist
- Credentials handling with security considerations
- CORS error responses with debugging information

### Extension Integration Patterns

#### Configuration Integration Pattern
**Unified Configuration Resolution**:
Extensions participate in the same configuration resolution system as the core framework, ensuring consistent behavior and precedence rules.

**Configuration Merge Behavior**:
1. Extension configuration loaded from dedicated section
2. Route patterns in extension config matched against actual routes
3. Route-specific overrides merged with global extension configuration
4. Final configuration passed to extension middleware factory
5. Configuration changes trigger middleware chain rebuilding

**Configuration Validation Flow**:
1. Extension validates its configuration section during initialization
2. Configuration schema validation happens at startup
3. Invalid configuration prevents application startup
4. Configuration warnings logged but don't prevent startup
5. Runtime configuration changes validated before application

#### Middleware Integration Pattern
**Chain Building and Execution**:
Extensions integrate into a unified middleware chain that ensures proper ordering and execution.

**Middleware Ordering Rules**:
- Extensions applied in order they appear in configuration
- Security extensions (auth, CSRF) typically run before business logic extensions
- Response processing extensions (headers) typically run last
- Extension priority configurable through configuration order
- Middleware execution follows LIFO pattern (last registered runs first)

**Error Handling Integration**:
- Extension middleware failures isolated from other extensions
- Extension errors logged with context information
- Core framework continues operating if extension fails
- Extension failures trigger health check warnings
- Error responses follow route configuration (JSON vs HTML)

#### Extension Interoperability
**Cross-Extension Communication**:
Extensions can interact with each other through well-defined patterns while maintaining isolation.

**Shared Context Pattern**:
- Request context shared between extensions through request attributes
- Authentication extension sets request.user for other extensions
- Rate limiting extension can use request.user for user-based limiting
- Extensions document their context contributions
- Context modifications follow naming conventions to prevent conflicts

**Extension Dependency Management**:
- Extensions can declare dependencies on other extensions
- Dependency validation happens at startup
- Missing dependencies prevent application startup
- Extension compatibility matrix maintained in documentation
- Version compatibility checking supported

## Bundled Extension Detailed Specifications

### Authentication Extension Architecture

**Extension Configuration Structure**:
```yaml
auth:
  # Provider configuration
  provider: jwt  # jwt, session, oauth, or multiple
  providers:
    jwt:
      secret_key: ${JWT_SECRET}
      algorithm: HS256
      token_expire_minutes: 30
      issuer: "beginnings-app"
      audience: "beginnings-users"
    session:
      secret_key: ${SESSION_SECRET}
      session_timeout: 3600
      cookie_name: "session_id"
      cookie_secure: true
      cookie_httponly: true
      cookie_samesite: "strict"
    oauth:
      google:
        client_id: ${GOOGLE_CLIENT_ID}
        client_secret: ${GOOGLE_CLIENT_SECRET}
        scopes: ["openid", "email", "profile"]
      github:
        client_id: ${GITHUB_CLIENT_ID}
        client_secret: ${GITHUB_CLIENT_SECRET}
        scopes: ["user:email"]

  # Route-based authentication requirements
  protected_routes:
    "/admin/*":
      required: true
      roles: ["admin"]
      provider: jwt
      redirect_unauthorized: "/login"
    "/api/user/*":
      required: true
      roles: ["user", "admin"]
      provider: jwt
      error_unauthorized: {"error": "authentication required"}
    "/dashboard":
      required: true
      redirect_unauthorized: "/login"

  # Authentication pages and redirects
  routes:
    login:
      path: "/login"
      template: "auth/login.html"
      redirect_after_login: "/dashboard"
      methods: ["GET", "POST"]
    logout:
      path: "/logout"
      redirect_after_logout: "/"
      methods: ["POST"]
    register:
      path: "/register"
      template: "auth/register.html"
      redirect_after_register: "/dashboard"
      enabled: true

  # Role-based access control
  rbac:
    roles:
      user:
        description: "Standard user access"
        permissions: ["read:profile", "update:profile"]
      admin:
        description: "Administrative access"
        permissions: ["*"]  # All permissions
        inherits: ["user"]
    
  # Security settings
  security:
    password_min_length: 8
    password_require_special: true
    password_require_number: true
    account_lockout_attempts: 5
    account_lockout_duration: 900  # 15 minutes
```

**AuthExtension Integration Behavior**:
- **Route Applicability**: Applies to routes matching patterns in `protected_routes` configuration
- **Middleware Factory**: Creates authentication middleware that checks tokens/sessions before route handler
- **Configuration Resolution**: Merges global auth config with route-specific requirements
- **Provider Selection**: Uses specified provider or defaults from global configuration
- **Error Handling**: Returns configured error responses or redirects based on route configuration
- **User Context**: Injects authenticated user information into request context for route handlers

**Authentication Middleware Execution Flow**:
1. Extract authentication token/session from request (headers, cookies)
2. Validate token/session using configured provider (JWT verification, session lookup)
3. Load user information and roles from authentication provider
4. Check route-specific role requirements against user roles
5. If authentication fails: return configured error response or redirect
6. If authentication succeeds: inject user context and continue to route handler
7. Handle token refresh and session management as configured

**Authentication Provider Implementations**:
- **JWT Provider**: Token generation, validation, refresh, and user claim extraction
- **Session Provider**: Session creation, validation, storage, and cleanup
- **OAuth Provider**: OAuth flow handling, token exchange, and user profile fetching
- **Multi-Provider**: Support multiple authentication methods simultaneously

### CSRF Protection Extension Architecture

**Extension Configuration Structure**:
```yaml
csrf:
  # Token generation and validation
  enabled: true
  token_name: "csrf_token"
  token_length: 32
  token_expire_minutes: 60
  double_submit_cookie: true
  
  # Route application rules
  protected_methods: ["POST", "PUT", "PATCH", "DELETE"]
  protected_routes:
    "/admin/*":
      enabled: true
      custom_error: "CSRF token validation failed for admin action"
    "/api/*":
      enabled: false  # APIs typically use other authentication
  
  # Template integration
  template_integration:
    enabled: true
    template_function_name: "csrf_token"
    form_field_name: "csrf_token"
    meta_tag_name: "csrf-token"
  
  # AJAX and SPA support
  ajax:
    header_name: "X-CSRFToken"
    cookie_name: "csrftoken"
    javascript_function: "getCSRFToken"
  
  # Error handling
  error_handling:
    template: "errors/csrf_error.html"
    json_response: {"error": "CSRF token validation failed"}
    status_code: 403
```

**CSRFExtension Integration Behavior**:
- **Route Applicability**: Applies to routes matching protected patterns and methods
- **Middleware Factory**: Creates CSRF validation middleware for state-changing requests
- **Token Management**: Generates tokens per session/request and validates on submission
- **Template Integration**: Provides template functions for token injection in forms
- **AJAX Support**: Supports token extraction and validation for AJAX requests
- **Error Handling**: Returns appropriate error responses based on request type (HTML vs JSON)

**CSRF Middleware Execution Flow**:
1. Check if request method requires CSRF protection (POST, PUT, PATCH, DELETE)
2. Check if route requires CSRF protection based on configuration patterns
3. If protection required: extract CSRF token from form data, headers, or cookies
4. Validate token against stored session token or double-submit cookie
5. If validation fails: return configured error response (HTML page or JSON)
6. If validation succeeds: continue to route handler
7. Generate new token for response if needed (template rendering or AJAX)

**Template Integration Implementation**:
- **Form Token Injection**: Automatic hidden input field generation for forms
- **Meta Tag Integration**: CSRF token injection in HTML head for AJAX access
- **Template Functions**: `csrf_token()` function available in all templates
- **Conditional Rendering**: Token injection only for routes requiring CSRF protection

### Rate Limiting Extension Architecture

**Extension Configuration Structure**:
```yaml
rate_limiting:
  # Storage backend
  storage:
    type: memory  # memory, redis, valkey
    redis_url: ${REDIS_URL}  # if using redis/valkey
    key_prefix: "beginnings:ratelimit:"
  
  # Global rate limiting
  global:
    algorithm: sliding_window  # sliding_window, token_bucket, fixed_window
    requests: 1000
    window_seconds: 3600  # 1 hour
    identifier: ip  # ip, user, api_key
  
  # Route-specific rate limiting
  routes:
    "/api/*":
      algorithm: token_bucket
      requests: 100
      window_seconds: 60
      burst_size: 10
      identifier: user  # requires authentication
      error_template: "errors/api_rate_limit.html"
      error_json: {"error": "API rate limit exceeded", "retry_after": "{retry_after}"}
    
    "/login":
      algorithm: fixed_window
      requests: 5
      window_seconds: 300  # 5 minutes
      identifier: ip
      error_template: "errors/login_rate_limit.html"
      
    "/admin/*":
      requests: 50
      window_seconds: 60
      identifier: user
      roles_multiplier:
        admin: 2.0  # Admins get 2x rate limit
        
  # Algorithm-specific settings
  algorithms:
    sliding_window:
      precision_seconds: 1
      cleanup_interval: 300
    token_bucket:
      refill_rate: 1.0  # tokens per second
      max_tokens: 100
    fixed_window:
      window_alignment: start  # start, end
  
  # Response headers
  headers:
    include_headers: true
    remaining_header: "X-RateLimit-Remaining"
    limit_header: "X-RateLimit-Limit"
    reset_header: "X-RateLimit-Reset"
    retry_after_header: "Retry-After"
```

**RateLimitExtension Integration Behavior**:
- **Route Applicability**: Applies rate limiting based on route patterns and global configuration
- **Middleware Factory**: Creates rate limiting middleware that tracks and enforces limits
- **Algorithm Implementation**: Supports multiple rate limiting algorithms with different characteristics
- **Storage Backend**: Supports in-memory and distributed storage for rate limit counters
- **Identifier Resolution**: Determines rate limit key based on IP, user, or API key
- **Error Responses**: Returns appropriate error responses with retry information

**Rate Limiting Middleware Execution Flow**:
1. Determine rate limit identifier (IP address, user ID, API key) from request
2. Resolve rate limit configuration for route (global + route-specific)
3. Check current rate limit status using configured algorithm and storage
4. If limit exceeded: return error response with retry-after information
5. If limit not exceeded: increment counter and add rate limit headers to response
6. Continue to route handler with updated rate limit status
7. Include rate limit headers in response for client awareness

**Rate Limiting Algorithm Implementations**:
- **Sliding Window**: Precise rate limiting with timestamp-based request tracking
- **Token Bucket**: Burst-friendly rate limiting with token replenishment
- **Fixed Window**: Simple time-window based rate limiting with reset points
- **Distributed Support**: Consistent rate limiting across multiple application instances

### Security Headers Extension Architecture

**Extension Configuration Structure**:
```yaml
security:
  # Security headers configuration
  headers:
    # Basic security headers
    x_frame_options: "DENY"  # DENY, SAMEORIGIN, ALLOW-FROM
    x_content_type_options: "nosniff"
    x_xss_protection: "0"  # Deprecated, set to 0 to disable
    strict_transport_security:
      max_age: 31536000  # 1 year
      include_subdomains: true
      preload: false
    referrer_policy: "strict-origin-when-cross-origin"
    
    # Advanced security headers
    permissions_policy:
      geolocation: []  # No origins allowed
      camera: ["self"]
      microphone: ["self"]
      payment: ["self", "https://payment.example.com"]
    
    cross_origin_embedder_policy: "require-corp"
    cross_origin_opener_policy: "same-origin"
    cross_origin_resource_policy: "same-origin"
  
  # Content Security Policy
  csp:
    enabled: true
    report_only: false  # Set to true for testing
    directives:
      default_src: ["'self'"]
      script_src: ["'self'", "'unsafe-inline'"]  # Consider removing unsafe-inline
      style_src: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
      img_src: ["'self'", "data:", "https:"]
      font_src: ["'self'", "https://fonts.gstatic.com"]
      connect_src: ["'self'"]
      frame_ancestors: ["'none'"]
      base_uri: ["'self'"]
      form_action: ["'self'"]
    
    # CSP reporting
    report_uri: "/csp-report"
    report_to: "csp-endpoint"
    
    # Nonce generation for inline scripts/styles
    nonce:
      enabled: true
      script_nonce: true
      style_nonce: true
      nonce_length: 16
  
  # Route-specific overrides
  routes:
    "/admin/*":
      csp:
        script_src: ["'self'"]  # Stricter CSP for admin
        style_src: ["'self'"]
    "/api/*":
      headers:
        # APIs don't need browser security headers
        x_frame_options: null
        csp: null
    "/embed/*":
      headers:
        x_frame_options: "SAMEORIGIN"  # Allow embedding
  
  # CORS configuration
  cors:
    enabled: true
    allow_origins: ["https://app.example.com"]
    allow_methods: ["GET", "POST", "PUT", "DELETE"]
    allow_headers: ["Content-Type", "Authorization", "X-Requested-With"]
    expose_headers: ["X-Request-ID"]
    allow_credentials: true
    max_age: 86400  # 24 hours
```

**SecurityHeadersExtension Integration Behavior**:
- **Route Applicability**: Applies security headers to all routes with route-specific overrides
- **Middleware Factory**: Creates middleware that adds security headers to responses
- **CSP Integration**: Generates Content Security Policy headers with nonce support
- **CORS Handling**: Manages cross-origin requests with configurable policies
- **Header Customization**: Supports route-specific header customization and removal
- **Performance Optimization**: Caches compiled headers for repeated use

**Security Headers Middleware Execution Flow**:
1. Determine applicable security headers for route based on configuration
2. Generate nonces for CSP if enabled (unique per request)
3. Compile CSP directives with nonces and route-specific overrides
4. Handle CORS preflight requests if applicable
5. Continue to route handler (headers added to response later)
6. Add security headers to response based on route configuration
7. Include CSP nonces in template context if template rendering

**Content Security Policy Implementation**:
- **Directive Building**: Compile CSP directives from configuration
- **Nonce Generation**: Generate cryptographically secure nonces per request
- **Template Integration**: Provide nonces to templates for inline scripts/styles
- **Violation Reporting**: Support CSP violation reporting endpoints
- **Testing Mode**: Report-only mode for testing CSP policies

## Extension Development Patterns and Integration

### Configuration Pattern Implementation
**Extension Configuration Loading**:
1. Extension receives full configuration section during initialization
2. Extension validates configuration structure and required parameters
3. Extension caches parsed configuration for performance
4. Extension supports environment-specific configuration overrides
5. Extension provides configuration schema for validation

**Route Configuration Resolution Integration**:
1. Extension registers route patterns in configuration
2. Route configuration resolver merges extension config with route-specific overrides
3. Extension middleware factory receives merged configuration for each route
4. Extension determines applicability based on merged configuration
5. Extension applies behavior based on final resolved configuration

### Middleware Integration Pattern
**Middleware Factory Implementation**:
```python
def get_middleware_factory(self) -> Callable[[Dict[str, Any]], Callable]:
    def create_middleware(route_config: Dict[str, Any]):
        # Extract extension-specific config from route_config
        extension_config = route_config.get(self.config_key, {})
        
        async def middleware(request: Request, call_next: Callable):
            # Pre-processing: authentication, validation, rate limiting
            try:
                # Extension-specific logic here
                result = await self._process_request(request, extension_config)
                if result:  # Authentication failed, rate limited, etc.
                    return result
                
                # Continue to route handler
                response = await call_next(request)
                
                # Post-processing: headers, logging, cleanup
                await self._process_response(request, response, extension_config)
                return response
                
            except Exception as e:
                # Extension-specific error handling
                return await self._handle_error(request, e, extension_config)
        
        return middleware
    return create_middleware
```

**Extension Interaction Patterns**:
- **Authentication + CSRF**: CSRF protection applies after successful authentication
- **Rate Limiting + Authentication**: Rate limiting can use authenticated user identity
- **Security Headers + All**: Security headers applied to all responses regardless of other extensions
- **Extension Ordering**: Configurable extension priority determines middleware execution order

### Extension Lifecycle Integration
**Startup Integration**:
1. Extension loading during application initialization
2. Extension configuration validation before route registration
3. Extension resource initialization (database connections, cache setup)
4. Extension middleware factory registration with router system
5. Extension health check and monitoring setup

**Runtime Integration**:
1. Route configuration resolution includes extension configuration
2. Middleware chain building queries extension applicability
3. Extension middleware execution with error isolation
4. Extension performance monitoring and metrics collection
5. Extension configuration hot-reloading support (development mode)

**Shutdown Integration**:
1. Extension cleanup and resource disposal
2. Extension state persistence if required
3. Extension graceful shutdown with request completion
4. Extension error reporting and logging
5. Extension dependency cleanup coordination

## Phase 2 Detailed Implementation Stages

## Stage 1: Test-Driven Development - Authentication Extension

### 1.1 JWT Authentication Implementation Tests
**Test File**: `tests/extensions/auth/test_jwt.py`

**JWT Token Management Tests**:
- Generate valid JWT tokens with configurable claims and expiration
- Validate JWT signatures using configured secret key and algorithm
- Handle token expiration with appropriate error responses
- Support token refresh mechanisms with rotation
- Extract user information and roles from token claims
- Test multiple JWT algorithms (HS256, HS512, RS256)
- Handle malformed and tampered tokens gracefully

**JWT Configuration Integration Tests**:
- Load JWT configuration from extension configuration section
- Apply route-specific JWT requirements (roles, expiration)
- Handle missing configuration parameters with defaults
- Validate JWT secret key security and rotation
- Test JWT issuer and audience validation
- Configuration hot-reloading for development

**JWT Middleware Integration Tests**:
- Apply JWT authentication to configured routes only
- Extract JWT tokens from Authorization header and cookies
- Inject authenticated user context into request for route handlers
- Handle authentication failure with configured error responses
- Support multiple JWT providers simultaneously
- Performance testing with JWT validation overhead

### 1.2 Session Authentication Implementation Tests
**Test File**: `tests/extensions/auth/test_sessions.py`

**Session Management Tests**:
- Create secure session IDs with cryptographic randomness
- Store and retrieve session data using configured storage backend
- Handle session expiration and cleanup automatically
- Support session renewal and sliding expiration
- Secure session cookie configuration (HttpOnly, Secure, SameSite)
- Session fixation attack prevention

**Session Storage Integration Tests**:
- In-memory session storage for development
- Redis/Valkey session storage for production
- Database session storage with cleanup
- Session data serialization and deserialization
- Session storage performance and scalability
- Session storage failure handling and graceful degradation

### 1.3 Role-Based Access Control Tests
**Test File**: `tests/extensions/auth/test_rbac.py`

**Permission System Tests**:
- Define roles with specific permissions
- Check user permissions against route requirements
- Support permission inheritance between roles
- Handle permission denial with appropriate responses
- Dynamic permission checking during request processing
- Permission caching and performance optimization

**RBAC Configuration Integration Tests**:
- Load role and permission definitions from configuration
- Apply route-specific role requirements
- Support multiple authentication providers with RBAC
- Role-based rate limiting and feature access
- RBAC audit logging and monitoring
- Role management and assignment patterns

### 1.4 OAuth Integration Implementation Tests
**Test File**: `tests/extensions/auth/test_oauth.py`

**OAuth Flow Implementation Tests**:
- Authorization code flow with PKCE for security
- State parameter validation for CSRF protection
- Token exchange and validation with OAuth providers
- User profile information retrieval and mapping
- OAuth provider configuration and registration
- OAuth error handling and user feedback

**OAuth Provider Integration Tests**:
- Google OAuth integration with OpenID Connect
- GitHub OAuth integration with user profile access
- Generic OAuth 2.0 provider support
- Multiple OAuth provider support simultaneously
- OAuth token refresh and expiration handling
- OAuth provider failure fallback and error handling

## Stage 2: Test-Driven Development - CSRF Protection Extension

### 2.1 CSRF Token Management Implementation Tests
**Test File**: `tests/extensions/csrf/test_tokens.py`

**Token Generation and Validation Tests**:
- Generate cryptographically secure CSRF tokens
- Validate tokens using HMAC or similar secure methods
- Support double-submit cookie pattern for stateless validation
- Handle token expiration and renewal
- Token storage in sessions or encrypted cookies
- Token uniqueness and collision resistance

**CSRF Security Implementation Tests**:
- Timing attack resistance in token validation
- Same-origin policy enforcement
- Referer header validation as additional protection
- CSRF token binding to user sessions
- Protection against token prediction attacks
- CSRF bypass attempt detection and logging

### 2.2 Template Integration Implementation Tests
**Test File**: `tests/extensions/csrf/test_templates.py`

**Template Function Integration Tests**:
- CSRF token injection in HTML forms automatically
- Hidden input field generation with correct token
- Meta tag token embedding for AJAX access
- Template context processor integration
- Conditional token injection based on route configuration
- Template error handling and fallback

**Template Engine Compatibility Tests**:
- Jinja2 template integration and function registration
- Custom template engine support patterns
- Template inheritance and token propagation
- Template caching with token generation
- Template performance impact measurement
- Template security and token exposure prevention

### 2.3 AJAX and SPA Support Implementation Tests
**Test File**: `tests/extensions/csrf/test_ajax.py`

**AJAX Integration Tests**:
- Token extraction from meta tags for JavaScript
- Token inclusion in AJAX request headers
- Token validation for JSON API requests
- CSRF token refresh for long-lived pages
- SPA (Single Page Application) token management
- AJAX error handling and token renewal

**JavaScript Integration Tests**:
- JavaScript function generation for token access
- Token extraction and inclusion utilities
- CSRF error handling in JavaScript
- Token refresh mechanisms for SPAs
- Cross-frame token access (if required)
- JavaScript security and token protection

## Stage 3: Test-Driven Development - Rate Limiting Extension

### 3.1 Rate Limiting Algorithm Implementation Tests
**Test File**: `tests/extensions/rate_limiting/test_algorithms.py`

**Sliding Window Algorithm Tests**:
- Accurate request counting within time windows
- Window sliding and boundary handling
- Memory-efficient request timestamp storage
- High-frequency request processing
- Sliding window precision and performance
- Window cleanup and memory management

**Token Bucket Algorithm Tests**:
- Token generation and replenishment rates
- Burst request handling with bucket capacity
- Token bucket state persistence
- Bucket overflow and underflow handling
- Distributed token bucket coordination

**Fixed Window Algorithm Tests**:
- Window reset timing and synchronization
- Request counting accuracy within windows
- Window boundary edge case handling
- Memory usage optimization for fixed windows
- Distributed window coordination
- Window reset race condition handling

### 3.2 Storage Backend Implementation Tests
**Test File**: `tests/extensions/rate_limiting/test_storage.py`

**In-Memory Storage Tests**:
- Thread-safe counter operations
- Memory cleanup and garbage collection
- Process-local rate limiting accuracy
- Concurrent access handling

**Redis/Valkey Storage Tests**:
- Distributed counter operations with atomicity
- Connection pooling and failure handling
- Redis transaction support for accuracy
- Network latency impact on rate limiting
- Redis cluster support and coordination
- Storage backend fallback mechanisms

### 3.3 Rate Limiting Configuration Integration Tests
**Test File**: `tests/extensions/rate_limiting/test_config.py`

**Route-Specific Configuration Tests**:
- Apply different rate limits to different route patterns
- Route pattern matching and precedence handling
- Method-specific rate limiting (GET vs POST)
- User-based vs IP-based rate limiting
- Role-based rate limit multipliers
- Dynamic rate limit configuration updates

**Identifier Resolution Tests**:
- IP address extraction and normalization
- Authenticated user identification
- API key-based rate limiting
- Custom identifier extraction patterns
- Identifier fallback and error handling
- Privacy considerations for identifier storage

## Stage 4: Test-Driven Development - Security Headers Extension

### 4.1 Security Headers Implementation Tests
**Test File**: `tests/extensions/security_headers/test_headers.py`

**Basic Security Headers Tests**:
- X-Frame-Options header with DENY/SAMEORIGIN/ALLOW-FROM
- X-Content-Type-Options nosniff header
- Strict-Transport-Security header with max-age and options
- Referrer-Policy header with various policy options
- X-XSS-Protection header (disabled by default as deprecated)
- Custom security header support and configuration

**Advanced Security Headers Tests**:
- Permissions-Policy header with feature control
- Cross-Origin-Embedder-Policy header
- Cross-Origin-Opener-Policy header
- Cross-Origin-Resource-Policy header
- Security header combinations and interactions
- Browser compatibility and fallback handling

### 4.2 Content Security Policy Implementation Tests
**Test File**: `tests/extensions/security_headers/test_csp.py`

**CSP Directive Generation Tests**:
- CSP directive compilation from configuration
- Nonce generation and injection for inline content
- Hash calculation for inline scripts and styles
- CSP directive validation and syntax checking
- CSP browser compatibility and fallbacks
- CSP policy testing and validation

**CSP Nonce Integration Tests**:
- Cryptographically secure nonce generation per request
- Nonce injection in template context automatically
- Nonce inclusion in script and style tags
- Nonce validation and security properties
- Nonce performance impact measurement
- Nonce template integration patterns

### 4.3 CORS Implementation Tests
**Test File**: `tests/extensions/security_headers/test_cors.py**

**CORS Request Handling Tests**:
- Preflight request handling with proper headers
- Simple CORS request processing
- Origin validation against whitelist
- Method and header validation
- Credentials handling and security
- CORS error responses and debugging

**CORS Configuration Integration Tests**:
- Route-specific CORS configuration
- Dynamic origin validation patterns
- CORS configuration inheritance and overrides
- CORS performance optimization
- CORS security considerations and validation
- CORS browser compatibility and testing

## Stage 5-9: Extension Implementation, Integration, and Verification

[Detailed implementation stages follow the same pattern as Phase 1, with specific focus on:]

### Extension Implementation Details
- **Configuration Schema Definition**: JSON Schema for each extension's configuration
- **Middleware Factory Implementation**: Creating route-specific middleware from configuration
- **Route Applicability Logic**: Determining which routes each extension applies to
- **Performance Optimization**: Caching, efficient algorithms, minimal overhead
- **Error Handling**: Graceful failure and clear error messages
- **Security Implementation**: Following security best practices and preventing common vulnerabilities

### Integration Testing Focus
- **Cross-Extension Compatibility**: Extensions working together without conflicts
- **Configuration Resolution**: Route configuration correctly merged from all sources
- **Middleware Chain Execution**: Proper ordering and execution of multiple extension middleware
- **Performance Impact**: Acceptable performance overhead with all extensions enabled
- **Error Isolation**: Extension failures not affecting other extensions or core functionality

### Security Verification Requirements
- **Authentication Security**: Secure token handling, session management, and password policies
- **CSRF Protection**: Cryptographically secure token generation and validation
- **Rate Limiting**: Accurate enforcement without bypass vulnerabilities
- **Security Headers**: Comprehensive protection against common web vulnerabilities
- **Configuration Security**: Secure defaults and validation of security-critical settings

## Phase 2 Completion Criteria

Phase 2 is complete when:

1. **All Bundled Extensions Fully Functional**:
   - Authentication extension supports JWT, sessions, OAuth, and RBAC
   - CSRF protection works for forms, AJAX, and API requests
   - Rate limiting accurately enforces limits with multiple algorithms
   - Security headers provide comprehensive protection
   - All extensions integrate seamlessly with core framework

2. **Extension Integration Patterns Established**:
   - Configuration patterns work consistently across all extensions
   - Middleware factory pattern implemented correctly in all extensions
   - Route applicability determination works accurately
   - Extension lifecycle management functions properly
   - Error handling and isolation work correctly

3. **Security Standards Met**:
   - All security verification checklists completed
   - Cryptographic implementations follow best practices
   - Default configurations prioritize security
   - Security testing validates against common attack vectors
   - Security documentation explains all security features

4. **Performance Requirements Met**:
   - Extension overhead minimal compared to base FastAPI
   - Configuration resolution performance acceptable
   - Middleware execution overhead within budgets
   - Memory usage stable with all extensions enabled
   - Startup time impact minimal

5. **Ready for Phase 3 Developer Tools**:
   - Extension development patterns clearly established
   - Configuration validation framework supports all extensions
   - Extension testing patterns documented and working
   - Extension development templates ready for Phase 3
   - Performance characteristics documented for optimization

This detailed implementation plan provides comprehensive guidance for building production-ready security extensions that integrate seamlessly with the beginnings framework while demonstrating best practices for extension development.