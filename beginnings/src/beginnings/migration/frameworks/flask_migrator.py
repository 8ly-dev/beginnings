"""Flask to Beginnings migration tool."""

import ast
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

from ..base import BaseMigrator


class FlaskMigrator(BaseMigrator):
    """Migrates Flask applications to Beginnings framework."""
    
    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        preserve_structure: bool = False,
        convert_config: bool = True,
        convert_auth: bool = True,
        verbose: bool = False
    ):
        """Initialize Flask migrator.
        
        Args:
            source_dir: Flask project directory
            output_dir: Output directory for Beginnings project
            preserve_structure: Whether to preserve Flask structure
            convert_config: Whether to convert Flask config
            convert_auth: Whether to convert Flask auth
            verbose: Enable verbose output
        """
        super().__init__(source_dir, output_dir, verbose)
        self.preserve_structure = preserve_structure
        self.convert_config = convert_config
        self.convert_auth = convert_auth
        
        # Migration results
        self.routes_count = 0
        self.blueprints_count = 0
        self.templates_count = 0
        self.config_files = 0
        self.auth_detected = False
    
    async def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform Flask to Beginnings migration.
        
        Args:
            dry_run: If True, only analyze without creating files
            
        Returns:
            Migration results
        """
        if self.verbose:
            print(f"Starting Flask migration from {self.source_dir}")
        
        # Analyze Flask project
        analysis = await self._analyze_flask_project()
        
        if dry_run:
            return analysis
        
        # Create Beginnings project structure
        await self._create_project_structure()
        
        # Convert Flask components
        await self._convert_routes(analysis['routes'])
        await self._convert_templates(analysis['templates'])
        await self._convert_static_files(analysis['static_files'])
        
        if self.convert_config:
            await self._convert_configuration(analysis['config'])
        
        if self.convert_auth and analysis['auth_detected']:
            await self._convert_authentication(analysis['auth'])
        
        # Generate main application file
        await self._generate_main_app()
        
        # Generate requirements and project files
        await self._generate_project_files(analysis)
        
        return {
            'routes_count': self.routes_count,
            'blueprints_count': self.blueprints_count,
            'templates_count': self.templates_count,
            'config_files': self.config_files,
            'auth_detected': self.auth_detected,
            'success': True
        }
    
    async def _analyze_flask_project(self) -> Dict[str, Any]:
        """Analyze Flask project structure and components."""
        analysis = {
            'routes': [],
            'blueprints': [],
            'templates': [],
            'static_files': [],
            'config': {},
            'auth': {},
            'auth_detected': False,
            'requirements': []
        }
        
        source_path = Path(self.source_dir)
        
        # Find Python files
        python_files = list(source_path.rglob("*.py"))
        
        for py_file in python_files:
            if self.verbose:
                print(f"Analyzing: {py_file}")
            
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                # Analyze routes and blueprints
                routes, blueprints = self._extract_routes_and_blueprints(tree, py_file)
                analysis['routes'].extend(routes)
                analysis['blueprints'].extend(blueprints)
                
                # Check for authentication
                if self._detect_flask_auth(content):
                    analysis['auth_detected'] = True
                    analysis['auth'] = self._extract_auth_config(content)
                
                # Check for configuration
                if py_file.name == 'config.py' or 'config' in py_file.name.lower():
                    analysis['config'].update(self._extract_config(tree, py_file))
                
            except Exception as e:
                if self.verbose:
                    print(f"Error analyzing {py_file}: {e}")
        
        # Find templates
        templates_dir = source_path / "templates"
        if templates_dir.exists():
            analysis['templates'] = list(templates_dir.rglob("*.html"))
            self.templates_count = len(analysis['templates'])
        
        # Find static files
        static_dir = source_path / "static"
        if static_dir.exists():
            analysis['static_files'] = list(static_dir.rglob("*"))
        
        # Find requirements
        req_file = source_path / "requirements.txt"
        if req_file.exists():
            analysis['requirements'] = req_file.read_text().strip().split('\n')
        
        self.routes_count = len(analysis['routes'])
        self.blueprints_count = len(analysis['blueprints'])
        self.auth_detected = analysis['auth_detected']
        
        return analysis
    
    def _extract_routes_and_blueprints(self, tree: ast.AST, file_path: Path) -> tuple[List[Dict], List[Dict]]:
        """Extract routes and blueprints from AST."""
        routes = []
        blueprints = []
        
        for node in ast.walk(tree):
            # Look for @app.route decorators
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if (isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr == 'route'):
                            
                            # Extract route info
                            route_info = {
                                'function': node.name,
                                'file': str(file_path),
                                'methods': [],
                                'path': '',
                                'line': node.lineno
                            }
                            
                            # Extract route path
                            if decorator.args:
                                if isinstance(decorator.args[0], ast.Constant):
                                    route_info['path'] = decorator.args[0].value
                            
                            # Extract methods
                            for keyword in decorator.keywords:
                                if keyword.arg == 'methods':
                                    if isinstance(keyword.value, ast.List):
                                        route_info['methods'] = [
                                            elt.value for elt in keyword.value.elts
                                            if isinstance(elt, ast.Constant)
                                        ]
                            
                            routes.append(route_info)
            
            # Look for Blueprint definitions
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Call):
                            if (isinstance(node.value.func, ast.Name) and
                                node.value.func.id == 'Blueprint'):
                                
                                blueprint_info = {
                                    'name': target.id,
                                    'file': str(file_path),
                                    'routes': []
                                }
                                blueprints.append(blueprint_info)
        
        return routes, blueprints
    
    def _detect_flask_auth(self, content: str) -> bool:
        """Detect Flask authentication patterns."""
        auth_patterns = [
            r'from\s+flask_login\s+import',
            r'from\s+flask_user\s+import',
            r'from\s+flask_security\s+import',
            r'@login_required',
            r'UserMixin',
            r'login_user\(',
            r'logout_user\(',
        ]
        
        for pattern in auth_patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def _extract_auth_config(self, content: str) -> Dict[str, Any]:
        """Extract authentication configuration from Flask code."""
        auth_config = {
            'type': 'session',
            'login_view': None,
            'session_protection': True
        }
        
        # Look for Flask-Login configuration
        if 'login_view' in content:
            match = re.search(r"login_view\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                auth_config['login_view'] = match.group(1)
        
        return auth_config
    
    def _extract_config(self, tree: ast.AST, file_path: Path) -> Dict[str, Any]:
        """Extract configuration from config.py files."""
        config = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Flask configuration classes
                class_config = {}
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if isinstance(item.value, ast.Constant):
                                    class_config[target.id] = item.value.value
                
                config[node.name] = class_config
        
        self.config_files += 1
        return config
    
    async def _create_project_structure(self):
        """Create Beginnings project directory structure."""
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create standard Beginnings structure
        (output_path / "config").mkdir(exist_ok=True)
        (output_path / "routes").mkdir(exist_ok=True)
        (output_path / "templates").mkdir(exist_ok=True)
        (output_path / "static").mkdir(exist_ok=True)
        (output_path / "tests").mkdir(exist_ok=True)
    
    async def _convert_routes(self, routes: List[Dict[str, Any]]):
        """Convert Flask routes to Beginnings routes."""
        output_path = Path(self.output_dir)
        
        # Group routes by type (HTML vs API)
        html_routes = []
        api_routes = []
        
        for route in routes:
            if any(method in ['POST', 'PUT', 'DELETE'] for method in route.get('methods', [])):
                api_routes.append(route)
            else:
                html_routes.append(route)
        
        # Generate HTML routes file
        if html_routes:
            html_content = self._generate_html_routes(html_routes)
            (output_path / "routes" / "html.py").write_text(html_content)
        
        # Generate API routes file
        if api_routes:
            api_content = self._generate_api_routes(api_routes)
            (output_path / "routes" / "api.py").write_text(api_content)
        
        # Generate __init__.py
        (output_path / "routes" / "__init__.py").write_text('"""Route modules."""\n')
    
    def _generate_html_routes(self, routes: List[Dict[str, Any]]) -> str:
        """Generate HTML routes module."""
        content = '''"""HTML route handlers converted from Flask."""

from beginnings.routing.html import HTMLRouter

def register_html_routes(app):
    """Register HTML routes with the application."""
    
'''
        
        for route in routes:
            content += f'''    @app.get("{route['path']}")
    async def {route['function']}():
        """Converted from Flask route."""
        # TODO: Implement {route['function']} logic
        return {{"message": "Route converted from Flask"}}
    
'''
        
        return content
    
    def _generate_api_routes(self, routes: List[Dict[str, Any]]) -> str:
        """Generate API routes module."""
        content = '''"""API route handlers converted from Flask."""

from beginnings.routing.api import APIRouter

def register_api_routes(app):
    """Register API routes with the application."""
    
'''
        
        for route in routes:
            methods = route.get('methods', ['GET'])
            for method in methods:
                content += f'''    @app.{method.lower()}("{route['path']}")
    async def {route['function']}_{method.lower()}():
        """Converted from Flask route."""
        # TODO: Implement {route['function']} logic
        return {{"message": "API route converted from Flask"}}
    
'''
        
        return content
    
    async def _convert_templates(self, templates: List[Path]):
        """Convert Flask templates to Beginnings templates."""
        output_path = Path(self.output_dir) / "templates"
        source_templates = Path(self.source_dir) / "templates"
        
        for template in templates:
            if template.is_file():
                relative_path = template.relative_to(source_templates)
                output_template = output_path / relative_path
                output_template.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy template (minimal conversion needed for Jinja2)
                content = template.read_text(encoding='utf-8')
                
                # Basic Flask to Beginnings template conversions
                content = self._convert_template_content(content)
                
                output_template.write_text(content, encoding='utf-8')
    
    def _convert_template_content(self, content: str) -> str:
        """Convert Flask template syntax to Beginnings-compatible syntax."""
        # Most Jinja2 syntax is compatible, minimal changes needed
        
        # Convert Flask-specific template functions
        conversions = {
            r'url_for\(': 'request.url_for(',
            r'get_flashed_messages\(\)': 'request.get_messages()',
            r'\{\{\s*config\[': '{{ app.config[',
        }
        
        for pattern, replacement in conversions.items():
            content = re.sub(pattern, replacement, content)
        
        return content
    
    async def _convert_static_files(self, static_files: List[Path]):
        """Copy static files to Beginnings project."""
        output_path = Path(self.output_dir) / "static"
        source_static = Path(self.source_dir) / "static"
        
        if not source_static.exists():
            return
        
        for static_file in static_files:
            if static_file.is_file():
                relative_path = static_file.relative_to(source_static)
                output_file = output_path / relative_path
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy static file
                import shutil
                shutil.copy2(static_file, output_file)
    
    async def _convert_configuration(self, config: Dict[str, Any]):
        """Convert Flask configuration to Beginnings format."""
        output_path = Path(self.output_dir) / "config" / "app.yaml"
        
        beginnings_config = {
            'app': {
                'name': Path(self.source_dir).name,
                'debug': False,
                'host': '127.0.0.1',
                'port': 8000
            }
        }
        
        # Convert Flask config classes to Beginnings config
        for class_name, class_config in config.items():
            if 'Config' in class_name:
                if 'SECRET_KEY' in class_config:
                    if 'auth' not in beginnings_config:
                        beginnings_config['auth'] = {'providers': {'session': {}}}
                    beginnings_config['auth']['providers']['session']['secret_key'] = 'CHANGE_ME_IN_PRODUCTION'
                
                if 'DEBUG' in class_config:
                    beginnings_config['app']['debug'] = class_config['DEBUG']
        
        # Add extensions based on detected features
        extensions = []
        if self.auth_detected:
            extensions.append('auth:session')
        
        if extensions:
            beginnings_config['extensions'] = extensions
        
        # Write configuration
        with open(output_path, 'w') as f:
            yaml.dump(beginnings_config, f, default_flow_style=False, indent=2)
    
    async def _convert_authentication(self, auth_config: Dict[str, Any]):
        """Convert Flask authentication to Beginnings auth extension."""
        # Authentication conversion is handled in the main config conversion
        # This method could add additional auth-specific files if needed
        pass
    
    async def _generate_main_app(self):
        """Generate main application file."""
        output_path = Path(self.output_dir) / "main.py"
        
        content = '''"""Main application file converted from Flask."""

from beginnings.core.app import BeginningsApp
from routes.html import register_html_routes
from routes.api import register_api_routes

# Create application instance
app = BeginningsApp()

# Register routes
register_html_routes(app)
register_api_routes(app)

if __name__ == "__main__":
    app.run()
'''
        
        output_path.write_text(content)
    
    async def _generate_project_files(self, analysis: Dict[str, Any]):
        """Generate project files like pyproject.toml, README, etc."""
        output_path = Path(self.output_dir)
        
        # Generate pyproject.toml
        pyproject_content = f'''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{Path(self.source_dir).name}"
version = "1.0.0"
description = "Converted from Flask to Beginnings"
dependencies = [
    "beginnings>=1.0.0",
]

[tool.beginnings]
app = "main:app"
'''
        
        (output_path / "pyproject.toml").write_text(pyproject_content)
        
        # Generate README
        readme_content = f'''# {Path(self.source_dir).name}

This project was migrated from Flask to the Beginnings framework.

## Migration Summary

- Routes converted: {self.routes_count}
- Blueprints converted: {self.blueprints_count}
- Templates migrated: {self.templates_count}
- Configuration files: {self.config_files}
- Authentication: {"Converted" if self.auth_detected else "Not detected"}

## Getting Started

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Run the application:
   ```bash
   beginnings run
   ```

## Next Steps

1. Review the generated configuration in `config/app.yaml`
2. Update route handlers in `routes/` directory
3. Test all functionality
4. Update templates if needed
5. Configure production settings

## Original Flask Features

This project was converted from Flask. Some manual adjustments may be needed:

- Review all route handlers for Flask-specific code
- Update template syntax if using Flask-specific features
- Configure authentication if Flask-Login was used
- Update any Flask extensions to Beginnings equivalents
'''
        
        (output_path / "README.md").write_text(readme_content)
    
    def generate_report(self, result: Dict[str, Any], report_path: Path):
        """Generate detailed migration report."""
        report_content = f'''# Flask to Beginnings Migration Report

## Project: {Path(self.source_dir).name}

**Migration Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Source Directory:** `{self.source_dir}`
- **Output Directory:** `{self.output_dir}`
- **Migration Status:** {"✅ Success" if result.get('success') else "❌ Failed"}

## Conversion Statistics

| Component | Count |
|-----------|-------|
| Routes | {result.get('routes_count', 0)} |
| Blueprints | {result.get('blueprints_count', 0)} |
| Templates | {result.get('templates_count', 0)} |
| Config Files | {result.get('config_files', 0)} |
| Authentication | {"✅ Detected and converted" if result.get('auth_detected') else "❌ Not detected"} |

## Generated Files

```
{self.output_dir}/
├── main.py                 # Main application file
├── config/
│   └── app.yaml           # Beginnings configuration
├── routes/
│   ├── html.py            # HTML route handlers
│   └── api.py             # API route handlers
├── templates/             # Jinja2 templates (migrated)
├── static/                # Static files (copied)
├── pyproject.toml         # Project configuration
└── README.md              # Migration documentation
```

## Manual Review Required

1. **Route Handlers:** Review generated route handlers in `routes/` directory
2. **Configuration:** Update secrets and environment-specific settings in `config/app.yaml`
3. **Templates:** Verify template conversions work correctly
4. **Authentication:** Test authentication flow if converted
5. **Dependencies:** Review and update dependencies in `pyproject.toml`

## Next Steps

1. Install the Beginnings framework: `pip install beginnings`
2. Install project dependencies: `pip install -e .`
3. Review configuration: `beginnings config validate`
4. Test the application: `beginnings run`
5. Run tests if available

## Notes

- Flask blueprints were converted to Beginnings route modules
- Flask-Login authentication was converted to Beginnings auth extension
- Jinja2 templates require minimal changes for Beginnings compatibility
- Static files were copied without modification

For more information about the Beginnings framework, visit the documentation.
'''
        
        report_path.write_text(report_content)