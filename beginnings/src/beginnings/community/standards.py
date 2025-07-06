"""Community standards and governance for Beginnings framework.

This module provides community standards including code review standards,
governance policies, and community guidelines. Supports community-driven
development and maintains high quality standards.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class StandardsVersion(Enum):
    """Standards version enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class CodeReviewCriteria:
    """Code review criteria definition."""
    
    name: str
    weight: float  # 0-1
    requirements: List[str]
    scoring_guidelines: Dict[str, str]
    automated_checks: List[str] = field(default_factory=list)


@dataclass
class ReviewStandards:
    """Code review standards definition."""
    
    version: str = "2.1"
    status: StandardsVersion = StandardsVersion.ACTIVE
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    review_criteria: Dict[str, CodeReviewCriteria] = field(default_factory=dict)
    review_process: Dict[str, Any] = field(default_factory=dict)
    quality_gates: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommunityGuideline:
    """Community guideline definition."""
    
    title: str
    description: str
    category: str  # conduct, contribution, security, quality
    priority: str  # critical, high, medium, low
    examples: List[str] = field(default_factory=list)
    enforcement: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishingStandard:
    """Publishing standards definition."""
    
    category: str  # metadata, quality, security, process
    requirements: Dict[str, Any]
    validation_rules: Dict[str, str]
    automated_checks: List[str] = field(default_factory=list)


