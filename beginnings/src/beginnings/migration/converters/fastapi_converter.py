"""FastAPI to Beginnings converter.

This module provides comprehensive conversion from FastAPI applications to
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


class FastAPIPatternAnalyzer:
    """Analyzes FastAPI-specific patterns.
    
    Follows Single Responsibility Principle - only handles FastAPI pattern analysis.
    """
    
    def __init__(self):
        """Initialize FastAPI pattern analyzer."""
        self.fastapi_imports = {
            'FastAPI': 'beginnings.create_app',
            'Request': 'beginnings.request',
            'Response': 'beginnings.response',
            'HTTPException': 'beginnings.abort',
            'Depends': 'beginnings.dependency',
            'Query': 'beginnings.query_param',
            'Path': 'beginnings.path_param',
            'Body': 'beginnings.body_param',
            'Header': 'beginnings.header_param',
            'Cookie': 'beginnings.cookie_param'
        }
    
    def analyze_fastapi_app(self, content: str) -> Dict[str, Any]:
        """Analyze FastAPI application patterns.
        
        Args:
            content: FastAPI application content
            
        Returns:
            Analysis results
        """
        analysis = {
            'app_creation': self._find_app_creation(content),
            'routes': self._find_routes(content),
            'dependencies': self._find_dependencies(content),
            'middleware': self._find_middleware(content),
            'exception_handlers': self._find_exception_handlers(content),
            'models': self._find_pydantic_models(content),
            'imports': self._find_fastapi_imports(content)
        }
        
        return analysis
    
    def analyze_pydantic_models(self, content: str) -> List[Dict[str, Any]]:
        """Analyze Pydantic model definitions.
        
        Args:
            content: Python file content with Pydantic models
            
        Returns:
            List of model analysis results
        """
        models = []
        
        # Find Pydantic model class definitions
        model_pattern = r'class\s+(\w+)\s*\(\s*([^)]*BaseModel[^)]*)\s*\)\s*:'
        matches = re.finditer(model_pattern, content)
        
        for match in matches:
            class_name, base_classes = match.groups()
            
            model_info = {
                'name': class_name,
                'base_classes': base_classes,
                'fields': self._extract_pydantic_fields(content, match.start()),
                'validators': self._extract_pydantic_validators(content, match.start()),
                'config': self._extract_pydantic_config(content, match.start()),
                'line': content[:match.start()].count('\n') + 1
            }
            models.append(model_info)
        
        return models
    
    def _find_app_creation(self, content: str) -> List[Dict[str, Any]]:
        """Find FastAPI app creation patterns."""
        patterns = [
            r'app\s*=\s*FastAPI\s*\([^)]*\)',
            r'(\w+)\s*=\s*FastAPI\s*\([^)]*\)'
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
        """Find FastAPI route definitions."""
        # Match @app.get, @app.post, etc. patterns
        route_pattern = r'@(\w+)\.(get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']*)["\']([^)]*)\)\s*(?:async\s+)?def\s+(\w+)\s*\([^)]*\):'
        
        routes = []
        matches = re.finditer(route_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            app_var, method, path, options, func_name = match.groups()
            
            # Parse route options
            status_code = self._extract_status_code(options)
            response_model = self._extract_response_model(options)
            tags = self._extract_tags(options)
            
            routes.append({
                'app_variable': app_var,
                'method': method.upper(),
                'path': path,
                'function_name': func_name,
                'status_code': status_code,
                'response_model': response_model,
                'tags': tags,
                'full_match': match.group(),
                'line': content[:match.start()].count('\n') + 1
            })
        
        return routes
    
    def _find_dependencies(self, content: str) -> List[Dict[str, Any]]:
        """Find FastAPI dependency patterns."""
        dependencies = []
        
        # Dependency function patterns
        dependency_patterns = [
            r'def\s+(\w+)\s*\([^)]*\)\s*->.*?:',  # Dependency functions
            r'(\w+)\s*=\s*Depends\s*\([^)]+\)',    # Dependency assignments
        ]
        
        for pattern in dependency_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dependencies.append({
                    'pattern': match.group(),
                    'name': match.group(1),
                    'type': 'function' if 'def' in match.group() else 'assignment',
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return dependencies
    
    def _find_middleware(self, content: str) -> List[Dict[str, Any]]:
        """Find FastAPI middleware patterns."""
        middleware = []
        
        middleware_patterns = [
            r'@app\.middleware\s*\(\s*["\']([^"\']*)["\'].*?\)\s*async\s+def\s+(\w+)',
            r'app\.add_middleware\s*\([^)]+\)'
        ]
        
        for pattern in middleware_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if '@app.middleware' in match.group():
                    middleware_type, func_name = match.groups()
                    middleware.append({
                        'type': 'decorator',
                        'middleware_type': middleware_type,
                        'function_name': func_name,
                        'line': content[:match.start()].count('\n') + 1
                    })
                else:
                    middleware.append({
                        'type': 'add_middleware',
                        'pattern': match.group(),
                        'line': content[:match.start()].count('\n') + 1
                    })
        
        return middleware
    
    def _find_exception_handlers(self, content: str) -> List[Dict[str, Any]]:
        """Find FastAPI exception handlers."""
        exception_handlers = []
        
        handler_pattern = r'@app\.exception_handler\s*\(\s*([^)]+)\s*\)\s*async\s+def\s+(\w+)'
        matches = re.finditer(handler_pattern, content)
        
        for match in matches:
            exception_type, func_name = match.groups()
            exception_handlers.append({
                'exception_type': exception_type.strip(),
                'function_name': func_name,
                'line': content[:match.start()].count('\n') + 1
            })
        
        return exception_handlers
    
    def _find_pydantic_models(self, content: str) -> List[Dict[str, Any]]:
        """Find Pydantic model references in FastAPI code."""
        models = []
        
        # Look for class definitions that inherit from BaseModel
        model_pattern = r'class\s+(\w+)\s*\([^)]*BaseModel[^)]*\)\s*:'
        matches = re.finditer(model_pattern, content)
        
        for match in matches:
            class_name = match.group(1)
            models.append({
                'name': class_name,
                'type': 'pydantic_model',
                'line': content[:match.start()].count('\n') + 1
            })
        
        return models
    
    def _find_fastapi_imports(self, content: str) -> List[Dict[str, Any]]:
        """Find FastAPI-specific imports."""
        imports = []
        
        import_patterns = [
            r'from fastapi import ([^\\n]+)',
            r'import fastapi',
            r'from pydantic import ([^\\n]+)',
            r'import pydantic'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                imports.append({
                    'import': match.group(),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return imports
    
    def _extract_app_variable(self, app_creation: str) -> str:
        """Extract app variable name from creation pattern."""
        match = re.match(r'(\\w+)\\s*=', app_creation)
        return match.group(1) if match else 'app'
    
    def _extract_status_code(self, options: str) -> Optional[int]:
        """Extract status code from route options."""
        status_match = re.search(r'status_code\\s*=\\s*(\\d+)', options)
        return int(status_match.group(1)) if status_match else None
    
    def _extract_response_model(self, options: str) -> Optional[str]:
        """Extract response model from route options."""
        model_match = re.search(r'response_model\\s*=\\s*(\\w+)', options)
        return model_match.group(1) if model_match else None
    
    def _extract_tags(self, options: str) -> List[str]:
        """Extract tags from route options."""
        tags_match = re.search(r'tags\\s*=\\s*\\[([^\\]]+)\\]', options)
        if tags_match:
            tags_str = tags_match.group(1)
            return [tag.strip().strip('\'"') for tag in tags_str.split(',')]
        return []
    
    def _extract_pydantic_fields(self, content: str, class_start: int) -> List[Dict[str, Any]]:
        """Extract Pydantic model fields."""
        fields = []
        
        # Find the class body
        class_body = self._extract_class_body(content, class_start)
        
        # Pydantic field patterns
        field_pattern = r'(\\w+)\\s*:\\s*([^=\\n]+)(?:\\s*=\\s*([^\\n]+))?'
        matches = re.finditer(field_pattern, class_body)
        
        for match in matches:
            field_name, field_type, default_value = match.groups()
            fields.append({
                'name': field_name,
                'type': field_type.strip(),
                'default': default_value.strip() if default_value else None,
                'line': class_body[:match.start()].count('\n') + 1
            })
        
        return fields
    
    def _extract_pydantic_validators(self, content: str, class_start: int) -> List[Dict[str, Any]]:
        """Extract Pydantic validators."""
        validators = []
        
        class_body = self._extract_class_body(content, class_start)
        
        # Validator patterns
        validator_pattern = r'@validator\\s*\\(\\s*["\']([^"\']*)["\'].*?\\)\\s*def\\s+(\\w+)'
        matches = re.finditer(validator_pattern, class_body)
        
        for match in matches:
            field_name, func_name = match.groups()
            validators.append({
                'field': field_name,
                'function': func_name,
                'line': class_body[:match.start()].count('\n') + 1
            })
        
        return validators
    
    def _extract_pydantic_config(self, content: str, class_start: int) -> Optional[Dict[str, Any]]:
        """Extract Pydantic Config class."""
        class_body = self._extract_class_body(content, class_start)
        
        config_pattern = r'class\\s+Config\\s*:[^}]*?(?=class|def|$)'
        match = re.search(config_pattern, class_body, re.DOTALL)
        
        if match:
            return {
                'content': match.group(),
                'attributes': self._parse_config_attributes(match.group())
            }
        
        return None
    
    def _extract_class_body(self, content: str, class_start: int) -> str:
        """Extract the body of a class definition."""
        lines = content[class_start:].split('\n')
        class_lines = []
        indent_level = None
        
        for line in lines[1:]:  # Skip the class definition line
            if line.strip() == '':
                class_lines.append(line)
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            if indent_level is None and line.strip():
                indent_level = current_indent
            
            if line.strip() and current_indent <= indent_level and not line.startswith(' ' * indent_level):
                break  # End of class
            
            class_lines.append(line)
        
        return '\n'.join(class_lines)
    
    def _parse_config_attributes(self, config_content: str) -> Dict[str, Any]:
        """Parse Pydantic Config attributes."""
        attributes = {}
        
        # Common Config attributes
        attr_patterns = {
            'allow_population_by_field_name': r'allow_population_by_field_name\\s*=\\s*(True|False)',
            'validate_assignment': r'validate_assignment\\s*=\\s*(True|False)',
            'use_enum_values': r'use_enum_values\\s*=\\s*(True|False)',
            'schema_extra': r'schema_extra\\s*=\\s*({[^}]*})'
        }
        
        for attr_name, pattern in attr_patterns.items():
            match = re.search(pattern, config_content)
            if match:
                value = match.group(1)
                if value in ('True', 'False'):
                    attributes[attr_name] = value == 'True'
                else:
                    attributes[attr_name] = value
        
        return attributes


class FastAPICodeTransformer:
    """Transforms FastAPI code to Beginnings format.
    
    Follows Single Responsibility Principle - only handles code transformation.
    """
    
    def __init__(self):
        """Initialize FastAPI code transformer."""
        self.logger = logging.getLogger(__name__)
    
    def transform_app_file(self, content: str, analysis: Dict[str, Any]) -> str:
        """Transform FastAPI application file to Beginnings format.
        
        Args:
            content: Original FastAPI code
            analysis: Analysis results from FastAPIPatternAnalyzer
            
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
        
        # Transform middleware
        transformed = self._transform_middleware(transformed, analysis.get('middleware', []))
        
        # Transform exception handlers
        transformed = self._transform_exception_handlers(transformed, analysis.get('exception_handlers', []))
        
        # Transform dependencies
        transformed = self._transform_dependencies(transformed, analysis.get('dependencies', []))
        
        return transformed
    
    def transform_models(self, content: str, models: List[Dict[str, Any]]) -> str:
        """Transform Pydantic models to Beginnings format.
        
        Args:
            content: Original Pydantic models code
            models: Model analysis results
            
        Returns:
            Transformed code
        """
        transformed = content
        
        # Transform imports
        transformed = re.sub(r'from pydantic import BaseModel',
                           'from beginnings.extensions.database import db, Model',
                           transformed)
        
        # Transform model base classes
        transformed = re.sub(r'\\(BaseModel\\)', '(Model)', transformed)
        
        # Transform field types and annotations
        transformed = self._transform_pydantic_fields(transformed)
        
        return transformed
    
    def _transform_imports(self, content: str) -> str:
        """Transform FastAPI imports to Beginnings imports."""
        # Replace FastAPI imports
        import_mappings = {
            r'from fastapi import (.+)': self._transform_fastapi_imports,
            r'import fastapi': 'import beginnings',
            r'from pydantic import (.+)': r'from beginnings.models import \\1',
            r'from fastapi.responses import (.+)': r'from beginnings import \\1',
            r'from fastapi.middleware.cors import CORSMiddleware': 'from beginnings.extensions.cors import CORSExtension'
        }
        
        transformed = content
        for pattern, replacement in import_mappings.items():
            if callable(replacement):
                transformed = re.sub(pattern, replacement, transformed)
            else:
                transformed = re.sub(pattern, replacement, transformed)
        
        return transformed
    
    def _transform_fastapi_imports(self, match):
        """Transform specific FastAPI imports."""
        imports = match.group(1)
        import_list = [imp.strip() for imp in imports.split(',')]
        
        fastapi_to_beginnings = {
            'FastAPI': 'create_app',
            'Request': 'request',
            'Response': 'response', 
            'HTTPException': 'abort',
            'Depends': 'dependency',
            'Query': 'query_param',
            'Path': 'path_param',
            'Body': 'body_param',
            'Header': 'header_param',
            'Cookie': 'cookie_param'
        }
        
        beginnings_imports = []
        for imp in import_list:
            if imp in fastapi_to_beginnings:
                beginnings_imports.append(fastapi_to_beginnings[imp])
            else:
                beginnings_imports.append(imp)  # Keep unknown imports
        
        return f"from beginnings import {', '.join(beginnings_imports)}"
    
    def _transform_app_creation(self, content: str, app_creations: List[Dict[str, Any]]) -> str:
        """Transform FastAPI app creation to Beginnings format."""
        transformed = content
        
        for app_creation in app_creations:
            old_pattern = app_creation['pattern']
            var_name = app_creation['variable_name']
            
            # Replace FastAPI() with create_app()
            new_pattern = f"{var_name} = create_app()"
            transformed = transformed.replace(old_pattern, new_pattern)
        
        return transformed
    
    def _transform_routes(self, content: str, routes: List[Dict[str, Any]]) -> str:
        """Transform FastAPI routes to Beginnings format."""
        transformed = content
        
        for route in routes:
            app_var = route['app_variable']
            method = route['method'].lower()
            path = route['path']
            func_name = route['function_name']
            
            # Convert FastAPI route decorator to Beginnings route decorator
            old_decorator = f"@{app_var}.{method}('{path}'"
            new_decorator = f"@{app_var}.route('{path}', methods=['{method.upper()}']"
            
            transformed = transformed.replace(old_decorator, new_decorator)
        
        # Remove async keywords from route handlers
        transformed = re.sub(r'async\\s+def\\s+(\\w+)', r'def \\1', transformed)
        
        # Transform await calls (basic transformation)
        transformed = re.sub(r'await\\s+', '', transformed)
        
        return transformed
    
    def _transform_middleware(self, content: str, middleware: List[Dict[str, Any]]) -> str:
        """Transform FastAPI middleware to Beginnings format."""
        transformed = content
        
        # Transform middleware decorators
        transformed = re.sub(r'@app\\.middleware\\s*\\([^)]+\\)',
                           '@app.before_request',
                           transformed)
        
        # Transform add_middleware calls
        transformed = re.sub(r'app\\.add_middleware\\s*\\([^)]+\\)',
                           '# TODO: Configure middleware in beginnings.yaml',
                           transformed)
        
        return transformed
    
    def _transform_exception_handlers(self, content: str, exception_handlers: List[Dict[str, Any]]) -> str:
        """Transform FastAPI exception handlers to Beginnings format."""
        transformed = content
        
        for handler in exception_handlers:
            exception_type = handler['exception_type']
            func_name = handler['function_name']
            
            # Convert exception handlers
            if 'HTTPException' in exception_type:
                old_decorator = f"@app.exception_handler({exception_type})"
                new_decorator = "@app.errorhandler(Exception)"
                transformed = transformed.replace(old_decorator, new_decorator)
        
        return transformed
    
    def _transform_dependencies(self, content: str, dependencies: List[Dict[str, Any]]) -> str:
        """Transform FastAPI dependencies to Beginnings format."""
        transformed = content
        
        # Transform Depends() calls
        transformed = re.sub(r'Depends\\s*\\(([^)]+)\\)',
                           r'dependency(\\1)',
                           transformed)
        
        # Transform dependency function signatures
        transformed = re.sub(r'def\\s+(\\w+)\\s*\\([^)]*\\)\\s*->.*?:',
                           r'def \\1():',
                           transformed)
        
        return transformed
    
    def _transform_pydantic_fields(self, content: str) -> str:
        """Transform Pydantic field types to Beginnings format."""
        # Transform common Pydantic field types
        field_mappings = {
            ': str': ': db.Column(db.String)',
            ': int': ': db.Column(db.Integer)',
            ': float': ': db.Column(db.Float)',
            ': bool': ': db.Column(db.Boolean)',
            ': datetime': ': db.Column(db.DateTime)',
            ': Optional\\[str\\]': ': db.Column(db.String, nullable=True)',
            ': Optional\\[int\\]': ': db.Column(db.Integer, nullable=True)',
            ': List\\[str\\]': ': db.Column(db.JSON)',
            ': Dict\\[str, Any\\]': ': db.Column(db.JSON)'
        }
        
        transformed = content
        for pydantic_type, beginnings_type in field_mappings.items():
            transformed = re.sub(pydantic_type, beginnings_type, transformed)
        
        return transformed


