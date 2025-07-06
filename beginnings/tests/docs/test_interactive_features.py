"""Tests for interactive documentation features.

This module tests the interactive components of the documentation system
including live configuration editor, code playground, and tutorial tracking.
Following TDD methodology - tests written first to define interfaces.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Import the interfaces we'll implement (they don't exist yet - TDD)
from beginnings.docs.interactive.config_editor import (
    InteractiveConfigEditor,
    ConfigEditorResult,
    ValidationResult
)
from beginnings.docs.interactive.code_playground import (
    CodePlayground,
    PlaygroundResult,
    ExecutionContext
)
from beginnings.docs.interactive.tutorial_tracker import (
    TutorialProgressTracker,
    ProgressResult,
    CompletionStatus
)


class TestInteractiveConfigEditor:
    """Test interactive configuration editor following SRP."""
    
    @pytest.fixture
    def config_editor(self):
        """Create config editor instance for testing."""
        return InteractiveConfigEditor()
    
    @pytest.fixture
    def sample_config_schema(self):
        """Sample configuration schema for testing."""
        return {
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "debug": {"type": "boolean", "default": False},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
                    },
                    "required": ["name"]
                },
                "database": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "pool_size": {"type": "integer", "minimum": 1}
                    }
                }
            },
            "required": ["app"]
        }
    
    def test_config_editor_initialization(self, config_editor):
        """Test config editor initializes correctly."""
        assert config_editor is not None
        assert hasattr(config_editor, 'validate_config')
        assert hasattr(config_editor, 'generate_form')
        assert hasattr(config_editor, 'update_config')
    
    def test_validate_config_valid_input(self, config_editor, sample_config_schema):
        """Test config validation with valid input."""
        valid_config = {
            "app": {
                "name": "test-app",
                "debug": True,
                "port": 8000
            },
            "database": {
                "url": "postgresql://localhost/test",
                "pool_size": 5
            }
        }
        
        result = config_editor.validate_config(valid_config, sample_config_schema)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validate_config_invalid_input(self, config_editor, sample_config_schema):
        """Test config validation with invalid input."""
        invalid_config = {
            "app": {
                "debug": True,
                "port": 70000  # Port too high
            },
            "database": {
                "url": "invalid-url",
                "pool_size": -1  # Negative pool size
            }
        }
        
        result = config_editor.validate_config(invalid_config, sample_config_schema)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("required" in error.lower() for error in result.errors)  # Missing app.name
        assert any("port" in error.lower() for error in result.errors)
    
    def test_generate_form_from_schema(self, config_editor, sample_config_schema):
        """Test form generation from schema."""
        result = config_editor.generate_form(sample_config_schema)
        
        assert isinstance(result, ConfigEditorResult)
        assert result.success is True
        assert "html_form" in result.data
        assert "javascript" in result.data
        assert "css" in result.data
        
        # Check form contains expected fields
        html_form = result.data["html_form"]
        assert "app.name" in html_form
        assert "app.debug" in html_form
        assert "app.port" in html_form
        assert "database.url" in html_form
    
    def test_update_config_realtime(self, config_editor, sample_config_schema):
        """Test real-time config updates."""
        initial_config = {"app": {"name": "test", "debug": False}}
        
        update_data = {
            "field": "app.debug",
            "value": True,
            "config": initial_config
        }
        
        result = config_editor.update_config(update_data, sample_config_schema)
        
        assert isinstance(result, ConfigEditorResult)
        assert result.success is True
        assert result.data["updated_config"]["app"]["debug"] is True
        assert result.data["validation"]["is_valid"] is True
    
    def test_config_editor_error_handling(self, config_editor):
        """Test config editor handles errors gracefully."""
        # Test with None schema
        result = config_editor.validate_config({}, None)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert "schema" in result.errors[0].lower()
        
        # Test with malformed schema
        malformed_schema = {"invalid": "schema"}
        result = config_editor.validate_config({}, malformed_schema)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False


class TestCodePlayground:
    """Test code playground following SRP and security principles."""
    
    @pytest.fixture
    def code_playground(self):
        """Create code playground instance for testing."""
        return CodePlayground()
    
    @pytest.fixture
    def execution_context(self):
        """Create execution context for testing."""
        return ExecutionContext(
            timeout_seconds=30,
            memory_limit_mb=128,
            allowed_imports=['beginnings', 'json', 're'],
            forbidden_functions=['eval', 'exec', 'open', '__import__']
        )
    
    def test_playground_initialization(self, code_playground):
        """Test playground initializes correctly."""
        assert code_playground is not None
        assert hasattr(code_playground, 'execute_code')
        assert hasattr(code_playground, 'validate_code')
        assert hasattr(code_playground, 'create_sandbox')
    
    def test_execute_safe_code(self, code_playground, execution_context):
        """Test execution of safe code."""
        safe_code = """
