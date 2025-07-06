"""Integration tests for the migration framework.

Tests the complete migration framework including Flask, Django, and FastAPI converters.
Follows TDD methodology and validates SOLID principles implementation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from beginnings.migration import (
    MigrationFramework,
    MigrationConfig,
    MigrationStatus,
    FrameworkType,
    ValidationResult,
    FlaskConverter,
    DjangoConverter,
    FastAPIConverter,
    ProjectAnalyzer,
    MigrationPlanner
)


class TestMigrationFrameworkIntegration:
    """Test complete migration framework integration."""
    
    @pytest.fixture
    def migration_framework(self):
        """Create migration framework with all converters registered."""
        framework = MigrationFramework()
        
        # Register all converters
        framework.register_converter(FrameworkType.FLASK, FlaskConverter())
        framework.register_converter(FrameworkType.DJANGO, DjangoConverter())
        framework.register_converter(FrameworkType.FASTAPI, FastAPIConverter())
        
        return framework
    
    @pytest.fixture
    def temp_directories(self):
        """Create temporary source and target directories."""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as target_dir:
                yield Path(source_dir), Path(target_dir)
    
    @pytest.fixture
    def flask_project(self, temp_directories):
        """Create a sample Flask project."""
        source_dir, _ = temp_directories
        
        # Create Flask app.py
        app_file = source_dir / "app.py"
        app_file.write_text("""
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        return jsonify({'message': 'User created'})
    return jsonify({'users': []})

if __name__ == '__main__':
    app.run(debug=True)
""")
        
        # Create requirements.txt
        req_file = source_dir / "requirements.txt"
        req_file.write_text("""
Flask==2.3.0
Flask-SQLAlchemy==3.0.0
""")
        
        return source_dir
    
    @pytest.fixture
    def django_project(self, temp_directories):
        """Create a sample Django project."""
        source_dir, _ = temp_directories
        
        # Create Django views.py
        views_file = source_dir / "views.py"
        views_file.write_text("""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def api_users(request):
    if request.method == 'POST':
        return JsonResponse({'message': 'User created'})
    return JsonResponse({'users': []})
""")
        
        # Create Django models.py
        models_file = source_dir / "models.py"
        models_file.write_text("""
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['name']
""")
        
        # Create Django urls.py
        urls_file = source_dir / "urls.py"
        urls_file.write_text("""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/users/', views.api_users, name='api_users'),
]
""")
        
        return source_dir
    
    @pytest.fixture
    def fastapi_project(self, temp_directories):
        """Create a sample FastAPI project."""
        source_dir, _ = temp_directories
        
        # Create FastAPI main.py
        main_file = source_dir / "main.py"
        main_file.write_text("""
from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/api/users", response_model=List[User])
async def get_users():
    return []

@app.post("/api/users", response_model=User)
async def create_user(user: User):
    return user

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    if user_id == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "name": "Test User"}
""")
        
        # Create Pydantic models.py
        models_file = source_dir / "models.py"
        models_file.write_text("""
