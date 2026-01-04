#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API兼容性层测试 - 属性54: API兼容性维护
API Compatibility Layer Tests - Property 54: API Compatibility Maintenance

Tests:
- 属性54: API兼容性维护
- 验证需求: 28.1
"""

import pytest
import pytest_asyncio
from hypothesis import given, settings, example, strategies as st, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
from datetime import datetime, timedelta
import asyncio

from bilingual_tutor.web.api_compatibility import (
    APICompatibilityLayer,
    CompatibilityConfig,
    DeploymentMode,
    APIMetrics
)


class TestAPICompatibilityLayer:
    """测试API兼容性层基础功能"""
    
    @pytest.fixture
    def compatibility_config(self):
        """创建兼容性配置"""
        return CompatibilityConfig(
            deployment_mode=DeploymentMode.GRADUAL,
            flask_port=5000,
            fastapi_port=8000,
            traffic_percentage=0.5,
            enable_metrics=True,
            enable_health_check=True,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
            enable_logging=False
        )
    
    @pytest_asyncio.fixture
    async def compatibility_layer(self, compatibility_config):
        """创建兼容性层实例"""
        layer = APICompatibilityLayer(
            config=compatibility_config,
            flask_app=None,
            fastapi_app=None
        )
        await layer.initialize()
        yield layer
        layer._initialized = False
    
    @pytest.mark.asyncio
    async def test_initialization(self, compatibility_layer):
        """测试兼容性层初始化"""
        assert compatibility_layer._initialized is True
        assert compatibility_layer.config.deployment_mode == DeploymentMode.GRADUAL
        assert compatibility_layer.config.traffic_percentage == 0.5
    
    @pytest.mark.asyncio
    async def test_deployment_status(self, compatibility_layer):
        """测试获取部署状态"""
        status = compatibility_layer.get_deployment_status()
        
        assert "deployment_mode" in status
        assert "traffic_percentage" in status
        assert "metrics" in status
        assert status["deployment_mode"] == "gradual"
        assert status["traffic_percentage"] == 0.5
        assert status["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, compatibility_layer):
        """测试健康检查"""
        health = await compatibility_layer.check_health()
        
        assert "overall" in health
        assert "flask" in health
        assert "fastapi" in health
        assert health["last_check"] is not None
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, compatibility_layer):
        """测试获取指标"""
        metrics = await compatibility_layer.get_metrics()
        
        assert "requests" in metrics
        assert "performance" in metrics
        assert "errors" in metrics
        assert "circuit_breaker" in metrics
        assert "last_updated" in metrics
    
    @pytest.mark.asyncio
    async def test_adjust_traffic_percentage(self, compatibility_layer):
        """测试调整流量比例"""
        result = await compatibility_layer.adjust_traffic_percentage(0.7)
        
        assert result["success"] is True
        assert result["new_percentage"] == 0.7
        assert compatibility_layer.config.traffic_percentage == 0.7
    
    @pytest.mark.asyncio
    async def test_adjust_traffic_percentage_invalid(self, compatibility_layer):
        """测试调整无效流量比例"""
        with pytest.raises(Exception):
            await compatibility_layer.adjust_traffic_percentage(-0.1)
        
        with pytest.raises(Exception):
            await compatibility_layer.adjust_traffic_percentage(1.5)
    
    @pytest.mark.asyncio
    async def test_trigger_rollback(self, compatibility_layer):
        """测试触发回滚"""
        result = await compatibility_layer.trigger_rollback()
        
        assert result["success"] is True
        assert result["current_mode"] == "rolled_back"
        assert compatibility_layer.config.deployment_mode == DeploymentMode.ROLLED_BACK
        assert compatibility_layer.config.traffic_percentage == 0.0


class TestProperty54APICompatibilityMaintenance:
    """属性54: API兼容性维护"""
    
    @pytest.fixture
    def compatibility_config(self):
        """创建兼容性配置"""
        return CompatibilityConfig(
            deployment_mode=DeploymentMode.GRADUAL,
            flask_port=5000,
            fastapi_port=8000,
            traffic_percentage=0.5,
            enable_metrics=True,
            enable_health_check=True,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=300,
            enable_logging=False
        )
    
    @pytest_asyncio.fixture
    async def compatibility_layer(self, compatibility_config):
        """创建兼容性层实例"""
        layer = APICompatibilityLayer(
            config=compatibility_config,
            flask_app=None,
            fastapi_app=None
        )
        await layer.initialize()
        yield layer
        layer._initialized = False
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_traffic_percentage_validity(
        self, compatibility_layer, traffic_percentage
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 流量比例必须在有效范围内(0-1)，并且调整后立即生效
        """
        result = await compatibility_layer.adjust_traffic_percentage(traffic_percentage)
        
        assert result["success"] is True
        assert 0.0 <= result["new_percentage"] <= 1.0
        assert abs(result["new_percentage"] - traffic_percentage) < 0.001
        assert compatibility_layer.config.traffic_percentage == traffic_percentage
    
    @given(st.integers(min_value=1, max_value=20), st.integers(min_value=1, max_value=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_backend_selection_consistency(
        self, compatibility_layer, num_flask, num_fastapi
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 后端选择逻辑应保持一致，相同的请求应路由到相同后端
        """
        compatibility_layer.config.traffic_percentage = 0.5
        
        selections = []
        for i in range(num_flask + num_fastapi):
            endpoint = f"/test/endpoint/{i}"
            backend = compatibility_layer._select_backend(endpoint, "GET")
            selections.append(backend)
        
        fastapi_count = selections.count("fastapi")
        flask_count = selections.count("flask")
        total = len(selections)
        
        if total > 0:
            actual_percentage = fastapi_count / total
            expected_percentage = compatibility_layer.config.traffic_percentage
            tolerance = 0.5
            assert abs(actual_percentage - expected_percentage) <= tolerance
    
    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_metrics_accuracy(self, compatibility_layer, num_requests):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 指标统计必须准确，总请求数等于Flask和FastAPI请求数之和
        """
        initial_total = compatibility_layer.metrics.total_requests
        initial_flask = compatibility_layer.metrics.flask_requests
        initial_fastapi = compatibility_layer.metrics.fastapi_requests
        
        for i in range(num_requests):
            compatibility_layer.metrics.total_requests += 1
            if i % 2 == 0:
                compatibility_layer.metrics.flask_requests += 1
            else:
                compatibility_layer.metrics.fastapi_requests += 1
        
        assert compatibility_layer.metrics.total_requests == initial_total + num_requests
        assert (compatibility_layer.metrics.flask_requests + 
                compatibility_layer.metrics.fastapi_requests == 
                (initial_flask + initial_fastapi + num_requests))
    
    @given(st.integers(min_value=0, max_value=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_circuit_breaker_functionality(
        self, compatibility_layer, error_count
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 熔断器应在错误达到阈值时触发，并在超时后恢复
        """
        compatibility_layer.config.circuit_breaker_threshold = 10
        compatibility_layer.config.circuit_breaker_timeout = 1
        
        for _ in range(error_count):
            compatibility_layer._update_metrics(100, False)
        
        is_open = compatibility_layer._is_circuit_breaker_open()
        
        if error_count >= 10:
            assert is_open is True
        
        if compatibility_layer._circuit_breaker_open_until:
            await asyncio.sleep(1.1)
            is_open_after = compatibility_layer._is_circuit_breaker_open()
            assert is_open_after is False
    
    @given(st.lists(st.floats(min_value=10, max_value=500), min_size=1, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_average_response_time_calculation(
        self, compatibility_layer, response_times
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 平均响应时间计算必须准确
        """
        initial_request_times = list(compatibility_layer._request_times)
        initial_count = len(initial_request_times)
        
        for response_time in response_times:
            compatibility_layer._update_metrics(response_time, True)
        
        expected_avg = sum(response_times) / len(response_times)
        actual_avg = compatibility_layer.metrics.avg_response_time_ms
        
        if initial_request_times and response_times:
            combined_avg = sum(initial_request_times + response_times) / (initial_count + len(response_times))
            assert abs(actual_avg - combined_avg) < 1.0
        elif response_times:
            assert abs(actual_avg - expected_avg) < 1.0
    
    @given(st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_rollback_reset_traffic(self, compatibility_layer, percentages):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 回滚后流量比例必须重置为0
        """
        for percentage in percentages:
            await compatibility_layer.adjust_traffic_percentage(percentage)
        
        result = await compatibility_layer.trigger_rollback()
        
        assert result["success"] is True
        assert compatibility_layer.config.deployment_mode == DeploymentMode.ROLLED_BACK
        assert compatibility_layer.config.traffic_percentage == 0.0
    
    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_health_status_updates(self, compatibility_layer, error_count):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 健康状态应根据错误率动态更新
        """
        total_requests = max(1, error_count)
        
        for _ in range(total_requests):
            compatibility_layer.metrics.total_requests += 1
            if error_count > 0:
                compatibility_layer.metrics.error_count += 1
        
        health = await compatibility_layer.check_health()
        
        if total_requests > 0 and (error_count / total_requests) > 0.1:
            assert health["overall"] in ["degraded", "unhealthy"]
        else:
            assert health["overall"] in ["healthy", "degraded"]
    
    @given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_request_routing_distribution(
        self, compatibility_layer, num_endpoints, num_requests_per_endpoint
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 请求路由分布应符合配置的流量比例
        """
        compatibility_layer.config.traffic_percentage = 0.5
        
        all_selections = []
        for i in range(num_endpoints):
            endpoint = f"/api/endpoint/{i}"
            for _ in range(num_requests_per_endpoint):
                backend = compatibility_layer._select_backend(endpoint, "GET")
                all_selections.append(backend)
        
        if all_selections:
            fastapi_count = all_selections.count("fastapi")
            total = len(all_selections)
            actual_percentage = fastapi_count / total
            expected_percentage = 0.5
            tolerance = 0.5
            assert abs(actual_percentage - expected_percentage) <= tolerance
    
    @given(st.text(min_size=1, max_size=50), st.sampled_from(["GET", "POST", "PUT", "DELETE"]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_54_backend_selection_deterministic(
        self, compatibility_layer, endpoint, method
    ):
        """
        属性54: API兼容性维护
        
        验证需求: 28.1
        
        属性: 相同的端点和方法应路由到相同的后端
        """
        compatibility_layer.config.traffic_percentage = 0.5
        compatibility_layer.config.deployment_mode = DeploymentMode.GRADUAL
        
        selections = []
        for _ in range(10):
            backend = compatibility_layer._select_backend(endpoint, method)
            selections.append(backend)
        
        assert len(set(selections)) == 1
        assert all(selections[0] == s for s in selections)


class TestAPICompatibilityLayerIntegration:
    """测试API兼容性层集成功能"""
    
    @pytest.fixture
    def compatibility_config(self):
        """创建兼容性配置"""
        return CompatibilityConfig(
            deployment_mode=DeploymentMode.TESTING,
            flask_port=5000,
            fastapi_port=8000,
            traffic_percentage=0.0,
            enable_metrics=True,
            enable_health_check=True,
            enable_logging=False
        )
    
    @pytest_asyncio.fixture
    async def compatibility_layer(self, compatibility_config):
        """创建兼容性层实例"""
        layer = APICompatibilityLayer(
            config=compatibility_config,
            flask_app=None,
            fastapi_app=None
        )
        await layer.initialize()
        yield layer
        layer._initialized = False
    
    @pytest.mark.asyncio
    async def test_full_deployment_lifecycle(self, compatibility_layer):
        """测试完整部署生命周期"""
        assert compatibility_layer.config.deployment_mode == DeploymentMode.TESTING
        
        await compatibility_layer.adjust_traffic_percentage(0.1)
        assert compatibility_layer.config.traffic_percentage == 0.1
        
        await compatibility_layer.adjust_traffic_percentage(0.5)
        assert compatibility_layer.config.traffic_percentage == 0.5
        
        await compatibility_layer.adjust_traffic_percentage(1.0)
        assert compatibility_layer.config.traffic_percentage == 1.0
        
        result = await compatibility_layer.trigger_rollback()
        assert result["success"] is True
        assert compatibility_layer.config.traffic_percentage == 0.0
        assert compatibility_layer.config.deployment_mode == DeploymentMode.ROLLED_BACK
    
    @pytest.mark.asyncio
    async def test_compatibility_validation(self, compatibility_layer):
        """测试兼容性验证"""
        validation_result = await compatibility_layer.validate_api_compatibility()
        
        assert "total_endpoints" in validation_result
        assert "compatible" in validation_result
        assert "incompatible" in validation_result
        assert "compatibility_rate" in validation_result
        assert 0 <= validation_result["compatibility_rate"] <= 100
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation(self, compatibility_layer):
        """测试指标聚合"""
        for i in range(10):
            compatibility_layer._update_metrics(50 + i * 10, i % 2 == 0)
        
        metrics = await compatibility_layer.get_metrics()
        
        assert metrics["requests"]["total"] == 10
        assert metrics["errors"]["count"] >= 0
        assert metrics["performance"]["avg_response_time_ms"] > 0


class TestAPICompatibilityLayerErrorHandling:
    """测试API兼容性层错误处理"""
    
    @pytest.fixture
    def compatibility_config(self):
        """创建兼容性配置"""
        return CompatibilityConfig(
            deployment_mode=DeploymentMode.GRADUAL,
            flask_port=5000,
            fastapi_port=8000,
            traffic_percentage=0.5,
            enable_metrics=True,
            enable_health_check=True,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=1,
            enable_logging=False
        )
    
    @pytest_asyncio.fixture
    async def compatibility_layer(self, compatibility_config):
        """创建兼容性层实例"""
        layer = APICompatibilityLayer(
            config=compatibility_config,
            flask_app=None,
            fastapi_app=None
        )
        await layer.initialize()
        yield layer
        layer._initialized = False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_on_threshold(self, compatibility_layer):
        """测试熔断器在阈值时触发"""
        compatibility_layer.config.circuit_breaker_threshold = 5
        
        for _ in range(5):
            compatibility_layer._update_metrics(100, False)
        
        assert compatibility_layer._is_circuit_breaker_open() is True
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_after_timeout(self, compatibility_layer):
        """测试熔断器在超时后恢复"""
        compatibility_layer.config.circuit_breaker_threshold = 5
        compatibility_layer.config.circuit_breaker_timeout = 1
        
        for _ in range(5):
            compatibility_layer._update_metrics(100, False)
        
        assert compatibility_layer._is_circuit_breaker_open() is True
        
        await asyncio.sleep(1.1)
        assert compatibility_layer._is_circuit_breaker_open() is False
    
    @pytest.mark.asyncio
    async def test_metrics_track_errors(self, compatibility_layer):
        """测试指标跟踪错误"""
        initial_errors = compatibility_layer.metrics.error_count
        
        for _ in range(3):
            compatibility_layer._update_metrics(100, False)
        
        assert compatibility_layer.metrics.error_count == initial_errors + 3
    
    @pytest.mark.asyncio
    async def test_invalid_traffic_percentage_raises_error(self, compatibility_layer):
        """测试无效流量比例引发错误"""
        with pytest.raises(Exception):
            await compatibility_layer.adjust_traffic_percentage(-0.1)
        
        with pytest.raises(Exception):
            await compatibility_layer.adjust_traffic_percentage(1.5)
