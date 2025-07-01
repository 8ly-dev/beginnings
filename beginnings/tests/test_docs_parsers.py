"""Unit tests for documentation parsers."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from beginnings.docs.parsers import (
    CodeParser, 
    ConfigParser, 
    ExtensionParser,
    ParsedFunction,
    ParsedClass,
    ParsedModule
)


class TestParsedFunction:
    """Test ParsedFunction dataclass."""
    
    def test_parsed_function_creation(self):
        """Test ParsedFunction creation."""
        func = ParsedFunction(
            name="test_function",
            docstring="Test function docstring",
            parameters=[{"name": "param1", "type": "str", "default": None}],
            return_type="bool",
            decorators=["decorator1"],
            is_async=False,
            line_number=10,
            source_code="def test_function(param1: str) -> bool: pass"
        )
        
        assert func.name == "test_function"
        assert func.docstring == "Test function docstring"
        assert len(func.parameters) == 1
        assert func.parameters[0]["name"] == "param1"
        assert func.return_type == "bool"
        assert func.decorators == ["decorator1"]
        assert func.is_async is False
        assert func.line_number == 10
        assert func.source_code is not None


class TestParsedClass:
    """Test ParsedClass dataclass."""
    
    def test_parsed_class_creation(self):
        """Test ParsedClass creation."""
        method = ParsedFunction(
            name="method1",
            docstring="Method docstring",
            parameters=[],
            return_type=None,
            decorators=[],
            is_async=False,
            line_number=15
        )
        
        cls = ParsedClass(
            name="TestClass",
            docstring="Class docstring",
            methods={"method1": method},
            properties={"prop1": {"value": "default", "type": "str", "line_number": 20}},
            base_classes=["BaseClass"],
            decorators=["dataclass"],
            line_number=10,
            is_abstract=False
        )
        
        assert cls.name == "TestClass"
        assert cls.docstring == "Class docstring"
        assert "method1" in cls.methods
        assert cls.methods["method1"] == method
        assert "prop1" in cls.properties
        assert cls.base_classes == ["BaseClass"]
        assert cls.decorators == ["dataclass"]
        assert cls.line_number == 10
        assert cls.is_abstract is False


class TestParsedModule:
    """Test ParsedModule dataclass."""
    
    def test_parsed_module_creation(self):
        """Test ParsedModule creation."""
        func = ParsedFunction(
            name="func1",
            docstring="Function docstring",
            parameters=[],
            return_type=None,
            decorators=[],
            is_async=False,
            line_number=5
        )
        
        cls = ParsedClass(
            name="Class1",
            docstring="Class docstring",
            methods={},
            properties={},
            base_classes=[],
            decorators=[],
            line_number=10
        )
        
        module = ParsedModule(
            name="test_module",
            docstring="Module docstring",
            file_path="/path/to/module.py",
            functions={"func1": func},
            classes={"Class1": cls},
            constants={"CONSTANT1": "value"},
            imports=["import os", "from typing import Dict"],
            exports=["func1", "Class1"]
        )
        
        assert module.name == "test_module"
        assert module.docstring == "Module docstring"
        assert module.file_path == "/path/to/module.py"
        assert "func1" in module.functions
        assert "Class1" in module.classes
        assert module.constants["CONSTANT1"] == "value"
        assert len(module.imports) == 2
        assert len(module.exports) == 2


class TestCodeParser:
    """Test CodeParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create CodeParser instance."""
        return CodeParser()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_python_file(self, temp_dir):
        """Create sample Python file for testing."""
        python_file = temp_dir / "sample.py"
        python_file.write_text('''
"""Sample module for testing."""

import os
from typing import Dict, List

CONSTANT_VALUE = "test"

class SampleClass:
    """Sample class with methods."""
    
    def __init__(self, name: str):
        """Initialize sample class."""
        self.name = name
    
    def process_data(self, data: Dict[str, str]) -> List[str]:
        """Process input data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            List of processed strings
        """
        return list(data.values())

def utility_function(value: int) -> str:
    """Convert integer to string.
    
    Args:
        value: Integer value
        
    Returns:
        String representation
    """
    return str(value)

async def async_function() -> None:
    """Async function example."""
    pass

__all__ = ["SampleClass", "utility_function"]
''')
        return python_file
    
    @pytest.mark.asyncio
    async def test_parse_module(self, parser, sample_python_file):
        """Test parsing a single module."""
        # Parse with private methods included to see __init__
        module = await parser.parse_module(sample_python_file, include_private=True)
        
        assert module is not None
        assert module.name == "sample"
        assert module.docstring == "Sample module for testing."
        assert str(sample_python_file) in module.file_path
        
        # Check functions
        assert "utility_function" in module.functions
        assert "async_function" in module.functions
        
        utility_func = module.functions["utility_function"]
        assert utility_func.name == "utility_function"
        assert utility_func.docstring is not None
        assert utility_func.return_type == "str"
        assert len(utility_func.parameters) == 1
        assert utility_func.parameters[0]["name"] == "value"
        assert utility_func.is_async is False
        
        async_func = module.functions["async_function"]
        assert async_func.is_async is True
        
        # Check classes
        assert "SampleClass" in module.classes
        sample_class = module.classes["SampleClass"]
        assert sample_class.name == "SampleClass"
        assert sample_class.docstring == "Sample class with methods."
        assert "__init__" in sample_class.methods
        assert "process_data" in sample_class.methods
        
        # Check constants
        assert "CONSTANT_VALUE" in module.constants
        assert module.constants["CONSTANT_VALUE"] == "test"
        
        # Check imports
        assert len(module.imports) > 0
        assert any("os" in imp for imp in module.imports)
        
        # Check exports
        assert "SampleClass" in module.exports
        assert "utility_function" in module.exports
    
    @pytest.mark.asyncio
    async def test_parse_modules_directory(self, parser, temp_dir):
        """Test parsing multiple modules in a directory."""
        # Create multiple Python files
        (temp_dir / "module1.py").write_text('"""Module 1."""\n\ndef func1(): pass')
        (temp_dir / "module2.py").write_text('"""Module 2."""\n\nclass Class2: pass')
        (temp_dir / "test_module.py").write_text('"""Test module."""\n\ndef test_func(): pass')
        
        # Parse all modules (excluding tests by default)
        modules = await parser.parse_modules(temp_dir)
        
        assert len(modules) == 2  # test_module.py should be excluded
        assert "module1" in modules
        assert "module2" in modules
        
        # Parse including tests
        modules_with_tests = await parser.parse_modules(temp_dir, include_tests=True)
        assert len(modules_with_tests) == 3
        assert "test_module" in modules_with_tests
    
    @pytest.mark.asyncio
    async def test_parse_example_file(self, parser, temp_dir):
        """Test parsing example file."""
        example_file = temp_dir / "example.py"
        example_file.write_text('''
"""Example script demonstrating functionality."""

def example_function():
    """Example function."""
    print("Hello, world!")

def main():
    """Main example function."""
    example_function()

if __name__ == "__main__":
    main()
''')
        
        example_data = await parser.parse_example_file(example_file)
        
        assert example_data is not None
        assert example_data["title"] == "Example"
        assert example_data["description"] == "Example script demonstrating functionality."
        assert len(example_data["functions"]) == 2
        assert example_data["main_example"] is not None
        assert example_data["main_example"].name == "main"


class TestConfigParser:
    """Test ConfigParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create ConfigParser instance."""
        return ConfigParser()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_parse_json_config(self, parser, temp_dir):
        """Test parsing JSON configuration file."""
        json_file = temp_dir / "config.json"
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "testdb"
            },
            "debug": True,
            "features": ["feature1", "feature2"]
        }
        json_file.write_text(json.dumps(config_data, indent=2))
        
        result = await parser.parse_config_file(json_file)
        
        assert result is not None
        assert result["format"] == "json"
        assert result["file_path"] == str(json_file)
        assert "schema" in result
        
        schema = result["schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "database" in schema["properties"]
        assert schema["properties"]["database"]["type"] == "object"
    
    @pytest.mark.asyncio
    async def test_parse_yaml_config(self, parser, temp_dir):
        """Test parsing YAML configuration file."""
        yaml_file = temp_dir / "config.yaml"
        yaml_content = """
