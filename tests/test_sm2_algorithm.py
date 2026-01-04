"""
Property-based tests for SM-2 algorithm correctness in the bilingual tutor system.

Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
Validates: Requirements 17.2
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from bilingual_tutor.storage.database import LearningDatabase, LearningRecord


@st.composite
def learning_record_strategy(draw):
    """Generate random learning records for property-based testing."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    item_id = draw(st.integers(min_value=1, max_value=10000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    learn_count = draw(st.integers(min_value=1, max_value=50))
    correct_count = draw(st.integers(min_value=0, max_value=50))
    # Ensure correct_count doesn't exceed learn_count
    assume(correct_count <= learn_count)
    
    # Generate realistic easiness factor (SM-2 range: 1.3 to 2.5+)
    easiness_factor = draw(st.floats(min_value=1.3, max_value=3.0))
    
    # Generate dates
    base_date = datetime.now() - timedelta(days=draw(st.integers(min_value=1, max_value=365)))
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type,
        'learn_count': learn_count,
        'correct_count': correct_count,
        'easiness_factor': easiness_factor,
        'last_review_date': base_date
    }


@st.composite
def performance_sequence_strategy(draw):
    """Generate sequences of correct/incorrect performance for testing."""
    sequence_length = draw(st.integers(min_value=1, max_value=20))
    return draw(st.lists(st.booleans(), min_size=sequence_length, max_size=sequence_length))


