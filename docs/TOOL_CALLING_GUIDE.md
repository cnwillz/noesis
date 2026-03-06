# Tool Calling 使用指南

> 让 LLM 能够调用工具，扩展其能力边界。

## 快速开始

### 1. 注册工具

```python
from noesis import register_tool

# 定义工具函数
def get_weather(city: str) -> str:
    """获取城市天气信息"""
    return f"Weather in {city}: Sunny, 25°C"

# 注册工具
register_tool("get_weather", get_weather, description="获取城市当前天气")
```

### 2. 使用工具调用 LLM

```python
from noesis import call

# 调用 LLM（带工具）
result = call(
    "北京天气怎么样？",
    profile="default",
    tools=["get_weather"]
)

print(result.output)
```

### 3. 查看思维链

```python
# 查看完整的思考过程（包含工具调用）
for step in result.thought_chain:
    print(f"[{step.kind}] {step.content}")
```

输出示例：
```
[thought] 北京天气怎么样？
[tool_call] get_weather({'city': '北京'})
[tool_result] Weather in 北京：Sunny, 25°C
[output] 北京今天天气晴朗，温度 25 摄氏度。
```

## 工具注册详解

### 自动推断参数 Schema

```python
def search(query: str, limit: int = 10) -> str:
    """搜索信息"""
    return f"Search results for: {query}"

register_tool("search", search, description="搜索信息")
# 参数 schema 会自动从函数签名推断
```

### 手动指定参数 Schema

```python
register_tool(
    "search",
    search,
    description="搜索信息",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "结果数量", "default": 10}
        },
        "required": ["query"]
    }
)
```

### 工具函数最佳实践

```python
def get_weather(city: str, unit: str = "celsius") -> str:
    """
    获取城市天气信息

    Args:
        city: 城市名称
        unit: 温度单位（celsius 或 fahrenheit）

    Returns:
        天气信息字符串
    """
    # 错误处理
    if not city:
        return "Error: City name is required"

    # 实际业务逻辑
    # ...

    return f"Weather in {city}: Sunny, 25°{unit[0].upper()}"
```

## 多工具调用

```python
# 注册多个工具
def calculator(expr: str) -> str:
    return str(eval(expr))

def translate(text: str, lang: str = "en") -> str:
    return f"Translated: {text}"

register_tool("calculator", calculator)
register_tool("translate", translate)

# 同时使用多个工具
result = call(
    "先计算 100 * 1.8 + 32，然后翻译成中文",
    profile="default",
    tools=["calculator", "translate"]
)
```

## 配置 Profile

### 方式 1: 配置文件（推荐）

创建 `.noesis.toml` 文件：

```toml
[profiles.default]
protocol = "anthropic"
model = "claude-3-5-sonnet-20241022"
api_key = "${ANTHROPIC_API_KEY}"
base_url = "https://api.anthropic.com/v1/messages"
```

```python
from noesis import call

result = call("你好", profile="default", tools=["get_weather"])
```

### 方式 2: 代码中注册

```python
from noesis import ModelProfile, register_profile, call

register_profile(
    "fast",
    ModelProfile(
        name="fast",
        protocol="anthropic",
        model="claude-3-haiku-20240307",
        api_key="sk-ant-...",
    )
)

result = call("你好", profile="fast", tools=["get_weather"])
```

### 方式 3: 直接配置

```python
from noesis import call

result = call(
    "北京天气",
    protocol="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
    tools=["get_weather"]
)
```

## API 协议支持

目前支持以下协议：

- **Anthropic** (`protocol="anthropic"`) - 完整支持 tool_use
- **OpenAI** (`protocol="openai"`) - 工具支持待实现
- **Ollama** (`protocol="ollama"`) - 本地模型

## 工具定义格式

注册的工具会自动转换为 Anthropic API 格式：

```python
from noesis.tools import get_tool_definitions

definitions = get_tool_definitions()
# [
#   {
#     "name": "get_weather",
#     "description": "获取城市当前天气",
#     "input_schema": {
#       "type": "object",
#       "properties": {
#         "city": {"type": "string"}
#       },
#       "required": ["city"]
#     }
#   }
# ]
```

## 错误处理

### 工具执行错误

```python
def failing_tool() -> str:
    raise ValueError("工具执行失败")

register_tool("failing_tool", failing_tool)

result = execute_tool("failing_tool", {})
# 返回："Error executing tool 'failing_tool': 工具执行失败"
```

### 工具未找到

```python
result = execute_tool("nonexistent", {})
# 返回："Error: Tool 'nonexistent' not found"
```

## 完整示例

查看 `examples/tool_calling_example.py` 获取完整的使用示例。

```bash
python examples/tool_calling_example.py
```

## API 参考

### `register_tool(name, func, description, parameters)`

注册一个工具。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 工具名称 |
| func | Callable | 是 | 工具函数 |
| description | str | 否 | 工具描述（默认使用 docstring） |
| parameters | dict | 否 | JSON Schema 格式参数定义 |

### `execute_tool(name, arguments)`

执行一个工具。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 工具名称 |
| arguments | dict | 是 | 工具参数 |

**返回**: 工具执行结果（任意类型）

### `call(prompt, profile, tools, ...)`

调用 LLM（带工具）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | str | 是 | 用户提示 |
| profile | str | 否 | Profile 名称 |
| tools | list[str] | 否 | 工具名称列表 |

**返回**: `CallResult` 对象，包含：
- `output`: LLM 输出
- `thought_chain`: 思维链（包含工具调用记录）
- `duration_ms`: 调用耗时
- `model`: 使用的模型

## 限制与注意事项

1. **Anthropic 协议支持最完善** - 推荐用于工具调用场景
2. **工具函数应该是纯函数** - 避免副作用，便于测试和调试
3. **工具返回值应该是字符串** - 非字符串值会自动转换
4. **工具名称应该简洁明确** - 便于 LLM 理解和选择

---

**相关文档**:
- [call.py 源码](../noesis/call.py)
- [tools.py 源码](../noesis/tools.py)
- [测试示例](../tests/test_tools.py)
