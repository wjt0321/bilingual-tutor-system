"""
语音识别和发音评估服务测试
测试语音转文字、发音准确性评估和离线处理功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from bilingual_tutor.services.speech_service import (
    SpeechService,
    SpeechRecognitionResult,
    PronunciationAssessment,
    SpeechProcessingMetrics,
    Language,
    PronunciationAccuracy,
    get_speech_service
)


class TestSpeechRecognitionResult:
    """测试语音识别结果"""
    
    def test_speech_recognition_result_creation(self):
        """测试语音识别结果创建"""
        result = SpeechRecognitionResult(
            text="Hello world",
            confidence=0.95,
            duration_ms=500.0,
            language=Language.ENGLISH
        )
        
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.duration_ms == 500.0
        assert result.language == Language.ENGLISH
    
    def test_speech_recognition_result_to_dict(self):
        """测试语音识别结果转换为字典"""
        result = SpeechRecognitionResult(
            text="Hello world",
            confidence=0.95,
            duration_ms=500.0,
            language=Language.ENGLISH
        )
        
        dict_result = result.to_dict()
        
        assert dict_result['text'] == "Hello world"
        assert dict_result['confidence'] == 0.95
        assert dict_result['language'] == "english"
        assert dict_result['duration_ms'] == 500.0


class TestPronunciationAssessment:
    """测试发音评估"""
    
    def test_pronunciation_assessment_creation(self):
        """测试发音评估创建"""
        assessment = PronunciationAssessment(
            overall_score=0.85,
            accuracy_level=PronunciationAccuracy.GOOD,
            text="Hello world",
            errors=[],
            feedback="Good job!",
            duration_ms=600.0,
            language=Language.ENGLISH
        )
        
        assert assessment.overall_score == 0.85
        assert assessment.accuracy_level == PronunciationAccuracy.GOOD
        assert assessment.text == "Hello world"
        assert assessment.duration_ms == 600.0
    
    def test_pronunciation_assessment_to_dict(self):
        """测试发音评估转换为字典"""
        assessment = PronunciationAssessment(
            overall_score=0.85,
            accuracy_level=PronunciationAccuracy.GOOD,
            text="Hello world",
            errors=[],
            feedback="Good job!",
            duration_ms=600.0,
            language=Language.ENGLISH
        )
        
        dict_result = assessment.to_dict()
        
        assert dict_result['overall_score'] == 0.85
        assert dict_result['accuracy_level'] == "good"
        assert dict_result['text'] == "Hello world"
        assert dict_result['feedback'] == "Good job!"


class TestSpeechProcessingMetrics:
    """测试语音处理指标"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = SpeechProcessingMetrics()
        
        assert metrics.total_processed == 0
        assert metrics.successful_recognitions == 0
        assert metrics.failed_recognitions == 0
        assert metrics.average_duration_ms == 0.0
        assert metrics.average_confidence == 0.0
    
    def test_metrics_update_success(self):
        """测试更新成功指标"""
        metrics = SpeechProcessingMetrics()
        metrics.update(True, 500.0, 0.9)
        
        assert metrics.total_processed == 1
        assert metrics.successful_recognitions == 1
        assert metrics.failed_recognitions == 0
        assert metrics.average_duration_ms == 500.0
        assert metrics.average_confidence == 0.9
    
    def test_metrics_update_failure(self):
        """测试更新失败指标"""
        metrics = SpeechProcessingMetrics()
        metrics.update(False, 600.0, 0.0)
        
        assert metrics.total_processed == 1
        assert metrics.successful_recognitions == 0
        assert metrics.failed_recognitions == 1
        assert metrics.average_confidence == 0.0
    
    def test_metrics_success_rate(self):
        """测试计算成功率"""
        metrics = SpeechProcessingMetrics()
        metrics.update(True, 500.0, 0.9)
        metrics.update(True, 600.0, 0.85)
        metrics.update(False, 700.0, 0.0)
        
        assert metrics.get_success_rate() == 2/3
    
    def test_metrics_average_calculation(self):
        """测试计算平均值"""
        metrics = SpeechProcessingMetrics()
        metrics.update(True, 500.0, 0.9)
        metrics.update(True, 600.0, 0.8)
        
        assert metrics.average_duration_ms == 550.0
        assert abs(metrics.average_confidence - 0.85) < 0.01
    
    def test_metrics_to_dict(self):
        """测试指标转换为字典"""
        metrics = SpeechProcessingMetrics()
        metrics.update(True, 500.0, 0.9)
        
        dict_result = metrics.to_dict()
        
        assert dict_result['total_processed'] == 1
        assert dict_result['successful_recognitions'] == 1
        assert dict_result['success_rate'] == 1.0


