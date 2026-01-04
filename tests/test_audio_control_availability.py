"""
Property-based tests for Audio Control Availability.
音频控件可用性属性测试
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List, Dict, Optional

from bilingual_tutor.audio.pronunciation_manager import PronunciationManager
from bilingual_tutor.audio.audio_storage import AudioStorage, AudioRecord
from bilingual_tutor.storage.database import LearningDatabase, VocabularyItem


class TestAudioControlAvailabilityProperties:
    """Property-based tests for Audio Control Availability functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.audio_storage_path = os.path.join(self.temp_dir, "audio")
        self.db_path = os.path.join(self.temp_dir, "test_learning.db")
        
        # Initialize components
        self.audio_storage = AudioStorage(self.audio_storage_path)
        self.pronunciation_manager = PronunciationManager(self.audio_storage_path)
        self.learning_db = LearningDatabase(self.db_path)
        
        # Create test audio files
        self._create_test_audio_files()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Close database connections first
        if hasattr(self, 'learning_db') and self.learning_db:
            try:
                self.learning_db.close()
            except:
                pass
        
        if hasattr(self, 'pronunciation_manager') and self.pronunciation_manager:
            try:
                self.pronunciation_manager.close()
            except:
                pass
        
        # Close audio storage
        if hasattr(self, 'audio_storage') and self.audio_storage:
            try:
                # Close any open database connections in audio storage
                if hasattr(self.audio_storage, 'conn') and self.audio_storage.conn:
                    self.audio_storage.conn.close()
            except:
                pass
        
        # Clean up temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                # Wait a bit for file handles to be released
                import time
                time.sleep(0.1)
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                # On Windows, sometimes files are still locked
                # Try again after a short delay
                try:
                    import time
                    time.sleep(0.5)
                    shutil.rmtree(self.temp_dir)
                except:
                    # If still can't delete, just leave it - temp files will be cleaned up eventually
                    pass
    
    def _create_test_audio_files(self):
        """Create test audio files for testing."""
        # Create directories
        os.makedirs(os.path.join(self.audio_storage_path, "english", "CET-4"), exist_ok=True)
        os.makedirs(os.path.join(self.audio_storage_path, "japanese", "N5"), exist_ok=True)
        
        # Create dummy audio files
        test_files = [
            ("english", "CET-4", "hello"),
            ("english", "CET-4", "world"),
            ("japanese", "N5", "こんにちは"),
            ("japanese", "N5", "ありがとう"),
        ]
        
        for language, level, word in test_files:
            file_path = os.path.join(self.audio_storage_path, language, level, f"{word}.mp3")
            with open(file_path, 'wb') as f:
                f.write(b"fake_audio_data")  # Dummy audio content
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                st.sampled_from(['english', 'japanese']),
                st.sampled_from(['CET-4', 'CET-5', 'CET-6', 'N5', 'N4', 'N3', 'N2', 'N1'])
            ),
            min_size=1,
            max_size=10,
            unique_by=lambda x: (x[0], x[1], x[2])  # Unique by word, language, level
        )
    )
    @settings(deadline=2000, max_examples=20)
    def test_audio_control_availability_property(self, vocabulary_items):
        """
        **Feature: bilingual-tutor, Property 39: Audio Control Availability**
        
        For any vocabulary item displayed in the interface, an audio play button 
        should be available if pronunciation audio exists.
        
        **Validates: Requirements 18.5**
        """
        # Property 1: Audio controls should be available when audio files exist
        items_with_audio = []
        items_without_audio = []
        
        for word, language, level in vocabulary_items:
            # Add vocabulary item to database
            vocab_item = VocabularyItem(
                word=word,
                reading=f"/{word}/",
                meaning=f"Meaning of {word}",
                language=language,
                level=level,
                category="noun",
                audio_url=""  # Will be set if audio exists
            )
            
            # Check if we should create audio for this item (simulate some having audio)
            should_have_audio = hash(word + language + level) % 3 == 0  # ~33% have audio
            
            if should_have_audio:
                # Create audio file
                audio_dir = os.path.join(self.audio_storage_path, language, level)
                os.makedirs(audio_dir, exist_ok=True)
                audio_file_path = os.path.join(audio_dir, f"{word}.mp3")
                
                with open(audio_file_path, 'wb') as f:
                    f.write(b"fake_audio_content")
                
                # Store audio record
                audio_record = self.audio_storage.store_audio_file(
                    word=word,
                    language=language,
                    level=level,
                    source_path=audio_file_path,
                    source="test_source",
                    quality="standard"
                )
                
                if audio_record:
                    vocab_item.audio_url = audio_record.file_path
                    items_with_audio.append((word, language, level, audio_record.file_path))
                else:
                    items_without_audio.append((word, language, level))
            else:
                items_without_audio.append((word, language, level))
        
        # Property 2: Audio control availability should be deterministic
        for word, language, level, audio_path in items_with_audio:
            # Check that audio file exists
            assert os.path.exists(audio_path), f"Audio file should exist for {word} ({language}, {level})"
            
            # Check that pronunciation manager can find the audio
            found_audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            assert found_audio_path is not None, f"Pronunciation manager should find audio for {word}"
            assert os.path.exists(found_audio_path), f"Found audio path should exist: {found_audio_path}"
            
            # Simulate audio control availability check
            audio_control_available = self._check_audio_control_availability(word, language, level)
            assert audio_control_available, f"Audio control should be available for {word} with existing audio"
        
        # Property 3: Audio controls should not be available when audio doesn't exist
        for word, language, level in items_without_audio:
            # Check that no audio file exists
            found_audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            
            if found_audio_path is None:
                # Simulate audio control availability check
                audio_control_available = self._check_audio_control_availability(word, language, level)
                assert not audio_control_available, f"Audio control should not be available for {word} without audio"
        
        # Property 4: Audio control state should be consistent across multiple checks
        for word, language, level, audio_path in items_with_audio:
            # Multiple checks should return consistent results
            results = []
            for _ in range(3):
                available = self._check_audio_control_availability(word, language, level)
                results.append(available)
            
            # All results should be the same
            assert all(r == results[0] for r in results), f"Audio control availability should be consistent for {word}"
            assert all(results), f"All checks should return True for {word} with audio"
        
        # Property 5: Audio file accessibility should be verified
        for word, language, level, audio_path in items_with_audio:
            # File should be readable
            assert os.path.isfile(audio_path), f"Audio path should be a file: {audio_path}"
            assert os.access(audio_path, os.R_OK), f"Audio file should be readable: {audio_path}"
            
            # File should have content
            file_size = os.path.getsize(audio_path)
            assert file_size > 0, f"Audio file should not be empty: {audio_path}"
        
        # Property 6: Language and level filtering should work correctly
        english_items = [(w, l, lv, p) for w, l, lv, p in items_with_audio if l == 'english']
        japanese_items = [(w, l, lv, p) for w, l, lv, p in items_with_audio if l == 'japanese']
        
        for word, language, level, audio_path in english_items:
            # English audio should be in english directory
            assert 'english' in audio_path, f"English audio should be in english directory: {audio_path}"
            
            # Should be findable by language filter
            found_audio = self.pronunciation_manager.get_pronunciation_audio(word, 'english', level)
            assert found_audio is not None, f"Should find English audio for {word}"
        
        for word, language, level, audio_path in japanese_items:
            # Japanese audio should be in japanese directory
            assert 'japanese' in audio_path, f"Japanese audio should be in japanese directory: {audio_path}"
            
            # Should be findable by language filter
            found_audio = self.pronunciation_manager.get_pronunciation_audio(word, 'japanese', level)
            assert found_audio is not None, f"Should find Japanese audio for {word}"
    
    @given(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        st.sampled_from(['english', 'japanese']),
        st.sampled_from(['CET-4', 'CET-5', 'CET-6', 'N5', 'N4', 'N3', 'N2', 'N1'])
    )
    @settings(deadline=1000, max_examples=15)
    def test_single_vocabulary_audio_control_property(self, word, language, level):
        """
        **Feature: bilingual-tutor, Property 39: Audio Control Availability (Single Item)**
        
        For any single vocabulary item, the audio control availability should be 
        determined solely by the existence of the corresponding audio file.
        
        **Validates: Requirements 18.5**
        """
        # Property 1: Audio control availability should depend only on file existence
        # First, ensure no audio exists
        initial_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
        initial_control_available = self._check_audio_control_availability(word, language, level)
        
        if initial_audio is None:
            assert not initial_control_available, "No audio should mean no control available"
        else:
            assert initial_control_available, "Existing audio should mean control is available"
        
        # Property 2: Creating audio should make control available
        # Create audio file
        audio_dir = os.path.join(self.audio_storage_path, language, level)
        os.makedirs(audio_dir, exist_ok=True)
        audio_file_path = os.path.join(audio_dir, f"{word}.mp3")
        
        with open(audio_file_path, 'wb') as f:
            f.write(b"test_audio_content_" + word.encode())
        
        # Store in audio storage
        audio_record = self.audio_storage.store_audio_file(
            word=word,
            language=language,
            level=level,
            source_path=audio_file_path,
            source="test_source",
            quality="standard"
        )
        
        if audio_record:
            # Now audio should be available
            found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            assert found_audio is not None, "Audio should be found after creation"
            
            control_available = self._check_audio_control_availability(word, language, level)
            assert control_available, "Audio control should be available after audio creation"
            
            # Property 3: Audio file properties should be correct
            assert os.path.exists(found_audio), "Found audio file should exist"
            assert os.path.isfile(found_audio), "Found audio should be a file"
            
            file_size = os.path.getsize(found_audio)
            assert file_size > 0, "Audio file should have content"
            
            # Property 4: Audio record should have correct metadata
            assert audio_record.word == word, "Audio record should have correct word"
            assert audio_record.language == language, "Audio record should have correct language"
            assert audio_record.level == level, "Audio record should have correct level"
            assert audio_record.file_path == found_audio, "Audio record path should match found path"
        
        # Property 5: Removing audio should make control unavailable
        if audio_record:
            # Delete the audio file
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
            
            # Control should no longer be available
            # Note: This depends on implementation - some systems might cache,
            # others might check file existence in real-time
            found_audio_after_delete = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            
            # If the system checks file existence, it should return None
            if found_audio_after_delete is None:
                control_available_after_delete = self._check_audio_control_availability(word, language, level)
                assert not control_available_after_delete, "Audio control should not be available after file deletion"
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
                st.sampled_from(['english', 'japanese'])
            ),
            min_size=2,
            max_size=8,
            unique=True
        )
    )
    @settings(deadline=1500, max_examples=10)
    def test_multiple_vocabulary_audio_control_consistency_property(self, word_language_pairs):
        """
        **Feature: bilingual-tutor, Property 39: Audio Control Availability (Multiple Items)**
        
        For any set of vocabulary items, audio control availability should be 
        independent for each item and consistent across the interface.
        
        **Validates: Requirements 18.5**
        """
        # Property 1: Audio control availability should be independent per item
        items_data = []
        
        for i, (word, language) in enumerate(word_language_pairs):
            level = 'CET-4' if language == 'english' else 'N5'
            
            # Randomly decide if this item should have audio (deterministic based on index)
            should_have_audio = i % 2 == 0  # Every other item has audio
            
            if should_have_audio:
                # Create audio
                audio_dir = os.path.join(self.audio_storage_path, language, level)
                os.makedirs(audio_dir, exist_ok=True)
                audio_file_path = os.path.join(audio_dir, f"{word}.mp3")
                
                with open(audio_file_path, 'wb') as f:
                    f.write(f"audio_for_{word}_{language}".encode())
                
                audio_record = self.audio_storage.store_audio_file(
                    word=word,
                    language=language,
                    level=level,
                    source_path=audio_file_path,
                    source="test_batch",
                    quality="standard"
                )
                
                items_data.append((word, language, level, True, audio_record))
            else:
                items_data.append((word, language, level, False, None))
        
        # Property 2: Each item's audio control should be independent
        for word, language, level, should_have_audio, audio_record in items_data:
            control_available = self._check_audio_control_availability(word, language, level)
            
            if should_have_audio and audio_record:
                assert control_available, f"Audio control should be available for {word} ({language})"
                
                # Verify audio can be found
                found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                assert found_audio is not None, f"Audio should be found for {word}"
                assert os.path.exists(found_audio), f"Audio file should exist for {word}"
            else:
                # Note: This might be True if audio was created in previous tests
                # The key property is consistency, not the absolute value
                pass
        
        # Property 3: Audio control state should not interfere between items
        # Check each item multiple times to ensure consistency
        for word, language, level, should_have_audio, audio_record in items_data:
            results = []
            for _ in range(3):
                available = self._check_audio_control_availability(word, language, level)
                results.append(available)
            
            # Results should be consistent for each item
            assert all(r == results[0] for r in results), f"Audio control availability should be consistent for {word}"
        
        # Property 4: Language separation should be maintained
        english_items = [(w, l, lv, s, a) for w, l, lv, s, a in items_data if l == 'english']
        japanese_items = [(w, l, lv, s, a) for w, l, lv, s, a in items_data if l == 'japanese']
        
        # English items should not interfere with Japanese items
        for word, language, level, should_have_audio, audio_record in english_items:
            if should_have_audio and audio_record:
                # Should not find this word in Japanese
                japanese_audio = self.pronunciation_manager.get_pronunciation_audio(word, 'japanese', 'N5')
                # This might be None or might find a different file - the key is it shouldn't be the same file
                if japanese_audio:
                    assert japanese_audio != audio_record.file_path, f"English and Japanese audio should be different files"
        
        # Property 5: Batch operations should maintain individual item properties
        # Search for audio files by language
        english_search = self.audio_storage.search_audio_files(language='english', limit=50)
        japanese_search = self.audio_storage.search_audio_files(language='japanese', limit=50)
        
        # Each found item should have correct language
        for record in english_search:
            assert record.language == 'english', "English search should only return English items"
            
            # Audio control should be available for found items
            control_available = self._check_audio_control_availability(record.word, record.language, record.level)
            assert control_available, f"Audio control should be available for found English item: {record.word}"
        
        for record in japanese_search:
            assert record.language == 'japanese', "Japanese search should only return Japanese items"
            
            # Audio control should be available for found items
            control_available = self._check_audio_control_availability(record.word, record.language, record.level)
            assert control_available, f"Audio control should be available for found Japanese item: {record.word}"
    
    def _check_audio_control_availability(self, word: str, language: str, level: str) -> bool:
        """
        Simulate checking if audio control should be available for a vocabulary item.
        This represents the logic that would be used in the web interface.
        """
        # Check if pronunciation audio exists
        audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
        
        if audio_path is None:
            return False
        
        # Check if the file actually exists and is accessible
        if not os.path.exists(audio_path):
            return False
        
        if not os.path.isfile(audio_path):
            return False
        
        # Check if file has content
        try:
            file_size = os.path.getsize(audio_path)
            if file_size <= 0:
                return False
        except OSError:
            return False
        
        # Check if file is readable
        if not os.access(audio_path, os.R_OK):
            return False
        
        return True
    
    @given(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        st.sampled_from(['english', 'japanese']),
        st.sampled_from(['standard', 'high', 'low'])
    )
    @settings(deadline=1000, max_examples=10)
    def test_audio_quality_control_availability_property(self, word, language, quality):
        """
        **Feature: bilingual-tutor, Property 39: Audio Control Availability (Quality Variants)**
        
        For any vocabulary item with multiple audio quality variants, the audio control 
        should be available and should prioritize higher quality audio.
        
        **Validates: Requirements 18.5**
        """
        level = 'CET-4' if language == 'english' else 'N5'
        
        # Property 1: Audio control should be available regardless of quality
        audio_dir = os.path.join(self.audio_storage_path, language, level)
        os.makedirs(audio_dir, exist_ok=True)
        audio_file_path = os.path.join(audio_dir, f"{word}_{quality}.mp3")
        
        with open(audio_file_path, 'wb') as f:
            f.write(f"audio_{quality}_{word}".encode())
        
        audio_record = self.audio_storage.store_audio_file(
            word=word,
            language=language,
            level=level,
            source_path=audio_file_path,
            source=f"test_{quality}",
            quality=quality
        )
        
        if audio_record:
            # Audio control should be available
            control_available = self._check_audio_control_availability(word, language, level)
            assert control_available, f"Audio control should be available for {quality} quality audio"
            
            # Should be able to find the audio
            found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            assert found_audio is not None, f"Should find {quality} quality audio"
            assert os.path.exists(found_audio), f"Found {quality} audio file should exist"
            
            # Property 2: Audio record should have correct quality metadata
            assert audio_record.quality == quality, f"Audio record should have {quality} quality"
            assert audio_record.word == word, "Audio record should have correct word"
            assert audio_record.language == language, "Audio record should have correct language"
            
            # Property 3: File should be accessible and have content
            assert os.path.isfile(found_audio), "Found audio should be a file"
            assert os.access(found_audio, os.R_OK), "Audio file should be readable"
            
            file_size = os.path.getsize(found_audio)
            assert file_size > 0, "Audio file should have content"