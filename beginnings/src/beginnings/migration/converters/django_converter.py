"""Django to Beginnings converter.

This module provides comprehensive conversion from Django applications to
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


class DjangoPatternAnalyzer:
    """Analyzes Django-specific patterns.
    
    Follows Single Responsibility Principle - only handles Django pattern analysis.
    """
    
    def __init__(self):
        """Initialize Django pattern analyzer."""
        self.django_imports = {
            'django.http.HttpResponse': 'beginnings.response',
            'django.http.JsonResponse': 'beginnings.jsonify',
            'django.shortcuts.render': 'beginnings.render_template',
            'django.shortcuts.redirect': 'beginnings.redirect',
            'django.shortcuts.get_object_or_404': 'beginnings.get_or_404',
            'django.contrib.auth.decorators.login_required': 'beginnings.auth_required'
        }
    
    def analyze_django_models(self, content: str) -> List[Dict[str, Any]]:
        """Analyze Django model definitions.
        
        Args:
            content: Django models.py content
            
        Returns:
            List of model analysis results
        """
        models = []
        
        # Find model class definitions
        model_pattern = r'class\s+(\w+)\s*\(\s*([^)]+)\s*\)\s*:'
        matches = re.finditer(model_pattern, content)
        
        for match in matches:
            class_name, base_classes = match.groups()
            
            # Check if it's a Django model
            if 'models.Model' in base_classes or 'Model' in base_classes:
                model_info = {
                    'name': class_name,
                    'base_classes': base_classes,
                    'fields': self._extract_model_fields(content, match.start()),
                    'meta': self._extract_model_meta(content, match.start()),
                    'methods': self._extract_model_methods(content, match.start()),
                    'line': content[:match.start()].count('\n') + 1
                }
                models.append(model_info)
        
        return models
    
    def analyze_django_views(self, content: str) -> Dict[str, Any]:
        """Analyze Django view definitions.
        
        Args:
            content: Django views.py content
            
        Returns:
            View analysis results
        """
        analysis = {
            'function_views': self._find_function_views(content),
            'class_views': self._find_class_views(content),
            'decorators': self._find_view_decorators(content),
            'imports': self._find_django_imports(content)
        }
        
        return analysis
    
    def analyze_django_urls(self, content: str) -> List[Dict[str, Any]]:
        """Analyze Django URL patterns.
        
        Args:
            content: Django urls.py content
            
        Returns:
            List of URL pattern analysis results
        """
        url_patterns = []
        
        # Find path() and url() patterns
        path_pattern = r"path\s*\(\s*[r]?['\"]([^'\"]*)['\"]\s*,\s*([^,]+)(?:,\s*name\s*=\s*['\"]([^'\"]*)['\"])?.*?\)"
        matches = re.finditer(path_pattern, content)
        
        for match in matches:
            path_str, view_ref, name = match.groups()
            url_patterns.append({
                'pattern': path_str,
                'view': view_ref.strip(),
                'name': name,
                'type': 'path',
                'line': content[:match.start()].count('\n') + 1
            })
        
        # Also check for older url() patterns
        url_pattern = r"url\s*\(\s*r['\"]([^'\"]*)['\"]\s*,\s*([^,]+)(?:,\s*name\s*=\s*['\"]([^'\"]*)['\"])?.*?\)"
        matches = re.finditer(url_pattern, content)
        
        for match in matches:
            regex_str, view_ref, name = match.groups()
            url_patterns.append({
                'pattern': regex_str,
                'view': view_ref.strip(),
                'name': name,
                'type': 'url_regex',
                'line': content[:match.start()].count('\n') + 1
            })
        
        return url_patterns
    
    def _extract_model_fields(self, content: str, class_start: int) -> List[Dict[str, Any]]:
        """Extract Django model fields."""
        fields = []
        
        # Find the class body
        class_body = self._extract_class_body(content, class_start)
        
        # Django field patterns
        field_pattern = r'(\w+)\s*=\s*models\.(\w+)\s*\(([^)]*?)\)'
        matches = re.finditer(field_pattern, class_body)
        
        for match in matches:
            field_name, field_type, field_args = match.groups()
            fields.append({
                'name': field_name,
                'type': field_type,
                'args': field_args.strip(),
                'line': class_body[:match.start()].count('\n') + 1
            })
        
        return fields
    
    def _extract_model_meta(self, content: str, class_start: int) -> Optional[Dict[str, Any]]:
        """Extract Django model Meta class."""
        class_body = self._extract_class_body(content, class_start)
        
        meta_pattern = r'class\s+Meta\s*:[^}]*?(?=class|def|$)'
        match = re.search(meta_pattern, class_body, re.DOTALL)
        
        if match:
            meta_content = match.group()
            return {
                'content': meta_content,
                'attributes': self._parse_meta_attributes(meta_content)
            }
        
        return None
    
    def _extract_model_methods(self, content: str, class_start: int) -> List[Dict[str, Any]]:
        """Extract Django model methods."""
        methods = []
        
        class_body = self._extract_class_body(content, class_start)
        
        method_pattern = r'def\s+(\w+)\s*\(([^)]*?)\)\s*:'
        matches = re.finditer(method_pattern, class_body)
        
        for match in matches:
            method_name, method_args = match.groups()
            methods.append({
                'name': method_name,
                'args': method_args.strip(),
                'line': class_body[:match.start()].count('\n') + 1
            })
        
        return methods
    
    def _find_function_views(self, content: str) -> List[Dict[str, Any]]:
        """Find Django function-based views."""
        views = []
        
        # Function views typically take request as first parameter
        view_pattern = r'def\s+(\w+)\s*\(\s*request\s*[^)]*\)\s*:'
        matches = re.finditer(view_pattern, content)
        
        for match in matches:
            func_name = match.group(1)
            views.append({
                'name': func_name,
                'type': 'function',
                'line': content[:match.start()].count('\n') + 1
            })
        
        return views
    
    def _find_class_views(self, content: str) -> List[Dict[str, Any]]:
        """Find Django class-based views."""
        views = []
        
        # Class views inherit from Django view classes
        class_pattern = r'class\s+(\w+)\s*\(\s*([^)]+)\s*\)\s*:'
        matches = re.finditer(class_pattern, content)
        
        for match in matches:
            class_name, base_classes = match.groups()
            
            # Check if it inherits from Django view classes
            django_view_bases = ['View', 'TemplateView', 'ListView', 'DetailView', 'CreateView', 'UpdateView', 'DeleteView']
            if any(base in base_classes for base in django_view_bases):
                views.append({
                    'name': class_name,
                    'type': 'class',
                    'base_classes': base_classes,
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return views
    
    def _find_view_decorators(self, content: str) -> List[Dict[str, Any]]:
        """Find Django view decorators."""
        decorators = []
        
        # Common Django decorators
        decorator_patterns = [
            r'@login_required',
            r'@csrf_exempt',
            r'@require_http_methods\s*\(\s*\[([^\]]+)\]\s*\)',
            r'@permission_required\s*\(\s*[\'"]([^\'"]*)[\'"]\s*\)',
            r'@cache_page\s*\(\s*(\d+)\s*\)'
        ]
        
        for pattern in decorator_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                decorators.append({
                    'decorator': match.group(),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return decorators
    
    def _find_django_imports(self, content: str) -> List[Dict[str, Any]]:
        """Find Django-specific imports."""
        imports = []
        
        import_patterns = [
            r'from django\.[\w.]+ import ([\w, ]+)',
            r'import django\.[\w.]+'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                imports.append({
                    'import': match.group(),
                    'line': content[:match.start()].count('\n') + 1
                })
        
        return imports
    
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
    
    def _parse_meta_attributes(self, meta_content: str) -> Dict[str, Any]:
        """Parse Django model Meta attributes."""
        attributes = {}
        
        # Common Meta attributes
        attr_patterns = {
            'db_table': r'db_table\s*=\s*[\'"]([^\'"]*)[\'"]',
            'ordering': r'ordering\s*=\s*\[([^\]]+)\]',
            'verbose_name': r'verbose_name\s*=\s*[\'"]([^\'"]*)[\'"]',
            'verbose_name_plural': r'verbose_name_plural\s*=\s*[\'"]([^\'"]*)[\'"]'
        }
        
        for attr_name, pattern in attr_patterns.items():
            match = re.search(pattern, meta_content)
            if match:
                attributes[attr_name] = match.group(1)
        
        return attributes


class DjangoCodeTransformer:
    """Transforms Django code to Beginnings format.
    
    Follows Single Responsibility Principle - only handles code transformation.
    """
    
    def __init__(self):
        """Initialize Django code transformer."""
        self.logger = logging.getLogger(__name__)
    
    def transform_models(self, content: str, models: List[Dict[str, Any]]) -> str:
        """Transform Django models to Beginnings format.
        
        Args:
            content: Original Django models code
            models: Model analysis results
            
        Returns:
            Transformed code
        """
        transformed = content
        
        # Transform imports
        transformed = re.sub(r'from django\.db import models', 
                           'from beginnings.extensions.database import db, Model', 
                           transformed)
        
        # Transform model base classes
        transformed = re.sub(r'\(models\.Model\)', '(Model)', transformed)
        
        # Transform field types
        field_mappings = {
            'models.CharField': 'db.Column(db.String',
            'models.TextField': 'db.Column(db.Text',
            'models.IntegerField': 'db.Column(db.Integer',
            'models.DateTimeField': 'db.Column(db.DateTime',
            'models.BooleanField': 'db.Column(db.Boolean',
            'models.ForeignKey': 'db.relationship',
            'models.EmailField': 'db.Column(db.String',
            'models.URLField': 'db.Column(db.String'
        }
        
        for django_field, beginnings_field in field_mappings.items():
            transformed = transformed.replace(django_field, beginnings_field)
        
        # Transform field arguments
        transformed = self._transform_field_arguments(transformed)
        
        return transformed
    
    def transform_views(self, content: str, analysis: Dict[str, Any]) -> str:
        """Transform Django views to Beginnings format.
        
        Args:
            content: Original Django views code
            analysis: View analysis results
            
        Returns:
            Transformed code
        """
        transformed = content
        
        # Transform imports
        import_mappings = {
            'from django.http import HttpResponse': 'from beginnings import response',
            'from django.http import JsonResponse': 'from beginnings import jsonify',
            'from django.shortcuts import render': 'from beginnings import render_template',
            'from django.shortcuts import redirect': 'from beginnings import redirect',
            'from django.shortcuts import get_object_or_404': 'from beginnings import get_or_404'
        }
        
        for django_import, beginnings_import in import_mappings.items():
            transformed = transformed.replace(django_import, beginnings_import)
        
        # Transform class-based views to function-based views
        transformed = self._transform_class_views(transformed, analysis.get('class_views', []))
        
        # Transform function-based views
        transformed = self._transform_function_views(transformed, analysis.get('function_views', []))
        
        # Transform decorators
        transformed = self._transform_view_decorators(transformed)
        
        return transformed
    
    def transform_urls(self, content: str, url_patterns: List[Dict[str, Any]]) -> str:
        """Transform Django URLs to Beginnings routes.
        
        Args:
            content: Original Django urls.py content
            url_patterns: URL pattern analysis results
            
        Returns:
            Transformed code with route definitions
        """
        # Start with Beginnings route structure
        route_definitions = []
        
        for pattern in url_patterns:
            path = pattern['pattern']
            view = pattern['view']
            name = pattern.get('name', '')
            
            # Convert Django URL pattern to Flask-style route
            beginnings_path = self._convert_url_pattern(path)
            
            # Generate route decorator
            route_def = f"@app.route('{beginnings_path}')"
            if name:
                route_def += f"  # name: {name}"
            
            route_definitions.append(route_def)
        
        # Create new content with routes
        header = """
