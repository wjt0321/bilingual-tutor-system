# 自动化作文爬取工具 (EssayCrawler)

## 项目简介
这是一个自动化的作文和美文爬取工具，支持定时爬取、智能分类、自动打标和本地存储。

## 功能特点
- **多源爬取**：支持配置多个目标网站。
- **智能分类**：基于 NLP 技术自动识别记叙文、议论文等。
- **自动清洗**：去除无关内容，保留正文。
- **可视化界面**：提供控制台和文章库浏览功能。
- **每日报告**：自动生成 Markdown 格式的爬取日报。

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动程序
双击运行 `start_crawler.bat` 即可启动图形界面。

或者在命令行运行：
```bash
python src/gui.py
```

### 3. 使用说明
- **控制台**：点击“立即开始爬取”手动触发任务，日志会显示爬取进度。
- **文章库**：爬取完成后，点击“刷新列表”查看已爬取的文章。
- **查看文件**：文章会自动保存为 Markdown 文件在 `data/articles` 目录下。

## 配置说明
修改 `config/settings.json` 可调整：
- `targets`: 目标网站列表
- `schedule`: 定时任务时间
- `classification`: 分类关键词

## 数据存储
- 数据库：`data/db/essays.db`
- 文章文件：`data/articles/`
- 每日报告：`data/reports/`
