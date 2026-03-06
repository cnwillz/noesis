"""
Agent Loop - 一个可观测的自主 Agent 运行时内核

Usage:
    from agent_loop import AgentLoop

    loop = AgentLoop(
        prompt_file="./PROMPT.md",
        consensus_file="./consensus.md",
    )
    result = loop.run()
"""

__version__ = "0.1.0"
__author__ = "Agent Loop Team"

from .core import AgentLoop, run_cycle
from .types import CycleResult, ThoughtChunk, ToolCall
from .config import AgentConfig

__all__ = [
    "AgentLoop",
    "run_cycle",
    "CycleResult",
    "ThoughtChunk",
    "ToolCall",
    "AgentConfig",
]
