"""Integration tests for documentation generation system."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from beginnings.docs import DocumentationGenerator, DocumentationConfig, OutputFormat


class TestDocumentationIntegration:
    """Test documentation generation system integration."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_source_files(self, temp_dir):
        """Create sample source files for testing."""
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        
        # Create sample Python module
        module_file = src_dir / "sample_module.py"
        module_file.write_text('''
"""Sample module for testing documentation generation."""

class SampleClass:
    """Sample class with methods."""
    
    def sample_method(self, param: str) -> str:
        """Sample method with docstring.
        
        Args:
            param: Sample parameter
            
        Returns:
            Processed parameter
        """
        return f"processed: {param}"

def sample_function(value: int) -> int:
    """Sample function with docstring.
    
    Args:
        value: Input value
        
    Returns:
        Doubled value
    """
    return value * 2
''')
        
        return src_dir
    
    @pytest.fixture
    def documentation_config(self, temp_dir, sample_source_files):
        """Create documentation configuration."""
        return DocumentationConfig(
            source_paths=[str(sample_source_files)],
            output_dir=str(temp_dir / "docs"),
            project_name="Test Project",
            project_version="1.0.0",
            project_description="Test project for documentation",
            author="Test Author",
            output_formats=[OutputFormat.HTML, OutputFormat.MARKDOWN]
        )
    
    @pytest.mark.asyncio
    async def test_documentation_generator_initialization(self, documentation_config):
        """Test documentation generator initialization."""
        generator = DocumentationGenerator(documentation_config)
        
        assert generator.config == documentation_config
        assert generator.code_parser is not None
        assert generator.config_parser is not None
        assert generator.extension_parser is not None
        assert generator.api_extractor is not None
        assert generator.route_extractor is not None
        assert generator.extension_extractor is not None
        assert generator.template_engine is not None
        assert generator.theme_manager is not None
        assert len(generator.renderers) >= 2
    
    @pytest.mark.asyncio
    async def test_code_documentation_extraction(self, documentation_config, sample_source_files):
        """Test code documentation extraction."""
        generator = DocumentationGenerator(documentation_config)
        
        # Extract code documentation
        await generator._extract_code_documentation()
        
        code_docs = generator.documentation_data.get("code_documentation", {})
        assert len(code_docs) > 0
        
        # Check for sample module
        module_name = "sample_module"
        assert module_name in code_docs
        
        module_data = code_docs[module_name]
        assert module_data.docstring is not None
        assert hasattr(module_data, "classes")
        assert hasattr(module_data, "functions")
        
        # Check sample class
        assert "SampleClass" in module_data.classes
        sample_class = module_data.classes["SampleClass"]
        assert sample_class.docstring is not None
        assert hasattr(sample_class, "methods")
        assert "sample_method" in sample_class.methods
        
        # Check sample function
        assert "sample_function" in module_data.functions
        sample_func = module_data.functions["sample_function"]
        assert sample_func.docstring is not None
        assert sample_func.return_type == "int"
    
    @pytest.mark.asyncio
    async def test_full_documentation_generation(self, documentation_config, sample_source_files):
        """Test full documentation generation process."""
        generator = DocumentationGenerator(documentation_config)
        
        # Mock some components to avoid external dependencies
        generator.template_engine.render_template = AsyncMock(return_value="<html>Test HTML</html>")
        generator.theme_manager.get_theme_assets = AsyncMock(return_value={"css/test.css": "body {}"})
        
        # Generate documentation
        results = await generator.generate_documentation()
        
        # Check results structure
        assert "generated_files" in results
        assert "errors" in results
        assert "warnings" in results
        assert "statistics" in results
        assert "generation_time" in results
        
        # Check that documentation data was extracted
        assert "code_documentation" in generator.documentation_data
        assert "api" in generator.documentation_data
        assert "extensions" in generator.documentation_data
        assert "configuration" in generator.documentation_data
        assert "metadata" in generator.documentation_data
        
        # Check metadata
        metadata = generator.documentation_data["metadata"]
        assert metadata["project_name"] == "Test Project"
        assert metadata["project_version"] == "1.0.0"
        assert metadata["author"] == "Test Author"
    
    @pytest.mark.asyncio
    async def test_documentation_validation(self, documentation_config, sample_source_files):
        """Test documentation validation."""
        generator = DocumentationGenerator(documentation_config)
        
        # Extract documentation data first
        await generator._extract_documentation_data({})
        
        # Validate documentation
        validation_results = await generator.validate_documentation()
        
        # Check validation results structure
        assert "missing_docstrings" in validation_results
        assert "broken_links" in validation_results
        assert "orphaned_files" in validation_results
        assert "incomplete_api_docs" in validation_results
        assert "warnings" in validation_results
        assert "score" in validation_results
        
        # Score should be a float between 0 and 100
        assert isinstance(validation_results["score"], float)
        assert 0 <= validation_results["score"] <= 100
    
    @pytest.mark.asyncio
    async def test_api_documentation_extraction(self, documentation_config):
        """Test API documentation extraction."""
        generator = DocumentationGenerator(documentation_config)
        
        # Create sample API file
        src_dir = Path(documentation_config.source_paths[0])
        api_file = src_dir / "api.py"
        api_file.write_text('''
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID.
    
    Args:
        user_id: User identifier
        
    Returns:
        User data
    """
    return {"user_id": user_id}

@app.post("/users")
async def create_user(user_data: dict):
    """Create new user.
    
    Args:
        user_data: User creation data
        
    Returns:
        Created user data
    """
    return user_data
''')
        
        # Extract API documentation
        api_data = await generator.generate_api_documentation()
        
        # Check API data structure
        assert "routes" in api_data
        assert "endpoints" in api_data
        assert "models" in api_data
        assert "middleware" in api_data
    
    @pytest.mark.asyncio
    async def test_statistics_generation(self, documentation_config, sample_source_files):
        """Test documentation statistics generation."""
        generator = DocumentationGenerator(documentation_config)
        
        # Extract documentation data
        await generator._extract_documentation_data({})
        
        # Generate statistics
        stats = await generator._generate_statistics()
        
        # Check statistics structure
        assert "total_modules" in stats
        assert "total_classes" in stats
        assert "total_functions" in stats
        assert "total_api_endpoints" in stats
        assert "total_extensions" in stats
        assert "documentation_coverage" in stats
        assert "generated_files_count" in stats
        
        # Check that we have some documentation
        assert stats["total_modules"] > 0
        assert stats["total_classes"] > 0
        assert stats["total_functions"] > 0
        
        # Coverage should be a percentage
        assert 0 <= stats["documentation_coverage"] <= 100
    
    def test_documentation_config_serialization(self):
        """Test documentation configuration serialization."""
        config = DocumentationConfig(
            project_name="Test Project",
            project_version="1.0.0",
            output_formats=[OutputFormat.HTML, OutputFormat.PDF]
        )
        
        # Test to_dict
        config_dict = config.to_dict()
        assert config_dict["project_name"] == "Test Project"
        assert config_dict["project_version"] == "1.0.0"
        assert config_dict["output_formats"] == ["html", "pdf"]
        
        # Test from_dict
        restored_config = DocumentationConfig.from_dict(config_dict)
        assert restored_config.project_name == "Test Project"
        assert restored_config.project_version == "1.0.0"
        assert restored_config.output_formats == [OutputFormat.HTML, OutputFormat.PDF]