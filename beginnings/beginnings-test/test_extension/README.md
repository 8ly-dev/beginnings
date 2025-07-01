# TestExtension Extension

A middleware extension for the Beginnings web framework.

## Description

This extension provides test_extension functionality for Beginnings applications.

## Installation

```bash
pip install test_extension-extension
```

Or if developing locally:

```bash
pip install -e .
```

## Configuration

Add the extension to your Beginnings application configuration:

```yaml
extensions:
  - "test_extension.extension:TestExtensionExtension"

test_extension:
  enabled: true
  # Add your configuration options here
```

## Usage

### Basic Usage

```python
from beginnings.core.app import App

app = App()

# The extension will be automatically loaded from configuration
```

### Route-specific Configuration

You can configure the extension on a per-route basis:

```yaml
routes:
  "/api/protected":
    methods: ["GET", "POST"]
    test_extension:
      enabled: true
      # Route-specific options
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the extension |

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/test_extension-extension.git
cd test_extension-extension

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black test_extension/ tests/

# Sort imports
isort test_extension/ tests/

# Type checking
mypy test_extension/

# Linting
flake8 test_extension/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### 0.1.0 (TBD)

- Initial release
- Basic middleware functionality