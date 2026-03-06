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

# 先配置：cp .noesis.example.toml .noesis.toml
# 然后编辑 .noesis.toml 填入你的 API Key
result = call(
    prompt="分析这个任务并逐步思考",
    profile="fast",  # 使用预配置的 profile
    log_to="./session.jsonl",
)

print(result.output)

# 查看思维链
for step in result.thought_chain:
    print(f"[{step.kind}] {step.content}")
```

## Profiles 机制（推荐）

**优势**：
- 配置文件保存在本地，不提交到 Git
- 代码中只使用 profile 名称，不暴露任何敏感信息
- 支持任意 API 协议（anthropic / openai / ollama）
- 一份配置，多处复用

### 步骤 1: 创建配置文件

```bash
# 复制示例配置
cp .noesis.example.toml .noesis.toml

# 编辑配置，填入你的 API Key
vim .noesis.toml
```

### 步骤 2: 配置模型

```toml
# .noesis.toml

[profiles.fast]
# 快速响应模型 - 用于简单任务
protocol = "anthropic"  # API 协议类型
model = "qwen-max"      # 模型名称
base_url = "https://dashscope.aliyuncs.com/api/v1/chat/completions"
api_key = "${QWEN_API_KEY}"  # 支持 ${ENV_VAR} 格式
max_tokens = 2048

[profiles.smart]
# 高智能模型 - 用于复杂任务
protocol = "anthropic"
model = "deepseek-v3"
base_url = "https://api.deepseek.com/v1/chat/completions"
api_key = "${DEEPSEEK_API_KEY}"
max_tokens = 4096

[profiles.claude]
# Claude 模型
protocol = "anthropic"
model = "claude-3-5-sonnet-20241022"
api_key = "${ANTHROPIC_API_KEY}"

[profiles.gpt4]
# GPT-4 模型
protocol = "openai"
model = "gpt-4o"
api_key = "${OPENAI_API_KEY}"
```

### 步骤 3: 代码中使用

```python
from noesis import call, list_profiles

# 查看所有可用 profiles
print(list_profiles())  # ["fast", "smart", "claude", "gpt4"]

# 使用不同的模型
result_fast = call("简单任务", profile="fast")
result_smart = call("复杂问题", profile="smart")
result_claude = call("创意写作", profile="claude")
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
    profile: str = None,            # Profile 名称（推荐）
    config: LLMConfig = None,       # LLM 配置对象
    protocol: str = None,           # API 协议：anthropic / openai / ollama
    model: str = None,              # 模型名称
    api_key: str = None,            # API Key
    base_url: str = None,           # 自定义 API 端点
    log_to: str = None,             # 日志文件路径
    trace: bool = False,            # 是否启用追踪
    system: str = None,             # System prompt
    max_tokens: int = 4096,         # 最大输出 token 数
) -> CallResult
```

### `ModelProfile`

```python
from noesis import ModelProfile, register_profile, call

# 创建 Profile
profile = ModelProfile(
    name="qwen",
    protocol="anthropic",           # API 协议类型
    model="qwen-max",               # 模型名称
    base_url="https://dashscope.aliyuncs.com/api/v1/chat/completions",
    api_key="sk-...",               # 或使用 ${ENV_VAR}
    max_tokens=2048,
)

# 注册并使用
register_profile("qwen", profile)
result = call("你好", profile="qwen")
```

### `list_profiles()`

```python
from noesis import list_profiles

# 查看所有可用的 Profile 名称
print(list_profiles())  # ["fast", "smart", "claude"]
```

### `register_profile()`

```python
from noesis import register_profile, ModelProfile

# 注册 Profile（动态添加）
register_profile(
    "custom",
    ModelProfile(
        name="custom",
        protocol="openai",
        model="gpt-4o",
        api_key="sk-...",
    ),
)
```

### `load_mcp()`

```python
load_mcp("./mcp.json")
```

## 环境变量

```bash
# 日志配置
export NOESIS_LOG_DIR=./logs
export NOESIS_TRACE_ENABLED=true

# Profile 配置（可选，默认使用 .noesis.toml）
export NOESIS_DEFAULT_PROFILE=fast
```

## 配置文件

配置文件会自动从以下位置加载：
1. `./.noesis.toml`（当前目录）
2. `~/.noesis.toml`（用户主目录）

**注意**: `.noesis.toml` 已加入 `.gitignore`，不要提交到 Git！

使用示例配置文件：
```bash
cp .noesis.example.toml .noesis.toml
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