from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class User(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True
""")
        
        # Create requirements.txt
        req_file = source_dir / "requirements.txt"
        req_file.write_text("""
fastapi==0.104.0
uvicorn==0.24.0
pydantic==2.4.0
""")
        
        return source_dir
    
    def test_flask_project_analysis(self, migration_framework, flask_project, temp_directories):
        """Test Flask project analysis and compatibility."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=flask_project,
            target_directory=target_dir
        )
        
        # Test compatibility analysis
        compatibility = migration_framework.analyze_compatibility(config)
        
        assert compatibility.is_compatible
        assert compatibility.detected_framework == "flask"
        assert compatibility.compatibility_score > 0.8
        assert compatibility.estimated_effort_hours > 0
    
    def test_django_project_analysis(self, migration_framework, django_project, temp_directories):
        """Test Django project analysis and compatibility."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="django",
            source_directory=django_project,
            target_directory=target_dir
        )
        
        # Test compatibility analysis
        compatibility = migration_framework.analyze_compatibility(config)
        
        assert compatibility.is_compatible
        assert compatibility.detected_framework == "django"
        assert compatibility.compatibility_score > 0.8
        assert compatibility.estimated_effort_hours > 0
    
    def test_fastapi_project_analysis(self, migration_framework, fastapi_project, temp_directories):
        """Test FastAPI project analysis and compatibility."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="fastapi",
            source_directory=fastapi_project,
            target_directory=target_dir
        )
        
        # Test compatibility analysis
        compatibility = migration_framework.analyze_compatibility(config)
        
        assert compatibility.is_compatible
        assert compatibility.detected_framework == "fastapi"
        assert compatibility.compatibility_score > 0.8
        assert compatibility.estimated_effort_hours > 0
    
    def test_flask_migration_plan_generation(self, migration_framework, flask_project, temp_directories):
        """Test Flask migration plan generation."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=flask_project,
            target_directory=target_dir
        )
        
        # Test migration plan generation
        plan = migration_framework.generate_migration_plan(config)
        
        assert 'steps' in plan
        assert 'estimated_time' in plan
        assert 'dependencies' in plan
        assert 'risks' in plan
        
        # Verify migration steps are present
        step_types = [step.type for step in plan['steps']]
        assert 'preparation' in step_types
        assert 'dependencies' in step_types
        assert 'config' in step_types
        assert 'routes' in step_types
        assert 'validation' in step_types
    
    def test_django_migration_plan_generation(self, migration_framework, django_project, temp_directories):
        """Test Django migration plan generation."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="django",
            source_directory=django_project,
            target_directory=target_dir
        )
        
        # Test migration plan generation
        plan = migration_framework.generate_migration_plan(config)
        
        assert 'steps' in plan
        assert 'estimated_time' in plan
        assert len(plan['steps']) > 0
        
        # Verify Django-specific steps are included
        step_types = [step.type for step in plan['steps']]
        assert 'models' in step_types  # Django has models
    
    def test_fastapi_migration_plan_generation(self, migration_framework, fastapi_project, temp_directories):
        """Test FastAPI migration plan generation."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="fastapi",
            source_directory=fastapi_project,
            target_directory=target_dir
        )
        
        # Test migration plan generation
        plan = migration_framework.generate_migration_plan(config)
        
        assert 'steps' in plan
        assert 'estimated_time' in plan
        assert len(plan['steps']) > 0
        
        # Verify FastAPI-specific considerations
        step_types = [step.type for step in plan['steps']]
        assert 'routes' in step_types
        assert 'validation' in step_types
    
    def test_flask_complete_migration(self, migration_framework, flask_project, temp_directories):
        """Test complete Flask to Beginnings migration."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=flask_project,
            target_directory=target_dir,
            backup_original=True,
            validate_after_migration=True
        )
        
        # Execute migration
        result = migration_framework.migrate_project(config)
        
        # Verify migration success
        assert result.success
        assert result.status == MigrationStatus.COMPLETED
        assert len(result.migrated_files) > 0
        assert len(result.created_files) > 0
        assert len(result.errors) == 0
        assert result.backup_location is not None
        
        # Verify output files exist
        assert (target_dir / "app.py").exists()
        assert (target_dir / "beginnings.yaml").exists()
        assert (target_dir / "requirements.txt").exists()
        
        # Verify Flask imports were transformed
        app_content = (target_dir / "app.py").read_text()
        assert "from beginnings import" in app_content
        assert "create_app()" in app_content
    
    def test_django_complete_migration(self, migration_framework, django_project, temp_directories):
        """Test complete Django to Beginnings migration."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="django",
            source_directory=django_project,
            target_directory=target_dir,
            backup_original=True
        )
        
        # Execute migration
        result = migration_framework.migrate_project(config)
        
        # Verify migration completed (may be partial due to complexity)
        assert result.status in [MigrationStatus.COMPLETED, MigrationStatus.PARTIAL]
        assert len(result.migrated_files) > 0
        assert len(result.created_files) > 0
        
        # Verify Django-specific transformations
        if (target_dir / "models.py").exists():
            models_content = (target_dir / "models.py").read_text()
            assert "from beginnings.extensions.database import" in models_content
        
        if (target_dir / "routes.py").exists():
            routes_content = (target_dir / "routes.py").read_text()
            assert "from beginnings import create_app" in routes_content
    
    def test_fastapi_complete_migration(self, migration_framework, fastapi_project, temp_directories):
        """Test complete FastAPI to Beginnings migration."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="fastapi",
            source_directory=fastapi_project,
            target_directory=target_dir,
            backup_original=True
        )
        
        # Execute migration
        result = migration_framework.migrate_project(config)
        
        # Verify migration success
        assert result.success
        assert result.status == MigrationStatus.COMPLETED
        assert len(result.migrated_files) > 0
        assert len(result.created_files) > 0
        
        # Verify FastAPI transformations
        main_content = (target_dir / "main.py").read_text()
        assert "from beginnings import" in main_content
        assert "create_app()" in main_content
        assert "@app.route" in main_content
        
        # Verify Pydantic models were transformed
        if (target_dir / "models.py").exists():
            models_content = (target_dir / "models.py").read_text()
            assert "from beginnings.extensions.database import" in models_content or "from beginnings.models import" in models_content
    
    def test_migration_validation(self, migration_framework, flask_project, temp_directories):
        """Test migration validation functionality."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=flask_project,
            target_directory=target_dir
        )
        
        # Execute migration first
        migration_framework.migrate_project(config)
        
        # Test validation
        validation_result = migration_framework.validate_migration(config)
        
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'validated_files')
        assert hasattr(validation_result, 'detected_features')
        assert len(validation_result.validated_files) > 0
    
    def test_migration_error_handling(self, migration_framework, temp_directories):
        """Test migration error handling for invalid projects."""
        source_dir, target_dir = temp_directories
        
        # Create an empty/invalid project
        config = MigrationConfig(
            source_framework="unknown",
            source_directory=source_dir,
            target_directory=target_dir
        )
        
        # Test compatibility analysis with unknown framework
        compatibility = migration_framework.analyze_compatibility(config)
        assert not compatibility.is_compatible
        assert len(compatibility.compatibility_issues) > 0
        
        # Test migration of unknown framework
        result = migration_framework.migrate_project(config)
        assert not result.success
        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) > 0
    
    def test_migration_backup_functionality(self, migration_framework, flask_project, temp_directories):
        """Test migration backup functionality."""
        _, target_dir = temp_directories
        
        config = MigrationConfig(
            source_framework="flask",
            source_directory=flask_project,
            target_directory=target_dir,
            backup_original=True
        )
        
        # Execute migration
        result = migration_framework.migrate_project(config)
        
        # Verify backup was created
        assert result.backup_location is not None
        assert result.backup_location.exists()
        assert (result.backup_location / "app.py").exists()
        assert (result.backup_location / "requirements.txt").exists()
    
    def test_migration_framework_convergence(self, migration_framework, temp_directories):
        """Test that all frameworks converge to similar Beginnings structure."""
        source_dir, target_dir = temp_directories
        
        # Create simple apps for each framework
        flask_dir = source_dir / "flask_app"
        django_dir = source_dir / "django_app"
        fastapi_dir = source_dir / "fastapi_app"
        
        flask_target = target_dir / "flask_result"
        django_target = target_dir / "django_result"
        fastapi_target = target_dir / "fastapi_result"
        
        # Create minimal apps
        for app_dir in [flask_dir, django_dir, fastapi_dir]:
            app_dir.mkdir(parents=True)
        
        # Flask app
        (flask_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)")
        
        # Django app
        (django_dir / "views.py").write_text("from django.http import HttpResponse")
        (django_dir / "models.py").write_text("from django.db import models")
        
        # FastAPI app
        (fastapi_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
        
        # Migrate all three
        configs = [
            MigrationConfig("flask", source_directory=flask_dir, target_directory=flask_target),
            MigrationConfig("django", source_directory=django_dir, target_directory=django_target),
            MigrationConfig("fastapi", source_directory=fastapi_dir, target_directory=fastapi_target)
        ]
        
        results = [migration_framework.migrate_project(config) for config in configs]
        
        # Verify all migrations created Beginnings config files
        for target in [flask_target, django_target, fastapi_target]:
            assert (target / "beginnings.yaml").exists()
            assert (target / "requirements.txt").exists()
            
            # Verify config content has Beginnings structure
            config_content = (target / "beginnings.yaml").read_text()
            assert "app:" in config_content
            assert "database:" in config_content
            assert "extensions:" in config_content


class TestFrameworkSpecificConverters:
    """Test individual framework converters in isolation."""
    
    def test_flask_converter_framework_support(self):
        """Test Flask converter framework support."""
        converter = FlaskConverter()
        
        assert converter.supports_framework(FrameworkType.FLASK)
        assert not converter.supports_framework(FrameworkType.DJANGO)
        assert not converter.supports_framework(FrameworkType.FASTAPI)
    
    def test_django_converter_framework_support(self):
        """Test Django converter framework support."""
        converter = DjangoConverter()
        
        assert converter.supports_framework(FrameworkType.DJANGO)
        assert not converter.supports_framework(FrameworkType.FLASK)
        assert not converter.supports_framework(FrameworkType.FASTAPI)
    
    def test_fastapi_converter_framework_support(self):
        """Test FastAPI converter framework support."""
        converter = FastAPIConverter()
        
        assert converter.supports_framework(FrameworkType.FASTAPI)
        assert not converter.supports_framework(FrameworkType.FLASK)
        assert not converter.supports_framework(FrameworkType.DJANGO)
    
    def test_flask_route_conversion(self):
        """Test Flask route conversion."""
        converter = FlaskConverter()
        
        flask_code = """
