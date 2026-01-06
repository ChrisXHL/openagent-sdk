# OpenAgent SDK v0.2.0

<p align="center">
  <strong>Context Engineering Tools for AI Agents</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#storage-backends">Storage</a> •
  <a href="#encryption">Encryption</a> •
  <a href="#rest-api">REST API</a> •
  <a href="#examples">Examples</a>
</p>

---

## 🎯 简介

OpenAgent SDK 是一个为 AI Agent 设计的**上下文工程框架**，帮助 Agent 进行任务规划、状态管理、决策追踪和错误日志记录。

## ✨ 特性

| 特性 | 描述 |
|------|------|
| 📋 **任务规划** | 结构化的多阶段任务管理 |
| 💾 **状态持久化** | 支持多种存储后端（JSON/SQLite/内存） |
| 🔐 **加密存储** | AES-256-GCM 加密敏感数据 |
| 🌐 **REST API** | 远程访问和 Web 界面支持 |
| 📊 **历史追踪** | 版本历史和回滚功能 |
| 🔄 **并发安全** | 线程锁支持多线程访问 |
| 🧪 **完整测试** | 34 个单元测试覆盖 |

---

## 🚀 快速开始

### 安装

```bash
pip install openagent-sdk
```

### 基本使用

```python
from openagent import OpenAgentEngine

# 初始化引擎
engine = OpenAgentEngine(workspace="./my_project")

# 创建任务计划
engine.create_plan(
    goal="Build a REST API",
    phases=["Design", "Implement", "Test", "Deploy"]
)

# 开始第一阶段
engine.start_phase("Design")

# 记录决策
engine.add_decision(
    decision="Use FastAPI",
    reason="High performance and automatic docs"
)

# 添加笔记
engine.add_note("API endpoints defined", section="Design")

# 查看状态
status = engine.get_status()
print(f"Progress: {status['progress']}%")
```

---

## 💾 存储后端

### 1. JSON 存储（默认）

```python
from openagent import OpenAgentEngine, JSONStorage

# 使用默认 JSON 存储
engine = OpenAgentEngine(workspace="./data")
```

### 2. SQLite 存储（推荐生产环境）

```python
from openagent import OpenAgentEngine, SQLiteStorage

storage = SQLiteStorage(db_path="./data/agent.db")
engine = OpenAgentEngine(storage=storage)
```

**特性**：
- ✅ 线程安全
- ✅ WAL 模式（更好的并发）
- ✅ 自动建表

### 3. SQLite + 历史记录

```python
from openagent import OpenAgentEngine, SQLiteStorageWithHistory

storage = SQLiteStorageWithHistory(
    db_path="./data/agent.db",
    max_history=1000,
)
engine = OpenAgentEngine(storage=storage)

# 获取历史
history = storage.get_history(limit=100)

# 回滚到指定版本
storage.rollback(target_version=5)
```

### 4. 内存存储（测试用）

```python
from openagent import MemoryStorage

storage = MemoryStorage()  # 不持久化
```

---

## 🔐 加密存储

保护敏感数据（如 API 密钥、密码等）：

```python
from openagent.core.encryption import EncryptedJSONStorage

# 创建加密存储
storage = EncryptedJSONStorage(
    file_path="./secret_data.json",
    password="my-secure-password",
)

# 保存数据（自动加密）
storage.save({
    "api_key": "sk-abc123",
    "database_password": "secret123"
})

# 加载数据（自动解密）
data = storage.load()
print(data["api_key"])  # sk-abc123
```

**加密特性**：
- AES-256-GCM 加密
- PBKDF2-SHA256 密钥派生（480000 次迭代）
- 随机盐和 Nonce

---

## 🌐 REST API

启动 REST API 服务器：

```python
from openagent import run_server

run_server(host="0.0.0.0", port=8080)
```

### API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/status` | 获取当前状态 |
| POST | `/api/plan` | 创建任务计划 |
| POST | `/api/phase/start` | 开始阶段 |
| POST | `/api/phase/complete` | 完成阶段 |
| POST | `/api/note` | 添加笔记 |
| GET | `/api/notes` | 获取所有笔记 |
| POST | `/api/decision` | 记录决策 |
| GET | `/api/decisions` | 获取所有决策 |
| POST | `/api/error` | 记录错误 |
| GET | `/api/errors` | 获取所有错误 |
| DELETE | `/api/clear` | 清除所有状态 |

### 使用示例

```bash
# 创建计划
curl -X POST http://localhost:8080/api/plan \
  -H "Content-Type: application/json" \
  -d '{"goal": "Build API", "phases": ["Design", "Implement"]}'

# 获取状态
curl http://localhost:8080/api/status

# 添加笔记
curl -X POST http://localhost:8080/api/note \
  -H "Content-Type: application/json" \
  -d '{"content": "Use FastAPI", "section": "Design"}'
```

---

## 📁 项目结构

```
openagent-sdk/
├── src/openagent/
│   ├── __init__.py           # 主入口，导出所有 API
│   ├── core/
│   │   ├── state.py          # 状态管理（TaskPlan, AgentState）
│   │   ├── storage.py         # 存储后端（JSON, SQLite, Memory）
│   │   └── encryption.py      # 加密存储（AES-256-GCM）
│   ├── api/
│   │   └── server.py          # REST API 服务器
│   ├── tools/
│   │   └── registry.py        # 工具注册
│   └── cli/
│       └── main.py            # CLI 界面
├── tests/
│   ├── test_state.py         # 28 个测试
│   └── test_storage.py        # 6 个测试
├── examples/
│   ├── basic.py              # 基本使用示例
│   └── api_server.py          # REST API 示例
└── pyproject.toml            # 项目配置
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 测试结果
# 34 passed in 0.06s ✅
```

---

## 📊 版本对比

| 维度 | v0.1.0 | v0.2.0 |
|------|--------|--------|
| 存储后端 | 仅 JSON | JSON + SQLite + Memory |
| 并发安全 | ❌ | ✅ 线程锁 |
| 历史记录 | ❌ | ✅ SQLiteStorageWithHistory |
| 单元测试 | 0 | 34 |
| 版本迁移 | ❌ | ✅ |
| Observer 模式 | ❌ | ✅ |
| REST API | ❌ | ✅ |
| 加密存储 | ❌ | ✅ AES-256-GCM |

---

## 📝 许可证

MIT License

---

**OpenAgent SDK - 让 AI Agent 拥有像人类一样的任务管理能力！** 🤖✨
