# 词汇爬虫使用指南

## 概述

词汇爬虫现在支持从多种来源加载词汇，包括：
- ✅ **网络 URL**（GitHub、Gist 等）
- ✅ **本地 JSON 文件**
- ✅ **本地 CSV 文件**
- ✅ **本地 HTML 文件**
- ✅ **内置词汇**（作为备份）

## 配置文件

### 1. 主配置文件 `vocabulary_sources.json`

位置：`d:\项目代码\bilingual-tutor-system\vocabulary_sources.json`

```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/xxx/xxx/master/CET4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    },
    "CET-6": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/xxx/xxx/master/CET6.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    }
  },
  "japanese_sources": {
    "N5": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/xxx/xxx/master/N5.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    },
    "N4": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/xxx/xxx/master/N4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    }
  }
}
```

### 2. 配置参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `type` | string | 数据源类型：`url`（网络）、`file`（本地文件） |
| `url` | string | 当 type 为 `url` 时的网络地址 |
| `path` | string | 当 type 为 `file` 时的本地文件路径 |
| `format` | string | 数据格式：`json`、`csv`、`html` |
| `enabled` | boolean | 是否启用此数据源 |
| `backup_builtin` | boolean | 网络失败时是否使用内置词汇 |

## 使用方法

### 方法 1：使用网络 URL（推荐）

```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/your-username/your-repo/main/CET4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    }
  }
}
```

**优点**：
- ✅ 可以从 GitHub 等平台自由管理词汇
- ✅ 多人协作
- ✅ 版本控制

**步骤**：
1. 在 GitHub 创建一个仓库
2. 上传词汇 JSON 文件
3. 复制 raw 文件链接
4. 修改 `vocabulary_sources.json`
5. 运行 `python run_crawler.py`

### 方法 2：使用本地文件

```json
{
  "english_sources": {
    "CET-4": {
      "type": "file",
      "path": "vocabulary_data/custom_english.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": false
    }
  }
}
```

**优点**：
- ✅ 完全离线可用
- ✅ 随时编辑
- ✅ 无需网络

## 数据格式

### 英语词汇 JSON 格式

```json
{
  "metadata": {
    "language": "english",
    "level": "CET-4"
  },
  "words": [
    {
      "word": "abandon",
      "phonetic": "/əˈbændən/",
      "meaning": "v. 放弃；抛弃",
      "pos": "verb",
      "example": "We had to abandon the car.",
      "example_cn": "我们不得不放弃这辆车。"
    }
  ]
}
```

### 日语词汇 JSON 格式

```json
{
  "metadata": {
    "language": "japanese",
    "level": "N5"
  },
  "words": [
    {
      "word": "あう",
      "reading": "会う",
      "meaning": "v. 见面",
      "pos": "動詞",
      "example": "友達に会います。",
      "example_cn": "和朋友见面。"
    }
  ]
}
```

### CSV 格式（可选）

```csv
word,phonetic,meaning,example,example_cn
abandon,/əˈbændən/,v. 放弃；抛弃,We had to abandon the car.,我们不得不放弃这辆车。
ability,/əˈbɪləti/,n. 能力,She has the ability to learn quickly.,她有快速学习的能力。
```

## 运行爬虫

### 基本使用

```bash
# 运行爬虫（增量模式）
python run_crawler.py

# 强制全量更新
python run_crawler.py --force-full
```

### Python 代码中调用

```python
from bilingual_tutor.storage.content_crawler import RealContentCrawler

# 创建爬虫实例
crawler = RealContentCrawler()

# 爬取英语词汇
count = crawler.crawl_english_vocabulary(level="CET-4", incremental=True)
print(f"成功添加 {count} 个词汇")

# 爬取日语词汇
count = crawler.crawl_japanese_vocabulary(level="N5", incremental=True)
print(f"成功添加 {count} 个词汇")

# 获取统计信息
stats = crawler.get_crawler_stats()
print(stats)
```

## 自定义词汇库示例

### 示例 1：从 GitHub 加载

