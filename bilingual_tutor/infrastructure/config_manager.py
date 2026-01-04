"""
双语导师系统 - 统一配置管理器
Bilingual Tutor System - Unified Configuration Manager

实现YAML配置文件支持、环境变量覆盖、配置验证、敏感信息加密和热重载功能。
"""

import os
import yaml
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, get_type_hints
from dataclasses import dataclass, field, asdict
from functools import lru_cache
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from threading import Lock

from bilingual_tutor.infrastructure.error_handler import (
    ConfigurationError,
    ValidationError,
    global_error_handler
)


logger = logging.getLogger(__name__)


class ConfigValidationError(ValidationError):
    """配置验证错误"""
    pass


class EncryptionError(ConfigurationError):
    """加密相关错误"""
    pass


T = TypeVar('T')


def encrypt_sensitive_value(value: str, key: Optional[bytes] = None) -> str:
    """加密敏感值
    
    Args:
        value: 要加密的值
        key: 加密密钥，如果为None则使用环境变量中的密钥
    
    Returns:
        加密后的值（base64编码）
    """
    if key is None:
        key_str = os.environ.get('CONFIG_ENCRYPTION_KEY', 'default-key-change-in-production')
        key_bytes = key_str.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'bilingual-tutor-salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
    
    try:
        f = Fernet(key)
        encrypted = f.encrypt(value.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        raise EncryptionError(f"加密失败: {str(e)}")


def decrypt_sensitive_value(encrypted_value: str, key: Optional[bytes] = None) -> str:
    """解密敏感值
    
    Args:
        encrypted_value: 加密的值
        key: 解密密钥
    
    Returns:
        解密后的值
    """
    if key is None:
        key_str = os.environ.get('CONFIG_ENCRYPTION_KEY', 'default-key-change-in-production')
        key_bytes = key_str.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'bilingual-tutor-salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
    
    try:
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_value.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        raise EncryptionError(f"解密失败: {str(e)}")


def is_encrypted_value(value: str) -> bool:
    """检查值是否为加密值"""
    try:
        encrypted_bytes = base64.urlsafe_b64decode(value.encode('utf-8'))
        return len(encrypted_bytes) > 0 and (value.startswith('g3A==') or value.startswith('gAAA'))
    except:
        return False


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = 'sqlite'
    path: str = 'bilingual_tutor/storage/learning.db'
    
    # MySQL/PostgreSQL 配置（如果使用）
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    
    # 连接池配置
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    
    # 加密字段
    _encrypted_fields: set = field(default_factory=lambda: {'password'})
    
    def validate(self) -> None:
        """验证数据库配置"""
        if self.type not in ['sqlite', 'mysql', 'postgresql']:
            raise ConfigValidationError(f"不支持的数据库类型: {self.type}")
        
        if self.type == 'sqlite':
            if not self.path:
                raise ConfigValidationError("SQLite需要指定数据库路径")
        else:
            if not all([self.host, self.port, self.username, self.database]):
                raise ConfigValidationError(f"{self.type}需要完整的连接信息")


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    type: str = 'redis'
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    # 缓存策略
    default_ttl: int = 3600  # 秒
    max_memory: str = '256mb'
    eviction_policy: str = 'allkeys-lru'
    
    # 加密字段
    _encrypted_fields: set = field(default_factory=lambda: {'password'})
    
    def validate(self) -> None:
        """验证缓存配置"""
        if self.type not in ['redis', 'memory']:
            raise ConfigValidationError(f"不支持的缓存类型: {self.type}")
        
        if self.type == 'redis':
            if not self.host or self.port <= 0:
                raise ConfigValidationError("Redis配置无效")
        
        if self.default_ttl <= 0:
            raise ConfigValidationError("缓存TTL必须大于0")


@dataclass
class WebConfig:
    """Web应用配置"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False
    secret_key: str = 'bilingual-tutor-secret-key-change-in-production'
    
    # 安全配置
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = 'Lax'
    permanent_session_lifetime: int = 86400  # 秒
    
    # CORS配置
    cors_origins: list = field(default_factory=lambda: ['http://localhost:5000'])
    cors_methods: list = field(default_factory=lambda: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # 加密字段
    _encrypted_fields: set = field(default_factory=lambda: {'secret_key'})
    
    def validate(self) -> None:
        """验证Web配置"""
        if self.port <= 0 or self.port > 65535:
            raise ConfigValidationError(f"无效的端口号: {self.port}")
        
        if len(self.secret_key) < 32:
            logger.warning("SECRET_KEY长度不足32，建议使用更长的密钥")
        
        if self.session_cookie_samesite not in ['Strict', 'Lax', 'None']:
            raise ConfigValidationError(f"无效的SameSite策略: {self.session_cookie_samesite}")


@dataclass
class LearningConfig:
    """学习配置"""
    default_daily_study_time: int = 60  # 分钟
    review_time_percent: float = 0.20  # 20%用于复习
    max_daily_content: int = 20
    
    # 支持的语言级别
    supported_english_levels: list = field(default_factory=lambda: ['CET-4', 'CET-5', 'CET-6', 'CET-6+'])
    supported_japanese_levels: list = field(default_factory=lambda: ['N5', 'N4', 'N3', 'N2', 'N1', 'N1+'])
    
    # SM-2算法参数
    sm2_min_easiness_factor: float = 1.3
    sm2_max_interval: int = 365  # 天
    
    def validate(self) -> None:
        """验证学习配置"""
        if self.default_daily_study_time <= 0:
            raise ConfigValidationError("每日学习时间必须大于0")
        
        if not (0 < self.review_time_percent < 1):
            raise ConfigValidationError("复习时间百分比必须在0到1之间")
        
        if self.max_daily_content <= 0:
            raise ConfigValidationError("每日最大内容量必须大于0")
        
        if self.sm2_min_easiness_factor < 1.3:
            raise ConfigValidationError("最小简易因子不能小于1.3")


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    
    # 文件日志
    file_enabled: bool = True
    file_path: str = 'logs/bilingual_tutor.log'
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    
    # 控制台日志
    console_enabled: bool = True
    
    # 结构化日志
    structured: bool = False
    
    def validate(self) -> None:
        """验证日志配置"""
        if self.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ConfigValidationError(f"无效的日志级别: {self.level}")
        
        if self.max_bytes <= 0:
            raise ConfigValidationError("日志文件大小必须大于0")
        
        if self.backup_count < 0:
            raise ConfigValidationError("备份计数不能为负数")


@dataclass
class ApplicationConfig:
    """应用程序总配置"""
    name: str = '双语导师系统'
    version: str = '1.0.0'
    environment: str = 'development'
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    web: WebConfig = field(default_factory=WebConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 配置元数据
    config_path: Optional[str] = None
    config_hash: str = ''
    
    def validate(self) -> None:
        """验证所有配置"""
        self.database.validate()
        self.cache.validate()
        self.web.validate()
        self.learning.validate()
        self.logging.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        config_dict = asdict(self)
        
        # 加密敏感字段
        sensitive_fields = {
            'database': list(self.database._encrypted_fields),
            'cache': list(self.cache._encrypted_fields),
            'web': list(self.web._encrypted_fields),
        }
        
        for section, fields in sensitive_fields.items():
            if section in config_dict:
                for field in fields:
                    if field in config_dict[section] and config_dict[section][field]:
                        value = config_dict[section][field]
                        if not is_encrypted_value(value):
                            try:
                                config_dict[section][f'_{field}_encrypted'] = encrypt_sensitive_value(value)
                                config_dict[section][field] = '***ENCRYPTED***'
                            except EncryptionError:
                                logger.warning(f"加密字段 {section}.{field} 失败")
        
        return config_dict
    
    def calculate_hash(self) -> str:
        """计算配置哈希值"""
        config_dict = asdict(self)
        # 移除无法序列化的字段
        for key in ['database', 'cache', 'web', 'learning', 'logging']:
            if key in config_dict and isinstance(config_dict[key], dict):
                config_dict[key] = {
                    k: v for k, v in config_dict[key].items()
                    if not k.startswith('_')
                }
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode('utf-8')).hexdigest()


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _lock: Lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.config_path = config_path or os.environ.get(
            'CONFIG_PATH',
            os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
        )
        self.config: Optional[ApplicationConfig] = None
        self._config_lock = Lock()
        
        # 加载配置
        self.load_config()
        
        # 注册热重载
        self._register_hot_reload()
    
    def load_config(self) -> ApplicationConfig:
        """加载配置"""
        with self._config_lock:
            # 1. 加载YAML配置文件
            config_dict = self._load_yaml_config()
            
            # 2. 环境变量覆盖
            config_dict = self._apply_env_overrides(config_dict)
            
            # 3. 创建配置对象
            self.config = self._create_config_from_dict(config_dict)
            self.config.config_path = self.config_path
            
            # 4. 验证配置
            try:
                self.config.validate()
            except (ConfigValidationError, ValidationError) as e:
                global_error_handler.log_error(e, {'config_path': self.config_path})
                raise ConfigurationError(f"配置验证失败: {str(e)}")
            
            # 5. 计算配置哈希
            self.config.config_hash = self.config.calculate_hash()
            
            logger.info(f"配置加载成功: {self.config_path}")
            logger.info(f"环境: {self.config.environment}")
            logger.info(f"配置哈希: {self.config.config_hash[:16]}...")
            
            return self.config
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
            logger.info(f"成功加载YAML配置: {self.config_path}")
            return config_dict
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML解析错误: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"加载配置文件失败: {str(e)}")
    
    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 数据库配置
        db_env_vars = {
            'DB_TYPE': 'database.type',
            'DB_PATH': 'database.path',
            'DB_HOST': 'database.host',
            'DB_PORT': 'database.port',
            'DB_USERNAME': 'database.username',
            'DB_PASSWORD': 'database.password',
            'DB_DATABASE': 'database.database',
        }
        
        # Web配置
        web_env_vars = {
            'WEB_HOST': 'web.host',
            'WEB_PORT': 'web.port',
            'WEB_SECRET_KEY': 'web.secret_key',
        }
        
        # 缓存配置
        cache_env_vars = {
            'CACHE_ENABLED': 'cache.enabled',
            'CACHE_HOST': 'cache.host',
            'CACHE_PORT': 'cache.port',
            'CACHE_PASSWORD': 'cache.password',
        }
        
        # 日志配置
        logging_env_vars = {
            'LOG_LEVEL': 'logging.level',
            'LOG_FILE_PATH': 'logging.file_path',
        }
        
        # 应用所有环境变量覆盖
        all_env_vars = {**db_env_vars, **web_env_vars, **cache_env_vars, **logging_env_vars}
        
        for env_var, config_path in all_env_vars.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # 转换类型
                if env_value.lower() in ['true', 'false']:
                    env_value = env_value.lower() == 'true'
                elif env_value.isdigit():
                    env_value = int(env_value)
                elif env_value.replace('.', '', 1).isdigit():
                    env_value = float(env_value)
                
                # 设置配置值
                keys = config_path.split('.')
                current = config_dict
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = env_value
                
                logger.debug(f"环境变量覆盖: {env_var} -> {config_path} = {env_value}")
        
        return config_dict
    
    def _create_config_from_dict(self, config_dict: Dict[str, Any]) -> ApplicationConfig:
        """从字典创建配置对象"""
        # 数据库配置
        db_config_dict = config_dict.get('database', {})
        database_config = DatabaseConfig(**{k: v for k, v in db_config_dict.items() if not k.startswith('_')})
        
        # 缓存配置
        cache_config_dict = config_dict.get('cache', {})
        cache_config = CacheConfig(**{k: v for k, v in cache_config_dict.items() if not k.startswith('_')})
        
        # Web配置
        web_config_dict = config_dict.get('web', {})
        web_config = WebConfig(**{k: v for k, v in web_config_dict.items() if not k.startswith('_')})
        
        # 学习配置
        learning_config_dict = config_dict.get('learning', {})
        learning_config = LearningConfig(**{k: v for k, v in learning_config_dict.items() if not k.startswith('_')})
        
        # 日志配置
        logging_config_dict = config_dict.get('logging', {})
        logging_config = LoggingConfig(**{k: v for k, v in logging_config_dict.items() if not k.startswith('_')})
        
        # 应用配置
        app_config = ApplicationConfig(
            name=config_dict.get('name', '双语导师系统'),
            version=config_dict.get('version', '1.0.0'),
            environment=config_dict.get('environment', 'development'),
            database=database_config,
            cache=cache_config,
            web=web_config,
            learning=learning_config,
            logging=logging_config
        )
        
        return app_config
    
    def reload_config(self) -> None:
        """热重载配置"""
        logger.info("开始热重载配置...")
        
        old_hash = self.config.config_hash if self.config else ''
        self.load_config()
        new_hash = self.config.config_hash
        
        if old_hash and old_hash != new_hash:
            logger.info(f"配置已更新 (哈希: {old_hash[:8]}... -> {new_hash[:8]}...)")
        else:
            logger.info("配置未变更")
    
    def _register_hot_reload(self) -> None:
        """注册热重载（简化版）"""
        # 在生产环境中，可以使用文件监视器如watchdog
        pass
    
    def get_config(self) -> ApplicationConfig:
        """获取当前配置"""
        if self.config is None:
            self.load_config()
        return self.config
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self.get_config().database
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        return self.get_config().cache
    
    def get_web_config(self) -> WebConfig:
        """获取Web配置"""
        return self.get_config().web
    
    def get_learning_config(self) -> LearningConfig:
        """获取学习配置"""
        return self.get_config().learning
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        return self.get_config().logging
    
    def save_config(self, path: Optional[str] = None, encrypt_sensitive: bool = True) -> None:
        """保存配置到文件"""
        save_path = path or self.config_path
        
        if encrypt_sensitive:
            config_dict = self.config.to_dict()
        else:
            config_dict = asdict(self.config)
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"配置已保存: {save_path}")
        except Exception as e:
            raise ConfigurationError(f"保存配置失败: {str(e)}")


@lru_cache(maxsize=1)
def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    return ConfigManager()


def get_config() -> ApplicationConfig:
    """获取应用配置的便捷函数"""
    return get_config_manager().get_config()
