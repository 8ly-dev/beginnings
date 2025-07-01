# {{ project_name_title }}

A web application built with the beginnings framework.

## Features

{% if include_html %}
- 🌐 **HTML Interface**: Server-rendered web pages with templates
{% endif %}
{% if include_api %}
- 🔌 **RESTful API**: JSON API endpoints with automatic documentation
{% endif %}
{% if include_auth %}
- 🔐 **Authentication**: Multi-provider authentication (session + JWT)
{% endif %}
{% if include_csrf %}
- 🛡️ **CSRF Protection**: Automatic CSRF token handling
{% endif %}
{% if include_rate_limiting %}
- ⚡ **Rate Limiting**: Advanced rate limiting with multiple algorithms
{% endif %}
{% if include_security_headers %}
- 🔒 **Security Headers**: Comprehensive security headers with CSP
{% endif %}
- ⚙️ **Configuration-Driven**: Everything configured through YAML
- 🔧 **Developer Tools**: CLI tools for development and deployment

## Getting Started

### Prerequisites

- Python 3.9 or higher
- uv (recommended) or pip

### Installation

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run the development server:**
   ```bash
   beginnings run
   ```

3. **Open your browser:**
   {% if include_html %}
   - Web Interface: http://localhost:8000
   {% endif %}
   {% if include_api %}
   - API Documentation: http://localhost:8000/docs
   {% endif %}

## Project Structure

```
{{ project_name }}/
├── config/              # Configuration files
│   ├── app.yaml        # Main configuration
│   ├── app.dev.yaml    # Development overrides
{% if include_staging_config %}
│   └── app.staging.yaml # Staging configuration
{% endif %}
├── routes/             # Route handlers
{% if include_html %}
│   ├── html.py        # HTML routes
{% endif %}
{% if include_api %}
│   └── api.py         # API routes
{% endif %}
{% if include_html %}
├── templates/          # HTML templates
│   ├── base.html      # Base template
│   ├── index.html     # Home page
│   ├── about.html     # About page
{% if include_auth %}
│   ├── dashboard.html # User dashboard
│   └── auth/          # Authentication templates
│       └── login.html
{% endif %}
{% endif %}
├── static/            # Static assets
│   └── css/
│       └── style.css
├── tests/             # Test suite
│   ├── conftest.py    # Test configuration
│   └── test_routes.py # Route tests
├── main.py           # Application entry point
├── pyproject.toml    # Project configuration
└── README.md         # This file
```

## Configuration

The application is configured through YAML files in the `config/` directory:

- **`app.yaml`**: Main configuration with all settings
- **`app.dev.yaml`**: Development-specific overrides
{% if include_staging_config %}
- **`app.staging.yaml`**: Staging environment configuration
{% endif %}

### Environment Variables

Set these environment variables for production:

{% if include_auth %}
```bash
# Authentication secrets (required for production)
export SESSION_SECRET="your-secret-session-key-change-in-production"
export JWT_SECRET="your-secret-jwt-key-must-be-32-chars-minimum"
{% endif %}

# Environment selection
export BEGINNINGS_ENV=production  # or development, staging
```

## Development

### Running the Development Server

```bash
# Standard development server
beginnings run

# With custom host/port
beginnings run --host 0.0.0.0 --port 8080

# With enhanced debugging
beginnings run --debug
```

### Configuration Management

```bash
# Validate configuration
beginnings config validate

# Show merged configuration
beginnings config show

# Compare environments
beginnings config diff dev staging

# Validate with security audit
beginnings config validate --include-security
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov={{ project_name_snake }}

# Run specific test file
pytest tests/test_routes.py
```

### Code Quality

```bash
# Lint code
ruff check .

# Format code
ruff format .
```

## API Documentation

{% if include_api %}
When running the development server, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication

{% if include_auth %}
The API supports JWT authentication:

```bash
# Get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token in requests
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/users
```
{% endif %}

### Endpoints

- `GET /api/health` - Health check
- `GET /api/info` - Application information
{% if include_auth %}
- `POST /api/v1/auth/login` - Authenticate and get JWT token
- `GET /api/v1/users` - List users (requires authentication)
- `GET /api/v1/users/me` - Current user info (requires authentication)
{% endif %}
- `GET /api/v1/status` - Application status
{% else %}
API endpoints are not enabled in this configuration. To enable them, add API routes in the configuration or use the `api` or `full` template.
{% endif %}

{% if include_auth %}
## Authentication

This application includes authentication with the following features:

- **Session Authentication**: For HTML forms and web interface
{% if include_api %}
- **JWT Authentication**: For API access and SPAs
{% endif %}
- **Secure Defaults**: HttpOnly cookies, secure sessions
- **Demo Mode**: Any username/password combination works for demonstration

### Login

{% if include_html %}
- Web Interface: http://localhost:8000/login
{% endif %}
{% if include_api %}
- API Endpoint: `POST /api/v1/auth/login`
{% endif %}

### Security Notes

- Change the default secrets in production
- Configure proper user storage (database)
- Implement password validation and hashing
- Add OAuth providers as needed
{% endif %}

{% if include_rate_limiting %}
## Rate Limiting

Rate limiting is configured to protect against abuse:

- **Global Limit**: 1000 requests per hour
- **Login Endpoint**: 5 attempts per 5 minutes
{% if include_api %}
- **API Endpoints**: 100 requests per minute
{% endif %}

Configure limits in `config/app.yaml` under the `rate_limiting` section.
{% endif %}

{% if include_security_headers %}
## Security

This application implements comprehensive security measures:

- **Content Security Policy (CSP)** with nonces
- **HTTP Strict Transport Security (HSTS)**
- **X-Frame-Options** to prevent clickjacking
- **X-Content-Type-Options** to prevent MIME type sniffing
{% if include_api %}
- **CORS** configuration for cross-origin requests
{% endif %}

Security headers are configured in `config/app.yaml` under the `security` section.
{% endif %}

## Deployment

### Production Checklist

1. **Environment Variables**: Set all required secrets
2. **Configuration**: Review and update `config/app.yaml`
3. **Security**: Run security validation
4. **Dependencies**: Install production dependencies
5. **Process Manager**: Use a process manager (systemd, supervisor, etc.)
6. **Reverse Proxy**: Configure nginx or similar
7. **SSL/TLS**: Configure HTTPS certificates

### Production Server

```bash
# Set production environment
export BEGINNINGS_ENV=production

# Validate configuration
beginnings config validate --include-security

# Run with production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install uv && uv sync

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Learn More

- [Beginnings Documentation](https://beginnings.8ly.xyz/docs)
- [Configuration Reference](https://beginnings.8ly.xyz/docs/configuration)
- [Extension Development](https://beginnings.8ly.xyz/docs/extensions)
- [Security Best Practices](https://beginnings.8ly.xyz/docs/security)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.