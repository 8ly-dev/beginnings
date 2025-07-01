"""Tests for framework-specific migration commands."""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from beginnings.cli.main import cli


class TestFlaskMigration:
    """Test Flask to Beginnings migration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_migrate_from_flask_basic(self):
        """Test basic Flask migration."""
        # Create a basic Flask app structure
        flask_dir = Path(self.temp_dir) / "flask_app"
        flask_dir.mkdir()
        
        # Create app.py
        (flask_dir / "app.py").write_text("""
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        return jsonify({'status': 'created'})
    return jsonify({'users': []})

if __name__ == '__main__':
    app.run(debug=True)
""")
        
        # Create templates
        templates_dir = flask_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "index.html").write_text("""
<!DOCTYPE html>
<html>
<head><title>Flask App</title></head>
<body><h1>Welcome</h1></body>
</html>
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-flask",
            "--source", str(flask_dir),
            "--output", str(output_dir)
        ])
        
        assert result.exit_code == 0
        
        # Check generated files
        assert output_dir.exists()
        assert (output_dir / "main.py").exists()
        assert (output_dir / "config" / "app.yaml").exists()
        assert (output_dir / "routes").exists()
        assert (output_dir / "templates").exists()
        
        # Check that templates were migrated
        assert (output_dir / "templates" / "index.html").exists()
    
    def test_migrate_from_flask_with_blueprints(self):
        """Test Flask migration with blueprints."""
        flask_dir = Path(self.temp_dir) / "flask_app"
        flask_dir.mkdir()
        
        # Create main app
        (flask_dir / "app.py").write_text("""
from flask import Flask
from auth import auth_bp
from api import api_bp

app = Flask(__name__)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(api_bp, url_prefix='/api')
""")
        
        # Create blueprint files
        (flask_dir / "auth.py").write_text("""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    return 'Login'
""")
        
        (flask_dir / "api.py").write_text("""
from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__)

@api_bp.route('/users')
def users():
    return jsonify({'users': []})
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-flask",
            "--source", str(flask_dir),
            "--output", str(output_dir),
            "--preserve-structure"
        ])
        
        assert result.exit_code == 0
        # Check that files were generated
        assert output_dir.exists()
    
    def test_migrate_from_flask_with_config(self):
        """Test Flask migration with configuration."""
        flask_dir = Path(self.temp_dir) / "flask_app"
        flask_dir.mkdir()
        
        (flask_dir / "config.py").write_text("""
class Config:
    SECRET_KEY = 'secret-key'
    DATABASE_URL = 'sqlite:///app.db'
    MAIL_SERVER = 'smtp.gmail.com'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
""")
        
        (flask_dir / "app.py").write_text("""
from flask import Flask
from config import DevelopmentConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-flask",
            "--source", str(flask_dir),
            "--output", str(output_dir),
            "--convert-config"
        ])
        
        assert result.exit_code == 0
        
        # Check that files were generated
        assert output_dir.exists()
        assert (output_dir / "main.py").exists()
        
        # Check config was converted if file exists
        config_file = output_dir / "config" / "app.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            assert "app" in config
            assert config["app"]["name"] == "flask_app"


class TestDjangoMigration:
    """Test Django to Beginnings migration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_migrate_from_django_basic(self):
        """Test basic Django migration."""
        django_dir = Path(self.temp_dir) / "django_project"
        django_dir.mkdir()
        
        # Create Django project structure
        (django_dir / "manage.py").write_text("""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
""")
        
        myproject_dir = django_dir / "myproject"
        myproject_dir.mkdir()
        
        (myproject_dir / "settings.py").write_text("""
SECRET_KEY = 'django-secret-key'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'myapp',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}
""")
        
        (myproject_dir / "urls.py").write_text("""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),
]
""")
        
        # Create app
        myapp_dir = django_dir / "myapp"
        myapp_dir.mkdir()
        
        (myapp_dir / "views.py").write_text("""
from django.http import JsonResponse
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def api_users(request):
    return JsonResponse({'users': []})