import json

data = {"message": "Hello from beginnings!"}
result = json.dumps(data)
print(result)
"""
        
        result = code_playground.execute_code(safe_code, execution_context)
        
        assert isinstance(result, PlaygroundResult)
        assert result.success is True
        assert result.stdout is not None
        assert "Hello from beginnings!" in result.stdout
        assert result.stderr == ""
        assert result.execution_time_ms > 0
    
    def test_execute_unsafe_code(self, code_playground, execution_context):
        """Test execution blocks unsafe code."""
        unsafe_code = """
import os
os.system("rm -rf /")  # This should be blocked
"""
        
        result = code_playground.execute_code(unsafe_code, execution_context)
        
        assert isinstance(result, PlaygroundResult)
        assert result.success is False
        assert "security" in result.error_message.lower() or "forbidden" in result.error_message.lower()
    
    def test_execute_code_with_timeout(self, code_playground, execution_context):
        """Test code execution respects timeout."""
        infinite_loop = """
while True:
    pass
"""
        
        result = code_playground.execute_code(infinite_loop, execution_context)
        
        assert isinstance(result, PlaygroundResult)
        assert result.success is False
        assert "timeout" in result.error_message.lower()
        assert result.execution_time_ms >= execution_context.timeout_seconds * 1000
    
    def test_validate_code_syntax(self, code_playground):
        """Test code syntax validation."""
        # Valid syntax
        valid_code = "print('Hello World')"
        result = code_playground.validate_code(valid_code)
        assert result.is_valid is True
        assert len(result.errors) == 0
        
        # Invalid syntax
        invalid_code = "print('Hello World'"  # Missing closing parenthesis
        result = code_playground.validate_code(invalid_code)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "syntax" in result.errors[0].lower()
    
    def test_create_sandbox_isolation(self, code_playground, execution_context):
        """Test sandbox creates isolated environment."""
        code1 = "x = 100"
        code2 = "print(x)"  # Should fail if properly isolated
        
        # Execute first code
        result1 = code_playground.execute_code(code1, execution_context)
        assert result1.success is True
        
        # Execute second code in new sandbox
        result2 = code_playground.execute_code(code2, execution_context)
        assert result2.success is False
        assert "nameerror" in result2.error_message.lower() or "not defined" in result2.error_message.lower()
    
    def test_playground_memory_limits(self, code_playground, execution_context):
        """Test playground respects memory limits."""
        memory_intensive_code = """
