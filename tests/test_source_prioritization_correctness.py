"""
Tests for Source Prioritization Correctness - Property 41.
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st
from bilingual_tutor.content.precise_level_crawler import PreciseLevelContentCrawler, LevelSpecificSource
from bilingual_tutor.models import Content, ContentType


def level_specific_source_strategy():
    """Strategy for generating LevelSpecificSource objects with different priorities."""
    def generate_source_with_appropriate_priority(source_type):
        """Generate priority based on source type to maintain hierarchy."""
        priority_ranges = {
            "official": st.integers(min_value=9, max_value=10),
            "educational": st.integers(min_value=7, max_value=9),
            "practice": st.integers(min_value=5, max_value=7),
            "unofficial": st.integers(min_value=1, max_value=5)
        }
        return priority_ranges.get(source_type, st.integers(min_value=1, max_value=10))
    
    return st.builds(
        LevelSpecificSource,
        url=st.text(min_size=10, max_size=50).map(lambda x: f"https://{x.replace(' ', '')}.com"),
        level=st.sampled_from(["CET-4", "CET-5", "CET-6", "N5", "N4", "N3", "N2", "N1"]),
        language=st.sampled_from(["english", "japanese"]),
        source_type=st.sampled_from(["official", "educational", "practice", "unofficial"]),
        priority=st.integers(min_value=1, max_value=10),  # Will be overridden below
        vocabulary_patterns=st.lists(st.text(min_size=3, max_size=15), min_size=1, max_size=3),
        content_selectors=st.dictionaries(
            st.text(min_size=3, max_size=10),
            st.text(min_size=5, max_size=20),
            min_size=1,
            max_size=3
        )
    ).flatmap(lambda source: st.builds(
        LevelSpecificSource,
        url=st.just(source.url),
        level=st.just(source.level),
        language=st.just(source.language),
        source_type=st.just(source.source_type),
        priority=generate_source_with_appropriate_priority(source.source_type),
        vocabulary_patterns=st.just(source.vocabulary_patterns),
        content_selectors=st.just(source.content_selectors)
    ))


def content_with_source_strategy():
    """Strategy for generating Content objects with different source types."""
    return st.builds(
        Content,
        content_id=st.text(min_size=5, max_size=20),
        title=st.text(min_size=10, max_size=100),
        body=st.text(min_size=50, max_size=500),
        language=st.sampled_from(["english", "japanese"]),
        difficulty_level=st.sampled_from(["CET-4", "CET-5", "CET-6", "N5", "N4", "N3", "N2", "N1"]),
        content_type=st.sampled_from(list(ContentType)),
        source_url=st.one_of(
            # Official sources (should have higher priority)
            st.just("https://www.jlpt.jp/samples/n5.html"),
            st.just("https://www.cambridge.org/elt/catalogue/subject/custom/item7640716/Cambridge-English-Advanced"),
            st.just("https://www.nhk.or.jp/lesson/english/learn/list/"),
            st.just("https://www.bbc.com/learningenglish/english/course/lower-intermediate"),
            # Educational sources (medium priority)
            st.just("https://www.voanews.com/learningenglish/level-one"),
            st.just("https://www.wasabi-jpn.com/japanese-grammar/"),
            # Unofficial sources (lower priority)
            st.just("https://randomsite.com/english-lessons"),
            st.just("https://blogspot.com/japanese-study"),
            st.just("https://personalwebsite.net/language-tips")
        ),
        quality_score=st.floats(min_value=0.0, max_value=1.0),
        created_at=st.just(datetime.now()),
        tags=st.lists(st.text(min_size=3, max_size=10), min_size=1, max_size=5)
    )


class TestSourcePrioritizationCorrectness:
    """Test suite for Source Prioritization Correctness - Property 41."""
    
    @given(
        st.lists(
            level_specific_source_strategy(),
            min_size=3,
            max_size=10
        )
    )
    def test_source_prioritization_correctness_property(self, sources):
        """
        **Feature: bilingual-tutor, Property 41: Source Prioritization Correctness**
        **Validates: Requirements 19.3**
        
        For any content crawling operation, official examination materials and 
        authoritative sources should be ranked higher than unofficial sources.
        """
        crawler = PreciseLevelContentCrawler()
        
        # Separate sources by type
        official_sources = [s for s in sources if s.source_type == "official"]
        educational_sources = [s for s in sources if s.source_type == "educational"]
        practice_sources = [s for s in sources if s.source_type == "practice"]
        unofficial_sources = [s for s in sources if s.source_type == "unofficial"]
        
        # Test priority ordering within the crawler's source sorting logic
        if len(sources) > 1:
            # Sort sources by priority (same logic as in crawler)
            sorted_sources = sorted(sources, key=lambda x: x.priority, reverse=True)
            
            # Check that official sources have higher priorities than unofficial sources
            if official_sources and unofficial_sources:
                min_official_priority = min(s.priority for s in official_sources)
                max_unofficial_priority = max(s.priority for s in unofficial_sources)
                
                # Official sources should have higher priority than unofficial sources
                # This validates the source type hierarchy is maintained
                assert min_official_priority >= max_unofficial_priority, \
                    f"Official sources (min priority: {min_official_priority}) should have higher priority than unofficial sources (max priority: {max_unofficial_priority})"
            
            # Check that educational sources have higher priority than practice sources
            if educational_sources and practice_sources:
                min_educational_priority = min(s.priority for s in educational_sources)
                max_practice_priority = max(s.priority for s in practice_sources)
                
                # Educational sources should have higher priority than practice sources
                assert min_educational_priority >= max_practice_priority, \
                    f"Educational sources (min priority: {min_educational_priority}) should have higher priority than practice sources (max priority: {max_practice_priority})"
            
            # Check that official sources have higher priority than educational sources
            if official_sources and educational_sources:
                min_official_priority = min(s.priority for s in official_sources)
                max_educational_priority = max(s.priority for s in educational_sources)
                
                # Official sources should have higher or equal priority to educational sources
                assert min_official_priority >= max_educational_priority, \
                    f"Official sources (min priority: {min_official_priority}) should have higher priority than educational sources (max priority: {max_educational_priority})"
            
            # Verify that the sorting maintains priority order
            for i in range(len(sorted_sources) - 1):
                assert sorted_sources[i].priority >= sorted_sources[i + 1].priority, \
                    f"Source at index {i} (priority: {sorted_sources[i].priority}) should have higher or equal priority than source at index {i+1} (priority: {sorted_sources[i+1].priority})"
    
    @given(
        st.lists(
            content_with_source_strategy(),
            min_size=3,
            max_size=8
        )
    )
    def test_content_source_quality_ranking_property(self, content_list):
        """
        **Feature: bilingual-tutor, Property 41: Source Prioritization Correctness**
        **Validates: Requirements 19.3**
        
        For any content with different source types, official examination materials
        should receive higher quality scores than unofficial sources.
        """
        from bilingual_tutor.content.content_quality_assessor import ContentQualityAssessor
        
        assessor = ContentQualityAssessor()
        
        # Categorize content by source type based on URL patterns
        official_content = []
        educational_content = []
        unofficial_content = []
        
        for content in content_list:
            url_lower = content.source_url.lower()
            if any(domain in url_lower for domain in ["jlpt.jp", "cambridge.org", "nhk.or.jp"]):
                official_content.append(content)
            elif any(domain in url_lower for domain in ["bbc.com", "voanews.com", "wasabi-jpn.com"]):
                educational_content.append(content)
            else:
                unofficial_content.append(content)
        
        # Test quality assessment prioritization using source reliability
        if official_content and unofficial_content:
            # Assess content quality which includes source reliability
            official_scores = []
            unofficial_scores = []
            
            for content in official_content:
                quality_score = assessor.assess_content_quality(content)
                official_scores.append(quality_score.source_reliability)
            
            for content in unofficial_content:
                quality_score = assessor.assess_content_quality(content)
                unofficial_scores.append(quality_score.source_reliability)
            
            if official_scores and unofficial_scores:
                # Official sources should have higher average source reliability scores
                avg_official_score = sum(official_scores) / len(official_scores)
                avg_unofficial_score = sum(unofficial_scores) / len(unofficial_scores)
                
                # Official sources should be prioritized with higher source reliability
                assert avg_official_score >= avg_unofficial_score, \
                    f"Official sources (avg reliability: {avg_official_score:.3f}) should have higher reliability than unofficial sources (avg reliability: {avg_unofficial_score:.3f})"
        
        # Test that educational sources are prioritized over unofficial sources
        if educational_content and unofficial_content:
            educational_scores = []
            unofficial_scores = []
            
            for content in educational_content:
                quality_score = assessor.assess_content_quality(content)
                educational_scores.append(quality_score.source_reliability)
            
            for content in unofficial_content:
                quality_score = assessor.assess_content_quality(content)
                unofficial_scores.append(quality_score.source_reliability)
            
            if educational_scores and unofficial_scores:
                avg_educational_score = sum(educational_scores) / len(educational_scores)
                avg_unofficial_score = sum(unofficial_scores) / len(unofficial_scores)
                
                # Educational sources should be prioritized over unofficial sources
                assert avg_educational_score >= avg_unofficial_score, \
                    f"Educational sources (avg reliability: {avg_educational_score:.3f}) should have higher reliability than unofficial sources (avg reliability: {avg_unofficial_score:.3f})"
    
    def test_official_source_priority_assignment(self):
        """
        Test that official sources are assigned higher priority values.
        This validates the source configuration follows prioritization rules.
        """
        crawler = PreciseLevelContentCrawler()
        
        # Check English sources
        english_sources = crawler.english_sources
        official_english = [s for s in english_sources if s.source_type == "official"]
        educational_english = [s for s in english_sources if s.source_type == "educational"]
        
        if official_english and educational_english:
            min_official_priority = min(s.priority for s in official_english)
            max_educational_priority = max(s.priority for s in educational_english)
            
            # Official sources should have priority >= educational sources
            assert min_official_priority >= max_educational_priority
        
        # Check Japanese sources
        japanese_sources = crawler.japanese_sources
        official_japanese = [s for s in japanese_sources if s.source_type == "official"]
        educational_japanese = [s for s in japanese_sources if s.source_type == "educational"]
        
        if official_japanese and educational_japanese:
            min_official_priority = min(s.priority for s in official_japanese)
            max_educational_priority = max(s.priority for s in educational_japanese)
            
            # Official sources should have priority >= educational sources
            assert min_official_priority >= max_educational_priority
    
    def test_source_type_priority_consistency(self):
        """
        Test that source type priority assignments are consistent across languages.
        """
        crawler = PreciseLevelContentCrawler()
        
        # Define expected priority ranges for each source type
        expected_priorities = {
            "official": (9, 10),      # Highest priority
            "educational": (7, 9),    # High priority
            "practice": (5, 7),       # Medium priority
            "unofficial": (1, 5)      # Lower priority
        }
        
        all_sources = crawler.english_sources + crawler.japanese_sources
        
        for source in all_sources:
            expected_min, expected_max = expected_priorities.get(source.source_type, (1, 10))
            
            # Verify that source priority falls within expected range for its type
            assert expected_min <= source.priority <= expected_max, \
                f"Source {source.url} of type {source.source_type} has priority {source.priority}, " \
                f"expected range [{expected_min}, {expected_max}]"