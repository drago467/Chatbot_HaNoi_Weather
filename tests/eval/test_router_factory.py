"""Test make_router factory + RouterBackend predict logic.

Mock HTTP client for SLM backends — không cần Colab tunnel hay sv1 live.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from experiments.evaluation.config import EvalSettings, GatewayAlias, load_config
from experiments.evaluation.backends.router import (
    NoneRouter,
    RouterBackend,
    RouterPrediction,
    SlmFtRouter,
    SlmZeroShotRouter,
    make_router,
)


# ── NoneRouter — pure logic, no HTTP ──────────────────────────────────────


def test_none_router_returns_no_intent():
    router = NoneRouter()
    pred = router.predict("trời Hà Nội hôm nay thế nào?")
    assert pred.intent is None
    assert pred.confidence == 0.0
    assert pred.latency_ms == 0.0


def test_make_router_c2_returns_none():
    """C2/C5/C6 (router_backend='none') → NoneRouter."""
    cfg = load_config("c2")
    router = make_router(cfg)
    assert isinstance(router, NoneRouter)


def test_make_router_c5_returns_none():
    cfg = load_config("c5")
    router = make_router(cfg)
    assert isinstance(router, NoneRouter)


# ── make_router — SLM backends with mock settings ─────────────────────────


@pytest.fixture
def mock_settings():
    s = EvalSettings(
        QWEN_TUNNEL_API_BASE="https://tunnel.test/v1",
        QWEN_TUNNEL_API_KEY="dummy",
        QWEN_API_BASE="https://qwen.test/v1",
        QWEN_API_KEY="sk-qwen-test",
        OPENAI_COMPAT_API_BASE="https://compat.test/v1",
        OPENAI_COMPAT_API_KEY="sk-compat-test",
    )
    return s


def test_make_router_c1_returns_slm_ft(mock_settings):
    """C1: slm_ft via qwen-tunnel."""
    cfg = load_config("c1")
    with make_router(cfg, settings=mock_settings) as router:
        assert isinstance(router, SlmFtRouter)
        assert router.base_url == "https://tunnel.test/v1"
        assert router.model_name == "qwen3-4b-finetune"


def test_make_router_c3_returns_slm_zero_shot(mock_settings):
    """C3: slm_zero_shot via qwen-api."""
    cfg = load_config("c3")
    with make_router(cfg, settings=mock_settings) as router:
        assert isinstance(router, SlmZeroShotRouter)
        assert router.base_url == "https://qwen.test/v1"
        assert router.model_name == "qwen3-4b"


def test_make_router_c4_returns_slm_ft(mock_settings):
    """C4: slm_ft via qwen-tunnel (giống C1, khác thinking)."""
    cfg = load_config("c4")
    with make_router(cfg, settings=mock_settings) as router:
        assert isinstance(router, SlmFtRouter)


# ── SLM router HTTP — mock httpx ──────────────────────────────────────────


def _mock_response(content_str: str, status_code: int = 200) -> MagicMock:
    """Build mock httpx.Response trả về JSON."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = {
        "choices": [{"message": {"content": content_str}}]
    }
    resp.raise_for_status.return_value = None
    return resp


def test_slm_router_predict_parses_valid_json(mock_settings):
    cfg = load_config("c1")
    router = make_router(cfg, settings=mock_settings)
    valid_json = json.dumps({
        "intent": "current_weather",
        "scope": "city",
        "confidence": 0.92,
    })
    with patch.object(router._client, "post", return_value=_mock_response(valid_json)):
        pred = router.predict("trời Hà Nội thế nào?")

    assert pred.intent == "current_weather"
    assert pred.scope == "city"
    assert pred.confidence == 0.92
    assert pred.fallback_reason is None
    assert pred.latency_ms >= 0
    router.close()


def test_slm_router_handles_markdown_fences(mock_settings):
    """Model đôi lúc wrap JSON trong ```json ... ``` — phải strip."""
    cfg = load_config("c1")
    router = make_router(cfg, settings=mock_settings)
    fenced = '```json\n{"intent": "rain_query", "scope": "ward", "confidence": 0.7}\n```'
    with patch.object(router._client, "post", return_value=_mock_response(fenced)):
        pred = router.predict("phường Đông Ngạc có mưa không?")

    assert pred.intent == "rain_query"
    assert pred.scope == "ward"
    router.close()


def test_slm_router_invalid_intent_falls_back(mock_settings):
    """Invalid intent → fallback_reason='parse_error', intent=None."""
    cfg = load_config("c1")
    router = make_router(cfg, settings=mock_settings)
    invalid = json.dumps({"intent": "not_a_real_intent", "scope": "city", "confidence": 0.5})
    with patch.object(router._client, "post", return_value=_mock_response(invalid)):
        pred = router.predict("xyz")

    assert pred.intent is None
    assert pred.fallback_reason is not None
    assert "parse_error" in pred.fallback_reason
    router.close()


def test_slm_router_http_error_falls_back(mock_settings):
    """HTTPError → fallback_reason='http_error', intent=None."""
    cfg = load_config("c1")
    router = make_router(cfg, settings=mock_settings)
    with patch.object(
        router._client, "post",
        side_effect=httpx.ConnectError("Cannot reach tunnel")
    ):
        pred = router.predict("xyz")

    assert pred.intent is None
    assert pred.fallback_reason is not None
    assert "http_error" in pred.fallback_reason
    router.close()


def test_slm_router_malformed_json_falls_back(mock_settings):
    cfg = load_config("c1")
    router = make_router(cfg, settings=mock_settings)
    with patch.object(router._client, "post", return_value=_mock_response("not json {{")):
        pred = router.predict("xyz")

    assert pred.intent is None
    assert pred.fallback_reason is not None
    router.close()


# ── Validation: settings missing → make_router raises ─────────────────────


def test_make_router_c1_missing_tunnel_raises():
    """QWEN_TUNNEL_API_BASE empty → C1 fails (Colab not up)."""
    s = EvalSettings(
        QWEN_TUNNEL_API_BASE="",
        QWEN_TUNNEL_API_KEY="dummy",
        QWEN_API_BASE="https://qwen.test/v1",
        QWEN_API_KEY="sk-qwen-test",
        OPENAI_COMPAT_API_BASE="https://compat.test/v1",
        OPENAI_COMPAT_API_KEY="sk-compat-test",
    )
    cfg = load_config("c1")
    with pytest.raises(ValueError, match="QWEN_TUNNEL_API_BASE not set"):
        make_router(cfg, settings=s)


# ── Test all 6 config: factory không crash ────────────────────────────────


@pytest.mark.parametrize("name", ["c1", "c2", "c3", "c4", "c5", "c6"])
def test_make_router_all_6_configs_work(mock_settings, name):
    """Factory phải tạo router cho cả 6 config mà không crash."""
    cfg = load_config(name)
    router = make_router(cfg, settings=mock_settings)
    assert isinstance(router, RouterBackend)
    router.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
