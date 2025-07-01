"""FastAPI to Beginnings migration tool."""

import ast
from pathlib import Path
from typing import Dict, List, Any
import asyncio

from ..base import BaseMigrator


class FastAPIMigrator(BaseMigrator):
    """Migrates FastAPI applications to Beginnings framework."""
    
    def __init__(
        self,
        source_dir: str,
        output_dir: str,
        preserve_structure: bool = False,
        convert_models: bool = True,
        convert_auth: bool = True,
        convert_dependencies: bool = True,
        verbose: bool = False
    ):
        """Initialize FastAPI migrator.
        
        Args:
            source_dir: FastAPI project directory
            output_dir: Output directory for Beginnings project
            preserve_structure: Whether to preserve FastAPI structure
            convert_models: Whether to convert Pydantic models
            convert_auth: Whether to convert FastAPI auth
            convert_dependencies: Whether to convert dependencies
            verbose: Enable verbose output
        """
        super().__init__(source_dir, output_dir, verbose)
        self.preserve_structure = preserve_structure
        self.convert_models = convert_models
        self.convert_auth = convert_auth
        self.convert_dependencies = convert_dependencies
    
    async def migrate(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform FastAPI to Beginnings migration.
        
        Args:
            dry_run: If True, only analyze without creating files
            
        Returns:
            Migration results
        """
        if self.verbose:
            print(f"Starting FastAPI migration from {self.source_dir}")
        
        # Analyze FastAPI project
        analysis = await self._analyze_fastapi_project()
        
        if dry_run:
            return analysis
        
        # Create Beginnings project
        await self._create_project_structure()
        await self._convert_routes(analysis['routes'])
        await self._convert_models(analysis['models'])
        await self._generate_main_app(analysis)
        await self._generate_config(analysis)
        
        return analysis
    
    async def _analyze_fastapi_project(self) -> Dict[str, Any]:
        """Analyze FastAPI project structure."""
        analysis = {
            'routes': [],
            'routers': [],
            'models': [],
            'dependencies': [],
            'auth_detected': False,
            'routes_count': 0,
            'routers_count': 0,
            'models_count': 0,
            'dependencies_count': 0,
            'success': True
        }
        
        source_path = Path(self.source_dir)
        python_files = list(source_path.rglob("*.py"))
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                # Analyze routes and routers
                routes, routers = self._extract_fastapi_routes(tree, py_file)
                analysis['routes'].extend(routes)
                analysis['routers'].extend(routers)
                
                # Analyze models
                models = self._extract_pydantic_models(tree, py_file)
                analysis['models'].extend(models)
                
                # Check for authentication
                if self._detect_fastapi_auth(content):
                    analysis['auth_detected'] = True
                
                # Count dependencies
                dependencies = self._extract_dependencies(tree)
                analysis['dependencies'].extend(dependencies)
                
            except Exception as e:
                if self.verbose:
                    print(f"Error analyzing {py_file}: {e}")
        
        # Update counts
        analysis['routes_count'] = len(analysis['routes'])
        analysis['routers_count'] = len(analysis['routers'])
        analysis['models_count'] = len(analysis['models'])
        analysis['dependencies_count'] = len(analysis['dependencies'])
        
        return analysis
    
    def _extract_fastapi_routes(self, tree: ast.AST, file_path: Path) -> tuple[List[Dict], List[Dict]]:
        """Extract FastAPI routes and routers."""
        routes = []
        routers = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for FastAPI route decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if (isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']):
                            
                            route_info = {
                                'function': node.name,
                                'method': decorator.func.attr.upper(),
                                'file': str(file_path),
                                'path': '',
                                'line': node.lineno
                            }
                            
                            # Extract path
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                route_info['path'] = decorator.args[0].value
                            
                            routes.append(route_info)
            
            # Look for APIRouter instances
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Call):
                            if (isinstance(node.value.func, ast.Name) and
                                node.value.func.id == 'APIRouter'):
                                
                                router_info = {
                                    'name': target.id,
                                    'file': str(file_path)
                                }
                                routers.append(router_info)
        
        return routes, routers
    
    def _extract_pydantic_models(self, tree: ast.AST, file_path: Path) -> List[Dict]:
        """Extract Pydantic models."""
        models = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseModel
                for base in node.bases:
                    if (isinstance(base, ast.Name) and base.id == 'BaseModel') or \
                       (isinstance(base, ast.Attribute) and base.attr == 'BaseModel'):
                        
                        model_info = {
                            'name': node.name,
                            'file': str(file_path),
                            'fields': [],
                            'line': node.lineno
                        }
                        
                        # Extract field annotations
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                model_info['fields'].append(item.target.id)
                        
                        models.append(model_info)
                        break
        
        return models
    
    def _detect_fastapi_auth(self, content: str) -> bool:
        """Detect FastAPI authentication patterns."""
        auth_patterns = [
            'HTTPBearer',
            'OAuth2PasswordBearer',
            'Depends(',
            'Security(',
            '@requires_auth',
            'get_current_user'
        ]
        
        return any(pattern in content for pattern in auth_patterns)
    
    def _extract_dependencies(self, tree: ast.AST) -> List[Dict]:
        """Extract FastAPI dependencies."""
        dependencies = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if isinstance(arg.annotation, ast.Call):
                        if (isinstance(arg.annotation.func, ast.Name) and
                            arg.annotation.func.id == 'Depends'):
                            
                            dep_info = {
                                'name': arg.arg,
                                'type': 'dependency'
                            }
                            dependencies.append(dep_info)
        
        return dependencies
    
    async def _create_project_structure(self):
        """Create Beginnings project structure."""
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        (output_path / "config").mkdir(exist_ok=True)
        (output_path / "routes").mkdir(exist_ok=True)
        (output_path / "models").mkdir(exist_ok=True)
        (output_path / "tests").mkdir(exist_ok=True)
    
    async def _convert_routes(self, routes: List[Dict]):
        """Convert FastAPI routes to Beginnings routes."""
        output_path = Path(self.output_dir) / "routes"
        
        # Generate routes file
        routes_content = '''"""API routes converted from FastAPI."""

from beginnings.routing.api import APIRouter

def register_api_routes(app):
    """Register API routes with the application."""
    
'''
        
        for route in routes:
            routes_content += f'''    @app.{route['method'].lower()}("{route['path']}")
    async def {route['function']}():
        """Converted from FastAPI route."""
        # TODO: Implement {route['function']} logic
        return {{"message": "Route converted from FastAPI"}}
    
'''
        
        (output_path / "api.py").write_text(routes_content)
        (output_path / "__init__.py").write_text('"""Route modules."""\n')
    
    async def _convert_models(self, models: List[Dict]):
        """Convert Pydantic models."""
        if not models:
            return
        
        output_path = Path(self.output_dir) / "models"
        
        models_content = '''"""Data models converted from Pydantic."""

from pydantic import BaseModel
from typing import Optional

'''
        
        for model in models:
            models_content += f'''class {model['name']}(BaseModel):
    """Converted from FastAPI Pydantic model."""
    # TODO: Add field definitions
    pass

'''
        
        (output_path / "models.py").write_text(models_content)
        (output_path / "__init__.py").write_text('"""Data models."""\n')
    
    async def _generate_main_app(self, analysis: Dict[str, Any]):
        """Generate main application file."""
        output_path = Path(self.output_dir) / "main.py"
        
        content = '''"""Main application file converted from FastAPI."""

from beginnings.core.app import BeginningsApp
from routes.api import register_api_routes

# Create application instance
app = BeginningsApp()

# Register routes
register_api_routes(app)

if __name__ == "__main__":
    app.run()
'''
        
        output_path.write_text(content)
    
    async def _generate_config(self, analysis: Dict[str, Any]):
        """Generate Beginnings configuration."""
        output_path = Path(self.output_dir) / "config" / "app.yaml"
        
        import yaml
        
        config = {
            'app': {
                'name': Path(self.source_dir).name,
                'debug': False,
                'host': '127.0.0.1',
                'port': 8000
            }
        }
        
        # Add auth if detected
        if analysis.get('auth_detected'):
            config['extensions'] = ['auth:jwt']
            config['auth'] = {
                'providers': {
                    'jwt': {
                        'secret_key': 'CHANGE_ME_IN_PRODUCTION',
                        'algorithm': 'HS256'
                    }
                }
            }
        
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
    
    def generate_report(self, result: Dict[str, Any], report_path: Path):
        """Generate detailed FastAPI migration report."""
        report_content = f'''# FastAPI to Beginnings Migration Report

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
| Routers | {result.get('routers_count', 0)} |
| Pydantic Models | {result.get('models_count', 0)} |
| Dependencies | {result.get('dependencies_count', 0)} |
| Authentication | {"✅ Detected" if result.get('auth_detected') else "❌ Not detected"} |

## Generated Files

```
{self.output_dir}/
├── main.py                 # Main application file
├── config/
│   └── app.yaml           # Beginnings configuration
├── routes/
│   └── api.py             # API route handlers
├── models/
│   └── models.py          # Data models (from Pydantic)
└── tests/                 # Test directory
```

## Manual Review Required

1. **Route Handlers:** Review generated route handlers in `routes/api.py`
2. **Data Models:** Update models in `models/models.py` 
3. **Dependencies:** Convert FastAPI dependencies to Beginnings middleware
4. **Authentication:** Configure Beginnings auth extension
5. **Validation:** Update Pydantic validation to Beginnings patterns

## FastAPI to Beginnings Mapping

- **FastAPI Routes** → **Beginnings API Routes**
- **Pydantic Models** → **Beginnings Data Models**
- **Dependencies** → **Beginnings Middleware**
- **Background Tasks** → **Beginnings Task System**
- **WebSockets** → **Beginnings WebSocket Support**

## Next Steps

1. Install dependencies: `pip install beginnings`
2. Review configuration: `beginnings config validate`
3. Test the application: `beginnings run`
4. Update authentication if needed
5. Migrate any custom middleware or dependencies

FastAPI and Beginnings share similar async patterns, making migration relatively straightforward.
'''
        
        report_path.write_text(report_content)