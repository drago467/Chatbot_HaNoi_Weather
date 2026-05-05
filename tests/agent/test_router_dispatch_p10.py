"""P10 (audit C1 batch2 IDs 110/115/120/130) — Fix B + C tests.

Fix B: SLMRouter default scope=None khi model không emit / fallback / invalid,
       KHÔNG silent default 'city' (root cause silent city swallow ở
       resolve_location_scoped line 32).
Fix C: dispatch_forecast propagate `needs_clarification` + `alternatives`
       đồng bộ với resolve_and_dispatch. build_error_output preserve flag
       khớp prompt SCOPE [1] rule.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agent.router.slm_router import RouterResult, SLMRouter


# ── Fix B: RouterResult constructor default ─────────────────────────────────


def test_router_result_constructor_default_scope_is_none():
    """P10 invariant: empty RouterResult().scope is None (was 'city')."""
    rr = RouterResult()
    assert rr.scope is None


def test_router_result_explicit_scope_preserved():
    rr = RouterResult(scope="ward")
    assert rr.scope == "ward"


def test_router_result_should_fallback_when_no_reason():
    rr = RouterResult(intent="current_weather", scope="city")
    assert rr.should_fallback is False


def test_router_result_should_fallback_when_reason_set():
    rr = RouterResult(fallback_reason="model_error")
    assert rr.should_fallback is True
    assert rr.scope is None  # constructor default


# ── Fix B: SLMRouter.classify scope handling ────────────────────────────────


def _make_router():
    """SLMRouter init không hit network (httpx.Client lazy)."""
    return SLMRouter(ollama_base_url="http://fake-base", model="fake-model")


def test_classify_no_scope_in_json_defaults_none():
    """Model emit JSON thiếu scope key → scope=None (was 'city')."""
    router = _make_router()
    fake = '{"intent": "current_weather", "confidence": 0.95}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("trời thế nào?")
    assert rr.fallback_reason is None, "Phải success path (intent valid + conf cao)"
    assert rr.scope is None, "Thiếu scope key → None, không phải 'city' default"


def test_classify_invalid_scope_normalized_to_none():
    """Model emit scope không hợp lệ → scope=None (was 'city')."""
    router = _make_router()
    fake = '{"intent": "current_weather", "scope": "country", "confidence": 0.9}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("trời thế nào?")
    assert rr.scope is None


def test_classify_explicit_city_kept():
    """Regression: scope='city' explicit → giữ nguyên 'city'."""
    router = _make_router()
    fake = '{"intent": "current_weather", "scope": "city", "confidence": 0.9}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("trời Hà Nội thế nào?")
    assert rr.scope == "city"
    assert rr.fallback_reason is None


def test_classify_explicit_ward_kept():
    router = _make_router()
    fake = '{"intent": "current_weather", "scope": "ward", "confidence": 0.95}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("phường Trung Hòa thế nào?")
    assert rr.scope == "ward"


def test_classify_explicit_district_kept():
    router = _make_router()
    fake = '{"intent": "current_weather", "scope": "district", "confidence": 0.9}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("Cầu Giấy thế nào?")
    assert rr.scope == "district"


def test_classify_model_error_returns_scope_none():
    """Network/model error → fallback path RouterResult() → scope=None."""
    router = _make_router()
    with patch.object(router, "_call_ollama", side_effect=RuntimeError("connection refused")):
        rr = router.classify("xyz")
    assert rr.should_fallback
    assert rr.scope is None  # was 'city' default before P10


def test_classify_json_parse_error_returns_scope_none():
    """Invalid JSON → fallback → scope=None."""
    router = _make_router()
    with patch.object(router, "_call_ollama", return_value="not valid json {{{"):
        rr = router.classify("xyz")
    assert rr.should_fallback
    assert rr.scope is None


def test_classify_invalid_intent_with_explicit_scope_preserves_scope():
    """Invalid intent + explicit scope → return fallback, scope từ parse được giữ.

    Edge case: nếu model emit intent lạ nhưng scope hợp lệ, scope vẫn được preserve
    để debugging. Chỉ default None khi parse path không có thông tin.
    """
    router = _make_router()
    fake = '{"intent": "not_a_real_intent", "scope": "ward", "confidence": 0.5}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("xyz")
    assert rr.should_fallback
    assert rr.scope == "ward"  # explicit scope preserved


def test_classify_low_confidence_preserves_explicit_scope():
    """Low confidence path: scope vẫn từ model output, không bị reset.

    (Production agent.py:747 sẽ should_fallback → early return → ContextVar
    không bị set, nên scope value không quan trọng — nhưng vẫn preserve cho
    telemetry/debug.)
    """
    router = _make_router()
    # confidence 0.1 chắc chắn dưới mọi per-intent threshold (~0.6+)
    fake = '{"intent": "current_weather", "scope": "ward", "confidence": 0.1}'
    with patch.object(router, "_call_ollama", return_value=fake):
        rr = router.classify("trời thế nào?")
    assert rr.should_fallback
    assert "low_confidence" in rr.fallback_reason
    assert rr.scope == "ward"  # preserved from parsed


# ── Fix C: dispatch_forecast propagate clarification ─────────────────────────


def test_dispatch_forecast_propagates_needs_clarification(monkeypatch):
    """Fix C: dispatch_forecast preserve needs_clarification + alternatives khi
    auto_resolve_location fail."""
    from app.agent import dispatch as dispatch_mod

    def stub_resolve(ward_id=None, location_hint=None, target_scope=None):
        return {
            "status": "not_found",
            "level": "not_found",
            "needs_clarification": True,
            "alternatives": ["Cầu Giấy", "Đống Đa"],
            "message": "Không tìm thấy 'Hồ Tây' trong database hành chính Hà Nội",
            "suggestion": "Vui lòng cho biết tên phường/xã hoặc quận/huyện cụ thể",
        }

    # Patch theo path dispatch_forecast import (lazy import inside function)
    from app.agent import utils as utils_mod
    monkeypatch.setattr(utils_mod, "auto_resolve_location", stub_resolve)

    out = dispatch_mod.dispatch_forecast(
        location_hint="Hồ Tây",
        ward_fn=lambda **k: [],
        district_fn=lambda **k: [],
        city_fn=lambda **k: [],
    )

    assert out["error"] == "not_found"
    assert out["needs_clarification"] is True
    assert out["alternatives"] == ["Cầu Giấy", "Đống Đa"]
    assert "Hồ Tây" in out["message"]
    assert "phường" in out["suggestion"].lower() or "quận" in out["suggestion"].lower()


def test_dispatch_forecast_no_clarification_when_resolve_ok(monkeypatch):
    """Sanity: resolve thành công → KHÔNG xuất needs_clarification ở error path."""
    from app.agent import dispatch as dispatch_mod
    from app.agent import utils as utils_mod

    def stub_resolve(ward_id=None, location_hint=None, target_scope=None):
        return {
            "status": "ok",
            "level": "city",
            "data": {"city_name": "Hà Nội"},
        }

    monkeypatch.setattr(utils_mod, "auto_resolve_location", stub_resolve)

    out = dispatch_mod.dispatch_forecast(
        location_hint="Hà Nội",
        ward_fn=lambda **k: [],
        district_fn=lambda **k: [],
        city_fn=lambda **k: [{"weather_main": "Clouds"}],
    )

    # Success → KHÔNG có error/needs_clarification
    assert out.get("error") is None
    assert "needs_clarification" not in out


# ── Fix C: build_error_output preserve clarification flag ────────────────────


def test_build_error_output_preserves_needs_clarification():
    """Khi raw có needs_clarification=True → flat VN output cũng có (English key,
    khớp prompt SCOPE [1] rule "tool sẽ trả `needs_clarification: true`...").
    """
    from app.agent.tools.output_builder import build_error_output

    raw = {
        "error": "not_found",
        "message": "Không tìm thấy 'Hồ Tây'",
        "suggestion": "Vui lòng cho biết phường/xã cụ thể",
        "needs_clarification": True,
    }
    out = build_error_output(raw)
    assert out["lỗi"] == "Không tìm thấy 'Hồ Tây'"
    assert out["gợi ý"].startswith("Vui lòng")
    assert out["needs_clarification"] is True


def test_build_error_output_omits_needs_clarification_if_false():
    """Raw không có flag → output không xuất key (giảm noise)."""
    from app.agent.tools.output_builder import build_error_output

    raw = {"error": "no_data", "message": "Không có dữ liệu"}
    out = build_error_output(raw)
    assert "needs_clarification" not in out


def test_build_error_output_omits_needs_clarification_if_explicit_false():
    """needs_clarification=False (truthy check) → KHÔNG emit."""
    from app.agent.tools.output_builder import build_error_output

    raw = {"error": "no_data", "message": "...", "needs_clarification": False}
    out = build_error_output(raw)
    assert "needs_clarification" not in out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