# Database configuration
database:
  host: localhost  # Database host
  port: 5432      # Database port
  name: testdb    # Database name

# Debug mode
debug: true

# Feature flags
features:
  - feature1
  - feature2
"""
        yaml_file.write_text(yaml_content)
        
        with patch('beginnings.docs.parsers.yaml') as mock_yaml:
            mock_yaml.safe_load.return_value = {
                "database": {"host": "localhost", "port": 5432, "name": "testdb"},
                "debug": True,
                "features": ["feature1", "feature2"]
            }
            
            result = await parser.parse_config_file(yaml_file)
        
        if result:  # Only test if YAML parsing is available
            assert result["format"] == "yaml"
            assert "schema" in result
            assert "documentation" in result
    
    @pytest.mark.asyncio
    async def test_parse_ini_config(self, parser, temp_dir):
        """Test parsing INI configuration file."""
        ini_file = temp_dir / "config.ini"
        ini_content = """
[database]
host = localhost
port = 5432
name = testdb

[logging]
level = INFO
file = app.log
"""
        ini_file.write_text(ini_content)
        
        result = await parser.parse_config_file(ini_file)
        
        assert result is not None
        assert result["format"] == "ini"
        assert "schema" in result
        
        schema = result["schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "database" in schema["properties"]
    
    @pytest.mark.asyncio
    async def test_parse_python_config(self, parser, temp_dir):
        """Test parsing Python configuration file."""
        py_file = temp_dir / "config.py"
        py_content = """
