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
            protocol="anthropic",
            model="claude-3-5-sonnet-20241022",
            api_key="sk-...",
        )

        # 方式 2: 使用 LLMConfig 对象
        config = LLMConfig(
            protocol="openai",
            model="gpt-4o",
            api_key=os.environ["OPENAI_API_KEY"],
        )
        result = call("你好", config=config)
    """
    # API 协议类型（决定请求格式）
    protocol: str = "anthropic"  # anthropic / openai / ollama

    # 模型标识（用户自定义名称，如 "qwen-max", "deepseek-v3"）
    model: Optional[str] = None

    # API 配置
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    system: Optional[str] = None

    def get_api_key(self) -> Optional[str]:
        """获取 API Key"""
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
        return defaults.get(self.protocol, "")

    def get_model(self) -> str:
        """获取模型名称（带默认值）"""
        if self.model:
            return self.model
        return "default-model"


# ============ Profiles 机制：预配置多个模型，代码中只使用名称 ============

@dataclass
class ModelProfile:
    """
    模型配置 Profile

    用于预先在 TOML 配置文件或环境变量中定义多个模型配置，
    代码中只使用配置名称，避免暴露敏感信息。

    用法:
        # TOML 配置文件 .noesis.toml
        # [profiles.fast]
        # protocol = "anthropic"
        # model = "qwen-max"
        # base_url = "https://dashscope.aliyuncs.com/api/v1/chat/completions"

        # 代码中使用
        result = call("你好", profile="fast")
    """
    name: str
    protocol: str = "anthropic"  # API 协议类型：anthropic / openai / ollama
    model: Optional[str] = None  # 模型名称（如 "qwen-max", "deepseek-v3"）
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    system: Optional[str] = None

    def to_config(self) -> LLMConfig:
        """转换为 LLMConfig"""
        return LLMConfig(
            protocol=self.protocol,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            max_tokens=self.max_tokens,
            system=self.system,
        )


def _load_env_config() -> dict:
    """从环境变量加载配置"""
    return {
        # 默认 Profile 名称
        "default_profile": os.environ.get("NOESIS_DEFAULT_PROFILE"),

        # 日志配置
        "log_dir": os.environ.get("NOESIS_LOG_DIR"),
        "trace_enabled": os.environ.get("NOESIS_TRACE_ENABLED", "false").lower() == "true",

        # Profiles 配置（从 TOML 文件加载）
        "profiles": _load_profiles_from_toml(),
    }


def _load_profiles_from_toml() -> dict[str, ModelProfile]:
    """从 TOML 配置文件加载 profiles"""
    import os

    # 查找配置文件：当前目录或用户主目录
    config_paths = [
        Path(".noesis.toml"),
        Path.home() / ".noesis.toml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            return _parse_toml_config(config_path)

    return {}


def _parse_toml_config(path: Path) -> dict[str, ModelProfile]:
    """解析 TOML 配置文件"""
    try:
        import tomllib
    except ImportError:
        # Python < 3.11
        try:
            import tomli as tomllib
        except ImportError:
            return {}

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    profiles = {}
    profiles_data = data.get("profiles", {})

    for name, config in profiles_data.items():
        # 替换环境变量 ${VAR_NAME}
        api_key = config.get("api_key")
        if api_key and isinstance(api_key, str) and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, "")

        base_url = config.get("base_url")
        if base_url and isinstance(base_url, str) and base_url.startswith("${") and base_url.endswith("}"):
            env_var = base_url[2:-1]
            base_url = os.environ.get(env_var, "")

        profiles[name] = ModelProfile(
            name=name,
            protocol=config.get("protocol", "anthropic"),
            model=config.get("model"),
            api_key=api_key,
            base_url=base_url or config.get("base_url"),
            max_tokens=config.get("max_tokens", 4096),
            system=config.get("system"),
        )

    return profiles


def _parse_profiles_env(profiles_str: Optional[str]) -> dict[str, ModelProfile]:
    """解析环境变量中的 profiles 配置（已废弃，保留用于兼容）"""
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
            protocol=config.get("protocol", "anthropic"),
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            max_tokens=config.get("max_tokens", 4096),
            system=config.get("system"),
        )
    return profiles


# 全局配置（环境变量 + 默认值）
_env_config = _load_env_config()
_config = {
    # 默认 Profile 名称
    "default_profile": _env_config["default_profile"],

    # 日志配置
    "log_dir": _env_config["log_dir"],
    "trace_enabled": _env_config["trace_enabled"],

    # Profiles
    "profiles": _env_config["profiles"],
}


def configure(
    default_profile: Optional[str] = None,
    log_dir: Optional[str] = None,
    trace_enabled: Optional[bool] = None,
    # Profile 注册
    profile: Optional[str] = None,
    profile_config: Optional[ModelProfile] = None,
):
    """配置全局参数"""
    global _config
    if default_profile is not None:
        _config["default_profile"] = default_profile
    if log_dir is not None:
        _config["log_dir"] = log_dir
    if trace_enabled is not None:
        _config["trace_enabled"] = trace_enabled

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
    protocol: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    log_to: Optional[str] = None,
    trace: bool = False,
    system: Optional[str] = None,
    max_tokens: int = 4096,
    profile: Optional[str] = None,  # 使用预配置的 Profile
) -> CallResult:
    """
    执行 LLM 调用（带完整思维链记录）

    Args:
        prompt: Prompt 内容
        config: LLM 配置对象（可选）
        protocol: API 协议类型（anthropic / openai / ollama）
        model: 模型名称
        api_key: API Key
        base_url: 自定义 API 端点
        log_to: 日志文件路径
        trace: 是否启用思维链追踪
        system: System prompt
        max_tokens: 最大输出 token 数
        profile: Profile 名称（使用预配置）

    Returns:
        CallResult: 调用结果

    Example:
        # 方式 1: 使用 Profile（推荐）
        result = call("你好", profile="fast")

        # 方式 2: 直接配置
        result = call(
            "你好",
            protocol="openai",
            model="gpt-4o",
            base_url="https://api.openai.com/v1/chat/completions",
        )
    """
    # 如果使用 Profile，转换为 LLMConfig
    if profile:
        profile_config = get_profile(profile)
        if profile_config:
            config = profile_config.to_config()

    # 构建调用配置（优先级：函数参数 > config > profile）
    call_config = LLMConfig(
        protocol=protocol or (config.protocol if config else None) or "anthropic",
        model=model or (config.model if config else None),
        api_key=api_key or (config.api_key if config else None),
        base_url=base_url or (config.base_url if config else None),
        max_tokens=max_tokens,
        system=system or (config.system if config else None),
    )

    start_time = time.time()
    protocol = call_config.protocol
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
        "protocol": protocol,
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
    if config.protocol == "anthropic":
        return _call_anthropic(config, prompt, on_step)
    elif config.protocol == "openai":
        return _call_openai(config, prompt, on_step)
    elif config.protocol == "ollama":
        return _call_ollama(config, prompt, on_step)
    else:
        raise ValueError(f"Unknown protocol: {config.protocol}")


def _call_anthropic(
    config: LLMConfig,
    prompt: str,
    on_step: callable,
) -> str:
    """调用 Anthropic API 格式"""
    import requests

    api_key = config.get_api_key()
    if not api_key:
        raise RuntimeError("API key not set")

    url = config.get_base_url()
    # 如果 URL 没有 /v1/messages 后缀，自动添加
    if not url.endswith("/v1/messages"):
        url = url.rstrip("/") + "/v1/messages"

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

    # 记录思考过程
    if output:
        on_step("thought", output)

    return output


def _call_openai(config: LLMConfig, prompt: str, on_step: callable) -> str:
    """调用 OpenAI API 格式"""
    import requests

    api_key = config.get_api_key()
    if not api_key:
        raise RuntimeError("API key not set")

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

    # 记录输出
    on_step("output", output)

    return output


def _call_ollama(config: LLMConfig, prompt: str, on_step: callable) -> str:
    """调用 Ollama"""
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