from beginnings import create_app

app = create_app()

"""
        
        routes_content = '\n\n'.join(route_definitions)
        
        return header + routes_content
    
    def _transform_field_arguments(self, content: str) -> str:
        """Transform Django field arguments to Beginnings format."""
        # Transform common field arguments
        arg_mappings = {
            'max_length': 'length',
            'null=True': 'nullable=True',
            'null=False': 'nullable=False',
            'blank=True': '',  # Remove blank argument
            'blank=False': '',  # Remove blank argument
            'auto_now_add=True': 'default=db.func.current_timestamp()',
            'auto_now=True': 'onupdate=db.func.current_timestamp()'
        }
        
        transformed = content
        for django_arg, beginnings_arg in arg_mappings.items():
            if beginnings_arg:
                transformed = transformed.replace(django_arg, beginnings_arg)
            else:
                transformed = re.sub(r',?\s*' + re.escape(django_arg), '', transformed)
        
        return transformed
    
    def _transform_class_views(self, content: str, class_views: List[Dict[str, Any]]) -> str:
        """Transform Django class-based views to function-based views."""
        transformed = content
        
        for view in class_views:
            class_name = view['name']
            base_classes = view['base_classes']
            
            # Generate function-based view
            if 'ListView' in base_classes:
                func_code = self._generate_list_view_function(class_name)
            elif 'DetailView' in base_classes:
                func_code = self._generate_detail_view_function(class_name)
            else:
                func_code = self._generate_generic_view_function(class_name)
            
            # Replace class definition with function
            class_pattern = rf'class\s+{class_name}\s*\([^)]+\)\s*:.*?(?=class|def|$)'
            transformed = re.sub(class_pattern, func_code, transformed, flags=re.DOTALL)
        
        return transformed
    
    def _transform_function_views(self, content: str, function_views: List[Dict[str, Any]]) -> str:
        """Transform Django function-based views."""
        transformed = content
        
        # Transform response objects
        transformed = transformed.replace('HttpResponse(', 'response(')
        transformed = transformed.replace('JsonResponse(', 'jsonify(')
        transformed = transformed.replace('render(request,', 'render_template(')
        
        return transformed
    
    def _transform_view_decorators(self, content: str) -> str:
        """Transform Django view decorators."""
        decorator_mappings = {
            '@login_required': '@auth_required',
            '@csrf_exempt': '@csrf.exempt',
            '@require_http_methods': '@app.route'
        }
        
        transformed = content
        for django_decorator, beginnings_decorator in decorator_mappings.items():
            transformed = transformed.replace(django_decorator, beginnings_decorator)
        
        return transformed
    
    def _convert_url_pattern(self, django_pattern: str) -> str:
        """Convert Django URL pattern to Flask-style route."""
        # Convert Django named groups to Flask parameters
        # Example: (?P<id>\d+) -> <int:id>
        pattern = django_pattern
        
        # Convert named groups
        pattern = re.sub(r'\(\?P<(\w+)>\\d\+\)', r'<int:\1>', pattern)
        pattern = re.sub(r'\(\?P<(\w+)>[^)]+\)', r'<\1>', pattern)
        
        # Remove regex anchors
        pattern = pattern.replace('^', '').replace('$', '')
        
        # Ensure it starts with /
        if not pattern.startswith('/'):
            pattern = '/' + pattern
        
        return pattern
    
    def _generate_list_view_function(self, class_name: str) -> str:
        """Generate function-based view for ListView."""
        func_name = class_name.lower().replace('view', '')
        return f"""
