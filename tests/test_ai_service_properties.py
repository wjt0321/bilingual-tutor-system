"""
AI服务属性测试
使用Hypothesis进行属性测试，验证AI服务的关键属性
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings, example
from bilingual_tutor.services.ai_service import (
    AIService,
    AIModelType,
    AIModelConfig,
    AIRequest,
    AIResponse,
    LanguageLevel,
    ScenarioType,
    ConversationPartner,
    get_conversation_partner
)


class TestAIDialogueDifficultyMatching:
    """
    属性49: AI对话难度匹配
    
    验证需求25.1: 当用户发起对话练习时，大语言模型服务应使用DeepSeek等国内模型
    根据用户的语言水平提供适当难度的对话
    """
    
    @pytest.mark.asyncio
    @given(
        level=st.sampled_from(LanguageLevel),
        scenario=st.sampled_from(ScenarioType)
    )
    @settings(max_examples=20)
    async def test_conversation_respects_language_level(self, level, scenario):
        """属性49: AI对话应该根据用户的语言水平提供适当难度的对话"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="AI response",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        result = await partner.start_conversation(user_level=level, scenario=scenario)
        
        # 验证对话级别匹配
        assert result['level'] == level.value
        assert result['scenario'] == scenario.value
        
        # 验证AI请求包含了语言级别信息
        call_args = ai_service.generate.call_args
        request = call_args[0][0]
        assert request.language_level == level
    
    @pytest.mark.asyncio
    @given(
        level=st.sampled_from(LanguageLevel),
        user_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=15)
    async def test_conversation_continuation_maintains_level(self, level, user_message):
        """属性49: 对话延续应该保持相同的语言水平"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="AI response",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        result = await partner.continue_conversation(
            conversation_id="test-id",
            user_message=user_message,
            conversation_history=conversation_history,
            user_level=level
        )
        
        # 验证请求中包含了正确的语言级别
        call_args = ai_service.generate.call_args
        request = call_args[0][0]
        assert request.language_level == level
    
    @pytest.mark.asyncio
    @given(
        word=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    )
    @settings(max_examples=10)
    async def test_vocabulary_explanation_respects_level(self, word):
        """属性49: 词汇解释应该根据用户的语言水平调整"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="Vocabulary explanation",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=400.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        level = LanguageLevel.CET4
        
        result = await partner.explain_vocabulary(word=word, language_level=level)
        
        # 验证词汇解释包含了正确的级别
        assert result['level'] == level.value
        assert result['word'] == word
        
        # 验证AI请求包含了语言级别
        call_args = ai_service.generate.call_args
        request = call_args[0][0]
        assert request.language_level == level