class CodeReviewStandards:
    """Code review standards manager.
    
    Follows Single Responsibility Principle - only handles code review standards.
    """
    
    def __init__(self):
        """Initialize code review standards."""
        self.logger = logging.getLogger(__name__)
        self.standards = self._initialize_standards()
    
    def get_code_review_standards(self) -> Dict[str, Any]:
        """Get current code review standards.
        
        Returns:
            Code review standards data
        """
        return {
            'version': self.standards.version,
            'status': self.standards.status.value,
            'updated_at': self.standards.updated_at,
            'review_criteria': {
                name: {
                    'weight': criteria.weight,
                    'requirements': criteria.requirements,
                    'scoring_guidelines': criteria.scoring_guidelines,
                    'automated_checks': criteria.automated_checks
                }
                for name, criteria in self.standards.review_criteria.items()
            },
            'review_process': self.standards.review_process,
            'quality_gates': self.standards.quality_gates
        }
    
    def validate_review_score(self, review_scores: Dict[str, float]) -> Dict[str, Any]:
        """Validate review scores against standards.
        
        Args:
            review_scores: Scores for each criteria
            
        Returns:
            Validation result
        """
        validation_result = {
            'is_valid': True,
            'overall_score': 0.0,
            'meets_threshold': False,
            'missing_criteria': [],
            'details': {}
        }
        
        # Calculate weighted overall score
        total_weight = 0
        weighted_score = 0
        
        for criteria_name, criteria in self.standards.review_criteria.items():
            if criteria_name in review_scores:
                weighted_score += review_scores[criteria_name] * criteria.weight
                total_weight += criteria.weight
            else:
                validation_result['missing_criteria'].append(criteria_name)
        
        if total_weight > 0:
            validation_result['overall_score'] = weighted_score / total_weight
        
        # Check against approval threshold
        approval_threshold = self.standards.quality_gates.get('approval_threshold', 75)
        validation_result['meets_threshold'] = validation_result['overall_score'] >= approval_threshold
        
        # Check if all required criteria are present
        if validation_result['missing_criteria']:
            validation_result['is_valid'] = False
        
        validation_result['details'] = {
            'weighted_scores': {
                name: review_scores.get(name, 0) * self.standards.review_criteria[name].weight
                for name in self.standards.review_criteria.keys()
            },
            'approval_threshold': approval_threshold,
            'total_weight': total_weight
        }
        
        return validation_result
    
    def _initialize_standards(self) -> ReviewStandards:
        """Initialize default review standards."""
        standards = ReviewStandards()
        
        # Define review criteria
        standards.review_criteria = {
            'code_quality': CodeReviewCriteria(
                name='Code Quality',
                weight=0.30,
                requirements=[
                    'Follows PEP 8 style guidelines',
                    'Proper error handling',
                    'Clear variable and function names',
                    'Appropriate comments and docstrings',
                    'No code duplication',
                    'Reasonable complexity levels'
                ],
                scoring_guidelines={
                    '90-100': 'Excellent code quality with best practices',
                    '80-89': 'Good code quality with minor issues',
                    '70-79': 'Acceptable code quality with some improvements needed',
                    '60-69': 'Below standard, requires significant improvements',
                    '0-59': 'Poor code quality, major refactoring required'
                },
                automated_checks=['syntax_check', 'style_check', 'complexity_analysis']
            ),
            'functionality': CodeReviewCriteria(
                name='Functionality',
                weight=0.25,
                requirements=[
                    'Meets specified requirements',
                    'Handles edge cases appropriately',
                    'No logical errors',
                    'Performs efficiently',
                    'Backwards compatibility maintained',
                    'API design follows conventions'
                ],
                scoring_guidelines={
                    '90-100': 'Fully functional with excellent design',
                    '80-89': 'Functional with good design',
                    '70-79': 'Functional with acceptable design',
                    '60-69': 'Limited functionality or design issues',
                    '0-59': 'Significant functionality problems'
                },
                automated_checks=['unit_tests', 'integration_tests', 'performance_tests']
            ),
            'testing': CodeReviewCriteria(
                name='Testing',
                weight=0.25,
                requirements=[
                    'Comprehensive test coverage (>80%)',
                    'Unit tests for all public methods',
                    'Integration tests where appropriate',
                    'Tests are well-organized and clear',
                    'Edge cases are tested',
                    'Mock dependencies appropriately'
                ],
                scoring_guidelines={
                    '90-100': 'Excellent test coverage and quality',
                    '80-89': 'Good test coverage with minor gaps',
                    '70-79': 'Acceptable test coverage',
                    '60-69': 'Insufficient test coverage',
                    '0-59': 'Poor or missing tests'
                },
                automated_checks=['coverage_check', 'test_execution', 'test_quality_analysis']
            ),
            'documentation': CodeReviewCriteria(
                name='Documentation',
                weight=0.20,
                requirements=[
                    'All public APIs documented',
                    'Usage examples provided',
                    'Installation instructions clear',
                    'Contribution guidelines followed',
                    'README is comprehensive',
                    'Code comments explain complex logic'
                ],
                scoring_guidelines={
                    '90-100': 'Excellent documentation coverage',
                    '80-89': 'Good documentation with minor gaps',
                    '70-79': 'Acceptable documentation',
                    '60-69': 'Insufficient documentation',
                    '0-59': 'Poor or missing documentation'
                },
                automated_checks=['doc_coverage_check', 'link_validation', 'format_validation']
            )
        }
        
        # Define review process
        standards.review_process = {
            'minimum_reviewers': 2,
            'approval_threshold': 75,
            'review_timeline_days': 14,
            'feedback_period_days': 7,
            'automated_checks_required': True,
            'manual_review_required': True,
            'reviewer_qualifications': [
                'Trusted contributor level or higher',
                'Experience with relevant technology',
                'No conflicts of interest'
            ]
        }
        
        # Define quality gates
        standards.quality_gates = {
            'approval_threshold': 75,
            'minimum_criteria_scores': {
                'code_quality': 70,
                'functionality': 75,
                'testing': 60,
                'documentation': 60
            },
            'automated_checks_must_pass': True,
            'security_scan_required': True,
            'performance_validation': False  # Optional for most contributions
        }
        
        return standards


