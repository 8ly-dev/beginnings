# TestExtension Extension Configuration Reference

## Configuration Overview

The TestExtension extension supports both global and route-specific configuration.

## Global Configuration

Global configuration is specified in your application's main configuration file:

```yaml
test_extension:
  enabled: true
  # Global configuration options
```

## Configuration Schema

### Core Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `enabled` | boolean | No | `true` | Enable or disable the extension globally |


### Middleware Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `option1` | string | No | `"default_value"` | Example configuration option |
| `option2` | boolean | No | `false` | Example boolean option |

### Route-specific Configuration

```yaml
routes:
  "/api/example":
    methods: ["GET", "POST"]
    test_extension:
      enabled: true
      option1: "route_specific_value"
```



## Environment Variables

The extension supports configuration via environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TEST_EXTENSION_ENABLED` | Enable/disable extension | `true` |


## Configuration Examples

### Development Environment

```yaml
test_extension:
  enabled: true
  option1: "development_value"
  option2: true
  
```

### Production Environment

```yaml
test_extension:
  enabled: true
  option1: "production_value"
  option2: false
  
```

## Configuration Validation

The extension validates configuration on startup. Common validation errors:

- Missing required configuration options
- Invalid data types or formats
- Invalid URL formats
- Missing environment variables

### Validation Example

```python
from test_extension.extension import TestExtensionExtension

config = {
    "enabled": True,
    # Add configuration
}

extension = TestExtensionExtension(config)
errors = extension.validate_config()

if errors:
    for error in errors:
        print(f"Configuration error: {error}")
```

## Security Considerations


- Enable configuration validation
- Use HTTPS for all external communications
- Monitor extension logs for security events

## Troubleshooting Configuration

### Common Issues

1. **Extension not starting**
   - Check required configuration is provided
   - Verify environment variables are set
   - Review configuration syntax

2. **Validation errors**
   - Check data types match expected formats
   - Verify required fields are present
   - Check for typos in configuration keys

3. **Runtime configuration issues**
   - Check configuration is properly loaded
   - Verify environment-specific settings
   - Review logs for configuration warnings