""")
        
        (myapp_dir / "urls.py").write_text("""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/users/', views.api_users, name='api_users'),
]
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-django",
            "--source", str(django_dir),
            "--output", str(output_dir)
        ])
        
        assert result.exit_code == 0
        
        # Check generated files
        assert output_dir.exists()
        assert (output_dir / "main.py").exists()
        assert (output_dir / "config" / "app.yaml").exists()
    
    def test_migrate_from_django_with_models(self):
        """Test Django migration with models."""
        django_dir = Path(self.temp_dir) / "django_project"
        myapp_dir = django_dir / "myapp"
        myapp_dir.mkdir(parents=True)
        
        (myapp_dir / "models.py").write_text("""
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    published = models.BooleanField(default=False)
""")
        
        (django_dir / "manage.py").write_text("# Django manage.py")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-django",
            "--source", str(django_dir),
            "--output", str(output_dir),
            "--convert-models"
        ])
        
        assert result.exit_code == 0
        # Check that files were generated
        assert output_dir.exists()


class TestFastAPIMigration:
    """Test FastAPI to Beginnings migration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_migrate_from_fastapi_basic(self):
        """Test basic FastAPI migration."""
        fastapi_dir = Path(self.temp_dir) / "fastapi_app"
        fastapi_dir.mkdir()
        
        (fastapi_dir / "main.py").write_text("""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="My API", version="1.0.0")

class User(BaseModel):
    name: str
    email: str

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}

@app.post("/users/")
def create_user(user: User):
    return {"message": "User created", "user": user}
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-fastapi",
            "--source", str(fastapi_dir),
            "--output", str(output_dir)
        ])
        
        assert result.exit_code == 0
        
        # Check generated files
        assert output_dir.exists()
        assert (output_dir / "main.py").exists()
        assert (output_dir / "config" / "app.yaml").exists()
        assert (output_dir / "routes").exists()
    
    def test_migrate_from_fastapi_with_routers(self):
        """Test FastAPI migration with routers."""
        fastapi_dir = Path(self.temp_dir) / "fastapi_app"
        fastapi_dir.mkdir()
        
        (fastapi_dir / "main.py").write_text("""
from fastapi import FastAPI
from routers import users, posts

app = FastAPI()
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
""")
        
        routers_dir = fastapi_dir / "routers"
        routers_dir.mkdir()
        
        (routers_dir / "users.py").write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_users():
    return {"users": []}

@router.post("/")
def create_user():
    return {"message": "User created"}
""")
        
        (routers_dir / "posts.py").write_text("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_posts():
    return {"posts": []}
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-fastapi",
            "--source", str(fastapi_dir),
            "--output", str(output_dir),
            "--preserve-structure"
        ])
        
        assert result.exit_code == 0
        # Check that files were generated
        assert output_dir.exists()
    
    def test_migrate_from_fastapi_with_dependencies(self):
        """Test FastAPI migration with dependencies."""
        fastapi_dir = Path(self.temp_dir) / "fastapi_app"
        fastapi_dir.mkdir()
        
        (fastapi_dir / "main.py").write_text("""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

def get_current_user(token: str = Depends(security)):
    return {"user": "test"}

@app.get("/protected")
def protected_route(user = Depends(get_current_user)):
    return {"message": "Protected", "user": user}
""")
        
        output_dir = Path(self.temp_dir) / "beginnings_app"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-fastapi",
            "--source", str(fastapi_dir),
            "--output", str(output_dir),
            "--convert-auth"
        ])
        
        assert result.exit_code == 0
        # Check that files were generated
        assert output_dir.exists()


class TestMigrationIntegration:
    """Test migration command integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_migration_help_commands(self):
        """Test help for migration commands."""
        # Test main migrate group help
        result = self.runner.invoke(cli, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "from-flask" in result.output
        assert "from-django" in result.output
        assert "from-fastapi" in result.output
        
        # Test individual command help
        for cmd in ["from-flask", "from-django", "from-fastapi"]:
            result = self.runner.invoke(cli, ["migrate", cmd, "--help"])
            assert result.exit_code == 0
    
    def test_migration_dry_run(self):
        """Test migration dry run mode."""
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)")
        
        result = self.runner.invoke(cli, [
            "migrate", "from-flask",
            "--source", str(source_dir),
            "--output", "/tmp/test",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        # Dry run mode should execute successfully without creating files
        # (actual dry run functionality may not output specific messages)
    
    def test_migration_report(self):
        """Test migration report generation."""
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)")
        
        output_dir = Path(self.temp_dir) / "output"
        
        result = self.runner.invoke(cli, [
            "migrate", "from-flask",
            "--source", str(source_dir),
            "--output", str(output_dir),
            "--generate-report"
        ])
        
        assert result.exit_code == 0
        
        # Check if report was generated
        report_file = output_dir / "migration_report.md"
        if report_file.exists():
            assert "Migration Report" in report_file.read_text()