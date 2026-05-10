# AI Chat Application

一个功能完善的 AI 角色聊天系统，支持多角色、朋友圈、世界书（Lorebook）等特性，兼容傻酒馆（SillyTavern）角色卡格式。

## 功能特性

### 用户功能
- 🔐 用户注册/登录
- 💬 与 AI 角色实时聊天
- 📷 朋友圈 - 查看角色的图文动态，点赞互动
- 🎭 多角色切换

### 管理员功能
- 🔐 独立的管理员登录入口
- 👥 用户管理 - 查看用户信息、封号/解封、调整亲密度
- 🎭 角色管理 - 创建/编辑角色，支持傻酒馆角色卡导入/导出
- 🌍 世界书管理 - 关键词触发的动态知识注入
- 📖 经历管理 - 为角色添加每日经历
- 📷 朋友圈管理 - 发布/删除角色动态

### 技术特性
- 兼容傻酒馆（SillyTavern）V1/V2 角色卡格式（JSON + PNG）
- 世界书/Lorebook 关键词触发机制
- 公共记忆（角色设定+经历）与独立聊天记录隔离
- 支持阿里云百炼 API

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# AI API 配置（阿里云百炼）
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-plus
```

或直接在终端设置：

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 初始化数据

```bash
python init_data.py
```

这会创建：
- 管理员账号: `admin` / `admin123`
- 默认角色: 小酒

### 4. 启动服务

```bash
python main.py
```

访问 http://localhost:8000

## 使用说明

### 用户流程
1. 访问首页 `/` 注册/登录
2. 进入聊天页面 `/chat` 选择角色对话
3. 点击 📷 朋友圈 查看角色动态

### 管理员流程
1. 访问 `/admin/login` 登录
2. 管理后台功能：
   - 角色管理：导入傻酒馆角色卡（支持 PNG 和 JSON）
   - 世界书：创建关键词触发的知识库
   - 经历管理：为角色添加每日经历
   - 朋友圈：发布角色动态
   - 用户管理：封号/解封、调整亲密度

## 项目结构

```
.
├── main.py              # FastAPI 主程序
├── database.py          # SQLAlchemy 数据库模型
├── models.py            # Pydantic 数据模型
├── auth.py              # JWT 认证
├── ai_service.py        # AI 对话服务
├── card_service.py      # 傻酒馆角色卡导入导出
├── init_data.py         # 数据初始化
├── requirements.txt     # 依赖列表
├── templates/           # HTML 模板
│   ├── login.html
│   ├── admin_login.html
│   ├── chat.html
│   ├── moments.html
│   └── admin.html
└── static/              # 静态资源
    ├── css/style.css
    └── js/
        ├── auth.js
        ├── chat.js
        └── admin.js
```

## API 文档

启动服务后访问：http://localhost:8000/docs

## 傻酒馆兼容性

### 支持导入的角色卡格式
- V1 JSON: 基础字段（name, description, personality, scenario, first_mes, mes_example）
- V2 JSON: 完整字段（包含 system_prompt, post_history_instructions, character_book 等）
- V2 PNG: 嵌入 tEXt 数据块的 PNG 图片

### 支持导入的世界书格式
- SillyTavern 世界书 JSON
- 自动兼容 entries 为数组或对象的格式

## 配置说明

### 更换 AI 模型

修改 `ai_service.py`：

```python
AI_MODEL = "qwen-max"  # 或其他模型
```

### 更换 API 提供商

修改 `ai_service.py`：

```python
AI_API_BASE = "https://api.openai.com/v1"  # OpenAI
AI_API_KEY = os.getenv("OPENAI_API_KEY", "")
```

## 许可证

MIT License
