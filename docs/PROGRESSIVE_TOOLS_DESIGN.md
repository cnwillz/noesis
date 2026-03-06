# 渐进式工具架构设计

> 按功能域组织工具，分层披露，降低 LLM 认知负担。

## 核心理念

1. **工具分组** - 按功能域组织（file、web、shell 等）
2. **分层披露** - 先披露核心工具，需要时再披露高级工具
3. **按需激活** - 根据任务上下文动态激活工具组

---

## 工具层级

```
Level 1: 核心工具（默认激活）
├── file.read
├── file.write
└── file.edit

Level 2: 常用工具（任务需要时激活）
├── file.delete
├── web.fetch
└── web.search

Level 3: 高级工具（明确请求时激活）
├── shell.exec
├── db.mysql.query
└── ai.llm.chat

Level N: 无限嵌套（按需展开）
├── cloud.aws.s3.upload
├── cloud.aws.ec2.start
├── cloud.gcp.storage.read
├── db.postgres.transaction
├── ai.vision.ocr
└── ...
```

---

## 工具分组

### 扁平组

```python
TOOLS_FILE = {
    "file.read":   (sandbox.read,   "读取文件内容"),
    "file.write":  (sandbox.write,  "创建文件或追加内容"),
    "file.edit":   (sandbox.edit,   "精确编辑文件"),
    "file.delete": (sandbox.delete, "删除文件到回收站"),
}
```

### 嵌套组（树状结构）

```python
# 方式 1: 使用字典树
TOOLS_TREE = {
    "cloud": {
        "aws": {
            "s3": {
                "upload": (s3_upload, "上传到 S3"),
                "download": (s3_download, "从 S3 下载"),
            },
            "ec2": {
                "start": (ec2_start, "启动 EC2 实例"),
                "stop": (ec2_stop, "停止 EC2 实例"),
            },
        },
        "gcp": {
            "storage": {
                "read": (gcp_read, "读取 GCS 文件"),
                "write": (gcp_write, "写入 GCS 文件"),
            },
        },
    },
    "db": {
        "mysql": {
            "query": (mysql_query, "MySQL 查询"),
            "transaction": (mysql_txn, "MySQL 事务"),
        },
        "postgres": {
            "query": (pg_query, "Postgres 查询"),
        },
    },
}

# 方式 2: 扁平注册，逻辑分组
registry.register("cloud.aws.s3.upload", s3_upload, "上传到 S3")
registry.register("cloud.aws.s3.download", s3_download, "从 S3 下载")
registry.register("cloud.gcp.storage.read", gcp_read, "读取 GCS 文件")
```

### 激活嵌套组

```python
# 激活整个子树
registry.activate("cloud")          # 激活所有云工具
registry.activate("cloud.aws")      # 仅激活 AWS 工具
registry.activate("cloud.aws.s3")   # 仅激活 S3 工具

# 激活单个工具
registry.activate("cloud.aws.s3.upload")

# 混合激活
registry.activate("file", "cloud.aws.s3", "db.mysql.query")
```

---

## 激活策略

### 策略 1: 静态配置

```toml
[tools]
# 默认激活的工具组
default = ["file"]

# 按需激活
on_keyword = { "搜索" = ["web"], "命令" = ["shell"] }
```

### 策略 2: 动态激活

```python
# 根据 prompt 关键词自动激活
if "搜索" in prompt:
    activate_tools("web")

if "运行" in prompt or "命令" in prompt:
    activate_tools("shell")
```

### 策略 3: 显式声明

```python
result = call(
    "帮我搜索 Python 新闻",
    tools=["web.search"]  # 显式指定
)
```

---

## API 设计

### 工具注册

```python
from noesis import ToolRegistry

registry = ToolRegistry()

# 注册工具组
registry.register_group("file", TOOLS_FILE)
registry.register_group("web", TOOLS_WEB)
registry.register_group("shell", TOOLS_SHELL)

# 获取工具定义（用于 LLM 调用）
registry.get_tools(["file.read", "file.write"])
registry.get_group("file")  # 获取整个组
```

### 工具调用

```python
# 方式 1: 字符串列表（扁平）
call("读取文件", tools=["file.read"])

# 方式 2: 组名（激活整个组）
call("处理文件", tools=["file"])

# 方式 3: 混合
call("读取并搜索", tools=["file.read", "web"])
```

