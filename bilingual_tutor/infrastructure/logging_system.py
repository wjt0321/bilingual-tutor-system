"""
双语导师系统 - 统一日志系统
Bilingual Tutor System - Unified Logging System

实现结构化日志记录、日志级别管理、文件轮转、性能指标和用户行为记录。
"""

import os
import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from functools import wraps
import time
from contextlib import contextmanager
from threading import Lock
from dataclasses import dataclass, asdict

from bilingual_tutor.infrastructure.config_manager import LoggingConfig, get_config
from bilingual_tutor.infrastructure.error_handler import ConfigurationError


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UserAction:
    """用户行为记录"""
    user_id: Optional[str]
    action: str
    resource: Optional[str] = None
    method: Optional[str] = None
    success: bool = True
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, 
                 structured: bool = False):
        super().__init__(fmt, datefmt)
        self.structured = structured
    
    def format(self, record: logging.LogRecord) -> str:
        if self.structured:
            return self._format_structured(record)
        else:
            return super().format(record)
    
    def _format_structured(self, record: logging.LogRecord) -> str:
        """格式化为结构化JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None
            }
        
        # 添加额外字段
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        return json.dumps(log_data, ensure_ascii=False)


class PerformanceLogger:
    """性能指标记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics: Dict[str, list] = {}
        self._lock = Lock()
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """记录性能指标"""
        with self._lock:
            if metric.name not in self.metrics:
                self.metrics[metric.name] = []
            self.metrics[metric.name].append(metric)
        
        metric_dict = {
            'metric_type': 'performance',
            'name': metric.name,
            'value': metric.value,
            'unit': metric.unit,
            'timestamp': metric.timestamp,
            'metadata': metric.metadata
        }
        
        self.logger.info(json.dumps(metric_dict, ensure_ascii=False), extra={
            'metric': True
        })
    
    def get_metrics(self, metric_name: Optional[str] = None) -> list:
        """获取性能指标"""
        with self._lock:
            if metric_name:
                return self.metrics.get(metric_name, [])
            return sum(self.metrics.values(), [])
    
    def clear_metrics(self) -> None:
        """清除性能指标"""
        with self._lock:
            self.metrics.clear()
    
    @contextmanager
    def measure_performance(self, name: str, unit: str = 'ms', metadata: Optional[Dict[str, Any]] = None):
        """测量性能上下文管理器"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            metric = PerformanceMetric(
                name=name,
                value=duration,
                unit=unit,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            self.record_metric(metric)


class UserActionLogger:
    """用户行为记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.actions: list = []
        self._lock = Lock()
    
    def log_action(self, action: UserAction) -> None:
        """记录用户行为"""
        with self._lock:
            self.actions.append(action)
        
        action_dict = asdict(action)
        action_dict['action_type'] = 'user_action'
        
        self.logger.info(json.dumps(action_dict, ensure_ascii=False), extra={
            'action': True
        })
    
    def get_actions(self, user_id: Optional[str] = None, 
                   action_type: Optional[str] = None) -> list:
        """获取用户行为"""
        with self._lock:
            filtered = self.actions
            if user_id:
                filtered = [a for a in filtered if a.user_id == user_id]
            if action_type:
                filtered = [a for a in filtered if a.action == action_type]
            return filtered
    
    def clear_actions(self) -> None:
        """清除用户行为记录"""
        with self._lock:
            self.actions.clear()


