"""R18 P1-6: unified output metadata schema contract tests.

Tools dùng các helper trong `app/agent/tools/output/_common.py` để emit
metadata block nhất quán:
- _emit_truncation_note: warning khi shown < full
- _emit_past_date_warning: warning cho daily_forecast nhận date past
- _emit_scope_gap: warning khi tool cover < user request
- (đã có) _detect_forecast_range_gap, _emit_coverage_days,
  _emit_snapshot_metadata, _emit_historical_metadata, _emit_missing_fields

Tests này guard contract: thay đổi message/key trong helpers sẽ break tests
→ buộc dev consider impact lên LLM downstream.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.agent.tools.output._common import (
    _emit_past_date_warning,
    _emit_scope_gap,
    _emit_truncation_note,
)


# ─────────────────────────────────────────────────────────────────
# _emit_truncation_note
# ─────────────────────────────────────────────────────────────────

def test_truncation_note_emits_when_shown_lt_full():
    """Truncate (12 < 48) → emit warning với count visible."""
    out = _emit_truncation_note(
        full_count=48, shown_count=12, label="timeline độ ẩm",
    )
    assert "⚠ dữ liệu bị giới hạn" in out
    msg = out["⚠ dữ liệu bị giới hạn"]
    assert "12/48" in msg
    assert "timeline độ ẩm" in msg


def test_truncation_note_no_op_when_shown_equals_full():
    """Không truncate (5 == 5) → no-op."""
    assert _emit_truncation_note(full_count=5, shown_count=5, label="x") == {}


def test_truncation_note_no_op_when_shown_gt_full():
    """Defensive: shown > full không nên xảy ra nhưng emit empty."""
    assert _emit_truncation_note(full_count=5, shown_count=10, label="x") == {}


def test_truncation_note_no_op_when_full_zero():
    """No data → no-op."""
    assert _emit_truncation_note(full_count=0, shown_count=0, label="x") == {}


def test_truncation_note_message_mentions_action():
    """Message phải gợi ý hành động (tăng hours, gọi tool khác)."""
    out = _emit_truncation_note(full_count=48, shown_count=12, label="X")
    msg = out["⚠ dữ liệu bị giới hạn"]
    assert "hours" in msg or "tool" in msg.lower()


# ─────────────────────────────────────────────────────────────────
# _emit_past_date_warning
# ─────────────────────────────────────────────────────────────────

def test_past_date_warning_flags_past_dates():
    """Date in past → emit warning với suggest history tool."""
    today = date(2026, 5, 9)
    out = _emit_past_date_warning(
        dates=["2026-05-05", "2026-05-09", "2026-05-12"],
        today=today,
    )
    assert "⚠ ngày đã qua" in out
    msg = out["⚠ ngày đã qua"]
    # Past date format DD/MM/YYYY
    assert "05/05/2026" in msg
    # Today + future không trong list
    assert "12/05/2026" not in msg
    # Today (== today) không phải past
    assert "09/05/2026" not in msg
    # Suggest history tool
    assert "get_weather_history" in msg


def test_past_date_warning_no_op_for_future_dates():
    today = date(2026, 5, 9)
    out = _emit_past_date_warning(
        dates=["2026-05-10", "2026-05-15"],
        today=today,
    )
    assert out == {}


def test_past_date_warning_no_op_for_today_only():
    today = date(2026, 5, 9)
    out = _emit_past_date_warning(dates=["2026-05-09"], today=today)
    assert out == {}


def test_past_date_warning_handles_empty_dates():
    today = date(2026, 5, 9)
    assert _emit_past_date_warning(dates=[], today=today) == {}


def test_past_date_warning_skips_invalid_dates():
    """Invalid date strings không phá flow."""
    today = date(2026, 5, 9)
    out = _emit_past_date_warning(
        dates=["invalid-string", "2026-05-05", None],
        today=today,
    )
    assert "⚠ ngày đã qua" in out
    assert "05/05/2026" in out["⚠ ngày đã qua"]


# ─────────────────────────────────────────────────────────────────
# _emit_scope_gap
# ─────────────────────────────────────────────────────────────────

def test_scope_gap_always_emits():
    """Caller-gated — helper always emit khi được gọi."""
    out = _emit_scope_gap(
        requested_label="3 ngày tới",
        available_label="24h tới",
    )
    assert "⚠ phạm vi" in out
    msg = out["⚠ phạm vi"]
    assert "3 ngày tới" in msg
    assert "24h tới" in msg
    # Suggest disclaim
    assert "disclaim" in msg.lower() or "kết luận" in msg.lower()


# ─────────────────────────────────────────────────────────────────
# Integration: builder uses helpers correctly
# ─────────────────────────────────────────────────────────────────

def test_humidity_timeline_no_truncate_at_max_hours():
    """Cap = FORECAST_MAX_HOURS (48). 48 entries pass through không truncate."""
    from app.agent.tools.output_builder import build_humidity_timeline_output

    timeline = [
        {"ts_utc": 1746748800 + i * 3600, "humidity": 70 + i % 20,
         "dew_point": 18 + i % 5, "temp": 25 + i % 8}
        for i in range(48)
    ]
    out = build_humidity_timeline_output({
        "timeline": timeline,
        "statistics": {},
        "nom_am_periods": [],
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    # 48 entries pass through (cap=48)
    assert len(out["timeline độ ẩm"]) == 48
    # KHÔNG có warning vì cap=full
    assert "⚠ dữ liệu bị giới hạn" not in out


def test_humidity_timeline_truncates_only_for_overflow():
    """Defensive: nếu data > 48 (edge case bug DAL) → truncate + warn."""
    from app.agent.tools.output_builder import build_humidity_timeline_output

    timeline = [
        {"ts_utc": 1746748800 + i * 3600, "humidity": 70,
         "dew_point": 18, "temp": 25}
        for i in range(60)  # over cap
    ]
    out = build_humidity_timeline_output({
        "timeline": timeline,
        "statistics": {},
        "nom_am_periods": [],
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert len(out["timeline độ ẩm"]) == 48  # cap
    assert "⚠ dữ liệu bị giới hạn" in out
    assert "48/60" in out["⚠ dữ liệu bị giới hạn"]


def test_sunny_periods_passes_through_normal_count():
    """Cap = 20 cloudy windows. 8 windows pass through không truncate."""
    from app.agent.tools.output_builder import build_sunny_periods_output

    cloudy = [
        {"start": f"{h:02d}:00 04/05", "end": f"{h+1:02d}:00 04/05",
         "clouds": 80, "pop": 0.4}
        for h in range(8)
    ]
    out = build_sunny_periods_output({
        "sunny_windows": [],
        "cloudy_windows": cloudy,
        "best_sunny_time": "",
        "summary": "no sunny",
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert len(out["khung nhiều mây"]) == 8
    assert "⚠ dữ liệu bị giới hạn" not in out


def test_sunny_periods_truncates_only_when_over_cap():
    """Defensive: nếu cloudy_windows > 20 → truncate + warn."""
    from app.agent.tools.output_builder import build_sunny_periods_output

    cloudy = [
        {"start": f"w{i}", "end": f"w{i}", "clouds": 80, "pop": 0.4}
        for i in range(25)  # over cap=20
    ]
    out = build_sunny_periods_output({
        "sunny_windows": [],
        "cloudy_windows": cloudy,
        "best_sunny_time": "",
        "summary": "many cloudy",
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert len(out["khung nhiều mây"]) == 20
    assert "⚠ dữ liệu bị giới hạn" in out
    assert "20/25" in out["⚠ dữ liệu bị giới hạn"]


def test_humidity_timeline_no_truncation_warning_when_below_cap():
    """Timeline ≤ 24 entries → no warning emitted."""
    from app.agent.tools.output_builder import build_humidity_timeline_output

    timeline = [
        {"ts_utc": 1746748800 + i * 3600, "humidity": 70,
         "dew_point": 18, "temp": 25}
        for i in range(10)
    ]
    out = build_humidity_timeline_output({
        "timeline": timeline,
        "statistics": {},
        "nom_am_periods": [],
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert len(out["timeline độ ẩm"]) == 10
    assert "⚠ dữ liệu bị giới hạn" not in out


def test_daily_forecast_emits_past_date_warning():
    """build_daily_forecast_output emit warning khi forecasts có date past.

    Dùng `2020-01-01` definitely-past để test independent of actual today.
    """
    from app.agent.tools.output_builder import build_daily_forecast_output

    forecasts = [
        {"date": "2020-01-01", "temp_min": 20, "temp_max": 28, "weather_main": "Clouds"},
        {"date": "2050-01-02", "temp_min": 22, "temp_max": 30, "weather_main": "Rain"},
    ]
    out = build_daily_forecast_output({
        "forecasts": forecasts,
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert "⚠ ngày đã qua" in out
    assert "01/01/2020" in out["⚠ ngày đã qua"]
    # Future date không xuất hiện trong warning list
    assert "02/01/2050" not in out["⚠ ngày đã qua"]


def test_daily_forecast_no_warning_for_all_future():
    """All future dates → no past-date warning."""
    from app.agent.tools.output_builder import build_daily_forecast_output

    # Use very far future to avoid time-dependent test fragility
    forecasts = [
        {"date": "2050-01-01", "temp_min": 20, "temp_max": 28, "weather_main": "Clouds"},
        {"date": "2050-01-02", "temp_min": 22, "temp_max": 30, "weather_main": "Rain"},
    ]
    out = build_daily_forecast_output({
        "forecasts": forecasts,
        "level": "ward",
        "resolved_location": {"ward_name_vi": "Test Ward"},
    })
    assert "⚠ ngày đã qua" not in out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
