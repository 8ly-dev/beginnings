"""Tests for code pattern analysis and conversion.

This module tests the analysis and conversion of code patterns from
Flask, Django, and FastAPI to Beginnings framework. Following TDD methodology.
"""

import pytest
import ast
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import interfaces to be implemented (TDD)
from beginnings.migration.converters import (
    CodePatternAnalyzer,
    RoutingConverter,
    ModelConverter,
    MiddlewareConverter,
    TemplateConverter
)
from beginnings.migration.patterns import (
    FlaskPatterns,
    DjangoPatterns,
    FastAPIPatterns,
    BeginningsPatterns
)
from beginnings.migration.transforms import (
    ASTTransformer,
    ImportTransformer,
    DecoratorTransformer,
    ClassTransformer
)


class TestCodePatternAnalyzer:
    """Test code pattern analysis following SRP."""
    
    @pytest.fixture
    def pattern_analyzer(self):
        """Create code pattern analyzer for testing."""
        return CodePatternAnalyzer()
    
    @pytest.fixture
    def flask_routing_sample(self):
        """Sample Flask routing patterns."""
        return """
from flask import Flask, request, jsonify, abort
from werkzeug.exceptions import NotFound

app = Flask(__name__)

@app.route('/')
def home():
    return {'message': 'Hello World'}

@app.route('/users/<int:user_id>', methods=['GET', 'POST'])
def user_detail(user_id):
    if request.method == 'GET':
        return {'user_id': user_id}
    elif request.method == 'POST':
        data = request.get_json()
        return {'user_id': user_id, 'data': data}, 201

@app.route('/api/posts')
def list_posts():
    page = request.args.get('page', 1, type=int)
    posts = get_posts(page=page)
    return jsonify(posts)

@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404

@app.before_request
def before_request():
    # Authentication check
    if not is_authenticated():
        abort(401)
"""
    
    @pytest.fixture
    def django_view_sample(self):
        """Sample Django view patterns."""
        return """
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from .models import Post, User
import json

class PostListView(ListView):
    model = Post
    template_name = 'posts/list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        return Post.objects.filter(published=True)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_posts(request):
    if request.method == 'GET':
        posts = Post.objects.all()[:10]
        data = [{'id': p.id, 'title': p.title} for p in posts]
        return JsonResponse({'posts': data})
    elif request.method == 'POST':
        data = json.loads(request.body)
        post = Post.objects.create(**data)
        return JsonResponse({'id': post.id})

@login_required
def user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'users/profile.html', {'user': user})
"""
    
    @pytest.fixture
    def fastapi_routing_sample(self):
        """Sample FastAPI routing patterns."""
        return """
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
security = HTTPBearer()

class UserCreate(BaseModel):
    username: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Authentication logic
    return User(id=1, username="test")

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, current_user: User = Depends(get_current_user)):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate):
    # Create user logic
    return UserResponse(id=1, username=user.username, email=user.email)

@app.get("/posts/", response_model=List[dict])
def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, le=100),
    current_user: User = Depends(get_current_user)
):
    return get_posts(page=page, size=size)
"""
    
    def test_analyzer_initialization(self, pattern_analyzer):
        """Test pattern analyzer initializes correctly."""
        assert pattern_analyzer is not None
        assert hasattr(pattern_analyzer, 'analyze_patterns')
        assert hasattr(pattern_analyzer, 'extract_routes')
        assert hasattr(pattern_analyzer, 'extract_middleware')
        assert hasattr(pattern_analyzer, 'extract_dependencies')
    
    def test_analyze_flask_patterns(self, pattern_analyzer, flask_routing_sample):
        """Test Flask pattern analysis."""
        patterns = pattern_analyzer.analyze_patterns(flask_routing_sample, "flask")
        
        assert isinstance(patterns, dict)
        assert "framework" in patterns
        assert "routing" in patterns
        assert "middleware" in patterns
        assert "error_handling" in patterns
        
        # Should detect Flask framework
        assert patterns["framework"] == "flask"
        
        # Should extract routing patterns
        routing = patterns["routing"]
        assert len(routing["routes"]) >= 3
        assert any(r["path"] == "/" for r in routing["routes"])
        assert any(r["path"] == "/users/<int:user_id>" for r in routing["routes"])
        
        # Should detect middleware patterns
        middleware = patterns["middleware"]
        assert "before_request" in middleware
        
        # Should detect error handling
        error_handling = patterns["error_handling"]
        assert "404" in error_handling
    
    def test_analyze_django_patterns(self, pattern_analyzer, django_view_sample):
        """Test Django pattern analysis."""
        patterns = pattern_analyzer.analyze_patterns(django_view_sample, "django")
        
        assert patterns["framework"] == "django"
        
        # Should extract class-based views
        views = patterns["views"]
        assert "class_based" in views
        assert "function_based" in views
        
        class_views = views["class_based"]
        assert any(v["name"] == "PostListView" for v in class_views)
        
        # Should detect decorators
        decorators = patterns["decorators"]
        assert "csrf_exempt" in decorators
        assert "login_required" in decorators
        assert "require_http_methods" in decorators
    
    def test_analyze_fastapi_patterns(self, pattern_analyzer, fastapi_routing_sample):
        """Test FastAPI pattern analysis."""
        patterns = pattern_analyzer.analyze_patterns(fastapi_routing_sample, "fastapi")
        
        assert patterns["framework"] == "fastapi"
        
        # Should extract dependency injection patterns
        dependencies = patterns["dependencies"]
        assert "get_current_user" in dependencies
        assert "security" in dependencies
        
        # Should extract type annotations
        type_annotations = patterns["type_annotations"]
        assert "pydantic_models" in type_annotations
        assert "response_models" in type_annotations
        
        # Should detect path and query parameters
        parameters = patterns["parameters"]
        assert "path_params" in parameters
        assert "query_params" in parameters