class TestSpeechService:
    """测试语音服务"""
    
    @pytest.mark.asyncio
    async def test_recognize_speech_offline(self):
        """测试离线语音识别"""
        service = SpeechService(enable_offline=True)
        
        audio_data = b"mock audio data"
        
        result = await service.recognize_speech(
            audio_data=audio_data,
            language=Language.ENGLISH,
            use_offline=True
        )
        
        assert isinstance(result, SpeechRecognitionResult)
        assert result.language == Language.ENGLISH
        assert 0.0 <= result.confidence <= 1.0
        assert result.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_recognize_speech_online(self):
        """测试在线语音识别"""
        service = SpeechService(enable_offline=False)
        
        audio_data = b"mock audio data"
        
        result = await service.recognize_speech(
            audio_data=audio_data,
            language=Language.ENGLISH,
            use_offline=False
        )
        
        assert isinstance(result, SpeechRecognitionResult)
        assert result.language == Language.ENGLISH
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_recognize_speech_with_cache(self):
        """测试带缓存的语音识别"""
        service = SpeechService(enable_offline=True)
        
        audio_data = b"mock audio data for caching"
        
        # 第一次识别
        result1 = await service.recognize_speech(
            audio_data=audio_data,
            language=Language.ENGLISH
        )
        
        # 第二次识别相同音频（应该从缓存返回）
        result2 = await service.recognize_speech(
            audio_data=audio_data,
            language=Language.ENGLISH
        )
        
        # 验证缓存工作
        assert result2.metadata.get('cached') == True
        assert result2.duration_ms < result1.duration_ms  # 缓存应该更快
    
    @pytest.mark.asyncio
    async def test_assess_pronunciation(self):
        """测试发音评估"""
        service = SpeechService()
        
        audio_data = b"mock audio data"
        target_text = "hello world"
        
        assessment = await service.assess_pronunciation(
            audio_data=audio_data,
            target_text=target_text,
            language=Language.ENGLISH
        )
        
        assert isinstance(assessment, PronunciationAssessment)
        assert 0.0 <= assessment.overall_score <= 1.0
        assert assessment.text is not None
        assert assessment.feedback is not None
        assert assessment.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_assess_pronunciation_with_japanese(self):
        """测试日语发音评估"""
        service = SpeechService()
        
        audio_data = b"mock audio data"
        target_text = "こんにちは"
        
        assessment = await service.assess_pronunciation(
            audio_data=audio_data,
            target_text=target_text,
            language=Language.JAPANESE
        )
        
        assert assessment.language == Language.JAPANESE
        assert 0.0 <= assessment.overall_score <= 1.0
    
    def test_pronunciation_score_calculation(self):
        """测试发音得分计算"""
        service = SpeechService()
        
        # 完全正确
        errors = []
        score = service._calculate_pronunciation_score(
            spoken_text="hello world",
            target_text="hello world",
            errors=errors
        )
        assert score == 1.0
        
        # 有错误
        errors = [
            {'type': 'mispronunciation'},
            {'type': 'missing'}
        ]
        score = service._calculate_pronunciation_score(
            spoken_text="hello",
            target_text="hello world",
            errors=errors
        )
        assert score < 1.0
        assert score > 0.0
    
    def test_accuracy_level_determination(self):
        """测试准确度等级确定"""
        service = SpeechService()
        
        assert service._determine_accuracy_level(0.95) == PronunciationAccuracy.EXCELLENT
        assert service._determine_accuracy_level(0.80) == PronunciationAccuracy.GOOD
        assert service._determine_accuracy_level(0.65) == PronunciationAccuracy.ACCEPTABLE
        assert service._determine_accuracy_level(0.50) == PronunciationAccuracy.NEEDS_IMPROVEMENT
    
    def test_feedback_generation(self):
        """测试反馈生成"""
        service = SpeechService()
        
        # 优秀
        feedback = service._generate_feedback(0.95, [], Language.ENGLISH)
        assert "Excellent" in feedback or "优秀" in feedback
        
        # 良好
        feedback = service._generate_feedback(0.80, [], Language.ENGLISH)
        assert "Good" in feedback or "良好" in feedback
        
        # 需要改进
        feedback = service._generate_feedback(0.50, [], Language.ENGLISH)
        assert "improvement" in feedback or "改进" in feedback or "improve" in feedback.lower()
    
    def test_metrics_tracking(self):
        """测试指标跟踪"""
        service = SpeechService()
        
        # 模拟一些处理
        service._metrics.update(True, 500.0, 0.9)
        service._metrics.update(True, 600.0, 0.85)
        service._metrics.update(False, 700.0, 0.0)
        
        metrics = service.get_metrics()
        
        assert metrics.total_processed == 3
        assert metrics.successful_recognitions == 2
        assert metrics.failed_recognitions == 1
        assert metrics.get_success_rate() == 2/3
    
    def test_cache_management(self):
        """测试缓存管理"""
        service = SpeechService()
        
        # 添加一些缓存
        service._cache['hash1'] = {'text': 'Hello', 'confidence': 0.9}
        service._cache['hash2'] = {'text': 'World', 'confidence': 0.85}
        
        cache_info = service.get_cache_info()
        
        assert cache_info['cache_size'] == 2
        assert cache_info['enabled_offline'] == True
        
        # 清除缓存
        service.clear_cache()
        
        cache_info = service.get_cache_info()
        assert cache_info['cache_size'] == 0


