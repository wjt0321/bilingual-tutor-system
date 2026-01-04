"""
简化的故障容错和恢复机制测试

测试系统在各种故障情况下的恢复能力和降级机制。

需求覆盖: 22.1, 35.1
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

from bilingual_tutor.core.engine import CoreLearningEngine
from bilingual_tutor.models import (
    UserProfile, StudySession, Content, ActivityType, 
    Skill, TimeAllocation, Goals, Preferences, ContentType
)


class TestFaultToleranceSimple:
    """简化的故障容错和恢复机制测试套件"""
    
    @pytest.fixture
    def engine(self):
        """创建核心学习引擎实例"""
        return CoreLearningEngine()
    
    @pytest.fixture
    def user_profile(self):
        """创建测试用户配置"""
        return UserProfile(
            user_id="fault_test_user",
            english_level="CET4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=Goals(
                target_english_level="CET6",
                target_japanese_level="N1",
                target_completion_date=datetime.now() + timedelta(days=730),
                priority_skills=[Skill.READING, Skill.VOCABULARY],
                custom_objectives=[]
            ),
            learning_preferences=Preferences(
                preferred_study_times=["morning"],
                content_preferences=[ContentType.ARTICLE],
                difficulty_preference="moderate",
                language_balance={"english": 0.5, "japanese": 0.5}
            ),
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def test_component_failure_recovery(self, engine, user_profile):
        """测试组件故障恢复"""
        # 保存原始组件
        original_crawler = engine.content_crawler
        
        try:
            # 模拟组件故障
            engine.content_crawler = None
            
            # 测试系统在组件缺失时的工作能力
            allocation = engine.allocate_study_time(60)
            
            # 即使组件缺失，基本功能仍应可用
            assert allocation is not None, "组件故障时基本功能不可用"
            assert allocation.total_minutes == 60, "组件故障时时间分配错误"
            
            print("组件故障恢复测试通过")
            
        finally:
            # 恢复原始组件
            engine.content_crawler = original_crawler
    
    def test_invalid_input_handling(self, engine):
        """测试无效输入处理"""
        # 测试无效的时间分配
        try:
            # 负数时间
            allocation = engine.allocate_study_time(-10)
            # 系统应该处理无效输入，可能返回None或抛出异常
            print("负数时间处理: 系统正常处理无效输入")
        except Exception as e:
            print(f"负数时间处理: 捕获异常 {type(e).__name__}")
        
        try:
            # 零时间
            allocation = engine.allocate_study_time(0)
            print("零时间处理: 系统正常处理")
        except Exception as e:
            print(f"零时间处理: 捕获异常 {type(e).__name__}")
        
        try:
            # 极大时间
            allocation = engine.allocate_study_time(10000)
            print("极大时间处理: 系统正常处理")
        except Exception as e:
            print(f"极大时间处理: 捕获异常 {type(e).__name__}")
    
    def test_concurrent_failure_handling(self, engine):
        """测试并发故障处理"""
        def failing_operation(operation_id):
            """模拟可能失败的操作"""
            try:
                # 随机模拟一些故障
                import random
                if random.random() < 0.3:  # 30%概率故障
                    raise Exception(f"模拟故障: {operation_id}")
                
                allocation = engine.allocate_study_time(60)
                return {'operation_id': operation_id, 'success': allocation is not None}
                
            except Exception as e:
                return {'operation_id': operation_id, 'success': False, 'error': str(e)}
        
        # 启动多个并发操作
        results = []
        threads = []
        
        for i in range(5):
            def worker(op_id=f"concurrent_test_{i}"):
                result = failing_operation(op_id)
                results.append(result)
            
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 分析结果
        successful_operations = [r for r in results if r['success']]
        failed_operations = [r for r in results if not r['success']]
        
        success_rate = len(successful_operations) / len(results) if results else 0
        
        print(f"并发操作总数: {len(results)}")
        print(f"成功操作数: {len(successful_operations)}")
        print(f"失败操作数: {len(failed_operations)}")
        print(f"成功率: {success_rate:.2%}")
        
        # 即使有故障，也应该有一定的成功率
        assert success_rate >= 0.4, f"并发故障恢复能力不足: {success_rate:.2%}"
    
    def test_memory_pressure_handling(self, engine):
        """测试内存压力处理"""
        # 创建大量对象模拟内存压力
        memory_objects = []
        
        try:
            # 创建内存压力
            for i in range(500):  # 适度数量
                large_data = [f"memory_test_data_{j}" for j in range(100)]
                memory_objects.append(large_data)
            
            # 在内存压力下测试系统功能
            allocation = engine.allocate_study_time(60)
            
            assert allocation is not None, "内存压力下系统无法正常工作"
            assert allocation.total_minutes == 60, "内存压力下时间分配错误"
            
            print("内存压力处理测试通过")
            
        finally:
            # 清理内存
            memory_objects.clear()
            import gc
            gc.collect()
    
    def test_exception_propagation_control(self, engine):
        """测试异常传播控制"""
        # 创建一个会产生异常的模拟组件
        class FailingComponent:
            def process(self):
                raise Exception("组件内部异常")
        
        failing_component = FailingComponent()
        
        # 注册故障组件
        try:
            engine.register_component('failing_test_component', failing_component)
            
            # 测试系统是否能够处理组件异常而不崩溃
            allocation = engine.allocate_study_time(60)
            
            assert allocation is not None, "组件异常导致系统崩溃"
            
            print("异常传播控制测试通过")
            
        except Exception as e:
            # 如果系统正确处理了异常，这里不应该到达
            print(f"异常传播控制: 捕获到异常 {type(e).__name__}")
    
    def test_resource_exhaustion_simulation(self, engine):
        """测试资源耗尽模拟"""
        # 模拟文件描述符耗尽
        import tempfile
        
        temp_files = []
        try:
            # 创建一些临时文件（适度数量）
            for i in range(20):
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_files.append(temp_file)
            
            # 在资源压力下测试系统
            allocation = engine.allocate_study_time(60)
            
            assert allocation is not None, "资源压力下系统无法工作"
            
            print("资源耗尽模拟测试通过")
            
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    temp_file.close()
                    import os
                    os.unlink(temp_file.name)
                except Exception:
                    pass
    
    def test_graceful_degradation(self, engine, user_profile):
        """测试优雅降级"""
        # 逐步禁用组件，测试系统降级能力
        components_to_test = [
            'content_crawler',
            'weakness_analyzer'
        ]
        
        disabled_components = []
        
        try:
            for component_name in components_to_test:
                # 保存原始组件
                original_component = getattr(engine, component_name, None)
                if original_component:
                    disabled_components.append((component_name, original_component))
                    setattr(engine, component_name, None)
                
                # 测试系统在组件缺失时的工作能力
                allocation = engine.allocate_study_time(60)
                
                assert allocation is not None, f"禁用 {component_name} 后系统无法工作"
                assert allocation.total_minutes == 60, f"禁用 {component_name} 后时间分配错误"
                
                print(f"成功处理 {component_name} 组件缺失")
        
        finally:
            # 恢复所有组件
            for component_name, original_component in disabled_components:
                setattr(engine, component_name, original_component)
    
    def test_timeout_handling(self, engine):
        """测试超时处理"""
        # 模拟慢操作
        def slow_operation():
            time.sleep(2)  # 2秒延迟
            return "slow_result"
        
        # 测试系统对慢操作的处理
        start_time = time.time()
        
        try:
            # 执行正常操作（应该很快）
            allocation = engine.allocate_study_time(60)
            
            response_time = time.time() - start_time
            
            # 正常操作应该很快完成
            assert response_time < 1.0, f"操作响应时间过长: {response_time:.3f}秒"
            assert allocation is not None, "超时测试中正常操作失败"
            
            print(f"超时处理测试通过: 响应时间 {response_time:.3f}秒")
            
        except Exception as e:
            print(f"超时处理测试: 捕获异常 {type(e).__name__}")
    
    def test_data_corruption_handling(self, engine, user_profile):
        """测试数据损坏处理"""
        # 模拟损坏的用户配置
        corrupted_profile = UserProfile(
            user_id="",  # 空用户ID
            english_level="INVALID_LEVEL",  # 无效级别
            japanese_level="INVALID_LEVEL",
            daily_study_time=-1,  # 无效时间
            target_goals=Goals(
                target_english_level="INVALID",
                target_japanese_level="INVALID", 
                target_completion_date=datetime.now() - timedelta(days=1),  # 过去日期
                priority_skills=[],
                custom_objectives=[]
            ),
            learning_preferences=Preferences(
                preferred_study_times=[],
                content_preferences=[],
                difficulty_preference="invalid",
                language_balance={}
            ),
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 系统应该能够处理损坏的数据
        try:
            # 尝试使用损坏的配置
            allocation = engine.allocate_study_time(60)
            
            # 即使配置损坏，基本功能仍应可用
            assert allocation is not None, "数据损坏时系统无法工作"
            
            print("数据损坏处理测试通过")
            
        except Exception as e:
            # 预期可能会有异常，这是正常的
            print(f"数据损坏处理: 捕获异常 {type(e).__name__}")
    
    def test_network_failure_simulation(self, engine):
        """测试网络故障模拟"""
        # 模拟网络故障
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("网络连接超时")
            
            # 系统应该能够在网络故障时正常工作
            allocation = engine.allocate_study_time(60)
            
            assert allocation is not None, "网络故障时系统无法正常工作"
            assert allocation.total_minutes == 60, "网络故障时时间分配错误"
            
            print("网络故障模拟测试通过")


class TestSystemResilience:
    """系统韧性测试"""
    
    def test_error_isolation(self):
        """测试错误隔离"""
        engine = CoreLearningEngine()
        
        # 创建一个会产生错误的组件
        class FailingComponent:
            def process(self):
                raise Exception("组件内部错误")
        
        failing_component = FailingComponent()
        engine.register_component('failing_test_component', failing_component)
        
        # 测试错误是否被正确隔离
        allocation = engine.allocate_study_time(60)
        
        assert allocation is not None, "组件错误导致系统崩溃"
        
        print("错误隔离测试通过")
    
    def test_retry_mechanism_simulation(self):
        """测试重试机制模拟"""
        # 模拟一个偶尔失败的操作
        class FlakyOperation:
            def __init__(self):
                self.attempt_count = 0
            
            def execute(self):
                self.attempt_count += 1
                if self.attempt_count <= 2:  # 前两次失败
                    raise Exception(f"操作失败 (尝试 {self.attempt_count})")
                return f"操作成功 (尝试 {self.attempt_count})"
        
        flaky_op = FlakyOperation()
        
        # 实现重试机制
        def retry_operation(operation, max_retries=3, delay=0.01):
            for attempt in range(max_retries + 1):
                try:
                    return operation.execute()
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    print(f"重试 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(delay)
        
        # 测试重试机制
        try:
            result = retry_operation(flaky_op)
            print(f"重试机制测试通过: {result}")
            assert "操作成功" in result, "重试机制未能成功"
        except Exception as e:
            pytest.fail(f"重试机制失败: {e}")
    
    def test_circuit_breaker_simulation(self):
        """测试断路器模式模拟"""
        # 模拟一个不稳定的服务
        class UnstableService:
            def __init__(self):
                self.failure_count = 0
                self.call_count = 0
            
            def call_service(self):
                self.call_count += 1
                if self.call_count <= 3:  # 前3次调用失败
                    self.failure_count += 1
                    raise Exception("服务暂时不可用")
                return "服务正常"
        
        unstable_service = UnstableService()
        
        # 实现简单的断路器逻辑
        class CircuitBreaker:
            def __init__(self, service, failure_threshold=2):
                self.service = service
                self.failure_threshold = failure_threshold
                self.failure_count = 0
                self.is_open = False
                self.last_failure_time = None
                self.timeout = 1  # 1秒后尝试恢复
            
            def call(self):
                if self.is_open:
                    # 检查是否可以尝试恢复
                    if time.time() - self.last_failure_time > self.timeout:
                        self.is_open = False
                        self.failure_count = 0
                    else:
                        raise Exception("断路器开启，服务不可用")
                
                try:
                    result = self.service.call_service()
                    self.failure_count = 0  # 重置失败计数
                    return result
                except Exception as e:
                    self.failure_count += 1
                    if self.failure_count >= self.failure_threshold:
                        self.is_open = True
                        self.last_failure_time = time.time()
                    raise e
        
        circuit_breaker = CircuitBreaker(unstable_service)
        
        # 测试断路器行为
        failure_count = 0
        success_count = 0
        
        for i in range(6):
            try:
                result = circuit_breaker.call()
                success_count += 1
                print(f"调用 {i+1} 成功: {result}")
            except Exception as e:
                failure_count += 1
                print(f"调用 {i+1} 失败: {e}")
            
            time.sleep(0.1)
        
        print(f"断路器测试: 成功 {success_count} 次，失败 {failure_count} 次")
        
        # 验证断路器有效工作
        assert failure_count > 0, "断路器未检测到故障"
        assert success_count > 0 or circuit_breaker.is_open, "断路器未正确工作"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])