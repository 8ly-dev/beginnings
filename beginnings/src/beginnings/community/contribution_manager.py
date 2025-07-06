"""Contribution management system for Beginnings framework.

This module provides comprehensive contribution management including submission,
review, validation, and publication workflows. Supports community governance
and maintains high quality standards.
"""

from __future__ import annotations

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid


class ContributionStatus(Enum):
    """Contribution status enumeration."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class ContributionType(Enum):
    """Contribution type enumeration."""
    EXTENSION = "extension"
    TEMPLATE = "template"
    DOCUMENTATION = "documentation"
    EXAMPLE = "example"
    TOOL = "tool"
    PLUGIN = "plugin"


class ReviewStatus(Enum):
    """Review status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REQUIRES_CHANGES = "requires_changes"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Contributor:
    """Contributor information."""
    
    id: str
    username: str
    email: str
    full_name: str
    reputation_score: int = 0
    level: str = "new"  # new, contributor, trusted_contributor, maintainer
    contributions_count: int = 0
    badges: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Contribution:
    """Contribution data structure."""
    
    id: str
    type: ContributionType
    name: str
    version: str
    title: str
    description: str
    contributor_id: str
    status: ContributionStatus = ContributionStatus.PENDING
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Metadata
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    homepage_url: Optional[str] = None
    
    # Quality metrics
    quality_score: float = 0.0
    validation_passed: bool = False
    security_scan_passed: bool = False
    
    # Review data
    review_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_notes: List[str] = field(default_factory=list)
    feedback: List[Dict[str, Any]] = field(default_factory=list)
    
    # Publication data
    published_at: Optional[str] = None
    registry_url: Optional[str] = None
    download_count: int = 0


@dataclass
class Review:
    """Review data structure."""
    
    id: str
    contribution_id: str
    reviewer_id: str
    status: ReviewStatus = ReviewStatus.NOT_STARTED
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    # Review criteria scores (0-100)
    code_quality_score: float = 0.0
    security_score: float = 0.0
    documentation_score: float = 0.0
    usability_score: float = 0.0
    overall_score: float = 0.0
    
    # Feedback
    comments: List[Dict[str, Any]] = field(default_factory=list)
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Decision
    decision: Optional[str] = None  # approved, rejected, requires_changes
    decision_reason: Optional[str] = None


@dataclass
class ContributionGuidelines:
    """Contribution guidelines and standards."""
    
    version: str = "1.0"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Code standards
    code_standards: Dict[str, Any] = field(default_factory=lambda: {
        'style_guide': 'PEP 8',
        'documentation_required': True,
        'testing_required': True,
        'minimum_test_coverage': 80,
        'type_hints_required': True,
        'security_scan_required': True
    })
    
    # Submission requirements
    submission_requirements: Dict[str, Any] = field(default_factory=lambda: {
        'metadata_required': ['name', 'version', 'description', 'author', 'license'],
        'supported_licenses': ['MIT', 'Apache-2.0', 'BSD-3-Clause', 'GPL-3.0'],
        'max_file_size_mb': 50,
        'max_dependencies': 20,
        'review_timeline_days': 14
    })
    
    # Quality requirements
    quality_requirements: Dict[str, Any] = field(default_factory=lambda: {
        'minimum_quality_score': 70,
        'security_scan_required': True,
        'documentation_score_min': 60,
        'code_quality_score_min': 70,
        'testing_score_min': 60
    })
    
    # Review process
    review_process: Dict[str, Any] = field(default_factory=lambda: {
        'minimum_reviewers': 1,
        'approval_threshold': 75,
        'feedback_period_days': 7,
        'appeal_process_available': True,
        'automated_checks': [
            'syntax_validation',
            'security_scan',
            'dependency_check',
            'license_validation',
            'quality_assessment'
        ]
    })


