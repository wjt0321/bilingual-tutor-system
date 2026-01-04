"""
Learning Analytics Enhancement - Advanced learning pattern analysis and prediction.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict

from ..models import Skill, ActivityType, SessionStatus


class StudyTimeSlot(Enum):
    """Best study time slots."""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


@dataclass
class StudyPattern:
    """User's study pattern data."""
    user_id: str
    best_time_slot: StudyTimeSlot
    best_day_of_week: str
    average_study_duration: float
    consistency_score: float
    peak_performance_hours: List[int]
    preferred_activity_types: List[ActivityType]


@dataclass
class SkillTrajectory:
    """Skill development trajectory."""
    skill: Skill
    language: str
    initial_level: float
    current_level: float
    predicted_level: float
    trajectory_points: List[Tuple[datetime, float]]
    growth_rate: float
    confidence_level: float


@dataclass
class LearningBottleneck:
    """Identified learning bottleneck."""
    bottleneck_id: str
    skill: Skill
    language: str
    description: str
    severity: float
    affected_duration: timedelta
    breakthrough_suggestions: List[str]
    identified_at: datetime


@dataclass
class LearningMilestone:
    """Predicted learning milestone."""
    milestone_id: str
    description: str
    target_level: str
    predicted_date: datetime
    confidence: float
    required_actions: List[str]
    progress: float


@dataclass
class AnalyticsReport:
    """Comprehensive learning analytics report."""
    user_id: str
    report_date: datetime
    study_pattern: StudyPattern
    skill_trajectories: List[SkillTrajectory]
    bottlenecks: List[LearningBottleneck]
    milestones: List[LearningMilestone]
    recommendations: List[str]
    summary: str


