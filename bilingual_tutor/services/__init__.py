"""
AI services for the bilingual tutor system.
包含大语言模型服务、智能内容生成等AI相关服务。
"""

from .ai_service import (
    AIModelType,
    AIResponseQuality,
    LanguageLevel,
    AIModelConfig,
    AIRequest,
    AIResponse,
    ModelPerformanceMetrics,
    BaseAIModelAdapter,
    DeepSeekAdapter,
    ZhipuAIAdapter,
    AIService,
    get_ai_service
)

__all__ = [
    'AIModelType',
    'AIResponseQuality',
    'LanguageLevel',
    'AIModelConfig',
    'AIRequest',
    'AIResponse',
    'ModelPerformanceMetrics',
    'BaseAIModelAdapter',
    'DeepSeekAdapter',
    'ZhipuAIAdapter',
    'AIService',
    'get_ai_service'
]
