"""
智能内容生成器测试
测试基于薄弱环节的练习生成、多种练习形式和质量评估机制
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from bilingual_tutor.services.intelligent_content_generator import (
    IntelligentContentGenerator,
    Exercise,
    ExerciseBatch,
    QualityMetrics,
    ContentQuality,
    get_intelligent_content_generator
)
from bilingual_tutor.services.ai_service import (
    AIModelType,
    AIRequest,
    AIResponse,
    LanguageLevel,
    ExerciseType
)


class TestExercise:
    """测试练习题目"""
    
    def test_exercise_creation(self):
        """测试练习创建"""
        exercise = Exercise(
            id="Q1",
            type=ExerciseType.MULTIPLE_CHOICE,
            question="Test question",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="Explanation",
            difficulty=0.5,
            weakness_areas=["语法"]
        )
        
        assert exercise.id == "Q1"
        assert exercise.type == ExerciseType.MULTIPLE_CHOICE
        assert exercise.difficulty == 0.5
        assert "语法" in exercise.weakness_areas
    
    def test_exercise_to_dict(self):
        """测试练习转换为字典"""
        exercise = Exercise(
            id="Q1",
            type=ExerciseType.MULTIPLE_CHOICE,
            question="Test question",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="Explanation"
        )
        
        result = exercise.to_dict()
        
        assert result['id'] == "Q1"
        assert result['type'] == "multiple_choice"
        assert result['question'] == "Test question"
        assert result['options'] == ["A", "B", "C", "D"]


class TestExerciseBatch:
    """测试练习批次"""
    
    def test_exercise_batch_creation(self):
        """测试练习批次创建"""
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Question 1",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation 1"
            ),
            Exercise(
                id="Q2",
                type=ExerciseType.FILL_BLANK,
                question="Question 2",
                correct_answer="answer",
                explanation="Explanation 2"
            )
        ]
        
        batch = ExerciseBatch(
            exercises=exercises,
            target_level=LanguageLevel.CET4,
            target_areas=["语法"],
            quality_score=0.85,
            generation_duration_ms=1000.0
        )
        
        assert len(batch.exercises) == 2
        assert batch.target_level == LanguageLevel.CET4
        assert batch.quality_score == 0.85
        assert batch.exercise_count == 2
    
    def test_exercise_batch_to_dict(self):
        """测试练习批次转换为字典"""
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Question",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation"
            )
        ]
        
        batch = ExerciseBatch(
            exercises=exercises,
            target_level=LanguageLevel.CET4,
            target_areas=["语法"],
            quality_score=0.85,
            generation_duration_ms=1000.0
        )
        
        result = batch.to_dict()
        
        assert 'exercises' in result
        assert 'target_level' in result
        assert result['exercise_count'] == 1


class TestQualityMetrics:
    """测试质量指标"""
    
    def test_quality_metrics_initialization(self):
        """测试质量指标初始化"""
        metrics = QualityMetrics()
        
        assert metrics.clarity_score == 0.0
        assert metrics.relevance_score == 0.0
        assert metrics.difficulty_match_score == 0.0
        assert metrics.variety_score == 0.0
        assert metrics.completeness_score == 0.0
        assert metrics.overall_score == 0.0
    
    def test_calculate_overall_score(self):
        """测试计算总体得分"""
        metrics = QualityMetrics(
            clarity_score=0.8,
            relevance_score=0.9,
            difficulty_match_score=0.7,
            variety_score=0.6,
            completeness_score=0.85
        )
        
        overall = metrics.calculate_overall()
        
        # 加权平均：0.8*0.25 + 0.9*0.20 + 0.7*0.20 + 0.6*0.15 + 0.85*0.20
        expected = 0.8*0.25 + 0.9*0.20 + 0.7*0.20 + 0.6*0.15 + 0.85*0.20
        assert abs(overall - expected) < 0.001
    
    def test_quality_metrics_to_dict(self):
        """测试质量指标转换为字典"""
        metrics = QualityMetrics(
            clarity_score=0.8,
            relevance_score=0.9,
            overall_score=0.85
        )
        
        result = metrics.to_dict()
        
        assert result['clarity_score'] == 0.8
        assert result['relevance_score'] == 0.9
        assert result['overall_score'] == 0.85


class TestIntelligentContentGenerator:
    """测试智能内容生成器"""
    
    @pytest.mark.asyncio
    async def test_generate_targeted_exercises(self):
        """测试生成针对性练习题"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Test explanation",
            "difficulty": 0.5
        },
        {
            "id": "Q2",
            "question": "Test question 2",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Test explanation 2",
            "difficulty": 0.5
        },
        {
            "id": "Q3",
            "question": "Test question 3",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "C",
            "explanation": "Test explanation 3",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            exercise_types=[ExerciseType.MULTIPLE_CHOICE],
            count=3
        )
        
        assert isinstance(batch, ExerciseBatch)
        assert len(batch.exercises) == 3
        assert batch.target_level == LanguageLevel.CET4
        assert "语法" in batch.target_areas
        assert batch.quality_score >= 0.0
        assert batch.generation_duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_generate_multiple_exercise_types(self):
        """测试生成多种类型的练习题"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Test explanation",
            "difficulty": 0.5
        },
        {
            "id": "Q2",
            "question": "Test question 2",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Test explanation 2",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法", "词汇"],
            language_level=LanguageLevel.CET4,
            count=8
        )
        
        # 应该生成练习，数量等于或小于请求的数量
        assert len(batch.exercises) <= 8
        # 应该包含多种类型的练习
        exercise_types = set(ex.type for ex in batch.exercises)
        assert len(exercise_types) > 1
    
    @pytest.mark.asyncio
    async def test_quality_evaluation_clarity(self):
        """测试评估清晰度"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "这是一个长度适中的问题，用于测试清晰度评估功能。",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "这是一个长度适中的解释，用于测试清晰度评估功能。",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 清晰度得分应该较高
        assert batch.quality_score > 0.5
    
    @pytest.mark.asyncio
    async def test_quality_evaluation_relevance(self):
        """测试评估相关性"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Test explanation",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法", "词汇"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 练习应该与目标领域相关
        assert len(batch.target_areas) > 0
    
    @pytest.mark.asyncio
    async def test_quality_evaluation_difficulty_match(self):
        """测试评估难度匹配度"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Test explanation",
            "difficulty": 0.4
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # CET-4的难度范围是0.2-0.5，0.4在范围内
        assert 0.2 <= batch.exercises[0].difficulty <= 0.5
    
    @pytest.mark.asyncio
    async def test_quality_evaluation_completeness(self):
        """测试评估完整性"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Complete test question with proper length",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "explanation": "Complete explanation with proper length",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 完整性得分应该较高
        assert batch.quality_score > 0.5
    
    def test_adjust_difficulty_based_on_feedback_high_accuracy(self):
        """测试根据高准确率反馈调整难度"""
        generator = IntelligentContentGenerator()
        
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Question",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation",
                difficulty=0.5
            )
        ]
        
        feedback = {'accuracy': 0.9}
        adjusted = generator._adjust_difficulty_based_on_feedback(exercises, feedback)
        
        # 高准确率应该提高难度
        assert adjusted[0].difficulty > 0.5
    
    def test_adjust_difficulty_based_on_feedback_low_accuracy(self):
        """测试根据低准确率反馈调整难度"""
        generator = IntelligentContentGenerator()
        
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Question",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation",
                difficulty=0.5
            )
        ]
        
        feedback = {'accuracy': 0.3}
        adjusted = generator._adjust_difficulty_based_on_feedback(exercises, feedback)
        
        # 低准确率应该降低难度
        assert adjusted[0].difficulty < 0.5
    
    def test_optimize_exercises(self):
        """测试优化练习题"""
        generator = IntelligentContentGenerator()
        
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Good question with proper length",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Good explanation with proper length",
                difficulty=0.5
            ),
            Exercise(
                id="Q2",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Short",  # 太短
                options=["A"],
                correct_answer="A",
                explanation="Short",  # 太短
                difficulty=0.5
            )
        ]
        
        optimized = generator.optimize_exercises(exercises)
        
        # 应该保留所有练习，但标记质量低的
        assert len(optimized) == 2
        assert optimized[1].metadata.get('quality') == 'low'
    
    def test_get_generation_statistics_empty(self):
        """测试获取生成统计信息（空历史）"""
        generator = IntelligentContentGenerator()
        
        stats = generator.get_generation_statistics()
        
        assert stats['total_generations'] == 0
        assert stats['average_quality_score'] == 0.0
        assert stats['average_duration_ms'] == 0.0
    
    @pytest.mark.asyncio
    async def test_get_generation_statistics_with_history(self):
        """测试获取生成统计信息（有历史记录）"""
        ai_service = Mock()
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercises": [
        {
            "id": "Q1",
            "question": "Test",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Test",
            "difficulty": 0.5
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = IntelligentContentGenerator(ai_service)
        
        # 生成两次练习
        await generator.generate_targeted_exercises(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        await generator.generate_targeted_exercises(
            weakness_areas=["词汇"],
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        stats = generator.get_generation_statistics()
        
        assert stats['total_generations'] == 2
        assert stats['average_quality_score'] > 0.0
        assert stats['average_duration_ms'] > 0.0
        assert len(stats['recent_history']) == 2


class TestContentGeneratorSingleton:
    """测试内容生成器单例"""
    
    def test_get_intelligent_content_generator_singleton(self):
        """测试获取智能内容生成器单例"""
        generator1 = get_intelligent_content_generator()
        generator2 = get_intelligent_content_generator()
        
        assert generator1 is generator2
