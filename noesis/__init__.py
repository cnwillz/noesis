"""
noesis — LLM 思维链调用库

让思考过程可见。

Usage:
    from noesis import call, LLMConfig, ModelProfile, register_profile

    # 方式 1: 使用 Profile（推荐，不暴露敏感信息）
    # 环境变量配置：
    #   export NOESIS_PROFILES='{"fast":{"model":"claude-3-haiku"},"smart":{"model":"claude-3-opus"}}'
    result = call("你好", profile="fast")
    result = call("复杂任务", profile="smart")

    # 方式 2: 代码中注册 Profile
    register_profile(
        "fast",
        ModelProfile(name="fast", model="claude-3-haiku-20240307"),
    )
    result = call("你好", profile="fast")

    # 方式 3: 直接使用 LLMConfig
    config = LLMConfig(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        api_key="sk-ant-...",
    )
    result = call("你好", config=config)

    # 查看思维链
    for step in result.thought_chain:
        print(f"[{step.kind}] {step.content}")

    # 查看所有可用 profiles
    print(list_profiles())  # ["fast", "smart"]
"""

__version__ = "0.1.0"
__author__ = "will"

from .call import call, configure, LLMConfig, ModelProfile, register_profile, get_profile, list_profiles
from .types import ThoughtStep, CallResult
from .mcp import load_mcp

__all__ = [
    "call",
    "configure",
    "load_mcp",
    "LLMConfig",
    "ModelProfile",
    "register_profile",
    "get_profile",
    "list_profiles",
    "ThoughtStep",
    "CallResult",
]
