# 词汇爬虫系统说明文档

## ⚠️ 法律声明

**本爬虫系统仅用于个人学习用途，禁止用于任何商业用途或非法目的。**

使用本爬虫时，请遵守以下原则：
- 仅爬取公开可访问的词汇数据
- 尊重目标网站的 robots.txt 协议
- 控制爬取频率，避免对目标服务器造成压力
- 尊重数据来源的版权和知识产权
- 如使用第三方数据源，请确保获得相应授权

---

## 📖 功能概述

本爬虫系统是一个灵活可配置的词汇数据采集工具，支持：

- ✅ **多数据源支持**：从网络 URL 或本地文件获取词汇
- ✅ **多格式支持**：JSON、CSV、HTML 格式自动识别和解析
- ✅ **增量更新**：自动跳过已存在的词汇，避免重复
- ✅ **智能映射**：自动适配不同数据源的格式和字段
- ✅ **失败回退**：网络失败时可回退到内置词汇库
- ✅ **双语支持**：英语（CET-4/6）和日语（JLPT N5/N4）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行爬虫

```bash
python run_crawler.py
```

### 3. 查看词汇

```bash
python view_vocabulary.py
```

---

## ⚙️ 配置说明

爬虫的所有配置通过 `vocabulary_sources.json` 文件控制。

### 配置文件结构

```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://example.com/vocabulary/cet4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    },
    "CET-6": {
      "type": "file",
      "path": "vocabulary_data/custom_english.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": false
    }
  },
  "japanese_sources": {
    "N5": {
      "type": "url",
      "url": "https://example.com/jlpt/n5.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    },
    "N4": {
      "type": "file",
      "path": "vocabulary_data/custom_japanese.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": false
    }
  }
}
```

### 配置参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `type` | 数据源类型 | `"url"` 或 `"file"` | 必填 |
| `url` | 数据源 URL（type 为 url 时） | 有效的 HTTP/HTTPS URL | - |
| `path` | 本地文件路径（type 为 file 时） | 相对或绝对路径 | - |
| `format` | 数据格式 | `"json"`, `"csv"`, `"html"` | `"json"` |
| `enabled` | 是否启用该数据源 | `true`, `false` | `true` |
| `backup_builtin` | 失败时是否回退到内置词汇 | `true`, `false` | `true` |

---

## 📚 数据格式规范

### JSON 格式

**英语词汇格式：**
```json
{
  "language": "english",
  "level": "CET-4",
  "metadata": {
    "source": "Custom Vocabulary",
    "description": "英语四级词汇"
  },
  "vocabulary": [
    {
      "word": "accomplish",
      "phonetic": "/əˈkɒmplɪʃ/",
      "part_of_speech": "verb",
      "meaning": "v. 完成；实现",
      "example": "We accomplished our goal.",
      "translation": "我们实现了目标。"
    }
  ]
}
```

**日语词汇格式：**
```json
{
  "language": "japanese",
  "level": "N5",
  "metadata": {
    "source": "Custom Vocabulary",
    "description": "日语N5词汇"
  },
  "vocabulary": [
    {
      "word": "あるく",
      "reading": "歩く",
      "part_of_speech": "動詞",
      "meaning": "v. 走路",
      "example": "毎日歩きます。",
      "translation": "每天走路。"
    }
  ]
}
```

### CSV 格式

**英语词汇：**
```csv
word,phonetic,part_of_speech,meaning,example,translation
accomplish,/əˈkɒmplɪʃ/,verb,v. 完成；实现,We accomplished our goal.,我们实现了目标。
average,/ˈævərɪdʒ/,noun/adj,n. 平均 adj. 平均的,The average age is 25.,平均年龄是25岁。
```

**日语词汇：**
```csv
word,reading,part_of_speech,meaning,example,translation
あるく,歩く,動詞,v. 走路,毎日歩きます。,每天走路。
いく,行く,動詞,v. 去,学校に行きます。,去学校。
```

### HTML 格式

爬虫会自动从 HTML 表格中提取词汇数据。表格应包含以下列：

**英语词汇：**
```html
<table>
  <thead>
    <tr>
      <th>word</th>
      <th>phonetic</th>
      <th>part_of_speech</th>
      <th>meaning</th>
      <th>example</th>
      <th>translation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>accomplish</td>
      <td>/əˈkɒmplɪʃ/</td>
      <td>verb</td>
      <td>v. 完成；实现</td>
      <td>We accomplished our goal.</td>
      <td>我们实现了目标。</td>
    </tr>
  </tbody>
</table>
```

---

## 🎯 使用示例

### 示例 1：从 GitHub 获取词汇

```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://raw.githubusercontent.com/username/vocabulary-repo/main/cet4.json",
      "format": "json",
      "enabled": true
    }
  }
}
```

### 示例 2：使用本地文件

```json
{
  "english_sources": {
    "CET-4": {
      "type": "file",
      "path": "my_vocabularies/cet4_custom.json",
      "format": "json",
      "enabled": true
    }
  }
}
```

### 示例 3：混合使用

```json
{
  "english_sources": {
    "CET-4": {
      "type": "url",
      "url": "https://example.com/cet4.json",
      "format": "json",
      "enabled": true,
      "backup_builtin": true
    },
    "CET-6": {
      "type": "file",
      "path": "vocabulary_data/cet6_custom.json",
      "format": "json",
      "enabled": true
    }
  }
}
```

### 示例 4：使用 CSV 格式

