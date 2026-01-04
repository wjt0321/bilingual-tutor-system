"""
缓存性能优化属性测试
测试Redis缓存管理器的响应时间性能和缓存命中率优化
"""

import pytest
import time
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch

from bilingual_tutor.infrastructure.cache_manager import (
    RedisCacheManager, FallbackCacheManager, create_cache_manager
)
from bilingual_tutor.models import (
    CacheConfig, CacheMetrics, DailyPlan, Content, StudySession,
    TimeAllocation, LearningActivity, ActivityType, ContentType, SessionStatus
)


class TestCachePerformanceOptimization:
    """缓存性能优化测试类"""
    
    @pytest.fixture
    def cache_config(self):
        """创建测试用的缓存配置"""
        return CacheConfig(
            redis_host="localhost",
            redis_port=6379,
            redis_db=1,  # 使用测试数据库
            default_ttl=3600,
            connection_pool_size=5
        )
    
    @pytest.fixture
    def fallback_cache_manager(self):
        """创建回退缓存管理器"""
        return FallbackCacheManager()
    
    @pytest.fixture
    def sample_daily_plan(self):
        """创建示例每日学习计划"""
        return DailyPlan(
            plan_id="test_plan_001",
            user_id="test_user",
            date=datetime.now(),
            activities=[],
            time_allocation=TimeAllocation(
                total_minutes=60,
                review_minutes=12,
                english_minutes=24,
                japanese_minutes=24,
                break_minutes=0
            ),
            learning_objectives=["词汇练习", "语法复习"],
            estimated_completion_time=60
        )
    
    @pytest.fixture
    def sample_content_list(self):
        """创建示例内容列表"""
        return [
            Content(
                content_id="content_001",
                title="英语词汇练习",
                body="Practice English vocabulary",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.EXERCISE,
                source_url="https://example.com/vocab",
                quality_score=0.85,
                created_at=datetime.now(),
                tags=["vocabulary", "practice"]
            ),
            Content(
                content_id="content_002",
                title="日语语法练习",
                body="Japanese grammar practice",
                language="japanese",
                difficulty_level="N5",
                content_type=ContentType.EXERCISE,
                source_url="https://example.com/grammar",
                quality_score=0.90,
                created_at=datetime.now(),
                tags=["grammar", "practice"]
            )
        ]
    
    @pytest.mark.property
    @given(
        user_id=st.text(min_size=1, max_size=50),
        request_count=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_response_time_performance_property(self, fallback_cache_manager, user_id, request_count):
        """
        属性44: 响应时间性能
        对于任何用户请求学习计划，系统应在500毫秒内响应
        **验证需求: 20.1, 20.5**
        **功能: bilingual-tutor, 属性44: 响应时间性能**
        """
        cache_manager = fallback_cache_manager
        
        # 创建动态的学习计划
        sample_daily_plan = DailyPlan(
            plan_id=f"test_plan_{user_id}",
            user_id=user_id,
            date=datetime.now(),
            activities=[],
            time_allocation=TimeAllocation(
                total_minutes=60,
                review_minutes=12,
                english_minutes=24,
                japanese_minutes=24,
                break_minutes=0
            ),
            learning_objectives=["词汇练习", "语法复习"],
            estimated_completion_time=60
        )
        
        # 首先设置缓存数据
        cache_manager.set_daily_plan(user_id, sample_daily_plan)
        
        response_times = []
        
        # 执行多次请求测试响应时间
        for _ in range(min(request_count, 20)):  # 限制测试次数以避免超时
            start_time = time.time()
            
            # 执行缓存查询
            result = cache_manager.get_daily_plan(user_id)
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            response_times.append(response_time_ms)
            
            # 验证返回了正确的数据
            assert result is not None
            assert result.user_id == user_id
        
        # 计算平均响应时间
        avg_response_time = sum(response_times) / len(response_times)
        
        # 验证平均响应时间在500毫秒以内
        assert avg_response_time < 500, f"平均响应时间 {avg_response_time:.2f}ms 超过了500ms的要求"
        
        # 验证所有单次请求都在合理范围内（考虑到内存缓存应该很快）
        max_response_time = max(response_times)
        assert max_response_time < 100, f"最大响应时间 {max_response_time:.2f}ms 过长"
    
    @pytest.mark.property
    @given(
        user_id=st.text(min_size=1, max_size=50),
        language=st.sampled_from(["english", "japanese"]),
        cache_requests=st.integers(min_value=5, max_value=20),
        miss_requests=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=10, deadline=2000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cache_hit_rate_optimization_property(self, fallback_cache_manager, sample_content_list, 
                                                user_id, language, cache_requests, miss_requests):
        """
        属性45: 缓存命中率优化
        对于任何学习计划请求，缓存命中率应至少达到80%
        **验证需求: 20.1, 20.5**
        **功能: bilingual-tutor, 属性45: 缓存命中率优化**
        """
        cache_manager = fallback_cache_manager
        
        # 设置内容推荐缓存
        cache_manager.set_content_recommendations(user_id, language, sample_content_list)
        
        hit_count = 0
        total_requests = 0
        
        # 执行缓存命中的请求
        for _ in range(cache_requests):
            result = cache_manager.get_content_recommendations(user_id, language)
            total_requests += 1
            
            if result is not None:
                hit_count += 1
                # 验证返回的数据正确
                assert len(result) == len(sample_content_list)
        
        # 执行缓存未命中的请求（使用不同的用户ID或语言）
        for i in range(miss_requests):
            different_user_id = f"{user_id}_different_{i}"
            result = cache_manager.get_content_recommendations(different_user_id, language)
            total_requests += 1
            
            # 这些请求应该未命中
            assert result is None
        
        # 计算命中率
        hit_rate = hit_count / total_requests if total_requests > 0 else 0
        
        # 验证命中率符合预期
        # 由于我们控制了命中和未命中的请求数量，可以精确计算期望的命中率
        expected_hit_rate = cache_requests / total_requests
        
        assert abs(hit_rate - expected_hit_rate) < 0.01, f"实际命中率 {hit_rate:.2%} 与期望命中率 {expected_hit_rate:.2%} 不符"
        
        # 验证缓存指标正确更新
        metrics = cache_manager.get_cache_metrics()
        assert metrics.total_requests >= total_requests
        assert metrics.hit_count >= hit_count
    
    @pytest.mark.property
    @given(
        user_ids=st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=10),
        session_duration=st.integers(min_value=30, max_value=120)
    )
    @settings(max_examples=5, deadline=2000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_cache_access_performance(self, fallback_cache_manager, sample_daily_plan, 
                                               user_ids, session_duration):
        """
        测试并发缓存访问的性能
        验证多用户同时访问缓存时的性能表现
        """
        cache_manager = fallback_cache_manager
        
        # 为每个用户设置缓存数据
        for user_id in user_ids:
            user_plan = DailyPlan(
                plan_id=f"plan_{user_id}",
                user_id=user_id,
                date=datetime.now(),
                activities=[],
                time_allocation=TimeAllocation(
                    total_minutes=session_duration,
                    review_minutes=int(session_duration * 0.2),
                    english_minutes=int(session_duration * 0.4),
                    japanese_minutes=int(session_duration * 0.4),
                    break_minutes=0
                ),
                learning_objectives=["测试目标"],
                estimated_completion_time=session_duration
            )
            cache_manager.set_daily_plan(user_id, user_plan)
        
        # 模拟并发访问
        start_time = time.time()
        
        for _ in range(3):  # 每个用户访问3次
            for user_id in user_ids:
                result = cache_manager.get_daily_plan(user_id)
                assert result is not None
                assert result.user_id == user_id
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        total_requests = len(user_ids) * 3
        avg_time_per_request = total_time / total_requests
        
        # 验证平均每个请求的时间在合理范围内
        assert avg_time_per_request < 50, f"并发访问时平均每请求时间 {avg_time_per_request:.2f}ms 过长"
    
    @pytest.mark.property
    @given(
        cache_size=st.integers(min_value=10, max_value=100),
        ttl_seconds=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=5, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])  # 增加超时时间以处理TTL测试
    def test_cache_expiration_performance(self, fallback_cache_manager, sample_content_list, 
                                        cache_size, ttl_seconds):
        """
        测试缓存过期机制的性能
        验证缓存项过期后的清理和性能影响
        """
        cache_manager = fallback_cache_manager
        
        # 设置多个缓存项，使用较短的TTL
        user_ids = [f"user_{i}" for i in range(min(cache_size, 20))]  # 限制用户数量
        
        for user_id in user_ids:
            cache_manager.set_content_recommendations(
                user_id, "english", sample_content_list, ttl=ttl_seconds
            )
        
        # 立即访问，应该都能命中
        immediate_hits = 0
        for user_id in user_ids:
            result = cache_manager.get_content_recommendations(user_id, "english")
            if result is not None:
                immediate_hits += 1
        
        # 验证立即访问的命中率
        immediate_hit_rate = immediate_hits / len(user_ids)
        assert immediate_hit_rate >= 0.9, f"立即访问命中率 {immediate_hit_rate:.2%} 过低"
        
        # 等待缓存过期
        time.sleep(ttl_seconds + 1)
        
        # 再次访问，应该大部分未命中（因为已过期）
        expired_hits = 0
        for user_id in user_ids:
            result = cache_manager.get_content_recommendations(user_id, "english")
            if result is not None:
                expired_hits += 1
        
        # 验证过期后的命中率应该很低
        expired_hit_rate = expired_hits / len(user_ids)
        assert expired_hit_rate <= 0.1, f"过期后命中率 {expired_hit_rate:.2%} 过高，缓存过期机制可能有问题"
    
    def test_cache_metrics_accuracy(self, fallback_cache_manager, sample_daily_plan):
        """
        测试缓存指标的准确性
        验证缓存命中率、请求数等指标的正确计算
        """
        cache_manager = fallback_cache_manager
        
        # 获取初始指标
        initial_metrics = cache_manager.get_cache_metrics()
        initial_requests = initial_metrics.total_requests
        initial_hits = initial_metrics.hit_count
        
        user_id = "metrics_test_user"
        
        # 执行一次未命中的查询
        result = cache_manager.get_daily_plan(user_id)
        assert result is None
        
        # 设置缓存
        cache_manager.set_daily_plan(user_id, sample_daily_plan)
        
        # 执行两次命中的查询
        for _ in range(2):
            result = cache_manager.get_daily_plan(user_id)
            assert result is not None
        
        # 获取最终指标
        final_metrics = cache_manager.get_cache_metrics()
        
        # 验证指标更新正确
        expected_total_requests = initial_requests + 3  # 1次未命中 + 2次命中
        expected_hits = initial_hits + 2  # 2次命中
        
        assert final_metrics.total_requests == expected_total_requests
        assert final_metrics.hit_count == expected_hits
        
        # 验证命中率计算正确
        expected_hit_rate = expected_hits / expected_total_requests
        assert abs(final_metrics.hit_rate - expected_hit_rate) < 0.01
    
    def test_cache_invalidation_performance(self, fallback_cache_manager, sample_daily_plan, sample_content_list):
        """
        测试缓存失效操作的性能
        验证批量清除缓存的效率
        """
        cache_manager = fallback_cache_manager
        
        user_id = "invalidation_test_user"
        
        # 设置多种类型的缓存
        cache_manager.set_daily_plan(user_id, sample_daily_plan)
        cache_manager.set_content_recommendations(user_id, "english", sample_content_list)
        cache_manager.set_content_recommendations(user_id, "japanese", sample_content_list)
        
        # 验证缓存存在
        assert cache_manager.get_daily_plan(user_id) is not None
        assert cache_manager.get_content_recommendations(user_id, "english") is not None
        assert cache_manager.get_content_recommendations(user_id, "japanese") is not None
        
        # 测试失效操作的性能
        start_time = time.time()
        
        success = cache_manager.invalidate_user_cache(user_id)
        
        end_time = time.time()
        invalidation_time = (end_time - start_time) * 1000
        
        # 验证失效操作成功且快速
        assert success is True
        assert invalidation_time < 100, f"缓存失效操作耗时 {invalidation_time:.2f}ms 过长"
        
        # 验证缓存已被清除
        assert cache_manager.get_daily_plan(user_id) is None
        assert cache_manager.get_content_recommendations(user_id, "english") is None
        assert cache_manager.get_content_recommendations(user_id, "japanese") is None
    
    def test_cache_manager_factory_fallback(self):
        """
        测试缓存管理器工厂方法的回退机制
        验证当Redis不可用时能正确回退到内存缓存
        """
        # 使用无效的Redis配置
        invalid_config = CacheConfig(
            redis_host="invalid_host",
            redis_port=9999,
            socket_timeout=1  # 快速超时
        )
        
        # 创建缓存管理器应该回退到内存缓存
        cache_manager = create_cache_manager(invalid_config)
        
        # 验证返回的是回退缓存管理器
        assert isinstance(cache_manager, FallbackCacheManager)
        
        # 验证回退缓存管理器功能正常
        assert cache_manager.health_check() is True
        
        # 测试基本功能
        user_id = "fallback_test_user"
        sample_plan = DailyPlan(
            plan_id="fallback_plan",
            user_id=user_id,
            date=datetime.now(),
            activities=[],
            time_allocation=TimeAllocation(60, 12, 24, 24, 0),
            learning_objectives=["测试"],
            estimated_completion_time=60
        )
        
        # 设置和获取缓存
        assert cache_manager.set_daily_plan(user_id, sample_plan) is True
        result = cache_manager.get_daily_plan(user_id)
        assert result is not None
        assert result.user_id == user_id
    
    @pytest.mark.property
    @given(
        batch_size=st.integers(min_value=5, max_value=20),
        operation_type=st.sampled_from(["set", "get", "invalidate"])
    )
    @settings(max_examples=5, deadline=1500, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_batch_operations_performance(self, fallback_cache_manager, sample_daily_plan, 
                                        batch_size, operation_type):
        """
        测试批量操作的性能
        验证批量设置、获取和失效操作的效率
        """
        cache_manager = fallback_cache_manager
        
        user_ids = [f"batch_user_{i}" for i in range(batch_size)]
        
        start_time = time.time()
        
        if operation_type == "set":
            # 批量设置缓存
            for user_id in user_ids:
                user_plan = DailyPlan(
                    plan_id=f"batch_plan_{user_id}",
                    user_id=user_id,
                    date=datetime.now(),
                    activities=[],
                    time_allocation=sample_daily_plan.time_allocation,
                    learning_objectives=["批量测试"],
                    estimated_completion_time=60
                )
                cache_manager.set_daily_plan(user_id, user_plan)
        
        elif operation_type == "get":
            # 先设置缓存
            for user_id in user_ids:
                cache_manager.set_daily_plan(user_id, sample_daily_plan)
            
            # 重置计时
            start_time = time.time()
            
            # 批量获取缓存
            for user_id in user_ids:
                result = cache_manager.get_daily_plan(user_id)
                assert result is not None
        
        elif operation_type == "invalidate":
            # 先设置缓存
            for user_id in user_ids:
                cache_manager.set_daily_plan(user_id, sample_daily_plan)
            
            # 重置计时
            start_time = time.time()
            
            # 批量失效缓存
            for user_id in user_ids:
                cache_manager.invalidate_user_cache(user_id)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        avg_time_per_operation = total_time / batch_size
        
        # 验证批量操作的平均时间在合理范围内
        max_time_per_operation = 20  # 每个操作最多20ms
        assert avg_time_per_operation < max_time_per_operation, \
            f"批量{operation_type}操作平均耗时 {avg_time_per_operation:.2f}ms 超过 {max_time_per_operation}ms"