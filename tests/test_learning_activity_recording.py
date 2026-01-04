"""
Property-based tests for learning activity recording completeness in the bilingual tutor system.

Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
Validates: Requirements 17.3
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from bilingual_tutor.storage.database import LearningDatabase, LearningRecord


@st.composite
def learning_activity_strategy(draw):
    """Generate random learning activities for property-based testing."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    item_id = draw(st.integers(min_value=1, max_value=10000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    correct = draw(st.booleans())
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type,
        'correct': correct
    }


@st.composite
def multiple_activities_strategy(draw):
    """Generate sequences of learning activities for the same user and item."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    item_id = draw(st.integers(min_value=1, max_value=10000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    
    # Generate a sequence of performance results
    num_activities = draw(st.integers(min_value=1, max_value=20))
    performance_sequence = draw(st.lists(st.booleans(), min_size=num_activities, max_size=num_activities))
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type,
        'performance_sequence': performance_sequence
    }


class TestLearningActivityRecordingCompleteness:
    """Test learning activity recording completeness properties."""
    
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
    
    @given(learning_activity_strategy())
    @settings(max_examples=100, deadline=None)
    def test_learning_activity_result_recording(self, activity_data):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any completed learning activity, the system should record the result
        and create a learning record with all required fields populated.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = activity_data['user_id']
            item_id = activity_data['item_id']
            item_type = activity_data['item_type']
            correct = activity_data['correct']
            
            # Record the learning activity
            before_time = datetime.now()
            result = db.record_learning(user_id, item_id, item_type, correct)
            after_time = datetime.now()
            
            # Verify that a learning record was created and returned
            assert result is not None, "Learning record should be created and returned"
            assert isinstance(result, LearningRecord), "Result should be a LearningRecord instance"
            
            # Verify all required fields are populated
            assert result.user_id == user_id, f"User ID should be {user_id}, got {result.user_id}"
            assert result.item_id == item_id, f"Item ID should be {item_id}, got {result.item_id}"
            assert result.item_type == item_type, f"Item type should be {item_type}, got {result.item_type}"
            
            # Verify learning counts are recorded
            assert result.learn_count >= 1, f"Learn count should be at least 1, got {result.learn_count}"
            assert result.correct_count >= 0, f"Correct count should be non-negative, got {result.correct_count}"
            assert result.correct_count <= result.learn_count, "Correct count should not exceed learn count"
            
            # Verify performance is recorded correctly
            if correct:
                assert result.correct_count >= 1, "Correct count should be at least 1 for correct answer"
            
            # Verify dates are set
            assert result.last_review_date is not None, "Last review date should be set"
            assert result.next_review_date is not None, "Next review date should be set"
            
            # Verify review dates are reasonable
            assert before_time <= result.last_review_date <= after_time, "Last review date should be within recording time"
            assert result.next_review_date > result.last_review_date, "Next review date should be after last review date"
            
            # Verify memory strength and mastery level are set
            assert 0.0 <= result.memory_strength <= 1.0, f"Memory strength {result.memory_strength} should be between 0.0 and 1.0"
            assert 0 <= result.mastery_level <= 5, f"Mastery level {result.mastery_level} should be between 0 and 5"
            
            # Verify easiness factor is set to valid SM-2 range
            assert result.easiness_factor >= 1.3, f"Easiness factor {result.easiness_factor} should be at least 1.3"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_activity_strategy())
    @settings(max_examples=100, deadline=None)
    def test_next_review_date_calculation(self, activity_data):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any completed learning activity, the system should calculate a next
        review date based on performance using the spaced repetition algorithm.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = activity_data['user_id']
            item_id = activity_data['item_id']
            item_type = activity_data['item_type']
            correct = activity_data['correct']
            
            # Record the learning activity
            result = db.record_learning(user_id, item_id, item_type, correct)
            
            # Verify next review date is calculated
            assert result.next_review_date is not None, "Next review date must be calculated"
            
            # Calculate the interval
            interval = (result.next_review_date - result.last_review_date).days
            
            # Verify interval is reasonable based on performance
            if correct:
                # For correct answers, interval should be at least 1 day
                assert interval >= 1, f"Correct answer should have at least 1-day interval, got {interval}"
                # First correct answer should be 1 day
                if result.learn_count == 1:
                    assert interval == 1, f"First correct answer should have 1-day interval, got {interval}"
            else:
                # For incorrect answers, interval should be 1 day (reset)
                assert interval == 1, f"Incorrect answer should have 1-day interval, got {interval}"
            
            # Verify interval is not unreasonably long
            assert interval <= 365, f"Review interval {interval} should not exceed 1 year"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(multiple_activities_strategy())
    @settings(max_examples=50, deadline=None)
    def test_sequential_activity_recording(self, activities_data):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any sequence of completed learning activities for the same item,
        the system should record each result and update the learning record
        with cumulative performance data.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = activities_data['user_id']
            item_id = activities_data['item_id']
            item_type = activities_data['item_type']
            performance_sequence = activities_data['performance_sequence']
            
            previous_result = None
            total_correct = 0
            
            for i, correct in enumerate(performance_sequence):
                if correct:
                    total_correct += 1
                
                # Record the learning activity
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Verify learning record is updated correctly
                assert result.learn_count == i + 1, f"Learn count should be {i + 1}, got {result.learn_count}"
                assert result.correct_count == total_correct, f"Correct count should be {total_correct}, got {result.correct_count}"
                
                # Verify memory strength is calculated correctly
                expected_memory_strength = total_correct / (i + 1)
                assert abs(result.memory_strength - expected_memory_strength) < 0.001, \
                    f"Memory strength {result.memory_strength} should be {expected_memory_strength}"
                
                # Verify mastery level progression
                expected_mastery = min(5, total_correct // 2)
                assert result.mastery_level == expected_mastery, \
                    f"Mastery level {result.mastery_level} should be {expected_mastery}"
                
                # Verify dates are updated
                assert result.last_review_date is not None, "Last review date should be updated"
                assert result.next_review_date is not None, "Next review date should be updated"
                
                if previous_result:
                    # Current last review should be after or equal to previous last review
                    assert result.last_review_date >= previous_result.last_review_date, \
                        "Last review date should not go backwards"
                
                previous_result = result
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_activity_strategy())
    @settings(max_examples=100, deadline=None)
    def test_learning_record_persistence(self, activity_data):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any completed learning activity, the system should persist the
        learning record to the database so it can be retrieved later.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = activity_data['user_id']
            item_id = activity_data['item_id']
            item_type = activity_data['item_type']
            correct = activity_data['correct']
            
            # Record the learning activity
            result = db.record_learning(user_id, item_id, item_type, correct)
            
            # Verify the record can be retrieved from database
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            db_record = cursor.fetchone()
            assert db_record is not None, "Learning record should be persisted in database"
            
            # Verify all fields match
            assert db_record['user_id'] == user_id, "User ID should match in database"
            assert db_record['item_id'] == item_id, "Item ID should match in database"
            assert db_record['item_type'] == item_type, "Item type should match in database"
            assert db_record['learn_count'] == result.learn_count, "Learn count should match in database"
            assert db_record['correct_count'] == result.correct_count, "Correct count should match in database"
            assert db_record['memory_strength'] == result.memory_strength, "Memory strength should match in database"
            assert db_record['mastery_level'] == result.mastery_level, "Mastery level should match in database"
            assert db_record['easiness_factor'] == result.easiness_factor, "Easiness factor should match in database"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(st.lists(learning_activity_strategy(), min_size=1, max_size=10))
    @settings(max_examples=50, deadline=None)
    def test_multiple_users_activity_recording(self, activities_list):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any set of learning activities from different users, the system
        should record each activity independently without interference.
        """
        db, db_path = self.create_temp_database()
        try:
            recorded_activities = []
            
            # Record all activities
            for activity_data in activities_list:
                user_id = activity_data['user_id']
                item_id = activity_data['item_id']
                item_type = activity_data['item_type']
                correct = activity_data['correct']
                
                result = db.record_learning(user_id, item_id, item_type, correct)
                recorded_activities.append((activity_data, result))
            
            # Verify each activity was recorded correctly
            for activity_data, result in recorded_activities:
                # Verify the record exists and has correct data
                cursor = db.conn.cursor()
                cursor.execute("""
                    SELECT * FROM learning_records 
                    WHERE user_id = ? AND item_id = ? AND item_type = ?
                """, (activity_data['user_id'], activity_data['item_id'], activity_data['item_type']))
                
                db_record = cursor.fetchone()
                assert db_record is not None, f"Record should exist for user {activity_data['user_id']}"
                
                # Verify basic fields
                assert db_record['user_id'] == activity_data['user_id'], "User ID should match"
                assert db_record['item_id'] == activity_data['item_id'], "Item ID should match"
                assert db_record['item_type'] == activity_data['item_type'], "Item type should match"
                
                # Verify dates are set
                assert db_record['last_review_date'] is not None, "Last review date should be set"
                assert db_record['next_review_date'] is not None, "Next review date should be set"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_activity_strategy(), st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, deadline=None)
    def test_repeated_activity_recording_updates(self, activity_data, num_repetitions):
        """
        Feature: bilingual-tutor, Property 35: Learning Activity Recording Completeness
        
        For any learning activity repeated multiple times, the system should
        update the existing record rather than creating duplicates.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = activity_data['user_id']
            item_id = activity_data['item_id']
            item_type = activity_data['item_type']
            correct = activity_data['correct']
            
            # Record the same activity multiple times
            for i in range(num_repetitions):
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Verify learn count increases
                assert result.learn_count == i + 1, f"Learn count should be {i + 1}, got {result.learn_count}"
            
            # Verify only one record exists in database
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            count = cursor.fetchone()['count']
            assert count == 1, f"Should have exactly 1 record, found {count}"
            
            # Verify final record has correct totals
            cursor.execute("""
                SELECT * FROM learning_records 
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (user_id, item_id, item_type))
            
            final_record = cursor.fetchone()
            assert final_record['learn_count'] == num_repetitions, \
                f"Final learn count should be {num_repetitions}, got {final_record['learn_count']}"
            
            expected_correct = num_repetitions if correct else 0
            assert final_record['correct_count'] == expected_correct, \
                f"Final correct count should be {expected_correct}, got {final_record['correct_count']}"
                
        finally:
            self.cleanup_temp_database(db, db_path)