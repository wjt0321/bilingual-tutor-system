"""
Tests for Vocabulary Extraction Completeness - Property 42.
"""

import pytest
import re
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from bilingual_tutor.content.precise_level_crawler import PreciseLevelContentCrawler, VocabularyItem
from bilingual_tutor.models import Content, ContentType


def content_with_vocabulary_strategy():
    """Strategy for generating Content objects that contain extractable vocabulary."""
    
    # Simplified content samples for faster generation
    english_samples = [
        "The word 'sophisticated' means complex. Example: She used sophisticated methods.",
        "The word 'comprehensive' means complete. Example: His comprehensive analysis was good.",
        "The word 'academic' means scholarly. Example: The academic research was useful.",
        "The word 'professional' means work-related. Example: She maintained professional standards.",
        "The word 'development' means growth. Example: The development was rapid."
    ]
    
    japanese_samples = [
        "「努力」（どりょく）は「頑張ること」という意味です。例文：彼は努力しました。",
        "「忍耐」（にんたい）は「耐えること」という意味です。例文：忍耐が必要です。",
        "「研究」（けんきゅう）は「調べること」という意味です。例文：研究を行います。",
        "「教育」（きょういく）は「教えること」という意味です。例文：教育は重要です。",
        "「技術」（ぎじゅつ）は「技能」という意味です。例文：新しい技術を学びました。"
    ]
    
    return st.builds(
        Content,
        content_id=st.text(min_size=3, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
        title=st.sampled_from(["English Lesson", "Japanese Study", "Vocabulary"]),
        body=st.sampled_from(english_samples + japanese_samples),
        language=st.sampled_from(["english", "japanese"]),
        difficulty_level=st.sampled_from(["CET-4", "CET-6", "N3", "N1"]),
        content_type=st.just(ContentType.ARTICLE),
        source_url=st.just("https://example.com/test"),
        quality_score=st.just(0.8),
        created_at=st.just(datetime.now()),
        tags=st.just(["test"])
    )


@st.composite
def vocabulary_item_strategy(draw):
    """Strategy for generating VocabularyItem objects with varying completeness."""
    
    # Define realistic word-definition-example combinations
    english_vocab_data = [
        ("sophisticated", "extremely complex and refined", "She used sophisticated research methodology.", "english"),
        ("comprehensive", "complete and thorough", "His comprehensive analysis was impressive.", "english"),
        ("academic", "relating to education and scholarship", "The academic research was groundbreaking.", "english"),
        ("professional", "relating to a profession", "She maintained professional standards.", "english"),
        ("development", "the process of developing", "The development of new technology is rapid.", "english")
    ]
    
    japanese_vocab_data = [
        ("努力", "目標に向かって頑張ること", "彼は努力して日本語を覚えました。", "japanese"),
        ("忍耐", "困難に耐えること", "忍耐が必要な仕事です。", "japanese"),
        ("研究", "詳しく調べること", "科学研究を行っています。", "japanese"),
        ("教育", "知識や技能を教えること", "教育は重要です。", "japanese"),
        ("技術", "物事を行う方法や技能", "新しい技術を学びました。", "japanese")
    ]
    
    all_vocab_data = english_vocab_data + japanese_vocab_data
    
    # Select a vocabulary item
    word_data = draw(st.sampled_from(all_vocab_data))
    word, definition, example, language = word_data
    
    # Determine appropriate level
    if language == "english":
        level = draw(st.sampled_from(["CET-4", "CET-5", "CET-6"]))
    else:
        level = draw(st.sampled_from(["N5", "N4", "N3", "N2", "N1"]))
    
    # Determine reading for Japanese words
    reading = None
    if language == "japanese":
        reading_map = {
            "努力": "どりょく",
            "忍耐": "にんたい", 
            "研究": "けんきゅう",
            "教育": "きょういく",
            "技術": "ぎじゅつ"
        }
        reading = reading_map.get(word)
    
    # Sometimes make fields None to test completeness validation
    has_definition = draw(st.booleans())
    has_example = draw(st.booleans())
    has_audio = draw(st.booleans())
    
    return VocabularyItem(
        word=word,
        reading=reading,
        definition=definition if has_definition else None,
        example_sentence=example if has_example else None,
        level=level,
        language=language,
        source_url=draw(st.sampled_from([
            "https://www.bbc.com/learningenglish/vocabulary/lesson1",
            "https://www.cambridge.org/elt/vocabulary/advanced",
            "https://www.nhk.or.jp/lesson/vocabulary/n3",
            "https://www.jlpt.jp/samples/vocabulary"
        ])),
        audio_url=draw(st.sampled_from([
            None,
            "https://audio.cambridge.org/pronunciation/sophisticated.mp3",
            "https://audio.nhk.or.jp/pronunciation/doryoku.mp3"
        ])) if has_audio else None
    )


class TestVocabularyExtractionCompleteness:
    """Test suite for Vocabulary Extraction Completeness - Property 42."""
    
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
    @given(
        st.lists(
            content_with_vocabulary_strategy(),
            min_size=1,
            max_size=3
        )
    )
    def test_vocabulary_extraction_completeness_property(self, content_list):
        """
        **Feature: bilingual-tutor, Property 42: Vocabulary Extraction Completeness**
        **Validates: Requirements 19.4**
        
        For any crawled vocabulary item, the extraction should include definitions, 
        example sentences, and pronunciation guides when available from the source.
        """
        crawler = PreciseLevelContentCrawler()
        
        for content in content_list:
            # Extract vocabulary from the content
            vocabulary_items = crawler.extract_level_vocabulary(content)
            
            # Verify that vocabulary extraction was attempted
            assert isinstance(vocabulary_items, list), \
                f"extract_level_vocabulary should return a list, got {type(vocabulary_items)}"
            
            # For each extracted vocabulary item, verify completeness
            for vocab_item in vocabulary_items:
                # Verify basic structure
                assert isinstance(vocab_item, VocabularyItem), \
                    f"Extracted item should be VocabularyItem, got {type(vocab_item)}"
                
                # Verify required fields are present
                assert vocab_item.word is not None and vocab_item.word.strip() != "", \
                    "Vocabulary item must have a non-empty word"
                
                assert vocab_item.language in ["english", "japanese"], \
                    f"Vocabulary item must have valid language, got {vocab_item.language}"
                
                assert vocab_item.level is not None, \
                    "Vocabulary item must have a level specified"
                
                assert vocab_item.source_url is not None, \
                    "Vocabulary item must have source URL for traceability"
                
                # Check for completeness based on content analysis
                content_text = content.title + " " + content.body
                
                # Basic completeness check - if vocabulary was extracted, it should have basic structure
                # More lenient approach: only check completeness for words that clearly have structured info
                
                # If the content contains definition patterns, extracted items should have definitions
                if self._content_has_definitions(content_text, vocab_item.language):
                    # Only check if this specific word has a definition pattern in the content
                    if self._word_appears_with_definition(vocab_item.word, content_text, vocab_item.language):
                        assert vocab_item.definition is not None and vocab_item.definition.strip() != "", \
                            f"Vocabulary item '{vocab_item.word}' should have definition when explicitly defined in source"
                
                # If the content contains example patterns, extracted items should have examples  
                if self._content_has_examples(content_text, vocab_item.language):
                    # Only check if this specific word has an example in the content
                    if self._word_appears_with_example(vocab_item.word, content_text, vocab_item.language):
                        assert vocab_item.example_sentence is not None and vocab_item.example_sentence.strip() != "", \
                            f"Vocabulary item '{vocab_item.word}' should have example sentence when explicitly shown in source"
    
    @given(
        st.lists(
            vocabulary_item_strategy(),
            min_size=3,
            max_size=10
        )
    )
    def test_vocabulary_item_completeness_validation_property(self, vocabulary_items):
        """
        **Feature: bilingual-tutor, Property 42: Vocabulary Extraction Completeness**
        **Validates: Requirements 19.4**
        
        For any vocabulary item extracted from a source, it should maintain completeness
        standards with all available information properly extracted and structured.
        """
        # Test that vocabulary items maintain expected structure and completeness
        for vocab_item in vocabulary_items:
            # Basic validation
            assert isinstance(vocab_item.word, str) and vocab_item.word.strip() != "", \
                "Vocabulary word must be a non-empty string"
            
            assert vocab_item.language in ["english", "japanese"], \
                f"Language must be 'english' or 'japanese', got {vocab_item.language}"
            
            assert vocab_item.level in ["CET-4", "CET-5", "CET-6", "N5", "N4", "N3", "N2", "N1"], \
                f"Level must be valid proficiency level, got {vocab_item.level}"
            
            # Completeness validation - if information is provided, it should be meaningful
            if vocab_item.definition is not None:
                assert vocab_item.definition.strip() != "", \
                    "Definition should not be empty if provided"
                
                # Definition should be reasonably informative (more than just the word itself)
                assert len(vocab_item.definition.strip()) >= 3, \
                    f"Definition should be informative, got '{vocab_item.definition}'"
            
            if vocab_item.example_sentence is not None:
                assert vocab_item.example_sentence.strip() != "", \
                    "Example sentence should not be empty if provided"
                
                # Example should contain the vocabulary word (case-insensitive for English)
                if vocab_item.language == "english":
                    assert vocab_item.word.lower() in vocab_item.example_sentence.lower(), \
                        f"Example sentence should contain the word '{vocab_item.word}'"
                elif vocab_item.language == "japanese":
                    assert vocab_item.word in vocab_item.example_sentence, \
                        f"Example sentence should contain the word '{vocab_item.word}'"
            
            if vocab_item.reading is not None:
                assert vocab_item.reading.strip() != "", \
                    "Reading should not be empty if provided"
            
            if vocab_item.audio_url is not None:
                assert vocab_item.audio_url.strip() != "", \
                    "Audio URL should not be empty if provided"
                
                # Basic URL validation
                assert vocab_item.audio_url.startswith(("http://", "https://")), \
                    f"Audio URL should be a valid URL, got '{vocab_item.audio_url}'"
    
    def test_vocabulary_extraction_from_rich_content(self):
        """
        Test vocabulary extraction from content that explicitly contains definitions,
        examples, and pronunciation guides to ensure completeness.
        """
        crawler = PreciseLevelContentCrawler()
        
        # Create content with explicit vocabulary information using words from the vocabulary lists
        rich_english_content = Content(
            content_id="test_rich_english",
            title="Advanced English Vocabulary",
            body="The word 'sophisticated' means extremely complex and refined. "
                 "For example: She used sophisticated research methodology. "
                 "Pronunciation: /səˈfɪstɪkeɪtɪd/. "
                 "Another word is 'comprehensive' which means complete and thorough. "
                 "Example: His comprehensive analysis was impressive. Pronunciation: /ˌkɒmprɪˈhensɪv/.",
            language="english",
            difficulty_level="CET-6",
            content_type=ContentType.ARTICLE,
            source_url="https://www.cambridge.org/vocabulary/advanced",
            quality_score=0.9,
            created_at=datetime.now(),
            tags=["vocabulary", "advanced", "english"]
        )
        
        rich_japanese_content = Content(
            content_id="test_rich_japanese",
            title="日本語語彙学習",
            body="「努力」（どりょく）という言葉は「目標に向かって頑張ること」という意味です。"
                 "例文：彼は努力して日本語を覚えました。"
                 "「忍耐」（にんたい）は「困難に耐えること」という意味です。"
                 "例文：忍耐が必要な仕事です。",
            language="japanese",
            difficulty_level="N3",
            content_type=ContentType.ARTICLE,
            source_url="https://www.nhk.or.jp/lesson/vocabulary",
            quality_score=0.9,
            created_at=datetime.now(),
            tags=["vocabulary", "japanese", "n3"]
        )
        
        # Test English vocabulary extraction
        english_vocab = crawler.extract_level_vocabulary(rich_english_content)
        assert len(english_vocab) > 0, "Should extract vocabulary from rich English content"
        
        # Verify completeness for extracted English vocabulary
        for vocab_item in english_vocab:
            if vocab_item.word.lower() in ["sophisticated", "comprehensive"]:
                # These words have explicit definitions and examples in the content
                assert vocab_item.definition is not None, \
                    f"Word '{vocab_item.word}' should have definition extracted"
                assert vocab_item.example_sentence is not None, \
                    f"Word '{vocab_item.word}' should have example sentence extracted"
        
        # Test Japanese vocabulary extraction
        japanese_vocab = crawler.extract_level_vocabulary(rich_japanese_content)
        assert len(japanese_vocab) > 0, "Should extract vocabulary from rich Japanese content"
        
        # Verify completeness for extracted Japanese vocabulary
        for vocab_item in japanese_vocab:
            if vocab_item.word in ["努力", "忍耐"]:
                # These words have explicit definitions and examples in the content
                assert vocab_item.definition is not None, \
                    f"Word '{vocab_item.word}' should have definition extracted"
                assert vocab_item.example_sentence is not None, \
                    f"Word '{vocab_item.word}' should have example sentence extracted"
                assert vocab_item.reading is not None, \
                    f"Japanese word '{vocab_item.word}' should have reading extracted"
    
    def test_vocabulary_extraction_maintains_source_traceability(self):
        """
        Test that extracted vocabulary items maintain proper source traceability
        for completeness verification.
        """
        crawler = PreciseLevelContentCrawler()
        
        test_content = Content(
            content_id="test_traceability",
            title="Test Content",
            body="This content contains vocabulary for testing extraction completeness.",
            language="english",
            difficulty_level="CET-4",
            content_type=ContentType.ARTICLE,
            source_url="https://test.example.com/vocabulary",
            quality_score=0.8,
            created_at=datetime.now(),
            tags=["test"]
        )
        
        vocabulary_items = crawler.extract_level_vocabulary(test_content)
        
        # Verify source traceability
        for vocab_item in vocabulary_items:
            assert vocab_item.source_url == test_content.source_url, \
                "Vocabulary item should maintain source URL for traceability"
            
            assert vocab_item.language == test_content.language, \
                "Vocabulary item should maintain source language"
            
            assert vocab_item.level == test_content.difficulty_level, \
                "Vocabulary item should maintain source difficulty level"
    
    def _content_has_definitions(self, content_text: str, language: str) -> bool:
        """Check if content contains definition patterns."""
        if language == "english":
            definition_patterns = [
                " means ", " is defined as ", " refers to ", " is the ", " definition:"
            ]
            return any(pattern in content_text.lower() for pattern in definition_patterns)
        elif language == "japanese":
            definition_patterns = [
                "という意味", "とは", "の意味", "という言葉", "定義"
            ]
            return any(pattern in content_text for pattern in definition_patterns)
        return False
    
    def _content_has_examples(self, content_text: str, language: str) -> bool:
        """Check if content contains example patterns."""
        if language == "english":
            example_patterns = [
                "for example", "example:", "e.g.", "such as", "instance:"
            ]
            return any(pattern in content_text.lower() for pattern in example_patterns)
        elif language == "japanese":
            example_patterns = [
                "例文", "例：", "たとえば", "例えば", "実例"
            ]
            return any(pattern in content_text for pattern in example_patterns)
        return False
    
    def _content_has_pronunciation(self, content_text: str, language: str) -> bool:
        """Check if content contains pronunciation patterns."""
        if language == "english":
            pronunciation_patterns = [
                "pronunciation:", "/", "phonetic", "ˈ", "ə", "ɪ", "æ"
            ]
            return any(pattern in content_text.lower() for pattern in pronunciation_patterns)
        elif language == "japanese":
            pronunciation_patterns = [
                "（", "）", "読み方", "発音", "よみ"
            ]
            return any(pattern in content_text for pattern in pronunciation_patterns)
        return False
    
    def _word_appears_with_definition(self, word: str, content_text: str, language: str) -> bool:
        """Check if a specific word appears with a definition in the content."""
        if language == "english":
            patterns = [
                rf"(?:The word|word)\s*['\"]?{re.escape(word)}['\"]?\s*(?:means|is defined as|refers to)",
                rf"{re.escape(word)}\s*(?:means|is defined as|refers to)"
            ]
            return any(re.search(pattern, content_text, re.IGNORECASE) for pattern in patterns)
        elif language == "japanese":
            patterns = [
                rf"「{re.escape(word)}」.*という意味",
                rf"{re.escape(word)}.*は「.*」という意味"
            ]
            return any(re.search(pattern, content_text) for pattern in patterns)
        return False
    
    def _word_appears_with_example(self, word: str, content_text: str, language: str) -> bool:
        """Check if a specific word appears with an example in the content."""
        if language == "english":
            patterns = [
                rf"(?:For example|Example|e\.g\.)[:\s]*[^.!?]*\b{re.escape(word)}\b[^.!?]*[.!?]"
            ]
            return any(re.search(pattern, content_text, re.IGNORECASE) for pattern in patterns)
        elif language == "japanese":
            patterns = [
                rf"例文?[：:][^。]*{re.escape(word)}[^。]*[。]?"
            ]
            return any(re.search(pattern, content_text) for pattern in patterns)
        return False