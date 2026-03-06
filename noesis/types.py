"""
类型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Literal


@dataclass
class ThoughtStep:
    """思维链中的一个步骤"""
    seq: int
    kind: Literal["thought", "tool_call", "tool_result", "decision", "output"]
    content: str
    parent_step: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "kind": self.kind,
            "content": self.content,
            "parent_step": self.parent_step,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data or {},
        }


@dataclass
class CallResult:
    """单次调用的完整结果"""
    prompt: str
    output: str
    thought_chain: list[ThoughtStep] = field(default_factory=list)
    duration_ms: int = 0
    model: Optional[str] = None
    cost_usd: Optional[float] = None

    def __bool__(self) -> bool:
        return bool(self.output)

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "output": self.output,
            "thought_chain": [s.to_dict() for s in self.thought_chain],
            "duration_ms": self.duration_ms,
            "model": self.model,
            "cost_usd": self.cost_usd,
            "thought_count": len(self.thought_chain),
        }
