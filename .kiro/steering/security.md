# 安全性与隐私保护规范

## 核心原则

在处理任何涉及上传、分享或公开代码的操作时，**必须严格保护用户的个人隐私信息**，防止敏感数据泄露到公共仓库或平台。

## 隐私保护要求

### 1. 个人信息脱敏

在以下场景中，**必须**使用示例值替换真实的个人信息：

#### 📧 邮箱地址
- ❌ 真实邮箱：`wjt0321@gmail.com`
- ✅ 示例邮箱：`user@example.com` 或 `your-email@example.com`

#### 🔑 API密钥和令牌
- ❌ 真实密钥：`ghp_xxxxxxxxxxxxxxxxxxxx`
- ✅ 示例密钥：`your-api-key-here` 或 `YOUR_API_KEY`

#### 👤 用户名和账户信息
- ❌ 真实用户名：`wjt0321`
- ✅ 示例用户名：`your-username` 或 `USERNAME`

#### 🌐 服务器地址和端口
- ❌ 真实地址：`192.168.1.100:3306`
- ✅ 示例地址：`localhost:3306` 或 `your-server:port`

#### 📱 电话号码
- ❌ 真实号码：`13812345678`
- ✅ 示例号码：`1234567890` 或 `YOUR_PHONE_NUMBER`

### 2. 配置文件处理

#### Git配置
```bash
# ❌ 避免使用真实信息
git config --global user.email "wjt0321@gmail.com"
git config --global user.name "wjt0321"

# ✅ 使用示例信息
git config --global user.email "user@example.com"
git config --global user.name "Your Name"
```

#### 环境变量文件
```bash
# .env 文件示例
# ❌ 避免真实值
DATABASE_URL=mysql://wjt0321:realpassword@192.168.1.100:3306/mydb
API_KEY=sk-1234567890abcdef

# ✅ 使用占位符
DATABASE_URL=mysql://username:password@localhost:3306/database_name
API_KEY=your-api-key-here
```

#### 配置文件模板
```json
{
  "user": {
    "email": "user@example.com",
    "name": "Your Name",
    "api_key": "YOUR_API_KEY"
  },
  "database": {
    "host": "localhost",
    "port": 3306,
    "username": "db_user",
    "password": "db_password"
  }
}
```

## 上传前检查清单

### 📋 GitHub上传前必检项目

在执行 `git push` 或上传到任何公共平台前，**必须**检查：

- [ ] **邮箱地址**：是否使用了示例邮箱
- [ ] **API密钥**：是否已替换为占位符
- [ ] **密码**：是否移除或使用示例值
- [ ] **服务器地址**：是否使用localhost或示例地址
- [ ] **个人用户名**：是否使用通用示例
- [ ] **电话号码**：是否使用示例号码
- [ ] **真实路径**：是否包含个人目录信息

### 🔍 自动检查命令

在上传前可以使用以下命令检查敏感信息：

```bash
# 检查是否包含邮箱地址
grep -r "@gmail\|@qq\|@163\|@outlook" . --exclude-dir=.git

# 检查是否包含API密钥模式
grep -r "api[_-]key\|token\|secret" . --exclude-dir=.git

# 检查是否包含IP地址
grep -r "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b" . --exclude-dir=.git
```

## 文档编写规范

### 📝 示例代码中的占位符

在编写文档和示例代码时，使用以下标准占位符：

```python
# 用户配置示例
USER_CONFIG = {
    "name": "Your Name",
    "email": "user@example.com",
    "api_key": "your-api-key-here",
    "database_url": "sqlite:///app.db"
}

# 网络请求示例
headers = {
    "Authorization": "Bearer YOUR_API_TOKEN",
    "User-Agent": "YourApp/1.0"
}
```

### 📖 README文件规范

```markdown
## 配置说明

1. 复制配置文件模板：
   ```bash
   cp config.example.json config.json
   ```

2. 编辑配置文件，填入您的信息：
   ```json
   {
     "email": "your-email@example.com",
     "api_key": "your-actual-api-key"
   }
   ```

**注意**：请勿将包含真实API密钥的配置文件提交到版本控制系统。
```

## .gitignore 配置

确保敏感文件不会被意外提交：

```gitignore
# 环境变量文件
.env
.env.local
.env.production

# 配置文件
config.json
settings.json
secrets.json

# 日志文件
*.log
logs/

# 数据库文件
*.db
*.sqlite

# 临时文件
temp/
tmp/
```

## 应急处理

### 🚨 如果意外上传了敏感信息

1. **立即删除敏感信息**：
   ```bash
   git rm --cached sensitive-file.json
   git commit -m "Remove sensitive information"
   git push origin main
   ```

2. **清理Git历史**（如果必要）：
   ```bash
   git filter-branch --force --index-filter \
   'git rm --cached --ignore-unmatch sensitive-file.json' \
   --prune-empty --tag-name-filter cat -- --all
   ```

3. **更换泄露的密钥**：
   - 立即在相关服务中撤销/重新生成API密钥
   - 更新本地配置使用新密钥

## 执行要求

### 🤖 AI助手执行规范

所有AI助手在处理涉及上传、分享的任务时：

1. **自动脱敏**：主动将真实信息替换为示例值
2. **提醒检查**：在上传前提醒用户检查敏感信息
3. **使用模板**：优先使用标准化的示例模板
4. **文档说明**：在文档中明确标注哪些值需要用户自行配置

### ✅ 正确示例

```bash
# 配置Git用户信息（示例）
git config --global user.email "user@example.com"
git config --global user.name "Your Name"

# 设置远程仓库（示例）
git remote add origin https://github.com/username/repository.git
```

### ❌ 错误示例

```bash
# 不要使用真实信息
git config --global user.email "wjt0321@gmail.com"
git config --global user.name "wjt0321"
```

## 总结

**安全第一**：在任何公开分享代码的场景中，保护个人隐私信息是最高优先级。宁可多花时间检查，也不要让敏感信息泄露到公共平台。

**标准化处理**：使用统一的示例值和占位符，确保文档的专业性和安全性。

**持续警惕**：每次上传前都要进行安全检查，养成良好的安全习惯。