@app.route('/users', methods=['GET', 'POST'])
def users():
    return 'Users'
"""
        
        converted = converter.convert_routes(flask_code)
        # Flask and Beginnings have similar syntax, so minimal changes expected
        assert "@app.route" in converted
    
    def test_django_model_conversion(self):
        """Test Django model conversion."""
        converter = DjangoConverter()
        
        django_code = """
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
"""
        
        converted = converter.convert_models(django_code)
        assert "from beginnings.extensions.database import" in converted
        assert "db.Column(db.String" in converted
    
    def test_fastapi_model_conversion(self):
        """Test FastAPI/Pydantic model conversion."""
        converter = FastAPIConverter()
        
        fastapi_code = """
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int
"""
        
        converted = converter.convert_models(fastapi_code)
        assert "from beginnings.extensions.database import" in converted or "from beginnings.models import" in converted
        assert "db.Column" in converted
    
    def test_fastapi_route_conversion(self):
        """Test FastAPI route conversion."""
        converter = FastAPIConverter()
        
        fastapi_code = """
@app.get('/users')
async def get_users():
    return []

@app.post('/users')
async def create_user(user: User):
    return user
"""
        
        converted = converter.convert_routes(fastapi_code)
        assert "@app.route('/users', methods=['GET'])" in converted
        assert "@app.route('/users', methods=['POST'])" in converted
        assert "def get_users():" in converted  # async removed
        assert "def create_user(" in converted


class TestProjectAnalyzer:
    """Test project analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create project analyzer."""
        return ProjectAnalyzer()
    
    def test_flask_framework_detection(self, analyzer, temp_directories):
        """Test Flask framework detection."""
        source_dir, _ = temp_directories
        
        # Create Flask indicators
        (source_dir / "app.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello'
""")
        
        framework = analyzer.detect_framework(source_dir)
        assert framework == FrameworkType.FLASK
    
    def test_django_framework_detection(self, analyzer, temp_directories):
        """Test Django framework detection."""
        source_dir, _ = temp_directories
        
        # Create Django indicators
        (source_dir / "manage.py").write_text("# Django manage.py")
        (source_dir / "settings.py").write_text("""
INSTALLED_APPS = [
    'django.contrib.admin',
]
""")
        
        framework = analyzer.detect_framework(source_dir)
        assert framework == FrameworkType.DJANGO
    
    def test_fastapi_framework_detection(self, analyzer, temp_directories):
        """Test FastAPI framework detection."""
        source_dir, _ = temp_directories
        
        # Create FastAPI indicators
        (source_dir / "main.py").write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello'}
