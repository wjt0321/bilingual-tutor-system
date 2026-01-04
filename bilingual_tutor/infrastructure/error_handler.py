"""
双语导师系统 - 统一错误处理器
Bilingual Tutor System - Unified Error Handler

实现统一的异常处理机制，提供用户友好的中文错误消息和恢复建议。
"""

import sys
import traceback
import functools
from typing import Callable, Dict, Any, Optional, Type, Tuple
from enum import Enum
from datetime import datetime
import logging


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BilingualTutorError(Exception):
    """双语导师系统基础异常类"""
    
    def __init__(self, 
                 message_cn: str, 
                 message_en: str = "",
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recovery_suggestion: Optional[str] = None):
        self.message_cn = message_cn
        self.message_en = message_en or message_cn
        self.severity = severity
        self.recovery_suggestion = recovery_suggestion
        self.timestamp = datetime.now()
        super().__init__(self.message_cn)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message_cn': self.message_cn,
            'message_en': self.message_en,
            'severity': self.severity.value,
            'recovery_suggestion': self.recovery_suggestion,
            'timestamp': self.timestamp.isoformat()
        }


class DatabaseError(BilingualTutorError):
    """数据库相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "请检查数据库连接和配置，或稍后重试。"
        super().__init__(message_cn, message_en, ErrorSeverity.ERROR, recovery_suggestion)


class CacheError(BilingualTutorError):
    """缓存相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "缓存服务暂时不可用，将自动使用数据库。"
        super().__init__(message_cn, message_en, ErrorSeverity.WARNING, recovery_suggestion)


class ValidationError(BilingualTutorError):
    """数据验证错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "请检查输入数据是否符合要求。"
        super().__init__(message_cn, message_en, ErrorSeverity.WARNING, recovery_suggestion)


class ContentError(BilingualTutorError):
    """内容相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "请尝试选择其他学习内容或稍后重试。"
        super().__init__(message_cn, message_en, ErrorSeverity.WARNING, recovery_suggestion)


class AudioError(BilingualTutorError):
    """音频相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "音频播放失败，请检查音频文件或稍后重试。"
        super().__init__(message_cn, message_en, ErrorSeverity.WARNING, recovery_suggestion)


class AuthenticationError(BilingualTutorError):
    """认证相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "请检查用户名和密码，或重新登录。"
        super().__init__(message_cn, message_en, ErrorSeverity.ERROR, recovery_suggestion)


class AuthorizationError(BilingualTutorError):
    """授权相关错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "您没有权限执行此操作，请联系管理员。"
        super().__init__(message_cn, message_en, ErrorSeverity.ERROR, recovery_suggestion)


class RateLimitError(BilingualTutorError):
    """请求频率限制错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "请求过于频繁，请稍后再试。"
        super().__init__(message_cn, message_en, ErrorSeverity.WARNING, recovery_suggestion)