data = [i for i in range(10**8)]  # Large list creation
"""
        
        result = code_playground.execute_code(memory_intensive_code, execution_context)
        
        # Should either succeed within limits or fail with memory error
        if not result.success:
            assert "memory" in result.error_message.lower()


class TestTutorialProgressTracker:
    """Test tutorial progress tracking following SRP."""
    
    @pytest.fixture
    def progress_tracker(self):
        """Create progress tracker instance for testing."""
        return TutorialProgressTracker()
    
    @pytest.fixture
    def sample_tutorial(self):
        """Sample tutorial structure for testing."""
        return {
            "id": "getting-started",
            "title": "Getting Started with Beginnings",
            "steps": [
                {
                    "id": "install",
                    "title": "Installation",
                    "type": "instruction",
                    "completion_criteria": "package_installed"
                },
                {
                    "id": "create-project",
                    "title": "Create Your First Project",
                    "type": "interactive",
                    "completion_criteria": "project_created"
                },
                {
                    "id": "run-server",
                    "title": "Run Development Server",
                    "type": "interactive", 
                    "completion_criteria": "server_running"
                }
            ]
        }
    
    def test_tracker_initialization(self, progress_tracker):
        """Test progress tracker initializes correctly."""
        assert progress_tracker is not None
        assert hasattr(progress_tracker, 'start_tutorial')
        assert hasattr(progress_tracker, 'complete_step')
        assert hasattr(progress_tracker, 'get_progress')
        assert hasattr(progress_tracker, 'save_progress')
    
    def test_start_tutorial(self, progress_tracker, sample_tutorial):
        """Test starting a tutorial."""
        user_id = "test_user_123"
        
        result = progress_tracker.start_tutorial(user_id, sample_tutorial)
        
        assert isinstance(result, ProgressResult)
        assert result.success is True
        assert result.tutorial_id == "getting-started"
        assert result.current_step_id == "install"
        assert result.completion_percentage == 0.0
        assert result.status == CompletionStatus.IN_PROGRESS
    
    def test_complete_step(self, progress_tracker, sample_tutorial):
        """Test completing tutorial steps."""
        user_id = "test_user_123"
        
        # Start tutorial
        progress_tracker.start_tutorial(user_id, sample_tutorial)
        
        # Complete first step
        result = progress_tracker.complete_step(
            user_id, 
            "getting-started", 
            "install",
            {"package_installed": True}
        )
        
        assert isinstance(result, ProgressResult)
        assert result.success is True
        assert result.current_step_id == "create-project"
        assert result.completion_percentage == pytest.approx(33.33, rel=1e-2)
        assert result.completed_steps == ["install"]
    
    def test_tutorial_completion(self, progress_tracker, sample_tutorial):
        """Test completing entire tutorial."""
        user_id = "test_user_123"
        
        # Start tutorial
        progress_tracker.start_tutorial(user_id, sample_tutorial)
        
        # Complete all steps
        for step in sample_tutorial["steps"]:
            progress_tracker.complete_step(
                user_id,
                "getting-started",
                step["id"],
                {step["completion_criteria"]: True}
            )
        
        result = progress_tracker.get_progress(user_id, "getting-started")
        
        assert result.completion_percentage == 100.0
        assert result.status == CompletionStatus.COMPLETED
        assert len(result.completed_steps) == 3
    
    def test_save_and_load_progress(self, progress_tracker, sample_tutorial):
        """Test saving and loading progress."""
        user_id = "test_user_123"
        
        # Start tutorial and complete a step
        progress_tracker.start_tutorial(user_id, sample_tutorial)
        progress_tracker.complete_step(
            user_id, 
            "getting-started", 
            "install",
            {"package_installed": True}
        )
        
        # Save progress
        save_result = progress_tracker.save_progress(user_id, "getting-started")
        assert save_result.success is True
        
        # Create new tracker and load progress
        new_tracker = TutorialProgressTracker()
        load_result = new_tracker.load_progress(user_id, "getting-started")
        
        assert load_result.success is True
        assert load_result.current_step_id == "create-project"
        assert len(load_result.completed_steps) == 1
    
    def test_progress_analytics(self, progress_tracker, sample_tutorial):
        """Test progress analytics and tracking."""
        user_id = "test_user_123"
        
        # Start tutorial
        start_time = progress_tracker.start_tutorial(user_id, sample_tutorial)
        
        # Complete steps with some delay simulation
        import time
        time.sleep(0.1)  # Small delay for timing
        
        progress_tracker.complete_step(
            user_id, 
            "getting-started", 
            "install",
            {"package_installed": True}
        )
        
        result = progress_tracker.get_progress(user_id, "getting-started")
        
        assert result.time_spent_seconds > 0
        assert result.started_at is not None
        assert result.last_activity_at is not None
        assert result.average_step_time_seconds > 0
    
    def test_multiple_users_isolation(self, progress_tracker, sample_tutorial):
        """Test progress tracking for multiple users is isolated."""
        user1_id = "user1"
        user2_id = "user2"
        
        # Start tutorial for both users
        progress_tracker.start_tutorial(user1_id, sample_tutorial)
        progress_tracker.start_tutorial(user2_id, sample_tutorial)
        
        # Complete different steps for each user
        progress_tracker.complete_step(
            user1_id, 
            "getting-started", 
            "install",
            {"package_installed": True}
        )
        
        # Check user1 progress
        user1_progress = progress_tracker.get_progress(user1_id, "getting-started")
        assert len(user1_progress.completed_steps) == 1
        
        # Check user2 progress (should be unchanged)
        user2_progress = progress_tracker.get_progress(user2_id, "getting-started")
        assert len(user2_progress.completed_steps) == 0
        assert user2_progress.current_step_id == "install"