class TestSM2AlgorithmCorrectness:
    """Test SM-2 algorithm correctness properties."""
    
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
    
    @given(learning_record_strategy(), st.booleans())
    @settings(max_examples=100, deadline=None)
    def test_sm2_easiness_factor_bounds(self, record_data, correct_response):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any learning record with performance data, the SM-2 algorithm should 
        calculate valid easiness factors within expected ranges (minimum 1.3).
        """
        db, db_path = self.create_temp_database()
        try:
            # Record initial learning
            result = db.record_learning(
                record_data['user_id'], 
                record_data['item_id'], 
                record_data['item_type'], 
                correct_response
            )
            
            # Verify easiness factor is within valid SM-2 bounds
            assert result.easiness_factor >= 1.3, f"Easiness factor {result.easiness_factor} below minimum 1.3"
            assert result.easiness_factor <= 5.0, f"Easiness factor {result.easiness_factor} above reasonable maximum 5.0"
            assert isinstance(result.easiness_factor, float), "Easiness factor must be a float"
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_record_strategy(), performance_sequence_strategy())
    @settings(max_examples=50, deadline=None)
    def test_sm2_review_interval_progression(self, record_data, performance_sequence):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any sequence of learning performances, review intervals should follow 
        SM-2 algorithm rules: 1 day for first correct, 6 days for second correct,
        then increasing intervals based on easiness factor.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = record_data['user_id']
            item_id = record_data['item_id']
            item_type = record_data['item_type']
            
            previous_interval = 0
            previous_date = datetime.now()
            
            for i, correct in enumerate(performance_sequence):
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Calculate actual interval
                if result.last_review_date and result.next_review_date:
                    actual_interval = (result.next_review_date - result.last_review_date).days
                    
                    if correct:
                        # Check consecutive correct count instead of total learn count
                        consecutive_correct = getattr(result, 'consecutive_correct', 1)
                        
                        if consecutive_correct == 1:
                            # First consecutive correct answer should have 1-day interval
                            assert actual_interval == 1, f"First consecutive correct should have 1-day interval, got {actual_interval}"
                        elif consecutive_correct == 2:
                            # Second consecutive correct answer should have 6-day interval
                            assert actual_interval == 6, f"Second consecutive correct should have 6-day interval, got {actual_interval}"
                        else:
                            # Subsequent intervals should be positive and reasonable
                            assert actual_interval > 0, f"Interval must be positive, got {actual_interval}"
                            assert actual_interval <= 365, f"Interval too large: {actual_interval} days"
                    else:
                        # Incorrect answers should reset to 1-day interval
                        assert actual_interval == 1, f"Incorrect answer should reset to 1-day interval, got {actual_interval}"
                
                previous_date = result.next_review_date
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_record_strategy(), st.integers(min_value=1, max_value=10))
    @settings(max_examples=100, deadline=None)
    def test_sm2_memory_strength_calculation(self, record_data, num_attempts):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any learning record, memory strength should be calculated as the ratio
        of correct answers to total attempts, bounded between 0.0 and 1.0.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = record_data['user_id']
            item_id = record_data['item_id']
            item_type = record_data['item_type']
            
            correct_count = 0
            
            for i in range(num_attempts):
                # Alternate between correct and incorrect for predictable testing
                correct = (i % 2 == 0)
                if correct:
                    correct_count += 1
                
                result = db.record_learning(user_id, item_id, item_type, correct)
                
                # Verify memory strength bounds
                assert 0.0 <= result.memory_strength <= 1.0, f"Memory strength {result.memory_strength} out of bounds [0.0, 1.0]"
                
                # Verify memory strength calculation
                expected_strength = correct_count / (i + 1)
                assert abs(result.memory_strength - expected_strength) < 0.001, \
                    f"Memory strength {result.memory_strength} doesn't match expected {expected_strength}"
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_record_strategy(), st.integers(min_value=1, max_value=20))
    @settings(max_examples=100, deadline=None)
    def test_sm2_mastery_level_progression(self, record_data, correct_answers):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any learning record, mastery level should progress based on correct
        answers and be bounded between 0 and 5.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = record_data['user_id']
            item_id = record_data['item_id']
            item_type = record_data['item_type']
            
            # Provide the specified number of correct answers
            for i in range(correct_answers):
                result = db.record_learning(user_id, item_id, item_type, True)
            
            # Verify mastery level bounds
            assert 0 <= result.mastery_level <= 5, f"Mastery level {result.mastery_level} out of bounds [0, 5]"
            assert isinstance(result.mastery_level, int), "Mastery level must be an integer"
            
            # Verify mastery level progression (should be correct_count // 2, capped at 5)
            expected_mastery = min(5, correct_answers // 2)
            assert result.mastery_level == expected_mastery, \
                f"Mastery level {result.mastery_level} doesn't match expected {expected_mastery}"
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_record_strategy())
    @settings(max_examples=100, deadline=None)
    def test_sm2_easiness_factor_adjustment(self, record_data):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any learning record, easiness factor should be adjusted according to
        SM-2 algorithm: increased for correct answers, decreased for incorrect ones.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = record_data['user_id']
            item_id = record_data['item_id']
            item_type = record_data['item_type']
            
            # Record first learning (correct)
            result1 = db.record_learning(user_id, item_id, item_type, True)
            initial_ef = result1.easiness_factor
            
            # Record second learning (correct) - should maintain or increase EF
            result2 = db.record_learning(user_id, item_id, item_type, True)
            correct_ef = result2.easiness_factor
            
            # Record third learning (incorrect) - should decrease EF
            result3 = db.record_learning(user_id, item_id, item_type, False)
            incorrect_ef = result3.easiness_factor
            
            # Verify EF adjustments follow SM-2 logic
            # For correct answers (quality=5), EF should stay same or increase slightly
            assert correct_ef >= initial_ef - 0.1, f"EF decreased too much for correct answer: {initial_ef} -> {correct_ef}"
            
            # For incorrect answers (quality=2), EF should decrease
            assert incorrect_ef < correct_ef, f"EF should decrease for incorrect answer: {correct_ef} -> {incorrect_ef}"
            
            # EF should never go below 1.3
            assert incorrect_ef >= 1.3, f"EF {incorrect_ef} went below minimum 1.3"
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(learning_record_strategy(), st.integers(min_value=1, max_value=5))
    @settings(max_examples=100, deadline=None)
    def test_sm2_review_date_calculation(self, record_data, days_offset):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any learning record, next review date should be calculated correctly
        based on the current date plus the calculated interval.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = record_data['user_id']
            item_id = record_data['item_id']
            item_type = record_data['item_type']
            
            # Record the learning at a specific time
            before_time = datetime.now()
            result = db.record_learning(user_id, item_id, item_type, True)
            after_time = datetime.now()
            
            # Verify review dates are set
            assert result.last_review_date is not None, "Last review date should be set"
            assert result.next_review_date is not None, "Next review date should be set"
            
            # Verify last review date is within reasonable bounds
            assert before_time <= result.last_review_date <= after_time, \
                "Last review date should be between before and after recording"
            
            # Verify next review date is after last review date
            assert result.next_review_date > result.last_review_date, \
                "Next review date should be after last review date"
            
            # Verify the interval is reasonable (at least 1 day for first correct answer)
            interval = (result.next_review_date - result.last_review_date).days
            assert interval >= 1, f"Review interval {interval} should be at least 1 day"
            assert interval <= 365, f"Review interval {interval} should not exceed 1 year"
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(st.text(min_size=1, max_size=20), st.integers(min_value=1, max_value=100), 
           st.sampled_from(["vocabulary", "grammar", "content"]))
    @settings(max_examples=100, deadline=None)
    def test_sm2_new_record_initialization(self, user_id, item_id, item_type):
        """
        Feature: bilingual-tutor, Property 34: SM-2 Algorithm Correctness
        
        For any new learning record, initial values should be set correctly
        according to SM-2 algorithm defaults.
        """
        db, db_path = self.create_temp_database()
        try:
            # Record first learning attempt
            result = db.record_learning(user_id, item_id, item_type, True)
            
            # Verify initial values
            assert result.learn_count == 1, f"Initial learn count should be 1, got {result.learn_count}"
            assert result.correct_count == 1, f"Initial correct count should be 1 for correct answer, got {result.correct_count}"
            assert result.easiness_factor == 2.5, f"Initial easiness factor should be 2.5, got {result.easiness_factor}"
            assert result.memory_strength == 1.0, f"Initial memory strength should be 1.0 for correct answer, got {result.memory_strength}"
            assert result.mastery_level == 0, f"Initial mastery level should be 0, got {result.mastery_level}"
            
            # Test with incorrect first answer
            result_incorrect = db.record_learning(user_id + "_incorrect", item_id, item_type, False)
            assert result_incorrect.correct_count == 0, f"Initial correct count should be 0 for incorrect answer, got {result_incorrect.correct_count}"
            assert result_incorrect.memory_strength == 0.0, f"Initial memory strength should be 0.0 for incorrect answer, got {result_incorrect.memory_strength}"
        finally:
            self.cleanup_temp_database(db, db_path)