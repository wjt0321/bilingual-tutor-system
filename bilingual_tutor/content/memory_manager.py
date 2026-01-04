"""
Memory Manager - Tracks learned content and prevents repetition.
"""

from typing import Dict, List, Set
from datetime import datetime, timedelta
from ..models import Content, MasteryLevel, MemoryManagerInterface


class MemoryManager(MemoryManagerInterface):
    """
    Tracks learned content and prevents repetition while managing
    content history and mastery levels.
    """
    
    def __init__(self):
        """Initialize the memory manager with tracking structures."""
        self.user_content_history: Dict[str, Set[str]] = {}
        self.content_mastery: Dict[str, Dict[str, MasteryLevel]] = {}
        self.learning_timestamps: Dict[str, Dict[str, datetime]] = {}
        self.review_schedule: Dict[str, Dict[str, datetime]] = {}
    
    def record_learned_content(self, user_id: str, content: Content) -> None:
        """
        Record that content has been learned by the user.
        
        Args:
            user_id: Unique identifier for the user
            content: Content that was learned
        """
        # Initialize user tracking if not exists
        if user_id not in self.user_content_history:
            self.user_content_history[user_id] = set()
            self.content_mastery[user_id] = {}
            self.learning_timestamps[user_id] = {}
            self.review_schedule[user_id] = {}
        
        # Record content as seen
        self.user_content_history[user_id].add(content.content_id)
        
        # Set initial mastery level
        if content.content_id not in self.content_mastery[user_id]:
            self.content_mastery[user_id][content.content_id] = MasteryLevel.LEARNING
        
        # Record learning timestamp
        self.learning_timestamps[user_id][content.content_id] = datetime.now()
    
    def check_content_seen(self, user_id: str, content: Content) -> bool:
        """
        Check if content has been seen recently by the user.
        
        Args:
            user_id: Unique identifier for the user
            content: Content to check
            
        Returns:
            True if content was seen recently, False otherwise
        """
        if user_id not in self.user_content_history:
            return False
        
        return content.content_id in self.user_content_history[user_id]
    
    def get_mastery_level(self, user_id: str, content: Content) -> MasteryLevel:
        """
        Get the mastery level for specific content.
        
        Args:
            user_id: Unique identifier for the user
            content: Content to check mastery for
            
        Returns:
            Current mastery level for the content
        """
        if user_id not in self.content_mastery:
            return MasteryLevel.NOT_LEARNED
        
        return self.content_mastery[user_id].get(content.content_id, MasteryLevel.NOT_LEARNED)
    
    def mark_for_review(self, user_id: str, content: Content, interval: timedelta) -> None:
        """
        Mark content for review after a specified interval.
        
        Args:
            user_id: Unique identifier for the user
            content: Content to schedule for review
            interval: Time interval before next review
        """
        # Initialize user tracking if not exists
        if user_id not in self.review_schedule:
            self.review_schedule[user_id] = {}
        
        # Schedule review for future date
        review_date = datetime.now() + interval
        self.review_schedule[user_id][content.content_id] = review_date
        
        # Update mastery level to indicate needs review
        if user_id not in self.content_mastery:
            self.content_mastery[user_id] = {}
        self.content_mastery[user_id][content.content_id] = MasteryLevel.NEEDS_REVIEW
    
    def get_due_reviews(self, user_id: str) -> List[Content]:
        """
        Get content that is due for review.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            List of content due for review
        """
        if user_id not in self.review_schedule:
            return []
        
        current_time = datetime.now()
        due_content_ids = []
        
        for content_id, review_date in self.review_schedule[user_id].items():
            if review_date <= current_time:
                due_content_ids.append(content_id)
        
        # Note: This returns content IDs only since we don't have a content store
        # In a real implementation, this would fetch Content objects from storage
        # For now, we'll return empty list as Content objects aren't available
        return []
    
    def update_mastery_level(self, user_id: str, content: Content, new_level: MasteryLevel) -> None:
        """
        Update the mastery level for content.
        
        Args:
            user_id: Unique identifier for the user
            content: Content to update
            new_level: New mastery level
        """
        # Initialize user tracking if not exists
        if user_id not in self.content_mastery:
            self.content_mastery[user_id] = {}
        
        # Update mastery level
        self.content_mastery[user_id][content.content_id] = new_level
        
        # Update timestamp for tracking
        if user_id not in self.learning_timestamps:
            self.learning_timestamps[user_id] = {}
        self.learning_timestamps[user_id][content.content_id] = datetime.now()
    
    def check_content_seen_within_window(self, user_id: str, content: Content, window: timedelta) -> bool:
        """
        Check if content has been seen within a specific time window.
        
        Args:
            user_id: Unique identifier for the user
            content: Content to check
            window: Time window to check within
            
        Returns:
            True if content was seen within the window, False otherwise
        """
        if user_id not in self.learning_timestamps:
            return False
        
        if content.content_id not in self.learning_timestamps[user_id]:
            return False
        
        last_seen = self.learning_timestamps[user_id][content.content_id]
        current_time = datetime.now()
        
        return (current_time - last_seen) <= window
    
    def get_content_history_count(self, user_id: str) -> int:
        """
        Get the total count of content seen by the user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Number of unique content items seen
        """
        if user_id not in self.user_content_history:
            return 0
        
        return len(self.user_content_history[user_id])
    
    def clear_old_content_history(self, user_id: str, retention_period: timedelta) -> None:
        """
        Clear content history older than the retention period.
        
        Args:
            user_id: Unique identifier for the user
            retention_period: How long to retain content history
        """
        if user_id not in self.learning_timestamps:
            return
        
        current_time = datetime.now()
        expired_content_ids = []
        
        for content_id, timestamp in self.learning_timestamps[user_id].items():
            if (current_time - timestamp) > retention_period:
                expired_content_ids.append(content_id)
        
        # Remove expired content from all tracking structures
        for content_id in expired_content_ids:
            if user_id in self.user_content_history:
                self.user_content_history[user_id].discard(content_id)
            if user_id in self.content_mastery:
                self.content_mastery[user_id].pop(content_id, None)
            if user_id in self.learning_timestamps:
                self.learning_timestamps[user_id].pop(content_id, None)
            if user_id in self.review_schedule:
                self.review_schedule[user_id].pop(content_id, None)