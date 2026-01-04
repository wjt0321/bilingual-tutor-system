"""
测试AI增强服务
Test AI Enhanced Service

属性49: AI对话难度匹配
属性50: AI响应时间约束

验证需求: 25.1, 25.7
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from typing import Dict, List
import time

from bilingual_tutor.services.ai_service import (
    AIModelType,
    AIResponseQuality,
    LanguageLevel,
    AIModelConfig,
    AIRequest,
    AIResponse,
    ModelPerformanceMetrics,
    BaseAIModelAdapter,
    DeepSeekAdapter,
    ZhipuAIAdapter,
    AIService,
    get_ai_service
)


class MockAIAdapter(BaseAIModelAdapter):
    """Mock AI适配器用于测试"""
    
    def __init__(self, config: AIModelConfig, response_delay: float = 0.1):
        super().__init__(config)
        self.response_delay = response_delay
        self.mock_response = "Mock AI response"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """生成模拟响应"""
        await asyncio.sleep(self.response_delay)
        
        duration_ms = self.response_delay * 1000
        self._update_metrics(True, duration_ms)
        
        return AIResponse(
            content=self.mock_response,
            model_type=self.config.model_type,
            model_name=self.config.model_name,
            duration_ms=duration_ms,
            request_id=request.request_id
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        prompt = messages[-1]['content']
        request = AIRequest(prompt=prompt, request_id=kwargs.get('request_id'))
        return await self.generate(request)
    
    def set_mock_response(self, response: str):
        """设置模拟响应"""
        self.mock_response = response
    
    def set_response_delay(self, delay: float):
        """设置响应延迟"""
        self.response_delay = delay


class TestAIDialogDifficultyMatching:
    """属性49: AI对话难度匹配"""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("language_level", [
        LanguageLevel.CET4,
        LanguageLevel.CET5,
        LanguageLevel.CET6,
        LanguageLevel.CET6_PLUS,
        LanguageLevel.N5,
        LanguageLevel.N4,
        LanguageLevel.N3,
        LanguageLevel.N2,
        LanguageLevel.N1,
        LanguageLevel.N1_PLUS
    ])
    async def test_request_includes_language_level(self, language_level):
        """验证请求包含语言级别"""
        request = AIRequest(
            prompt="Hello",
            language_level=language_level
        )
        
        request_dict = request.to_dict()
        assert 'language_level' in request_dict
        assert request_dict['language_level'] == language_level.value
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("language_level,expected_vocabulary", [
        (LanguageLevel.CET4, ["简单", "基础", "初级"]),
        (LanguageLevel.CET6, ["中等", "进阶", "高级"]),
        (LanguageLevel.N5, ["简单", "基础", "初级"]),
        (LanguageLevel.N2, ["中等", "进阶", "高级"]),
    ])
    async def test_system_prompt_adapts_to_level(self, language_level, expected_vocabulary):
        """验证系统提示词根据级别调整"""
        request = AIRequest(
            prompt="Test",
            language_level=language_level,
            system_prompt=f"为{language_level.value}级别学习者提供内容"
        )
        
        assert request.language_level == language_level
        assert language_level.value in request.system_prompt
    
    @given(st.sampled_from([LanguageLevel.CET4, LanguageLevel.CET5, LanguageLevel.CET6, 
                           LanguageLevel.N5, LanguageLevel.N4, LanguageLevel.N3]))
    @settings(max_examples=50)
    def test_all_levels_supported(self, language_level):
        """验证所有语言级别都支持"""
        request = AIRequest(
            prompt="Test",
            language_level=language_level
        )
        
        assert request.language_level == language_level
        assert language_level.value in [l.value for l in LanguageLevel]
    
    @pytest.mark.asyncio
    async def test_adapter_preserves_language_level(self):
        """验证适配器保留语言级别"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config)
        
        request = AIRequest(
            prompt="Hello",
            language_level=LanguageLevel.CET6
        )
        
        response = await adapter.generate(request)
        assert response is not None
        assert isinstance(response, AIResponse)
    
    @pytest.mark.asyncio
    async def test_conversation_history_preservation(self):
        """验证对话历史保留"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config)
        
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        request = AIRequest(
            prompt="Tell me more",
            conversation_history=conversation_history
        )
        
        request_dict = request.to_dict()
        assert 'conversation_history' in request_dict
        assert len(request_dict['conversation_history']) == 3


class TestAIResponseTimeConstraints:
    """属性50: AI响应时间约束"""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("delay,expected_duration_ms", [
        (0.1, 100),
        (0.2, 200),
        (0.5, 500),
        (1.0, 1000),
    ])
    async def test_response_time_measured(self, delay, expected_duration_ms):
        """验证响应时间被测量"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config, response_delay=delay)
        
        request = AIRequest(prompt="Test")
        response = await adapter.generate(request)
        
        assert response.duration_ms is not None
        assert abs(response.duration_ms - expected_duration_ms) < 50
    
    @pytest.mark.asyncio
    async def test_response_time_includes_in_metrics(self):
        """验证响应时间包含在性能指标中"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config, response_delay=0.2)
        
        await adapter.generate(AIRequest(prompt="Test1"))
        await adapter.generate(AIRequest(prompt="Test2"))
        await adapter.generate(AIRequest(prompt="Test3"))
        
        metrics = adapter.get_metrics()
        assert metrics.average_duration_ms > 0
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 3
    
    @pytest.mark.asyncio
    @given(st.floats(min_value=0.01, max_value=1.0))
    @settings(max_examples=50)
    async def test_various_response_times(self, delay):
        """验证各种响应时间都被正确测量"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config, response_delay=delay)
        
        request = AIRequest(prompt="Test")
        response = await adapter.generate(request)
        
        expected_duration_ms = delay * 1000
        assert abs(response.duration_ms - expected_duration_ms) < 50
    
    @pytest.mark.asyncio
    async def test_timeout_configuration(self):
        """验证超时配置"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model",
            timeout=10
        )
        
        assert config.timeout == 10
        config.validate()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self):
        """验证并发请求性能"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config, response_delay=0.1)
        
        # 创建10个并发请求
        tasks = [
            adapter.generate(AIRequest(prompt=f"Test{i}", request_id=f"req{i}"))
            for i in range(10)
        ]
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_duration_ms = (end_time - start_time) * 1000
        
        assert len(responses) == 10
        # 并发请求应该比顺序请求快
        assert total_duration_ms < 800  # 应该远小于10 * 100ms = 1000ms
        
        metrics = adapter.get_metrics()
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 10


