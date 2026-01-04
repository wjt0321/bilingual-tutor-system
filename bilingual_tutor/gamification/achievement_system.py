"""
Achievement System and Gamification - Badges, rewards, and incentives.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

from ..models import Skill, ActivityType


class AchievementType(Enum):
    """Types of achievements."""
    STUDY_DURATION = "study_duration"
    CONTENT_MASTERY = "content_mastery"
    STREAK = "streak"
    CONSISTENCY = "consistency"
    SKILL_PROGRESSION = "skill_progression"
    MILESTONE = "milestone"
    SOCIAL = "social"


class AchievementTier(Enum):
    """Achievement tiers/levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class Achievement:
    """An achievement that can be unlocked."""
    achievement_id: str
    name: str
    description: str
    achievement_type: AchievementType
    tier: AchievementTier
    points: int
    icon: Optional[str] = None
    requirements: Dict = field(default_factory=dict)
    unlocked_at: Optional[datetime] = None
    progress: float = 0.0
    max_progress: float = 1.0


@dataclass
class UserAchievement:
    """User's achievement progress and status."""
    user_id: str
    achievement: Achievement
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None
    progress: float = 0.0
    view_count: int = 0


@dataclass
class Reward:
    """A reward that can be claimed."""
    reward_id: str
    name: str
    description: str
    reward_type: str  # "badge", "points", "content", "theme", etc.
    points_value: int = 0
    cost_points: int = 0
    available: bool = True
    expiry_date: Optional[datetime] = None


@dataclass
class UserReward:
    """User's claimed rewards."""
    user_id: str
    reward: Reward
    claimed_at: datetime
    used: bool = False


@dataclass
class LeaderboardEntry:
    """Entry in a leaderboard."""
    user_id: str
    username: str
    points: int
    rank: int
    change: int = 0  # Rank change from previous period


@dataclass
class Challenge:
    """A time-limited learning challenge."""
    challenge_id: str
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    challenge_type: AchievementType
    target_value: float
    reward_points: int
    participants: Set[str] = field(default_factory=set)
    completed: Set[str] = field(default_factory=set)


