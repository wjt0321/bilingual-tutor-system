"""
AI增强服务测试
测试大语言模型服务的核心功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from bilingual_tutor.services.ai_service import (
    AIService,
    AIModelType,
    AIModelConfig,
    AIRequest,
    AIResponse,
    LanguageLevel,
    ExerciseType,
    ScenarioType,
    ConversationPartner,
    GrammarCorrector,
    ExerciseGenerator,
    get_ai_service,
    get_conversation_partner,
    get_grammar_corrector,
    get_exercise_generator
)
from bilingual_tutor.infrastructure.error_handler import ConfigurationError


class TestAIModelConfig:
    """测试AI模型配置"""
    
    def test_valid_config(self):
        """测试有效配置"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="https://api.test.com",
            model_name="test-model"
        )
        config.validate()
        assert config.model_type == AIModelType.DEEPSEEK
        assert config.api_key == "test_key"
    
    def test_invalid_config_no_api_key(self):
        """测试无效配置：缺少API密钥"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="",
            api_url="https://api.test.com",
            model_name="test-model"
        )
        with pytest.raises(ConfigurationError):
            config.validate()
    
    def test_invalid_config_max_tokens(self):
        """测试无效配置：max_tokens <= 0"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="https://api.test.com",
            model_name="test-model",
            max_tokens=0
        )
        with pytest.raises(ConfigurationError):
            config.validate()
    
    def test_invalid_config_temperature(self):
        """测试无效配置：temperature超出范围"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="https://api.test.com",
            model_name="test-model",
            temperature=3.0
        )
        with pytest.raises(ConfigurationError):
            config.validate()


class TestAIRequest:
    """测试AI请求"""
    
    def test_request_to_dict(self):
        """测试请求转换为字典"""
        request = AIRequest(
            prompt="Test prompt",
            system_prompt="System prompt",
            language_level=LanguageLevel.CET4,
            max_tokens=500,
            temperature=0.7
        )
        result = request.to_dict()
        
        assert result['prompt'] == "Test prompt"
        assert result['system_prompt'] == "System prompt"
        assert result['language_level'] == "CET-4"
        assert result['max_tokens'] == 500
        assert result['temperature'] == 0.7


class TestAIResponse:
    """测试AI响应"""
    
    def test_response_to_dict(self):
        """测试响应转换为字典"""
        response = AIResponse(
            content="Test response",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=1234.56,
            tokens_used=100,
            request_id="test-id"
        )
        result = response.to_dict()
        
        assert result['content'] == "Test response"
        assert result['model_type'] == "deepseek"
        assert result['model_name'] == "deepseek-chat"
        assert result['duration_ms'] == 1234.56
        assert result['tokens_used'] == 100
        assert result['request_id'] == "test-id"


class TestConversationPartner:
    """测试AI对话伙伴"""
    
    @pytest.mark.asyncio
    async def test_start_conversation_with_mock(self):
        """测试开始对话（使用Mock）"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="Hello! Let's practice English conversation.",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        result = await partner.start_conversation(
            user_level=LanguageLevel.CET4,
            scenario=ScenarioType.DAILY
        )
        
        assert result['type'] == 'conversation'
        assert result['level'] == 'CET-4'
        assert result['scenario'] == 'daily'
        assert 'ai_message' in result
        assert 'conversation_id' in result
        assert result['duration_ms'] == 500.0
        
        ai_service.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """测试继续对话"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="That's great! Tell me more about it.",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=450.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        result = await partner.continue_conversation(
            conversation_id="test-conv-id",
            user_message="I like reading books.",
            conversation_history=conversation_history,
            user_level=LanguageLevel.CET4
        )
        
        assert result['type'] == 'conversation'
        assert result['conversation_id'] == 'test-conv-id'
        assert result['user_message'] == "I like reading books."
        assert result['duration_ms'] == 450.0
    
    @pytest.mark.asyncio
    async def test_explain_vocabulary(self):
        """测试词汇解释"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="Definition and examples...",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=300.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        result = await partner.explain_vocabulary(
            word="hello",
            language_level=LanguageLevel.CET4
        )
        
        assert result['type'] == 'vocabulary'
        assert result['word'] == 'hello'
        assert result['level'] == 'CET-4'
        assert result['duration_ms'] == 300.0


class TestGrammarCorrector:
    """测试语法纠错器"""
    
    @pytest.mark.asyncio
    async def test_correct_grammar_with_mock(self):
        """测试语法纠错（使用Mock）"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "is_correct": false,
    "corrected_text": "He goes to school every day.",
    "errors": [
        {
            "original": "He go",
            "correction": "He goes",
            "explanation": "第三人称单数需要加s",
            "rule": "一般现在时第三人称单数"
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=400.0,
            request_id="test-id"
        ))
        
        corrector = GrammarCorrector(ai_service)
        result = await corrector.correct(
            text="He go to school everyday.",
            language="english"
        )
        
        assert result['is_correct'] == False
        assert 'corrected_text' in result
        assert 'errors' in result
        assert result['duration_ms'] == 400.0
    
    @pytest.mark.asyncio
    async def test_correct_grammar_no_errors(self):
        """测试语法纠错：无错误"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "is_correct": true,
    "corrected_text": "The weather is nice today.",
    "errors": []
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=350.0,
            request_id="test-id"
        ))
        
        corrector = GrammarCorrector(ai_service)
        result = await corrector.correct(
            text="The weather is nice today.",
            language="english"
        )
        
        assert result['is_correct'] == True
        assert len(result['errors']) == 0


