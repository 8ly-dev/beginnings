"""Tests for migration framework.

This module tests the migration tools for converting Flask, Django, and FastAPI
applications to the Beginnings framework. Following TDD methodology.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import interfaces to be implemented (TDD)
from beginnings.migration.framework import (
    MigrationFramework,
    MigrationResult,
    MigrationConfig,
    MigrationStatus
)
from beginnings.migration.analyzers import (
    CodeAnalyzer,
    DependencyAnalyzer,
    RouteAnalyzer,
    ConfigAnalyzer
)
from beginnings.migration.converters import (
    FlaskConverter,
    DjangoConverter,
    FastAPIConverter,
    UniversalConverter
)
from beginnings.migration.validators import (
    MigrationValidator,
    ValidationResult,
    CompatibilityChecker
)


class TestMigrationFramework:
    """Test universal migration framework following SRP."""
    
    @pytest.fixture
    def migration_framework(self):
        """Create migration framework for testing."""
        return MigrationFramework()
    
    @pytest.fixture
    def migration_config(self):
        """Sample migration configuration."""
        return MigrationConfig(
            source_framework="flask",
            target_framework="beginnings",
            source_directory=Path("/test/source"),
            target_directory=Path("/test/target"),
            preserve_structure=True,
            backup_original=True,
            migration_strategy="incremental",
            custom_mappings={
                "flask.Flask": "beginnings.create_app",
                "flask.request": "beginnings.request",
                "flask.jsonify": "beginnings.jsonify"
            }
        )
    
    @pytest.fixture
    def sample_flask_app(self, tmp_path):
        """Sample Flask application for testing."""
        app_code = """
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'name': u.name, 'email': u.email} for u in users])

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = User(name=data['name'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'name': user.name, 'email': user.email}), 201

if __name__ == '__main__':
    app.run(debug=True)
"""
        
        app_file = tmp_path / "app.py"
        app_file.write_text(app_code)
        
        requirements = """
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Werkzeug==2.3.7
"""
        
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text(requirements)
        
        return tmp_path
    
    def test_framework_initialization(self, migration_framework):
        """Test migration framework initializes correctly."""
        assert migration_framework is not None
        assert hasattr(migration_framework, 'migrate_project')
        assert hasattr(migration_framework, 'analyze_compatibility')
        assert hasattr(migration_framework, 'generate_migration_plan')
        assert hasattr(migration_framework, 'validate_migration')
    
    def test_analyze_compatibility(self, migration_framework, migration_config, sample_flask_app):
        """Test compatibility analysis."""
        migration_config.source_directory = sample_flask_app
        
        result = migration_framework.analyze_compatibility(migration_config)
        
        assert isinstance(result, ValidationResult)
        assert result.is_compatible is not None
        assert len(result.compatibility_issues) >= 0
        assert len(result.migration_suggestions) >= 0
        
        # Should detect Flask framework
        assert "flask" in result.detected_framework.lower()
    
    def test_generate_migration_plan(self, migration_framework, migration_config, sample_flask_app):
        """Test migration plan generation."""
        migration_config.source_directory = sample_flask_app
        
        plan = migration_framework.generate_migration_plan(migration_config)
        
        assert isinstance(plan, dict)
        assert "steps" in plan
        assert "estimated_time" in plan
        assert "dependencies" in plan
        assert "risks" in plan
        
        # Should have migration steps
        assert len(plan["steps"]) > 0
        
        # Should identify key migration areas
        step_types = [step["type"] for step in plan["steps"]]
        assert "dependencies" in step_types
        assert "routes" in step_types
        assert "models" in step_types
    
    def test_migrate_project(self, migration_framework, migration_config, sample_flask_app, tmp_path):
        """Test complete project migration."""
        migration_config.source_directory = sample_flask_app
        migration_config.target_directory = tmp_path / "migrated"
        
        result = migration_framework.migrate_project(migration_config)
        
        assert isinstance(result, MigrationResult)
        assert result.success is not None
        assert result.status in [status.value for status in MigrationStatus]
        assert len(result.migrated_files) >= 0
        assert len(result.errors) >= 0
        assert len(result.warnings) >= 0
        
        if result.success:
            # Check that target directory was created
            assert migration_config.target_directory.exists()
            
            # Check that main files were migrated
            migrated_app = migration_config.target_directory / "app.py"
            assert migrated_app.exists()
    
    def test_validate_migration(self, migration_framework, migration_config, tmp_path):
        """Test migration validation."""
        # Create a simple migrated project
        migrated_dir = tmp_path / "migrated"
        migrated_dir.mkdir()
        
        migrated_app = migrated_dir / "app.py"
        migrated_app.write_text("""
