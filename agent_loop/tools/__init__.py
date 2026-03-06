"""
工具注册表

提供工具的注册、发现、调用功能。
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..types import ToolCall

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    function: Callable
    parameters: dict  # JSON Schema 格式


class ToolRegistry:
    """
    工具注册表

    用法:
        registry = ToolRegistry()

        @registry.register(name="hello", description="Say hello")
        def hello(name: str) -> str:
            return f"Hello, {name}!"

        result = registry.call("hello", name="World")
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[dict] = None,
    ) -> Callable:
        """
        注册工具装饰器

        Args:
            name: 工具名称（默认函数名）
            description: 工具描述
            parameters: 参数 Schema（可选，自动推断）
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "")

            # 简单参数推断
            tool_params = parameters or self._infer_parameters(func)

            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=tool_desc,
                function=func,
                parameters=tool_params,
            )

            logger.debug(f"🔧 注册工具：{tool_name}")
            return func

        return decorator

    def _infer_parameters(self, func: Callable) -> dict:
        """推断函数参数 Schema"""
        import inspect

        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # 类型推断
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == dict:
                param_type = "object"
            elif param.annotation == list:
                param_type = "array"

            properties[param_name] = {"type": param_type}

            # 必填参数
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """列出所有工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def call(self, name: str, **kwargs) -> Any:
        """
        调用工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        logger.debug(f"🔧 调用工具：{name}({kwargs})")

        start_time = time.time()
        try:
            result = tool.function(**kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"✅ 工具 {name} 执行完成 ({duration_ms}ms)")
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ 工具 {name} 执行失败：{e} ({duration_ms}ms)")
            raise


# 全局默认注册表
_default_registry: Optional[ToolRegistry] = None


def get_default_registry() -> ToolRegistry:
    """获取默认注册表"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


def register_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Callable:
    """注册工具到默认注册表"""
    return get_default_registry().register(name=name, description=description)
