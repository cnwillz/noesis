"""
MCP 支持
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional


def load_mcp(config_path: str):
    """
    加载 MCP 服务器配置

    Args:
        config_path: MCP 配置文件路径（JSON 格式）

    Example:
        load_mcp("./mcp.json")
    """
    config_file = Path(config_path).expanduser()
    if not config_file.exists():
        raise FileNotFoundError(f"MCP config not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 这里后续可以集成 MCP 服务器
    # 目前先记录配置
    print(f"📦 MCP 配置已加载：{len(config.get('mcpServers', {}))} 个服务器")

    return config
