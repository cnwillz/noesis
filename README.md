# noesis

> LLM 思维链调用库 — 让思考过程可见

名字来自希腊语 **noesis** (νόησις)，意为"理性思维"。

## 安装

```bash
pip install -e .
```

## 快速开始

```python
from noesis import call

result = call(
    prompt="分析这个任务并逐步思考",
    model="claude-sonnet-4-6",
    log_to="./session.jsonl",
)

print(result.output)

# 查看思维链
for step in result.thought_chain:
    print(f"[{step.kind}] {step.content}")
```

## 输出示例

```
[thought] 用户要求分析任务，我需要先理解需求
[thought] 检查当前目录结构
[tool_call] read_file("README.md")
[tool_result] 文件内容...
[thought] 这是一个 Python 项目
[output] 这是一个 Python 项目，主要用于...
```

## API

### `call()`

```python
result = call(
    prompt: str,           # Prompt 内容
    model: str = None,     # 模型名称
    provider: str = None,  # claude / openai / ollama
    log_to: str = None,    # 日志文件路径
    trace: bool = False,   # 是否启用追踪
) -> CallResult
```

### `configure()`

```python
configure(
    provider: str = "claude",
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    log_dir: str = None,
    trace_enabled: bool = False,
)
```

### `load_mcp()`

```python
load_mcp("./mcp.json")
```

## 配置

### 方式 1: 代码配置

```python
from noesis import configure, call

configure(
    model="claude-sonnet-4-6",
    log_dir="./logs",
    trace_enabled=True,
)

result = call(prompt="你好")
```

### 方式 2: 环境变量

```bash
export NOESIS_MODEL=claude-sonnet-4-6
export NOESIS_LOG_DIR=./logs
export ANTHROPIC_API_KEY=sk-...
```

### 方式 3: 配置文件

`.noesis.toml`:

```toml
[llm]
provider = "claude"
model = "claude-sonnet-4-6"

[logging]
log_dir = "./logs"
trace_enabled = true
```

## 日志格式 (JSONL)

```jsonl
{"seq": 1, "type": "start", "model": "claude-sonnet-4-6"}
{"seq": 2, "type": "thought", "content": "用户要求..."}
{"seq": 3, "type": "tool_call", "name": "read_file", "args": {...}}
{"seq": 4, "type": "output", "content": "最终输出..."}
{"seq": 5, "type": "end", "duration_ms": 5230}
```

## 项目结构

```
noesis/
├── noesis/
│   ├── __init__.py   # call, configure, load_mcp
│   ├── call.py       # 核心调用逻辑
│   ├── types.py      # ThoughtStep, CallResult
│   └── mcp.py        # MCP 支持
├── README.md
└── pyproject.toml
```

## License

MIT
