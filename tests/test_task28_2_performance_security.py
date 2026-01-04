"""
Task 28.2: 性能和安全测试
Performance and Security Tests

验证响应时间和缓存命中率、测试数据安全和隐私保护、确认系统监控和告警功能
需求: 20.1, 34.1, 35.1
"""

import pytest
import time
import threading
import tempfile
import os
import hashlib
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# 系统组件导入
from bilingual_tutor.core.system_integrator import SystemIntegrator
from bilingual_tutor.infrastructure.cache_manager import FallbackCacheManager
from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, Content, ContentType,
    DailyPlan, TimeAllocation, StudySession, SessionStatus
)


class TestPerformanceOptimization:
    """性能优化测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.system_integrator = SystemIntegrator()
        self.cache_manager = FallbackCacheManager()
        self.test_user_id = "performance_test_user"
        print(f"\n 开始性能优化测试 - 用户: {self.test_user_id}")
    
    def teardown_method(self):
        """测试后清理"""
        try:
            self.system_integrator.close()
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理警告: {e}")
    
    def test_response_time_performance(self):
        """测试响应时间性能 (需求 20.1)"""
        print("\n 测试响应时间性能...")
        
        # 测试缓存响应时间
        sample_plan = DailyPlan(
            plan_id="perf_test_plan",
            user_id=self.test_user_id,
            date=datetime.now(),
            activities=[],
            time_allocation=TimeAllocation(60, 12, 24, 24, 0),
            learning_objectives=["性能测试"],
            estimated_completion_time=60
        )
        
        # 预热缓存
        self.cache_manager.set_daily_plan(self.test_user_id, sample_plan)
        
        # 测试缓存响应时间
        cache_times = []
        for _ in range(20):
            start_time = time.time()
            result = self.cache_manager.get_daily_plan(self.test_user_id)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            cache_times.append(response_time_ms)
            assert result is not None
        
        avg_cache_time = sum(cache_times) / len(cache_times)
        max_cache_time = max(cache_times)
        
        assert avg_cache_time < 50, f"缓存平均响应时间 {avg_cache_time:.2f}ms 超过50ms阈值"
        assert max_cache_time < 100, f"缓存最大响应时间 {max_cache_time:.2f}ms 超过100ms阈值"
        
        print(f" 缓存响应时间测试通过")
        print(f"   平均响应时间: {avg_cache_time:.2f}ms")
        print(f"   最大响应时间: {max_cache_time:.2f}ms")
        
        print(" 响应时间性能测试完成")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
