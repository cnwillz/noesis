"""
LLM 调用 - 核心接口

支持：
- Anthropic API (Claude)
- OpenAI API
- 兼容 OpenAI 格式的 API
- Ollama (本地模型)

配置优先级：
1. 代码配置 configure()
2. 环境变量 (NOESIS_*, ANTHROPIC_API_KEY, OPENAI_API_KEY 等)
3. 默认值
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .types import ThoughtStep, CallResult


def _load_env_config() -> dict:
    """从环境变量加载配置"""
    return {
        # Provider 配置
        "provider": os.environ.get("NOESIS_PROVIDER"),
        "model": os.environ.get("NOESIS_MODEL"),
        "api_key": os.environ.get("NOESIS_API_KEY"),
        "base_url": os.environ.get("NOESIS_BASE_URL"),

        # 日志配置
        "log_dir": os.environ.get("NOESIS_LOG_DIR"),
        "trace_enabled": os.environ.get("NOESIS_TRACE_ENABLED", "false").lower() == "true",

        # Provider 特定的 API Key
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
    }


# 全局配置（环境变量 + 默认值）
_env_config = _load_env_config()
_config = {
    "provider": _env_config["provider"] or "anthropic",
    "model": _env_config["model"],  # 自动根据 provider 选择
    "api_key": _env_config["api_key"],
    "base_url": _env_config["base_url"],
    "log_dir": _env_config["log_dir"],
    "trace_enabled": _env_config["trace_enabled"],

    # Provider 特定的 API Key
    "anthropic_api_key": _env_config["anthropic_api_key"],
    "openai_api_key": _env_config["openai_api_key"],
}


def configure(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    log_dir: Optional[str] = None,
    trace_enabled: Optional[bool] = None,
    # Provider 特定的 API Key（可选，覆盖通用 api_key）
    anthropic_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
):
    """
    配置全局参数

    配置优先级：
    1. 本函数参数（最高优先级）
    2. 环境变量
    3. 默认值

    环境变量列表:
    - NOESIS_PROVIDER: 提供商 (anthropic / openai / ollama)
    - NOESIS_MODEL: 模型名称
    - NOESIS_API_KEY: 通用 API Key
    - NOESIS_BASE_URL: 自定义 API 端点
    - NOESIS_LOG_DIR: 日志目录
    - NOESIS_TRACE_ENABLED: 是否启用追踪 (true/false)
    - ANTHROPIC_API_KEY: Anthropic 专用 API Key
    - OPENAI_API_KEY: OpenAI 专用 API Key

    Usage:
        configure(
            provider="anthropic",
            model="claude-sonnet-4-5-20251001",
            log_dir="./logs",
            trace_enabled=True,
        )
    """
    global _config
    if provider is not None:
        _config["provider"] = provider
    if model is not None:
        _config["model"] = model
    if api_key is not None:
        _config["api_key"] = api_key
    if base_url is not None:
        _config["base_url"] = base_url
    if log_dir is not None:
        _config["log_dir"] = log_dir
    if trace_enabled is not None:
        _config["trace_enabled"] = trace_enabled
    if anthropic_api_key is not None:
        _config["anthropic_api_key"] = anthropic_api_key
    if openai_api_key is not None:
        _config["openai_api_key"] = openai_api_key


def _get_model() -> str:
    """获取模型名称"""
    if _config["model"]:
        return _config["model"]

    defaults = {
        "anthropic": "claude-sonnet-4-5-20251001",
        "openai": "gpt-4o",
        "ollama": "llama3.1:8b",
    }
    return defaults.get(_config["provider"], "gpt-3.5-turbo")


def call(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    log_to: Optional[str] = None,
    trace: bool = False,
    system: Optional[str] = None,  # System prompt（仅 Anthropic）
    max_tokens: int = 4096,
) -> CallResult:
    """
    执行 LLM 调用（带完整思维链记录）

    Args:
        prompt: Prompt 内容
        model: 模型名称（可选，覆盖全局配置）
        provider: LLM 提供商（可选，覆盖全局配置）
        log_to: 日志文件路径（JSONL 格式）
        trace: 是否启用思维链追踪
        system: System prompt（仅 Anthropic）
        max_tokens: 最大输出 token 数

    Returns:
        CallResult: 调用结果，包含输出和思维链
    """
    start_time = time.time()
    provider = provider or _config["provider"]
    model = model or _get_model()

    # 确定日志输出位置
    log_path = log_to
    if not log_path and (_config["log_dir"] or trace):
        log_dir = _config["log_dir"] or "./logs"
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_path = f"{log_dir}/session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    # 日志记录器
    log_file = None
    if log_path:
        log_file = Path(log_path).expanduser()
        log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(entry: dict):
        if log_file:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 记录开始
    _log({
        "seq": 0,
        "type": "start",
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
    })

    thought_chain: list[ThoughtStep] = []
    seq = [0]  # 用列表实现可变引用

    def _add_step(kind: str, content: str, data: Optional[dict] = None):
        seq[0] += 1
        step = ThoughtStep(seq=seq[0], kind=kind, content=content, data=data)
        thought_chain.append(step)
        _log({
            "seq": step.seq,
            "type": kind,
            "content": content,
            "data": data or {},
            "timestamp": step.timestamp.isoformat(),
        })

    # 记录 prompt
    _add_step("output", prompt, {"role": "prompt"})

    # 调用 LLM
    output = _call_llm(provider, model, prompt, _add_step)

    # 记录结束
    duration_ms = int((time.time() - start_time) * 1000)
    _log({
        "seq": seq[0] + 1,
        "type": "end",
        "timestamp": datetime.now().isoformat(),
        "duration_ms": duration_ms,
        "output_length": len(output),
    })

    return CallResult(
        prompt=prompt,
        output=output,
        thought_chain=thought_chain,
        duration_ms=duration_ms,
        model=model,
    )


def _call_llm(
    provider: str,
    model: str,
    prompt: str,
    on_step: callable,
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """调用 LLM"""
    if provider == "anthropic":
        return _call_anthropic(model, prompt, on_step, system, max_tokens)
    elif provider == "openai":
        return _call_openai(model, prompt, on_step, max_tokens)
    elif provider == "ollama":
        return _call_ollama(model, prompt, on_step)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _get_api_key(provider: str) -> Optional[str]:
    """获取 API Key（优先级：专用 > 通用 > 环境变量）"""
    # 先检查 provider 专用的 API Key
    if provider == "anthropic":
        return _config["anthropic_api_key"] or _config["api_key"]
    elif provider == "openai":
        return _config["openai_api_key"] or _config["api_key"]
    return _config["api_key"]


def _get_base_url(provider: str) -> str:
    """获取 API 端点 URL"""
    # 如果配置了自定义 URL，优先使用
    if _config["base_url"]:
        return _config["base_url"]

    # 返回默认 URL
    defaults = {
        "anthropic": "https://api.anthropic.com/v1/messages",
        "openai": "https://api.openai.com/v1/chat/completions",
        "ollama": "http://localhost:11434/api/generate",
    }
    return defaults.get(provider, "")


def _call_anthropic(
    model: str,
    prompt: str,
    on_step: callable,
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    """调用 Anthropic API"""
    import requests

    api_key = _get_api_key("anthropic")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (use configure() or set ANTHROPIC_API_KEY env var)")

    url = _get_base_url("anthropic")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    response.raise_for_status()
    data = response.json()

    # 提取内容
    content = data.get("content", [])
    output = ""
    for c in content:
        if c.get("type") == "text":
            output += c.get("text", "")

    # 记录思考过程（如果有）
    if output:
        on_step("thought", output)

    return output


def _call_openai(model: str, prompt: str, on_step: callable, max_tokens: int = 4096) -> str:
    """调用 OpenAI API"""
    import requests

    api_key = _get_api_key("openai")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set (use configure() or set OPENAI_API_KEY env var)")

    url = _get_base_url("openai")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    response.raise_for_status()
    data = response.json()

    output = data["choices"][0]["message"]["content"]

    # OpenAI 不直接暴露思考过程，记录为 output
    on_step("output", output)

    return output


def _call_ollama(model: str, prompt: str, on_step: callable) -> str:
    """调用 Ollama (本地模型)"""
    import requests

    url = _get_base_url("ollama")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    data = response.json()

    output = data.get("response", "")
    on_step("output", output)

    return output
