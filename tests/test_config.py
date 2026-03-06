"""
TOML 配置加载测试
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestTomlConfigLoading:
    """TOML 配置加载测试"""

    def setup_method(self):
        """每个测试前清空 profiles"""
        from noesis.call import _config
        self._original_profiles = dict(_config["profiles"])
        _config["profiles"] = {}

    def teardown_method(self):
        """每个测试后恢复 profiles"""
        from noesis.call import _config
        _config["profiles"] = self._original_profiles

    def test_parse_toml_config_basic(self):
        """解析基本 TOML 配置"""
        from noesis.call import _parse_toml_config

        toml_content = """
[profiles.fast]
protocol = "anthropic"
model = "qwen-max"
base_url = "https://test.api.com"
api_key = "sk-test-key"
max_tokens = 2048
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                profiles = _parse_toml_config(Path(f.name))
                assert "fast" in profiles
                assert profiles["fast"].protocol == "anthropic"
                assert profiles["fast"].model == "qwen-max"
                assert profiles["fast"].api_key == "sk-test-key"
                assert profiles["fast"].max_tokens == 2048
            finally:
                os.unlink(f.name)

    def test_parse_toml_env_var(self):
        """解析带环境变量的 TOML 配置"""
        from noesis.call import _parse_toml_config

        toml_content = """
[profiles.test]
protocol = "anthropic"
model = "test-model"
api_key = "${TEST_API_KEY}"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                with patch.dict(os.environ, {"TEST_API_KEY": "env-key-123"}):
                    profiles = _parse_toml_config(Path(f.name))
                    assert profiles["test"].api_key == "env-key-123"
            finally:
                os.unlink(f.name)

    def test_parse_toml_missing_file(self):
        """解析不存在的文件"""
        from noesis.call import _parse_toml_config
        profiles = _parse_toml_config(Path("/nonexistent/path.toml"))
        assert profiles == {}

    def test_parse_toml_invalid_syntax(self):
        """解析无效的 TOML 语法"""
        from noesis.call import _parse_toml_config

        toml_content = """
[profiles.test
protocol = invalid
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                profiles = _parse_toml_config(Path(f.name))
                assert profiles == {}  # 解析失败返回空字典
            finally:
                os.unlink(f.name)

    def test_parse_toml_no_profiles_section(self):
        """解析没有 profiles 部分的 TOML"""
        from noesis.call import _parse_toml_config

        toml_content = """
[other]
key = "value"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                profiles = _parse_toml_config(Path(f.name))
                assert profiles == {}
            finally:
                os.unlink(f.name)

    def test_parse_toml_default_values(self):
        """解析使用默认值的配置"""
        from noesis.call import _parse_toml_config

        toml_content = """
[profiles.minimal]
model = "test-model"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                profiles = _parse_toml_config(Path(f.name))
                assert profiles["minimal"].protocol == "anthropic"  # 默认值
                assert profiles["minimal"].max_tokens == 4096  # 默认值
            finally:
                os.unlink(f.name)