class TestExerciseGenerator:
    """测试练习生成器"""
    
    @pytest.mark.asyncio
    async def test_generate_exercise_with_mock(self):
        """测试生成练习题（使用Mock）"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercise_type": "multiple_choice",
    "level": "CET-4",
    "target_areas": ["语法"],
    "questions": [
        {
            "id": "Q1",
            "question": "选择正确的句子：",
            "options": ["He go to school.", "He goes to school.", "He going to school.", "He went to school."],
            "correct_answer": "He goes to school.",
            "explanation": "第三人称单数需要加s"
        }
    ]
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=800.0,
            request_id="test-id"
        ))
        
        generator = ExerciseGenerator(ai_service)
        result = await generator.generate_exercise(
            weakness_areas=["语法"],
            language_level=LanguageLevel.CET4,
            exercise_type=ExerciseType.MULTIPLE_CHOICE,
            count=5
        )
        
        assert result['exercise_type'] == 'multiple_choice'
        assert result['level'] == 'CET-4'
        assert 'questions' in result
        assert result['duration_ms'] == 800.0
    
    @pytest.mark.asyncio
    async def test_generate_batch_exercises(self):
        """测试批量生成练习题"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content='''{
    "exercise_type": "multiple_choice",
    "level": "CET-4",
    "target_areas": ["词汇"],
    "questions": []
}''',
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        generator = ExerciseGenerator(ai_service)
        result = await generator.generate_batch_exercises(
            weakness_areas={'general': ['词汇']},
            language_level=LanguageLevel.CET4,
            exercises_per_area=2
        )
        
        assert result['batch'] == True
        assert result['level'] == 'CET-4'
        assert 'exercises' in result
        assert 'multiple_choice' in result['exercises']


class TestServiceSingletons:
    """测试服务单例"""
    
    def test_get_ai_service_singleton(self):
        """测试AI服务单例"""
        service1 = get_ai_service()
        service2 = get_ai_service()
        assert service1 is service2
    
    def test_get_conversation_partner_singleton(self):
        """测试对话伙伴单例"""
        partner1 = get_conversation_partner()
        partner2 = get_conversation_partner()
        assert partner1 is partner2
    
    def test_get_grammar_corrector_singleton(self):
        """测试语法纠错器单例"""
        corrector1 = get_grammar_corrector()
        corrector2 = get_grammar_corrector()
        assert corrector1 is corrector2
    
    def test_get_exercise_generator_singleton(self):
        """测试练习生成器单例"""
        generator1 = get_exercise_generator()
        generator2 = get_exercise_generator()
        assert generator1 is generator2


class TestModelPerformanceMetrics:
    """测试模型性能指标"""
    
    def test_metrics_update(self):
        """测试指标更新"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(True, 500.0)
        metrics.update(True, 600.0)
        metrics.update(False, 700.0)
        
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.get_success_rate() == 2/3
        assert metrics.average_duration_ms == 600.0
    
    def test_metrics_to_dict(self):
        """测试指标转换为字典"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(True, 500.0)
        
        result = metrics.to_dict()
        
        assert result['model_type'] == 'deepseek'
        assert result['total_requests'] == 1
        assert result['successful_requests'] == 1
        assert result['success_rate'] == 1.0
        assert result['average_duration_ms'] == 500.0


class TestLanguageLevelAndExerciseType:
    """测试语言级别和练习类型枚举"""
    
    def test_language_levels(self):
        """测试语言级别枚举"""
        assert LanguageLevel.CET4.value == "CET-4"
        assert LanguageLevel.CET6.value == "CET-6"
        assert LanguageLevel.N5.value == "N5"
        assert LanguageLevel.N1.value == "N1"
    
    def test_exercise_types(self):
        """测试练习类型枚举"""
        assert ExerciseType.MULTIPLE_CHOICE.value == "multiple_choice"
        assert ExerciseType.FILL_BLANK.value == "fill_blank"
        assert ExerciseType.TRANSLATION.value == "translation"
        assert ExerciseType.WRITING.value == "writing"
    
    def test_scenario_types(self):
        """测试场景类型枚举"""
        assert ScenarioType.DAILY.value == "daily"
        assert ScenarioType.BUSINESS.value == "business"
        assert ScenarioType.ACADEMIC.value == "academic"
        assert ScenarioType.TRAVEL.value == "travel"
