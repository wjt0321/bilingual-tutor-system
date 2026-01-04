"""
Review Scheduler - Implements Ebbinghaus forgetting curve for spaced repetition.
"""

import math
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from ..models import Content, ActivityResult


class ReviewScheduler:
    """
    Implements spaced repetition scheduling based on the Ebbinghaus forgetting curve
    to optimize long-term retention of learned content.
    """
    
    def __init__(self):
        """Initialize the review scheduler with forgetting curve parameters."""
        # Ebbinghaus forgetting curve parameters
        self.initial_strength = 1.0  # Initial memory strength
        self.decay_constant = 0.5    # Rate of forgetting
        self.review_threshold = 0.3  # Threshold below which review is needed
        
        # Spaced repetition intervals (in days)
        self.base_intervals = [1, 3, 7, 14, 30, 90, 180, 365]
        
        # Content review tracking
        self.content_reviews: Dict[str, List[Tuple[datetime, float]]] = {}
        self.next_review_dates: Dict[str, datetime] = {}
        self.performance_history: Dict[str, List[float]] = {}
    
    def schedule_review(self, content: Content, performance: float) -> datetime:
        """
        Schedule the next review for content based on performance.
        
        Args:
            content: Content item to schedule review for
            performance: Performance score (0.0 to 1.0) from last review
            
        Returns:
            Next review date
        """
        content_id = content.content_id
        current_time = datetime.now()
        
        # Initialize tracking if first time
        if content_id not in self.content_reviews:
            self.content_reviews[content_id] = []
            self.performance_history[content_id] = []
        
        # Record this review
        self.content_reviews[content_id].append((current_time, performance))
        self.performance_history[content_id].append(performance)
        
        # Calculate next review interval
        interval_days = self._calculate_next_interval(content_id, performance)
        next_review = current_time + timedelta(days=interval_days)
        
        # Store next review date
        self.next_review_dates[content_id] = next_review
        
        return next_review
    
    def calculate_forgetting_curve(self, initial_strength: float, time_elapsed: timedelta) -> float:
        """
        Calculate memory retention using Ebbinghaus forgetting curve.
        
        Formula: R(t) = e^(-t/S)
        Where R(t) is retention at time t, and S is memory strength
        
        Args:
            initial_strength: Initial memory strength
            time_elapsed: Time elapsed since learning
            
        Returns:
            Current retention level (0.0 to 1.0)
        """
        if time_elapsed.total_seconds() <= 0:
            return initial_strength
        
        # Convert time to hours for calculation
        hours_elapsed = time_elapsed.total_seconds() / 3600
        
        # Apply forgetting curve formula
        retention = initial_strength * math.exp(-hours_elapsed / (24 * self.decay_constant))
        
        return max(0.0, min(retention, 1.0))
    
    def adjust_interval(self, content: Content, performance: float) -> timedelta:
        """
        Adjust review interval based on performance.
        
        Args:
            content: Content item
            performance: Performance score (0.0 to 1.0)
            
        Returns:
            Adjusted interval as timedelta
        """
        content_id = content.content_id
        
        # Get current interval level
        review_count = len(self.content_reviews.get(content_id, []))
        base_interval_index = min(review_count, len(self.base_intervals) - 1)
        base_interval = self.base_intervals[base_interval_index]
        
        # Adjust based on performance
        if performance >= 0.9:
            # Excellent performance - increase interval significantly
            multiplier = 1.5
        elif performance >= 0.7:
            # Good performance - slight increase
            multiplier = 1.2
        elif performance >= 0.5:
            # Average performance - keep same interval
            multiplier = 1.0
        elif performance >= 0.3:
            # Poor performance - decrease interval
            multiplier = 0.7
        else:
            # Very poor performance - reset to beginning
            multiplier = 0.3
            base_interval = self.base_intervals[0]
        
        # Consider performance history for stability
        if content_id in self.performance_history:
            avg_performance = sum(self.performance_history[content_id]) / len(self.performance_history[content_id])
            
            # If consistently good, allow longer intervals
            if avg_performance >= 0.8 and len(self.performance_history[content_id]) >= 3:
                multiplier *= 1.3
            # If consistently poor, keep shorter intervals
            elif avg_performance <= 0.5:
                multiplier *= 0.8
        
        adjusted_days = int(base_interval * multiplier)
        return timedelta(days=max(1, adjusted_days))  # Minimum 1 day
    
    def prioritize_reviews(self, due_reviews: List[Tuple[str, Content]]) -> List[Tuple[str, Content]]:
        """
        Prioritize reviews based on urgency and importance.
        
        Args:
            due_reviews: List of (content_id, content) tuples due for review
            
        Returns:
            Prioritized list of reviews
        """
        current_time = datetime.now()
        prioritized = []
        
        for content_id, content in due_reviews:
            # Calculate priority score
            priority_score = self._calculate_priority_score(content_id, content, current_time)
            prioritized.append((priority_score, content_id, content))
        
        # Sort by priority score (highest first)
        prioritized.sort(key=lambda x: x[0], reverse=True)
        
        return [(content_id, content) for _, content_id, content in prioritized]
    
    def get_due_reviews(self, current_time: datetime = None) -> List[str]:
        """
        Get list of content IDs that are due for review.
        
        Args:
            current_time: Current time (defaults to now)
            
        Returns:
            List of content IDs due for review
        """
        if current_time is None:
            current_time = datetime.now()
        
        due_reviews = []
        
        for content_id, next_review in self.next_review_dates.items():
            if next_review <= current_time:
                due_reviews.append(content_id)
        
        return due_reviews
    
    def estimate_review_load(self, timeframe: timedelta) -> Dict[str, int]:
        """
        Estimate review load for a given timeframe.
        
        Args:
            timeframe: Time period to estimate for
            
        Returns:
            Dictionary with review load statistics
        """
        current_time = datetime.now()
        end_time = current_time + timeframe
        
        # Count reviews by day
        daily_counts = {}
        total_reviews = 0
        
        for content_id, next_review in self.next_review_dates.items():
            if current_time <= next_review <= end_time:
                review_date = next_review.date()
                daily_counts[review_date] = daily_counts.get(review_date, 0) + 1
                total_reviews += 1
        
        # Calculate statistics
        days_with_reviews = len(daily_counts)
        avg_daily_reviews = total_reviews / max(1, timeframe.days)
        max_daily_reviews = max(daily_counts.values()) if daily_counts else 0
        
        return {
            'total_reviews': total_reviews,
            'days_with_reviews': days_with_reviews,
            'avg_daily_reviews': avg_daily_reviews,
            'max_daily_reviews': max_daily_reviews,
            'daily_breakdown': daily_counts
        }
    
    def optimize_review_schedule(self, available_time_per_day: int) -> Dict[str, any]:
        """
        Optimize review schedule based on available time.
        
        Args:
            available_time_per_day: Available minutes per day for reviews
            
        Returns:
            Optimized schedule recommendations
        """
        # Estimate time per review (average)
        avg_review_time = 3  # minutes per review item
        max_reviews_per_day = available_time_per_day // avg_review_time
        
        # Get upcoming reviews
        week_ahead = timedelta(days=7)
        review_load = self.estimate_review_load(week_ahead)
        
        recommendations = {
            'max_reviews_per_day': max_reviews_per_day,
            'current_load': review_load,
            'overload_days': [],
            'suggestions': []
        }
        
        # Identify overload days
        for date, count in review_load['daily_breakdown'].items():
            if count > max_reviews_per_day:
                recommendations['overload_days'].append({
                    'date': date,
                    'reviews': count,
                    'excess': count - max_reviews_per_day
                })
        
        # Generate suggestions
        if recommendations['overload_days']:
            recommendations['suggestions'].append(
                "考虑将部分复习内容提前或延后，以平衡每日复习量"
            )
        
        if review_load['avg_daily_reviews'] > max_reviews_per_day:
            recommendations['suggestions'].append(
                "当前复习量超出可用时间，建议增加每日复习时间或调整学习计划"
            )
        
        return recommendations
    
    def _calculate_next_interval(self, content_id: str, performance: float) -> int:
        """Calculate the next review interval in days."""
        review_count = len(self.content_reviews.get(content_id, []))
        
        # Base interval from spaced repetition sequence
        base_index = min(review_count, len(self.base_intervals) - 1)
        base_interval = self.base_intervals[base_index]
        
        # Performance-based adjustment
        if performance >= 0.9:
            multiplier = 1.5
        elif performance >= 0.7:
            multiplier = 1.2
        elif performance >= 0.5:
            multiplier = 1.0
        elif performance >= 0.3:
            multiplier = 0.7
        else:
            multiplier = 0.5
            base_interval = self.base_intervals[0]  # Reset to beginning
        
        return max(1, int(base_interval * multiplier))
    
    def _calculate_priority_score(self, content_id: str, content: Content, current_time: datetime) -> float:
        """Calculate priority score for review scheduling."""
        score = 0.0
        
        # Urgency factor (how overdue)
        if content_id in self.next_review_dates:
            next_review = self.next_review_dates[content_id]
            days_overdue = (current_time - next_review).days
            if days_overdue > 0:
                score += days_overdue * 10  # High priority for overdue items
        
        # Performance history factor
        if content_id in self.performance_history:
            avg_performance = sum(self.performance_history[content_id]) / len(self.performance_history[content_id])
            # Lower performance = higher priority
            score += (1.0 - avg_performance) * 5
        
        # Content difficulty factor
        difficulty_weights = {
            'CET-4': 1.0, 'CET-5': 1.2, 'CET-6': 1.5,
            'N5': 1.0, 'N4': 1.2, 'N3': 1.5, 'N2': 1.8, 'N1': 2.0
        }
        difficulty_weight = difficulty_weights.get(content.difficulty_level, 1.0)
        score += difficulty_weight
        
        # Content quality factor
        score += content.quality_score * 2
        
        return score
    
    def get_review_statistics(self) -> Dict[str, any]:
        """Get comprehensive review statistics."""
        total_content = len(self.content_reviews)
        total_reviews = sum(len(reviews) for reviews in self.content_reviews.values())
        
        if total_content == 0:
            return {
                'total_content': 0,
                'total_reviews': 0,
                'avg_reviews_per_content': 0,
                'avg_performance': 0,
                'retention_rate': 0
            }
        
        # Calculate average performance
        all_performances = []
        for performances in self.performance_history.values():
            all_performances.extend(performances)
        
        avg_performance = sum(all_performances) / len(all_performances) if all_performances else 0
        
        # Calculate retention rate (content with performance > 0.7)
        good_performance_count = sum(
            1 for performances in self.performance_history.values()
            if performances and performances[-1] >= 0.7
        )
        retention_rate = good_performance_count / total_content if total_content > 0 else 0
        
        return {
            'total_content': total_content,
            'total_reviews': total_reviews,
            'avg_reviews_per_content': total_reviews / total_content,
            'avg_performance': avg_performance,
            'retention_rate': retention_rate,
            'due_today': len(self.get_due_reviews()),
            'scheduled_this_week': len(self.get_due_reviews(datetime.now() + timedelta(days=7)))
        }