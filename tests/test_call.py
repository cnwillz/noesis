"""
LLM 配置和 Profiles 测试
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from noesis.call import LLMConfig, ModelProfile, register_profile, get_profile, list_profiles, configure


class TestLLMConfig:
    """LLMConfig 配置测试"""

    def test_default_config(self):
        """默认配置"""
        config = LLMConfig()
        assert config.protocol == "anthropic"
        assert config.model is None
        assert config.api_key is None
        assert config.base_url is None
        assert config.max_tokens == 4096

    def test_custom_config(self):
        """自定义配置"""
        config = LLMConfig(
            protocol="openai",
            model="gpt-4o",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            max_tokens=2048,
        )
        assert config.protocol == "openai"
        assert config.model == "gpt-4o"
        assert config.api_key == "sk-test"
        assert config.max_tokens == 2048

    def test_get_api_key(self):
        """获取 API Key"""
        config = LLMConfig(api_key="sk-test-key")
        assert config.get_api_key() == "sk-test-key"

    def test_get_base_url_custom(self):
        """获取自定义 base_url"""
        config = LLMConfig(base_url="https://custom.api.com/v1")
        assert config.get_base_url() == "https://custom.api.com/v1"

    def test_get_base_url_anthropic(self):
        """获取 Anthropic 默认 URL"""
        config = LLMConfig(protocol="anthropic")
        assert config.get_base_url() == "https://api.anthropic.com/v1/messages"

    def test_get_base_url_openai(self):
        """获取 OpenAI 默认 URL"""
        config = LLMConfig(protocol="openai")
        assert config.get_base_url() == "https://api.openai.com/v1/chat/completions"

    def test_get_base_url_ollama(self):
        """获取 Ollama 默认 URL"""
        config = LLMConfig(protocol="ollama")
        assert config.get_base_url() == "http://localhost:11434/api/generate"

    def test_get_model_with_value(self):
        """获取模型名称（已设置）"""
        config = LLMConfig(model="qwen-max")
        assert config.get_model() == "qwen-max"

    def test_get_model_default(self):
        """获取默认模型名称"""
        config = LLMConfig()
        assert config.get_model() == "default-model"


class TestModelProfile:
    """ModelProfile 配置测试"""

    def test_create_profile(self):
        """创建 Profile"""
        profile = ModelProfile(
            name="test",
            protocol="openai",
            model="gpt-4o",
            api_key="sk-test",
            max_tokens=2048,
        )
        assert profile.name == "test"
        assert profile.protocol == "openai"
        assert profile.model == "gpt-4o"
        assert profile.max_tokens == 2048

    def test_profile_to_config(self):
        """Profile 转换为 LLMConfig"""
        profile = ModelProfile(
            name="test",
            protocol="anthropic",
            model="claude-3-5",
            api_key="sk-test",
            base_url="https://test.api.com",
            max_tokens=1024,
            system="你是一个助手",
        )
        config = profile.to_config()
        assert config.protocol == "anthropic"
        assert config.model == "claude-3-5"
        assert config.api_key == "sk-test"
        assert config.base_url == "https://test.api.com"
        assert config.max_tokens == 1024
        assert config.system == "你是一个助手"


class TestProfileRegistry:
    """Profile 注册管理测试"""

    def setup_method(self):
        """每个测试前清空 profiles"""
        # 保存原有 profiles
        from noesis.call import _config
        self._original_profiles = dict(_config["profiles"])
        # 清空
        _config["profiles"] = {}

    def teardown_method(self):
        """每个测试后恢复 profiles"""
        from noesis.call import _config
        _config["profiles"] = self._original_profiles

    def test_register_profile(self):
        """注册 Profile"""
        profile = ModelProfile(name="test", model="test-model")
        register_profile("test", profile)
        assert "test" in list_profiles()

    def test_get_profile(self):
        """获取 Profile"""
        profile = ModelProfile(name="test", model="test-model")
        register_profile("test", profile)
        retrieved = get_profile("test")
        assert retrieved is not None
        assert retrieved.model == "test-model"

    def test_get_profile_not_found(self):
        """获取不存在的 Profile"""
        result = get_profile("nonexistent")
        assert result is None

    def test_list_profiles(self):
        """列出所有 Profiles"""
        register_profile("profile1", ModelProfile(name="profile1"))
        register_profile("profile2", ModelProfile(name="profile2"))
        profiles = list_profiles()
        assert "profile1" in profiles
        assert "profile2" in profiles

    def test_configure_default_profile(self):
        """配置默认 Profile"""
        configure(default_profile="test")
        from noesis.call import _config
        assert _config["default_profile"] == "test"

    def test_configure_log_dir(self):
        """配置日志目录"""
        configure(log_dir="/tmp/logs")
        from noesis.call import _config
        assert _config["log_dir"] == "/tmp/logs"

    def test_configure_trace_enabled(self):
        """配置追踪开关"""
        configure(trace_enabled=True)
        from noesis.call import _config
        assert _config["trace_enabled"] is True
