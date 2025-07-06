"""Tutorial progress tracking system.

This module provides progress tracking for interactive tutorials with
completion validation and analytics. Follows Single Responsibility Principle.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from pathlib import Path


class CompletionStatus(Enum):
    """Tutorial completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class StepType(Enum):
    """Tutorial step types."""
    INSTRUCTION = "instruction"
    INTERACTIVE = "interactive"
    CODE_EXERCISE = "code_exercise"
    QUIZ = "quiz"
    VERIFICATION = "verification"


@dataclass
class TutorialStep:
    """Individual tutorial step configuration."""
    
    id: str
    title: str
    step_type: StepType
    content: str = ""
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    estimated_time_minutes: int = 5
    prerequisites: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Tutorial:
    """Tutorial configuration."""
    
    id: str
    title: str
    description: str
    steps: List[TutorialStep]
    difficulty_level: str = "beginner"
    estimated_duration_minutes: int = 30
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class StepCompletion:
    """Record of step completion."""
    
    step_id: str
    completed_at: datetime
    completion_data: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 1
    time_spent_seconds: float = 0
    hints_used: List[str] = field(default_factory=list)


@dataclass
class ProgressResult:
    """Result of progress tracking operation."""
    
    success: bool
    tutorial_id: Optional[str] = None
    current_step_id: Optional[str] = None
    completion_percentage: float = 0.0
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    completed_steps: List[str] = field(default_factory=list)
    time_spent_seconds: float = 0
    started_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    average_step_time_seconds: float = 0
    error_message: Optional[str] = None


