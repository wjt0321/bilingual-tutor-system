"""
多模型支持和管理测试
测试统一接口适配器、多模型支持、自动切换和性能监控
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from bilingual_tutor.services.ai_service import (
    AIService,
    AIModelType,
    AIModelConfig,
    AIRequest,
    AIResponse,
    DeepSeekAdapter,
    ZhipuAIAdapter,
    BaichuanAIAdapter,
    BaseAIModelAdapter,
    LanguageLevel
)
from bilingual_tutor.infrastructure.error_handler import ConfigurationError, RateLimitError


class TestDeepSeekAdapter:
    """测试DeepSeek适配器"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """测试成功生成响应"""
        config = AIModelConfig(
            model_type=AIModelType.DEEPSEEK,
            api_key="test_key",
            api_url="https://api.deepseek.com/v1/chat/completions",
            model_name="deepseek-chat"
        )
        adapter = DeepSeekAdapter(config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'choices': [{'message': {'content': 'Test response'}}],
                'usage': {'total_tokens': 100}
            })
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock()
            
            mock_session.return_value.__aenter__.return_value.post = Mock(return_value=mock_post)
            
            request = AIRequest(prompt="Test prompt")
            response = await adapter.generate(request)
            
            assert response.content == "Test response"
            assert response.model_type == AIModelType.DEEPSEEK
            assert response.tokens_used == 100
            assert response.duration_ms > 0


class TestZhipuAIAdapter:
    """测试智谱AI适配器"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """测试成功生成响应"""
        config = AIModelConfig(
            model_type=AIModelType.ZHIPU,
            api_key="test_key",
            api_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            model_name="glm-4"
        )
        adapter = ZhipuAIAdapter(config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'choices': [{'message': {'content': 'Test response'}}],
                'usage': {'total_tokens': 100}
            })
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock()
            
            mock_session.return_value.__aenter__.return_value.post = Mock(return_value=mock_post)
            
            request = AIRequest(prompt="Test prompt")
            response = await adapter.generate(request)
            
            assert response.content == "Test response"
            assert response.model_type == AIModelType.ZHIPU
            assert response.tokens_used == 100


class TestBaichuanAIAdapter:
    """测试百川AI适配器"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """测试成功生成响应"""
        config = AIModelConfig(
            model_type=AIModelType.BAICHUAN,
            api_key="test_key",
            api_url="https://api.baichuan-ai.com/v1/chat/completions",
            model_name="Baichuan2-Turbo"
        )
        adapter = BaichuanAIAdapter(config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'choices': [{'message': {'content': 'Test response'}}],
                'usage': {'total_tokens': 100}
            })
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock()
            
            mock_session.return_value.__aenter__.return_value.post = Mock(return_value=mock_post)
            
            request = AIRequest(prompt="Test prompt")
            response = await adapter.generate(request)
            
            assert response.content == "Test response"
            assert response.model_type == AIModelType.BAICHUAN
            assert response.tokens_used == 100


class TestAIServiceMultiModel:
    """测试AI服务多模型支持"""
    
    def test_load_models_from_env(self):
        """测试从环境变量加载模型"""
        env_vars = {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key',
            'BAICHUAN_API_KEY': 'test_baichuan_key'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            service = AIService()
            
            assert len(service._adapters) == 3
            assert AIModelType.DEEPSEEK in service._adapters
            assert AIModelType.ZHIPU in service._adapters
            assert AIModelType.BAICHUAN in service._adapters
    
    @pytest.mark.asyncio
    async def test_auto_fallback_on_failure(self):
        """测试失败时自动切换到备用模型"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # Mock DeepSeek失败，智谱AI成功
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter.generate = AsyncMock(side_effect=Exception("DeepSeek failed"))
            zhipu_adapter.generate = AsyncMock(return_value=AIResponse(
                content="Fallback response",
                model_type=AIModelType.ZHIPU,
                model_name="glm-4",
                duration_ms=600.0,
                request_id="test-id"
            ))
            
            request = AIRequest(prompt="Test prompt")
            response = await service.generate(request)
            
            assert response.model_type == AIModelType.ZHIPU
            assert response.content == "Fallback response"
            deepseek_adapter.generate.assert_called_once()
            zhipu_adapter.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_models_fail(self):
        """测试所有模型都失败的情况"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 所有模型都失败
            for adapter in service._adapters.values():
                adapter.generate = AsyncMock(side_effect=Exception("Model failed"))
            
            request = AIRequest(prompt="Test prompt")
            
            from bilingual_tutor.infrastructure.error_handler import ExternalServiceError
            with pytest.raises(ExternalServiceError, match="所有AI模型都不可用"):
                await service.generate(request)


class TestLoadBalancing:
    """测试负载均衡"""
    
    def test_select_best_model_by_success_rate(self):
        """测试根据成功率选择最佳模型"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置不同的性能指标
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter._update_metrics(True, 500.0)
            deepseek_adapter._update_metrics(True, 600.0)
            deepseek_adapter._update_metrics(True, 550.0)
            deepseek_adapter._update_metrics(True, 520.0)
            deepseek_adapter._update_metrics(False, 580.0)  # 80% 成功率
            
            zhipu_adapter._update_metrics(True, 800.0)
            zhipu_adapter._update_metrics(False, 900.0)  # 50% 成功率
            
            best_model = service._select_best_model()
            assert best_model == AIModelType.DEEPSEEK
    
    def test_select_best_model_by_duration(self):
        """测试根据响应时间选择最佳模型"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置相同的成功率，不同的响应时间
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter._update_metrics(True, 300.0)
            deepseek_adapter._update_metrics(True, 320.0)
            
            zhipu_adapter._update_metrics(True, 600.0)
            zhipu_adapter._update_metrics(True, 620.0)
            
            best_model = service._select_best_model()
            assert best_model == AIModelType.DEEPSEEK
    
    @pytest.mark.asyncio
    async def test_generate_with_load_balancing(self):
        """测试使用负载均衡生成响应"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置DeepSeek性能更好
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter.generate = AsyncMock(return_value=AIResponse(
                content="DeepSeek response",
                model_type=AIModelType.DEEPSEEK,
                model_name="deepseek-chat",
                duration_ms=400.0,
                request_id="test-id"
            ))
            deepseek_adapter._update_metrics(True, 400.0)
            deepseek_adapter._update_metrics(True, 420.0)
            
            zhipu_adapter.generate = AsyncMock(return_value=AIResponse(
                content="Zhipu response",
                model_type=AIModelType.ZHIPU,
                model_name="glm-4",
                duration_ms=800.0,
                request_id="test-id"
            ))
            zhipu_adapter._update_metrics(True, 800.0)
            zhipu_adapter._update_metrics(False, 900.0)
            
            request = AIRequest(prompt="Test prompt")
            response = await service.generate_with_load_balancing(request)
            
            assert response.model_type == AIModelType.DEEPSEEK


