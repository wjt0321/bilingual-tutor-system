"""
Level Content Integration - Integrates precise level crawler with existing content system.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from ..models import Content, UserProfile, ContentType
from .precise_level_crawler import PreciseLevelContentCrawler, VocabularyItem
from .content_quality_assessor import ContentQualityAssessor, LevelGradingResult
from .filter import ContentFilter
from .memory_manager import MemoryManager


class LevelContentIntegration:
    """
    Integration layer that combines precise level crawling with existing content management.
    Provides unified interface for level-appropriate content discovery and management.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize the level content integration system.
        
        Args:
            memory_manager: Memory manager for content tracking
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.precise_crawler = PreciseLevelContentCrawler()
        self.quality_assessor = ContentQualityAssessor()
        self.content_filter = ContentFilter()
        self.memory_manager = memory_manager
        
        # Configuration
        self.max_content_per_request = 20
        self.quality_threshold = 0.7
        self.level_confidence_threshold = 0.8
    
    def discover_level_appropriate_content(self, user_profile: UserProfile, 
                                         language: str, topic: Optional[str] = None,
                                         content_type: Optional[ContentType] = None,
                                         limit: int = 10) -> List[Content]:
        """
        Discover and return level-appropriate content for the user.
        
        Args:
            user_profile: User's profile with current levels
            language: Target language (english/japanese)
            topic: Optional topic filter
            content_type: Optional content type filter
            limit: Maximum number of content items to return
            
        Returns:
            List of verified level-appropriate content
        """
        self.logger.info(f"Discovering {language} content for user {user_profile.user_id}")
        
        # Get user's current level for the language
        current_level = self._get_user_level(user_profile, language)
        
        # Crawl content using precise level crawler
        if language == "english":
            raw_content = self.precise_crawler.crawl_cet_content(
                level=current_level, 
                topic=topic, 
                limit=self.max_content_per_request
            )
        elif language == "japanese":
            raw_content = self.precise_crawler.crawl_jlpt_content(
                level=current_level, 
                topic=topic, 
                limit=self.max_content_per_request
            )
        else:
            self.logger.warning(f"Unsupported language: {language}")
            return []
        
        # Filter content by type if specified
        if content_type:
            raw_content = [c for c in raw_content if c.content_type == content_type]
        
        # Quality assessment and level verification
        verified_content = self._verify_and_assess_content(raw_content, current_level, user_profile)
        
        # Filter out content already seen by user
        new_content = self._filter_seen_content(verified_content, user_profile.user_id)
        
        # Sort by quality and relevance
        sorted_content = self._sort_content_by_relevance(new_content, user_profile)
        
        # Return limited results
        result = sorted_content[:limit]
        
        self.logger.info(f"Discovered {len(result)} level-appropriate content items")
        return result
    
    def extract_vocabulary_for_user(self, content: Content, user_profile: UserProfile) -> List[VocabularyItem]:
        """
        Extract vocabulary items from content appropriate for user's level.
        
        Args:
            content: Content to extract vocabulary from
            user_profile: User's profile for level checking
            
        Returns:
            List of level-appropriate vocabulary items
        """
        # Extract vocabulary using precise crawler
        vocabulary_items = self.precise_crawler.extract_level_vocabulary(content)
        
        # Filter vocabulary by user's current level
        current_level = self._get_user_level(user_profile, content.language)
        appropriate_vocab = []
        
        for vocab_item in vocabulary_items:
            # Check if vocabulary is appropriate for user's level
            if self._is_vocabulary_appropriate_for_user(vocab_item, current_level, user_profile):
                appropriate_vocab.append(vocab_item)
        
        return appropriate_vocab
    
    def assess_content_for_user(self, content: Content, user_profile: UserProfile) -> Tuple[float, LevelGradingResult]:
        """
        Assess content quality and level appropriateness for specific user.
        
        Args:
            content: Content to assess
            user_profile: User's profile for personalized assessment
            
        Returns:
            Tuple of (quality_score, level_grading_result)
        """
        # Get quality assessment
        quality_score = self.quality_assessor.assess_content_quality(content)
        
        # Get level grading
        level_grading = self.quality_assessor.grade_content_level(content)
        
        # Adjust scores based on user's weak areas
        adjusted_quality = self._adjust_quality_for_user_weaknesses(
            quality_score.overall_score, content, user_profile
        )
        
        return adjusted_quality, level_grading
    
    def get_content_recommendations(self, content: Content, user_profile: UserProfile) -> List[str]:
        """
        Get personalized content improvement recommendations.
        
        Args:
            content: Content to analyze
            user_profile: User's profile for personalized recommendations
            
        Returns:
            List of improvement recommendations in Chinese
        """
        current_level = self._get_user_level(user_profile, content.language)
        
        # Get base recommendations from quality assessor
        recommendations = self.quality_assessor.generate_improvement_recommendations(content, current_level)
        
        # Add user-specific recommendations based on weak areas
        user_recommendations = self._generate_user_specific_recommendations(content, user_profile)
        recommendations.extend(user_recommendations)
        
        return recommendations
    
    def validate_content_level_accuracy(self, content: Content) -> float:
        """
        Validate how accurately content matches its claimed level.
        
        Args:
            content: Content to validate
            
        Returns:
            Level accuracy score (0.0 to 1.0)
        """
        return self.precise_crawler.assess_content_level_accuracy(content)
    
    def batch_process_content(self, content_list: List[Content], 
                            user_profile: UserProfile) -> Dict[str, List[Content]]:
        """
        Batch process content list and categorize by quality and appropriateness.
        
        Args:
            content_list: List of content to process
            user_profile: User's profile for assessment
            
        Returns:
            Dictionary categorizing content by quality level
        """
        categorized_content = {
            "excellent": [],
            "good": [],
            "acceptable": [],
            "needs_improvement": []
        }
        
        for content in content_list:
            quality_score, level_grading = self.assess_content_for_user(content, user_profile)
            
            # Categorize based on quality score
            if quality_score >= 0.9:
                categorized_content["excellent"].append(content)
            elif quality_score >= 0.8:
                categorized_content["good"].append(content)
            elif quality_score >= 0.7:
                categorized_content["acceptable"].append(content)
            else:
                categorized_content["needs_improvement"].append(content)
        
        return categorized_content
    
    def _get_user_level(self, user_profile: UserProfile, language: str) -> str:
        """Get user's current level for specified language."""
        if language == "english":
            return user_profile.english_level
        elif language == "japanese":
            return user_profile.japanese_level
        else:
            return "beginner"
    
    def _verify_and_assess_content(self, content_list: List[Content], 
                                 target_level: str, user_profile: UserProfile) -> List[Content]:
        """Verify and assess content quality and level appropriateness."""
        verified_content = []
        
        for content in content_list:
            try:
                # Assess quality
                quality_score = self.quality_assessor.assess_content_quality(content)
                
                if quality_score.overall_score < self.quality_threshold:
                    continue
                
                # Verify level appropriateness
                level_appropriateness = self.quality_assessor.validate_level_appropriateness(
                    content, target_level
                )
                
                if level_appropriateness < self.level_confidence_threshold:
                    continue
                
                # Check content appropriateness using existing filter
                if not self.content_filter.check_appropriateness(content):
                    continue
                
                # Update content with assessed quality score
                content.quality_score = quality_score.overall_score
                verified_content.append(content)
                
            except Exception as e:
                self.logger.error(f"Error verifying content {content.content_id}: {e}")
                continue
        
        return verified_content
    
    def _filter_seen_content(self, content_list: List[Content], user_id: str) -> List[Content]:
        """Filter out content already seen by the user."""
        new_content = []
        
        for content in content_list:
            if not self.memory_manager.check_content_seen(user_id, content):
                new_content.append(content)
        
        return new_content
    
    def _sort_content_by_relevance(self, content_list: List[Content], 
                                 user_profile: UserProfile) -> List[Content]:
        """Sort content by relevance to user's needs and weak areas."""
        def relevance_score(content: Content) -> float:
            score = content.quality_score
            
            # Boost score for content that addresses user's weak areas
            for weak_area in user_profile.weak_areas:
                if weak_area.language == content.language:
                    if self._content_addresses_weakness(content, weak_area):
                        score += weak_area.severity * 0.2
            
            # Boost score for preferred content types
            if content.content_type in user_profile.learning_preferences.content_preferences:
                score += 0.1
            
            return score
        
        return sorted(content_list, key=relevance_score, reverse=True)
    
    def _is_vocabulary_appropriate_for_user(self, vocab_item: VocabularyItem, 
                                          current_level: str, user_profile: UserProfile) -> bool:
        """Check if vocabulary item is appropriate for user's current level."""
        # Check level appropriateness
        if vocab_item.level != current_level:
            # Allow vocabulary from one level below or at current level
            if vocab_item.language == "english":
                level_hierarchy = ["CET-4", "CET-5", "CET-6"]
            elif vocab_item.language == "japanese":
                level_hierarchy = ["N5", "N4", "N3", "N2", "N1"]
            else:
                return True
            
            try:
                vocab_idx = level_hierarchy.index(vocab_item.level)
                user_idx = level_hierarchy.index(current_level)
                
                # Allow vocabulary at or below user's level
                if vocab_idx > user_idx:
                    return False
            except ValueError:
                return True
        
        return True
    
    def _adjust_quality_for_user_weaknesses(self, base_quality: float, 
                                          content: Content, user_profile: UserProfile) -> float:
        """Adjust quality score based on how well content addresses user's weaknesses."""
        adjusted_quality = base_quality
        
        # Boost quality for content that addresses user's weak areas
        weakness_boost = 0.0
        for weak_area in user_profile.weak_areas:
            if weak_area.language == content.language:
                if self._content_addresses_weakness(content, weak_area):
                    weakness_boost += weak_area.severity * 0.1
        
        return min(1.0, adjusted_quality + weakness_boost)
    
    def _content_addresses_weakness(self, content: Content, weak_area) -> bool:
        """Check if content addresses a specific weakness."""
        # Check if content type matches weakness skill
        from ..models import Skill
        
        skill_to_content_type = {
            Skill.VOCABULARY: [ContentType.EXERCISE, ContentType.ARTICLE],
            Skill.GRAMMAR: [ContentType.EXERCISE, ContentType.DIALOGUE],
            Skill.READING: [ContentType.ARTICLE, ContentType.NEWS],
            Skill.LISTENING: [ContentType.AUDIO],
            Skill.SPEAKING: [ContentType.DIALOGUE],
            Skill.WRITING: [ContentType.EXERCISE]
        }
        
        appropriate_types = skill_to_content_type.get(weak_area.skill, [])
        if content.content_type in appropriate_types:
            return True
        
        # Check if content tags or body mention weakness patterns
        content_text = (content.title + " " + content.body + " " + " ".join(content.tags)).lower()
        
        for pattern in weak_area.error_patterns:
            if pattern.lower() in content_text:
                return True
        
        return False
    
    def _generate_user_specific_recommendations(self, content: Content, 
                                              user_profile: UserProfile) -> List[str]:
        """Generate user-specific recommendations based on profile and weak areas."""
        recommendations = []
        
        # Recommendations based on weak areas
        user_weaknesses = [w for w in user_profile.weak_areas if w.language == content.language]
        
        if user_weaknesses:
            weakness_skills = [w.skill.value for w in user_weaknesses]
            
            if "vocabulary" in weakness_skills:
                recommendations.append("建议增加更多词汇练习和解释")
            
            if "grammar" in weakness_skills:
                recommendations.append("建议添加更多语法要点和例句")
            
            if "reading" in weakness_skills:
                recommendations.append("建议提供阅读理解练习和问题")
            
            if "listening" in weakness_skills:
                recommendations.append("建议添加音频内容和听力练习")
        
        # Recommendations based on learning preferences
        preferred_types = user_profile.learning_preferences.content_preferences
        
        if ContentType.DIALOGUE in preferred_types and content.content_type != ContentType.DIALOGUE:
            recommendations.append("考虑将内容改编为对话形式")
        
        if ContentType.EXERCISE in preferred_types and content.content_type != ContentType.EXERCISE:
            recommendations.append("建议添加相关的练习题")
        
        return recommendations