@app.route('/{func_name}/')
def {func_name}_list():
    # TODO: Implement list view logic
    return render_template('{func_name}_list.html')
"""
    
    def _generate_detail_view_function(self, class_name: str) -> str:
        """Generate function-based view for DetailView."""
        func_name = class_name.lower().replace('view', '')
        return f"""
@app.route('/{func_name}/<int:id>/')
def {func_name}_detail(id):
    # TODO: Implement detail view logic
    return render_template('{func_name}_detail.html')
"""
    
    def _generate_generic_view_function(self, class_name: str) -> str:
        """Generate generic function-based view."""
        func_name = class_name.lower().replace('view', '')
        return f"""
@app.route('/{func_name}/')
def {func_name}():
    # TODO: Implement view logic
    return render_template('{func_name}.html')
"""


class DjangoConverter(MigrationConverter):
    """Converts Django applications to Beginnings framework.
    
    Follows Single Responsibility Principle - orchestrates Django conversion.
    Uses Dependency Inversion - depends on analyzer and transformer abstractions.
    """
    
    def __init__(self):
        """Initialize Django converter."""
        self.logger = logging.getLogger(__name__)
        self.analyzer = DjangoPatternAnalyzer()
        self.transformer = DjangoCodeTransformer()
    
    def supports_framework(self, framework: FrameworkType) -> bool:
        """Check if converter supports framework.
        
        Args:
            framework: Framework type to check
            
        Returns:
            True if Django framework is supported
        """
        return framework == FrameworkType.DJANGO
    
    def convert_project(self, source_path: Path, target_path: Path, config: MigrationConfig) -> MigrationResult:
        """Convert entire Django project.
        
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
            # Convert models.py files
            models_files = list(source_path.rglob("models.py"))
            for models_file in models_files:
                if self._should_convert_file(models_file, config):
                    self._convert_models_file(models_file, target_path, result)
            
            # Convert views.py files
            views_files = list(source_path.rglob("views.py"))
            for views_file in views_files:
                if self._should_convert_file(views_file, config):
                    self._convert_views_file(views_file, target_path, result)
            
            # Convert urls.py files
            urls_files = list(source_path.rglob("urls.py"))
            for urls_file in urls_files:
                if self._should_convert_file(urls_file, config):
                    self._convert_urls_file(urls_file, target_path, result)
            
            # Convert settings.py
            settings_files = list(source_path.rglob("settings.py"))
            for settings_file in settings_files:
                if self._should_convert_file(settings_file, config):
                    self._convert_settings_file(settings_file, target_path, result)
            
            # Copy other Python files
            self._copy_other_files(source_path, target_path, config, result)
            
            # Generate main app file
            self._generate_main_app_file(target_path, result)
            
            result.success = len(result.errors) == 0
            result.status = MigrationStatus.COMPLETED if result.success else MigrationStatus.PARTIAL
            
        except Exception as e:
            self.logger.error(f"Django project conversion failed: {e}")
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Conversion failed: {str(e)}")
        
        return result
    
    def convert_file(self, source_file: Path, target_file: Path) -> bool:
        """Convert individual Django file.
        
        Args:
            source_file: Source file path
            target_file: Target file path
            
        Returns:
            True if conversion successful
        """
        try:
            content = source_file.read_text(encoding='utf-8')
            
            if source_file.name == 'models.py':
                models = self.analyzer.analyze_django_models(content)
                transformed_content = self.transformer.transform_models(content, models)
            elif source_file.name == 'views.py':
                analysis = self.analyzer.analyze_django_views(content)
                transformed_content = self.transformer.transform_views(content, analysis)
            elif source_file.name == 'urls.py':
                url_patterns = self.analyzer.analyze_django_urls(content)
                transformed_content = self.transformer.transform_urls(content, url_patterns)
            else:
                # Basic transformation for other files
                transformed_content = content
            
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(transformed_content, encoding='utf-8')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to convert Django file {source_file}: {e}")
            return False
    
    def convert_models(self, django_model_code: str) -> str:
        """Convert Django models to Beginnings format.
        
        Args:
            django_model_code: Django model code
            
        Returns:
            Converted model code
        """
        models = self.analyzer.analyze_django_models(django_model_code)
        return self.transformer.transform_models(django_model_code, models)
    
    def convert_views(self, django_view_code: str) -> str:
        """Convert Django views to Beginnings format.
        
        Args:
            django_view_code: Django view code
            
        Returns:
            Converted view code
        """
        analysis = self.analyzer.analyze_django_views(django_view_code)
        return self.transformer.transform_views(django_view_code, analysis)
    
    def convert_urls(self, django_urls_code: str) -> str:
        """Convert Django URLs to Beginnings routes.
        
        Args:
            django_urls_code: Django URLs code
            
        Returns:
            Converted routes code
        """
        url_patterns = self.analyzer.analyze_django_urls(django_urls_code)
        return self.transformer.transform_urls(django_urls_code, url_patterns)
    
    def convert_settings(self, django_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Django settings to Beginnings configuration.
        
        Args:
            django_settings: Django settings dictionary
            
        Returns:
            Converted configuration
        """
        beginnings_config = {
            'app': {},
            'database': {},
            'extensions': []
        }
        
        # Map Django settings to Beginnings structure
        if 'DEBUG' in django_settings:
            beginnings_config['app']['debug'] = django_settings['DEBUG']
        
        if 'SECRET_KEY' in django_settings:
            beginnings_config['app']['secret_key'] = django_settings['SECRET_KEY']
        
        if 'DATABASES' in django_settings:
            default_db = django_settings['DATABASES'].get('default', {})
            if default_db:
                engine = default_db.get('ENGINE', '')
                if 'postgresql' in engine:
                    db_url = f"postgresql://{default_db.get('USER', '')}:{default_db.get('PASSWORD', '')}@{default_db.get('HOST', 'localhost')}:{default_db.get('PORT', 5432)}/{default_db.get('NAME', '')}"
                elif 'mysql' in engine:
                    db_url = f"mysql://{default_db.get('USER', '')}:{default_db.get('PASSWORD', '')}@{default_db.get('HOST', 'localhost')}:{default_db.get('PORT', 3306)}/{default_db.get('NAME', '')}"
                else:
                    db_url = f"sqlite:///{default_db.get('NAME', 'db.sqlite3')}"
                
                beginnings_config['database']['uri'] = db_url
        
        return beginnings_config
    
    def _should_convert_file(self, file_path: Path, config: MigrationConfig) -> bool:
        """Check if file should be converted."""
        # Skip migration files
        if 'migrations' in str(file_path):
            return False
        
        # Skip test files unless specifically requested
        if not config.include_tests and 'test' in str(file_path):
            return False
        
        # Skip __pycache__ and other generated directories
        if '__pycache__' in str(file_path) or '.git' in str(file_path):
            return False
        
        return True
    
    def _convert_models_file(self, models_file: Path, target_path: Path, result: MigrationResult) -> None:
        """Convert Django models.py file."""
        try:
            content = models_file.read_text(encoding='utf-8')
            models = self.analyzer.analyze_django_models(content)
            transformed_content = self.transformer.transform_models(content, models)
            
            # Create target file path
            relative_path = models_file.relative_to(models_file.parents[1])  # Get relative path from Django app
            target_file = target_path / relative_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            target_file.write_text(transformed_content, encoding='utf-8')
            result.migrated_files.append(target_file)
            
        except Exception as e:
            result.errors.append(f"Failed to convert models file {models_file}: {e}")
    
    def _convert_views_file(self, views_file: Path, target_path: Path, result: MigrationResult) -> None:
        """Convert Django views.py file."""
        try:
            content = views_file.read_text(encoding='utf-8')
            analysis = self.analyzer.analyze_django_views(content)
            transformed_content = self.transformer.transform_views(content, analysis)
            
            relative_path = views_file.relative_to(views_file.parents[1])
            target_file = target_path / relative_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            target_file.write_text(transformed_content, encoding='utf-8')
            result.migrated_files.append(target_file)
            
        except Exception as e:
            result.errors.append(f"Failed to convert views file {views_file}: {e}")
    
    def _convert_urls_file(self, urls_file: Path, target_path: Path, result: MigrationResult) -> None:
        """Convert Django urls.py file."""
        try:
            content = urls_file.read_text(encoding='utf-8')
            url_patterns = self.analyzer.analyze_django_urls(content)
            transformed_content = self.transformer.transform_urls(content, url_patterns)
            
            # Save as routes.py instead of urls.py
            relative_path = urls_file.relative_to(urls_file.parents[1])
            target_file = target_path / relative_path.with_name('routes.py')
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            target_file.write_text(transformed_content, encoding='utf-8')
            result.created_files.append(target_file)
            
        except Exception as e:
            result.errors.append(f"Failed to convert urls file {urls_file}: {e}")
    
    def _convert_settings_file(self, settings_file: Path, target_path: Path, result: MigrationResult) -> None:
        """Convert Django settings.py file to Beginnings configuration."""
        try:
            # Parse Django settings (simplified)
            # In a real implementation, you'd use ast or exec to safely parse the settings
            content = settings_file.read_text(encoding='utf-8')
            
            # Generate Beginnings config file
            config_content = """
# Beginnings Configuration (converted from Django settings)
app:
  name: "My Beginnings App"
  debug: true
  secret_key: "your-secret-key-here"

database:
  uri: "sqlite:///app.db"

extensions:
  - beginnings.extensions.database:DatabaseExtension
  - beginnings.extensions.auth:AuthExtension
"""
            
            config_file = target_path / 'beginnings.yaml'
            config_file.write_text(config_content, encoding='utf-8')
            result.created_files.append(config_file)
            
        except Exception as e:
            result.errors.append(f"Failed to convert settings file {settings_file}: {e}")
    
    def _copy_other_files(self, source_path: Path, target_path: Path, config: MigrationConfig, result: MigrationResult) -> None:
        """Copy other Python files that don't need special conversion."""
        python_files = list(source_path.rglob("*.py"))
        special_files = {'models.py', 'views.py', 'urls.py', 'settings.py', 'manage.py'}
        
        for py_file in python_files:
            if py_file.name not in special_files and self._should_convert_file(py_file, config):
                try:
                    relative_path = py_file.relative_to(source_path)
                    target_file = target_path / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Basic transformation - mainly import changes
                    content = py_file.read_text(encoding='utf-8')
                    transformed_content = content.replace('from django', '# from django')
                    
                    target_file.write_text(transformed_content, encoding='utf-8')
                    result.migrated_files.append(target_file)
                    
                except Exception as e:
                    result.errors.append(f"Failed to copy file {py_file}: {e}")
    
    def _generate_main_app_file(self, target_path: Path, result: MigrationResult) -> None:
        """Generate main Beginnings application file."""
        try:
            app_content = """
from beginnings import create_app
from beginnings.extensions.database import DatabaseExtension

app = create_app()
db = DatabaseExtension()

# Import routes from converted Django apps
# TODO: Add route imports here

if __name__ == '__main__':
    app.run(debug=True)
"""
            
            app_file = target_path / 'app.py'
            app_file.write_text(app_content, encoding='utf-8')
            result.created_files.append(app_file)
            
        except Exception as e:
            result.errors.append(f"Failed to generate main app file: {e}")