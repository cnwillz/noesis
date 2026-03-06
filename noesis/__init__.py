"""
noesis — LLM 思维链调用库

让思考过程可见。

Usage:
    from noesis import call, LLMConfig

    # 方式 1: 使用全局配置
    result = call(
        prompt="分析这个任务并逐步思考",
        log_to="./session.jsonl",
    )

    # 方式 2: 单次调用指定不同 provider
    result = call(
        prompt="Hello",
        provider="openai",
        model="gpt-4o",
        api_key="sk-...",
    )

    # 方式 3: 使用 LLMConfig 对象
    config = LLMConfig(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        api_key="sk-ant-...",
    )
    result = call("你好", config=config)

    # 查看思维链
    for step in result.thought_chain:
        print(f"[{step.kind}] {step.content}")
"""

__version__ = "0.1.0"
__author__ = "will"

from .call import call, configure, LLMConfig
from .types import ThoughtStep, CallResult
from .mcp import load_mcp

__all__ = [
    "call",
    "configure",
    "load_mcp",
    "LLMConfig",
    "ThoughtStep",
    "CallResult",
]
