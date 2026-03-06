"""
MCP 加载测试
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from noesis.mcp import load_mcp


class TestLoadMcp:
    """MCP 加载测试"""

    def test_load_mcp_success(self):
        """成功加载 MCP 配置"""
        config_data = {
            "mcpServers": {
                "tavily": {
                    "command": "npx",
                    "args": ["-y", "tavily-mcp"]
                },
                "slack": {
                    "command": "npx",
                    "args": ["-y", "@slack/mcp"]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            try:
                result = load_mcp(f.name)
                assert result == config_data
                assert len(result.get('mcpServers', {})) == 2
            finally:
                os.unlink(f.name)

    def test_load_mcp_file_not_found(self):
        """文件不存在"""
        with pytest.raises(FileNotFoundError):
            load_mcp("/nonexistent/path.json")

    def test_load_mcp_empty_config(self):
        """加载空配置"""
        config_data = {}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            try:
                result = load_mcp(f.name)
                assert result == {}
            finally:
                os.unlink(f.name)

    def test_load_mcp_invalid_json(self):
        """加载无效的 JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            f.flush()
            try:
                with pytest.raises(json.JSONDecodeError):
                    load_mcp(f.name)
            finally:
                os.unlink(f.name)