class ContributionValidator:
    """Validates contributions against community standards.
    
    Follows Single Responsibility Principle - only handles contribution validation.
    """
    
    def __init__(self, guidelines: ContributionGuidelines):
        """Initialize contribution validator.
        
        Args:
            guidelines: Community guidelines to validate against
        """
        self.guidelines = guidelines
        self.logger = logging.getLogger(__name__)
    
    def validate_contribution(self, contribution: Contribution) -> Dict[str, Any]:
        """Validate contribution against standards.
        
        Args:
            contribution: Contribution to validate
            
        Returns:
            Validation result
        """
        validation_result = {
            'is_valid': True,
            'validation_score': 100,
            'issues': [],
            'warnings': [],
            'requirements_met': True,
            'details': {}
        }
        
        # Validate metadata
        metadata_validation = self._validate_metadata(contribution)
        validation_result['details']['metadata'] = metadata_validation
        
        if not metadata_validation['is_valid']:
            validation_result['is_valid'] = False
            validation_result['validation_score'] -= 30
            validation_result['issues'].extend(metadata_validation['issues'])
        
        # Validate license
        license_validation = self._validate_license(contribution)
        validation_result['details']['license'] = license_validation
        
        if not license_validation['is_valid']:
            validation_result['is_valid'] = False
            validation_result['validation_score'] -= 20
            validation_result['issues'].extend(license_validation['issues'])
        
        # Validate quality requirements
        quality_validation = self._validate_quality_requirements(contribution)
        validation_result['details']['quality'] = quality_validation
        
        if not quality_validation['is_valid']:
            validation_result['requirements_met'] = False
            validation_result['validation_score'] -= 25
            validation_result['issues'].extend(quality_validation['issues'])
        
        # Validate naming and versioning
        naming_validation = self._validate_naming(contribution)
        validation_result['details']['naming'] = naming_validation
        
        if not naming_validation['is_valid']:
            validation_result['validation_score'] -= 15
            validation_result['warnings'].extend(naming_validation['warnings'])
        
        # Final validation score adjustment
        validation_result['validation_score'] = max(0, validation_result['validation_score'])
        
        return validation_result
    
    def _validate_metadata(self, contribution: Contribution) -> Dict[str, Any]:
        """Validate contribution metadata."""
        required_fields = self.guidelines.submission_requirements['metadata_required']
        issues = []
        
        # Check required fields
        contribution_dict = {
            'name': contribution.name,
            'version': contribution.version,
            'description': contribution.description,
            'author': contribution.contributor_id,  # Simplified
            'license': contribution.license
        }
        
        for field in required_fields:
            if not contribution_dict.get(field):
                issues.append(f"Missing required field: {field}")
        
        # Validate description length
        if len(contribution.description) < 50:
            issues.append("Description too short (minimum 50 characters)")
        
        # Validate tags
        if not contribution.tags:
            issues.append("At least one tag is required")
        elif len(contribution.tags) > 10:
            issues.append("Too many tags (maximum 10)")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_license(self, contribution: Contribution) -> Dict[str, Any]:
        """Validate contribution license."""
        supported_licenses = self.guidelines.submission_requirements['supported_licenses']
        issues = []
        
        if contribution.license not in supported_licenses:
            issues.append(f"Unsupported license: {contribution.license}")
            issues.append(f"Supported licenses: {', '.join(supported_licenses)}")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_quality_requirements(self, contribution: Contribution) -> Dict[str, Any]:
        """Validate quality requirements."""
        min_score = self.guidelines.quality_requirements['minimum_quality_score']
        issues = []
        
        if contribution.quality_score < min_score:
            issues.append(f"Quality score {contribution.quality_score} below minimum {min_score}")
        
        if not contribution.validation_passed:
            issues.append("Extension validation has not passed")
        
        if not contribution.security_scan_passed:
            issues.append("Security scan has not passed")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_naming(self, contribution: Contribution) -> Dict[str, Any]:
        """Validate naming conventions."""
        warnings = []
        
        # Check name format
        if not re.match(r'^[a-z][a-z0-9_-]*$', contribution.name):
            warnings.append("Name should use lowercase letters, numbers, hyphens, and underscores only")
        
        # Check version format (semantic versioning)
        if not re.match(r'^\d+\.\d+\.\d+(-[a-z0-9]+)?$', contribution.version):
            warnings.append("Version should follow semantic versioning (e.g., 1.0.0)")
        
        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings
        }


