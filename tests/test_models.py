"""
Tests for core data models and interfaces.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st

from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, Content, LearningActivity,
    StudySession, TimeAllocation, WeakArea, ActivityResult,
    ActivityType, ContentType, Skill, SessionStatus, MasteryLevel
)
from tests.conftest import user_profile_strategy, content_strategy, time_allocation_strategy


class TestDataModels:
    """Test core data model functionality."""
    
    def test_user_profile_creation(self, sample_user_profile):
        """Test that user profiles can be created with valid data."""
        assert sample_user_profile.user_id == "test_user_001"
        assert sample_user_profile.english_level == "CET-4"
        assert sample_user_profile.japanese_level == "N5"
        assert sample_user_profile.daily_study_time == 60
        assert len(sample_user_profile.weak_areas) == 0
    
    def test_content_creation(self, sample_content):
        """Test that content objects can be created with valid data."""
        assert sample_content.content_id == "content_001"
        assert sample_content.language == "english"
        assert sample_content.difficulty_level == "CET-4"
        assert sample_content.content_type == ContentType.ARTICLE
        assert 0.0 <= sample_content.quality_score <= 1.0
    
    def test_time_allocation_creation(self, sample_time_allocation):
        """Test that time allocation objects maintain proper constraints."""
        assert sample_time_allocation.total_minutes == 60
        assert sample_time_allocation.review_minutes == 12  # 20% of 60
        assert sample_time_allocation.english_minutes + sample_time_allocation.japanese_minutes <= 48
    
    @given(user_profile_strategy())
    def test_user_profile_property_validation(self, user_profile):
        """Property test: User profiles should have valid constraints."""
        # Feature: bilingual-tutor, Property: User profile validation
        assert user_profile.daily_study_time >= 30
        assert user_profile.daily_study_time <= 120
        assert user_profile.english_level in ["CET-4", "CET-5", "CET-6"]
        assert user_profile.japanese_level in ["N5", "N4", "N3", "N2", "N1"]
        assert len(user_profile.target_goals.priority_skills) >= 1
    
    @given(content_strategy())
    def test_content_property_validation(self, content):
        """Property test: Content should have valid properties."""
        # Feature: bilingual-tutor, Property: Content validation
        assert content.language in ["english", "japanese"]
        assert 0.0 <= content.quality_score <= 1.0
        assert len(content.title) >= 1
        assert len(content.body) >= 10
        
        if content.language == "english":
            assert content.difficulty_level in ["CET-4", "CET-5", "CET-6"]
        else:
            assert content.difficulty_level in ["N5", "N4", "N3", "N2", "N1"]
    
    @given(time_allocation_strategy())
    def test_time_allocation_property_validation(self, time_allocation):
        """Property test: Time allocation should maintain 20% review constraint."""
        # Feature: bilingual-tutor, Property: Time allocation validation
        expected_review = int(time_allocation.total_minutes * 0.2)
        assert time_allocation.review_minutes == expected_review
        
        remaining_time = time_allocation.total_minutes - time_allocation.review_minutes
        allocated_time = time_allocation.english_minutes + time_allocation.japanese_minutes
        assert allocated_time <= remaining_time