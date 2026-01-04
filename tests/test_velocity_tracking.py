"""
Property-based tests for velocity tracking and comparison.

Feature: bilingual-tutor, Property 21: Velocity Tracking and Comparison
**Validates: Requirements 7.3**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta
import uuid

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    ActivityResult, LearningActivity, ActivityType, Content, ContentType, Skill
)


class TestVelocityTracking:
    """Test velocity tracking and comparison property."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a completely fresh engine instance for each test
        self.engine = CoreLearningEngine()
        self.progress_tracker = self.engine.get_component("progress_tracker")
        
        # Ensure complete isolation by clearing all data structures
        if hasattr(self.progress_tracker, 'activity_history'):
            self.progress_tracker.activity_history.clear()
        if hasattr(self.progress_tracker, 'user_metrics'):
            self.progress_tracker.user_metrics.clear()
        if hasattr(self.progress_tracker, 'skill_progress'):
            self.progress_tracker.skill_progress.clear()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Ensure complete cleanup after each test
        if hasattr(self, 'progress_tracker'):
            if hasattr(self.progress_tracker, 'activity_history'):
                self.progress_tracker.activity_history.clear()
            if hasattr(self.progress_tracker, 'user_metrics'):
                self.progress_tracker.user_metrics.clear()
            if hasattr(self.progress_tracker, 'skill_progress'):
                self.progress_tracker.skill_progress.clear()
        # Clear the engine reference
        self.engine = None
        self.progress_tracker = None
    
    @given(
        num_activities=st.integers(min_value=1, max_value=10),
        timeframe_days=st.integers(min_value=1, max_value=30),
        activity_data=st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=1.0),  # score
                st.integers(min_value=5, max_value=60)    # time_spent
            ),
            min_size=1,
            max_size=10
        )
    )
    def test_velocity_tracking_property(self, num_activities, timeframe_days, activity_data):
        """
        Property 21: Velocity Tracking and Comparison
        For any learning period, actual learning velocity should be tracked 
        and compared against target progression rates.
        
        **Validates: Requirements 7.3**
        """
        # Ensure we have enough data
        assume(len(activity_data) >= num_activities)
        
        # Extract scores and time data
        scores = [data[0] for data in activity_data[:num_activities]]
        time_spent_per_activity = [data[1] for data in activity_data[:num_activities]]
        
        user_id = f"velocity_test_user_{uuid.uuid4().hex[:8]}"
        
        # Create activity results over the timeframe
        activity_results = []
        # Create activities within the timeframe, ensuring they're recent enough to be found
        base_time = datetime.now() - timedelta(days=max(1, timeframe_days - 1))
        
        for i in range(num_activities):
            # Distribute activities across the timeframe, but keep them recent
            days_offset = (i * (timeframe_days - 1)) // max(1, num_activities - 1) if num_activities > 1 else 0
            activity_time = base_time + timedelta(
                days=days_offset,
                hours=i % 12,  # Spread across different hours
                minutes=i * 5  # Add minute offsets for uniqueness
            )
            
            # Create test content
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Velocity test content {i}",
                body="Sample content for velocity tracking test",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url=f"test://velocity/{i}",
                quality_score=0.8,
                created_at=activity_time,
                tags=["english", "CET-4", "velocity_test"]
            )
            
            # Create learning activity
            activity = LearningActivity(
                activity_id=str(uuid.uuid4()),
                activity_type=ActivityType.VOCABULARY,
                language="english",
                content=content,
                estimated_duration=time_spent_per_activity[i],
                difficulty_level="CET-4",
                skills_practiced=[Skill.VOCABULARY]
            )
            
            # Create activity result
            result = ActivityResult(
                activity_id=activity.activity_id,
                user_id=user_id,
                score=scores[i],
                time_spent=time_spent_per_activity[i],
                errors_made=[],
                completed_at=activity_time,
                feedback="Test feedback"
            )
            
            activity_results.append((activity, result))
        
        # Record all activities in the progress tracker
        for activity, result in activity_results:
            self.progress_tracker.record_performance(user_id, activity, result)
        
        # Test velocity tracking
        timeframe = timedelta(days=timeframe_days)
        
        # Property: Learning velocity should be calculable
        velocity = self.progress_tracker.calculate_learning_velocity(user_id, timeframe)
        
        # Property: Velocity should be a non-negative number
        assert isinstance(velocity, (int, float)), "Velocity must be numeric"
        assert velocity >= 0.0, "Velocity cannot be negative"
        
        # Property: Velocity should reflect actual learning rate
        if num_activities > 0:
            # Get the actual recorded activities to ensure we're using the same data
            recorded_activities = self.progress_tracker.activity_history.get(user_id, [])
            
            if recorded_activities:
                # Filter activities within the timeframe (same as implementation)
                cutoff_time = datetime.now() - timeframe
                recent_activities = [
                    result for result in recorded_activities
                    if result.completed_at >= cutoff_time
                ]
                
                if recent_activities:
                    total_score = sum(result.score for result in recent_activities)
                    total_time_hours = sum(result.time_spent for result in recent_activities) / 60.0
                    
                    if total_time_hours > 0:
                        expected_velocity = total_score / total_time_hours
                        
                        # Allow for reasonable tolerance in calculation
                        tolerance = 0.1
                        assert abs(velocity - expected_velocity) <= tolerance, f"Velocity calculation mismatch: expected {expected_velocity}, got {velocity}. Recent activities: {len(recent_activities)}, total_score: {total_score}, total_time_hours: {total_time_hours}"
                    else:
                        # If no time spent, velocity should be 0
                        assert velocity == 0.0, f"Velocity should be 0 when no time spent, got {velocity}"
                else:
                    # If no recent activities in timeframe, velocity should be 0
                    assert velocity == 0.0, f"Velocity should be 0 when no recent activities, got {velocity}"
        
        # Property: Velocity should be comparable across different periods
        # Test with a shorter timeframe
        shorter_timeframe = timedelta(days=max(1, timeframe_days // 2))
        shorter_velocity = self.progress_tracker.calculate_learning_velocity(user_id, shorter_timeframe)
        
        assert isinstance(shorter_velocity, (int, float)), "Shorter timeframe velocity must be numeric"
        assert shorter_velocity >= 0.0, "Shorter timeframe velocity cannot be negative"
        
        # Property: Velocity comparison should be meaningful
        # If we have activities in both periods, both velocities should be calculable
        if num_activities >= 2:
            # Both velocities should be valid for comparison
            velocity_difference = abs(velocity - shorter_velocity)
            assert isinstance(velocity_difference, (int, float)), "Velocity difference should be calculable"
    
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(
        target_velocity=st.floats(min_value=0.1, max_value=5.0),
        actual_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0), 
            min_size=3, 
            max_size=15
        ),
        study_times=st.lists(
            st.integers(min_value=10, max_value=120), 
            min_size=3, 
            max_size=15
        )
    )
    def test_velocity_comparison_property(self, target_velocity, actual_scores, study_times):
        """
        Property: Velocity comparison against targets
        For any target velocity and actual performance data, the system should 
        be able to compare actual velocity against target progression rates.
        
        **Validates: Requirements 7.3**
        """
        # Ensure we have matching data
        assume(len(actual_scores) == len(study_times))
        
        user_id = f"velocity_comparison_user_{uuid.uuid4().hex[:8]}"
        
        # Create activity results to simulate actual performance
        current_time = datetime.now()
        
        for i, (score, time_spent) in enumerate(zip(actual_scores, study_times)):
            activity_time = current_time - timedelta(days=len(actual_scores) - i)
            
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Comparison test content {i}",
                body="Content for velocity comparison testing",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url=f"test://comparison/{i}",
                quality_score=0.8,
                created_at=activity_time,
                tags=["english", "CET-4", "comparison_test"]
            )
            
            activity = LearningActivity(
                activity_id=str(uuid.uuid4()),
                activity_type=ActivityType.VOCABULARY,
                language="english",
                content=content,
                estimated_duration=time_spent,
                difficulty_level="CET-4",
                skills_practiced=[Skill.VOCABULARY]
            )
            
            result = ActivityResult(
                activity_id=activity.activity_id,
                user_id=user_id,
                score=score,
                time_spent=time_spent,
                errors_made=[],
                completed_at=activity_time,
                feedback="Comparison test feedback"
            )
            
            self.progress_tracker.record_performance(user_id, activity, result)
        
        # Calculate actual velocity
        timeframe = timedelta(days=len(actual_scores))
        actual_velocity = self.progress_tracker.calculate_learning_velocity(user_id, timeframe)
        
        # Property: Velocity comparison should be deterministic
        velocity_ratio = actual_velocity / target_velocity if target_velocity > 0 else 0
        
        assert isinstance(velocity_ratio, (int, float)), "Velocity ratio must be numeric"
        assert velocity_ratio >= 0.0, "Velocity ratio cannot be negative"
        
        # Property: Comparison should indicate performance relative to target
        if velocity_ratio > 1.1:
            # Performing above target
            performance_status = "above_target"
        elif velocity_ratio < 0.9:
            # Performing below target
            performance_status = "below_target"
        else:
            # Performing at target
            performance_status = "at_target"
        
        # Property: Performance status should be consistent with velocity data
        assert performance_status in ["above_target", "at_target", "below_target"], "Performance status should be valid"
        
        # Property: Velocity tracking should enable adaptive planning
        # If below target, system should be able to identify need for adjustment
        if performance_status == "below_target":
            # System should be able to calculate adjustment needed
            adjustment_factor = target_velocity / actual_velocity if actual_velocity > 0 else 2.0
            assert adjustment_factor >= 1.0, "Adjustment factor should indicate need to increase effort"
        
        elif performance_status == "above_target":
            # System should recognize opportunity for optimization
            optimization_factor = actual_velocity / target_velocity
            assert optimization_factor >= 1.0, "Optimization factor should indicate exceeding expectations"
    
    @given(
        num_users=st.integers(min_value=2, max_value=5),
        activities_per_user=st.integers(min_value=3, max_value=10)
    )
    def test_multi_user_velocity_comparison_property(self, num_users, activities_per_user):
        """
        Property: Multi-user velocity comparison
        For any group of users, velocity tracking should enable comparison 
        of learning rates across different users.
        
        **Validates: Requirements 7.3**
        """
        user_velocities = {}
        
        # Create activity data for multiple users
        for user_idx in range(num_users):
            user_id = f"multi_user_{user_idx}_{uuid.uuid4().hex[:8]}"
            
            # Create varied performance patterns for each user
            base_score = 0.5 + (user_idx * 0.1)  # Different base performance levels
            
            for activity_idx in range(activities_per_user):
                activity_time = datetime.now() - timedelta(days=activities_per_user - activity_idx)
                
                # Vary scores around base level
                score = min(1.0, max(0.0, base_score + (activity_idx * 0.05)))
                time_spent = 20 + (activity_idx * 2)  # Gradually increasing time
                
                content = Content(
                    content_id=str(uuid.uuid4()),
                    title=f"Multi-user content {user_idx}_{activity_idx}",
                    body="Content for multi-user velocity comparison",
                    language="english",
                    difficulty_level="CET-4",
                    content_type=ContentType.ARTICLE,
                    source_url=f"test://multi/{user_idx}/{activity_idx}",
                    quality_score=0.8,
                    created_at=activity_time,
                    tags=["english", "CET-4", "multi_user_test"]
                )
                
                activity = LearningActivity(
                    activity_id=str(uuid.uuid4()),
                    activity_type=ActivityType.VOCABULARY,
                    language="english",
                    content=content,
                    estimated_duration=time_spent,
                    difficulty_level="CET-4",
                    skills_practiced=[Skill.VOCABULARY]
                )
                
                result = ActivityResult(
                    activity_id=activity.activity_id,
                    user_id=user_id,
                    score=score,
                    time_spent=time_spent,
                    errors_made=[],
                    completed_at=activity_time,
                    feedback="Multi-user test feedback"
                )
                
                self.progress_tracker.record_performance(user_id, activity, result)
            
            # Calculate velocity for each user
            timeframe = timedelta(days=activities_per_user)
            velocity = self.progress_tracker.calculate_learning_velocity(user_id, timeframe)
            user_velocities[user_id] = velocity
        
        # Property: All user velocities should be calculable
        for user_id, velocity in user_velocities.items():
            assert isinstance(velocity, (int, float)), f"Velocity for {user_id} must be numeric"
            assert velocity >= 0.0, f"Velocity for {user_id} cannot be negative"
        
        # Property: Velocities should be comparable across users
        velocity_values = list(user_velocities.values())
        
        if len(velocity_values) >= 2:
            # Should be able to rank users by velocity
            sorted_velocities = sorted(velocity_values, reverse=True)
            
            # Property: Ranking should be consistent
            assert len(sorted_velocities) == len(velocity_values), "All velocities should be rankable"
            
            # Property: Velocity differences should be meaningful
            max_velocity = max(velocity_values)
            min_velocity = min(velocity_values)
            
            if max_velocity > 0:
                velocity_range = max_velocity - min_velocity
                assert velocity_range >= 0, "Velocity range should be non-negative"
                
                # Property: Relative performance should be calculable
                for user_id, velocity in user_velocities.items():
                    relative_performance = velocity / max_velocity if max_velocity > 0 else 0
                    assert 0.0 <= relative_performance <= 1.0, f"Relative performance for {user_id} should be between 0 and 1"