class TestPerformanceMonitoring:
    """测试性能监控"""
    
    def test_model_health_status(self):
        """测试模型健康状态"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置不同的性能指标
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter._update_metrics(True, 500.0)
            deepseek_adapter._update_metrics(True, 520.0)
            deepseek_adapter._update_metrics(True, 510.0)
            deepseek_adapter._update_metrics(True, 505.0)
            deepseek_adapter._update_metrics(True, 515.0)  # 100% 成功率
            
            zhipu_adapter._update_metrics(True, 600.0)
            zhipu_adapter._update_metrics(False, 700.0)
            zhipu_adapter._update_metrics(False, 800.0)  # 33% 成功率
            
            status = service.get_model_health_status()
            
            assert status['deepseek']['health'] == 'excellent'
            assert status['zhipu']['health'] == 'poor'
            assert 'metrics' in status['deepseek']
            assert 'metrics' in status['zhipu']
    
    def test_get_recommendation(self):
        """测试获取使用建议"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置良好的性能
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            zhipu_adapter = service._adapters[AIModelType.ZHIPU]
            
            deepseek_adapter._update_metrics(True, 500.0)
            deepseek_adapter._update_metrics(True, 520.0)
            
            zhipu_adapter._update_metrics(True, 600.0)
            zhipu_adapter._update_metrics(True, 620.0)
            
            recommendation = service.get_recommendation()
            
            assert recommendation['recommendation'] == 'use_load_balancing'
            assert 'healthy_models' in recommendation
            assert len(recommendation['healthy_models']) == 2
    
    def test_get_recommendation_degraded(self):
        """测试获取使用建议（性能一般）"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            # 设置一般的性能
            deepseek_adapter = service._adapters[AIModelType.DEEPSEEK]
            
            deepseek_adapter._update_metrics(True, 800.0)
            deepseek_adapter._update_metrics(True, 900.0)
            deepseek_adapter._update_metrics(False, 1000.0)  # 67% 成功率
            
            recommendation = service.get_recommendation()
            
            assert recommendation['recommendation'] == 'use_primary_with_fallback'
            assert 'available_models' in recommendation
    
    def test_get_model_metrics(self):
        """测试获取模型性能指标"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key'
        }, clear=False):
            service = AIService()
            
            # 更新指标
            adapter = service._adapters[AIModelType.DEEPSEEK]
            adapter._update_metrics(True, 500.0)
            adapter._update_metrics(True, 600.0)
            adapter._update_metrics(False, 700.0)
            
            metrics = service.get_model_metrics(AIModelType.DEEPSEEK)
            
            assert metrics['total_requests'] == 3
            assert metrics['successful_requests'] == 2
            assert metrics['failed_requests'] == 1
            assert metrics['success_rate'] == 2/3
    
    def test_get_all_model_metrics(self):
        """测试获取所有模型性能指标"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            metrics = service.get_model_metrics()
            
            assert 'deepseek' in metrics
            assert 'zhipu' in metrics


class TestModelManagement:
    """测试模型管理"""
    
    def test_set_primary_model(self):
        """测试设置主模型"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key'
        }, clear=False):
            service = AIService()
            
            service.set_primary_model(AIModelType.ZHIPU)
            assert service._primary_model == AIModelType.ZHIPU
    
    def test_set_invalid_primary_model(self):
        """测试设置无效的主模型"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key'
        }, clear=False):
            service = AIService()
            
            with pytest.raises(ConfigurationError):
                service.set_primary_model(AIModelType.ZHIPU)
    
    def test_get_available_models(self):
        """测试获取可用模型列表"""
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'ZHIPU_API_KEY': 'test_zhipu_key',
            'BAICHUAN_API_KEY': 'test_baichuan_key'
        }, clear=False):
            service = AIService()
            
            models = service.get_available_models()
            
            assert len(models) == 3
            assert 'deepseek' in models
            assert 'zhipu' in models
            assert 'baichuan' in models


class TestModelMetrics:
    """测试模型性能指标"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        
        assert metrics.model_type == AIModelType.DEEPSEEK
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_duration_ms == 0.0
    
    def test_metrics_update_success(self):
        """测试更新成功指标"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(True, 500.0)
        
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.average_duration_ms == 500.0
    
    def test_metrics_update_failure(self):
        """测试更新失败指标"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(False, 600.0)
        
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.average_duration_ms == 600.0
    
    def test_metrics_calculate_average(self):
        """测试计算平均持续时间"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(True, 500.0)
        metrics.update(True, 600.0)
        metrics.update(True, 700.0)
        
        assert metrics.average_duration_ms == 600.0
    
    def test_metrics_success_rate(self):
        """测试计算成功率"""
        from bilingual_tutor.services.ai_service import ModelPerformanceMetrics
        
        metrics = ModelPerformanceMetrics(AIModelType.DEEPSEEK)
        metrics.update(True, 500.0)
        metrics.update(True, 600.0)
        metrics.update(False, 700.0)
        
        assert metrics.get_success_rate() == 2/3
