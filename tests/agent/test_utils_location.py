"""Test POI matching + auto_resolve_location.

Mục tiêu: pin behavior của 3 nhánh POI matching (direct → case-insensitive →
substring) và `auto_resolve_location` trước khi PR1.3 gộp các nhánh thành
helper duy nhất. Pin cả thứ tự ưu tiên để refactor sau giữ nguyên semantics.

Test KHÔNG động DB: monkeypatch `app.dal.location_dal.resolve_location` /
`resolve_location_scoped` / `get_ward_by_id`, gán `_POI_MAPPING` trực tiếp.
"""

from __future__ import annotations

import pytest

from app.agent import utils as utils_mod


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_poi_map(monkeypatch):
    """Set deterministic POI map (bypass file load)."""
    poi = {
        "Hồ Tây": "Tây Hồ",
        "Sân bay Nội Bài": "Sóc Sơn",
        "Công viên Cầu Giấy": "Cầu Giấy",
        "Hoàn Kiếm": "Hoàn Kiếm",
    }
    monkeypatch.setattr(utils_mod, "_POI_MAPPING", poi)
    return poi


@pytest.fixture
def stub_district_resolver(monkeypatch):
    """Patch `resolve_location` để trả `district` exact result theo tên."""
    def _stub(name: str):
        return {
            "status": "exact",
            "level": "district",
            "data": {"district_name_vi": name, "district_id": f"D_{name}"},
        }

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location", _stub)
    return _stub


@pytest.fixture
def stub_resolver_fail(monkeypatch):
    """Patch `resolve_location` để luôn trả ambiguous (không match)."""
    def _stub(name: str):
        return {"status": "ambiguous", "level": "district", "data": {}}

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location", _stub)
    return _stub


# ── _resolve_poi: 3 nhánh ưu tiên ───────────────────────────────────────────


def test_resolve_poi_returns_none_when_map_empty(monkeypatch):
    monkeypatch.setattr(utils_mod, "_POI_MAPPING", {})
    assert utils_mod._resolve_poi("Hồ Tây") is None


def test_resolve_poi_direct_match(fake_poi_map, stub_district_resolver):
    out = utils_mod._resolve_poi("Hồ Tây")
    assert out is not None
    assert out["status"] == "ok"
    assert out["level"] == "district"
    assert out["district_name"] == "Tây Hồ"
    assert out["poi_matched"] == "Hồ Tây"


def test_resolve_poi_case_insensitive_match(fake_poi_map, stub_district_resolver):
    out = utils_mod._resolve_poi("hồ tây")
    assert out is not None
    # Phải trả poi_matched dạng canonical (case từ map gốc)
    assert out["poi_matched"] == "Hồ Tây"
    assert out["district_name"] == "Tây Hồ"


def test_resolve_poi_substring_match(fake_poi_map, stub_district_resolver):
    """Substring nhánh 3 — kích hoạt khi hint chứa POI hoặc ngược lại."""
    out = utils_mod._resolve_poi("đi sân bay nội bài bây giờ")
    assert out is not None
    assert out["poi_matched"] == "Sân bay Nội Bài"
    assert out["district_name"] == "Sóc Sơn"


def test_resolve_poi_priority_direct_beats_substring(
    fake_poi_map, stub_district_resolver
):
    """Hint là exact key 'Hoàn Kiếm' phải dùng direct match, không substring.

    Ngữ cảnh: 'Hoàn Kiếm' tồn tại như direct key. Substring path cũng có thể
    match (vì POI map có 'Hoàn Kiếm' → 'Hoàn Kiếm'), nhưng priority phải là
    direct trước.
    """
    out = utils_mod._resolve_poi("Hoàn Kiếm")
    assert out is not None
    assert out["poi_matched"] == "Hoàn Kiếm"


def test_resolve_poi_returns_none_when_resolver_fails(
    fake_poi_map, stub_resolver_fail
):
    """POI matched nhưng DAL resolver không trả exact/fuzzy → coi như fail."""
    assert utils_mod._resolve_poi("Hồ Tây") is None


