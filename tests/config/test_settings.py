"""Test `app.config.settings.Settings`.

Pin:
- Default value khớp với behavior cũ (trước PR1.1) — bất kỳ field nào đổi
  default = behavior change, phải hỏi user trước.
- Field type + alias đúng → consumer dùng `settings.<field>` ổn định.
- `cors_origins_list` parse `.split(",")` (giữ behavior `app/api/main.py:40` cũ).
- Env override hoạt động (case-insensitive — pin behavior pydantic-settings).
"""

from __future__ import annotations

import pytest

from app.config.settings import Settings, get_settings


# ── Default values (pin behavior cũ) ────────────────────────────────────────


def _isolated(monkeypatch, **env):
    """Helper: clear all relevant env vars + set test env vars + new instance.

    Phải clear tất cả env vars trước khi tạo Settings để không lẫn với .env
    thật của project.
    """
    # Clear toàn bộ env vars Settings quan tâm
    for key in (
        "DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST",
        "POSTGRES_PORT", "POSTGRES_DB", "LOG_LEVEL", "LOG_DIR",
        "API_CORS_ORIGINS", "API_URL", "AGENT_API_BASE", "AGENT_API_KEY",
        "AGENT_MODEL", "CONVERSATION_TTL_SECONDS", "OLLAMA_BASE_URL",
        "OLLAMA_MODEL", "SLM_CONFIDENCE_THRESHOLD", "USE_SLM_ROUTER",
    ):
        monkeypatch.delenv(key, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Tạo instance không đọc từ .env file (chỉ env vars)
    return Settings(_env_file=None)


def test_default_log_level(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.log_level == "INFO"


def test_default_log_dir(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.log_dir == "logs"


def test_default_cors_origins_is_star(monkeypatch):
    """PIN: CORS default `*` — đổi sang `[]` cần hỏi user (behavior change)."""
    s = _isolated(monkeypatch)
    assert s.api_cors_origins == "*"
    assert s.cors_origins_list == ["*"]


def test_default_api_url(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.api_url == "http://localhost:8000"


def test_default_agent_model(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.agent_model == "gpt-4o-mini-2024-07-18"


def test_default_conversation_ttl_seconds(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.conversation_ttl_seconds == 1800


def test_default_ollama_base_url(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.ollama_base_url == "http://localhost:11434"


def test_default_ollama_model(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.ollama_model == "hanoi-weather-router"


def test_default_slm_confidence_threshold(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.slm_confidence_threshold == 0.75


def test_default_use_slm_router_false(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.use_slm_router is False


def test_optional_fields_none_when_unset(monkeypatch):
    s = _isolated(monkeypatch)
    assert s.database_url is None
    assert s.postgres_user is None
    assert s.agent_api_base is None
    assert s.agent_api_key is None


# ── Env override behavior ───────────────────────────────────────────────────


def test_env_override_string(monkeypatch):
    s = _isolated(monkeypatch, LOG_LEVEL="DEBUG")
    assert s.log_level == "DEBUG"


def test_env_override_int_coercion(monkeypatch):
    s = _isolated(monkeypatch, CONVERSATION_TTL_SECONDS="60")
    assert s.conversation_ttl_seconds == 60
    assert isinstance(s.conversation_ttl_seconds, int)


def test_env_override_float_coercion(monkeypatch):
    s = _isolated(monkeypatch, SLM_CONFIDENCE_THRESHOLD="0.9")
    assert s.slm_confidence_threshold == 0.9
    assert isinstance(s.slm_confidence_threshold, float)


def test_env_override_bool_true_variants(monkeypatch):
    """Pydantic v2 nhận `true`, `1`, `yes` (case-insensitive) → True."""
    for v in ("true", "True", "1", "yes"):
        s = _isolated(monkeypatch, USE_SLM_ROUTER=v)
        assert s.use_slm_router is True, f"Failed for value: {v}"


def test_env_override_bool_false_variants(monkeypatch):
    """Pydantic v2 nhận `false`, `False`, `0`, `no` → False.

    Khác với code cũ ở `app/agent/router/config.py:36` (dùng
    `.lower() in ("true","1","yes")` → empty string → False), Pydantic
    KHÔNG nhận empty string làm bool. Hiện không phải behavior change vì
    code cũ vẫn dùng `os.getenv` direct, chưa migrate sang Settings.
    """
    for v in ("false", "False", "0", "no"):
        s = _isolated(monkeypatch, USE_SLM_ROUTER=v)
        assert s.use_slm_router is False, f"Failed for value: {v}"


def test_env_case_insensitive(monkeypatch):
    """`case_sensitive=False` → lowercase env var cũng đọc được."""
    s = _isolated(monkeypatch, log_level="WARNING")
    assert s.log_level == "WARNING"


# ── cors_origins_list ───────────────────────────────────────────────────────


def test_cors_origins_list_split_comma(monkeypatch):
    """Multi-origin string → list (pin behavior `.split(',')` cũ)."""
    s = _isolated(monkeypatch, API_CORS_ORIGINS="https://a.com,https://b.com")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]


def test_cors_origins_list_single(monkeypatch):
    s = _isolated(monkeypatch, API_CORS_ORIGINS="https://only.com")
    assert s.cors_origins_list == ["https://only.com"]


# ── get_settings singleton ──────────────────────────────────────────────────


def test_get_settings_returns_singleton():
    """`get_settings()` cache với `lru_cache` → cùng instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_extra_env_vars_ignored(monkeypatch):
    """`extra='ignore'` → env var lạ không gây ValidationError."""
    s = _isolated(monkeypatch, RANDOM_UNKNOWN_VAR="abc")
    assert s.log_level == "INFO"  # vẫn load bình thường


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
