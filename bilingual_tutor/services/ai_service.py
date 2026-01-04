"""
双语导师系统 - AI增强服务
Bilingual Tutor System - AI Enhanced Service

实现大语言模型集成、智能内容生成和个性化练习生成功能。
"""

import os
import json
import time
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import logging
import random

from bilingual_tutor.infrastructure.error_handler import (
    ExternalServiceError,
    ConfigurationError,
    RateLimitError,
    handle_errors
)
from bilingual_tutor.infrastructure.logging_system import get_logger


logger = get_logger(__name__)


class AIModelType(Enum):
    """AI模型类型"""
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"
    BAICHUAN = "baichuan"
    QWEN = "qwen"


class AIResponseQuality(Enum):
    """AI响应质量"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class LanguageLevel(Enum):
    """语言级别"""
    CET4 = "CET-4"
    CET5 = "CET-5"
    CET6 = "CET-6"
    CET6_PLUS = "CET-6+"
    N5 = "N5"
    N4 = "N4"
    N3 = "N3"
    N2 = "N2"
    N1 = "N1"
    N1_PLUS = "N1+"


class ExerciseType(Enum):
    """练习类型"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    TRANSLATION = "translation"
    WRITING = "writing"


class ScenarioType(Enum):
    """场景类型"""
    DAILY = "daily"
    BUSINESS = "business"
    ACADEMIC = "academic"
    TRAVEL = "travel"


@dataclass
class AIModelConfig:
    """AI模型配置"""
    model_type: AIModelType
    api_key: str
    api_url: str
    model_name: str
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3
    priority: int = 1
    
    def validate(self) -> None:
        """验证配置"""
        if not self.api_key:
            raise ConfigurationError(f"{self.model_type.value} API密钥未配置")
        if self.max_tokens <= 0:
            raise ConfigurationError("max_tokens必须大于0")
        if not (0 <= self.temperature <= 2):
            raise ConfigurationError("temperature必须在0到2之间")


@dataclass
class AIRequest:
    """AI请求"""
    prompt: str
    system_prompt: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    language_level: Optional[LanguageLevel] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'prompt': self.prompt,
        }
        if self.system_prompt:
            result['system_prompt'] = self.system_prompt
        if self.conversation_history:
            result['conversation_history'] = self.conversation_history
        if self.max_tokens:
            result['max_tokens'] = self.max_tokens
        if self.temperature:
            result['temperature'] = self.temperature
        if self.language_level:
            result['language_level'] = self.language_level.value
        return result


@dataclass
class AIResponse:
    """AI响应"""
    content: str
    model_type: AIModelType
    model_name: str
    duration_ms: float
    tokens_used: Optional[int] = None
    quality: Optional[AIResponseQuality] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content': self.content,
            'model_type': self.model_type.value,
            'model_name': self.model_name,
            'duration_ms': self.duration_ms,
            'tokens_used': self.tokens_used,
            'quality': self.quality.value if self.quality else None,
            'request_id': self.request_id,
            'metadata': self.metadata
        }


@dataclass
class ModelPerformanceMetrics:
    """模型性能指标"""
    model_type: AIModelType
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    last_request_time: Optional[float] = None
    
    def update(self, success: bool, duration_ms: float) -> None:
        """更新指标"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_duration_ms += duration_ms
        self.average_duration_ms = self.total_duration_ms / self.total_requests
        self.last_request_time = time.time()
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_type': self.model_type.value,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.get_success_rate(),
            'average_duration_ms': self.average_duration_ms,
            'last_request_time': self.last_request_time
        }


class BaseAIModelAdapter(ABC):
    """AI模型适配器基类"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.logger = get_logger(f"{__name__}.{config.model_type.value}")
        self._metrics = ModelPerformanceMetrics(config.model_type)
    
    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """生成AI响应"""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        pass
    
    def get_metrics(self) -> ModelPerformanceMetrics:
        """获取性能指标"""
        return self._metrics
    
    def _update_metrics(self, success: bool, duration_ms: float) -> None:
        """更新性能指标"""
        self._metrics.update(success, duration_ms)


