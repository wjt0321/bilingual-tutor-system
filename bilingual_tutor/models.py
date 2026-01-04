"""
Core data models for the bilingual tutor system.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod


class ActivityType(Enum):
    """Types of learning activities."""
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"
    READING = "reading"
    LISTENING = "listening"
    SPEAKING = "speaking"
    WRITING = "writing"
    REVIEW = "review"


class ContentType(Enum):
    """Types of learning content."""
    ARTICLE = "article"
    NEWS = "news"
    DIALOGUE = "dialogue"
    EXERCISE = "exercise"
    CULTURAL = "cultural"
    AUDIO = "audio"
    VIDEO = "video"


class Skill(Enum):
    """Language learning skills."""
    VOCABULARY = "vocabulary"
    GRAMMAR = "grammar"
    READING = "reading"
    LISTENING = "listening"
    SPEAKING = "speaking"
    WRITING = "writing"
    PRONUNCIATION = "pronunciation"
    COMPREHENSION = "comprehension"


class SessionStatus(Enum):
    """Study session status."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MasteryLevel(Enum):
    """Content mastery levels."""
    NOT_LEARNED = "not_learned"
    LEARNING = "learning"
    PRACTICED = "practiced"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Goals:
    """User learning goals and objectives."""
    target_english_level: str
    target_japanese_level: str
    target_completion_date: datetime
    priority_skills: List[Skill]
    custom_objectives: List[str]


@dataclass
class Preferences:
    """User learning preferences."""
    preferred_study_times: List[str]
    content_preferences: List[ContentType]
    difficulty_preference: str
    language_balance: Dict[str, float]  # english: 0.5, japanese: 0.5


@dataclass
class WeakArea:
    """Identified weakness in user's learning."""
    area_id: str
    skill: Skill
    language: str
    severity: float  # 0.0 to 1.0
    error_patterns: List[str]
    improvement_suggestions: List[str]
    identified_at: datetime


@dataclass
class UserProfile:
    """Complete user profile with learning status and preferences."""
    user_id: str
    english_level: str  # CET-4, CET-5, CET-6, etc.
    japanese_level: str  # N5, N4, N3, N2, N1
    daily_study_time: int  # minutes
    target_goals: Goals
    learning_preferences: Preferences
    weak_areas: List[WeakArea]
    created_at: datetime
    updated_at: datetime


@dataclass
class TimeAllocation:
    """Time distribution for study sessions."""
    total_minutes: int
    review_minutes: int  # 20% of total
    english_minutes: int
    japanese_minutes: int
    break_minutes: int


