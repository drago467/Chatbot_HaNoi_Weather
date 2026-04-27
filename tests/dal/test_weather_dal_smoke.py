"""Smoke tests cho `app.dal.weather_dal` (729 dòng).

Mục tiêu: pin import + signature + behavior với DB rỗng/mock, để PR2.2
(split DAL theo domain) sau này có thể verify split không phá public API.

Test KHÔNG cần DB thật — monkeypatch `app.db.dal.query` và `query_one`.
Chia 3 nhóm:

  A. Import + signature stability — public function name + param đúng
  B. Empty-DB behavior — mock query trả [] / None, hàm không crash
  C. Pure function — `analyze_rain_from_forecasts` không phụ thuộc DB
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import pytest


# Helper: ts_utc là datetime trong DB, không phải Unix int.
_BASE_DT = datetime(2026, 4, 19, 9, 0, 0, tzinfo=timezone.utc)


def _ts(hours_offset: int = 0) -> datetime:
    return _BASE_DT + timedelta(hours=hours_offset)


# ── Group A: Import smoke + signature pin ───────────────────────────────────


def test_import_weather_dal_module():
    """Module load được, không lỗi khi import dependency."""
    import app.dal.weather_dal as dal
    assert dal is not None


def test_public_functions_exist():
    """14 public function chính phải có sau split."""
    import app.dal.weather_dal as dal
    expected = [
        "get_current_weather",
        "get_hourly_forecast",
        "get_daily_forecast",
        "get_weather_history",
        "get_city_weather_history",
        "get_district_weather_history",
        "get_weather_range",
        "get_latest_weather_time",
        "get_daily_summary_data",
        "analyze_rain_from_forecasts",
        "get_rain_timeline",
        "get_temperature_trend",
        "get_weather_period_data",
        "detect_weather_changes",
    ]
    missing = [name for name in expected if not hasattr(dal, name)]
    assert not missing, f"Missing public functions after split: {missing}"


@pytest.mark.parametrize("fn_name,expected_params", [
    ("get_current_weather", ["ward_id"]),
    ("get_hourly_forecast", ["ward_id", "hours"]),
    ("get_daily_forecast", ["ward_id", "days", "start_date"]),
    ("get_weather_history", ["ward_id", "date"]),
    ("get_weather_range", ["ward_id", "start_date", "end_date"]),
    ("get_rain_timeline", ["ward_id", "hours"]),
    ("get_temperature_trend", ["ward_id", "days"]),
    ("get_weather_period_data", ["ward_id", "start_date", "end_date"]),
    ("detect_weather_changes", ["ward_id", "hours"]),
    ("analyze_rain_from_forecasts", ["rows", "hours", "source_note"]),
])
def test_signature_matches(fn_name, expected_params):
    """Param order/name không đổi sau refactor (các tool consume positional/kwarg)."""
    import app.dal.weather_dal as dal
    fn = getattr(dal, fn_name)
    sig = inspect.signature(fn)
    actual = list(sig.parameters.keys())
    assert actual == expected_params, (
        f"{fn_name} signature drift: expected {expected_params}, got {actual}"
    )


@pytest.mark.parametrize("fn_name,param,default", [
    ("get_hourly_forecast", "hours", 48),
    ("get_daily_forecast", "days", 8),
    ("get_daily_forecast", "start_date", None),
    ("get_rain_timeline", "hours", 24),
    ("get_temperature_trend", "days", 7),
    ("detect_weather_changes", "hours", 6),
    ("analyze_rain_from_forecasts", "hours", 24),
    ("analyze_rain_from_forecasts", "source_note", ""),
])
def test_default_values_pinned(fn_name, param, default):
    """Default value của param không đổi (consumer phụ thuộc vào)."""
    import app.dal.weather_dal as dal
    fn = getattr(dal, fn_name)
    sig = inspect.signature(fn)
    assert sig.parameters[param].default == default


# ── Group B: Empty-DB behavior (mock query) ─────────────────────────────────


@pytest.fixture
def mock_empty_db(monkeypatch):
    """Patch `query` và `query_one` trả empty results.

    Sau PR2.2 split, weather_dal.py là thin shim — `query`/`query_one` được
    import vào từng submodule namespace (current/forecast/history/analytics)
    qua `from app.db.dal import query, query_one`. Phải patch ở từng submodule.
    """
    import app.db.dal as db
    monkeypatch.setattr(db, "query", lambda *args, **kwargs: [])
    monkeypatch.setattr(db, "query_one", lambda *args, **kwargs: None)

    # Patch submodule namespaces (DAL split-by-domain after PR2.2)
    from app.dal.weather import current, forecast, history, analytics
    for submod in (current, forecast, history, analytics):
        monkeypatch.setattr(submod, "query", lambda *args, **kwargs: [])
        monkeypatch.setattr(submod, "query_one", lambda *args, **kwargs: None)


def test_get_current_weather_empty_db(mock_empty_db):
    """DB không trả gì → hàm phải trả None hoặc dict có error key, KHÔNG raise."""
    import app.dal.weather_dal as dal
    result = dal.get_current_weather("ID_NONEXISTENT")
    # Pin: với empty DB, hàm trả None (current code path)
    # Nếu PR refactor đổi sang error dict, test này fail và phải update.
    assert result is None or (isinstance(result, dict) and "error" in result)


def test_get_hourly_forecast_empty_db(mock_empty_db):
    import app.dal.weather_dal as dal
    result = dal.get_hourly_forecast("ID_X")
    assert result == []


def test_get_daily_forecast_empty_db(mock_empty_db):
    import app.dal.weather_dal as dal
    result = dal.get_daily_forecast("ID_X")
    assert result == []


def test_get_weather_range_empty_db(mock_empty_db):
    import app.dal.weather_dal as dal
    result = dal.get_weather_range("ID_X", "2026-04-01", "2026-04-07")
    assert isinstance(result, list)


def test_get_hourly_forecast_clamps_hours(mock_empty_db):
    """`hours` clamp 1-48 — pin behavior để PR sau không drift."""
    import app.dal.weather_dal as dal
    # KHÔNG raise dù value out-of-range (clamp at line :95)
    dal.get_hourly_forecast("ID_X", hours=0)
    dal.get_hourly_forecast("ID_X", hours=999)


def test_get_daily_forecast_clamps_days(mock_empty_db):
    import app.dal.weather_dal as dal
    dal.get_daily_forecast("ID_X", days=0)
    dal.get_daily_forecast("ID_X", days=999)


# ── Group C: Pure function — analyze_rain_from_forecasts ────────────────────


def test_analyze_rain_empty_returns_error():
    from app.dal.weather_dal import analyze_rain_from_forecasts
    out = analyze_rain_from_forecasts([])
    assert out["error"] == "no_data"
    assert "suggestion" in out


def test_analyze_rain_no_rain_periods():
    """Forecast toàn nắng → 0 rain_periods."""
    from app.dal.weather_dal import analyze_rain_from_forecasts
    rows = [
        {"ts_utc": _ts(i), "pop": 0.1, "rain_1h": 0, "weather_main": "Clouds"}
        for i in range(6)
    ]
    out = analyze_rain_from_forecasts(rows)
    assert out["total_rain_periods"] == 0
    assert out["rain_periods"] == []
    assert out["hours_scanned"] == 6


def test_analyze_rain_detects_continuous_rain_period():
    """Mưa liên tục 3 giờ → 1 period."""
    from app.dal.weather_dal import analyze_rain_from_forecasts
    rows = [
        {"ts_utc": _ts(0), "pop": 0.1, "rain_1h": 0, "weather_main": "Clouds"},
        {"ts_utc": _ts(1), "pop": 0.6, "rain_1h": 1.0, "weather_main": "Rain"},
        {"ts_utc": _ts(2), "pop": 0.7, "rain_1h": 1.5, "weather_main": "Rain"},
        {"ts_utc": _ts(3), "pop": 0.5, "rain_1h": 0.8, "weather_main": "Rain"},
        {"ts_utc": _ts(4), "pop": 0.1, "rain_1h": 0, "weather_main": "Clouds"},
    ]
    out = analyze_rain_from_forecasts(rows)
    assert out["total_rain_periods"] == 1
    assert out["rain_periods"][0]["max_pop"] == 70  # 0.7 → 70%
    assert out["next_clear"] is not None


def test_analyze_rain_supports_aggregate_keys():
    """District/city aggregate dùng avg_pop, avg_rain_1h thay vì pop, rain_1h."""
    from app.dal.weather_dal import analyze_rain_from_forecasts
    rows = [
        {"ts_utc": _ts(0), "avg_pop": 0.6, "avg_rain_1h": 0.5,
         "weather_main": "Rain"},
    ]
    out = analyze_rain_from_forecasts(rows)
    assert out["total_rain_periods"] == 1


def test_analyze_rain_source_note_propagates():
    from app.dal.weather_dal import analyze_rain_from_forecasts
    out = analyze_rain_from_forecasts(
        [{"ts_utc": _ts(0), "pop": 0.1, "rain_1h": 0, "weather_main": "Clouds"}],
        source_note="city_aggregated",
    )
    assert out["source_note"] == "city_aggregated"


def test_analyze_rain_threshold_pop_30_percent():
    """Pin: ngưỡng pop >= 0.3 mới coi là is_rain (không phải 0.5)."""
    from app.dal.weather_dal import analyze_rain_from_forecasts
    rows = [
        {"ts_utc": _ts(0), "pop": 0.3, "rain_1h": 0, "weather_main": "Clouds"},
    ]
    out = analyze_rain_from_forecasts(rows)
    assert out["total_rain_periods"] == 1


def test_analyze_rain_threshold_pop_below_30_no_match():
    from app.dal.weather_dal import analyze_rain_from_forecasts
    rows = [
        {"ts_utc": _ts(0), "pop": 0.29, "rain_1h": 0, "weather_main": "Clouds"},
    ]
    out = analyze_rain_from_forecasts(rows)
    assert out["total_rain_periods"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