1. 在 GitHub 创建仓库 `my-vocabulary`
2. 创建文件 `CET4.json`：
```json
{
  "words": [
    {"word": "hello", "phonetic": "/həˈloʊ/", "meaning": "int. 你好", "example": "Hello, world!", "example_cn": "你好，世界！"}
  ]
}
```
3. 修改配置：
```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/yourname/my-vocabulary/main/CET4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": false
    }
  }
}
```
4. 运行爬虫

### 示例 2：使用本地文件

编辑 `vocabulary_data/custom_english.json`，然后修改配置：

```json
{
  "english_sources": {
    "CET-4": {
      "type": "file",
      "path": "vocabulary_data/custom_english.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": false
    }
  }
}
```

## 网络爬虫特性

### 1. 智能字段识别

爬虫会自动识别不同的字段名：

**英语词汇**：
- `word`, `text`, `name` → 单词
- `phonetic`, `pronunciation`, `reading` → 音标
- `meaning`, `definition`, `translation` → 释义
- `example`, `sentence` → 例句
- `pos`, `part_of_speech`, `type` → 词性

**日语词汇**：
- `word`, `text`, `name` → 单词
- `reading`, `kana`, `hiragana` → 读音
- `meaning`, `definition`, `translation` → 释义
- `example`, `sentence` → 例句
- `pos`, `part_of_speech`, `type` → 词性

### 2. 多种数据格式

支持：
- **JSON**：最常用，支持复杂结构
- **CSV**：简单表格格式
- **HTML**：从网页提取词汇

### 3. 容错机制

- ✅ 网络失败时自动使用内置词汇（如果 `backup_builtin: true`）
- ✅ 解析失败时跳过错误数据
- ✅ 缺失字段时自动填充空值

### 4. 增量更新

- ✅ 自动跳过已存在的词汇
- ✅ 支持全量/增量模式切换
- ✅ 记录最后爬取时间

## 常见问题

### Q1: 如何添加新的词汇级别？

编辑 `vocabulary_sources.json`，添加新级别：

```json
{
  "english_sources": {
    "GRE": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/xxx/GRE.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    }
  }
}
```

### Q2: 如何禁用某个数据源？

设置 `enabled: false`：

```json
{
  "CET-4": {
    "enabled": false
  }
}
```

### Q3: 网络爬虫失败怎么办？

- 检查网络连接
- 检查 URL 是否正确
- 设置 `backup_builtin: true` 使用内置词汇
- 或使用本地文件作为数据源

### Q4: 如何验证词汇格式？

使用爬虫的测试功能：

```python
from bilingual_tutor.storage.content_crawler import RealContentCrawler

crawler = RealContentCrawler()

# 测试加载
words = crawler._fetch_vocabulary_from_url(
    "https://raw.githubusercontent.com/xxx/xxx.json",
    "english",
    "CET-4",
    "json",
    backup_builtin=False
)

print(f"成功加载 {len(words)} 个词汇")
for word in words[:5]:
    print(word)
```

## 技术架构

```
┌─────────────────┐
│ vocabulary_     │
│ sources.json    │
└────────┬────────┘
         │
         ├─── URL (GitHub/Gist/自定义)
         │
         ├─── 本地文件 (JSON/CSV/HTML)
         │
         └─── 内置词汇 (备份)
              │
         ┌────▼────┐
         │ 爬虫引擎  │
         └────┬────┘
              │
              ├─── 网络请求器 (RobustRequester)
              │
              ├─── 格式解析器 (JSON/CSV/HTML)
              │
              ├─── 数据标准化器
              │
              └─── 去重检测器
                    │
               ┌────▼────┐
               │ 数据库   │
               └─────────┘
```

## 扩展开发

### 添加新的数据格式

在 `content_crawler.py` 中添加：

```python
def _parse_xxx_vocabulary(self, content: str) -> List[Dict]:
    """解析 XXX 格式"""
    # 解析逻辑
    return words
```

### 添加新的词汇来源

在 `vocabulary_sources.json` 中添加配置，然后在代码中支持新的 `type`。

## 总结

现在你可以：

1. ✅ **自由管理词汇库**：使用 GitHub、本地文件等
2. ✅ **多种格式支持**：JSON、CSV、HTML
3. ✅ **智能容错**：网络失败自动备份
4. ✅ **增量更新**：避免重复添加
5. ✅ **完全自主**：不依赖 AI 知识库

享受你的自由词汇管理！🎉
