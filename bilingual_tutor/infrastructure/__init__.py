"""
Infrastructure components for the bilingual tutor system.
包含缓存管理、配置管理、日志系统等基础设施组件。
"""

from .error_handler import (
    BilingualTutorError,
    DatabaseError,
    CacheError,
    ValidationError,
    ContentError,
    AudioError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ExternalServiceError,
    ConfigurationError,
    ErrorHandler,
    ErrorSeverity,
    handle_errors,
    ErrorContext,
    create_error_handler,
    global_error_handler
)

from .config_manager import (
    DatabaseConfig,
    CacheConfig,
    WebConfig,
    LearningConfig,
    LoggingConfig,
    ApplicationConfig,
    ConfigManager,
    get_config_manager,
    get_config,
    encrypt_sensitive_value,
    decrypt_sensitive_value,
    is_encrypted_value
)

from .logging_system import (
    StructuredFormatter,
    PerformanceMetric,
    UserAction,
    PerformanceLogger,
    UserActionLogger,
    BilingualTutorLogger,
    LoggingMixin,
    get_logging_system,
    get_logger,
    log_performance,
    log_user_action,
    measure_performance
)

__all__ = [
    'BilingualTutorError',
    'DatabaseError',
    'CacheError',
    'ValidationError',
    'ContentError',
    'AudioError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'ExternalServiceError',
    'ConfigurationError',
    'ErrorHandler',
    'ErrorSeverity',
    'handle_errors',
    'ErrorContext',
    'create_error_handler',
    'global_error_handler',
    'DatabaseConfig',
    'CacheConfig',
    'WebConfig',
    'LearningConfig',
    'LoggingConfig',
    'ApplicationConfig',
    'ConfigManager',
    'get_config_manager',
    'get_config',
    'encrypt_sensitive_value',
    'decrypt_sensitive_value',
    'is_encrypted_value',
    'StructuredFormatter',
    'PerformanceMetric',
    'UserAction',
    'PerformanceLogger',
    'UserActionLogger',
    'BilingualTutorLogger',
    'LoggingMixin',
    'get_logging_system',
    'get_logger',
    'log_performance',
    'log_user_action',
    'measure_performance'
]