class AchievementSystem:
    """
    Achievement system with badges, rewards, and incentives.
    """
    
    def __init__(self):
        """Initialize achievement system."""
        self.achievements: Dict[str, Achievement] = {}
        self.user_achievements: Dict[str, Dict[str, UserAchievement]] = defaultdict(dict)
        self.user_points: Dict[str, int] = defaultdict(int)
        self.user_rewards: Dict[str, List[UserReward]] = defaultdict(list)
        self.rewards_catalog: Dict[str, Reward] = {}
        self.challenges: Dict[str, Challenge] = {}
        
        # Track streaks
        self.user_streaks: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'current': 0,
            'longest': 0,
            'last_study_date': None
        })
        
        # Track session counts
        self.user_session_counts: Dict[str, int] = defaultdict(int)
        
        # Initialize default achievements
        self._initialize_default_achievements()
        
        # Initialize rewards catalog
        self._initialize_rewards_catalog()
    
    def _initialize_default_achievements(self):
        """Initialize default achievement definitions."""
        
        # Study duration achievements
        self.achievements['first_study'] = Achievement(
            achievement_id='first_study',
            name='First Steps',
            description='Complete your first study session',
            achievement_type=AchievementType.STUDY_DURATION,
            tier=AchievementTier.BRONZE,
            points=10,
            requirements={'sessions': 1}
        )
        
        self.achievements['week_warrior'] = Achievement(
            achievement_id='week_warrior',
            name='Week Warrior',
            description='Study for 7 consecutive days',
            achievement_type=AchievementType.STREAK,
            tier=AchievementTier.SILVER,
            points=100,
            requirements={'streak_days': 7}
        )
        
        self.achievements['month_master'] = Achievement(
            achievement_id='month_master',
            name='Month Master',
            description='Study for 30 consecutive days',
            achievement_type=AchievementType.STREAK,
            tier=AchievementTier.GOLD,
            points=500,
            requirements={'streak_days': 30}
        )
        
        self.achievements['centurion'] = Achievement(
            achievement_id='centurion',
            name='Centurion',
            description='Complete 100 study sessions',
            achievement_type=AchievementType.STUDY_DURATION,
            tier=AchievementTier.GOLD,
            points=300,
            requirements={'sessions': 100}
        )
        
        # Content mastery achievements
        self.achievements['vocab_collector'] = Achievement(
            achievement_id='vocab_collector',
            name='Vocabulary Collector',
            description='Master 100 vocabulary words',
            achievement_type=AchievementType.CONTENT_MASTERY,
            tier=AchievementTier.SILVER,
            points=150,
            requirements={'vocabulary_mastered': 100}
        )
        
        self.achievements['grammar_guru'] = Achievement(
            achievement_id='grammar_guru',
            name='Grammar Guru',
            description='Complete all grammar exercises with 90%+ accuracy',
            achievement_type=AchievementType.CONTENT_MASTERY,
            tier=AchievementTier.GOLD,
            points=250,
            requirements={'grammar_accuracy': 0.9, 'grammar_exercises': 20}
        )
        
        # Consistency achievements
        self.achievements['consistent_learner'] = Achievement(
            achievement_id='consistent_learner',
            name='Consistent Learner',
            description='Study at least 5 days a week for 4 weeks',
            achievement_type=AchievementType.CONSISTENCY,
            tier=AchievementTier.SILVER,
            points=200,
            requirements={'days_per_week': 5, 'weeks': 4}
        )
        
        self.achievements['dedicated_student'] = Achievement(
            achievement_id='dedicated_student',
            name='Dedicated Student',
            description='Study at least 6 days a week for 8 weeks',
            achievement_type=AchievementType.CONSISTENCY,
            tier=AchievementTier.GOLD,
            points=400,
            requirements={'days_per_week': 6, 'weeks': 8}
        )
        
        # Skill progression achievements
        self.achievements['skill_rising'] = Achievement(
            achievement_id='skill_rising',
            name='Skill Rising',
            description='Reach 60% proficiency in any skill',
            achievement_type=AchievementType.SKILL_PROGRESSION,
            tier=AchievementTier.SILVER,
            points=150,
            requirements={'skill_level': 0.6}
        )
        
        self.achievements['skill_master'] = Achievement(
            achievement_id='skill_master',
            name='Skill Master',
            description='Reach 90% proficiency in any skill',
            achievement_type=AchievementType.SKILL_PROGRESSION,
            tier=AchievementTier.GOLD,
            points=350,
            requirements={'skill_level': 0.9}
        )
        
        # Milestone achievements
        self.achievements['level_1_reached'] = Achievement(
            achievement_id='level_1_reached',
            name='Level 1 Reached',
            description='Reach beginner level',
            achievement_type=AchievementType.MILESTONE,
            tier=AchievementTier.BRONZE,
            points=50,
            requirements={'proficiency_level': 'beginner'}
        )
        
        self.achievements['level_5_reached'] = Achievement(
            achievement_id='level_5_reached',
            name='Level 5 Reached',
            description='Reach intermediate level',
            achievement_type=AchievementType.MILESTONE,
            tier=AchievementTier.SILVER,
            points=200,
            requirements={'proficiency_level': 'intermediate'}
        )
        
        self.achievements['level_10_reached'] = Achievement(
            achievement_id='level_10_reached',
            name='Level 10 Reached',
            description='Reach advanced level',
            achievement_type=AchievementType.MILESTONE,
            tier=AchievementTier.GOLD,
            points=500,
            requirements={'proficiency_level': 'advanced'}
        )
    
    def _initialize_rewards_catalog(self):
        """Initialize rewards catalog for point redemption."""
        
        # Badge rewards
        self.rewards_catalog['custom_badge'] = Reward(
            reward_id='custom_badge',
            name='Custom Profile Badge',
            description='Create a custom badge for your profile',
            reward_type='badge',
            points_value=0,
            cost_points=500
        )
        
        # Content rewards
        self.rewards_catalog['premium_content'] = Reward(
            reward_id='premium_content',
            name='Premium Content Access',
            description='Access premium learning content for 7 days',
            reward_type='content',
            points_value=0,
            cost_points=1000
        )
        
        # Theme rewards
        self.rewards_catalog['dark_theme'] = Reward(
            reward_id='dark_theme',
            name='Dark Theme',
            description='Unlock dark theme',
            reward_type='theme',
            points_value=0,
            cost_points=200
        )
        
        self.rewards_catalog['premium_theme'] = Reward(
            reward_id='premium_theme',
            name='Premium Theme Pack',
            description='Unlock all premium themes',
            reward_type='theme',
            points_value=0,
            cost_points=800
        )
        
        # Points rewards
        self.rewards_catalog['bonus_points'] = Reward(
            reward_id='bonus_points',
            name='Bonus Points',
            description='Get 500 bonus points',
            reward_type='points',
            points_value=500,
            cost_points=300
        )
    
    def record_study_session(self, user_id: str, session_data: Dict):
        """
        Record a study session and check for achievements.
        
        Args:
            user_id: User identifier
            session_data: Session data including duration, activities, etc.
        """
        # Update session count
        self.user_session_counts[user_id] += 1
        
        # Update streak
        self._update_streak(user_id)
        
        # Check study duration achievements
        session_count = self._get_session_count(user_id)
        self._check_achievement(user_id, 'first_study', {'sessions': session_count})
        self._check_achievement(user_id, 'centurion', {'sessions': session_count})
        
        # Check streak achievements
        current_streak = self.user_streaks[user_id]['current']
        self._check_achievement(user_id, 'week_warrior', {'streak_days': 7})
        self._check_achievement(user_id, 'month_master', {'streak_days': 30})
        
        # Award points for session
        duration = session_data.get('duration_minutes', 0)
        points_awarded = int(duration / 10)  # 1 point per 10 minutes
        self.award_points(user_id, points_awarded)
    
    def record_skill_progression(self, user_id: str, skill: Skill, 
                               current_level: float):
        """
        Record skill progression and check for achievements.
        
        Args:
            user_id: User identifier
            skill: Skill being tracked
            current_level: Current skill level (0.0 to 1.0)
        """
        # Check skill progression achievements
        if current_level >= 0.6:
            self._check_achievement(user_id, 'skill_rising', {'skill_level': 0.6})
        
        if current_level >= 0.9:
            self._check_achievement(user_id, 'skill_master', {'skill_level': 0.9})
    
    def record_content_mastery(self, user_id: str, mastery_type: str,
                            mastery_value: float):
        """
        Record content mastery achievements.
        
        Args:
            user_id: User identifier
            mastery_type: Type of content mastered (vocabulary, grammar, etc.)
            mastery_value: Value indicating mastery level
        """
        if mastery_type == 'vocabulary':
            self._check_achievement(user_id, 'vocab_collector', 
                                 {'vocabulary_mastered': mastery_value})
        elif mastery_type == 'grammar':
            self._check_achievement(user_id, 'grammar_guru',
                                 {'grammar_accuracy': mastery_value})
    
    def award_points(self, user_id: str, points: int):
        """
        Award points to a user.
        
        Args:
            user_id: User identifier
            points: Number of points to award
        """
        self.user_points[user_id] += points
    
    def claim_reward(self, user_id: str, reward_id: str) -> bool:
        """
        Claim a reward using points.
        
        Args:
            user_id: User identifier
            reward_id: ID of reward to claim
            
        Returns:
            True if reward was claimed successfully
        """
        if reward_id not in self.rewards_catalog:
            return False
        
        reward = self.rewards_catalog[reward_id]
        
        # Check if user has enough points
        if self.user_points[user_id] < reward.cost_points:
            return False
        
        # Check if reward is available
        if not reward.available:
            return False
        
        # Deduct points and claim reward
        self.user_points[user_id] -= reward.cost_points
        user_reward = UserReward(
            user_id=user_id,
            reward=reward,
            claimed_at=datetime.now()
        )
        self.user_rewards[user_id].append(user_reward)
        
        return True
    
    def get_user_achievements(self, user_id: str) -> List[Achievement]:
        """
        Get all achievements for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of achievements (both unlocked and locked)
        """
        achievements = []
        
        for achievement_id, achievement in self.achievements.items():
            user_achievement = self.user_achievements[user_id].get(achievement_id)
            
            if user_achievement:
                # Update achievement with user progress
                achievement_copy = Achievement(
                    achievement_id=achievement.achievement_id,
                    name=achievement.name,
                    description=achievement.description,
                    achievement_type=achievement.achievement_type,
                    tier=achievement.tier,
                    points=achievement.points,
                    icon=achievement.icon,
                    requirements=achievement.requirements,
                    unlocked_at=user_achievement.unlocked_at,
                    progress=user_achievement.progress,
                    max_progress=achievement.max_progress
                )
                achievements.append(achievement_copy)
            else:
                achievements.append(achievement)
        
        return achievements
    
    def get_user_points(self, user_id: str) -> int:
        """
        Get user's current point balance.
        
        Args:
            user_id: User identifier
            
        Returns:
            Current point balance
        """
        return self.user_points[user_id]
    
    def get_user_streak(self, user_id: str) -> Dict[str, any]:
        """
        Get user's current streak information.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with streak information
        """
        return dict(self.user_streaks[user_id])
    
    def get_rewards_catalog(self) -> List[Reward]:
        """
        Get all available rewards.
        
        Returns:
            List of rewards
        """
        return list(self.rewards_catalog.values())
    
    def get_leaderboard(self, limit: int = 10) -> List[LeaderboardEntry]:
        """
        Get leaderboard of top users.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of leaderboard entries sorted by points
        """
        # Sort users by points
        sorted_users = sorted(
            self.user_points.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        entries = []
        for rank, (user_id, points) in enumerate(sorted_users[:limit], 1):
            entry = LeaderboardEntry(
                user_id=user_id,
                username=user_id,  # In real system, would fetch username
                points=points,
                rank=rank
            )
            entries.append(entry)
        
        return entries
    
    def create_challenge(self, name: str, description: str,
                       challenge_type: AchievementType,
                       target_value: float, reward_points: int,
                       duration_days: int) -> Challenge:
        """
        Create a new time-limited challenge.
        
        Args:
            name: Challenge name
            description: Challenge description
            challenge_type: Type of challenge
            target_value: Target value to complete challenge
            reward_points: Points awarded for completion
            duration_days: Duration of challenge in days
            
        Returns:
            Created Challenge
        """
        challenge_id = f"challenge_{datetime.now().timestamp()}"
        
        challenge = Challenge(
            challenge_id=challenge_id,
            name=name,
            description=description,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            challenge_type=challenge_type,
            target_value=target_value,
            reward_points=reward_points
        )
        
        self.challenges[challenge_id] = challenge
        return challenge
    
    def join_challenge(self, user_id: str, challenge_id: str) -> bool:
        """
        Join a challenge.
        
        Args:
            user_id: User identifier
            challenge_id: Challenge identifier
            
        Returns:
            True if joined successfully
        """
        if challenge_id not in self.challenges:
            return False
        
        challenge = self.challenges[challenge_id]
        
        # Check if challenge is still active
        if datetime.now() > challenge.end_date:
            return False
        
        challenge.participants.add(user_id)
        return True
    
    def get_active_challenges(self) -> List[Challenge]:
        """
        Get all active challenges.
        
        Returns:
            List of active challenges
        """
        now = datetime.now()
        active = []
        
        for challenge in self.challenges.values():
            if challenge.start_date <= now <= challenge.end_date:
                active.append(challenge)
        
        return active
    
    def _update_streak(self, user_id: str):
        """Update user's study streak."""
        today = datetime.now().date()
        last_date = self.user_streaks[user_id]['last_study_date']
        
        if last_date is None:
            # First study session
            self.user_streaks[user_id]['current'] = 1
            self.user_streaks[user_id]['longest'] = 1
        elif last_date == today - timedelta(days=1):
            # Consecutive day
            self.user_streaks[user_id]['current'] += 1
            self.user_streaks[user_id]['longest'] = max(
                self.user_streaks[user_id]['longest'],
                self.user_streaks[user_id]['current']
            )
        elif last_date != today:
            # Streak broken
            self.user_streaks[user_id]['current'] = 1
        
        self.user_streaks[user_id]['last_study_date'] = today
    
    def _check_achievement(self, user_id: str, achievement_id: str, 
                         current_values: Dict):
        """Check and unlock achievement if criteria met."""
        if achievement_id not in self.achievements:
            return
        
        achievement = self.achievements[achievement_id]
        
        # Get or create user achievement
        if achievement_id not in self.user_achievements[user_id]:
            self.user_achievements[user_id][achievement_id] = UserAchievement(
                user_id=user_id,
                achievement=achievement
            )
        
        user_achievement = self.user_achievements[user_id][achievement_id]
        
        # Check if already unlocked
        if user_achievement.unlocked:
            return
        
        # Check requirements
        requirements_met = True
        progress = 0.0
        
        for req_key, req_value in achievement.requirements.items():
            current_value = current_values.get(req_key, 0)
            
            if isinstance(req_value, (int, float)):
                # Calculate progress
                progress = min(1.0, current_value / req_value)
                requirements_met = requirements_met and (current_value >= req_value)
        
        # Update progress
        user_achievement.progress = progress
        
        # Unlock if requirements met
        if requirements_met:
            user_achievement.unlocked = True
            user_achievement.unlocked_at = datetime.now()
            self.award_points(user_id, achievement.points)
    
    def _get_session_count(self, user_id: str) -> int:
        """Get total study session count for user."""
        return self.user_session_counts[user_id]
