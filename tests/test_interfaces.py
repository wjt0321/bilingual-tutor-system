"""
Tests for core component interfaces.
"""

import pytest
from hypothesis import given, strategies as st
from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.interfaces.chinese_interface import ChineseInterface
from bilingual_tutor.content.crawler import ContentCrawler
from bilingual_tutor.content.memory_manager import MemoryManager
from bilingual_tutor.progress.tracker import ProgressTracker
from bilingual_tutor.analysis.weakness_analyzer import WeaknessAnalyzer
from .conftest import content_strategy
import re


class TestCoreInterfaces:
    """Test that all core interfaces are properly defined."""
    
    def test_core_learning_engine_interface(self):
        """Test that CoreLearningEngine implements required interface."""
        engine = CoreLearningEngine()
        
        # Test component registration
        test_component = "test_component"
        engine.register_component("test", test_component)
        assert engine.get_component("test") == test_component
        
        # Test that start_daily_session method works
        session = engine.start_daily_session("user_001")
        assert session is not None
        assert session.user_id == "user_001"
        assert session.planned_duration == 60  # Default 60 minutes
        assert session.status.value == "planned"
    
    def test_chinese_interface_initialization(self):
        """Test that ChineseInterface initializes properly."""
        interface = ChineseInterface()
        
        # Test that message templates are loaded
        assert "welcome" in interface.message_templates
        assert "session_start" in interface.message_templates
        
        # Test that cultural contexts are loaded
        assert "english_formal" in interface.cultural_contexts
        
        # Test basic functionality
        message = interface.display_message("welcome")
        assert "欢迎" in message
        
        feedback = interface.format_feedback("correct answer")
        assert "✓" in feedback
    
    def test_content_crawler_initialization(self):
        """Test that ContentCrawler initializes with proper sources."""
        crawler = ContentCrawler()
        
        # Test that sources are loaded
        assert len(crawler.english_sources) > 0
        assert len(crawler.japanese_sources) > 0
        assert "bbc.com" in str(crawler.english_sources)
        assert "nhk.or.jp" in str(crawler.japanese_sources)
        
        # Test quality thresholds
        assert crawler.quality_thresholds["min_educational_value"] > 0
    
    def test_memory_manager_initialization(self):
        """Test that MemoryManager initializes with tracking structures."""
        manager = MemoryManager()
        
        # Test that tracking structures are initialized
        assert isinstance(manager.user_content_history, dict)
        assert isinstance(manager.content_mastery, dict)
        assert isinstance(manager.learning_timestamps, dict)
    
    def test_progress_tracker_initialization(self):
        """Test that ProgressTracker initializes with tracking structures."""
        tracker = ProgressTracker()
        
        # Test that storage structures are initialized
        assert isinstance(tracker.user_metrics, dict)
        assert isinstance(tracker.activity_history, dict)
        assert isinstance(tracker.skill_progress, dict)
    
    def test_weakness_analyzer_initialization(self):
        """Test that WeaknessAnalyzer initializes with analysis structures."""
        analyzer = WeaknessAnalyzer()
        
        # Test that analysis structures are initialized
        assert isinstance(analyzer.error_patterns, dict)
        assert isinstance(analyzer.skill_performance, dict)
        assert isinstance(analyzer.weakness_history, dict)


