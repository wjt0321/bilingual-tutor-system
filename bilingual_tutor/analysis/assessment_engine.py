"""
Assessment Engine - Evaluates user performance and determines comprehension levels.
"""

from typing import List, Dict, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from ..models import Skill, ActivityResult


class ComprehensionLevel(Enum):
    """Comprehension levels for assessment."""
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class DifficultyLevel(Enum):
    """Difficulty levels for content calibration."""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


class AssessmentEngine:
    """
    Evaluates user performance and determines comprehension levels
    for adaptive difficulty adjustment and feedback generation.
    """
    
    def __init__(self):
        """Initialize the assessment engine."""
        # Performance thresholds for different levels
        self.comprehension_thresholds = {
            ComprehensionLevel.BEGINNER: (0.0, 0.4),
            ComprehensionLevel.ELEMENTARY: (0.4, 0.6),
            ComprehensionLevel.INTERMEDIATE: (0.6, 0.75),
            ComprehensionLevel.ADVANCED: (0.75, 0.9),
            ComprehensionLevel.EXPERT: (0.9, 1.0)
        }
        
        # Difficulty adjustment parameters
        self.difficulty_adjustment_threshold = 0.1
        self.performance_window_size = 10  # Number of recent activities to consider
        
        # Assessment history
        self.user_assessments: Dict[str, List[Tuple[datetime, float, Skill]]] = {}
        self.comprehension_levels: Dict[str, Dict[Skill, ComprehensionLevel]] = {}
        self.difficulty_calibrations: Dict[str, Dict[Skill, DifficultyLevel]] = {}
    
    def evaluate_performance(self, user_id: str, activity_result: ActivityResult, expected_performance: float = None) -> Dict[str, Any]:
        """
        Evaluate user performance for an activity.
        
        Args:
            user_id: User identifier
            activity_result: Result of the completed activity
            expected_performance: Expected performance level (optional)
            
        Returns:
            Performance evaluation with score, analysis, and recommendations
        """
        score = activity_result.score
        
        # Record assessment
        if user_id not in self.user_assessments:
            self.user_assessments[user_id] = []
        
        # Infer skill from activity (simplified - would be more sophisticated in real implementation)
        primary_skill = self._infer_primary_skill(activity_result)
        
        self.user_assessments[user_id].append((
            activity_result.completed_at,
            score,
            primary_skill
        ))
        
        # Analyze performance
        analysis = self._analyze_performance(user_id, activity_result, expected_performance)
        
        # Generate feedback
        feedback = self._generate_performance_feedback(score, analysis, activity_result.errors_made)
        
        # Update comprehension level
        new_comprehension = self._update_comprehension_level(user_id, primary_skill, score)
        
        return {
            'score': score,
            'skill': primary_skill.value,
            'comprehension_level': new_comprehension.value,
            'analysis': analysis,
            'feedback': feedback,
            'improvement_areas': self._identify_improvement_areas(activity_result),
            'next_difficulty': self._recommend_next_difficulty(user_id, primary_skill),
            'confidence_level': self._calculate_confidence_level(user_id, primary_skill)
        }
    
    def assess_comprehension(self, user_id: str, skill: Skill, recent_activities: List[ActivityResult]) -> ComprehensionLevel:
        """
        Assess overall comprehension level for a specific skill.
        
        Args:
            user_id: User identifier
            skill: Skill to assess
            recent_activities: Recent activity results for the skill
            
        Returns:
            Current comprehension level
        """
        if not recent_activities:
            return ComprehensionLevel.BEGINNER
        
        # Calculate weighted average performance
        total_weight = 0
        weighted_score = 0
        
        for i, activity in enumerate(recent_activities):
            # More recent activities have higher weight
            weight = (i + 1) / len(recent_activities)
            weighted_score += activity.score * weight
            total_weight += weight
        
        avg_performance = weighted_score / total_weight if total_weight > 0 else 0
        
        # Determine comprehension level
        comprehension_level = self._score_to_comprehension_level(avg_performance)
        
        # Update stored comprehension level
        if user_id not in self.comprehension_levels:
            self.comprehension_levels[user_id] = {}
        self.comprehension_levels[user_id][skill] = comprehension_level
        
        return comprehension_level
    
    def calibrate_difficulty(self, user_id: str, skill: Skill, performance_history: List[float]) -> DifficultyLevel:
        """
        Calibrate difficulty level based on performance history.
        
        Args:
            user_id: User identifier
            skill: Skill to calibrate difficulty for
            performance_history: List of recent performance scores
            
        Returns:
            Recommended difficulty level
        """
        if not performance_history:
            return DifficultyLevel.EASY
        
        # Calculate performance statistics
        avg_performance = sum(performance_history) / len(performance_history)
        performance_variance = self._calculate_variance(performance_history)
        recent_trend = self._calculate_trend(performance_history[-5:])  # Last 5 scores
        
        # Determine difficulty level
        difficulty = self._calculate_optimal_difficulty(
            avg_performance, 
            performance_variance, 
            recent_trend
        )
        
        # Update stored difficulty calibration
        if user_id not in self.difficulty_calibrations:
            self.difficulty_calibrations[user_id] = {}
        self.difficulty_calibrations[user_id][skill] = difficulty
        
        return difficulty
    
    def generate_feedback(self, user_id: str, activity_result: ActivityResult, context: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Generate comprehensive feedback for user performance.
        
        Args:
            user_id: User identifier
            activity_result: Activity result to generate feedback for
            context: Additional context for feedback generation
            
        Returns:
            Dictionary with different types of feedback
        """
        score = activity_result.score
        errors = activity_result.errors_made
        
        feedback = {
            'overall': self._generate_overall_feedback(score),
            'specific': self._generate_specific_feedback(errors),
            'encouragement': self._generate_encouragement(score, user_id),
            'improvement_tips': self._generate_improvement_tips(errors, score),
            'chinese_explanation': self._generate_chinese_feedback(score, errors)
        }
        
        return feedback
    
    def get_learning_analytics(self, user_id: str, timeframe: timedelta = None) -> Dict[str, Any]:
        """
        Get comprehensive learning analytics for a user.
        
        Args:
            user_id: User identifier
            timeframe: Time period to analyze (defaults to all time)
            
        Returns:
            Learning analytics data
        """
        if user_id not in self.user_assessments:
            return {'error': 'No assessment data available'}
        
        assessments = self.user_assessments[user_id]
        
        # Filter by timeframe if specified
        if timeframe:
            cutoff_time = datetime.now() - timeframe
            assessments = [
                (timestamp, score, skill) for timestamp, score, skill in assessments
                if timestamp >= cutoff_time
            ]
        
        if not assessments:
            return {'error': 'No data in specified timeframe'}
        
        # Calculate analytics
        analytics = {
            'total_activities': len(assessments),
            'average_performance': sum(score for _, score, _ in assessments) / len(assessments),
            'skill_breakdown': self._calculate_skill_breakdown(assessments),
            'performance_trend': self._calculate_performance_trend(assessments),
            'comprehension_levels': self.comprehension_levels.get(user_id, {}),
            'difficulty_levels': self.difficulty_calibrations.get(user_id, {}),
            'strengths': self._identify_strengths(assessments),
            'weaknesses': self._identify_weaknesses(assessments),
            'improvement_rate': self._calculate_improvement_rate(assessments),
            'consistency_score': self._calculate_consistency_score(assessments)
        }
        
        return analytics
    
    def _infer_primary_skill(self, activity_result: ActivityResult) -> Skill:
        """Infer the primary skill from activity result."""
        # This would be more sophisticated in a real implementation
        # For now, use a simple heuristic based on errors
        error_keywords = {
            Skill.VOCABULARY: ['word', 'meaning', 'vocabulary'],
            Skill.GRAMMAR: ['grammar', 'tense', 'syntax'],
            Skill.PRONUNCIATION: ['pronunciation', 'sound'],
            Skill.READING: ['reading', 'comprehension'],
            Skill.LISTENING: ['listening', 'audio'],
            Skill.WRITING: ['writing', 'composition'],
            Skill.SPEAKING: ['speaking', 'fluency']
        }
        
        for skill, keywords in error_keywords.items():
            if any(keyword in error.lower() for error in activity_result.errors_made for keyword in keywords):
                return skill
        
        return Skill.VOCABULARY  # Default
    
    def _analyze_performance(self, user_id: str, activity_result: ActivityResult, expected_performance: float = None) -> Dict[str, Any]:
        """Analyze performance in detail."""
        score = activity_result.score
        
        analysis = {
            'performance_level': 'excellent' if score >= 0.9 else 'good' if score >= 0.7 else 'average' if score >= 0.5 else 'needs_improvement',
            'error_count': len(activity_result.errors_made),
            'time_efficiency': self._analyze_time_efficiency(activity_result),
            'consistency': self._analyze_consistency(user_id, score),
            'difficulty_match': self._analyze_difficulty_match(user_id, score)
        }
        
        if expected_performance:
            analysis['vs_expected'] = 'above' if score > expected_performance else 'below' if score < expected_performance else 'as_expected'
        
        return analysis
    
    def _generate_performance_feedback(self, score: float, analysis: Dict[str, Any], errors: List[str]) -> str:
        """Generate performance-specific feedback."""
        if score >= 0.9:
            return "优秀的表现！继续保持这种学习状态。"
        elif score >= 0.7:
            return "表现良好，还有进步空间。"
        elif score >= 0.5:
            return "表现一般，建议加强练习。"
        else:
            return "需要更多练习来提高表现。"
    
    def _update_comprehension_level(self, user_id: str, skill: Skill, score: float) -> ComprehensionLevel:
        """Update and return comprehension level."""
        # Get recent scores for this skill
        recent_scores = self._get_recent_scores(user_id, skill, limit=5)
        recent_scores.append(score)
        
        # Calculate average
        avg_score = sum(recent_scores) / len(recent_scores)
        
        # Determine comprehension level
        comprehension_level = self._score_to_comprehension_level(avg_score)
        
        # Update stored level
        if user_id not in self.comprehension_levels:
            self.comprehension_levels[user_id] = {}
        self.comprehension_levels[user_id][skill] = comprehension_level
        
        return comprehension_level
    
    def _score_to_comprehension_level(self, score: float) -> ComprehensionLevel:
        """Convert score to comprehension level."""
        for level, (min_score, max_score) in self.comprehension_thresholds.items():
            if min_score <= score < max_score:
                return level
        return ComprehensionLevel.EXPERT  # For perfect scores
    
    def _identify_improvement_areas(self, activity_result: ActivityResult) -> List[str]:
        """Identify specific areas for improvement."""
        areas = []
        
        if activity_result.score < 0.7:
            areas.append("overall_accuracy")
        
        if len(activity_result.errors_made) > 3:
            areas.append("error_reduction")
        
        if activity_result.time_spent > 30:  # Assuming 30 minutes is long
            areas.append("time_efficiency")
        
        # Analyze error patterns
        error_types = self._categorize_errors(activity_result.errors_made)
        areas.extend(error_types)
        
        return areas
    
    def _recommend_next_difficulty(self, user_id: str, skill: Skill) -> str:
        """Recommend next difficulty level."""
        current_level = self.difficulty_calibrations.get(user_id, {}).get(skill, DifficultyLevel.MODERATE)
        recent_scores = self._get_recent_scores(user_id, skill, limit=3)
        
        if not recent_scores:
            return current_level.value
        
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        if avg_recent >= 0.85:
            # Increase difficulty
            difficulty_order = [DifficultyLevel.VERY_EASY, DifficultyLevel.EASY, DifficultyLevel.MODERATE, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
            current_index = difficulty_order.index(current_level)
            if current_index < len(difficulty_order) - 1:
                return difficulty_order[current_index + 1].value
        elif avg_recent < 0.5:
            # Decrease difficulty
            difficulty_order = [DifficultyLevel.VERY_EASY, DifficultyLevel.EASY, DifficultyLevel.MODERATE, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
            current_index = difficulty_order.index(current_level)
            if current_index > 0:
                return difficulty_order[current_index - 1].value
        
        return current_level.value
    
    def _calculate_confidence_level(self, user_id: str, skill: Skill) -> float:
        """Calculate confidence level based on consistency."""
        recent_scores = self._get_recent_scores(user_id, skill, limit=10)
        
        if len(recent_scores) < 3:
            return 0.5  # Neutral confidence
        
        # Calculate consistency (inverse of variance)
        variance = self._calculate_variance(recent_scores)
        avg_score = sum(recent_scores) / len(recent_scores)
        
        # Confidence is high when both average and consistency are high
        consistency_factor = max(0, 1 - variance)
        confidence = (avg_score + consistency_factor) / 2
        
        return min(1.0, max(0.0, confidence))
    
    def _get_recent_scores(self, user_id: str, skill: Skill, limit: int = 5) -> List[float]:
        """Get recent scores for a specific skill."""
        if user_id not in self.user_assessments:
            return []
        
        # Filter by skill and get recent scores
        skill_assessments = [
            (timestamp, score) for timestamp, score, s in self.user_assessments[user_id]
            if s == skill
        ]
        
        # Sort by timestamp and get most recent
        skill_assessments.sort(key=lambda x: x[0], reverse=True)
        return [score for _, score in skill_assessments[:limit]]
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return variance
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate performance trend."""
        if len(scores) < 2:
            return "stable"
        
        first_half = scores[:len(scores)//2] if len(scores) > 2 else scores[:1]
        second_half = scores[len(scores)//2:] if len(scores) > 2 else scores[1:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            return "improving"
        elif second_avg < first_avg * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _calculate_optimal_difficulty(self, avg_performance: float, variance: float, trend: str) -> DifficultyLevel:
        """Calculate optimal difficulty level."""
        # Base difficulty on average performance
        if avg_performance >= 0.85:
            base_difficulty = DifficultyLevel.HARD
        elif avg_performance >= 0.7:
            base_difficulty = DifficultyLevel.MODERATE
        elif avg_performance >= 0.5:
            base_difficulty = DifficultyLevel.EASY
        else:
            base_difficulty = DifficultyLevel.VERY_EASY
        
        # Adjust based on consistency and trend
        if variance > 0.2:  # High variance - reduce difficulty for stability
            difficulty_order = [DifficultyLevel.VERY_EASY, DifficultyLevel.EASY, DifficultyLevel.MODERATE, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
            current_index = difficulty_order.index(base_difficulty)
            if current_index > 0:
                base_difficulty = difficulty_order[current_index - 1]
        
        if trend == "improving":
            # Can handle slightly higher difficulty
            difficulty_order = [DifficultyLevel.VERY_EASY, DifficultyLevel.EASY, DifficultyLevel.MODERATE, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
            current_index = difficulty_order.index(base_difficulty)
            if current_index < len(difficulty_order) - 1:
                base_difficulty = difficulty_order[current_index + 1]
        
        return base_difficulty
    
    def _generate_overall_feedback(self, score: float) -> str:
        """Generate overall performance feedback."""
        if score >= 0.9:
            return "Excellent work! Your performance is outstanding."
        elif score >= 0.7:
            return "Good job! You're making solid progress."
        elif score >= 0.5:
            return "Fair performance. Keep practicing to improve."
        else:
            return "Needs improvement. Focus on the basics and practice more."
    
    def _generate_specific_feedback(self, errors: List[str]) -> str:
        """Generate specific feedback based on errors."""
        if not errors:
            return "No errors detected. Great accuracy!"
        
        error_count = len(errors)
        if error_count == 1:
            return f"One error found: {errors[0]}. Review this concept."
        elif error_count <= 3:
            return f"{error_count} errors found. Focus on these areas for improvement."
        else:
            return f"Multiple errors ({error_count}) detected. Consider reviewing the fundamentals."
    
    def _generate_encouragement(self, score: float, user_id: str) -> str:
        """Generate encouraging feedback."""
        if score >= 0.8:
            return "Keep up the excellent work!"
        elif score >= 0.6:
            return "You're on the right track. Keep going!"
        else:
            return "Don't give up! Every mistake is a learning opportunity."
    
    def _generate_improvement_tips(self, errors: List[str], score: float) -> List[str]:
        """Generate specific improvement tips."""
        tips = []
        
        if score < 0.5:
            tips.append("Review the basic concepts before attempting more exercises")
        
        if len(errors) > 3:
            tips.append("Take your time and double-check your answers")
        
        # Analyze error patterns for specific tips
        error_categories = self._categorize_errors(errors)
        for category in error_categories:
            if category == "vocabulary":
                tips.append("Practice vocabulary with flashcards and context sentences")
            elif category == "grammar":
                tips.append("Review grammar rules and practice with exercises")
        
        return tips
    
    def _generate_chinese_feedback(self, score: float, errors: List[str]) -> str:
        """Generate feedback in Chinese."""
        if score >= 0.9:
            feedback = "表现优秀！继续保持这种学习状态。"
        elif score >= 0.7:
            feedback = "表现良好，继续努力提高。"
        elif score >= 0.5:
            feedback = "表现一般，需要加强练习。"
        else:
            feedback = "需要更多练习来提高水平。"
        
        if errors:
            feedback += f" 发现{len(errors)}个错误，建议重点复习相关知识点。"
        
        return feedback
    
    def _categorize_errors(self, errors: List[str]) -> List[str]:
        """Categorize errors into types."""
        categories = []
        
        for error in errors:
            error_lower = error.lower()
            if any(word in error_lower for word in ['word', 'vocabulary', 'meaning']):
                categories.append('vocabulary')
            elif any(word in error_lower for word in ['grammar', 'tense', 'syntax']):
                categories.append('grammar')
            elif any(word in error_lower for word in ['pronunciation', 'sound']):
                categories.append('pronunciation')
        
        return list(set(categories))  # Remove duplicates
    
    def _analyze_time_efficiency(self, activity_result: ActivityResult) -> str:
        """Analyze time efficiency of the activity."""
        time_spent = activity_result.time_spent
        
        if time_spent <= 10:
            return "very_efficient"
        elif time_spent <= 20:
            return "efficient"
        elif time_spent <= 30:
            return "moderate"
        else:
            return "needs_improvement"
    
    def _analyze_consistency(self, user_id: str, current_score: float) -> str:
        """Analyze consistency with previous performances."""
        recent_scores = self._get_recent_scores(user_id, Skill.VOCABULARY, limit=5)  # Simplified
        
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        variance = self._calculate_variance(recent_scores + [current_score])
        
        if variance < 0.05:
            return "very_consistent"
        elif variance < 0.15:
            return "consistent"
        elif variance < 0.25:
            return "somewhat_consistent"
        else:
            return "inconsistent"
    
    def _analyze_difficulty_match(self, user_id: str, score: float) -> str:
        """Analyze if difficulty level matches user ability."""
        if score >= 0.85:
            return "too_easy"
        elif score >= 0.6:
            return "appropriate"
        elif score >= 0.4:
            return "challenging"
        else:
            return "too_difficult"
    
    def _calculate_skill_breakdown(self, assessments: List[Tuple[datetime, float, Skill]]) -> Dict[str, float]:
        """Calculate performance breakdown by skill."""
        skill_scores = {}
        skill_counts = {}
        
        for _, score, skill in assessments:
            if skill not in skill_scores:
                skill_scores[skill] = 0
                skill_counts[skill] = 0
            skill_scores[skill] += score
            skill_counts[skill] += 1
        
        return {
            skill.value: skill_scores[skill] / skill_counts[skill]
            for skill in skill_scores
        }
    
    def _calculate_performance_trend(self, assessments: List[Tuple[datetime, float, Skill]]) -> str:
        """Calculate overall performance trend."""
        if len(assessments) < 5:
            return "insufficient_data"
        
        # Sort by timestamp
        sorted_assessments = sorted(assessments, key=lambda x: x[0])
        scores = [score for _, score, _ in sorted_assessments]
        
        return self._calculate_trend(scores)
    
    def _identify_strengths(self, assessments: List[Tuple[datetime, float, Skill]]) -> List[str]:
        """Identify user's strengths."""
        skill_breakdown = self._calculate_skill_breakdown(assessments)
        
        strengths = []
        for skill, avg_score in skill_breakdown.items():
            if avg_score >= 0.8:
                strengths.append(skill)
        
        return strengths
    
    def _identify_weaknesses(self, assessments: List[Tuple[datetime, float, Skill]]) -> List[str]:
        """Identify user's weaknesses."""
        skill_breakdown = self._calculate_skill_breakdown(assessments)
        
        weaknesses = []
        for skill, avg_score in skill_breakdown.items():
            if avg_score < 0.6:
                weaknesses.append(skill)
        
        return weaknesses
    
    def _calculate_improvement_rate(self, assessments: List[Tuple[datetime, float, Skill]]) -> float:
        """Calculate rate of improvement over time."""
        if len(assessments) < 10:
            return 0.0
        
        # Sort by timestamp
        sorted_assessments = sorted(assessments, key=lambda x: x[0])
        scores = [score for _, score, _ in sorted_assessments]
        
        # Compare first and last quarters
        first_quarter = scores[:len(scores)//4]
        last_quarter = scores[-len(scores)//4:]
        
        first_avg = sum(first_quarter) / len(first_quarter)
        last_avg = sum(last_quarter) / len(last_quarter)
        
        if first_avg == 0:
            return 0.0
        
        return (last_avg - first_avg) / first_avg
    
    def _calculate_consistency_score(self, assessments: List[Tuple[datetime, float, Skill]]) -> float:
        """Calculate consistency score (inverse of variance)."""
        scores = [score for _, score, _ in assessments]
        variance = self._calculate_variance(scores)
        
        # Convert variance to consistency score (0-1 scale)
        consistency = max(0, 1 - variance)
        return consistency