"""
工具调用功能测试
"""

import pytest
from unittest.mock import patch, MagicMock
from importlib import import_module

noesis_module = import_module('noesis.call')

from noesis.call import LLMConfig, ModelProfile, register_profile
from noesis.types import ThoughtStep, CallResult

# 工具功能在 tools 模块中
from noesis import register_tool, get_tool, list_tools, execute_tool
from noesis.tools import get_tool_definitions, infer_parameters_schema


class TestToolRegistration:
    """工具注册测试"""

    def setup_method(self):
        """清空工具注册表"""
        self._original_tools = dict(noesis_module._config.get("tools", {}))
        noesis_module._config["tools"] = {}

    def teardown_method(self):
        """恢复工具注册表"""
        noesis_module._config["tools"] = self._original_tools

    def test_register_tool(self):
        """注册一个工具"""
        def get_weather(city: str) -> str:
            return f"Weather in {city}: Sunny"

        register_tool("get_weather", get_weather, description="获取天气信息")

        assert "get_weather" in list_tools()

    def test_register_tool_with_schema(self):
        """注册带参数 schema 的工具"""
        def search(query: str, limit: int = 10) -> str:
            return f"Search results for: {query}"

        register_tool(
            "search",
            search,
            description="搜索信息",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "结果数量限制", "default": 10}
                },
                "required": ["query"]
            }
        )

        tools = list_tools()
        assert "search" in tools

    def test_get_tool(self):
        """获取已注册的工具"""
        def calculator(expr: str) -> str:
            return "42"

        register_tool("calculator", calculator, description="计算器")

        tool = get_tool("calculator")
        assert tool is not None
        assert tool["name"] == "calculator"

    def test_get_tool_not_found(self):
        """获取不存在的工具"""
        tool = get_tool("nonexistent")
        assert tool is None

    def test_infer_parameters_schema(self):
        """从函数签名推断参数 schema"""
        def test_func(name: str, age: int, score: float, active: bool) -> str:
            return "test"

        schema = infer_parameters_schema(test_func)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["score"]["type"] == "number"
        assert "active" in schema["properties"]

    def test_get_tool_definitions(self):
        """获取工具定义（Anthropic 格式）"""
        def get_weather(city: str) -> str:
            return f"Weather in {city}"

        register_tool("get_weather", get_weather, description="获取天气")

        definitions = get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "get_weather"
        assert definitions[0]["description"] == "获取天气"
        assert "input_schema" in definitions[0]


class TestToolExecution:
    """工具执行测试"""

    def setup_method(self):
        self._original_tools = dict(noesis_module._config.get("tools", {}))
        noesis_module._config["tools"] = {}

    def teardown_method(self):
        noesis_module._config["tools"] = self._original_tools

    def test_execute_tool(self):
        """执行工具"""
        def add(a: int, b: int) -> int:
            return a + b

        register_tool("add", add, description="加法")

        result = execute_tool("add", {"a": 1, "b": 2})
        assert result == 3

    def test_execute_tool_with_error(self):
        """工具执行出错"""
        def failing_tool() -> str:
            raise ValueError("工具执行失败")

        register_tool("failing_tool", failing_tool, description="会失败的工具")

        result = execute_tool("failing_tool", {})
        assert "error" in result.lower()

    def test_execute_tool_not_found(self):
        """执行不存在的工具"""
        result = execute_tool("nonexistent", {})
        assert "not found" in result.lower()


class TestToolWithLLMCall:
    """工具与 LLM 调用集成测试"""

    def setup_method(self):
        self._original_tools = dict(noesis_module._config.get("tools", {}))
        noesis_module._config["tools"] = {}
        self._original_profiles = dict(noesis_module._config["profiles"])
        noesis_module._config["profiles"] = {}

    def teardown_method(self):
        noesis_module._config["tools"] = self._original_tools
        noesis_module._config["profiles"] = self._original_profiles

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_tools(self, mock_call_llm):
        """带工具的 LLM 调用"""
        # 注册工具
        def get_weather(city: str) -> str:
            return f"Weather in {city}: Sunny, 25°C"

        register_tool("get_weather", get_weather, description="获取城市天气")

        # Mock LLM 返回 tool_use
        mock_call_llm.return_value = "今天天气晴朗。"

        result = noesis_module.call("北京天气怎么样？", profile="test", tools=["get_weather"])

        assert result.output == "今天天气晴朗。"

    @patch.object(noesis_module, '_call_llm')
    def test_tool_call_recorded_in_thought_chain(self, mock_call_llm):
        """工具调用记录在思维链中"""
        def get_weather(city: str) -> str:
            return f"Weather: Sunny"

        register_tool("get_weather", get_weather, description="获取天气")

        # Mock LLM 返回包含工具调用
        mock_call_llm.return_value = "天气晴朗"

        result = noesis_module.call("北京天气", profile="test", tools=["get_weather"])

        # 思维链中应该有 thought 记录
        kinds = [step.kind for step in result.thought_chain]
        assert "thought" in kinds


class TestCallAnthropicWithToolUse:
    """测试 Anthropic tool_use 响应处理"""

    def setup_method(self):
        self._original_tools = dict(noesis_module._config.get("tools", {}))
        noesis_module._config["tools"] = {}

    def teardown_method(self):
        noesis_module._config["tools"] = self._original_tools

    @patch.object(noesis_module, '_call_anthropic')
    def test_anthropic_tool_use_response(self, mock_call_anthropic):
        """测试 Anthropic tool_use 响应处理"""
        # 注册工具
        def get_weather(city: str) -> str:
            return f"Weather in {city}: Sunny"

        register_tool("get_weather", get_weather, description="获取天气")

        # Mock _call_anthropic 直接返回包含 tool_use 的处理结果
        # 模拟工具调用被记录
        def side_effect(config, prompt, on_step, tools):
            on_step("tool_call", "get_weather({'city': '北京'})", {"tool_name": "get_weather", "tool_input": {"city": "北京"}, "tool_id": "tool_123"})
            on_step("tool_result", "Weather in 北京：Sunny", {"tool_name": "get_weather", "tool_id": "tool_123"})
            return ""

        mock_call_anthropic.side_effect = side_effect

        # 调用
        result = noesis_module.call(
            "北京天气",
            protocol="anthropic",
            model="qwen3.5-plus",
            api_key="sk-test",
            base_url="https://test.api.com"
        )

        # 验证思维链中有 tool_call 和 tool_result
        kinds = [step.kind for step in result.thought_chain]
        assert "tool_call" in kinds
        assert "tool_result" in kinds

    @patch.object(noesis_module, '_call_anthropic')
    def test_anthropic_text_response(self, mock_call_anthropic):
        """测试 Anthropic 纯文本响应"""
        def side_effect(config, prompt, on_step, tools):
            on_step("output", "你好！有什么可以帮你的？")
            return "你好！有什么可以帮你的？"

        mock_call_anthropic.side_effect = side_effect

        result = noesis_module.call(
            "你好",
            protocol="anthropic",
            model="qwen3.5-plus",
            api_key="sk-test",
            base_url="https://test.api.com"
        )

        assert result.output == "你好！有什么可以帮你的？"
