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
├── db.query
└── api.call
```

---

## 工具分组

### file 组

```python
TOOLS_FILE = {
    "file.read":   (sandbox.read,   "读取文件内容"),
    "file.write":  (sandbox.write,  "创建文件或追加内容"),
    "file.edit":   (sandbox.edit,   "精确编辑文件"),
    "file.delete": (sandbox.delete, "删除文件到回收站"),
}
```

### web 组

```python
TOOLS_WEB = {
    "web.fetch":  (fetch,  "获取指定 URL 内容"),
    "web.search": (search, "搜索网络信息"),
}
```

### shell 组

```python
TOOLS_SHELL = {
    "shell.exec": (exec, "执行 shell 命令"),
}
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

```
<组名>.<操作>

示例:
- file.read
- file.write
- file.edit
- file.delete
- web.fetch
- web.search
- shell.exec
- db.query
```

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

```python
class ToolRegistry:
    def __init__(self):
        self._groups = {}
        self._tools = {}

    def register_group(self, name: str, tools: dict):
        self._groups[name] = tools

    def activate(self, *tool_refs: str) -> list[dict]:
        """激活工具，返回 LLM 可用的工具定义"""
        result = []
        for ref in tool_refs:
            if "." in ref:
                # 单个工具：file.read
                group, op = ref.split(".")
                tool = self._groups[group][f"{group}.{op}"]
                result.append(self._make_definition(tool))
            else:
                # 整个组：file
                for tool_ref, tool in self._groups[ref].items():
                    result.append(self._make_definition(tool))
        return result

    def _make_definition(self, tool: tuple) -> dict:
        func, desc = tool
        return {
            "name": func.__name__,
            "description": desc,
            "parameters": infer_schema(func)
        }
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

### 场景 3: 显式指定

```python
call(
    "下载这个 URL 的内容并保存",
    tools=["web.fetch", "file.write"]
)
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
BOLD_TOOLS = ["file", "web", "shell.exec", "file.delete"]
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
# 默认激活的工具组
default = ["file"]

# 关键词触发激活
on_keyword = { "搜索" = ["web"], "下载" = ["web"], "命令" = ["shell"] }

# 最大工具数（防止 context 过长）
max_tools = 10

# 安全模式（禁用危险工具）
safe_mode = true  # 禁用 file.delete 和 shell.exec
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
