"""
类型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CycleStatus(str, Enum):
    """周期执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CIRCUIT_BREAK = "circuit_break"


class EventType(str, Enum):
    """事件类型"""
    CYCLE_START = "cycle_start"
    CYCLE_COMPLETE = "cycle_complete"
    CYCLE_ERROR = "cycle_error"
    CONSENSUS_READ = "consensus_read"
    CONSENSUS_WRITE = "consensus_write"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"


@dataclass
class ThoughtChunk:
    """思考片段"""
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    sequence: int = 0  # 思考顺序


@dataclass
class ToolCall:
    """工具调用"""
    name: str
    args: dict
    result: Any = None
    status: str = "pending"  # pending, success, error
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None


@dataclass
class Event:
    """结构化事件"""
    event_type: EventType
    cycle_id: Optional[int] = None
    data: Optional[dict] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None

    def to_json(self) -> dict:
        """转换为 JSON 格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event": self.event_type.value,
            "cycle_id": self.cycle_id,
            "data": self.data,
            "error": self.error,
            "traceback": self.traceback,
            "duration_ms": self.duration_ms,
        }


@dataclass
class CycleResult:
    """周期执行结果"""
    cycle_id: int
    status: CycleStatus
    output: str = ""
    error: Optional[str] = None
    thought_chain: list[ThoughtChunk] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    duration_ms: int = 0
    consensus_updated: bool = False
    metadata: dict = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.status == CycleStatus.SUCCESS

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "cycle_id": self.cycle_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "consensus_updated": self.consensus_updated,
            "thought_count": len(self.thought_chain),
            "tool_call_count": len(self.tool_calls),
            "metadata": self.metadata,
        }


@dataclass
class TraceSpan:
    """调用链 Span"""
    span_id: str
    name: str
    parent_span_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    data: dict = field(default_factory=dict)

    def duration(self) -> Optional[float]:
        """计算持续时间（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