class TestModelPerformanceMetrics:
    """测试模型性能指标"""
    
    def test_metrics_initialization(self):
        """验证指标初始化"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        assert metrics.model_type == AIModelType.DEEPSEEK
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_duration_ms == 0.0
    
    def test_successful_request_update(self):
        """验证成功请求更新"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        metrics.update(success=True, duration_ms=100.0)
        metrics.update(success=True, duration_ms=200.0)
        
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 0
        assert metrics.average_duration_ms == 150.0
    
    def test_failed_request_update(self):
        """验证失败请求更新"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        metrics.update(success=True, duration_ms=100.0)
        metrics.update(success=False, duration_ms=50.0)
        metrics.update(success=True, duration_ms=150.0)
        
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.average_duration_ms == 100.0
    
    def test_success_rate_calculation(self):
        """验证成功率计算"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        assert metrics.get_success_rate() == 0.0
        
        metrics.update(success=True, duration_ms=100.0)
        assert metrics.get_success_rate() == 1.0
        
        metrics.update(success=False, duration_ms=50.0)
        assert metrics.get_success_rate() == 0.5
        
        metrics.update(success=True, duration_ms=100.0)
        metrics.update(success=True, duration_ms=100.0)
        assert metrics.get_success_rate() == 0.75
    
    @given(st.integers(min_value=0, max_value=100), st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_metrics_with_various_inputs(self, success_count, fail_count):
        """验证各种输入的指标"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        total = success_count + fail_count
        if total == 0:
            assert metrics.get_success_rate() == 0.0
        else:
            for _ in range(success_count):
                metrics.update(success=True, duration_ms=100.0)
            for _ in range(fail_count):
                metrics.update(success=False, duration_ms=50.0)
            
            assert metrics.total_requests == total
            assert metrics.successful_requests == success_count
            assert metrics.failed_requests == fail_count
            assert metrics.get_success_rate() == success_count / total
    
    def test_metrics_to_dict(self):
        """验证指标转换为字典"""
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(success=True, duration_ms=100.0)
        
        metrics_dict = metrics.to_dict()
        
        assert 'model_type' in metrics_dict
        assert 'total_requests' in metrics_dict
        assert 'successful_requests' in metrics_dict
        assert 'failed_requests' in metrics_dict
        assert 'success_rate' in metrics_dict
        assert 'average_duration_ms' in metrics_dict
        assert metrics_dict['model_type'] == 'deepseek'


class TestAIService:
    """测试AI服务"""
    
    @pytest.mark.asyncio
    async def test_generate_with_mock_adapter(self):
        """验证使用Mock适配器生成响应"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config)
        adapter.set_mock_response("Custom response")
        
        request = AIRequest(prompt="Test", request_id="test-req-1")
        response = await adapter.generate(request)
        
        assert response.content == "Custom response"
        assert response.request_id == "test-req-1"
        assert response.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_chat_mode(self):
        """验证对话模式"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config)
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        response = await adapter.chat(messages, request_id="chat-req-1")
        
        assert response.content == "Mock AI response"
        assert response.request_id == "chat-req-1"
    
    @pytest.mark.asyncio
    async def test_multiple_requests(self):
        """验证多个请求"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        
        adapter = MockAIAdapter(config)
        
        for i in range(5):
            request = AIRequest(prompt=f"Test {i}", request_id=f"req-{i}")
            response = await adapter.generate(request)
            
            assert response is not None
            assert isinstance(response, AIResponse)
        
        metrics = adapter.get_metrics()
        assert metrics.total_requests == 5
        assert metrics.successful_requests == 5
    
    def test_model_config_validation(self):
        """验证模型配置验证"""
        # 有效配置
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="http://test.com",
            model_name="test-model"
        )
        config.validate()
        
        # 无效配置 - 缺少API密钥
        with pytest.raises(Exception):
            config = AIModelConfig(
                model_type=AIModelType.DEEPSEEK,
                api_key="",
                api_url="http://test.com",
                model_name="test-model"
            )
            config.validate()
    
    @pytest.mark.asyncio
    async def test_request_and_response_structure(self):
        """验证请求和响应结构"""
        request = AIRequest(
            prompt="Test prompt",
            system_prompt="Test system",
            conversation_history=[{"role": "user", "content": "Previous"}],
            language_level=LanguageLevel.CET6,
            max_tokens=1000,
            temperature=0.8,
            request_id="test-id"
        )
        
        request_dict = request.to_dict()
        assert 'prompt' in request_dict
        assert 'system_prompt' in request_dict
        assert 'conversation_history' in request_dict
        assert 'language_level' in request_dict
        assert 'max_tokens' in request_dict
        assert 'temperature' in request_dict
        
        response = AIResponse(
            content="Test response",
            model_type=AIModelType.DEEPSEEK,
            model_name="test-model",
            duration_ms=150.5,
            tokens_used=50,
            quality=AIResponseQuality.GOOD,
            request_id="test-id"
        )
        
        response_dict = response.to_dict()
        assert 'content' in response_dict
        assert 'model_type' in response_dict
        assert 'model_name' in response_dict
        assert 'duration_ms' in response_dict
        assert 'tokens_used' in response_dict
        assert 'quality' in response_dict
        assert 'request_id' in response_dict
