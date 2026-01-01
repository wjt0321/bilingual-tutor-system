# 技术栈与构建系统

## 核心技术

### 后端技术
- **Python 3.8+**：主要开发语言
- **Flask**：Web框架，用于Web界面
- **SQLite**：本地数据库，存储学习数据和间隔重复
- **pytest + Hypothesis**：测试框架，包含属性测试

### 前端技术
- **HTML/CSS/JavaScript**：Web界面（模板位于 `bilingual_tutor/web/templates/`）
- **Flask模板**：使用Jinja2进行服务端渲染
- **响应式设计**：支持移动端和桌面端

### 关键依赖库
- **requests + BeautifulSoup4**：网页内容爬取
- **dataclasses-json**：数据模型序列化
- **flask-cors**：跨域资源共享
- **lxml**：XML/HTML解析，用于内容提取

## 项目结构约定

### 模块组织
- `bilingual_tutor/core/`：中央学习引擎和协调
- `bilingual_tutor/models.py`：所有数据模型和接口（单文件集中管理）
- `bilingual_tutor/interfaces/`：中文本地化层
- `bilingual_tutor/content/`：内容管理、爬取和过滤
- `bilingual_tutor/progress/`：进度跟踪和时间规划
- `bilingual_tutor/analysis/`：弱点分析和改进规划
- `bilingual_tutor/storage/`：数据库和数据持久化
- `bilingual_tutor/web/`：Flask Web应用

### 测试策略
- **属性测试**：使用Hypothesis进行30+个正确性属性验证
- **94.4%测试通过率**：使用pytest进行全面测试覆盖
- **测试标记**：`@pytest.mark.property`、`@pytest.mark.unit`、`@pytest.mark.integration`

## 常用命令

### 开发环境设置
```bash
# 安装依赖
pip install -r requirements.txt

# 运行所有测试
python -m pytest tests/ -v

# 运行带覆盖率的测试
python -m pytest tests/ --cov=bilingual_tutor --cov-report=html

# 仅运行属性测试
python -m pytest tests/ -k "property" -v
```

### 运行应用
```bash
# 启动Web服务器
cd bilingual_tutor/web
python app.py

# 访问地址：http://localhost:5000
```

### 测试命令
```bash
# 运行特定测试文件
python -m pytest tests/test_core_engine.py -v

# 运行集成测试
python -m pytest tests/ -k "integration" -v

# 生成覆盖率报告
python -m pytest tests/ --cov=bilingual_tutor --cov-report=term-missing
```

## 架构模式

### 组件注册模式
- 中央`CoreLearningEngine`管理所有组件
- 通过`register_component()`方法注册组件
- 通过依赖注入实现松耦合

### 基于接口的设计
- 所有主要组件实现抽象基类
- 在`models.py`中定义（如`LearningEngineInterface`、`ContentCrawlerInterface`）

### 中文优先本地化
- 所有面向用户的文本使用中文
- 针对中文学习者的文化适配
- 使用中文语音描述提供发音指导

## 配置管理

### 环境设置
- 开发环境：`FLASK_ENV=development`
- 生产环境：`FLASK_ENV=production`
- 测试环境：`FLASK_ENV=testing`

### 关键设置
- 默认学习时间：60分钟
- 复习时间比例：20%（固定要求）
- 内容质量阈值：0.7
- 间隔重复：SM-2算法实现