class TestSpeechServiceSingleton:
    """测试语音服务单例"""
    
    def test_get_speech_service_singleton(self):
        """测试获取语音服务单例"""
        service1 = get_speech_service()
        service2 = get_speech_service()
        
        assert service1 is service2


class TestPronunciationComparison:
    """测试发音比较"""
    
    def test_compare_perfect_pronunciation(self):
        """测试完美发音比较"""
        service = SpeechService()
        
        errors = service._compare_pronunciation(
            spoken_text="hello world",
            target_text="hello world",
            language=Language.ENGLISH
        )
        
        assert len(errors) == 0
    
    def test_compare_with_errors(self):
        """测试有错误的发音比较"""
        service = SpeechService()
        
        errors = service._compare_pronunciation(
            spoken_text="hello word",
            target_text="hello world",
            language=Language.ENGLISH
        )
        
        assert len(errors) > 0
        assert errors[0]['type'] == 'mispronunciation'
    
    def test_compare_with_missing_word(self):
        """测试有遗漏词的发音比较"""
        service = SpeechService()
        
        errors = service._compare_pronunciation(
            spoken_text="hello",
            target_text="hello world",
            language=Language.ENGLISH
        )
        
        assert len(errors) > 0
        missing_errors = [e for e in errors if e['type'] == 'missing']
        assert len(missing_errors) > 0
    
    def test_compare_with_extra_word(self):
        """测试有多余词的发音比较"""
        service = SpeechService()
        
        errors = service._compare_pronunciation(
            spoken_text="hello world test",
            target_text="hello world",
            language=Language.ENGLISH
        )
        
        assert len(errors) > 0
        extra_errors = [e for e in errors if e['type'] == 'extra']
        assert len(extra_errors) > 0


class TestLanguageEnum:
    """测试语言枚举"""
    
    def test_language_values(self):
        """测试语言枚举值"""
        assert Language.ENGLISH.value == "english"
        assert Language.JAPANESE.value == "japanese"


class TestPronunciationAccuracyEnum:
    """测试发音准确度枚举"""
    
    def test_accuracy_values(self):
        """测试准确度枚举值"""
        assert PronunciationAccuracy.EXCELLENT.value == "excellent"
        assert PronunciationAccuracy.GOOD.value == "good"
        assert PronunciationAccuracy.ACCEPTABLE.value == "acceptable"
        assert PronunciationAccuracy.NEEDS_IMPROVEMENT.value == "needs_improvement"
