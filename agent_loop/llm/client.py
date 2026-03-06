"""
LLM 客户端 - 统一的 LLM 调用接口

支持：
- Claude Code CLI
- OpenAI Codex CLI
- Ollama (本地模型)
- OpenAI API
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from ..types import ThoughtChunk, ToolCall

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """LLM 调用结果"""
    output: str
    thought_chain: list[ThoughtChunk] = None
    tool_calls: list[ToolCall] = None
    raw_response: Any = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None

    def __post_init__(self):
        if self.thought_chain is None:
            self.thought_chain = []
        if self.tool_calls is None:
            self.tool_calls = []


class LLMClient:
    """
    统一的 LLM 客户端

    支持的 Provider:
    - claude: Claude Code CLI
    - codex: OpenAI Codex CLI
    - ollama: Ollama 本地模型
    - openai: OpenAI API
    """

    def __init__(
        self,
        provider: str = "claude",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        on_think_chunk: Optional[Callable[[ThoughtChunk], None]] = None,
        on_tool_call: Optional[Callable[[ToolCall], None]] = None,
    ):
        self.provider = provider
        self.model = model or self._default_model(provider)
        self.api_key = api_key
        self.base_url = base_url
        self.on_think_chunk = on_think_chunk
        self.on_tool_call = on_tool_call

    def _default_model(self, provider: str) -> str:
        """获取默认模型"""
        models = {
            "claude": "claude-sonnet-4-6",
            "codex": "o3",
            "ollama": "llama3.1:8b",
            "openai": "gpt-4o",
        }
        return models.get(provider, "gpt-3.5-turbo")

    def execute(
        self,
        prompt: str,
        context: dict = None,
        tools: list = None,
    ) -> LLMResult:
        """
        执行 LLM 调用

        Args:
            prompt: Prompt 内容
            context: 上下文信息
            tools: 可用工具列表

        Returns:
            LLMResult: 调用结果
        """
        start_time = time.time()

        if self.provider == "claude":
            result = self._execute_claude(prompt, context, tools)
        elif self.provider == "codex":
            result = self._execute_codex(prompt, context, tools)
        elif self.provider == "ollama":
            result = self._execute_ollama(prompt, context, tools)
        elif self.provider == "openai":
            result = self._execute_openai(prompt, context, tools)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        result.latency_ms = int((time.time() - start_time) * 1000)
        return result

    def _execute_claude(
        self,
        prompt: str,
        context: dict = None,
        tools: list = None,
    ) -> LLMResult:
        """调用 Claude Code CLI"""
        logger.info("🤖 调用 Claude Code CLI...")

        # 构建命令
        cmd = ["claude", "-p", prompt, "--output-format", "json"]

        if self.model:
            cmd.extend(["--model", self.model])

        # 执行
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
            )

            # 解析 JSON 输出
            try:
                response = json.loads(proc.stdout)
            except json.JSONDecodeError:
                response = {"output_text": proc.stdout}

            # 提取思考过程（如果有）
            thought_chain = []
            if "thought" in response:
                thought_chain = [
                    ThoughtChunk(text=response["thought"], sequence=0)
                ]
                # 触发回调
                if self.on_think_chunk:
                    for chunk in thought_chain:
                        self.on_think_chunk(chunk)

            # 提取工具调用（如果有）
            tool_calls = []
            if "tool_calls" in response:
                tool_calls = [
                    ToolCall(name=tc.get("name", ""), args=tc.get("args", {}))
                    for tc in response["tool_calls"]
                ]

            return LLMResult(
                output=response.get("output_text", response.get("result", "")),
                thought_chain=thought_chain,
                tool_calls=tool_calls,
                raw_response=response,
                cost_usd=response.get("cost_usd"),
            )

        except subprocess.TimeoutExpired:
            raise TimeoutError("Claude Code execution timed out")
        except FileNotFoundError:
            raise RuntimeError("Claude Code CLI not found. Please install it first.")

    def _execute_codex(
        self,
        prompt: str,
        context: dict = None,
        tools: list = None,
    ) -> LLMResult:
        """调用 OpenAI Codex CLI"""
        logger.info("🤖 调用 Codex CLI...")

        cmd = ["codex", "exec", "-c", prompt]

        if self.model:
            cmd.extend(["-m", self.model])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
            )

            response = {"output_text": proc.stdout}

            return LLMResult(
                output=proc.stdout,
                raw_response=response,
            )

        except subprocess.TimeoutExpired:
            raise TimeoutError("Codex execution timed out")

    def _execute_ollama(
        self,
        prompt: str,
        context: dict = None,
        tools: list = None,
    ) -> LLMResult:
        """调用 Ollama"""
        logger.info(f"🦙 调用 Ollama ({self.model})...")

        import requests

        url = self.base_url or "http://localhost:11434/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()

            return LLMResult(
                output=data.get("response", ""),
                raw_response=data,
            )

        except requests.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def _execute_openai(
        self,
        prompt: str,
        context: dict = None,
        tools: list = None,
    ) -> LLMResult:
        """调用 OpenAI API"""
        logger.info(f"🤖 调用 OpenAI API ({self.model})...")

        import requests

        url = self.base_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]

            # 提取工具调用
            tool_calls = []
            if "tool_calls" in message:
                tool_calls = [
                    ToolCall(
                        name=tc["function"]["name"],
                        args=json.loads(tc["function"]["arguments"]),
                    )
                    for tc in message["tool_calls"]
                ]

            return LLMResult(
                output=message.get("content", ""),
                tool_calls=tool_calls,
                raw_response=data,
                cost_usd=None,  # OpenAI API 需要额外计算
            )

        except requests.RequestException as e:
            raise RuntimeError(f"OpenAI API request failed: {e}")
