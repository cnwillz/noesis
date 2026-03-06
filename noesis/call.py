"""
LLM 调用 - 核心接口

支持：
- Anthropic API (Claude)
- OpenAI API
- 兼容 OpenAI 格式的 API
- Ollama (本地模型)

配置优先级（针对每次调用）：
1. call() 函数参数（最高优先级）
2. configure() 全局配置 / profiles
3. 环境变量
4. 默认值
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .types import ThoughtStep, CallResult


@dataclass
class LLMConfig:
    """
    单次 LLM 调用配置

    用于支持每次调用使用不同的 provider、模型、API Key 等。

    用法:
        # 方式 1: 直接在 call() 中传参数
        result = call(
            prompt="你好",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="sk-...",
        )

        # 方式 2: 使用 LLMConfig 对象
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
        )
        result = call("你好", config=config)
    """
    provider: str = "anthropic"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    system: Optional[str] = None

    # Provider 特定的 API Key
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    def get_api_key(self) -> Optional[str]:
        """获取 API Key（优先级：provider 专用 > 通用 > None）"""
        if self.provider == "anthropic":
            return self.anthropic_api_key or self.api_key
        elif self.provider == "openai":
            return self.openai_api_key or self.api_key
        return self.api_key

    def get_base_url(self) -> str:
        """获取 API 端点 URL"""
        if self.base_url:
            return self.base_url

        defaults = {
            "anthropic": "https://api.anthropic.com/v1/messages",
            "openai": "https://api.openai.com/v1/chat/completions",
            "ollama": "http://localhost:11434/api/generate",
        }
        return defaults.get(self.provider, "")

    def get_model(self) -> str:
        """获取模型名称（带默认值）"""
        if self.model:
            return self.model

        defaults = {
            "anthropic": "claude-sonnet-4-5-20251001",
            "openai": "gpt-4o",
            "ollama": "llama3.1:8b",
        }
        return defaults.get(self.provider, "gpt-3.5-turbo")


# ============ Profiles 机制：预配置多个模型，代码中只使用名称 ============

@dataclass
class ModelProfile:
    """
    模型配置 Profile

    用于预先在环境变量或配置文件中定义多个模型配置，
    代码中只使用配置名称，避免暴露敏感信息。

    用法:
        # 环境变量定义 profiles
        export NOESIS_PROFILES='{"fast":{"model":"claude-3-haiku"}, "smart":{"model":"claude-3-opus"}}'

        # 代码中使用
        result = call("你好", profile="fast")
    """
    name: str
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    system: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    def to_config(self) -> LLMConfig:
        """转换为 LLMConfig"""
        return LLMConfig(
            provider=self.provider,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            max_tokens=self.max_tokens,
            system=self.system,
            anthropic_api_key=self.anthropic_api_key,
            openai_api_key=self.openai_api_key,
        )


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

        # Profiles 配置
        "profiles": _parse_profiles_env(os.environ.get("NOESIS_PROFILES")),
    }


def _parse_profiles_env(profiles_str: Optional[str]) -> dict[str, ModelProfile]:
    """解析环境变量中的 profiles 配置"""
    if not profiles_str:
        return {}

    try:
        import json as stdlib_json
        profiles_data = stdlib_json.loads(profiles_str)
    except (json.JSONDecodeError, ValueError):
        return {}

    profiles = {}
    for name, config in profiles_data.items():
        profiles[name] = ModelProfile(
            name=name,
            provider=config.get("provider"),
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            max_tokens=config.get("max_tokens", 4096),
            system=config.get("system"),
            anthropic_api_key=config.get("anthropic_api_key"),
            openai_api_key=config.get("openai_api_key"),
        )
    return profiles


# 全局配置（环境变量 + 默认值）
_env_config = _load_env_config()
_config = {
    "provider": _env_config["provider"] or "anthropic",
    "model": _env_config["model"],
    "api_key": _env_config["api_key"],
    "base_url": _env_config["base_url"],
    "log_dir": _env_config["log_dir"],
    "trace_enabled": _env_config["trace_enabled"],

    # Provider 特定的 API Key
    "anthropic_api_key": _env_config["anthropic_api_key"],
    "openai_api_key": _env_config["openai_api_key"],

    # Profiles
    "profiles": _env_config["profiles"],
}


def configure(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    log_dir: Optional[str] = None,
    trace_enabled: Optional[bool] = None,
    anthropic_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    # Profile 注册
    profile: Optional[str] = None,
    profile_config: Optional[ModelProfile] = None,
):
    """配置全局参数"""
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

    # 注册 Profile
    if profile and profile_config:
        _config["profiles"][profile] = profile_config


def register_profile(name: str, profile: ModelProfile):
    """
    注册一个模型配置 Profile

    用法:
        register_profile(
            "fast",
            ModelProfile(
                name="fast",
                provider="anthropic",
                model="claude-3-haiku-20240307",
            ),
        )

        register_profile(
            "smart",
            ModelProfile(
                name="smart",
                provider="anthropic",
                model="claude-3-opus-20240229",
            ),
        )

        # 使用时
        result = call("你好", profile="fast")
    """
    global _config
    _config["profiles"][name] = profile


def get_profile(name: str) -> Optional[ModelProfile]:
    """获取注册的 Profile 配置"""
    return _config["profiles"].get(name)


def list_profiles() -> list[str]:
    """列出所有可用的 Profile 名称"""
    return list(_config["profiles"].keys())


def call(
    prompt: str,
    config: Optional[LLMConfig] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    log_to: Optional[str] = None,
    trace: bool = False,
    system: Optional[str] = None,
    max_tokens: int = 4096,
    profile: Optional[str] = None,  # 新增：使用预配置的 Profile
) -> CallResult:
    """
    执行 LLM 调用（带完整思维链记录）

    Args:
        prompt: Prompt 内容
        config: LLM 配置对象（可选，使用 LLMConfig 可完整配置）
        model: 模型名称（可选，覆盖 config）
        provider: LLM 提供商（可选，覆盖 config）
        api_key: API Key（可选，覆盖 config）
        base_url: 自定义 API 端点（可选，覆盖 config）
        log_to: 日志文件路径（JSONL 格式）
        trace: 是否启用思维链追踪
        system: System prompt（仅 Anthropic）
        max_tokens: 最大输出 token 数
        profile: Profile 名称（可选，使用预配置的配置）

    Returns:
        CallResult: 调用结果，包含输出和思维链

    Example:
        # 方式 1: 使用全局配置（环境变量或 configure()）
        result = call("你好")

        # 方式 2: 使用 Profile（推荐，不暴露敏感信息）
        result = call("你好", profile="fast")  # 快速响应
        result = call("复杂任务", profile="smart")  # 高智能

        # 方式 3: 单次调用配置不同的 provider
        result = call(
            "你好",
            provider="openai",
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
        )

        # 方式 4: 使用 LLMConfig 对象
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="sk-ant-...",
        )
        result = call("你好", config=config)
    """
    # 如果使用 Profile，转换为 LLMConfig
    if profile:
        profile_config = get_profile(profile)
        if profile_config:
            config = profile_config.to_config()

    # 构建调用配置（优先级：函数参数 > config 参数 > 全局配置）
    call_config = LLMConfig(
        provider=provider or (config.provider if config else None) or _config["provider"],
        model=model or (config.model if config else None) or _config["model"],
        api_key=api_key or (config.api_key if config else None) or _config["api_key"],
        base_url=base_url or (config.base_url if config else None) or _config["base_url"],
        max_tokens=max_tokens,
        system=system or (config.system if config else None),
        anthropic_api_key=anthropic_api_key or (config.anthropic_api_key if config else None) or _config["anthropic_api_key"],
        openai_api_key=openai_api_key or (config.openai_api_key if config else None) or _config["openai_api_key"],
    )

    start_time = time.time()
    provider = call_config.provider
    model = call_config.get_model()

    # 确定日志输出位置（使用全局配置）
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

    # 调用 LLM（传入配置对象）
    output = _call_llm(call_config, prompt, _add_step)

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
    config: LLMConfig,
    prompt: str,
    on_step: callable,
) -> str:
    """调用 LLM"""
    if config.provider == "anthropic":
        return _call_anthropic(config, prompt, on_step)
    elif config.provider == "openai":
        return _call_openai(config, prompt, on_step)
    elif config.provider == "ollama":
        return _call_ollama(config, prompt, on_step)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def _call_anthropic(
    config: LLMConfig,
    prompt: str,
    on_step: callable,
) -> str:
    """调用 Anthropic API"""
    import requests

    api_key = config.get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (use configure(), LLMConfig, or set ANTHROPIC_API_KEY env var)")

    url = config.get_base_url()
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": config.get_model(),
        "max_tokens": config.max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if config.system:
        payload["system"] = config.system

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


def _call_openai(config: LLMConfig, prompt: str, on_step: callable) -> str:
    """调用 OpenAI API"""
    import requests

    api_key = config.get_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set (use configure(), LLMConfig, or set OPENAI_API_KEY env var)")

    url = config.get_base_url()
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": config.get_model(),
        "max_tokens": config.max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    response.raise_for_status()
    data = response.json()

    output = data["choices"][0]["message"]["content"]

    # OpenAI 不直接暴露思考过程，记录为 output
    on_step("output", output)

    return output


def _call_ollama(config: LLMConfig, prompt: str, on_step: callable) -> str:
    """调用 Ollama (本地模型)"""
    import requests

    url = config.get_base_url()
    payload = {
        "model": config.get_model(),
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    data = response.json()

    output = data.get("response", "")
    on_step("output", output)

    return output