# Configuration settings
DATABASE_HOST = "localhost"
DATABASE_PORT = 5432
DEBUG = True
FEATURES = ["feature1", "feature2"]
"""
        py_file.write_text(py_content)
        
        result = await parser.parse_config_file(py_file)
        
        assert result is not None
        assert result["format"] == "python"
        assert "variables" in result
        
        variables = result["variables"]
        assert "DATABASE_HOST" in variables
        assert variables["DATABASE_HOST"]["value"] == "localhost"
        assert variables["DATABASE_PORT"]["value"] == 5432
    
    @pytest.mark.asyncio
    async def test_parse_config_files_directory(self, parser, temp_dir):
        """Test parsing all config files in directory."""
        # Create multiple config files
        (temp_dir / "app.json").write_text('{"app": {"name": "test"}}')
        (temp_dir / "database.ini").write_text('[db]\nhost=localhost')
        (temp_dir / "settings.py").write_text('SETTING = "value"')
        
        configs = await parser.parse_config_files(temp_dir)
        
        assert len(configs) >= 3
        assert any("app.json" in path for path in configs.keys())
        assert any("database.ini" in path for path in configs.keys())
        assert any("settings.py" in path for path in configs.keys())


class TestExtensionParser:
    """Test ExtensionParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create ExtensionParser instance."""
        return ExtensionParser()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_extension(self, temp_dir):
        """Create sample extension directory."""
        ext_dir = temp_dir / "sample_extension"
        ext_dir.mkdir()
        
        # Create __init__.py with metadata
        init_file = ext_dir / "__init__.py"
        init_file.write_text('''
"""Sample extension for testing."""

__version__ = "1.0.0"
__author__ = "Test Author"
__description__ = "Sample extension"

class SampleExtension:
    """Main extension class."""
    
    def initialize(self):
        """Initialize the extension."""
        pass
''')
        
        # Create extension metadata file
        metadata_file = ext_dir / "extension.json"
        metadata = {
            "name": "sample_extension",
            "version": "1.0.0",
            "description": "Sample extension for testing",
            "author": "Test Author",
            "dependencies": ["requests"],
            "entry_point": "SampleExtension"
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Create example file
        examples_dir = ext_dir / "examples"
        examples_dir.mkdir()
        example_file = examples_dir / "basic_usage.py"
        example_file.write_text('''
"""Basic usage example."""

from sample_extension import SampleExtension

def example():
    """Example usage of the extension."""
    ext = SampleExtension()
    ext.initialize()
''')
        
        return ext_dir
    
    @pytest.mark.asyncio
    async def test_parse_extension(self, parser, sample_extension):
        """Test parsing a single extension."""
        result = await parser.parse_extension(sample_extension)
        
        assert result is not None
        assert result["name"] == "sample_extension"
        assert result["path"] == str(sample_extension)
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["version"] == "1.0.0"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "Sample extension for testing"
        
        # Check code documentation
        code_docs = result["code_documentation"]
        assert len(code_docs) > 0
        
        # Check examples
        examples = result["examples"]
        assert len(examples) > 0
        assert "basic_usage.py" in examples
    
    @pytest.mark.asyncio
    async def test_parse_extensions_directory(self, parser, temp_dir):
        """Test parsing multiple extensions in directory."""
        # Create multiple extension directories
        ext1_dir = temp_dir / "extension1"
        ext1_dir.mkdir()
        (ext1_dir / "__init__.py").write_text('"""Extension 1."""\n__version__ = "1.0.0"')
        
        ext2_dir = temp_dir / "extension2"
        ext2_dir.mkdir()
        (ext2_dir / "__init__.py").write_text('"""Extension 2."""\n__version__ = "2.0.0"')
        
        # Create non-extension directory (should be ignored)
        (temp_dir / ".hidden").mkdir()
        
        extensions = await parser.parse_extensions(temp_dir)
        
        assert len(extensions) == 2
        assert "extension1" in extensions
        assert "extension2" in extensions
    
    @pytest.mark.asyncio
    async def test_parse_extension_metadata_json(self, parser, temp_dir):
        """Test parsing extension metadata from JSON file."""
        ext_dir = temp_dir / "test_extension"
        ext_dir.mkdir()
        
        metadata_file = ext_dir / "extension.json"
        metadata = {
            "name": "test_extension",
            "version": "1.0.0",
            "description": "Test extension",
            "author": "Test Author",
            "license": "MIT",
            "dependencies": ["requests", "click"]
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        result = await parser._parse_extension_metadata(metadata_file)
        
        assert result is not None
        assert result["name"] == "test_extension"
        assert result["version"] == "1.0.0"
        assert result["dependencies"] == ["requests", "click"]
    
    @pytest.mark.asyncio
    async def test_parse_extension_metadata_init_py(self, parser, temp_dir):
        """Test parsing extension metadata from __init__.py file."""
        ext_dir = temp_dir / "test_extension"
        ext_dir.mkdir()
        
        init_file = ext_dir / "__init__.py"
        init_file.write_text('''
"""Test extension module."""

__version__ = "2.0.0"
__author__ = "Test Author"
__description__ = "Test extension description"
''')
        
        result = await parser._parse_extension_metadata(init_file)
        
        assert result is not None
        assert result["version"] == "2.0.0"
        assert result["author"] == "Test Author"
        assert result["description"] == "Test extension description"