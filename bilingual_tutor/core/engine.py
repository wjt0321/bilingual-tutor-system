"""
Core Learning Engine - Central orchestrator for the bilingual tutor system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import uuid

from ..models import (
    UserProfile, StudySession, TimeAllocation, DailyPlan,
    LearningActivity, ActivityResult, LearningEngineInterface,
    SessionStatus, ActivityType, ContentType, Skill, Content
)
from ..content.level_generator import LevelAppropriateContentGenerator
from ..analysis.historical_performance import HistoricalPerformanceIntegrator
from ..analysis.weakness_prioritizer import WeaknessPrioritizer
from ..content.memory_manager import MemoryManager
from ..content.crawler import ContentCrawler
from ..content.filter import ContentFilter
from ..progress.tracker import ProgressTracker
from ..progress.vocabulary_tracker import VocabularyTracker
from ..progress.time_planner import TimePlanner
from ..analysis.weakness_analyzer import WeaknessAnalyzer
from ..analysis.improvement_advisor import ImprovementAdvisor
from ..analysis.review_scheduler import ReviewScheduler
from ..analysis.assessment_engine import AssessmentEngine
from ..interfaces.chinese_interface import ChineseInterface


class CoreLearningEngine(LearningEngineInterface):
    """
    Central orchestrator that coordinates all system components and manages
    the learning workflow.
    """
    
    def __init__(self):
        """Initialize the core learning engine and wire all components."""
        self.active_sessions: dict = {}
        self.component_registry: dict = {}
        
        # Initialize all system components
        self._initialize_components()
        
        # Wire components together
        self._wire_components()
    
    def _initialize_components(self) -> None:
        """Initialize all system components."""
        # Content Management Layer
        self.memory_manager = MemoryManager()
        self.content_crawler = ContentCrawler()
        self.content_filter = ContentFilter()
        self.level_generator = LevelAppropriateContentGenerator()
        
        # Progress Tracking Layer
        self.progress_tracker = ProgressTracker()
        self.vocabulary_tracker = VocabularyTracker()
        self.time_planner = TimePlanner()
        
        # Analysis & Planning Layer
        self.weakness_analyzer = WeaknessAnalyzer()
        self.improvement_advisor = ImprovementAdvisor()
        self.review_scheduler = ReviewScheduler()
        self.assessment_engine = AssessmentEngine()
        self.historical_integrator = HistoricalPerformanceIntegrator()
        self.weakness_prioritizer = WeaknessPrioritizer()
        
        # Interface Layer
        self.chinese_interface = ChineseInterface()
    
    def _wire_components(self) -> None:
        """Wire components together and register them."""
        # Register all components in the registry for easy access
        self.register_component("memory_manager", self.memory_manager)
        self.register_component("content_crawler", self.content_crawler)
        self.register_component("content_filter", self.content_filter)
        self.register_component("level_generator", self.level_generator)
        self.register_component("progress_tracker", self.progress_tracker)
        self.register_component("vocabulary_tracker", self.vocabulary_tracker)
        self.register_component("time_planner", self.time_planner)
        self.register_component("weakness_analyzer", self.weakness_analyzer)
        self.register_component("improvement_advisor", self.improvement_advisor)
        self.register_component("review_scheduler", self.review_scheduler)
        self.register_component("assessment_engine", self.assessment_engine)
        self.register_component("historical_integrator", self.historical_integrator)
        self.register_component("weakness_prioritizer", self.weakness_prioritizer)
        self.register_component("chinese_interface", self.chinese_interface)
        
        # Set up component communication protocols
        self._setup_component_communication()
    
    def _setup_component_communication(self) -> None:
        """Set up communication protocols between components."""
        # Configure content refresh scheduling
        self.content_crawler.schedule_content_refresh(timedelta(hours=24))
        
        # Set up default quality thresholds for content filtering
        # This ensures crawled content meets educational standards
        
        # Initialize system configuration
        self._initialize_system_configuration()
    
    def _initialize_system_configuration(self) -> None:
        """Initialize system-wide configuration settings."""
        # Set default time allocation parameters
        self.default_study_time = 60  # minutes
        self.review_percentage = 0.2  # 20% for review as per requirements
        
        # Set content quality thresholds
        self.min_content_quality = 0.7
        
        # Set performance thresholds for level progression
        self.level_progression_threshold = 0.8
        
        # Configure spaced repetition parameters
        self.review_scheduler.review_threshold = 0.3
        
        print("✓ 双语导师系统初始化完成 - Bilingual Tutor System Initialized")
    
    def start_daily_session(self, user_id: str) -> StudySession:
        """
        Start a new daily study session for the user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            StudySession: Configured study session with activities and timing
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Default to 60 minutes total study time as per requirements
        total_minutes = 60
        
        # Allocate study time according to requirements (20% review)
        time_allocation = self.allocate_study_time(total_minutes)
        
        # Create initial session with basic structure
        session = StudySession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(),
            planned_duration=total_minutes,
            activities=[],  # Will be populated by learning plan generation
            time_allocation=time_allocation,
            status=SessionStatus.PLANNED
        )
        
        # Store active session
        self.active_sessions[user_id] = session
        
        # Display welcome message in Chinese
        welcome_msg = self.chinese_interface.display_message("session_start")
        print(welcome_msg)
        
        return session
        
        return session
    
    def allocate_study_time(self, total_minutes: int) -> TimeAllocation:
        """
        Allocate study time across different activities and languages.
        
        Requirements:
        - 20% of total time must be allocated to review (Requirements 7.7)
        - Remaining time split between English and Japanese
        - Small buffer for breaks
        
        Args:
            total_minutes: Total available study time in minutes
            
        Returns:
            TimeAllocation: Distribution of time across activities
        """
        # Calculate review time (exactly 20% as per requirement 7.7)
        review_minutes = int(total_minutes * 0.2)
        
        # Calculate remaining time for new content
        remaining_minutes = total_minutes - review_minutes
        
        # Allocate small buffer for breaks (5 minutes)
        break_minutes = min(5, remaining_minutes // 12)  # ~8% for breaks
        content_minutes = remaining_minutes - break_minutes
        
        # Split content time equally between English and Japanese by default
        # This can be adjusted based on user preferences and progress in future tasks
        english_minutes = content_minutes // 2
        japanese_minutes = content_minutes - english_minutes
        
        return TimeAllocation(
            total_minutes=total_minutes,
            review_minutes=review_minutes,
            english_minutes=english_minutes,
            japanese_minutes=japanese_minutes,
            break_minutes=break_minutes
        )
    
    def generate_learning_plan(self, user_profile: UserProfile) -> DailyPlan:
        """
        Generate a personalized daily learning plan based on user profile.
        
        Creates a structured learning plan that:
        - Respects time allocation constraints
        - Considers user's current levels (CET-4 English, N5 Japanese)
        - Balances different skill areas
        - Includes review activities
        - Integrates historical performance data for adaptation
        
        Args:
            user_profile: Complete user profile with preferences and goals
            
        Returns:
            DailyPlan: Customized daily learning plan adapted for user's history
        """
        plan_id = str(uuid.uuid4())
        
        # Get time allocation for the user's daily study time
        time_allocation = self.allocate_study_time(user_profile.daily_study_time)
        
        # Generate activities based on time allocation
        activities = []
        learning_objectives = []
        
        # Create review activities (20% of time)
        if time_allocation.review_minutes > 0:
            review_activity = self._create_review_activity(
                user_profile, 
                time_allocation.review_minutes
            )
            activities.append(review_activity)
            learning_objectives.append("复习之前学过的内容以加强记忆")
        
        # Create English learning activities
        if time_allocation.english_minutes > 0:
            english_activity = self._create_language_activity(
                user_profile, 
                "english", 
                user_profile.english_level,
                time_allocation.english_minutes
            )
            activities.append(english_activity)
            learning_objectives.append(f"提高英语水平 ({user_profile.english_level})")
        
        # Create Japanese learning activities  
        if time_allocation.japanese_minutes > 0:
            japanese_activity = self._create_language_activity(
                user_profile,
                "japanese", 
                user_profile.japanese_level,
                time_allocation.japanese_minutes
            )
            activities.append(japanese_activity)
            learning_objectives.append(f"提高日语水平 ({user_profile.japanese_level})")
        
        # Create base plan
        base_plan = DailyPlan(
            plan_id=plan_id,
            user_id=user_profile.user_id,
            date=datetime.now(),
            activities=activities,
            time_allocation=time_allocation,
            learning_objectives=learning_objectives,
            estimated_completion_time=user_profile.daily_study_time
        )
        
        # Apply historical performance integration if available
        progress_tracker = self.get_component("progress_tracker")
        if progress_tracker:
            try:
                # Get user's activity history
                activity_history = getattr(progress_tracker, 'activity_history', {}).get(user_profile.user_id, [])
                
                if activity_history:
                    # Analyze performance patterns
                    performance_patterns = self.historical_integrator.analyze_performance_history(
                        user_profile.user_id, activity_history
                    )
                    
                    # Generate adaptive plan based on patterns
                    adapted_plan = self.historical_integrator.generate_adaptive_plan(
                        user_profile, performance_patterns, base_plan
                    )
                    
                    # Apply weakness prioritization if user has weak areas
                    if user_profile.weak_areas:
                        prioritized_weaknesses, curriculum_balance = self.weakness_prioritizer.prioritize_weaknesses_with_balance(
                            user_profile, user_profile.weak_areas, adapted_plan
                        )
                        
                        # Adjust curriculum for weaknesses while maintaining balance
                        final_plan = self.weakness_prioritizer.adjust_curriculum_for_weaknesses(
                            adapted_plan, prioritized_weaknesses, curriculum_balance
                        )
                        
                        return final_plan
                    
                    return adapted_plan
            except Exception:
                # If historical integration fails, try weakness prioritization only
                pass
        
        # Apply weakness prioritization even without historical data
        if user_profile.weak_areas:
            try:
                prioritized_weaknesses, curriculum_balance = self.weakness_prioritizer.prioritize_weaknesses_with_balance(
                    user_profile, user_profile.weak_areas, base_plan
                )
                
                # Adjust curriculum for weaknesses while maintaining balance
                weakness_focused_plan = self.weakness_prioritizer.adjust_curriculum_for_weaknesses(
                    base_plan, prioritized_weaknesses, curriculum_balance
                )
                
                return weakness_focused_plan
            except Exception:
                # If weakness prioritization fails, return base plan
                pass
        
        return base_plan
    
    def _create_review_activity(self, user_profile: UserProfile, duration: int) -> LearningActivity:
        """Create a review activity for spaced repetition."""
        # Create placeholder content for review
        review_content = Content(
            content_id=str(uuid.uuid4()),
            title="复习活动",
            body="基于遗忘曲线的间隔重复复习",
            language="mixed",  # Review can include both languages
            difficulty_level="adaptive",
            content_type=ContentType.EXERCISE,
            source_url="internal://review",
            quality_score=1.0,
            created_at=datetime.now(),
            tags=["review", "spaced_repetition"]
        )
        
        return LearningActivity(
            activity_id=str(uuid.uuid4()),
            activity_type=ActivityType.REVIEW,
            language="mixed",
            content=review_content,
            estimated_duration=duration,
            difficulty_level="adaptive",
            skills_practiced=[Skill.VOCABULARY, Skill.GRAMMAR]
        )
    
    def _create_language_activity(self, user_profile: UserProfile, language: str, 
                                level: str, duration: int) -> LearningActivity:
        """Create a language-specific learning activity."""
        # Generate level-appropriate content using the new generator
        appropriate_content = self.level_generator.generate_level_appropriate_content(
            user_profile, language, ContentType.ARTICLE
        )
        
        # Use the first appropriate content item, or create placeholder if none available
        if appropriate_content:
            content = appropriate_content[0]
        else:
            # Fallback to placeholder content
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"{language.title()} 学习内容",
                body=f"适合 {level} 水平的{language}学习材料",
                language=language,
                difficulty_level=level,
                content_type=ContentType.ARTICLE,
                source_url="internal://placeholder",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=[language, level, "learning"]
            )
        
        # Determine primary skill to practice based on user's weak areas
        primary_skill = Skill.VOCABULARY  # Default to vocabulary
        if user_profile.weak_areas:
            # Find the most severe weakness for this language
            language_weaknesses = [w for w in user_profile.weak_areas if w.language == language]
            if language_weaknesses:
                most_severe = max(language_weaknesses, key=lambda w: w.severity)
                primary_skill = most_severe.skill
        
        return LearningActivity(
            activity_id=str(uuid.uuid4()),
            activity_type=ActivityType.VOCABULARY if primary_skill == Skill.VOCABULARY else ActivityType.GRAMMAR,
            language=language,
            content=content,
            estimated_duration=duration,
            difficulty_level=level,
            skills_practiced=[primary_skill, Skill.READING]
        )
    
    def execute_learning_activity(self, activity: LearningActivity) -> ActivityResult:
        """
        Execute a learning activity and return results.
        
        Creates activity results with:
        - Performance scoring based on activity type
        - Time tracking
        - Error identification and feedback
        - Completion status
        - Integration with all system components
        
        Args:
            activity: Learning activity to execute
            
        Returns:
            ActivityResult: Results and performance metrics from the activity
        """
        # Simulate activity execution - in a real system this would involve
        # user interaction, content presentation, and response collection
        
        # Generate basic performance metrics
        # For now, we'll simulate reasonable performance scores
        base_score = 0.75  # Default reasonable performance
        
        # Adjust score based on activity type and difficulty
        if activity.activity_type == ActivityType.REVIEW:
            # Review activities typically have higher success rates
            score = min(0.95, base_score + 0.15)
        elif activity.activity_type == ActivityType.VOCABULARY:
            # Vocabulary can vary more widely
            score = base_score
        elif activity.activity_type == ActivityType.GRAMMAR:
            # Grammar might be more challenging
            score = max(0.5, base_score - 0.1)
        else:
            score = base_score
        
        # Generate feedback using Chinese interface and assessment engine
        feedback = self._generate_integrated_feedback(activity, score)
        
        # Simulate some common errors for learning purposes
        errors_made = []
        if score < 0.8:
            errors_made = self._generate_common_errors(activity)
        
        # Create activity result
        result = ActivityResult(
            activity_id=activity.activity_id,
            user_id="",  # Will be set by calling code
            score=score,
            time_spent=activity.estimated_duration,
            errors_made=errors_made,
            completed_at=datetime.now(),
            feedback=feedback
        )
        
        return result
    
    def _generate_integrated_feedback(self, activity: LearningActivity, score: float) -> str:
        """
        Generate comprehensive feedback using integrated components.
        
        Args:
            activity: The completed learning activity
            score: Performance score (0.0 to 1.0)
            
        Returns:
            Integrated feedback message in Chinese
        """
        # Use assessment engine for detailed evaluation
        mock_result = ActivityResult(
            activity_id=activity.activity_id,
            user_id="temp",
            score=score,
            time_spent=activity.estimated_duration,
            errors_made=[],
            completed_at=datetime.now(),
            feedback=""
        )
        
        # Get assessment feedback
        assessment_feedback = self.assessment_engine.generate_feedback("temp", mock_result)
        
        # Use Chinese interface to format the feedback appropriately
        base_feedback = assessment_feedback.get('chinese_explanation', '')
        if not base_feedback:
            base_feedback = self._generate_activity_feedback(activity, score)
        
        # Format using Chinese interface
        formatted_feedback = self.chinese_interface.format_feedback(base_feedback)
        
        return formatted_feedback
    
    def _generate_activity_feedback(self, activity: LearningActivity, score: float) -> str:
        """
        Generate appropriate feedback for an activity based on performance.
        
        Args:
            activity: The completed learning activity
            score: Performance score (0.0 to 1.0)
            
        Returns:
            Feedback message in Chinese
        """
        # Get Chinese interface if available for proper localization
        chinese_interface = self.get_component("chinese_interface")
        
        if score >= 0.9:
            feedback = "优秀！您在这个练习中表现出色。"
        elif score >= 0.8:
            feedback = "很好！您掌握得不错，继续保持。"
        elif score >= 0.7:
            feedback = "良好。还有一些地方需要改进。"
        elif score >= 0.6:
            feedback = "及格。建议多练习相关内容。"
        else:
            feedback = "需要更多练习。不要气馁，继续努力！"
        
        # Add activity-specific feedback
        if activity.activity_type == ActivityType.VOCABULARY:
            if score < 0.7:
                feedback += " 建议使用间隔重复法来加强词汇记忆。"
        elif activity.activity_type == ActivityType.GRAMMAR:
            if score < 0.7:
                feedback += " 语法规则需要更多练习和理解。"
        elif activity.activity_type == ActivityType.READING:
            if score < 0.7:
                feedback += " 多读相似难度的文章来提高理解能力。"
        
        return feedback
    
    def _generate_common_errors(self, activity: LearningActivity) -> List[str]:
        """
        Generate common errors based on activity type for learning purposes.
        
        Args:
            activity: The learning activity
            
        Returns:
            List of common error descriptions
        """
        errors = []
        
        if activity.language == "english":
            if activity.activity_type == ActivityType.VOCABULARY:
                errors = ["词汇拼写错误", "词义理解偏差"]
            elif activity.activity_type == ActivityType.GRAMMAR:
                errors = ["时态使用错误", "语序问题"]
            elif activity.activity_type == ActivityType.READING:
                errors = ["细节理解不准确", "主旨把握不够"]
        
        elif activity.language == "japanese":
            if activity.activity_type == ActivityType.VOCABULARY:
                errors = ["假名书写错误", "汉字读音混淆"]
            elif activity.activity_type == ActivityType.GRAMMAR:
                errors = ["助词使用错误", "敬语形式不当"]
            elif activity.activity_type == ActivityType.READING:
                errors = ["语境理解偏差", "文化背景缺失"]
        
        return errors
    
    def register_component(self, component_name: str, component_instance) -> None:
        """
        Register a system component with the engine.
        
        Args:
            component_name: Name of the component
            component_instance: Instance of the component
        """
        self.component_registry[component_name] = component_instance
    
    def get_component(self, component_name: str):
        """
        Get a registered component by name.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            Component instance or None if not found
        """
        return self.component_registry.get(component_name)
    
    def get_active_session(self, user_id: str) -> Optional[StudySession]:
        """
        Get the active study session for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Active StudySession or None if no active session
        """
        return self.active_sessions.get(user_id)
    
    def update_session_status(self, user_id: str, status: SessionStatus) -> bool:
        """
        Update the status of an active session.
        
        Args:
            user_id: User identifier
            status: New session status
            
        Returns:
            True if session was updated, False if no active session
        """
        if user_id in self.active_sessions:
            self.active_sessions[user_id].status = status
            return True
        return False
    
    def generate_level_appropriate_content(self, user_profile: UserProfile, 
                                         language: str, content_type: ContentType,
                                         topic: Optional[str] = None) -> List[Content]:
        """
        Generate content appropriate for user's proficiency level.
        
        Args:
            user_profile: User's profile with current levels and preferences
            language: Target language (english/japanese)
            content_type: Type of content to generate
            topic: Optional specific topic to focus on
            
        Returns:
            List of Content objects appropriate for user's level
        """
        return self.level_generator.generate_level_appropriate_content(
            user_profile, language, content_type, topic
        )
    
    def assess_content_difficulty(self, content: Content) -> str:
        """
        Assess the difficulty level of existing content.
        
        Args:
            content: Content to assess
            
        Returns:
            Assessed difficulty level string
        """
        return self.level_generator.assess_content_difficulty(content)
    
    def match_content_to_user_level(self, content: Content, user_profile: UserProfile) -> bool:
        """
        Check if content is appropriate for user's current proficiency levels.
        
        Args:
            content: Content to check
            user_profile: User's profile with current levels
            
        Returns:
            True if content is appropriate for user's level
        """
        language = content.language
        if language == "english":
            target_level = user_profile.english_level
        elif language == "japanese":
            target_level = user_profile.japanese_level
        else:
            return True  # Allow content in other languages
        
        # Check vocabulary appropriateness
        vocab_match = self.level_generator._is_vocabulary_appropriate(content, language, target_level)
        
        # Check grammar appropriateness
        grammar_match = self.level_generator.match_grammar_to_level(content, target_level)
        
        return vocab_match and grammar_match
    
    def analyze_user_performance_history(self, user_id: str, activity_history: List[ActivityResult]) -> List:
        """
        Analyze user's performance history to identify patterns and trends.
        
        Args:
            user_id: User identifier
            activity_history: List of completed activities and results
            
        Returns:
            List of identified performance patterns
        """
        return self.historical_integrator.analyze_performance_history(user_id, activity_history)
    
    def get_performance_insights(self, user_id: str) -> List:
        """
        Get performance insights for a user based on their learning history.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of learning insights and recommendations
        """
        return self.historical_integrator.get_performance_insights(user_id)
    
    def predict_activity_performance(self, user_id: str, activity: LearningActivity) -> float:
        """
        Predict likely performance for a given activity based on user's history.
        
        Args:
            user_id: User identifier
            activity: Activity to predict performance for
            
        Returns:
            Predicted performance score (0.0 to 1.0)
        """
        return self.historical_integrator.predict_performance(user_id, activity)
    
    def recognize_learning_patterns(self, user_id: str, activity_history: List[ActivityResult]) -> List:
        """
        Recognize learning patterns from user's complete activity history.
        
        Args:
            user_id: User identifier
            activity_history: Complete activity history
            
        Returns:
            List of recognized learning patterns and insights
        """
        return self.historical_integrator.recognize_learning_patterns(user_id, activity_history)
    
    def prioritize_user_weaknesses(self, user_profile: UserProfile, current_plan: DailyPlan) -> Tuple[List, Dict]:
        """
        Prioritize user's weaknesses while maintaining curriculum balance.
        
        Args:
            user_profile: User's profile with identified weak areas
            current_plan: Current daily learning plan
            
        Returns:
            Tuple of (prioritized weaknesses, curriculum balance recommendation)
        """
        if not user_profile.weak_areas:
            return [], {}
        
        prioritized_weaknesses, curriculum_balance = self.weakness_prioritizer.prioritize_weaknesses_with_balance(
            user_profile, user_profile.weak_areas, current_plan
        )
        
        return prioritized_weaknesses, curriculum_balance
    
    def get_weakness_focus_recommendations(self, user_profile: UserProfile) -> List[str]:
        """
        Get specific recommendations for focusing on user's weaknesses.
        
        Args:
            user_profile: User's profile with weak areas
            
        Returns:
            List of specific weakness focus recommendations
        """
        return self.weakness_prioritizer.get_weakness_focus_recommendations(
            user_profile, user_profile.weak_areas
        )
    
    def calculate_curriculum_balance(self, plan: DailyPlan) -> Dict[str, float]:
        """
        Calculate balance metrics for a learning plan.
        
        Args:
            plan: Daily learning plan to analyze
            
        Returns:
            Dictionary of balance metrics
        """
        return self.weakness_prioritizer.calculate_balance_metrics(plan)
    
    def process_activity_completion(self, user_id: str, activity: LearningActivity, result: ActivityResult) -> None:
        """
        Process activity completion through all integrated components.
        
        Args:
            user_id: User identifier
            activity: Completed activity
            result: Activity result
        """
        # Set user ID in result
        result.user_id = user_id
        
        # Record performance in progress tracker
        self.progress_tracker.record_performance(user_id, activity, result)
        
        # Process vocabulary learning if applicable
        self.vocabulary_tracker.process_activity_result(user_id, activity, result)
        
        # Record content as learned in memory manager
        self.memory_manager.record_learned_content(user_id, activity.content)
        
        # Record activity result for weakness analysis
        self.weakness_analyzer.record_activity_result(user_id, result)
        
        # Schedule content for review based on performance
        next_review = self.review_scheduler.schedule_review(activity.content, result.score)
        self.memory_manager.mark_for_review(user_id, activity.content, 
                                          next_review - datetime.now())
        
        # Evaluate performance using assessment engine
        assessment = self.assessment_engine.evaluate_performance(user_id, result)
        
        # Check for level advancement
        self._check_level_advancement(user_id, activity.language)
        
        # Update weakness analysis
        self._update_weakness_analysis(user_id)
    
    def _check_level_advancement(self, user_id: str, language: str) -> None:
        """Check and process level advancement."""
        if self.vocabulary_tracker.suggest_level_advancement(user_id, language):
            new_level = self.vocabulary_tracker.advance_level(user_id, language)
            
            # Display advancement notification in Chinese
            advancement_msg = self.chinese_interface.display_message(
                f"level_up_{language}", 
                {"level": new_level}
            )
            print(advancement_msg)
    
    def _update_weakness_analysis(self, user_id: str) -> None:
        """Update weakness analysis and generate improvement recommendations."""
        # Analyze recent errors for weaknesses
        recent_weaknesses = self.weakness_analyzer.analyze_error_patterns(
            user_id, timedelta(days=7)
        )
        
        # Generate improvement plans for identified weaknesses
        for weakness in recent_weaknesses:
            improvement_plan = self.improvement_advisor.generate_improvement_plan(weakness)
            # Store improvement plan for future reference
    
    def get_comprehensive_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status for a user across all system components.
        
        Args:
            user_id: User identifier
            
        Returns:
            Comprehensive user status dictionary
        """
        status = {
            'progress_metrics': {},
            'vocabulary_progress': {},
            'weakness_analysis': {},
            'review_schedule': {},
            'assessment_data': {},
            'content_history': {}
        }
        
        # Get progress metrics
        status['progress_metrics'] = {
            'english': self.progress_tracker.get_current_metrics(user_id),
            'japanese': self.progress_tracker.get_current_metrics(user_id)
        }
        
        # Get vocabulary progress
        status['vocabulary_progress'] = {
            'english': self.vocabulary_tracker.get_vocabulary_progress(user_id, 'english'),
            'japanese': self.vocabulary_tracker.get_vocabulary_progress(user_id, 'japanese')
        }
        
        # Get weakness analysis
        english_weaknesses = self.weakness_analyzer.identify_skill_gaps(user_id, 'english')
        japanese_weaknesses = self.weakness_analyzer.identify_skill_gaps(user_id, 'japanese')
        status['weakness_analysis'] = {
            'english': english_weaknesses,
            'japanese': japanese_weaknesses
        }
        
        # Get review statistics
        status['review_schedule'] = self.review_scheduler.get_review_statistics()
        
        # Get assessment analytics
        status['assessment_data'] = self.assessment_engine.get_learning_analytics(
            user_id, timedelta(days=30)
        )
        
        # Get content history
        status['content_history'] = {
            'total_content_seen': self.memory_manager.get_content_history_count(user_id)
        }
        
        return status
    
    def generate_adaptive_content(self, user_id: str, language: str, content_type: ContentType) -> List[Content]:
        """
        Generate adaptive content using integrated content management system.
        
        Args:
            user_id: User identifier
            language: Target language
            content_type: Type of content to generate
            
        Returns:
            List of adaptive content
        """
        # Get user's current level and preferences (simplified)
        user_level = "CET-4" if language == "english" else "N5"
        
        # Search for content using crawler
        crawled_content = self.content_crawler.search_english_content(user_level, "general") if language == "english" else self.content_crawler.search_japanese_content(user_level, "general")
        
        # Filter content for quality and appropriateness
        filtered_content = self.content_filter.filter_content_batch(crawled_content, user_level)
        
        # Remove content already seen recently
        unseen_content = []
        for content in filtered_content:
            if not self.memory_manager.check_content_seen_within_window(
                user_id, content, timedelta(days=7)
            ):
                unseen_content.append(content)
        
        return unseen_content[:5]  # Return top 5 unseen content items
    
    def optimize_learning_plan(self, user_id: str, user_profile: UserProfile) -> DailyPlan:
        """
        Generate optimized learning plan using all integrated components.
        
        Args:
            user_id: User identifier
            user_profile: User's complete profile
            
        Returns:
            Optimized daily learning plan
        """
        # Get current progress metrics
        current_progress = {
            'english': self.progress_tracker.get_current_metrics(user_id),
            'japanese': self.progress_tracker.get_current_metrics(user_id)
        }
        
        # Calculate optimal time allocation using time planner
        daily_volume = self.time_planner.calculate_daily_volume(user_profile, current_progress)
        
        # Generate base plan
        base_plan = self.generate_learning_plan(user_profile)
        
        # Optimize plan based on weakness analysis
        optimized_plan = self.adjust_plan_for_weaknesses(base_plan, user_profile)
        
        # Add review activities based on spaced repetition
        due_reviews = self.review_scheduler.get_due_reviews()
        if due_reviews:
            # Add review activities to the plan
            review_activity = self._create_review_activity(user_profile, 
                                                         optimized_plan.time_allocation.review_minutes)
            optimized_plan.activities.insert(0, review_activity)  # Prioritize reviews
        
        return optimized_plan
    
    def adjust_plan_for_weaknesses(self, base_plan: DailyPlan, user_profile: UserProfile) -> DailyPlan:
        """
        Adjust a learning plan to focus on user's weaknesses while maintaining balance.
        
        Args:
            base_plan: Original learning plan
            user_profile: User's profile with weak areas
            
        Returns:
            Adjusted plan with weakness focus and curriculum balance
        """
        if not user_profile.weak_areas:
            return base_plan
        
        prioritized_weaknesses, curriculum_balance = self.weakness_prioritizer.prioritize_weaknesses_with_balance(
            user_profile, user_profile.weak_areas, base_plan
        )
        
        return self.weakness_prioritizer.adjust_curriculum_for_weaknesses(
            base_plan, prioritized_weaknesses, curriculum_balance
        )
    
    def complete_session(self, user_id: str) -> Optional[StudySession]:
        """
        Complete and remove an active session.
        
        Args:
            user_id: User identifier
            
        Returns:
            Completed StudySession or None if no active session
        """
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session.status = SessionStatus.COMPLETED
            del self.active_sessions[user_id]
            return session
        return None
    
    def execute_session_activities(self, user_id: str) -> List[ActivityResult]:
        """
        Execute all activities in the user's active session.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of ActivityResult objects for all completed activities
        """
        session = self.get_active_session(user_id)
        if not session:
            return []
        
        results = []
        for activity in session.activities:
            result = self.execute_learning_activity(activity)
            result.user_id = user_id  # Set the user ID
            results.append(result)
        
        return results
    
    def add_activity_to_session(self, user_id: str, activity: LearningActivity) -> bool:
        """
        Add an activity to the user's active session.
        
        Args:
            user_id: User identifier
            activity: Activity to add
            
        Returns:
            True if activity was added, False if no active session
        """
        if user_id in self.active_sessions:
            self.active_sessions[user_id].activities.append(activity)
            return True
        return False