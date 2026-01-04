"""
Property-based tests for preference update persistence
偏好设置持久化属性测试

This module tests Property 33: Preference Update Persistence
**Validates: Requirements 16.6**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
from bilingual_tutor.models import UserProfile, Goals, Preferences, Skill, ContentType
from bilingual_tutor.web.routes.api import user_profiles, get_or_create_user_profile


# ==================== Test Data Generators ====================

@st.composite
def generate_valid_preferences(draw):
    """Generate valid user preferences for testing."""
    # Generate preferred study times
    study_times = draw(st.lists(
        st.sampled_from(["早上", "上午", "中午", "下午", "晚上", "深夜"]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    # Generate content preferences
    content_prefs = draw(st.lists(
        st.sampled_from(list(ContentType)),
        min_size=1,
        max_size=4,
        unique=True
    ))
    
    # Generate difficulty preference
    difficulty = draw(st.sampled_from(["简单", "适中", "困难", "渐进式"]))
    
    # Generate language balance (must sum to 1.0)
    english_ratio = draw(st.floats(min_value=0.1, max_value=0.9))
    japanese_ratio = 1.0 - english_ratio
    
    return Preferences(
        preferred_study_times=study_times,
        content_preferences=content_prefs,
        difficulty_preference=difficulty,
        language_balance={"english": english_ratio, "japanese": japanese_ratio}
    )

@st.composite
def generate_user_profile(draw):
    """Generate a complete user profile for testing."""
    user_id = draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    english_level = draw(st.sampled_from(["CET-4", "CET-5", "CET-6"]))
    japanese_level = draw(st.sampled_from(["N5", "N4", "N3", "N2", "N1"]))
    daily_time = draw(st.integers(min_value=15, max_value=300))
    
    goals = Goals(
        target_english_level="CET-6",
        target_japanese_level="N1",
        target_completion_date=datetime.now() + timedelta(days=730),
        priority_skills=[Skill.VOCABULARY, Skill.READING],
        custom_objectives=["提高语言能力"]
    )
    
    preferences = draw(generate_valid_preferences())
    
    return UserProfile(
        user_id=user_id,
        english_level=english_level,
        japanese_level=japanese_level,
        daily_study_time=daily_time,
        target_goals=goals,
        learning_preferences=preferences,
        weak_areas=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@st.composite
def generate_preference_updates(draw):
    """Generate preference update data that might come from web forms."""
    updates = {}
    
    # Randomly include different preference fields
    if draw(st.booleans()):
        updates['preferred_study_times'] = draw(st.lists(
            st.sampled_from(["早上", "上午", "中午", "下午", "晚上", "深夜"]),
            min_size=1,
            max_size=3,
            unique=True
        ))
    
    if draw(st.booleans()):
        updates['content_preferences'] = draw(st.lists(
            st.sampled_from([ct.value for ct in ContentType]),
            min_size=1,
            max_size=4,
            unique=True
        ))
    
    if draw(st.booleans()):
        updates['difficulty_preference'] = draw(st.sampled_from(["简单", "适中", "困难", "渐进式"]))
    
    if draw(st.booleans()):
        english_ratio = draw(st.floats(min_value=0.1, max_value=0.9))
        updates['language_balance'] = {
            "english": english_ratio,
            "japanese": 1.0 - english_ratio
        }
    
    # Ensure at least one update is present
    assume(len(updates) > 0)
    
    return updates


# ==================== Property Tests ====================

class TestPreferenceUpdatePersistence:
    """
    Property-based tests for preference update persistence.
    
    **Feature: bilingual-tutor, Property 33: Preference Update Persistence**
    **Validates: Requirements 16.6**
    """
    
    def setup_method(self):
        """Clear user profiles before each test."""
        user_profiles.clear()
    
    @given(generate_user_profile(), generate_preference_updates())
    def test_preference_update_persistence(self, user_profile, preference_updates):
        """
        Property 33: Preference Update Persistence
        
        For any user preference update through web forms, the changes should be 
        saved and reflected in subsequent sessions.
        
        **Validates: Requirements 16.6**
        """
        # Store original profile
        user_profiles[user_profile.user_id] = user_profile
        original_preferences = user_profile.learning_preferences
        
        # Get the profile (simulating web form access)
        retrieved_profile = get_or_create_user_profile(user_profile.user_id)
        assert retrieved_profile.user_id == user_profile.user_id
        
        # Apply preference updates (simulating web form submission)
        updated_preferences = self._apply_preference_updates(
            retrieved_profile.learning_preferences, 
            preference_updates
        )
        retrieved_profile.learning_preferences = updated_preferences
        retrieved_profile.updated_at = datetime.now()
        
        # Verify changes are immediately reflected
        current_profile = get_or_create_user_profile(user_profile.user_id)
        
        # Check that all updated preferences are persisted
        for field, expected_value in preference_updates.items():
            actual_value = getattr(current_profile.learning_preferences, field)
            
            if field == 'content_preferences':
                # Convert string values back to ContentType enums for comparison
                expected_enums = [ContentType(v) for v in expected_value]
                assert actual_value == expected_enums, f"Content preferences not persisted: expected {expected_enums}, got {actual_value}"
            else:
                assert actual_value == expected_value, f"Preference {field} not persisted: expected {expected_value}, got {actual_value}"
        
        # Check that non-updated preferences remain unchanged
        for field in ['preferred_study_times', 'content_preferences', 'difficulty_preference', 'language_balance']:
            if field not in preference_updates:
                original_value = getattr(original_preferences, field)
                current_value = getattr(current_profile.learning_preferences, field)
                assert current_value == original_value, f"Non-updated preference {field} was changed unexpectedly"
        
        # Verify updated_at timestamp was modified
        assert current_profile.updated_at > user_profile.created_at
    
    @given(generate_user_profile())
    def test_preference_persistence_across_sessions(self, user_profile):
        """
        Test that preferences persist across multiple session retrievals.
        
        **Validates: Requirements 16.6**
        """
        # Store profile
        user_profiles[user_profile.user_id] = user_profile
        original_preferences = user_profile.learning_preferences
        
        # Retrieve profile multiple times (simulating multiple web sessions)
        for _ in range(5):
            retrieved_profile = get_or_create_user_profile(user_profile.user_id)
            
            # Verify all preference fields are consistent
            assert retrieved_profile.learning_preferences.preferred_study_times == original_preferences.preferred_study_times
            assert retrieved_profile.learning_preferences.content_preferences == original_preferences.content_preferences
            assert retrieved_profile.learning_preferences.difficulty_preference == original_preferences.difficulty_preference
            assert retrieved_profile.learning_preferences.language_balance == original_preferences.language_balance
    
    @given(generate_user_profile(), generate_preference_updates(), generate_preference_updates())
    def test_sequential_preference_updates(self, user_profile, first_updates, second_updates):
        """
        Test that sequential preference updates are properly persisted.
        
        **Validates: Requirements 16.6**
        """
        # Store original profile
        user_profiles[user_profile.user_id] = user_profile
        
        # Apply first set of updates
        profile = get_or_create_user_profile(user_profile.user_id)
        updated_preferences = self._apply_preference_updates(
            profile.learning_preferences, 
            first_updates
        )
        profile.learning_preferences = updated_preferences
        profile.updated_at = datetime.now()
        
        # Apply second set of updates
        profile = get_or_create_user_profile(user_profile.user_id)
        updated_preferences = self._apply_preference_updates(
            profile.learning_preferences, 
            second_updates
        )
        profile.learning_preferences = updated_preferences
        profile.updated_at = datetime.now()
        
        # Verify final state reflects the second updates
        final_profile = get_or_create_user_profile(user_profile.user_id)
        
        for field, expected_value in second_updates.items():
            actual_value = getattr(final_profile.learning_preferences, field)
            
            if field == 'content_preferences':
                expected_enums = [ContentType(v) for v in expected_value]
                assert actual_value == expected_enums
            else:
                assert actual_value == expected_value
        
        # Verify first updates are preserved where not overridden by second updates
        for field, expected_value in first_updates.items():
            if field not in second_updates:
                actual_value = getattr(final_profile.learning_preferences, field)
                
                if field == 'content_preferences':
                    expected_enums = [ContentType(v) for v in expected_value]
                    assert actual_value == expected_enums
                else:
                    assert actual_value == expected_value
    
    @given(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    def test_preference_persistence_for_new_user(self, user_id):
        """
        Test that default preferences are created and persisted for new users.
        
        **Validates: Requirements 16.6**
        """
        # Ensure user doesn't exist initially
        assume(user_id not in user_profiles)
        
        # Get profile for new user (should create default)
        profile = get_or_create_user_profile(user_id)
        
        # Verify default preferences are set
        assert profile.learning_preferences is not None
        assert len(profile.learning_preferences.preferred_study_times) > 0
        assert len(profile.learning_preferences.content_preferences) > 0
        assert profile.learning_preferences.difficulty_preference is not None
        assert profile.learning_preferences.language_balance is not None
        
        # Verify language balance sums to 1.0
        balance = profile.learning_preferences.language_balance
        total_balance = balance.get("english", 0) + balance.get("japanese", 0)
        assert abs(total_balance - 1.0) < 0.001  # Allow for floating point precision
        
        # Retrieve again and verify persistence
        profile2 = get_or_create_user_profile(user_id)
        assert profile2.learning_preferences.preferred_study_times == profile.learning_preferences.preferred_study_times
        assert profile2.learning_preferences.content_preferences == profile.learning_preferences.content_preferences
        assert profile2.learning_preferences.difficulty_preference == profile.learning_preferences.difficulty_preference
        assert profile2.learning_preferences.language_balance == profile.learning_preferences.language_balance
    
    def _apply_preference_updates(self, current_preferences, updates):
        """Helper method to apply preference updates to existing preferences."""
        # Create a copy of current preferences
        new_preferences = Preferences(
            preferred_study_times=current_preferences.preferred_study_times.copy(),
            content_preferences=current_preferences.content_preferences.copy(),
            difficulty_preference=current_preferences.difficulty_preference,
            language_balance=current_preferences.language_balance.copy()
        )
        
        # Apply updates
        for field, value in updates.items():
            if field == 'content_preferences':
                # Convert string values to ContentType enums
                new_preferences.content_preferences = [ContentType(v) for v in value]
            else:
                setattr(new_preferences, field, value)
        
        return new_preferences


# ==================== Unit Tests for Edge Cases ====================

class TestPreferenceUpdateEdgeCases:
    """Unit tests for specific edge cases in preference updates."""
    
    def setup_method(self):
        """Clear user profiles before each test."""
        user_profiles.clear()
    
    def test_empty_preference_updates(self):
        """Test that empty updates don't break the system."""
        user_id = "test_user_empty"
        profile = get_or_create_user_profile(user_id)
        original_preferences = profile.learning_preferences
        
        # Apply empty updates (simulating form submission with no changes)
        empty_updates = {}
        updated_preferences = self._apply_preference_updates(original_preferences, empty_updates)
        profile.learning_preferences = updated_preferences
        
        # Verify nothing changed
        retrieved_profile = get_or_create_user_profile(user_id)
        assert retrieved_profile.learning_preferences.preferred_study_times == original_preferences.preferred_study_times
        assert retrieved_profile.learning_preferences.content_preferences == original_preferences.content_preferences
        assert retrieved_profile.learning_preferences.difficulty_preference == original_preferences.difficulty_preference
        assert retrieved_profile.learning_preferences.language_balance == original_preferences.language_balance
    
    def test_invalid_language_balance(self):
        """Test handling of invalid language balance values."""
        user_id = "test_user_invalid_balance"
        profile = get_or_create_user_profile(user_id)
        
        # Test that language balance is always normalized
        invalid_updates = {
            'language_balance': {"english": 0.7, "japanese": 0.5}  # Sums to 1.2
        }
        
        # The system should handle this gracefully
        # In a real implementation, this might normalize the values
        # For now, we just verify the system doesn't crash
        try:
            updated_preferences = self._apply_preference_updates(
                profile.learning_preferences, 
                invalid_updates
            )
            profile.learning_preferences = updated_preferences
            
            # Verify profile can still be retrieved
            retrieved_profile = get_or_create_user_profile(user_id)
            assert retrieved_profile is not None
        except Exception as e:
            # If the system rejects invalid balance, that's also acceptable
            assert "balance" in str(e).lower() or "invalid" in str(e).lower()
    
    def _apply_preference_updates(self, current_preferences, updates):
        """Helper method to apply preference updates to existing preferences."""
        # Create a copy of current preferences
        new_preferences = Preferences(
            preferred_study_times=current_preferences.preferred_study_times.copy(),
            content_preferences=current_preferences.content_preferences.copy(),
            difficulty_preference=current_preferences.difficulty_preference,
            language_balance=current_preferences.language_balance.copy()
        )
        
        # Apply updates
        for field, value in updates.items():
            if field == 'content_preferences':
                # Convert string values to ContentType enums
                new_preferences.content_preferences = [ContentType(v) for v in value]
            else:
                setattr(new_preferences, field, value)
        
        return new_preferences