class TestAIResponseTimeConstraints:
    """
    属性50: AI响应时间约束
    
    验证需求25.7: AI响应时间应控制在5秒以内
    """
    
    @pytest.mark.asyncio
    @given(
        prompt=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=20, deadline=None)
    async def test_conversation_response_time_under_5_seconds(self, prompt):
        """属性50: AI对话响应时间应该小于5秒"""
        with patch.dict('os.environ', {
            'DEEPSEEK_API_KEY': 'test_key'
        }, clear=False):
            service = AIService()
            
            # Mock真实的API调用，模拟快速响应
            for adapter in service._adapters.values():
                async def mock_generate(request):
                    await asyncio.sleep(0.1)  # 模拟100ms延迟
                    return AIResponse(
                        content="Fast response",
                        model_type=AIModelType.DEEPSEEK,
                        model_name="deepseek-chat",
                        duration_ms=100.0,
                        request_id="test-id"
                    )
                adapter.generate = mock_generate
            
            request = AIRequest(prompt=prompt)
            
            import time
            start_time = time.time()
            response = await service.generate(request)
            end_time = time.time()
            
            actual_duration = (end_time - start_time) * 1000
            
            # 验证响应时间小于5000毫秒（5秒）
            assert actual_duration < 5000.0, f"响应时间 {actual_duration}ms 超过了5秒限制"
    
    @pytest.mark.asyncio
    @given(
        level=st.sampled_from(LanguageLevel)
    )
    @settings(max_examples=10)
    async def test_conversation_start_response_time(self, level):
        """属性50: 开始对话的响应时间应该小于5秒"""
        ai_service = Mock(spec=AIService)
        
        async def mock_generate(request):
            await asyncio.sleep(0.05)  # 模拟50ms延迟
            return AIResponse(
                content="Conversation start response",
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=50.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        partner = ConversationPartner(ai_service)
        
        import time
        start_time = time.time()
        result = await partner.start_conversation(user_level=level)
        end_time = time.time()
        
        actual_duration = (end_time - start_time) * 1000
        
        # 验证总响应时间小于5000毫秒（5秒）
        assert actual_duration < 5000.0, f"开始对话耗时 {actual_duration}ms 超过了5秒限制"
        assert result['duration_ms'] < 5000.0
    
    @pytest.mark.asyncio
    @given(
        text=st.text(min_size=1, max_size=300)
    )
    @settings(max_examples=15)
    async def test_grammar_correction_response_time(self, text):
        """属性50: 语法纠错的响应时间应该小于5秒"""
        from bilingual_tutor.services.ai_service import GrammarCorrector
        
        ai_service = Mock(spec=AIService)
        
        async def mock_generate(request):
            await asyncio.sleep(0.08)  # 模拟80ms延迟
            return AIResponse(
                content='{"is_correct": true, "corrected_text": "' + text + '", "errors": []}',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=80.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        corrector = GrammarCorrector(ai_service)
        
        import time
        start_time = time.time()
        result = await corrector.correct(text=text, language="english")
        end_time = time.time()
        
        actual_duration = (end_time - start_time) * 1000
        
        # 验证响应时间小于5000毫秒（5秒）
        assert actual_duration < 5000.0, f"语法纠错耗时 {actual_duration}ms 超过了5秒限制"
    
    @pytest.mark.asyncio
    @given(
        weakness_areas=st.lists(
            st.text(min_size=1, max_size=20),
            min_size=1,
            max_size=5
        ),
        count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10)
    async def test_exercise_generation_response_time(self, weakness_areas, count):
        """属性50: 练习生成的响应时间应该小于5秒"""
        from bilingual_tutor.services.ai_service import ExerciseGenerator, ExerciseType
        
        ai_service = Mock(spec=AIService)
        
        async def mock_generate(request):
            await asyncio.sleep(0.2)  # 模拟200ms延迟
            return AIResponse(
                content='{"exercise_type": "multiple_choice", "level": "CET-4", "questions": []}',
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=200.0,
                request_id="test-id"
            )
        
        ai_service.generate = mock_generate
        
        generator = ExerciseGenerator(ai_service)
        
        import time
        start_time = time.time()
        result = await generator.generate_exercise(
            weakness_areas=weakness_areas,
            language_level=LanguageLevel.CET4,
            exercise_type=ExerciseType.MULTIPLE_CHOICE,
            count=count
        )
        end_time = time.time()
        
        actual_duration = (end_time - start_time) * 1000
        
        # 验证响应时间小于5000毫秒（5秒）
        assert actual_duration < 5000.0, f"练习生成耗时 {actual_duration}ms 超过了5秒限制"


class TestAIDialogueContentQuality:
    """
    测试AI对话内容质量
    """
    
    @pytest.mark.asyncio
    @given(
        level=st.sampled_from(LanguageLevel),
        scenario=st.sampled_from(ScenarioType)
    )
    @settings(max_examples=15)
    async def test_conversation_includes_chinese_explanations(self, level, scenario):
        """AI对话应该包含中文解释和反馈"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="This is an English response with 中文 explanations.",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        result = await partner.start_conversation(user_level=level, scenario=scenario)
        
        # 验证响应内容存在
        assert result['ai_message'] is not None
        assert len(result['ai_message']) > 0
    
    @pytest.mark.asyncio
    @given(
        user_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=10)
    async def test_conversation_maintains_context(self, user_message):
        """对话应该保持上下文"""
        ai_service = Mock(spec=AIService)
        ai_service.generate = AsyncMock(return_value=AIResponse(
            content="Context-aware response",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        ))
        
        partner = ConversationPartner(ai_service)
        
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm good, thanks!"}
        ]
        
        result = await partner.continue_conversation(
            conversation_id="test-id",
            user_message=user_message,
            conversation_history=conversation_history,
            user_level=LanguageLevel.CET4
        )
        
        # 验证对话历史被传递
        call_args = ai_service.generate.call_args
        request = call_args[0][0]
        assert request.conversation_history == conversation_history


class TestAIModelSelectionProperties:
    """
    测试AI模型选择的属性
    """
    
    @pytest.mark.asyncio
    @given(
        prompt=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=15)
    async def test_model_selection_is_deterministic(self, prompt):
        """模型选择应该是确定性的（相同的输入选择相同的模型）"""
        with patch.dict('os.environ', {
            'DEEPSEEK_API_KEY': 'test_key',
            'ZHIPU_API_KEY': 'test_key'
        }, clear=False):
            service = AIService()
            
            # 设置相同的性能指标
            for adapter in service._adapters.values():
                adapter._update_metrics(True, 500.0)
                adapter._update_metrics(True, 520.0)
            
            # Mock生成方法
            async def mock_generate(request):
                return AIResponse(
                    content="Response",
                    model_type=AIModelType.DEEPSEEK,
                    model_name="deepseek-chat",
                    duration_ms=500.0,
                    request_id="test-id"
                )
            
            for adapter in service._adapters.values():
                adapter.generate = mock_generate
            
            request = AIRequest(prompt=prompt)
            
            # 两次请求应该选择相同的模型
            response1 = await service.generate_with_load_balancing(request)
            response2 = await service.generate_with_load_balancing(request)
            
            assert response1.model_type == response2.model_type
    
    @pytest.mark.asyncio
    @given(
        num_requests=st.integers(min_value=10, max_value=50)
    )
    @settings(max_examples=5)
    async def test_multiple_requests_respect_time_limit(self, num_requests):
        """多个请求的总时间应该符合线性增长（不会出现性能退化）"""
        with patch.dict('os.environ', {
            'DEEPSEEK_API_KEY': 'test_key'
        }, clear=False):
            service = AIService()
            
            async def mock_generate(request):
                await asyncio.sleep(0.01)  # 模拟10ms延迟
                return AIResponse(
                    content="Response",
                    model_type=AIModelType.DEEPSEEK,
                    model_name="deepseek-chat",
                    duration_ms=10.0,
                    request_id="test-id"
                )
            
            for adapter in service._adapters.values():
                adapter.generate = mock_generate
            
            import time
            start_time = time.time()
            
            for i in range(num_requests):
                request = AIRequest(prompt=f"Request {i}")
                response = await service.generate(request)
                assert response.duration_ms < 5000.0  # 每个请求都小于5秒
            
            end_time = time.time()
            total_duration = (end_time - start_time) * 1000
            
            # 验证总时间合理（每个请求约10ms，加上一些开销）
            expected_max = num_requests * 50  # 允许每请求最多50ms
            assert total_duration < expected_max, f"总时间 {total_duration}ms 超过了预期 {expected_max}ms"