class ProgressStorage:
    """Handles persistence of tutorial progress.
    
    Follows Single Responsibility Principle - only handles data storage.
    Interface Segregation - specific interface for progress storage.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize progress storage.
        
        Args:
            storage_path: Path to store progress data
        """
        self.storage_path = storage_path or Path.cwd() / ".tutorial_progress"
        self.storage_path.mkdir(exist_ok=True)
    
    def save_progress(self, user_id: str, tutorial_id: str, progress_data: Dict[str, Any]) -> bool:
        """Save user's tutorial progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            progress_data: Progress data to save
            
        Returns:
            True if saved successfully
        """
        try:
            user_dir = self.storage_path / user_id
            user_dir.mkdir(exist_ok=True)
            
            progress_file = user_dir / f"{tutorial_id}.json"
            
            # Add metadata
            progress_data["last_saved"] = datetime.now(timezone.utc).isoformat()
            progress_data["version"] = "1.0"
            
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2, default=str)
            
            return True
        except Exception:
            return False
    
    def load_progress(self, user_id: str, tutorial_id: str) -> Optional[Dict[str, Any]]:
        """Load user's tutorial progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            Progress data or None if not found
        """
        try:
            progress_file = self.storage_path / user_id / f"{tutorial_id}.json"
            
            if not progress_file.exists():
                return None
            
            with open(progress_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def delete_progress(self, user_id: str, tutorial_id: str) -> bool:
        """Delete user's tutorial progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            progress_file = self.storage_path / user_id / f"{tutorial_id}.json"
            if progress_file.exists():
                progress_file.unlink()
            return True
        except Exception:
            return False
    
    def list_user_tutorials(self, user_id: str) -> List[str]:
        """List all tutorials for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of tutorial IDs
        """
        try:
            user_dir = self.storage_path / user_id
            if not user_dir.exists():
                return []
            
            tutorial_files = user_dir.glob("*.json")
            return [f.stem for f in tutorial_files]
        except Exception:
            return []


class CompletionValidator:
    """Validates tutorial step completion.
    
    Follows Single Responsibility Principle - only handles completion validation.
    """
    
    def __init__(self):
        """Initialize completion validator."""
        self.validators = {
            "package_installed": self._validate_package_installed,
            "project_created": self._validate_project_created,
            "server_running": self._validate_server_running,
            "code_executed": self._validate_code_executed,
            "file_exists": self._validate_file_exists,
            "config_valid": self._validate_config_valid,
        }
    
    def validate_completion(
        self, 
        step: TutorialStep, 
        completion_data: Dict[str, Any]
    ) -> bool:
        """Validate if step completion criteria are met.
        
        Args:
            step: Tutorial step configuration
            completion_data: Data submitted for completion
            
        Returns:
            True if completion criteria are met
        """
        criteria = step.completion_criteria
        
        for criterion_name, expected_value in criteria.items():
            if criterion_name in self.validators:
                validator = self.validators[criterion_name]
                if not validator(completion_data, expected_value):
                    return False
            else:
                # Simple value comparison for unknown criteria
                if completion_data.get(criterion_name) != expected_value:
                    return False
        
        return True
    
    def _validate_package_installed(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate package installation."""
        return data.get("package_installed", False) is True
    
    def _validate_project_created(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate project creation."""
        return data.get("project_created", False) is True
    
    def _validate_server_running(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate server is running."""
        return data.get("server_running", False) is True
    
    def _validate_code_executed(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate code execution."""
        return data.get("code_executed", False) is True
    
    def _validate_file_exists(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate file exists."""
        file_path = data.get("file_path")
        if not file_path:
            return False
        return Path(file_path).exists()
    
    def _validate_config_valid(self, data: Dict[str, Any], expected: Any) -> bool:
        """Validate configuration is valid."""
        return data.get("config_valid", False) is True


class TutorialProgressTracker:
    """Tracks user progress through interactive tutorials.
    
    Follows Single Responsibility Principle - orchestrates tutorial progress tracking.
    Uses Dependency Inversion - depends on storage and validation abstractions.
    """
    
    def __init__(self, storage: Optional[ProgressStorage] = None):
        """Initialize tutorial progress tracker.
        
        Args:
            storage: Optional progress storage implementation
        """
        self.storage = storage or ProgressStorage()
        self.validator = CompletionValidator()
        self._active_sessions = {}
        self._tutorials = {}
    
    def register_tutorial(self, tutorial: Tutorial) -> bool:
        """Register a tutorial for tracking.
        
        Args:
            tutorial: Tutorial configuration
            
        Returns:
            True if registered successfully
        """
        try:
            self._tutorials[tutorial.id] = tutorial
            return True
        except Exception:
            return False
    
    def start_tutorial(self, user_id: str, tutorial: Tutorial) -> ProgressResult:
        """Start a tutorial for a user.
        
        Args:
            user_id: User identifier
            tutorial: Tutorial to start
            
        Returns:
            Progress result with initial state
        """
        try:
            # Register tutorial if not already registered
            if tutorial.id not in self._tutorials:
                self.register_tutorial(tutorial)
            
            # Check if tutorial already in progress
            existing_progress = self.storage.load_progress(user_id, tutorial.id)
            if existing_progress:
                return self._load_existing_progress(user_id, tutorial.id, existing_progress)
            
            # Create new progress
            started_at = datetime.now(timezone.utc)
            first_step_id = tutorial.steps[0].id if tutorial.steps else None
            
            progress_data = {
                "tutorial_id": tutorial.id,
                "user_id": user_id,
                "status": CompletionStatus.IN_PROGRESS.value,
                "started_at": started_at.isoformat(),
                "current_step_id": first_step_id,
                "completed_steps": [],
                "step_completions": [],
                "last_activity_at": started_at.isoformat(),
                "total_time_seconds": 0
            }
            
            # Save initial progress
            self.storage.save_progress(user_id, tutorial.id, progress_data)
            
            # Create active session
            session_id = str(uuid.uuid4())
            self._active_sessions[session_id] = {
                "user_id": user_id,
                "tutorial_id": tutorial.id,
                "started_at": time.time()
            }
            
            return ProgressResult(
                success=True,
                tutorial_id=tutorial.id,
                current_step_id=first_step_id,
                completion_percentage=0.0,
                status=CompletionStatus.IN_PROGRESS,
                completed_steps=[],
                started_at=started_at
            )
            
        except Exception as e:
            return ProgressResult(
                success=False,
                error_message=f"Failed to start tutorial: {str(e)}"
            )
    
    def complete_step(
        self, 
        user_id: str, 
        tutorial_id: str, 
        step_id: str,
        completion_data: Dict[str, Any]
    ) -> ProgressResult:
        """Complete a tutorial step.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            step_id: Step identifier
            completion_data: Data proving step completion
            
        Returns:
            Updated progress result
        """
        try:
            # Load current progress
            progress_data = self.storage.load_progress(user_id, tutorial_id)
            if not progress_data:
                return ProgressResult(
                    success=False,
                    error_message="No tutorial progress found"
                )
            
            # Get tutorial and step
            tutorial = self._tutorials.get(tutorial_id)
            if not tutorial:
                return ProgressResult(
                    success=False,
                    error_message="Tutorial not found"
                )
            
            step = next((s for s in tutorial.steps if s.id == step_id), None)
            if not step:
                return ProgressResult(
                    success=False,
                    error_message="Step not found"
                )
            
            # Validate completion
            if not self.validator.validate_completion(step, completion_data):
                return ProgressResult(
                    success=False,
                    error_message="Step completion criteria not met"
                )
            
            # Record completion
            completed_at = datetime.now(timezone.utc)
            step_completion = {
                "step_id": step_id,
                "completed_at": completed_at.isoformat(),
                "completion_data": completion_data,
                "time_spent_seconds": self._calculate_step_time(progress_data, step_id)
            }
            
            # Update progress
            if step_id not in progress_data["completed_steps"]:
                progress_data["completed_steps"].append(step_id)
                progress_data["step_completions"].append(step_completion)
            
            progress_data["last_activity_at"] = completed_at.isoformat()
            
            # Calculate next step
            current_step_index = next(
                (i for i, s in enumerate(tutorial.steps) if s.id == step_id), 
                -1
            )
            
            if current_step_index >= 0 and current_step_index < len(tutorial.steps) - 1:
                # Move to next step
                next_step = tutorial.steps[current_step_index + 1]
                progress_data["current_step_id"] = next_step.id
                status = CompletionStatus.IN_PROGRESS
            else:
                # Tutorial completed
                progress_data["current_step_id"] = None
                progress_data["status"] = CompletionStatus.COMPLETED.value
                progress_data["completed_at"] = completed_at.isoformat()
                status = CompletionStatus.COMPLETED
            
            # Calculate completion percentage
            completion_percentage = (len(progress_data["completed_steps"]) / len(tutorial.steps)) * 100
            
            # Save updated progress
            self.storage.save_progress(user_id, tutorial_id, progress_data)
            
            return ProgressResult(
                success=True,
                tutorial_id=tutorial_id,
                current_step_id=progress_data["current_step_id"],
                completion_percentage=completion_percentage,
                status=status,
                completed_steps=progress_data["completed_steps"],
                last_activity_at=completed_at
            )
            
        except Exception as e:
            return ProgressResult(
                success=False,
                error_message=f"Failed to complete step: {str(e)}"
            )
    
    def get_progress(self, user_id: str, tutorial_id: str) -> ProgressResult:
        """Get current tutorial progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            Current progress result
        """
        try:
            progress_data = self.storage.load_progress(user_id, tutorial_id)
            if not progress_data:
                return ProgressResult(
                    success=False,
                    error_message="No progress found"
                )
            
            return self._progress_data_to_result(progress_data)
            
        except Exception as e:
            return ProgressResult(
                success=False,
                error_message=f"Failed to get progress: {str(e)}"
            )
    
    def save_progress(self, user_id: str, tutorial_id: str) -> ProgressResult:
        """Explicitly save current progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            Save operation result
        """
        try:
            progress_data = self.storage.load_progress(user_id, tutorial_id)
            if not progress_data:
                return ProgressResult(
                    success=False,
                    error_message="No progress to save"
                )
            
            # Update last activity
            progress_data["last_activity_at"] = datetime.now(timezone.utc).isoformat()
            
            success = self.storage.save_progress(user_id, tutorial_id, progress_data)
            
            return ProgressResult(
                success=success,
                tutorial_id=tutorial_id,
                error_message="Failed to save progress" if not success else None
            )
            
        except Exception as e:
            return ProgressResult(
                success=False,
                error_message=f"Failed to save progress: {str(e)}"
            )
    
    def load_progress(self, user_id: str, tutorial_id: str) -> ProgressResult:
        """Load saved tutorial progress.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            Loaded progress result
        """
        return self.get_progress(user_id, tutorial_id)
    
    def reset_tutorial(self, user_id: str, tutorial_id: str) -> ProgressResult:
        """Reset tutorial progress for a user.
        
        Args:
            user_id: User identifier
            tutorial_id: Tutorial identifier
            
        Returns:
            Reset operation result
        """
        try:
            success = self.storage.delete_progress(user_id, tutorial_id)
            
            return ProgressResult(
                success=success,
                tutorial_id=tutorial_id,
                error_message="Failed to reset progress" if not success else None
            )
            
        except Exception as e:
            return ProgressResult(
                success=False,
                error_message=f"Failed to reset tutorial: {str(e)}"
            )
    
    def get_user_tutorials(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all tutorials for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of tutorial progress summaries
        """
        try:
            tutorial_ids = self.storage.list_user_tutorials(user_id)
            tutorials = []
            
            for tutorial_id in tutorial_ids:
                progress = self.get_progress(user_id, tutorial_id)
                if progress.success:
                    tutorial_data = self._tutorials.get(tutorial_id, {})
                    tutorials.append({
                        "tutorial_id": tutorial_id,
                        "title": getattr(tutorial_data, 'title', tutorial_id),
                        "status": progress.status.value,
                        "completion_percentage": progress.completion_percentage,
                        "last_activity": progress.last_activity_at
                    })
            
            return tutorials
            
        except Exception:
            return []
    
    def _load_existing_progress(
        self, 
        user_id: str, 
        tutorial_id: str, 
        progress_data: Dict[str, Any]
    ) -> ProgressResult:
        """Load existing progress data."""
        return self._progress_data_to_result(progress_data)
    
    def _progress_data_to_result(self, progress_data: Dict[str, Any]) -> ProgressResult:
        """Convert progress data to result object."""
        # Parse timestamps
        started_at = None
        last_activity_at = None
        
        if "started_at" in progress_data:
            started_at = datetime.fromisoformat(progress_data["started_at"].replace('Z', '+00:00'))
        
        if "last_activity_at" in progress_data:
            last_activity_at = datetime.fromisoformat(progress_data["last_activity_at"].replace('Z', '+00:00'))
        
        # Calculate completion percentage
        tutorial = self._tutorials.get(progress_data["tutorial_id"])
        total_steps = len(tutorial.steps) if tutorial else 1
        completed_steps = len(progress_data.get("completed_steps", []))
        completion_percentage = (completed_steps / total_steps) * 100
        
        # Calculate time spent
        time_spent = 0
        if "step_completions" in progress_data:
            time_spent = sum(
                comp.get("time_spent_seconds", 0) 
                for comp in progress_data["step_completions"]
            )
        
        # Calculate average step time
        avg_step_time = time_spent / max(completed_steps, 1)
        
        return ProgressResult(
            success=True,
            tutorial_id=progress_data["tutorial_id"],
            current_step_id=progress_data.get("current_step_id"),
            completion_percentage=completion_percentage,
            status=CompletionStatus(progress_data.get("status", "not_started")),
            completed_steps=progress_data.get("completed_steps", []),
            time_spent_seconds=time_spent,
            started_at=started_at,
            last_activity_at=last_activity_at,
            average_step_time_seconds=avg_step_time
        )
    
    def _calculate_step_time(self, progress_data: Dict[str, Any], step_id: str) -> float:
        """Calculate time spent on a step."""
        # This is a simplified implementation
        # In a real implementation, you'd track step start times
        return 30.0  # Default 30 seconds per step