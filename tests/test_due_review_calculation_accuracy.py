"""
Property-based tests for due review calculation accuracy in bilingual tutor system.

Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
Validates: Requirements 17.5
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from bilingual_tutor.storage.database import LearningDatabase, LearningRecord


# ==================== 测试常量 ====================
MIN_USER_ID_LENGTH = 1
MAX_USER_ID_LENGTH = 20
MIN_ITEM_ID = 1
MAX_ITEM_ID = 10000
MIN_ITEMS_PER_USER = 2
MAX_ITEMS_PER_USER = 8
TIME_TOLERANCE_SECONDS = 2
DEFAULT_TEST_LIMIT = 10
HYPOTHESIS_MAX_EXAMPLES_FAST = 20
HYPOTHESIS_MAX_EXAMPLES_NORMAL = 50
HYPOTHESIS_MAX_EXAMPLES_SLOW = 100


# ==================== Hypothesis策略 ====================
@st.composite
def learning_item_strategy(draw):
    """Generate random learning items for property-based testing."""
    user_id = draw(st.text(
        min_size=MIN_USER_ID_LENGTH, 
        max_size=MAX_USER_ID_LENGTH,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
    ))
    item_id = draw(st.integers(min_value=MIN_ITEM_ID, max_value=MAX_ITEM_ID))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    
    return {
        'user_id': user_id,
        'item_id': item_id,
        'item_type': item_type
    }


@st.composite
def review_schedule_strategy(draw):
    """Generate learning items with specific review schedules for testing."""
    learning_item = draw(learning_item_strategy())
    
    # Generate a base time for scheduling
    base_time = datetime.now()
    
    # Generate different review scenarios
    scenario = draw(st.sampled_from([
        "due_now",      # Items due for review now
        "due_past",     # Items overdue for review
        "due_future",   # Items not yet due for review
        "mixed"         # Mix of due and not due items
    ]))
    
    if scenario == "due_now":
        # Items due within the last hour
        review_offset = draw(st.integers(min_value=-60, max_value=0))  # minutes
        next_review_date = base_time + timedelta(minutes=review_offset)
    elif scenario == "due_past":
        # Items overdue (1 hour to 30 days ago)
        review_offset = draw(st.integers(min_value=-30*24*60, max_value=-60))  # minutes
        next_review_date = base_time + timedelta(minutes=review_offset)
    elif scenario == "due_future":
        # Items not yet due (1 hour to 30 days in future)
        review_offset = draw(st.integers(min_value=60, max_value=30*24*60))  # minutes
        next_review_date = base_time + timedelta(minutes=review_offset)
    else:  # mixed
        # Random offset between -30 days and +30 days
        review_offset = draw(st.integers(min_value=-30*24*60, max_value=30*24*60))  # minutes
        next_review_date = base_time + timedelta(minutes=review_offset)
    
    return {
        **learning_item,
        'next_review_date': next_review_date,
        'scenario': scenario,
        'base_time': base_time
    }


@st.composite
def multiple_items_strategy(draw):
    """Generate multiple learning items with different review schedules."""
    num_items = draw(st.integers(min_value=MIN_ITEMS_PER_USER, max_value=MAX_ITEMS_PER_USER))
    
    # Use a simpler approach to generate unique items
    base_user_id = draw(st.text(
        min_size=1, 
        max_size=10, 
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
    ))
    base_item_id = draw(st.integers(min_value=MIN_ITEM_ID, max_value=1000))
    item_type = draw(st.sampled_from(["vocabulary", "grammar", "content"]))
    
    items = []
    base_time = datetime.now()
    
    for i in range(num_items):
        # Create unique items by incrementing IDs
        user_id = f"{base_user_id}_{i}" if i > 0 else base_user_id
        item_id = base_item_id + i
        
        # Generate review dates with different scenarios
        scenario = draw(st.sampled_from(["due_now", "due_past", "due_future"]))
        
        if scenario == "due_now":
            review_offset = draw(st.integers(min_value=-60, max_value=0))  # minutes
        elif scenario == "due_past":
            review_offset = draw(st.integers(min_value=-24*60, max_value=-60))  # minutes
        else:  # due_future
            review_offset = draw(st.integers(min_value=60, max_value=24*60))  # minutes
        
        next_review_date = base_time + timedelta(minutes=review_offset)
        
        items.append({
            'user_id': user_id,
            'item_id': item_id,
            'item_type': item_type,
            'next_review_date': next_review_date,
            'scenario': scenario,
            'base_time': base_time
        })
    
    return items


# ==================== pytest Fixture ====================
@pytest.fixture
def temp_database():
    """自动创建和清理临时数据库的fixture"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()
    db = LearningDatabase(temp_file.name)
    yield db
    db.close()
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