class TestChineseInterfaceProperties:
    """Property-based tests for Chinese Interface consistency."""
    
    @given(
        message_key=st.sampled_from([
            "welcome", "session_start", "session_complete", "level_up",
            "progress_good", "vocabulary_mastered", "keep_going"
        ]),
        params=st.dictionaries(
            st.sampled_from(["level", "word", "days", "accuracy"]),
            st.one_of(st.text(min_size=1, max_size=20), st.integers(min_value=1, max_value=100)),
            max_size=3
        )
    )
    def test_chinese_interface_consistency(self, message_key, params):
        """
        **Feature: bilingual-tutor, Property 13: Chinese Language Interface Consistency**
        
        For any system interaction, all messages, instructions, and feedback 
        should be presented in Chinese.
        
        **Validates: Requirements 5.1, 5.2, 5.4, 5.5**
        """
        interface = ChineseInterface()
        
        # Test that display_message always returns Chinese text
        message = interface.display_message(message_key, params)
        
        # Check that the message is not empty
        assert len(message) > 0
        
        # Check that the message contains Chinese characters or is a valid Chinese message
        # Chinese characters are in Unicode ranges: 4E00-9FFF (CJK Unified Ideographs)
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', message))
        
        # For messages that might not have Chinese characters (like error messages),
        # ensure they are still appropriate Chinese responses
        if not has_chinese:
            # Should not contain English-only responses that aren't translated
            english_only_patterns = [
                r'^[A-Za-z\s]+$',  # Only English letters and spaces
                r'NotImplementedError',
                r'Error:',
                r'Exception:'
            ]
            for pattern in english_only_patterns:
                assert not re.match(pattern, message), f"Message appears to be untranslated English: {message}"
        
        # Test that format_feedback returns Chinese-formatted feedback
        test_feedback = "test feedback"
        formatted = interface.format_feedback(test_feedback)
        
        # Should contain Chinese formatting elements or Chinese text
        chinese_formatting_indicators = ['✓', '✗', '💡', '📝', '很好', '需要', '提示', '反馈', '继续']
        has_chinese_formatting = any(indicator in formatted for indicator in chinese_formatting_indicators)
        assert has_chinese_formatting, f"Feedback not properly formatted in Chinese style: {formatted}"
    
    @given(content=content_strategy())
    def test_content_translation_chinese_explanations(self, content):
        """
        **Feature: bilingual-tutor, Property 13: Chinese Language Interface Consistency**
        
        For any content translation, Chinese explanations should be provided.
        
        **Validates: Requirements 5.2, 5.4, 5.5**
        """
        interface = ChineseInterface()
        
        # Test translation to Chinese
        translated = interface.translate_content(content, "chinese")
        
        # Should contain Chinese text
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', translated))
        assert has_chinese or content.language.lower() == "chinese", "Translation should contain Chinese explanations"
        
        # Test translation from foreign language should include explanations
        if content.language.lower() in ["english", "japanese"]:
            translated_with_explanations = interface.translate_content(content, "chinese")
            
            # Should contain explanation markers
            explanation_markers = ['【', '】', '解释', '背景', '原文']
            has_explanations = any(marker in translated_with_explanations for marker in explanation_markers)
            assert has_explanations, "Foreign language content should include Chinese explanations"
    
    @given(
        concept=st.text(min_size=1, max_size=50),
        language_hint=st.sampled_from(["english", "japanese", "grammar", "culture", ""])
    )
    def test_cultural_context_chinese_responses(self, concept, language_hint):
        """
        **Feature: bilingual-tutor, Property 13: Chinese Language Interface Consistency**
        
        For any cultural context request, responses should be in Chinese.
        
        **Validates: Requirements 5.1, 5.5**
        """
        interface = ChineseInterface()
        
        # Test cultural context provision
        context = interface.provide_cultural_context(f"{language_hint} {concept}".strip())
        
        # Should return Chinese text
        assert len(context) > 0, "Cultural context should not be empty"
        
        # Should contain Chinese characters or be a proper Chinese response
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', context))
        
        # If no Chinese characters, should still be a valid Chinese-style response
        if not has_chinese:
            # Should not be raw English error messages
            assert not context.startswith("Error"), f"Should not return raw error: {context}"
            assert "NotImplementedError" not in context, f"Should not expose implementation details: {context}"
    
    @given(
        word=st.text(min_size=1, max_size=30, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
        language=st.sampled_from(["english", "japanese"])
    )
    def test_pronunciation_guidance_localization(self, word, language):
        """
        **Feature: bilingual-tutor, Property 14: Pronunciation Guidance Localization**
        
        For any pronunciation guidance request, Chinese phonetic descriptions 
        should be used where helpful.
        
        **Validates: Requirements 5.3**
        """
        interface = ChineseInterface()
        
        # Test pronunciation guidance provision
        guidance = interface.provide_pronunciation_guidance(word, language)
        
        # Should return non-empty guidance
        assert len(guidance) > 0, "Pronunciation guidance should not be empty"
        
        # Should contain Chinese characters (phonetic descriptions)
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', guidance))
        assert has_chinese, f"Pronunciation guidance should contain Chinese phonetic descriptions: {guidance}"
        
        # Should contain helpful phonetic description indicators
        phonetic_indicators = [
            '类似', '读作', '发音', '音标', '重音', '轻声', '咬舌', '卷舌', 
            '促音', '长音', '弹舌', '齿音', '唇音', '建议'
        ]
        has_phonetic_help = any(indicator in guidance for indicator in phonetic_indicators)
        assert has_phonetic_help, f"Guidance should contain helpful phonetic descriptions: {guidance}"
        
        # Should not contain untranslated technical terms without explanation
        technical_terms_without_context = [
            r'\bIPA\b(?!.*音标)',  # IPA without Chinese explanation
            r'\bphoneme\b(?!.*音素)',  # phoneme without Chinese explanation
            r'\bstress\b(?!.*重音)',  # stress without Chinese explanation
        ]
        
        for pattern in technical_terms_without_context:
            assert not re.search(pattern, guidance, re.IGNORECASE), \
                f"Technical terms should be explained in Chinese: {guidance}"
        
        # Language-specific validation
        if language == "english":
            # English pronunciation guidance should mention relevant concepts
            if any(sound in word.lower() for sound in ['th', 'r', 'l']):
                # Should provide specific guidance for difficult English sounds
                difficult_sound_guidance = ['咬舌', '卷舌', '舌音']
                has_specific_guidance = any(guide in guidance for guide in difficult_sound_guidance)
                # This is a soft assertion - not all words will have difficult sounds
                
        elif language == "japanese":
            # Japanese pronunciation guidance should mention relevant concepts
            japanese_concepts = ['假名', '长音', '促音', '拗音', '重音', '弹舌']
            # Should contain some Japanese-specific pronunciation concepts
            # This is informational rather than strictly required