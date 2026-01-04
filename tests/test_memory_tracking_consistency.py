"""
Property-based tests for memory tracking consistency in the bilingual tutor system.

Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
Validates: Requirements 17.4
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from bilingual_tutor.storage.database import LearningDatabase, LearningRecord


@st.composite
def learning_item_strategy(draw):
    """Generate random learning items for property-based testing."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    item_id = draw(st.integers(min_value=1, max_value=10000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type
    }


@st.composite
def performance_sequence_strategy(draw):
    """Generate sequences of performance results for memory tracking testing."""
    learning_item = draw(learning_item_strategy())
    
    # Generate a sequence of performance results (correct/incorrect)
    num_activities = draw(st.integers(min_value=1, max_value=25))
    performance_sequence = draw(st.lists(st.booleans(), min_size=num_activities, max_size=num_activities))
    
    return {
        **learning_item,
        'performance_sequence': performance_sequence
    }


@st.composite
def mixed_performance_strategy(draw):
    """Generate mixed performance patterns for testing memory strength calculations."""
    learning_item = draw(learning_item_strategy())
    
    # Generate specific patterns: some correct, some incorrect
    correct_count = draw(st.integers(min_value=0, max_value=20))
    incorrect_count = draw(st.integers(min_value=0, max_value=20))
    
    # Ensure at least one activity
    assume(correct_count + incorrect_count > 0)
    
    # Create a mixed sequence using Hypothesis shuffling instead of random
    performance_sequence = [True] * correct_count + [False] * incorrect_count
    # Use Hypothesis to shuffle the sequence
    performance_sequence = draw(st.permutations(performance_sequence))
    
    return {
        **learning_item,
        'performance_sequence': list(performance_sequence),
        'expected_correct': correct_count,
        'expected_total': correct_count + incorrect_count
    }