from beginnings import create_app, request, jsonify
from beginnings.extensions.database import DatabaseExtension

app = create_app()
db = DatabaseExtension()

@app.route('/')
def home():
    return {'message': 'Hello World'}

@app.route('/api/users')
def get_users():
    return jsonify([])
""")
        
        migration_config.target_directory = migrated_dir
        
        result = migration_framework.validate_migration(migration_config)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is not None
        assert len(result.validation_errors) >= 0
        assert len(result.warnings) >= 0
        assert len(result.suggestions) >= 0


class TestCodeAnalyzer:
    """Test code analysis functionality following SRP."""
    
    @pytest.fixture
    def code_analyzer(self):
        """Create code analyzer for testing."""
        return CodeAnalyzer()
    
    @pytest.fixture
    def flask_code_sample(self):
        """Sample Flask code for analysis."""
        return """
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

app = Flask(__name__)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    return jsonify({'token': 'abc123'})
"""
    
    def test_analyzer_initialization(self, code_analyzer):
        """Test code analyzer initializes correctly."""
        assert code_analyzer is not None
        assert hasattr(code_analyzer, 'analyze_imports')
        assert hasattr(code_analyzer, 'analyze_routes')
        assert hasattr(code_analyzer, 'analyze_models')
        assert hasattr(code_analyzer, 'analyze_patterns')
    
    def test_analyze_imports(self, code_analyzer, flask_code_sample):
        """Test import analysis."""
        imports = code_analyzer.analyze_imports(flask_code_sample)
        
        assert isinstance(imports, dict)
        assert "flask" in imports
        assert "werkzeug" in imports
        
        # Should detect specific imports
        flask_imports = imports["flask"]
        assert "Flask" in flask_imports
        assert "request" in flask_imports
        assert "jsonify" in flask_imports
    
    def test_analyze_routes(self, code_analyzer, flask_code_sample):
        """Test route analysis."""
        routes = code_analyzer.analyze_routes(flask_code_sample)
        
        assert isinstance(routes, list)
        assert len(routes) > 0
        
        # Should find the login route
        login_route = next((r for r in routes if r["path"] == "/login"), None)
        assert login_route is not None
        assert "POST" in login_route["methods"]
        assert login_route["function_name"] == "login"
    
    def test_analyze_models(self, code_analyzer, flask_code_sample):
        """Test model analysis."""
        models = code_analyzer.analyze_models(flask_code_sample)
        
        assert isinstance(models, list)
        assert len(models) > 0
        
        # Should find the User model
        user_model = next((m for m in models if m["name"] == "User"), None)
        assert user_model is not None
        assert user_model["base_class"] == "db.Model"
        assert len(user_model["fields"]) >= 2
    
    def test_analyze_patterns(self, code_analyzer, flask_code_sample):
        """Test pattern analysis."""
        patterns = code_analyzer.analyze_patterns(flask_code_sample)
        
        assert isinstance(patterns, dict)
        assert "framework" in patterns
        assert "architecture" in patterns
        assert "security" in patterns
        
        # Should detect Flask framework
        assert patterns["framework"] == "flask"
        
        # Should detect security patterns
        security_patterns = patterns["security"]
        assert "password_hashing" in security_patterns


class TestFlaskConverter:
    """Test Flask-specific conversion following SRP."""
    
    @pytest.fixture
    def flask_converter(self):
        """Create Flask converter for testing."""
        return FlaskConverter()
    
    @pytest.fixture
    def flask_app_structure(self, tmp_path):
        """Create Flask application structure."""
        # Main app file
        app_code = """
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import User
from routes import api_bp

