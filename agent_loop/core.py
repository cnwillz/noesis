"""
Agent Loop 核心实现

提供自主循环运行的核心逻辑，包含：
- 感知层：读取共识、状态、反馈
- 认知层：LLM 调用、思考过程、决策链
- 行动层：工具调用、文件操作
- 记忆层：共识更新、事件日志
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .types import (
    CycleResult,
    CycleStatus,
    ThoughtChunk,
    ToolCall,
    Event,
)
from .config import AgentConfig, ObservabilityConfig
from .llm.client import LLMClient
from .tools.registry import ToolRegistry
from .memory.consensus import ConsensusManager
from .memory.event_store import EventStore
from .observability.logger import StructuredLogger
from .observability.tracer import TraceCollector

logger = logging.getLogger(__name__)


@dataclass
class AgentLoop:
    """
    自主 Agent 循环运行器

    Attributes:
        prompt_file: Prompt 模板文件路径
        consensus_file: 共识文件路径
        config: Agent 配置
        obs_config: 可观测性配置
    """

    prompt_file: str
    consensus_file: str
    config: AgentConfig = field(default_factory=AgentConfig)
    obs_config: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    # 运行时状态（内部）
    _llm: Optional[LLMClient] = None
    _tools: Optional[ToolRegistry] = None
    _consensus: Optional[ConsensusManager] = None
    _events: Optional[EventStore] = None
    _logger: Optional[StructuredLogger] = None
    _tracer: Optional[TraceCollector] = None
    _cycle_count: int = 0
    _error_count: int = 0
    _running: bool = False

    def __post_init__(self):
        """初始化后设置"""
        # 路径解析
        self.prompt_path = Path(self.prompt_file).expanduser().resolve()
        self.consensus_path = Path(self.consensus_file).expanduser().resolve()
        self.workdir = self.consensus_path.parent

        # 验证文件存在
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_file}")

        # 初始化组件
        self._init_components()

    def _init_components(self):
        """初始化所有组件"""
        # 确保目录存在
        self.workdir.mkdir(parents=True, exist_ok=True)
        logs_dir = self.workdir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # LLM 客户端
        self._llm = LLMClient(
            provider=self.config.provider,
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            # 可观测性回调
            on_think_chunk=self._on_think_chunk,
            on_tool_call=self._on_tool_call,
        )

        # 工具注册表
        self._tools = ToolRegistry()
        self._register_default_tools()

        # 共识管理器
        self._consensus = ConsensusManager(self.consensus_path)

        # 事件存储
        self._events = EventStore(logs_dir / "events.jsonl")

        # 结构化日志
        self._logger = StructuredLogger(
            output_file=logs_dir / "agent.log",
            verbose=self.obs_config.verbose,
        )

        # 调用链追踪
        self._tracer = TraceCollector(logs_dir / "traces")

    def _register_default_tools(self):
        """注册默认工具"""
        from .tools.file_ops import register_file_tools
        from .tools.shell import register_shell_tools

        register_file_tools(self._tools)
        register_shell_tools(self._tools)

    def _on_think_chunk(self, chunk: ThoughtChunk):
        """思考片段回调"""
        if self.obs_config.log_thoughts:
            self._logger.log_thought(chunk)
            self._tracer.add_span({
                "name": "thought",
                "data": {"chunk": chunk.text},
                "timestamp": chunk.timestamp.isoformat(),
            })

    def _on_tool_call(self, call: ToolCall):
        """工具调用回调"""
        if self.obs_config.trace_tools:
            self._logger.log_tool_call(call)
            self._tracer.add_span({
                "name": f"tool_call:{call.name}",
                "data": {
                    "args": call.args,
                    "status": call.status,
                },
                "timestamp": call.timestamp.isoformat(),
            })

    def run(self) -> CycleResult:
        """
        运行单个周期

        Returns:
            CycleResult: 周期执行结果
        """
        self._cycle_count += 1
        cycle_id = self._cycle_count

        # 记录周期开始
        start_time = time.time()
        self._logger.log_event(Event(
            event_type="cycle_start",
            cycle_id=cycle_id,
            timestamp=datetime.now(),
        ))
        self._tracer.start_cycle(cycle_id)

        try:
            # Phase 1: 感知
            self._logger.info(f"🔄 周期 #{cycle_id} 开始")
            context = self._perceive()

            # Phase 2: 认知（LLM 调用 + 思考）
            self._logger.info("🧠 开始分析...")
            llm_result = self._cognize(context)

            # Phase 3: 行动（工具调用）
            self._logger.info("🔧 执行行动...")
            action_result = self._act(llm_result)

            # Phase 4: 记忆（更新共识）
            self._logger.info("📝 更新共识...")
            self._memorize(action_result)

            # 记录周期完成
            duration = time.time() - start_time
            result = CycleResult(
                cycle_id=cycle_id,
                status=CycleStatus.SUCCESS,
                output=llm_result.output,
                thought_chain=llm_result.thought_chain,
                tool_calls=llm_result.tool_calls,
                duration_ms=int(duration * 1000),
            )

            self._logger.log_event(Event(
                event_type="cycle_complete",
                cycle_id=cycle_id,
                duration_ms=result.duration_ms,
                timestamp=datetime.now(),
            ))
            self._tracer.end_cycle(cycle_id, result)

            self._error_count = 0  # 重置错误计数
            return result

        except Exception as e:
            # 记录错误
            duration = time.time() - start_time
            self._error_count += 1

            self._logger.error(f"❌ 周期 #{cycle_id} 失败：{e}")
            self._logger.log_event(Event(
                event_type="cycle_error",
                cycle_id=cycle_id,
                error=str(e),
                traceback=traceback.format_exc(),
                timestamp=datetime.now(),
            ))
            self._tracer.end_cycle(cycle_id, CycleResult(
                cycle_id=cycle_id,
                status=CycleStatus.ERROR,
                error=str(e),
                duration_ms=int(duration * 1000),
            ))

            # 熔断检查
            if self._error_count >= self.config.max_errors:
                self._logger.critical(f"🔥 熔断器触发！连续{self._error_count}次错误")
                # 触发熔断回调
                if self.config.on_circuit_break:
                    self.config.on_circuit_break(self._error_count)

            raise

    def _perceive(self) -> dict:
        """
        感知层：收集当前状态

        Returns:
            包含共识、反馈、信号的上下文字典
        """
        # 读取共识
        consensus = self._consensus.read()

        # 读取反馈（如果有）
        feedback = []
        feedback_dir = self.workdir / "docs" / "feedback"
        if feedback_dir.exists():
            for f in feedback_dir.glob("*.json"):
                feedback.append(json.loads(f.read_text()))

        # 读取社区信号（如果有）
        community_signals = []
        community_dir = self.workdir / "docs" / "community"
        if community_dir.exists():
            for f in community_dir.glob("*.md"):
                community_signals.append(f.read_text())

        return {
            "consensus": consensus,
            "feedback": feedback,
            "community_signals": community_signals,
            "cycle_number": self._cycle_count,
        }

    def _cognize(self, context: dict) -> LLMResult:
        """
        认知层：LLM 调用 + 思考过程

        Returns:
            LLM 调用结果
        """
        # 读取 Prompt 模板
        prompt_template = self.prompt_path.read_text()

        # 构建完整 Prompt
        full_prompt = self._build_prompt(prompt_template, context)

        # 调用 LLM（带流式思考输出）
        llm_result = self._llm.execute(
            prompt=full_prompt,
            context=context,
            tools=self._tools.list_tools(),
        )

        return llm_result

    def _act(self, llm_result: LLMResult) -> dict:
        """
        行动层：执行工具调用

        Returns:
            行动结果
        """
        action_results = []

        for tool_call in llm_result.tool_calls:
            self._logger.info(f"  🔧 执行：{tool_call.name}({tool_call.args})")

            result = self._tools.call(tool_call.name, **tool_call.args)

            action_results.append({
                "tool": tool_call.name,
                "args": tool_call.args,
                "result": result,
            })

            self._on_tool_call(ToolCall(
                name=tool_call.name,
                args=tool_call.args,
                result=result,
                status="success",
            ))

        return {"actions": action_results}

    def _memorize(self, action_result: dict):
        """
        记忆层：更新共识和日志
        """
        # 如果共识被修改，保存新版本
        if action_result.get("consensus_updated"):
            self._consensus.save(action_result["consensus_content"])

    def _build_prompt(self, template: str, context: dict) -> str:
        """构建完整的 Prompt"""
        # 简单模板替换
        prompt = template

        # 插入共识
        if "consensus" in context:
            prompt = prompt.replace("{{CONSENSUS}}", context["consensus"])

        # 插入反馈
        if "feedback" in context:
            feedback_text = json.dumps(context["feedback"], indent=2, ensure_ascii=False)
            prompt = prompt.replace("{{FEEDBACK}}", feedback_text)

        return prompt

    def start_daemon(self, interval: Optional[int] = None):
        """
        以守护进程模式启动

        Args:
            interval: 周期间隔（秒），默认使用配置值
        """
        interval = interval or self.config.loop_interval
        self._running = True

        self._logger.info(f"🚀 Agent 守护进程启动 (间隔：{interval}s)")

        # 信号处理
        def signal_handler(sig, frame):
            self._logger.info("👋 收到退出信号，正在关闭...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 主循环
        while self._running:
            try:
                self.run()
            except Exception as e:
                self._logger.error(f"周期执行失败：{e}")

            # 冷却
            if self._running:
                time.sleep(interval)

        self._logger.info("✅ 守护进程已停止")


@dataclass
class LLMResult:
    """LLM 执行结果"""
    output: str
    thought_chain: list[ThoughtChunk] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_response: Any = None


async def run_cycle_async(
    prompt_file: str,
    consensus_file: str,
    config: Optional[AgentConfig] = None,
    obs_config: Optional[ObservabilityConfig] = None,
) -> CycleResult:
    """异步运行单周期"""
    loop = AgentLoop(
        prompt_file=prompt_file,
        consensus_file=consensus_file,
        config=config or AgentConfig(),
        obs_config=obs_config or ObservabilityConfig(),
    )
    return loop.run()


def run_cycle(
    prompt_file: str,
    consensus_file: str,
    config: Optional[AgentConfig] = None,
    obs_config: Optional[ObservabilityConfig] = None,
) -> CycleResult:
    """同步运行单周期"""
    return asyncio.run(run_cycle_async(
        prompt_file=prompt_file,
        consensus_file=consensus_file,
        config=config,
        obs_config=obs_config,
    ))
