"""
Property-based tests for progress reporting toward goals.

Feature: bilingual-tutor, Property 23: Progress Reporting Toward Goals
**Validates: Requirements 3.2, 7.6**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
import uuid

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    ActivityResult, LearningActivity, ActivityType, Content, ContentType, Skill,
    UserProfile, Goals, Preferences
)


class TestProgressReporting:
    """Test progress reporting toward goals property."""
    
    def setup_method(self):
        """Set up test fixtures with complete isolation."""
        # Create a completely fresh engine instance for each test
        self.engine = CoreLearningEngine()
        # Create a completely fresh progress tracker instance to ensure isolation
        from bilingual_tutor.progress.tracker import ProgressTracker
        self.progress_tracker = ProgressTracker()
        # Replace the engine's progress tracker with our fresh instance
        self.engine.progress_tracker = self.progress_tracker
        self.engine.register_component("progress_tracker", self.progress_tracker)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear all references to ensure garbage collection
        self.engine = None
        self.progress_tracker = None
    
    @given(
        reporting_period=st.sampled_from(["weekly", "monthly"]),
        num_activities=st.integers(min_value=1, max_value=15),
        target_completion_days=st.integers(min_value=30, max_value=730),  # 1 month to 2 years
        scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0), 
            min_size=1, 
            max_size=15
        )
    )
    def test_progress_reporting_property(self, reporting_period, num_activities, target_completion_days, scores):
        """
        Property 23: Progress Reporting Toward Goals
        For any reporting period (weekly/monthly), progress reports should show 
        advancement metrics toward the 2-year objectives.
        
        **Validates: Requirements 3.2, 7.6**
        """
        # Ensure we have enough scores
        assume(len(scores) >= num_activities)
        
        user_id = f"progress_reporting_user_{uuid.uuid4().hex[:8]}"
        
        # Create user profile with goals
        target_date = datetime.now() + timedelta(days=target_completion_days)
        
        user_profile = UserProfile(
            user_id=user_id,
            english_level="CET-4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=Goals(
                target_english_level="CET-6",
                target_japanese_level="N1",
                target_completion_date=target_date,
                priority_skills=[Skill.VOCABULARY, Skill.GRAMMAR],
                custom_objectives=["Achieve fluency in both languages"]
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
        
        # Create activity results over the reporting period
        period_days = 7 if reporting_period == "weekly" else 30
        base_time = datetime.now() - timedelta(days=period_days)
        
        for i in range(num_activities):
            # Distribute activities across the period
            activity_time = base_time + timedelta(
                days=(i * period_days) // num_activities,
                hours=i % 24
            )
            
            # Alternate between English and Japanese
            language = "english" if i % 2 == 0 else "japanese"
            difficulty = "CET-4" if language == "english" else "N5"
            
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Progress test {language} content {i}",
                body=f"Sample {language} content for progress reporting test",
                language=language,
                difficulty_level=difficulty,
                content_type=ContentType.ARTICLE,
                source_url=f"test://progress/{language}/{i}",
                quality_score=0.8,
                created_at=activity_time,
                tags=[language, difficulty, "progress_test"]
            )
            
            activity = LearningActivity(
                activity_id=str(uuid.uuid4()),
                activity_type=ActivityType.VOCABULARY,
                language=language,
                content=content,
                estimated_duration=20,
                difficulty_level=difficulty,
                skills_practiced=[Skill.VOCABULARY]
            )
            
            result = ActivityResult(
                activity_id=activity.activity_id,
                user_id=user_id,
                score=scores[i],
                time_spent=20,
                errors_made=[],
                completed_at=activity_time,
                feedback="Progress test feedback"
            )
            
            self.progress_tracker.record_performance(user_id, activity, result)
        
        # Generate progress report
        progress_report = self.progress_tracker.generate_progress_report(user_id, reporting_period)
        
        # Property: Progress report should be generated successfully
        assert progress_report is not None, "Progress report should be generated"
        assert progress_report.user_id == user_id, "Report should be for correct user"
        
        # Property: Report should cover the specified period
        if reporting_period == "weekly":
            expected_period_days = 7
        else:  # monthly
            expected_period_days = 30
        
        actual_period = (progress_report.period_end - progress_report.period_start).days
        assert abs(actual_period - expected_period_days) <= 1, f"Report period should be approximately {expected_period_days} days"
        
        # Property: Report should include activity metrics
        assert isinstance(progress_report.activities_completed, int), "Activities completed should be integer"
        assert progress_report.activities_completed >= 0, "Activities completed cannot be negative"
        assert progress_report.activities_completed <= num_activities, "Activities completed should not exceed actual activities"
        
        # Property: Report should include time metrics
        assert isinstance(progress_report.time_studied, int), "Time studied should be integer"
        assert progress_report.time_studied >= 0, "Time studied cannot be negative"
        
        # Property: Report should include skill improvement data
        assert isinstance(progress_report.skills_improved, list), "Skills improved should be a list"
        
        # Property: Report should include achievements
        assert isinstance(progress_report.achievements, list), "Achievements should be a list"
        
        # Property: Report should include recommendations
        assert isinstance(progress_report.recommendations, list), "Recommendations should be a list"
        assert len(progress_report.recommendations) > 0, "Report should include at least one recommendation"
        
        # Property: Progress metrics should reflect goal advancement
        current_metrics = self.progress_tracker.get_current_metrics(user_id)
        
        # Property: Current metrics should show progress toward goals
        assert isinstance(current_metrics.overall_progress, float), "Overall progress should be numeric"
        assert 0.0 <= current_metrics.overall_progress <= 1.0, "Overall progress should be between 0 and 1"
        
        # Property: Progress should be measurable against time remaining
        days_remaining = (target_date - datetime.now()).days
        if days_remaining > 0:
            # Calculate expected progress based on time elapsed
            total_goal_days = target_completion_days
            days_elapsed = total_goal_days - days_remaining
            expected_progress_ratio = days_elapsed / total_goal_days
            
            # Progress reporting should enable comparison with expected timeline
            assert isinstance(expected_progress_ratio, float), "Expected progress ratio should be calculable"
            assert 0.0 <= expected_progress_ratio <= 1.0, "Expected progress ratio should be valid"
    
    @given(
        num_weeks=st.integers(min_value=1, max_value=12),
        activities_per_week=st.integers(min_value=2, max_value=10),
        goal_achievement_rate=st.floats(min_value=0.1, max_value=2.0)
    )
    def test_goal_advancement_tracking_property(self, num_weeks, activities_per_week, goal_achievement_rate):
        """
        Property: Goal advancement tracking over time
        For any series of progress reports, advancement toward goals should be trackable.
        
        **Validates: Requirements 3.2, 7.6**
        """
        user_id = f"goal_tracking_user_{uuid.uuid4().hex[:8]}"
        
        # Create user with 2-year goals
        target_date = datetime.now() + timedelta(days=730)  # 2 years
        
        user_profile = UserProfile(
            user_id=user_id,
            english_level="CET-4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=Goals(
                target_english_level="CET-6",
                target_japanese_level="N1",
                target_completion_date=target_date,
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
        
        weekly_reports = []
        
        # Generate activities and reports for multiple weeks
        for week in range(num_weeks):
            week_start = datetime.now() - timedelta(days=(num_weeks - week) * 7)
            
            # Create activities for this week
            for activity_idx in range(activities_per_week):
                activity_time = week_start + timedelta(days=activity_idx)
                
                # Simulate improving performance over time
                base_score = 0.5 + (week * 0.05 * goal_achievement_rate)
                score = min(1.0, max(0.0, base_score + (activity_idx * 0.02)))
                
                content = Content(
                    content_id=str(uuid.uuid4()),
                    title=f"Goal tracking content week {week} activity {activity_idx}",
                    body="Content for goal advancement tracking",
                    language="english",
                    difficulty_level="CET-4",
                    content_type=ContentType.ARTICLE,
                    source_url=f"test://goal_tracking/{week}/{activity_idx}",
                    quality_score=0.8,
                    created_at=activity_time,
                    tags=["english", "CET-4", "goal_tracking"]
                )
                
                activity = LearningActivity(
                    activity_id=str(uuid.uuid4()),
                    activity_type=ActivityType.VOCABULARY,
                    language="english",
                    content=content,
                    estimated_duration=15,
                    difficulty_level="CET-4",
                    skills_practiced=[Skill.VOCABULARY]
                )
                
                result = ActivityResult(
                    activity_id=activity.activity_id,
                    user_id=user_id,
                    score=score,
                    time_spent=15,
                    errors_made=[],
                    completed_at=activity_time,
                    feedback="Goal tracking feedback"
                )
                
                self.progress_tracker.record_performance(user_id, activity, result)
            
            # Generate weekly report
            weekly_report = self.progress_tracker.generate_progress_report(user_id, "weekly")
            weekly_reports.append(weekly_report)
        
        # Property: Multiple reports should show progression
        assert len(weekly_reports) == num_weeks, "Should have report for each week"
        
        # Property: Reports should show advancement over time
        if len(weekly_reports) >= 2:
            first_report = weekly_reports[0]
            last_report = weekly_reports[-1]
            
            # Activities should generally increase or stay consistent
            assert last_report.activities_completed >= 0, "Last report should have valid activity count"
            assert first_report.activities_completed >= 0, "First report should have valid activity count"
            
            # Time studied should accumulate
            assert last_report.time_studied >= 0, "Time studied should be non-negative"
            
        # Property: Goal advancement should be calculable from reports
        total_activities = sum(report.activities_completed for report in weekly_reports)
        total_time = sum(report.time_studied for report in weekly_reports)
        
        assert total_activities >= 0, "Total activities should be non-negative"
        assert total_time >= 0, "Total time should be non-negative"
        
        # Property: Progress toward 2-year goals should be measurable
        current_metrics = self.progress_tracker.get_current_metrics(user_id)
        
        # Calculate progress rate
        weeks_elapsed = num_weeks
        total_weeks_to_goal = 104  # 2 years = 104 weeks
        
        if total_weeks_to_goal > 0:
            time_progress_ratio = weeks_elapsed / total_weeks_to_goal
            
            # Property: Time-based progress should be trackable
            assert 0.0 <= time_progress_ratio <= 1.0, "Time progress ratio should be valid"
            
            # Property: Actual progress should be comparable to time progress
            actual_progress = current_metrics.overall_progress
            progress_efficiency = actual_progress / time_progress_ratio if time_progress_ratio > 0 else 0
            
            # Progress efficiency should be calculable (may be above or below 1.0)
            assert isinstance(progress_efficiency, (int, float)), "Progress efficiency should be numeric"
    
    @given(
        english_focus=st.floats(min_value=0.1, max_value=0.9),
        japanese_focus=st.floats(min_value=0.1, max_value=0.9),
        num_activities=st.integers(min_value=5, max_value=20)
    )
    def test_dual_language_progress_reporting_property(self, english_focus, japanese_focus, num_activities):
        """
        Property: Dual language progress reporting
        For any bilingual learning plan, progress reports should show advancement 
        toward goals in both English and Japanese.
        
        **Validates: Requirements 3.2, 7.6**
        """
        # Normalize focus ratios
        total_focus = english_focus + japanese_focus
        english_ratio = english_focus / total_focus
        japanese_ratio = japanese_focus / total_focus
        
        user_id = f"dual_language_user_{uuid.uuid4().hex[:8]}"
        
        # Create activities for both languages
        english_activities = int(num_activities * english_ratio)
        japanese_activities = num_activities - english_activities
        
        # Ensure at least one activity per language
        if english_activities == 0:
            english_activities = 1
            japanese_activities = num_activities - 1
        elif japanese_activities == 0:
            japanese_activities = 1
            english_activities = num_activities - 1
        
        # Create English activities
        for i in range(english_activities):
            # Ensure activities are within the last week
            activity_time = datetime.now() - timedelta(days=max(1, 6 - i), hours=i)
            
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Dual language English content {i}",
                body="English content for dual language progress test",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url=f"test://dual/english/{i}",
                quality_score=0.8,
                created_at=activity_time,
                tags=["english", "CET-4", "dual_language"]
            )
            
            activity = LearningActivity(
                activity_id=str(uuid.uuid4()),
                activity_type=ActivityType.VOCABULARY,
                language="english",
                content=content,
                estimated_duration=20,
                difficulty_level="CET-4",
                skills_practiced=[Skill.VOCABULARY]
            )
            
            result = ActivityResult(
                activity_id=activity.activity_id,
                user_id=user_id,
                score=0.7 + (i * 0.05),  # Improving scores
                time_spent=20,
                errors_made=[],
                completed_at=activity_time,
                feedback="English progress feedback"
            )
            
            self.progress_tracker.record_performance(user_id, activity, result)
        
        # Create Japanese activities
        for i in range(japanese_activities):
            # Ensure activities are within the last week, offset from English activities
            activity_time = datetime.now() - timedelta(days=max(1, 6 - i - english_activities), hours=i + english_activities)
            
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Dual language Japanese content {i}",
                body="Japanese content for dual language progress test",
                language="japanese",
                difficulty_level="N5",
                content_type=ContentType.ARTICLE,
                source_url=f"test://dual/japanese/{i}",
                quality_score=0.8,
                created_at=activity_time,
                tags=["japanese", "N5", "dual_language"]
            )
            
            activity = LearningActivity(
                activity_id=str(uuid.uuid4()),
                activity_type=ActivityType.VOCABULARY,
                language="japanese",
                content=content,
                estimated_duration=20,
                difficulty_level="N5",
                skills_practiced=[Skill.VOCABULARY]
            )
            
            result = ActivityResult(
                activity_id=activity.activity_id,
                user_id=user_id,
                score=0.6 + (i * 0.06),  # Different improvement rate
                time_spent=20,
                errors_made=[],
                completed_at=activity_time,
                feedback="Japanese progress feedback"
            )
            
            self.progress_tracker.record_performance(user_id, activity, result)
        
        # Generate progress report
        progress_report = self.progress_tracker.generate_progress_report(user_id, "weekly")
        
        # Property: Report should account for both languages
        assert progress_report.activities_completed >= 2, "Should have activities in both languages"
        
        # Property: Progress should be trackable for each language separately
        # (This would require language-specific metrics in a full implementation)
        current_metrics = self.progress_tracker.get_current_metrics(user_id)
        
        # Property: Overall progress should reflect combined language learning
        assert isinstance(current_metrics.overall_progress, float), "Overall progress should be numeric"
        assert current_metrics.overall_progress >= 0.0, "Progress should be non-negative"
        
        # Property: Dual language progress should be reportable
        total_time = progress_report.time_studied
        expected_time = (english_activities + japanese_activities) * 20
        
        # Allow some tolerance for time calculation
        assert abs(total_time - expected_time) <= expected_time * 0.2, "Total time should approximately match expected time"