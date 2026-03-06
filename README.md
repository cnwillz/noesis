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

# 先设置环境变量：export ANTHROPIC_API_KEY=sk-...
result = call(
    prompt="分析这个任务并逐步思考",
    log_to="./session.jsonl",
)

print(result.output)

# 查看思维链
for step in result.thought_chain:
    print(f"[{step.kind}] {step.content}")
```

## 多 Provider 支持

```python
from noesis import call, LLMConfig

# 方式 1: 直接在 call() 中指定不同 provider
result_anthropic = call(
    prompt="你好",
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
)

result_openai = call(
    prompt="Hello",
    provider="openai",
    model="gpt-4o",
    api_key="sk-...",
)

# 方式 2: 使用 LLMConfig 对象
anthropic_config = LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
)

openai_config = LLMConfig(
    provider="openai",
    model="gpt-4o",
    api_key="sk-...",
)

result1 = call("你好", config=anthropic_config)
result2 = call("Hello", config=openai_config)

# 方式 3: 并发调用不同 provider
import asyncio

async def main():
    tasks = [
        call("你好", provider="anthropic", api_key="sk-ant-..."),
        call("Hello", provider="openai", api_key="sk-..."),
        call("こんにちは", provider="openai", base_url="https://custom-api.com"),
    ]
    results = await asyncio.gather(*tasks)
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
    config: LLMConfig = None,       # LLM 配置对象（可选）
    model: str = None,              # 模型名称
    provider: str = None,           # anthropic / openai / ollama
    api_key: str = None,            # API Key
    base_url: str = None,           # 自定义 API 端点
    log_to: str = None,             # 日志文件路径
    trace: bool = False,            # 是否启用追踪
    system: str = None,             # System prompt (仅 Anthropic)
    max_tokens: int = 4096,         # 最大输出 token 数
) -> CallResult
```

### `LLMConfig`

```python
from noesis import LLMConfig

# 创建配置对象
config = LLMConfig(
    provider="anthropic",           # 提供商
    model="claude-3-5-sonnet-20241022",  # 模型名称
    api_key="sk-ant-...",           # API Key
    base_url="https://...",         # 自定义端点（可选）
    max_tokens=4096,                # 最大 token 数
    system="你是一个助手",           # System prompt
    anthropic_api_key="sk-ant-...", # 或 provider 专用 key
    openai_api_key="sk-...",        # 或 provider 专用 key
)

# 使用配置
result = call("你好", config=config)
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
    anthropic_api_key: str = None,  # Anthropic 专用 Key
    openai_api_key: str = None,     # OpenAI 专用 Key
)
```

### `load_mcp()`

```python
load_mcp("./mcp.json")
```

## 配置

### 方式 1: 环境变量（推荐）

```bash
# 必要配置
export ANTHROPIC_API_KEY=sk-...        # Anthropic API Key
# 或
export OPENAI_API_KEY=sk-...            # OpenAI API Key

# 可选配置
export NOESIS_PROVIDER=anthropic        # 默认提供商 (anthropic / openai / ollama)
export NOESIS_MODEL=claude-sonnet-4-5-20251001  # 默认模型
export NOESIS_BASE_URL=https://...      # 自定义 API 端点
export NOESIS_LOG_DIR=./logs            # 日志目录
export NOESIS_TRACE_ENABLED=true        # 启用追踪
```

### 方式 2: 代码配置

```python
from noesis import configure, call

# 方式 A: 直接配置 API Key
configure(
    provider="anthropic",
    model="claude-sonnet-4-5-20251001",
    anthropic_api_key="sk-...",  # 不推荐：敏感信息
    log_dir="./logs",
    trace_enabled=True,
)

# 方式 B: 使用环境变量（推荐）
configure(
    provider="anthropic",
    model="claude-sonnet-4-5-20251001",
    log_dir="./logs",
    trace_enabled=True,
)
# 然后在命令行设置：export ANTHROPIC_API_KEY=sk-...

result = call(prompt="你好")
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

```python
import tomli
from noesis import configure

with open(".noesis.toml", "rb") as f:
    config = tomli.load(f)

configure(
    provider=config["llm"]["provider"],
    model=config["llm"]["model"],
    log_dir=config["logging"]["log_dir"],
    trace_enabled=config["logging"]["trace_enabled"],
)
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
