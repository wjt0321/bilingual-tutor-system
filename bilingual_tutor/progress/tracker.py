"""
Progress Tracker - Monitors learning advancement and performance metrics.
"""

from typing import List, Dict
from datetime import datetime, timedelta
from ..models import (
    LearningActivity, ActivityResult, ProgressReport, ProgressMetrics,
    Skill, ProgressTrackerInterface, ActivityType
)


class ProgressTracker(ProgressTrackerInterface):
    """
    Monitors learning advancement and performance metrics across all skills.
    """
    
    def __init__(self):
        """Initialize the progress tracker with metric storage."""
        self.user_metrics: Dict[str, ProgressMetrics] = {}
        self.activity_history: Dict[str, List[ActivityResult]] = {}
        self.skill_progress: Dict[str, Dict[Skill, float]] = {}
    
    def record_performance(self, user_id: str, activity: LearningActivity, result: ActivityResult) -> None:
        """
        Record user performance for a completed activity.
        
        Args:
            user_id: Unique identifier for the user
            activity: Learning activity that was completed
            result: Results and performance metrics from the activity
        """
        # Initialize user data if not exists
        if user_id not in self.activity_history:
            self.activity_history[user_id] = []
        if user_id not in self.skill_progress:
            self.skill_progress[user_id] = {}
        if user_id not in self.user_metrics:
            self.user_metrics[user_id] = ProgressMetrics(
                user_id=user_id,
                language=activity.language,
                vocabulary_mastered=0,
                grammar_points_learned=0,
                reading_comprehension_score=0.0,
                listening_comprehension_score=0.0,
                speaking_fluency_score=0.0,
                writing_proficiency_score=0.0,
                overall_progress=0.0,
                last_updated=datetime.now()
            )
        
        # Record the activity result
        self.activity_history[user_id].append(result)
        
        # Update skill progress based on activity
        for skill in activity.skills_practiced:
            if skill not in self.skill_progress[user_id]:
                self.skill_progress[user_id][skill] = 0.0
            
            # Update skill progress based on performance (weighted average)
            current_progress = self.skill_progress[user_id][skill]
            new_progress = (current_progress * 0.8) + (result.score * 0.2)
            self.skill_progress[user_id][skill] = min(1.0, new_progress)
        
        # Update metrics based on activity type and performance
        metrics = self.user_metrics[user_id]
        if activity.activity_type == ActivityType.VOCABULARY:
            if result.score >= 0.8:  # Consider mastered if score >= 80%
                metrics.vocabulary_mastered += 1
        elif activity.activity_type == ActivityType.GRAMMAR:
            if result.score >= 0.8:
                metrics.grammar_points_learned += 1
        elif activity.activity_type == ActivityType.READING:
            metrics.reading_comprehension_score = (metrics.reading_comprehension_score * 0.7) + (result.score * 0.3)
        elif activity.activity_type == ActivityType.LISTENING:
            metrics.listening_comprehension_score = (metrics.listening_comprehension_score * 0.7) + (result.score * 0.3)
        elif activity.activity_type == ActivityType.SPEAKING:
            metrics.speaking_fluency_score = (metrics.speaking_fluency_score * 0.7) + (result.score * 0.3)
        elif activity.activity_type == ActivityType.WRITING:
            metrics.writing_proficiency_score = (metrics.writing_proficiency_score * 0.7) + (result.score * 0.3)
        
        # Update overall progress as average of all skills
        all_scores = [
            metrics.reading_comprehension_score,
            metrics.listening_comprehension_score,
            metrics.speaking_fluency_score,
            metrics.writing_proficiency_score
        ]
        metrics.overall_progress = sum(score for score in all_scores if score > 0) / len([s for s in all_scores if s > 0]) if any(all_scores) else 0.0
        metrics.last_updated = datetime.now()
    
    def calculate_learning_velocity(self, user_id: str, timeframe: timedelta) -> float:
        """
        Calculate learning velocity over a specified timeframe.
        
        Args:
            user_id: Unique identifier for the user
            timeframe: Time period to calculate velocity for
            
        Returns:
            Learning velocity as progress per unit time
        """
        if user_id not in self.activity_history:
            return 0.0
        
        cutoff_time = datetime.now() - timeframe
        recent_activities = [
            result for result in self.activity_history[user_id]
            if result.completed_at >= cutoff_time
        ]
        
        if not recent_activities:
            return 0.0
        
        # Calculate velocity as average score improvement over time
        total_score = sum(result.score for result in recent_activities)
        total_time_hours = sum(result.time_spent for result in recent_activities) / 60.0
        
        if total_time_hours == 0:
            return 0.0
        
        # Velocity = progress points per hour
        return total_score / total_time_hours
    
    def generate_progress_report(self, user_id: str, period: str) -> ProgressReport:
        """
        Generate a comprehensive progress report for a period.
        
        Args:
            user_id: Unique identifier for the user
            period: Period for the report (weekly, monthly, etc.)
            
        Returns:
            Detailed progress report
        """
        if user_id not in self.activity_history:
            # Return empty report for new users
            return ProgressReport(
                user_id=user_id,
                period_start=datetime.now() - timedelta(days=7),
                period_end=datetime.now(),
                activities_completed=0,
                time_studied=0,
                skills_improved=[],
                weaknesses_addressed=[],
                achievements=[],
                recommendations=["开始学习以获得进度报告"]
            )
        
        # Determine timeframe based on period
        if period == "weekly":
            timeframe = timedelta(days=7)
        elif period == "monthly":
            timeframe = timedelta(days=30)
        else:
            timeframe = timedelta(days=7)  # Default to weekly
        
        period_start = datetime.now() - timeframe
        period_end = datetime.now()
        
        # Filter activities for the period
        period_activities = [
            result for result in self.activity_history[user_id]
            if period_start <= result.completed_at <= period_end
        ]
        
        # Calculate metrics
        activities_completed = len(period_activities)
        time_studied = sum(result.time_spent for result in period_activities)
        
        # Identify improved skills (those with recent high scores)
        skills_improved = []
        if user_id in self.skill_progress:
            for skill, progress in self.skill_progress[user_id].items():
                if progress >= 0.7:  # Consider improved if progress >= 70%
                    skills_improved.append(skill)
        
        # Generate achievements based on performance
        achievements = []
        if activities_completed >= 7:
            achievements.append("完成了一周的学习目标")
        if time_studied >= 300:  # 5 hours
            achievements.append("学习时间超过5小时")
        
        avg_score = sum(result.score for result in period_activities) / len(period_activities) if period_activities else 0
        if avg_score >= 0.8:
            achievements.append("平均成绩优秀 (80%+)")
        
        # Generate recommendations
        recommendations = []
        if activities_completed < 5:
            recommendations.append("建议增加学习频率，每周至少5次")
        if avg_score < 0.6:
            recommendations.append("建议复习基础知识，提高理解程度")
        if not skills_improved:
            recommendations.append("尝试不同类型的练习来提高技能")
        
        return ProgressReport(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            activities_completed=activities_completed,
            time_studied=time_studied,
            skills_improved=skills_improved,
            weaknesses_addressed=[],  # Will be populated by weakness analyzer
            achievements=achievements,
            recommendations=recommendations
        )
    
    def track_skill_improvement(self, user_id: str, skill: Skill) -> float:
        """
        Track improvement in a specific skill over time.
        
        Args:
            user_id: Unique identifier for the user
            skill: Skill to track improvement for
            
        Returns:
            Improvement rate for the skill
        """
        if user_id not in self.skill_progress or skill not in self.skill_progress[user_id]:
            return 0.0
        
        return self.skill_progress[user_id][skill]
    
    def get_current_metrics(self, user_id: str) -> ProgressMetrics:
        """
        Get current progress metrics for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Current progress metrics
        """
        if user_id not in self.user_metrics:
            # Return default metrics for new users
            return ProgressMetrics(
                user_id=user_id,
                language="english",  # Default language
                vocabulary_mastered=0,
                grammar_points_learned=0,
                reading_comprehension_score=0.0,
                listening_comprehension_score=0.0,
                speaking_fluency_score=0.0,
                writing_proficiency_score=0.0,
                overall_progress=0.0,
                last_updated=datetime.now()
            )
        
        return self.user_metrics[user_id]
    
    def calculate_achievement_rate(self, user_id: str, timeframe: timedelta) -> float:
        """
        Calculate achievement rate over a timeframe.
        
        Args:
            user_id: Unique identifier for the user
            timeframe: Time period to calculate for
            
        Returns:
            Achievement rate as percentage
        """
        if user_id not in self.activity_history:
            return 0.0
        
        cutoff_time = datetime.now() - timeframe
        recent_activities = [
            result for result in self.activity_history[user_id]
            if result.completed_at >= cutoff_time
        ]
        
        if not recent_activities:
            return 0.0
        
        # Calculate achievement rate as percentage of activities with score >= 0.7
        successful_activities = sum(1 for result in recent_activities if result.score >= 0.7)
        return (successful_activities / len(recent_activities)) * 100.0