"""
配置模块
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class AgentConfig:
    """
    Agent 配置

    Attributes:
        provider: LLM 提供商 (claude, openai, ollama 等)
        model: 模型名称
        api_key: API Key（可选，有些 Provider 不需要）
        base_url: 自定义 API 端点
        timeout_seconds: 单周期超时时间
        max_errors: 熔断前最大错误数
        cooldown_seconds: 熔断后冷却时间
        loop_interval: 周期间隔（秒）
        on_circuit_break: 熔断回调
    """

    # LLM 配置
    provider: str = "claude"
    model: str = "claude-sonnet-4-6"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # 循环配置
    timeout_seconds: int = 1800  # 30 分钟
    max_errors: int = 5
    cooldown_seconds: int = 300  # 5 分钟
    loop_interval: int = 30  # 30 秒

    # 回调
    on_circuit_break: Optional[Callable[[int], None]] = None

    # 工作目录
    workdir: Optional[str] = None


@dataclass
class ObservabilityConfig:
    """
    可观测性配置

    Attributes:
        verbose: 详细输出
        log_thoughts: 记录思考过程
        trace_tools: 追踪工具调用
        log_file: 日志文件路径
        trace_dir: 调用链追踪目录
    """

    verbose: bool = True
    log_thoughts: bool = True
    trace_tools: bool = True
    log_file: Optional[str] = None
    trace_dir: Optional[str] = None