```json
{
  "japanese_sources": {
    "N5": {
      "type": "file",
      "path": "vocabulary_data/n5_vocabulary.csv",
      "format": "csv",
      "enabled": true
    }
  }
}
```

---

## 🔧 高级功能

### 智能字段映射

爬虫会自动映射不同来源的字段名称，支持以下同义词：

**英语词汇：**
- `word` / `text` / `name` / `vocabulary` → 单词
- `phonetic` / `pronunciation` / `ipa` → 音标
- `part_of_speech` / `pos` / `type` → 词性
- `meaning` / `definition` / `chinese` → 释义
- `example` / `sentence` / `usage` → 例句
- `translation` / `chinese_translation` → 翻译

**日语词汇：**
- `word` / `text` / `kana` / `hiragana` → 单词
- `reading` / `kanji` / `chinese` / `hanzi` → 读音
- `part_of_speech` / `pos` / `type` → 词性
- `meaning` / `definition` / `chinese` → 释义
- `example` / `sentence` / `usage` → 例句
- `translation` / `chinese_translation` → 翻译

### 增量更新机制

爬虫使用两级去重机制：

1. **内存缓存**：本次爬取过程中已处理的词汇
2. **数据库去重**：已存储在数据库中的词汇

每次运行爬虫时，会：
- 加载已存在的词汇到内存
- 检查新词汇是否已存在
- 只添加不存在的词汇
- 显示实际新增的词汇数量

### 失败回退机制

当网络请求或数据解析失败时：
- 如果 `backup_builtin: true`，则使用内置词汇库
- 如果 `backup_builtin: false`，则跳过该级别
- 详细错误信息会显示在控制台

---

## 📊 数据库结构

爬虫将词汇存储在 SQLite 数据库中，表结构如下：

```sql
CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    phonetic TEXT,
    reading TEXT,
    part_of_speech TEXT,
    meaning TEXT,
    example TEXT,
    translation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🛠️ 故障排除

### 问题 1：配置文件加载失败

**错误信息：**
```
✗ 词汇源配置文件不存在: xxx\vocabulary_sources.json
```

**解决方案：**
- 检查 `vocabulary_sources.json` 是否存在于项目根目录
- 确认文件名拼写正确
- 确认文件编码为 UTF-8

### 问题 2：网络请求失败

**错误信息：**
```
✗ 网络请求失败: [Errno 11001] getaddrinfo failed
```

**解决方案：**
- 检查网络连接
- 确认 URL 正确且可访问
- 检查防火墙设置
- 设置 `backup_builtin: true` 以使用回退机制

### 问题 3：数据格式解析错误

**错误信息：**
```
✗ 数据格式错误: Expecting value: line 1 column 1 (char 0)
```

**解决方案：**
- 确认数据源返回的是有效的 JSON/CSV/HTML 格式
- 检查字段名称是否符合规范
- 使用浏览器或 Postman 先测试数据源

### 问题 4：重复词汇过多

**现象：**
```
成功添加 0 个 CET-4 词汇
```

**解决方案：**
- 这是正常现象，表示词汇已存在
- 增量更新机制会自动跳过已存在的词汇
- 如需重新导入，请先清空数据库

---

## 📝 开发说明

### 核心文件

- `bilingual_tutor/storage/content_crawler.py` - 爬虫核心实现
- `bilingual_tutor/storage/learning_database.py` - 数据库操作
- `vocabulary_sources.json` - 配置文件
- `run_crawler.py` - 爬虫启动脚本
- `view_vocabulary.py` - 词汇查看脚本

### 主要类和方法

**ContentCrawler 类：**

```python
class ContentCrawler:
    def __init__(self, db: LearningDatabase = None, config_path: Optional[str] = None)
    
    def crawl_vocabulary(self, language: str, level: str) -> int
        """爬取指定语言和级别的词汇"""
    
    def _load_vocabulary_sources(self) -> dict
        """加载词汇源配置"""
    
    def _fetch_vocabulary_from_url(self, url: str, language: str, 
                                    level: str, format_type: str, 
                                    backup_builtin: bool) -> List[Dict]
        """从 URL 获取词汇"""
    
    def _normalize_vocabulary(self, words: List[Dict], 
                               language: str, level: str) -> List[Dict]
        """标准化词汇数据格式"""
```

### 扩展开发

如需支持新的数据格式，可在 `_fetch_vocabulary_from_url` 方法中添加对应的解析逻辑。

如需支持新的语言，可在相应的词汇获取方法中添加支持。

---

## ⚖️ 法律与伦理

### 使用原则

1. **仅限个人学习**：本爬虫只能用于个人学习和研究目的
2. **尊重版权**：尊重数据来源的版权和知识产权
3. **遵守协议**：遵守目标网站的 robots.txt 和服务条款
4. **合理使用**：控制爬取频率，避免对服务器造成压力
5. **数据安全**：妥善保管爬取的数据，不得非法传播

### 禁止用途

❌ 商业用途
❌ 数据转售
❌ 侵犯知识产权
❌ 恶意爬取
❌ 破坏网站服务

---

## 📞 联系与支持

如有问题或建议，请通过以下方式联系：

- 查看项目文档：`README.md`
- 查看详细使用指南：`VOCABULARY_CRAWLER_GUIDE.md`

---

## 📄 许可证

本爬虫系统仅用于个人学习目的，请遵守相关法律法规。

---

**最后更新日期：2026-01-03**
