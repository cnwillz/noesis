# noesis

> LLM 思维链调用库 — 让思考过程可见

名字来自希腊语 **noesis** (νόησις)，意为"理性思维"。

## 安装

```bash
pip install -e .
```

## 快速开始

```python
from noesis import call, configure

# 配置 API Key
configure(
    provider="anthropic",  # 或 openai
    api_key="sk-...",      # 或使用环境变量 ANTHROPIC_API_KEY
)

result = call(
    prompt="分析这个任务并逐步思考",
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
    prompt: str,                    # Prompt 内容
    model: str = None,              # 模型名称
    provider: str = None,           # anthropic / openai / ollama
    log_to: str = None,             # 日志文件路径
    trace: bool = False,            # 是否启用追踪
    system: str = None,             # System prompt (仅 Anthropic)
    max_tokens: int = 4096,         # 最大输出 token 数
) -> CallResult
```

### `configure()`

```python
configure(
    provider: str = "anthropic",    # anthropic / openai / ollama
    model: str = None,              # 模型名称
    api_key: str = None,            # API Key
    base_url: str = None,           # 自定义 API 端点
    log_dir: str = None,            # 日志目录
    trace_enabled: bool = False,    # 是否启用追踪
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
    provider="anthropic",
    model="claude-sonnet-4-5-20251001",
    log_dir="./logs",
    trace_enabled=True,
)

result = call(prompt="你好")
```

### 方式 2: 环境变量

```bash
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
export NOESIS_LOG_DIR=./logs
```

### 方式 3: 配置文件

`.noesis.toml`:

```toml
[llm]
provider = "anthropic"
model = "claude-sonnet-4-5-20251001"

[logging]
log_dir = "./logs"
trace_enabled = true
```

## 日志格式 (JSONL)

```jsonl
{"seq": 1, "type": "start", "model": "claude-sonnet-4-5-20251001"}
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
