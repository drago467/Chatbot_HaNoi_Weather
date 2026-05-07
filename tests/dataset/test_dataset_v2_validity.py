"""Validity tests for Dataset v2 (Phase 2 ablation eval).

Pin schema constraints để mỗi batch sinh dataset không drift khỏi:
- 15 canonical intents
- 3 valid scopes (city/district/ward) + legacy 'poi'
- 3 difficulties (easy/medium/hard)
- Location names (district/ward) tồn tại trong dim_ward.csv
- expected_tools, expected_abstain, expected_clarification, source columns hợp lệ

Test SKIP khi dataset chưa tồn tại (PR-B.2 trở đi sẽ sinh data thực).
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = ROOT / "data" / "evaluation"
COVERAGE_TRACKER = EVAL_DIR / "coverage_tracker.csv"
DATASET_FULL = EVAL_DIR / "eval_dataset_500.csv"
DIM_WARD = ROOT / "data" / "processed" / "dim_ward.csv"

VALID_INTENTS = {
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
}
VALID_SCOPES = {"city", "district", "ward"}
LEGACY_SCOPES = VALID_SCOPES | {"poi"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SOURCES = {"v1_legacy", "v2_new"}


def _normalize_vi(s: str) -> str:
    """Lowercase + strip diacritics + collapse whitespace."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _load_dim_ward():
    if not DIM_WARD.exists():
        return set(), set()
    rows = list(csv.DictReader(DIM_WARD.open(encoding="utf-8")))
    wards = {_normalize_vi(r["ward_name_vi"]) for r in rows}
    wards |= {_normalize_vi(r["ward_name_core_norm"]) for r in rows if r.get("ward_name_core_norm")}
    districts = {_normalize_vi(r["district_name_vi"]) for r in rows}
    return wards, districts


# ── Coverage tracker tests (always available) ────────────────────────────


def test_coverage_tracker_exists():
    assert COVERAGE_TRACKER.exists(), f"Missing: {COVERAGE_TRACKER}"


def test_coverage_tracker_has_135_cells():
    rows = list(csv.DictReader(COVERAGE_TRACKER.open(encoding="utf-8")))
    assert len(rows) == 135, f"Expected 135 cells (15×3×3), got {len(rows)}"


def test_coverage_tracker_intents_valid():
    rows = list(csv.DictReader(COVERAGE_TRACKER.open(encoding="utf-8")))
    for r in rows:
        assert r["intent"] in VALID_INTENTS, f"Invalid intent: {r['intent']}"


def test_coverage_tracker_scopes_valid():
    rows = list(csv.DictReader(COVERAGE_TRACKER.open(encoding="utf-8")))
    for r in rows:
        assert r["scope"] in VALID_SCOPES, f"Invalid scope: {r['scope']}"


def test_coverage_tracker_difficulties_valid():
    rows = list(csv.DictReader(COVERAGE_TRACKER.open(encoding="utf-8")))
    for r in rows:
        assert r["difficulty"] in VALID_DIFFICULTIES, f"Invalid difficulty: {r['difficulty']}"


# ── Dataset CSV tests (skip until PR-B.2+ produces data) ─────────────────


def _load_dataset():
    if not DATASET_FULL.exists():
        pytest.skip(f"Dataset not yet produced: {DATASET_FULL}")
    return list(csv.DictReader(DATASET_FULL.open(encoding="utf-8")))


def test_dataset_total_500():
    rows = _load_dataset()
    assert len(rows) == 500, f"Expected 500 rows, got {len(rows)}"


def test_dataset_intents_valid():
    rows = _load_dataset()
    for r in rows:
        assert r["intent"] in VALID_INTENTS, f"id={r['id']}: invalid intent {r['intent']}"


def test_dataset_scopes_valid():
    rows = _load_dataset()
    for r in rows:
        # Legacy 'poi' allowed only for v1_legacy
        if r["location_scope"] == "poi":
            assert r["source"] == "v1_legacy", f"id={r['id']}: poi only for legacy"
        else:
            assert r["location_scope"] in VALID_SCOPES, f"id={r['id']}: invalid scope"


def test_dataset_difficulties_valid():
    rows = _load_dataset()
    for r in rows:
        assert r["difficulty"] in VALID_DIFFICULTIES, f"id={r['id']}: invalid difficulty"


def test_dataset_sources_valid():
    rows = _load_dataset()
    for r in rows:
        assert r["source"] in VALID_SOURCES, f"id={r['id']}: invalid source"


def test_dataset_v1_legacy_count_199():
    rows = _load_dataset()
    legacy = [r for r in rows if r["source"] == "v1_legacy"]
    assert len(legacy) == 199, f"Expected 199 legacy rows, got {len(legacy)}"


def test_dataset_poi_15_with_clarification():
    rows = _load_dataset()
    poi = [r for r in rows if r["location_scope"] == "poi"]
    assert len(poi) == 15, f"Expected 15 POI rows (legacy), got {len(poi)}"
    for r in poi:
        assert r["expected_clarification"] == "True", (
            f"id={r['id']}: POI must have expected_clarification=True"
        )


def test_dataset_expected_tools_parseable():
    rows = _load_dataset()
    for r in rows:
        try:
            tools = json.loads(r["expected_tools"]) if r["expected_tools"] else []
        except json.JSONDecodeError:
            pytest.fail(f"id={r['id']}: expected_tools not valid JSON: {r['expected_tools']!r}")
        assert isinstance(tools, list), f"id={r['id']}: expected_tools not list"


def test_dataset_locations_in_dim_ward():
    """Location_name (district/ward scope) phải khớp với dim_ward.csv.

    Skip clarification rows (expected_clarification=True) vì location ở các
    trường hợp này là ambiguous/unresolved (vd 'khu trung tâm', typo) — chatbot
    phải clarify thay vì assume.
    """
    rows = _load_dataset()
    wards, districts = _load_dim_ward()
    if not wards:
        pytest.skip("dim_ward.csv not available")
    for r in rows:
        if r["location_scope"] == "city" or not r["location_name"]:
            continue
        if r["location_scope"] == "poi":
            continue  # legacy POI free-form
        if r.get("expected_clarification") == "True":
            continue  # ambiguous location intentionally unresolved
        loc_norm = _normalize_vi(r["location_name"])
        if r["location_scope"] == "district":
            # Allow "Cầu Giấy" or "Quận Cầu Giấy" — match against district names
            matched = any(loc_norm in d or d in loc_norm for d in districts)
            assert matched, f"id={r['id']}: district '{r['location_name']}' not in dim_ward"
        elif r["location_scope"] == "ward":
            matched = any(loc_norm in w or w in loc_norm for w in wards)
            assert matched, f"id={r['id']}: ward '{r['location_name']}' not in dim_ward"


def test_dataset_no_duplicate_questions():
    """Levenshtein-style: same normalized question = duplicate."""
    rows = _load_dataset()
    seen = {}
    for r in rows:
        norm = _normalize_vi(r["question"])
        if norm in seen:
            pytest.fail(f"Duplicate question: id={r['id']} matches id={seen[norm]}: {r['question']!r}")
        seen[norm] = r["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
