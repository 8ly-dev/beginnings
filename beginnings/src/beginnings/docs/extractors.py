"""Extractors for API routes, endpoints, and other documentation elements."""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Set, Union, Tuple
from pathlib import Path
from dataclasses import dataclass
import inspect
import importlib.util


@dataclass
class APIEndpoint:
    """Represents an API endpoint."""
    path: str
    method: str
    function_name: str
    summary: Optional[str]
    description: Optional[str]
    parameters: List[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    tags: List[str]
    deprecated: bool = False
    request_body: Optional[Dict[str, Any]] = None
    security: List[Dict[str, Any]] = None


@dataclass
class RouteInfo:
    """Represents a route definition."""
    path: str
    methods: List[str]
    function_name: str
    module: str
    line_number: int
    decorators: List[str]
    middleware: List[str] = None


@dataclass
class DataModel:
    """Represents a data model or schema."""
    name: str
    fields: Dict[str, Dict[str, Any]]
    description: Optional[str]
    example: Optional[Dict[str, Any]]
    required_fields: List[str]


class APIExtractor:
    """Extractor for API documentation from FastAPI/Flask applications."""
    
    def __init__(self):
        self.endpoints = {}
        self.models = {}
        self.middleware = {}
    
    async def extract_api_endpoints(self, source_path: Path) -> Dict[str, APIEndpoint]:
        """Extract API endpoints from source code.
        
        Args:
            source_path: Path to source directory
            
        Returns:
            Dictionary of API endpoints
        """
        endpoints = {}
        
        for py_file in source_path.rglob("*.py"):
            try:
                file_endpoints = await self._extract_endpoints_from_file(py_file)
                endpoints.update(file_endpoints)
            except Exception as e:
                continue
        
        return endpoints
    
    async def extract_models(self, source_path: Path) -> Dict[str, DataModel]:
        """Extract data models from source code.
        
        Args:
            source_path: Path to source directory
            
        Returns:
            Dictionary of data models
        """
        models = {}
        
        for py_file in source_path.rglob("*.py"):
            try:
                file_models = await self._extract_models_from_file(py_file)
                models.update(file_models)
            except Exception as e:
                continue
        
        return models
    
    async def extract_middleware(self, source_path: Path) -> Dict[str, Dict[str, Any]]:
        """Extract middleware information from source code.
        
        Args:
            source_path: Path to source directory
            
        Returns:
            Dictionary of middleware information
        """
        middleware = {}
        
        for py_file in source_path.rglob("*.py"):
            try:
                file_middleware = await self._extract_middleware_from_file(py_file)
                middleware.update(file_middleware)
            except Exception as e:
                continue
        
        return middleware
    
    async def _extract_endpoints_from_file(self, file_path: Path) -> Dict[str, APIEndpoint]:
        """Extract endpoints from a single file."""
        endpoints = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint = self._parse_endpoint_function(node, content, str(file_path))
                    if endpoint:
                        key = f"{endpoint.method}:{endpoint.path}"
                        endpoints[key] = endpoint
        
        except Exception as e:
            pass
        
        return endpoints
    
    def _parse_endpoint_function(self, node: ast.FunctionDef, content: str, file_path: str) -> Optional[APIEndpoint]:
        """Parse a function to extract endpoint information."""
        # Look for route decorators
        route_info = self._extract_route_from_decorators(node.decorator_list)
        if not route_info:
            return None
        
        path, methods = route_info
        
        # Extract docstring and parse it
        docstring = ast.get_docstring(node)
        doc_info = self._parse_endpoint_docstring(docstring) if docstring else {}
        
        # Extract parameters from function signature
        parameters = self._extract_function_parameters(node)
        
        # Create endpoint
        endpoint = APIEndpoint(
            path=path,
            method=methods[0] if methods else "GET",
            function_name=node.name,
            summary=doc_info.get("summary"),
            description=doc_info.get("description"),
            parameters=parameters,
            responses=doc_info.get("responses", {}),
            tags=doc_info.get("tags", []),
            deprecated=doc_info.get("deprecated", False),
            request_body=doc_info.get("request_body"),
            security=doc_info.get("security")
        )
        
        return endpoint
    
    def _extract_route_from_decorators(self, decorators: List[ast.expr]) -> Optional[Tuple[str, List[str]]]:
        """Extract route information from decorators."""
        for decorator in decorators:
            route_info = None
            
            # Handle @app.route() or @router.get() style decorators
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method_name = decorator.func.attr.lower()
                    if method_name in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                        route_info = self._extract_route_args(decorator, [method_name.upper()])
                    elif method_name == 'route':
                        route_info = self._extract_route_args(decorator)
                
                elif isinstance(decorator.func, ast.Name):
                    func_name = decorator.func.id.lower()
                    if func_name in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                        route_info = self._extract_route_args(decorator, [func_name.upper()])
            
            # Handle @app.get('/path') style decorators
            elif isinstance(decorator, ast.Attribute):
                method_name = decorator.attr.lower()
                if method_name in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    # This would need the next decorator to have the path
                    continue
            
            if route_info:
                return route_info
        
        return None
    
    def _extract_route_args(self, call_node: ast.Call, default_methods: List[str] = None) -> Optional[Tuple[str, List[str]]]:
        """Extract route path and methods from decorator call."""
        path = None
        methods = default_methods or ["GET"]
        
        # Extract positional arguments (usually the path)
        if call_node.args:
            try:
                path = ast.literal_eval(call_node.args[0])
            except (ValueError, TypeError):
                pass
        
        # Extract keyword arguments
        for keyword in call_node.keywords:
            if keyword.arg == "methods":
                try:
                    methods = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    pass
            elif keyword.arg == "path" and not path:
                try:
                    path = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    pass
        
        return (path, methods) if path else None
    
    def _parse_endpoint_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse endpoint docstring for API documentation."""
        doc_info = {
            "summary": None,
            "description": None,
            "parameters": [],
            "responses": {},
            "tags": [],
            "deprecated": False,
            "request_body": None,
            "security": None
        }
        
        if not docstring:
            return doc_info
        
        lines = docstring.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Check for section headers
            if line.lower().startswith(('args:', 'arguments:', 'parameters:')):
                current_section = 'parameters'
                continue
            elif line.lower().startswith(('returns:', 'return:', 'response:')):
                current_section = 'responses'
                continue
            elif line.lower().startswith('tags:'):
                current_section = 'tags'
                continue
            elif line.lower().startswith('deprecated'):
                doc_info["deprecated"] = True
                continue
            
            # Process content based on current section
            if current_section == 'parameters':
                param_match = re.match(r'(\w+)(?:\s*\(([^)]+)\))?\s*:\s*(.+)', line)
                if param_match:
                    param_name, param_type, param_desc = param_match.groups()
                    doc_info["parameters"].append({
                        "name": param_name,
                        "type": param_type or "string",
                        "description": param_desc,
                        "required": True  # Could be inferred differently
                    })
            
            elif current_section == 'responses':
                response_match = re.match(r'(\d+)\s*:\s*(.+)', line)
                if response_match:
                    status_code, description = response_match.groups()
                    doc_info["responses"][status_code] = {
                        "description": description,
                        "content": {}
                    }
            
            elif current_section == 'tags':
                # Extract tags from line
                tags = [tag.strip() for tag in line.split(',')]
                doc_info["tags"].extend(tags)
            
            elif not doc_info["summary"]:
                # First non-empty line is summary
                doc_info["summary"] = line
            
            elif not doc_info["description"]:
                # Second part is description
                doc_info["description"] = line
            else:
                # Append to description
                doc_info["description"] += " " + line
        
        return doc_info
    
    def _extract_function_parameters(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract parameters from function definition."""
        parameters = []
        
        for arg in node.args.args:
            # Skip 'self' parameter
            if arg.arg == 'self':
                continue
            
            param = {
                "name": arg.arg,
                "type": self._get_type_annotation(arg.annotation) if arg.annotation else "any",
                "required": True,
                "location": "query"  # Default location
            }
            
            # Determine parameter location based on name patterns
            if arg.arg in ['request', 'req']:
                param["location"] = "body"
            elif arg.arg.endswith('_id') or arg.arg in ['id', 'pk']:
                param["location"] = "path"
            
            parameters.append(param)
        
        return parameters
    
    def _get_type_annotation(self, annotation) -> str:
        """Get type annotation as string."""
        if annotation:
            try:
                return ast.unparse(annotation)
            except AttributeError:
                return str(annotation)
        return "any"
    
    async def _extract_models_from_file(self, file_path: Path) -> Dict[str, DataModel]:
        """Extract data models from a file."""
        models = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    model = self._parse_model_class(node, content)
                    if model:
                        models[model.name] = model
        
        except Exception as e:
            pass
        
        return models
    
    def _parse_model_class(self, node: ast.ClassDef, content: str) -> Optional[DataModel]:
        """Parse a class to extract model information."""
        # Check if this looks like a data model class
        is_model = False
        
        # Check for model indicators
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ['BaseModel', 'Model', 'Schema', 'SQLModel']:
                    is_model = True
                    break
            elif isinstance(base, ast.Attribute):
                if base.attr in ['BaseModel', 'Model', 'Schema']:
                    is_model = True
                    break
        
        # Check for dataclass decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == 'dataclass':
                is_model = True
                break
        
        if not is_model:
            return None
        
        # Extract fields
        fields = {}
        required_fields = []
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = self._get_type_annotation(item.annotation)
                
                field_info = {
                    "type": field_type,
                    "description": None,
                    "default": None,
                    "example": None
                }
                
                # Check for default value
                if item.value:
                    try:
                        field_info["default"] = ast.literal_eval(item.value)
                    except (ValueError, TypeError):
                        field_info["default"] = ast.unparse(item.value)
                else:
                    required_fields.append(field_name)
                
                fields[field_name] = field_info
        
        # Create model
        model = DataModel(
            name=node.name,
            fields=fields,
            description=ast.get_docstring(node),
            example=None,  # Could be extracted from docstring
            required_fields=required_fields
        )
        
        return model
    
    async def _extract_middleware_from_file(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Extract middleware information from a file."""
        middleware = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    middleware_info = self._parse_middleware_class(node, content)
                    if middleware_info:
                        middleware[node.name] = middleware_info
                
                elif isinstance(node, ast.FunctionDef):
                    middleware_info = self._parse_middleware_function(node, content)
                    if middleware_info:
                        middleware[node.name] = middleware_info
        
        except Exception as e:
            pass
        
        return middleware
    
    def _parse_middleware_class(self, node: ast.ClassDef, content: str) -> Optional[Dict[str, Any]]:
        """Parse a middleware class."""
        # Check if this looks like middleware
        is_middleware = False
        
        # Check for middleware indicators
        for base in node.bases:
            if isinstance(base, ast.Name):
                if 'middleware' in base.id.lower():
                    is_middleware = True
                    break
        
        # Check for middleware methods
        has_call_method = False
        has_dispatch_method = False
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == '__call__':
                    has_call_method = True
                elif item.name == 'dispatch':
                    has_dispatch_method = True
        
        if not (is_middleware or has_call_method or has_dispatch_method):
            return None
        
        return {
            "type": "class",
            "description": ast.get_docstring(node),
            "methods": [item.name for item in node.body if isinstance(item, ast.FunctionDef)],
            "line_number": node.lineno
        }
    
    def _parse_middleware_function(self, node: ast.FunctionDef, content: str) -> Optional[Dict[str, Any]]:
        """Parse a middleware function."""
        # Check if this looks like middleware
        if 'middleware' not in node.name.lower():
            return None
        
        # Check function signature for middleware patterns
        if len(node.args.args) < 2:  # Should have request and call_next or similar
            return None
        
        return {
            "type": "function",
            "description": ast.get_docstring(node),
            "parameters": [arg.arg for arg in node.args.args],
            "line_number": node.lineno
        }


class RouteExtractor:
    """Extractor for route definitions."""
    
    async def extract_routes(self, source_path: Path) -> Dict[str, RouteInfo]:
        """Extract route definitions from source code.
        
        Args:
            source_path: Path to source directory
            
        Returns:
            Dictionary of route information
        """
        routes = {}
        
        for py_file in source_path.rglob("*.py"):
            try:
                file_routes = await self._extract_routes_from_file(py_file)
                routes.update(file_routes)
            except Exception as e:
                continue
        
        return routes
    
    async def _extract_routes_from_file(self, file_path: Path) -> Dict[str, RouteInfo]:
        """Extract routes from a single file."""
        routes = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            module_name = file_path.stem
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    route_info = self._parse_route_function(node, module_name)
                    if route_info:
                        key = f"{route_info.path}:{':'.join(route_info.methods)}"
                        routes[key] = route_info
        
        except Exception as e:
            pass
        
        return routes
    
    def _parse_route_function(self, node: ast.FunctionDef, module_name: str) -> Optional[RouteInfo]:
        """Parse a function to extract route information."""
        # Extract decorators
        decorators = []
        route_path = None
        methods = []
        
        for decorator in node.decorator_list:
            decorator_info = self._parse_route_decorator(decorator)
            if decorator_info:
                path, route_methods = decorator_info
                if path:
                    route_path = path
                    methods = route_methods or ["GET"]
                    break
            
            # Store decorator name for reference
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(decorator.attr)
        
        if not route_path:
            return None
        
        return RouteInfo(
            path=route_path,
            methods=methods,
            function_name=node.name,
            module=module_name,
            line_number=node.lineno,
            decorators=decorators
        )
    
    def _parse_route_decorator(self, decorator) -> Optional[Tuple[str, List[str]]]:
        """Parse a route decorator to extract path and methods."""
        if isinstance(decorator, ast.Call):
            # Handle @app.route('/path', methods=['GET', 'POST'])
            if isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in ['route', 'get', 'post', 'put', 'delete', 'patch']:
                    return self._extract_route_args(decorator)
            elif isinstance(decorator.func, ast.Name):
                if decorator.func.id in ['route', 'get', 'post', 'put', 'delete', 'patch']:
                    return self._extract_route_args(decorator)
        
        return None
    
    def _extract_route_args(self, call_node: ast.Call) -> Optional[Tuple[str, List[str]]]:
        """Extract route arguments from decorator call."""
        path = None
        methods = []
        
        # Extract positional arguments
        if call_node.args:
            try:
                path = ast.literal_eval(call_node.args[0])
            except (ValueError, TypeError):
                pass
        
        # Extract keyword arguments
        for keyword in call_node.keywords:
            if keyword.arg == "methods":
                try:
                    methods = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    pass
        
        # Infer method from decorator name if not specified
        if isinstance(call_node.func, ast.Attribute):
            method_name = call_node.func.attr.upper()
            if method_name in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
                methods = [method_name]
        
        return (path, methods) if path else None


class ExtensionExtractor:
    """Extractor for extension documentation."""
    
    async def extract_extensions(self, extension_path: Path) -> Dict[str, Dict[str, Any]]:
        """Extract extension documentation.
        
        Args:
            extension_path: Path to extensions directory
            
        Returns:
            Dictionary of extension documentation
        """
        extensions = {}
        
        for ext_dir in extension_path.iterdir():
            if ext_dir.is_dir() and not ext_dir.name.startswith('.'):
                try:
                    extension_doc = await self._extract_extension_info(ext_dir)
                    if extension_doc:
                        extensions[ext_dir.name] = extension_doc
                except Exception as e:
                    continue
        
        return extensions
    
    async def _extract_extension_info(self, extension_path: Path) -> Optional[Dict[str, Any]]:
        """Extract information from a single extension."""
        extension_info = {
            "name": extension_path.name,
            "path": str(extension_path),
            "description": None,
            "version": None,
            "author": None,
            "dependencies": [],
            "api_endpoints": {},
            "configuration": {},
            "hooks": [],
            "examples": []
        }
        
        # Look for extension entry point
        init_file = extension_path / "__init__.py"
        if init_file.exists():
            init_info = await self._parse_extension_init(init_file)
            extension_info.update(init_info)
        
        # Extract API endpoints if any
        api_extractor = APIExtractor()
        endpoints = await api_extractor.extract_api_endpoints(extension_path)
        extension_info["api_endpoints"] = endpoints
        
        # Look for configuration schema
        config_files = [
            extension_path / "config.json",
            extension_path / "config.yaml",
            extension_path / "schema.json"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                config_info = await self._parse_extension_config(config_file)
                if config_info:
                    extension_info["configuration"] = config_info
                    break
        
        return extension_info
    
    async def _parse_extension_init(self, init_file: Path) -> Dict[str, Any]:
        """Parse extension __init__.py for metadata."""
        info = {}
        
        try:
            content = init_file.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(init_file))
            
            # Extract module docstring
            module_docstring = ast.get_docstring(tree)
            if module_docstring:
                info["description"] = module_docstring
            
            # Extract metadata variables
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            try:
                                value = ast.literal_eval(node.value)
                                if var_name == "__version__":
                                    info["version"] = value
                                elif var_name == "__author__":
                                    info["author"] = value
                                elif var_name == "__description__":
                                    info["description"] = value
                                elif var_name == "__dependencies__":
                                    info["dependencies"] = value
                            except (ValueError, TypeError):
                                pass
        
        except Exception as e:
            pass
        
        return info
    
    async def _parse_extension_config(self, config_file: Path) -> Optional[Dict[str, Any]]:
        """Parse extension configuration file."""
        try:
            if config_file.suffix == '.json':
                content = config_file.read_text(encoding='utf-8')
                return json.loads(content)
            elif config_file.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    content = config_file.read_text(encoding='utf-8')
                    return yaml.safe_load(content)
                except ImportError:
                    pass
        
        except Exception as e:
            pass
        
        return None