class DeepSeekAdapter(BaseAIModelAdapter):
    """DeepSeek模型适配器"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.api_url = config.api_url or "https://api.deepseek.com/v1/chat/completions"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """生成AI响应"""
        start_time = time.perf_counter()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.model_name,
                "messages": [],
                "max_tokens": request.max_tokens or self.config.max_tokens,
                "temperature": request.temperature or self.config.temperature
            }
            
            if request.system_prompt:
                payload["messages"].append({
                    "role": "system",
                    "content": request.system_prompt
                })
            
            payload["messages"].append({
                "role": "user",
                "content": request.prompt
            })
            
            if request.conversation_history:
                payload["messages"] = request.conversation_history + payload["messages"]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API请求频率限制")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ExternalServiceError(f"DeepSeek API错误: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if 'choices' not in data or len(data['choices']) == 0:
                        raise ExternalServiceError("DeepSeek API返回无效响应")
                    
                    content = data['choices'][0]['message']['content']
                    tokens_used = data.get('usage', {}).get('total_tokens')
                    
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._update_metrics(True, duration_ms)
                    
                    return AIResponse(
                        content=content,
                        model_type=AIModelType.DEEPSEEK,
                        model_name=self.config.model_name,
                        duration_ms=duration_ms,
                        tokens_used=tokens_used,
                        request_id=request.request_id
                    )
        
        except RateLimitError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except ExternalServiceError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise ExternalServiceError(f"DeepSeek请求失败: {str(e)}")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        request = AIRequest(
            prompt=messages[-1]['content'],
            conversation_history=messages[:-1],
            **kwargs
        )
        return await self.generate(request)


class ZhipuAIAdapter(BaseAIModelAdapter):
    """智谱AI模型适配器"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.api_url = config.api_url or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """生成AI响应"""
        start_time = time.perf_counter()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.model_name,
                "messages": [],
                "max_tokens": request.max_tokens or self.config.max_tokens,
                "temperature": request.temperature or self.config.temperature
            }
            
            if request.system_prompt:
                payload["messages"].append({
                    "role": "system",
                    "content": request.system_prompt
                })
            
            payload["messages"].append({
                "role": "user",
                "content": request.prompt
            })
            
            if request.conversation_history:
                payload["messages"] = request.conversation_history + payload["messages"]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API请求频率限制")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ExternalServiceError(f"智谱AI API错误: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if 'choices' not in data or len(data['choices']) == 0:
                        raise ExternalServiceError("智谱AI API返回无效响应")
                    
                    content = data['choices'][0]['message']['content']
                    tokens_used = data.get('usage', {}).get('total_tokens')
                    
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._update_metrics(True, duration_ms)
                    
                    return AIResponse(
                        content=content,
                        model_type=AIModelType.ZHIPU,
                        model_name=self.config.model_name,
                        duration_ms=duration_ms,
                        tokens_used=tokens_used,
                        request_id=request.request_id
                    )
        
        except RateLimitError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except ExternalServiceError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise ExternalServiceError(f"智谱AI请求失败: {str(e)}")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        request = AIRequest(
            prompt=messages[-1]['content'],
            conversation_history=messages[:-1],
            **kwargs
        )
        return await self.generate(request)


class BaichuanAIAdapter(BaseAIModelAdapter):
    """百川AI模型适配器"""
    
    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self.api_url = config.api_url or "https://api.baichuan-ai.com/v1/chat/completions"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """生成AI响应"""
        start_time = time.perf_counter()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.model_name,
                "messages": [],
                "max_tokens": request.max_tokens or self.config.max_tokens,
                "temperature": request.temperature or self.config.temperature
            }
            
            if request.system_prompt:
                payload["messages"].append({
                    "role": "system",
                    "content": request.system_prompt
                })
            
            payload["messages"].append({
                "role": "user",
                "content": request.prompt
            })
            
            if request.conversation_history:
                payload["messages"] = request.conversation_history + payload["messages"]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API请求频率限制")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ExternalServiceError(f"百川AI API错误: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if 'choices' not in data or len(data['choices']) == 0:
                        raise ExternalServiceError("百川AI API返回无效响应")
                    
                    content = data['choices'][0]['message']['content']
                    tokens_used = data.get('usage', {}).get('total_tokens')
                    
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._update_metrics(True, duration_ms)
                    
                    return AIResponse(
                        content=content,
                        model_type=AIModelType.BAICHUAN,
                        model_name=self.config.model_name,
                        duration_ms=duration_ms,
                        tokens_used=tokens_used,
                        request_id=request.request_id
                    )
        
        except RateLimitError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except ExternalServiceError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(False, duration_ms)
            raise ExternalServiceError(f"百川AI请求失败: {str(e)}")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> AIResponse:
        """对话模式"""
        request = AIRequest(
            prompt=messages[-1]['content'],
            conversation_history=messages[:-1],
            **kwargs
        )
        return await self.generate(request)


class AIService:
    """AI服务"""
    
    def __init__(self):
        self._adapters: Dict[AIModelType, BaseAIModelAdapter] = {}
        self._primary_model: Optional[AIModelType] = None
        self._fallback_order: List[AIModelType] = []
        self._load_models()
    
    def _load_models(self) -> None:
        """加载模型配置"""
        # DeepSeek
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
        if deepseek_key:
            config = AIModelConfig(
                model_type=AIModelType.DEEPSEEK,
                api_key=deepseek_key,
                api_url=os.environ.get('DEEPSEEK_API_URL', "https://api.deepseek.com/v1/chat/completions"),
                model_name=os.environ.get('DEEPSEEK_MODEL', "deepseek-chat"),
                priority=1
            )
            config.validate()
            self._adapters[AIModelType.DEEPSEEK] = DeepSeekAdapter(config)
            if self._primary_model is None:
                self._primary_model = AIModelType.DEEPSEEK
        
        # 智谱AI
        zhipu_key = os.environ.get('ZHIPU_API_KEY')
        if zhipu_key:
            config = AIModelConfig(
                model_type=AIModelType.ZHIPU,
                api_key=zhipu_key,
                api_url=os.environ.get('ZHIPU_API_URL', "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
                model_name=os.environ.get('ZHIPU_MODEL', "glm-4"),
                priority=2
            )
            config.validate()
            self._adapters[AIModelType.ZHIPU] = ZhipuAIAdapter(config)
        
        # 百川AI
        baichuan_key = os.environ.get('BAICHUAN_API_KEY')
        if baichuan_key:
            config = AIModelConfig(
                model_type=AIModelType.BAICHUAN,
                api_key=baichuan_key,
                api_url=os.environ.get('BAICHUAN_API_URL', "https://api.baichuan-ai.com/v1/chat/completions"),
                model_name=os.environ.get('BAICHUAN_MODEL', "Baichuan2-Turbo"),
                priority=3
            )
            config.validate()
            self._adapters[AIModelType.BAICHUAN] = BaichuanAIAdapter(config)
        
        # 设置备用顺序
        self._fallback_order = sorted(
            self._adapters.keys(),
            key=lambda m: self._adapters[m].config.priority
        )
        
        logger.info(f"AI服务初始化完成，加载了{len(self._adapters)}个模型")
        logger.info(f"主模型: {self._primary_model.value if self._primary_model else 'None'}")
    
    async def generate(self, request: AIRequest, model_type: Optional[AIModelType] = None) -> AIResponse:
        """生成AI响应（带自动切换）"""
        target_model = model_type or self._primary_model
        
        if target_model is None or target_model not in self._adapters:
            if len(self._fallback_order) == 0:
                raise ConfigurationError("没有可用的AI模型")
            target_model = self._fallback_order[0]
        
        # 尝试主模型
        try:
            adapter = self._adapters[target_model]
            response = await adapter.generate(request)
            logger.info(f"AI响应成功，模型: {target_model.value}, 耗时: {response.duration_ms:.2f}ms")
            return response
        except Exception as e:
            logger.warning(f"主模型{target_model.value}失败，尝试备用模型: {str(e)}")
            
            # 尝试备用模型
            for fallback_model in self._fallback_order:
                if fallback_model == target_model:
                    continue
                
                try:
                    adapter = self._adapters[fallback_model]
                    response = await adapter.generate(request)
                    logger.info(f"备用模型{fallback_model.value}成功，耗时: {response.duration_ms:.2f}ms")
                    return response
                except Exception as fallback_error:
                    logger.warning(f"备用模型{fallback_model.value}也失败: {str(fallback_error)}")
                    continue
            
            # 所有模型都失败
            raise ExternalServiceError("所有AI模型都不可用，请稍后重试")
    
    async def generate_with_load_balancing(self, request: AIRequest) -> AIResponse:
        """使用负载均衡策略生成AI响应"""
        if len(self._adapters) == 0:
            raise ConfigurationError("没有可用的AI模型")
        
        # 根据性能指标选择最佳模型
        best_model = self._select_best_model()
        
        try:
            adapter = self._adapters[best_model]
            response = await adapter.generate(request)
            logger.info(f"负载均衡选择模型: {best_model.value}, 耗时: {response.duration_ms:.2f}ms")
            return response
        except Exception as e:
            logger.warning(f"负载均衡选择的模型{best_model.value}失败，尝试其他模型: {str(e)}")
            # 回退到普通生成方法
            return await self.generate(request)
    
    def _select_best_model(self) -> AIModelType:
        """选择最佳模型（基于性能指标）"""
        if len(self._adapters) == 0:
            raise ConfigurationError("没有可用的AI模型")
        
        if len(self._adapters) == 1:
            return list(self._adapters.keys())[0]
        
        # 评估每个模型的性能
        model_scores = {}
        for model_type, adapter in self._adapters.items():
            metrics = adapter.get_metrics()
            
            # 计算综合得分（成功率权重0.6，响应时间权重0.4）
            success_rate = metrics.get_success_rate()
            avg_duration = metrics.average_duration_ms
            
            # 归一化响应时间（越短越好）
            duration_score = 1.0 / (1.0 + avg_duration / 1000.0) if avg_duration > 0 else 1.0
            
            # 综合得分
            score = 0.6 * success_rate + 0.4 * duration_score
            model_scores[model_type] = score
        
        # 选择得分最高的模型
        best_model = max(model_scores, key=model_scores.get)
        return best_model
    
    def get_model_health_status(self) -> Dict[str, Any]:
        """获取所有模型健康状态"""
        status = {}
        
        for model_type, adapter in self._adapters.items():
            metrics = adapter.get_metrics()
            
            # 判断健康状态
            if metrics.total_requests == 0:
                health = "unknown"
            elif metrics.get_success_rate() >= 0.95:
                health = "excellent"
            elif metrics.get_success_rate() >= 0.8:
                health = "good"
            elif metrics.get_success_rate() >= 0.5:
                health = "degraded"
            else:
                health = "poor"
            
            status[model_type.value] = {
                'health': health,
                'metrics': metrics.to_dict()
            }
        
        return status
    
    def get_recommendation(self) -> Dict[str, Any]:
        """获取模型使用建议"""
        if len(self._adapters) == 0:
            return {'recommendation': 'none', 'reason': '没有配置的模型'}
        
        health_status = self.get_model_health_status()
        
        # 检查是否有健康状态良好的模型
        healthy_models = [
            model for model, status in health_status.items()
            if status['health'] in ['excellent', 'good']
        ]
        
        if len(healthy_models) > 0:
            return {
                'recommendation': 'use_load_balancing',
                'reason': '有多个健康模型可用，建议使用负载均衡',
                'healthy_models': healthy_models
            }
        
        # 检查是否有可用模型
        available_models = [
            model for model, status in health_status.items()
            if status['health'] != 'poor'
        ]
        
        if len(available_models) > 0:
            return {
                'recommendation': 'use_primary_with_fallback',
                'reason': '模型性能一般，建议使用主模型+备用机制',
                'available_models': available_models
            }
        
        return {
            'recommendation': 'check_configuration',
            'reason': '所有模型性能较差，建议检查配置和网络'
        }
    
    async def chat(self, messages: List[Dict[str, str]], 
                 model_type: Optional[AIModelType] = None,
                 **kwargs) -> AIResponse:
        """对话模式"""
        target_model = model_type or self._primary_model
        
        if target_model is None or target_model not in self._adapters:
            if len(self._fallback_order) == 0:
                raise ConfigurationError("没有可用的AI模型")
            target_model = self._fallback_order[0]
        
        adapter = self._adapters[target_model]
        return await adapter.chat(messages, **kwargs)
    
    def get_model_metrics(self, model_type: Optional[AIModelType] = None) -> Dict[str, Any]:
        """获取模型性能指标"""
        if model_type:
            if model_type not in self._adapters:
                return {}
            return self._adapters[model_type].get_metrics().to_dict()
        
        return {
            model_type.value: adapter.get_metrics().to_dict()
            for model_type, adapter in self._adapters.items()
        }
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [model_type.value for model_type in self._adapters.keys()]
    
    def set_primary_model(self, model_type: AIModelType) -> None:
        """设置主模型"""
        if model_type not in self._adapters:
            raise ConfigurationError(f"模型{model_type.value}未配置")
        self._primary_model = model_type
        logger.info(f"主模型已设置为: {model_type.value}")


class ConversationPartner:
    """AI对话伙伴"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.logger = get_logger(f"{__name__}.ConversationPartner")
    
    async def start_conversation(self, user_level: LanguageLevel, 
                                scenario: ScenarioType = ScenarioType.DAILY,
                                topic: Optional[str] = None) -> Dict[str, Any]:
        """开始对话"""
        level_description = self._get_level_description(user_level)
        scenario_description = self._get_scenario_description(scenario)
        
        system_prompt = f"""你是一个专业的语言学习助手。你的任务是帮助用户练习{level_description}水平的{scenario_description}对话。

要求：
1. 根据用户的语言水平调整对话难度
2. 使用简单清晰的句子，避免过于复杂的词汇和语法
3. 使用中文提供必要的解释和反馈
4. 当用户犯语法错误时，温和地纠正并解释
5. 保持对话自然流畅，模拟真实场景
6. 主动引导用户表达，鼓励多说话"""

        if topic:
            system_prompt += f"\n对话主题：{topic}"
        
        prompt = f"你好！我是你的语言学习伙伴。今天我们来练习{scenario_description}对话。请告诉我你想聊什么？"
        
        request = AIRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            language_level=user_level,
            max_tokens=500
        )
        
        response = await self.ai_service.generate(request)
        
        return {
            'type': 'conversation',
            'level': user_level.value,
            'scenario': scenario.value,
            'ai_message': response.content,
            'conversation_id': self._generate_conversation_id(),
            'duration_ms': response.duration_ms
        }
    
    async def continue_conversation(self, conversation_id: str,
                                    user_message: str,
                                    conversation_history: List[Dict[str, str]],
                                    user_level: LanguageLevel) -> Dict[str, Any]:
        """继续对话"""
        system_prompt = f"""你是一个专业的语言学习助手。你的任务是帮助用户练习{self._get_level_description(user_level)}水平的对话。

要求：
1. 根据用户的语言水平调整对话难度
2. 使用简单清晰的句子
3. 使用中文提供必要的解释和反馈
4. 当用户犯语法错误时，温和地纠正并解释
5. 保持对话自然流畅
6. 主动引导用户表达"""

        request = AIRequest(
            prompt=user_message,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            language_level=user_level,
            max_tokens=500
        )
        
        response = await self.ai_service.generate(request)
        
        return {
            'type': 'conversation',
            'conversation_id': conversation_id,
            'user_message': user_message,
            'ai_message': response.content,
            'duration_ms': response.duration_ms
        }
    
    async def explain_vocabulary(self, word: str, 
                                language_level: LanguageLevel) -> Dict[str, Any]:
        """解释词汇"""
        system_prompt = f"""你是一个专业的语言学习助手。请用中文解释这个词汇的含义，并提供例句。

要求：
1. 提供{self._get_level_description(language_level)}水平的解释
2. 提供2-3个适合该水平的例句
3. 包含音标（如果是英语）或读音（如果是日语）
4. 提供常见搭配和用法
5. 用中文解释，保持简洁明了"""

        request = AIRequest(
            prompt=f"请解释词汇：{word}",
            system_prompt=system_prompt,
            language_level=language_level,
            max_tokens=400
        )
        
        response = await self.ai_service.generate(request)
        
        return {
            'type': 'vocabulary',
            'word': word,
            'explanation': response.content,
            'level': language_level.value,
            'duration_ms': response.duration_ms
        }
    
    def _get_level_description(self, level: LanguageLevel) -> str:
        """获取级别描述"""
        descriptions = {
            LanguageLevel.CET4: "大学英语四级",
            LanguageLevel.CET5: "大学英语五级",
            LanguageLevel.CET6: "大学英语六级",
            LanguageLevel.CET6_PLUS: "大学英语六级以上",
            LanguageLevel.N5: "日语N5",
            LanguageLevel.N4: "日语N4",
            LanguageLevel.N3: "日语N3",
            LanguageLevel.N2: "日语N2",
            LanguageLevel.N1: "日语N1",
            LanguageLevel.N1_PLUS: "日语N1以上"
        }
        return descriptions.get(level, "中级")
    
    def _get_scenario_description(self, scenario: ScenarioType) -> str:
        """获取场景描述"""
        descriptions = {
            ScenarioType.DAILY: "日常生活",
            ScenarioType.BUSINESS: "商务",
            ScenarioType.ACADEMIC: "学术",
            ScenarioType.TRAVEL: "旅游"
        }
        return descriptions.get(scenario, "通用")
    
    def _generate_conversation_id(self) -> str:
        """生成对话ID"""
        import uuid
        return str(uuid.uuid4())


