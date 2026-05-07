"""Tests cho `compare_weather_forecast` (P11) — 1-call wrapper bypass Qwen3 thinking
multi-tool stop-after-1 bug. Tests focus vào `build_compare_forecast_output` builder
(unit-level, không hit DB) + 1 smoke test gọi tool object qua mock.
"""

from __future__ import annotations

import pytest

from app.agent.tools.output_builder import build_compare_forecast_output


def _make_raw(name_vi: str, level: str, dates_temps: list[tuple[str, float, float, int, float]]):
    """Build raw output từ dispatch_forecast (giống wrap_forecast_result).

    dates_temps: list (date, temp_min, temp_max, humidity, rain_total).
    """
    forecasts = [
        {
            "date": d,
            "temp_min": tmin,
            "temp_max": tmax,
            "temp_avg": (tmin + tmax) / 2,
            "humidity": h,
            "rain_total": r,
            "pop": 0.5,
            "weather_main": "Clouds",
        }
        for (d, tmin, tmax, h, r) in dates_temps
    ]
    resolved = {
        "ward_name_vi": name_vi if level == "ward" else "",
        "district_name_vi": name_vi if level != "city" else "",
        "city_name": "Hà Nội" if level == "city" else "",
    }
    return {
        "forecasts": forecasts,
        "resolved_location": resolved,
        "level": level,
        "data_coverage": f"{len(forecasts)} ngày tới",
    }


def test_basic_2_wards_returns_symmetric_blocks():
    """2 ward khác nhau, cùng 2 ngày → output có đủ địa điểm 1/2 + chênh lệch."""
    raw1 = _make_raw("Cầu Giấy", "ward", [("2026-05-09", 24, 31, 70, 4.8), ("2026-05-10", 25, 30, 65, 0.8)])
    raw2 = _make_raw("Nghĩa Đô", "ward", [("2026-05-09", 22, 29, 75, 6.2), ("2026-05-10", 23, 28, 70, 1.0)])

    out = build_compare_forecast_output(raw1, raw2, "Cầu Giấy", "Nghĩa Đô")

    assert "địa điểm 1" in out
    assert "địa điểm 2" in out
    assert "Cầu Giấy" in out["địa điểm 1"]
    assert "Nghĩa Đô" in out["địa điểm 2"]
    assert "dự báo địa điểm 1" in out and len(out["dự báo địa điểm 1"]) == 2
    assert "dự báo địa điểm 2" in out and len(out["dự báo địa điểm 2"]) == 2
    assert "chênh lệch" in out and len(out["chênh lệch"]) == 2
    assert "ngày cover" in out
    assert "tóm tắt" in out


def test_chenh_lech_per_day_has_delta_fields():
    """chênh lệch list có Δnhiệt + Δẩm + Δmưa per ngày."""
    raw1 = _make_raw("A", "ward", [("2026-05-09", 24, 31, 70, 4.8)])
    raw2 = _make_raw("B", "ward", [("2026-05-09", 22, 29, 75, 6.2)])

    out = build_compare_forecast_output(raw1, raw2, "A", "B")
    diff = out["chênh lệch"][0]

    assert "ngày" in diff
    assert "Δnhiệt" in diff
    # A avg = 27.5, B avg = 25.5 → +2.0°C
    assert "+2.0°C" in diff["Δnhiệt"] or "2.0" in diff["Δnhiệt"]
    assert "Δẩm" in diff
    assert "Δmưa" in diff


def test_intersect_dates_when_one_location_covers_more():
    """Location 1 cover 3 ngày, location 2 cover 2 → output chỉ 2 ngày chung + ghi chú."""
    raw1 = _make_raw("A", "ward", [
        ("2026-05-09", 24, 31, 70, 1.0),
        ("2026-05-10", 25, 30, 65, 0.5),
        ("2026-05-11", 26, 32, 60, 0.0),
    ])
    raw2 = _make_raw("B", "ward", [
        ("2026-05-09", 22, 29, 75, 2.0),
        ("2026-05-10", 23, 28, 70, 1.5),
    ])

    out = build_compare_forecast_output(raw1, raw2, "A", "B")

    assert len(out["dự báo địa điểm 1"]) == 2  # chỉ 2 ngày chung
    assert len(out["dự báo địa điểm 2"]) == 2
    assert len(out["chênh lệch"]) == 2
    assert "ghi chú dữ liệu" in out  # disclaim cover lệch


def test_same_location_returns_error():
    """Cả 2 raw resolve cùng location → error same_location."""
    raw1 = _make_raw("Cầu Giấy", "ward", [("2026-05-09", 24, 31, 70, 1.0)])
    raw2 = _make_raw("Cầu Giấy", "ward", [("2026-05-09", 24, 31, 70, 1.0)])

    out = build_compare_forecast_output(raw1, raw2, "Cầu Giấy", "Cầu Giấy")

    assert "error" in out or "lỗi" in str(out).lower()


def test_no_common_days_returns_error():
    """2 location cover ngày khác nhau hoàn toàn → error no_common_days."""
    raw1 = _make_raw("A", "ward", [("2026-05-09", 24, 31, 70, 1.0)])
    raw2 = _make_raw("B", "ward", [("2026-05-15", 24, 31, 70, 1.0)])

    out = build_compare_forecast_output(raw1, raw2, "A", "B")

    assert "error" in out or "lỗi" in str(out).lower()


def test_propagates_first_error():
    """raw1 có error → builder propagate + tag location 1."""
    raw1 = {"error": "not_found", "message": "Không tìm thấy địa điểm"}
    raw2 = _make_raw("B", "ward", [("2026-05-09", 24, 31, 70, 1.0)])

    out = build_compare_forecast_output(raw1, raw2, "Hồ Gươm", "B")

    assert "error" in out or "lỗi" in str(out).lower()
    assert "Hồ Gươm" in str(out)  # tag location bị lỗi


def test_compare_weather_forecast_tool_registered():
    """Tool có name + args_schema đúng (smoke check registration)."""
    from app.agent.tools.compare import compare_weather_forecast

    assert compare_weather_forecast.name == "compare_weather_forecast"
    schema = compare_weather_forecast.args
    assert "location_hint1" in schema
    assert "location_hint2" in schema
    assert "start_date" in schema
    assert "days" in schema


def test_compare_weather_forecast_in_primary_tool_map():
    """compare_weather_forecast nằm trong PRIMARY_TOOL_MAP[location_comparison] cả 3 scope."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP

    for scope in ("city", "district", "ward"):
        tools = PRIMARY_TOOL_MAP["location_comparison"][scope]
        names = [t.name for t in tools]
        assert "compare_weather_forecast" in names, f"missing trong scope={scope}"
