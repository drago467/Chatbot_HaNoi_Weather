"""Test fuzzy threshold cho `_search_district_only` / `_search_ward_only`.

P10 (audit C1 batch2 ID 110): "Mỹ Đình" fuzzy match "Ba Đình" do pg_trgm
default threshold ~0.3 cho qua các pair share trigram. Raise lên 0.5 ngắt
được false positive nhưng vẫn giữ legit fuzzy (typo 1-2 ký tự).

Test KHÔNG cần DB — monkeypatch `query` / `query_one` từ `app.db.dal`.
"""

from __future__ import annotations

import pytest

from app.dal import location_dal


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def stub_query(monkeypatch):
    """Cho phép set fuzzy results returned bởi `query`."""
    state = {"results": [], "exact": None}

    def _query(sql, params):
        # Phân loại: SELECT ... similarity(...) là fuzzy; còn lại là exact
        return state["results"]

    def _query_one(sql, params):
        return state["exact"]

    monkeypatch.setattr(location_dal, "query", _query)
    monkeypatch.setattr(location_dal, "query_one", _query_one)
    return state


# ── Fix A: district fuzzy threshold ─────────────────────────────────────────


def test_my_dinh_low_score_match_does_not_resolve_to_ba_dinh(stub_query):
    """ID 110 regression: 'Mỹ Đình' (POI ngoài admin) KHÔNG được fuzzy match
    sang 'Ba Đình' khi pg_trgm trả single match score thấp (~0.4).
    """
    stub_query["exact"] = None  # exact path miss
    stub_query["results"] = [
        {
            "district_id": 1,
            "district_name_vi": "Ba Đình",
            "district_name_norm": "ba dinh",
            "score": 0.4,  # share suffix 'dinh' nhưng head token khác
        },
    ]
    out = location_dal._search_district_only("my dinh")
    assert out["status"] == "not_found", (
        f"'my dinh' KHÔNG nên fuzzy match 'ba dinh' với score 0.4 — "
        f"got {out['status']!r}"
    )
    assert out.get("needs_clarification") is True


def test_district_fuzzy_score_above_threshold_still_matches(stub_query):
    """Regression: typo legit ('cau giay' với 1 ký tự sai) vẫn fuzzy đúng
    khi score >= threshold (0.5)."""
    stub_query["exact"] = None
    stub_query["results"] = [
        {
            "district_id": 5,
            "district_name_vi": "Cầu Giấy",
            "district_name_norm": "cau giay",
            "score": 0.7,
        },
    ]
    out = location_dal._search_district_only("cau giay")
    assert out["status"] == "fuzzy"
    assert out["data"]["district_name_vi"] == "Cầu Giấy"


def test_district_fuzzy_at_exactly_threshold_matches(stub_query):
    """Boundary: score == 0.5 (threshold) phải pass (>= threshold)."""
    stub_query["exact"] = None
    stub_query["results"] = [
        {
            "district_id": 9,
            "district_name_vi": "Hoài Đức",
            "district_name_norm": "hoai duc",
            "score": 0.5,
        },
    ]
    out = location_dal._search_district_only("hoai duk")  # 1 typo
    assert out["status"] == "fuzzy"


def test_district_fuzzy_just_below_threshold_rejected(stub_query):
    """Boundary: score 0.49 < 0.5 → reject."""
    stub_query["exact"] = None
    stub_query["results"] = [
        {
            "district_id": 1,
            "district_name_vi": "Ba Đình",
            "district_name_norm": "ba dinh",
            "score": 0.49,
        },
    ]
    out = location_dal._search_district_only("my dinh")
    assert out["status"] == "not_found"


def test_district_no_fuzzy_results_still_not_found(stub_query):
    """pg_trgm trả [] (không match nào) → not_found như cũ."""
    stub_query["exact"] = None
    stub_query["results"] = []
    out = location_dal._search_district_only("xyz_random_text")
    assert out["status"] == "not_found"
    assert out.get("needs_clarification") is True


# ── Fix A: ward fuzzy threshold (đồng bộ với district) ──────────────────────


def test_ward_fuzzy_below_threshold_filtered(stub_query):
    """Ward fuzzy cũng filter theo threshold đồng bộ."""
    stub_query["exact"] = None
    # Hai kết quả score thấp cùng 'dinh' suffix — sau filter đều rớt
    stub_query["results"] = [
        {
            "ward_id": "ID_A", "ward_name_vi": "Phường Ba Đình",
            "district_id": 1, "district_name_vi": "Ba Đình",
            "lat": 21.0, "lon": 105.8,
            "score": 0.42,
        },
    ]
    out = location_dal._search_ward_only("my dinh")
    assert out["status"] == "not_found"


def test_ward_fuzzy_above_threshold_matches(stub_query):
    """Ward fuzzy score cao vẫn match."""
    stub_query["exact"] = None
    stub_query["results"] = [
        {
            "ward_id": "ID_W1", "ward_name_vi": "Phường Dịch Vọng",
            "district_id": 5, "district_name_vi": "Cầu Giấy",
            "lat": 21.0, "lon": 105.8,
            "score": 0.85,
        },
    ]
    out = location_dal._search_ward_only("dich vong")
    assert out["status"] == "fuzzy"
    assert out["data"]["ward_name_vi"] == "Phường Dịch Vọng"


# ── Sanity: threshold constant exposed ──────────────────────────────────────


def test_fuzzy_threshold_constant_is_0_5():
    """P10 invariant: threshold 0.5. Nếu đổi → cập nhật assertion + comment."""
    assert location_dal.FUZZY_SCORE_THRESHOLD == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
