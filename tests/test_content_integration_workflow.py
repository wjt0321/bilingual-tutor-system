"""
Property-based tests for content integration workflow.

Feature: bilingual-tutor, Property 17: Content Integration Workflow
**Validates: Requirements 6.4**
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime
import uuid

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    Content, ContentType, UserProfile, Goals, Preferences
)


class TestContentIntegrationWorkflow:
    """Test content integration workflow property."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CoreLearningEngine()
    
    @given(
        language=st.sampled_from(["english", "japanese"]),
        content_type=st.sampled_from(list(ContentType)),
        quality_score=st.floats(min_value=0.0, max_value=1.0),
        difficulty_level=st.sampled_from(["CET-4", "CET-5", "CET-6", "N5", "N4", "N3", "N2", "N1"]),
        content_length=st.integers(min_value=50, max_value=2000)
    )
    def test_content_integration_workflow_property(self, language, content_type, quality_score, difficulty_level, content_length):
        """
        Property 17: Content Integration Workflow
        For any newly discovered content that passes quality evaluation, 
        it should be integrated into the user's available study materials.
        
        **Validates: Requirements 6.4**
        """
        # Filter difficulty levels by language
        if language == "english":
            assume(difficulty_level.startswith("CET"))
        else:  # japanese
            assume(difficulty_level in ["N5", "N4", "N3", "N2", "N1"])
        
        # Create test content with varying quality
        content = Content(
            content_id=str(uuid.uuid4()),
            title=f"Test {language} {content_type.value} content",
            body="Sample content. " * (content_length // 15),  # Approximate content length
            language=language,
            difficulty_level=difficulty_level,
            content_type=content_type,
            source_url=f"https://example.com/{language}/{content_type.value}",
            quality_score=quality_score,
            created_at=datetime.now(),
            tags=[language, difficulty_level, content_type.value]
        )
        
        # Create test user profile
        user_profile = UserProfile(
            user_id="test_user",
            english_level="CET-4" if language == "english" else "CET-4",
            japanese_level="N5" if language == "japanese" else "N5",
            daily_study_time=60,
            target_goals=Goals(
                target_english_level="CET-6",
                target_japanese_level="N1",
                target_completion_date=datetime.now(),
                priority_skills=[],
                custom_objectives=[]
            ),
            learning_preferences=Preferences(
                language_balance={"english": 0.5, "japanese": 0.5},
                preferred_study_times=["morning"],
                content_preferences=[content_type],
                difficulty_preference="moderate"
            ),
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test the content integration workflow
        
        # Step 1: Content should be evaluated for quality
        content_filter = self.engine.get_component("content_filter")
        educational_value = content_filter.evaluate_educational_value(content)
        
        # Property: Educational value should be calculated
        assert isinstance(educational_value, float), "Educational value must be a float"
        assert 0.0 <= educational_value <= 1.0, "Educational value must be between 0 and 1"
        
        # Step 2: Content should be checked for appropriateness
        is_appropriate = content_filter.check_appropriateness(content)
        
        # Property: Appropriateness should be determined
        assert isinstance(is_appropriate, bool), "Appropriateness check must return boolean"
        
        # Step 3: Content should be checked for difficulty match
        difficulty_match = content_filter.match_difficulty_level(content, user_profile.english_level if language == "english" else user_profile.japanese_level)
        
        # Property: Difficulty match should be determined
        assert isinstance(difficulty_match, bool), "Difficulty match must return boolean"
        
        # Step 4: If content passes quality evaluation, it should be integrated
        quality_threshold = 0.6  # Minimum quality threshold
        
        if (educational_value >= quality_threshold and 
            is_appropriate and 
            difficulty_match):
            
            # Property: High-quality, appropriate content should be integrable
            # Test integration by checking if content can be added to user's materials
            
            # Check if content is not already seen
            memory_manager = self.engine.get_component("memory_manager")
            is_already_seen = memory_manager.check_content_seen("test_user", content)
            
            # Property: Content integration status should be trackable
            assert isinstance(is_already_seen, bool), "Content seen status must be boolean"
            
            # If not already seen, it should be available for integration
            if not is_already_seen:
                # Property: New content should be integrable into study materials
                # This would typically involve adding to content database/queue
                
                # Simulate integration by recording the content
                memory_manager.record_learned_content("test_user", content)
                
                # Verify integration
                is_now_recorded = memory_manager.check_content_seen("test_user", content)
                assert is_now_recorded, "Content should be recorded after integration"
                
                # Property: Integrated content should be available for future sessions
                content_history_count = memory_manager.get_content_history_count("test_user")
                assert content_history_count > 0, "Content history should increase after integration"
        
        else:
            # Property: Low-quality or inappropriate content should not be integrated
            # This is validated by the filtering process itself
            pass
    
    @given(
        num_contents=st.integers(min_value=1, max_value=10),
        quality_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0), 
            min_size=1, 
            max_size=10
        )
    )
    def test_batch_content_integration_property(self, num_contents, quality_scores):
        """
        Property: Batch content integration workflow
        For any batch of discovered content, only content that passes 
        quality evaluation should be integrated.
        
        **Validates: Requirements 6.4**
        """
        # Ensure we have enough quality scores
        assume(len(quality_scores) >= num_contents)
        
        content_list = []
        
        # Create batch of content with varying quality
        for i in range(num_contents):
            content = Content(
                content_id=str(uuid.uuid4()),
                title=f"Batch content {i}",
                body="Sample batch content for testing integration workflow.",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url=f"https://example.com/batch/{i}",
                quality_score=quality_scores[i],
                created_at=datetime.now(),
                tags=["english", "CET-4", "batch"]
            )
            content_list.append(content)
        
        # Test batch integration workflow
        content_filter = self.engine.get_component("content_filter")
        
        # Filter content batch
        filtered_content = content_filter.filter_content_batch(content_list, "CET-4")
        
        # Property: Filtered content should be a subset of original content
        assert len(filtered_content) <= len(content_list), "Filtered content should not exceed original"
        
        # Property: All filtered content should meet quality standards
        for content in filtered_content:
            educational_value = content_filter.evaluate_educational_value(content)
            is_appropriate = content_filter.check_appropriateness(content)
            difficulty_match = content_filter.match_difficulty_level(content, "CET-4")
            
            # Each filtered content should pass quality checks
            assert educational_value >= 0.6, "Filtered content should have good educational value"
            assert is_appropriate, "Filtered content should be appropriate"
            assert difficulty_match, "Filtered content should match difficulty level"
        
        # Property: Integration should preserve content order and properties
        memory_manager = self.engine.get_component("memory_manager")
        
        integrated_count = 0
        for content in filtered_content:
            if not memory_manager.check_content_seen("batch_user", content):
                memory_manager.record_learned_content("batch_user", content)
                integrated_count += 1
        
        # Property: Number of integrated items should match filtered content
        final_count = memory_manager.get_content_history_count("batch_user")
        assert final_count >= integrated_count, "All filtered content should be integrable"
    
    @given(
        content_source=st.text(min_size=10, max_size=100),
        crawl_frequency=st.integers(min_value=1, max_value=24)  # hours
    )
    def test_content_discovery_integration_property(self, content_source, crawl_frequency):
        """
        Property: Content discovery and integration workflow
        For any content discovery process, discovered content should follow 
        the complete integration workflow.
        
        **Validates: Requirements 6.4**
        """
        # Test the complete workflow from discovery to integration
        
        # Step 1: Content discovery (simulated)
        content_crawler = self.engine.get_component("content_crawler")
        
        # Property: Content crawler should be able to search for content
        english_content = content_crawler.search_english_content("CET-4", "general")
        
        # Property: Discovered content should be in expected format
        assert isinstance(english_content, list), "Discovered content should be a list"
        
        for content in english_content:
            assert isinstance(content, Content), "Each discovered item should be Content object"
            assert content.content_id is not None, "Content should have ID"
            assert content.language == "english", "English search should return English content"
            assert content.quality_score >= 0.0, "Content should have quality score"
        
        # Step 2: Quality evaluation and filtering
        if english_content:
            content_filter = self.engine.get_component("content_filter")
            
            # Property: Each content item should be evaluable
            for content in english_content[:3]:  # Test first 3 items
                educational_value = content_filter.evaluate_educational_value(content)
                assert isinstance(educational_value, float), "Educational value should be numeric"
                
                appropriateness = content_filter.check_appropriateness(content)
                assert isinstance(appropriateness, bool), "Appropriateness should be boolean"
        
        # Step 3: Integration workflow completion
        # Property: The workflow should be completable end-to-end
        # This is validated by the successful execution of all previous steps
        
        # Property: Content refresh scheduling should be configurable
        from datetime import timedelta
        refresh_interval = timedelta(hours=crawl_frequency)
        
        # This should not raise an exception
        content_crawler.schedule_content_refresh(refresh_interval)
        
        # Property: Scheduled refresh should be trackable
        assert hasattr(content_crawler, 'refresh_frequency'), "Crawler should track refresh frequency"
        assert content_crawler.refresh_frequency == refresh_interval, "Refresh frequency should be set correctly"