class BilingualTutorLogger:
    """双语导师系统日志器"""
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or get_config().logging
        self.logger = logging.getLogger('bilingual_tutor')
        self._initialized = False
        self._lock = Lock()
        
        self.performance_logger: Optional[PerformanceLogger] = None
        self.user_action_logger: Optional[UserActionLogger] = None
        
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """设置日志器"""
        with self._lock:
            if self._initialized:
                return
            
            # 清除现有处理器
            self.logger.handlers.clear()
            
            # 设置日志级别
            level = getattr(logging, self.config.level.upper(), logging.INFO)
            self.logger.setLevel(level)
            
            # 创建格式化器
            formatter = StructuredFormatter(
                fmt=self.config.format,
                datefmt=self.config.date_format,
                structured=self.config.structured
            )
            
            # 添加文件处理器
            if self.config.file_enabled:
                self._add_file_handler(formatter, level)
            
            # 添加控制台处理器
            if self.config.console_enabled:
                self._add_console_handler(formatter, level)
            
            # 初始化性能和用户行为记录器
            self.performance_logger = PerformanceLogger(self.logger)
            self.user_action_logger = UserActionLogger(self.logger)
            
            self._initialized = True
    
    def _add_file_handler(self, formatter: StructuredFormatter, level: int) -> None:
        """添加文件处理器"""
        log_path = Path(self.config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建文件处理器，带轮转
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.config.file_path,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _add_console_handler(self, formatter: StructuredFormatter, level: int) -> None:
        """添加控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """获取日志器"""
        return self.logger
    
    def get_performance_logger(self) -> PerformanceLogger:
        """获取性能记录器"""
        return self.performance_logger
    
    def get_user_action_logger(self) -> UserActionLogger:
        """获取用户行为记录器"""
        return self.user_action_logger
    
    def reload_config(self, config: LoggingConfig) -> None:
        """重新加载配置"""
        self.config = config
        self._initialized = False
        self._setup_logger()
    
    def shutdown(self) -> None:
        """关闭日志器"""
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()
        self._initialized = False


class LoggingMixin:
    """日志记录混入类"""
    
    @staticmethod
    def log_performance(func: Callable) -> Callable:
        """性能记录装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                
                # 记录性能
                logger = logging.getLogger('bilingual_tutor')
                metric = {
                    'metric_type': 'function_performance',
                    'function': func.__name__,
                    'module': func.__module__,
                    'duration_ms': duration * 1000,
                    'timestamp': datetime.now().isoformat()
                }
                logger.debug(json.dumps(metric, ensure_ascii=False))
                
                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                logger = logging.getLogger('bilingual_tutor')
                error_metric = {
                    'metric_type': 'function_error',
                    'function': func.__name__,
                    'module': func.__module__,
                    'duration_ms': duration * 1000,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(json.dumps(error_metric, ensure_ascii=False))
                raise
        
        return wrapper
    
    @staticmethod
    def log_user_action(action: str, resource: Optional[str] = None,
                      method: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """记录用户行为的装饰器工厂"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # 尝试获取用户ID
                user_id = None
                if hasattr(self, 'user_id'):
                    user_id = self.user_id
                
                start_time = time.perf_counter()
                success = True
                
                try:
                    result = func(self, *args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    user_action = UserAction(
                        user_id=user_id,
                        action=action,
                        resource=resource,
                        method=method,
                        success=success,
                        duration_ms=duration * 1000 if success else None,
                        metadata=metadata or {}
                    )
                    
                    logger = logging.getLogger('bilingual_tutor')
                    action_dict = asdict(user_action)
                    action_dict['action_type'] = 'user_action'
                    
                    logger.info(json.dumps(action_dict, ensure_ascii=False))
            
            return wrapper
        return decorator


# 全局日志器实例
_global_logger: Optional[BilingualTutorLogger] = None
_logger_lock = Lock()


def get_logging_system(config: Optional[LoggingConfig] = None) -> BilingualTutorLogger:
    """获取日志系统单例"""
    global _global_logger
    
    with _logger_lock:
        if _global_logger is None:
            _global_logger = BilingualTutorLogger(config)
    
    return _global_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志器的便捷函数"""
    system = get_logging_system()
    base_logger = system.get_logger()
    
    if name:
        return base_logger.getChild(name)
    return base_logger


def log_performance(metric_name: str, value: float, unit: str = 'ms',
                 metadata: Optional[Dict[str, Any]] = None) -> None:
    """记录性能指标的便捷函数"""
    system = get_logging_system()
    metric = PerformanceMetric(
        name=metric_name,
        value=value,
        unit=unit,
        timestamp=datetime.now().isoformat(),
        metadata=metadata or {}
    )
    system.performance_logger.record_metric(metric)


def log_user_action(action: UserAction) -> None:
    """记录用户行为的便捷函数"""
    system = get_logging_system()
    system.user_action_logger.log_action(action)


@contextmanager
def measure_performance(metric_name: str, unit: str = 'ms',
                    metadata: Optional[Dict[str, Any]] = None):
    """测量性能的上下文管理器"""
    system = get_logging_system()
    with system.performance_logger.measure_performance(metric_name, unit, metadata):
        yield
