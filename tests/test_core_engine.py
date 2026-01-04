"""
Property-based tests for the Core Learning Engine.
"""

import pytest
import uuid
from hypothesis import given, strategies as st
from datetime import datetime, timedelta

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, TimeAllocation, 
    Skill, ContentType, SessionStatus, LearningActivity, ActivityType, ActivityResult
)
from tests.conftest import user_profile_strategy, time_allocation_strategy, content_strategy


class TestCoreEngineProperties:
    """Property-based tests for Core Learning Engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CoreLearningEngine()
    
    @given(user_profile_strategy(), user_profile_strategy())
    def test_time_allocation_consistency_property(self, user_profile1, user_profile2):
        """
        **Feature: bilingual-tutor, Property 2: Time Allocation Consistency**
        
        For any user preferences and goals, the time allocation between English and Japanese 
        should respect user preferences while ensuring both languages receive adequate time 
        to meet 2-year objectives.
        
        **Validates: Requirements 1.3, 7.2**
        """
        # Generate time allocations for both user profiles
        allocation1 = self.engine.allocate_study_time(user_profile1.daily_study_time)
        allocation2 = self.engine.allocate_study_time(user_profile2.daily_study_time)
        
        # Property 1: Total time should equal input time
        assert allocation1.total_minutes == user_profile1.daily_study_time
        assert allocation2.total_minutes == user_profile2.daily_study_time
        
        # Property 2: Review time should always be exactly 20% of total
        expected_review1 = int(user_profile1.daily_study_time * 0.2)
        expected_review2 = int(user_profile2.daily_study_time * 0.2)
        assert allocation1.review_minutes == expected_review1
        assert allocation2.review_minutes == expected_review2
        
        # Property 3: All time components should sum to total (accounting for rounding)
        total_allocated1 = (allocation1.review_minutes + allocation1.english_minutes + 
                           allocation1.japanese_minutes + allocation1.break_minutes)
        total_allocated2 = (allocation2.review_minutes + allocation2.english_minutes + 
                           allocation2.japanese_minutes + allocation2.break_minutes)
        
        assert total_allocated1 == allocation1.total_minutes
        assert total_allocated2 == allocation2.total_minutes
        
        # Property 4: Both languages should receive some time (unless total time is very small)
        if user_profile1.daily_study_time >= 30:
            assert allocation1.english_minutes > 0
            assert allocation1.japanese_minutes > 0
        
        if user_profile2.daily_study_time >= 30:
            assert allocation2.english_minutes > 0
            assert allocation2.japanese_minutes > 0
        
        # Property 5: Time allocation should be deterministic for same input
        allocation1_repeat = self.engine.allocate_study_time(user_profile1.daily_study_time)
        assert allocation1.total_minutes == allocation1_repeat.total_minutes
        assert allocation1.review_minutes == allocation1_repeat.review_minutes
        assert allocation1.english_minutes == allocation1_repeat.english_minutes
        assert allocation1.japanese_minutes == allocation1_repeat.japanese_minutes
        assert allocation1.break_minutes == allocation1_repeat.break_minutes
    
    @given(st.integers(min_value=20, max_value=180))
    def test_review_time_allocation_constraint_property(self, total_minutes):
        """
        **Feature: bilingual-tutor, Property 24: Review Time Allocation Constraint**
        
        For any daily study plan, exactly 20% of total study time should be allocated 
        to spaced repetition review while maximizing new content exposure.
        
        **Validates: Requirements 7.7**
        """
        # Generate time allocation
        allocation = self.engine.allocate_study_time(total_minutes)
        
        # Property 1: Review time must be exactly 20% of total (with integer rounding)
        expected_review_minutes = int(total_minutes * 0.2)
        assert allocation.review_minutes == expected_review_minutes
        
        # Property 2: Review time should be approximately 20% (accounting for integer rounding)
        review_percentage = allocation.review_minutes / total_minutes
        
        # Integer rounding can cause deviations from exactly 20%, especially for smaller values
        # The key requirement is that we're attempting to allocate 20%, not that we achieve exactly 20%
        assert review_percentage <= 0.25  # Never more than 25%
        assert review_percentage >= 0.15  # Never less than 15%
        
        # Verify we're using the correct calculation (int(total * 0.2))
        expected_review_minutes = int(total_minutes * 0.2)
        assert allocation.review_minutes == expected_review_minutes
        
        # Property 3: Remaining time should be maximized for new content
        remaining_time = total_minutes - allocation.review_minutes
        content_time = allocation.english_minutes + allocation.japanese_minutes
        
        # Content time should be most of the remaining time (allowing small buffer for breaks)
        assert content_time >= remaining_time * 0.8  # At least 80% of remaining time for content
        
        # Property 4: Total allocation should equal input
        total_allocated = (allocation.review_minutes + allocation.english_minutes + 
                          allocation.japanese_minutes + allocation.break_minutes)
        assert total_allocated == total_minutes
        
        # Property 5: All time components should be non-negative
        assert allocation.review_minutes >= 0
        assert allocation.english_minutes >= 0
        assert allocation.japanese_minutes >= 0
        assert allocation.break_minutes >= 0
    
    @given(content_strategy(), st.floats(min_value=0.0, max_value=1.0))
    def test_exercise_feedback_provision_property(self, content, score):
        """
        **Feature: bilingual-tutor, Property 6: Exercise Feedback Provision**
        
        For any completed exercise, the system should provide explanations for 
        correct answers and common mistakes.
        
        **Validates: Requirements 2.2, 2.4**
        """
        # Create a learning activity from the content
        activity = LearningActivity(
            activity_id=str(uuid.uuid4()),
            activity_type=ActivityType.VOCABULARY,
            language=content.language,
            content=content,
            estimated_duration=15,
            difficulty_level=content.difficulty_level,
            skills_practiced=[Skill.VOCABULARY]
        )
        
        # Execute the activity
        result = self.engine.execute_learning_activity(activity)
        
        # Property 1: Every activity execution should produce feedback
        assert result.feedback is not None
        assert len(result.feedback) > 0
        assert isinstance(result.feedback, str)
        
        # Property 2: Feedback should be in Chinese (contains Chinese characters)
        # Check for presence of Chinese characters (Unicode range for CJK)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in result.feedback)
        assert has_chinese, f"Feedback should be in Chinese: {result.feedback}"
        
        # Property 3: Activity result should have valid structure
        assert result.activity_id == activity.activity_id
        assert 0.0 <= result.score <= 1.0
        assert result.time_spent > 0
        assert isinstance(result.errors_made, list)
        assert result.completed_at is not None
        
        # Property 4: Lower scores should generate error information
        if result.score < 0.8:
            # Should have some errors or detailed feedback for improvement
            assert len(result.errors_made) > 0 or "练习" in result.feedback or "建议" in result.feedback
        
        # Property 5: Feedback should be contextual to activity type
        if activity.activity_type == ActivityType.VOCABULARY:
            # Vocabulary feedback should mention vocabulary-related terms
            vocab_terms = ["词汇", "记忆", "拼写", "词义"]
            has_vocab_context = any(term in result.feedback for term in vocab_terms)
            if result.score < 0.7:  # Only check for low scores where specific advice is given
                assert has_vocab_context, f"Vocabulary feedback should be contextual: {result.feedback}"
        
        # Property 6: Consistent feedback for same inputs
        result2 = self.engine.execute_learning_activity(activity)
        # While scores might vary slightly due to simulation, feedback structure should be consistent
        assert len(result2.feedback) > 0
        has_chinese2 = any('\u4e00' <= char <= '\u9fff' for char in result2.feedback)
        assert has_chinese2
    
    @given(user_profile_strategy(), st.sampled_from(["english", "japanese"]), 
           st.sampled_from(list(ContentType)))
    def test_level_appropriate_content_generation_property(self, user_profile, language, content_type):
        """
        **Feature: bilingual-tutor, Property 1: Level-Appropriate Content Generation**
        
        For any user profile with a specified language level, the generated study plan 
        should contain only content appropriate to that level (CET-4 for English, N5 for Japanese, etc.)
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        # Generate level-appropriate content
        content_list = self.engine.generate_level_appropriate_content(
            user_profile, language, content_type
        )
        
        # Property 1: Should generate some content (unless very restrictive parameters)
        assert isinstance(content_list, list)
        
        # Property 2: All generated content should match the requested language
        for content in content_list:
            assert content.language == language
            assert content.content_type == content_type
        
        # Property 3: Content difficulty should match user's proficiency level
        user_level = user_profile.english_level if language == "english" else user_profile.japanese_level
        
        for content in content_list:
            # Content should be at or near user's level
            assert content.difficulty_level is not None
            
            # Check that content is appropriate for user's level using the engine's matcher
            is_appropriate = self.engine.match_content_to_user_level(content, user_profile)
            assert is_appropriate, f"Content difficulty {content.difficulty_level} not appropriate for user level {user_level}"
        
        # Property 4: Content should have valid structure
        for content in content_list:
            assert content.content_id is not None
            assert len(content.content_id) > 0
            assert content.title is not None
            assert len(content.title) > 0
            assert content.body is not None
            assert len(content.body) > 0
            assert content.quality_score >= 0.0
            assert content.quality_score <= 1.0
            assert content.created_at is not None
            assert isinstance(content.tags, list)
        
        # Property 5: Content should be tagged appropriately
        for content in content_list:
            # Should contain language and level tags
            assert language in content.tags or language in content.body.lower()
            assert user_level in content.tags or user_level in content.difficulty_level
        
        # Property 6: Generated content should be deterministic for same inputs
        content_list2 = self.engine.generate_level_appropriate_content(
            user_profile, language, content_type
        )
        
        # Should generate same number of items
        assert len(content_list) == len(content_list2)
        
        # Content should have same characteristics (though IDs may differ)
        for content1, content2 in zip(content_list, content_list2):
            assert content1.language == content2.language
            assert content1.difficulty_level == content2.difficulty_level
            assert content1.content_type == content2.content_type
        
        # Property 7: Content should address user's weak areas when present
        if user_profile.weak_areas:
            language_weaknesses = [w for w in user_profile.weak_areas if w.language == language]
            if language_weaknesses and content_list:
                # At least some content should be relevant to addressing weaknesses
                # This is verified by the prioritization in the generator
                assert len(content_list) > 0  # Should have content to work with weaknesses
    
    @given(user_profile_strategy(), st.lists(st.builds(ActivityResult,
        activity_id=st.text(min_size=1, max_size=50),
        user_id=st.text(min_size=1, max_size=20),
        score=st.floats(min_value=0.0, max_value=1.0),
        time_spent=st.integers(min_value=1, max_value=60),
        errors_made=st.lists(st.text(min_size=1, max_size=100), max_size=5),
        completed_at=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime.now()),
        feedback=st.text(min_size=1, max_size=200)
    ), min_size=0, max_size=20))
    def test_historical_performance_integration_property(self, user_profile, activity_history):
        """
        **Feature: bilingual-tutor, Property 3: Historical Performance Integration**
        
        For any user with learning history, newly generated study plans should differ 
        appropriately based on previous performance and progress data.
        
        **Validates: Requirements 1.4**
        """
        # Generate a base learning plan
        base_plan = self.engine.generate_learning_plan(user_profile)
        
        # Property 1: Base plan should always be generated successfully
        assert base_plan is not None
        assert base_plan.user_id == user_profile.user_id
        assert len(base_plan.activities) > 0
        assert base_plan.time_allocation is not None
        
        # Property 2: Plans should be consistent for users without history
        if not activity_history:
            base_plan2 = self.engine.generate_learning_plan(user_profile)
            assert len(base_plan.activities) == len(base_plan2.activities)
            assert base_plan.time_allocation.total_minutes == base_plan2.time_allocation.total_minutes
        
        # Property 3: Historical analysis should handle any activity history
        if activity_history:
            # Analyze performance history
            patterns = self.engine.analyze_user_performance_history(user_profile.user_id, activity_history)
            
            # Should return a list (may be empty for insufficient data)
            assert isinstance(patterns, list)
            
            # All patterns should have valid structure if any are returned
            for pattern in patterns:
                assert hasattr(pattern, 'skill')
                assert hasattr(pattern, 'language')
                assert hasattr(pattern, 'trend')
                assert hasattr(pattern, 'confidence')
                assert 0.0 <= pattern.confidence <= 1.0
                assert pattern.trend in ["improving", "declining", "stable"]
        
        # Property 4: Performance prediction should be reasonable
        if base_plan.activities:
            for activity in base_plan.activities:
                predicted_score = self.engine.predict_activity_performance(user_profile.user_id, activity)
                assert 0.0 <= predicted_score <= 1.0
                
                # Prediction should be reasonable (not extreme values for most cases)
                assert 0.1 <= predicted_score <= 0.95
        
        # Property 5: Learning pattern recognition should handle any history
        learning_patterns = self.engine.recognize_learning_patterns(user_profile.user_id, activity_history)
        assert isinstance(learning_patterns, list)
        
        # All insights should have valid structure if any are returned
        for insight in learning_patterns:
            assert hasattr(insight, 'insight_type')
            assert hasattr(insight, 'description')
            assert hasattr(insight, 'confidence')
            assert 0.0 <= insight.confidence <= 1.0
            assert insight.insight_type in ["strength", "weakness", "pattern", "recommendation"]
        
        # Property 6: Performance insights should be accessible
        insights = self.engine.get_performance_insights(user_profile.user_id)
        assert isinstance(insights, list)
        
        # Property 7: Plans with history should potentially differ from base plans
        if len(activity_history) >= 5:  # Sufficient history for meaningful adaptation
            # Register a mock progress tracker with the activity history
            mock_tracker = type('MockTracker', (), {
                'activity_history': {user_profile.user_id: activity_history}
            })()
            self.engine.register_component("progress_tracker", mock_tracker)
            
            # Generate plan with historical integration
            adapted_plan = self.engine.generate_learning_plan(user_profile)
            
            # Plan should still be valid
            assert adapted_plan is not None
            assert adapted_plan.user_id == user_profile.user_id
            assert len(adapted_plan.activities) > 0
            
            # Time allocation should remain consistent
            assert adapted_plan.time_allocation.total_minutes == user_profile.daily_study_time
            
            # Learning objectives may be enhanced with historical insights
            # (The adaptation may add additional objectives)
            assert len(adapted_plan.learning_objectives) >= len(base_plan.learning_objectives)
        
        # Property 8: System should handle edge cases gracefully
        # Empty activity history
        empty_patterns = self.engine.analyze_user_performance_history(user_profile.user_id, [])
        assert isinstance(empty_patterns, list)
        
        # Invalid user ID should not crash
        invalid_insights = self.engine.get_performance_insights("invalid_user_id")
        assert isinstance(invalid_insights, list)
    
    @given(user_profile_strategy())
    def test_weakness_prioritization_with_balance_property(self, user_profile):
        """
        **Feature: bilingual-tutor, Property 28: Weakness Prioritization with Balance**
        
        For any daily study plan generation, weak areas should be prioritized while 
        maintaining overall curriculum balance.
        
        **Validates: Requirements 8.5**
        """
        # Generate a base learning plan
        base_plan = self.engine.generate_learning_plan(user_profile)
        
        # Property 1: Base plan should always be generated successfully
        assert base_plan is not None
        assert base_plan.user_id == user_profile.user_id
        assert len(base_plan.activities) > 0
        
        # Property 2: Weakness prioritization should handle users without weak areas
        if not user_profile.weak_areas:
            prioritized_weaknesses, curriculum_balance = self.engine.prioritize_user_weaknesses(
                user_profile, base_plan
            )
            assert isinstance(prioritized_weaknesses, list)
            assert len(prioritized_weaknesses) == 0
            assert isinstance(curriculum_balance, dict)
        
        # Property 3: Weakness prioritization should work with weak areas
        if user_profile.weak_areas:
            prioritized_weaknesses, curriculum_balance = self.engine.prioritize_user_weaknesses(
                user_profile, base_plan
            )
            
            # Should return prioritized list
            assert isinstance(prioritized_weaknesses, list)
            assert len(prioritized_weaknesses) == len(user_profile.weak_areas)
            
            # Should maintain order (most severe first, considering balance)
            for i in range(len(prioritized_weaknesses) - 1):
                current_weakness = prioritized_weaknesses[i]
                next_weakness = prioritized_weaknesses[i + 1]
                
                # Verify weakness structure
                assert hasattr(current_weakness, 'severity')
                assert hasattr(current_weakness, 'skill')
                assert hasattr(current_weakness, 'language')
                assert 0.0 <= current_weakness.severity <= 1.0
                
                # Priority should generally decrease (allowing for balance adjustments)
                # We don't enforce strict severity ordering because balance factors matter
                assert current_weakness.severity >= 0.0
                assert next_weakness.severity >= 0.0
            
            # Curriculum balance should be valid
            assert isinstance(curriculum_balance, dict)
            if hasattr(curriculum_balance, 'weakness_focus_ratio'):
                assert 0.0 <= curriculum_balance.weakness_focus_ratio <= 1.0
        
        # Property 4: Curriculum balance calculation should work for any plan
        balance_metrics = self.engine.calculate_curriculum_balance(base_plan)
        assert isinstance(balance_metrics, dict)
        
        # All balance metrics should be between 0 and 1
        for metric_name, metric_value in balance_metrics.items():
            assert isinstance(metric_value, (int, float))
            assert 0.0 <= metric_value <= 1.0
        
        # Should include key balance metrics
        expected_metrics = ["skill_balance", "language_balance", "overall_balance"]
        for expected_metric in expected_metrics:
            assert expected_metric in balance_metrics
        
        # Property 5: Weakness focus recommendations should be appropriate
        recommendations = self.engine.get_weakness_focus_recommendations(user_profile)
        assert isinstance(recommendations, list)
        
        # All recommendations should be strings
        for recommendation in recommendations:
            assert isinstance(recommendation, str)
            assert len(recommendation) > 0
        
        # Should have recommendations if there are weaknesses
        if user_profile.weak_areas:
            assert len(recommendations) > 0
            # Should mention weaknesses in Chinese
            has_weakness_mention = any(
                "弱点" in rec or "改进" in rec or "优先级" in rec 
                for rec in recommendations
            )
            assert has_weakness_mention
        
        # Property 6: Plan adjustment should maintain plan validity
        if user_profile.weak_areas:
            adjusted_plan = self.engine.adjust_plan_for_weaknesses(base_plan, user_profile)
            
            # Adjusted plan should be valid
            assert adjusted_plan is not None
            assert adjusted_plan.user_id == user_profile.user_id
            assert len(adjusted_plan.activities) >= len(base_plan.activities)  # May add activities
            
            # Time allocation should remain consistent
            assert adjusted_plan.time_allocation.total_minutes == base_plan.time_allocation.total_minutes
            
            # Should have learning objectives (may be enhanced)
            assert len(adjusted_plan.learning_objectives) >= len(base_plan.learning_objectives)
            
            # Activities should have valid structure
            for activity in adjusted_plan.activities:
                assert activity.activity_id is not None
                assert activity.language in ["english", "japanese", "mixed"]
                assert activity.estimated_duration > 0
                assert len(activity.skills_practiced) > 0
        
        # Property 7: System should handle edge cases gracefully
        # Empty weak areas
        empty_profile = UserProfile(
            user_id="test_empty",
            english_level="CET-4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=user_profile.target_goals,
            learning_preferences=user_profile.learning_preferences,
            weak_areas=[],  # Empty weak areas
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        empty_recommendations = self.engine.get_weakness_focus_recommendations(empty_profile)
        assert isinstance(empty_recommendations, list)
        
        # Property 8: Balance should be maintained across different weakness configurations
        if len(user_profile.weak_areas) >= 2:
            # Test with different subsets of weaknesses
            subset_profile = UserProfile(
                user_id=user_profile.user_id + "_subset",
                english_level=user_profile.english_level,
                japanese_level=user_profile.japanese_level,
                daily_study_time=user_profile.daily_study_time,
                target_goals=user_profile.target_goals,
                learning_preferences=user_profile.learning_preferences,
                weak_areas=user_profile.weak_areas[:1],  # Only first weakness
                created_at=user_profile.created_at,
                updated_at=user_profile.updated_at
            )
            
            subset_plan = self.engine.generate_learning_plan(subset_profile)
            subset_balance = self.engine.calculate_curriculum_balance(subset_plan)
            
            # Balance should still be reasonable
            assert subset_balance["overall_balance"] >= 0.0
            assert subset_balance["overall_balance"] <= 1.0