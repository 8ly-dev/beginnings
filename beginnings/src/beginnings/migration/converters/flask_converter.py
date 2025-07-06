"""Flask to Beginnings converter.

This module provides comprehensive conversion from Flask applications to
the Beginnings framework. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import re
import ast
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

from ..framework import MigrationConverter, MigrationConfig, MigrationResult, MigrationStatus, FrameworkType


@dataclass
class FlaskConversionResult:
    """Result of Flask-specific conversion."""
    
    success: bool
    converted_files: List[Path]
    conversion_mappings: Dict[str, str]
    warnings: List[str]
    errors: List[str]


class FlaskPatternAnalyzer:
    """Analyzes Flask-specific patterns.
    
    Follows Single Responsibility Principle - only handles Flask pattern analysis.
    """
    
    def __init__(self):
        """Initialize Flask pattern analyzer."""
        self.flask_imports = {
            'Flask': 'beginnings.create_app',
            'request': 'beginnings.request', 
            'jsonify': 'beginnings.jsonify',
            'render_template': 'beginnings.render_template',
            'redirect': 'beginnings.redirect',
            'url_for': 'beginnings.url_for',
            'flash': 'beginnings.flash',
            'session': 'beginnings.session',
            'g': 'beginnings.g',
            'abort': 'beginnings.abort',
            'make_response': 'beginnings.make_response'
        }
        
        self.flask_extensions = {
            'flask_sqlalchemy': 'beginnings.extensions.database',
            'flask_login': 'beginnings.extensions.auth',
            'flask_wtf': 'beginnings.extensions.forms',
            'flask_migrate': 'beginnings.extensions.migrations',
            'flask_mail': 'beginnings.extensions.mail',
            'flask_caching': 'beginnings.extensions.cache',
            'flask_cors': 'beginnings.extensions.cors'
        }
    
    def analyze_flask_app(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Flask application file.
        
        Args:
            file_path: Path to Flask application file
            
        Returns:
            Analysis results
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            
            analysis = {
                'app_creation': self._find_app_creation(content),
                'routes': self._find_routes(content),
                'extensions': self._find_extensions(content),
                'configuration': self._find_configuration(content),
                'blueprints': self._find_blueprints(content),
                'error_handlers': self._find_error_handlers(content),
                'middleware': self._find_middleware(content)
            }
            
            return analysis
            
        except Exception as e:
            logging.error(f"Failed to analyze Flask app {file_path}: {e}")
            return {}
    
    def _find_app_creation(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask app creation patterns."""
        patterns = [
            r'app\s*=\s*Flask\s*\(\s*__name__\s*\)',
            r'app\s*=\s*Flask\s*\([^)]+\)',
            r'(\w+)\s*=\s*Flask\s*\([^)]+\)'
        ]
        
        app_creations = []
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                app_creations.append({
                    'pattern': match.group(),
                    'variable_name': self._extract_app_variable(match.group()),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return app_creations
    
    def _find_routes(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask route definitions."""
        # Match @app.route and @blueprint.route patterns
        route_pattern = r'@(\w+)\.route\s*\(\s*[\'"]([^\'"]*)[\'"](.*?)\)\s*\n\s*def\s+(\w+)\s*\([^)]*\):'
        
        routes = []
        matches = re.finditer(route_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            app_var, path, options, func_name = match.groups()
            
            # Parse route options
            methods = self._extract_methods(options)
            
            routes.append({
                'app_variable': app_var,
                'path': path,
                'methods': methods,
                'function_name': func_name,
                'full_match': match.group(),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return routes
    
    def _find_extensions(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask extension usage."""
        extensions = []
        
        # Common Flask extension patterns
        extension_patterns = {
            'SQLAlchemy': r'(\w+)\s*=\s*SQLAlchemy\s*\(\s*(\w+)?\s*\)',
            'Login': r'(\w+)\s*=\s*LoginManager\s*\(\s*(\w+)?\s*\)',
            'Migrate': r'(\w+)\s*=\s*Migrate\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)',
            'CORS': r'CORS\s*\(\s*(\w+)\s*\)',
            'Cache': r'(\w+)\s*=\s*Cache\s*\(\s*(\w+)?\s*\)'
        }
        
        for ext_name, pattern in extension_patterns.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                extensions.append({
                    'type': ext_name,
                    'pattern': match.group(),
                    'variable_name': match.group(1) if match.groups() else None,
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return extensions
    
    def _find_configuration(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask configuration patterns."""
        config_patterns = [
            r'app\.config\[\s*[\'"]([^\'"]*)[\'"]\s*\]\s*=\s*(.+)',
            r'app\.config\.from_object\s*\(\s*(.+)\s*\)',
            r'app\.config\.from_pyfile\s*\(\s*(.+)\s*\)',
            r'app\.config\.from_envvar\s*\(\s*(.+)\s*\)'
        ]
        
        configurations = []
        for pattern in config_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                configurations.append({
                    'pattern': match.group(),
                    'type': self._identify_config_type(match.group()),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return configurations
    
    def _find_blueprints(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask blueprint definitions and registrations."""
        blueprints = []
        
        # Blueprint creation
        bp_creation_pattern = r'(\w+)\s*=\s*Blueprint\s*\(\s*[\'"]([^\'"]*)[\'"](.*?)\)'
        matches = re.finditer(bp_creation_pattern, content)
        for match in matches:
            var_name, bp_name, options = match.groups()
            blueprints.append({
                'type': 'creation',
                'variable_name': var_name,
                'blueprint_name': bp_name,
                'options': options,
                'line': content[:match.start()].count('\n') + 1
            })
        
        # Blueprint registration
        bp_register_pattern = r'app\.register_blueprint\s*\(\s*(\w+)(.*?)\)'
        matches = re.finditer(bp_register_pattern, content)
        for match in matches:
            var_name, options = match.groups()
            blueprints.append({
                'type': 'registration',
                'variable_name': var_name,
                'options': options,
                'line': content[:match.start()].count('\n') + 1
            })
        
        return blueprints
    
    def _find_error_handlers(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask error handlers."""
        error_pattern = r'@app\.errorhandler\s*\(\s*(\d+)\s*\)\s*\n\s*def\s+(\w+)\s*\([^)]*\):'
        
        error_handlers = []
        matches = re.finditer(error_pattern, content, re.MULTILINE)
        
        for match in matches:
            error_code, func_name = match.groups()
            error_handlers.append({
                'error_code': int(error_code),
                'function_name': func_name,
                'line': content[:match.start()].count('\n') + 1
            })
        
        return error_handlers
    
    def _find_middleware(self, content: str) -> List[Dict[str, Any]]:
        """Find Flask middleware patterns."""
        middleware_patterns = [
            r'@app\.before_request\s*\n\s*def\s+(\w+)\s*\([^)]*\):',
            r'@app\.after_request\s*\n\s*def\s+(\w+)\s*\([^)]*\):',
            r'@app\.before_first_request\s*\n\s*def\s+(\w+)\s*\([^)]*\):',
            r'@app\.teardown_appcontext\s*\n\s*def\s+(\w+)\s*\([^)]*\):'
        ]
        
        middleware = []
        for pattern in middleware_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                func_name = match.group(1)
                middleware_type = self._extract_middleware_type(match.group())
                middleware.append({
                    'type': middleware_type,
                    'function_name': func_name,
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return middleware
    
    def _extract_app_variable(self, app_creation: str) -> str:
        """Extract app variable name from creation pattern."""
        match = re.match(r'(\w+)\s*=', app_creation)
        return match.group(1) if match else 'app'
    
    def _extract_methods(self, options: str) -> List[str]:
        """Extract HTTP methods from route options."""
        methods_match = re.search(r'methods\s*=\s*\[([^\]]+)\]', options)
        if methods_match:
            methods_str = methods_match.group(1)
            methods = [m.strip().strip('\'"') for m in methods_str.split(',')]
            return [m for m in methods if m]
        return ['GET']  # Default method
    
    def _identify_config_type(self, config_pattern: str) -> str:
        """Identify type of configuration pattern."""
        if 'from_object' in config_pattern:
            return 'from_object'
        elif 'from_pyfile' in config_pattern:
            return 'from_pyfile'
        elif 'from_envvar' in config_pattern:
            return 'from_envvar'
        else:
            return 'direct_assignment'
    
    def _extract_middleware_type(self, pattern: str) -> str:
        """Extract middleware type from pattern."""
        if 'before_request' in pattern:
            return 'before_request'
        elif 'after_request' in pattern:
            return 'after_request'
        elif 'before_first_request' in pattern:
            return 'before_first_request'
        elif 'teardown_appcontext' in pattern:
            return 'teardown_appcontext'
        return 'unknown'


class FlaskCodeTransformer:
    """Transforms Flask code to Beginnings format.
    
    Follows Single Responsibility Principle - only handles code transformation.
    """
    
    def __init__(self):
        """Initialize Flask code transformer."""
        self.logger = logging.getLogger(__name__)
    
    def transform_app_file(self, content: str, analysis: Dict[str, Any]) -> str:
        """Transform Flask application file to Beginnings format.
        
        Args:
            content: Original Flask code
            analysis: Analysis results from FlaskPatternAnalyzer
            
        Returns:
            Transformed code
        """
        transformed = content
        
        # Transform imports
        transformed = self._transform_imports(transformed)
        
        # Transform app creation
        transformed = self._transform_app_creation(transformed, analysis.get('app_creation', []))
        
        # Transform routes
        transformed = self._transform_routes(transformed, analysis.get('routes', []))
        
        # Transform extensions
        transformed = self._transform_extensions(transformed, analysis.get('extensions', []))
        
        # Transform configuration
        transformed = self._transform_configuration(transformed, analysis.get('configuration', []))
        
        # Transform error handlers
        transformed = self._transform_error_handlers(transformed, analysis.get('error_handlers', []))
        
        # Transform middleware
        transformed = self._transform_middleware(transformed, analysis.get('middleware', []))
        
        return transformed
    
    def _transform_imports(self, content: str) -> str:
        """Transform Flask imports to Beginnings imports."""
        # Replace Flask imports
        import_mappings = {
            r'from flask import (.+)': self._transform_flask_imports,
            r'import flask': 'import beginnings',
            r'from flask_sqlalchemy import SQLAlchemy': 'from beginnings.extensions.database import DatabaseExtension',
            r'from flask_login import (.+)': r'from beginnings.extensions.auth import \1',
            r'from flask_wtf import (.+)': r'from beginnings.extensions.forms import \1',
            r'from flask_migrate import (.+)': r'from beginnings.extensions.migrations import \1'
        }
        
        transformed = content
        for pattern, replacement in import_mappings.items():
            if callable(replacement):
                transformed = re.sub(pattern, replacement, transformed)
            else:
                transformed = re.sub(pattern, replacement, transformed)
        
        return transformed
    
    def _transform_flask_imports(self, match):
        """Transform specific Flask imports."""
        imports = match.group(1)
        import_list = [imp.strip() for imp in imports.split(',')]
        
        flask_to_beginnings = {
            'Flask': 'create_app',
            'request': 'request',
            'jsonify': 'jsonify',
            'render_template': 'render_template',
            'redirect': 'redirect',
            'url_for': 'url_for',
            'flash': 'flash',
            'session': 'session',
            'g': 'g',
            'abort': 'abort',
            'make_response': 'make_response'
        }
        
        beginnings_imports = []
        for imp in import_list:
            if imp in flask_to_beginnings:
                beginnings_imports.append(flask_to_beginnings[imp])
            else:
                beginnings_imports.append(imp)  # Keep unknown imports
        
        return f"from beginnings import {', '.join(beginnings_imports)}"
    
    def _transform_app_creation(self, content: str, app_creations: List[Dict[str, Any]]) -> str:
        """Transform Flask app creation to Beginnings format."""
        transformed = content
        
        for app_creation in app_creations:
            old_pattern = app_creation['pattern']
            var_name = app_creation['variable_name']
            
            # Replace Flask() with create_app()
            new_pattern = f"{var_name} = create_app()"
            transformed = transformed.replace(old_pattern, new_pattern)
        
        return transformed
    
    def _transform_routes(self, content: str, routes: List[Dict[str, Any]]) -> str:
        """Transform Flask routes to Beginnings format."""
        # Flask and Beginnings have similar routing syntax, so minimal changes needed
        # Main change is ensuring the app variable is correct
        return content
    
    def _transform_extensions(self, content: str, extensions: List[Dict[str, Any]]) -> str:
        """Transform Flask extensions to Beginnings extensions."""
        transformed = content
        
        extension_mappings = {
            'SQLAlchemy': 'DatabaseExtension',
            'LoginManager': 'AuthExtension',
            'Migrate': 'MigrationExtension',
            'Cache': 'CacheExtension'
        }
        
        for extension in extensions:
            ext_type = extension['type']
            if ext_type in extension_mappings:
                old_pattern = extension['pattern']
                beginnings_type = extension_mappings[ext_type]
                
                # Transform the extension initialization
                if extension['variable_name']:
                    var_name = extension['variable_name']
                    new_pattern = f"{var_name} = {beginnings_type}()"
                    transformed = transformed.replace(old_pattern, new_pattern)
        
        return transformed
    
    def _transform_configuration(self, content: str, configurations: List[Dict[str, Any]]) -> str:
        """Transform Flask configuration to Beginnings format."""
        transformed = content
        
        # Convert app.config patterns to Beginnings configuration
        config_pattern = r'app\.config\[\s*[\'"]([^\'"]*)[\'"]+\s*\]\s*=\s*(.+)'
        
        def replace_config(match):
            key = match.group(1)
            value = match.group(2)
            
            # Map Flask config keys to Beginnings config structure
            key_mappings = {
                'SQLALCHEMY_DATABASE_URI': 'database.uri',
                'SECRET_KEY': 'app.secret_key',
                'DEBUG': 'app.debug',
                'TESTING': 'app.testing',
                'SQLALCHEMY_TRACK_MODIFICATIONS': 'database.track_modifications'
            }
            
            beginnings_key = key_mappings.get(key, key.lower())
            return f"# Configuration: {beginnings_key} = {value}"
        
        transformed = re.sub(config_pattern, replace_config, transformed)
        
        return transformed
    
    def _transform_error_handlers(self, content: str, error_handlers: List[Dict[str, Any]]) -> str:
        """Transform Flask error handlers to Beginnings format."""
        # Error handlers in Beginnings are similar to Flask
        # Just ensure they use the correct app variable
        return content
    
    def _transform_middleware(self, content: str, middleware: List[Dict[str, Any]]) -> str:
        """Transform Flask middleware to Beginnings format."""
        transformed = content
        
        # Map Flask middleware decorators to Beginnings equivalents
        middleware_mappings = {
            '@app.before_request': '@app.before_request',
            '@app.after_request': '@app.after_request',
            '@app.before_first_request': '@app.before_first_request',
            '@app.teardown_appcontext': '@app.teardown_appcontext'
        }
        
        for old_decorator, new_decorator in middleware_mappings.items():
            transformed = transformed.replace(old_decorator, new_decorator)
        
        return transformed


class FlaskConverter(MigrationConverter):
    """Converts Flask applications to Beginnings framework.
    
    Follows Single Responsibility Principle - orchestrates Flask conversion.
    Uses Dependency Inversion - depends on analyzer and transformer abstractions.
    """
    
    def __init__(self):
        """Initialize Flask converter."""
        self.logger = logging.getLogger(__name__)
        self.analyzer = FlaskPatternAnalyzer()
        self.transformer = FlaskCodeTransformer()
    
    def supports_framework(self, framework: FrameworkType) -> bool:
        """Check if converter supports framework.
        
        Args:
            framework: Framework type to check
            
        Returns:
            True if Flask framework is supported
        """
        return framework == FrameworkType.FLASK
    
    def convert_project(self, source_path: Path, target_path: Path, config: MigrationConfig) -> MigrationResult:
        """Convert entire Flask project.
        
        Args:
            source_path: Source project directory
            target_path: Target project directory
            config: Migration configuration
            
        Returns:
            Migration result
        """
        result = MigrationResult(
            success=False,
            status=MigrationStatus.IN_PROGRESS
        )
        
        try:
            # Find Python files to convert
            python_files = list(source_path.rglob("*.py"))
            
            for py_file in python_files:
                if self._should_convert_file(py_file, config):
                    relative_path = py_file.relative_to(source_path)
                    target_file = target_path / relative_path
                    
                    if self.convert_file(py_file, target_file):
                        result.migrated_files.append(target_file)
                    else:
                        result.errors.append(f"Failed to convert {py_file}")
            
            # Copy non-Python files
            self._copy_static_files(source_path, target_path, config, result)
            
            # Generate Beginnings-specific files
            self._generate_beginnings_files(target_path, config, result)
            
            result.success = len(result.errors) == 0
            result.status = MigrationStatus.COMPLETED if result.success else MigrationStatus.PARTIAL
            
        except Exception as e:
            self.logger.error(f"Flask project conversion failed: {e}")
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Conversion failed: {str(e)}")
        
        return result
    
    def convert_file(self, source_file: Path, target_file: Path) -> bool:
        """Convert individual Flask file.
        
        Args:
            source_file: Source file path
            target_file: Target file path
            
        Returns:
            True if conversion successful
        """
        try:
            # Ensure target directory exists
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read source content
            content = source_file.read_text(encoding='utf-8')
            
            # Analyze Flask patterns
            analysis = self.analyzer.analyze_flask_app(source_file)
            
            # Transform code
            transformed_content = self.transformer.transform_app_file(content, analysis)
            
            # Write transformed content
            target_file.write_text(transformed_content, encoding='utf-8')
            
            self.logger.info(f"Converted {source_file} -> {target_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to convert file {source_file}: {e}")
            return False
    
    def _should_convert_file(self, file_path: Path, config: MigrationConfig) -> bool:
        """Check if file should be converted."""
        # Skip test files unless specifically requested
        if not config.include_tests and 'test' in str(file_path):
            return False
        
        # Skip files matching exclude patterns
        for pattern in config.exclude_patterns:
            if pattern in str(file_path):
                return False
        
        # Skip __pycache__ and other generated directories
        if '__pycache__' in str(file_path) or '.git' in str(file_path):
            return False
        
        return True
    
    def _copy_static_files(self, source_path: Path, target_path: Path, config: MigrationConfig, result: MigrationResult) -> None:
        """Copy static files (templates, CSS, JS, etc.)."""
        static_extensions = {'.html', '.css', '.js', '.png', '.jpg', '.gif', '.svg', '.ico', '.txt', '.md'}
        
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in static_extensions:
                if self._should_convert_file(file_path, config):
                    relative_path = file_path.relative_to(source_path)
                    target_file = target_path / relative_path
                    
                    try:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_bytes(file_path.read_bytes())
                        result.created_files.append(target_file)
                    except Exception as e:
                        result.errors.append(f"Failed to copy {file_path}: {e}")
    
    def _generate_beginnings_files(self, target_path: Path, config: MigrationConfig, result: MigrationResult) -> None:
        """Generate Beginnings-specific configuration files."""
        try:
            # Generate beginnings.yaml configuration
            config_content = self._generate_beginnings_config()
            config_file = target_path / "beginnings.yaml"
            config_file.write_text(config_content, encoding='utf-8')
            result.created_files.append(config_file)
            
            # Generate requirements.txt with Beginnings dependencies
            requirements_content = self._generate_requirements()
            requirements_file = target_path / "requirements.txt"
            requirements_file.write_text(requirements_content, encoding='utf-8')
            result.created_files.append(requirements_file)
            
        except Exception as e:
            result.errors.append(f"Failed to generate Beginnings files: {e}")
    
    def _generate_beginnings_config(self) -> str:
        """Generate Beginnings configuration file."""
        return """
# Beginnings Framework Configuration
app:
  name: "My Beginnings App"
  debug: true
  secret_key: "your-secret-key-here"

database:
  uri: "sqlite:///app.db"
  track_modifications: false

extensions:
  - beginnings.extensions.database:DatabaseExtension
  - beginnings.extensions.auth:AuthExtension

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt for Beginnings."""
        return """
# Beginnings Framework Dependencies
beginnings>=1.0.0

# Database support
SQLAlchemy>=2.0.0

# Web server
gunicorn>=21.0.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
"""
    
    def convert_routes(self, flask_route_code: str) -> str:
        """Convert Flask routes to Beginnings format.
        
        Args:
            flask_route_code: Flask route code
            
        Returns:
            Converted route code
        """
        # For testing purposes - Flask and Beginnings have similar routing
        return flask_route_code.replace('Flask', 'beginnings')
    
    def convert_models(self, flask_model_code: str) -> str:
        """Convert Flask models to Beginnings format.
        
        Args:
            flask_model_code: Flask model code
            
        Returns:
            Converted model code
        """
        # Replace Flask-SQLAlchemy imports and patterns
        converted = flask_model_code
        converted = converted.replace('from flask_sqlalchemy import SQLAlchemy', 
                                    'from beginnings.extensions.database import DatabaseExtension')
        converted = converted.replace('db = SQLAlchemy()', 'db = DatabaseExtension()')
        return converted
    
    def convert_config(self, flask_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Flask configuration to Beginnings format.
        
        Args:
            flask_config: Flask configuration dictionary
            
        Returns:
            Converted configuration
        """
        beginnings_config = {
            'app': {},
            'database': {},
            'extensions': []
        }
        
        # Map Flask config keys to Beginnings structure
        key_mappings = {
            'SECRET_KEY': ('app', 'secret_key'),
            'DEBUG': ('app', 'debug'),
            'TESTING': ('app', 'testing'),
            'SQLALCHEMY_DATABASE_URI': ('database', 'uri'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': ('database', 'track_modifications')
        }
        
        for flask_key, value in flask_config.items():
            if flask_key in key_mappings:
                section, beginnings_key = key_mappings[flask_key]
                beginnings_config[section][beginnings_key] = value
        
        return beginnings_config
    
    def convert_app(self, source_path: Path, target_path: Path) -> FlaskConversionResult:
        """Convert Flask app with detailed result.
        
        Args:
            source_path: Source directory
            target_path: Target directory
            
        Returns:
            Detailed conversion result
        """
        config = MigrationConfig(
            source_framework="flask",
            source_directory=source_path,
            target_directory=target_path
        )
        
        migration_result = self.convert_project(source_path, target_path, config)
        
        return FlaskConversionResult(
            success=migration_result.success,
            converted_files=migration_result.migrated_files,
            conversion_mappings={},  # Would be populated with actual mappings
            warnings=migration_result.warnings,
            errors=migration_result.errors
        )