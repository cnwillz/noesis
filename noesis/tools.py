"""
工具调用支持
"""

import inspect
from typing import Any, Callable, Optional


def _get_default_tools_config() -> dict:
    """获取默认工具配置"""
    return {}


def infer_parameters_schema(func: Callable) -> dict:
    """从函数签名推断参数 schema"""
    sig = inspect.signature(func)
    properties = {}
    required = []

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    for name, param in sig.parameters.items():
        param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
        default = param.default if param.default != inspect.Parameter.empty else None

        properties[name] = {
            "type": type_map.get(param_type, "string"),
            "description": f"Parameter {name}",
        }

        if default is None or default == inspect.Parameter.empty:
            required.append(name)
        elif default is not inspect.Parameter.empty:
            properties[name]["default"] = default

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def register_tool(
    name: str,
    func: Callable,
    description: Optional[str] = None,
    parameters: Optional[dict] = None,
):
    """
    注册一个工具

    Args:
        name: 工具名称
        func: 工具函数
        description: 工具描述
        parameters: JSON Schema 格式的参数定义（可选，会自动从函数签名推断）

    Example:
        def get_weather(city: str) -> str:
            return f"Weather in {city}: Sunny"

        register_tool("get_weather", get_weather, description="获取城市天气")
    """
    from noesis.call import _config

    if "tools" not in _config:
        _config["tools"] = {}

    # 自动推断参数 schema
    if parameters is None:
        parameters = infer_parameters_schema(func)

    # 如果没有描述，使用函数 docstring
    if description is None:
        description = func.__doc__ or ""

    _config["tools"][name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "func": func,
    }


def get_tool(name: str) -> Optional[dict]:
    """获取已注册的工具"""
    from noesis.call import _config
    return _config.get("tools", {}).get(name)


def list_tools() -> list[str]:
    """列出所有已注册的工具名称"""
    from noesis.call import _config
    return list(_config.get("tools", {}).keys())


def execute_tool(name: str, arguments: dict) -> Any:
    """
    执行一个工具

    Args:
        name: 工具名称
        arguments: 工具参数（字典）

    Returns:
        工具执行结果
    """
    tool = get_tool(name)
    if tool is None:
        return f"Error: Tool '{name}' not found"

    func = tool.get("func")
    if func is None:
        return f"Error: Tool '{name}' has no function"

    try:
        # 调用函数
        return func(**arguments)
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"


def get_tool_definitions() -> list[dict]:
    """
    获取所有工具的 Anthropic API 格式定义

    返回格式符合 Anthropic tool_use 规范
    """
    from noesis.call import _config
    tools = _config.get("tools", {})

    definitions = []
    for name, tool in tools.items():
        definitions.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"],
        })

    return definitions
