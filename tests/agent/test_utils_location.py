"""Test auto_resolve_location (P8: POI hard-removed, admin-only).

Sau P8 (2026-05-03): POI mapping + helpers (`_resolve_poi`, `_get_poi_mapping`,
`_iter_poi_candidates`, `_POI_MAPPING`) đã xóa khỏi `app/agent/utils.py`. Mọi
địa danh phi-admin (Hồ Gươm, Mỹ Đình, Văn Miếu…) phải đi thẳng vào
`resolve_location_scoped` và trả `needs_clarification=True` để bot hỏi lại.

Test KHÔNG động DB: monkeypatch `app.dal.location_dal.resolve_location_scoped`
/ `get_ward_by_id`.
"""

from __future__ import annotations

import pytest

from app.agent import utils as utils_mod


# ── auto_resolve_location: ward_id branch ───────────────────────────────────


def test_auto_resolve_with_valid_ward_id(monkeypatch):
    import app.dal.location_dal as dal
    monkeypatch.setattr(
        dal, "get_ward_by_id",
        lambda wid: {"ward_id": wid, "ward_name_vi": "Cầu Giấy"} if wid else None,
    )
    out = utils_mod.auto_resolve_location(ward_id="ID_00169")
    assert out["status"] == "ok"
    assert out["level"] == "ward"
    assert out["ward_id"] == "ID_00169"


def test_auto_resolve_invalid_ward_id_falls_through_to_error(monkeypatch):
    """ward_id không tồn tại + không có hint → trả status=error."""
    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "get_ward_by_id", lambda wid: None)
    out = utils_mod.auto_resolve_location(ward_id="ID_BAD")
    assert out["status"] == "error"
    assert out["level"] == "error"


def test_auto_resolve_no_input_returns_error():
    out = utils_mod.auto_resolve_location()
    assert out["status"] == "error"


# ── P8: POI hard-removed → clarification ────────────────────────────────────


def test_poi_input_returns_not_found_with_clarification(monkeypatch):
    """POI 'Hồ Gươm' không còn map → DAL fail → needs_clarification=True."""
    def stub_scoped(name, target_scope=None):
        return {
            "status": "not_found", "level": "not_found",
            "message": "Không tìm thấy 'Hồ Gươm' trong database",
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Hồ Gươm")
    assert out["status"] == "not_found"
    assert out["needs_clarification"] is True
    assert "phường" in out["suggestion"].lower() or "quận" in out["suggestion"].lower()


def test_landmark_input_returns_not_found(monkeypatch):
    """Landmark 'Sân bay Nội Bài' → not_found + clarification."""
    def stub_scoped(name, target_scope=None):
        return {"status": "not_found", "level": "not_found", "message": "miss"}

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Sân bay Nội Bài")
    assert out["status"] == "not_found"
    assert out["needs_clarification"] is True


def test_no_poi_module_symbols_exposed():
    """Regression guard: P8 hard-remove. Các symbol POI cũ KHÔNG được
    expose lại trong `app.agent.utils` (tránh ai đó re-import từ history)."""
    for sym in ("_POI_MAPPING", "_get_poi_mapping", "_iter_poi_candidates", "_resolve_poi"):
        assert not hasattr(utils_mod, sym), (
            f"{sym} đã hard-removed ở P8, không được tái xuất hiện"
        )


# ── auto_resolve_location: scoped resolver branches ─────────────────────────


def test_scoped_exact_ward(monkeypatch):
    def stub_scoped(name, target_scope=None):
        return {
            "status": "exact", "level": "ward",
            "data": {"ward_id": "ID_00200", "ward_name_vi": "Xuân Đỉnh"},
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Xuân Đỉnh")
    assert out["level"] == "ward"
    assert out["ward_id"] == "ID_00200"


def test_scoped_exact_district(monkeypatch):
    """Admin district name → exact district result."""
    def stub_scoped(name, target_scope=None):
        return {
            "status": "exact", "level": "district",
            "data": {"district_id": "D_TayHo", "district_name_vi": "Tây Hồ"},
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Tây Hồ")
    assert out["level"] == "district"
    assert out["district_name"] == "Tây Hồ"


def test_scoped_ambiguous_returns_clarification(monkeypatch):
    def stub_scoped(name, target_scope=None):
        return {
            "status": "ambiguous", "level": "ward",
            "message": "Tên trùng",
            "needs_clarification": True,
            "alternatives": ["A", "B"],
            "suggestion": "Vui lòng chọn",
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Tên trùng")
    assert out["status"] == "ambiguous"
    assert out["needs_clarification"] is True
    assert out["alternatives"] == ["A", "B"]


def test_scoped_not_found_always_needs_clarification(monkeypatch):
    """P8: status=not_found ALWAYS sets needs_clarification=True
    (kể cả khi DAL không set), để bot luôn hỏi lại user."""
    def stub_scoped(name, target_scope=None):
        return {"status": "not_found", "level": "not_found", "message": "Không có"}

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Một nơi không có")
    assert out["status"] == "not_found"
    assert out["level"] == "not_found"
    assert out["needs_clarification"] is True


def test_scoped_multiple_returns_candidates(monkeypatch):
    def stub_scoped(name, target_scope=None):
        return {
            "status": "multiple", "level": "ward",
            "data": [{"ward_id": "A"}, {"ward_id": "B"}],
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="X")
    assert out["status"] == "multiple"
    assert len(out["candidates"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
