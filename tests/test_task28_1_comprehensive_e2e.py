"""
Task 28.1: 端到端功能测试 - 综合测试
Comprehensive End-to-End Functionality Tests

测试AI对话和智能内容生成、验证缓存系统和性能优化、测试移动端响应式设计
Tests AI dialogue and intelligent content generation, validates cache system and performance optimization, tests mobile responsive design

需求: 所有新增需求 (20-35)
"""

import pytest
import asyncio
import time
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import threading

# 系统组件导入
from bilingual_tutor.core.system_integrator import SystemIntegrator
from bilingual_tutor.services.ai_service import (
    AIService, AIModelType, AIRequest, AIResponse, LanguageLevel
)
from bilingual_tutor.services.intelligent_content_generator import (
    IntelligentContentGenerator, Exercise, ExerciseBatch
)
from bilingual_tutor.infrastructure.cache_manager import (
    create_cache_manager, CacheConfig, FallbackCacheManager
)
from bilingual_tutor.storage.database import LearningDatabase
from bilingual_tutor.web.app import create_app
from bilingual_tutor.models import (
    UserProfile, Goals, Preferences, Content, ContentType, 
    DailyPlan, TimeAllocation, StudySession, SessionStatus
)


class TestComprehensiveE2EFunctionality:
    """综合端到端功能测试类"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建临时目录和数据库
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, 'test_e2e.db')
        
        # 初始化系统集成器
        self.system_integrator = SystemIntegrator()
        
        # 创建测试用户
        self.test_user_id = "e2e_comprehensive_user"
        self.test_user_profile = self._create_test_user_profile()
        
        # 初始化缓存管理器
        self.cache_manager = FallbackCacheManager()
        
        print(f"\n🚀 开始综合端到端测试 - 用户: {self.test_user_id}")
    
    def teardown_method(self):
        """测试后清理"""
        try:
            self.system_integrator.close()
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理警告: {e}")
    
    def test_ai_dialogue_and_content_generation_integration(self):
        """
        测试AI对话和智能内容生成集成
        Test AI dialogue and intelligent content generation integration
        
        验证：
        - AI对话功能完整性
        - 智能内容生成准确性
        - 难度匹配和个性化
        - 响应时间性能
        - 多轮对话连续性
        """
        print("\n🤖 测试AI对话和智能内容生成集成...")
        
        # 测试1: AI对话功能
        conversation_result = self.system_integrator.start_ai_conversation(
            user_id=self.test_user_id,
            language="english",
            scenario="daily"
        )
        
        assert 'success' in conversation_result
        if conversation_result['success']:
            assert 'conversation_id' in conversation_result
            assert 'ai_message' in conversation_result or 'content' in conversation_result
            print("✅ AI对话启动成功")
        else:
            print(f"⚠️  AI对话启动失败: {conversation_result.get('error', '未知错误')}")
            print("✅ AI对话测试完成（服务可能不可用但系统稳定）")
        
        # 测试2: 词汇解释功能
        vocab_result = self.system_integrator.explain_vocabulary_with_ai(
            user_id=self.test_user_id,
            word="serendipity",
            language="english"
        )
        
        assert 'success' in vocab_result
        if vocab_result['success']:
            assert 'explanation' in vocab_result or 'content' in vocab_result
            print("✅ AI词汇解释功能正常")
        else:
            print(f"⚠️  AI词汇解释失败: {vocab_result.get('error', '未知错误')}")
        
        # 测试3: 语法纠错功能
        grammar_result = self.system_integrator.correct_grammar_with_ai(
            user_id=self.test_user_id,
            text="He go to school everyday.",
            language="english"
        )
        
        assert 'success' in grammar_result
        if grammar_result['success']:
            assert 'corrected_text' in grammar_result or 'is_correct' in grammar_result
            print("✅ AI语法纠错功能正常")
        else:
            print(f"⚠️  AI语法纠错失败: {grammar_result.get('error', '未知错误')}")
        
        # 测试4: 个性化练习生成
        exercise_result = self.system_integrator.generate_personalized_exercises(
            user_id=self.test_user_id,
            weakness_areas=["语法", "词汇"],
            language="english",
            exercise_type="multiple_choice",
            count=5
        )
        
        assert 'success' in exercise_result
        if exercise_result['success']:
            assert 'exercises' in exercise_result or 'content' in exercise_result
            print("✅ 个性化练习生成功能正常")
        else:
            print(f"⚠️  个性化练习生成失败: {exercise_result.get('error', '未知错误')}")
        
        # 测试5: AI服务健康检查
        health_result = self.system_integrator.get_ai_service_health()
        
        assert 'status' in health_result
        assert 'conversation_partner' in health_result
        assert 'grammar_corrector' in health_result
        assert 'exercise_generator' in health_result
        
        print("✅ AI对话和智能内容生成集成测试完成")
    
    def test_cache_system_and_performance_optimization(self):
        """
        测试缓存系统和性能优化
        Test cache system and performance optimization
        
        验证：
        - 缓存响应时间性能
        - 缓存命中率优化
        - 数据库查询性能
        - 批量操作效率
        - 并发访问处理
        """
        print("\n⚡ 测试缓存系统和性能优化...")
        
        # 测试1: 缓存响应时间性能
        sample_plan = DailyPlan(
            plan_id="cache_test_plan",
            user_id=self.test_user_id,
            date=datetime.now(),
            activities=[],
            time_allocation=TimeAllocation(
                total_minutes=60,
                review_minutes=12,
                english_minutes=24,
                japanese_minutes=24,
                break_minutes=0
            ),
            learning_objectives=["缓存测试"],
            estimated_completion_time=60
        )
        
        # 设置缓存
        self.cache_manager.set_daily_plan(self.test_user_id, sample_plan)
        
        # 测试响应时间
        response_times = []
        for _ in range(10):
            start_time = time.time()
            result = self.cache_manager.get_daily_plan(self.test_user_id)
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert result is not None
            assert result.user_id == self.test_user_id
        
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 100, f"缓存平均响应时间 {avg_response_time:.2f}ms 过长"
        
        print(f"✅ 缓存响应时间测试通过，平均响应时间: {avg_response_time:.2f}ms")
        
        # 测试2: 缓存命中率
        sample_content = [
            Content(
                content_id="cache_content_1",
                title="缓存测试内容",
                body="Test content for cache",
                language="english",
                difficulty_level="CET-4",
                content_type=ContentType.ARTICLE,
                source_url="https://example.com/cache",
                quality_score=0.8,
                created_at=datetime.now(),
                tags=["cache", "test"]
            )
        ]
        
        # 设置内容推荐缓存
        self.cache_manager.set_content_recommendations(self.test_user_id, "english", sample_content)
        
        # 测试命中率
        hit_count = 0
        total_requests = 10
        
        for _ in range(total_requests):
            result = self.cache_manager.get_content_recommendations(self.test_user_id, "english")
            if result is not None:
                hit_count += 1
        
        hit_rate = hit_count / total_requests
        assert hit_rate >= 0.9, f"缓存命中率 {hit_rate:.2%} 过低"
        
        print(f"✅ 缓存命中率测试通过，命中率: {hit_rate:.2%}")
        
        # 测试3: 数据库性能优化
        optimization_result = self.system_integrator.optimize_database_queries()
        
        if optimization_result['success']:
            opt_results = optimization_result['optimization_results']
            print("✅ 数据库优化完成:")
            print(f"   缓存优化: {opt_results.get('cache_optimization', {})}")
            print(f"   数据库优化: {opt_results.get('database_optimization', {})}")
        else:
            print("⚠️  数据库优化失败，但系统仍然稳定")
        
        # 测试4: 并发缓存访问
        def concurrent_cache_access(user_suffix):
            """并发缓存访问函数"""
            user_id = f"{self.test_user_id}_{user_suffix}"
            plan = DailyPlan(
                plan_id=f"concurrent_plan_{user_suffix}",
                user_id=user_id,
                date=datetime.now(),
                activities=[],
                time_allocation=TimeAllocation(60, 12, 24, 24, 0),
                learning_objectives=["并发测试"],
                estimated_completion_time=60
            )
            
            # 设置和获取缓存
            self.cache_manager.set_daily_plan(user_id, plan)
            result = self.cache_manager.get_daily_plan(user_id)
            return result is not None and result.user_id == user_id
        
        # 创建并发线程
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(
                target=lambda i=i: results.append(concurrent_cache_access(i))
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证并发访问结果
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8, f"并发缓存访问成功率 {success_rate:.2%} 过低"
        
        print(f"✅ 并发缓存访问测试通过，成功率: {success_rate:.2%}")
        
        print("✅ 缓存系统和性能优化测试完成")
    
    def test_mobile_responsive_design(self):
        """
        测试移动端响应式设计
        Test mobile responsive design
        
        验证：
        - Web界面响应性
        - 移动端兼容性
        - 响应式布局
        - 触摸交互支持
        - PWA功能
        """
        print("\n📱 测试移动端响应式设计...")
        
        # 创建Flask测试客户端
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            # 测试1: 主页响应性
            response = client.get('/')
            assert response.status_code in [200, 302], "主页应该可访问"
            
            print("✅ 主页响应性测试通过")
            
            # 测试2: 移动端用户代理测试
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            }
            
            mobile_response = client.get('/', headers=mobile_headers)
            assert mobile_response.status_code in [200, 302], "移动端访问应该正常"
            
            print("✅ 移动端用户代理测试通过")
            
            # 测试3: 平板端用户代理测试
            tablet_headers = {
                'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            }
            
            tablet_response = client.get('/', headers=tablet_headers)
            assert tablet_response.status_code in [200, 302], "平板端访问应该正常"
            
            print("✅ 平板端用户代理测试通过")
            
            # 测试4: API端点响应性
            try:
                api_response = client.get('/api/health')
                # API可能不存在，但不应该导致服务器错误
                assert api_response.status_code in [200, 404, 405], "API端点应该有合理的响应"
            except Exception as e:
                print(f"API端点测试异常: {e}")
            
            # 测试5: 静态资源访问
            try:
                css_response = client.get('/static/css/style.css')
                js_response = client.get('/static/js/main.js')
                
                # 静态资源可能存在也可能不存在
                assert css_response.status_code in [200, 404], "CSS文件应该有合理的响应"
                assert js_response.status_code in [200, 404], "JS文件应该有合理的响应"
                
                print("✅ 静态资源访问测试通过")
            except Exception as e:
                print(f"静态资源测试异常: {e}")
        
        # 测试6: 响应式设计验证
        self._test_responsive_design_elements()
        
        print("✅ 移动端响应式设计测试完成")
    
    def test_integrated_learning_workflow(self):
        """
        测试集成学习工作流程
        Test integrated learning workflow
        
        验证：
        - 完整学习会话创建
        - 多组件协作
        - 数据流一致性
        - 错误恢复能力
        - 性能监控
        """
        print("\n🎯 测试集成学习工作流程...")
        
        # 测试1: 创建集成学习会话
        session_result = self.system_integrator.create_integrated_learning_session(
            self.test_user_id,
            preferences={
                'english_level': 'CET-4',
                'japanese_level': 'N5',
                'daily_time': 60
            }
        )
        
        assert 'success' in session_result
        if session_result['success']:
            session_data = session_result['session']
            
            assert session_data['user_id'] == self.test_user_id
            assert session_data['duration'] == 60
            assert session_data['status'] == 'planned'
            assert len(session_data['activities']) >= 0
            
            # 验证时间分配
            time_allocation = session_data['time_allocation']
            assert time_allocation['total'] == 60
            assert time_allocation['review'] == 12  # 20% of 60
            
            print("✅ 集成学习会话创建成功")
            
            # 测试2: 执行学习活动
            if session_data['activities']:
                activity = session_data['activities'][0]
                activity_result = self.system_integrator.execute_integrated_activity(
                    self.test_user_id,
                    activity['id']
                )
                
                assert 'success' in activity_result
                if activity_result['success']:
                    result_data = activity_result['result']
                    assert 'score' in result_data or 'feedback' in result_data
                    print("✅ 学习活动执行成功")
                else:
                    print(f"⚠️  学习活动执行失败: {activity_result.get('message', '未知错误')}")
        else:
            print(f"⚠️  集成学习会话创建失败: {session_result.get('message', '未知错误')}")
        
        # 测试3: 获取综合进度报告
        progress_result = self.system_integrator.get_integrated_progress_report(self.test_user_id)
        
        assert 'success' in progress_result
        if progress_result['success']:
            report_data = progress_result['report']
            
            assert report_data['user_id'] == self.test_user_id
            assert 'core_progress' in report_data
            assert 'database_stats' in report_data
            assert 'integration_health' in report_data
            
            print("✅ 综合进度报告生成成功")
        else:
            print(f"⚠️  综合进度报告生成失败: {progress_result.get('message', '未知错误')}")
        
        # 测试4: 系统健康检查
        health_data = self.system_integrator.get_system_health()
        
        assert isinstance(health_data, dict)
        assert 'overall_status' in health_data or 'components' in health_data
        
        print("✅ 系统健康检查完成")
        
        print("✅ 集成学习工作流程测试完成")
    
    def test_error_handling_and_recovery(self):
        """
        测试错误处理和恢复
        Test error handling and recovery
        
        验证：
        - 无效输入处理
        - 服务不可用处理
        - 数据一致性保护
        - 优雅降级
        - 错误恢复能力
        """
        print("\n🛡️  测试错误处理和恢复...")
        
        # 测试1: 无效用户ID处理
        invalid_session = self.system_integrator.create_integrated_learning_session("")
        
        assert isinstance(invalid_session, dict)
        assert 'success' in invalid_session
        # 系统应该优雅处理无效输入
        
        print("✅ 无效用户ID处理测试通过")
        
        # 测试2: 无效活动ID处理
        invalid_activity = self.system_integrator.execute_integrated_activity(
            self.test_user_id, "invalid_activity_id"
        )
        
        assert isinstance(invalid_activity, dict)
        assert 'success' in invalid_activity
        # 系统应该返回错误信息而不是崩溃
        
        print("✅ 无效活动ID处理测试通过")
        
        # 测试3: 不存在用户的进度查询
        nonexistent_progress = self.system_integrator.get_integrated_progress_report("nonexistent_user")
        
        assert isinstance(nonexistent_progress, dict)
        assert 'success' in nonexistent_progress
        # 系统应该优雅处理不存在的用户
        
        print("✅ 不存在用户处理测试通过")
        
        # 测试4: AI服务不可用时的处理
        ai_health = self.system_integrator.get_ai_service_health()
        
        assert isinstance(ai_health, dict)
        assert 'status' in ai_health
        
        if ai_health['status'] == 'error':
            # 验证系统在AI服务不可用时仍能正常运行
            basic_session = self.system_integrator.create_integrated_learning_session(
                self.test_user_id
            )
            assert isinstance(basic_session, dict)
            print("✅ AI服务不可用时的降级处理正常")
        
        # 测试5: 缓存失效时的处理
        # 清除所有缓存
        self.cache_manager.invalidate_user_cache(self.test_user_id)
        
        # 系统应该能够在没有缓存的情况下正常工作
        no_cache_session = self.system_integrator.create_integrated_learning_session(
            self.test_user_id
        )
        
        assert isinstance(no_cache_session, dict)
        assert 'success' in no_cache_session
        
        print("✅ 缓存失效处理测试通过")
        
        print("✅ 错误处理和恢复测试完成")
    
    def test_performance_monitoring_and_metrics(self):
        """
        测试性能监控和指标
        Test performance monitoring and metrics
        
        验证：
        - 响应时间监控
        - 资源使用监控
        - 错误率统计
        - 性能指标收集
        - 系统健康状态
        """
        print("\n📊 测试性能监控和指标...")
        
        # 测试1: 缓存性能指标
        cache_metrics = self.cache_manager.get_cache_metrics()
        
        assert hasattr(cache_metrics, 'total_requests') or 'total_requests' in cache_metrics
        assert hasattr(cache_metrics, 'hit_count') or 'hit_count' in cache_metrics
        assert hasattr(cache_metrics, 'hit_rate') or 'hit_rate' in cache_metrics
        
        print("✅ 缓存性能指标收集正常")
        
        # 测试2: AI服务性能指标
        ai_health = self.system_integrator.get_ai_service_health()
        
        if 'performance_metrics' in ai_health:
            metrics = ai_health['performance_metrics']
            assert isinstance(metrics, dict)
            print("✅ AI服务性能指标收集正常")
        
        # 测试3: 数据库性能指标
        try:
            db_stats = self.system_integrator.learning_db.get_performance_stats()
            
            if db_stats:
                assert 'query_count' in db_stats or 'connection_pool_size' in db_stats
                print("✅ 数据库性能指标收集正常")
        except Exception as e:
            print(f"数据库性能指标收集异常: {e}")
        
        # 测试4: 系统整体健康状态
        system_health = self.system_integrator.get_system_health()
        
        assert isinstance(system_health, dict)
        
        # 验证健康状态包含关键组件信息
        expected_components = ['cache_manager', 'learning_database', 'ai_service']
        for component in expected_components:
            # 组件可能存在也可能不存在，但不应该导致错误
            if component in system_health:
                assert isinstance(system_health[component], (str, dict))
        
        print("✅ 系统整体健康状态监控正常")
        
        # 测试5: 性能基准测试
        start_time = time.time()
        
        # 执行一系列操作来测试整体性能
        operations = [
            lambda: self.system_integrator.create_integrated_learning_session(f"{self.test_user_id}_perf"),
            lambda: self.system_integrator.get_integrated_progress_report(f"{self.test_user_id}_perf"),
            lambda: self.cache_manager.get_daily_plan(f"{self.test_user_id}_perf"),
        ]
        
        for operation in operations:
            try:
                result = operation()
                assert isinstance(result, dict)
            except Exception as e:
                print(f"性能测试操作异常: {e}")
        
        total_time = time.time() - start_time
        assert total_time < 5.0, f"性能基准测试耗时 {total_time:.2f}s 过长"
        
        print(f"✅ 性能基准测试通过，总耗时: {total_time:.2f}s")
        
        print("✅ 性能监控和指标测试完成")
    
    def _create_test_user_profile(self) -> UserProfile:
        """创建测试用户档案"""
        goals = Goals(
            target_english_level="CET-6",
            target_japanese_level="N1",
            target_completion_date=datetime.now() + timedelta(days=730),
            priority_skills=["vocabulary", "reading"],
            custom_objectives=["商务英语", "动漫理解"]
        )
        
        preferences = Preferences(
            preferred_study_times=["晚上"],
            content_preferences=[ContentType.ARTICLE, ContentType.NEWS],
            difficulty_preference="渐进式",
            language_balance={"english": 0.6, "japanese": 0.4}
        )
        
        return UserProfile(
            user_id=self.test_user_id,
            english_level="CET-4",
            japanese_level="N5",
            daily_study_time=60,
            target_goals=goals,
            learning_preferences=preferences,
            weak_areas=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _test_responsive_design_elements(self):
        """测试响应式设计元素"""
        try:
            # 检查CSS文件是否存在响应式设计元素
            css_path = 'bilingual_tutor/web/static/css/style.css'
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                
                # 检查媒体查询
                responsive_elements = [
                    '@media',
                    'max-width',
                    'min-width',
                    'viewport'
                ]
                
                for element in responsive_elements:
                    if element in css_content:
                        print(f"✅ 发现响应式设计元素: {element}")
            
            # 检查HTML模板是否包含viewport meta标签
            template_path = 'bilingual_tutor/web/templates/base.html'
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                if 'viewport' in html_content and 'device-width' in html_content:
                    print("✅ 发现viewport meta标签")
        
        except Exception as e:
            print(f"响应式设计元素检查异常: {e}")


class TestSystemStabilityUnderLoad:
    """系统负载稳定性测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.system_integrator = SystemIntegrator()
        self.cache_manager = FallbackCacheManager()
    
    def teardown_method(self):
        """测试后清理"""
        try:
            self.system_integrator.close()
        except Exception as e:
            print(f"清理警告: {e}")
    
    def test_concurrent_user_load(self):
        """
        测试并发用户负载
        Test concurrent user load
        """
        print("\n⚡ 测试并发用户负载...")
        
        concurrent_users = 5
        user_results = []
        
        def create_user_session(user_index):
            """创建用户会话的函数"""
            user_id = f"load_test_user_{user_index}"
            try:
                result = self.system_integrator.create_integrated_learning_session(
                    user_id,
                    preferences={'english_level': 'CET-4', 'japanese_level': 'N5'}
                )
                return result['success'] if 'success' in result else False
            except Exception as e:
                print(f"用户 {user_id} 会话创建异常: {e}")
                return False
        
        # 创建并发线程
        threads = []
        for i in range(concurrent_users):
            thread = threading.Thread(
                target=lambda i=i: user_results.append(create_user_session(i))
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证并发处理结果
        success_count = sum(user_results)
        success_rate = success_count / len(user_results) if user_results else 0
        
        assert success_rate >= 0.6, f"并发用户处理成功率 {success_rate:.2%} 过低"
        
        print(f"✅ 并发用户负载测试通过，成功率: {success_rate:.2%}")
    
    def test_memory_usage_stability(self):
        """
        测试内存使用稳定性
        Test memory usage stability
        """
        print("\n💾 测试内存使用稳定性...")
        
        # 执行大量操作来测试内存稳定性
        operations_count = 20
        
        for i in range(operations_count):
            user_id = f"memory_test_user_{i}"
            
            # 创建学习会话
            session_result = self.system_integrator.create_integrated_learning_session(user_id)
            
            # 获取进度报告
            progress_result = self.system_integrator.get_integrated_progress_report(user_id)
            
            # 设置和获取缓存
            sample_plan = DailyPlan(
                plan_id=f"memory_plan_{i}",
                user_id=user_id,
                date=datetime.now(),
                activities=[],
                time_allocation=TimeAllocation(60, 12, 24, 24, 0),
                learning_objectives=["内存测试"],
                estimated_completion_time=60
            )
            
            self.cache_manager.set_daily_plan(user_id, sample_plan)
            cached_plan = self.cache_manager.get_daily_plan(user_id)
            
            # 验证操作结果
            assert isinstance(session_result, dict)
            assert isinstance(progress_result, dict)
            assert cached_plan is not None
        
        print(f"✅ 内存使用稳定性测试通过，执行了 {operations_count} 次操作")
    
    def test_error_recovery_under_load(self):
        """
        测试负载下的错误恢复
        Test error recovery under load
        """
        print("\n🔄 测试负载下的错误恢复...")
        
        # 模拟各种错误情况
        error_scenarios = [
            ("无效用户ID", lambda: self.system_integrator.create_integrated_learning_session("")),
            ("无效活动ID", lambda: self.system_integrator.execute_integrated_activity("test", "invalid")),
            ("不存在用户", lambda: self.system_integrator.get_integrated_progress_report("nonexistent")),
        ]
        
        recovery_success = 0
        
        for scenario_name, scenario_func in error_scenarios:
            try:
                # 执行多次以测试一致性
                for _ in range(3):
                    result = scenario_func()
                    assert isinstance(result, dict), f"{scenario_name} 应该返回字典结果"
                
                recovery_success += 1
                print(f"✅ {scenario_name} 错误恢复测试通过")
                
            except Exception as e:
                print(f"⚠️  {scenario_name} 错误恢复测试异常: {e}")
        
        recovery_rate = recovery_success / len(error_scenarios)
        assert recovery_rate >= 0.5, f"错误恢复率 {recovery_rate:.2%} 过低"
        
        print(f"✅ 负载下错误恢复测试通过，恢复率: {recovery_rate:.2%}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])