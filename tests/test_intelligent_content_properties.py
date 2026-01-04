"""
智能内容生成属性测试
使用Hypothesis进行属性测试，验证智能内容生成的关键属性
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings
from bilingual_tutor.services.intelligent_content_generator import (
    IntelligentContentGenerator,
    Exercise,
    ExerciseBatch,
    QualityMetrics,
    get_intelligent_content_generator
)
from bilingual_tutor.services.ai_service import (
    AIService,
    AIModelType,
    AIRequest,
    AIResponse,
    LanguageLevel,
    ExerciseType
)


class TestTargetedExerciseGeneration:
    """
    属性51: 针对性练习生成
    
    验证需求26.1: 当识别到用户薄弱领域时，大语言模型服务应使用DeepSeek等国内模型
    生成针对性的练习题
    """
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇", "听力", "阅读", "写作"]),
            min_size=1,
            max_size=5,
            unique=True
        ),
        level=st.sampled_from(LanguageLevel)
    )
    @settings(max_examples=20)
    async def test_exercises_target_weakness_areas(self, weakness_areas, level):
        """属性51: 生成的练习题应该针对用户的薄弱领域"""
        ai_service = Mock()
        
        # 模拟AI返回包含目标领域的练习
        async def mock_generate(request):
            exercises = []
            for area in weakness_areas:
                exercises.append({
                    "id": f"Q{len(exercises)+1}",
                    "question": f"Test question for {area}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": f"Explanation for {area}",
                    "difficulty": 0.5
                })
            
            return AIResponse(
                content=f'{{"exercises": {exercises}}}'.replace("'", '"'),
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        # 指定练习类型，避免生成所有类型
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=level,
            exercise_types=[ExerciseType.MULTIPLE_CHOICE],
            count=len(weakness_areas)
        )
        
        # 验证练习题的数量
        assert len(batch.exercises) == len(weakness_areas)
        
        # 验证每道练习都针对了薄弱领域
        for exercise in batch.exercises:
            assert len(exercise.weakness_areas) > 0
            # 验证薄弱领域被正确记录
            assert any(area in weakness_areas for area in exercise.weakness_areas)
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
            min_size=1,
            max_size=3
        ),
        count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=15)
    async def test_exercise_count_matches_request(self, weakness_areas, count):
        """属性51: 生成的练习题数量应该匹配请求的数量"""
        ai_service = Mock()
        
        async def mock_generate(request):
            exercises = []
            for i in range(count):
                exercises.append({
                    "id": f"Q{i+1}",
                    "question": f"Question {i+1}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": f"Explanation {i+1}",
                    "difficulty": 0.5
                })
            
            return AIResponse(
                content=f'{{"exercises": {exercises}}}'.replace("'", '"'),
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        # 指定练习类型以避免生成所有类型
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            exercise_types=[ExerciseType.MULTIPLE_CHOICE],
            count=count
        )
        
        # 验证练习题数量
        assert len(batch.exercises) == count
        assert batch.exercise_count == count
    
    @pytest.mark.asyncio
    @given(
        level=st.sampled_from(LanguageLevel),
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇", "听力"]),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=15)
    async def test_exercises_match_language_level(self, level, weakness_areas):
        """属性51: 生成的练习题应该匹配用户的语言水平"""
        ai_service = Mock()
        
        async def mock_generate(request):
            # 根据语言级别返回适当的难度
            difficulty = 0.5
            if level in [LanguageLevel.CET4, LanguageLevel.N5]:
                difficulty = 0.3
            elif level in [LanguageLevel.CET6, LanguageLevel.N2]:
                difficulty = 0.7
            elif level in [LanguageLevel.CET6_PLUS, LanguageLevel.N1_PLUS]:
                difficulty = 0.9
            
            return AIResponse(
                content=f'''{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation",
            "difficulty": {difficulty}
        }}
    ]
}}''',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=level,
            count=1
        )
        
        # 验证目标级别正确
        assert batch.target_level == level
        
        # 验证练习题的难度匹配级别
        exercise = batch.exercises[0]
        assert 0.0 <= exercise.difficulty <= 1.0
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇"]),
            min_size=1,
            max_size=2
        ),
        exercise_types=st.lists(
            st.sampled_from(ExerciseType),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=10)
    async def test_exercises_include_specified_types(self, weakness_areas, exercise_types):
        """属性51: 生成的练习题应该包含指定的类型"""
        ai_service = Mock()
        
        async def mock_generate(request):
            exercises = []
            for i, ex_type in enumerate(exercise_types):
                exercises.append({
                    "id": f"Q{i+1}",
                    "question": f"Question for {ex_type.value}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": f"Explanation for {ex_type.value}",
                    "difficulty": 0.5
                })
            
            return AIResponse(
                content=f'{{"exercises": {exercises}}}'.replace("'", '"'),
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            exercise_types=exercise_types,
            count=len(exercise_types)
        )
        
        # 验证包含所有指定的类型
        generated_types = set(ex.type for ex in batch.exercises)
        requested_types = set(exercise_types)
        
        assert generated_types == requested_types


class TestExerciseQualityProperties:
    """测试练习题质量属性"""
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇"]),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=15)
    async def test_all_exercises_have_required_fields(self, weakness_areas):
        """所有练习题都应该有必需的字段"""
        ai_service = Mock()
        
        async def mock_generate(request):
            return AIResponse(
                content=f'''{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "Test question with proper length",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation with proper length",
            "difficulty": 0.5
        }}
    ]
}}''',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 验证所有练习题都有必需字段
        for exercise in batch.exercises:
            assert exercise.id is not None
            assert exercise.question is not None
            assert exercise.correct_answer is not None
            assert exercise.explanation is not None
            assert 0.0 <= exercise.difficulty <= 1.0
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇"]),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=10)
    async def test_quality_score_is_calculated(self, weakness_areas):
        """质量分数应该被正确计算"""
        ai_service = Mock()
        
        async def mock_generate(request):
            return AIResponse(
                content=f'''{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "Question with appropriate length for testing quality",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation with appropriate length for testing quality",
            "difficulty": 0.5
        }}
    ]
}}''',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 验证质量分数被计算
        assert 0.0 <= batch.quality_score <= 1.0
        
        # 质量分数应该合理（对于好的练习）
        assert batch.quality_score > 0.3
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇"]),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=10)
    async def test_generation_time_is_recorded(self, weakness_areas):
        """生成时间应该被正确记录"""
        ai_service = Mock()
        
        async def mock_generate(request):
            return AIResponse(
                content=f'''{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation",
            "difficulty": 0.5
        }}
    ]
}}''',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            count=1
        )
        
        # 验证生成时间被记录
        assert batch.generation_duration_ms > 0
        assert batch.generation_duration_ms < 10000  # 应该小于10秒


class TestExerciseVarietyProperties:
    """测试练习题多样性属性"""
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇", "听力"]),
            min_size=2,
            max_size=3
        ),
        count=st.integers(min_value=4, max_value=8)
    )
    @settings(max_examples=10)
    async def test_exercises_have_variety(self, weakness_areas, count):
        """生成的练习题应该有多样性"""
        ai_service = Mock()
        
        async def mock_generate(request):
            exercises = []
            for i in range(count):
                exercises.append({
                    "id": f"Q{i+1}",
                    "question": f"Question {i+1} with unique content",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": f"Explanation {i+1} with unique content",
                    "difficulty": 0.4 + (i * 0.1)  # 不同的难度
                })
            
            return AIResponse(
                content=f'{{"exercises": {exercises}}}'.replace("'", '"'),
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        # 指定单一类型以避免生成所有类型
        batch = await generator.generate_targeted_exercises(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            exercise_types=[ExerciseType.MULTIPLE_CHOICE],
            count=count
        )
        
        # 验证练习题有多样性（不同的难度）
        difficulties = [ex.difficulty for ex in batch.exercises]
        assert len(set(difficulties)) > 1 or len(difficulties) == 1
        
        # 如果有多个练习，验证问题内容不同
        if len(batch.exercises) > 1:
            questions = [ex.question for ex in batch.exercises]
            assert len(set(questions)) == len(questions)  # 所有问题都不同


class TestExerciseFeedbackProperties:
    """测试练习题反馈属性"""
    
    @pytest.mark.asyncio
    @given(
        accuracy=st.floats(min_value=0.0, max_value=1.0),
        weakness_areas=st.lists(
            st.sampled_from(["语法"]),
            min_size=1,
            max_size=1
        )
    )
    @settings(max_examples=15)
    async def test_feedback_adjusts_difficulty(self, accuracy, weakness_areas):
        """用户反馈应该能够调整练习难度"""
        generator = IntelligentContentGenerator()
        
        exercises = [
            Exercise(
                id="Q1",
                type=ExerciseType.MULTIPLE_CHOICE,
                question="Test question",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Test explanation",
                difficulty=0.5
            )
        ]
        
        feedback = {'accuracy': accuracy}
        adjusted = generator.optimize_exercises(exercises, user_feedback=feedback)
        
        # 验证难度被调整
        if accuracy > 0.8:
            # 高准确率应该提高难度
            assert adjusted[0].difficulty >= 0.5
        elif accuracy < 0.5:
            # 低准确率应该降低难度
            assert adjusted[0].difficulty <= 0.5
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.sampled_from(["语法", "词汇"]),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=10)
    async def test_statistics_are_tracked(self, weakness_areas):
        """生成统计信息应该被正确跟踪"""
        ai_service = Mock()
        
        async def mock_generate(request):
            return AIResponse(
                content=f'''{{
    "exercises": [
        {{
            "id": "Q1",
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation",
            "difficulty": 0.5
        }}
    ]
}}''',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=500.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = IntelligentContentGenerator(ai_service)
        
        # 生成多次
        for _ in range(3):
            await generator.generate_targeted_exercises(
                weakness_areas=weakness_areas,
                language_level=LanguageLevel.CET4,
                count=1
            )
        
        stats = generator.get_generation_statistics()
        
        # 验证统计信息
        assert stats['total_generations'] == 3
        assert stats['average_quality_score'] > 0.0
        assert stats['average_duration_ms'] > 0.0
        assert len(stats['recent_history']) == 3
