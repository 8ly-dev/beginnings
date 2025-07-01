"""Code and configuration parsers for documentation extraction."""

from __future__ import annotations

import ast
import json
from typing import Any, Dict, List, Optional, Union, Set
from pathlib import Path
import inspect
import importlib.util
from dataclasses import dataclass
import re

try:
    import yaml
except ImportError:
    yaml = None

try:
    import toml
except ImportError:
    toml = None


@dataclass
class ParsedFunction:
    """Represents a parsed function or method."""
    name: str
    docstring: Optional[str]
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    decorators: List[str]
    is_async: bool
    line_number: int
    source_code: Optional[str] = None


@dataclass
class ParsedClass:
    """Represents a parsed class."""
    name: str
    docstring: Optional[str]
    methods: Dict[str, ParsedFunction]
    properties: Dict[str, Dict[str, Any]]
    base_classes: List[str]
    decorators: List[str]
    line_number: int
    is_abstract: bool = False


@dataclass
class ParsedModule:
    """Represents a parsed module."""
    name: str
    docstring: Optional[str]
    file_path: str
    functions: Dict[str, ParsedFunction]
    classes: Dict[str, ParsedClass]
    constants: Dict[str, Any]
    imports: List[str]
    exports: List[str]


class CodeParser:
    """Parser for Python code files."""
    
    def __init__(self):
        self.parsed_modules = {}
    
    async def parse_modules(
        self, 
        source_path: Path, 
        include_private: bool = False,
        include_tests: bool = False
    ) -> Dict[str, ParsedModule]:
        """Parse all Python modules in a directory.
        
        Args:
            source_path: Path to source directory
            include_private: Whether to include private members
            include_tests: Whether to include test files
            
        Returns:
            Dictionary of parsed modules
        """
        modules = {}
        
        for py_file in source_path.rglob("*.py"):
            # Skip test files if not included
            if not include_tests and ("test_" in py_file.name or py_file.name.endswith("_test.py")):
                continue
            
            # Skip __pycache__ and other special directories
            if "__pycache__" in str(py_file):
                continue
            
            try:
                module = await self.parse_module(py_file, include_private)
                if module:
                    # Use relative path as module name
                    relative_path = py_file.relative_to(source_path)
                    module_name = str(relative_path.with_suffix("")).replace("/", ".")
                    module.name = module_name
                    modules[module_name] = module
            except Exception as e:
                # Skip files that can't be parsed
                continue
        
        return modules
    
    async def parse_module(self, file_path: Path, include_private: bool = False) -> Optional[ParsedModule]:
        """Parse a single Python module.
        
        Args:
            file_path: Path to Python file
            include_private: Whether to include private members
            
        Returns:
            Parsed module or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            module = ParsedModule(
                name=file_path.stem,
                docstring=ast.get_docstring(tree),
                file_path=str(file_path),
                functions={},
                classes={},
                constants={},
                imports=[],
                exports=[]
            )
            
            # Parse module contents
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if include_private or not node.name.startswith('_'):
                        func = self._parse_function(node, content)
                        module.functions[func.name] = func
                
                elif isinstance(node, ast.AsyncFunctionDef):
                    if include_private or not node.name.startswith('_'):
                        func = self._parse_function(node, content, is_async=True)
                        module.functions[func.name] = func
                
                elif isinstance(node, ast.ClassDef):
                    if include_private or not node.name.startswith('_'):
                        cls = self._parse_class(node, content, include_private)
                        module.classes[cls.name] = cls
                
                elif isinstance(node, ast.Assign):
                    # Parse module-level constants
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            try:
                                value = ast.literal_eval(node.value)
                                module.constants[target.id] = value
                            except (ValueError, TypeError):
                                pass
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        module.imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            module.imports.append(f"{node.module}.{alias.name}")
            
            # Extract __all__ exports if present
            module.exports = self._extract_exports(tree)
            
            return module
            
        except Exception as e:
            return None
    
    async def parse_example_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse an example file for documentation.
        
        Args:
            file_path: Path to example file
            
        Returns:
            Example documentation data
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            example_data = {
                "title": file_path.stem.replace('_', ' ').title(),
                "description": ast.get_docstring(tree),
                "file_path": str(file_path),
                "code": content,
                "functions": [],
                "classes": [],
                "main_example": None
            }
            
            # Look for main example function
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name == "main" or node.name.startswith("example"):
                        func = self._parse_function(node, content)
                        example_data["functions"].append(func)
                        if node.name == "main":
                            example_data["main_example"] = func
                
                elif isinstance(node, ast.ClassDef):
                    cls = self._parse_class(node, content, include_private=False)
                    example_data["classes"].append(cls)
            
            return example_data
            
        except Exception as e:
            return None
    
    def _parse_function(self, node: ast.FunctionDef, source_code: str, is_async: bool = False) -> ParsedFunction:
        """Parse a function or method node."""
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param = {
                "name": arg.arg,
                "type": self._get_type_annotation(arg.annotation) if arg.annotation else None,
                "default": None
            }
            parameters.append(param)
        
        # Add defaults
        defaults = node.args.defaults
        if defaults:
            # Defaults are for the last len(defaults) parameters
            for i, default in enumerate(defaults):
                param_index = len(parameters) - len(defaults) + i
                if param_index < len(parameters):
                    try:
                        parameters[param_index]["default"] = ast.literal_eval(default)
                    except (ValueError, TypeError):
                        parameters[param_index]["default"] = ast.unparse(default)
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                decorators.append(decorator.func.id)
            else:
                decorators.append(ast.unparse(decorator))
        
        # Extract source code if needed
        source_lines = source_code.split('\n')
        func_source = None
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            try:
                func_source = '\n'.join(source_lines[node.lineno-1:node.end_lineno])
            except (IndexError, AttributeError):
                pass
        
        return ParsedFunction(
            name=node.name,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=self._get_type_annotation(node.returns) if node.returns else None,
            decorators=decorators,
            is_async=is_async or isinstance(node, ast.AsyncFunctionDef),
            line_number=node.lineno,
            source_code=func_source
        )
    
    def _parse_class(self, node: ast.ClassDef, source_code: str, include_private: bool = False) -> ParsedClass:
        """Parse a class node."""
        methods = {}
        properties = {}
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if include_private or not item.name.startswith('_'):
                    method = self._parse_function(item, source_code, isinstance(item, ast.AsyncFunctionDef))
                    methods[method.name] = method
            
            elif isinstance(item, ast.Assign):
                # Look for class attributes/properties
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        try:
                            value = ast.literal_eval(item.value)
                            properties[target.id] = {
                                "value": value,
                                "type": type(value).__name__,
                                "line_number": item.lineno
                            }
                        except (ValueError, TypeError):
                            properties[target.id] = {
                                "value": ast.unparse(item.value),
                                "type": "expression",
                                "line_number": item.lineno
                            }
        
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            else:
                base_classes.append(ast.unparse(base))
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            else:
                decorators.append(ast.unparse(decorator))
        
        # Check if class is abstract
        is_abstract = any(
            isinstance(item, ast.FunctionDef) and 
            any(isinstance(dec, ast.Name) and dec.id == "abstractmethod" for dec in item.decorator_list)
            for item in node.body
        )
        
        return ParsedClass(
            name=node.name,
            docstring=ast.get_docstring(node),
            methods=methods,
            properties=properties,
            base_classes=base_classes,
            decorators=decorators,
            line_number=node.lineno,
            is_abstract=is_abstract
        )
    
    def _get_type_annotation(self, annotation) -> Optional[str]:
        """Extract type annotation as string."""
        if annotation:
            try:
                return ast.unparse(annotation)
            except AttributeError:
                # Fallback for older Python versions
                return str(annotation)
        return None
    
    def _extract_exports(self, tree: ast.AST) -> List[str]:
        """Extract __all__ exports from module."""
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and 
                len(node.targets) == 1 and 
                isinstance(node.targets[0], ast.Name) and 
                node.targets[0].id == "__all__"):
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
        return []


class ConfigParser:
    """Parser for configuration files."""
    
    async def parse_config_files(self, config_path: Path) -> Dict[str, Any]:
        """Parse configuration files in a directory.
        
        Args:
            config_path: Path to configuration directory
            
        Returns:
            Dictionary of parsed configurations
        """
        configs = {}
        
        # Parse different config file formats
        for config_file in config_path.rglob("*"):
            if config_file.is_file():
                config_data = await self.parse_config_file(config_file)
                if config_data:
                    configs[str(config_file.relative_to(config_path))] = config_data
        
        return configs
    
    async def parse_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single configuration file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Parsed configuration data
        """
        try:
            suffix = file_path.suffix.lower()
            content = file_path.read_text(encoding='utf-8')
            
            config_data = {
                "file_path": str(file_path),
                "format": suffix[1:] if suffix else "unknown",
                "schema": {},
                "documentation": {},
                "examples": {}
            }
            
            if suffix == '.json':
                data = json.loads(content)
                config_data["schema"] = self._analyze_json_schema(data)
                config_data["documentation"] = self._extract_json_documentation(content)
            
            elif suffix in ['.yml', '.yaml'] and yaml:
                data = yaml.safe_load(content)
                config_data["schema"] = self._analyze_yaml_schema(data, content)
                config_data["documentation"] = self._extract_yaml_documentation(content)
            
            elif suffix == '.toml' and toml:
                data = toml.loads(content)
                config_data["schema"] = self._analyze_toml_schema(data)
                config_data["documentation"] = self._extract_toml_documentation(content)
            
            elif suffix in ['.ini', '.cfg']:
                data = self._parse_ini_file(content)
                config_data["schema"] = self._analyze_ini_schema(data)
                config_data["documentation"] = self._extract_ini_documentation(content)
            
            elif suffix == '.py':
                # Parse Python configuration files
                config_data = await self._parse_python_config(file_path)
            
            else:
                return None
            
            return config_data
            
        except Exception as e:
            return None
    
    def _analyze_json_schema(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze JSON data to create schema information."""
        if isinstance(data, dict):
            schema = {
                "type": "object",
                "properties": {},
                "path": path
            }
            for key, value in data.items():
                schema["properties"][key] = self._analyze_json_schema(value, f"{path}.{key}" if path else key)
            return schema
        
        elif isinstance(data, list):
            schema = {
                "type": "array",
                "path": path
            }
            if data:
                schema["items"] = self._analyze_json_schema(data[0], f"{path}[0]")
            return schema
        
        else:
            return {
                "type": type(data).__name__,
                "value": data,
                "path": path
            }
    
    def _extract_json_documentation(self, content: str) -> Dict[str, str]:
        """Extract documentation from JSON comments (if any)."""
        # JSON doesn't support comments natively, but some parsers allow them
        documentation = {}
        
        # Look for comment patterns
        lines = content.split('\n')
        current_key = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('//') or line.startswith('#'):
                # Comment line
                comment = line.lstrip('/# ')
                if current_key:
                    documentation[current_key] = comment
            elif ':' in line and not line.startswith('{'):
                # Potential key line
                key_match = re.match(r'"([^"]+)":', line)
                if key_match:
                    current_key = key_match.group(1)
        
        return documentation
    
    def _analyze_yaml_schema(self, data: Any, content: str, path: str = "") -> Dict[str, Any]:
        """Analyze YAML data to create schema information."""
        return self._analyze_json_schema(data, path)  # Same logic for now
    
    def _extract_yaml_documentation(self, content: str) -> Dict[str, str]:
        """Extract documentation from YAML comments."""
        documentation = {}
        lines = content.split('\n')
        current_key = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                # Comment line
                comment = stripped.lstrip('# ')
                if current_key:
                    documentation[current_key] = comment
            elif ':' in stripped and not stripped.startswith('#'):
                # Potential key line
                key_match = re.match(r'([^:]+):', stripped)
                if key_match:
                    current_key = key_match.group(1).strip()
        
        return documentation
    
    def _analyze_toml_schema(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze TOML data to create schema information."""
        return self._analyze_json_schema(data, path)  # Same logic for now
    
    def _extract_toml_documentation(self, content: str) -> Dict[str, str]:
        """Extract documentation from TOML comments."""
        documentation = {}
        lines = content.split('\n')
        current_key = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                # Comment line
                comment = stripped.lstrip('# ')
                if current_key:
                    documentation[current_key] = comment
            elif '=' in stripped and not stripped.startswith('#'):
                # Potential key line
                key_match = re.match(r'([^=]+)=', stripped)
                if key_match:
                    current_key = key_match.group(1).strip()
        
        return documentation
    
    def _parse_ini_file(self, content: str) -> Dict[str, Any]:
        """Parse INI file content."""
        config = {}
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                config[current_section] = {}
            elif '=' in line and current_section:
                key, value = line.split('=', 1)
                config[current_section][key.strip()] = value.strip()
        
        return config
    
    def _analyze_ini_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze INI data to create schema information."""
        return self._analyze_json_schema(data)
    
    def _extract_ini_documentation(self, content: str) -> Dict[str, str]:
        """Extract documentation from INI comments."""
        documentation = {}
        lines = content.split('\n')
        current_key = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith(';'):
                # Comment line
                comment = stripped.lstrip('#; ')
                if current_key:
                    documentation[current_key] = comment
            elif '=' in stripped and not (stripped.startswith('#') or stripped.startswith(';')):
                # Potential key line
                key_match = re.match(r'([^=]+)=', stripped)
                if key_match:
                    current_key = key_match.group(1).strip()
        
        return documentation
    
    async def _parse_python_config(self, file_path: Path) -> Dict[str, Any]:
        """Parse Python configuration file."""
        try:
            spec = importlib.util.spec_from_file_location("config", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                config_data = {
                    "file_path": str(file_path),
                    "format": "python",
                    "schema": {},
                    "documentation": {},
                    "variables": {}
                }
                
                # Extract configuration variables
                for name in dir(module):
                    if not name.startswith('_'):
                        value = getattr(module, name)
                        if not callable(value) and not inspect.ismodule(value):
                            config_data["variables"][name] = {
                                "value": value,
                                "type": type(value).__name__
                            }
                
                return config_data
        
        except Exception as e:
            pass
        
        return None


class ExtensionParser:
    """Parser for extension files and metadata."""
    
    async def parse_extensions(self, extension_path: Path) -> Dict[str, Any]:
        """Parse extensions in a directory.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Dictionary of parsed extensions
        """
        extensions = {}
        
        for ext_dir in extension_path.iterdir():
            if ext_dir.is_dir() and not ext_dir.name.startswith('.'):
                extension_data = await self.parse_extension(ext_dir)
                if extension_data:
                    extensions[ext_dir.name] = extension_data
        
        return extensions
    
    async def parse_extension(self, extension_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single extension.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Extension documentation data
        """
        try:
            extension_data = {
                "name": extension_path.name,
                "path": str(extension_path),
                "metadata": {},
                "code_documentation": {},
                "configuration": {},
                "examples": {},
                "tests": {}
            }
            
            # Look for extension metadata files
            metadata_files = [
                extension_path / "extension.json",
                extension_path / "extension.yaml",
                extension_path / "extension.yml",
                extension_path / "metadata.json",
                extension_path / "setup.py",
                extension_path / "__init__.py"
            ]
            
            for metadata_file in metadata_files:
                if metadata_file.exists():
                    metadata = await self._parse_extension_metadata(metadata_file)
                    if metadata:
                        extension_data["metadata"].update(metadata)
                        break
            
            # Parse extension code
            code_parser = CodeParser()
            code_docs = await code_parser.parse_modules(extension_path, include_private=False)
            extension_data["code_documentation"] = code_docs
            
            # Look for configuration files
            config_parser = ConfigParser()
            config_files = await config_parser.parse_config_files(extension_path)
            extension_data["configuration"] = config_files
            
            # Look for examples
            examples_dir = extension_path / "examples"
            if examples_dir.exists():
                for example_file in examples_dir.glob("*.py"):
                    example_data = await code_parser.parse_example_file(example_file)
                    if example_data:
                        extension_data["examples"][example_file.name] = example_data
            
            # Look for tests
            tests_dir = extension_path / "tests"
            if tests_dir.exists():
                test_docs = await code_parser.parse_modules(tests_dir, include_tests=True)
                extension_data["tests"] = test_docs
            
            return extension_data
            
        except Exception as e:
            return None
    
    async def _parse_extension_metadata(self, metadata_file: Path) -> Optional[Dict[str, Any]]:
        """Parse extension metadata file."""
        try:
            if metadata_file.suffix == '.json':
                content = metadata_file.read_text(encoding='utf-8')
                return json.loads(content)
            
            elif metadata_file.suffix in ['.yaml', '.yml'] and yaml:
                content = metadata_file.read_text(encoding='utf-8')
                return yaml.safe_load(content)
            
            elif metadata_file.name == '__init__.py':
                # Extract metadata from __init__.py
                content = metadata_file.read_text(encoding='utf-8')
                metadata = {}
                
                # Look for common metadata variables
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('__version__'):
                        version_match = re.search(r'["\']([^"\']+)["\']', line)
                        if version_match:
                            metadata['version'] = version_match.group(1)
                    elif line.startswith('__author__'):
                        author_match = re.search(r'["\']([^"\']+)["\']', line)
                        if author_match:
                            metadata['author'] = author_match.group(1)
                    elif line.startswith('__description__'):
                        desc_match = re.search(r'["\']([^"\']+)["\']', line)
                        if desc_match:
                            metadata['description'] = desc_match.group(1)
                
                return metadata if metadata else None
            
            elif metadata_file.name == 'setup.py':
                # Extract basic info from setup.py
                content = metadata_file.read_text(encoding='utf-8')
                metadata = {}
                
                # Simple regex extraction (could be improved)
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if name_match:
                    metadata['name'] = name_match.group(1)
                
                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    metadata['version'] = version_match.group(1)
                
                desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                if desc_match:
                    metadata['description'] = desc_match.group(1)
                
                return metadata if metadata else None
        
        except Exception as e:
            pass
        
        return None