# ==================== 辅助方法 ====================
class TestDueReviewCalculationAccuracy:
    """Test due review calculation accuracy properties."""
    
    def _update_review_date(
        self, 
        db: LearningDatabase, 
        user_id: str, 
        item_id: int, 
        item_type: str, 
        review_date: datetime
    ) -> None:
        """通用的复习日期更新方法"""
        with db._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learning_records 
                SET next_review_date = ?
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (review_date.isoformat(), user_id, item_id, item_type))
            conn.commit()
    
    def _update_memory_strength(
        self,
        db: LearningDatabase,
        user_id: str,
        item_id: int,
        item_type: str,
        memory_strength: float
    ) -> None:
        """更新记忆强度"""
        with db._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learning_records 
                SET memory_strength = ?
                WHERE user_id = ? AND item_id = ? AND item_type = ?
            """, (memory_strength, user_id, item_id, item_type))
            conn.commit()
    
    def _should_be_due(self, review_date: datetime, current_time: datetime) -> bool:
        """判断项目是否到期（带时间容差）"""
        tolerance = timedelta(seconds=TIME_TOLERANCE_SECONDS)
        return review_date <= (current_time + tolerance)
    
    def _format_assertion_message(
        self, 
        title: str, 
        details: Dict[str, Any]
    ) -> str:
        """格式化断言消息为结构化格式"""
        message_lines = [title]
        for key, value in details.items():
            message_lines.append(f"  {key}: {value}")
        return "\n".join(message_lines)
    
    def setup_learning_record_with_review_date(
        self, 
        db: LearningDatabase, 
        user_id: str, 
        item_id: int, 
        item_type: str, 
        next_review_date: datetime
    ) -> None:
        """Set up a learning record with a specific next review date."""
        # First create a learning record
        db.record_learning(user_id, item_id, item_type, True)
        
        # Then manually update next review date for testing
        self._update_review_date(db, user_id, item_id, item_type, next_review_date)
    
    @given(review_schedule_strategy())
    @settings(max_examples=HYPOTHESIS_MAX_EXAMPLES_SLOW, deadline=None, 
               suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_due_review_calculation_single_item(self, temp_database, test_data):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any user at any given time, due review list should correctly 
        include all items that have passed their review date according to 
        Ebbinghaus curve.
        """
        # Clear any existing data from previous Hypothesis examples
        with temp_database._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM learning_records")
            conn.commit()
        
        user_id = test_data['user_id']
        item_id = test_data['item_id']
        item_type = test_data['item_type']
        next_review_date = test_data['next_review_date']
        scenario = test_data['scenario']
        base_time = test_data['base_time']
        
        # Set up learning record with specific review date
        self.setup_learning_record_with_review_date(temp_database, user_id, item_id, item_type, next_review_date)
        
        # Get due reviews at base time
        due_reviews = temp_database.get_due_reviews(user_id, item_type)
        
        # Check if item should be in the due reviews list
        current_time = datetime.now()
        should_be_due = self._should_be_due(next_review_date, current_time)
        
        # Find our specific item in results
        found_item = None
        for review in due_reviews:
            if (review['user_id'] == user_id and 
                review['item_id'] == item_id and 
                review['item_type'] == item_type):
                found_item = review
                break
        
        if should_be_due:
            assert found_item is not None, self._format_assertion_message(
                "Item should be in due reviews",
                {
                    'User ID': user_id,
                    'Item ID': item_id,
                    'Item Type': item_type,
                    'Review Date': next_review_date,
                    'Current Time': current_time,
                    'Scenario': scenario
                }
            )
            
            # Verify review date in returned item
            returned_review_date = datetime.fromisoformat(found_item['next_review_date'])
            assert returned_review_date <= (current_time + timedelta(seconds=TIME_TOLERANCE_SECONDS)), \
                f"Returned item should have review date <= current time: {returned_review_date} vs {current_time}"
        else:
            assert found_item is None, self._format_assertion_message(
                "Item should NOT be in due reviews",
                {
                    'User ID': user_id,
                    'Item ID': item_id,
                    'Item Type': item_type,
                    'Review Date': next_review_date,
                    'Current Time': current_time,
                    'Scenario': scenario
                }
            )
    
    @given(multiple_items_strategy())
    @settings(max_examples=HYPOTHESIS_MAX_EXAMPLES_NORMAL, deadline=None, 
               suppress_health_check=[HealthCheck.large_base_example, HealthCheck.function_scoped_fixture])
    def test_due_review_calculation_multiple_items(self, temp_database, test_items):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any user with multiple learning items, due review list should 
        correctly include only those items that have passed their review date.
        """
        # Group items by user for testing
        items_by_user: Dict[str, List[Dict[str, Any]]] = {}
        for item in test_items:
            user_id = item['user_id']
            if user_id not in items_by_user:
                items_by_user[user_id] = []
            items_by_user[user_id].append(item)
        
        # Set up all learning records
        for item in test_items:
            self.setup_learning_record_with_review_date(
                temp_database, item['user_id'], item['item_id'], 
                item['item_type'], item['next_review_date']
            )
        
        current_time = datetime.now()
        
        # Test each user's due reviews
        for user_id, user_items in items_by_user.items():
            due_reviews = temp_database.get_due_reviews(user_id)
            
            # Calculate expected due items
            expected_due_items = []
            expected_not_due_items = []
            
            for item in user_items:
                if self._should_be_due(item['next_review_date'], current_time):
                    expected_due_items.append(item)
                else:
                    expected_not_due_items.append(item)
            
            # Verify all expected due items are in results
            for expected_item in expected_due_items:
                found = any(
                    (review['user_id'] == expected_item['user_id'] and
                     review['item_id'] == expected_item['item_id'] and
                     review['item_type'] == expected_item['item_type'])
                    for review in due_reviews
                )
                
                assert found, self._format_assertion_message(
                    "Expected due item not found",
                    {
                        'User ID': expected_item['user_id'],
                        'Item ID': expected_item['item_id'],
                        'Item Type': expected_item['item_type'],
                        'Review Date': expected_item['next_review_date']
                    }
                )
            
            # Verify no not-due items are in results
            for not_due_item in expected_not_due_items:
                found = any(
                    (review['user_id'] == not_due_item['user_id'] and
                     review['item_id'] == not_due_item['item_id'] and
                     review['item_type'] == not_due_item['item_type'])
                    for review in due_reviews
                )
                
                assert not found, self._format_assertion_message(
                    "Not-due item incorrectly included",
                    {
                        'User ID': not_due_item['user_id'],
                        'Item ID': not_due_item['item_id'],
                        'Item Type': not_due_item['item_type'],
                        'Review Date': not_due_item['next_review_date']
                    }
                )
    
    @given(learning_item_strategy(), st.integers(min_value=1, max_value=10))
    @settings(max_examples=HYPOTHESIS_MAX_EXAMPLES_SLOW, deadline=None,
               suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_due_review_calculation_with_time_progression(self, temp_database, item_data, days_ahead):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any learning item, as time progresses, items should become due 
        for review at the correct time according to their scheduled review date.
        """
        user_id = item_data['user_id']
        item_id = item_data['item_id']
        item_type = item_data['item_type']
        
        # Set up a learning record with a future review date
        future_review_date = datetime.now() + timedelta(days=days_ahead)
        self.setup_learning_record_with_review_date(temp_database, user_id, item_id, item_type, future_review_date)
        
        # Check that item is not due now
        current_due_reviews = temp_database.get_due_reviews(user_id, item_type)
        current_item_found = any(
            review['item_id'] == item_id and review['item_type'] == item_type
            for review in current_due_reviews
        )
        assert not current_item_found, \
            f"Item should not be due now (review date: {future_review_date})"
        
        # Simulate time progression by manually updating next_review_date to past
        past_review_date = datetime.now() - timedelta(hours=1)
        self._update_review_date(temp_database, user_id, item_id, item_type, past_review_date)
        
        # Check that item is now due
        updated_due_reviews = temp_database.get_due_reviews(user_id, item_type)
        updated_item_found = any(
            review['item_id'] == item_id and review['item_type'] == item_type
            for review in updated_due_reviews
        )
        assert updated_item_found, \
            f"Item should be due after time progression (review date: {past_review_date})"
    
    @given(learning_item_strategy(), st.integers(min_value=1, max_value=50))
    @settings(max_examples=HYPOTHESIS_MAX_EXAMPLES_NORMAL, deadline=None,
               suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_due_review_calculation_ordering_and_limits(self, temp_database, item_data, limit):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any user with multiple due reviews, due review list should be 
        ordered correctly (by review date and memory strength) and respect 
        specified limit.
        """
        user_id = item_data['user_id']
        base_item_id = item_data['item_id']
        item_type = item_data['item_type']
        
        # Create multiple items with different review dates and memory strengths
        num_items = min(limit + 5, 20)  # Create more items than limit
        items_created = []
        
        for i in range(num_items):
            item_id = base_item_id + i
            
            # Create items with review dates in the past (all should be due)
            review_date = datetime.now() - timedelta(hours=i + 1)
            
            # Set up learning record
            self.setup_learning_record_with_review_date(temp_database, user_id, item_id, item_type, review_date)
            
            # Set different memory strengths for ordering test
            memory_strength = 0.1 + (i * 0.1) % 1.0  # Vary memory strength
            self._update_memory_strength(temp_database, user_id, item_id, item_type, memory_strength)
            
            items_created.append({
                'item_id': item_id,
                'review_date': review_date,
                'memory_strength': memory_strength
            })
        
        # Get due reviews with limit
        due_reviews = temp_database.get_due_reviews(user_id, item_type, limit)
        
        # Verify limit is respected
        assert len(due_reviews) <= limit, \
            f"Due reviews count {len(due_reviews)} should not exceed limit {limit}"
        
        # Verify ordering (should be ordered by next_review_date ASC, then memory_strength ASC)
        for i in range(len(due_reviews) - 1):
            current_review = due_reviews[i]
            next_review = due_reviews[i + 1]
            
            current_date = datetime.fromisoformat(current_review['next_review_date'])
            next_date = datetime.fromisoformat(next_review['next_review_date'])
            
            # Primary ordering: by review date (ascending - oldest first)
            if current_date != next_date:
                assert current_date <= next_date, \
                    f"Reviews should be ordered by date: {current_date} should be <= {next_date}"
            else:
                # Secondary ordering: by memory strength (ascending - weakest first)
                assert current_review['memory_strength'] <= next_review['memory_strength'], \
                    f"Reviews with same date should be ordered by memory strength: " \
                    f"{current_review['memory_strength']} should be <= {next_review['memory_strength']}"
        
        # Verify all returned items are actually due
        current_time = datetime.now()
        for review in due_reviews:
            review_date = datetime.fromisoformat(review['next_review_date'])
            assert self._should_be_due(review_date, current_time), \
                f"All returned items should be due: {review_date} should be <= {current_time}"
    
    @given(st.lists(learning_item_strategy(), min_size=1, max_size=10, 
                     unique_by=lambda x: (x['user_id'], x['item_id'], x['item_type'])))
    @settings(max_examples=HYPOTHESIS_MAX_EXAMPLES_NORMAL, deadline=None,
               suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_due_review_calculation_item_type_filtering(self, temp_database, learning_items):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any user with multiple item types, due review list should 
        correctly filter by item type when specified.
        """
        # Clear any existing data from previous Hypothesis examples
        with temp_database._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM learning_records")
            conn.commit()
        
        # Set up all items as due for review
        current_time = datetime.now()
        past_review_date = current_time - timedelta(hours=1)
        
        items_by_type: Dict[tuple, List[Dict[str, Any]]] = {}
        
        for item in learning_items:
            user_id = item['user_id']
            item_id = item['item_id']
            item_type = item['item_type']
            
            # Set up learning record with past review date (should be due)
            self.setup_learning_record_with_review_date(temp_database, user_id, item_id, item_type, past_review_date)
            
            # Group by user and item type
            key = (user_id, item_type)
            if key not in items_by_type:
                items_by_type[key] = []
            items_by_type[key].append(item)
        
        # Test filtering by item type for each user
        users_tested = set()
        for (user_id, item_type), items in items_by_type.items():
            if user_id in users_tested:
                continue  # Test each user only once to avoid redundancy
            users_tested.add(user_id)
            
            # Get all due reviews for this user (no type filter)
            all_due_reviews = temp_database.get_due_reviews(user_id)
            
            # Get due reviews filtered by each item type
            for test_item_type in ["vocabulary", "grammar", "content"]:
                filtered_due_reviews = temp_database.get_due_reviews(user_id, test_item_type)
                
                # Count expected items of this type for this user
                expected_count = sum(1 for item in learning_items 
                                           if item['user_id'] == user_id and item['item_type'] == test_item_type)
                
                # Verify filtering works correctly
                assert len(filtered_due_reviews) == expected_count, \
                    f"User {user_id}, type {test_item_type}: expected {expected_count} items, got {len(filtered_due_reviews)}"
                
                # Verify all returned items are of correct type
                for review in filtered_due_reviews:
                    assert review['item_type'] == test_item_type, \
                        f"Filtered results should only contain {test_item_type} items, found {review['item_type']}"
                    assert review['user_id'] == user_id, \
                        f"Filtered results should only contain items for user {user_id}, found {review['user_id']}"
            
            # Verify that sum of filtered results equals total results
            vocab_count = len(temp_database.get_due_reviews(user_id, "vocabulary"))
            grammar_count = len(temp_database.get_due_reviews(user_id, "grammar"))
            content_count = len(temp_database.get_due_reviews(user_id, "content"))
            total_filtered = vocab_count + grammar_count + content_count
            
            assert total_filtered == len(all_due_reviews), \
                f"Sum of filtered results ({total_filtered}) should equal total results ({len(all_due_reviews)})"
    
    @pytest.mark.parametrize("time_offset_seconds,should_be_due", [
        (-10, True),      # 10 seconds ago (definitely due)
        (-1, True),       # 1 second ago (due)
        (0, True),        # exactly now (due with tolerance)
        (5, False),       # 5 seconds in future (not due)
        (10, False),      # 10 seconds in future (definitely not due)
    ])
    def test_due_review_calculation_boundary_conditions(self, temp_database, time_offset_seconds, should_be_due):
        """
        Feature: bilingual-tutor, Property 37: Due Review Calculation Accuracy
        
        For any learning item, due review calculation should handle boundary 
        conditions correctly (exactly at review time, just before, just after).
        """
        item_data = learning_item_strategy().example()
        user_id = item_data['user_id']
        item_id = item_data['item_id']
        item_type = item_data['item_type']
        
        # Set up learning record with specific time offset
        exact_review_time = datetime.now() + timedelta(seconds=time_offset_seconds)
        self.setup_learning_record_with_review_date(temp_database, user_id, item_id, item_type, exact_review_time)
        
        # Check if item should be due
        due_reviews = temp_database.get_due_reviews(user_id, item_type)
        item_found = any(review['item_id'] == item_id for review in due_reviews)
        
        if should_be_due:
            assert item_found, self._format_assertion_message(
                "Item should be due",
                {
                    'Time Offset (seconds)': time_offset_seconds,
                    'Review Time': exact_review_time,
                    'Current Time': datetime.now(),
                    'Item ID': item_id,
                    'Item Type': item_type,
                    'Tolerance (seconds)': TIME_TOLERANCE_SECONDS
                }
            )
        else:
            assert not item_found, self._format_assertion_message(
                "Item should NOT be due",
                {
                    'Time Offset (seconds)': time_offset_seconds,
                    'Review Time': exact_review_time,
                    'Current Time': datetime.now(),
                    'Item ID': item_id,
                    'Item Type': item_type,
                    'Tolerance (seconds)': TIME_TOLERANCE_SECONDS
                }
            )
