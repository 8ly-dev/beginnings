"""Extension quality validation for Beginnings framework.

This module provides comprehensive quality validation for extensions including
code quality analysis, security scanning, documentation validation, and
compliance checking. Follows SOLID principles.
"""

from __future__ import annotations

import ast
import re
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import subprocess
import hashlib


@dataclass
class QualityScore:
    """Quality score for a specific aspect."""
    
    score: float  # 0-100
    weight: float  # 0-1
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of extension quality validation."""
    
    overall_score: float
    is_compliant: bool
    metrics: Dict[str, QualityScore]
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validation_time: float = 0.0
    validated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CodeQualityAnalyzer:
    """Analyzes code quality metrics.
    
    Follows Single Responsibility Principle - only handles code quality analysis.
    """
    
    def __init__(self):
        """Initialize code quality analyzer."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_code_quality(self, extension_path: Path) -> QualityScore:
        """Analyze code quality for extension.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Quality score for code quality
        """
        issues = []
        recommendations = []
        details = {}
        
        # Find Python files
        python_files = list(extension_path.rglob("*.py"))
        if not python_files:
            return QualityScore(
                score=0,
                weight=0.25,
                issues=["No Python files found"],
                recommendations=["Add Python implementation files"]
            )
        
        # Analyze each Python file
        total_score = 0
        file_scores = []
        
        for py_file in python_files:
            if self._should_analyze_file(py_file):
                file_score = self._analyze_file(py_file)
                file_scores.append(file_score)
                total_score += file_score['score']
        
        if file_scores:
            average_score = total_score / len(file_scores)
            
            # Aggregate issues and recommendations
            for file_data in file_scores:
                issues.extend(file_data.get('issues', []))
                recommendations.extend(file_data.get('recommendations', []))
            
            details = {
                'files_analyzed': len(file_scores),
                'average_score': average_score,
                'file_scores': file_scores[:5]  # Limit details
            }
        else:
            average_score = 0
            issues.append("No analyzable Python files found")
        
        return QualityScore(
            score=average_score,
            weight=0.25,
            issues=issues[:10],  # Limit issues
            recommendations=recommendations[:10],  # Limit recommendations
            details=details
        )
    
    def _should_analyze_file(self, file_path: Path) -> bool:
        """Check if file should be analyzed."""
        # Skip test files, __pycache__, migrations, etc.
        skip_patterns = ['test_', '__pycache__', 'migrations', '.pyc']
        return not any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze individual Python file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Parse AST
            tree = ast.parse(content)
            
            # Calculate metrics
            complexity = self._calculate_complexity(tree)
            maintainability = self._calculate_maintainability(content, tree)
            documentation = self._calculate_documentation_score(content, tree)
            
            # Overall file score
            score = (complexity * 0.4 + maintainability * 0.4 + documentation * 0.2)
            
            issues = []
            recommendations = []
            
            if complexity < 70:
                issues.append(f"High complexity in {file_path.name}")
                recommendations.append("Consider breaking down complex functions")
            
            if maintainability < 70:
                issues.append(f"Low maintainability in {file_path.name}")
                recommendations.append("Improve code structure and naming")
            
            if documentation < 60:
                issues.append(f"Insufficient documentation in {file_path.name}")
                recommendations.append("Add docstrings and comments")
            
            return {
                'file': str(file_path.relative_to(file_path.parents[2])),
                'score': score,
                'complexity': complexity,
                'maintainability': maintainability,
                'documentation': documentation,
                'issues': issues,
                'recommendations': recommendations
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze {file_path}: {e}")
            return {
                'file': str(file_path.relative_to(file_path.parents[2])),
                'score': 50,  # Default score for unparseable files
                'issues': [f"Could not analyze {file_path.name}: {str(e)}"],
                'recommendations': ["Ensure file has valid Python syntax"]
            }
    
    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate cyclomatic complexity score."""
        complexity_count = 0
        total_functions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                # Count decision points
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                        complexity_count += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity_count += len(child.values) - 1
        
        if total_functions == 0:
            return 100  # No functions to analyze
        
        avg_complexity = complexity_count / total_functions
        
        # Score based on average complexity (lower is better)
        if avg_complexity <= 3:
            return 100
        elif avg_complexity <= 5:
            return 90
        elif avg_complexity <= 8:
            return 75
        elif avg_complexity <= 12:
            return 60
        else:
            return 40
    
    def _calculate_maintainability(self, content: str, tree: ast.AST) -> float:
        """Calculate maintainability score."""
        lines = content.splitlines()
        total_lines = len(lines)
        
        if total_lines == 0:
            return 0
        
        # Count meaningful lines (non-blank, non-comment)
        code_lines = 0
        comment_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                if stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
        
        # Calculate various maintainability factors
        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
        
        # Count long lines (over 100 characters)
        long_lines = sum(1 for line in lines if len(line) > 100)
        long_line_ratio = long_lines / total_lines if total_lines > 0 else 0
        
        # Count functions and classes
        functions = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        
        # Score based on maintainability factors
        score = 100
        
        # Penalize low comment ratio
        if comment_ratio < 0.1:
            score -= 20
        elif comment_ratio < 0.2:
            score -= 10
        
        # Penalize long lines
        if long_line_ratio > 0.2:
            score -= 20
        elif long_line_ratio > 0.1:
            score -= 10
        
        # Penalize very large files
        if total_lines > 500:
            score -= 15
        elif total_lines > 300:
            score -= 10
        
        return max(0, score)
    
    def _calculate_documentation_score(self, content: str, tree: ast.AST) -> float:
        """Calculate documentation coverage score."""
        # Count docstrings
        docstring_count = 0
        total_definitions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_definitions += 1
                # Check if first statement is a string (docstring)
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    docstring_count += 1
        
        if total_definitions == 0:
            return 100  # No definitions to document
        
        docstring_ratio = docstring_count / total_definitions
        
        # Base score from docstring coverage
        score = docstring_ratio * 100
        
        # Bonus for module docstring
        if content.strip().startswith('"""') or content.strip().startswith("'''"):
            score = min(100, score + 10)
        
        # Bonus for type hints
        has_type_hints = 'typing' in content or '->' in content or ':' in content
        if has_type_hints:
            score = min(100, score + 5)
        
        return score


class SecurityAnalyzer:
    """Analyzes security aspects of extensions.
    
    Follows Single Responsibility Principle - only handles security analysis.
    """
    
    def __init__(self):
        """Initialize security analyzer."""
        self.logger = logging.getLogger(__name__)
        self.security_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*["\'][^"\']*%[^"\']*["\']',
                r'cursor\.execute\s*\(\s*f["\']',
                r'\.format\s*\([^)]*\)\s*\)',
            ],
            'command_injection': [
                r'os\.system\s*\(',
                r'subprocess\.[a-z]*\([^)]*shell\s*=\s*True',
                r'eval\s*\(',
                r'exec\s*\(',
            ],
            'path_traversal': [
                r'open\s*\([^)]*\.\./[^)]*\)',
                r'Path\s*\([^)]*\.\./[^)]*\)',
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
            ]
        }
    
    def analyze_security(self, extension_path: Path) -> QualityScore:
        """Analyze security for extension.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Quality score for security
        """
        issues = []
        recommendations = []
        details = {}
        
        # Find Python files
        python_files = list(extension_path.rglob("*.py"))
        
        security_issues = []
        vulnerability_count = 0
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                file_issues = self._scan_file_security(py_file, content)
                security_issues.extend(file_issues)
                vulnerability_count += len(file_issues)
            except Exception as e:
                self.logger.warning(f"Failed to scan {py_file}: {e}")
        
        # Check dependencies
        dependency_issues = self._check_dependencies(extension_path)
        security_issues.extend(dependency_issues)
        
        # Check permissions and metadata
        metadata_issues = self._check_metadata_security(extension_path)
        security_issues.extend(metadata_issues)
        
        # Calculate score
        if vulnerability_count == 0 and not dependency_issues and not metadata_issues:
            score = 100
        elif vulnerability_count <= 2 and len(dependency_issues) <= 1:
            score = 85
        elif vulnerability_count <= 5 and len(dependency_issues) <= 3:
            score = 70
        else:
            score = 50
        
        # Aggregate issues and recommendations
        for issue in security_issues[:10]:  # Limit issues
            issues.append(issue['description'])
            recommendations.extend(issue.get('recommendations', []))
        
        details = {
            'vulnerability_count': vulnerability_count,
            'dependency_issues': len(dependency_issues),
            'metadata_issues': len(metadata_issues),
            'issues_by_type': self._categorize_issues(security_issues)
        }
        
        return QualityScore(
            score=score,
            weight=0.25,
            issues=issues,
            recommendations=recommendations[:10],
            details=details
        )
    
    def _scan_file_security(self, file_path: Path, content: str) -> List[Dict[str, Any]]:
        """Scan individual file for security issues."""
        issues = []
        
        for issue_type, patterns in self.security_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': issue_type,
                        'file': str(file_path.relative_to(file_path.parents[2])),
                        'line': line_num,
                        'description': f"{issue_type} detected in {file_path.name}:{line_num}",
                        'pattern': pattern,
                        'recommendations': self._get_security_recommendations(issue_type)
                    })
        
        return issues
    
    def _check_dependencies(self, extension_path: Path) -> List[Dict[str, Any]]:
        """Check for security issues in dependencies."""
        issues = []
        
        # Check requirements.txt
        req_file = extension_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text()
                # Look for known vulnerable packages (simplified check)
                vulnerable_patterns = [
                    r'django<[2-9]',  # Old Django versions
                    r'flask<[1-9]',   # Old Flask versions
                    r'requests<2\.20', # Old requests versions
                ]
                
                for pattern in vulnerable_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append({
                            'type': 'vulnerable_dependency',
                            'description': f"Potentially vulnerable dependency detected",
                            'recommendations': ["Update to latest secure version"]
                        })
            except Exception:
                pass
        
        # Check for setup.py with unsafe patterns
        setup_file = extension_path / "setup.py"
        if setup_file.exists():
            try:
                content = setup_file.read_text()
                if 'download_url' in content or 'dependency_links' in content:
                    issues.append({
                        'type': 'unsafe_setup',
                        'description': "Potentially unsafe setup.py configuration",
                        'recommendations': ["Use secure package installation methods"]
                    })
            except Exception:
                pass
        
        return issues
    
    def _check_metadata_security(self, extension_path: Path) -> List[Dict[str, Any]]:
        """Check metadata for security issues."""
        issues = []
        
        # Check extension.yaml for security settings
        metadata_file = extension_path / "extension.yaml"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = yaml.safe_load(f)
                
                # Check for overly broad permissions
                permissions = metadata.get('permissions', [])
                if 'admin' in permissions or 'root' in permissions:
                    issues.append({
                        'type': 'excessive_permissions',
                        'description': "Extension requests excessive permissions",
                        'recommendations': ["Use minimal required permissions"]
                    })
                
                # Check for missing security metadata
                if 'security' not in metadata:
                    issues.append({
                        'type': 'missing_security_metadata',
                        'description': "Missing security declarations",
                        'recommendations': ["Add security section to extension.yaml"]
                    })
                    
            except Exception:
                pass
        
        return issues
    
    def _get_security_recommendations(self, issue_type: str) -> List[str]:
        """Get recommendations for security issue type."""
        recommendations = {
            'sql_injection': [
                "Use parameterized queries",
                "Validate and sanitize user input",
                "Use ORM instead of raw SQL"
            ],
            'command_injection': [
                "Avoid shell=True in subprocess calls",
                "Validate command arguments",
                "Use subprocess.run with list arguments"
            ],
            'path_traversal': [
                "Validate file paths",
                "Use os.path.abspath() and check paths",
                "Restrict file access to allowed directories"
            ],
            'hardcoded_secrets': [
                "Use environment variables for secrets",
                "Use configuration management",
                "Never commit secrets to version control"
            ]
        }
        return recommendations.get(issue_type, ["Review and fix security issue"])
    
    def _categorize_issues(self, security_issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize security issues by type."""
        categories = {}
        for issue in security_issues:
            issue_type = issue.get('type', 'unknown')
            categories[issue_type] = categories.get(issue_type, 0) + 1
        return categories


class DocumentationAnalyzer:
    """Analyzes documentation quality and completeness.
    
    Follows Single Responsibility Principle - only handles documentation analysis.
    """
    
    def __init__(self):
        """Initialize documentation analyzer."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_documentation(self, extension_path: Path) -> QualityScore:
        """Analyze documentation for extension.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Quality score for documentation
        """
        issues = []
        recommendations = []
        details = {}
        
        # Check for documentation files
        doc_files = self._find_documentation_files(extension_path)
        
        # Analyze README
        readme_score = self._analyze_readme(extension_path)
        
        # Analyze API documentation
        api_doc_score = self._analyze_api_documentation(extension_path)
        
        # Analyze code documentation
        code_doc_score = self._analyze_code_documentation(extension_path)
        
        # Calculate overall documentation score
        overall_score = (readme_score * 0.4 + api_doc_score * 0.3 + code_doc_score * 0.3)
        
        # Generate issues and recommendations
        if readme_score < 70:
            issues.append("README documentation is insufficient")
            recommendations.append("Improve README with better descriptions and examples")
        
        if api_doc_score < 70:
            issues.append("API documentation is lacking")
            recommendations.append("Add comprehensive API documentation")
        
        if code_doc_score < 70:
            issues.append("Code documentation needs improvement")
            recommendations.append("Add docstrings and inline comments")
        
        details = {
            'doc_files_found': len(doc_files),
            'readme_score': readme_score,
            'api_doc_score': api_doc_score,
            'code_doc_score': code_doc_score,
            'documentation_files': [str(f.relative_to(extension_path)) for f in doc_files]
        }
        
        return QualityScore(
            score=overall_score,
            weight=0.2,
            issues=issues,
            recommendations=recommendations,
            details=details
        )
    
    def _find_documentation_files(self, extension_path: Path) -> List[Path]:
        """Find documentation files in extension."""
        doc_patterns = ['*.md', '*.rst', '*.txt']
        doc_files = []
        
        for pattern in doc_patterns:
            doc_files.extend(extension_path.rglob(pattern))
        
        # Also look in docs/ directory
        docs_dir = extension_path / "docs"
        if docs_dir.exists():
            for pattern in doc_patterns:
                doc_files.extend(docs_dir.rglob(pattern))
        
        return doc_files
    
    def _analyze_readme(self, extension_path: Path) -> float:
        """Analyze README file quality."""
        readme_files = [
            extension_path / "README.md",
            extension_path / "README.rst",
            extension_path / "README.txt",
            extension_path / "readme.md"
        ]
        
        readme_file = None
        for readme in readme_files:
            if readme.exists():
                readme_file = readme
                break
        
        if not readme_file:
            return 0
        
        try:
            content = readme_file.read_text(encoding='utf-8')
            
            score = 0
            
            # Check for basic sections
            required_sections = [
                r'#.*installation',
                r'#.*usage',
                r'#.*description',
                r'#.*example'
            ]
            
            for section in required_sections:
                if re.search(section, content, re.IGNORECASE):
                    score += 25
            
            # Bonus for additional useful sections
            bonus_sections = [
                r'#.*configuration',
                r'#.*api.*reference',
                r'#.*contributing',
                r'#.*license'
            ]
            
            for section in bonus_sections:
                if re.search(section, content, re.IGNORECASE):
                    score += 5
            
            # Bonus for code examples
            if '```' in content or '.. code-block::' in content:
                score += 10
            
            return min(100, score)
            
        except Exception:
            return 20  # Basic score for existing but unreadable README
    
    def _analyze_api_documentation(self, extension_path: Path) -> float:
        """Analyze API documentation quality."""
        # Look for API documentation files
        api_docs = []
        docs_dir = extension_path / "docs"
        
        if docs_dir.exists():
            api_patterns = ['*api*', '*reference*', '*guide*']
            for pattern in api_patterns:
                api_docs.extend(docs_dir.rglob(f"{pattern}.md"))
                api_docs.extend(docs_dir.rglob(f"{pattern}.rst"))
        
        if not api_docs:
            return 50  # Default score if no specific API docs
        
        score = 60  # Base score for having API docs
        
        for doc_file in api_docs:
            try:
                content = doc_file.read_text(encoding='utf-8')
                
                # Check for comprehensive API coverage
                if len(content) > 1000:  # Substantial content
                    score += 20
                
                # Check for examples in API docs
                if 'example' in content.lower() and '```' in content:
                    score += 20
                
                break  # Only analyze first API doc file
                
            except Exception:
                continue
        
        return min(100, score)
    
    def _analyze_code_documentation(self, extension_path: Path) -> float:
        """Analyze code documentation quality."""
        python_files = list(extension_path.rglob("*.py"))
        
        if not python_files:
            return 0
        
        total_score = 0
        analyzed_files = 0
        
        for py_file in python_files:
            if '__pycache__' not in str(py_file) and 'test_' not in py_file.name:
                try:
                    content = py_file.read_text(encoding='utf-8')
                    tree = ast.parse(content)
                    
                    # Count docstrings vs definitions
                    docstring_count = 0
                    total_definitions = 0
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            total_definitions += 1
                            # Check for docstring
                            if (node.body and 
                                isinstance(node.body[0], ast.Expr) and 
                                isinstance(node.body[0].value, ast.Constant) and 
                                isinstance(node.body[0].value.value, str)):
                                docstring_count += 1
                    
                    if total_definitions > 0:
                        file_score = (docstring_count / total_definitions) * 100
                        total_score += file_score
                        analyzed_files += 1
                        
                except Exception:
                    continue
        
        if analyzed_files == 0:
            return 50  # Default if no files could be analyzed
        
        return total_score / analyzed_files


class TestingAnalyzer:
    """Analyzes testing coverage and quality.
    
    Follows Single Responsibility Principle - only handles testing analysis.
    """
    
    def __init__(self):
        """Initialize testing analyzer."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_testing(self, extension_path: Path) -> QualityScore:
        """Analyze testing for extension.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Quality score for testing
        """
        issues = []
        recommendations = []
        details = {}
        
        # Find test files
        test_files = self._find_test_files(extension_path)
        
        # Find source files
        source_files = self._find_source_files(extension_path)
        
        if not test_files:
            return QualityScore(
                score=0,
                weight=0.25,
                issues=["No test files found"],
                recommendations=[
                    "Add unit tests for your extension",
                    "Use pytest for testing framework",
                    "Aim for >80% test coverage"
                ],
                details={'test_files_found': 0, 'source_files_found': len(source_files)}
            )
        
        # Analyze test coverage
        coverage_score = self._estimate_test_coverage(test_files, source_files)
        
        # Analyze test quality
        quality_score = self._analyze_test_quality(test_files)
        
        # Calculate overall testing score
        overall_score = (coverage_score * 0.6 + quality_score * 0.4)
        
        if coverage_score < 50:
            issues.append("Low test coverage")
            recommendations.append("Add more comprehensive tests")
        
        if quality_score < 70:
            issues.append("Test quality could be improved")
            recommendations.append("Improve test structure and assertions")
        
        details = {
            'test_files_found': len(test_files),
            'source_files_found': len(source_files),
            'estimated_coverage': coverage_score,
            'test_quality': quality_score,
            'test_files': [str(f.relative_to(extension_path)) for f in test_files]
        }
        
        return QualityScore(
            score=overall_score,
            weight=0.25,
            issues=issues,
            recommendations=recommendations,
            details=details
        )
    
    def _find_test_files(self, extension_path: Path) -> List[Path]:
        """Find test files in extension."""
        test_files = []
        
        # Look for test files
        test_patterns = ['test_*.py', '*_test.py', 'tests.py']
        for pattern in test_patterns:
            test_files.extend(extension_path.rglob(pattern))
        
        # Look in tests/ directory
        tests_dir = extension_path / "tests"
        if tests_dir.exists():
            test_files.extend(tests_dir.rglob("*.py"))
        
        return test_files
    
    def _find_source_files(self, extension_path: Path) -> List[Path]:
        """Find source files to test."""
        source_files = []
        
        for py_file in extension_path.rglob("*.py"):
            # Skip test files and __pycache__
            if ('test' not in str(py_file) and 
                '__pycache__' not in str(py_file) and
                py_file.name != 'setup.py'):
                source_files.append(py_file)
        
        return source_files
    
    def _estimate_test_coverage(self, test_files: List[Path], source_files: List[Path]) -> float:
        """Estimate test coverage based on file counts and content."""
        if not source_files:
            return 100  # No source to test
        
        if not test_files:
            return 0  # No tests
        
        # Simple heuristic: ratio of test files to source files
        file_ratio = len(test_files) / len(source_files)
        
        # Analyze test content for function coverage estimation
        total_test_functions = 0
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                # Count test functions
                test_func_count = len(re.findall(r'def test_', content))
                total_test_functions += test_func_count
            except Exception:
                continue
        
        # Estimate coverage based on test function count and file ratio
        if total_test_functions == 0:
            coverage = 0
        elif total_test_functions >= len(source_files) * 3:  # 3+ tests per source file
            coverage = min(90, file_ratio * 100)
        elif total_test_functions >= len(source_files):  # 1+ test per source file
            coverage = min(70, file_ratio * 80)
        else:
            coverage = min(50, file_ratio * 60)
        
        return coverage
    
    def _analyze_test_quality(self, test_files: List[Path]) -> float:
        """Analyze quality of test files."""
        if not test_files:
            return 0
        
        total_score = 0
        analyzed_files = 0
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                
                file_score = 0
                
                # Check for proper test structure
                if 'import pytest' in content or 'import unittest' in content:
                    file_score += 30
                
                # Check for test classes
                if 'class Test' in content:
                    file_score += 20
                
                # Check for assertions
                assertion_count = len(re.findall(r'assert ', content))
                if assertion_count > 0:
                    file_score += min(30, assertion_count * 5)
                
                # Check for fixtures or setup
                if '@pytest.fixture' in content or 'setUp' in content:
                    file_score += 10
                
                # Check for test documentation
                if '"""' in content and 'test' in content.lower():
                    file_score += 10
                
                total_score += min(100, file_score)
                analyzed_files += 1
                
            except Exception:
                continue
        
        if analyzed_files == 0:
            return 0
        
        return total_score / analyzed_files


class ExtensionQualityValidator:
    """Main extension quality validator.
    
    Follows Single Responsibility Principle - orchestrates quality validation.
    Uses Dependency Inversion - depends on analyzer abstractions.
    """
    
    def __init__(self):
        """Initialize extension quality validator."""
        self.logger = logging.getLogger(__name__)
        self.code_analyzer = CodeQualityAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.doc_analyzer = DocumentationAnalyzer()
        self.test_analyzer = TestingAnalyzer()
    
    def validate_extension(self, extension_path: Union[str, Path]) -> ValidationResult:
        """Validate extension quality.
        
        Args:
            extension_path: Path to extension directory
            
        Returns:
            Validation result with scores and recommendations
        """
        import time
        start_time = time.time()
        
        extension_path = Path(extension_path)
        
        if not extension_path.exists():
            return ValidationResult(
                overall_score=0,
                is_compliant=False,
                metrics={},
                issues=["Extension path does not exist"],
                recommendations=["Ensure extension path is correct"]
            )
        
        try:
            # Run all analyzers
            code_quality = self.code_analyzer.analyze_code_quality(extension_path)
            security = self.security_analyzer.analyze_security(extension_path)
            documentation = self.doc_analyzer.analyze_documentation(extension_path)
            testing = self.test_analyzer.analyze_testing(extension_path)
            
            # Calculate weighted overall score
            metrics = {
                'code_quality': code_quality,
                'security': security,
                'documentation': documentation,
                'testing': testing
            }
            
            overall_score = sum(
                metric.score * metric.weight for metric in metrics.values()
            )
            
            # Determine compliance (>= 70% overall score)
            is_compliant = overall_score >= 70
            
            # Aggregate issues and recommendations
            all_issues = []
            all_recommendations = []
            
            for metric in metrics.values():
                all_issues.extend(metric.issues)
                all_recommendations.extend(metric.recommendations)
            
            # Remove duplicates while preserving order
            unique_issues = list(dict.fromkeys(all_issues))
            unique_recommendations = list(dict.fromkeys(all_recommendations))
            
            validation_time = time.time() - start_time
            
            return ValidationResult(
                overall_score=overall_score,
                is_compliant=is_compliant,
                metrics=metrics,
                issues=unique_issues[:15],  # Limit issues
                recommendations=unique_recommendations[:15],  # Limit recommendations
                validation_time=validation_time
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed for {extension_path}: {e}")
            return ValidationResult(
                overall_score=0,
                is_compliant=False,
                metrics={},
                issues=[f"Validation failed: {str(e)}"],
                recommendations=["Check extension structure and try again"],
                validation_time=time.time() - start_time
            )


class QualityMetrics:
    """Quality metrics utilities and calculations."""
    
    @staticmethod
    def calculate_grade(score: float) -> str:
        """Calculate letter grade from score.
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            Letter grade
        """
        if score >= 95:
            return 'A+'
        elif score >= 90:
            return 'A'
        elif score >= 85:
            return 'A-'
        elif score >= 80:
            return 'B+'
        elif score >= 75:
            return 'B'
        elif score >= 70:
            return 'B-'
        elif score >= 65:
            return 'C+'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
    
    @staticmethod
    def calculate_compliance_level(score: float) -> str:
        """Calculate compliance level from score.
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            Compliance level
        """
        if score >= 90:
            return 'excellent'
        elif score >= 80:
            return 'high'
        elif score >= 70:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def generate_summary_report(result: ValidationResult) -> Dict[str, Any]:
        """Generate summary report from validation result.
        
        Args:
            result: Validation result
            
        Returns:
            Summary report dictionary
        """
        return {
            'overall_score': result.overall_score,
            'grade': QualityMetrics.calculate_grade(result.overall_score),
            'compliance_level': QualityMetrics.calculate_compliance_level(result.overall_score),
            'is_compliant': result.is_compliant,
            'metrics_summary': {
                name: {
                    'score': metric.score,
                    'weight': metric.weight,
                    'weighted_score': metric.score * metric.weight
                }
                for name, metric in result.metrics.items()
            },
            'issue_count': len(result.issues),
            'recommendation_count': len(result.recommendations),
            'validation_time': result.validation_time,
            'validated_at': result.validated_at
        }