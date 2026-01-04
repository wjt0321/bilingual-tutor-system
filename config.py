"""
双语导师系统 - 配置管理
Bilingual Tutor System - Configuration Management
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY: str = 'bilingual-tutor-secret-key-2024'
    DEBUG: bool = False
    TESTING: bool = False
    
    # Server settings
    HOST: str = '0.0.0.0'
    PORT: int = 5000
    
    # Application settings
    APP_NAME: str = '双语导师系统'
    APP_VERSION: str = '1.0.0'
    
    # Learning settings
    DEFAULT_DAILY_STUDY_TIME: int = 60  # minutes
    REVIEW_TIME_PERCENT: float = 0.20  # 20% for review
    
    # Language settings
    SUPPORTED_ENGLISH_LEVELS: list = None
    SUPPORTED_JAPANESE_LEVELS: list = None
    
    def __post_init__(self):
        if self.SUPPORTED_ENGLISH_LEVELS is None:
            self.SUPPORTED_ENGLISH_LEVELS = ['CET-4', 'CET-5', 'CET-6', 'CET-6+']
        if self.SUPPORTED_JAPANESE_LEVELS is None:
            self.SUPPORTED_JAPANESE_LEVELS = ['N5', 'N4', 'N3', 'N2', 'N1', 'N1+']


@dataclass
class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG: bool = True
    

@dataclass
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG: bool = False
    

@dataclass
class TestingConfig(Config):
    """Testing configuration."""
    TESTING: bool = True
    DEBUG: bool = True


def get_config(env: Optional[str] = None) -> Config:
    """Get configuration based on environment."""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()


# Default configuration instance
config = get_config()
