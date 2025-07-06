"""Universal migration framework for converting web frameworks to Beginnings.

This module provides a comprehensive migration system that can convert Flask,
Django, and FastAPI applications to the Beginnings framework. Follows SOLID principles.
"""

from __future__ import annotations

import json
import shutil
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Protocol
from enum import Enum


class MigrationStatus(Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class FrameworkType(Enum):
    """Supported framework types."""
    FLASK = "flask"
    DJANGO = "django"
    FASTAPI = "fastapi"
    BEGINNINGS = "beginnings"
    UNKNOWN = "unknown"


@dataclass
class MigrationConfig:
    """Configuration for migration process."""
    
    source_framework: str
    target_framework: str = "beginnings"
    source_directory: Path = field(default_factory=Path)
    target_directory: Path = field(default_factory=Path)
    preserve_structure: bool = True
    backup_original: bool = True
    migration_strategy: str = "incremental"  # full, incremental, selective
    custom_mappings: Dict[str, str] = field(default_factory=dict)
    exclude_patterns: List[str] = field(default_factory=list)
    include_tests: bool = True
    generate_docs: bool = True
    validate_after_migration: bool = True
    parallel_processing: bool = False
    max_workers: int = 4


@dataclass
class MigrationStep:
    """Individual migration step."""
    
    id: str
    name: str
    description: str
    type: str  # dependencies, routes, models, config, tests, docs
    dependencies: List[str] = field(default_factory=list)
    estimated_time_minutes: int = 5
    priority: int = 1  # 1 = high, 5 = low
    automated: bool = True
    validation_criteria: List[str] = field(default_factory=list)


@dataclass
class MigrationResult:
    """Result of migration operation."""
    
    success: bool
    status: MigrationStatus
    migration_time_seconds: float = 0
    migrated_files: List[Path] = field(default_factory=list)
    created_files: List[Path] = field(default_factory=list)
    skipped_files: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    migration_report: Dict[str, Any] = field(default_factory=dict)
    backup_location: Optional[Path] = None


@dataclass
class ValidationResult:
    """Result of migration validation."""
    
    is_compatible: bool
    is_valid: bool = True
    detected_framework: str = ""
    compatibility_score: float = 0.0
    compatibility_issues: List[str] = field(default_factory=list)
    migration_suggestions: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    validated_files: List[Path] = field(default_factory=list)
    detected_features: List[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0


class MigrationAnalyzer(Protocol):
    """Protocol for migration analysis components."""
    
    def analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure and patterns."""
        ...
    
    def detect_framework(self, project_path: Path) -> FrameworkType:
        """Detect the framework used in the project."""
        ...
    
    def assess_complexity(self, project_path: Path) -> Dict[str, Any]:
        """Assess migration complexity."""
        ...


class MigrationConverter(Protocol):
    """Protocol for migration conversion components."""
    
    def convert_project(self, source_path: Path, target_path: Path, config: MigrationConfig) -> MigrationResult:
        """Convert entire project."""
        ...
    
    def convert_file(self, source_file: Path, target_file: Path) -> bool:
        """Convert individual file."""
        ...
    
    def supports_framework(self, framework: FrameworkType) -> bool:
        """Check if converter supports framework."""
        ...


class MigrationValidator(Protocol):
    """Protocol for migration validation components."""
    
    def validate_syntax(self, code: str) -> ValidationResult:
        """Validate code syntax."""
        ...
    
    def validate_imports(self, code: str) -> ValidationResult:
        """Validate import statements."""
        ...
    
    def validate_structure(self, project_path: Path) -> ValidationResult:
        """Validate project structure."""
        ...
    
    def validate_functionality(self, project_path: Path) -> ValidationResult:
        """Validate functional correctness."""
        ...


class ProjectAnalyzer:
    """Analyzes project structure and framework patterns.
    
    Follows Single Responsibility Principle - only handles project analysis.
    """
    
    def __init__(self):
        """Initialize project analyzer."""
        self.logger = logging.getLogger(__name__)
        self.framework_indicators = {
            FrameworkType.FLASK: {
                "files": ["app.py", "wsgi.py"],
                "imports": ["flask", "Flask"],
                "patterns": [r"@app\.route", r"Flask\(__name__\)"]
            },
            FrameworkType.DJANGO: {
                "files": ["manage.py", "settings.py", "urls.py"],
                "imports": ["django", "Django"],
                "patterns": [r"from django", r"INSTALLED_APPS", r"urlpatterns"]
            },
            FrameworkType.FASTAPI: {
                "files": ["main.py"],
                "imports": ["fastapi", "FastAPI"],
                "patterns": [r"@app\.(get|post|put|delete)", r"FastAPI\("]
            }
        }
    
    def analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure and patterns.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Analysis results with project metadata
        """
        analysis = {
            "framework": self.detect_framework(project_path),
            "structure": self._analyze_structure(project_path),
            "dependencies": self._analyze_dependencies(project_path),
            "patterns": self._analyze_patterns(project_path),
            "complexity": self.assess_complexity(project_path),
            "size_metrics": self._calculate_size_metrics(project_path)
        }
        
        return analysis
    
    def detect_framework(self, project_path: Path) -> FrameworkType:
        """Detect the framework used in the project.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Detected framework type
        """
        scores = {framework: 0 for framework in FrameworkType}
        
        # Check for framework-specific files
        for framework, indicators in self.framework_indicators.items():
            for filename in indicators["files"]:
                if (project_path / filename).exists():
                    scores[framework] += 3
        
        # Check for framework-specific imports and patterns
        python_files = list(project_path.rglob("*.py"))
        for py_file in python_files[:20]:  # Limit to first 20 files for performance
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for framework, indicators in self.framework_indicators.items():
                    # Check imports
                    for import_name in indicators["imports"]:
                        if import_name in content:
                            scores[framework] += 2
                    
                    # Check patterns
                    import re
                    for pattern in indicators["patterns"]:
                        if re.search(pattern, content):
                            scores[framework] += 1
            except Exception:
                continue
        
        # Return framework with highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return FrameworkType.UNKNOWN
    
    def assess_complexity(self, project_path: Path) -> Dict[str, Any]:
        """Assess migration complexity.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Complexity assessment
        """
        complexity = {
            "overall_score": 0,  # 1-10 scale
            "factors": {},
            "estimated_hours": 0,
            "risk_level": "low"  # low, medium, high
        }
        
        # Count Python files
        python_files = list(project_path.rglob("*.py"))
        file_count = len(python_files)
        
        # Calculate lines of code
        total_lines = 0
        for py_file in python_files:
            try:
                lines = len(py_file.read_text(encoding='utf-8').splitlines())
                total_lines += lines
            except Exception:
                continue
        
        # Assess based on project size
        if file_count <= 10 and total_lines <= 1000:
            complexity["overall_score"] = 2
            complexity["estimated_hours"] = 4
            complexity["risk_level"] = "low"
        elif file_count <= 50 and total_lines <= 10000:
            complexity["overall_score"] = 5
            complexity["estimated_hours"] = 16
            complexity["risk_level"] = "medium"
        else:
            complexity["overall_score"] = 8
            complexity["estimated_hours"] = 40
            complexity["risk_level"] = "high"
        
        complexity["factors"] = {
            "file_count": file_count,
            "lines_of_code": total_lines,
            "dependencies": self._count_dependencies(project_path),
            "custom_patterns": self._count_custom_patterns(project_path)
        }
        
        return complexity
    
    def _analyze_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project directory structure."""
        structure = {
            "directories": [],
            "python_files": [],
            "config_files": [],
            "template_files": [],
            "static_files": [],
            "test_files": []
        }
        
        for item in project_path.rglob("*"):
            if item.is_dir():
                structure["directories"].append(str(item.relative_to(project_path)))
            elif item.suffix == ".py":
                structure["python_files"].append(str(item.relative_to(project_path)))
            elif item.name in ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"]:
                structure["config_files"].append(str(item.relative_to(project_path)))
            elif item.suffix in [".html", ".jinja2", ".j2"]:
                structure["template_files"].append(str(item.relative_to(project_path)))
            elif item.suffix in [".css", ".js", ".png", ".jpg", ".gif"]:
                structure["static_files"].append(str(item.relative_to(project_path)))
            elif "test" in str(item) and item.suffix == ".py":
                structure["test_files"].append(str(item.relative_to(project_path)))
        
        return structure
    
    def _analyze_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project dependencies."""
        dependencies = {
            "requirements": [],
            "framework_specific": [],
            "third_party": []
        }
        
        # Check requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]
                dependencies["requirements"] = lines
            except Exception:
                pass
        
        # Check for framework-specific dependencies
        all_reqs = ' '.join(dependencies["requirements"])
        if "flask" in all_reqs.lower():
            dependencies["framework_specific"].extend(["Flask", "Flask-*"])
        if "django" in all_reqs.lower():
            dependencies["framework_specific"].extend(["Django", "django-*"])
        if "fastapi" in all_reqs.lower():
            dependencies["framework_specific"].extend(["FastAPI", "uvicorn", "pydantic"])
        
        return dependencies
    
    def _analyze_patterns(self, project_path: Path) -> Dict[str, Any]:
        """Analyze code patterns in the project."""
        patterns = {
            "routing_patterns": [],
            "model_patterns": [],
            "middleware_patterns": [],
            "template_patterns": []
        }
        
        python_files = list(project_path.rglob("*.py"))[:10]  # Limit for performance
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Detect routing patterns
                import re
                if re.search(r"@app\.route", content):
                    patterns["routing_patterns"].append("flask_routes")
                if re.search(r"@app\.(get|post|put|delete)", content):
                    patterns["routing_patterns"].append("fastapi_routes")
                if re.search(r"urlpatterns", content):
                    patterns["routing_patterns"].append("django_urls")
                
                # Detect model patterns
                if re.search(r"class.*\(db\.Model\)", content):
                    patterns["model_patterns"].append("sqlalchemy_models")
                if re.search(r"class.*\(models\.Model\)", content):
                    patterns["model_patterns"].append("django_models")
                if re.search(r"class.*\(BaseModel\)", content):
                    patterns["model_patterns"].append("pydantic_models")
                
            except Exception:
                continue
        
        return patterns
    
    def _calculate_size_metrics(self, project_path: Path) -> Dict[str, Any]:
        """Calculate project size metrics."""
        metrics = {
            "total_files": 0,
            "python_files": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0
        }
        
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                metrics["total_files"] += 1
                
                if file_path.suffix == ".py":
                    metrics["python_files"] += 1
                    
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        lines = content.splitlines()
                        metrics["total_lines"] += len(lines)
                        
                        for line in lines:
                            stripped = line.strip()
                            if not stripped:
                                metrics["blank_lines"] += 1
                            elif stripped.startswith('#'):
                                metrics["comment_lines"] += 1
                            else:
                                metrics["code_lines"] += 1
                    except Exception:
                        continue
        
        return metrics
    
    def _count_dependencies(self, project_path: Path) -> int:
        """Count number of dependencies."""
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() 
                        if line.strip() and not line.startswith('#') and not line.startswith('-')]
                return len(lines)
            except Exception:
                pass
        return 0
    
    def _count_custom_patterns(self, project_path: Path) -> int:
        """Count custom patterns that might complicate migration."""
        # This is a simplified implementation
        # In practice, you'd look for custom decorators, metaclasses, etc.
        return 0


class MigrationPlanner:
    """Plans migration steps and strategy.
    
    Follows Single Responsibility Principle - only handles migration planning.
    """
    
    def __init__(self):
        """Initialize migration planner."""
        self.logger = logging.getLogger(__name__)
    
    def generate_migration_plan(self, config: MigrationConfig, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed migration plan.
        
        Args:
            config: Migration configuration
            analysis: Project analysis results
            
        Returns:
            Detailed migration plan
        """
        framework = analysis.get("framework", FrameworkType.UNKNOWN)
        complexity = analysis.get("complexity", {})
        
        plan = {
            "steps": self._generate_migration_steps(framework, analysis),
            "estimated_time": complexity.get("estimated_hours", 8),
            "dependencies": self._identify_dependencies(analysis),
            "risks": self._assess_risks(framework, complexity),
            "strategy": config.migration_strategy,
            "validation_points": self._define_validation_points(),
            "rollback_plan": self._create_rollback_plan(config)
        }
        
        return plan
    
    def _generate_migration_steps(self, framework: FrameworkType, analysis: Dict[str, Any]) -> List[MigrationStep]:
        """Generate ordered migration steps."""
        steps = []
        
        # Step 1: Backup and preparation
        steps.append(MigrationStep(
            id="backup",
            name="Backup Original Project",
            description="Create backup of original project before migration",
            type="preparation",
            estimated_time_minutes=2,
            priority=1,
            automated=True
        ))
        
        # Step 2: Dependency analysis and migration
        steps.append(MigrationStep(
            id="dependencies",
            name="Migrate Dependencies",
            description="Convert requirements.txt and dependencies to Beginnings equivalents",
            type="dependencies",
            dependencies=["backup"],
            estimated_time_minutes=10,
            priority=1,
            automated=True
        ))
        
        # Step 3: Configuration migration
        steps.append(MigrationStep(
            id="config",
            name="Migrate Configuration",
            description="Convert framework-specific configuration to Beginnings format",
            type="config",
            dependencies=["dependencies"],
            estimated_time_minutes=15,
            priority=1,
            automated=True
        ))
        
        # Step 4: Model migration (if applicable)
        if analysis.get("patterns", {}).get("model_patterns"):
            steps.append(MigrationStep(
                id="models",
                name="Migrate Models",
                description="Convert ORM models to Beginnings database models",
                type="models",
                dependencies=["config"],
                estimated_time_minutes=30,
                priority=2,
                automated=True
            ))
        
        # Step 5: Route migration
        steps.append(MigrationStep(
            id="routes",
            name="Migrate Routes",
            description="Convert framework-specific routing to Beginnings routes",
            type="routes",
            dependencies=["models"] if "models" in [s.id for s in steps] else ["config"],
            estimated_time_minutes=45,
            priority=2,
            automated=True
        ))
        
        # Step 6: Middleware and extensions
        steps.append(MigrationStep(
            id="middleware",
            name="Migrate Middleware",
            description="Convert middleware and extensions to Beginnings equivalents",
            type="middleware",
            dependencies=["routes"],
            estimated_time_minutes=20,
            priority=3,
            automated=True
        ))
        
        # Step 7: Template migration (if applicable)
        if analysis.get("structure", {}).get("template_files"):
            steps.append(MigrationStep(
                id="templates",
                name="Migrate Templates",
                description="Convert templates to Beginnings template format",
                type="templates",
                dependencies=["middleware"],
                estimated_time_minutes=25,
                priority=3,
                automated=False  # May require manual review
            ))
        
        # Step 8: Test migration
        if analysis.get("structure", {}).get("test_files"):
            steps.append(MigrationStep(
                id="tests",
                name="Migrate Tests",
                description="Convert test files to work with Beginnings",
                type="tests",
                dependencies=["templates"] if "templates" in [s.id for s in steps] else ["middleware"],
                estimated_time_minutes=30,
                priority=4,
                automated=False
            ))
        
        # Step 9: Validation
        steps.append(MigrationStep(
            id="validation",
            name="Validate Migration",
            description="Run comprehensive validation of migrated project",
            type="validation",
            dependencies=[steps[-1].id],  # Depends on last step
            estimated_time_minutes=10,
            priority=1,
            automated=True
        ))
        
        return steps
    
    def _identify_dependencies(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify migration dependencies."""
        dependencies = []
        
        # Framework-specific dependencies
        framework = analysis.get("framework")
        if framework == FrameworkType.FLASK:
            dependencies.extend(["Flask", "Werkzeug", "Jinja2"])
        elif framework == FrameworkType.DJANGO:
            dependencies.extend(["Django", "django-*"])
        elif framework == FrameworkType.FASTAPI:
            dependencies.extend(["FastAPI", "Pydantic", "Uvicorn"])
        
        # Add project-specific dependencies
        project_deps = analysis.get("dependencies", {}).get("requirements", [])
        dependencies.extend(project_deps[:10])  # Limit to first 10
        
        return dependencies
    
    def _assess_risks(self, framework: FrameworkType, complexity: Dict[str, Any]) -> List[str]:
        """Assess migration risks."""
        risks = []
        
        risk_level = complexity.get("risk_level", "low")
        if risk_level == "high":
            risks.append("Large codebase may require significant manual review")
            risks.append("Complex patterns may not convert automatically")
        
        if framework == FrameworkType.UNKNOWN:
            risks.append("Unknown framework - manual conversion required")
        
        file_count = complexity.get("factors", {}).get("file_count", 0)
        if file_count > 100:
            risks.append("Many files to convert - potential for errors")
        
        return risks
    
    def _define_validation_points(self) -> List[str]:
        """Define validation checkpoints."""
        return [
            "Syntax validation after each step",
            "Import validation after dependency migration",
            "Route functionality validation",
            "Model integrity validation",
            "Overall application validation"
        ]
    
    def _create_rollback_plan(self, config: MigrationConfig) -> Dict[str, Any]:
        """Create rollback plan in case of migration failure."""
        return {
            "backup_location": str(config.target_directory.parent / f"{config.source_directory.name}_backup"),
            "rollback_steps": [
                "Stop migration process",
                "Restore from backup",
                "Review migration logs",
                "Address issues and retry"
            ],
            "recovery_time_minutes": 5
        }


class MigrationFramework:
    """Universal migration framework for web applications.
    
    Follows Single Responsibility Principle - orchestrates migration process.
    Uses Dependency Inversion - depends on analyzer, planner, and converter abstractions.
    """
    
    def __init__(self):
        """Initialize migration framework."""
        self.logger = logging.getLogger(__name__)
        self.analyzer = ProjectAnalyzer()
        self.planner = MigrationPlanner()
        self.converters = {}  # Will be populated with framework-specific converters
        self.validators = {}  # Will be populated with validators
    
    def register_converter(self, framework: FrameworkType, converter: MigrationConverter) -> None:
        """Register framework-specific converter.
        
        Args:
            framework: Framework type
            converter: Converter implementation
        """
        self.converters[framework] = converter
    
    def register_validator(self, name: str, validator: MigrationValidator) -> None:
        """Register validator.
        
        Args:
            name: Validator name
            validator: Validator implementation
        """
        self.validators[name] = validator
    
    def analyze_compatibility(self, config: MigrationConfig) -> ValidationResult:
        """Analyze project compatibility for migration.
        
        Args:
            config: Migration configuration
            
        Returns:
            Compatibility analysis result
        """
        try:
            analysis = self.analyzer.analyze_project(config.source_directory)
            framework = analysis["framework"]
            complexity = analysis["complexity"]
            
            # Check if we have a converter for this framework
            is_compatible = framework in self.converters or framework != FrameworkType.UNKNOWN
            
            compatibility_score = 1.0
            issues = []
            suggestions = []
            
            if framework == FrameworkType.UNKNOWN:
                compatibility_score = 0.0
                issues.append("Unknown framework - cannot determine migration path")
                suggestions.append("Manual review required to identify framework")
            elif framework not in self.converters:
                compatibility_score = 0.3
                issues.append(f"No specific converter available for {framework.value}")
                suggestions.append("Generic conversion may be possible with manual review")
            else:
                # Adjust score based on complexity
                risk_level = complexity.get("risk_level", "low")
                if risk_level == "high":
                    compatibility_score = 0.7
                    issues.append("High complexity project may require manual intervention")
                elif risk_level == "medium":
                    compatibility_score = 0.85
            
            return ValidationResult(
                is_compatible=is_compatible,
                detected_framework=framework.value,
                compatibility_score=compatibility_score,
                compatibility_issues=issues,
                migration_suggestions=suggestions,
                estimated_effort_hours=complexity.get("estimated_hours", 0)
            )
            
        except Exception as e:
            self.logger.error(f"Compatibility analysis failed: {e}")
            return ValidationResult(
                is_compatible=False,
                compatibility_issues=[f"Analysis failed: {str(e)}"]
            )
    
    def generate_migration_plan(self, config: MigrationConfig) -> Dict[str, Any]:
        """Generate detailed migration plan.
        
        Args:
            config: Migration configuration
            
        Returns:
            Migration plan with steps and estimates
        """
        try:
            analysis = self.analyzer.analyze_project(config.source_directory)
            plan = self.planner.generate_migration_plan(config, analysis)
            
            # Add framework-specific adjustments
            framework = analysis["framework"]
            if framework in self.converters:
                converter = self.converters[framework]
                # Allow converter to adjust the plan
                if hasattr(converter, 'adjust_migration_plan'):
                    plan = converter.adjust_migration_plan(plan, analysis)
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Migration planning failed: {e}")
            return {
                "steps": [],
                "estimated_time": 0,
                "error": str(e)
            }
    
    def migrate_project(self, config: MigrationConfig) -> MigrationResult:
        """Execute complete project migration.
        
        Args:
            config: Migration configuration
            
        Returns:
            Migration result with status and details
        """
        import time
        start_time = time.time()
        
        result = MigrationResult(
            success=False,
            status=MigrationStatus.IN_PROGRESS
        )
        
        try:
            # Step 1: Analyze project
            self.logger.info(f"Starting migration from {config.source_directory} to {config.target_directory}")
            analysis = self.analyzer.analyze_project(config.source_directory)
            framework = analysis["framework"]
            
            # Step 2: Check compatibility
            compatibility = self.analyze_compatibility(config)
            if not compatibility.is_compatible:
                result.status = MigrationStatus.FAILED
                result.errors.extend(compatibility.compatibility_issues)
                return result
            
            # Step 3: Create backup if requested
            if config.backup_original:
                backup_location = self._create_backup(config.source_directory)
                result.backup_location = backup_location
            
            # Step 4: Prepare target directory
            config.target_directory.mkdir(parents=True, exist_ok=True)
            
            # Step 5: Execute migration
            if framework in self.converters:
                converter = self.converters[framework]
                conversion_result = converter.convert_project(
                    config.source_directory, 
                    config.target_directory, 
                    config
                )
                
                result.migrated_files.extend(conversion_result.migrated_files)
                result.created_files.extend(conversion_result.created_files)
                result.errors.extend(conversion_result.errors)
                result.warnings.extend(conversion_result.warnings)
                
                if not conversion_result.success:
                    result.status = MigrationStatus.PARTIAL if result.migrated_files else MigrationStatus.FAILED
                    return result
            else:
                result.status = MigrationStatus.FAILED
                result.errors.append(f"No converter available for {framework.value}")
                return result
            
            # Step 6: Validate migration if requested
            if config.validate_after_migration:
                validation_result = self.validate_migration(config)
                if not validation_result.is_valid:
                    result.warnings.extend(validation_result.warnings)
                    result.warnings.append("Migration validation found issues")
            
            # Step 7: Generate migration report
            result.migration_report = self._generate_migration_report(analysis, result)
            
            result.success = True
            result.status = MigrationStatus.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Migration failed: {str(e)}")
        
        finally:
            result.migration_time_seconds = time.time() - start_time
        
        return result
    
    def validate_migration(self, config: MigrationConfig) -> ValidationResult:
        """Validate migrated project.
        
        Args:
            config: Migration configuration
            
        Returns:
            Validation result
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Basic validation using registered validators
            for validator_name, validator in self.validators.items():
                if hasattr(validator, 'validate_structure'):
                    validation = validator.validate_structure(config.target_directory)
                    if not validation.is_valid:
                        result.is_valid = False
                        result.validation_errors.extend(validation.validation_errors)
                    result.warnings.extend(validation.warnings)
            
            # Check that main files exist
            main_files = ["app.py", "main.py", "__init__.py"]
            has_main_file = any((config.target_directory / f).exists() for f in main_files)
            if not has_main_file:
                result.is_valid = False
                result.validation_errors.append("No main application file found")
            
            # Check for beginnings imports
            python_files = list(config.target_directory.rglob("*.py"))
            has_beginnings_imports = False
            for py_file in python_files[:5]:  # Check first 5 files
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if "beginnings" in content:
                        has_beginnings_imports = True
                        break
                except Exception:
                    continue
            
            if not has_beginnings_imports:
                result.warnings.append("No Beginnings imports found - migration may be incomplete")
            
            result.validated_files = python_files
            result.detected_features = ["migration_completed"]
            
        except Exception as e:
            result.is_valid = False
            result.validation_errors.append(f"Validation failed: {str(e)}")
        
        return result
    
    def _create_backup(self, source_directory: Path) -> Path:
        """Create backup of source directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_directory.name}_backup_{timestamp}"
        backup_path = source_directory.parent / backup_name
        
        shutil.copytree(source_directory, backup_path)
        self.logger.info(f"Created backup at {backup_path}")
        
        return backup_path
    
    def _generate_migration_report(self, analysis: Dict[str, Any], result: MigrationResult) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        return {
            "source_framework": analysis["framework"].value,
            "target_framework": "beginnings",
            "migration_timestamp": datetime.now(timezone.utc).isoformat(),
            "files_migrated": len(result.migrated_files),
            "files_created": len(result.created_files),
            "files_skipped": len(result.skipped_files),
            "errors_count": len(result.errors),
            "warnings_count": len(result.warnings),
            "migration_time_seconds": result.migration_time_seconds,
            "complexity_assessment": analysis.get("complexity", {}),
            "success_rate": 1.0 if result.success else 0.0
        }