app.register_blueprint(api_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)
"""
        
        # Models file
        models_code = """
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
"""
        
        # Routes file
        routes_code = """
from flask import Blueprint, request, jsonify
from models import User
from app import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username} for u in users])

@api_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'username': user.username}), 201
"""
        
        (tmp_path / "app.py").write_text(app_code)
        (tmp_path / "models.py").write_text(models_code)
        (tmp_path / "routes.py").write_text(routes_code)
        
        return tmp_path
    
    def test_converter_initialization(self, flask_converter):
        """Test Flask converter initializes correctly."""
        assert flask_converter is not None
        assert hasattr(flask_converter, 'convert_app')
        assert hasattr(flask_converter, 'convert_routes')
        assert hasattr(flask_converter, 'convert_models')
        assert hasattr(flask_converter, 'convert_config')
    
    def test_convert_app(self, flask_converter, flask_app_structure, tmp_path):
        """Test Flask app conversion."""
        target_dir = tmp_path / "converted"
        target_dir.mkdir()
        
        result = flask_converter.convert_app(flask_app_structure, target_dir)
        
        assert result.success is True
        assert len(result.converted_files) > 0
        
        # Check that main app file was converted
        converted_app = target_dir / "app.py"
        assert converted_app.exists()
        
        converted_content = converted_app.read_text()
        assert "from beginnings" in converted_content
        assert "create_app" in converted_content
    
    def test_convert_routes(self, flask_converter):
        """Test Flask route conversion."""
        flask_route_code = """
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user_detail(user_id):
    if request.method == 'GET':
        user = User.query.get_or_404(user_id)
        return jsonify({'id': user.id, 'username': user.username})
    elif request.method == 'PUT':
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        user.username = data.get('username', user.username)
        db.session.commit()
        return jsonify({'id': user.id, 'username': user.username})
"""
        
        converted = flask_converter.convert_routes(flask_route_code)
        
        assert "@app.route" in converted
        assert "beginnings" in converted or "request" in converted
    
    def test_convert_models(self, flask_converter):
        """Test Flask model conversion."""
        flask_model_code = """
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
"""
        
        converted = flask_converter.convert_models(flask_model_code)
        
        assert "beginnings" in converted or "Model" in converted
        assert "username" in converted
        assert "email" in converted
    
    def test_convert_config(self, flask_converter):
        """Test Flask configuration conversion."""
        flask_config = {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///app.db",
            "SECRET_KEY": "your-secret-key",
            "DEBUG": True,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False
        }
        
        converted_config = flask_converter.convert_config(flask_config)
        
        assert isinstance(converted_config, dict)
        assert "database" in converted_config
        assert "app" in converted_config
        
        # Check database configuration
        db_config = converted_config["database"]
        assert "uri" in db_config or "url" in db_config
        
        # Check app configuration
        app_config = converted_config["app"]
        assert "debug" in app_config
        assert "secret_key" in app_config


class TestDjangoConverter:
    """Test Django-specific conversion following SRP."""
    
    @pytest.fixture
    def django_converter(self):
        """Create Django converter for testing."""
        return DjangoConverter()
    
    @pytest.fixture
    def django_model_sample(self):
        """Sample Django model code."""
        return """
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
"""
    
    @pytest.fixture
    def django_view_sample(self):
        """Sample Django view code."""
        return """
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from .models import Post, User
import json