class ExternalServiceError(BilingualTutorError):
    """外部服务错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "外部服务暂时不可用，请稍后重试。"
        super().__init__(message_cn, message_en, ErrorSeverity.ERROR, recovery_suggestion)


class ConfigurationError(BilingualTutorError):
    """配置错误"""
    
    def __init__(self, message_cn: str, message_en: str = "", recovery_suggestion: Optional[str] = None):
        if recovery_suggestion is None:
            recovery_suggestion = "系统配置有误，请联系管理员。"
        super().__init__(message_cn, message_en, ErrorSeverity.CRITICAL, recovery_suggestion)


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志"""
        error_type = type(error).__name__
        
        # 统计错误次数
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 构建日志消息
        log_message = f"Error [{error_type}]: {str(error)}"
        if context:
            log_message += f" | Context: {context}"
        
        # 根据错误严重程度记录日志
        if isinstance(error, BilingualTutorError):
            severity = error.severity
            error_dict = error.to_dict()
            
            if severity == ErrorSeverity.CRITICAL:
                self.logger.critical(log_message, extra=error_dict)
            elif severity == ErrorSeverity.ERROR:
                self.logger.error(log_message, extra=error_dict)
            elif severity == ErrorSeverity.WARNING:
                self.logger.warning(log_message, extra=error_dict)
            else:
                self.logger.info(log_message, extra=error_dict)
        else:
            self.logger.error(log_message, exc_info=True)
    
    def get_error_response(self, error: Exception, language: str = 'cn') -> Dict[str, Any]:
        """获取标准化的错误响应"""
        if isinstance(error, BilingualTutorError):
            error_dict = error.to_dict()
            response = {
                'success': False,
                'error': error_dict['error_type'],
                'message': error_dict['message_cn'] if language == 'cn' else error_dict['message_en'],
                'severity': error_dict['severity'],
                'recovery_suggestion': error_dict['recovery_suggestion']
            }
            
            # 根据严重程度设置HTTP状态码
            if error.severity == ErrorSeverity.CRITICAL:
                response['status_code'] = 500
            elif error.severity == ErrorSeverity.ERROR:
                response['status_code'] = 400
            else:
                response['status_code'] = 200
        else:
            # 处理未知异常
            self.logger.error(f"Unhandled exception: {type(error).__name__}: {str(error)}", exc_info=True)
            response = {
                'success': False,
                'error': 'InternalServerError',
                'message': '系统内部错误' if language == 'cn' else 'Internal server error',
                'severity': 'error',
                'recovery_suggestion': '请稍后重试，如果问题持续，请联系管理员。',
                'status_code': 500
            }
        
        return response
    
    def get_user_friendly_message(self, error: Exception, language: str = 'cn') -> str:
        """获取用户友好的错误消息"""
        if isinstance(error, BilingualTutorError):
            message = error.message_cn if language == 'cn' else error.message_en
            
            # 添加恢复建议
            if error.recovery_suggestion:
                message += f"\n\n💡 建议: {error.recovery_suggestion}"
            
            return message
        else:
            return "系统遇到意外错误，请稍后重试。" if language == 'cn' else "An unexpected error occurred. Please try again later."
    
    def get_error_statistics(self) -> Dict[str, int]:
        """获取错误统计信息"""
        return self.error_counts.copy()
    
    def reset_error_statistics(self) -> None:
        """重置错误统计"""
        self.error_counts.clear()


def handle_errors(
    default_error_message_cn: str = "操作失败，请稍后重试。",
    default_error_message_en: str = "Operation failed, please try again later.",
    return_type: Optional[str] = None
):
    """错误处理装饰器
    
    Args:
        default_error_message_cn: 默认中文错误消息
        default_error_message_en: 默认英文错误消息
        return_type: 返回类型 ('dict' or 'tuple')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BilingualTutorError as e:
                error_handler = ErrorHandler()
                error_handler.log_error(e, {'function': func.__name__})
                
                if return_type == 'dict':
                    return error_handler.get_error_response(e)
                elif return_type == 'tuple':
                    response = error_handler.get_error_response(e)
                    return response, response.get('status_code', 400)
                else:
                    raise
            except Exception as e:
                error_handler = ErrorHandler()
                error_handler.log_error(e, {'function': func.__name__})
                
                # 转换为标准错误
                wrapped_error = BilingualTutorError(
                    default_error_message_cn,
                    default_error_message_en,
                    ErrorSeverity.ERROR,
                    "请稍后重试，如果问题持续，请联系管理员。"
                )
                
                if return_type == 'dict':
                    return error_handler.get_error_response(wrapped_error)
                elif return_type == 'tuple':
                    response = error_handler.get_error_response(wrapped_error)
                    return response, response.get('status_code', 500)
                else:
                    raise wrapped_error
        return wrapper
    return decorator


class ErrorContext:
    """错误上下文管理器"""
    
    def __init__(self, 
                 operation_name: str,
                 error_handler: Optional[ErrorHandler] = None):
        self.operation_name = operation_name
        self.error_handler = error_handler or ErrorHandler()
        self.success = False
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            self.error_handler.log_error(
                exc_val,
                {'operation': self.operation_name}
            )
            return False  # 不抑制异常
        else:
            self.success = True
            return True
    
    def get_result(self) -> Dict[str, Any]:
        """获取操作结果"""
        return {
            'operation': self.operation_name,
            'success': self.success,
            'error': str(self.error) if self.error else None,
            'error_type': type(self.error).__name__ if self.error else None
        }


def create_error_handler(logger: Optional[logging.Logger] = None) -> ErrorHandler:
    """创建错误处理器实例的工厂函数"""
    return ErrorHandler(logger)


# 全局错误处理器实例
global_error_handler = ErrorHandler()
