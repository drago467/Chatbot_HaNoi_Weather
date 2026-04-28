"""EvalConfig + GatewayAlias for Phase 2 ablation eval (6 config).

3-gateway architecture (decoupled từ `app/config/settings.py` để eval framework
không bị bind vào production runtime):

- `qwen-tunnel`: Colab Cloudflare tunnel hosting hanoi-weather-router (qwen3-4b finetune GGUF qua Ollama).
- `qwen-api`: Qwen production API (sv1) hosting qwen3-4b zero-shot + qwen3-14b.
- `openai-compat`: gpt-4o, gpt-4o-mini, gemini-2.5-flash + judge.

Mỗi alias đọc từ `(QWEN_TUNNEL|QWEN|OPENAI_COMPAT)_API_BASE/KEY` env vars.
EvalConfig load từ YAML ở `experiments/evaluation/configs/{c1..c6}.yaml`.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
_CONFIGS_DIR = Path(__file__).resolve().parent / "configs"


class GatewayAlias(str, Enum):
    qwen_tunnel = "qwen-tunnel"
    qwen_api = "qwen-api"
    openai_compat = "openai-compat"


class GatewayResolved(BaseModel):
    """Concrete (base_url, api_key) for a gateway alias after env lookup."""

    alias: GatewayAlias
    base_url: str
    api_key: str


class EvalSettings(BaseSettings):
    """Env-driven gateway endpoints.

    Decoupled từ `app/config/settings.py` — eval framework đọc 6 var riêng
    (`QWEN_TUNNEL_*`, `QWEN_API_*`, `OPENAI_COMPAT_*`). Production `AGENT_*` /
    `JUDGE_*` không bị ảnh hưởng.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    qwen_tunnel_api_base: Optional[str] = Field(default=None, alias="QWEN_TUNNEL_API_BASE")
    qwen_tunnel_api_key: str = Field(default="ollama", alias="QWEN_TUNNEL_API_KEY")

    qwen_api_base: Optional[str] = Field(default=None, alias="QWEN_API_BASE")
    qwen_api_key: Optional[str] = Field(default=None, alias="QWEN_API_KEY")

    openai_compat_api_base: Optional[str] = Field(default=None, alias="OPENAI_COMPAT_API_BASE")
    openai_compat_api_key: Optional[str] = Field(default=None, alias="OPENAI_COMPAT_API_KEY")

    def resolve(self, alias: GatewayAlias) -> GatewayResolved:
        if alias == GatewayAlias.qwen_tunnel:
            if not self.qwen_tunnel_api_base:
                raise ValueError(
                    "QWEN_TUNNEL_API_BASE not set in .env — Colab tunnel must be up "
                    "to use 'qwen-tunnel' gateway (cần cho C1/C4 router)"
                )
            return GatewayResolved(
                alias=alias,
                base_url=self.qwen_tunnel_api_base,
                api_key=self.qwen_tunnel_api_key,
            )
        if alias == GatewayAlias.qwen_api:
            if not self.qwen_api_base or not self.qwen_api_key:
                raise ValueError("QWEN_API_BASE / QWEN_API_KEY not set in .env")
            return GatewayResolved(
                alias=alias,
                base_url=self.qwen_api_base,
                api_key=self.qwen_api_key,
            )
        if alias == GatewayAlias.openai_compat:
            if not self.openai_compat_api_base or not self.openai_compat_api_key:
                raise ValueError(
                    "OPENAI_COMPAT_API_BASE / OPENAI_COMPAT_API_KEY not set in .env"
                )
            return GatewayResolved(
                alias=alias,
                base_url=self.openai_compat_api_base,
                api_key=self.openai_compat_api_key,
            )
        raise ValueError(f"Unknown gateway alias: {alias}")


@lru_cache(maxsize=1)
def get_eval_settings() -> EvalSettings:
    """Lazy singleton — instantiate on first call."""
    return EvalSettings()


class EvalConfig(BaseModel):
    """One ablation eval config (C1..C6).

    Loaded từ YAML — pydantic validates schema + cross-field consistency.
    """

    name: str = Field(description="Config name, e.g., 'C1'")

    router_backend: Literal["slm_ft", "slm_zero_shot", "none"]
    router_gateway: Optional[GatewayAlias] = None
    router_model_name: Optional[str] = None

    agent_gateway: GatewayAlias
    agent_model_name: str
    agent_thinking: bool = True

    tool_path: Literal["router_prefilter", "full_27"]

    @field_validator("router_gateway")
    @classmethod
    def _check_router_gateway_consistency(cls, v, info):
        backend = info.data.get("router_backend")
        if backend == "none" and v is not None:
            raise ValueError(
                f"router_backend='none' must have router_gateway=None, got {v}"
            )
        if backend in ("slm_ft", "slm_zero_shot") and v is None:
            raise ValueError(f"router_backend={backend!r} requires router_gateway")
        return v

    @field_validator("router_model_name")
    @classmethod
    def _check_router_model_consistency(cls, v, info):
        backend = info.data.get("router_backend")
        if backend == "none" and v is not None:
            raise ValueError(
                f"router_backend='none' must have router_model_name=None, got {v!r}"
            )
        if backend in ("slm_ft", "slm_zero_shot") and not v:
            raise ValueError(f"router_backend={backend!r} requires router_model_name")
        return v

    @field_validator("tool_path")
    @classmethod
    def _check_tool_path_consistency(cls, v, info):
        backend = info.data.get("router_backend")
        if backend == "none" and v == "router_prefilter":
            raise ValueError(
                "router_backend='none' không thể dùng tool_path='router_prefilter' "
                "(không có router để prefilter) — set tool_path='full_27'"
            )
        return v


def load_config(name: str, configs_dir: Optional[Path] = None) -> EvalConfig:
    """Load EvalConfig by name (case-insensitive, e.g., 'c1' or 'C1')."""
    cfg_dir = configs_dir or _CONFIGS_DIR
    cfg_file = cfg_dir / f"{name.lower()}.yaml"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Eval config not found: {cfg_file}")
    with cfg_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return EvalConfig(**data)


class JudgeConfig(BaseModel):
    """LLM-as-Judge configuration (PR-C.5)."""

    judge_gateway: GatewayAlias = GatewayAlias.openai_compat
    judge_model_name: str = "gpt-4o"
    judge_temperature: float = 0.0
    max_tool_output_chars: Optional[int] = None
    chunked_threshold_chars: int = 80000
    rubric_prompt_path: Optional[str] = None


def load_judge_config(configs_dir: Optional[Path] = None) -> JudgeConfig:
    cfg_dir = configs_dir or _CONFIGS_DIR
    cfg_file = cfg_dir / "judge.yaml"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Judge config not found: {cfg_file}")
    with cfg_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return JudgeConfig(**data)
