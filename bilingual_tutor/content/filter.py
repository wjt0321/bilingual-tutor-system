"""
Content Filter - Evaluates and selects valuable educational content.
"""

import re
from typing import List, Dict, Set
from urllib.parse import urlparse
from ..models import Content, ContentType


class ContentFilter:
    """
    Evaluates and selects valuable educational content from crawled materials.
    Implements educational value assessment, difficulty level matching, and
    content appropriateness validation.
    """
    
    def __init__(self):
        """Initialize the content filter with evaluation criteria."""
        self.educational_keywords = self._load_educational_keywords()
        self.inappropriate_keywords = self._load_inappropriate_keywords()
        self.difficulty_indicators = self._load_difficulty_indicators()
        self.trusted_domains = self._load_trusted_domains()
    
    def evaluate_educational_value(self, content: Content) -> float:
        """
        Evaluate the educational value of content.
        
        Args:
            content: Content to evaluate
            
        Returns:
            Educational value score (0.0 to 1.0)
        """
        score = 0.0
        
        # Check for educational keywords in title and body
        text_to_analyze = (content.title + " " + content.body).lower()
        
        # Educational keyword presence (40% of score)
        educational_score = self._calculate_educational_keyword_score(text_to_analyze)
        score += educational_score * 0.4
        
        # Content structure and length (30% of score)
        structure_score = self._evaluate_content_structure(content)
        score += structure_score * 0.3
        
        # Source reliability (20% of score)
        source_score = self._evaluate_source_reliability(content.source_url)
        score += source_score * 0.2
        
        # Content type appropriateness (10% of score)
        type_score = self._evaluate_content_type_appropriateness(content)
        score += type_score * 0.1
        
        return min(1.0, max(0.0, score))
    
    def match_difficulty_level(self, content: Content, user_level: str) -> bool:
        """
        Check if content difficulty matches user's proficiency level.
        
        Args:
            content: Content to check
            user_level: User's current proficiency level
            
        Returns:
            True if difficulty is appropriate, False otherwise
        """
        content_level = content.difficulty_level
        
        # Direct match
        if content_level == user_level:
            return True
        
        # Check if content is within acceptable range
        if content.language == "english":
            return self._match_english_level(content_level, user_level)
        elif content.language == "japanese":
            return self._match_japanese_level(content_level, user_level)
        
        return False
    
    def check_appropriateness(self, content: Content) -> bool:
        """
        Check if content is appropriate for educational use.
        
        Args:
            content: Content to check
            
        Returns:
            True if content is appropriate, False otherwise
        """
        text_to_check = (content.title + " " + content.body).lower()
        
        # Check for inappropriate keywords
        for keyword in self.inappropriate_keywords:
            if keyword in text_to_check:
                return False
        
        # Check minimum content length
        if len(content.body.strip()) < 50:
            return False
        
        # Check for educational indicators
        has_educational_content = any(
            keyword in text_to_check 
            for keyword in self.educational_keywords[:10]  # Check top educational keywords
        )
        
        return has_educational_content
    
    def detect_duplicates(self, new_content: Content, existing: List[Content]) -> bool:
        """
        Detect if new content is a duplicate of existing content.
        
        Args:
            new_content: New content to check
            existing: List of existing content
            
        Returns:
            True if duplicate detected, False otherwise
        """
        for existing_content in existing:
            # Check exact title match
            if new_content.title.strip().lower() == existing_content.title.strip().lower():
                return True
            
            # Check URL match
            if new_content.source_url == existing_content.source_url:
                return True
            
            # Check content similarity (simplified)
            if self._calculate_content_similarity(new_content.body, existing_content.body) > 0.8:
                return True
        
        return False
    
    def filter_content_batch(self, content_list: List[Content], user_level: str) -> List[Content]:
        """
        Filter a batch of content for quality and appropriateness.
        
        Args:
            content_list: List of content to filter
            user_level: User's proficiency level
            
        Returns:
            Filtered list of high-quality, appropriate content
        """
        filtered_content = []
        
        for content in content_list:
            # Check appropriateness
            if not self.check_appropriateness(content):
                continue
            
            # Check difficulty match
            if not self.match_difficulty_level(content, user_level):
                continue
            
            # Check educational value
            educational_value = self.evaluate_educational_value(content)
            if educational_value < 0.6:  # Minimum threshold
                continue
            
            # Check for duplicates in already filtered content
            if self.detect_duplicates(content, filtered_content):
                continue
            
            # Update content quality score
            content.quality_score = educational_value
            filtered_content.append(content)
        
        return filtered_content
    
    def _load_educational_keywords(self) -> List[str]:
        """Load keywords that indicate educational content."""
        return [
            "learn", "study", "education", "grammar", "vocabulary", "lesson",
            "practice", "exercise", "tutorial", "guide", "example", "explanation",
            "skill", "language", "comprehension", "reading", "writing", "speaking",
            "listening", "pronunciation", "conversation", "dialogue", "文法", "語彙",
            "練習", "勉強", "学習", "教育", "説明", "例文", "会話"
        ]
    
    def _load_inappropriate_keywords(self) -> List[str]:
        """Load keywords that indicate inappropriate content."""
        return [
            "violence", "adult", "explicit", "inappropriate", "offensive",
            "spam", "advertisement", "promotion", "sale", "buy now"
        ]
    
    def _load_difficulty_indicators(self) -> Dict[str, List[str]]:
        """Load indicators for different difficulty levels."""
        return {
            "CET-4": ["basic", "elementary", "beginner", "simple", "easy"],
            "CET-5": ["intermediate", "moderate", "standard", "regular"],
            "CET-6": ["advanced", "complex", "sophisticated", "challenging"],
            "N5": ["初級", "基本", "簡単", "やさしい"],
            "N4": ["初中級", "普通", "標準"],
            "N3": ["中級", "中程度"],
            "N2": ["中上級", "やや難しい"],
            "N1": ["上級", "高級", "難しい", "複雑"]
        }
    
    def _load_trusted_domains(self) -> Set[str]:
        """Load trusted educational domains."""
        return {
            "bbc.com", "voanews.com", "cambridge.org", "oxford.com",
            "nhk.or.jp", "jlpt.jp", "wasabi-jpn.com", "tofugu.com",
            "edu", "ac.jp", "ac.uk", "edu.cn"
        }
    
    def _calculate_educational_keyword_score(self, text: str) -> float:
        """Calculate score based on educational keywords."""
        keyword_count = sum(1 for keyword in self.educational_keywords if keyword in text)
        # Normalize by total number of keywords, cap at 1.0
        return min(1.0, keyword_count / 10.0)
    
    def _evaluate_content_structure(self, content: Content) -> float:
        """Evaluate content structure and organization."""
        score = 0.0
        
        # Check content length (appropriate for learning)
        body_length = len(content.body)
        if 100 <= body_length <= 2000:  # Good length for learning materials
            score += 0.5
        elif body_length > 50:  # At least some content
            score += 0.3
        
        # Check for structured content (paragraphs, sentences)
        sentence_count = len(re.findall(r'[.!?]+', content.body))
        if sentence_count >= 3:
            score += 0.3
        
        # Check title quality
        if len(content.title.strip()) > 5:
            score += 0.2
        
        return min(1.0, score)
    
    def _evaluate_source_reliability(self, url: str) -> float:
        """Evaluate source reliability based on domain."""
        domain = urlparse(url).netloc.lower()
        
        # Check trusted domains
        for trusted_domain in self.trusted_domains:
            if trusted_domain in domain:
                return 1.0
        
        # Check for educational indicators in domain
        if any(indicator in domain for indicator in ["edu", "learn", "study", "language"]):
            return 0.8
        
        # Default score for unknown domains
        return 0.5
    
    def _evaluate_content_type_appropriateness(self, content: Content) -> float:
        """Evaluate if content type is appropriate for learning."""
        appropriate_types = {
            ContentType.ARTICLE: 1.0,
            ContentType.NEWS: 0.9,
            ContentType.DIALOGUE: 1.0,
            ContentType.EXERCISE: 1.0,
            ContentType.CULTURAL: 0.8,
            ContentType.AUDIO: 0.9,
            ContentType.VIDEO: 0.8
        }
        
        return appropriate_types.get(content.content_type, 0.5)
    
    def _match_english_level(self, content_level: str, user_level: str) -> bool:
        """Match English proficiency levels."""
        level_hierarchy = ["CET-4", "CET-5", "CET-6", "CET-6+"]
        
        try:
            content_idx = level_hierarchy.index(content_level)
            user_idx = level_hierarchy.index(user_level)
            
            # Allow content at user level or one level above
            return content_idx <= user_idx + 1
        except ValueError:
            return False
    
    def _match_japanese_level(self, content_level: str, user_level: str) -> bool:
        """Match Japanese JLPT levels."""
        level_hierarchy = ["N5", "N4", "N3", "N2", "N1", "N1+"]
        
        try:
            content_idx = level_hierarchy.index(content_level)
            user_idx = level_hierarchy.index(user_level)
            
            # Allow content at user level or one level above
            return content_idx <= user_idx + 1
        except ValueError:
            return False
    
    def _calculate_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text contents."""
        # Simple similarity based on common words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0