class GrammarCorrector:
    """语法纠错器"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.logger = get_logger(f"{__name__}.GrammarCorrector")
    
    async def correct(self, text: str, 
                     language: str = "english") -> Dict[str, Any]:
        """语法纠错"""
        language_name = "英语" if language == "english" else "日语"
        
        system_prompt = f"""你是一个专业的{language_name}语法纠错助手。你的任务是检查和纠正用户输入中的语法错误。

要求：
1. 仔细检查文本中的语法错误、拼写错误和用词不当
2. 提供纠正后的文本
3. 列出所有错误，并解释错误原因
4. 使用中文进行解释
5. 提供正确的语法规则说明
6. 提供相关的例句帮助理解

输出格式（JSON）：
{{
    "is_correct": true/false,
    "corrected_text": "纠正后的文本",
    "errors": [
        {{
            "original": "错误部分",
            "correction": "纠正",
            "explanation": "错误解释（中文）",
            "rule": "语法规则"
        }}
    ]
}}"""

        request = AIRequest(
            prompt=f"请检查并纠正以下{language_name}文本的语法错误：\n{text}",
            system_prompt=system_prompt,
            max_tokens=600
        )
        
        response = await self.ai_service.generate(request)
        
        try:
            import json
            result = json.loads(response.content)
            result['duration_ms'] = response.duration_ms
            return result
        except json.JSONDecodeError:
            return {
                'is_correct': True,
                'corrected_text': text,
                'errors': [],
                'explanation': response.content,
                'duration_ms': response.duration_ms
            }


class ExerciseGenerator:
    """练习生成器"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.logger = get_logger(f"{__name__}.ExerciseGenerator")
    
    async def generate_exercise(self, weakness_areas: List[str],
                               language_level: LanguageLevel,
                               exercise_type: ExerciseType,
                               count: int = 5) -> Dict[str, Any]:
        """生成针对性练习题"""
        level_description = self._get_level_description(language_level)
        type_description = self._get_type_description(exercise_type)
        
        weakness_text = "、".join(weakness_areas) if weakness_areas else "综合练习"
        
        system_prompt = f"""你是一个专业的语言学习练习题生成器。你的任务是根据用户的薄弱环节生成针对性的练习题。

要求：
1. 练习难度应匹配{level_description}水平
2. 生成{count}道{type_description}
3. 重点关注以下薄弱领域：{weakness_text}
4. 每道题都要提供详细的答案解析
5. 题目内容要有意义，避免无意义重复
6. 使用中文提供题目说明和解析

输出格式（JSON）：
{{
    "exercise_type": "{exercise_type.value}",
    "level": "{language_level.value}",
    "target_areas": ["薄弱领域1", "薄弱领域2"],
    "questions": [
        {{
            "id": "Q1",
            "question": "题目内容",
            "options": ["选项A", "选项B", "选项C", "选项D"],
            "correct_answer": "正确答案",
            "explanation": "详细解析（中文）"
        }}
    ]
}}"""

        prompt = f"请生成{count}道针对{weakness_text}的{level_description}水平{type_description}"
        
        request = AIRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            language_level=language_level,
            max_tokens=1500
        )
        
        response = await self.ai_service.generate(request)
        
        try:
            import json
            result = json.loads(response.content)
            result['duration_ms'] = response.duration_ms
            return result
        except json.JSONDecodeError:
            return {
                'exercise_type': exercise_type.value,
                'level': language_level.value,
                'target_areas': weakness_areas,
                'questions': [],
                'error': '解析失败',
                'raw_response': response.content,
                'duration_ms': response.duration_ms
            }
    
    async def generate_batch_exercises(self, weakness_areas: Dict[str, List[str]],
                                     language_level: LanguageLevel,
                                     exercises_per_area: int = 3) -> Dict[str, Any]:
        """批量生成多种类型的练习题"""
        results = {}
        total_duration = 0.0
        
        for exercise_type in ExerciseType:
            areas = weakness_areas.get(exercise_type.value, weakness_areas.get('general', []))
            
            result = await self.generate_exercise(
                weakness_areas=areas,
                language_level=language_level,
                exercise_type=exercise_type,
                count=exercises_per_area
            )
            
            results[exercise_type.value] = result
            total_duration += result.get('duration_ms', 0)
        
        return {
            'batch': True,
            'level': language_level.value,
            'total_duration_ms': total_duration,
            'exercises': results
        }
    
    def _get_level_description(self, level: LanguageLevel) -> str:
        """获取级别描述"""
        descriptions = {
            LanguageLevel.CET4: "大学英语四级",
            LanguageLevel.CET5: "大学英语五级",
            LanguageLevel.CET6: "大学英语六级",
            LanguageLevel.CET6_PLUS: "大学英语六级以上",
            LanguageLevel.N5: "日语N5",
            LanguageLevel.N4: "日语N4",
            LanguageLevel.N3: "日语N3",
            LanguageLevel.N2: "日语N2",
            LanguageLevel.N1: "日语N1",
            LanguageLevel.N1_PLUS: "日语N1以上"
        }
        return descriptions.get(level, "中级")
    
    def _get_type_description(self, exercise_type: ExerciseType) -> str:
        """获取练习类型描述"""
        descriptions = {
            ExerciseType.MULTIPLE_CHOICE: "选择题",
            ExerciseType.FILL_BLANK: "填空题",
            ExerciseType.TRANSLATION: "翻译题",
            ExerciseType.WRITING: "写作题"
        }
        return descriptions.get(exercise_type, "练习题")


# 全局AI服务实例
_global_ai_service: Optional[AIService] = None
_global_conversation_partner: Optional[ConversationPartner] = None
_global_grammar_corrector: Optional[GrammarCorrector] = None
_global_exercise_generator: Optional[ExerciseGenerator] = None


def get_ai_service() -> AIService:
    """获取AI服务单例"""
    global _global_ai_service
    if _global_ai_service is None:
        _global_ai_service = AIService()
    return _global_ai_service


def get_conversation_partner() -> ConversationPartner:
    """获取对话伙伴单例"""
    global _global_conversation_partner
    if _global_conversation_partner is None:
        _global_conversation_partner = ConversationPartner(get_ai_service())
    return _global_conversation_partner


def get_grammar_corrector() -> GrammarCorrector:
    """获取语法纠错器单例"""
    global _global_grammar_corrector
    if _global_grammar_corrector is None:
        _global_grammar_corrector = GrammarCorrector(get_ai_service())
    return _global_grammar_corrector


def get_exercise_generator() -> ExerciseGenerator:
    """获取练习生成器单例"""
    global _global_exercise_generator
    if _global_exercise_generator is None:
        _global_exercise_generator = ExerciseGenerator(get_ai_service())
    return _global_exercise_generator