def test_resolve_poi_no_match_returns_none(fake_poi_map, stub_district_resolver):
    """Hint không có trong POI map (any nhánh) → None."""
    assert utils_mod._resolve_poi("Một địa điểm xa lạ chưa từng tồn tại") is None


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


# ── auto_resolve_location: target_scope behavior ────────────────────────────


def test_target_scope_ward_skips_poi(fake_poi_map, monkeypatch):
    """Q3 case: 'phường Cầu Giấy' bị POI 'Công viên Cầu Giấy' override.

    Khi router set scope=ward, POI matching phải skip để ưu tiên DB ward search.
    """
    called = {"poi": False, "scoped": False}

    def fail_poi(_):
        called["poi"] = True
        return {"status": "ok", "level": "district", "data": {}}

    def stub_scoped(name, target_scope=None):
        called["scoped"] = True
        assert target_scope == "ward"
        return {
            "status": "exact", "level": "ward",
            "data": {"ward_id": "ID_00169", "ward_name_vi": "Cầu Giấy"},
        }

    monkeypatch.setattr(utils_mod, "_resolve_poi", fail_poi)
    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(
        location_hint="Cầu Giấy", target_scope="ward"
    )
    assert called["poi"] is False, "POI phải bị skip khi scope=ward"
    assert called["scoped"] is True
    assert out["level"] == "ward"


def test_target_scope_city_upgrades_poi_match(fake_poi_map, stub_district_resolver):
    """POI match district nhưng scope=city → upgrade thành city level."""
    out = utils_mod.auto_resolve_location(
        location_hint="Hồ Tây", target_scope="city"
    )
    assert out["status"] == "ok"
    assert out["level"] == "city"
    assert out["data"] == {"city_name": "Hà Nội"}


def test_no_scope_returns_district_from_poi(fake_poi_map, stub_district_resolver):
    out = utils_mod.auto_resolve_location(location_hint="Hồ Tây")
    assert out["level"] == "district"
    assert out["district_name"] == "Tây Hồ"


# ── auto_resolve_location: scoped resolver branches ─────────────────────────


def test_scoped_exact_ward(monkeypatch, fake_poi_map):
    """POI miss → fall through to scoped resolver → exact ward result."""
    monkeypatch.setattr(utils_mod, "_resolve_poi", lambda _: None)

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


def test_scoped_ambiguous_returns_clarification(monkeypatch, fake_poi_map):
    monkeypatch.setattr(utils_mod, "_resolve_poi", lambda _: None)

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


def test_scoped_not_found(monkeypatch, fake_poi_map):
    """`not_found` đi qua nhánh chung với `ambiguous` (utils.py:149-158).

    `needs_clarification` mặc định là False (lấy từ `result.get(..., False)`)
    nếu stub không set. Nhánh `elif result["status"] == "not_found"` riêng
    (utils.py:167-174) hardcode True nhưng KHÔNG REACHABLE vì line 149 đã
    match cả `not_found` rồi — đây là dead code, không fix trong PR refactor
    này (cần xác nhận với user vì đụng = behavior change).
    """
    monkeypatch.setattr(utils_mod, "_resolve_poi", lambda _: None)

    def stub_scoped(name, target_scope=None):
        return {"status": "not_found", "level": "not_found", "message": "Không có"}

    import app.dal.location_dal as dal
    monkeypatch.setattr(dal, "resolve_location_scoped", stub_scoped)

    out = utils_mod.auto_resolve_location(location_hint="Một nơi không có")
    assert out["status"] == "not_found"
    assert out["level"] == "not_found"
    assert out["needs_clarification"] is False  # Pin: default từ result.get


def test_scoped_multiple_returns_candidates(monkeypatch, fake_poi_map):
    monkeypatch.setattr(utils_mod, "_resolve_poi", lambda _: None)

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
