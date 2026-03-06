"""
类型定义测试
"""

import pytest
from datetime import datetime
from noesis.types import ThoughtStep, CallResult


class TestThoughtStep:
    """ThoughtStep 类型测试"""

    def test_create_thought_step(self):
        """创建思维步骤"""
        step = ThoughtStep(
            seq=1,
            kind="thought",
            content="这是一个思考过程",
        )
        assert step.seq == 1
        assert step.kind == "thought"
        assert step.content == "这是一个思考过程"
        assert step.parent_step is None
        assert step.data is None
        assert isinstance(step.timestamp, datetime)

    def test_thought_step_with_parent(self):
        """带父步骤的思维步骤"""
        step = ThoughtStep(
            seq=2,
            kind="tool_call",
            content="调用工具",
            parent_step=1,
        )
        assert step.parent_step == 1

    def test_thought_step_with_data(self):
        """带附加数据的思维步骤"""
        step = ThoughtStep(
            seq=3,
            kind="tool_result",
            content="工具返回结果",
            data={"result": "success"},
        )
        assert step.data == {"result": "success"}

    def test_to_dict(self):
        """转换为字典"""
        step = ThoughtStep(
            seq=1,
            kind="output",
            content="输出内容",
            data={"key": "value"},
        )
        result = step.to_dict()
        assert result["seq"] == 1
        assert result["kind"] == "output"
        assert result["content"] == "输出内容"
        assert result["data"] == {"key": "value"}
        assert "timestamp" in result


class TestCallResult:
    """CallResult 类型测试"""

    def test_create_call_result(self):
        """创建调用结果"""
        result = CallResult(
            prompt="测试 prompt",
            output="测试输出",
            duration_ms=1000,
            model="test-model",
        )
        assert result.prompt == "测试 prompt"
        assert result.output == "测试输出"
        assert result.duration_ms == 1000
        assert result.model == "test-model"
        assert result.thought_chain == []
        assert result.cost_usd is None

    def test_call_result_with_thoughts(self):
        """带思维链的调用结果"""
        step = ThoughtStep(seq=1, kind="thought", content="思考")
        result = CallResult(
            prompt="test",
            output="output",
            thought_chain=[step],
        )
        assert len(result.thought_chain) == 1
        assert result.thought_chain[0].content == "思考"

    def test_call_result_bool_true(self):
        """有输出时布尔值为 True"""
        result = CallResult(prompt="test", output="有内容")
        assert bool(result) is True

    def test_call_result_bool_false(self):
        """无输出时布尔值为 False"""
        result = CallResult(prompt="test", output="")
        assert bool(result) is False

    def test_to_dict(self):
        """转换为字典"""
        step = ThoughtStep(seq=1, kind="thought", content="思考")
        result = CallResult(
            prompt="测试",
            output="输出",
            thought_chain=[step],
            duration_ms=500,
            model="test",
            cost_usd=0.001,
        )
        d = result.to_dict()
        assert d["prompt"] == "测试"
        assert d["output"] == "输出"
        assert d["duration_ms"] == 500
        assert d["model"] == "test"
        assert d["cost_usd"] == 0.001
        assert d["thought_count"] == 1
        assert len(d["thought_chain"]) == 1
