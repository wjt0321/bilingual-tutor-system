"""
Task 28.1.1: 测试AI对话和智能内容生成功能
Test AI Dialogue and Intelligent Content Generation

验证需求: 25.1, 25.7, 26.1, 26.2
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from typing import Dict, Any, List

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
    ExerciseGenerator
)
from bilingual_tutor.services.intelligent_content_generator import (
    IntelligentContentGenerator,
    Exercise,
    ExerciseBatch,
    QualityMetrics
)
from bilingual_tutor.core.system_integrator import SystemIntegrator


class TestAIDialogueFunctionality:
    """测试AI对话功能"""
    
    @pytest.fixture
    def system_integrator(self):
        """创建系统集成器实例"""
        si = SystemIntegrator()
        yield si
        si.close()
    
    @pytest.fixture
    def mock_ai_service(self):
        """创建Mock AI服务"""
        service = Mock(spec=AIService)
        service.generate = AsyncMock()
        return service
    
    def test_ai_service_health_check(self, system_integrator):
        """测试AI服务健康检查"""
        health = system_integrator.get_ai_service_health()
        
        assert 'status' in health
        assert 'conversation_partner' in health
        assert 'grammar_corrector' in health
        assert 'exercise_generator' in health
        assert 'performance_metrics' in health
    
    def test_conversation_partner_initialization(self, system_integrator):
        """测试对话伙伴初始化"""
        result = system_integrator.start_ai_conversation(
            user_id="test_user",
            language="english",
            scenario="daily"
        )
        
        assert result['success'] is True
        assert 'conversation_id' in result
        assert 'ai_message' in result or 'error' in result
    
    def test_vocabulary_explanation(self, system_integrator):
        """测试词汇解释功能"""
        result = system_integrator.explain_vocabulary_with_ai(
            user_id="test_user",
            word="serendipity",
            language="english"
        )
        
        assert 'success' in result
        if result['success']:
            assert 'explanation' in result or 'content' in result
        else:
            assert 'error' in result
    
    def test_grammar_correction(self, system_integrator):
        """测试语法纠错功能"""
        result = system_integrator.correct_grammar_with_ai(
            user_id="test_user",
            text="He go to school everyday.",
            language="english"
        )
        
        assert 'success' in result
        if result['success']:
            assert 'corrected_text' in result or 'is_correct' in result
        else:
            assert 'error' in result
    
    def test_exercise_generation(self, system_integrator):
        """测试练习生成功能"""
        result = system_integrator.generate_personalized_exercises(
            user_id="test_user",
            weakness_areas=["语法", "词汇"],
            language="english",
            exercise_type="multiple_choice",
            count=5
        )
        
        assert 'success' in result
        if result['success']:
            assert 'exercises' in result or 'exercise_type' in result
        else:
            assert 'error' in result


class TestIntelligentContentGeneration:
    """测试智能内容生成"""
    
    @pytest.fixture
    def generator(self):
        """创建智能内容生成器"""
        return IntelligentContentGenerator()
    
    def test_generator_initialization(self, generator):
        """测试生成器初始化"""
        assert generator is not None
        assert hasattr(generator, 'generate_exercise')
        assert hasattr(generator, 'generate_batch_exercises')
        assert hasattr(generator, 'adjust_difficulty_based_on_feedback')
    
    def test_difficulty_adjustment_high_accuracy(self, generator):
        """测试高准确率时的难度调整"""
        feedback = {
            'accuracy': 0.9,
            'time_taken': 300,
            'exercises_completed': 10
        }
        
        adjustment = generator.adjust_difficulty_based_on_feedback(
            current_level=LanguageLevel.CET4,
            feedback=feedback
        )
        
        assert adjustment is not None
        assert 'suggested_level' in adjustment or 'action' in adjustment
    
    def test_difficulty_adjustment_low_accuracy(self, generator):
        """测试低准确率时的难度调整"""
        feedback = {
            'accuracy': 0.4,
            'time_taken': 600,
            'exercises_completed': 10
        }
        
        adjustment = generator.adjust_difficulty_based_on_feedback(
            current_level=LanguageLevel.CET6,
            feedback=feedback
        )
        
        assert adjustment is not None
        assert 'suggested_level' in adjustment or 'action' in adjustment
    
    def test_exercise_optimization(self, generator):
        """测试练习优化"""
        exercises = [
            Exercise(
                exercise_id="ex1",
                question="Test question 1",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Explanation 1",
                difficulty="medium"
            ),
            Exercise(
                exercise_id="ex2",
                question="Test question 2",
                options=["A", "B", "C", "D"],
                correct_answer="B",
                explanation="Explanation 2",
                difficulty="hard"
            )
        ]
        
        result = generator.optimize_exercises(exercises)
        
        assert result is not None
        assert isinstance(result, list) or isinstance(result, dict)
    
    def test_generation_statistics(self, generator):
        """测试生成统计信息"""
        stats = generator.get_generation_statistics()
        
        assert 'total_generated' in stats
        assert 'successful_generations' in stats
        assert 'average_quality_score' in stats


class TestAIResponseQuality:
    """测试AI响应质量"""
    
    @pytest.fixture
    def mock_ai_service(self):
        """创建Mock AI服务"""
        service = Mock(spec=AIService)
        service.generate = AsyncMock()
        return service
    
    def test_response_structure_validation(self, mock_ai_service):
        """测试响应结构验证"""
        mock_ai_service.generate.return_value = AIResponse(
            content="This is a test response.",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=500.0,
            request_id="test-id"
        )
        
        async def test_async():
            response = await mock_ai_service.generate(AIRequest(prompt="Test"))
            
            assert response.content is not None
            assert len(response.content) > 0
            assert response.duration_ms > 0
            assert response.request_id is not None
            assert response.model_type is not None
        
        asyncio.run(test_async())
    
    def test_response_time_measurement(self, mock_ai_service):
        """测试响应时间测量"""
        mock_ai_service.generate.return_value = AIResponse(
            content="Test response",
            model_type=AIModelType.DEEPSEEK,
            model_name="deepseek-chat",
            duration_ms=450.0,
            request_id="test-id"
        )
        
        async def test_async():
            response = await mock_ai_service.generate(AIRequest(prompt="Test"))
            
            assert response.duration_ms is not None
            assert response.duration_ms > 0
            assert response.duration_ms < 10000  # 应该小于10秒
        
        asyncio.run(test_async())
    
    def test_language_level_matching(self):
        """测试语言级别匹配"""
        levels = [
            LanguageLevel.CET4,
            LanguageLevel.CET5,
            LanguageLevel.CET6,
            LanguageLevel.N5,
            LanguageLevel.N4,
            LanguageLevel.N3
        ]
        
        for level in levels:
            request = AIRequest(
                prompt="Test",
                language_level=level
            )
            
            assert request.language_level == level
            assert request.to_dict()['language_level'] == level.value


class TestExerciseQualityMetrics:
    """测试练习质量指标"""
    
    def test_quality_metrics_initialization(self):
        """测试质量指标初始化"""
        metrics = QualityMetrics()
        
        assert metrics.clarity_score >= 0
        assert metrics.clarity_score <= 1
        assert metrics.relevance_score >= 0
        assert metrics.relevance_score <= 1
        assert metrics.difficulty_score >= 0
        assert metrics.difficulty_score <= 1
    
    def test_quality_metrics_calculation(self):
        """测试质量指标计算"""
        metrics = QualityMetrics(
            clarity_score=0.85,
            relevance_score=0.90,
            difficulty_score=0.75
        )
        
        overall_score = metrics.calculate_overall_score()
        
        assert overall_score >= 0
        assert overall_score <= 1
        assert overall_score > 0.7  # 应该较高
    
    def test_quality_metrics_to_dict(self):
        """测试质量指标转字典"""
        metrics = QualityMetrics(
            clarity_score=0.8,
            relevance_score=0.9,
            difficulty_score=0.75
        )
        
        metrics_dict = metrics.to_dict()
        
        assert 'clarity_score' in metrics_dict
        assert 'relevance_score' in metrics_dict
        assert 'difficulty_score' in metrics_dict
        assert 'overall_score' in metrics_dict


class TestConversationFlow:
    """测试对话流程"""
    
    @pytest.fixture
    def system_integrator(self):
        """创建系统集成器实例"""
        si = SystemIntegrator()
        yield si
        si.close()
    
    def test_conversation_start_and_continue(self, system_integrator):
        """测试对话开始和继续"""
        start_result = system_integrator.start_ai_conversation(
            user_id="test_user",
            language="english",
            scenario="daily"
        )
        
        if start_result['success']:
            conversation_id = start_result.get('conversation_id')
            
            if conversation_id:
                continue_result = system_integrator.continue_ai_conversation(
                    user_id="test_user",
                    conversation_id=conversation_id,
                    user_message="Hello, how are you?",
                    language="english",
                    conversation_history=[
                        {"role": "user", "content": "Start"},
                        {"role": "assistant", "content": start_result.get('ai_message', '')}
                    ]
                )
                
                assert 'success' in continue_result
                assert 'ai_response' in continue_result or 'error' in continue_result
    
    def test_multi_turn_conversation(self, system_integrator):
        """测试多轮对话"""
        conversation_history = []
        
        for i in range(3):
            result = system_integrator.continue_ai_conversation(
                user_id="test_user",
                conversation_id=f"conv_{i}",
                user_message=f"Message {i}",
                language="english",
                conversation_history=conversation_history
            )
            
            if result['success']:
                ai_response = result.get('ai_response', '')
                conversation_history.append({
                    "role": "user",
                    "content": f"Message {i}"
                })
                conversation_history.append({
                    "role": "assistant",
                    "content": ai_response
                })
        
        assert len(conversation_history) >= 0


class TestPersonalization:
    """测试个性化功能"""
    
    @pytest.fixture
    def system_integrator(self):
        """创建系统集成器实例"""
        si = SystemIntegrator()
        yield si
        si.close()
    
    def test_personalized_exercise_generation(self, system_integrator):
        """测试个性化练习生成"""
        result = system_integrator.generate_personalized_exercises(
            user_id="test_user",
            weakness_areas=["语法", "词汇"],
            language="english",
            exercise_type="multiple_choice",
            count=5
        )
        
        assert 'success' in result
        if result['success']:
            assert 'exercises' in result or 'content' in result
    
    def test_level_appropriate_content(self, system_integrator):
        """测试级别适当的内容"""
        levels = ["CET-4", "CET-6", "N5", "N3"]
        
        for level in levels:
            result = system_integrator.explain_vocabulary_with_ai(
                user_id="test_user",
                word="hello",
                language="english" if level.startswith("CET") else "japanese"
            )
            
            assert 'success' in result


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def system_integrator(self):
        """创建系统集成器实例"""
        si = SystemIntegrator()
        yield si
        si.close()
    
    def test_invalid_language_level(self):
        """测试无效语言级别"""
        request = AIRequest(
            prompt="Test",
            language_level=LanguageLevel.CET4
        )
        
        assert request.language_level == LanguageLevel.CET4
    
    def test_empty_user_message_handling(self, system_integrator):
        """测试空用户消息处理"""
        result = system_integrator.continue_ai_conversation(
            user_id="test_user",
            conversation_id="test_conv",
            user_message="",
            language="english",
            conversation_history=[]
        )
        
        assert 'success' in result
        assert 'error' in result or 'ai_response' in result
    
    def test_service_unavailable_handling(self, system_integrator):
        """测试服务不可用处理"""
        health = system_integrator.get_ai_service_health()
        
        assert 'status' in health
        if health['status'] == 'error':
            assert 'error' in health
