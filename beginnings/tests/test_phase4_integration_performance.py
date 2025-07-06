"""Integration and performance tests for Phase 4 implementation.

This module provides comprehensive integration and performance validation 
for the complete Phase 4 implementation including interactive documentation,
migration framework, and community standards.
"""

import pytest
import tempfile
import time
import psutil
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

# Import Phase 4 modules
from beginnings.docs.interactive.config_editor import InteractiveConfigEditor
from beginnings.docs.interactive.code_playground import CodePlayground
from beginnings.docs.interactive.tutorial_tracker import TutorialProgressTracker
from beginnings.docs.website.static_generator import StaticSiteGenerator
from beginnings.docs.search.search_engine import DocumentationSearchEngine

from beginnings.migration import (
    MigrationFramework, 
    FlaskConverter, 
    DjangoConverter, 
    FastAPIConverter,
    MigrationConfig,
    FrameworkType
)

from beginnings.community import (
    ExtensionQualityValidator,
    ContributionManager,
    CommunityStandards
)


class TestPhase4Integration:
    """Test integration across Phase 4 components."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for integration tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create test directories
            (workspace / "source").mkdir()
            (workspace / "target").mkdir() 
            (workspace / "docs").mkdir()
            (workspace / "extensions").mkdir()
            
            yield workspace
    
    def test_full_documentation_pipeline(self, temp_workspace):
        """Test complete documentation generation pipeline."""
        docs_dir = temp_workspace / "docs"
        output_dir = temp_workspace / "output"
        
        # Create sample documentation
        (docs_dir / "index.md").write_text("""
# Test Documentation

This is a test documentation file.

## Configuration

Use the interactive config editor below:

```yaml
app:
  name: Test App
  debug: true
```

## Code Example

Try this code in the playground:

```python
def hello_world():
    return "Hello, World!"
```
""")
        
        # Initialize components
        config_editor = InteractiveConfigEditor()
        playground = CodePlayground()
        tracker = TutorialProgressTracker()
        generator = StaticSiteGenerator(
            content_directory=docs_dir,
            output_directory=output_dir
        )
        search_engine = DocumentationSearchEngine()
        
        # Test config editor functionality
        schema = {
            'app': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'debug': {'type': 'boolean'}
                }
            }
        }
        
        config_result = config_editor.validate_config({'app': {'name': 'Test', 'debug': True}}, schema)
        assert config_result['is_valid']
        
        # Test code playground
        code = "print('Hello, World!')"
        exec_result = playground.execute_code(code, timeout=5)
        assert exec_result['success']
        assert 'Hello, World!' in exec_result['output']
        
        # Test tutorial progress
        tutorial_id = tracker.start_tutorial("test_tutorial", "Test Tutorial")
        assert tutorial_id is not None
        
        progress = tracker.update_progress(tutorial_id, "step1", {"completed": True})
        assert progress['current_step'] == "step1"
        
        # Test static site generation
        generation_result = generator.generate_site()
        assert generation_result['success']
        assert (output_dir / "index.html").exists()
        
        # Test search functionality
        search_engine.add_document("test_doc", "Test documentation content", "/test", {"type": "docs"})
        results = search_engine.search("documentation")
        assert len(results) > 0
        assert results[0]['title'] == "test_doc"
    
    def test_migration_framework_integration(self, temp_workspace):
        """Test complete migration framework integration."""
        source_dir = temp_workspace / "source"
        target_dir = temp_workspace / "target"
        
        # Create sample Flask project
        flask_app = source_dir / "app.py"
        flask_app.write_text("""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello Flask!'

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        return jsonify({'message': 'User created'})
    return jsonify({'users': []})

if __name__ == '__main__':
    app.run(debug=True)