class PostListView(ListView):
    model = Post
    template_name = 'posts/list.html'
    context_object_name = 'posts'
    paginate_by = 10

@csrf_exempt
def api_posts(request):
    if request.method == 'GET':
        posts = Post.objects.all()[:10]
        data = [{'id': p.id, 'title': p.title} for p in posts]
        return JsonResponse({'posts': data})
    elif request.method == 'POST':
        data = json.loads(request.body)
        post = Post.objects.create(
            title=data['title'],
            content=data['content'],
            author_id=data['author_id']
        )
        return JsonResponse({'id': post.id, 'title': post.title})
"""
    
    def test_converter_initialization(self, django_converter):
        """Test Django converter initializes correctly."""
        assert django_converter is not None
        assert hasattr(django_converter, 'convert_models')
        assert hasattr(django_converter, 'convert_views')
        assert hasattr(django_converter, 'convert_urls')
        assert hasattr(django_converter, 'convert_settings')
    
    def test_convert_models(self, django_converter, django_model_sample):
        """Test Django model conversion."""
        converted = django_converter.convert_models(django_model_sample)
        
        assert "beginnings" in converted or "Model" in converted
        assert "User" in converted
        assert "Post" in converted
        # Should convert foreign key relationships
        assert "author" in converted
    
    def test_convert_views(self, django_converter, django_view_sample):
        """Test Django view conversion."""
        converted = django_converter.convert_views(django_view_sample)
        
        assert "beginnings" in converted or "@app.route" in converted
        assert "api_posts" in converted or "posts" in converted
        # Should convert class-based views to function-based
        assert "def" in converted
    
    def test_convert_urls(self, django_converter):
        """Test Django URL pattern conversion."""
        django_urls = """
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('api/posts/', views.api_posts, name='api_posts'),
    path('api/posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('admin/', include('admin.urls')),
]
"""
        
        converted = django_converter.convert_urls(django_urls)
        
        assert "@app.route" in converted or "beginnings" in converted
        assert "posts" in converted
    
    def test_convert_settings(self, django_converter):
        """Test Django settings conversion."""
        django_settings = {
            "DEBUG": True,
            "SECRET_KEY": "django-secret-key",
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": "myproject",
                    "USER": "myuser",
                    "PASSWORD": "mypassword",
                    "HOST": "localhost",
                    "PORT": "5432"
                }
            },
            "INSTALLED_APPS": [
                "django.contrib.admin",
                "django.contrib.auth",
                "myapp"
            ]
        }
        
        converted = django_converter.convert_settings(django_settings)
        
        assert isinstance(converted, dict)
        assert "app" in converted
        assert "database" in converted
        
        # Check database conversion
        db_config = converted["database"]
        assert "host" in db_config
        assert "port" in db_config
        assert "name" in db_config


class TestFastAPIConverter:
    """Test FastAPI-specific conversion following SRP."""
    
    @pytest.fixture
    def fastapi_converter(self):
        """Create FastAPI converter for testing."""
        return FastAPIConverter()
    
    @pytest.fixture
    def fastapi_app_sample(self):
        """Sample FastAPI application code."""
        return """
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List

app = FastAPI(title="My API", version="1.0.0")

