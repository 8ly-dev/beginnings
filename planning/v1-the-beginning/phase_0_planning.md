# Phase 0: Project Foundation Setup

## Overview
Establish the project foundation with modern Python tooling, project structure, and development environment. This phase creates the base infrastructure that all subsequent phases will build upon.

## AI Agent Directives and Tool Usage

### uv Package Manager
- **Primary Tool**: Use `uv` for all Python package management and virtual environment operations
- **Project Initialization**: `uv init beginnings --lib` for library structure
- **Dependency Management**: Use `uv add` for adding dependencies, `uv remove` for removal
- **Development Dependencies**: Use `uv add --dev` for test/dev-only packages
- **Virtual Environment**: `uv venv` creates isolated environment, `uv pip` for pip operations
- **Lock Files**: `uv.lock` ensures reproducible builds across environments
- **Scripts**: Define common commands in `pyproject.toml` scripts section

### Best Practices for AI Agent
- **Function Length**: Maximum 20 lines per function, prefer smaller focused functions
- **Class Length**: Maximum 200 lines per class, break into smaller classes if exceeded
- **Naming**: Favor descriptive names over concise (`load_configuration_with_includes` vs `load_config`)
- **Type Hints**: All functions must have complete type hints including return types
- **Docstrings**: All public functions/classes require comprehensive docstrings
- **Error Handling**: Prefer specific exceptions over generic Exception catches
- **Import Organization**: Group imports (stdlib, third-party, local) with blank lines between

## Stage 1: Test-Driven Development Setup

### 1.1 Testing Framework Selection
- **Primary Framework**: pytest for all testing
- **Coverage Tool**: pytest-cov for coverage reporting
- **Test Structure**: Mirror source structure in tests/ directory
- **Naming Convention**: `test_*.py` files, `test_*` functions

### 1.2 Test Infrastructure Planning
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions
- **Configuration Tests**: Test config loading, merging, validation
- **Environment Tests**: Test environment detection and overrides
- **Security Tests**: Test configuration conflict detection

### 1.3 Quality Assurance Tools
- **Linting**: ruff for fast Python linting
- **Type Checking**: mypy for static type analysis  
- **Formatting**: ruff format for consistent code style
- **Security**: bandit for security vulnerability scanning

## Stage 2: Project Structure Creation

### 2.1 Directory Structure
```
beginnings/
├── src/
│   └── beginnings/
│       ├── __init__.py           # Main App class export
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py         # Configuration loading logic
│       │   └── validator.py     # Configuration validation
│       ├── routing/
│       │   ├── __init__.py
│       │   ├── html.py          # HTML router implementation
│       │   └── api.py           # API router implementation
│       └── extensions/
│           ├── __init__.py
│           ├── base.py          # Base extension interface
│           └── loader.py        # Extension loading mechanism
├── tests/
│   ├── __init__.py
│   ├── config/
│   ├── routing/
│   ├── extensions/
│   └── fixtures/                # Test configuration files
├── docs/                        # Documentation
├── examples/                    # Example projects
├── pyproject.toml               # Project configuration
├── README.md
└── .gitignore
```

### 2.2 Package Configuration
- **Build System**: Use hatchling as build backend
- **Version Management**: Single source version in `__init__.py`
- **Entry Points**: CLI commands defined in pyproject.toml
- **Dependencies**: Minimal core dependencies (FastAPI, PyYAML, uvicorn)

## Stage 3: Development Environment Setup

### 3.1 Virtual Environment Configuration
- Create isolated environment with `uv venv`
- Install development dependencies: pytest, ruff, mypy, bandit
- Configure IDE integration for type checking and linting

### 3.2 Git Configuration
- Initialize repository with appropriate .gitignore
- Set up pre-commit hooks for linting and testing
- Configure branch protection and PR requirements

### 3.3 Continuous Integration Planning
- Test matrix: Python 3.9, 3.10, 3.11, 3.12
- Coverage requirements: 100% for new code, minimum 95% overall
- Security scanning in CI pipeline
- Type checking enforcement

## Stage 4: Core Dependencies Setup

### 4.1 Required Dependencies
- **FastAPI**: Web framework foundation (latest stable)
- **PyYAML**: Configuration file parsing
- **uvicorn**: ASGI server for development
- **pydantic**: Data validation and settings management

### 4.2 Development Dependencies
- **pytest**: Testing framework with async support
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **ruff**: Linting and formatting
- **mypy**: Static type checking
- **bandit**: Security analysis

### 4.3 Optional Dependencies
- Define optional dependency groups for extensions
- Database group: asyncpg, sqlalchemy
- Cache group: redis, valkey-py
- Auth group: python-jose, passlib

## Stage 5: Basic Project Configuration

### 5.1 pyproject.toml Configuration
```toml
[project]
name = "beginnings"
description = "A thoughtful web framework built on FastAPI"
requires-python = ">=3.9"
dependencies = [
    "fastapi>=0.104.0",
    "PyYAML>=6.0",
    "uvicorn>=0.24.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "bandit>=1.7.0",
]

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.mypy]
python_version = "3.9"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 5.2 Development Scripts
- `uv run pytest`: Run test suite
- `uv run pytest --cov`: Run with coverage
- `uv run ruff check`: Lint code
- `uv run mypy`: Type check
- `uv run bandit -r src/`: Security scan

## Stage 6: Verification and Validation

### 6.1 Project Structure Verification
- [ ] All directories created with proper __init__.py files
- [ ] pyproject.toml properly configured with all dependencies
- [ ] Virtual environment activated and dependencies installed
- [ ] Git repository initialized with appropriate .gitignore

### 6.2 Tool Integration Verification
- [ ] `uv` commands work for package management
- [ ] `pytest` discovers and runs (empty) test suite
- [ ] `ruff` lints code without errors
- [ ] `mypy` type checks without errors
- [ ] `bandit` security scan runs without issues

### 6.3 Development Workflow Verification
- [ ] Can add/remove dependencies with uv
- [ ] Test discovery works in IDE
- [ ] Linting and type checking integrate with IDE
- [ ] Pre-commit hooks (if configured) function properly

### 6.4 Documentation and Standards Verification
- [ ] README.md contains project overview and setup instructions
- [ ] All placeholder modules contain proper docstrings
- [ ] Code style guidelines documented
- [ ] Contributing guidelines established

## Success Criteria
- ✅ Project structure matches planned architecture
- ✅ All development tools properly configured and functional
- ✅ Test infrastructure ready for TDD development
- ✅ Code quality tools enforcing standards
- ✅ Virtual environment isolated and reproducible
- ✅ Documentation foundation established

## Security Checklist
- [ ] No secrets or credentials in version control
- [ ] .gitignore prevents accidental credential commits
- [ ] Security scanning integrated into development workflow
- [ ] Dependency vulnerability checking enabled

## Clean Code Checklist
- [ ] Consistent naming conventions established
- [ ] Maximum function/class length limits defined
- [ ] Type hint requirements documented
- [ ] Import organization standards specified
- [ ] Docstring requirements clarified

## Phase 0 Completion Criteria
Phase 0 is complete when:
1. All verification checklists pass
2. Development environment is fully functional
3. Code quality standards are enforced
4. Project structure supports planned architecture
5. AI agent has clear directives for subsequent phases