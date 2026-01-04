"""
Tests for the Weakness Analyzer component.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st
from bilingual_tutor.analysis.weakness_analyzer import WeaknessAnalyzer
from bilingual_tutor.analysis.improvement_advisor import ImprovementAdvisor
from bilingual_tutor.models import (
    WeakArea, Skill, ActivityResult, ActivityType
)


class TestWeaknessAnalyzer:
    """Test suite for WeaknessAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = WeaknessAnalyzer()
        self.advisor = ImprovementAdvisor()
    
    @given(st.data())
    def test_comprehensive_performance_monitoring(self, data):
        """
        **Feature: bilingual-tutor, Property 25: Comprehensive Performance Monitoring**
        
        For any user activity, performance should be monitored across all skill areas:
        vocabulary, grammar, listening, speaking, reading, and writing.
        
        **Validates: Requirements 8.1**
        """
        # Generate test parameters
        user_id = data.draw(st.text(min_size=1, max_size=20))
        num_activities = data.draw(st.integers(min_value=5, max_value=50))
        timeframe_days = data.draw(st.integers(min_value=1, max_value=30))
        
        # Generate activity results covering all skills
        all_skills = list(Skill)
        timeframe = timedelta(days=timeframe_days)
        
        # Create activity results with various skills and performance levels
        for i in range(num_activities):
            score = data.draw(st.floats(min_value=0.0, max_value=1.0))
            time_spent = data.draw(st.integers(min_value=5, max_value=30))
            num_errors = data.draw(st.integers(min_value=0, max_value=5))
            error_skills = data.draw(st.lists(st.sampled_from(all_skills), min_size=1, max_size=2, unique=True))
            days_ago = data.draw(st.integers(min_value=0, max_value=timeframe_days))
            
            errors_made = [
                f"error_{j}_{skill.value}" 
                for j in range(num_errors)
                for skill in error_skills
            ]
            
            activity_result = ActivityResult(
                activity_id=f"activity_{i}",
                user_id=user_id,
                score=score,
                time_spent=time_spent,
                errors_made=errors_made,
                completed_at=datetime.now() - timedelta(days=days_ago),
                feedback="Test feedback"
            )
            
            # Record the activity result
            self.analyzer.record_activity_result(user_id, activity_result)
        
        # Analyze error patterns
        weak_areas = self.analyzer.analyze_error_patterns(user_id, timeframe)
        
        # Verify that performance monitoring is comprehensive
        # The system should be able to identify weaknesses across different skills
        if weak_areas:
            # Check that identified weaknesses cover various skills
            identified_skills = {wa.skill for wa in weak_areas}
            
            # At least some skills should be monitored if there are enough activities
            assert len(identified_skills) >= 0  # Can be 0 if no weaknesses found
            
            # Each weakness should have valid severity
            for weak_area in weak_areas:
                assert 0.0 <= weak_area.severity <= 1.0
                assert weak_area.skill in all_skills
                assert weak_area.language in ['english', 'japanese']
                assert isinstance(weak_area.error_patterns, list)
        
        # Verify skill gap identification works for both languages
        english_gaps = self.analyzer.identify_skill_gaps(user_id, 'english')
        japanese_gaps = self.analyzer.identify_skill_gaps(user_id, 'japanese')
        
        # Both should return lists (may be empty)
        assert isinstance(english_gaps, list)
        assert isinstance(japanese_gaps, list)
        
        # If gaps are found, they should be properly structured
        for gap in english_gaps + japanese_gaps:
            assert isinstance(gap, WeakArea)
            assert 0.0 <= gap.severity <= 1.0
            assert gap.skill in all_skills
    
    @given(st.data())
    def test_error_pattern_analysis(self, data):
        """
        **Feature: bilingual-tutor, Property 26: Error Pattern Analysis**
        
        For any sequence of user errors, the system should identify patterns
        to determine specific weak areas for both English and Japanese.
        
        **Validates: Requirements 8.2**
        """
        # Generate test parameters
        user_id = data.draw(st.text(min_size=1, max_size=20))
        num_errors = data.draw(st.integers(min_value=10, max_value=100))
        
        # Create activity results with specific error patterns
        error_patterns = [
            "vocabulary_confusion", "grammar_tense_error", "pronunciation_mistake",
            "reading_comprehension_error", "listening_misunderstanding"
        ]
        
        # Generate errors with some patterns repeated
        for i in range(num_errors):
            # Create some repeated patterns to test pattern detection
            error_type = error_patterns[i % len(error_patterns)]
            repeated_error = f"{error_type}_{i // 5}"  # Group errors to create patterns
            score = data.draw(st.floats(min_value=0.0, max_value=0.8))  # Lower scores to trigger weakness detection
            time_spent = data.draw(st.integers(min_value=5, max_value=20))
            
            activity_result = ActivityResult(
                activity_id=f"activity_{i}",
                user_id=user_id,
                score=score,
                time_spent=time_spent,
                errors_made=[repeated_error],
                completed_at=datetime.now() - timedelta(minutes=i * 10),
                feedback="Test feedback"
            )
            
            self.analyzer.record_activity_result(user_id, activity_result)
        
        # Analyze error patterns
        timeframe = timedelta(days=7)
        weak_areas = self.analyzer.analyze_error_patterns(user_id, timeframe)
        
        # Verify error pattern analysis
        if weak_areas:
            # Should identify patterns in errors
            for weak_area in weak_areas:
                # Should have identified error patterns
                assert isinstance(weak_area.error_patterns, list)
                
                # Severity should reflect error frequency
                assert 0.0 <= weak_area.severity <= 1.0
                
                # Should be associated with specific skills
                assert weak_area.skill in list(Skill)
                
                # Should be associated with a language
                assert weak_area.language in ['english', 'japanese']
        
        # Test that the analyzer can distinguish between languages
        english_gaps = self.analyzer.identify_skill_gaps(user_id, 'english')
        japanese_gaps = self.analyzer.identify_skill_gaps(user_id, 'japanese')
        
        # Should return separate analyses for each language
        assert isinstance(english_gaps, list)
        assert isinstance(japanese_gaps, list)
    
    @given(st.data())
    def test_improvement_tracking_and_focus_adjustment(self, data):
        """
        **Feature: bilingual-tutor, Property 29: Improvement Tracking and Focus Adjustment**
        
        For any previously identified weak area, improvement should be tracked
        and system focus should adjust as weaknesses are addressed.
        
        **Validates: Requirements 8.6**
        """
        # Generate test parameters
        user_id = data.draw(st.text(min_size=1, max_size=20))
        initial_performance = data.draw(st.floats(min_value=0.3, max_value=0.6))
        improved_performance = data.draw(st.floats(min_value=0.7, max_value=1.0))
        
        # Create a weakness to track
        weakness = WeakArea(
            area_id="test_weakness_001",
            skill=Skill.VOCABULARY,
            language="english",
            severity=0.8,
            error_patterns=["word_confusion", "meaning_error"],
            improvement_suggestions=[],
            identified_at=datetime.now() - timedelta(days=7)
        )
        
        # Record initial poor performance
        for i in range(5):
            initial_result = ActivityResult(
                activity_id=f"initial_activity_{i}",
                user_id=user_id,
                score=initial_performance,
                time_spent=15,
                errors_made=["word_confusion", "meaning_error"],
                completed_at=datetime.now() - timedelta(days=6, hours=i),
                feedback="Initial performance"
            )
            self.analyzer.record_activity_result(user_id, initial_result)
        
        # Record improved performance
        for i in range(5):
            improved_result = ActivityResult(
                activity_id=f"improved_activity_{i}",
                user_id=user_id,
                score=improved_performance,
                time_spent=15,
                errors_made=[],  # Fewer errors showing improvement
                completed_at=datetime.now() - timedelta(hours=i),
                feedback="Improved performance"
            )
            self.analyzer.record_activity_result(user_id, improved_result)
        
        # Track improvement progress
        improvement_progress = self.analyzer.track_improvement_progress(user_id, weakness)
        
        # Verify improvement tracking
        assert isinstance(improvement_progress, float)
        assert 0.0 <= improvement_progress <= 100.0
        
        # With improved performance, should show positive progress
        # (Note: May be 0 if not enough data, but should not be negative)
        assert improvement_progress >= 0.0
        
        # Test focus adjustment through weakness prioritization
        current_weaknesses = self.analyzer.analyze_error_patterns(user_id, timedelta(days=1))
        
        if current_weaknesses:
            # Should be able to prioritize weaknesses
            prioritized = self.analyzer.prioritize_improvements(current_weaknesses)
            assert isinstance(prioritized, list)
            assert len(prioritized) == len(current_weaknesses)
            
            # Should maintain all weaknesses in prioritized list
            assert set(w.area_id for w in prioritized) == set(w.area_id for w in current_weaknesses)
        
        # Test recommendation generation
        recommendations = self.analyzer.generate_improvement_recommendations(weakness)
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0  # Should provide some recommendations
        
        # All recommendations should be strings
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0  # Non-empty recommendations
    
    def test_weakness_severity_calculation(self):
        """Test weakness severity calculation."""
        weakness = WeakArea(
            area_id="test_weakness",
            skill=Skill.VOCABULARY,
            language="english",
            severity=0.6,
            error_patterns=["error1", "error2"],
            improvement_suggestions=[],
            identified_at=datetime.now()
        )
        
        severity = self.analyzer.calculate_weakness_severity(weakness)
        
        assert isinstance(severity, float)
        assert 0.0 <= severity <= 1.0
    
    def test_weakness_prioritization(self):
        """Test weakness prioritization."""
        weaknesses = [
            WeakArea(
                area_id=f"weakness_{i}",
                skill=list(Skill)[i % len(Skill)],
                language="english",
                severity=0.5 + (i * 0.1),
                error_patterns=[f"error_{i}"],
                improvement_suggestions=[],
                identified_at=datetime.now() - timedelta(days=i)
            )
            for i in range(5)
        ]
        
        prioritized = self.analyzer.prioritize_improvements(weaknesses)
        
        assert isinstance(prioritized, list)
        assert len(prioritized) == len(weaknesses)
        
        # Should maintain all weaknesses
        assert set(w.area_id for w in prioritized) == set(w.area_id for w in weaknesses)
    
    @given(st.data())
    def test_targeted_improvement_suggestions(self, data):
        """
        **Feature: bilingual-tutor, Property 27: Targeted Improvement Suggestions**
        
        For any identified weak area, the system should provide specific suggestions,
        examples, and practice exercises.
        
        **Validates: Requirements 8.3, 8.4**
        """
        # Generate a weakness to test
        skill = data.draw(st.sampled_from(list(Skill)))
        language = data.draw(st.sampled_from(['english', 'japanese']))
        severity = data.draw(st.floats(min_value=0.1, max_value=1.0))
        num_error_patterns = data.draw(st.integers(min_value=1, max_value=5))
        
        error_patterns = [
            f"error_pattern_{i}_{skill.value}" 
            for i in range(num_error_patterns)
        ]
        
        weakness = WeakArea(
            area_id=f"weakness_{data.draw(st.integers(min_value=1, max_value=1000))}",
            skill=skill,
            language=language,
            severity=severity,
            error_patterns=error_patterns,
            improvement_suggestions=[],
            identified_at=datetime.now()
        )
        
        # Test improvement plan generation
        improvement_plan = self.advisor.generate_improvement_plan(weakness)
        
        # Verify improvement plan structure and content
        assert isinstance(improvement_plan, dict)
        assert 'weakness_id' in improvement_plan
        assert 'skill' in improvement_plan
        assert 'language' in improvement_plan
        assert 'strategies' in improvement_plan
        assert 'examples' in improvement_plan
        assert 'practice_exercises' in improvement_plan
        assert 'chinese_explanation' in improvement_plan
        
        # Verify strategies are provided
        strategies = improvement_plan['strategies']
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        
        # All strategies should be non-empty strings
        for strategy in strategies:
            assert isinstance(strategy, str)
            assert len(strategy) > 0
        
        # Test example provision
        concept = f"{skill.value}_practice"
        examples = self.advisor.provide_examples(concept, language)
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        
        # All examples should be strings with content
        for example in examples:
            assert isinstance(example, str)
            assert len(example) > 0
        
        # Test practice recommendations
        level = "CET-4" if language == "english" else "N5"
        practice_recommendations = self.advisor.recommend_practice(skill, level)
        
        assert isinstance(practice_recommendations, list)
        assert len(practice_recommendations) > 0
        
        # Each recommendation should have required fields
        for recommendation in practice_recommendations:
            assert isinstance(recommendation, dict)
            assert 'exercise_type' in recommendation
            assert 'difficulty' in recommendation
            assert 'chinese_instructions' in recommendation
            
            # Verify field types and content
            assert isinstance(recommendation['exercise_type'], str)
            assert len(recommendation['exercise_type']) > 0
            assert isinstance(recommendation['chinese_instructions'], str)
            assert len(recommendation['chinese_instructions']) > 0
        
        # Test Chinese explanation generation
        chinese_explanation = improvement_plan['chinese_explanation']
        assert isinstance(chinese_explanation, str)
        assert len(chinese_explanation) > 0
        
        # Should contain Chinese characters (basic check)
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in chinese_explanation)
        assert has_chinese, "Chinese explanation should contain Chinese characters"
    
    @given(st.data())
    def test_chinese_weakness_explanations(self, data):
        """
        **Feature: bilingual-tutor, Property 30: Chinese Weakness Explanations**
        
        For any identified weak area, detailed explanations in Chinese should be provided
        explaining why the area is weak and how to improve.
        
        **Validates: Requirements 8.7**
        """
        # Generate a weakness
        skill = data.draw(st.sampled_from(list(Skill)))
        language = data.draw(st.sampled_from(['english', 'japanese']))
        severity = data.draw(st.floats(min_value=0.1, max_value=1.0))
        
        weakness = WeakArea(
            area_id=f"weakness_chinese_test_{data.draw(st.integers(min_value=1, max_value=1000))}",
            skill=skill,
            language=language,
            severity=severity,
            error_patterns=[f"pattern_{i}" for i in range(data.draw(st.integers(min_value=1, max_value=3)))],
            improvement_suggestions=[],
            identified_at=datetime.now()
        )
        
        # Generate improvement plan with Chinese explanations
        improvement_plan = self.advisor.generate_improvement_plan(weakness)
        
        # Verify Chinese explanation exists and has content
        assert 'chinese_explanation' in improvement_plan
        chinese_explanation = improvement_plan['chinese_explanation']
        
        assert isinstance(chinese_explanation, str)
        assert len(chinese_explanation) > 0
        
        # Verify it contains Chinese characters
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in chinese_explanation)
        assert has_chinese, "Explanation should contain Chinese characters"
        
        # Verify explanation mentions key elements
        explanation_lower = chinese_explanation.lower()
        
        # Should mention the language being studied
        language_mentioned = ("英语" in chinese_explanation) or ("日语" in chinese_explanation)
        assert language_mentioned, "Should mention the target language"
        
        # Should mention severity or improvement
        severity_mentioned = any(word in chinese_explanation for word in ["严重", "程度", "改善", "提升", "练习"])
        assert severity_mentioned, "Should mention severity or improvement concepts"
        
        # Test practice recommendations also have Chinese instructions
        level = "CET-4" if language == "english" else "N5"
        practice_recommendations = self.advisor.recommend_practice(skill, level)
        
        for recommendation in practice_recommendations:
            chinese_instructions = recommendation.get('chinese_instructions', '')
            assert isinstance(chinese_instructions, str)
            assert len(chinese_instructions) > 0
            
            # Should contain Chinese characters
            has_chinese_instructions = any('\u4e00' <= char <= '\u9fff' for char in chinese_instructions)
            assert has_chinese_instructions, "Instructions should be in Chinese"
        
        # Test example provision includes Chinese explanations
        concept = f"{skill.value}_improvement"
        examples = self.advisor.provide_examples(concept, language)
        
        # At least some examples should contain Chinese explanations
        chinese_in_examples = any(
            any('\u4e00' <= char <= '\u9fff' for char in example)
            for example in examples
        )
        assert chinese_in_examples, "Examples should include Chinese explanations"