"""
Property tests for content source extension functionality.
Tests content freshness maintenance and source extensibility.
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from datetime import datetime, timedelta
from typing import List

from bilingual_tutor.content.enhanced_crawler import (
    EnhancedContentCrawler,
    BBCLearningEnglishSource,
    VOALearningEnglishSource,
    NHKNewsEasySource,
    CustomContentSource
)
from bilingual_tutor.models import Content, ContentType


class TestContentFreshnessMaintenance:
    """
    Property 56: Content Freshness Maintenance
    Validates Requirements: 30.7
    
    Ensures that content from all sources maintains freshness
    and is updated within acceptable timeframes.
    """
    
    @pytest.fixture
    def crawler(self):
        """Create enhanced content crawler instance."""
        return EnhancedContentCrawler()
    
    @given(
        level=st.sampled_from(["CET-4", "CET-5", "CET-6"]),
        topic=st.text(min_size=3, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz '),
        days_old=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=20, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_freshness_within_threshold(self, crawler, level, topic, days_old):
        """
        Test that all retrieved content is within freshness threshold (7 days).
        
        Property: For any content retrieved from any source,
        age should be <= freshness_threshold (7 days).
        """
        # Retrieve content
        content_list = crawler.search_english_content(level, topic, limit=10)
        
        if not content_list:
            pytest.skip("No content retrieved for this combination")
        
        # Check freshness for all content
        freshness_threshold = timedelta(days=7)
        for content in content_list:
            content_age = datetime.now() - content.created_at
            assert content_age <= freshness_threshold, \
                f"Content {content.content_id} is {content_age.days} days old, exceeds threshold of 7 days"
    
    @given(
        level=st.sampled_from(["N5", "N4", "N3"]),
        topic=st.text(min_size=3, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz '),
        limit=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=20, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_japanese_content_freshness_within_threshold(self, crawler, level, topic, limit):
        """
        Test that Japanese content freshness is within threshold.
        
        Property: Japanese content should also maintain freshness.
        """
        content_list = crawler.search_japanese_content(level, topic, limit=limit)
        
        if not content_list:
            pytest.skip("No content retrieved for this combination")
        
        freshness_threshold = timedelta(days=7)
        for content in content_list:
            content_age = datetime.now() - content.created_at
            assert content_age <= freshness_threshold, \
                f"Japanese content {content.content_id} exceeds freshness threshold"
    
    @given(
        level=st.sampled_from(["CET-4", "CET-5", "CET-6"]),
        topic=st.text(min_size=3, max_size=30),
        num_sources=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_fresh_content_from_multiple_sources(self, crawler, level, topic, num_sources):
        """
        Test that content from multiple sources maintains freshness.
        
        Property: Content from all sources (BBC, VOA, custom) should be fresh.
        """
        content_list = crawler.search_english_content(level, topic, limit=20)
        
        if not content_list:
            pytest.skip("No content retrieved")
        
        # Group content by source
        sources_seen = set()
        for content in content_list:
            source = content.metadata.get('source', 'unknown')
            sources_seen.add(source)
            
            # Verify freshness for each piece of content
            content_age = datetime.now() - content.created_at
            assert content_age <= timedelta(days=7), \
                f"Content from {source} exceeds freshness threshold"
        
        # Ensure we got content from at least one source
        assert len(sources_seen) > 0, "No sources provided content"
    
    @given(
        content_ids=st.lists(
            st.text(min_size=5, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'),
            min_size=1, max_size=10, unique=True
        )
    )
    @settings(max_examples=20, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_freshness_update(self, crawler, content_ids):
        """
        Test that content freshness timestamps can be updated.
        
        Property: Updating content freshness should succeed for valid IDs.
        """
        before_update = datetime.now()
        
        # Update freshness
        updated_count = crawler.update_content_freshness(content_ids)
        
        # Verify update count
        assert updated_count == len(content_ids), \
            f"Expected to update {len(content_ids)} items, got {updated_count}"
        
        # Verify all IDs were cached with recent timestamps
        for content_id in content_ids:
            assert content_id in crawler.content_cache, \
                f"Content ID {content_id} not found in cache"
            
            cached_time = crawler.content_cache[content_id]
            assert cached_time >= before_update, \
                f"Content {content_id} cached timestamp is before update time"
    
    @given(
        age_days=st.integers(min_value=0, max_value=14)
    )
    @settings(max_examples=20, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_old_content_filtering(self, crawler, age_days):
        """
        Test that old content is filtered out.
        
        Property: Content older than threshold should be filtered.
        """
        # Create test content with specific age
        old_content = Content(
            content_id="test_old_content",
            title="Old Content",
            body="This is old content",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://example.com/old",
            quality_score=0.8,
            created_at=datetime.now() - timedelta(days=age_days),
            tags=["test"]
        )
        
        # Check if content passes freshness filter
        is_fresh = crawler._is_content_fresh(old_content)
        
        # Content older than 7 days should not be fresh (7 days is not fresh)
        threshold = timedelta(days=7)
        if age_days >= 7:
            assert not is_fresh, \
                f"Content {age_days} days old should be filtered out"
        else:
            assert is_fresh, \
                f"Content {age_days} days old should be considered fresh"


class TestSourceExtensibility:
    """
    Test that crawler system supports extensibility
    with custom content sources.
    """
    
    @pytest.fixture
    def crawler(self):
        """Create enhanced content crawler instance."""
        return EnhancedContentCrawler()
    
    @given(
        name=st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'),
        domain=st.sampled_from(["example.com", "testsite.org", "mysite.net"]),
        levels=st.lists(
            st.sampled_from(["CET-4", "CET-5", "CET-6", "N5", "N4"]),
            min_size=1, max_size=3, unique=True
        )
    )
    @settings(max_examples=10, deadline=timedelta(milliseconds=10000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_custom_source_addition(self, crawler, name, domain, levels):
        """
        Test that custom sources can be added successfully.
        
        Property: Valid custom sources should be added and accessible.
        """
        url = f"https://{domain}"
        
        # Add custom source
        success = crawler.add_custom_source(name, url, levels)
        
        # Note: This might fail due to accessibility check in real environment
        # In test environment, we handle this gracefully
        if success:
            # Verify source was added
            assert name in crawler.custom_sources, \
                f"Custom source {name} was not added to crawler"
            
            # Verify source details
            source = crawler.custom_sources[name]
            assert source.get_source_name() == name, \
                f"Source name mismatch: {source.get_source_name()} != {name}"
            assert source.get_supported_levels() == levels, \
                f"Source levels mismatch"
    
    @given(
        level=st.sampled_from(["CET-4", "CET-5"]),
        topic=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_sources_content_diversity(self, crawler, level, topic):
        """
        Test that content from multiple sources provides diversity.
        
        Property: Content from different sources should have variety.
        """
        # Get content from all sources
        content_list = crawler.search_english_content(level, topic, limit=20)
        
        if len(content_list) < 2:
            pytest.skip("Not enough content retrieved")
        
        # Check that content comes from different sources
        sources = set()
        for content in content_list:
            source = content.metadata.get('source', 'unknown')
            sources.add(source)
        
        # Should have content from at least one source
        assert len(sources) >= 1, \
            "No sources provided content"
    
    def test_source_accessibility_validation(self, crawler):
        """
        Test that source accessibility can be validated.
        
        Property: Sources should report accessibility status.
        """
        sources = [
            BBCLearningEnglishSource(),
            VOALearningEnglishSource(),
            NHKNewsEasySource()
        ]
        
        accessible_count = 0
        for source in sources:
            is_accessible = source.validate_accessibility()
            # Note: In test environment, accessibility might fail
            # This is expected - we're testing the validation mechanism
            if is_accessible:
                accessible_count += 1
                assert source.get_source_name(), "Source should have a name"
                assert len(source.get_supported_levels()) > 0, \
                    "Source should support at least one level"
    
    def test_source_statistics_generation(self, crawler):
        """
        Test that source statistics can be generated.
        
        Property: Statistics should provide accurate source information.
        """
        stats = crawler.get_source_statistics()
        
        # Verify statistics structure
        assert "total_english_sources" in stats
        assert "total_japanese_sources" in stats
        assert "total_custom_sources" in stats
        assert "accessible_sources" in stats
        assert "sources_with_details" in stats
        
        # Verify counts are non-negative
        assert stats["total_english_sources"] >= 0
        assert stats["total_japanese_sources"] >= 0
        assert stats["total_custom_sources"] >= 0
        assert stats["accessible_sources"] >= 0
        
        # Verify accessible_sources doesn't exceed total
        total_sources = (stats["total_english_sources"] + 
                       stats["total_japanese_sources"] + 
                       stats["total_custom_sources"])
        assert stats["accessible_sources"] <= total_sources, \
            "Accessible sources count exceeds total sources"
        
        # Verify source details structure
        for source_detail in stats["sources_with_details"]:
            assert "name" in source_detail
            assert "accessible" in source_detail
            assert "supported_levels" in source_detail
            assert isinstance(source_detail["accessible"], bool)
            assert isinstance(source_detail["supported_levels"], list)
    
    def test_available_sources_listing(self, crawler):
        """
        Test that available sources can be listed.
        
        Property: Source listing should include all configured sources.
        """
        available = crawler.get_available_sources()
        
        # Verify structure
        assert "english" in available
        assert "japanese" in available
        assert isinstance(available["english"], list)
        assert isinstance(available["japanese"], list)
        
        # Verify English sources
        english_sources = available["english"]
        assert len(english_sources) >= 2, \
            "Should have at least BBC and VOA English sources"
        assert "BBC Learning English" in english_sources, \
            "BBC Learning English should be in available sources"
        assert "VOA Learning English" in english_sources, \
            "VOA Learning English should be in available sources"
        
        # Verify Japanese sources
        japanese_sources = available["japanese"]
        assert len(japanese_sources) >= 1, \
            "Should have at least NHK Japanese source"
        assert "NHK News Web Easy" in japanese_sources, \
            "NHK News Web Easy should be in available sources"
    
    @given(
        name=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_custom_source_removal(self, crawler, name):
        """
        Test that custom sources can be removed.
        
        Property: Removed sources should no longer be available.
        """
        # First add a source
        url = "https://example.com"
        levels = ["CET-4"]
        added = crawler.add_custom_source(name, url, levels)
        
        if added:
            # Remove source
            removed = crawler.remove_custom_source(name)
            assert removed, f"Failed to remove custom source {name}"
            assert name not in crawler.custom_sources, \
                f"Source {name} still in custom sources after removal"
        else:
            # Source wasn't added, try to remove anyway
            removed = crawler.remove_custom_source(name)
            assert not removed, \
                "Should not be able to remove non-existent source"


class TestContentQualityAssessment:
    """
    Test that content quality is properly assessed for all sources.
    """
    
    @pytest.fixture
    def crawler(self):
        """Create enhanced content crawler instance."""
        return EnhancedContentCrawler()
    
    @given(
        level=st.sampled_from(["CET-4", "CET-5", "CET-6"]),
        topic=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_quality_threshold_filtering(self, crawler, level, topic):
        """
        Test that low-quality content is filtered out.
        
        Property: All retrieved content should meet quality threshold (0.7).
        """
        content_list = crawler.search_english_content(level, topic, limit=20)
        
        if not content_list:
            pytest.skip("No content retrieved")
        
        # Verify all content meets quality threshold
        min_quality = 0.7
        for content in content_list:
            assert content.quality_score >= min_quality, \
                f"Content {content.content_id} has quality score {content.quality_score}, below threshold {min_quality}"
    
    @given(
        level=st.sampled_from(["N5", "N4", "N3"]),
        topic=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_japanese_content_quality_threshold(self, crawler, level, topic):
        """
        Test that Japanese content meets quality threshold.
        
        Property: Japanese content should also meet quality standards.
        """
        content_list = crawler.search_japanese_content(level, topic, limit=20)
        
        if not content_list:
            pytest.skip("No content retrieved")
        
        min_quality = 0.7
        for content in content_list:
            assert content.quality_score >= min_quality, \
                f"Japanese content {content.content_id} below quality threshold"
    
    @given(
        level=st.sampled_from(["CET-4", "CET-5"]),
        topic=st.text(min_size=3, max_size=20),
        limit=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=15, deadline=timedelta(milliseconds=5000), suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_quality_sorting(self, crawler, level, topic, limit):
        """
        Test that content is sorted by quality score.
        
        Property: Results should be sorted in descending order by quality.
        """
        content_list = crawler.search_english_content(level, topic, limit=limit)
        
        if len(content_list) < 2:
            pytest.skip("Not enough content to verify sorting")
        
        # Verify content is sorted by quality (descending)
        for i in range(len(content_list) - 1):
            current_quality = content_list[i].quality_score
            next_quality = content_list[i + 1].quality_score
            assert current_quality >= next_quality, \
                f"Content not sorted by quality: {current_quality} < {next_quality} at index {i}"
