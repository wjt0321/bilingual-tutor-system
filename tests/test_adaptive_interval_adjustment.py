"""
Property-based tests for adaptive interval adjustment in the bilingual tutor system.

Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
Validates: Requirements 17.6
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from bilingual_tutor.storage.database import LearningDatabase, LearningRecord


@st.composite
def user_performance_sequence_strategy(draw):
    """Generate sequences of user performance for testing adaptive intervals."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    item_id = draw(st.integers(min_value=1, max_value=10000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    
    # Generate a sequence of correct/incorrect responses
    sequence_length = draw(st.integers(min_value=2, max_value=15))
    performance_sequence = draw(st.lists(st.booleans(), min_size=sequence_length, max_size=sequence_length))
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type,
        'performance_sequence': performance_sequence
    }


@st.composite
def single_performance_strategy(draw):
    """Generate single performance data for testing interval adjustment."""
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


class TestAdaptiveIntervalAdjustment:
    """Test adaptive interval adjustment properties."""
    
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
    
    @given(single_performance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_correct_answer_extends_interval(self, performance_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any correct user performance input, the system should extend the review 
        interval compared to the previous interval (or set appropriate initial intervals).
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = performance_data['user_id']
            item_id = performance_data['item_id']
            item_type = performance_data['item_type']
            
            # Record first correct answer
            result1 = db.record_learning(user_id, item_id, item_type, True)
            first_interval = (result1.next_review_date - result1.last_review_date).days
            
            # First correct answer should have 1-day interval
            assert first_interval == 1, f"First correct answer should have 1-day interval, got {first_interval}"
            
            # Record second correct answer
            result2 = db.record_learning(user_id, item_id, item_type, True)
            second_interval = (result2.next_review_date - result2.last_review_date).days
            
            # Second correct answer should have 6-day interval (extended from 1)
            assert second_interval == 6, f"Second correct answer should have 6-day interval, got {second_interval}"
            assert second_interval > first_interval, f"Second interval {second_interval} should be greater than first {first_interval}"
            
            # Record third correct answer
            result3 = db.record_learning(user_id, item_id, item_type, True)
            third_interval = (result3.next_review_date - result3.last_review_date).days
            
            # Third correct answer should have interval > 6 days (extended based on easiness factor)
            assert third_interval > second_interval, f"Third interval {third_interval} should be greater than second {second_interval}"
            assert third_interval > 6, f"Third interval {third_interval} should be greater than 6 days"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(single_performance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_incorrect_answer_shortens_interval(self, performance_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any incorrect user performance input, the system should shorten the review 
        interval to 1 day, regardless of previous performance.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = performance_data['user_id']
            item_id = performance_data['item_id']
            item_type = performance_data['item_type']
            
            # Build up some correct answers first to establish longer intervals
            db.record_learning(user_id, item_id, item_type, True)  # 1 day
            db.record_learning(user_id, item_id, item_type, True)  # 6 days
            result_before = db.record_learning(user_id, item_id, item_type, True)  # longer interval
            
            interval_before = (result_before.next_review_date - result_before.last_review_date).days
            assert interval_before > 6, f"Should have established longer interval, got {interval_before}"
            
            # Now record an incorrect answer
            result_after = db.record_learning(user_id, item_id, item_type, False)
            interval_after = (result_after.next_review_date - result_after.last_review_date).days
            
            # Incorrect answer should reset interval to 1 day
            assert interval_after == 1, f"Incorrect answer should reset interval to 1 day, got {interval_after}"
            assert interval_after < interval_before, f"Interval after incorrect {interval_after} should be less than before {interval_before}"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(user_performance_sequence_strategy())
    @settings(max_examples=50, deadline=None)
    def test_interval_adjustment_consistency(self, sequence_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any sequence of user performance inputs, the system should consistently 
        adjust intervals: extending for correct answers and resetting to 1 day for incorrect ones.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = sequence_data['user_id']
            item_id = sequence_data['item_id']
            item_type = sequence_data['item_type']
            performance_sequence = sequence_data['performance_sequence']
            
            previous_interval = 0
            consecutive_correct_from_start = 0  # Track consecutive correct from the beginning or after last incorrect
            
            for i, correct in enumerate(performance_sequence):
                result = db.record_learning(user_id, item_id, item_type, correct)
                current_interval = (result.next_review_date - result.last_review_date).days
                
                if correct:
                    consecutive_correct_from_start += 1
                    
                    if consecutive_correct_from_start == 1:
                        # First correct (or first after incorrect) should be 1 day
                        assert current_interval == 1, f"First correct should have 1-day interval, got {current_interval}"
                    elif consecutive_correct_from_start == 2:
                        # Second consecutive correct should be 6 days
                        assert current_interval == 6, f"Second consecutive correct should have 6-day interval, got {current_interval}"
                    else:
                        # Subsequent correct answers should have increasing intervals
                        assert current_interval > 6, f"Subsequent correct answers should have intervals > 6 days, got {current_interval}"
                        if previous_interval > 0:
                            # Should be greater than or equal to previous (due to easiness factor)
                            assert current_interval >= previous_interval * 0.8, \
                                f"Interval {current_interval} should not decrease significantly from {previous_interval}"
                else:
                    # Incorrect answer should reset to 1 day and reset consecutive count
                    consecutive_correct_from_start = 0
                    assert current_interval == 1, f"Incorrect answer should reset interval to 1 day, got {current_interval}"
                
                previous_interval = current_interval
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(single_performance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_easiness_factor_affects_interval_extension(self, performance_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any user performance input, the easiness factor should influence how much 
        intervals are extended for correct answers.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = performance_data['user_id']
            item_id = performance_data['item_id']
            item_type = performance_data['item_type']
            
            # Build up to third correct answer to see easiness factor effect
            db.record_learning(user_id, item_id, item_type, True)  # 1 day
            db.record_learning(user_id, item_id, item_type, True)  # 6 days
            
            # Record third correct answer and check easiness factor influence
            result = db.record_learning(user_id, item_id, item_type, True)
            interval = (result.next_review_date - result.last_review_date).days
            easiness_factor = result.easiness_factor
            
            # Interval should be influenced by easiness factor
            # For SM-2, interval = previous_interval * easiness_factor
            # Since previous was 6 days, new interval should be approximately 6 * EF
            expected_min_interval = int(6 * 1.3)  # Minimum EF is 1.3
            expected_max_interval = int(6 * 3.0)  # Reasonable maximum EF
            
            assert expected_min_interval <= interval <= expected_max_interval, \
                f"Interval {interval} should be between {expected_min_interval} and {expected_max_interval} (EF: {easiness_factor})"
            
            # Easiness factor should be within valid range
            assert 1.3 <= easiness_factor <= 5.0, f"Easiness factor {easiness_factor} should be between 1.3 and 5.0"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(user_performance_sequence_strategy())
    @settings(max_examples=50, deadline=None)
    def test_interval_bounds_are_reasonable(self, sequence_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any sequence of user performance inputs, all calculated intervals should 
        be within reasonable bounds (minimum 1 day, maximum reasonable limit).
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = sequence_data['user_id']
            item_id = sequence_data['item_id']
            item_type = sequence_data['item_type']
            performance_sequence = sequence_data['performance_sequence']
            
            for correct in performance_sequence:
                result = db.record_learning(user_id, item_id, item_type, correct)
                interval = (result.next_review_date - result.last_review_date).days
                
                # All intervals should be at least 1 day
                assert interval >= 1, f"Interval {interval} should be at least 1 day"
                
                # All intervals should be reasonable (not more than 2 years)
                assert interval <= 730, f"Interval {interval} should not exceed 730 days (2 years)"
                
                # Next review date should be after last review date
                assert result.next_review_date > result.last_review_date, \
                    "Next review date should be after last review date"
                
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(single_performance_strategy(), st.integers(min_value=1, max_value=10))
    @settings(max_examples=100, deadline=None)
    def test_repeated_correct_answers_increase_intervals(self, performance_data, num_correct):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any sequence of repeated correct answers, intervals should generally increase 
        or stay stable, demonstrating the adaptive extension behavior.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = performance_data['user_id']
            item_id = performance_data['item_id']
            item_type = performance_data['item_type']
            
            intervals = []
            
            # Record multiple correct answers
            for i in range(num_correct):
                result = db.record_learning(user_id, item_id, item_type, True)
                interval = (result.next_review_date - result.last_review_date).days
                intervals.append(interval)
            
            # Check that intervals follow expected pattern
            if len(intervals) >= 1:
                assert intervals[0] == 1, f"First interval should be 1 day, got {intervals[0]}"
            
            if len(intervals) >= 2:
                assert intervals[1] == 6, f"Second interval should be 6 days, got {intervals[1]}"
            
            if len(intervals) >= 3:
                # From third interval onwards, should be increasing or stable
                for i in range(2, len(intervals)):
                    assert intervals[i] >= intervals[i-1] * 0.8, \
                        f"Interval {i+1} ({intervals[i]}) should not decrease significantly from interval {i} ({intervals[i-1]})"
                    assert intervals[i] > 6, f"Interval {i+1} ({intervals[i]}) should be greater than 6 days"
            
        finally:
            self.cleanup_temp_database(db, db_path)
    
    @given(single_performance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_mixed_performance_interval_adjustment(self, performance_data):
        """
        Feature: bilingual-tutor, Property 38: Adaptive Interval Adjustment
        
        For any mixed sequence of correct and incorrect answers, the system should 
        appropriately adjust intervals: extending for correct, resetting for incorrect.
        """
        db, db_path = self.create_temp_database()
        try:
            user_id = performance_data['user_id']
            item_id = performance_data['item_id']
            item_type = performance_data['item_type']
            
            # Test pattern: correct -> correct -> incorrect -> correct
            
            # First correct: should be 1 day
            result1 = db.record_learning(user_id, item_id, item_type, True)
            interval1 = (result1.next_review_date - result1.last_review_date).days
            assert interval1 == 1, f"First correct should be 1 day, got {interval1}"
            
            # Second correct: should be 6 days
            result2 = db.record_learning(user_id, item_id, item_type, True)
            interval2 = (result2.next_review_date - result2.last_review_date).days
            assert interval2 == 6, f"Second correct should be 6 days, got {interval2}"
            
            # Incorrect: should reset to 1 day
            result3 = db.record_learning(user_id, item_id, item_type, False)
            interval3 = (result3.next_review_date - result3.last_review_date).days
            assert interval3 == 1, f"Incorrect should reset to 1 day, got {interval3}"
            
            # Correct after incorrect: should be 1 day (restart pattern)
            result4 = db.record_learning(user_id, item_id, item_type, True)
            interval4 = (result4.next_review_date - result4.last_review_date).days
            assert interval4 == 1, f"Correct after incorrect should be 1 day, got {interval4}"
            
            # Verify the adjustment pattern
            assert interval2 > interval1, "Second interval should be greater than first"
            assert interval3 < interval2, "Incorrect should reduce interval"
            assert interval4 == interval1, "Pattern should restart after incorrect"
            
        finally:
            self.cleanup_temp_database(db, db_path)