# TestExtension Extension User Guide

## Overview

The TestExtension extension provides middleware functionality for Beginnings applications.

## Installation

1. Install the extension in your project:
   ```bash
   pip install test_extension-extension
   ```

2. Add to your application configuration:
   ```yaml
   extensions:
     - "test_extension.extension:TestExtensionExtension"
   ```

3. Configure the extension:
   ```yaml
   test_extension:
     enabled: true
     # Add configuration options here
   ```

## Configuration

### Global Configuration

The extension can be configured globally in your application configuration:

```yaml
test_extension:
  enabled: true
  # Extension-specific options
```

### Route-specific Configuration

You can also configure the extension on a per-route basis:

```yaml
routes:
  "/api/protected":
    methods: ["GET", "POST"]
    test_extension:
      enabled: true
      # Route-specific options
```

## Usage Examples

### Basic Usage

```python
from beginnings.core.app import App

# Create application
app = App()

# Extension is automatically loaded from configuration
```


### Middleware Features

The test_extension middleware provides:

- Request preprocessing
- Response postprocessing
- Error handling
- Route-specific configuration

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the middleware |
| `option1` | str | `"default_value"` | Example option |
| `option2` | bool | `false` | Example boolean option |



## Advanced Usage

### Custom Configuration

```python
from test_extension.extension import TestExtensionExtension

# Custom configuration
custom_config = {
    "enabled": True,
    # Add custom options
}

# Initialize extension manually
extension = TestExtensionExtension(custom_config)
```

### Error Handling

The extension provides built-in error handling for common scenarios:

- Configuration validation errors
- Runtime processing errors
- Service connection errors

### Debugging

Enable debug logging to troubleshoot issues:

```yaml
logging:
  level: DEBUG
  loggers:
    test_extension:
      level: DEBUG
```

## Troubleshooting

### Common Issues

1. **Extension not loading**
   - Check extension is properly installed
   - Verify configuration syntax
   - Check application logs for errors

2. **Configuration errors**
   - Validate required configuration options
   - Check data types and formats
   - Review configuration documentation

3. **Runtime errors**
   - Enable debug logging
   - Check service connectivity
   - Verify permissions and credentials

### Getting Help

- Check the [configuration reference](configuration.md)
- Review extension logs for error details
- Open an issue on the project repository