class ReputationManager:
    """Manages contributor reputation and levels.
    
    Follows Single Responsibility Principle - only handles reputation management.
    """
    
    def __init__(self):
        """Initialize reputation manager."""
        self.logger = logging.getLogger(__name__)
        self.level_thresholds = {
            'new': 0,
            'contributor': 100,
            'trusted_contributor': 500,
            'maintainer': 1000
        }
        self.badge_criteria = {
            'first_contribution': lambda c: c.contributions_count >= 1,
            'quality_contributor': lambda c: c.reputation_score >= 200,
            'documentation_champion': lambda c: c.reputation_score >= 300,
            'security_expert': lambda c: c.reputation_score >= 400,
            'community_leader': lambda c: c.reputation_score >= 800
        }
    
    def update_reputation(self, contributor: Contributor, action: str, points: int = 0) -> Contributor:
        """Update contributor reputation.
        
        Args:
            contributor: Contributor to update
            action: Action that triggered reputation change
            points: Points to add/subtract (if not using predefined action)
            
        Returns:
            Updated contributor
        """
        # Predefined reputation actions
        reputation_actions = {
            'contribution_submitted': 10,
            'contribution_approved': 50,
            'contribution_rejected': -10,
            'helpful_review': 25,
            'quality_extension': 75,
            'security_contribution': 100,
            'documentation_improvement': 30,
            'community_help': 15
        }
        
        points_to_add = reputation_actions.get(action, points)
        contributor.reputation_score = max(0, contributor.reputation_score + points_to_add)
        
        # Update level
        new_level = self._calculate_level(contributor.reputation_score)
        if new_level != contributor.level:
            contributor.level = new_level
            self.logger.info(f"Contributor {contributor.username} promoted to {new_level}")
        
        # Update badges
        self._update_badges(contributor)
        
        # Update permissions
        self._update_permissions(contributor)
        
        contributor.last_active = datetime.now(timezone.utc).isoformat()
        
        return contributor
    
    def _calculate_level(self, reputation_score: int) -> str:
        """Calculate contributor level based on reputation."""
        for level, threshold in reversed(list(self.level_thresholds.items())):
            if reputation_score >= threshold:
                return level
        return 'new'
    
    def _update_badges(self, contributor: Contributor) -> None:
        """Update contributor badges."""
        for badge_name, criteria in self.badge_criteria.items():
            if badge_name not in contributor.badges and criteria(contributor):
                contributor.badges.append(badge_name)
                self.logger.info(f"Contributor {contributor.username} earned badge: {badge_name}")
    
    def _update_permissions(self, contributor: Contributor) -> None:
        """Update contributor permissions based on level."""
        permissions_by_level = {
            'new': ['submit_contributions'],
            'contributor': ['submit_contributions', 'comment_on_contributions'],
            'trusted_contributor': [
                'submit_contributions', 
                'comment_on_contributions',
                'review_community_contributions',
                'moderate_discussions'
            ],
            'maintainer': [
                'submit_contributions',
                'comment_on_contributions', 
                'review_community_contributions',
                'moderate_discussions',
                'approve_contributions',
                'manage_community_standards'
            ]
        }
        
        contributor.permissions = permissions_by_level.get(contributor.level, ['submit_contributions'])


