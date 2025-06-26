# Beginnings: Web Framework Architecture Plan

## Overview

**Framework Name:** `beginnings`

A minimal, thoughtful web framework built on FastAPI that provides essential infrastructure - configuration loading, HTML/API routing, and extension loading - while keeping everything else as optional, loadable extensions.

The core philosophy: provide a solid foundation with just what you need to get started, then let you add exactly the features you want through a simple, powerful extension system.

## Core Architecture Principles

### Minimal Core Philosophy
- **Configuration Infrastructure**: Single config file with include system and environment support
- **Routing Infrastructure**: Separate HTML and API routers with clear boundaries
- **Extension Infrastructure**: Dynamic loading system for functionality extensions
- **Nothing Else**: Authentication, security, caching, etc. are all optional extensions

### Configuration-First Design
- All application behavior controlled through YAML configuration
- Extensions loaded and configured declaratively
- Environment-specific overrides without code changes
- Fail-fast validation with clear error messages

### Extension Everything Architecture
- Core framework provides only the loading mechanism
- All features (auth, CSRF, rate limiting) implemented as extensions
- Bundled extensions for common needs
- Third-party extension ecosystem support

## Project Structure Design

```
my-app/
├── config/
│   ├── app.yaml              # Single base configuration hub
│   ├── auth.yaml             # Authentication configuration (included)
│   ├── security.yaml         # Security configuration (included)  
│   ├── app.dev.yaml          # Development environment overrides
│   ├── app.staging.yaml      # Staging environment overrides
│   └── extensions/           # Custom extension configurations
│       └── analytics.yaml
├── routes/
│   ├── __init__.py
│   └── pages.py              # Business logic routes
├── templates/                # HTML templates
├── static/                   # Static assets
└── main.py                   # Minimal bootstrap
```

## Configuration Architecture

### Single Config with Includes
- **Base Config**: One `app.yaml` file as the configuration hub
- **Include System**: Reference other config files via `include` directive
- **Conflict Detection**: Duplicate keys across included files cause startup failure
- **Merge Strategy**: Simple `dict.update()` - no deep merging complexity

### Environment Override Strategy
- **Base Environment**: `app.yaml` for production (clean path)
- **Environment Files**: `app.{environment}.yaml` for overrides
- **Environment Detection**: Via `BEGINNINGS_ENV` and `BEGINNINGS_DEV_MODE`
- **Fallback Logic**: Environment files can fall back to base if missing

### Configuration Loading Priority
1. Load base config file (`app.yaml` or `app.{env}.yaml`)
2. Process `include` directive and load referenced files
3. Merge included configs with conflict detection
4. Apply environment variables for runtime values
5. Validate final configuration structure

## Routing Architecture

### Dual Router Design
- **HTML Router**: Optimized for browser interactions, defaults to HTML responses
- **API Router**: Optimized for machine-to-machine, defaults to JSON responses
- **Clear Separation**: No content negotiation - explicit routing choices
- **FastAPI Integration**: Uses native FastAPI mounting system

### Route Configuration Resolution
- **Pattern Matching**: Wildcard patterns (`/admin/*`, `/api/*`) for broad rules
- **Exact Matching**: Specific paths for precise control
- **Method Specificity**: Different rules per HTTP method
- **Precedence Rules**: Exact paths override patterns, method-specific overrides general

### Standard Decorator Enhancement
- Enhance existing `@app.get()`, `@app.post()` decorators
- Automatic configuration application based on route patterns
- No new decorators or syntax to learn
- Transparent middleware chain building

## Extension System Architecture

### Extension Loading Mechanism
- **Import Path Specification**: `"module.path:ClassName"` in configuration
- **Dynamic Loading**: Extensions loaded at startup via importlib
- **Configuration Injection**: Each extension receives relevant config section
- **Lifecycle Management**: Startup/shutdown hooks for extension cleanup

### Extension Interface Design
- **Middleware Factory Pattern**: Extensions provide middleware creation functions
- **Route Applicability**: Extensions decide which routes they apply to
- **Configuration Driven**: All extension behavior controlled via YAML
- **Standard Interface**: Consistent API across all extensions

### Bundled Extension Strategy
- **Common Extensions Included**: Auth, CSRF, rate limiting, security headers
- **Optional Usage**: Even bundled extensions must be explicitly enabled
- **Reference Implementations**: Show best practices for extension development
- **Production Ready**: Full-featured implementations, not just examples

## Environment Management Strategy

### Environment Detection Logic
- **Development Mode**: `BEGINNINGS_DEV_MODE=true` forces dev environment
- **Explicit Environment**: `BEGINNINGS_ENV` variable for specific environments
- **Production Default**: No environment variables defaults to production
- **Config Directory**: `BEGINNINGS_CONFIG_DIR` for custom config locations

### Environment-Specific Behavior
- **Development**: Relaxed security, debug modes, auto-reload features
- **Staging**: Production-like security with testing accommodations
- **Production**: Full security, performance optimizations, minimal logging
- **Custom Environments**: Support for arbitrary environment names

## Security and Safety Design

### Configuration Safety
- **Startup Validation**: All configuration errors detected before serving requests
- **Conflict Detection**: Duplicate configuration keys cause immediate failure
- **Environment Interpolation**: Safe handling of environment variables in config
- **Schema Validation**: Configuration structure validation against expected schemas

### Extension Safety
- **Isolation**: Extensions cannot interfere with core framework operation
- **Error Handling**: Extension failures don't crash the application
- **Permission Model**: Extensions only access their configured sections
- **Validation**: Extension configurations validated before loading

## Development Experience Design

### Minimal Setup Requirements
- Single import: `from beginnings import App`
- Zero configuration for basic usage
- Standard FastAPI patterns throughout
- Familiar project structure

### Configuration Experience
- **Single Source of Truth**: One config file to understand the application
- **Clear Error Messages**: Helpful feedback for configuration problems
- **Environment Flexibility**: Easy switching between dev/staging/production
- **Extension Discovery**: Clear patterns for finding and using extensions

### Extension Development Experience
- **Standard Interface**: Consistent pattern for creating extensions
- **Configuration Integration**: Extensions receive their config automatically
- **Middleware Patterns**: Clear patterns for adding functionality to routes
- **Community Friendly**: Easy to share and install third-party extensions

## Implementation Phases

### Phase 1: Core Infrastructure
- Configuration loading system with include support
- Environment detection and override logic
- Basic HTML and API router implementation
- Extension loading mechanism

### Phase 2: Bundled Extensions
- Authentication extension (JWT, sessions, RBAC)
- CSRF protection extension
- Rate limiting extension
- Security headers extension

### Phase 3: Developer Experience
- CLI tools for project scaffolding
- Configuration validation tools
- Development server with auto-reload
- Extension development templates

### Phase 4: Ecosystem Support
- Documentation and examples
- Community extension guidelines
- Migration tools from other frameworks

## Success Criteria

### For Developers
- Can create a working web application with minimal configuration
- Can add security features without writing security code
- Can deploy to different environments without code changes
- Can extend functionality through clear extension patterns

### For AI Agents
- Cannot accidentally remove security protections
- Use standard FastAPI patterns without framework-specific knowledge
- Focus on business logic without infrastructure concerns
- Benefit from automatic security application based on route patterns

### For Operations
- Clear separation between application logic and configuration
- Environment-specific deployments without code changes
- Predictable startup behavior with clear error reporting
- Extensible architecture that grows with application needs

This architecture provides a thoughtful foundation that grows with your needs - starting simple but scaling to handle complex applications through its powerful extension system.