security = HTTPBearer()
Base = declarative_base()
engine = create_engine("sqlite:///./test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)

class UserCreate(BaseModel):
    username: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
"""
    
    def test_converter_initialization(self, fastapi_converter):
        """Test FastAPI converter initializes correctly."""
        assert fastapi_converter is not None
        assert hasattr(fastapi_converter, 'convert_app')
        assert hasattr(fastapi_converter, 'convert_routes')
        assert hasattr(fastapi_converter, 'convert_models')
        assert hasattr(fastapi_converter, 'convert_dependencies')
    
    def test_convert_app(self, fastapi_converter, fastapi_app_sample):
        """Test FastAPI app conversion."""
        converted = fastapi_converter.convert_app(fastapi_app_sample)
        
        assert "beginnings" in converted
        assert "create_app" in converted or "app" in converted
    
    def test_convert_routes(self, fastapi_converter, fastapi_app_sample):
        """Test FastAPI route conversion."""
        converted = fastapi_converter.convert_routes(fastapi_app_sample)
        
        assert "@app.route" in converted or "beginnings" in converted
        assert "users" in converted
        # Should convert path parameters
        assert "user_id" in converted
    
    def test_convert_models(self, fastapi_converter, fastapi_app_sample):
        """Test FastAPI model conversion."""
        converted = fastapi_converter.convert_models(fastapi_app_sample)
        
        assert "beginnings" in converted or "Model" in converted
        assert "User" in converted
        # Should convert Pydantic models to appropriate format
        assert "username" in converted
        assert "email" in converted
    
    def test_convert_dependencies(self, fastapi_converter, fastapi_app_sample):
        """Test FastAPI dependency injection conversion."""
        converted = fastapi_converter.convert_dependencies(fastapi_app_sample)
        
        assert "beginnings" in converted or "extension" in converted
        # Should convert database dependencies
        assert "database" in converted or "db" in converted


class TestMigrationValidator:
    """Test migration validation following SRP."""
    
    @pytest.fixture
    def migration_validator(self):
        """Create migration validator for testing."""
        return MigrationValidator()
    
    @pytest.fixture
    def valid_beginnings_app(self, tmp_path):
        """Sample valid Beginnings application."""
        app_code = """
from beginnings import create_app
from beginnings.extensions.database import DatabaseExtension
from beginnings.extensions.auth import AuthExtension

app = create_app({
    'database': {
        'uri': 'sqlite:///app.db'
    },
    'auth': {
        'secret_key': 'your-secret-key'
    }
})

db = DatabaseExtension()
auth = AuthExtension()

@app.route('/')
def home():
    return {'message': 'Hello World'}

@app.route('/api/users')
def get_users():
    return {'users': []}
"""
        
        app_file = tmp_path / "app.py"
        app_file.write_text(app_code)
        
        return tmp_path
    
    def test_validator_initialization(self, migration_validator):
        """Test migration validator initializes correctly."""
        assert migration_validator is not None
        assert hasattr(migration_validator, 'validate_syntax')
        assert hasattr(migration_validator, 'validate_imports')
        assert hasattr(migration_validator, 'validate_structure')
        assert hasattr(migration_validator, 'validate_functionality')
    
    def test_validate_syntax(self, migration_validator, valid_beginnings_app):
        """Test syntax validation."""
        app_file = valid_beginnings_app / "app.py"
        code = app_file.read_text()
        
        result = migration_validator.validate_syntax(code)
        
        assert result.is_valid is True
        assert len(result.syntax_errors) == 0
    
    def test_validate_imports(self, migration_validator, valid_beginnings_app):
        """Test import validation."""
        app_file = valid_beginnings_app / "app.py"
        code = app_file.read_text()
        
        result = migration_validator.validate_imports(code)
        
        assert result.is_valid is True
        assert len(result.missing_imports) == 0
        # Should detect beginnings imports
        assert "beginnings" in str(result.detected_imports)
    
    def test_validate_structure(self, migration_validator, valid_beginnings_app):
        """Test project structure validation."""
        result = migration_validator.validate_structure(valid_beginnings_app)
        
        assert result.is_valid is not None
        assert len(result.structure_issues) >= 0
        # Should have main app file
        assert any("app.py" in str(file) for file in result.validated_files)
    
    def test_validate_functionality(self, migration_validator, valid_beginnings_app):
        """Test functionality validation."""
        result = migration_validator.validate_functionality(valid_beginnings_app)
        
        assert result.is_valid is not None
        assert len(result.functionality_issues) >= 0
        
        # Should detect basic app functionality
        if result.is_valid:
            assert "routes" in result.detected_features
            assert "extensions" in result.detected_features