"""Interactive configuration editor.

This module provides a live configuration editor with real-time validation
and form generation from JSON schemas. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum

try:
    import jsonschema
except ImportError:
    jsonschema = None


class ValidationSeverity(Enum):
    """Validation message severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Single validation message."""
    
    field_path: str
    message: str
    severity: ValidationSeverity
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    messages: List[ValidationMessage] = field(default_factory=list)
    
    def add_error(self, field_path: str, message: str, suggestion: Optional[str] = None):
        """Add validation error."""
        self.errors.append(message)
        self.messages.append(ValidationMessage(
            field_path=field_path,
            message=message,
            severity=ValidationSeverity.ERROR,
            suggestion=suggestion
        ))
        self.is_valid = False
    
    def add_warning(self, field_path: str, message: str, suggestion: Optional[str] = None):
        """Add validation warning."""
        self.warnings.append(message)
        self.messages.append(ValidationMessage(
            field_path=field_path,
            message=message,
            severity=ValidationSeverity.WARNING,
            suggestion=suggestion
        ))


@dataclass
class ConfigEditorResult:
    """Result of config editor operation."""
    
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    validation: Optional[ValidationResult] = None


class InteractiveConfigEditor:
    """Interactive configuration editor with real-time validation.
    
    Follows Single Responsibility Principle - only handles config editing.
    Uses Dependency Inversion - depends on validation abstractions.
    """
    
    def __init__(self):
        """Initialize the config editor."""
        self._validators = {}
        self._form_generators = {}
        self._change_listeners = []
    
    def validate_config(
        self, 
        config: Dict[str, Any], 
        schema: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate configuration against schema.
        
        Args:
            config: Configuration data to validate
            schema: JSON schema to validate against
            
        Returns:
            Validation result with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        if schema is None:
            result.add_error("", "No schema provided for validation")
            return result
        
        if not isinstance(schema, dict):
            result.add_error("", "Schema must be a dictionary")
            return result
        
        # Use jsonschema if available, otherwise basic validation
        if jsonschema is not None:
            try:
                jsonschema.validate(config, schema)
            except jsonschema.ValidationError as e:
                result.add_error(
                    ".".join(str(p) for p in e.absolute_path),
                    e.message,
                    self._generate_suggestion(e)
                )
            except jsonschema.SchemaError as e:
                result.add_error("", f"Invalid schema: {e.message}")
        else:
            # Fallback basic validation
            self._basic_validation(config, schema, result)
        
        # Additional custom validations
        self._validate_security_settings(config, result)
        self._validate_performance_settings(config, result)
        
        return result
    
    def _basic_validation(
        self, 
        config: Dict[str, Any], 
        schema: Dict[str, Any], 
        result: ValidationResult,
        path: str = ""
    ) -> None:
        """Basic validation without jsonschema."""
        if "required" in schema:
            for required_field in schema["required"]:
                if required_field not in config:
                    field_path = f"{path}.{required_field}" if path else required_field
                    result.add_error(
                        field_path,
                        f"Required field '{required_field}' is missing"
                    )
        
        if "properties" in schema:
            for field_name, field_schema in schema["properties"].items():
                if field_name in config:
                    field_path = f"{path}.{field_name}" if path else field_name
                    self._validate_field_type(
                        config[field_name], 
                        field_schema, 
                        field_path, 
                        result
                    )
    
    def _validate_field_type(
        self, 
        value: Any, 
        field_schema: Dict[str, Any], 
        field_path: str, 
        result: ValidationResult
    ) -> None:
        """Validate individual field type."""
        expected_type = field_schema.get("type")
        
        if expected_type == "string" and not isinstance(value, str):
            result.add_error(field_path, f"Expected string, got {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            result.add_error(field_path, f"Expected integer, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            result.add_error(field_path, f"Expected boolean, got {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            result.add_error(field_path, f"Expected array, got {type(value).__name__}")
        elif expected_type == "object" and not isinstance(value, dict):
            result.add_error(field_path, f"Expected object, got {type(value).__name__}")
        
        # Validate constraints
        if expected_type == "string":
            min_length = field_schema.get("minLength")
            if min_length and len(value) < min_length:
                result.add_error(
                    field_path, 
                    f"String too short (minimum {min_length} characters)"
                )
        
        if expected_type == "integer":
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            if minimum is not None and value < minimum:
                result.add_error(field_path, f"Value too small (minimum {minimum})")
            if maximum is not None and value > maximum:
                result.add_error(field_path, f"Value too large (maximum {maximum})")
    
    def _validate_security_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate security-related configuration."""
        # Check debug mode in production-like settings
        if config.get("app", {}).get("debug") is True:
            host = config.get("app", {}).get("host", "127.0.0.1")
            if host in ["0.0.0.0", "0.0.0.0"]:
                result.add_warning(
                    "app.debug",
                    "Debug mode enabled with public host binding",
                    "Disable debug mode or use localhost for development"
                )
        
        # Check for weak secret keys
        auth_config = config.get("auth", {})
        if auth_config:
            session_config = auth_config.get("providers", {}).get("session", {})
            secret_key = session_config.get("secret_key", "")
            if isinstance(secret_key, str) and len(secret_key) < 32:
                result.add_warning(
                    "auth.providers.session.secret_key",
                    "Secret key should be at least 32 characters long",
                    "Generate a strong random secret key"
                )
    
    def _validate_performance_settings(self, config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate performance-related configuration."""
        # Check database connection pool settings
        db_config = config.get("database", {})
        if db_config:
            pool_size = db_config.get("pool_size")
            if pool_size and pool_size > 100:
                result.add_warning(
                    "database.pool_size",
                    "Large connection pool size may impact performance",
                    "Consider using a smaller pool size (5-20 connections)"
                )
    
    def _generate_suggestion(self, error: Any) -> Optional[str]:
        """Generate helpful suggestion for validation error."""
        if hasattr(error, 'validator') and hasattr(error, 'validator_value'):
            if error.validator == "required":
                return f"Add the required field: {error.validator_value}"
            elif error.validator == "type":
                return f"Change value to type: {error.validator_value}"
            elif error.validator == "minimum":
                return f"Use value >= {error.validator_value}"
            elif error.validator == "maximum":
                return f"Use value <= {error.validator_value}"
        return None
    
    def generate_form(self, schema: Dict[str, Any]) -> ConfigEditorResult:
        """Generate HTML form from JSON schema.
        
        Args:
            schema: JSON schema to generate form from
            
        Returns:
            Result containing HTML form, CSS, and JavaScript
        """
        try:
            form_html = self._generate_form_html(schema)
            form_css = self._generate_form_css()
            form_js = self._generate_form_javascript()
            
            return ConfigEditorResult(
                success=True,
                data={
                    "html_form": form_html,
                    "css": form_css,
                    "javascript": form_js,
                    "schema_id": str(uuid.uuid4())
                }
            )
        except Exception as e:
            return ConfigEditorResult(
                success=False,
                error_message=f"Failed to generate form: {str(e)}"
            )
    
    def _generate_form_html(self, schema: Dict[str, Any], path: str = "") -> str:
        """Generate HTML form from schema."""
        html_parts = []
        
        if schema.get("type") == "object" and "properties" in schema:
            html_parts.append('<div class="config-section">')
            
            for field_name, field_schema in schema["properties"].items():
                field_path = f"{path}.{field_name}" if path else field_name
                required = field_name in schema.get("required", [])
                
                html_parts.append(self._generate_field_html(
                    field_name, field_schema, field_path, required
                ))
            
            html_parts.append('</div>')
        
        return "\n".join(html_parts)
    
    def _generate_field_html(
        self, 
        field_name: str, 
        field_schema: Dict[str, Any], 
        field_path: str,
        required: bool = False
    ) -> str:
        """Generate HTML for individual form field."""
        field_type = field_schema.get("type", "string")
        field_title = field_schema.get("title", field_name.replace("_", " ").title())
        field_description = field_schema.get("description", "")
        
        html_parts = [
            f'<div class="form-field" data-field-path="{field_path}">',
            f'<label for="{field_path}" class="field-label">',
            f'{field_title}',
            ' <span class="required">*</span>' if required else '',
            '</label>'
        ]
        
        if field_description:
            html_parts.append(f'<p class="field-description">{field_description}</p>')
        
        # Generate input based on type
        if field_type == "string":
            html_parts.append(self._generate_string_input(field_path, field_schema))
        elif field_type == "integer":
            html_parts.append(self._generate_number_input(field_path, field_schema))
        elif field_type == "boolean":
            html_parts.append(self._generate_boolean_input(field_path, field_schema))
        elif field_type == "array":
            html_parts.append(self._generate_array_input(field_path, field_schema))
        elif field_type == "object":
            html_parts.append(self._generate_form_html(field_schema, field_path))
        
        html_parts.extend([
            '<div class="field-validation" id="{}-validation"></div>'.format(field_path),
            '</div>'
        ])
        
        return "\n".join(html_parts)
    
    def _generate_string_input(self, field_path: str, schema: Dict[str, Any]) -> str:
        """Generate string input field."""
        input_attrs = [
            f'id="{field_path}"',
            f'name="{field_path}"',
            'type="text"',
            'class="form-input"',
            f'data-field-path="{field_path}"'
        ]
        
        if "default" in schema:
            input_attrs.append(f'value="{schema["default"]}"')
        
        if "minLength" in schema:
            input_attrs.append(f'minlength="{schema["minLength"]}"')
        
        if "maxLength" in schema:
            input_attrs.append(f'maxlength="{schema["maxLength"]}"')
        
        if "pattern" in schema:
            input_attrs.append(f'pattern="{schema["pattern"]}"')
        
        # Use textarea for longer text
        if schema.get("format") == "textarea" or schema.get("maxLength", 0) > 100:
            return f'<textarea {" ".join(input_attrs)}></textarea>'
        else:
            return f'<input {" ".join(input_attrs)} />'
    
    def _generate_number_input(self, field_path: str, schema: Dict[str, Any]) -> str:
        """Generate number input field."""
        input_attrs = [
            f'id="{field_path}"',
            f'name="{field_path}"',
            'type="number"',
            'class="form-input"',
            f'data-field-path="{field_path}"'
        ]
        
        if "default" in schema:
            input_attrs.append(f'value="{schema["default"]}"')
        
        if "minimum" in schema:
            input_attrs.append(f'min="{schema["minimum"]}"')
        
        if "maximum" in schema:
            input_attrs.append(f'max="{schema["maximum"]}"')
        
        return f'<input {" ".join(input_attrs)} />'
    
    def _generate_boolean_input(self, field_path: str, schema: Dict[str, Any]) -> str:
        """Generate boolean input field."""
        checked = 'checked' if schema.get("default") is True else ''
        
        return f"""
        <div class="checkbox-wrapper">
            <input type="checkbox" id="{field_path}" name="{field_path}" 
                   class="form-checkbox" data-field-path="{field_path}" {checked} />
            <label for="{field_path}" class="checkbox-label"></label>
        </div>
        """
    
    def _generate_array_input(self, field_path: str, schema: Dict[str, Any]) -> str:
        """Generate array input field."""
        return f"""
        <div class="array-field" data-field-path="{field_path}">
            <div class="array-items" id="{field_path}-items"></div>
            <button type="button" class="add-item-btn" data-target="{field_path}">
                Add Item
            </button>
        </div>
        """
    
    def _generate_form_css(self) -> str:
        """Generate CSS styles for the form."""
        return """
        .config-section {
            margin-bottom: 2rem;
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background: #ffffff;
        }
        
        .form-field {
            margin-bottom: 1.5rem;
        }
        
        .field-label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #374151;
        }
        
        .required {
            color: #dc2626;
        }
        
        .field-description {
            font-size: 0.875rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }
        
        .form-input, .form-checkbox {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .form-checkbox {
            width: auto;
        }
        
        .field-validation {
            margin-top: 0.5rem;
            font-size: 0.875rem;
        }
        
        .validation-error {
            color: #dc2626;
        }
        
        .validation-warning {
            color: #d97706;
        }
        
        .validation-success {
            color: #059669;
        }
        
        .array-field {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 1rem;
        }
        
        .add-item-btn {
            background: #2563eb;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        
        .add-item-btn:hover {
            background: #1d4ed8;
        }
        """
    
    def _generate_form_javascript(self) -> str:
        """Generate JavaScript for form interactivity."""
        return """
        class ConfigEditor {
            constructor() {
                this.setupValidation();
                this.setupArrayFields();
                this.setupRealTimeUpdates();
            }
            
            setupValidation() {
                document.querySelectorAll('.form-input, .form-checkbox').forEach(input => {
                    input.addEventListener('blur', (e) => this.validateField(e.target));
                    input.addEventListener('input', (e) => this.debounceValidation(e.target));
                });
            }
            
            setupArrayFields() {
                document.querySelectorAll('.add-item-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => this.addArrayItem(e.target));
                });
            }
            
            setupRealTimeUpdates() {
                document.querySelectorAll('.form-input, .form-checkbox').forEach(input => {
                    input.addEventListener('input', (e) => this.updateConfig(e.target));
                });
            }
            
            validateField(field) {
                const fieldPath = field.dataset.fieldPath;
                const value = field.type === 'checkbox' ? field.checked : field.value;
                
                // Trigger validation via API call
                this.callValidationAPI(fieldPath, value);
            }
            
            debounceValidation(field) {
                clearTimeout(field.validationTimeout);
                field.validationTimeout = setTimeout(() => {
                    this.validateField(field);
                }, 500);
            }
            
            addArrayItem(button) {
                const targetPath = button.dataset.target;
                const itemsContainer = document.getElementById(targetPath + '-items');
                
                const itemDiv = document.createElement('div');
                itemDiv.className = 'array-item';
                itemDiv.innerHTML = `
                    <input type="text" class="form-input" />
                    <button type="button" class="remove-item-btn">Remove</button>
                `;
                
                itemsContainer.appendChild(itemDiv);
                
                // Setup remove functionality
                itemDiv.querySelector('.remove-item-btn').addEventListener('click', () => {
                    itemDiv.remove();
                });
            }
            
            updateConfig(field) {
                const fieldPath = field.dataset.fieldPath;
                const value = field.type === 'checkbox' ? field.checked : field.value;
                
                // Update configuration object
                this.setConfigValue(fieldPath, value);
                
                // Trigger change event
                document.dispatchEvent(new CustomEvent('configChanged', {
                    detail: { fieldPath, value }
                }));
            }
            
            setConfigValue(path, value) {
                const keys = path.split('.');
                let current = window.currentConfig = window.currentConfig || {};
                
                for (let i = 0; i < keys.length - 1; i++) {
                    current[keys[i]] = current[keys[i]] || {};
                    current = current[keys[i]];
                }
                
                current[keys[keys.length - 1]] = value;
            }
            
            async callValidationAPI(fieldPath, value) {
                try {
                    const response = await fetch('/api/validate-config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fieldPath, value, config: window.currentConfig })
                    });
                    
                    const result = await response.json();
                    this.displayValidationResult(fieldPath, result);
                } catch (error) {
                    console.error('Validation error:', error);
                }
            }
            
            displayValidationResult(fieldPath, result) {
                const validationDiv = document.getElementById(fieldPath + '-validation');
                
                if (result.isValid) {
                    validationDiv.innerHTML = '<span class="validation-success">✓ Valid</span>';
                } else {
                    const errors = result.errors.map(error => 
                        `<div class="validation-error">✗ ${error}</div>`
                    ).join('');
                    validationDiv.innerHTML = errors;
                }
            }
        }
        
        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', () => {
            new ConfigEditor();
        });
        """
    
    def update_config(
        self, 
        update_data: Dict[str, Any], 
        schema: Optional[Dict[str, Any]] = None
    ) -> ConfigEditorResult:
        """Update configuration with real-time validation.
        
        Args:
            update_data: Contains field, value, and current config
            schema: Schema to validate against
            
        Returns:
            Result with updated config and validation
        """
        try:
            field_path = update_data.get("field", "")
            new_value = update_data.get("value")
            current_config = update_data.get("config", {})
            
            # Update the config
            updated_config = self._set_nested_value(current_config.copy(), field_path, new_value)
            
            # Validate updated config
            validation_result = self.validate_config(updated_config, schema) if schema else None
            
            return ConfigEditorResult(
                success=True,
                data={
                    "updated_config": updated_config,
                    "validation": validation_result.__dict__ if validation_result else None,
                    "field_updated": field_path
                },
                validation=validation_result
            )
        except Exception as e:
            return ConfigEditorResult(
                success=False,
                error_message=f"Failed to update config: {str(e)}"
            )
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
        """Set nested value in configuration dictionary."""
        keys = path.split(".")
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        return config