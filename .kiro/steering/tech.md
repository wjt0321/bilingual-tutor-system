# 技术栈和构建系统

## 核心技术栈

### 后端框架
- **Python 3.8+** - 主要编程语言
- **Flask 3.0+** - Web应用框架
- **SQLite** - 轻量级数据库存储
- **Werkzeug** - WSGI工具库

### 前端技术
- **HTML5/CSS3** - 响应式Web界面
- **JavaScript (ES6+)** - 前端交互逻辑
- **Bootstrap/自定义CSS** - 界面样式框架

### 数据处理
- **BeautifulSoup4** - HTML解析和网页爬取
- **lxml** - XML/HTML处理引擎
- **requests** - HTTP请求库

### 测试框架
- **pytest** - 单元测试框架
- **pytest-cov** - 测试覆盖率工具
- **Hypothesis** - 属性测试库（Property-based testing）

### 安全和加密
- **cryptography** - 加密算法库
- **itsdangerous** - 安全令牌生成
- **Flask-CORS** - 跨域资源共享

### 数据序列化
- **dataclasses-json** - 数据类JSON序列化

## 项目架构

### 模块化设计
```
bilingual_tutor/
├── core/           # 核心学习引擎
├── interfaces/     # 中文界面层
├── content/        # 内容管理层
├── progress/       # 进度跟踪层
├── analysis/       # 分析和规划层
├── storage/        # 数据存储层
├── audio/          # 音频处理层
└── web/           # Web应用层
```

### 设计模式
- **依赖注入** - 组件注册机制实现松耦合
- **接口抽象** - 所有核心组件都有明确的接口定义
- **工厂模式** - 动态创建学习活动和内容
- **观察者模式** - 进度跟踪和事件通知

## 常用命令

### 环境设置
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 开发和测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=bilingual_tutor --cov-report=html

# 运行属性测试（包含长时间运行警告）
python -m pytest tests/ -k "property" -v

# 运行特定测试文件
python -m pytest tests/test_core_engine.py -v

# 运行集成测试
python -m pytest tests/ -k "integration" -v
```

### Web应用
```bash
# 启动开发服务器
cd bilingual_tutor/web
python app.py

# 启动生产服务器 (使用脚本)
./start_server.sh    # Linux/macOS
start_server.bat     # Windows

# 访问应用
# 浏览器打开: http://localhost:5000
```

### 代码质量
```bash
# 代码格式化 (如果安装了black)
black bilingual_tutor/

# 代码风格检查 (如果安装了flake8)
flake8 bilingual_tutor/

# 类型检查 (如果安装了mypy)
mypy bilingual_tutor/
```

### 数据库管理
```bash
# 数据库迁移 (如果需要)
python bilingual_tutor/storage/migrate_database.py

# 音频文件迁移
python bilingual_tutor/storage/migrate_audio.py
```

## 配置管理

### 环境配置
- **开发环境**: `DevelopmentConfig` - DEBUG=True
- **生产环境**: `ProductionConfig` - DEBUG=False  
- **测试环境**: `TestingConfig` - TESTING=True

### 配置文件
- `config.py` - 主配置文件
- `pytest.ini` - 测试配置
- `requirements.txt` - 依赖包列表

### 环境变量
```bash
# 设置Flask环境
export FLASK_ENV=development  # 或 production, testing

# 设置Flask应用
export FLASK_APP=bilingual_tutor.web.app:app
```

## 部署要求

### 系统要求
- Python 3.8 或更高版本
- 至少 2GB 可用内存
- 稳定的网络连接（用于内容爬取）

### 生产部署
```bash
# 使用Gunicorn (推荐)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 bilingual_tutor.web.app:app

# 使用uWSGI
pip install uwsgi
uwsgi --http :5000 --module bilingual_tutor.web.app:app
```

## 开发规范

### 代码风格
- 遵循 PEP 8 Python代码规范
- 使用类型注解 (Type Hints)
- 函数和类必须有文档字符串
- 面向用户功能的注释使用中文

### 测试要求
- 每个新功能都需要对应的单元测试
- 关键功能需要属性测试 (Property-based tests)
- 测试覆盖率目标: 85%+
- 集成测试覆盖端到端流程

### 提交规范
- 提交信息使用中文
- 每个提交应该是一个完整的功能单元
- 重大更改需要更新相关文档