"""
End-to-end integration tests for the bilingual tutor system.

Tests complete learning session workflows, validates cross-component data flow,
and tests error handling and recovery.

Requirements: All requirements (validation)
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume
import uuid

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, Content, LearningActivity,
    StudySession, TimeAllocation, WeakArea, ActivityResult,
    ActivityType, ContentType, Skill, SessionStatus, MasteryLevel
)


class TestEndToEndIntegration:
    """End-to-end integration tests for complete learning workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CoreLearningEngine()
        self.test_user_id = "e2e_test_user"
    
    def test_complete_learning_session_workflow(self):
        """
        Test complete learning session workflow from start to finish.
        
        Validates:
        - Session creation and initialization
        - Learning plan generation
        - Activity execution
        - Progress tracking
        - Session completion
        """
        # Create test user profile
        user_profile = self._create_test_user_profile()
        
        # Step 1: Start daily session
        session = self.engine.start_daily_session(self.test_user_id)
        
        # Validate session creation
        assert isinstance(session, StudySession)
        assert session.user_id == self.test_user_id
        assert session.status == SessionStatus.PLANNED
        assert session.planned_duration == 60  # Default 60 minutes
        
        # Validate time allocation (20% review requirement)
        time_allocation = session.time_allocation
        assert time_allocation.total_minutes == 60
        assert time_allocation.review_minutes == 12  # 20% of 60
        assert time_allocation.english_minutes + time_allocation.japanese_minutes + time_allocation.review_minutes <= 60
        
        # Step 2: Generate learning plan
        daily_plan = self.engine.generate_learning_plan(user_profile)
        
        # Validate learning plan
        assert daily_plan is not None
        assert daily_plan.user_id == user_profile.user_id
        assert len(daily_plan.activities) > 0
        assert daily_plan.time_allocation.total_minutes == user_profile.daily_study_time
        
        # Validate activities are appropriate for user level
        for activity in daily_plan.activities:
            if activity.language == "english":
                assert activity.difficulty_level == user_profile.english_level
            elif activity.language == "japanese":
                assert activity.difficulty_level == user_profile.japanese_level
        
        # Step 3: Execute activities
        activity_results = []
        for activity in daily_plan.activities[:2]:  # Test first 2 activities
            result = self.engine.execute_learning_activity(activity)
            result.user_id = self.test_user_id
            
            # Validate activity result
            assert isinstance(result, ActivityResult)
            assert 0.0 <= result.score <= 1.0
            assert result.time_spent > 0
            assert result.feedback is not None
            
            activity_results.append(result)
            
            # Process activity completion through all components
            self.engine.process_activity_completion(self.test_user_id, activity, result)
        
        # Step 4: Validate cross-component data flow
        
        # Check progress tracking
        progress_tracker = self.engine.get_component("progress_tracker")
        user_metrics = progress_tracker.get_current_metrics(self.test_user_id)
        assert user_metrics is not None
        
        # Check memory management
        memory_manager = self.engine.get_component("memory_manager")
        content_count = memory_manager.get_content_history_count(self.test_user_id)
        assert content_count >= len(activity_results)
        
        # Check vocabulary tracking
        vocabulary_tracker = self.engine.get_component("vocabulary_tracker")
        english_progress = vocabulary_tracker.get_vocabulary_progress(self.test_user_id, "english")
        japanese_progress = vocabulary_tracker.get_vocabulary_progress(self.test_user_id, "japanese")
        assert english_progress is not None
        assert japanese_progress is not None
        
        # Step 5: Complete session
        completed_session = self.engine.complete_session(self.test_user_id)
        
        # Validate session completion
        assert completed_session is not None
        assert completed_session.status == SessionStatus.COMPLETED
        assert self.engine.get_active_session(self.test_user_id) is None
    
    def test_multi_day_learning_journey(self):
        """
        Test multi-day learning journey with progress accumulation.
        
        Validates:
        - Progress persistence across sessions
        - Adaptive content generation
        - Weakness identification and improvement
        - Level progression tracking
        """
        user_profile = self._create_test_user_profile()
        
        # Simulate 5 days of learning
        for day in range(5):
            # Start daily session
            session = self.engine.start_daily_session(f"{self.test_user_id}_day_{day}")
            
            # Generate and execute learning plan
            daily_plan = self.engine.generate_learning_plan(user_profile)
            
            # Execute activities with varying performance
            for i, activity in enumerate(daily_plan.activities[:2]):
                # Simulate performance variation (better performance over time)
                base_score = 0.6 + (day * 0.05) + (i * 0.02)
                
                result = ActivityResult(
                    activity_id=activity.activity_id,
                    user_id=f"{self.test_user_id}_day_{day}",
                    score=min(0.95, base_score),
                    time_spent=activity.estimated_duration,
                    errors_made=[],
                    completed_at=datetime.now(),
                    feedback="Test feedback"
                )
                
                # Process activity completion
                self.engine.process_activity_completion(
                    f"{self.test_user_id}_day_{day}", activity, result
                )
            
            # Complete session
            self.engine.complete_session(f"{self.test_user_id}_day_{day}")
        
        # Validate progress accumulation
        progress_tracker = self.engine.get_component("progress_tracker")
        
        # Check that progress has been recorded for multiple days
        for day in range(5):
            user_id = f"{self.test_user_id}_day_{day}"
            metrics = progress_tracker.get_current_metrics(user_id)
            assert metrics is not None
        
        # Validate content memory across sessions
        memory_manager = self.engine.get_component("memory_manager")
        total_content_seen = 0
        for day in range(5):
            user_id = f"{self.test_user_id}_day_{day}"
            content_count = memory_manager.get_content_history_count(user_id)
            total_content_seen += content_count
        
        assert total_content_seen >= 10  # At least 2 activities per day for 5 days
    
    def test_error_handling_and_recovery(self):
        """
        Test system error handling and recovery mechanisms.
        
        Validates:
        - Graceful handling of invalid inputs
        - Component failure recovery
        - Data consistency under error conditions
        - System stability after errors
        """
        # Test 1: Invalid user profile handling
        invalid_profile = UserProfile(
            user_id="",  # Invalid empty user ID
            english_level="INVALID_LEVEL",
            japanese_level="INVALID_LEVEL",
            daily_study_time=-10,  # Invalid negative time
            target_goals=None,
            learning_preferences=None,
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # System should handle invalid profile gracefully
        try:
            session = self.engine.start_daily_session("")
            # Should create session with defaults even with invalid user ID
            assert session is not None
        except Exception as e:
            # If exception occurs, it should be handled gracefully
            assert isinstance(e, (ValueError, TypeError))
        
        # Test 2: Component failure simulation
        # Temporarily disable a component to test recovery
        original_memory_manager = self.engine.get_component("memory_manager")
        self.engine.register_component("memory_manager", None)
        
        # System should continue functioning with degraded capability
        try:
            user_profile = self._create_test_user_profile()
            session = self.engine.start_daily_session(self.test_user_id)
            daily_plan = self.engine.generate_learning_plan(user_profile)
            
            # Should still generate plan even with missing component
            assert daily_plan is not None
            assert len(daily_plan.activities) > 0
        finally:
            # Restore component
            self.engine.register_component("memory_manager", original_memory_manager)
        
        # Test 3: Invalid activity execution
        invalid_activity = LearningActivity(
            activity_id="invalid",
            activity_type=ActivityType.VOCABULARY,
            language="invalid_language",
            content=None,  # Invalid None content
            estimated_duration=-5,  # Invalid negative duration
            difficulty_level="INVALID",
            skills_practiced=[]
        )
        
        # Should handle invalid activity gracefully
        try:
            result = self.engine.execute_learning_activity(invalid_activity)
            # If it succeeds, result should be valid
            if result:
                assert isinstance(result, ActivityResult)
                assert 0.0 <= result.score <= 1.0
        except Exception as e:
            # Should be a handled exception type
            assert isinstance(e, (ValueError, TypeError, AttributeError))
        
        # Test 4: Data consistency after errors
        # Verify system state is still consistent after error conditions
        user_profile = self._create_test_user_profile()
        session = self.engine.start_daily_session(self.test_user_id)
        
        # System should still function normally after error recovery
        assert session is not None
        assert session.status == SessionStatus.PLANNED
        
        # Components should still be accessible
        assert self.engine.get_component("progress_tracker") is not None
        assert self.engine.get_component("memory_manager") is not None
        assert self.engine.get_component("vocabulary_tracker") is not None
    
    def test_cross_component_data_flow(self):
        """
        Test data flow between all system components.
        
        Validates:
        - Component communication protocols
        - Data consistency across components
        - Event propagation through system
        - Integration points between layers
        """
        user_profile = self._create_test_user_profile()
        
        # Create and execute a complete learning activity
        session = self.engine.start_daily_session(self.test_user_id)
        daily_plan = self.engine.generate_learning_plan(user_profile)
        
        # Take first activity for detailed testing
        activity = daily_plan.activities[0]
        result = self.engine.execute_learning_activity(activity)
        result.user_id = self.test_user_id
        
        # Process through all components
        self.engine.process_activity_completion(self.test_user_id, activity, result)
        
        # Validate data flow to Progress Tracker
        progress_tracker = self.engine.get_component("progress_tracker")
        metrics = progress_tracker.get_current_metrics(self.test_user_id)
        assert metrics is not None
        
        # Validate data flow to Memory Manager
        memory_manager = self.engine.get_component("memory_manager")
        is_content_recorded = memory_manager.check_content_seen(self.test_user_id, activity.content)
        assert is_content_recorded
        
        # Validate data flow to Vocabulary Tracker
        vocabulary_tracker = self.engine.get_component("vocabulary_tracker")
        vocab_progress = vocabulary_tracker.get_vocabulary_progress(self.test_user_id, activity.language)
        assert vocab_progress is not None
        
        # Validate data flow to Weakness Analyzer
        weakness_analyzer = self.engine.get_component("weakness_analyzer")
        recent_weaknesses = weakness_analyzer.analyze_error_patterns(
            self.test_user_id, timedelta(days=1)
        )
        assert isinstance(recent_weaknesses, list)
        
        # Validate data flow to Assessment Engine
        assessment_engine = self.engine.get_component("assessment_engine")
        assessment = assessment_engine.evaluate_performance(self.test_user_id, result)
        assert assessment is not None
        
        # Validate data flow to Review Scheduler
        review_scheduler = self.engine.get_component("review_scheduler")
        next_review = review_scheduler.schedule_review(activity.content, result.score)
        assert isinstance(next_review, datetime)
        
        # Test comprehensive user status (integrates all components)
        comprehensive_status = self.engine.get_comprehensive_user_status(self.test_user_id)
        
        # Validate all status sections are present
        assert 'progress_metrics' in comprehensive_status
        assert 'vocabulary_progress' in comprehensive_status
        assert 'weakness_analysis' in comprehensive_status
        assert 'review_schedule' in comprehensive_status
        assert 'assessment_data' in comprehensive_status
        assert 'content_history' in comprehensive_status
        
        # Validate data consistency across components
        content_count_memory = memory_manager.get_content_history_count(self.test_user_id)
        content_count_status = comprehensive_status['content_history']['total_content_seen']
        assert content_count_memory == content_count_status
    
    def test_adaptive_content_generation_workflow(self):
        """
        Test adaptive content generation using integrated content management.
        
        Validates:
        - Content discovery and crawling
        - Quality filtering and evaluation
        - User-appropriate content selection
        - Content integration into learning plans
        """
        user_profile = self._create_test_user_profile()
        
        # Test adaptive content generation for both languages
        for language in ["english", "japanese"]:
            adaptive_content = self.engine.generate_adaptive_content(
                self.test_user_id, language, ContentType.ARTICLE
            )
            
            # Validate content generation
            assert isinstance(adaptive_content, list)
            
            # If content is generated, validate properties
            for content in adaptive_content:
                assert isinstance(content, Content)
                assert content.language == language
                assert content.quality_score >= 0.6  # Should meet quality threshold
                
                # Validate content is appropriate for user level
                user_level = user_profile.english_level if language == "english" else user_profile.japanese_level
                is_appropriate = self.engine.match_content_to_user_level(content, user_profile)
                assert is_appropriate or content.difficulty_level == "adaptive"
        
        # Test content integration into learning plan
        session = self.engine.start_daily_session(self.test_user_id)
        optimized_plan = self.engine.optimize_learning_plan(self.test_user_id, user_profile)
        
        # Validate optimized plan uses appropriate content
        assert optimized_plan is not None
        assert len(optimized_plan.activities) > 0
        
        # Validate time allocation is maintained
        assert optimized_plan.time_allocation.total_minutes == user_profile.daily_study_time
        assert optimized_plan.time_allocation.review_minutes == int(user_profile.daily_study_time * 0.2)
    
    def test_weakness_focused_learning_workflow(self):
        """
        Test learning workflow with weakness identification and targeted improvement.
        
        Validates:
        - Weakness identification from performance data
        - Targeted improvement plan generation
        - Curriculum adjustment for weakness focus
        - Progress tracking for improvement areas
        """
        # Create user profile with identified weaknesses
        user_profile = self._create_test_user_profile_with_weaknesses()
        
        # Generate learning plan (should prioritize weaknesses)
        daily_plan = self.engine.generate_learning_plan(user_profile)
        
        # Validate weakness prioritization
        assert daily_plan is not None
        
        # Check if plan addresses user's weak areas
        weakness_skills = [w.skill for w in user_profile.weak_areas]
        plan_skills = []
        for activity in daily_plan.activities:
            plan_skills.extend(activity.skills_practiced)
        
        # At least some activities should target weak skills
        weakness_addressed = any(skill in plan_skills for skill in weakness_skills)
        assert weakness_addressed or len(user_profile.weak_areas) == 0
        
        # Test improvement advisor integration
        improvement_advisor = self.engine.get_component("improvement_advisor")
        
        for weakness in user_profile.weak_areas:
            improvement_plan = improvement_advisor.generate_improvement_plan(weakness)
            assert improvement_plan is not None
            
            # Validate improvement plan has actionable suggestions
            assert hasattr(improvement_plan, 'strategies') or hasattr(improvement_plan, 'recommendations')
        
        # Execute activities and track improvement
        for activity in daily_plan.activities[:2]:
            result = self.engine.execute_learning_activity(activity)
            result.user_id = self.test_user_id
            
            # Process activity to update weakness analysis
            self.engine.process_activity_completion(self.test_user_id, activity, result)
        
        # Validate weakness analysis is updated
        weakness_analyzer = self.engine.get_component("weakness_analyzer")
        updated_weaknesses = weakness_analyzer.analyze_error_patterns(
            self.test_user_id, timedelta(days=1)
        )
        
        # Should have weakness analysis data
        assert isinstance(updated_weaknesses, list)
    
    def _create_test_user_profile(self) -> UserProfile:
        """Create a standard test user profile."""
        goals = Goals(
            target_english_level="CET-6",
            target_japanese_level="N1",
            target_completion_date=datetime.now() + timedelta(days=730),
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
            user_id=self.test_user_id,
            english_level="CET-4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=goals,
            learning_preferences=preferences,
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _create_test_user_profile_with_weaknesses(self) -> UserProfile:
        """Create a test user profile with identified weaknesses."""
        profile = self._create_test_user_profile()
        
        # Add some weak areas
        profile.weak_areas = [
            WeakArea(
                area_id="weak_1",
                skill=Skill.GRAMMAR,
                language="english",
                severity=0.7,
                error_patterns=["tense confusion", "article usage"],
                improvement_suggestions=["Practice past tense", "Study article rules"],
                identified_at=datetime.now()
            ),
            WeakArea(
                area_id="weak_2",
                skill=Skill.VOCABULARY,
                language="japanese",
                severity=0.6,
                error_patterns=["kanji reading", "particle usage"],
                improvement_suggestions=["Practice kanji", "Study particles"],
                identified_at=datetime.now()
            )
        ]
        
        return profile


class TestSystemPerformanceIntegration:
    """Test system performance and scalability under various conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CoreLearningEngine()
    
    def test_concurrent_user_sessions(self):
        """
        Test system handling of multiple concurrent user sessions.
        
        Validates:
        - Multiple active sessions
        - Session isolation
        - Resource management
        - Data consistency across users
        """
        num_users = 5
        user_sessions = {}
        
        # Create multiple concurrent sessions
        for i in range(num_users):
            user_id = f"concurrent_user_{i}"
            session = self.engine.start_daily_session(user_id)
            user_sessions[user_id] = session
            
            # Validate session creation
            assert session is not None
            assert session.user_id == user_id
        
        # Validate session isolation
        for user_id, session in user_sessions.items():
            retrieved_session = self.engine.get_active_session(user_id)
            assert retrieved_session is not None
            assert retrieved_session.session_id == session.session_id
            assert retrieved_session.user_id == user_id
        
        # Test concurrent activity execution
        for user_id in user_sessions.keys():
            user_profile = UserProfile(
                user_id=user_id,
                english_level="CET-4",
                japanese_level="N5",
                daily_study_time=60,
                target_goals=Goals(
                    target_english_level="CET-6",
                    target_japanese_level="N1",
                    target_completion_date=datetime.now() + timedelta(days=730),
                    priority_skills=[Skill.VOCABULARY],
                    custom_objectives=[]
                ),
                learning_preferences=Preferences(
                    language_balance={"english": 0.5, "japanese": 0.5},
                    preferred_study_times=["morning"],
                    content_preferences=[ContentType.ARTICLE],
                    difficulty_preference="moderate"
                ),
                weak_areas=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            daily_plan = self.engine.generate_learning_plan(user_profile)
            assert daily_plan is not None
            assert daily_plan.user_id == user_id
        
        # Clean up sessions
        for user_id in user_sessions.keys():
            completed_session = self.engine.complete_session(user_id)
            assert completed_session is not None
            assert self.engine.get_active_session(user_id) is None
    
    def test_large_content_batch_processing(self):
        """
        Test system performance with large batches of content.
        
        Validates:
        - Batch content processing
        - Memory management with large datasets
        - Performance under load
        - System stability
        """
        # Create large batch of test content
        large_content_batch = []
        batch_size = 50
        
        for i in range(batch_size):
            content = Content(
                content_id=f"batch_content_{i}",
                title=f"Test Content {i}",
                body=f"This is test content number {i} for batch processing validation.",
                language="english" if i % 2 == 0 else "japanese",
                difficulty_level="CET-4" if i % 2 == 0 else "N5",
                content_type=ContentType.ARTICLE,
                source_url=f"https://example.com/content/{i}",
                quality_score=0.7 + (i % 3) * 0.1,  # Varying quality scores
                created_at=datetime.now(),
                tags=["test", "batch", f"item_{i}"]
            )
            large_content_batch.append(content)
        
        # Test batch filtering
        content_filter = self.engine.get_component("content_filter")
        filtered_batch = content_filter.filter_content_batch(large_content_batch, "CET-4")
        
        # Validate batch processing
        assert isinstance(filtered_batch, list)
        assert len(filtered_batch) <= len(large_content_batch)
        
        # Test batch integration
        memory_manager = self.engine.get_component("memory_manager")
        test_user = "batch_test_user"
        
        integrated_count = 0
        for content in filtered_batch[:20]:  # Test first 20 items
            if not memory_manager.check_content_seen(test_user, content):
                memory_manager.record_learned_content(test_user, content)
                integrated_count += 1
        
        # Validate integration results
        final_count = memory_manager.get_content_history_count(test_user)
        assert final_count >= integrated_count
        
        # Test system stability after large batch processing
        session = self.engine.start_daily_session(test_user)
        assert session is not None
        assert session.status == SessionStatus.PLANNED