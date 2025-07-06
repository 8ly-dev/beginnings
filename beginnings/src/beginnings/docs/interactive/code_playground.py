"""Code playground for interactive documentation.

This module provides a secure code execution environment for documentation
examples and tutorials. Follows Single Responsibility Principle and security best practices.
"""

from __future__ import annotations

import ast
import sys
import time
import subprocess
import tempfile
import uuid
import shutil
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from pathlib import Path


class ExecutionStatus(Enum):
    """Code execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"


@dataclass
class ExecutionContext:
    """Configuration for code execution environment."""
    
    timeout_seconds: int = 30
    memory_limit_mb: int = 128
    allowed_imports: List[str] = field(default_factory=lambda: [
        'beginnings', 'json', 're', 'datetime', 'uuid', 'pathlib'
    ])
    forbidden_functions: List[str] = field(default_factory=lambda: [
        'eval', 'exec', 'open', '__import__', 'compile', 'globals', 'locals',
        'getattr', 'setattr', 'delattr', 'hasattr'
    ])
    allowed_builtins: List[str] = field(default_factory=lambda: [
        'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple',
        'set', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'sum',
        'min', 'max', 'abs', 'round', 'type', 'isinstance'
    ])
    enable_file_operations: bool = False
    enable_network_access: bool = False


@dataclass
class ValidationResult:
    """Result of code validation."""
    
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PlaygroundResult:
    """Result of code execution in playground."""
    
    success: bool
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0
    memory_used_mb: float = 0
    error_message: str = ""
    security_violations: List[str] = field(default_factory=list)


class SecurityValidator:
    """Validates code for security issues before execution.
    
    Follows Single Responsibility Principle - only handles security validation.
    """
    
    def __init__(self, context: ExecutionContext):
        """Initialize security validator with execution context."""
        self.context = context
        self.forbidden_patterns = [
            # File system access
            r'open\s*\(',
            r'file\s*\(',
            r'__file__',
            r'__name__',
            # System access
            r'os\.',
            r'subprocess\.',
            r'system\s*\(',
            # Network access
            r'socket\.',
            r'urllib\.',
            r'requests\.',
            r'http\.',
            # Dangerous builtins
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            # Import manipulation
            r'__import__\s*\(',
            r'importlib\.',
            # Reflection
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'globals\s*\(',
            r'locals\s*\(',
        ]
    
    def validate_code(self, code: str) -> ValidationResult:
        """Validate code for security issues.
        
        Args:
            code: Python code to validate
            
        Returns:
            Validation result with security violations
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Parse AST to check for dangerous constructs
            tree = ast.parse(code)
            violations = self._check_ast_security(tree)
            
            if violations:
                result.is_valid = False
                result.errors.extend(violations)
            
            # Check for forbidden patterns in source
            import re
            for pattern in self.forbidden_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    result.is_valid = False
                    result.errors.append(f"Forbidden pattern detected: {pattern}")
            
            # Validate imports
            import_violations = self._validate_imports(tree)
            if import_violations:
                result.is_valid = False
                result.errors.extend(import_violations)
            
        except SyntaxError as e:
            result.is_valid = False
            result.errors.append(f"Syntax error: {e.msg}")
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation error: {str(e)}")
        
        return result
    
    def _check_ast_security(self, tree: ast.AST) -> List[str]:
        """Check AST for security violations."""
        violations = []
        
        for node in ast.walk(tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.context.forbidden_functions:
                        violations.append(f"Forbidden function call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    # Check for dangerous method calls
                    if hasattr(node.func, 'attr'):
                        if node.func.attr in ['system', 'popen', 'spawn']:
                            violations.append(f"Forbidden method call: {node.func.attr}")
            
            # Check for dangerous imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.context.allowed_imports:
                        violations.append(f"Forbidden import: {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in self.context.allowed_imports:
                    violations.append(f"Forbidden import from: {node.module}")
        
        return violations
    
    def _validate_imports(self, tree: ast.AST) -> List[str]:
        """Validate import statements."""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._is_import_allowed(alias.name):
                        violations.append(f"Import not allowed: {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module and not self._is_import_allowed(node.module):
                    violations.append(f"Import from not allowed: {node.module}")
        
        return violations
    
    def _is_import_allowed(self, module_name: str) -> bool:
        """Check if module import is allowed."""
        # Check exact matches
        if module_name in self.context.allowed_imports:
            return True
        
        # Check if it's a submodule of an allowed import
        for allowed in self.context.allowed_imports:
            if module_name.startswith(f"{allowed}."):
                return True
        
        return False


class SandboxExecutor:
    """Executes code in a sandboxed environment.
    
    Follows Single Responsibility Principle - only handles code execution.
    """
    
    def __init__(self, context: ExecutionContext):
        """Initialize sandbox executor."""
        self.context = context
    
    def execute_code(self, code: str) -> PlaygroundResult:
        """Execute code in sandbox with security restrictions.
        
        Args:
            code: Python code to execute
            
        Returns:
            Execution result with output and metrics
        """
        start_time = time.time()
        
        try:
            # Create temporary execution environment
            with tempfile.TemporaryDirectory() as temp_dir:
                result = self._execute_in_subprocess(code, temp_dir)
                
                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000
                result.execution_time_ms = execution_time
                
                return result
                
        except Exception as e:
            return PlaygroundResult(
                success=False,
                status=ExecutionStatus.ERROR,
                error_message=f"Execution failed: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _execute_in_subprocess(self, code: str, temp_dir: str) -> PlaygroundResult:
        """Execute code in subprocess for isolation."""
        # Create execution script
        script_path = Path(temp_dir) / "exec_script.py"
        
        # Prepare restricted execution environment
        restricted_code = self._create_restricted_environment(code)
        script_path.write_text(restricted_code)
        
        try:
            # Execute with timeout and resource limits
            result = subprocess.run(
                [sys.executable, str(script_path)],
                timeout=self.context.timeout_seconds,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            return PlaygroundResult(
                success=result.returncode == 0,
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.ERROR,
                stdout=result.stdout,
                stderr=result.stderr,
                error_message=result.stderr if result.returncode != 0 else ""
            )
            
        except subprocess.TimeoutExpired:
            return PlaygroundResult(
                success=False,
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Code execution timed out after {self.context.timeout_seconds} seconds"
            )
    
    def _create_restricted_environment(self, user_code: str) -> str:
        """Create restricted execution environment."""
        # Prepare allowed builtins
        allowed_builtins = {name: __builtins__[name] for name in self.context.allowed_builtins 
                           if name in __builtins__}
        
        # Create execution wrapper
        wrapper_code = f"""
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Restrict builtins
__builtins__ = {allowed_builtins!r}

# Capture output
stdout_capture = io.StringIO()
stderr_capture = io.StringIO()

try:
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        # User code execution
{self._indent_code(user_code, 8)}
    
    print(stdout_capture.getvalue(), end='')
    if stderr_capture.getvalue():
        print(stderr_capture.getvalue(), file=sys.stderr, end='')

except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
        return wrapper_code
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces."""
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)


class CodePlayground:
    """Interactive code playground for documentation.
    
    Follows Single Responsibility Principle - orchestrates code validation and execution.
    Uses Dependency Inversion - depends on abstractions for validation and execution.
    """
    
    def __init__(self, context: Optional[ExecutionContext] = None):
        """Initialize code playground.
        
        Args:
            context: Execution context configuration
        """
        self.context = context or ExecutionContext()
        self.security_validator = SecurityValidator(self.context)
        self.sandbox_executor = SandboxExecutor(self.context)
        self._execution_history = []
    
    def validate_code(self, code: str) -> ValidationResult:
        """Validate code syntax and security.
        
        Args:
            code: Python code to validate
            
        Returns:
            Validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Check syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.is_valid = False
            result.errors.append(f"Syntax error on line {e.lineno}: {e.msg}")
            return result
        
        # Security validation
        security_result = self.security_validator.validate_code(code)
        if not security_result.is_valid:
            result.is_valid = False
            result.errors.extend(security_result.errors)
        
        result.warnings.extend(security_result.warnings)
        result.suggestions.extend(security_result.suggestions)
        
        return result
    
    def execute_code(self, code: str, context: Optional[ExecutionContext] = None) -> PlaygroundResult:
        """Execute code in secure sandbox.
        
        Args:
            code: Python code to execute
            context: Optional execution context override
            
        Returns:
            Execution result
        """
        execution_context = context or self.context
        
        # Validate code first
        validation = self.validate_code(code)
        if not validation.is_valid:
            return PlaygroundResult(
                success=False,
                status=ExecutionStatus.SECURITY_VIOLATION,
                error_message="Code validation failed: " + "; ".join(validation.errors),
                security_violations=validation.errors
            )
        
        # Execute code
        result = self.sandbox_executor.execute_code(code)
        
        # Store in execution history
        self._execution_history.append({
            "timestamp": time.time(),
            "code": code,
            "result": result,
            "context": execution_context
        })
        
        # Limit history size
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
        
        return result
    
    def create_sandbox(self) -> str:
        """Create isolated sandbox environment.
        
        Returns:
            Sandbox identifier for session isolation
        """
        sandbox_id = str(uuid.uuid4())
        
        # In a full implementation, this would create an isolated container
        # or virtual environment. For now, we return a unique identifier.
        
        return sandbox_id
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history.
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        return self._execution_history[-limit:]
    
    def clear_execution_history(self) -> None:
        """Clear execution history."""
        self._execution_history.clear()
    
    def get_allowed_imports(self) -> List[str]:
        """Get list of allowed imports for user reference.
        
        Returns:
            List of allowed module names
        """
        return self.context.allowed_imports.copy()
    
    def update_context(self, **kwargs) -> None:
        """Update execution context configuration.
        
        Args:
            **kwargs: Context parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        
        # Recreate validators with new context
        self.security_validator = SecurityValidator(self.context)
        self.sandbox_executor = SandboxExecutor(self.context)