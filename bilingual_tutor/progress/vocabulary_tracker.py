"""
Vocabulary Tracker - Monitors vocabulary acquisition and triggers level progression.
"""

from typing import Dict, List, Set
from datetime import datetime, timedelta
from ..models import (
    UserProfile, Content, ActivityResult, LearningActivity, ActivityType, Skill
)


class VocabularyTracker:
    """
    Monitors vocabulary mastery and triggers level progression.
    """
    
    def __init__(self):
        """Initialize the vocabulary tracker."""
        # Track vocabulary mastery per user per language
        self.user_vocabulary: Dict[str, Dict[str, Set[str]]] = {}  # user_id -> language -> set of mastered words
        self.user_levels: Dict[str, Dict[str, str]] = {}  # user_id -> language -> current level
        self.level_requirements: Dict[str, Dict[str, int]] = {
            "english": {
                "CET-4": 4500,
                "CET-5": 6000,
                "CET-6": 7500,
                "CET-6+": 10000
            },
            "japanese": {
                "N5": 800,
                "N4": 1500,
                "N3": 3000,
                "N2": 6000,
                "N1": 10000,
                "N1+": 15000
            }
        }
        self.level_progression: Dict[str, List[str]] = {
            "english": ["CET-4", "CET-5", "CET-6", "CET-6+"],
            "japanese": ["N5", "N4", "N3", "N2", "N1", "N1+"]
        }
        # Track retention rates
        self.word_learning_dates: Dict[str, Dict[str, Dict[str, datetime]]] = {}  # user_id -> language -> word -> learned_date
        self.word_review_history: Dict[str, Dict[str, Dict[str, List[float]]]] = {}  # user_id -> language -> word -> [scores]
        # Track level advancement notifications
        self.advancement_notifications: Dict[str, List[Dict[str, any]]] = {}  # user_id -> list of notifications
    
    def record_word_learned(self, user_id: str, word: str, language: str, score: float = 1.0) -> None:
        """
        Record that a vocabulary word has been learned.
        
        Args:
            user_id: Unique identifier for the user
            word: The vocabulary word that was learned
            language: Language of the word (english/japanese)
            score: Performance score for the word (0.0 to 1.0)
        """
        # Initialize user data if not exists
        if user_id not in self.user_vocabulary:
            self.user_vocabulary[user_id] = {}
        if language not in self.user_vocabulary[user_id]:
            self.user_vocabulary[user_id][language] = set()
        
        if user_id not in self.word_learning_dates:
            self.word_learning_dates[user_id] = {}
        if language not in self.word_learning_dates[user_id]:
            self.word_learning_dates[user_id][language] = {}
        
        if user_id not in self.word_review_history:
            self.word_review_history[user_id] = {}
        if language not in self.word_review_history[user_id]:
            self.word_review_history[user_id][language] = {}
        
        # Record word as learned if score is high enough
        if score >= 0.8:  # Consider mastered if score >= 80%
            self.user_vocabulary[user_id][language].add(word)
            if word not in self.word_learning_dates[user_id][language]:
                self.word_learning_dates[user_id][language][word] = datetime.now()
        
        # Track review history
        if word not in self.word_review_history[user_id][language]:
            self.word_review_history[user_id][language][word] = []
        self.word_review_history[user_id][language][word].append(score)
    
    def check_level_completion(self, user_id: str, language: str) -> bool:
        """
        Check if user has completed their current level's vocabulary requirements.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to check (english/japanese)
            
        Returns:
            True if current level is completed, False otherwise
        """
        if user_id not in self.user_vocabulary or language not in self.user_vocabulary[user_id]:
            return False
        
        if user_id not in self.user_levels or language not in self.user_levels[user_id]:
            # Default to starting levels
            current_level = "CET-4" if language == "english" else "N5"
        else:
            current_level = self.user_levels[user_id][language]
        
        mastered_count = len(self.user_vocabulary[user_id][language])
        required_count = self.level_requirements[language].get(current_level, 0)
        
        return mastered_count >= required_count
    
    def calculate_retention_rate(self, user_id: str, language: str, timeframe: timedelta) -> float:
        """
        Calculate vocabulary retention rate over a timeframe.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to calculate for
            timeframe: Time period to calculate retention for
            
        Returns:
            Retention rate as a percentage (0.0 to 100.0)
        """
        if (user_id not in self.word_learning_dates or 
            language not in self.word_learning_dates[user_id]):
            return 0.0
        
        cutoff_date = datetime.now() - timeframe
        words_in_timeframe = [
            word for word, learned_date in self.word_learning_dates[user_id][language].items()
            if learned_date >= cutoff_date
        ]
        
        if not words_in_timeframe:
            return 0.0
        
        # Calculate retention based on recent review performance
        retained_words = 0
        for word in words_in_timeframe:
            if (word in self.word_review_history[user_id][language] and
                self.word_review_history[user_id][language][word]):
                # Consider retained if recent average score >= 0.7
                recent_scores = self.word_review_history[user_id][language][word][-3:]  # Last 3 reviews
                avg_score = sum(recent_scores) / len(recent_scores)
                if avg_score >= 0.7:
                    retained_words += 1
        
        return (retained_words / len(words_in_timeframe)) * 100.0
    
    def suggest_level_advancement(self, user_id: str, language: str) -> bool:
        """
        Suggest if user should advance to the next level.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to check advancement for
            
        Returns:
            True if advancement is suggested, False otherwise
        """
        if not self.check_level_completion(user_id, language):
            return False
        
        # Additional criteria for advancement
        # 1. Good retention rate
        retention_rate = self.calculate_retention_rate(user_id, language, timedelta(days=30))
        if retention_rate < 70.0:  # Require 70% retention
            return False
        
        # 2. Consistent performance
        if (user_id in self.word_review_history and 
            language in self.word_review_history[user_id]):
            all_scores = []
            for word_scores in self.word_review_history[user_id][language].values():
                all_scores.extend(word_scores[-5:])  # Recent scores
            
            if all_scores:
                avg_performance = sum(all_scores) / len(all_scores)
                if avg_performance < 0.75:  # Require 75% average performance
                    return False
        
        return True
    
    def advance_level(self, user_id: str, language: str) -> str:
        """
        Advance user to the next level.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to advance
            
        Returns:
            New level string, or current level if advancement not possible
        """
        if user_id not in self.user_levels:
            self.user_levels[user_id] = {}
        
        current_level = self.user_levels[user_id].get(language, 
                                                     "CET-4" if language == "english" else "N5")
        
        progression = self.level_progression[language]
        try:
            current_index = progression.index(current_level)
            if current_index < len(progression) - 1:
                new_level = progression[current_index + 1]
                self.user_levels[user_id][language] = new_level
                
                # Generate advancement notification
                self._create_advancement_notification(user_id, language, current_level, new_level)
                
                return new_level
        except ValueError:
            pass
        
        return current_level
    
    def _create_advancement_notification(self, user_id: str, language: str, old_level: str, new_level: str) -> None:
        """
        Create a level advancement notification.
        
        Args:
            user_id: User who advanced
            language: Language that was advanced
            old_level: Previous level
            new_level: New level
        """
        if user_id not in self.advancement_notifications:
            self.advancement_notifications[user_id] = []
        
        # Get requirements for new level
        new_requirements = self.level_requirements[language].get(new_level, 0)
        
        notification = {
            "type": "level_advancement",
            "language": language,
            "old_level": old_level,
            "new_level": new_level,
            "timestamp": datetime.now(),
            "message": f"恭喜！您的{language}水平已从{old_level}提升到{new_level}！",
            "new_expectations": f"新目标：掌握{new_requirements}个{language}词汇",
            "encouragement": "继续努力，您正在稳步进步！"
        }
        
        self.advancement_notifications[user_id].append(notification)
    
    def get_pending_notifications(self, user_id: str) -> List[Dict[str, any]]:
        """
        Get pending advancement notifications for a user.
        
        Args:
            user_id: User to get notifications for
            
        Returns:
            List of notification dictionaries
        """
        return self.advancement_notifications.get(user_id, [])
    
    def clear_notifications(self, user_id: str) -> None:
        """
        Clear all notifications for a user.
        
        Args:
            user_id: User to clear notifications for
        """
        if user_id in self.advancement_notifications:
            self.advancement_notifications[user_id] = []
    
    def get_vocabulary_progress(self, user_id: str, language: str) -> Dict[str, any]:
        """
        Get comprehensive vocabulary progress information.
        
        Args:
            user_id: Unique identifier for the user
            language: Language to get progress for
            
        Returns:
            Dictionary with progress information
        """
        if user_id not in self.user_vocabulary or language not in self.user_vocabulary[user_id]:
            mastered_count = 0
        else:
            mastered_count = len(self.user_vocabulary[user_id][language])
        
        current_level = self.user_levels.get(user_id, {}).get(language, 
                                                             "CET-4" if language == "english" else "N5")
        required_count = self.level_requirements[language].get(current_level, 0)
        
        progress_percentage = (mastered_count / required_count * 100.0) if required_count > 0 else 0.0
        
        return {
            "current_level": current_level,
            "mastered_words": mastered_count,
            "required_words": required_count,
            "progress_percentage": min(100.0, progress_percentage),
            "level_completed": self.check_level_completion(user_id, language),
            "advancement_ready": self.suggest_level_advancement(user_id, language),
            "retention_rate": self.calculate_retention_rate(user_id, language, timedelta(days=30))
        }
    
    def process_activity_result(self, user_id: str, activity: LearningActivity, result: ActivityResult) -> None:
        """
        Process an activity result to update vocabulary tracking.
        
        Args:
            user_id: Unique identifier for the user
            activity: Learning activity that was completed
            result: Results from the activity
        """
        # Only process vocabulary-related activities
        if (activity.activity_type == ActivityType.VOCABULARY or 
            Skill.VOCABULARY in activity.skills_practiced):
            
            # Extract vocabulary words from content (simplified - in real implementation 
            # this would use NLP to extract actual vocabulary)
            words = self._extract_vocabulary_from_content(activity.content, activity.language)
            
            # Record each word with the activity score
            for word in words:
                self.record_word_learned(user_id, word, activity.language, result.score)
    
    def _extract_vocabulary_from_content(self, content: Content, language: str) -> List[str]:
        """
        Extract vocabulary words from content (simplified implementation).
        
        Args:
            content: Content to extract vocabulary from
            language: Language of the content
            
        Returns:
            List of vocabulary words
        """
        # Simplified implementation - in reality this would use NLP
        # For testing purposes, generate some words based on content
        words = []
        
        # Extract words from title and body (simplified)
        text = f"{content.title} {content.body}".lower()
        
        # Simple word extraction (in reality would use proper tokenization)
        import re
        potential_words = re.findall(r'\b[a-zA-Z]+\b' if language == "english" else r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', text)
        
        # Filter and limit words (simplified)
        for word in potential_words[:5]:  # Limit to 5 words per content
            if len(word) >= 3:  # Only words with 3+ characters
                words.append(word)
        
        return words