class ContributionManager:
    """Main contribution management system.
    
    Follows Single Responsibility Principle - orchestrates contribution workflow.
    Uses Dependency Inversion - depends on validator and reputation manager abstractions.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize contribution manager.
        
        Args:
            storage_path: Path to store contribution data
        """
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path or Path.cwd() / "contributions"
        self.storage_path.mkdir(exist_ok=True)
        
        self.guidelines = ContributionGuidelines()
        self.validator = ContributionValidator(self.guidelines)
        self.reputation_manager = ReputationManager()
        
        # In-memory storage (in production, use database)
        self.contributions: Dict[str, Contribution] = {}
        self.contributors: Dict[str, Contributor] = {}
        self.reviews: Dict[str, Review] = {}
        
        # Load existing data
        self._load_data()
    
    def submit_contribution(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit new contribution.
        
        Args:
            contribution_data: Contribution data
            
        Returns:
            Submission result
        """
        try:
            # Generate contribution ID
            contribution_id = str(uuid.uuid4())
            
            # Create contribution object
            contribution = Contribution(
                id=contribution_id,
                type=ContributionType(contribution_data.get('type', 'extension')),
                name=contribution_data['name'],
                version=contribution_data['version'],
                title=contribution_data.get('title', contribution_data['name']),
                description=contribution_data['description'],
                contributor_id=contribution_data['contributor_id'],
                license=contribution_data.get('license', 'MIT'),
                tags=contribution_data.get('tags', []),
                repository_url=contribution_data.get('repository_url'),
                documentation_url=contribution_data.get('documentation_url'),
                homepage_url=contribution_data.get('homepage_url')
            )
            
            # Validate contribution
            validation_result = self.validator.validate_contribution(contribution)
            
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'issues': validation_result['issues'],
                    'validation_score': validation_result['validation_score']
                }
            
            # Store contribution
            self.contributions[contribution_id] = contribution
            
            # Update contributor
            if contribution.contributor_id in self.contributors:
                contributor = self.contributors[contribution.contributor_id]
                contributor.contributions_count += 1
                self.reputation_manager.update_reputation(contributor, 'contribution_submitted')
            
            # Save data
            self._save_data()
            
            self.logger.info(f"Contribution {contribution_id} submitted successfully")
            
            return {
                'success': True,
                'contribution_id': contribution_id,
                'status': contribution.status.value,
                'message': 'Contribution submitted successfully',
                'validation_score': validation_result['validation_score']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to submit contribution: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_review_status(self, contribution_id: str) -> Dict[str, Any]:
        """Get review status for contribution.
        
        Args:
            contribution_id: Contribution ID
            
        Returns:
            Review status information
        """
        if contribution_id not in self.contributions:
            return {'error': 'Contribution not found'}
        
        contribution = self.contributions[contribution_id]
        
        if not contribution.review_id:
            return {
                'status': 'not_started',
                'message': 'Review has not been assigned yet'
            }
        
        review = self.reviews.get(contribution.review_id)
        if not review:
            return {'error': 'Review not found'}
        
        return {
            'status': review.status.value,
            'reviewer': review.reviewer_id,
            'started_at': review.started_at,
            'completed_at': review.completed_at,
            'overall_score': review.overall_score,
            'feedback': review.comments[-3:] if review.comments else [],  # Last 3 comments
            'estimated_completion': self._estimate_completion_time(review)
        }
    
    def approve_contribution(self, contribution_id: str, reviewer_id: str, notes: str = "") -> Dict[str, Any]:
        """Approve contribution.
        
        Args:
            contribution_id: Contribution ID
            reviewer_id: Reviewer ID
            notes: Approval notes
            
        Returns:
            Approval result
        """
        if contribution_id not in self.contributions:
            return {'success': False, 'error': 'Contribution not found'}
        
        contribution = self.contributions[contribution_id]
        
        # Update contribution status
        contribution.status = ContributionStatus.APPROVED
        contribution.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Create or update review
        if contribution.review_id:
            review = self.reviews[contribution.review_id]
            review.status = ReviewStatus.APPROVED
            review.decision = 'approved'
            review.decision_reason = notes
            review.completed_at = datetime.now(timezone.utc).isoformat()
        
        # Update contributor reputation
        if contribution.contributor_id in self.contributors:
            contributor = self.contributors[contribution.contributor_id]
            self.reputation_manager.update_reputation(contributor, 'contribution_approved')
        
        # Publish contribution
        publication_result = self._publish_contribution(contribution)
        
        self._save_data()
        
        self.logger.info(f"Contribution {contribution_id} approved by {reviewer_id}")
        
        return {
            'success': True,
            'approved_by': reviewer_id,
            'approved_at': contribution.updated_at,
            'publication_status': 'published' if publication_result['success'] else 'pending',
            'registry_url': publication_result.get('registry_url'),
            'notes': notes
        }
    
    def reject_contribution(self, contribution_id: str, reviewer_id: str, reason: str, feedback: List[str] = None) -> Dict[str, Any]:
        """Reject contribution.
        
        Args:
            contribution_id: Contribution ID
            reviewer_id: Reviewer ID  
            reason: Rejection reason
            feedback: Detailed feedback
            
        Returns:
            Rejection result
        """
        if contribution_id not in self.contributions:
            return {'success': False, 'error': 'Contribution not found'}
        
        contribution = self.contributions[contribution_id]
        feedback = feedback or []
        
        # Update contribution status
        contribution.status = ContributionStatus.REJECTED
        contribution.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Create or update review
        if contribution.review_id:
            review = self.reviews[contribution.review_id]
            review.status = ReviewStatus.REJECTED
            review.decision = 'rejected'
            review.decision_reason = reason
            review.completed_at = datetime.now(timezone.utc).isoformat()
            review.recommendations.extend(feedback)
        
        # Update contributor reputation (small penalty)
        if contribution.contributor_id in self.contributors:
            contributor = self.contributors[contribution.contributor_id]
            self.reputation_manager.update_reputation(contributor, 'contribution_rejected')
        
        self._save_data()
        
        self.logger.info(f"Contribution {contribution_id} rejected by {reviewer_id}")
        
        return {
            'success': True,
            'rejected_by': reviewer_id,
            'rejected_at': contribution.updated_at,
            'reason': reason,
            'feedback': feedback,
            'resubmission_allowed': True
        }
    
    def get_contribution_guidelines(self) -> Dict[str, Any]:
        """Get current contribution guidelines.
        
        Returns:
            Contribution guidelines
        """
        return {
            'version': self.guidelines.version,
            'updated': self.guidelines.updated_at,
            'sections': {
                'code_standards': self.guidelines.code_standards,
                'submission_process': self.guidelines.submission_requirements,
                'quality_requirements': self.guidelines.quality_requirements,
                'review_process': self.guidelines.review_process
            }
        }
    
    def get_contributor_reputation(self, contributor_id: str) -> Dict[str, Any]:
        """Get contributor reputation information.
        
        Args:
            contributor_id: Contributor ID
            
        Returns:
            Reputation information
        """
        if contributor_id not in self.contributors:
            return {'error': 'Contributor not found'}
        
        contributor = self.contributors[contributor_id]
        
        # Calculate contribution statistics
        contributions = [c for c in self.contributions.values() if c.contributor_id == contributor_id]
        approved_count = len([c for c in contributions if c.status == ContributionStatus.APPROVED])
        rejected_count = len([c for c in contributions if c.status == ContributionStatus.REJECTED])
        pending_count = len([c for c in contributions if c.status == ContributionStatus.PENDING])
        
        return {
            'contributor_id': contributor_id,
            'username': contributor.username,
            'reputation_score': contributor.reputation_score,
            'level': contributor.level,
            'contributions': {
                'total': contributor.contributions_count,
                'approved': approved_count,
                'rejected': rejected_count,
                'pending': pending_count
            },
            'badges': contributor.badges,
            'permissions': contributor.permissions,
            'joined_at': contributor.joined_at,
            'last_active': contributor.last_active
        }
    
    def register_contributor(self, contributor_data: Dict[str, Any]) -> str:
        """Register new contributor.
        
        Args:
            contributor_data: Contributor data
            
        Returns:
            Contributor ID
        """
        contributor_id = str(uuid.uuid4())
        
        contributor = Contributor(
            id=contributor_id,
            username=contributor_data['username'],
            email=contributor_data['email'],
            full_name=contributor_data.get('full_name', contributor_data['username'])
        )
        
        # Initialize permissions
        self.reputation_manager._update_permissions(contributor)
        
        self.contributors[contributor_id] = contributor
        self._save_data()
        
        self.logger.info(f"New contributor registered: {contributor.username}")
        
        return contributor_id
    
    def _estimate_completion_time(self, review: Review) -> str:
        """Estimate review completion time."""
        if review.status == ReviewStatus.COMPLETED:
            return review.completed_at
        
        # Estimate based on review timeline
        timeline_days = self.guidelines.review_process['feedback_period_days']
        estimated_completion = datetime.fromisoformat(review.started_at.replace('Z', '+00:00'))
        estimated_completion += timedelta(days=timeline_days)
        
        return estimated_completion.isoformat()
    
    def _publish_contribution(self, contribution: Contribution) -> Dict[str, Any]:
        """Publish approved contribution."""
        try:
            # Generate registry URL
            registry_url = f"https://registry.beginnings.dev/{contribution.type.value}s/{contribution.name}"
            
            contribution.status = ContributionStatus.PUBLISHED
            contribution.published_at = datetime.now(timezone.utc).isoformat()
            contribution.registry_url = registry_url
            
            return {
                'success': True,
                'registry_url': registry_url
            }
            
        except Exception as e:
            self.logger.error(f"Failed to publish contribution: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _load_data(self) -> None:
        """Load data from storage."""
        try:
            # Load contributions
            contributions_file = self.storage_path / "contributions.json"
            if contributions_file.exists():
                with open(contributions_file, 'r') as f:
                    data = json.load(f)
                    for contrib_id, contrib_data in data.items():
                        self.contributions[contrib_id] = Contribution(**contrib_data)
            
            # Load contributors
            contributors_file = self.storage_path / "contributors.json"
            if contributors_file.exists():
                with open(contributors_file, 'r') as f:
                    data = json.load(f)
                    for contrib_id, contrib_data in data.items():
                        self.contributors[contrib_id] = Contributor(**contrib_data)
                        
        except Exception as e:
            self.logger.warning(f"Failed to load data: {e}")
    
    def _save_data(self) -> None:
        """Save data to storage."""
        try:
            # Save contributions
            contributions_file = self.storage_path / "contributions.json"
            with open(contributions_file, 'w') as f:
                data = {k: v.__dict__ for k, v in self.contributions.items()}
                # Convert enums to strings
                for contrib_data in data.values():
                    if 'type' in contrib_data:
                        contrib_data['type'] = contrib_data['type'].value
                    if 'status' in contrib_data:
                        contrib_data['status'] = contrib_data['status'].value
                json.dump(data, f, indent=2)
            
            # Save contributors
            contributors_file = self.storage_path / "contributors.json"
            with open(contributors_file, 'w') as f:
                data = {k: v.__dict__ for k, v in self.contributors.items()}
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")