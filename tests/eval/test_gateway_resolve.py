"""Test EvalSettings gateway resolver — đọc env var đúng cho 3 alias.

Mock env để không phụ thuộc giá trị `.env` thực (test stable + isolated).
"""

from __future__ import annotations

import pytest

from experiments.evaluation.config import EvalSettings, GatewayAlias


@pytest.fixture
def all_gateways_set(monkeypatch):
    """Set tất cả 6 var → resolver có data đầy đủ."""
    monkeypatch.setenv("QWEN_TUNNEL_API_BASE", "https://tunnel.test/v1")
    monkeypatch.setenv("QWEN_TUNNEL_API_KEY", "tunnel-dummy")
    monkeypatch.setenv("QWEN_API_BASE", "https://qwen.test/v1")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-test")
    monkeypatch.setenv("OPENAI_COMPAT_API_BASE", "https://compat.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-compat-test")


def test_resolve_qwen_tunnel(all_gateways_set):
    """qwen-tunnel resolves to QWEN_TUNNEL_API_BASE/KEY."""
    s = EvalSettings()
    resolved = s.resolve(GatewayAlias.qwen_tunnel)
    assert resolved.alias == GatewayAlias.qwen_tunnel
    assert resolved.base_url == "https://tunnel.test/v1"
    assert resolved.api_key == "tunnel-dummy"


def test_resolve_qwen_api(all_gateways_set):
    """qwen-api resolves to QWEN_API_BASE/KEY."""
    s = EvalSettings()
    resolved = s.resolve(GatewayAlias.qwen_api)
    assert resolved.alias == GatewayAlias.qwen_api
    assert resolved.base_url == "https://qwen.test/v1"
    assert resolved.api_key == "sk-qwen-test"


def test_resolve_openai_compat(all_gateways_set):
    """openai-compat resolves to OPENAI_COMPAT_API_BASE/KEY."""
    s = EvalSettings()
    resolved = s.resolve(GatewayAlias.openai_compat)
    assert resolved.alias == GatewayAlias.openai_compat
    assert resolved.base_url == "https://compat.test/v1"
    assert resolved.api_key == "sk-compat-test"


def test_resolve_qwen_tunnel_unset_raises(monkeypatch):
    """QWEN_TUNNEL_API_BASE empty → ValueError (Colab not up yet)."""
    monkeypatch.setenv("QWEN_TUNNEL_API_BASE", "")
    monkeypatch.setenv("QWEN_API_BASE", "https://qwen.test/v1")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-test")
    monkeypatch.setenv("OPENAI_COMPAT_API_BASE", "https://compat.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-compat-test")
    s = EvalSettings()
    with pytest.raises(ValueError, match="QWEN_TUNNEL_API_BASE not set"):
        s.resolve(GatewayAlias.qwen_tunnel)


def test_resolve_qwen_api_unset_raises(monkeypatch):
    """QWEN_API_BASE empty → ValueError."""
    monkeypatch.setenv("QWEN_API_BASE", "")
    monkeypatch.setenv("QWEN_API_KEY", "")
    monkeypatch.setenv("QWEN_TUNNEL_API_BASE", "https://tunnel.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_BASE", "https://compat.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-compat-test")
    s = EvalSettings()
    with pytest.raises(ValueError, match="QWEN_API_BASE / QWEN_API_KEY"):
        s.resolve(GatewayAlias.qwen_api)


def test_resolve_openai_compat_unset_raises(monkeypatch):
    """OPENAI_COMPAT_API_BASE empty → ValueError."""
    monkeypatch.setenv("OPENAI_COMPAT_API_BASE", "")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "")
    monkeypatch.setenv("QWEN_TUNNEL_API_BASE", "https://tunnel.test/v1")
    monkeypatch.setenv("QWEN_API_BASE", "https://qwen.test/v1")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-test")
    s = EvalSettings()
    with pytest.raises(ValueError, match="OPENAI_COMPAT_API_BASE / OPENAI_COMPAT_API_KEY"):
        s.resolve(GatewayAlias.openai_compat)


def test_qwen_tunnel_key_default(monkeypatch):
    """QWEN_TUNNEL_API_KEY default = 'ollama' (tunnel không cần auth)."""
    monkeypatch.delenv("QWEN_TUNNEL_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_TUNNEL_API_BASE", "https://tunnel.test/v1")
    monkeypatch.setenv("QWEN_API_BASE", "https://qwen.test/v1")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-test")
    monkeypatch.setenv("OPENAI_COMPAT_API_BASE", "https://compat.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-compat-test")
    s = EvalSettings()
    resolved = s.resolve(GatewayAlias.qwen_tunnel)
    assert resolved.api_key == "ollama"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
