"""
测试统一错误处理器
Test Unified Error Handler

属性47: 错误消息本地化
属性48: 异常层次结构一致性

验证需求: 22.1, 22.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Type, List
import logging

from bilingual_tutor.infrastructure.error_handler import (
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
    ErrorContext
)


class TestErrorMessageLocalization:
    """属性47: 错误消息本地化"""
    
    @pytest.mark.parametrize("error_class,expected_recovery_cn", [
        (DatabaseError, "请检查数据库连接和配置，或稍后重试。"),
        (CacheError, "缓存服务暂时不可用，将自动使用数据库。"),
        (ValidationError, "请检查输入数据是否符合要求。"),
        (ContentError, "请尝试选择其他学习内容或稍后重试。"),
        (AudioError, "音频播放失败，请检查音频文件或稍后重试。"),
        (AuthenticationError, "请检查用户名和密码，或重新登录。"),
        (AuthorizationError, "您没有权限执行此操作，请联系管理员。"),
        (RateLimitError, "请求过于频繁，请稍后再试。"),
        (ExternalServiceError, "外部服务暂时不可用，请稍后重试。"),
        (ConfigurationError, "系统配置有误，请联系管理员。"),
    ])
    def test_default_recovery_suggestion_cn(self, error_class, expected_recovery_cn):
        """验证所有错误类型都有中文恢复建议"""
        error = error_class("测试错误")
        assert error.recovery_suggestion == expected_recovery_cn
    
    @pytest.mark.parametrize("language", ['cn', 'en'])
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_error_message_language_support(self, language, message_cn):
        """验证错误消息支持中英文"""
        message_en = "Test error message"
        error = BilingualTutorError(message_cn, message_en)
        
        error_dict = error.to_dict()
        assert error_dict['message_cn'] == message_cn
        assert error_dict['message_en'] == message_en
    
    @given(st.text(min_size=1, max_size=100), st.text(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_fallback_english_message(self, message_cn, message_en):
        """验证英文消息的回退机制"""
        error = BilingualTutorError(message_cn, message_en if message_en else None)
        
        error_dict = error.to_dict()
        assert error_dict['message_cn'] == message_cn
        assert error_dict['message_en'] == message_cn if not message_en else message_en
    
    @pytest.mark.parametrize("language", ['cn', 'en'])
    @given(st.sampled_from([DatabaseError, CacheError, ValidationError, ContentError, AudioError]))
    @settings(max_examples=50)
    def test_error_handler_language_support(self, language, error_class):
        """验证错误处理器支持语言切换"""
        error = error_class("测试错误", "Test error")
        handler = ErrorHandler()
        
        response_cn = handler.get_error_response(error, language='cn')
        response_en = handler.get_error_response(error, language='en')
        
        assert 'message' in response_cn
        assert 'message' in response_en
        assert 'recovery_suggestion' in response_cn
        assert 'recovery_suggestion' in response_en
        
        if language == 'cn':
            assert '请' in response_cn['message'] or '测试' in response_cn['message']
        else:
            assert 'Test' in response_en['message']
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_user_friendly_message_includes_recovery(self, message_cn):
        """验证用户友好消息包含恢复建议"""
        recovery_suggestion = "尝试重启应用"
        error = BilingualTutorError(message_cn, recovery_suggestion=recovery_suggestion)
        handler = ErrorHandler()
        
        friendly_message = handler.get_user_friendly_message(error, language='cn')
        assert message_cn in friendly_message
        assert recovery_suggestion in friendly_message
        assert '💡 建议:' in friendly_message


class TestExceptionHierarchyConsistency:
    """属性48: 异常层次结构一致性"""
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    def test_all_errors_inherit_from_base(self, error_class):
        """验证所有错误类都继承自基础异常类"""
        error = error_class("测试错误")
        assert isinstance(error, BilingualTutorError)
        assert isinstance(error, Exception)
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    @given(st.text(min_size=1, max_size=50), st.text(min_size=0, max_size=50))
    @settings(max_examples=50)
    def test_all_errors_have_required_attributes(self, error_class, message_cn, message_en):
        """验证所有错误类都有必需的属性"""
        error = error_class(message_cn, message_en)
        
        assert hasattr(error, 'message_cn')
        assert hasattr(error, 'message_en')
        assert hasattr(error, 'severity')
        assert hasattr(error, 'recovery_suggestion')
        assert hasattr(error, 'timestamp')
        assert hasattr(error, 'to_dict')
    
    @pytest.mark.parametrize("error_class,expected_severity", [
        (DatabaseError, ErrorSeverity.ERROR),
        (CacheError, ErrorSeverity.WARNING),
        (ValidationError, ErrorSeverity.WARNING),
        (ContentError, ErrorSeverity.WARNING),
        (AudioError, ErrorSeverity.WARNING),
        (AuthenticationError, ErrorSeverity.ERROR),
        (AuthorizationError, ErrorSeverity.ERROR),
        (RateLimitError, ErrorSeverity.WARNING),
        (ExternalServiceError, ErrorSeverity.ERROR),
        (ConfigurationError, ErrorSeverity.CRITICAL),
    ])
    def test_default_severity_levels(self, error_class, expected_severity):
        """验证每个错误类型的默认严重程度"""
        error = error_class("测试错误")
        assert error.severity == expected_severity
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    def test_to_dict_consistency(self, error_class):
        """验证所有错误类的to_dict方法返回一致的格式"""
        error = error_class("测试错误", "Test error")
        error_dict = error.to_dict()
        
        required_keys = [
            'error_type',
            'message_cn',
            'message_en',
            'severity',
            'recovery_suggestion',
            'timestamp'
        ]
        
        for key in required_keys:
            assert key in error_dict
        
        assert error_dict['error_type'] == error_class.__name__
        assert isinstance(error_dict['severity'], str)
        assert isinstance(error_dict['timestamp'], str)
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    def test_exception_can_be_raised_and_caught(self, error_class):
        """验证异常可以被抛出和捕获"""
        with pytest.raises(BilingualTutorError):
            raise error_class("测试错误")
        
        with pytest.raises(error_class):
            raise error_class("测试错误")


class TestErrorHandlerFunctionality:
    """测试错误处理器的核心功能"""
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    def test_error_logging(self, error_class, caplog):
        """验证错误被正确记录"""
        error = error_class("测试错误")
        handler = ErrorHandler()
        
        with caplog.at_level(logging.INFO):
            handler.log_error(error, {'test_context': 'test'})
        
        assert len(caplog.records) > 0
    
    def test_error_statistics(self):
        """验证错误统计功能"""
        handler = ErrorHandler()
        
        handler.log_error(DatabaseError("错误1"))
        handler.log_error(CacheError("错误2"))
        handler.log_error(DatabaseError("错误3"))
        
        stats = handler.get_error_statistics()
        assert stats.get('DatabaseError', 0) == 2
        assert stats.get('CacheError', 0) == 1
    
    def test_error_statistics_reset(self):
        """验证错误统计重置功能"""
        handler = ErrorHandler()
        
        handler.log_error(DatabaseError("错误1"))
        assert handler.get_error_statistics().get('DatabaseError', 0) == 1
        
        handler.reset_error_statistics()
        assert handler.get_error_statistics().get('DatabaseError', 0) == 0
    
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_unknown_exception_handling(self, message):
        """验证未知异常的处理"""
        handler = ErrorHandler()
        
        try:
            raise ValueError(message)
        except Exception as e:
            response = handler.get_error_response(e, language='cn')
            
            assert response['success'] == False
            assert 'message' in response
            assert response.get('status_code', 500) == 500
    
    @pytest.mark.parametrize("severity,expected_status", [
        (ErrorSeverity.CRITICAL, 500),
        (ErrorSeverity.ERROR, 400),
        (ErrorSeverity.WARNING, 200),
        (ErrorSeverity.INFO, 200),
    ])
    def test_status_code_mapping(self, severity, expected_status):
        """验证严重程度到HTTP状态码的映射"""
        error = BilingualTutorError("测试", severity=severity)
        handler = ErrorHandler()
        
        response = handler.get_error_response(error)
        assert response['status_code'] == expected_status


class TestErrorHandlingDecorator:
    """测试错误处理装饰器"""
    
    def test_decorator_handles_bilingual_tutor_errors(self):
        """验证装饰器处理双语导师错误"""
        @handle_errors(return_type='dict')
        def test_function():
            raise DatabaseError("数据库错误")
        
        result = test_function()
        assert result['success'] == False
        assert 'DatabaseError' in result.get('error', '')
    
    def test_decorator_handles_unknown_errors(self):
        """验证装饰器处理未知错误"""
        @handle_errors(return_type='dict')
        def test_function():
            raise ValueError("未知错误")
        
        result = test_function()
        assert result['success'] == False
    
    def test_decorator_returns_tuple(self):
        """验证装饰器返回元组格式"""
        @handle_errors(return_type='tuple')
        def test_function():
            raise DatabaseError("数据库错误")
        
        result, status_code = test_function()
        assert isinstance(result, dict)
        assert isinstance(status_code, int)
    
    def test_decorator_allows_success(self):
        """验证装饰器不干扰正常执行"""
        @handle_errors(return_type='dict')
        def test_function():
            return {'success': True, 'data': 'test'}
        
        result = test_function()
        assert result['success'] == True
        assert result['data'] == 'test'


class TestErrorContext:
    """测试错误上下文管理器"""
    
    def test_successful_operation(self):
        """验证成功操作的上下文"""
        with ErrorContext("test_operation") as context:
            result = context.get_result()
            assert context.success is False
        
        result = context.get_result()
        assert result['success'] == True
        assert result['error'] is None
    
    def test_failed_operation(self):
        """验证失败操作的上下文"""
        with pytest.raises(ValueError):
            with ErrorContext("test_operation") as context:
                raise ValueError("测试错误")
        
        result = context.get_result()
        assert result['success'] == False
        assert result['error'] is not None
        assert result['error_type'] == 'ValueError'


class TestErrorRecoveryIntegration:
    """测试错误恢复集成"""
    
    @pytest.mark.parametrize("error_class", [
        DatabaseError,
        CacheError,
        ValidationError,
        ContentError,
        AudioError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
        ConfigurationError
    ])
    def test_all_errors_have_recovery_suggestion(self, error_class):
        """验证所有错误都有恢复建议"""
        error = error_class("测试错误")
        assert error.recovery_suggestion is not None
        assert len(error.recovery_suggestion) > 0
    
    @given(st.sampled_from([DatabaseError, CacheError, ValidationError, ContentError, AudioError]))
    @settings(max_examples=50)
    def test_recovery_suggestion_in_response(self, error_class):
        """验证恢复建议包含在响应中"""
        error = error_class("测试错误")
        handler = ErrorHandler()
        
        response = handler.get_error_response(error)
        assert 'recovery_suggestion' in response
        assert len(response['recovery_suggestion']) > 0
    
    def test_custom_recovery_suggestion(self):
        """验证自定义恢复建议"""
        custom_suggestion = "自定义恢复建议"
        error = BilingualTutorError("测试", recovery_suggestion=custom_suggestion)
        
        assert error.recovery_suggestion == custom_suggestion
        
        handler = ErrorHandler()
        response = handler.get_error_response(error)
        assert response['recovery_suggestion'] == custom_suggestion