@dataclass
class Content:
    """Learning content item."""
    content_id: str
    title: str
    body: str
    language: str
    difficulty_level: str
    content_type: ContentType
    source_url: str
    quality_score: float
    created_at: datetime
    tags: List[str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LearningActivity:
    """Individual learning activity within a session."""
    activity_id: str
    activity_type: ActivityType
    language: str  # english, japanese
    content: Content
    estimated_duration: int
    difficulty_level: str
    skills_practiced: List[Skill]


@dataclass
class StudySession:
    """Complete study session with activities and timing."""
    session_id: str
    user_id: str
    start_time: datetime
    planned_duration: int  # minutes
    activities: List[LearningActivity]
    time_allocation: TimeAllocation
    status: SessionStatus


@dataclass
class ProgressMetrics:
    """User progress metrics across all skills."""
    user_id: str
    language: str
    vocabulary_mastered: int
    grammar_points_learned: int
    reading_comprehension_score: float
    listening_comprehension_score: float
    speaking_fluency_score: float
    writing_proficiency_score: float
    overall_progress: float
    last_updated: datetime


@dataclass
class ActivityResult:
    """Result of a completed learning activity."""
    activity_id: str
    user_id: str
    score: float
    time_spent: int  # minutes
    errors_made: List[str]
    completed_at: datetime
    feedback: str


@dataclass
class QualityScore:
    """Content quality assessment."""
    educational_value: float
    difficulty_match: float
    source_reliability: float
    content_freshness: float
    overall_score: float


@dataclass
class DailyPlan:
    """Generated daily learning plan."""
    plan_id: str
    user_id: str
    date: datetime
    activities: List[LearningActivity]
    time_allocation: TimeAllocation
    learning_objectives: List[str]
    estimated_completion_time: int


@dataclass
class ProgressReport:
    """Progress report for a specific period."""
    user_id: str
    period_start: datetime
    period_end: datetime
    activities_completed: int
    time_studied: int  # minutes
    skills_improved: List[Skill]
    weaknesses_addressed: List[WeakArea]
    achievements: List[str]
    recommendations: List[str]


# Base interfaces for major components
class LearningEngineInterface(ABC):
    """Interface for the core learning engine."""
    
    @abstractmethod
    def start_daily_session(self, user_id: str) -> StudySession:
        """Start a new daily study session."""
        pass
    
    @abstractmethod
    def allocate_study_time(self, total_minutes: int) -> TimeAllocation:
        """Allocate study time across activities."""
        pass
    
    @abstractmethod
    def generate_learning_plan(self, user_profile: UserProfile) -> DailyPlan:
        """Generate a personalized daily learning plan."""
        pass
    
    @abstractmethod
    def execute_learning_activity(self, activity: LearningActivity) -> ActivityResult:
        """Execute a learning activity and return results."""
        pass


class ContentCrawlerInterface(ABC):
    """Interface for content crawling and discovery."""
    
    @abstractmethod
    def search_english_content(self, level: str, topic: str) -> List[Content]:
        """Search for English learning content."""
        pass
    
    @abstractmethod
    def search_japanese_content(self, jlpt_level: str, topic: str) -> List[Content]:
        """Search for Japanese learning content."""
        pass
    
    @abstractmethod
    def validate_source_quality(self, url: str) -> QualityScore:
        """Validate the quality of a content source."""
        pass


class ProgressTrackerInterface(ABC):
    """Interface for progress tracking and analytics."""
    
    @abstractmethod
    def record_performance(self, user_id: str, activity: LearningActivity, result: ActivityResult) -> None:
        """Record user performance for an activity."""
        pass
    
    @abstractmethod
    def calculate_learning_velocity(self, user_id: str, timeframe: timedelta) -> float:
        """Calculate learning velocity over a timeframe."""
        pass
    
    @abstractmethod
    def generate_progress_report(self, user_id: str, period: str) -> ProgressReport:
        """Generate a progress report for a period."""
        pass


class MemoryManagerInterface(ABC):
    """Interface for content memory and repetition management."""
    
    @abstractmethod
    def record_learned_content(self, user_id: str, content: Content) -> None:
        """Record that content has been learned."""
        pass
    
    @abstractmethod
    def check_content_seen(self, user_id: str, content: Content) -> bool:
        """Check if content has been seen recently."""
        pass
    
    @abstractmethod
    def get_mastery_level(self, user_id: str, content: Content) -> MasteryLevel:
        """Get the mastery level for specific content."""
        pass


class WeaknessAnalyzerInterface(ABC):
    """Interface for weakness analysis and improvement planning."""
    
    @abstractmethod
    def analyze_error_patterns(self, user_id: str, timeframe: timedelta) -> List[WeakArea]:
        """Analyze error patterns to identify weaknesses."""
        pass
    
    @abstractmethod
    def identify_skill_gaps(self, user_id: str, language: str) -> List[WeakArea]:
        """Identify skill gaps for a specific language."""
        pass
    
    @abstractmethod
    def calculate_weakness_severity(self, weakness: WeakArea) -> float:
        """Calculate the severity of a weakness."""
        pass


class ChineseInterfaceInterface(ABC):
    """Interface for Chinese language user interactions."""
    
    @abstractmethod
    def display_message(self, message_key: str, params: Dict[str, Any]) -> str:
        """Display a localized message in Chinese."""
        pass
    
    @abstractmethod
    def format_feedback(self, feedback: str) -> str:
        """Format feedback in Chinese."""
        pass
    
    @abstractmethod
    def translate_content(self, content: Content, target_lang: str) -> str:
        """Translate content with Chinese explanations."""
        pass
    
    @abstractmethod
    def provide_cultural_context(self, concept: str) -> str:
        """Provide cultural context for foreign language concepts in Chinese."""
        pass
    
    @abstractmethod
    def provide_pronunciation_guidance(self, word: str, language: str) -> str:
        """Provide pronunciation guidance using Chinese phonetic descriptions."""
        pass
    
    @abstractmethod
    def explain_grammar_rule(self, rule: str, language: str) -> str:
        """Explain grammar rules in Chinese with examples."""
        pass


# Cache-related data models
@dataclass
class CacheConfig:
    """Redis缓存系统配置"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    default_ttl: int = 3600  # 默认过期时间（秒）
    max_memory: str = "256mb"  # 最大内存限制
    eviction_policy: str = "allkeys-lru"  # 淘汰策略
    connection_pool_size: int = 10  # 连接池大小
    socket_timeout: int = 5  # 套接字超时时间
    retry_on_timeout: bool = True  # 超时重试


@dataclass
class CacheKey:
    """缓存键管理"""
    prefix: str
    key: str
    
    def __str__(self) -> str:
        return f"{self.prefix}:{self.key}"


@dataclass
class CacheMetrics:
    """缓存性能指标"""
    hit_count: int = 0
    miss_count: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    memory_usage: int = 0
    active_keys: int = 0
    last_updated: datetime = datetime.now()
    
    def calculate_hit_rate(self) -> float:
        """计算缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hit_count / self.total_requests


class CacheManagerInterface(ABC):
    """缓存管理器接口"""
    
    @abstractmethod
    def get_daily_plan(self, user_id: str) -> Optional[DailyPlan]:
        """获取缓存的每日学习计划"""
        pass
    
    @abstractmethod
    def set_daily_plan(self, user_id: str, plan: DailyPlan, ttl: Optional[int] = None) -> bool:
        """缓存每日学习计划"""
        pass
    
    @abstractmethod
    def get_content_recommendations(self, user_id: str, language: str) -> Optional[List[Content]]:
        """获取内容推荐缓存"""
        pass
    
    @abstractmethod
    def set_content_recommendations(self, user_id: str, language: str, content: List[Content], ttl: Optional[int] = None) -> bool:
        """缓存内容推荐"""
        pass
    
    @abstractmethod
    def get_user_session(self, session_id: str) -> Optional[StudySession]:
        """获取用户会话缓存"""
        pass
    
    @abstractmethod
    def set_user_session(self, session_id: str, session: StudySession, ttl: Optional[int] = None) -> bool:
        """缓存用户会话"""
        pass
    
    @abstractmethod
    def invalidate_user_cache(self, user_id: str) -> bool:
        """清除用户相关的所有缓存"""
        pass
    
    @abstractmethod
    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式清除缓存"""
        pass
    
    @abstractmethod
    def preload_cache(self, user_id: str) -> bool:
        """预热用户缓存"""
        pass
    
    @abstractmethod
    def get_cache_metrics(self) -> CacheMetrics:
        """获取缓存性能指标"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """缓存系统健康检查"""
        pass