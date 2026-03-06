"""
call() 函数集成测试（使用 mock）
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from importlib import import_module

# 正确导入 noesis 模块（不是 call 函数）
noesis_module = import_module('noesis.call')

from noesis.call import LLMConfig, ModelProfile, register_profile, configure, _call_llm
from noesis.types import ThoughtStep, CallResult


class TestCallFunction:
    """call() 函数测试"""

    def setup_method(self):
        """每个测试前清空 profiles"""
        self._original_profiles = dict(noesis_module._config["profiles"])
        noesis_module._config["profiles"] = {}

    def teardown_method(self):
        """每个测试后恢复 profiles"""
        noesis_module._config["profiles"] = self._original_profiles

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_profile(self, mock_call_lllm):
        """使用 profile 调用"""
        mock_call_lllm.return_value = "你好！有什么可以帮你的？"

        profile = ModelProfile(
            name="test",
            protocol="anthropic",
            model="test-model",
            api_key="sk-test",
        )
        register_profile("test", profile)

        result = noesis_module.call("你好", profile="test")

        assert result.output == "你好！有什么可以帮你的？"
        assert result.model == "test-model"
        assert len(result.thought_chain) >= 1  # 至少有 prompt

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_direct_config(self, mock_call_lllm):
        """直接使用配置调用"""
        mock_call_lllm.return_value = " respuesta"

        result = noesis_module.call(
            "Hola",
            protocol="anthropic",
            model="claude-3",
            api_key="sk-test",
        )

        assert result.output == " respuesta"
        assert result.model == "claude-3"

    @patch.object(noesis_module, '_call_llm')
    def test_call_openai_protocol(self, mock_call_lllm):
        """使用 OpenAI 协议调用"""
        mock_call_lllm.return_value = "Hello!"

        result = noesis_module.call(
            "Hi",
            protocol="openai",
            model="gpt-4o",
            api_key="sk-test",
        )

        assert result.output == "Hello!"
        mock_call_lllm.assert_called_once()

    @patch.object(noesis_module, '_call_llm')
    def test_call_ollama_protocol(self, mock_call_lllm):
        """使用 Ollama 协议调用"""
        mock_call_lllm.return_value = "I'm Ollama"

        result = noesis_module.call(
            "Who are you?",
            protocol="ollama",
            model="llama3",
        )

        assert result.output == "I'm Ollama"
        mock_call_lllm.assert_called_once()

    @patch.object(noesis_module, '_call_llm')
    def test_call_unknown_protocol(self, mock_call_llm):
        """未知协议抛出异常"""
        mock_call_llm.side_effect = ValueError("Unknown protocol: unknown")

        with pytest.raises(ValueError, match="Unknown protocol: unknown"):
            noesis_module.call(
                "test",
                protocol="unknown",
                api_key="test",
            )

    @patch.object(noesis_module, '_call_llm')
    def test_call_records_thought_chain(self, mock_call_lllm):
        """验证思维链记录"""
        mock_call_lllm.return_value = "output"

        result = noesis_module.call("test prompt", profile="test")

        # 应该有 prompt 和 output 两个步骤
        assert len(result.thought_chain) >= 1
        # 第一个是 prompt
        assert result.thought_chain[0].kind == "thought"
        assert result.thought_chain[0].content == "test prompt"

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_system_prompt(self, mock_call_lllm):
        """带 system prompt 调用"""
        mock_call_lllm.return_value = "output"

        result = noesis_module.call(
            "用户消息",
            protocol="anthropic",
            model="test",
            api_key="sk-test",
            system="你是一个助手",
        )

        assert result.output == "output"

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_max_tokens(self, mock_call_lllm):
        """带 max_tokens 调用"""
        mock_call_lllm.return_value = "output"

        result = noesis_module.call(
            "test",
            protocol="anthropic",
            model="test",
            api_key="sk-test",
            max_tokens=1024,
        )

        assert result.output == "output"

    @patch.object(noesis_module, '_call_llm')
    def test_call_returns_call_result(self, mock_call_lllm):
        """验证返回类型"""
        mock_call_lllm.return_value = "output"

        result = noesis_module.call(
            "test",
            protocol="anthropic",
            model="test",
            api_key="sk-test",
        )

        assert isinstance(result, CallResult)
        assert bool(result) is True  # 有输出为 True


class TestCallLogging:
    """call() 日志记录测试"""

    def setup_method(self):
        self._original_profiles = dict(noesis_module._config["profiles"])
        noesis_module._config["profiles"] = {}
        self._original_log_dir = noesis_module._config.get("log_dir")
        noesis_module._config["log_dir"] = None

    def teardown_method(self):
        noesis_module._config["profiles"] = self._original_profiles
        noesis_module._config["log_dir"] = self._original_log_dir

    @patch.object(noesis_module, '_call_llm')
    def test_call_log_to_file(self, mock_call_lllm, tmp_path):
        """测试日志写入文件"""
        mock_call_lllm.return_value = "output"

        log_file = tmp_path / "test_session.jsonl"

        result = noesis_module.call(
            "test",
            protocol="anthropic",
            model="test",
            api_key="sk-test",
            log_to=str(log_file),
        )

        # 验证日志文件存在
        assert log_file.exists()

        # 验证日志内容
        content = log_file.read_text()
        lines = content.strip().split('\n')
        assert len(lines) >= 2  # start + end

        # 解析 JSONL
        import json
        first_log = json.loads(lines[0])
        assert first_log["type"] == "start"
        assert first_log["model"] == "test"

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_trace_enabled(self, mock_call_lllm, tmp_path):
        """测试启用 trace 时的日志"""
        mock_call_lllm.return_value = "output"

        configure(trace_enabled=True, log_dir=str(tmp_path))

        result = noesis_module.call(
            "test",
            protocol="anthropic",
            model="test",
            api_key="sk-test",
        )

        # 验证日志文件被创建
        log_files = list(tmp_path.glob("session_*.jsonl"))
        assert len(log_files) > 0


class TestCallWithConfigObject:
    """使用 LLMConfig 对象调用测试"""

    @patch.object(noesis_module, '_call_llm')
    def test_call_with_config_object(self, mock_call_lllm):
        """使用 LLMConfig 对象调用"""
        mock_call_lllm.return_value = "output"

        config = LLMConfig(
            protocol="anthropic",
            model="test-model",
            api_key="sk-config-key",
        )

        result = noesis_module.call("test", config=config)

        assert result.output == "output"
        assert result.model == "test-model"

    @patch.object(noesis_module, '_call_llm')
    def test_call_config_priority(self, mock_call_lllm):
        """测试配置优先级：函数参数 > config > profile"""
        mock_call_lllm.return_value = "output"

        # 注册 profile
        profile = ModelProfile(
            name="test",
            protocol="openai",  # profile 是 openai
            model="profile-model",
            api_key="sk-profile",
        )
        register_profile("test", profile)

        # config 覆盖 profile
        config = LLMConfig(
            protocol="anthropic",
            model="config-model",
            api_key="sk-config",
        )

        # 函数参数覆盖 config
        result = noesis_module.call(
            "test",
            config=config,
            profile="test",
            model="param-model",  # 参数优先级最高
        )

        assert result.model == "param-model"