""")
        
        (source_dir / "requirements.txt").write_text("Flask==2.3.0\nrequests==2.28.0")
        
        # Initialize migration framework
        migration_framework = MigrationFramework()
        
        # Register converters
        migration_framework.register_converter(FrameworkType.FLASK, FlaskConverter())
        migration_framework.register_converter(FrameworkType.DJANGO, DjangoConverter())
        migration_framework.register_converter(FrameworkType.FASTAPI, FastAPIConverter())
        
        # Test compatibility analysis
        config = MigrationConfig(
            source_framework="flask",
            source_directory=source_dir,
            target_directory=target_dir
        )
        
        compatibility = migration_framework.analyze_compatibility(config)
        assert compatibility.is_compatible
        assert compatibility.detected_framework == "flask"
        
        # Test migration plan generation
        plan = migration_framework.generate_migration_plan(config)
        assert 'steps' in plan
        assert len(plan['steps']) > 0
        
        # Test complete migration
        result = migration_framework.migrate_project(config)
        assert result.success
        assert len(result.migrated_files) > 0
        assert (target_dir / "app.py").exists()
        assert (target_dir / "beginnings.yaml").exists()
        
        # Verify transformed content
        migrated_content = (target_dir / "app.py").read_text()
        assert "from beginnings import" in migrated_content
        assert "create_app()" in migrated_content
    
    def test_community_standards_integration(self, temp_workspace):
        """Test community standards and quality validation integration."""
        extension_dir = temp_workspace / "extensions" / "test_extension"
        extension_dir.mkdir(parents=True)
        
        # Create sample extension
        (extension_dir / "extension.yaml").write_text("""
name: "Test Extension"
version: "1.0.0"
description: "A comprehensive test extension for validation"
author: "Test Author"
license: "MIT"
beginnings_version: ">=1.0.0"
""")
        
        (extension_dir / "__init__.py").write_text("""
\"\"\"Test extension for community standards validation.\"\"\"

from beginnings.extensions import BaseExtension
from typing import Dict, Any


class TestExtension(BaseExtension):
    \"\"\"Test extension class.\"\"\"
    
    def __init__(self, config: Dict[str, Any] = None):
        \"\"\"Initialize test extension.\"\"\"
        super().__init__(config or {})
        self.name = "test_extension"
    
    def initialize(self, app) -> None:
        \"\"\"Initialize extension with app.\"\"\"
        app.config.setdefault('TEST_SETTING', 'default_value')
    
    def get_routes(self) -> list:
        \"\"\"Get extension routes.\"\"\"
        return []
""")
        
        # Create test file
        tests_dir = extension_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_extension.py").write_text("""
\"\"\"Tests for test extension.\"\"\"

import pytest
from test_extension import TestExtension


def test_extension_initialization():
    \"\"\"Test extension initialization.\"\"\"
    extension = TestExtension()
    assert extension.name == "test_extension"
""")
        
        # Create README
        (extension_dir / "README.md").write_text("""
# Test Extension

This is a test extension for community standards validation.

## Installation

```bash
pip install test-extension
```

## Usage

```python
from test_extension import TestExtension
extension = TestExtension()
```
""")
        
        # Test quality validation
        validator = ExtensionQualityValidator()
        result = validator.validate_extension(extension_dir)
        
        assert result.overall_score > 60  # Should pass basic quality checks
        assert 'code_quality' in result.metrics
        assert 'security' in result.metrics
        assert 'documentation' in result.metrics
        assert 'testing' in result.metrics
        
        # Test contribution management
        contribution_manager = ContributionManager(workspace / "contributions")
        
        # Register a contributor
        contributor_id = contribution_manager.register_contributor({
            'username': 'test_contributor',
            'email': 'test@example.com',
            'full_name': 'Test Contributor'
        })
        
        # Submit contribution
        submission_result = contribution_manager.submit_contribution({
            'type': 'extension',
            'name': 'test-extension',
            'version': '1.0.0',
            'description': 'A test extension for validation',
            'contributor_id': contributor_id,
            'license': 'MIT',
            'tags': ['testing', 'validation']
        })
        
        assert submission_result['success']
        
        # Test community standards
        standards = CommunityStandards()
        guidelines = standards.get_community_guidelines()
        
        assert 'code_of_conduct' in guidelines
        assert 'contribution_ethics' in guidelines
        assert 'enforcement' in guidelines
        
        publishing_standards = standards.get_publishing_standards()
        assert 'metadata_requirements' in publishing_standards
        assert 'quality_gates' in publishing_standards


class TestPhase4Performance:
    """Test performance characteristics of Phase 4 components."""
    
    def test_documentation_generation_performance(self, temp_workspace):
        """Test documentation generation performance with large content."""
        docs_dir = temp_workspace / "docs"
        output_dir = temp_workspace / "output"
        
        # Create multiple documentation files
        for i in range(50):
            doc_file = docs_dir / f"doc_{i}.md"
            doc_file.write_text(f"""
# Document {i}

This is documentation file number {i}.

## Section 1

Content for section 1 of document {i}.

## Section 2

Content for section 2 of document {i}.