---

## 工具命名规范

### 扁平命名（两级）

```
<组名>.<操作>

示例:
- file.read
- file.write
- web.fetch
- web.search
```

### 嵌套命名（无限层级）

```
<顶级>.<子组>.<操作>
<顶级>.<子组>.<孙组>.<操作>
...

示例:
- file.read
- file.write
- cloud.aws.s3.upload
- cloud.aws.s3.download
- cloud.gcp.storage.read
- db.mysql.query
- db.mysql.transaction
- db.postgres.query
- ai.llm.chat
- ai.llm.embed
- ai.vision.analyze
- ai.vision.ocr
```

**支持层级深度**: 无限（受限于实际工具数量）

---

## 上下文优化

### 问题：工具过多导致 context 过长

```
传统方式（所有工具一次性注入）:
├── file_read (200 tokens)
├── file_write (200 tokens)
├── file_edit (200 tokens)
├── file_delete (200 tokens)
├── web_fetch (200 tokens)
├── web_search (200 tokens)
└── ... = 1400+ tokens
```

### 解决：渐进式披露

```
Level 1 (仅 file 核心):
├── file.read (200 tokens)
├── file.write (200 tokens)
└── file.edit (200 tokens)
= 600 tokens  ✓

Level 2 (需要 web 时):
+ web.fetch (200 tokens)
+ web.search (200 tokens)
= 1000 tokens  ✓
```

---

## 实现示例

### 核心实现（支持嵌套）

```python
class ToolRegistry:
    def __init__(self):
        self._tools = {}  # 扁平存储：{"cloud.aws.s3.upload": (func, desc)}

    def register(self, name: str, func: callable, desc: str):
        """注册单个工具"""
        self._tools[name] = (func, desc)

    def activate(self, *patterns: str) -> list[dict]:
        """
        激活工具，支持前缀匹配

        activate("file")              -> 激活所有 file.* 工具
        activate("cloud.aws")         -> 激活所有 cloud.aws.* 工具
        activate("cloud.aws.s3")      -> 激活所有 cloud.aws.s3.* 工具
        activate("db.mysql.query")    -> 激活单个工具
        """
        result = []
        for pattern in patterns:
            for name, (func, desc) in self._tools.items():
                # 前缀匹配：pattern 是工具名的前缀
                if name == pattern or name.startswith(f"{pattern}."):
                    result.append(self._make_definition(func, desc, name))
        return result

    def _make_definition(self, func, desc, name) -> dict:
        return {
            "name": name.replace(".", "_"),  # LLM 友好名称
            "description": desc,
            "parameters": infer_schema(func)
        }
```

### 工具树可视化

```python
def print_tool_tree(registry: ToolRegistry):
    """打印工具树结构"""
    tree = {}
    for name in registry._tools:
        parts = name.split(".")
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def _print(node, indent=0):
        for key, value in sorted(node.items()):
            if value:
                print("  " * indent + key)
                _print(value, indent + 1)
            else:
                print("  " * indent + key + " [tool]")

    _print(tree)

# 输出:
# cloud
#   aws
#     ec2
#       start [tool]
#       stop [tool]
#     s3
#       upload [tool]
#       download [tool]
#   gcp
#     storage
#       read [tool]
#       write [tool]
# db
#   mysql
#     query [tool]
#     transaction [tool]
#   postgres
#     query [tool]
```

---

## 使用示例

### 场景 1: 简单文件操作（默认工具组）

```toml
# .noesis.toml
[tools]
default = ["file"]
```

```python
call("读取 config.py 并修改 DEBUG 设置")
# 自动激活：file.read, file.write, file.edit
```

### 场景 2: 需要网络搜索

```toml
[tools]
default = ["file"]
on_keyword = { "搜索" = ["web"], "爬虫" = ["web"] }
```

```python
call("搜索最新的 Python 新闻")
# 关键词匹配，自动激活：web.fetch, web.search
```

### 场景 3: 云资源管理（嵌套层级）

```python
# 激活整个 AWS 工具树
call("启动 my-instance EC2 实例", tools=["cloud.aws"])
# 可用工具：cloud.aws.ec2.start, cloud.aws.ec2.stop,
#            cloud.aws.s3.upload, cloud.aws.s3.download

# 仅激活 S3 工具
call("上传文件到 bucket", tools=["cloud.aws.s3"])
# 可用工具：cloud.aws.s3.upload, cloud.aws.s3.download

# 激活单个工具
call("上传文件", tools=["cloud.aws.s3.upload"])
```