class CommunityStandards:
    """Community standards and governance manager.
    
    Follows Single Responsibility Principle - orchestrates community standards.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize community standards.
        
        Args:
            storage_path: Path to store standards data
        """
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path or Path.cwd() / "community_standards"
        self.storage_path.mkdir(exist_ok=True)
        
        self.review_standards = CodeReviewStandards()
        self.guidelines = self._initialize_guidelines()
        self.publishing_standards = self._initialize_publishing_standards()
        self.standards_history = self._load_standards_history()
    
    def get_community_guidelines(self) -> Dict[str, Any]:
        """Get community guidelines.
        
        Returns:
            Community guidelines data
        """
        return {
            'version': '1.0',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'code_of_conduct': {
                'principles': [
                    'Be respectful and inclusive',
                    'Focus on constructive feedback',
                    'Help others learn and grow',
                    'Respect different perspectives',
                    'Maintain professional communication'
                ],
                'prohibited_behavior': [
                    'Harassment or discrimination',
                    'Spam or excessive self-promotion',
                    'Sharing malicious code',
                    'Violating intellectual property',
                    'Personal attacks or toxic behavior'
                ]
            },
            'contribution_ethics': {
                'original_work': 'All contributions must be original or properly attributed',
                'licensing': 'All contributions must use compatible licenses',
                'security': 'No malicious or vulnerable code allowed',
                'quality': 'Maintain high standards for community benefit',
                'transparency': 'Be transparent about limitations and dependencies'
            },
            'enforcement': {
                'warning_system': True,
                'temporary_restrictions': True,
                'permanent_bans': True,
                'appeal_process': True,
                'escalation_path': [
                    'Informal warning',
                    'Formal warning',
                    'Temporary restriction',
                    'Extended restriction',
                    'Permanent ban'
                ]
            },
            'guidelines_by_category': {
                category: [
                    {
                        'title': guideline.title,
                        'description': guideline.description,
                        'priority': guideline.priority,
                        'examples': guideline.examples
                    }
                    for guideline in guidelines
                ]
                for category, guidelines in self._group_guidelines_by_category().items()
            }
        }
    
    def get_publishing_standards(self) -> Dict[str, Any]:
        """Get publishing standards.
        
        Returns:
            Publishing standards data
        """
        return {
            'version': '1.0',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'metadata_requirements': {
                'required_fields': [
                    'name', 'version', 'description', 'author', 
                    'license', 'beginnings_version'
                ],
                'optional_fields': [
                    'homepage', 'repository', 'documentation',
                    'keywords', 'classifiers', 'maintainers'
                ],
                'validation_rules': {
                    name: standard.validation_rules.get(name, 'Standard validation')
                    for name, standard in self.publishing_standards.items()
                    if 'metadata' in standard.category
                }
            },
            'quality_gates': {
                'minimum_quality_score': 70,
                'required_documentation': True,
                'required_tests': True,
                'security_scan_passed': True,
                'compatibility_verified': True,
                'performance_acceptable': False  # Optional
            },
            'publication_process': {
                'review_required': True,
                'staging_period_days': 7,
                'feedback_period_days': 14,
                'appeal_process_available': True,
                'automated_validation': True,
                'manual_approval_required': True
            },
            'standards_by_category': {
                category: {
                    'requirements': standard.requirements,
                    'validation_rules': standard.validation_rules,
                    'automated_checks': standard.automated_checks
                }
                for category, standard in self.publishing_standards.items()
            }
        }
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics framework.
        
        Returns:
            Quality metrics framework data
        """
        return {
            'version': '1.0',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'code_quality_metrics': {
                'cyclomatic_complexity': {'threshold': 10, 'weight': 20},
                'maintainability_index': {'threshold': 70, 'weight': 25},
                'code_duplication': {'threshold': 5, 'weight': 15},
                'test_coverage': {'threshold': 80, 'weight': 25},
                'documentation_coverage': {'threshold': 90, 'weight': 15}
            },
            'security_metrics': {
                'vulnerability_scan': {'required': True, 'weight': 40},
                'dependency_security': {'required': True, 'weight': 30},
                'secret_detection': {'required': True, 'weight': 20},
                'license_compliance': {'required': True, 'weight': 10}
            },
            'usability_metrics': {
                'api_consistency': {'weight': 30},
                'documentation_clarity': {'weight': 25},
                'example_completeness': {'weight': 25},
                'error_message_quality': {'weight': 20}
            },
            'performance_metrics': {
                'startup_time': {'threshold_ms': 1000, 'weight': 25},
                'memory_usage': {'threshold_mb': 100, 'weight': 25},
                'response_time': {'threshold_ms': 500, 'weight': 30},
                'throughput': {'threshold_rps': 100, 'weight': 20}
            }
        }
    
    def get_standards_history(self) -> Dict[str, Any]:
        """Get standards evolution history.
        
        Returns:
            Standards history data
        """
        return {
            'current_version': '2.1',
            'versions': [
                {
                    'version': '2.1',
                    'released': '2024-01-01T00:00:00Z',
                    'status': 'active',
                    'changes': [
                        'Increased minimum test coverage to 80%',
                        'Added security scan requirements',
                        'Updated documentation standards',
                        'Introduced performance guidelines'
                    ],
                    'impact': 'Enhanced quality and security requirements'
                },
                {
                    'version': '2.0',
                    'released': '2023-06-01T00:00:00Z',
                    'status': 'deprecated',
                    'changes': [
                        'Introduced quality scoring system',
                        'Added automated validation',
                        'Updated licensing requirements',
                        'Established review process'
                    ],
                    'impact': 'Major overhaul of quality standards'
                },
                {
                    'version': '1.0',
                    'released': '2023-01-01T00:00:00Z',
                    'status': 'archived',
                    'changes': [
                        'Initial community standards',
                        'Basic code review guidelines',
                        'Contribution process established'
                    ],
                    'impact': 'Foundation of community governance'
                }
            ],
            'upcoming_changes': [
                {
                    'version': '2.2',
                    'planned_release': '2024-06-01T00:00:00Z',
                    'status': 'draft',
                    'proposed_changes': [
                        'Performance benchmarking requirements',
                        'Accessibility compliance checks',
                        'Carbon footprint assessment',
                        'Multi-language support standards'
                    ],
                    'rationale': 'Expanding quality criteria for modern development needs'
                }
            ],
            'evolution_principles': [
                'Community-driven decision making',
                'Backward compatibility when possible',
                'Gradual implementation of changes',
                'Regular review and feedback cycles'
            ]
        }
    
    def validate_against_standards(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contribution against all community standards.
        
        Args:
            contribution_data: Contribution data to validate
            
        Returns:
            Comprehensive validation result
        """
        validation_result = {
            'overall_compliance': True,
            'compliance_score': 100,
            'validations': {},
            'issues': [],
            'recommendations': []
        }
        
        # Validate against publishing standards
        publishing_validation = self._validate_publishing_standards(contribution_data)
        validation_result['validations']['publishing'] = publishing_validation
        
        if not publishing_validation['is_compliant']:
            validation_result['overall_compliance'] = False
            validation_result['compliance_score'] -= 30
            validation_result['issues'].extend(publishing_validation['issues'])
        
        # Validate against community guidelines
        guidelines_validation = self._validate_community_guidelines(contribution_data)
        validation_result['validations']['guidelines'] = guidelines_validation
        
        if not guidelines_validation['is_compliant']:
            validation_result['overall_compliance'] = False
            validation_result['compliance_score'] -= 20
            validation_result['issues'].extend(guidelines_validation['issues'])
        
        # Validate against quality metrics
        quality_validation = self._validate_quality_metrics(contribution_data)
        validation_result['validations']['quality'] = quality_validation
        
        if not quality_validation['meets_standards']:
            validation_result['compliance_score'] -= 25
            validation_result['recommendations'].extend(quality_validation['recommendations'])
        
        validation_result['compliance_score'] = max(0, validation_result['compliance_score'])
        
        return validation_result
    
    def _initialize_guidelines(self) -> List[CommunityGuideline]:
        """Initialize community guidelines."""
        guidelines = [
            CommunityGuideline(
                title='Respectful Communication',
                description='Maintain respectful and professional communication in all interactions',
                category='conduct',
                priority='critical',
                examples=[
                    'Use inclusive language',
                    'Provide constructive feedback',
                    'Acknowledge others\' contributions'
                ],
                enforcement={'violation_severity': 'high', 'escalation_required': True}
            ),
            CommunityGuideline(
                title='Original Content',
                description='Ensure all contributions are original or properly attributed',
                category='contribution',
                priority='critical',
                examples=[
                    'Write original code',
                    'Properly attribute third-party code',
                    'Respect copyright and licenses'
                ],
                enforcement={'violation_severity': 'high', 'automatic_rejection': True}
            ),
            CommunityGuideline(
                title='Security Responsibility',
                description='Do not submit malicious or vulnerable code',
                category='security',
                priority='critical',
                examples=[
                    'Scan for vulnerabilities',
                    'Follow secure coding practices',
                    'Report security issues responsibly'
                ],
                enforcement={'violation_severity': 'critical', 'immediate_action': True}
            ),
            CommunityGuideline(
                title='Quality Standards',
                description='Maintain high quality standards in all contributions',
                category='quality',
                priority='high',
                examples=[
                    'Include comprehensive tests',
                    'Provide clear documentation',
                    'Follow coding conventions'
                ],
                enforcement={'violation_severity': 'medium', 'feedback_required': True}
            ),
            CommunityGuideline(
                title='Collaborative Spirit',
                description='Foster collaboration and knowledge sharing',
                category='conduct',
                priority='medium',
                examples=[
                    'Help newcomers',
                    'Share knowledge openly',
                    'Participate in discussions'
                ],
                enforcement={'violation_severity': 'low', 'guidance_provided': True}
            )
        ]
        
        return guidelines
    
    def _initialize_publishing_standards(self) -> Dict[str, PublishingStandard]:
        """Initialize publishing standards."""
        return {
            'metadata': PublishingStandard(
                category='metadata',
                requirements={
                    'name': 'Unique, descriptive name following naming conventions',
                    'version': 'Semantic versioning (e.g., 1.0.0)',
                    'description': 'Clear, comprehensive description (min 50 characters)',
                    'license': 'OSI-approved license',
                    'author': 'Author information with contact details'
                },
                validation_rules={
                    'name': 'Must be unique and follow naming conventions',
                    'version': 'Must follow semantic versioning',
                    'license': 'Must be OSI-approved license'
                },
                automated_checks=['uniqueness_check', 'format_validation', 'license_validation']
            ),
            'quality': PublishingStandard(
                category='quality',
                requirements={
                    'minimum_score': 'Overall quality score >= 70',
                    'code_quality': 'Code quality score >= 70',
                    'documentation': 'Documentation score >= 60',
                    'testing': 'Test coverage >= 60%'
                },
                validation_rules={
                    'quality_score': 'Comprehensive quality assessment',
                    'test_coverage': 'Automated test coverage analysis'
                },
                automated_checks=['quality_analysis', 'test_coverage', 'documentation_check']
            ),
            'security': PublishingStandard(
                category='security',
                requirements={
                    'vulnerability_scan': 'Pass security vulnerability scan',
                    'dependency_check': 'All dependencies secure and up-to-date',
                    'no_secrets': 'No hardcoded secrets or credentials'
                },
                validation_rules={
                    'security_scan': 'Automated security scanning required',
                    'dependency_security': 'Dependency vulnerability check'
                },
                automated_checks=['security_scan', 'dependency_check', 'secret_detection']
            )
        }
    
    def _group_guidelines_by_category(self) -> Dict[str, List[CommunityGuideline]]:
        """Group guidelines by category."""
        categories = {}
        for guideline in self.guidelines:
            if guideline.category not in categories:
                categories[guideline.category] = []
            categories[guideline.category].append(guideline)
        return categories
    
    def _validate_publishing_standards(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate against publishing standards."""
        # Simplified validation - in practice, would be more comprehensive
        issues = []
        
        required_fields = ['name', 'version', 'description', 'license']
        for field in required_fields:
            if not contribution_data.get(field):
                issues.append(f"Missing required field: {field}")
        
        return {
            'is_compliant': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_community_guidelines(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate against community guidelines."""
        # Simplified validation - in practice, would check for policy violations
        return {
            'is_compliant': True,
            'issues': []
        }
    
    def _validate_quality_metrics(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate against quality metrics."""
        quality_score = contribution_data.get('quality_score', 0)
        
        return {
            'meets_standards': quality_score >= 70,
            'quality_score': quality_score,
            'recommendations': ['Improve code quality'] if quality_score < 70 else []
        }
    
    def _load_standards_history(self) -> Dict[str, Any]:
        """Load standards history from storage."""
        history_file = self.storage_path / "standards_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load standards history: {e}")
        
        return {'versions': [], 'current_version': '2.1'}