class TestRoutingConverter:
    """Test routing pattern conversion following SRP."""
    
    @pytest.fixture
    def routing_converter(self):
        """Create routing converter for testing."""
        return RoutingConverter()
    
    def test_converter_initialization(self, routing_converter):
        """Test routing converter initializes correctly."""
        assert routing_converter is not None
        assert hasattr(routing_converter, 'convert_flask_routes')
        assert hasattr(routing_converter, 'convert_django_urls')
        assert hasattr(routing_converter, 'convert_fastapi_routes')
        assert hasattr(routing_converter, 'to_beginnings_routes')
    
    def test_convert_flask_simple_route(self, routing_converter):
        """Test converting simple Flask route."""
        flask_route = """
@app.route('/')
def home():
    return {'message': 'Hello World'}
"""
        
        converted = routing_converter.convert_flask_routes(flask_route)
        
        assert "@app.route('/')" in converted
        assert "def home()" in converted
        assert "beginnings" in converted or "return" in converted
    
    def test_convert_flask_parameterized_route(self, routing_converter):
        """Test converting Flask route with parameters."""
        flask_route = """
@app.route('/users/<int:user_id>', methods=['GET', 'POST'])
def user_detail(user_id):
    return {'user_id': user_id}
"""
        
        converted = routing_converter.convert_flask_routes(flask_route)
        
        assert "@app.route('/users/<int:user_id>'" in converted
        assert "methods=['GET', 'POST']" in converted
        assert "user_id" in converted
    
    def test_convert_django_function_view(self, routing_converter):
        """Test converting Django function-based view."""
        django_view = """
@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_posts(request):
    if request.method == 'GET':
        return JsonResponse({'posts': []})
    return JsonResponse({'created': True})
"""
        
        converted = routing_converter.convert_django_urls(django_view)
        
        assert "@app.route" in converted
        assert "methods=['GET', 'POST']" in converted
        assert "request" in converted
    
    def test_convert_django_class_view(self, routing_converter):
        """Test converting Django class-based view."""
        django_view = """
class PostListView(ListView):
    model = Post
    template_name = 'posts/list.html'
    context_object_name = 'posts'
    paginate_by = 10
"""
        
        converted = routing_converter.convert_django_urls(django_view)
        
        # Should convert to function-based view
        assert "def" in converted
        assert "posts" in converted
        assert "@app.route" in converted
    
    def test_convert_fastapi_route(self, routing_converter):
        """Test converting FastAPI route."""
        fastapi_route = """
@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, current_user: User = Depends(get_current_user)):
    return current_user
"""
        
        converted = routing_converter.convert_fastapi_routes(fastapi_route)
        
        assert "@app.route('/users/<int:user_id>'" in converted
        assert "methods=['GET']" in converted
        assert "user_id" in converted
    
    def test_to_beginnings_routes(self, routing_converter):
        """Test final conversion to Beginnings format."""
        generic_route = {
            "path": "/api/users/<int:user_id>",
            "methods": ["GET", "POST"],
            "function_name": "user_detail",
            "parameters": ["user_id"],
            "decorators": ["login_required"]
        }
        
        converted = routing_converter.to_beginnings_routes([generic_route])
        
        assert "@app.route('/api/users/<int:user_id>'" in converted
        assert "methods=['GET', 'POST']" in converted
        assert "@login_required" in converted or "auth" in converted


