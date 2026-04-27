"""Centralized settings via Pydantic BaseSettings.

Single source of truth cho env vars trong `app/`. Default value GIỮ NGUYÊN
với behavior cũ trước PR1.1 — không đổi mặc định nào để tránh behavior change.

PR1.1 chỉ tạo settings + centralize `load_dotenv()`. Các site `os.getenv(...)`
hiện tại VẪN GIỮ NGUYÊN và chạy đúng vì `.env` được load ở `app/api/main.py`
trước mọi import. Migration `os.getenv → settings.<field>` để PR sau (khi cần
validate type / đổi default / thêm computed field).

Pattern env vars dynamic (ví dụ `OPENWEATHER_API_KEY_0..4`) KHÔNG migrate vào
đây — `app/core/key_manager.py` tự loop bằng `os.getenv` là phù hợp hơn.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """All env-driven configuration. Default value pin behavior trước PR1.1."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────────────────────────
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    postgres_user: Optional[str] = Field(default=None, alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, alias="POSTGRES_PASSWORD")
    postgres_host: Optional[str] = Field(default=None, alias="POSTGRES_HOST")
    postgres_port: Optional[str] = Field(default=None, alias="POSTGRES_PORT")
    postgres_db: Optional[str] = Field(default=None, alias="POSTGRES_DB")

    # ── Logging ─────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="logs", alias="LOG_DIR")

    # ── API / UI ────────────────────────────────────────────────────────
    api_cors_origins: str = Field(default="*", alias="API_CORS_ORIGINS")
    api_url: str = Field(default="http://localhost:8000", alias="API_URL")

    # ── Agent LLM (OpenAI-compatible endpoint) ──────────────────────────
    agent_api_base: Optional[str] = Field(default=None, alias="AGENT_API_BASE")
    agent_api_key: Optional[str] = Field(default=None, alias="AGENT_API_KEY")
    agent_model: str = Field(
        default="gpt-4o-mini-2024-07-18", alias="AGENT_MODEL",
    )

    # ── Conversation State ──────────────────────────────────────────────
    conversation_ttl_seconds: int = Field(
        default=1800, alias="CONVERSATION_TTL_SECONDS",
    )

    # ── SLM Router (Ollama) ─────────────────────────────────────────────
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="hanoi-weather-router", alias="OLLAMA_MODEL",
    )
    slm_confidence_threshold: float = Field(
        default=0.75, alias="SLM_CONFIDENCE_THRESHOLD",
    )
    use_slm_router: bool = Field(default=False, alias="USE_SLM_ROUTER")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins → list (giữ behavior `.split(',')` cũ)."""
        return self.api_cors_origins.split(",")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy singleton — instantiate on first call."""
    return Settings()
