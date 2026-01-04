"""
语音识别和发音评估服务
Speech Recognition and Pronunciation Assessment Service

实现语音转文字、发音准确性评估和离线语音处理功能。
"""

import time
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from bilingual_tutor.infrastructure.logging_system import get_logger


logger = get_logger(__name__)


class Language(Enum):
    """语言类型"""
    ENGLISH = "english"
    JAPANESE = "japanese"


class PronunciationAccuracy(Enum):
    """发音准确度"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"  # 75-89%
    ACCEPTABLE = "acceptable"  # 60-74%
    NEEDS_IMPROVEMENT = "needs_improvement"  # <60%


@dataclass
class SpeechRecognitionResult:
    """语音识别结果"""
    text: str
    confidence: float  # 0-1之间，1表示完全准确
    duration_ms: float
    language: Language
    segments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'text': self.text,
            'confidence': self.confidence,
            'duration_ms': self.duration_ms,
            'language': self.language.value,
            'segments': self.segments,
            'metadata': self.metadata
        }


@dataclass
class PronunciationAssessment:
    """发音评估结果"""
    overall_score: float  # 0-1之间
    accuracy_level: PronunciationAccuracy
    text: str
    errors: List[Dict[str, Any]]
    feedback: str
    duration_ms: float
    language: Language
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'overall_score': self.overall_score,
            'accuracy_level': self.accuracy_level.value,
            'text': self.text,
            'errors': self.errors,
            'feedback': self.feedback,
            'duration_ms': self.duration_ms,
            'language': self.language.value,
            'metadata': self.metadata
        }


@dataclass
class SpeechProcessingMetrics:
    """语音处理指标"""
    total_processed: int = 0
    successful_recognitions: int = 0
    failed_recognitions: int = 0
    average_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    average_confidence: float = 0.0
    
    def update(self, success: bool, duration_ms: float, confidence: float) -> None:
        """更新指标"""
        self.total_processed += 1
        if success:
            self.successful_recognitions += 1
        else:
            self.failed_recognitions += 1
        
        self.total_duration_ms += duration_ms
        self.average_duration_ms = self.total_duration_ms / self.total_processed
        
        # 更新平均置信度
        self.average_confidence = (
            (self.average_confidence * (self.total_processed - 1) + confidence) /
            self.total_processed
        )
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_processed == 0:
            return 0.0
        return self.successful_recognitions / self.total_processed
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_processed': self.total_processed,
            'successful_recognitions': self.successful_recognitions,
            'failed_recognitions': self.failed_recognitions,
            'success_rate': self.get_success_rate(),
            'average_duration_ms': self.average_duration_ms,
            'average_confidence': self.average_confidence
        }


class SpeechService:
    """语音服务"""
    
    def __init__(self, enable_offline: bool = True):
        self.enable_offline = enable_offline
        self.logger = get_logger(f"{__name__}.SpeechService")
        self._metrics = SpeechProcessingMetrics()
        self._cache: Dict[str, Any] = {}
    
    async def recognize_speech(self,
                             audio_data: bytes,
                             language: Language = Language.ENGLISH,
                             use_offline: bool = None) -> SpeechRecognitionResult:
        """语音转文字"""
        start_time = time.perf_counter()
        
        use_offline = use_offline if use_offline is not None else self.enable_offline
        
        try:
            # 生成音频指纹用于缓存
            audio_hash = self._generate_audio_hash(audio_data)
            
            # 检查缓存
            if audio_hash in self._cache:
                cached_result = self._cache[audio_hash]
                logger.info(f"从缓存返回语音识别结果: {cached_result['text']}")
                
                self._metrics.update(True, 10.0, cached_result['confidence'])
                
                return SpeechRecognitionResult(
                    text=cached_result['text'],
                    confidence=cached_result['confidence'],
                    duration_ms=10.0,
                    language=language,
                    metadata={'cached': True}
                )
            
            # 执行语音识别
            if use_offline:
                result = await self._recognize_offline(audio_data, language)
            else:
                result = await self._recognize_online(audio_data, language)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # 缓存结果
            if result.confidence > 0.8:
                self._cache[audio_hash] = {
                    'text': result.text,
                    'confidence': result.confidence
                }
                
                # 限制缓存大小
                if len(self._cache) > 100:
                    self._cache.pop(next(iter(self._cache)))
            
            self._metrics.update(True, duration_ms, result.confidence)
            logger.info(f"语音识别成功，置信度: {result.confidence:.2f}, 耗时: {duration_ms:.2f}ms")
            
            return result
        
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.update(False, duration_ms, 0.0)
            self.logger.error(f"语音识别失败: {str(e)}")
            raise RuntimeError(f"语音识别失败: {str(e)}")
    
    async def assess_pronunciation(self,
                                   audio_data: bytes,
                                   target_text: str,
                                   language: Language = Language.ENGLISH) -> PronunciationAssessment:
        """发音评估"""
        start_time = time.perf_counter()
        
        try:
            # 首先识别语音
            recognition_result = await self.recognize_speech(audio_data, language)
            
            # 评估发音准确性
            errors = self._compare_pronunciation(
                recognition_result.text,
                target_text,
                language
            )
            
            # 计算整体得分
            overall_score = self._calculate_pronunciation_score(
                recognition_result.text,
                target_text,
                errors
            )
            
            # 确定准确度等级
            accuracy_level = self._determine_accuracy_level(overall_score)
            
            # 生成反馈
            feedback = self._generate_feedback(overall_score, errors, language)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            result = PronunciationAssessment(
                overall_score=overall_score,
                accuracy_level=accuracy_level,
                text=recognition_result.text,
                errors=errors,
                feedback=feedback,
                duration_ms=duration_ms,
                language=language,
                metadata={
                    'recognition_confidence': recognition_result.confidence
                }
            )
            
            logger.info(f"发音评估完成，得分: {overall_score:.2f}, 等级: {accuracy_level.value}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"发音评估失败: {str(e)}")
            raise RuntimeError(f"发音评估失败: {str(e)}")
    
    async def _recognize_offline(self,
                                  audio_data: bytes,
                                  language: Language) -> SpeechRecognitionResult:
        """离线语音识别"""
        start_time = time.perf_counter()
        
        # 这里实现离线语音识别
        # 实际实现可以使用 offline-voice-recognition 或类似库
        
        # 模拟识别结果（实际使用时需要替换为真实的离线识别）
        await asyncio.sleep(0.1)  # 模拟处理时间
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # 返回模拟结果
        return SpeechRecognitionResult(
            text="Simulated speech recognition result",
            confidence=0.85,
            duration_ms=duration_ms,
            language=language,
            metadata={'mode': 'offline'}
        )
    
    async def _recognize_online(self,
                                 audio_data: bytes,
                                 language: Language) -> SpeechRecognitionResult:
        """在线语音识别"""
        start_time = time.perf_counter()
        
        # 这里实现在线语音识别
        # 实际实现可以使用 Google Cloud Speech-to-Text、Azure Speech Services 等
        
        # 模拟识别结果（实际使用时需要替换为真实的在线识别）
        await asyncio.sleep(0.2)  # 模拟网络延迟
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # 返回模拟结果
        return SpeechRecognitionResult(
            text="Simulated online speech recognition result",
            confidence=0.90,
            duration_ms=duration_ms,
            language=language,
            metadata={'mode': 'online'}
        )
    
    def _compare_pronunciation(self,
                               spoken_text: str,
                               target_text: str,
                               language: Language) -> List[Dict[str, Any]]:
        """比较发音"""
        errors = []
        
        # 简单的文本比较（实际实现应该使用更复杂的语音比较算法）
        spoken_words = spoken_text.lower().split()
        target_words = target_text.lower().split()
        
        # 查找错误的词
        for i, spoken_word in enumerate(spoken_words):
            if i >= len(target_words):
                # 多说了词
                errors.append({
                    'type': 'extra',
                    'spoken': spoken_word,
                    'position': i,
                    'suggestion': 'remove this word'
                })
            elif spoken_word != target_words[i]:
                # 发音错误的词
                errors.append({
                    'type': 'mispronunciation',
                    'spoken': spoken_word,
                    'target': target_words[i],
                    'position': i,
                    'suggestion': f'try saying "{target_words[i]}"'
                })
        
        # 检查遗漏的词
        if len(target_words) > len(spoken_words):
            for i in range(len(spoken_words), len(target_words)):
                errors.append({
                    'type': 'missing',
                    'target': target_words[i],
                    'position': i,
                    'suggestion': f'missing "{target_words[i]}"'
                })
        
        return errors
    
    def _calculate_pronunciation_score(self,
                                      spoken_text: str,
                                      target_text: str,
                                      errors: List[Dict[str, Any]]) -> float:
        """计算发音得分"""
        if not target_text:
            return 0.0
        
        # 基于错误数量计算得分
        target_word_count = len(target_text.split())
        
        if target_word_count == 0:
            return 0.0
        
        error_penalty = 0.0
        for error in errors:
            if error['type'] == 'mispronunciation':
                error_penalty += 0.3
            elif error['type'] == 'missing':
                error_penalty += 0.5
            elif error['type'] == 'extra':
                error_penalty += 0.2
        
        # 计算得分
        score = max(0.0, 1.0 - error_penalty / target_word_count)
        
        return score
    
    def _determine_accuracy_level(self, score: float) -> PronunciationAccuracy:
        """确定准确度等级"""
        if score >= 0.90:
            return PronunciationAccuracy.EXCELLENT
        elif score >= 0.75:
            return PronunciationAccuracy.GOOD
        elif score >= 0.60:
            return PronunciationAccuracy.ACCEPTABLE
        else:
            return PronunciationAccuracy.NEEDS_IMPROVEMENT
    
    def _generate_feedback(self,
                         score: float,
                         errors: List[Dict[str, Any]],
                         language: Language) -> str:
        """生成反馈"""
        if score >= 0.90:
            feedback = "Excellent! Your pronunciation is very accurate."
        elif score >= 0.75:
            feedback = "Good job! Your pronunciation is mostly correct with minor issues."
        elif score >= 0.60:
            feedback = "Acceptable. Try to improve the pronunciation of specific words."
        else:
            feedback = "Needs improvement. Practice the words that were mispronounced."
        
        # 添加具体建议
        if errors:
            specific_suggestions = []
            for error in errors[:3]:  # 只显示前3个错误
                if error['type'] == 'mispronunciation':
                    specific_suggestions.append(
                        f"Try to pronounce '{error['target']}' instead of '{error['spoken']}'"
                    )
                elif error['type'] == 'missing':
                    specific_suggestions.append(
                        f"Don't forget to say '{error['target']}'"
                    )
            
            if specific_suggestions:
                feedback += " " + " ".join(specific_suggestions)
        
        return feedback
    
    def _generate_audio_hash(self, audio_data: bytes) -> str:
        """生成音频指纹"""
        return hashlib.md5(audio_data).hexdigest()
    
    def get_metrics(self) -> SpeechProcessingMetrics:
        """获取处理指标"""
        return self._metrics
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """获取处理指标（字典格式）"""
        return self._metrics.to_dict()
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        self.logger.info("语音识别缓存已清除")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'cache_size': len(self._cache),
            'enabled_offline': self.enable_offline,
            'max_cache_size': 100
        }


# 全局语音服务实例
_global_speech_service: Optional[SpeechService] = None


def get_speech_service(enable_offline: bool = True) -> SpeechService:
    """获取语音服务单例"""
    global _global_speech_service
    if _global_speech_service is None:
        _global_speech_service = SpeechService(enable_offline=enable_offline)
    return _global_speech_service