""")
        
        framework = analyzer.detect_framework(source_dir)
        assert framework == FrameworkType.FASTAPI
    
    def test_unknown_framework_detection(self, analyzer, temp_directories):
        """Test unknown framework detection."""
        source_dir, _ = temp_directories
        
        # Create non-framework Python file
        (source_dir / "script.py").write_text("print('Hello World')")
        
        framework = analyzer.detect_framework(source_dir)
        assert framework == FrameworkType.UNKNOWN
    
    def test_complexity_assessment(self, analyzer, temp_directories):
        """Test project complexity assessment."""
        source_dir, _ = temp_directories
        
        # Create a medium complexity project
        for i in range(15):
            py_file = source_dir / f"module_{i}.py"
            py_file.write_text(f"# Module {i}\n" + "print('test')\n" * 50)
        
        complexity = analyzer.assess_complexity(source_dir)
        
        assert complexity['overall_score'] > 0
        assert complexity['estimated_hours'] > 0
        assert complexity['risk_level'] in ['low', 'medium', 'high']
        assert 'file_count' in complexity['factors']
        assert 'lines_of_code' in complexity['factors']


class TestMigrationPlanner:
    """Test migration planning functionality."""
    
    @pytest.fixture
    def planner(self):
        """Create migration planner."""
        return MigrationPlanner()
    
    def test_flask_migration_plan_generation(self, planner):
        """Test Flask migration plan generation."""
        config = MigrationConfig(source_framework="flask")
        analysis = {
            'framework': FrameworkType.FLASK,
            'complexity': {'estimated_hours': 8, 'risk_level': 'medium'},
            'patterns': {'routing_patterns': ['flask_routes']},
            'structure': {'template_files': ['index.html'], 'test_files': ['test_app.py']}
        }
        
        plan = planner.generate_migration_plan(config, analysis)
        
        assert 'steps' in plan
        assert 'estimated_time' in plan
        assert 'dependencies' in plan
        assert 'risks' in plan
        assert 'strategy' in plan
        
        # Verify step dependencies are properly ordered
        steps = plan['steps']
        step_ids = [step.id for step in steps]
        
        # Backup should be first
        assert step_ids[0] == 'backup'
        
        # Validation should be last
        assert step_ids[-1] == 'validation'
        
        # Dependencies should come before config
        backup_index = step_ids.index('backup')
        dependencies_index = step_ids.index('dependencies')
        config_index = step_ids.index('config')
        
        assert backup_index < dependencies_index < config_index
    
    def test_django_migration_plan_with_models(self, planner):
        """Test Django migration plan includes model migration."""
        config = MigrationConfig(source_framework="django")
        analysis = {
            'framework': FrameworkType.DJANGO,
            'complexity': {'estimated_hours': 12, 'risk_level': 'high'},
            'patterns': {'model_patterns': ['django_models']},
            'structure': {'test_files': []}
        }
        
        plan = planner.generate_migration_plan(config, analysis)
        
        # Verify models step is included
        step_types = [step.type for step in plan['steps']]
        assert 'models' in step_types
        
        # Verify models step comes before routes
        steps = plan['steps']
        models_step = next(step for step in steps if step.type == 'models')
        routes_step = next(step for step in steps if step.type == 'routes')
        
        assert 'config' in models_step.dependencies
        assert models_step.id in routes_step.dependencies


if __name__ == "__main__":
    pytest.main([__file__])