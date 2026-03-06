"""
noesis — LLM 思维链调用库

让思考过程可见。

Usage:
    from noesis import call

    result = call(
        prompt="分析这个任务并逐步思考",
        model="claude-sonnet-4-6",
        log_to="./session.jsonl",
    )

    # 查看思维链
    for step in result.thought_chain:
        print(f"[{step.kind}] {step.content}")
"""

__version__ = "0.1.0"
__author__ = "will"

from .call import call, configure
from .types import ThoughtStep, CallResult
from .mcp import load_mcp

__all__ = [
    "call",
    "configure",
    "load_mcp",
    "ThoughtStep",
    "CallResult",
]
