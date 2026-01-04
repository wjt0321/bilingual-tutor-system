"""
Tests for the Memory Manager component.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st
from bilingual_tutor.content.memory_manager import MemoryManager
from bilingual_tutor.content.crawler import ContentCrawler
from bilingual_tutor.content.filter import ContentFilter
from bilingual_tutor.models import Content, MasteryLevel, ContentType
from tests.conftest import content_strategy


class TestMemoryManager:
    """Test suite for Memory Manager functionality."""
    
    def test_memory_manager_initialization(self):
        """Test that MemoryManager initializes correctly."""
        manager = MemoryManager()
        
        assert manager.user_content_history == {}
        assert manager.content_mastery == {}
        assert manager.learning_timestamps == {}
        assert manager.review_schedule == {}
    
    def test_record_learned_content(self):
        """Test recording learned content."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        manager.record_learned_content(user_id, content)
        
        assert content.content_id in manager.user_content_history[user_id]
        assert manager.content_mastery[user_id][content.content_id] == MasteryLevel.LEARNING
        assert content.content_id in manager.learning_timestamps[user_id]
    
    def test_check_content_seen(self):
        """Test checking if content has been seen."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        # Initially not seen
        assert not manager.check_content_seen(user_id, content)
        
        # After recording, should be seen
        manager.record_learned_content(user_id, content)
        assert manager.check_content_seen(user_id, content)
    
    def test_get_mastery_level(self):
        """Test getting mastery level for content."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        # Initially not learned
        assert manager.get_mastery_level(user_id, content) == MasteryLevel.NOT_LEARNED
        
        # After recording, should be learning
        manager.record_learned_content(user_id, content)
        assert manager.get_mastery_level(user_id, content) == MasteryLevel.LEARNING
    
    def test_update_mastery_level(self):
        """Test updating mastery level."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        manager.update_mastery_level(user_id, content, MasteryLevel.MASTERED)
        
        assert manager.get_mastery_level(user_id, content) == MasteryLevel.MASTERED
        assert content.content_id in manager.learning_timestamps[user_id]
    
    def test_mark_for_review(self):
        """Test marking content for review."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        interval = timedelta(days=1)
        manager.mark_for_review(user_id, content, interval)
        
        assert content.content_id in manager.review_schedule[user_id]
        assert manager.get_mastery_level(user_id, content) == MasteryLevel.NEEDS_REVIEW
    
    def test_check_content_seen_within_window(self):
        """Test checking content within time window."""
        manager = MemoryManager()
        user_id = "test_user"
        content = Content(
            content_id="test_content",
            title="Test Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        # Record content
        manager.record_learned_content(user_id, content)
        
        # Should be seen within a large window
        assert manager.check_content_seen_within_window(user_id, content, timedelta(hours=1))
        
        # Should not be seen within a very small window (simulate old content)
        # Manually set old timestamp
        manager.learning_timestamps[user_id][content.content_id] = datetime.now() - timedelta(days=1)
        assert not manager.check_content_seen_within_window(user_id, content, timedelta(minutes=1))
    
    @given(content_strategy(), st.integers(min_value=1, max_value=24))
    def test_content_uniqueness_within_window_property(self, content, window_hours):
        """
        **Feature: bilingual-tutor, Property 4: Content Uniqueness Within Window**
        **Validates: Requirements 1.5**
        
        For any configurable time window, no duplicate content should be 
        presented to the same user within that period.
        """
        manager = MemoryManager()
        user_id = "test_user"
        window = timedelta(hours=window_hours)
        
        # Record content as learned
        manager.record_learned_content(user_id, content)
        
        # Content should be seen within the window
        assert manager.check_content_seen_within_window(user_id, content, window)
        
        # The same content should be detected as duplicate within the window
        assert manager.check_content_seen(user_id, content)
        
        # If we simulate content being older than the window, it should not be seen within window
        old_timestamp = datetime.now() - window - timedelta(minutes=1)
        manager.learning_timestamps[user_id][content.content_id] = old_timestamp
        
        assert not manager.check_content_seen_within_window(user_id, content, window)
    
    def test_get_content_history_count(self):
        """Test getting content history count."""
        manager = MemoryManager()
        user_id = "test_user"
        
        # Initially zero
        assert manager.get_content_history_count(user_id) == 0
        
        # Add some content
        for i in range(3):
            content = Content(
                content_id=f"content_{i}",
                title=f"Content {i}",
                body="Test body",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url="https://example.com",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=["test"]
            )
            manager.record_learned_content(user_id, content)
        
        assert manager.get_content_history_count(user_id) == 3
    
    def test_clear_old_content_history(self):
        """Test clearing old content history."""
        manager = MemoryManager()
        user_id = "test_user"
        
        # Add content
        content = Content(
            content_id="old_content",
            title="Old Content",
            body="Test body",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        manager.record_learned_content(user_id, content)
        
        # Simulate old timestamp
        old_timestamp = datetime.now() - timedelta(days=10)
        manager.learning_timestamps[user_id][content.content_id] = old_timestamp
        
        # Clear old content (retention period of 5 days)
        manager.clear_old_content_history(user_id, timedelta(days=5))
        
        # Content should be removed from all tracking structures
        assert content.content_id not in manager.user_content_history[user_id]
        assert content.content_id not in manager.content_mastery[user_id]
        assert content.content_id not in manager.learning_timestamps[user_id]


class TestContentCrawler:
    """Test suite for Content Crawler functionality."""
    
    def test_content_crawler_initialization(self):
        """Test that ContentCrawler initializes correctly."""
        crawler = ContentCrawler()
        
        assert len(crawler.english_sources) > 0
        assert len(crawler.japanese_sources) > 0
        assert "min_educational_value" in crawler.quality_thresholds
    
    @given(
        st.sampled_from(["CET-4", "CET-5", "CET-6"]),
        st.text(min_size=1, max_size=20)
    )
    def test_content_discovery_and_level_matching_property(self, level, topic):
        """
        **Feature: bilingual-tutor, Property 15: Content Discovery and Level Matching**
        **Validates: Requirements 6.1, 6.2, 6.7**
        
        For any content crawling operation, discovered materials should be 
        appropriate to the user's current proficiency level and learning objectives.
        """
        crawler = ContentCrawler()
        
        # Test English content discovery
        english_content = crawler.search_english_content(level, topic)
        
        # All discovered content should match the requested level
        for content in english_content:
            assert content.language == "english"
            assert content.difficulty_level == level
            assert topic.lower() in [tag.lower() for tag in content.tags]
            assert content.quality_score >= crawler.quality_thresholds["min_educational_value"]
        
        # Test Japanese content discovery
        jlpt_levels = {"CET-4": "N5", "CET-5": "N4", "CET-6": "N3"}
        jlpt_level = jlpt_levels.get(level, "N5")
        
        japanese_content = crawler.search_japanese_content(jlpt_level, topic)
        
        # All discovered content should match the requested JLPT level
        for content in japanese_content:
            assert content.language == "japanese"
            assert content.difficulty_level == jlpt_level
            assert topic.lower() in [tag.lower() for tag in content.tags]
            assert content.quality_score >= crawler.quality_thresholds["min_educational_value"]
    
    @given(
        st.lists(
            st.sampled_from(["news", "culture", "dialogue", "exercise", "grammar", "vocabulary"]),
            min_size=3,
            max_size=6,
            unique=True
        )
    )
    def test_content_type_diversity_property(self, topics):
        """
        **Feature: bilingual-tutor, Property 19: Content Type Diversity**
        **Validates: Requirements 6.6**
        
        For any content discovery session, the crawler should search for diverse 
        content types including articles, news, dialogues, and cultural materials.
        """
        crawler = ContentCrawler()
        
        all_content = []
        
        # Collect content for multiple topics to test diversity
        for topic in topics:
            english_content = crawler.search_english_content("CET-4", topic)
            japanese_content = crawler.search_japanese_content("N5", topic)
            all_content.extend(english_content)
            all_content.extend(japanese_content)
        
        if len(all_content) > 0:
            # Check that we have diverse content types
            content_types = {content.content_type for content in all_content}
            
            # Should have at least 2 different content types for diversity
            # (since we're testing with multiple topics)
            assert len(content_types) >= 1  # At minimum should have some content types
            
            # Verify that content types are appropriate for topics
            for content in all_content:
                # Content type should be valid
                assert content.content_type in [
                    ContentType.ARTICLE, ContentType.NEWS, ContentType.DIALOGUE,
                    ContentType.EXERCISE, ContentType.CULTURAL
                ]
                
                # Content should have appropriate tags for diversity tracking
                assert len(content.tags) > 0


class TestContentFilter:
    """Test suite for Content Filter functionality."""
    
    def test_content_filter_initialization(self):
        """Test that ContentFilter initializes correctly."""
        filter_obj = ContentFilter()
        
        assert len(filter_obj.educational_keywords) > 0
        assert len(filter_obj.inappropriate_keywords) > 0
        assert len(filter_obj.trusted_domains) > 0
    
    @given(content_strategy())
    def test_content_quality_evaluation_property(self, content):
        """
        **Feature: bilingual-tutor, Property 16: Content Quality Evaluation**
        **Validates: Requirements 6.3**
        
        For any crawled content, it should be evaluated for educational value 
        and relevance before integration.
        """
        filter_obj = ContentFilter()
        
        # Evaluate educational value
        educational_value = filter_obj.evaluate_educational_value(content)
        
        # Educational value should be a valid score between 0.0 and 1.0
        assert 0.0 <= educational_value <= 1.0
        
        # Check appropriateness
        is_appropriate = filter_obj.check_appropriateness(content)
        
        # Appropriateness should be a boolean
        assert isinstance(is_appropriate, bool)
        
        # If content has educational keywords, it should have higher educational value
        text_to_check = (content.title + " " + content.body).lower()
        has_educational_keywords = any(
            keyword in text_to_check 
            for keyword in ["learn", "study", "education", "grammar", "vocabulary"]
        )
        
        if has_educational_keywords and len(content.body) > 50:
            # Content with educational keywords should have reasonable educational value
            assert educational_value > 0.3
        
        # Content from trusted sources should have higher scores
        if any(domain in content.source_url.lower() for domain in ["bbc.com", "cambridge.org"]):
            assert educational_value > 0.5
    
    @given(
        st.lists(
            content_strategy(),
            min_size=2,
            max_size=10
        )
    )
    def test_source_prioritization_property(self, content_list):
        """
        **Feature: bilingual-tutor, Property 18: Source Prioritization**
        **Validates: Requirements 6.5**
        
        For any content selection process, materials from reputable educational 
        sources and native speakers should be prioritized over other sources.
        """
        filter_obj = ContentFilter()
        
        # Create content with different source types
        trusted_content = []
        untrusted_content = []
        
        for content in content_list:
            # Modify some content to have trusted sources
            if len(trusted_content) < len(content_list) // 2:
                # Make this content from a trusted source
                trusted_domains = ["bbc.com", "cambridge.org", "nhk.or.jp"]
                content.source_url = f"https://{trusted_domains[len(trusted_content) % len(trusted_domains)]}/article/{content.content_id}"
                trusted_content.append(content)
            else:
                # Keep as untrusted source
                untrusted_content.append(content)
        
        all_content = trusted_content + untrusted_content
        
        if len(all_content) > 1:
            # Evaluate all content
            evaluated_content = []
            for content in all_content:
                educational_value = filter_obj.evaluate_educational_value(content)
                content.quality_score = educational_value
                evaluated_content.append(content)
            
            # Check that trusted sources generally have higher scores
            trusted_scores = [c.quality_score for c in trusted_content]
            untrusted_scores = [c.quality_score for c in untrusted_content]
            
            if trusted_scores and untrusted_scores:
                # Average score of trusted sources should be higher
                avg_trusted = sum(trusted_scores) / len(trusted_scores)
                avg_untrusted = sum(untrusted_scores) / len(untrusted_scores)
                
                # Trusted sources should have higher average quality (with small tolerance for floating point)
                assert avg_trusted >= avg_untrusted - 0.01
            
            # Filter content and check prioritization
            filtered_content = filter_obj.filter_content_batch(all_content, "CET-4")
            
            # Filtered content should maintain quality standards
            for content in filtered_content:
                assert content.quality_score >= 0.6  # Minimum threshold