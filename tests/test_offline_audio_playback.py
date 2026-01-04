"""
Property-based tests for Offline Audio Playback Support.
离线音频播放支持属性测试
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import List, Dict, Optional
from unittest.mock import patch, MagicMock

from bilingual_tutor.audio.pronunciation_manager import PronunciationManager
from bilingual_tutor.audio.audio_storage import AudioStorage, AudioRecord
from bilingual_tutor.storage.database import LearningDatabase, VocabularyItem


class TestOfflineAudioPlaybackProperties:
    """Property-based tests for Offline Audio Playback Support functionality."""
    
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
        os.makedirs(os.path.join(self.audio_storage_path, "english", "CET-5"), exist_ok=True)
        os.makedirs(os.path.join(self.audio_storage_path, "japanese", "N5"), exist_ok=True)
        os.makedirs(os.path.join(self.audio_storage_path, "japanese", "N4"), exist_ok=True)
        
        # Create dummy audio files with realistic content
        test_files = [
            ("english", "CET-4", "hello"),
            ("english", "CET-4", "world"),
            ("english", "CET-5", "beautiful"),
            ("japanese", "N5", "こんにちは"),
            ("japanese", "N5", "ありがとう"),
            ("japanese", "N4", "勉強"),
        ]
        
        for language, level, word in test_files:
            file_path = os.path.join(self.audio_storage_path, language, level, f"{word}.mp3")
            # Create realistic fake audio content
            audio_content = f"FAKE_MP3_HEADER_{word}_{language}_{level}_AUDIO_DATA".encode()
            with open(file_path, 'wb') as f:
                f.write(audio_content)
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                st.sampled_from(['english', 'japanese']),
                st.sampled_from(['CET-4', 'CET-5', 'CET-6', 'N5', 'N4', 'N3', 'N2', 'N1'])
            ),
            min_size=1,
            max_size=8,
            unique_by=lambda x: (x[0], x[1], x[2])  # Unique by word, language, level
        )
    )
    @settings(deadline=3000, max_examples=15)
    def test_offline_audio_playback_support_property(self, vocabulary_items):
        """
        **Feature: bilingual-tutor, Property 40: Offline Audio Playback Support**
        
        For any downloaded pronunciation file, the system should support offline playback 
        without requiring internet connectivity.
        
        **Validates: Requirements 18.6**
        """
        # Property 1: Downloaded audio files should be accessible offline
        downloaded_audio_files = []
        
        for word, language, level in vocabulary_items:
            # Simulate downloading and storing audio file
            audio_dir = os.path.join(self.audio_storage_path, language, level)
            os.makedirs(audio_dir, exist_ok=True)
            audio_file_path = os.path.join(audio_dir, f"{word}.mp3")
            
            # Create realistic audio file content
            audio_content = f"MP3_AUDIO_DATA_{word}_{language}_{level}".encode()
            with open(audio_file_path, 'wb') as f:
                f.write(audio_content)
            
            # Store audio record in database
            audio_record = self.audio_storage.store_audio_file(
                word=word,
                language=language,
                level=level,
                source_path=audio_file_path,
                source="downloaded_source",
                quality="standard"
            )
            
            if audio_record:
                downloaded_audio_files.append((word, language, level, audio_record.file_path))
        
        # Property 2: Offline playback should work without internet connectivity
        # Simulate offline environment by mocking network access
        with patch('urllib.request.urlopen') as mock_urlopen, \
             patch('requests.get') as mock_requests_get, \
             patch('socket.create_connection') as mock_socket:
            
            # Make network calls fail to simulate offline environment
            mock_urlopen.side_effect = OSError("Network is unreachable")
            mock_requests_get.side_effect = OSError("Network is unreachable")
            mock_socket.side_effect = OSError("Network is unreachable")
            
            for word, language, level, audio_path in downloaded_audio_files:
                # Property 2a: Audio file should be accessible locally
                assert os.path.exists(audio_path), f"Downloaded audio file should exist locally: {audio_path}"
                assert os.path.isfile(audio_path), f"Audio path should be a file: {audio_path}"
                
                # Property 2b: File should be readable without network access
                assert os.access(audio_path, os.R_OK), f"Audio file should be readable offline: {audio_path}"
                
                # Property 2c: File should have content
                file_size = os.path.getsize(audio_path)
                assert file_size > 0, f"Audio file should have content: {audio_path}"
                
                # Property 2d: Audio manager should find file without network
                found_audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                assert found_audio_path is not None, f"Should find audio offline for {word} ({language}, {level})"
                assert found_audio_path == audio_path, f"Found path should match stored path for {word}"
                
                # Property 2e: File content should be intact
                with open(audio_path, 'rb') as f:
                    content = f.read()
                    assert len(content) > 0, f"Audio file should have readable content: {audio_path}"
                    # Verify it's the content we wrote
                    expected_content = f"MP3_AUDIO_DATA_{word}_{language}_{level}".encode()
                    assert content == expected_content, f"Audio file content should be intact for {word}"
        
        # Property 3: Offline playback should be deterministic and repeatable
        for word, language, level, audio_path in downloaded_audio_files:
            # Multiple offline access attempts should be consistent
            offline_access_results = []
            
            with patch('urllib.request.urlopen', side_effect=OSError("Offline")):
                for _ in range(3):
                    # Simulate offline playback attempt
                    playback_supported = self._simulate_offline_playback(word, language, level)
                    offline_access_results.append(playback_supported)
            
            # All attempts should succeed consistently
            assert all(offline_access_results), f"Offline playback should be consistently supported for {word}"
            assert len(set(offline_access_results)) == 1, f"Offline playback results should be consistent for {word}"
        
        # Property 4: Local file system operations should not require network
        with patch('socket.socket') as mock_socket:
            mock_socket.side_effect = OSError("No network access")
            
            for word, language, level, audio_path in downloaded_audio_files:
                # File system operations should work without network
                assert os.path.exists(audio_path), f"File existence check should work offline: {audio_path}"
                
                # File metadata should be accessible offline
                stat_info = os.stat(audio_path)
                assert stat_info.st_size > 0, f"File size should be accessible offline: {audio_path}"
                
                # File should be openable offline
                try:
                    with open(audio_path, 'rb') as f:
                        first_bytes = f.read(10)
                        assert len(first_bytes) > 0, f"File should be readable offline: {audio_path}"
                except Exception as e:
                    pytest.fail(f"File should be readable offline without network: {audio_path}: {e}")
        
        # Property 5: Audio storage database should work offline
        with patch('urllib.request.urlopen', side_effect=OSError("Offline")):
            for word, language, level, audio_path in downloaded_audio_files:
                # Database queries should work offline
                audio_record = self.audio_storage.get_audio_file(word, language, level)
                assert audio_record is not None, f"Should retrieve audio record offline for {word}"
                assert audio_record.file_path == audio_path, f"Record should have correct path for {word}"
                
                # Search operations should work offline
                search_results = self.audio_storage.search_audio_files(language=language, level=level)
                matching_records = [r for r in search_results if r.word == word]
                assert len(matching_records) > 0, f"Should find audio record in offline search for {word}"
    
    @given(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        st.sampled_from(['english', 'japanese']),
        st.sampled_from(['CET-4', 'CET-5', 'CET-6', 'N5', 'N4', 'N3', 'N2', 'N1']),
        st.integers(min_value=100, max_value=10000)  # File size in bytes
    )
    @settings(deadline=2000, max_examples=12)
    def test_single_file_offline_playback_property(self, word, language, level, file_size):
        """
        **Feature: bilingual-tutor, Property 40: Offline Audio Playback Support (Single File)**
        
        For any single downloaded pronunciation file, offline playback should be supported 
        regardless of file size or network status.
        
        **Validates: Requirements 18.6**
        """
        # Property 1: Create a downloaded audio file with specific size
        audio_dir = os.path.join(self.audio_storage_path, language, level)
        os.makedirs(audio_dir, exist_ok=True)
        audio_file_path = os.path.join(audio_dir, f"{word}.mp3")
        
        # Create audio file with specified size
        base_content = f"AUDIO_HEADER_{word}_{language}_{level}_"
        # Repeat content to reach desired size, then truncate to exact size
        repeated_content = (base_content * (file_size // len(base_content) + 1))[:file_size]
        audio_content = repeated_content.encode('utf-8')
        # Ensure we have exactly the right size
        if len(audio_content) > file_size:
            audio_content = audio_content[:file_size]
        elif len(audio_content) < file_size:
            # Pad with zeros to reach exact size
            audio_content += b'\x00' * (file_size - len(audio_content))
        
        with open(audio_file_path, 'wb') as f:
            f.write(audio_content)
        
        # Store in audio storage
        audio_record = self.audio_storage.store_audio_file(
            word=word,
            language=language,
            level=level,
            source_path=audio_file_path,
            source="test_download",
            quality="standard"
        )
        
        assert audio_record is not None, f"Should successfully store audio file for {word}"
        
        # Property 2: Offline playback should work regardless of network failures
        network_failure_scenarios = [
            ("urllib.request.urlopen", OSError("Network unreachable")),
            ("requests.get", ConnectionError("Connection failed")),
            ("socket.create_connection", OSError("No route to host")),
            ("urllib.request.Request", TimeoutError("Request timeout")),
        ]
        
        for mock_target, exception in network_failure_scenarios:
            with patch(mock_target, side_effect=exception):
                # Should still be able to access audio file
                found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                assert found_audio is not None, f"Should find audio during {mock_target} failure for {word}"
                assert os.path.exists(found_audio), f"Audio file should exist during network failure for {word}"
                
                # Should be able to read file content
                with open(found_audio, 'rb') as f:
                    content = f.read()
                    assert len(content) == file_size, f"Should read full file content offline for {word}"
                
                # Offline playback simulation should succeed
                playback_success = self._simulate_offline_playback(word, language, level)
                assert playback_success, f"Offline playback should succeed during {mock_target} failure for {word}"
        
        # Property 3: File integrity should be maintained offline
        with patch('urllib.request.urlopen', side_effect=OSError("Offline mode")):
            # Verify file size
            actual_size = os.path.getsize(audio_record.file_path)
            assert actual_size == file_size, f"File size should be preserved offline for {word}"
            
            # Verify file content integrity
            with open(audio_record.file_path, 'rb') as f:
                read_content = f.read()
                assert len(read_content) == file_size, f"Should read complete file offline for {word}"
                assert read_content == audio_content, f"File content should be intact offline for {word}"
            
            # Verify file metadata
            assert audio_record.file_size == file_size, f"Recorded file size should match actual for {word}"
            assert audio_record.word == word, f"Audio record should have correct word for {word}"
            assert audio_record.language == language, f"Audio record should have correct language for {word}"
        
        # Property 4: Multiple offline access attempts should be consistent
        offline_results = []
        with patch('socket.socket', side_effect=OSError("No network")):
            for attempt in range(5):
                try:
                    # Attempt to access file
                    found_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                    file_accessible = found_path is not None and os.path.exists(found_path)
                    
                    if file_accessible:
                        # Try to read file
                        with open(found_path, 'rb') as f:
                            content_size = len(f.read())
                            content_correct = content_size == file_size
                    else:
                        content_correct = False
                    
                    offline_results.append((file_accessible, content_correct))
                    
                except Exception as e:
                    offline_results.append((False, False))
            
            # All attempts should have consistent results
            assert len(set(offline_results)) == 1, f"Offline access should be consistent across attempts for {word}"
            assert all(accessible for accessible, _ in offline_results), f"File should be consistently accessible offline for {word}"
            assert all(correct for _, correct in offline_results), f"File content should be consistently correct offline for {word}"
    
    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
                st.sampled_from(['english', 'japanese']),
                st.sampled_from(['standard', 'high', 'low'])
            ),
            min_size=2,
            max_size=6,
            unique_by=lambda x: (x[0], x[1])  # Unique by word and language
        )
    )
    @settings(deadline=2500, max_examples=10)
    def test_multiple_files_offline_playback_property(self, word_language_quality_items):
        """
        **Feature: bilingual-tutor, Property 40: Offline Audio Playback Support (Multiple Files)**
        
        For any set of downloaded pronunciation files, offline playback should be supported 
        for all files simultaneously without network dependency.
        
        **Validates: Requirements 18.6**
        """
        # Property 1: Create multiple downloaded audio files
        downloaded_files = []
        
        for word, language, quality in word_language_quality_items:
            level = 'CET-4' if language == 'english' else 'N5'
            
            # Create audio file
            audio_dir = os.path.join(self.audio_storage_path, language, level)
            os.makedirs(audio_dir, exist_ok=True)
            audio_file_path = os.path.join(audio_dir, f"{word}_{quality}.mp3")
            
            # Create unique content for each file
            audio_content = f"MULTI_AUDIO_{word}_{language}_{quality}_DATA_CONTENT".encode()
            with open(audio_file_path, 'wb') as f:
                f.write(audio_content)
            
            # Store in audio storage
            audio_record = self.audio_storage.store_audio_file(
                word=word,
                language=language,
                level=level,
                source_path=audio_file_path,
                source=f"download_{quality}",
                quality=quality
            )
            
            if audio_record:
                downloaded_files.append((word, language, level, quality, audio_record.file_path, audio_content))
        
        # Property 2: All files should be accessible offline simultaneously
        with patch('urllib.request.urlopen', side_effect=OSError("Network offline")), \
             patch('requests.get', side_effect=ConnectionError("No connection")), \
             patch('socket.create_connection', side_effect=OSError("Network unreachable")):
            
            # Test simultaneous access to all files
            for word, language, level, quality, file_path, expected_content in downloaded_files:
                # Each file should be independently accessible
                assert os.path.exists(file_path), f"File should exist offline: {word} ({quality})"
                
                # Should be findable through pronunciation manager
                found_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                assert found_path is not None, f"Should find audio offline: {word} ({quality})"
                
                # Content should be readable
                with open(file_path, 'rb') as f:
                    actual_content = f.read()
                    assert actual_content == expected_content, f"Content should be intact offline: {word} ({quality})"
                
                # Offline playback should be supported
                playback_supported = self._simulate_offline_playback(word, language, level)
                assert playback_supported, f"Offline playback should be supported: {word} ({quality})"
        
        # Property 3: Batch operations should work offline
        with patch('socket.socket', side_effect=OSError("No network access")):
            # Search operations should work offline
            english_files = [f for f in downloaded_files if f[1] == 'english']
            japanese_files = [f for f in downloaded_files if f[1] == 'japanese']
            
            if english_files:
                english_search = self.audio_storage.search_audio_files(language='english', limit=50)
                english_words = {f[0] for f in english_files}
                found_english_words = {r.word for r in english_search if r.word in english_words}
                assert len(found_english_words) > 0, "Should find English files in offline search"
            
            if japanese_files:
                japanese_search = self.audio_storage.search_audio_files(language='japanese', limit=50)
                japanese_words = {f[0] for f in japanese_files}
                found_japanese_words = {r.word for r in japanese_search if r.word in japanese_words}
                assert len(found_japanese_words) > 0, "Should find Japanese files in offline search"
            
            # Statistics should be available offline
            stats = self.audio_storage.get_storage_statistics()
            assert stats is not None, "Should get storage statistics offline"
            assert stats.get('total_files', 0) >= len(downloaded_files), "Statistics should reflect stored files"
        
        # Property 4: File system integrity should be maintained offline
        with patch('urllib.request.urlopen', side_effect=OSError("Offline")):
            for word, language, level, quality, file_path, expected_content in downloaded_files:
                # File properties should be consistent
                assert os.path.isfile(file_path), f"Should be a file offline: {word}"
                assert os.access(file_path, os.R_OK), f"Should be readable offline: {word}"
                
                # File size should be correct
                expected_size = len(expected_content)
                actual_size = os.path.getsize(file_path)
                assert actual_size == expected_size, f"File size should be correct offline: {word}"
                
                # File modification time should be preserved
                stat_info = os.stat(file_path)
                assert stat_info.st_mtime > 0, f"File should have valid modification time: {word}"
        
        # Property 5: Concurrent offline access should be safe
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def offline_access_worker(file_info):
            word, language, level, quality, file_path, expected_content = file_info
            try:
                with patch('urllib.request.urlopen', side_effect=OSError("Offline worker")):
                    # Try to access file
                    found_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                    file_exists = found_path is not None and os.path.exists(found_path)
                    
                    if file_exists:
                        with open(found_path, 'rb') as f:
                            content = f.read()
                            content_correct = content == expected_content
                    else:
                        content_correct = False
                    
                    results_queue.put((word, file_exists, content_correct, None))
            except Exception as e:
                results_queue.put((word, False, False, str(e)))
        
        # Start concurrent access threads
        threads = []
        for file_info in downloaded_files:
            thread = threading.Thread(target=offline_access_worker, args=(file_info,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Collect results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())
        
        # All concurrent accesses should succeed
        assert len(concurrent_results) == len(downloaded_files), "All concurrent accesses should complete"
        
        for word, file_exists, content_correct, error in concurrent_results:
            assert file_exists, f"Concurrent offline access should succeed for {word}: {error}"
            assert content_correct, f"Concurrent offline content read should be correct for {word}: {error}"
    
    def _simulate_offline_playback(self, word: str, language: str, level: str) -> bool:
        """
        Simulate offline audio playback functionality.
        This represents the logic that would be used for offline playback.
        """
        try:
            # Check if audio file exists locally
            audio_path = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            
            if audio_path is None:
                return False
            
            # Verify file exists and is accessible
            if not os.path.exists(audio_path):
                return False
            
            if not os.path.isfile(audio_path):
                return False
            
            # Check file permissions
            if not os.access(audio_path, os.R_OK):
                return False
            
            # Check file has content
            try:
                file_size = os.path.getsize(audio_path)
                if file_size <= 0:
                    return False
            except OSError:
                return False
            
            # Simulate reading file for playback (without actually playing)
            try:
                with open(audio_path, 'rb') as f:
                    # Read first few bytes to verify file is readable
                    header = f.read(10)
                    if len(header) == 0:
                        return False
            except (OSError, IOError):
                return False
            
            # All checks passed - offline playback is supported
            return True
            
        except Exception:
            # Any exception means offline playback is not supported
            return False
    
    @given(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        st.sampled_from(['english', 'japanese'])
    )
    @settings(deadline=1500, max_examples=8)
    def test_offline_playback_without_download_property(self, word, language):
        """
        **Feature: bilingual-tutor, Property 40: Offline Audio Playback Support (No Download)**
        
        For any vocabulary item without a downloaded pronunciation file, offline playback 
        should gracefully fail without requiring network access.
        
        **Validates: Requirements 18.6**
        """
        level = 'CET-4' if language == 'english' else 'N5'
        
        # Property 1: Non-existent files should fail gracefully offline
        with patch('urllib.request.urlopen', side_effect=OSError("Network offline")), \
             patch('requests.get', side_effect=ConnectionError("No connection")), \
             patch('socket.create_connection', side_effect=OSError("Network unreachable")):
            
            # Should not find audio for non-existent file
            found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
            
            # If no audio exists, offline playback should fail gracefully
            if found_audio is None:
                playback_supported = self._simulate_offline_playback(word, language, level)
                assert not playback_supported, f"Offline playback should fail gracefully for non-existent audio: {word}"
            
            # Should not crash or hang when trying to access non-existent audio
            try:
                # These operations should complete quickly without network access
                audio_record = self.audio_storage.get_audio_file(word, language, level)
                # If record exists but file doesn't, that's a valid scenario
                if audio_record and not os.path.exists(audio_record.file_path):
                    playback_supported = self._simulate_offline_playback(word, language, level)
                    assert not playback_supported, f"Should fail gracefully for missing file: {word}"
            except Exception as e:
                # Should not raise exceptions during offline checks
                pytest.fail(f"Offline check should not raise exceptions for {word}: {e}")
        
        # Property 2: System should remain stable when audio is unavailable offline
        with patch('socket.socket', side_effect=OSError("No network")):
            # Multiple attempts should be consistent
            results = []
            for _ in range(3):
                try:
                    found_audio = self.pronunciation_manager.get_pronunciation_audio(word, language, level)
                    playback_result = self._simulate_offline_playback(word, language, level)
                    results.append((found_audio, playback_result))
                except Exception:
                    results.append((None, False))
            
            # Results should be consistent
            assert len(set(results)) <= 2, f"Offline results should be consistent for non-existent audio: {word}"
            
            # If no audio exists, all playback attempts should fail
            if all(audio is None for audio, _ in results):
                assert all(not playback for _, playback in results), f"All playback attempts should fail for non-existent audio: {word}"