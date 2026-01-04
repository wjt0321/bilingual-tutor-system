"""
Weakness Analyzer - Identifies user's weak areas through pattern analysis.
"""

from typing import List, Dict, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import uuid
from ..models import WeakArea, Skill, WeaknessAnalyzerInterface, ActivityResult


class WeaknessAnalyzer(WeaknessAnalyzerInterface):
    """
    Identifies user's weak areas in language learning through error pattern
    analysis and skill gap identification.
    """
    
    def __init__(self):
        """Initialize the weakness analyzer with analysis structures."""
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)
        self.skill_performance: Dict[str, Dict[Skill, List[float]]] = defaultdict(lambda: defaultdict(list))
        self.weakness_history: Dict[str, List[WeakArea]] = defaultdict(list)
        self.activity_results: Dict[str, List[ActivityResult]] = defaultdict(list)
        
        # Severity thresholds for different metrics
        self.error_rate_threshold = 0.3  # 30% error rate indicates weakness
        self.performance_threshold = 0.6  # Below 60% performance indicates weakness
        self.consistency_threshold = 0.2  # High variance indicates inconsistency
    
    def record_activity_result(self, user_id: str, result: ActivityResult) -> None:
        """
        Record an activity result for later analysis.
        
        Args:
            user_id: Unique identifier for the user
            result: Activity result to record
        """
        self.activity_results[user_id].append(result)
        
        # Extract error patterns
        if result.errors_made:
            self.error_patterns[user_id].extend(result.errors_made)
    
    def analyze_error_patterns(self, user_id: str, timeframe: timedelta) -> List[WeakArea]:
        """
        Analyze error patterns to identify weaknesses.
        
        Args:
            user_id: Unique identifier for the user
            timeframe: Time period to analyze errors for
            
        Returns:
            List of identified weak areas
        """
        weak_areas = []
        cutoff_time = datetime.now() - timeframe
        
        # Get recent activity results
        recent_results = [
            result for result in self.activity_results[user_id]
            if result.completed_at >= cutoff_time
        ]
        
        if not recent_results:
            return weak_areas
        
        # Analyze error patterns by skill type
        skill_errors = defaultdict(list)
        skill_activities = defaultdict(int)
        
        for result in recent_results:
            # Infer skill from activity patterns
            skills = self._infer_skills_from_errors(result.errors_made)
            skill_activities[Skill.VOCABULARY] += 1  # Default tracking
            
            for skill in skills:
                skill_errors[skill].extend(result.errors_made)
                skill_activities[skill] += 1
        
        # Identify patterns in errors
        for skill, errors in skill_errors.items():
            if not errors:
                continue
                
            error_counter = Counter(errors)
            total_activities = skill_activities[skill]
            
            # Calculate error rate
            error_rate = len(errors) / max(total_activities, 1)
            
            if error_rate >= self.error_rate_threshold:
                # Find common error patterns
                common_patterns = [
                    error for error, count in error_counter.most_common(3)
                    if count >= 2  # Appears at least twice
                ]
                
                if common_patterns:
                    weak_area = WeakArea(
                        area_id=str(uuid.uuid4()),
                        skill=skill,
                        language=self._infer_language_from_errors(errors),
                        severity=min(error_rate, 1.0),
                        error_patterns=common_patterns,
                        improvement_suggestions=[],
                        identified_at=datetime.now()
                    )
                    weak_areas.append(weak_area)
        
        return weak_areas
    
    def identify_skill_gaps(self, user_id: str, language: str) -> List[WeakArea]:
        """
        Identify skill gaps for a specific language.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to analyze (english or japanese)
            
        Returns:
            List of skill gaps identified
        """
        weak_areas = []
        
        # Get performance data for the language
        language_results = [
            result for result in self.activity_results[user_id]
            if self._get_language_from_activity(result) == language
        ]
        
        if not language_results:
            return weak_areas
        
        # Analyze performance by skill
        skill_performance = defaultdict(list)
        
        for result in language_results:
            skills = self._infer_skills_from_activity(result)
            for skill in skills:
                skill_performance[skill].append(result.score)
        
        # Identify gaps based on performance
        for skill, scores in skill_performance.items():
            if not scores:
                continue
                
            avg_score = sum(scores) / len(scores)
            score_variance = self._calculate_variance(scores)
            
            # Check for low performance or high inconsistency
            is_low_performance = avg_score < self.performance_threshold
            is_inconsistent = score_variance > self.consistency_threshold
            
            if is_low_performance or is_inconsistent:
                severity = 1.0 - avg_score if is_low_performance else score_variance
                
                weak_area = WeakArea(
                    area_id=str(uuid.uuid4()),
                    skill=skill,
                    language=language,
                    severity=min(severity, 1.0),
                    error_patterns=self._get_common_errors_for_skill(user_id, skill, language),
                    improvement_suggestions=[],
                    identified_at=datetime.now()
                )
                weak_areas.append(weak_area)
        
        return weak_areas
    
    def calculate_weakness_severity(self, weakness: WeakArea) -> float:
        """
        Calculate the severity of a weakness.
        
        Args:
            weakness: Weak area to calculate severity for
            
        Returns:
            Severity score from 0.0 to 1.0
        """
        # Base severity from the weakness itself
        base_severity = weakness.severity
        
        # Adjust based on error pattern frequency
        pattern_weight = len(weakness.error_patterns) * 0.1
        
        # Adjust based on skill importance (some skills are more critical)
        skill_weights = {
            Skill.VOCABULARY: 1.0,
            Skill.GRAMMAR: 0.9,
            Skill.READING: 0.8,
            Skill.LISTENING: 0.8,
            Skill.SPEAKING: 0.7,
            Skill.WRITING: 0.7,
            Skill.PRONUNCIATION: 0.6,
            Skill.COMPREHENSION: 0.8
        }
        
        skill_weight = skill_weights.get(weakness.skill, 0.5)
        
        # Calculate final severity
        final_severity = base_severity * skill_weight + pattern_weight
        
        return min(final_severity, 1.0)
    
    def prioritize_improvements(self, weaknesses: List[WeakArea]) -> List[WeakArea]:
        """
        Prioritize weaknesses by severity and impact.
        
        Args:
            weaknesses: List of identified weaknesses
            
        Returns:
            Prioritized list of weaknesses
        """
        # Calculate priority scores for each weakness
        prioritized = []
        
        for weakness in weaknesses:
            severity = self.calculate_weakness_severity(weakness)
            
            # Consider recency (more recent weaknesses get higher priority)
            days_since_identified = (datetime.now() - weakness.identified_at).days
            recency_factor = max(0.1, 1.0 - (days_since_identified * 0.1))
            
            # Consider skill interdependencies
            dependency_factor = self._get_skill_dependency_factor(weakness.skill)
            
            priority_score = severity * recency_factor * dependency_factor
            
            prioritized.append((priority_score, weakness))
        
        # Sort by priority score (highest first)
        prioritized.sort(key=lambda x: x[0], reverse=True)
        
        return [weakness for _, weakness in prioritized]
    
    def track_improvement_progress(self, user_id: str, weakness: WeakArea) -> float:
        """
        Track improvement progress for a specific weakness.
        
        Args:
            user_id: Unique identifier for the user
            weakness: Weakness to track progress for
            
        Returns:
            Improvement progress as percentage
        """
        # Get historical performance for this skill and language
        relevant_results = [
            result for result in self.activity_results[user_id]
            if (self._get_language_from_activity(result) == weakness.language and
                weakness.skill in self._infer_skills_from_activity(result))
        ]
        
        if len(relevant_results) < 2:
            return 0.0  # Not enough data to track progress
        
        # Sort by completion time
        relevant_results.sort(key=lambda x: x.completed_at)
        
        # Compare recent performance to baseline
        baseline_period = len(relevant_results) // 3  # First third as baseline
        recent_period = len(relevant_results) // 3   # Last third as recent
        
        if baseline_period == 0 or recent_period == 0:
            return 0.0
        
        baseline_scores = [r.score for r in relevant_results[:baseline_period]]
        recent_scores = [r.score for r in relevant_results[-recent_period:]]
        
        baseline_avg = sum(baseline_scores) / len(baseline_scores)
        recent_avg = sum(recent_scores) / len(recent_scores)
        
        # Calculate improvement percentage
        if baseline_avg == 0:
            return 100.0 if recent_avg > 0 else 0.0
        
        improvement = ((recent_avg - baseline_avg) / baseline_avg) * 100
        return max(0.0, min(improvement, 100.0))
    
    def generate_improvement_recommendations(self, weakness: WeakArea) -> List[str]:
        """
        Generate specific improvement recommendations for a weakness.
        
        Args:
            weakness: Weakness to generate recommendations for
            
        Returns:
            List of improvement recommendations
        """
        recommendations = []
        
        # Skill-specific recommendations
        skill_recommendations = {
            Skill.VOCABULARY: [
                "增加词汇练习频率，使用间隔重复法",
                "创建词汇卡片，包含例句和语境",
                "阅读相关主题的文章来学习词汇用法"
            ],
            Skill.GRAMMAR: [
                "专注于语法规则的理解和应用",
                "做更多语法填空练习",
                "分析错误句子，理解语法错误原因"
            ],
            Skill.READING: [
                "增加阅读量，选择适合水平的材料",
                "练习快速阅读和精读技巧",
                "学习阅读策略，如预测和推理"
            ],
            Skill.LISTENING: [
                "每天听适合水平的音频材料",
                "练习听写，提高听力准确性",
                "学习识别语音模式和语调"
            ],
            Skill.SPEAKING: [
                "增加口语练习时间",
                "录音自我评估发音和流利度",
                "参与对话练习，提高表达能力"
            ],
            Skill.WRITING: [
                "练习不同类型的写作任务",
                "学习写作结构和连接词使用",
                "请他人检查和反馈写作内容"
            ]
        }
        
        base_recommendations = skill_recommendations.get(weakness.skill, [])
        recommendations.extend(base_recommendations)
        
        # Add pattern-specific recommendations
        if weakness.error_patterns:
            recommendations.append(f"重点关注常见错误模式：{', '.join(weakness.error_patterns[:3])}")
        
        # Add severity-based recommendations
        if weakness.severity > 0.7:
            recommendations.append("这是一个高优先级弱点，建议每天专门练习")
        elif weakness.severity > 0.4:
            recommendations.append("建议每周安排2-3次针对性练习")
        else:
            recommendations.append("可以在日常学习中逐步改进")
        
        return recommendations
    
    def _infer_skills_from_errors(self, errors: List[str]) -> Set[Skill]:
        """Infer skills from error patterns."""
        skills = set()
        
        for error in errors:
            error_lower = error.lower()
            if any(word in error_lower for word in ['word', 'vocabulary', 'meaning']):
                skills.add(Skill.VOCABULARY)
            elif any(word in error_lower for word in ['grammar', 'tense', 'particle']):
                skills.add(Skill.GRAMMAR)
            elif any(word in error_lower for word in ['pronunciation', 'sound']):
                skills.add(Skill.PRONUNCIATION)
            elif any(word in error_lower for word in ['reading', 'comprehension']):
                skills.add(Skill.READING)
            else:
                skills.add(Skill.VOCABULARY)  # Default
        
        return skills if skills else {Skill.VOCABULARY}
    
    def _infer_language_from_errors(self, errors: List[str]) -> str:
        """Infer language from error patterns."""
        # Simple heuristic - could be improved with better analysis
        japanese_indicators = ['hiragana', 'katakana', 'kanji', 'particle', 'です', 'ます']
        
        for error in errors:
            if any(indicator in error.lower() for indicator in japanese_indicators):
                return 'japanese'
        
        return 'english'  # Default
    
    def _get_language_from_activity(self, result: ActivityResult) -> str:
        """Extract language from activity result."""
        # This would typically be stored in the activity result
        # For now, use a simple heuristic
        return 'english'  # Default - would need proper implementation
    
    def _infer_skills_from_activity(self, result: ActivityResult) -> Set[Skill]:
        """Infer skills practiced in an activity."""
        # This would typically be stored in the activity
        # For now, return a default set
        return {Skill.VOCABULARY, Skill.GRAMMAR}
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate variance of scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return variance
    
    def _get_common_errors_for_skill(self, user_id: str, skill: Skill, language: str) -> List[str]:
        """Get common errors for a specific skill and language."""
        relevant_errors = []
        
        for result in self.activity_results[user_id]:
            if (self._get_language_from_activity(result) == language and
                skill in self._infer_skills_from_activity(result)):
                relevant_errors.extend(result.errors_made)
        
        # Return most common errors
        error_counter = Counter(relevant_errors)
        return [error for error, _ in error_counter.most_common(3)]
    
    def _get_skill_dependency_factor(self, skill: Skill) -> float:
        """Get dependency factor for skill prioritization."""
        # Some skills are foundational and should be prioritized
        dependency_factors = {
            Skill.VOCABULARY: 1.0,  # Most foundational
            Skill.GRAMMAR: 0.9,     # Very important
            Skill.PRONUNCIATION: 0.8,
            Skill.READING: 0.7,
            Skill.LISTENING: 0.7,
            Skill.COMPREHENSION: 0.8,
            Skill.SPEAKING: 0.6,
            Skill.WRITING: 0.6
        }
        
        return dependency_factors.get(skill, 0.5)