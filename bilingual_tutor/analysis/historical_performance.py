"""
Historical Performance Integration - Analyzes performance history and creates adaptive plans.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

from ..models import (
    UserProfile, ActivityResult, LearningActivity, DailyPlan, 
    Skill, ActivityType, ContentType, WeakArea, Goals
)


@dataclass
class PerformancePattern:
    """Represents a pattern in user's learning performance."""
    skill: Skill
    language: str
    trend: str  # "improving", "declining", "stable"
    confidence: float  # 0.0 to 1.0
    recent_scores: List[float]
    time_of_day_preference: Optional[str]
    difficulty_preference: Optional[str]


@dataclass
class LearningInsight:
    """Insights derived from historical performance analysis."""
    user_id: str
    insight_type: str  # "strength", "weakness", "pattern", "recommendation"
    description: str
    confidence: float
    supporting_data: Dict
    generated_at: datetime


class HistoricalPerformanceIntegrator:
    """
    Analyzes performance history and creates adaptive learning plans.
    Implements performance history analysis, adaptive plan generation,
    and learning pattern recognition.
    """
    
    def __init__(self):
        """Initialize the historical performance integrator."""
        self.performance_patterns: Dict[str, List[PerformancePattern]] = {}
        self.learning_insights: Dict[str, List[LearningInsight]] = {}
        self.adaptation_history: Dict[str, List[Dict]] = {}
    
    def analyze_performance_history(self, user_id: str, 
                                  activity_history: List[ActivityResult],
                                  timeframe: timedelta = timedelta(days=30)) -> List[PerformancePattern]:
        """
        Analyze user's performance history to identify patterns and trends.
        
        Args:
            user_id: User identifier
            activity_history: List of completed activities and results
            timeframe: Time period to analyze
            
        Returns:
            List of identified performance patterns
        """
        cutoff_time = datetime.now() - timeframe
        recent_activities = [
            result for result in activity_history
            if result.completed_at >= cutoff_time
        ]
        
        if not recent_activities:
            return []
        
        # Group activities by skill and language
        skill_groups = self._group_activities_by_skill(recent_activities)
        
        patterns = []
        for (skill, language), activities in skill_groups.items():
            if len(activities) >= 3:  # Need minimum data for pattern analysis
                pattern = self._analyze_skill_pattern(skill, language, activities)
                if pattern:
                    patterns.append(pattern)
        
        # Store patterns for future reference
        self.performance_patterns[user_id] = patterns
        
        return patterns
    
    def generate_adaptive_plan(self, user_profile: UserProfile, 
                             performance_patterns: List[PerformancePattern],
                             base_plan: DailyPlan) -> DailyPlan:
        """
        Generate an adaptive learning plan based on historical performance.
        
        Args:
            user_profile: User's profile and preferences
            performance_patterns: Identified performance patterns
            base_plan: Base learning plan to adapt
            
        Returns:
            Adapted learning plan optimized for user's patterns
        """
        # Create a copy of the base plan to modify
        adapted_plan = DailyPlan(
            plan_id=base_plan.plan_id + "_adapted",
            user_id=user_profile.user_id,
            date=base_plan.date,
            activities=base_plan.activities.copy(),
            time_allocation=base_plan.time_allocation,
            learning_objectives=base_plan.learning_objectives.copy(),
            estimated_completion_time=base_plan.estimated_completion_time
        )
        
        # Apply adaptations based on performance patterns
        adapted_plan = self._adapt_for_skill_trends(adapted_plan, performance_patterns)
        adapted_plan = self._adapt_for_time_preferences(adapted_plan, performance_patterns)
        adapted_plan = self._adapt_for_difficulty_preferences(adapted_plan, performance_patterns)
        adapted_plan = self._adapt_for_weak_areas(adapted_plan, user_profile.weak_areas)
        
        # Record adaptation for future analysis
        self._record_adaptation(user_profile.user_id, base_plan, adapted_plan, performance_patterns)
        
        return adapted_plan
    
    def recognize_learning_patterns(self, user_id: str, 
                                  activity_history: List[ActivityResult]) -> List[LearningInsight]:
        """
        Recognize learning patterns from user's activity history.
        
        Args:
            user_id: User identifier
            activity_history: Complete activity history
            
        Returns:
            List of learning insights and patterns
        """
        insights = []
        
        # Analyze time-based patterns
        time_insights = self._analyze_time_patterns(activity_history)
        insights.extend(time_insights)
        
        # Analyze difficulty progression patterns
        difficulty_insights = self._analyze_difficulty_patterns(activity_history)
        insights.extend(difficulty_insights)
        
        # Analyze skill development patterns
        skill_insights = self._analyze_skill_development_patterns(activity_history)
        insights.extend(skill_insights)
        
        # Analyze error patterns
        error_insights = self._analyze_error_patterns(activity_history)
        insights.extend(error_insights)
        
        # Store insights
        self.learning_insights[user_id] = insights
        
        return insights
    
    def predict_performance(self, user_id: str, activity: LearningActivity) -> float:
        """
        Predict likely performance for a given activity based on history.
        
        Args:
            user_id: User identifier
            activity: Activity to predict performance for
            
        Returns:
            Predicted performance score (0.0 to 1.0)
        """
        if user_id not in self.performance_patterns:
            return 0.7  # Default prediction for new users
        
        patterns = self.performance_patterns[user_id]
        
        # Find relevant patterns for this activity
        relevant_patterns = [
            p for p in patterns
            if any(skill in activity.skills_practiced for skill in [p.skill]) and
            p.language == activity.language
        ]
        
        if not relevant_patterns:
            return 0.7  # Default if no relevant patterns
        
        # Calculate weighted prediction based on pattern confidence
        total_weight = 0.0
        weighted_score = 0.0
        
        for pattern in relevant_patterns:
            if pattern.recent_scores:
                avg_score = statistics.mean(pattern.recent_scores)
                weight = pattern.confidence
                weighted_score += avg_score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.7
        
        predicted_score = weighted_score / total_weight
        
        # Adjust based on activity difficulty
        if activity.difficulty_level:
            difficulty_adjustment = self._calculate_difficulty_adjustment(
                activity.difficulty_level, relevant_patterns
            )
            predicted_score *= difficulty_adjustment
        
        return max(0.0, min(1.0, predicted_score))
    
    def get_performance_insights(self, user_id: str) -> List[LearningInsight]:
        """
        Get current performance insights for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of current learning insights
        """
        return self.learning_insights.get(user_id, [])
    
    def _group_activities_by_skill(self, activities: List[ActivityResult]) -> Dict[Tuple[Skill, str], List[ActivityResult]]:
        """Group activities by skill and language for pattern analysis."""
        groups = {}
        
        for activity in activities:
            # For this simplified implementation, we'll infer skill from activity_id
            # In a real system, this would come from the activity metadata
            skill = self._infer_skill_from_activity(activity)
            language = self._infer_language_from_activity(activity)
            
            key = (skill, language)
            if key not in groups:
                groups[key] = []
            groups[key].append(activity)
        
        return groups
    
    def _analyze_skill_pattern(self, skill: Skill, language: str, 
                             activities: List[ActivityResult]) -> Optional[PerformancePattern]:
        """Analyze pattern for a specific skill."""
        if len(activities) < 3:
            return None
        
        # Sort by completion time
        activities.sort(key=lambda x: x.completed_at)
        scores = [activity.score for activity in activities]
        
        # Determine trend
        trend = self._calculate_trend(scores)
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_pattern_confidence(scores)
        
        # Analyze time preferences (simplified)
        time_preference = self._analyze_time_preference(activities)
        
        # Analyze difficulty preferences
        difficulty_preference = self._analyze_difficulty_preference(activities)
        
        return PerformancePattern(
            skill=skill,
            language=language,
            trend=trend,
            confidence=confidence,
            recent_scores=scores[-5:],  # Last 5 scores
            time_of_day_preference=time_preference,
            difficulty_preference=difficulty_preference
        )
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate performance trend from scores."""
        if len(scores) < 6:  # 需要至少6个分数才能进行有意义的趋势分析
            return "stable"
        
        # Simple linear trend analysis
        recent_avg = statistics.mean(scores[-3:])
        earlier_avg = statistics.mean(scores[:-3])
        
        if recent_avg > earlier_avg + 0.1:
            return "improving"
        elif recent_avg < earlier_avg - 0.1:
            return "declining"
        else:
            return "stable"
    
    def _calculate_pattern_confidence(self, scores: List[float]) -> float:
        """Calculate confidence in the pattern based on data consistency."""
        if len(scores) < 3:
            return 0.5
        
        # Use coefficient of variation (lower = more consistent = higher confidence)
        if statistics.mean(scores) == 0:
            return 0.5
        
        cv = statistics.stdev(scores) / statistics.mean(scores)
        confidence = max(0.1, 1.0 - cv)
        
        return min(1.0, confidence)
    
    def _analyze_time_preference(self, activities: List[ActivityResult]) -> Optional[str]:
        """Analyze time-of-day preferences from activity history."""
        # Simplified implementation - would need more sophisticated analysis
        return None
    
    def _analyze_difficulty_preference(self, activities: List[ActivityResult]) -> Optional[str]:
        """Analyze difficulty level preferences from activity history."""
        # Simplified implementation
        return None
    
    def _adapt_for_skill_trends(self, plan: DailyPlan, 
                               patterns: List[PerformancePattern]) -> DailyPlan:
        """Adapt plan based on skill performance trends."""
        # Increase focus on declining skills
        declining_skills = [p.skill for p in patterns if p.trend == "declining"]
        
        if declining_skills:
            # Add additional practice for declining skills
            plan.learning_objectives.append(f"加强练习表现下降的技能: {', '.join([s.value for s in declining_skills])}")
        
        return plan
    
    def _adapt_for_time_preferences(self, plan: DailyPlan, 
                                   patterns: List[PerformancePattern]) -> DailyPlan:
        """Adapt plan based on time-of-day preferences."""
        # Simplified implementation - would adjust activity scheduling
        return plan
    
    def _adapt_for_difficulty_preferences(self, plan: DailyPlan, 
                                        patterns: List[PerformancePattern]) -> DailyPlan:
        """Adapt plan based on difficulty preferences."""
        # Simplified implementation - would adjust content difficulty
        return plan
    
    def _adapt_for_weak_areas(self, plan: DailyPlan, weak_areas: List[WeakArea]) -> DailyPlan:
        """Adapt plan to address identified weak areas."""
        if weak_areas:
            # Add objectives to address weak areas
            for weakness in weak_areas[:2]:  # Focus on top 2 weaknesses
                plan.learning_objectives.append(f"重点改进: {weakness.skill.value} ({weakness.language})")
        
        return plan
    
    def _record_adaptation(self, user_id: str, base_plan: DailyPlan, 
                          adapted_plan: DailyPlan, patterns: List[PerformancePattern]) -> None:
        """Record adaptation for future analysis."""
        if user_id not in self.adaptation_history:
            self.adaptation_history[user_id] = []
        
        adaptation_record = {
            "timestamp": datetime.now(),
            "base_plan_id": base_plan.plan_id,
            "adapted_plan_id": adapted_plan.plan_id,
            "patterns_used": len(patterns),
            "adaptations_made": len(adapted_plan.learning_objectives) - len(base_plan.learning_objectives)
        }
        
        self.adaptation_history[user_id].append(adaptation_record)
    
    def _analyze_time_patterns(self, activities: List[ActivityResult]) -> List[LearningInsight]:
        """Analyze time-based learning patterns."""
        insights = []
        
        if len(activities) < 10:
            return insights
        
        # Analyze performance by time of day (simplified)
        # In a real system, this would be more sophisticated
        
        return insights
    
    def _analyze_difficulty_patterns(self, activities: List[ActivityResult]) -> List[LearningInsight]:
        """Analyze difficulty progression patterns."""
        insights = []
        
        # Simplified analysis - would be more complex in practice
        
        return insights
    
    def _analyze_skill_development_patterns(self, activities: List[ActivityResult]) -> List[LearningInsight]:
        """Analyze skill development patterns."""
        insights = []
        
        # Group by inferred skills and analyze progression
        skill_groups = {}
        for activity in activities:
            skill = self._infer_skill_from_activity(activity)
            if skill not in skill_groups:
                skill_groups[skill] = []
            skill_groups[skill].append(activity)
        
        for skill, skill_activities in skill_groups.items():
            if len(skill_activities) >= 5:
                scores = [a.score for a in sorted(skill_activities, key=lambda x: x.completed_at)]
                trend = self._calculate_trend(scores)
                
                if trend == "improving":
                    insights.append(LearningInsight(
                        user_id="",  # Will be set by caller
                        insight_type="strength",
                        description=f"{skill.value} 技能持续改进",
                        confidence=0.8,
                        supporting_data={"scores": scores, "trend": trend},
                        generated_at=datetime.now()
                    ))
                elif trend == "declining":
                    insights.append(LearningInsight(
                        user_id="",  # Will be set by caller
                        insight_type="weakness",
                        description=f"{skill.value} 技能需要更多关注",
                        confidence=0.7,
                        supporting_data={"scores": scores, "trend": trend},
                        generated_at=datetime.now()
                    ))
        
        return insights
    
    def _analyze_error_patterns(self, activities: List[ActivityResult]) -> List[LearningInsight]:
        """Analyze error patterns in user performance."""
        insights = []
        
        # Collect all errors
        all_errors = []
        for activity in activities:
            all_errors.extend(activity.errors_made)
        
        if len(all_errors) >= 5:
            # Find common error patterns
            error_counts = {}
            for error in all_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
            
            # Identify frequent errors
            frequent_errors = [error for error, count in error_counts.items() if count >= 3]
            
            if frequent_errors:
                insights.append(LearningInsight(
                    user_id="",  # Will be set by caller
                    insight_type="pattern",
                    description=f"常见错误模式: {', '.join(frequent_errors[:3])}",
                    confidence=0.6,
                    supporting_data={"error_counts": error_counts},
                    generated_at=datetime.now()
                ))
        
        return insights
    
    def _calculate_difficulty_adjustment(self, difficulty_level: str, 
                                       patterns: List[PerformancePattern]) -> float:
        """Calculate adjustment factor based on difficulty and patterns."""
        # Simplified implementation
        base_adjustment = 1.0
        
        # Adjust based on user's historical performance with similar difficulty
        for pattern in patterns:
            if pattern.difficulty_preference:
                if difficulty_level == pattern.difficulty_preference:
                    base_adjustment *= 1.1  # Boost for preferred difficulty
                else:
                    base_adjustment *= 0.9  # Slight penalty for non-preferred
        
        return base_adjustment
    
    def _infer_skill_from_activity(self, activity: ActivityResult) -> Skill:
        """Infer skill from activity result (simplified implementation)."""
        # In a real system, this would come from activity metadata
        # For now, use a simple heuristic based on activity_id or errors
        
        if "vocabulary" in activity.activity_id.lower():
            return Skill.VOCABULARY
        elif "grammar" in activity.activity_id.lower():
            return Skill.GRAMMAR
        elif "reading" in activity.activity_id.lower():
            return Skill.READING
        elif "listening" in activity.activity_id.lower():
            return Skill.LISTENING
        elif "speaking" in activity.activity_id.lower():
            return Skill.SPEAKING
        elif "writing" in activity.activity_id.lower():
            return Skill.WRITING
        else:
            return Skill.VOCABULARY  # Default
    
    def _infer_language_from_activity(self, activity: ActivityResult) -> str:
        """Infer language from activity result (simplified implementation)."""
        # In a real system, this would come from activity metadata
        # For now, use a simple heuristic
        
        if "english" in activity.activity_id.lower():
            return "english"
        elif "japanese" in activity.activity_id.lower():
            return "japanese"
        else:
            return "english"  # Default
    def predict_performance(self, user_id: str, activity: LearningActivity) -> float:
        """
        Predict likely performance for a given activity based on user's history.
        
        Args:
            user_id: User identifier
            activity: Activity to predict performance for
            
        Returns:
            Predicted performance score (0.0 to 1.0)
        """
        # Get user's performance patterns
        patterns = self.performance_patterns.get(user_id, [])
        
        if not patterns:
            # No history available, return moderate prediction
            return 0.5
        
        # Find relevant patterns for this activity
        relevant_patterns = []
        for pattern in patterns:
            # Match by language
            if hasattr(activity, 'language') and pattern.language == activity.language:
                relevant_patterns.append(pattern)
            # Match by inferred skill
            elif hasattr(activity, 'skills_practiced'):
                for skill in activity.skills_practiced:
                    if pattern.skill == skill:
                        relevant_patterns.append(pattern)
                        break
        
        if not relevant_patterns:
            # No relevant patterns, return moderate prediction
            return 0.5
        
        # Calculate weighted prediction based on relevant patterns
        total_weight = 0.0
        weighted_score = 0.0
        
        for pattern in relevant_patterns:
            if pattern.recent_scores:
                # Use recent average as base prediction
                recent_avg = statistics.mean(pattern.recent_scores)
                
                # Adjust based on trend
                if pattern.trend == "improving":
                    predicted_score = min(1.0, recent_avg + 0.1)
                elif pattern.trend == "declining":
                    predicted_score = max(0.0, recent_avg - 0.1)
                else:
                    predicted_score = recent_avg
                
                # Weight by confidence
                weight = pattern.confidence
                weighted_score += predicted_score * weight
                total_weight += weight
        
        if total_weight > 0:
            final_prediction = weighted_score / total_weight
            # Ensure reasonable bounds (not too extreme)
            return max(0.2, min(0.9, final_prediction))
        else:
            return 0.5
    
    def get_performance_insights(self, user_id: str) -> List[LearningInsight]:
        """
        Get performance insights for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of learning insights and recommendations
        """
        return self.learning_insights.get(user_id, [])