class TestModelConverter:
    """Test model conversion following SRP."""
    
    @pytest.fixture
    def model_converter(self):
        """Create model converter for testing."""
        return ModelConverter()
    
    @pytest.fixture
    def flask_sqlalchemy_model(self):
        """Sample Flask-SQLAlchemy model."""
        return """
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
"""
    
    @pytest.fixture
    def django_model(self):
        """Sample Django model."""
        return """
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    class Meta:
        db_table = 'custom_users'
        ordering = ['date_joined']

class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['published', 'created_at']),
        ]
"""
    
    def test_converter_initialization(self, model_converter):
        """Test model converter initializes correctly."""
        assert model_converter is not None
        assert hasattr(model_converter, 'convert_flask_models')
        assert hasattr(model_converter, 'convert_django_models')
        assert hasattr(model_converter, 'convert_pydantic_models')
        assert hasattr(model_converter, 'to_beginnings_models')
    
    def test_convert_flask_sqlalchemy_model(self, model_converter, flask_sqlalchemy_model):
        """Test converting Flask-SQLAlchemy model."""
        converted = model_converter.convert_flask_models(flask_sqlalchemy_model)
        
        assert "beginnings" in converted
        assert "User" in converted
        assert "Post" in converted
        
        # Should convert field types
        assert "String" in converted or "CharField" in converted
        assert "Integer" in converted or "IntegerField" in converted
        
        # Should preserve relationships
        assert "relationship" in converted or "ForeignKey" in converted
    
    def test_convert_django_model(self, model_converter, django_model):
        """Test converting Django model."""
        converted = model_converter.convert_django_models(django_model)
        
        assert "beginnings" in converted
        assert "User" in converted
        assert "Post" in converted
        
        # Should convert Django field types
        assert "CharField" in converted
        assert "TextField" in converted
        assert "DateTimeField" in converted
        
        # Should handle Meta classes
        assert "ordering" in converted or "__table_args__" in converted
    
    def test_convert_field_types(self, model_converter):
        """Test field type conversion."""
        flask_field = "db.Column(db.String(120), unique=True, nullable=False)"
        converted = model_converter._convert_field_type(flask_field, "flask")
        
        assert "String" in converted or "CharField" in converted
        assert "unique=True" in converted
        assert "nullable=False" in converted or "null=False" in converted
    
    def test_convert_relationships(self, model_converter):
        """Test relationship conversion."""
        flask_relationship = "db.relationship('Post', backref='author', lazy=True)"
        converted = model_converter._convert_relationship(flask_relationship, "flask")
        
        assert "relationship" in converted or "ForeignKey" in converted
        assert "Post" in converted
        assert "author" in converted


class TestASTTransformer:
    """Test AST-based code transformation following SRP."""
    
    @pytest.fixture
    def ast_transformer(self):
        """Create AST transformer for testing."""
        return ASTTransformer()
    
    @pytest.fixture
    def sample_flask_code(self):
        """Sample Flask code for AST transformation."""
        return """
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        return jsonify({'users': []})
    data = request.get_json()
    return jsonify({'created': True}), 201
"""
    
    def test_transformer_initialization(self, ast_transformer):
        """Test AST transformer initializes correctly."""
        assert ast_transformer is not None
        assert hasattr(ast_transformer, 'transform_code')
        assert hasattr(ast_transformer, 'replace_imports')
        assert hasattr(ast_transformer, 'replace_decorators')
        assert hasattr(ast_transformer, 'replace_function_calls')
    
    def test_parse_and_transform_code(self, ast_transformer, sample_flask_code):
        """Test parsing and transforming code via AST."""
        transformations = {
            "imports": {
                "flask": "beginnings",
                "Flask": "create_app",
                "request": "request",
                "jsonify": "jsonify"
            },
            "decorators": {
                "app.route": "app.route"
            },
            "function_calls": {
                "Flask(__name__)": "create_app()"
            }
        }
        
        transformed = ast_transformer.transform_code(sample_flask_code, transformations)
        
        assert "beginnings" in transformed
        assert "create_app" in transformed
        assert "@app.route" in transformed
        assert "request." in transformed
    
    def test_replace_imports(self, ast_transformer):
        """Test import replacement."""
        code = "from flask import Flask, request\nimport flask_sqlalchemy"
        
        import_map = {
            "flask": "beginnings",
            "flask_sqlalchemy": "beginnings.extensions.database"
        }
        
        transformed = ast_transformer.replace_imports(code, import_map)
        
        assert "from beginnings import" in transformed
        assert "beginnings.extensions.database" in transformed
    
    def test_replace_decorators(self, ast_transformer):
        """Test decorator replacement."""
        code = """
@app.route('/users')
@login_required
def users():
    return {}
"""
        
        decorator_map = {
            "login_required": "auth_required"
        }
        
        transformed = ast_transformer.replace_decorators(code, decorator_map)
        
        assert "@auth_required" in transformed
        assert "@app.route('/users')" in transformed
    
    def test_replace_function_calls(self, ast_transformer):
        """Test function call replacement."""
        code = "app = Flask(__name__)\nresult = request.get_json()"
        
        function_map = {
            "Flask": "create_app",
            "request.get_json": "request.json"
        }
        
        transformed = ast_transformer.replace_function_calls(code, function_map)
        
        assert "create_app" in transformed
        assert "request.json" in transformed
    
    def test_preserve_code_structure(self, ast_transformer, sample_flask_code):
        """Test that code structure is preserved during transformation."""
        transformations = {
            "imports": {"flask": "beginnings"},
            "decorators": {},
            "function_calls": {}
        }
        
        transformed = ast_transformer.transform_code(sample_flask_code, transformations)
        
        # Should preserve function structure
        assert "def users():" in transformed
        assert "if request.method == 'GET':" in transformed
        assert "return" in transformed
        
        # Should preserve indentation and formatting
        lines = transformed.split('\n')
        indented_lines = [line for line in lines if line.startswith('    ')]
        assert len(indented_lines) > 0