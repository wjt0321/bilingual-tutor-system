"""
Weakness Prioritization System - Implements balanced curriculum with weakness focus.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from ..models import (
    WeakArea, Skill, UserProfile, DailyPlan, LearningActivity, 
    ActivityType, ContentType, Content
)


@dataclass
class CurriculumBalance:
    """Represents the balance between different aspects of curriculum."""
    weakness_focus_ratio: float  # 0.0 to 1.0, how much to focus on weaknesses
    skill_distribution: Dict[Skill, float]  # Distribution across skills
    language_distribution: Dict[str, float]  # Distribution across languages
    new_vs_review_ratio: float  # Balance between new content and review


@dataclass
class PriorityCalculation:
    """Detailed priority calculation for a weakness."""
    weakness: WeakArea
    base_priority: float
    urgency_factor: float
    impact_factor: float
    dependency_factor: float
    balance_factor: float
    final_priority: float


class WeaknessPrioritizer:
    """
    Implements balanced curriculum with weakness focus.
    Creates priority calculation algorithms and curriculum adjustment logic.
    """
    
    def __init__(self):
        """Initialize the weakness prioritizer."""
        self.priority_history: Dict[str, List[PriorityCalculation]] = {}
        self.curriculum_adjustments: Dict[str, List[Dict]] = {}
        self.balance_targets = self._initialize_balance_targets()
    
    def prioritize_weaknesses_with_balance(self, user_profile: UserProfile, 
                                         weaknesses: List[WeakArea],
                                         current_plan: DailyPlan) -> Tuple[List[WeakArea], CurriculumBalance]:
        """
        Prioritize weaknesses while maintaining curriculum balance.
        
        Args:
            user_profile: User's profile and learning goals
            weaknesses: List of identified weaknesses
            current_plan: Current daily learning plan
            
        Returns:
            Tuple of (prioritized weaknesses, recommended curriculum balance)
        """
        if not weaknesses:
            return [], self._get_default_balance()
        
        # Calculate priority for each weakness
        priority_calculations = []
        for weakness in weaknesses:
            calculation = self._calculate_detailed_priority(
                weakness, user_profile, current_plan
            )
            priority_calculations.append(calculation)
        
        # Sort by final priority
        priority_calculations.sort(key=lambda x: x.final_priority, reverse=True)
        
        # Apply balance constraints
        balanced_priorities = self._apply_balance_constraints(
            priority_calculations, user_profile, current_plan
        )
        
        # Generate curriculum balance recommendation
        curriculum_balance = self._generate_curriculum_balance(
            balanced_priorities, user_profile
        )
        
        # Store priority history
        self.priority_history[user_profile.user_id] = balanced_priorities
        
        # Extract prioritized weaknesses
        prioritized_weaknesses = [calc.weakness for calc in balanced_priorities]
        
        return prioritized_weaknesses, curriculum_balance
    
    def adjust_curriculum_for_weaknesses(self, base_plan: DailyPlan, 
                                       prioritized_weaknesses: List[WeakArea],
                                       curriculum_balance: CurriculumBalance) -> DailyPlan:
        """
        Adjust curriculum to focus on weaknesses while maintaining balance.
        
        Args:
            base_plan: Original daily learning plan
            prioritized_weaknesses: Weaknesses ordered by priority
            curriculum_balance: Recommended curriculum balance
            
        Returns:
            Adjusted daily plan with weakness focus
        """
        # Create adjusted plan
        adjusted_plan = DailyPlan(
            plan_id=base_plan.plan_id + "_weakness_focused",
            user_id=base_plan.user_id,
            date=base_plan.date,
            activities=base_plan.activities.copy(),
            time_allocation=base_plan.time_allocation,
            learning_objectives=base_plan.learning_objectives.copy(),
            estimated_completion_time=base_plan.estimated_completion_time
        )
        
        # Apply weakness-focused adjustments
        adjusted_plan = self._adjust_activities_for_weaknesses(
            adjusted_plan, prioritized_weaknesses, curriculum_balance
        )
        
        # Ensure curriculum balance is maintained
        adjusted_plan = self._ensure_curriculum_balance(
            adjusted_plan, curriculum_balance
        )
        
        # Add weakness-focused objectives
        adjusted_plan = self._add_weakness_objectives(
            adjusted_plan, prioritized_weaknesses
        )
        
        # Record curriculum adjustment
        self._record_curriculum_adjustment(
            base_plan.user_id, base_plan, adjusted_plan, prioritized_weaknesses
        )
        
        return adjusted_plan
    
    def calculate_balance_metrics(self, plan: DailyPlan) -> Dict[str, float]:
        """
        Calculate balance metrics for a learning plan.
        
        Args:
            plan: Daily learning plan to analyze
            
        Returns:
            Dictionary of balance metrics
        """
        metrics = {
            "skill_balance": 0.0,
            "language_balance": 0.0,
            "difficulty_balance": 0.0,
            "activity_type_balance": 0.0,
            "overall_balance": 0.0
        }
        
        if not plan.activities:
            return metrics
        
        # Calculate skill distribution
        skill_distribution = self._calculate_skill_distribution(plan.activities)
        metrics["skill_balance"] = self._calculate_distribution_balance(skill_distribution)
        
        # Calculate language distribution
        language_distribution = self._calculate_language_distribution(plan.activities)
        metrics["language_balance"] = self._calculate_distribution_balance(language_distribution)
        
        # Calculate difficulty distribution
        difficulty_distribution = self._calculate_difficulty_distribution(plan.activities)
        metrics["difficulty_balance"] = self._calculate_distribution_balance(difficulty_distribution)
        
        # Calculate activity type distribution
        activity_type_distribution = self._calculate_activity_type_distribution(plan.activities)
        metrics["activity_type_balance"] = self._calculate_distribution_balance(activity_type_distribution)
        
        # Calculate overall balance
        metrics["overall_balance"] = (
            metrics["skill_balance"] * 0.3 +
            metrics["language_balance"] * 0.3 +
            metrics["difficulty_balance"] * 0.2 +
            metrics["activity_type_balance"] * 0.2
        )
        
        return metrics
    
    def get_weakness_focus_recommendations(self, user_profile: UserProfile,
                                        weaknesses: List[WeakArea]) -> List[str]:
        """
        Get specific recommendations for focusing on weaknesses.
        
        Args:
            user_profile: User's profile and preferences
            weaknesses: List of prioritized weaknesses
            
        Returns:
            List of specific recommendations
        """
        recommendations = []
        
        if not weaknesses:
            recommendations.append("目前没有发现明显的弱点，继续保持均衡学习")
            return recommendations
        
        # Focus on top weaknesses
        top_weaknesses = weaknesses[:3]  # Focus on top 3
        
        for i, weakness in enumerate(top_weaknesses):
            priority_level = ["最高", "高", "中等"][i] if i < 3 else "一般"
            
            recommendations.append(
                f"{priority_level}优先级：加强 {weakness.skill.value} ({weakness.language}) - "
                f"严重程度: {weakness.severity:.1%}"
            )
        
        # Add balance recommendations
        if len(weaknesses) > 3:
            recommendations.append(
                f"同时关注其他 {len(weaknesses) - 3} 个弱点，但优先级较低"
            )
        
        # Add time allocation recommendations
        total_weakness_time = min(0.6, len(top_weaknesses) * 0.15)  # Max 60% on weaknesses
        recommendations.append(
            f"建议将 {total_weakness_time:.0%} 的学习时间用于改进弱点"
        )
        
        return recommendations
    
    def _calculate_detailed_priority(self, weakness: WeakArea, 
                                   user_profile: UserProfile,
                                   current_plan: DailyPlan) -> PriorityCalculation:
        """Calculate detailed priority for a weakness."""
        
        # Base priority from weakness severity
        base_priority = weakness.severity
        
        # Urgency factor (how recently identified, how severe)
        days_since_identified = (datetime.now() - weakness.identified_at).days
        urgency_factor = max(0.1, 1.0 - (days_since_identified * 0.05))
        
        # Impact factor (how much this weakness affects overall learning)
        impact_factor = self._calculate_impact_factor(weakness, user_profile)
        
        # Dependency factor (how foundational this skill is)
        dependency_factor = self._get_skill_dependency_factor(weakness.skill)
        
        # Balance factor (how much this weakness is already being addressed)
        balance_factor = self._calculate_balance_factor(weakness, current_plan)
        
        # Calculate final priority
        final_priority = (
            base_priority * 0.3 +
            urgency_factor * 0.2 +
            impact_factor * 0.2 +
            dependency_factor * 0.2 +
            balance_factor * 0.1
        )
        
        return PriorityCalculation(
            weakness=weakness,
            base_priority=base_priority,
            urgency_factor=urgency_factor,
            impact_factor=impact_factor,
            dependency_factor=dependency_factor,
            balance_factor=balance_factor,
            final_priority=final_priority
        )
    
    def _apply_balance_constraints(self, priority_calculations: List[PriorityCalculation],
                                 user_profile: UserProfile,
                                 current_plan: DailyPlan) -> List[PriorityCalculation]:
        """Apply balance constraints to priority calculations."""
        
        # Ensure we don't over-focus on any single skill or language
        skill_counts = {}
        language_counts = {}
        
        balanced_calculations = []
        
        for calc in priority_calculations:
            skill = calc.weakness.skill
            language = calc.weakness.language
            
            # Count current focus
            skill_count = skill_counts.get(skill, 0)
            language_count = language_counts.get(language, 0)
            
            # Apply diminishing returns for over-represented skills/languages
            skill_penalty = min(1.0, 1.0 - (skill_count * 0.2))
            language_penalty = min(1.0, 1.0 - (language_count * 0.3))
            
            # Adjust priority
            adjusted_priority = calc.final_priority * skill_penalty * language_penalty
            
            # Create adjusted calculation
            adjusted_calc = PriorityCalculation(
                weakness=calc.weakness,
                base_priority=calc.base_priority,
                urgency_factor=calc.urgency_factor,
                impact_factor=calc.impact_factor,
                dependency_factor=calc.dependency_factor,
                balance_factor=calc.balance_factor * skill_penalty * language_penalty,
                final_priority=adjusted_priority
            )
            
            balanced_calculations.append(adjusted_calc)
            
            # Update counts
            skill_counts[skill] = skill_count + 1
            language_counts[language] = language_count + 1
        
        # Re-sort by adjusted priority
        balanced_calculations.sort(key=lambda x: x.final_priority, reverse=True)
        
        return balanced_calculations
    
    def _generate_curriculum_balance(self, priority_calculations: List[PriorityCalculation],
                                   user_profile: UserProfile) -> CurriculumBalance:
        """Generate curriculum balance recommendation."""
        
        # Calculate weakness focus ratio based on severity
        if priority_calculations:
            avg_severity = sum(calc.weakness.severity for calc in priority_calculations) / len(priority_calculations)
            weakness_focus_ratio = min(0.6, avg_severity * 0.8)  # Max 60% focus on weaknesses
        else:
            weakness_focus_ratio = 0.2  # Default 20% if no weaknesses
        
        # Calculate skill distribution
        skill_distribution = {}
        total_priority = sum(calc.final_priority for calc in priority_calculations)
        
        if total_priority > 0:
            for calc in priority_calculations:
                skill = calc.weakness.skill
                if skill not in skill_distribution:
                    skill_distribution[skill] = 0.0
                skill_distribution[skill] += calc.final_priority / total_priority
        
        # Ensure all skills have some representation
        all_skills = list(Skill)
        for skill in all_skills:
            if skill not in skill_distribution:
                skill_distribution[skill] = 0.1 / len(all_skills)
        
        # Normalize skill distribution
        total_skill_weight = sum(skill_distribution.values())
        if total_skill_weight > 0:
            skill_distribution = {
                skill: weight / total_skill_weight 
                for skill, weight in skill_distribution.items()
            }
        
        # Calculate language distribution based on user goals
        english_weight = 0.5  # Default equal weight
        japanese_weight = 0.5
        
        # Adjust based on user's target levels and current progress
        if hasattr(user_profile, 'target_goals'):
            # This would be more sophisticated in a real implementation
            pass
        
        language_distribution = {
            "english": english_weight,
            "japanese": japanese_weight
        }
        
        # Set new vs review ratio (maintain 20% review as per requirements)
        new_vs_review_ratio = 0.8  # 80% new content, 20% review
        
        return CurriculumBalance(
            weakness_focus_ratio=weakness_focus_ratio,
            skill_distribution=skill_distribution,
            language_distribution=language_distribution,
            new_vs_review_ratio=new_vs_review_ratio
        )
    
    def _adjust_activities_for_weaknesses(self, plan: DailyPlan,
                                        weaknesses: List[WeakArea],
                                        balance: CurriculumBalance) -> DailyPlan:
        """Adjust activities to focus on weaknesses."""
        
        if not weaknesses:
            return plan
        
        # Calculate time to allocate to weakness-focused activities
        total_content_time = plan.time_allocation.english_minutes + plan.time_allocation.japanese_minutes
        weakness_time = int(total_content_time * balance.weakness_focus_ratio)
        
        # Create weakness-focused activities
        weakness_activities = []
        time_per_weakness = weakness_time // min(len(weaknesses), 3)  # Focus on top 3
        
        for i, weakness in enumerate(weaknesses[:3]):
            if time_per_weakness > 0:
                activity = self._create_weakness_focused_activity(
                    weakness, time_per_weakness, plan.user_id
                )
                weakness_activities.append(activity)
        
        # Add weakness activities to the plan
        plan.activities.extend(weakness_activities)
        
        return plan
    
    def _ensure_curriculum_balance(self, plan: DailyPlan, 
                                 balance: CurriculumBalance) -> DailyPlan:
        """Ensure the plan maintains curriculum balance."""
        
        # Check current balance
        current_metrics = self.calculate_balance_metrics(plan)
        
        # If balance is too skewed, add balancing activities
        if current_metrics["overall_balance"] < 0.6:  # Threshold for acceptable balance
            balancing_activities = self._create_balancing_activities(
                plan, balance, current_metrics
            )
            plan.activities.extend(balancing_activities)
        
        return plan
    
    def _add_weakness_objectives(self, plan: DailyPlan, 
                               weaknesses: List[WeakArea]) -> DailyPlan:
        """Add weakness-focused learning objectives."""
        
        for weakness in weaknesses[:3]:  # Top 3 weaknesses
            objective = f"重点改进 {weakness.skill.value} ({weakness.language}) - 严重程度: {weakness.severity:.1%}"
            plan.learning_objectives.append(objective)
        
        if len(weaknesses) > 3:
            plan.learning_objectives.append(f"同时关注其他 {len(weaknesses) - 3} 个弱点")
        
        return plan
    
    def _calculate_impact_factor(self, weakness: WeakArea, user_profile: UserProfile) -> float:
        """Calculate how much this weakness impacts overall learning."""
        
        # Base impact from skill importance
        skill_importance = {
            Skill.VOCABULARY: 1.0,
            Skill.GRAMMAR: 0.9,
            Skill.READING: 0.8,
            Skill.LISTENING: 0.8,
            Skill.COMPREHENSION: 0.8,
            Skill.SPEAKING: 0.7,
            Skill.WRITING: 0.7,
            Skill.PRONUNCIATION: 0.6
        }
        
        base_impact = skill_importance.get(weakness.skill, 0.5)
        
        # Adjust based on user's goals
        if hasattr(user_profile, 'target_goals') and user_profile.target_goals:
            if weakness.skill in user_profile.target_goals.priority_skills:
                base_impact *= 1.2  # Boost for priority skills
        
        return min(1.0, base_impact)
    
    def _get_skill_dependency_factor(self, skill: Skill) -> float:
        """Get dependency factor for skill prioritization."""
        dependency_factors = {
            Skill.VOCABULARY: 1.0,  # Most foundational
            Skill.GRAMMAR: 0.9,     # Very important for structure
            Skill.PRONUNCIATION: 0.8,
            Skill.COMPREHENSION: 0.8,
            Skill.READING: 0.7,
            Skill.LISTENING: 0.7,
            Skill.SPEAKING: 0.6,
            Skill.WRITING: 0.6
        }
        
        return dependency_factors.get(skill, 0.5)
    
    def _calculate_balance_factor(self, weakness: WeakArea, current_plan: DailyPlan) -> float:
        """Calculate how much this weakness is already being addressed."""
        
        # Count activities that address this weakness
        addressing_activities = 0
        total_activities = len(current_plan.activities)
        
        for activity in current_plan.activities:
            if (activity.language == weakness.language and
                weakness.skill in activity.skills_practiced):
                addressing_activities += 1
        
        if total_activities == 0:
            return 1.0
        
        # Higher balance factor if weakness is under-addressed
        address_ratio = addressing_activities / total_activities
        balance_factor = max(0.1, 1.0 - address_ratio)
        
        return balance_factor
    
    def _create_weakness_focused_activity(self, weakness: WeakArea, 
                                        duration: int, user_id: str) -> LearningActivity:
        """Create an activity focused on a specific weakness."""
        
        # Map skill to activity type
        skill_to_activity = {
            Skill.VOCABULARY: ActivityType.VOCABULARY,
            Skill.GRAMMAR: ActivityType.GRAMMAR,
            Skill.READING: ActivityType.READING,
            Skill.LISTENING: ActivityType.LISTENING,
            Skill.SPEAKING: ActivityType.SPEAKING,
            Skill.WRITING: ActivityType.WRITING
        }
        
        activity_type = skill_to_activity.get(weakness.skill, ActivityType.VOCABULARY)
        
        # Create content focused on the weakness
        content = Content(
            content_id=str(uuid.uuid4()),
            title=f"{weakness.skill.value} 弱点改进练习",
            body=f"针对 {weakness.skill.value} 弱点的专项练习",
            language=weakness.language,
            difficulty_level="adaptive",
            content_type=ContentType.EXERCISE,
            source_url="internal://weakness_focused",
            quality_score=0.9,
            created_at=datetime.now(),
            tags=[weakness.language, weakness.skill.value, "weakness_focused"]
        )
        
        return LearningActivity(
            activity_id=str(uuid.uuid4()),
            activity_type=activity_type,
            language=weakness.language,
            content=content,
            estimated_duration=duration,
            difficulty_level="adaptive",
            skills_practiced=[weakness.skill]
        )
    
    def _create_balancing_activities(self, plan: DailyPlan, 
                                   balance: CurriculumBalance,
                                   current_metrics: Dict[str, float]) -> List[LearningActivity]:
        """Create activities to improve curriculum balance."""
        
        balancing_activities = []
        
        # This would be more sophisticated in a real implementation
        # For now, return empty list
        
        return balancing_activities
    
    def _calculate_skill_distribution(self, activities: List[LearningActivity]) -> Dict[Skill, float]:
        """Calculate distribution of skills across activities."""
        skill_counts = {}
        total_skills = 0
        
        for activity in activities:
            for skill in activity.skills_practiced:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
                total_skills += 1
        
        if total_skills == 0:
            return {}
        
        return {skill: count / total_skills for skill, count in skill_counts.items()}
    
    def _calculate_language_distribution(self, activities: List[LearningActivity]) -> Dict[str, float]:
        """Calculate distribution of languages across activities."""
        language_counts = {}
        total_activities = len(activities)
        
        for activity in activities:
            language_counts[activity.language] = language_counts.get(activity.language, 0) + 1
        
        if total_activities == 0:
            return {}
        
        return {lang: count / total_activities for lang, count in language_counts.items()}
    
    def _calculate_difficulty_distribution(self, activities: List[LearningActivity]) -> Dict[str, float]:
        """Calculate distribution of difficulty levels across activities."""
        difficulty_counts = {}
        total_activities = len(activities)
        
        for activity in activities:
            difficulty_counts[activity.difficulty_level] = difficulty_counts.get(activity.difficulty_level, 0) + 1
        
        if total_activities == 0:
            return {}
        
        return {diff: count / total_activities for diff, count in difficulty_counts.items()}
    
    def _calculate_activity_type_distribution(self, activities: List[LearningActivity]) -> Dict[ActivityType, float]:
        """Calculate distribution of activity types across activities."""
        type_counts = {}
        total_activities = len(activities)
        
        for activity in activities:
            type_counts[activity.activity_type] = type_counts.get(activity.activity_type, 0) + 1
        
        if total_activities == 0:
            return {}
        
        return {atype: count / total_activities for atype, count in type_counts.items()}
    
    def _calculate_distribution_balance(self, distribution: Dict) -> float:
        """Calculate balance score for a distribution (higher = more balanced)."""
        if not distribution:
            return 0.0
        
        values = list(distribution.values())
        if not values:
            return 0.0
        
        # Calculate entropy-based balance score
        total = sum(values)
        if total == 0:
            return 0.0
        
        # Normalize
        normalized = [v / total for v in values]
        
        # Calculate entropy (higher entropy = more balanced)
        import math
        entropy = -sum(p * math.log2(p) for p in normalized if p > 0)
        
        # Normalize entropy to 0-1 scale
        max_entropy = math.log2(len(values)) if len(values) > 1 else 1
        balance_score = entropy / max_entropy if max_entropy > 0 else 0
        
        return balance_score
    
    def _get_default_balance(self) -> CurriculumBalance:
        """Get default curriculum balance when no weaknesses are identified."""
        return CurriculumBalance(
            weakness_focus_ratio=0.2,  # 20% focus on general improvement
            skill_distribution={skill: 1.0 / len(Skill) for skill in Skill},  # Equal distribution
            language_distribution={"english": 0.5, "japanese": 0.5},  # Equal languages
            new_vs_review_ratio=0.8  # 80% new, 20% review
        )
    
    def _initialize_balance_targets(self) -> Dict[str, float]:
        """Initialize target balance metrics."""
        return {
            "min_skill_balance": 0.6,
            "min_language_balance": 0.4,
            "min_overall_balance": 0.6,
            "max_weakness_focus": 0.6
        }
    
    def _record_curriculum_adjustment(self, user_id: str, base_plan: DailyPlan,
                                    adjusted_plan: DailyPlan, weaknesses: List[WeakArea]) -> None:
        """Record curriculum adjustment for analysis."""
        if user_id not in self.curriculum_adjustments:
            self.curriculum_adjustments[user_id] = []
        
        adjustment_record = {
            "timestamp": datetime.now(),
            "base_plan_id": base_plan.plan_id,
            "adjusted_plan_id": adjusted_plan.plan_id,
            "weaknesses_addressed": len(weaknesses),
            "activities_added": len(adjusted_plan.activities) - len(base_plan.activities),
            "objectives_added": len(adjusted_plan.learning_objectives) - len(base_plan.learning_objectives)
        }
        
        self.curriculum_adjustments[user_id].append(adjustment_record)