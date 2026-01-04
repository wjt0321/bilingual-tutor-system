"""
测试配置管理器
Test Configuration Manager

验证需求: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from hypothesis import given, strategies as st, settings

from bilingual_tutor.infrastructure.config_manager import (
    DatabaseConfig,
    CacheConfig,
    WebConfig,
    LearningConfig,
    LoggingConfig,
    ApplicationConfig,
    ConfigManager,
    encrypt_sensitive_value,
    decrypt_sensitive_value,
    is_encrypted_value,
    get_config_manager,
    get_config,
    ConfigValidationError,
    EncryptionError
)

from bilingual_tutor.infrastructure.error_handler import ConfigurationError


class TestDatabaseConfig:
    """测试数据库配置"""
    
    def test_default_database_config(self):
        """验证默认数据库配置"""
        config = DatabaseConfig()
        assert config.type == 'sqlite'
        assert config.pool_size == 5
        assert config.max_overflow == 10
    
    def test_valid_sqlite_config(self):
        """验证有效的SQLite配置"""
        config = DatabaseConfig(type='sqlite', path='test.db')
        config.validate()  # 不应该抛出异常
    
    def test_valid_mysql_config(self):
        """验证有效的MySQL配置"""
        config = DatabaseConfig(
            type='mysql',
            host='localhost',
            port=3306,
            username='root',
            password='password',
            database='test_db'
        )
        config.validate()  # 不应该抛出异常
    
    def test_invalid_database_type(self):
        """验证无效的数据库类型"""
        config = DatabaseConfig(type='invalid')
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_missing_sqlite_path(self):
        """验证缺少SQLite路径"""
        config = DatabaseConfig(type='sqlite', path='')
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_incomplete_mysql_config(self):
        """验证不完整的MySQL配置"""
        config = DatabaseConfig(type='mysql', host='localhost')
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestCacheConfig:
    """测试缓存配置"""
    
    def test_default_cache_config(self):
        """验证默认缓存配置"""
        config = CacheConfig()
        assert config.enabled == True
        assert config.type == 'redis'
        assert config.default_ttl == 3600
    
    def test_valid_redis_config(self):
        """验证有效的Redis配置"""
        config = CacheConfig(type='redis', host='localhost', port=6379)
        config.validate()  # 不应该抛出异常
    
    def test_valid_memory_config(self):
        """验证有效的内存配置"""
        config = CacheConfig(type='memory')
        config.validate()  # 不应该抛出异常
    
    def test_invalid_cache_type(self):
        """验证无效的缓存类型"""
        config = CacheConfig(type='invalid')
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_redis_config(self):
        """验证无效的Redis配置"""
        config = CacheConfig(type='redis', host='', port=0)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_ttl(self):
        """验证无效的TTL"""
        config = CacheConfig(default_ttl=-1)
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestWebConfig:
    """测试Web配置"""
    
    def test_default_web_config(self):
        """验证默认Web配置"""
        config = WebConfig()
        assert config.host == '0.0.0.0'
        assert config.port == 5000
        assert config.debug == False
    
    def test_valid_web_config(self):
        """验证有效的Web配置"""
        config = WebConfig(host='127.0.0.1', port=8080)
        config.validate()  # 不应该抛出异常
    
    def test_invalid_port(self):
        """验证无效的端口"""
        config = WebConfig(port=0)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_port_too_high(self):
        """验证过大的端口"""
        config = WebConfig(port=70000)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_samesite(self):
        """验证无效的SameSite策略"""
        config = WebConfig(session_cookie_samesite='invalid')
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestLearningConfig:
    """测试学习配置"""
    
    def test_default_learning_config(self):
        """验证默认学习配置"""
        config = LearningConfig()
        assert config.default_daily_study_time == 60
        assert config.review_time_percent == 0.20
        assert config.max_daily_content == 20
    
    def test_valid_learning_config(self):
        """验证有效的学习配置"""
        config = LearningConfig(
            default_daily_study_time=90,
            review_time_percent=0.25,
            max_daily_content=30
        )
        config.validate()  # 不应该抛出异常
    
    def test_invalid_study_time(self):
        """验证无效的学习时间"""
        config = LearningConfig(default_daily_study_time=0)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_review_percent(self):
        """验证无效的复习百分比"""
        config = LearningConfig(review_time_percent=1.5)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_max_content(self):
        """验证无效的最大内容量"""
        config = LearningConfig(max_daily_content=0)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_easiness_factor(self):
        """验证无效的简易因子"""
        config = LearningConfig(sm2_min_easiness_factor=1.0)
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestLoggingConfig:
    """测试日志配置"""
    
    def test_default_logging_config(self):
        """验证默认日志配置"""
        config = LoggingConfig()
        assert config.level == 'INFO'
        assert config.file_enabled == True
        assert config.console_enabled == True
    
    def test_valid_logging_config(self):
        """验证有效的日志配置"""
        config = LoggingConfig(level='DEBUG', file_path='test.log')
        config.validate()  # 不应该抛出异常
    
    def test_invalid_log_level(self):
        """验证无效的日志级别"""
        config = LoggingConfig(level='INVALID')
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_max_bytes(self):
        """验证无效的最大字节数"""
        config = LoggingConfig(max_bytes=0)
        with pytest.raises(ConfigValidationError):
            config.validate()
    
    def test_invalid_backup_count(self):
        """验证无效的备份计数"""
        config = LoggingConfig(backup_count=-1)
        with pytest.raises(ConfigValidationError):
            config.validate()


class TestEncryption:
    """测试加密功能"""
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_encrypt_decrypt_roundtrip(self, value):
        """验证加密解密往返"""
        encrypted = encrypt_sensitive_value(value)
        decrypted = decrypt_sensitive_value(encrypted)
        assert decrypted == value
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_encrypted_value_detection(self, value):
        """验证加密值检测"""
        encrypted = encrypt_sensitive_value(value)
        assert is_encrypted_value(encrypted)
        assert not is_encrypted_value(value)
    
    def test_encrypt_with_custom_key(self):
        """验证使用自定义密钥加密"""
        from cryptography.fernet import Fernet
        custom_key = Fernet.generate_key()
        value = "test_password"
        
        encrypted = encrypt_sensitive_value(value, custom_key)
        decrypted = decrypt_sensitive_value(encrypted, custom_key)
        
        assert decrypted == value


class TestApplicationConfig:
    """测试应用配置"""
    
    def test_default_application_config(self):
        """验证默认应用配置"""
        config = ApplicationConfig()
        assert config.name == '双语导师系统'
        assert config.version == '1.0.0'
        assert config.environment == 'development'
    
    def test_validate_all_configs(self):
        """验证所有子配置"""
        config = ApplicationConfig()
        config.validate()  # 不应该抛出异常
    
    def test_to_dict_encryption(self):
        """验证配置转字典时的加密"""
        config = ApplicationConfig()
        config.web.secret_key = 'test-secret-key'
        
        config_dict = config.to_dict()
        assert 'secret_key' in config_dict['web']
        assert '_secret_key_encrypted' in config_dict['web']
    
    def test_calculate_hash(self):
        """验证配置哈希计算"""
        config = ApplicationConfig()
        hash1 = config.calculate_hash()
        hash2 = config.calculate_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256哈希长度
        
        # 修改配置后哈希应该改变
        config.web.port = 8080
        hash3 = config.calculate_hash()
        assert hash1 != hash3


class TestConfigManager:
    """测试配置管理器"""
    
    def test_singleton_pattern(self):
        """验证单例模式"""
        # 使用默认配置路径
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_load_config_from_yaml(self):
        """验证从YAML加载配置"""
        config_data = {
            'name': 'Test App',
            'version': '2.0.0',
            'environment': 'testing',
            'database': {'type': 'sqlite', 'path': 'test.db'},
            'cache': {'enabled': True, 'type': 'redis'},
            'web': {'port': 8000},
            'learning': {'default_daily_study_time': 90},
            'logging': {'level': 'DEBUG'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # 创建新的配置管理器实例（不使用单例）
            manager = object.__new__(ConfigManager)
            manager._initialized = False
            manager.__init__(temp_path)
            config = manager.get_config()
            
            assert config.name == 'Test App'
            assert config.version == '2.0.0'
            assert config.environment == 'testing'
            assert config.database.type == 'sqlite'
            assert config.web.port == 8000
            assert config.learning.default_daily_study_time == 90
            assert config.logging.level == 'DEBUG'
        finally:
            os.unlink(temp_path)
    
    def test_env_overrides(self):
        """验证环境变量覆盖"""
        config_data = {
            'database': {'type': 'sqlite', 'path': 'original.db'},
            'web': {'port': 5000}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # 设置环境变量
            original_port = os.environ.get('WEB_PORT')
            original_path = os.environ.get('DB_PATH')
            
            os.environ['WEB_PORT'] = '8080'
            os.environ['DB_PATH'] = 'overridden.db'
            
            # 创建新的配置管理器实例
            manager = object.__new__(ConfigManager)
            manager._initialized = False
            manager.__init__(temp_path)
            config = manager.get_config()
            
            assert config.web.port == 8080
            assert config.database.path == 'overridden.db'
            
            # 恢复环境变量
            if original_port is not None:
                os.environ['WEB_PORT'] = original_port
            else:
                os.environ.pop('WEB_PORT', None)
            
            if original_path is not None:
                os.environ['DB_PATH'] = original_path
            else:
                os.environ.pop('DB_PATH', None)
        finally:
            os.unlink(temp_path)
    
    def test_config_validation_on_load(self):
        """验证加载时的配置验证"""
        config_data = {
            'database': {'type': 'invalid_type'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # 创建新的配置管理器实例
            with pytest.raises((ConfigValidationError, ConfigurationError)):
                manager = object.__new__(ConfigManager)
                manager._initialized = False
                manager.__init__(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self):
        """验证保存配置"""
        config_data = {
            'name': 'Test Save',
            'database': {'type': 'sqlite', 'path': 'test.db'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            save_path = f.name
        
        try:
            # 创建新的配置管理器实例
            manager = object.__new__(ConfigManager)
            manager._initialized = False
            manager.__init__(temp_path)
            manager.config.web.port = 9999
            manager.save_config(save_path, encrypt_sensitive=False)
            
            # 加载保存的配置
            with open(save_path, 'r', encoding='utf-8') as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config['web']['port'] == 9999
        finally:
            os.unlink(temp_path)
            os.unlink(save_path)
    
    def test_reload_config(self):
        """验证热重载配置"""
        config_data = {
            'name': 'Test Reload',
            'web': {'port': 5000}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # 创建新的配置管理器实例
            manager = object.__new__(ConfigManager)
            manager._initialized = False
            manager.__init__(temp_path)
            old_port = manager.get_config().web.port
            
            # 修改配置文件
            config_data['web']['port'] = 8888
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f)
            
            # 重新加载
            manager.reload_config()
            
            assert manager.get_config().web.port == 8888
            assert old_port == 5000
        finally:
            os.unlink(temp_path)
    
    def test_get_sub_configs(self):
        """验证获取子配置"""
        config_data = {
            'database': {'type': 'sqlite'},
            'cache': {'enabled': True},
            'web': {'port': 5000},
            'learning': {'default_daily_study_time': 60},
            'logging': {'level': 'INFO'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            # 创建新的配置管理器实例
            manager = object.__new__(ConfigManager)
            manager._initialized = False
            manager.__init__(temp_path)
            
            assert isinstance(manager.get_database_config(), DatabaseConfig)
            assert isinstance(manager.get_cache_config(), CacheConfig)
            assert isinstance(manager.get_web_config(), WebConfig)
            assert isinstance(manager.get_learning_config(), LearningConfig)
            assert isinstance(manager.get_logging_config(), LoggingConfig)
        finally:
            os.unlink(temp_path)


class TestConfigConvenienceFunctions:
    """测试配置便捷函数"""
    
    def test_get_config_manager_singleton(self):
        """验证获取配置管理器单例"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_get_config_function(self):
        """验证获取配置函数"""
        config = get_config()
        
        assert isinstance(config, ApplicationConfig)
        assert config.name == '双语导师系统'
