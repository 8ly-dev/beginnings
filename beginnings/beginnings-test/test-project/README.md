# Test Project

A web application built with the beginnings framework.

## Features


- 🌐 **HTML Interface**: Server-rendered web pages with templates






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
   
   - Web Interface: http://localhost:8000
   
   

## Project Structure

```
test-project/
├── config/              # Configuration files
│   ├── app.yaml        # Main configuration
│   ├── app.dev.yaml    # Development overrides

├── routes/             # Route handlers

│   ├── html.py        # HTML routes



├── templates/          # HTML templates
│   ├── base.html      # Base template
│   ├── index.html     # Home page
│   ├── about.html     # About page


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


### Environment Variables

Set these environment variables for production:



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
pytest --cov=test_project

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


API endpoints are not enabled in this configuration. To enable them, add API routes in the configuration or use the `api` or `full` template.








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