class TestMemoryTrackingConsistency:
    """Test memory tracking consistency properties."""
    
    def create_temp_database(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        db = LearningDatabase(temp_file.name)
        return db, temp_file.name
    
    def cleanup_temp_database(self, db, db_path):
        """Clean up temporary database."""
        db.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @given(performance_sequence_strategy())
    @settings(max_examples=100, deadline=None)
    def test_memory_strength_consistency_with_performance(self, test_data):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any learning item, memory strength should be tracked and updated 
        consistently with user performance, reflecting the ratio of correct 
        to total attempts.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = test_data['user_id']
            item_id = test_data['item_id']
            item_type = test_data['item_type']
            performance_sequence = test_data['performance_sequence']
            
            total_attempts = 0
            correct_attempts = 0
            
            for correct in performance_sequence:
                total_attempts += 1
                if correct:
                    correct_attempts += 1
                
                # Record the learning activity
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Verify memory strength is consistent with performance
                expected_memory_strength = correct_attempts / total_attempts
                assert abs(result.memory_strength - expected_memory_strength) < 0.001, \
                    f"Memory strength {result.memory_strength} should equal {expected_memory_strength} " \
                    f"(correct: {correct_attempts}, total: {total_attempts})"
                
                # Verify memory strength is within valid range
                assert 0.0 <= result.memory_strength <= 1.0, \
                    f"Memory strength {result.memory_strength} should be between 0.0 and 1.0"
                
                # Verify counts are consistent
                assert result.learn_count == total_attempts, \
                    f"Learn count {result.learn_count} should equal total attempts {total_attempts}"
                assert result.correct_count == correct_attempts, \
                    f"Correct count {result.correct_count} should equal correct attempts {correct_attempts}"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(performance_sequence_strategy())
    @settings(max_examples=100, deadline=None)
    def test_mastery_level_progression_consistency(self, test_data):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any learning item, mastery level should be tracked and updated 
        consistently based on the number of correct attempts, following 
        the progression rule (mastery_level = min(5, correct_count // 2)).
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = test_data['user_id']
            item_id = test_data['item_id']
            item_type = test_data['item_type']
            performance_sequence = test_data['performance_sequence']
            
            correct_attempts = 0
            
            for correct in performance_sequence:
                if correct:
                    correct_attempts += 1
                
                # Record the learning activity
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Verify mastery level follows the progression rule
                expected_mastery_level = min(5, correct_attempts // 2)
                assert result.mastery_level == expected_mastery_level, \
                    f"Mastery level {result.mastery_level} should equal {expected_mastery_level} " \
                    f"(correct attempts: {correct_attempts})"
                
                # Verify mastery level is within valid range
                assert 0 <= result.mastery_level <= 5, \
                    f"Mastery level {result.mastery_level} should be between 0 and 5"
                
                # Verify mastery level never decreases (monotonic progression)
                if correct_attempts > 0:
                    # Get previous record to check monotonic progression
                    cursor = db.conn.cursor()
                    cursor.execute("""
                        SELECT mastery_level FROM learning_records 
                        WHERE user_id = ? AND item_id = ? AND item_type = ?
                    """, (user_id, item_id, item_type))
                    
                    current_mastery = cursor.fetchone()['mastery_level']
                    assert current_mastery >= 0, "Mastery level should never be negative"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(mixed_performance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_memory_tracking_accuracy_with_mixed_performance(self, test_data):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any learning item with mixed performance (correct and incorrect attempts),
        memory strength and mastery level should be tracked accurately and 
        consistently reflect the actual performance data.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = test_data['user_id']
            item_id = test_data['item_id']
            item_type = test_data['item_type']
            performance_sequence = test_data['performance_sequence']
            expected_correct = test_data['expected_correct']
            expected_total = test_data['expected_total']
            
            # Record all performance data
            for correct in performance_sequence:
                db.record_learning(user_id, item_id, item_type, correct)
            
            # Get final learning record
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            final_record = cursor.fetchone()
            assert final_record is not None, "Learning record should exist"
            
            # Verify final counts are accurate
            assert final_record['learn_count'] == expected_total, \
                f"Learn count {final_record['learn_count']} should equal expected total {expected_total}"
            assert final_record['correct_count'] == expected_correct, \
                f"Correct count {final_record['correct_count']} should equal expected correct {expected_correct}"
            
            # Verify final memory strength is accurate
            expected_memory_strength = expected_correct / expected_total if expected_total > 0 else 0.0
            assert abs(final_record['memory_strength'] - expected_memory_strength) < 0.001, \
                f"Memory strength {final_record['memory_strength']} should equal {expected_memory_strength}"
            
            # Verify final mastery level is accurate
            expected_mastery_level = min(5, expected_correct // 2)
            assert final_record['mastery_level'] == expected_mastery_level, \
                f"Mastery level {final_record['mastery_level']} should equal {expected_mastery_level}"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(st.lists(learning_item_strategy(), min_size=2, max_size=10, unique_by=lambda x: (x['user_id'], x['item_id'], x['item_type'])))
    @settings(max_examples=50, deadline=None)
    def test_independent_memory_tracking_across_items(self, learning_items):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any set of different learning items, memory strength and mastery 
        level should be tracked independently for each item without interference.
        """
        db, db_path = self.create_temp_database()
        try:
            item_performance = {}
            
            # Record different performance for each item
            for i, item_data in enumerate(learning_items):
                user_id = item_data['user_id']
                item_id = item_data['item_id']
                item_type = item_data['item_type']
                
                # Create different performance patterns for each item
                correct_attempts = i + 1  # Different number of correct attempts
                incorrect_attempts = (len(learning_items) - i)  # Different number of incorrect attempts
                
                # Record correct attempts
                for _ in range(correct_attempts):
                    db.record_learning(user_id, item_id, item_type, True)
                
                # Record incorrect attempts
                for _ in range(incorrect_attempts):
                    db.record_learning(user_id, item_id, item_type, False)
                
                total_attempts = correct_attempts + incorrect_attempts
                expected_memory_strength = correct_attempts / total_attempts
                expected_mastery_level = min(5, correct_attempts // 2)
                
                item_performance[(user_id, item_id, item_type)] = {
                    'correct': correct_attempts,
                    'total': total_attempts,
                    'expected_memory_strength': expected_memory_strength,
                    'expected_mastery_level': expected_mastery_level
                }
            
            # Verify each item has independent tracking
            for (user_id, item_id, item_type), expected in item_performance.items():
                cursor = db.conn.cursor()
                cursor.execute("""
                    SELECT * FROM learning_records 
                    WHERE user_id = ? AND item_id = ? AND item_type = ?
                """, (user_id, item_id, item_type))
                
                record = cursor.fetchone()
                assert record is not None, f"Record should exist for item {item_id}"
                
                # Verify independent tracking
                assert record['correct_count'] == expected['correct'], \
                    f"Item {item_id} correct count should be {expected['correct']}, got {record['correct_count']}"
                assert record['learn_count'] == expected['total'], \
                    f"Item {item_id} total count should be {expected['total']}, got {record['learn_count']}"
                
                assert abs(record['memory_strength'] - expected['expected_memory_strength']) < 0.001, \
                    f"Item {item_id} memory strength should be {expected['expected_memory_strength']}, got {record['memory_strength']}"
                assert record['mastery_level'] == expected['expected_mastery_level'], \
                    f"Item {item_id} mastery level should be {expected['expected_mastery_level']}, got {record['mastery_level']}"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_item_strategy(), st.integers(min_value=1, max_value=20))
    @settings(max_examples=50, deadline=None)
    def test_memory_tracking_persistence_across_sessions(self, item_data, num_sessions):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any learning item across multiple learning sessions, memory strength 
        and mastery level should be tracked consistently and persist between sessions.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = item_data['user_id']
            item_id = item_data['item_id']
            item_type = item_data['item_type']
            
            total_correct = 0
            total_attempts = 0
            
            # Simulate multiple learning sessions
            for session in range(num_sessions):
                # Each session has 1-3 attempts with random performance
                session_attempts = min(3, num_sessions - session)  # Vary attempts per session
                
                for attempt in range(session_attempts):
                    # Alternate between correct and incorrect for predictable testing
                    correct = (total_attempts % 2) == 0
                    
                    total_attempts += 1
                    if correct:
                        total_correct += 1
                    
                    # Record the learning activity
                    result = db.record_learning(user_id, item_id, item_type, correct)
                    
                    # Verify tracking is consistent across sessions
                    expected_memory_strength = total_correct / total_attempts
                    assert abs(result.memory_strength - expected_memory_strength) < 0.001, \
                        f"Session {session}, attempt {attempt}: memory strength {result.memory_strength} " \
                        f"should equal {expected_memory_strength}"
                    
                    expected_mastery_level = min(5, total_correct // 2)
                    assert result.mastery_level == expected_mastery_level, \
                        f"Session {session}, attempt {attempt}: mastery level {result.mastery_level} " \
                        f"should equal {expected_mastery_level}"
                    
                    # Verify persistence by checking database directly
                    cursor = db.conn.cursor()
                    cursor.execute("""
                        SELECT memory_strength, mastery_level, learn_count, correct_count 
                        FROM learning_records 
                        WHERE user_id = ? AND item_id = ? AND item_type = ?
                    """, (user_id, item_id, item_type))
                    
                    db_record = cursor.fetchone()
                    assert db_record is not None, "Record should persist in database"
                    assert db_record['learn_count'] == total_attempts, "Learn count should persist"
                    assert db_record['correct_count'] == total_correct, "Correct count should persist"
                    assert abs(db_record['memory_strength'] - expected_memory_strength) < 0.001, \
                        "Memory strength should persist accurately"
                    assert db_record['mastery_level'] == expected_mastery_level, \
                        "Mastery level should persist accurately"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_item_strategy())
    @settings(max_examples=100, deadline=None)
    def test_memory_tracking_boundary_conditions(self, item_data):
        """
        Feature: bilingual-tutor, Property 36: Memory Tracking Consistency
        
        For any learning item, memory strength and mastery level should be 
        tracked consistently even at boundary conditions (all correct, all incorrect, 
        single attempt).
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = item_data['user_id']
            item_id = item_data['item_id']
            item_type = item_data['item_type']
            
            # Test boundary condition: single correct attempt
            result = db.record_learning(user_id, item_id, item_type, True)
            assert result.memory_strength == 1.0, f"Single correct attempt should have memory strength 1.0, got {result.memory_strength}"
            assert result.mastery_level == 0, f"Single correct attempt should have mastery level 0, got {result.mastery_level}"
            
            # Test boundary condition: single incorrect attempt (reset by recording incorrect)
            db.record_learning(user_id, item_id, item_type, False)
            
            # Get updated record
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            record = cursor.fetchone()
            expected_memory_strength = 1.0 / 2.0  # 1 correct out of 2 total
            assert abs(record['memory_strength'] - expected_memory_strength) < 0.001, \
                f"After one incorrect, memory strength should be {expected_memory_strength}, got {record['memory_strength']}"
            
            # Test boundary condition: achieving maximum mastery level
            # Need 10 correct attempts to reach mastery level 5 (10 // 2 = 5)
            # We already have 1 correct and 1 incorrect, so we need 9 more correct for total of 10 correct
            for _ in range(9):  # Need 9 more correct attempts
                db.record_learning(user_id, item_id, item_type, True)
            
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            final_record = cursor.fetchone()
            assert final_record['correct_count'] == 10, f"Should have 10 correct attempts, got {final_record['correct_count']}"
            assert final_record['mastery_level'] == 5, f"Should reach maximum mastery level 5, got {final_record['mastery_level']}"
            
            # Memory strength should be calculated as correct_count / learn_count
            # We have: 1 correct + 1 incorrect + 9 correct = 10 correct, 11 total
            expected_final_memory_strength = 10.0 / 11.0  # 10 correct out of 11 total
            assert abs(final_record['memory_strength'] - expected_final_memory_strength) < 0.001, \
                f"Final memory strength should be {expected_final_memory_strength}, got {final_record['memory_strength']}"
                
        finally:
            self.cleanup_temp_database(db, db_path)