# Beginnings

A thoughtful web framework built on FastAPI, designed to provide sensible defaults and conventions for building modern web applications.

## Overview

Beginnings is a Python web framework that wraps FastAPI with thoughtful defaults, configuration management, and an extension system. It aims to make web development more productive by providing:

- **Thoughtful Defaults**: Sensible configuration and setup out of the box
- **Configuration Management**: Flexible configuration loading from files and environment variables
- **Extension System**: Modular architecture with a plugin system for extending functionality
- **Modern Python**: Built with type hints, async support, and modern Python practices
- **Development Experience**: Comprehensive tooling for linting, testing, and type checking

## Features

- **FastAPI Foundation**: Built on the solid foundation of FastAPI for high performance
- **Configuration Management**: YAML-based configuration with environment variable support
- **Extension System**: Modular plugin architecture for adding functionality
- **Security-First**: Built-in security scanning and validation
- **Type Safety**: Comprehensive type hints and static analysis
- **Testing**: Complete testing framework with async support
- **Developer Experience**: Modern tooling with ruff, mypy, and pytest

## Quick Start

### Installation

```bash
# Install from source (for development)
git clone <repository-url>
cd beginnings
uv venv
uv sync --dev
```

### Basic Usage

```python
from beginnings import App

# Create application
app = App()

# Use HTML router for web pages
@app.html.get("/")
def index():
    return "<h1>Welcome to Beginnings!</h1>"

# Use API router for JSON endpoints
@app.api.get("/hello")
def hello():
    return {"message": "Hello from Beginnings!"}

# Run the application
if __name__ == "__main__":
    app.run()
```

## Development

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd beginnings
uv venv
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Run type checking
uv run mypy

# Run security scan
uv run bandit -r src/
```

### Project Structure

```
beginnings/
├── src/beginnings/          # Main package
│   ├── config/             # Configuration management
│   ├── routing/            # HTML and API routing
│   ├── extensions/         # Extension system
│   └── core.py            # Main App class
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Example projects
└── pyproject.toml         # Project configuration
```

## Configuration

Beginnings supports flexible configuration through YAML files and environment variables:

```yaml
# config.yml
app:
  debug: false
  host: "0.0.0.0"
  port: 8000

database:
  url: "postgresql://user:pass@localhost/db"

extensions:
  - "my_extension.DatabaseExtension"
```

Environment variables can override configuration values using the `BEGINNINGS_` prefix:

```bash
export BEGINNINGS_APP_PORT=3000
export BEGINNINGS_APP_DEBUG=true
```

## Extensions

Create custom extensions by inheriting from `BeginningsExtension`:

```python
from beginnings.extensions import BeginningsExtension

class MyExtension(BeginningsExtension):
    def __init__(self):
        super().__init__("my_extension")
    
    def initialize(self, app, config):
        # Extension initialization logic
        pass
    
    def get_version(self):
        return "1.0.0"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Development Status

This project is in early development. APIs may change as the framework evolves.