### 场景 4: 数据库操作（多层嵌套）

```python
# 激活所有数据库工具
call("查询用户数据", tools=["db"])
# 可用工具：db.mysql.query, db.mysql.transaction, db.postgres.query

# 仅激活 MySQL
call("查询用户表", tools=["db.mysql"])
# 可用工具：db.mysql.query, db.mysql.transaction

# 显式指定
call(
    "用 MySQL 查询用户数据",
    tools=["db.mysql.query"]
)
```

### 场景 5: AI 服务（深度嵌套）

```python
# 激活所有 AI 工具
call("分析这张图片", tools=["ai"])
# 可用工具：ai.llm.chat, ai.llm.embed, ai.vision.analyze, ai.vision.ocr

# 仅激活视觉工具
call("识别图片中的文字", tools=["ai.vision"])
# 可用工具：ai.vision.analyze, ai.vision.ocr

# 精确激活
call("OCR 识别", tools=["ai.vision.ocr"])
```

---

## 工具组预设

```python
# 核心工具组（最小可用集合）
CORE_TOOLS = ["file.read", "file.write", "file.edit"]

# 完整工具组
ALL_TOOLS = ["file", "web", "shell"]

# 安全工具组（只读）
SAFE_TOOLS = ["file.read", "web.fetch"]

# 激进工具组（允许删除和执行）
BOLD_TOOLS = ["file", "web", "shell", "file.delete"]

# 云服务工具组（嵌套）
CLOUD_TOOLS = {
    "aws": ["cloud.aws"],      # 所有 AWS 工具
    "aws.s3": ["cloud.aws.s3"], # 仅 S3
    "aws.ec2": ["cloud.aws.ec2"], # 仅 EC2
    "gcp": ["cloud.gcp"],       # 所有 GCP 工具
    "all": ["cloud"],           # 所有云服务
}

# 数据库工具组（嵌套）
DB_TOOLS = {
    "mysql": ["db.mysql"],
    "postgres": ["db.postgres"],
    "all": ["db"],
}

# AI 工具组（嵌套）
AI_TOOLS = {
    "llm": ["ai.llm"],
    "vision": ["ai.vision"],
    "speech": ["ai.speech"],
    "all": ["ai"],
}
```

---

## 配置文件示例

```toml
# .noesis.toml

[profiles.default]
protocol = "anthropic"
model = "claude-3-5-sonnet"

# 工具配置
[tools]
# 默认激活的工具组（支持前缀）
default = ["file", "cloud.aws"]

# 关键词触发激活
on_keyword = {
    "搜索" = ["web"],
    "下载" = ["web.fetch"],
    "命令" = ["shell"],
    "数据库" = ["db"],
    "MySQL" = ["db.mysql"],
    "OCR" = ["ai.vision.ocr"]
}

# 最大工具数（防止 context 过长）
max_tools = 15

# 安全模式（禁用危险工具）
safe_mode = true  # 禁用 file.delete 和 shell.exec

# 显式禁用的工具前缀
disabled = ["shell.exec", "db.mysql.transaction"]
```

---

## 文件结构

```
noesis/
├── tools/
│   ├── __init__.py
│   ├── registry.py     # ToolRegistry
│   ├── groups.py       # 预定义工具组
│   └── loader.py       # 从配置加载
tests/
└── test_tools/
    ├── test_registry.py
    └── test_groups.py
```

---

## 扩展性

### 添加工具组

```python
# 新增 db 组
TOOLS_DB = {
    "db.query":    (query,    "执行 SQL 查询"),
    "db.execute":  (execute,  "执行写操作"),
}

registry.register_group("db", TOOLS_DB)
```

### 自定义激活逻辑

```python
@register_activation_rule
def activate_db_for_heavy_tasks(prompt: str) -> Optional[list[str]]:
    if "数据库" in prompt or "SQL" in prompt:
        return ["db"]
    return None
```

---

## 优势

| 传统方式 | 渐进式披露 |
|----------|------------|
| 所有工具一次性注入 | 按需激活 |
| Context 冗长 | Context 精简 |
| LLM 容易混淆 | 工具意图清晰 |
| 难以控制权限 | 可按组控制 |
