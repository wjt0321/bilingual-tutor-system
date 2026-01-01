# 项目结构与组织

## 目录布局

```
bilingual-tutor-system/
├── bilingual_tutor/                    # 主应用包
│   ├── __init__.py                     # 包初始化文件
│   ├── models.py                       # 所有数据模型和接口（集中管理）
│   ├── core/                          # 中央学习引擎
│   │   ├── __init__.py
│   │   └── engine.py                  # CoreLearningEngine - 主协调器
│   ├── interfaces/                    # 用户界面层
│   │   ├── __init__.py
│   │   └── chinese_interface.py       # 中文本地化和文化适配
│   ├── content/                       # 内容管理系统
│   │   ├── __init__.py
│   │   ├── crawler.py                 # 网页内容爬取
│   │   ├── filter.py                  # 内容质量过滤
│   │   ├── memory_manager.py          # 内容历史和去重
│   │   ├── level_generator.py         # 难度适配内容生成
│   │   └── learning_content.py        # 静态学习内容数据
│   ├── progress/                      # 进度跟踪层
│   │   ├── __init__.py
│   │   ├── tracker.py                 # 学习进度监控
│   │   ├── vocabulary_tracker.py      # 词汇掌握跟踪
│   │   └── time_planner.py           # 每日内容规划
│   ├── analysis/                      # 分析和规划层
│   │   ├── __init__.py
│   │   ├── weakness_analyzer.py       # 弱点识别
│   │   ├── improvement_advisor.py     # 改进建议
│   │   ├── review_scheduler.py        # 间隔重复调度
│   │   ├── assessment_engine.py       # 性能评估
│   │   ├── historical_performance.py  # 历史数据整合
│   │   └── weakness_prioritizer.py    # 弱点优先级
│   ├── storage/                       # 数据持久化层
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite数据库管理
│   │   ├── content_crawler.py         # 内容存储
│   │   └── learning.db               # SQLite数据库文件
│   └── web/                          # Flask Web应用
│       ├── __init__.py
│       ├── app.py                    # 主Flask应用
│       ├── routes/                   # API路由模块（如需扩展）
│       ├── templates/                # HTML模板
│       │   ├── base.html            # 基础模板
│       │   ├── index.html           # 仪表板
│       │   ├── learn.html           # 学习界面
│       │   ├── progress.html        # 进度报告
│       │   ├── settings.html        # 用户设置
│       │   ├── login.html           # 身份验证
│       │   └── register.html        # 用户注册
│       └── static/                   # 静态资源
│           ├── css/style.css        # 样式表
│           └── js/main.js           # JavaScript
├── tests/                             # 测试套件
│   ├── __init__.py
│   ├── conftest.py                    # Pytest配置和固件
│   ├── test_*.py                      # 测试文件（属性测试+单元测试）
│   └── ...
├── EssayCrawler/                      # 独立爬虫模块
├── config.py                          # 应用配置
├── requirements.txt                   # Python依赖
├── pytest.ini                        # Pytest配置
└── README.md                          # 项目文档
```

## 架构原则

### 单一职责
- 每个模块都有明确、专注的目的
- `models.py`集中管理所有数据结构和接口
- 组件通过依赖注入实现松耦合

### 分层架构
1. **界面层**：中文本地化（`interfaces/`）
2. **核心层**：中央协调（`core/`）
3. **业务逻辑**：内容、进度、分析（`content/`、`progress/`、`analysis/`）
4. **数据层**：存储和持久化（`storage/`）
5. **表现层**：Web界面（`web/`）

### 组件通信
- `CoreLearningEngine`中的中央注册模式
- 组件通过`register_component()`注册
- 通过引擎进行组件间通信
- 抽象基类定义契约

## 文件命名约定

### Python文件
- 所有Python文件和模块使用snake_case
- 描述性名称表明用途（如`weakness_analyzer.py`）
- 测试文件以`test_`为前缀（如`test_core_engine.py`）

### 类和接口
- 类名使用PascalCase（如`CoreLearningEngine`）
- 抽象基类使用Interface后缀（如`LearningEngineInterface`）
- 常量使用枚举类（如`ActivityType`、`Skill`）

### 数据模型
- 所有模型集中在`models.py`中
- 数据结构使用dataclass装饰器
- 所有属性需要类型提示
- 受控词汇使用枚举

## 导入约定

### 相对导入
```python
# 在bilingual_tutor包内
from ..models import UserProfile, StudySession
from ..content.crawler import ContentCrawler
```

### 外部依赖
```python
# 标准库优先
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# 第三方库
import pytest
from hypothesis import given, strategies as st
from flask import Flask, render_template

# 本地导入最后
from bilingual_tutor.core.engine import CoreLearningEngine
```

## 测试结构

### 测试组织
- 每个主要模块一个测试文件（如`test_core_engine.py`）
- 使用Hypothesis进行属性测试
- 共享测试数据的固件在`conftest.py`中
- 测试标记：`@pytest.mark.property`、`@pytest.mark.unit`、`@pytest.mark.integration`

### 测试命名
```python
def test_specific_functionality():           # 单元测试
def test_property_name_property():          # 属性测试  
class TestComponentName:                    # 分组测试类
```

## 配置管理

### 基于环境的配置
- `config.py`包含配置类
- 部署设置使用环境变量
- 开发环境的默认值

### 数据库配置
- 本地开发和生产使用SQLite
- 数据库初始化在`storage/database.py`中
- 间隔重复参数可配置

## 文档标准

### 代码注释
- 面向用户功能使用中文注释
- 技术实现使用英文注释
- 所有公共方法和类需要文档字符串
- 所有函数签名需要类型提示

### README结构
- 双语（中文为主，英文为辅）
- 清晰的安装和使用说明
- 网页爬取功能的法律免责声明
- 架构概述和组件描述