class FastAPIConverter(MigrationConverter):
    """Converts FastAPI applications to Beginnings framework.
    
    Follows Single Responsibility Principle - orchestrates FastAPI conversion.
    Uses Dependency Inversion - depends on analyzer and transformer abstractions.
    """
    
    def __init__(self):
        """Initialize FastAPI converter."""
        self.logger = logging.getLogger(__name__)
        self.analyzer = FastAPIPatternAnalyzer()
        self.transformer = FastAPICodeTransformer()
    
    def supports_framework(self, framework: FrameworkType) -> bool:
        """Check if converter supports framework.
        
        Args:
            framework: Framework type to check
            
        Returns:
            True if FastAPI framework is supported
        """
        return framework == FrameworkType.FASTAPI
    
    def convert_project(self, source_path: Path, target_path: Path, config: MigrationConfig) -> MigrationResult:
        """Convert entire FastAPI project.
        
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
            self.logger.error(f"FastAPI project conversion failed: {e}")
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Conversion failed: {str(e)}")
        
        return result
    
    def convert_file(self, source_file: Path, target_file: Path) -> bool:
        """Convert individual FastAPI file.
        
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
            
            # Analyze FastAPI patterns
            analysis = self.analyzer.analyze_fastapi_app(content)
            
            # Transform code
            transformed_content = self.transformer.transform_app_file(content, analysis)
            
            # Write transformed content
            target_file.write_text(transformed_content, encoding='utf-8')
            
            self.logger.info(f"Converted {source_file} -> {target_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to convert file {source_file}: {e}")
            return False
    
    def convert_models(self, fastapi_model_code: str) -> str:
        """Convert FastAPI/Pydantic models to Beginnings format.
        
        Args:
            fastapi_model_code: FastAPI model code
            
        Returns:
            Converted model code
        """
        models = self.analyzer.analyze_pydantic_models(fastapi_model_code)
        return self.transformer.transform_models(fastapi_model_code, models)
    
    def convert_routes(self, fastapi_route_code: str) -> str:
        """Convert FastAPI routes to Beginnings format.
        
        Args:
            fastapi_route_code: FastAPI route code
            
        Returns:
            Converted route code
        """
        analysis = self.analyzer.analyze_fastapi_app(fastapi_route_code)
        return self.transformer.transform_app_file(fastapi_route_code, analysis)
    
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
# Beginnings Framework Configuration (converted from FastAPI)
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
  - beginnings.extensions.cors:CORSExtension

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt for Beginnings."""
        return """
# Beginnings Framework Dependencies (converted from FastAPI)
beginnings>=1.0.0

# Database support
SQLAlchemy>=2.0.0

# Web server
gunicorn>=21.0.0

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
"""