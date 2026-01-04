"""
Pytest configuration and shared fixtures for the bilingual tutor system.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import strategies as st
from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, Content, LearningActivity,
    StudySession, TimeAllocation, WeakArea, ActivityResult,
    ActivityType, ContentType, Skill, SessionStatus, MasteryLevel
)


@pytest.fixture
def sample_user_profile():
    """Sample user profile for testing."""
    goals = Goals(
        target_english_level="CET-6",
        target_japanese_level="N1",
        target_completion_date=datetime.now() + timedelta(days=730),  # 2 years
        priority_skills=[Skill.VOCABULARY, Skill.READING],
        custom_objectives=["Business English", "Anime comprehension"]
    )
    
    preferences = Preferences(
        preferred_study_times=["morning", "evening"],
        content_preferences=[ContentType.ARTICLE, ContentType.NEWS],
        difficulty_preference="progressive",
        language_balance={"english": 0.6, "japanese": 0.4}
    )
    
    return UserProfile(
        user_id="test_user_001",
        english_level="CET-4",
        japanese_level="N5",
        daily_study_time=60,
        target_goals=goals,
        learning_preferences=preferences,
        weak_areas=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return Content(
        content_id="content_001",
        title="Basic English Grammar",
        body="This is a sample English grammar lesson...",
        language="english",
        difficulty_level="CET-4",
        content_type=ContentType.ARTICLE,
        source_url="https://example.com/grammar",
        quality_score=0.85,
        created_at=datetime.now(),
        tags=["grammar", "basic", "english"]
    )


@pytest.fixture
def sample_time_allocation():
    """Sample time allocation for testing."""
    return TimeAllocation(
        total_minutes=60,
        review_minutes=12,  # 20% of 60
        english_minutes=30,
        japanese_minutes=18,
        break_minutes=0
    )


# Hypothesis strategies for property-based testing
@st.composite
def user_profile_strategy(draw):
    """Generate random user profiles for property-based testing."""
    user_id = draw(st.text(min_size=1, max_size=20))
    english_level = draw(st.sampled_from(["CET-4", "CET-5", "CET-6"]))
    japanese_level = draw(st.sampled_from(["N5", "N4", "N3", "N2", "N1"]))
    daily_study_time = draw(st.integers(min_value=30, max_value=120))
    
    goals = Goals(
        target_english_level=draw(st.sampled_from(["CET-5", "CET-6", "CET-6+"])),
        target_japanese_level=draw(st.sampled_from(["N4", "N3", "N2", "N1", "N1+"])),
        target_completion_date=datetime.now() + timedelta(days=draw(st.integers(min_value=365, max_value=1095))),
        priority_skills=draw(st.lists(st.sampled_from(list(Skill)), min_size=1, max_size=3, unique=True)),
        custom_objectives=draw(st.lists(st.text(min_size=1, max_size=50), max_size=3))
    )
    
    preferences = Preferences(
        preferred_study_times=draw(st.lists(st.sampled_from(["morning", "afternoon", "evening"]), min_size=1, unique=True)),
        content_preferences=draw(st.lists(st.sampled_from(list(ContentType)), min_size=1, max_size=3, unique=True)),
        difficulty_preference=draw(st.sampled_from(["easy", "progressive", "challenging"])),
        language_balance={"english": draw(st.floats(min_value=0.3, max_value=0.7)), "japanese": draw(st.floats(min_value=0.3, max_value=0.7))}
    )
    
    return UserProfile(
        user_id=user_id,
        english_level=english_level,
        japanese_level=japanese_level,
        daily_study_time=daily_study_time,
        target_goals=goals,
        learning_preferences=preferences,
        weak_areas=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@st.composite
def content_strategy(draw):
    """Generate random content for property-based testing."""
    content_id = draw(st.text(min_size=1, max_size=20))
    title = draw(st.text(min_size=1, max_size=100))
    body = draw(st.text(min_size=10, max_size=1000))
    language = draw(st.sampled_from(["english", "japanese"]))
    
    if language == "english":
        difficulty_level = draw(st.sampled_from(["CET-4", "CET-5", "CET-6"]))
    else:
        difficulty_level = draw(st.sampled_from(["N5", "N4", "N3", "N2", "N1"]))
    
    return Content(
        content_id=content_id,
        title=title,
        body=body,
        language=language,
        difficulty_level=difficulty_level,
        content_type=draw(st.sampled_from(list(ContentType))),
        source_url=f"https://example.com/{content_id}",
        quality_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        created_at=datetime.now(),
        tags=draw(st.lists(st.text(min_size=1, max_size=20), max_size=5))
    )


@st.composite
def time_allocation_strategy(draw):
    """Generate random time allocations for property-based testing."""
    total_minutes = draw(st.integers(min_value=30, max_value=120))
    review_minutes = int(total_minutes * 0.2)  # Always 20%
    remaining_minutes = total_minutes - review_minutes
    
    english_minutes = draw(st.integers(min_value=10, max_value=remaining_minutes - 10))
    japanese_minutes = remaining_minutes - english_minutes
    
    return TimeAllocation(
        total_minutes=total_minutes,
        review_minutes=review_minutes,
        english_minutes=english_minutes,
        japanese_minutes=japanese_minutes,
        break_minutes=0
    )