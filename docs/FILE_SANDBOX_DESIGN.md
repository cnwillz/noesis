# 文件沙盒系统设计

> 安全的文件交互系统，通过白名单机制限制文件访问范围。

## 核心目标

1. **安全隔离** - 仅允许访问配置目录白名单内的文件
2. **受限写入** - write 仅允许末尾插入或创建新文件
3. **精确编辑** - edit 需要指定原文本进行替换
4. **安全删除** - delete 将文件移入回收站（时间戳目录隔离）

---

## 配置示例 (`.noesis.toml`)

```toml
[sandbox]
enabled = true
allowed_dirs = ["./workspace", "./output"]
trash_dir = "./.trash"
forbidden_extensions = [".exe", ".bin", ".sh"]
max_file_size = 10485760  # 10MB
allow_delete = false
```

---

## 工具设计

### 1. file_read - 读取文件

```python
def file_read(path: str, start_line: int = 0, end_line: int = None) -> dict
```

**安全检查**:
- 路径必须在白名单内
- 文件不能超过 max_file_size
- 扩展名不能在被禁列表中

---

### 2. file_write - 写入文件

```python
def file_write(path: str, content: str, mode: str = "create") -> dict
```

**模式**:
- `create` - 仅创建新文件
- `append` - 追加到文件末尾

**限制**: 不允许覆盖已有文件内容

---

### 3. file_edit - 编辑文件

```python
def file_edit(path: str, old_text: str, new_text: str, occurrence: int = 1) -> dict
```

**限制**:
- old_text 必须精确匹配
- 多次出现需指定 occurrence

---

### 4. file_delete - 删除文件/目录

```python
def file_delete(path: str, reason: str = None) -> dict
```

**回收站结构**:
```
.trash/
├── 20260306140801888/       # 时间戳 (YYYYMMDDHHmmssfff)
│   └── workspace/file.txt   # 保留原目录结构
└── 20260306140902001/
    └── workspace/temp.txt
```

**特点**:
- 每次删除创建独立时间戳目录，防止冲突
- 移动而非永久删除
- 仅在 allow_delete=true 时启用

---

## 回收站管理 (API，非 LLM 工具)

```python
# 程序化调用，不注册为 LLM 工具
sandbox.trash_list()                      # 列出删除记录
sandbox.trash_restore(timestamp, confirm) # 恢复
sandbox.trash_cleanup(retention_days)     # 清理过期
sandbox.trash_purge(confirm)              # 清空回收站
```

---

## 安全机制

| 威胁 | 防护 |
|------|------|
| 目录遍历 (`../`) | 绝对路径校验 |
| 符号链接攻击 | resolve() 解析真实路径 |
| 恶意覆盖 | write 仅允许追加/创建 |
| 永久删除 | 移入回收站，可恢复 |
| 大文件 DoS | max_file_size 限制 |

---

## 工具注册

```python
from noesis.sandbox import FileSandbox

sandbox = FileSandbox()

# 注册给 LLM 使用的工具
register_tool("file_read", sandbox.read)
register_tool("file_write", sandbox.write)
register_tool("file_edit", sandbox.edit)
register_tool("file_delete", sandbox.delete)  # 需 allow_delete=true

# 回收站管理是 API，不注册为工具
# sandbox.trash_list()
# sandbox.trash_restore()
# sandbox.trash_cleanup()
```

---

## 使用示例

```python
from noesis import call

# 读取文件
result = call("读取 ./workspace/data.txt", tools=["file_read"])

# 创建文件
result = call("在 ./workspace/log.txt 追加日志", tools=["file_write"])

# 编辑文件
result = call("将 config.py 的 DEBUG=True 改为 DEBUG=False", tools=["file_edit"])

# 删除文件
result = call("删除 temp.txt", tools=["file_delete"])
```

---

## 文件结构

```
noesis/
├── sandbox/
│   ├── __init__.py
│   ├── config.py       # SandboxConfig
│   ├── core.py         # FileSandbox
│   └── logger.py       # 操作日志
├── tools_sandbox.py    # 工具注册
tests/
└── test_sandbox/
```