{'Content line. ' * 100}
""")
        
        generator = StaticSiteGenerator(
            content_directory=docs_dir,
            output_directory=output_dir
        )
        
        # Measure generation time
        start_time = time.time()
        result = generator.generate_site()
        generation_time = time.time() - start_time
        
        assert result['success']
        assert generation_time < 30  # Should complete within 30 seconds
        assert len(list(output_dir.rglob("*.html"))) >= 50
    
    def test_migration_performance(self, temp_workspace):
        """Test migration performance with multiple files."""
        source_dir = temp_workspace / "source"
        target_dir = temp_workspace / "target"
        
        # Create multiple Flask files
        for i in range(20):
            py_file = source_dir / f"module_{i}.py"
            py_file.write_text(f"""
from flask import Flask, jsonify

app_{i} = Flask(__name__)

@app_{i}.route('/api/{i}')
def endpoint_{i}():
    return jsonify({{'module': {i}}})

{'# Comment line\\n' * 50}
""")
        
        migration_framework = MigrationFramework()
        migration_framework.register_converter(FrameworkType.FLASK, FlaskConverter())
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=source_dir,
            target_directory=target_dir
        )
        
        # Measure migration time
        start_time = time.time()
        result = migration_framework.migrate_project(config)
        migration_time = time.time() - start_time
        
        assert result.success
        assert migration_time < 20  # Should complete within 20 seconds
        assert len(result.migrated_files) >= 20
    
    def test_quality_validation_performance(self, temp_workspace):
        """Test quality validation performance with complex extension."""
        extension_dir = temp_workspace / "extensions" / "complex_extension"
        extension_dir.mkdir(parents=True)
        
        # Create complex extension structure
        (extension_dir / "extension.yaml").write_text("""
name: "Complex Extension"
version: "1.0.0"
description: "A complex extension for performance testing"
author: "Test Author"
license: "MIT"
""")
        
        # Create multiple Python files
        for i in range(10):
            py_file = extension_dir / f"module_{i}.py"
            py_file.write_text(f"""
\"\"\"Module {i} for complex extension.\"\"\"

from typing import Dict, Any, List, Optional
import json
import logging


class Module{i}:
    \"\"\"Module {i} class.\"\"\"
    
    def __init__(self, config: Dict[str, Any] = None):
        \"\"\"Initialize module {i}.\"\"\"
        self.config = config or {{}}
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        \"\"\"Process data in module {i}.\"\"\"
        try:
            result = {{}}
            for item in data:
                if self._validate_item(item):
                    result[f'item_{{len(result)}}'] = self._transform_item(item)
            return result
        except Exception as e:
            self.logger.error(f'Error processing data: {{e}}')
            return None
    
    def _validate_item(self, item: Dict[str, Any]) -> bool:
        \"\"\"Validate data item.\"\"\"
        required_fields = ['id', 'name', 'type']
        return all(field in item for field in required_fields)
    
    def _transform_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Transform data item.\"\"\"
        return {{
            'id': item['id'],
            'name': item['name'].upper(),
            'type': item['type'],
            'processed': True,
            'module': {i}
        }}

{'# Additional comment line\\n' * 20}
""")
        
        # Create tests
        tests_dir = extension_dir / "tests"
        tests_dir.mkdir()
        for i in range(5):
            test_file = tests_dir / f"test_module_{i}.py"
            test_file.write_text(f"""
\"\"\"Tests for module {i}.\"\"\"

import pytest
from module_{i} import Module{i}


class TestModule{i}:
    \"\"\"Test module {i}.\"\"\"
    
    def test_initialization(self):
        \"\"\"Test module initialization.\"\"\"
        module = Module{i}()
        assert module.config == {{}}
    
    def test_data_processing(self):
        \"\"\"Test data processing.\"\"\"
        module = Module{i}()
        data = [{{'id': 1, 'name': 'test', 'type': 'item'}}]
        result = module.process_data(data)
        assert result is not None
        assert len(result) == 1
""")
        
        validator = ExtensionQualityValidator()
        
        # Measure validation time
        start_time = time.time()
        result = validator.validate_extension(extension_dir)
        validation_time = time.time() - start_time
        
        assert validation_time < 10  # Should complete within 10 seconds
        assert result.overall_score > 0
        assert len(result.metrics) == 4  # All metrics should be calculated
    
    def test_concurrent_operations(self, temp_workspace):
        """Test concurrent operations across Phase 4 components."""
        
        def create_and_validate_extension(index):
            """Create and validate an extension concurrently."""
            ext_dir = temp_workspace / f"extension_{index}"
            ext_dir.mkdir(exist_ok=True)
            
            (ext_dir / "extension.yaml").write_text(f"""
