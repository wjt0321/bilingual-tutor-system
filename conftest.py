# -*- coding: utf-8 -*-
"""
全局测试配置文件
配置Hypothesis以加快测试速度
"""

from hypothesis import settings, Verbosity

# 配置Hypothesis以减少示例数量，加快测试速度
settings.register_profile("fast", 
    max_examples=20,  # 从默认的100减少到20
    deadline=5000,    # 5秒超时
    verbosity=Verbosity.quiet
)

settings.register_profile("ci", 
    max_examples=50,  # CI环境使用中等数量
    deadline=10000,   # 10秒超时
    verbosity=Verbosity.normal
)

settings.register_profile("thorough", 
    max_examples=200,  # 彻底测试时使用更多示例
    deadline=None,
    verbosity=Verbosity.verbose
)

# 默认使用快速配置
settings.load_profile("fast")