class LearningAnalyticsEnhancer:
    """
    Enhanced learning analytics with pattern analysis,
    predictions, and bottleneck identification.
    """
    
    def __init__(self):
        """Initialize analytics enhancer."""
        self.study_history: Dict[str, List[Dict]] = defaultdict(list)
        self.skill_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
    
    def add_study_session(self, user_id: str, session_data: Dict):
        """
        Add a study session to history.
        
        Args:
            user_id: User identifier
            session_data: Session data including duration, activities, performance, etc.
        """
        session_data['timestamp'] = datetime.now().isoformat()
        self.study_history[user_id].append(session_data)
    
    def add_skill_measurement(self, user_id: str, skill: Skill, 
                         language: str, level: float):
        """
        Add a skill measurement point.
        
        Args:
            user_id: User identifier
            skill: Skill being measured
            language: Language being learned
            level: Current skill level (0.0 to 1.0)
        """
        key = f"{user_id}_{skill.value}_{language}"
        self.skill_history[key].append((datetime.now(), level))
    
    def analyze_study_pattern(self, user_id: str) -> StudyPattern:
        """
        Analyze user's study patterns to find optimal times.
        
        Args:
            user_id: User identifier
            
        Returns:
            StudyPattern with optimal time slot and day analysis
        """
        sessions = self.study_history.get(user_id, [])
        
        if not sessions:
            return self._default_study_pattern(user_id)
        
        # Analyze by time of day
        time_slot_performance = defaultdict(list)
        for session in sessions:
            if 'start_time' not in session:
                continue
            
            start_time = datetime.fromisoformat(session['start_time'])
            hour = start_time.hour
            performance = session.get('performance_score', 0.5)
            
            time_slot = self._categorize_time_slot(hour)
            time_slot_performance[time_slot].append(performance)
        
        # Find best time slot
        best_time_slot = None
        best_avg_performance = 0.0
        
        for slot, performances in time_slot_performance.items():
            avg_performance = sum(performances) / len(performances)
            if avg_performance > best_avg_performance:
                best_avg_performance = avg_performance
                best_time_slot = slot
        
        # Analyze by day of week
        day_performance = defaultdict(list)
        for session in sessions:
            if 'start_time' not in session:
                continue
            
            start_time = datetime.fromisoformat(session['start_time'])
            day = start_time.strftime('%A')
            performance = session.get('performance_score', 0.5)
            day_performance[day].append(performance)
        
        # Find best day
        best_day = None
        best_day_avg = 0.0
        for day, performances in day_performance.items():
            avg_performance = sum(performances) / len(performances)
            if avg_performance > best_day_avg:
                best_day_avg = avg_performance
                best_day = day
        
        # Calculate average duration
        durations = [s.get('duration_minutes', 0) for s in sessions if 'duration_minutes' in s]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate consistency (how regular the study is)
        consistency = self._calculate_consistency(sessions)
        
        # Find peak performance hours
        hourly_performance = defaultdict(list)
        for session in sessions:
            if 'start_time' not in session:
                continue
            
            start_time = datetime.fromisoformat(session['start_time'])
            hour = start_time.hour
            performance = session.get('performance_score', 0.5)
            hourly_performance[hour].append(performance)
        
        peak_hours = []
        for hour, performances in hourly_performance.items():
            avg_perf = sum(performances) / len(performances)
            if avg_perf >= 0.7:  # High performance threshold
                peak_hours.append(hour)
        
        # Find preferred activity types
        activity_counts = defaultdict(int)
        for session in sessions:
            activities = session.get('activities', [])
            for activity in activities:
                activity_counts[activity] += 1
        
        preferred_activities = [
            ActivityType(act) for act, count in activity_counts.items()
            if count > 0
        ]
        
        return StudyPattern(
            user_id=user_id,
            best_time_slot=best_time_slot or StudyTimeSlot.MORNING,
            best_day_of_week=best_day or "Monday",
            average_study_duration=avg_duration,
            consistency_score=consistency,
            peak_performance_hours=peak_hours,
            preferred_activity_types=preferred_activities
        )
    
    def predict_skill_trajectory(self, user_id: str, skill: Skill, 
                           language: str) -> SkillTrajectory:
        """
        Predict skill development trajectory.
        
        Args:
            user_id: User identifier
            skill: Skill to analyze
            language: Target language
            
        Returns:
            SkillTrajectory with predictions and growth rate
        """
        key = f"{user_id}_{skill.value}_{language}"
        history = self.skill_history.get(key, [])
        
        if len(history) < 2:
            return self._default_skill_trajectory(user_id, skill, language)
        
        # Sort history by date
        history.sort(key=lambda x: x[0])
        
        # Extract data points
        dates = [point[0] for point in history]
        levels = [point[1] for point in history]
        
        # Calculate initial and current levels
        initial_level = levels[0]
        current_level = levels[-1]
        
        # Calculate growth rate (linear regression simplified)
        time_span_days = (dates[-1] - dates[0]).days
        if time_span_days > 0:
            growth_rate = (levels[-1] - levels[0]) / time_span_days
        else:
            growth_rate = 0.0
        
        # Predict future level (30 days ahead)
        predicted_level = current_level + (growth_rate * 30)
        predicted_level = max(0.0, min(1.0, predicted_level))
        
        # Calculate confidence based on data points
        confidence_level = min(1.0, len(history) / 10.0)
        
        return SkillTrajectory(
            skill=skill,
            language=language,
            initial_level=initial_level,
            current_level=current_level,
            predicted_level=predicted_level,
            trajectory_points=list(zip(dates, levels)),
            growth_rate=growth_rate,
            confidence_level=confidence_level
        )
    
    def identify_bottlenecks(self, user_id: str) -> List[LearningBottleneck]:
        """
        Identify learning bottlenecks and provide breakthrough suggestions.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of identified bottlenecks with solutions
        """
        bottlenecks = []
        sessions = self.study_history.get(user_id, [])
        
        if not sessions:
            return bottlenecks
        
        # Analyze skill performance trends
        skill_performance = defaultdict(list)
        for session in sessions:
            activities = session.get('activities', [])
            performance = session.get('performance_score', 0.5)
            
            # Map activity types to skills
            for activity in activities:
                skill = self._activity_to_skill(activity)
                skill_performance[skill].append(performance)
        
        # Identify stagnating skills
        for skill, performances in skill_performance.items():
            if len(performances) < 3:
                continue
            
            recent_performance = performances[-5:] if len(performances) >= 5 else performances
            avg_recent = sum(recent_performance) / len(recent_performance)
            
            # Check for stagnation (low or declining performance)
            if avg_recent < 0.5:
                bottleneck_id = f"bottleneck_{skill.value}_{datetime.now().timestamp()}"
                
                bottleneck = LearningBottleneck(
                    bottleneck_id=bottleneck_id,
                    skill=skill,
                    language=self._infer_language_from_sessions(sessions),
                    description=f"Performance in {skill.value} has been below optimal levels",
                    severity=1.0 - avg_recent,
                    affected_duration=timedelta(days=7),
                    breakthrough_suggestions=self._generate_breakthrough_suggestions(skill, avg_recent),
                    identified_at=datetime.now()
                )
                bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def predict_milestones(self, user_id: str, 
                         target_level: str) -> List[LearningMilestone]:
        """
        Predict learning milestones based on progress.
        
        Args:
            user_id: User identifier
            target_level: Target proficiency level
            
        Returns:
            List of predicted milestones
        """
        milestones = []
        sessions = self.study_history.get(user_id, [])
        
        if not sessions:
            # Generate default milestones even without data
            today = datetime.now()
            default_days = 90  # Default estimate
            
            return [
                LearningMilestone(
                    milestone_id=f"milestone_25_{user_id}",
                    description=f"Reach 25% progress toward {target_level}",
                    target_level=target_level,
                    predicted_date=today + timedelta(days=default_days * 0.25),
                    confidence=0.5,
                    required_actions=["Start regular study sessions"],
                    progress=0.0
                ),
                LearningMilestone(
                    milestone_id=f"milestone_50_{user_id}",
                    description=f"Reach 50% progress toward {target_level}",
                    target_level=target_level,
                    predicted_date=today + timedelta(days=default_days * 0.5),
                    confidence=0.5,
                    required_actions=["Maintain consistent practice"],
                    progress=0.0
                ),
                LearningMilestone(
                    milestone_id=f"milestone_75_{user_id}",
                    description=f"Reach 75% progress toward {target_level}",
                    target_level=target_level,
                    predicted_date=today + timedelta(days=default_days * 0.75),
                    confidence=0.5,
                    required_actions=["Complete learning objectives"],
                    progress=0.0
                ),
                LearningMilestone(
                    milestone_id=f"milestone_final_{user_id}",
                    description=f"Achieve target level: {target_level}",
                    target_level=target_level,
                    predicted_date=today + timedelta(days=default_days),
                    confidence=0.5,
                    required_actions=["Master all required skills"],
                    progress=0.0
                )
            ]
        
        # Calculate overall progress rate
        durations = [s.get('duration_minutes', 0) for s in sessions if 'duration_minutes' in s]
        total_study_time = sum(durations)
        
        # Estimate time to reach target (simplified model)
        # Assume 100 hours needed per level progression
        current_progress_estimate = total_study_time / 6000.0  # Normalize to 0-1
        remaining_progress = 1.0 - current_progress_estimate
        
        # Estimate time remaining (assuming 60 min/day average)
        avg_daily_minutes = sum(durations) / len(durations) if durations else 60
        days_remaining = (remaining_progress * 6000) / avg_daily_minutes
        
        # Create milestones
        today = datetime.now()
        
        # Milestone 1: 25% progress
        if current_progress_estimate < 0.25:
            milestone_date = today + timedelta(days=days_remaining * 0.25)
            milestones.append(LearningMilestone(
                milestone_id=f"milestone_25_{user_id}",
                description=f"Reach 25% progress toward {target_level}",
                target_level=target_level,
                predicted_date=milestone_date,
                confidence=0.8,
                required_actions=[
                    "Maintain consistent daily study sessions",
                    "Focus on vocabulary building",
                    "Practice listening comprehension"
                ],
                progress=current_progress_estimate * 100
            ))
        
        # Milestone 2: 50% progress
        if current_progress_estimate < 0.5:
            milestone_date = today + timedelta(days=days_remaining * 0.5)
            milestones.append(LearningMilestone(
                milestone_id=f"milestone_50_{user_id}",
                description=f"Reach 50% progress toward {target_level}",
                target_level=target_level,
                predicted_date=milestone_date,
                confidence=0.75,
                required_actions=[
                    "Complete all grammar exercises",
                    "Read at least 5 articles per week",
                    "Participate in conversation practice"
                ],
                progress=current_progress_estimate * 100
            ))
        
        # Milestone 3: 75% progress
        if current_progress_estimate < 0.75:
            milestone_date = today + timedelta(days=days_remaining * 0.75)
            milestones.append(LearningMilestone(
                milestone_id=f"milestone_75_{user_id}",
                description=f"Reach 75% progress toward {target_level}",
                target_level=target_level,
                predicted_date=milestone_date,
                confidence=0.7,
                required_actions=[
                    "Master intermediate vocabulary",
                    "Complete all review sessions",
                    "Achieve 80% accuracy in practice tests"
                ],
                progress=current_progress_estimate * 100
            ))
        
        # Final milestone: Target level
        milestone_date = today + timedelta(days=days_remaining)
        milestones.append(LearningMilestone(
            milestone_id=f"milestone_final_{user_id}",
            description=f"Achieve target level: {target_level}",
            target_level=target_level,
            predicted_date=milestone_date,
            confidence=0.65,
            required_actions=[
                "Complete all learning objectives",
                "Pass comprehensive assessment",
                "Maintain 90% accuracy in tests"
            ],
            progress=current_progress_estimate * 100
        ))
        
        return milestones
    
    def generate_analytics_report(self, user_id: str, 
                               target_level: str) -> AnalyticsReport:
        """
        Generate comprehensive analytics report.
        
        Args:
            user_id: User identifier
            target_level: Target proficiency level
            
        Returns:
            Complete AnalyticsReport with all analyses
        """
        # Analyze study pattern
        study_pattern = self.analyze_study_pattern(user_id)
        
        # Analyze skill trajectories for major skills
        skill_trajectories = []
        major_skills = [Skill.VOCABULARY, Skill.GRAMMAR, Skill.READING, Skill.LISTENING]
        languages = ['english', 'japanese']
        
        for skill in major_skills:
            for language in languages:
                trajectory = self.predict_skill_trajectory(user_id, skill, language)
                skill_trajectories.append(trajectory)
        
        # Identify bottlenecks
        bottlenecks = self.identify_bottlenecks(user_id)
        
        # Predict milestones
        milestones = self.predict_milestones(user_id, target_level)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            study_pattern, bottlenecks, skill_trajectories
        )
        
        # Generate summary
        summary = self._generate_summary(
            study_pattern, bottlenecks, milestones
        )
        
        return AnalyticsReport(
            user_id=user_id,
            report_date=datetime.now(),
            study_pattern=study_pattern,
            skill_trajectories=skill_trajectories,
            bottlenecks=bottlenecks,
            milestones=milestones,
            recommendations=recommendations,
            summary=summary
        )
    
    def export_data(self, user_id: str, format: str = 'json') -> str:
        """
        Export learning data for personal analysis.
        
        Args:
            user_id: User identifier
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        sessions = self.study_history.get(user_id, [])
        
        if format == 'json':
            export_data = {
                'user_id': user_id,
                'export_date': datetime.now().isoformat(),
                'study_sessions': sessions,
                'skill_history': dict(self.skill_history)
            }
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        
        elif format == 'csv':
            # CSV format for study sessions
            lines = ['timestamp,duration_minutes,performance_score,activities']
            for session in sessions:
                timestamp = session.get('timestamp', '')
                duration = session.get('duration_minutes', 0)
                performance = session.get('performance_score', 0.0)
                activities = ','.join(session.get('activities', []))
                lines.append(f"{timestamp},{duration},{performance},{activities}")
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _categorize_time_slot(self, hour: int) -> StudyTimeSlot:
        """Categorize hour into time slot."""
        if 5 <= hour < 12:
            return StudyTimeSlot.MORNING
        elif 12 <= hour < 17:
            return StudyTimeSlot.AFTERNOON
        elif 17 <= hour < 21:
            return StudyTimeSlot.EVENING
        else:
            return StudyTimeSlot.NIGHT
    
    def _calculate_consistency(self, sessions: List[Dict]) -> float:
        """Calculate study consistency score."""
        if len(sessions) < 2:
            return 0.5
        
        # Group by date
        dates = set()
        for session in sessions:
            if 'start_time' in session:
                start_time = datetime.fromisoformat(session['start_time'])
                dates.add(start_time.date())
        
        # Calculate consistency based on regularity
        total_days = 30  # Consider last 30 days
        study_days = len(dates)
        consistency = study_days / total_days
        
        return consistency
    
    def _activity_to_skill(self, activity: ActivityType) -> Skill:
        """Map activity type to skill."""
        mapping = {
            ActivityType.VOCABULARY: Skill.VOCABULARY,
            ActivityType.GRAMMAR: Skill.GRAMMAR,
            ActivityType.READING: Skill.READING,
            ActivityType.LISTENING: Skill.LISTENING,
            ActivityType.SPEAKING: Skill.SPEAKING,
            ActivityType.WRITING: Skill.WRITING,
            ActivityType.REVIEW: Skill.COMPREHENSION
        }
        # Handle string values from ActivityType.value
        if isinstance(activity, str):
            activity_lower = activity.lower()
            if 'vocabulary' in activity_lower:
                return Skill.VOCABULARY
            elif 'grammar' in activity_lower:
                return Skill.GRAMMAR
            elif 'reading' in activity_lower:
                return Skill.READING
            elif 'listening' in activity_lower:
                return Skill.LISTENING
            elif 'speaking' in activity_lower:
                return Skill.SPEAKING
            elif 'writing' in activity_lower:
                return Skill.WRITING
            elif 'review' in activity_lower:
                return Skill.COMPREHENSION
        return mapping.get(activity, Skill.COMPREHENSION)
    
    def _infer_language_from_sessions(self, sessions: List[Dict]) -> str:
        """Infer primary language from sessions."""
        if not sessions:
            return 'english'
        
        # Count activities by language (if specified)
        english_count = 0
        japanese_count = 0
        
        for session in sessions:
            if 'language' in session:
                if session['language'] == 'english':
                    english_count += 1
                elif session['language'] == 'japanese':
                    japanese_count += 1
        
        return 'english' if english_count >= japanese_count else 'japanese'
    
    def _generate_breakthrough_suggestions(self, skill: Skill, 
                                       performance: float) -> List[str]:
        """Generate suggestions for overcoming bottlenecks."""
        suggestions = []
        
        if performance < 0.4:
            suggestions.append(f"Revisit {skill.value} fundamentals")
            suggestions.append("Practice with easier materials first")
            suggestions.append("Consider additional review sessions")
        elif performance < 0.6:
            suggestions.append(f"Increase {skill.value} practice frequency")
            suggestions.append("Try different learning approaches")
            suggestions.append("Use spaced repetition for better retention")
        else:
            suggestions.append(f"Focus on advanced {skill.value} techniques")
            suggestions.append("Challenge yourself with complex materials")
        
        return suggestions
    
    def _generate_recommendations(self, pattern: StudyPattern,
                               bottlenecks: List[LearningBottleneck],
                               trajectories: List[SkillTrajectory]) -> List[str]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Time-based recommendations
        if pattern.best_time_slot == StudyTimeSlot.MORNING:
            recommendations.append("Morning study is most effective for you - schedule important sessions early")
        elif pattern.best_time_slot == StudyTimeSlot.EVENING:
            recommendations.append("Evening study works best - use this time for complex topics")
        
        # Consistency recommendations
        if pattern.consistency_score < 0.5:
            recommendations.append("Try to study more consistently - regular practice improves retention")
        
        # Bottleneck recommendations
        if bottlenecks:
            high_severity_bottlenecks = [
                b for b in bottlenecks if b.severity > 0.5
            ]
            if high_severity_bottlenecks:
                recommendations.append("Focus on addressing identified bottlenecks for faster progress")
        
        # Skill trajectory recommendations
        low_growth_skills = [
            t.skill.value for t in trajectories
            if t.growth_rate < 0.001
        ]
        if low_growth_skills:
            recommendations.append(f"Consider adjusting approach for: {', '.join(low_growth_skills)}")
        
        return recommendations
    
    def _generate_summary(self, pattern: StudyPattern,
                        bottlenecks: List[LearningBottleneck],
                        milestones: List[LearningMilestone]) -> str:
        """Generate analytics summary."""
        summary_parts = [
            f"Best study time: {pattern.best_time_slot.value} on {pattern.best_day_of_week}",
            f"Average session duration: {pattern.average_study_duration:.1f} minutes",
            f"Study consistency: {pattern.consistency_score * 100:.1f}%"
        ]
        
        if bottlenecks:
            summary_parts.append(f"Identified {len(bottlenecks)} bottleneck(s) to address")
        
        if milestones:
            next_milestone = min(milestones, key=lambda m: m.predicted_date)
            days_to_milestone = (next_milestone.predicted_date - datetime.now()).days
            summary_parts.append(
                f"Next milestone: {next_milestone.description} in {days_to_milestone} days"
            )
        
        return '. '.join(summary_parts)
    
    def _default_study_pattern(self, user_id: str) -> StudyPattern:
        """Create default study pattern when no data available."""
        return StudyPattern(
            user_id=user_id,
            best_time_slot=StudyTimeSlot.MORNING,
            best_day_of_week="Monday",
            average_study_duration=60.0,
            consistency_score=0.5,
            peak_performance_hours=[9, 10, 11],
            preferred_activity_types=[
                ActivityType.VOCABULARY, ActivityType.GRAMMAR
            ]
        )
    
    def _default_skill_trajectory(self, user_id: str, 
                              skill: Skill, language: str) -> SkillTrajectory:
        """Create default skill trajectory when no data available."""
        return SkillTrajectory(
            skill=skill,
            language=language,
            initial_level=0.3,
            current_level=0.3,
            predicted_level=0.35,
            trajectory_points=[(datetime.now(), 0.3)],
            growth_rate=0.001,
            confidence_level=0.5
        )