name: "Extension {index}"
version: "1.0.0"
description: "Extension {index} for concurrent testing"
author: "Test Author"
license: "MIT"
""")
            
            (ext_dir / "__init__.py").write_text(f"""
\"\"\"Extension {index}.\"\"\"

class Extension{index}:
    \"\"\"Extension {index} class.\"\"\"
    
    def __init__(self):
        self.name = "extension_{index}"
""")
            
            validator = ExtensionQualityValidator()
            result = validator.validate_extension(ext_dir)
            return result.overall_score > 0
        
        # Test concurrent extension validation
        with ThreadPoolExecutor(max_workers=5) as executor:
            start_time = time.time()
            futures = [executor.submit(create_and_validate_extension, i) for i in range(10)]
            results = [future.result() for future in futures]
            concurrent_time = time.time() - start_time
        
        assert all(results)  # All validations should succeed
        assert concurrent_time < 15  # Should complete within 15 seconds
    
    def test_memory_usage(self, temp_workspace):
        """Test memory usage during intensive operations."""
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        docs_dir = temp_workspace / "docs"
        output_dir = temp_workspace / "output"
        
        # Create large documentation
        for i in range(100):
            doc_file = docs_dir / f"large_doc_{i}.md"
            content = f"# Large Document {i}\n\n" + "Large content. " * 1000
            doc_file.write_text(content)
        
        generator = StaticSiteGenerator(
            content_directory=docs_dir,
            output_directory=output_dir
        )
        
        result = generator.generate_site()
        
        # Get peak memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Clean up
        gc.collect()
        
        assert result['success']
        assert memory_increase < 500  # Should not use more than 500MB additional memory
    
    def test_scalability_limits(self, temp_workspace):
        """Test scalability limits of Phase 4 components."""
        
        # Test search engine with large dataset
        search_engine = DocumentationSearchEngine()
        
        # Add many documents
        start_time = time.time()
        for i in range(1000):
            content = f"Document {i} with content about testing and validation " * 10
            search_engine.add_document(f"doc_{i}", content, f"/doc_{i}", {"type": "test"})
        indexing_time = time.time() - start_time
        
        # Test search performance
        start_time = time.time()
        results = search_engine.search("testing validation")
        search_time = time.time() - start_time
        
        assert indexing_time < 30  # Indexing should complete within 30 seconds
        assert search_time < 2   # Search should complete within 2 seconds
        assert len(results) > 0
        assert results[0]['score'] > 0


class TestPhase4ErrorHandling:
    """Test error handling and resilience in Phase 4 components."""
    
    def test_migration_error_recovery(self, temp_workspace):
        """Test migration error handling and recovery."""
        source_dir = temp_workspace / "source"
        target_dir = temp_workspace / "target"
        
        # Create invalid Python file
        (source_dir / "invalid.py").write_text("invalid python syntax <<<")
        
        # Create valid file
        (source_dir / "valid.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello!'
""")
        
        migration_framework = MigrationFramework()
        migration_framework.register_converter(FrameworkType.FLASK, FlaskConverter())
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=source_dir,
            target_directory=target_dir
        )
        
        # Test partial migration with errors
        result = migration_framework.migrate_project(config)
        
        # Should have partial success
        assert len(result.migrated_files) > 0  # Valid file should be migrated
        assert len(result.errors) > 0         # Invalid file should cause errors
        
        # Valid file should be properly migrated
        assert (target_dir / "valid.py").exists()
    
    def test_quality_validation_error_handling(self, temp_workspace):
        """Test quality validator error handling."""
        validator = ExtensionQualityValidator()
        
        # Test with non-existent directory
        result = validator.validate_extension(temp_workspace / "nonexistent")
        assert not result.is_compliant
        assert len(result.issues) > 0
        
        # Test with empty directory
        empty_dir = temp_workspace / "empty"
        empty_dir.mkdir()
        
        result = validator.validate_extension(empty_dir)
        assert not result.is_compliant
        assert result.overall_score == 0
    
    def test_contribution_manager_error_handling(self, temp_workspace):
        """Test contribution manager error handling."""
        manager = ContributionManager(temp_workspace / "contributions")
        
        # Test invalid contribution submission
        result = manager.submit_contribution({
            'name': '',  # Invalid: empty name
            'version': 'invalid-version',  # Invalid version format
            'description': '',  # Invalid: empty description
            'contributor_id': 'nonexistent'  # Nonexistent contributor
        })
        
        assert not result['success']
        assert 'issues' in result
        assert len(result['issues']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])