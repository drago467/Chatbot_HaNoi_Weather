"""Flat Vietnamese tool output builders.

Mỗi builder biến raw dict từ DAL/dispatch → flat dict có:
- key = mô tả tiếng Việt ("nhiệt độ", "xác suất mưa", ...)
- value = chuỗi combined "<nhãn> <số> <đơn vị>"

LLM nhận output đã "thành câu" → chỉ copy/reshape, không tự diễn giải.

Dùng cho 27 tools chia 4 nhóm:
- Group 1 (11): full weather data builders (dưới)
- Group 2 (8): shape_labeled_dict với key_map
- Group 3 (5): window-list builders
- Group 4 (3): shape_ranking_output
"""

from __future__ import annotations

from datetime import datetime, date as _date_cls
from typing import Any, Dict, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

from app.dal.weather_helpers import (
    compute_heat_index,
    compute_wind_chill,
    get_dew_point_status,
    get_pressure_status,
    get_uv_status,
    label_clouds,
    label_rain_intensity,
    label_rain_probability,
    label_rain_total,
    label_temp_hn,
    weather_main_to_vietnamese,
    wind_beaufort_vietnamese,
    wind_deg_to_vietnamese,
    wind_speed_to_beaufort,
)

# PR2.1: helpers extracted to output._common — re-import for backward compat.
from app.agent.tools.output._common import *  # noqa: F401, F403
from app.agent.tools.output._common import (
    _ICT, _WEEKDAYS_VI, _LEVEL_SUFFIX,
    _as_date, _format_date_vi, _format_dt_ict, _format_hour_short,
    _format_time_only, _format_location, _pick_temp,
    _wind_text, _wind_gust_only, _add_conditional_comfort, _add_visibility,
    _narrative_current, _is_error,
    _detect_forecast_range_gap, _emit_coverage_days,
    _emit_snapshot_metadata, _emit_historical_metadata, _emit_missing_fields,
    _METRIC_VN_LABEL, _UNIT_DISPLAY,
    _fmt_window, _ADVICE_NO_HALLUCINATE,
)




# ── Group 1: full weather data builders ─────────────────────────────────────

def build_current_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """get_current_weather → flat VN dict."""
    if _is_error(raw):
        return build_error_output(raw)

    level = raw.get("level") or "ward"
    resolved = raw.get("resolved_location") or {}
    location_name = _format_location(resolved, level)

    temp = _pick_temp(raw, "temp", "avg_temp")
    feels_like = raw.get("feels_like")
    humidity = raw.get("humidity") or raw.get("avg_humidity")
    dew_point = raw.get("dew_point") or raw.get("avg_dew_point")
    pressure = raw.get("pressure") or raw.get("avg_pressure")
    wind_speed = raw.get("wind_speed") or raw.get("avg_wind_speed")
    wind_gust = raw.get("wind_gust") or raw.get("max_wind_gust")
    wind_deg = raw.get("wind_deg") or raw.get("avg_wind_deg")
    clouds = raw.get("clouds") or raw.get("avg_clouds")
    uvi = raw.get("uvi") or raw.get("avg_uvi")
    pop = raw.get("pop") or raw.get("avg_pop")
    rain_1h = raw.get("rain_1h") or raw.get("avg_rain_1h")
    visibility = raw.get("visibility") or raw.get("avg_visibility")
    weather_main = raw.get("weather_main")

    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "thời điểm": _format_dt_ict(raw.get("time_ict") or raw.get("ts_utc")),
        "thời tiết chung": weather_main_to_vietnamese(weather_main or "") or "Không xác định",
        "nhiệt độ": label_temp_hn(temp),
    }
    if humidity is not None:
        result["độ ẩm"] = f"{int(round(humidity))}%"
    if level == "ward" and feels_like is not None:
        result["cảm giác"] = f"{label_temp_hn(feels_like)}"
    if dew_point is not None:
        result["điểm sương"] = f"{get_dew_point_status(dew_point)} {dew_point:.1f}°C"
    if pop is not None:
        result["xác suất mưa"] = label_rain_probability(pop)
    if rain_1h is not None and rain_1h >= 0.05:
        result["cường độ mưa hiện tại"] = label_rain_intensity(rain_1h)
    result["gió"] = _wind_text(wind_speed, wind_gust, wind_deg)
    if clouds is not None:
        result["mây"] = label_clouds(clouds)
    if uvi is not None:
        result["UV"] = f"{get_uv_status(uvi)} {uvi:.1f}"
    if pressure is not None:
        result["áp suất"] = f"{get_pressure_status(int(pressure))} {float(pressure):.1f} hPa"
    _add_conditional_comfort(result, temp, humidity, wind_speed)
    _add_visibility(result, visibility)

    pop_pct = pop * 100 if pop is not None else None
    result["tóm tắt"] = _narrative_current(raw, location_name, temp, clouds, pop_pct, rain_1h)
    result["gợi ý dùng output"] = (
        "Đây là SNAPSHOT tại thời điểm hiện tại. CHỈ dùng khi user hỏi 'bây giờ / hiện tại / đang / lúc này'. "
        "Nếu user hỏi 'chiều/tối/đêm/sáng mai/ngày mai/cuối tuần' → KHÔNG dùng số ở đây; "
        "gọi get_hourly_forecast (1-48h) hoặc get_daily_forecast. "
        "KHÔNG dán nhiệt độ/gió hiện tại làm 'nhiệt độ tối nay' hay 'gió giật mạnh nhất cả ngày'."
    )
    if raw.get("data_stale"):
        result["ghi chú dữ liệu"] = raw.get("data_warning") or "Dữ liệu có thể cũ hơn thường lệ."
    # R11 Contract B: snapshot metadata (front-loaded grounding)
    # R13 Contract D: absence emission cho field thường bị LLM suy diễn (v11 ID 12, 81)
    return {
        **_emit_snapshot_metadata(raw.get("time_ict") or raw.get("ts_utc")),
        **_emit_missing_fields(raw, [
            ("tầm nhìn", "visibility"),
            ("sương mù", "fog"),
        ]),
        **result,
    }


def _build_hourly_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    temp = _pick_temp(entry, "temp", "avg_temp")
    pop = entry.get("pop") or entry.get("avg_pop")
    rain_1h = entry.get("rain_1h") or entry.get("avg_rain_1h")
    clouds = entry.get("clouds") or entry.get("avg_clouds")
    wind_speed = entry.get("wind_speed") or entry.get("avg_wind_speed")
    wind_gust = entry.get("wind_gust") or entry.get("max_wind_gust")
    wind_deg = entry.get("wind_deg") or entry.get("avg_wind_deg")
    humidity = entry.get("humidity") or entry.get("avg_humidity")

    out: Dict[str, Any] = {
        "thời điểm": _format_hour_short(entry.get("time_ict") or entry.get("ts_utc")),
        "thời tiết": weather_main_to_vietnamese(entry.get("weather_main") or "") or "—",
        "nhiệt độ": label_temp_hn(temp),
    }
    if humidity is not None:
        out["độ ẩm"] = f"{int(round(humidity))}%"
    if pop is not None:
        out["xác suất mưa"] = label_rain_probability(pop)
    if rain_1h is not None and rain_1h >= 0.05:
        out["cường độ mưa"] = label_rain_intensity(rain_1h)
    out["gió"] = _wind_text(wind_speed, wind_gust, wind_deg)
    if clouds is not None:
        out["mây"] = label_clouds(clouds)
    return out


def _narrative_hourly(forecasts: Sequence[Mapping[str, Any]], location_name: str) -> str:
    if not forecasts:
        return ""
    temps = [_pick_temp(f, "temp", "avg_temp") for f in forecasts]
    temps = [t for t in temps if t is not None]
    pops = [f.get("pop") or f.get("avg_pop") or 0 for f in forecasts]
    rain_hours = sum(1 for f in forecasts
                     if (f.get("rain_1h") or f.get("avg_rain_1h") or 0) >= 0.1)
    max_pop = int(round(max(pops) * 100)) if pops else 0
    bits = [f"{len(forecasts)} giờ tới tại {location_name}"]
    if temps:
        bits.append(f"nhiệt {min(temps):.0f}–{max(temps):.0f}°C")
    if rain_hours:
        bits.append(f"{rain_hours} giờ có mưa")
    elif max_pop >= 40:
        bits.append(f"xác suất mưa cao nhất {max_pop}%")
    else:
        bits.append("không mưa")
    return ", ".join(bits) + "."




def build_hourly_forecast_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    forecasts = raw.get("forecasts") or []

    entries = [_build_hourly_entry(f) for f in forecasts]
    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "loại dự báo": raw.get("data_coverage") or f"{len(entries)} giờ tới",
        "dự báo": entries,
    }
    # Past-frame detection: thêm "phạm vi thực tế" + cảnh báo nếu khung đã qua
    result.update(_detect_forecast_range_gap(forecasts))
    # R13 Contract D + R16 P7 (audit ID 345): hourly forecast entries không emit
    # visibility/fog/uvi → LLM suy diễn từ độ ẩm+mây hoặc bịa "UV 12-17h: 8-10".
    # Emit explicit absence cho cả 3 fields.
    first_entry = forecasts[0] if forecasts else {}
    result.update(_emit_missing_fields(first_entry, [
        ("tầm nhìn", "visibility"),
        ("sương mù", "fog"),
        ("UV theo giờ", "uvi"),
    ]))
    result["tóm tắt tổng"] = _narrative_hourly(forecasts, location_name)
    if raw.get("data_note"):
        result["ghi chú dữ liệu"] = raw["data_note"]
    return result


def _build_daily_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    date_v = entry.get("date")
    temp_min = entry.get("temp_min")
    temp_max = entry.get("temp_max")
    temp_avg = entry.get("temp_avg") or entry.get("temp") or entry.get("avg_temp")
    humidity = entry.get("humidity") or entry.get("avg_humidity")
    pop = entry.get("pop") or entry.get("avg_pop")
    rain_total = entry.get("rain_total") or entry.get("total_rain")
    uvi = entry.get("uvi") or entry.get("max_uvi") or entry.get("uvi_max")
    wind_speed = entry.get("wind_speed") or entry.get("avg_wind_speed")
    wind_gust = entry.get("wind_gust") or entry.get("max_wind_gust")
    wind_deg = entry.get("wind_deg") or entry.get("avg_wind_deg")
    weather_main = entry.get("weather_main")
    summary_ai = entry.get("summary")

    out: Dict[str, Any] = {
        "ngày": _format_date_vi(date_v),
        "thời tiết": weather_main_to_vietnamese(weather_main or "") or "—",
    }
    if temp_min is not None and temp_max is not None:
        tb = f" (TB {temp_avg:.1f}°C)" if temp_avg is not None else ""
        out["nhiệt độ"] = f"Thấp {temp_min:.1f}°C — Cao {temp_max:.1f}°C{tb}"
    elif temp_avg is not None:
        out["nhiệt độ"] = label_temp_hn(temp_avg)

    # Daily structured sub-temps (morn/day/eve/night) — ward forecast có từ OWM
    morn = entry.get("temp_morn")
    day = entry.get("temp_day")
    eve = entry.get("temp_eve")
    night = entry.get("temp_night")
    if any(x is not None for x in (morn, day, eve, night)):
        parts = []
        if morn is not None: parts.append(f"Sáng {morn:.1f}°C")
        if day is not None: parts.append(f"Trưa {day:.1f}°C")
        if eve is not None: parts.append(f"Chiều {eve:.1f}°C")
        if night is not None: parts.append(f"Tối {night:.1f}°C")
        out["nhiệt độ theo ngày"] = " / ".join(parts)

    if humidity is not None:
        out["độ ẩm"] = f"{int(round(humidity))}%"
    if pop is not None:
        out["xác suất mưa"] = label_rain_probability(pop)
    if rain_total is not None and rain_total >= 0.05:
        out["tổng lượng mưa"] = label_rain_total(rain_total)
    out["gió"] = _wind_text(wind_speed, wind_gust, wind_deg)
    if uvi is not None:
        out["UV"] = f"{get_uv_status(uvi)} {uvi:.1f}"

    sr = entry.get("sunrise_time") or entry.get("sunrise")
    ss = entry.get("sunset_time") or entry.get("sunset")
    sr_s = _format_time_only(sr) if sr else ""
    ss_s = _format_time_only(ss) if ss else ""
    if sr_s and ss_s:
        out["mọc-lặn"] = f"Mặt trời {sr_s} → {ss_s}"

    if summary_ai:
        out["tóm tắt"] = str(summary_ai)
    return out


def _compute_daily_superlatives(forecasts: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    """Pre-compute argmax/argmin trên list ngày forecast.

    Trả dict VN key → "DD/MM (Thứ X): <label> <value>".
    LLM không phải argmax qua list — chỉ copy key.
    """
    if not forecasts:
        return {}

    def _day_label(f: Mapping[str, Any]) -> str:
        date_v = _as_date(f.get("date"))
        if not date_v:
            return str(f.get("date", ""))
        return f"{date_v.strftime('%d/%m')} ({_WEEKDAYS_VI[date_v.weekday()]})"

    def _safe_num(f: Mapping[str, Any], *keys: str) -> Optional[float]:
        for k in keys:
            v = f.get(k)
            if v is not None:
                return float(v)
        return None

    result: Dict[str, str] = {}

    # Ngày nóng nhất (theo temp_max)
    hottest = max(
        ((f, _safe_num(f, "temp_max")) for f in forecasts),
        key=lambda x: x[1] if x[1] is not None else -999,
        default=(None, None),
    )
    if hottest[1] is not None:
        result["ngày nóng nhất"] = f"{_day_label(hottest[0])}: Cao {hottest[1]:.1f}°C"

    # Ngày mát nhất (theo temp_min)
    coolest = min(
        ((f, _safe_num(f, "temp_min")) for f in forecasts),
        key=lambda x: x[1] if x[1] is not None else 999,
        default=(None, None),
    )
    if coolest[1] is not None:
        result["ngày mát nhất"] = f"{_day_label(coolest[0])}: Thấp {coolest[1]:.1f}°C"

    # Ngày mưa nhiều nhất (theo rain_total)
    rainiest = max(
        ((f, _safe_num(f, "rain_total", "total_rain") or 0) for f in forecasts),
        key=lambda x: x[1],
        default=(None, 0),
    )
    if rainiest[0] is not None and rainiest[1] > 0.05:
        result["ngày mưa nhiều nhất"] = f"{_day_label(rainiest[0])}: {label_rain_total(rainiest[1])}"

    # Ngày ít mưa nhất / khô nhất — chỉ liệt kê khi có >= 2 ngày có data
    def _rain_of(f: Mapping[str, Any]) -> float:
        return _safe_num(f, "rain_total", "total_rain") or 0
    def _pop_of(f: Mapping[str, Any]) -> float:
        return _safe_num(f, "pop") or 0

    rains_per_day = [(f, _rain_of(f), _pop_of(f)) for f in forecasts]
    driest = min(rains_per_day, key=lambda x: (x[1], x[2]))
    if len(forecasts) >= 2 and driest[0] is not None:
        rain_txt = label_rain_total(driest[1]) if driest[1] >= 0.05 else "Không mưa"
        pop_txt = label_rain_probability(driest[2]) if driest[2] else ""
        tail = f" ({pop_txt})" if pop_txt else ""
        result["ngày khô/ít mưa nhất"] = f"{_day_label(driest[0])}: {rain_txt}{tail}"

    return result


def _narrative_daily(forecasts: Sequence[Mapping[str, Any]], location_name: str) -> str:
    if not forecasts:
        return ""
    temps_min = [f.get("temp_min") for f in forecasts if f.get("temp_min") is not None]
    temps_max = [f.get("temp_max") for f in forecasts if f.get("temp_max") is not None]
    rain_days = sum(1 for f in forecasts
                    if (f.get("rain_total") or f.get("total_rain") or 0) >= 1)
    bits = [f"{len(forecasts)} ngày tại {location_name}"]
    if temps_min and temps_max:
        bits.append(f"nhiệt {min(temps_min):.0f}–{max(temps_max):.0f}°C")
    if rain_days:
        bits.append(f"{rain_days} ngày có mưa")
    else:
        bits.append("không mưa đáng kể")
    return ", ".join(bits) + "."


def build_daily_forecast_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    forecasts = raw.get("forecasts") or []
    entries = [_build_daily_entry(f) for f in forecasts]
    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "loại dự báo": raw.get("data_coverage") or f"{len(entries)} ngày tới",
        "dự báo": entries,
    }
    # Pre-computed superlatives để LLM không phải argmax qua list
    sup = _compute_daily_superlatives(forecasts)
    if sup:
        result["tổng hợp"] = sup
    result["tóm tắt tổng"] = _narrative_daily(forecasts, location_name)
    if raw.get("data_note"):
        result["ghi chú dữ liệu"] = raw["data_note"]
    # R11 Contract A: front-load ngày cover (ISO + weekday)
    dates = [f.get("date") for f in forecasts if isinstance(f, Mapping) and f.get("date")]
    return {**_emit_coverage_days(dates), **result}


def build_rain_timeline_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    periods = raw.get("rain_periods") or []
    period_entries: List[Dict[str, Any]] = []
    for p in periods:
        max_pop = p.get("max_pop")
        max_rain = p.get("max_rain_1h") or 0
        rain_label = label_rain_intensity(max_rain) if max_rain >= 0.05 else ""
        entry = {
            "bắt đầu": p.get("start", ""),
            "kết thúc": p.get("end", ""),
            "xác suất cao nhất": f"{int(max_pop)}%" if max_pop is not None else "—",
        }
        if rain_label:
            entry["cường độ đỉnh"] = rain_label
        period_entries.append(entry)

    summary_bits: List[str] = []
    if raw.get("next_rain"):
        summary_bits.append(f"mưa bắt đầu lúc {raw['next_rain']}")
    if raw.get("next_clear"):
        summary_bits.append(f"tạnh lúc {raw['next_clear']}")
    if not periods and not summary_bits:
        summary_bits.append(f"không có đợt mưa nào trong {raw.get('hours_scanned', '?')} giờ tới")

    summary_text = "; ".join(summary_bits)
    if summary_text:
        summary_text = summary_text[:1].upper() + summary_text[1:] + "."
    else:
        summary_text = "Không có đợt mưa dự báo."
    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "phạm vi": raw.get("data_coverage") or f"{raw.get('hours_scanned', 0)} giờ tới",
        "đợt mưa": period_entries,
        "tổng số đợt": raw.get("total_rain_periods") or len(periods),
        "tóm tắt": summary_text,
    }
    # Past-frame warning: nếu đợt mưa đầu tiên bắt đầu >1.5h sau NOW,
    # các khung sáng/trưa/chiều/tối đã qua trong hôm nay có thể không cover.
    # Tận dụng raw forecasts nếu dispatch layer forward qua.
    if isinstance(raw.get("forecasts"), list):
        result.update(_detect_forecast_range_gap(raw["forecasts"]))
    return result


def build_best_time_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    def _fmt_slot(s: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "thời điểm": s.get("time_ict", ""),
            "điểm": f"{s.get('score', 0)}/100",
            "nhiệt độ": label_temp_hn(s.get("temp")),
            "xác suất mưa": label_rain_probability((s.get("pop") or 0) / 100) if s.get("pop") is not None else "—",
            "ghi chú": ", ".join(s.get("issues") or []) or "Tốt",
        }

    # R11 Contract A: extract dates từ best_hours + worst_hours timestamps
    all_slots = (raw.get("best_hours") or []) + (raw.get("worst_hours") or [])
    slot_dates = []
    for s in all_slots:
        ts = s.get("ts_utc") if isinstance(s, Mapping) else None
        if isinstance(ts, (int, float)):
            slot_dates.append(datetime.fromtimestamp(float(ts), tz=_ICT).date())
    return {
        **_emit_coverage_days(slot_dates),
        "địa điểm": location_name,
        "hoạt động": raw.get("activity", ""),
        "giờ tốt nhất": [_fmt_slot(s) for s in (raw.get("best_hours") or [])],
        "giờ kém nhất": [_fmt_slot(s) for s in (raw.get("worst_hours") or [])],
        "tổng số giờ quét": raw.get("total_hours_scanned", 0),
    }


def build_weather_history_output(raw: Mapping[str, Any], date_hint: Optional[str] = None) -> Dict[str, Any]:
    """Timemachine/daily history — ward ONLY có wind_gust (không wind_speed).

    R11 Contract C: emit `"loại dữ liệu": "quá khứ"` + `"⚠ không phải hiện tại"`.
    """
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    temp = _pick_temp(raw, "temp", "avg_temp")
    feels_like = raw.get("feels_like")
    humidity = raw.get("humidity") or raw.get("avg_humidity")
    dew_point = raw.get("dew_point") or raw.get("avg_dew_point")
    wind_gust = raw.get("wind_gust") or raw.get("max_wind_gust")
    wind_speed = raw.get("wind_speed") or raw.get("avg_wind_speed")
    wind_deg = raw.get("wind_deg") or raw.get("avg_wind_deg")
    weather_main = raw.get("weather_main")
    daily = raw.get("daily_summary") or {}

    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "ngày": _format_date_vi(date_hint or raw.get("date") or daily.get("date")),
        "thời tiết chung": weather_main_to_vietnamese(weather_main or "") or "—",
    }
    if raw.get("note"):
        result["phạm vi dữ liệu"] = raw["note"]

    if temp is not None:
        result["nhiệt độ"] = label_temp_hn(temp)
    if level == "ward" and feels_like is not None:
        result["cảm giác"] = label_temp_hn(feels_like)
    if daily.get("temp_min") is not None and daily.get("temp_max") is not None:
        result["nhiệt độ min-max"] = f"Thấp {daily['temp_min']:.1f}°C — Cao {daily['temp_max']:.1f}°C"
    elif raw.get("temp_min") is not None and raw.get("temp_max") is not None:
        result["nhiệt độ min-max"] = f"Thấp {raw['temp_min']:.1f}°C — Cao {raw['temp_max']:.1f}°C"
    if humidity is not None:
        result["độ ẩm"] = f"{int(round(humidity))}%"
    if dew_point is not None:
        result["điểm sương"] = f"{get_dew_point_status(dew_point)} {dew_point:.1f}°C"

    rain_total = daily.get("rain_total") or raw.get("rain_total") or raw.get("total_rain")
    if rain_total is not None and rain_total >= 0.05:
        result["tổng lượng mưa"] = label_rain_total(rain_total)

    # Wind: history ward chỉ có wind_gust, KHÔNG bịa avg
    if wind_speed is None and wind_gust is not None:
        result["gió"] = _wind_gust_only(wind_gust, wind_deg)
    else:
        result["gió"] = _wind_text(wind_speed, wind_gust, wind_deg)

    uvi = daily.get("uvi") or raw.get("uvi") or raw.get("max_uvi")
    if uvi is not None:
        result["UV"] = f"{get_uv_status(uvi)} {uvi:.1f}"
    # R11 Contract C: front-load historical metadata (merge metadata keys TRƯỚC data keys)
    # R13 Contract D: weather_history không emit visibility → LLM suy diễn. Emit absence.
    return {
        **_emit_historical_metadata("quá khứ"),
        **_emit_missing_fields(raw, [("tầm nhìn", "visibility")]),
        **result,
    }


def build_daily_summary_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "ngày": _format_date_vi(raw.get("date")),
        "thời tiết chung": weather_main_to_vietnamese(raw.get("weather_main") or "") or "—",
    }

    # Pre-compute chênh nhiệt ngày-đêm (arithmetic self-check, fix audit B4 ID 64)
    temp_min_val: Optional[float] = None
    temp_max_val: Optional[float] = None

    tr = raw.get("temp_range")
    if isinstance(tr, Mapping):
        temp_min_val = tr.get("min")
        temp_max_val = tr.get("max")
        result["nhiệt độ"] = f"Thấp {tr.get('min', 0):.1f}°C — Cao {tr.get('max', 0):.1f}°C (biên độ {tr.get('bien_do', 0):.1f}°C)"
    elif raw.get("temp_min") is not None and raw.get("temp_max") is not None:
        temp_min_val = raw["temp_min"]
        temp_max_val = raw["temp_max"]
        result["nhiệt độ"] = f"Thấp {raw['temp_min']:.1f}°C — Cao {raw['temp_max']:.1f}°C"
    elif raw.get("avg_temp") is not None:
        result["nhiệt độ"] = label_temp_hn(raw["avg_temp"])

    if temp_min_val is not None and temp_max_val is not None:
        diff = float(temp_max_val) - float(temp_min_val)
        result["chênh nhiệt ngày-đêm"] = f"{diff:.1f}°C (COPY thẳng, KHÔNG tự tính)"

    prog = raw.get("temp_progression")
    has_progression = False
    if isinstance(prog, Mapping):
        parts = []
        for k, vi in (("sang", "Sáng"), ("trua", "Trưa"), ("chieu", "Chiều"), ("toi", "Tối")):
            v = prog.get(k)
            if v is not None:
                parts.append(f"{vi} {v:.1f}°C")
        if parts:
            result["nhiệt độ theo ngày"] = " / ".join(parts)
            has_progression = True

    humidity = raw.get("humidity") or raw.get("avg_humidity")
    if humidity is not None:
        result["độ ẩm"] = f"{int(round(humidity))}%"

    pop = raw.get("pop") or raw.get("avg_pop")
    if pop is not None:
        result["xác suất mưa"] = label_rain_probability(pop)

    rain_total = raw.get("rain_total") or raw.get("total_rain")
    if rain_total is not None and rain_total >= 0.05:
        result["tổng lượng mưa"] = label_rain_total(rain_total)

    wind = raw.get("wind")
    if isinstance(wind, Mapping):
        result["gió"] = _wind_text(wind.get("speed"), wind.get("gust"),
                                   None if wind.get("direction") else None)
        if wind.get("direction"):
            # direction may already be VN string
            result["gió"] = result["gió"] + f", hướng {wind['direction']}"
    else:
        ws = raw.get("avg_wind_speed")
        wg = raw.get("max_wind_gust") or raw.get("wind_gust")
        wd = raw.get("avg_wind_deg") or raw.get("wind_deg")
        result["gió"] = _wind_text(ws, wg, wd)

    uvi = raw.get("uvi") or raw.get("max_uvi")
    if uvi is not None:
        result["UV"] = f"{get_uv_status(uvi)} {uvi:.1f}"
    if raw.get("daylight_hours") is not None:
        result["thời gian nắng"] = f"{raw['daylight_hours']:.1f} giờ"

    sr = _format_time_only(raw.get("sunrise")) if raw.get("sunrise") else ""
    ss = _format_time_only(raw.get("sunset")) if raw.get("sunset") else ""
    if sr and ss:
        result["mọc-lặn"] = f"Mặt trời {sr} → {ss}"

    if raw.get("note"):
        result["ghi chú"] = raw["note"]
    if has_progression:
        result["gợi ý dùng output"] = (
            "Đây là TỔNG HỢP CẢ NGÀY (min/max/TB + sáng/trưa/chiều/tối), KHÔNG phải thời điểm tức thời. "
            "Nếu user hỏi 'bây giờ / hiện tại / đang' → gọi get_current_weather. "
            "Khi trả lời câu hỏi theo khung (chiều/tối/sáng) → LẤY ĐÚNG giá trị từ 'nhiệt độ theo ngày', "
            "không gán cả dải 'Thấp X — Cao Y' làm giá trị tức thời. "
            "Key `chênh nhiệt ngày-đêm` đã pre-compute — COPY thẳng, KHÔNG tự trừ max-min."
        )
    else:
        # B.3: Output không có temp_progression (sáng/trưa/chiều/tối). Gợi ý
        # phải khớp với data thực tế để LLM không bịa giá trị từng buổi.
        result["gợi ý dùng output"] = (
            "Đây là TỔNG HỢP CẢ NGÀY (min/max/TB), KHÔNG phải thời điểm tức thời. "
            "Output KHÔNG có breakdown sáng/trưa/chiều/tối — chỉ có dải nhiệt min-max cả ngày. "
            "Nếu user hỏi nhiệt độ buổi cụ thể → trả dải min-max và gọi get_hourly_forecast(start_date=date) "
            "để lấy nhiệt độ chi tiết theo giờ. TUYỆT ĐỐI KHÔNG bịa giá trị từng buổi từ min-max. "
            "Nếu user hỏi 'bây giờ / hiện tại / đang' → gọi get_current_weather. "
            "Key `chênh nhiệt ngày-đêm` đã pre-compute — COPY thẳng, KHÔNG tự trừ max-min."
        )
    # R11 Contract C: daily_summary là tổng hợp cả ngày, không phải snapshot
    # R13 Contract D: daily_summary không có mm chi tiết per-hour (ID 21 bịa 20-24h)
    missing_topics = [("lượng mưa mm chi tiết từng giờ", "rain_hourly_mm")]
    if not has_progression:
        # B.3: emit explicit absence để LLM không bịa breakdown sáng/trưa/chiều/tối
        missing_topics.append(("nhiệt độ theo buổi", "temp_progression"))
    return {
        **_emit_historical_metadata("tổng hợp cả ngày"),
        **_emit_missing_fields(raw, missing_topics),
        **result,
    }


def build_weather_period_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    daily = raw.get("daily_data") or []
    stats = raw.get("statistics") or {}
    days = raw.get("days") or len(daily)

    result: Dict[str, Any] = {
        "địa điểm": location_name,
        "phạm vi": f"{days} ngày",
    }
    result["ngày"] = [_build_daily_entry(d) for d in daily]
    # Pre-computed superlatives trên list ngày
    sup = _compute_daily_superlatives(daily)
    if sup:
        result["tổng hợp"] = sup
    if stats:
        result["thống kê tổng"] = {
            "nhiệt độ TB": label_temp_hn(stats.get("avg_temp")) if stats.get("avg_temp") is not None else "—",
            "nhiệt độ thấp nhất": f"{stats.get('min_temp'):.1f}°C" if stats.get("min_temp") is not None else "—",
            "nhiệt độ cao nhất": f"{stats.get('max_temp'):.1f}°C" if stats.get("max_temp") is not None else "—",
            "tổng lượng mưa": label_rain_total(stats.get("total_rain") or 0),
            "số ngày có mưa": f"{stats.get('rain_days', 0)}/{days}",
        }
    if raw.get("note"):
        result["ghi chú dữ liệu"] = raw["note"]
    # R11 Contract A: ngày cover từ daily list (front-loaded)
    # R13 Contract D: weather_period không emit alerts/hazard list → LLM có thể suy diễn
    dates = [d.get("date") for d in daily if isinstance(d, Mapping) and d.get("date")]
    return {
        **_emit_coverage_days(dates),
        **_emit_missing_fields(raw, [("cảnh báo cực đoan cụ thể", "alerts")]),
        **result,
    }


def _compare_location_block(loc_info: Mapping[str, Any]) -> Dict[str, Any]:
    name = loc_info.get("name") or "?"
    w = loc_info.get("weather") or {}
    temp = _pick_temp(w, "temp", "avg_temp")
    humidity = w.get("humidity") or w.get("avg_humidity")
    wind_speed = w.get("wind_speed") or w.get("avg_wind_speed")
    wind_gust = w.get("wind_gust") or w.get("max_wind_gust")
    wind_deg = w.get("wind_deg") or w.get("avg_wind_deg")
    out = {
        "tên": name,
        "thời tiết": weather_main_to_vietnamese(w.get("weather_main") or "") or "—",
        "nhiệt độ": label_temp_hn(temp),
    }
    if humidity is not None:
        out["độ ẩm"] = f"{int(round(humidity))}%"
    out["gió"] = _wind_text(wind_speed, wind_gust, wind_deg)
    return out


def build_compare_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    loc1 = raw.get("location1") or {}
    loc2 = raw.get("location2") or {}
    diffs = raw.get("differences") or {}
    diff_bits = []
    if diffs.get("temp_diff") is not None:
        diff_bits.append(f"chênh nhiệt độ {diffs['temp_diff']:+.1f}°C")
    if diffs.get("humidity_diff") is not None:
        diff_bits.append(f"chênh độ ẩm {diffs['humidity_diff']:+.0f}%")
    return {
        # R11 Contract B: so sánh 2 địa điểm tại NOW
        **_emit_snapshot_metadata(None, note="So sánh 2 địa điểm tại NOW. User hỏi so sánh khung khác → gọi tool riêng."),
        "loại so sánh": "Hai địa điểm, thời điểm hiện tại",
        "địa điểm 1": _compare_location_block(loc1),
        "địa điểm 2": _compare_location_block(loc2),
        "chênh lệch": {
            "nhiệt độ": f"{diffs.get('temp_diff', 0):+.1f}°C",
            "độ ẩm": f"{diffs.get('humidity_diff', 0):+.0f}%" if diffs.get("humidity_diff") is not None else "—",
        },
        "tóm tắt": raw.get("comparison_text") or ", ".join(diff_bits) or "Chênh lệch không đáng kể.",
    }


def build_compare_with_yesterday_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    today = raw.get("today") or {}
    prev = raw.get("previous") or {}
    level = raw.get("level") or "ward"
    location_name = raw.get("location_name") or _format_location(raw.get("resolved_location") or {}, level)

    def _day_block(d: Mapping[str, Any], date_v: Any) -> Dict[str, Any]:
        temp_avg = d.get("temp_avg") or d.get("avg_temp")
        rain = d.get("rain_total") or d.get("total_rain") or 0
        humidity = d.get("humidity") or d.get("avg_humidity")
        out = {
            "ngày": _format_date_vi(date_v or d.get("date")),
            "nhiệt độ TB": label_temp_hn(temp_avg),
            "thời tiết": weather_main_to_vietnamese(d.get("weather_main") or "") or "—",
            "lượng mưa": label_rain_total(rain) if rain >= 0.05 else "Không mưa",
        }
        if humidity is not None:
            out["độ ẩm"] = f"{int(round(humidity))}%"
        return out

    today_block = _day_block(today, today.get("date"))
    prev_block = _day_block(prev, prev.get("date"))

    changes = list(raw.get("changes") or [])
    if not changes:
        temp_diff = raw.get("temp_diff")
        if temp_diff is not None:
            changes.append(f"Nhiệt độ thay đổi {temp_diff:+.1f}°C")
        rain_diff = raw.get("rain_diff")
        if rain_diff is not None and abs(rain_diff) >= 1:
            changes.append(f"Lượng mưa thay đổi {rain_diff:+.1f} mm")

    return {
        **_emit_historical_metadata("so sánh past (hôm nay vs hôm qua)",
                                    note="So sánh này CHỈ hôm nay vs hôm qua. User hỏi 'ngày mai vs hôm nay' → gọi get_current_weather + get_daily_forecast riêng."),
        "loại so sánh": "Hôm nay vs Hôm qua",
        "địa điểm": location_name,
        "hôm nay": today_block,
        "hôm qua": prev_block,
        "thay đổi": changes or ["Thay đổi không đáng kể"],
        "tóm tắt": (changes[0] if changes else "Thời tiết hôm nay tương tự hôm qua."),
    }


def build_seasonal_comparison_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    cur = raw.get("current") or {}
    seasonal = raw.get("seasonal_avg") or {}
    # DAL compare_with_seasonal trả comparisons là list of VN strings, không phải dict
    comparisons = raw.get("comparisons") or []
    month_name = raw.get("month_name") or ""

    cur_temp = _pick_temp(cur, "temp", "avg_temp")
    seasonal_temp = seasonal.get("temp_avg")  # DAL dùng key "temp_avg"

    result: Dict[str, Any] = {
        "loại so sánh": f"Hiện tại vs trung bình {month_name}",
        "hiện tại": {
            "nhiệt độ": label_temp_hn(cur_temp),
            "độ ẩm": f"{int(round(cur.get('humidity') or cur.get('avg_humidity') or 0))}%",
        },
        "trung bình mùa": {
            "nhiệt độ TB": label_temp_hn(seasonal_temp),
        },
    }
    if seasonal.get("humidity") is not None:
        result["trung bình mùa"]["độ ẩm"] = f"{int(round(seasonal['humidity']))}%"
    if seasonal.get("temp_min") is not None and seasonal.get("temp_max") is not None:
        result["trung bình mùa"]["dải nhiệt TB"] = f"{seasonal['temp_min']}–{seasonal['temp_max']}°C"
    if seasonal.get("rain_days") is not None:
        result["trung bình mùa"]["số ngày mưa TB"] = f"{seasonal['rain_days']} ngày/tháng"

    # comparisons là list VN strings từ DAL — giữ nguyên, chỉ rename key
    if comparisons:
        result["nhận xét"] = [str(c) for c in comparisons]
    # R11 Contract B: seasonal comparison baseline là NOW (hiện tại vs TB climatology)
    return {
        **_emit_snapshot_metadata(None, note="So sánh hiện tại vs TB climatology tháng. KHÔNG dùng cho 'so hôm qua / ngày mai'."),
        **result,
    }








def build_uv_safe_windows_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    def _uv_win(w: Mapping[str, Any]) -> Dict[str, Any]:
        base = _fmt_window(w)
        uvi = w.get("uvi") or w.get("max_uvi")
        if uvi is not None:
            base["UV"] = f"{get_uv_status(uvi)} {uvi:.1f}"
        return base

    # R11 Contract A + R16 P5: scan 48h FORWARD-ONLY từ NOW. Khung đã qua trong
    # HÔM NAY (sáng/trưa nếu NOW>14h, chiều nếu >19h, etc.) KHÔNG được cover.
    return {
        **_emit_snapshot_metadata(None, note=(
            "Scan UV windows 48h FORWARD-ONLY từ NOW. ⛔ KHÔNG cover khung đã qua "
            "trong hôm nay (vd sáng nay nếu NOW>11h). User hỏi 'UV sáng nay' lúc "
            "chiều/tối → BẮT BUỘC báo 'sáng nay đã qua' + gợi ý get_weather_history(date=today)."
        )),
        "địa điểm": location_name,
        "UV đỉnh": f"{raw.get('peak_uvi', 0):.1f}" if raw.get("peak_uvi") is not None else "—",
        "giờ đỉnh": raw.get("peak_time", ""),
        "khung UV an toàn": [_uv_win(w) for w in (raw.get("safe_windows") or [])],
        "khung UV nguy hiểm": [_uv_win(w) for w in (raw.get("danger_windows") or [])],
        "tóm tắt": raw.get("summary") or "",
    }


def build_pressure_trend_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    # R11 Contract A: pressure trend 48h from NOW baseline
    return {
        **_emit_snapshot_metadata(None, note="Xu hướng áp suất 48h từ NOW. Front detect qua drop ≥3 hPa/3h."),
        "địa điểm": location_name,
        "xu hướng áp suất": raw.get("trend", ""),
        "thay đổi tổng": f"{raw.get('total_change', 0):+.1f} hPa" if raw.get("total_change") is not None else "—",
        "drop 3h lớn nhất": f"{raw.get('max_3h_drop', 0):.1f} hPa" if raw.get("max_3h_drop") is not None else "—",
        "cảnh báo front": raw.get("front_warning") or "Không có",
        "tóm tắt": raw.get("summary") or "",
    }


def build_daily_rhythm_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)
    rhythm = raw.get("rhythm") or {}

    def _bucket(b: Mapping[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        avg = b.get("avg_temp") or b.get("temp")
        if avg is not None:
            out["nhiệt độ TB"] = label_temp_hn(avg)
        if b.get("min_temp") is not None and b.get("max_temp") is not None:
            out["dải nhiệt"] = f"{b['min_temp']:.1f} – {b['max_temp']:.1f}°C"
        if b.get("avg_humidity") is not None:
            out["độ ẩm TB"] = f"{int(round(b['avg_humidity']))}%"
        return out

    result: Dict[str, Any] = {"địa điểm": location_name}
    for k, vi in (("morning", "sáng"), ("noon", "trưa"), ("afternoon", "chiều"), ("evening", "tối")):
        if isinstance(rhythm.get(k), Mapping):
            result[vi] = _bucket(rhythm[k])
    if raw.get("coolest_period"):
        result["khung mát nhất"] = raw["coolest_period"]
    if raw.get("hottest_period"):
        result["khung nóng nhất"] = raw["hottest_period"]
    # R11 Contract A: daily rhythm = 1 ngày (4 khung)
    target_date = raw.get("date") or raw.get("target_date")
    if target_date:
        return {**_emit_coverage_days([target_date]), **result}
    return {**_emit_snapshot_metadata(None, note="Nhịp nhiệt 1 ngày (4 khung sáng/trưa/chiều/tối)."), **result}


def build_humidity_timeline_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    def _hent(e: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "thời điểm": _format_hour_short(e.get("time_ict") or e.get("ts_utc")),
            "độ ẩm": f"{int(round(e.get('humidity') or 0))}%" if e.get("humidity") is not None else "—",
            "điểm sương": f"{e.get('dew_point'):.1f}°C" if e.get("dew_point") is not None else "—",
        }

    nom = raw.get("nom_am_periods") or []
    stats = raw.get("statistics") or {}
    # R11 Contract A + R16 P5 (audit IDs 177/313/422): use _detect_forecast_range_gap
    # để có past-frame check. Trước R16: dùng _emit_coverage_days (không có past-frame
    # warning) → bot dán nhãn "sáng nay" cho data 18:00+ khi user hỏi lúc 17:25.
    timeline = raw.get("timeline") or []
    if timeline and any(isinstance(e, Mapping) and isinstance(e.get("ts_utc"), (int, float)) for e in timeline):
        metadata = _detect_forecast_range_gap(timeline)
    else:
        metadata = _emit_snapshot_metadata(
            None,
            note=(
                "Timeline độ ẩm từ NOW trở đi (forward 24h). KHÔNG cover khung đã "
                "qua trong ngày (sáng/trưa nếu hỏi sau giờ đó). User hỏi past → gọi "
                "get_weather_history. KHÔNG dán nhãn 'sáng nay' cho data từ chiều/tối."
            ),
        )
    # R13 Contract D: humidity_timeline không emit sương mù dày / băng giá → LLM dễ suy diễn
    missing_emit = _emit_missing_fields(raw, [
        ("sương mù dày đặc (phân loại cụ thể)", "fog_density"),
        ("băng giá", "frost"),
    ])
    return {
        **metadata,
        **missing_emit,
        "địa điểm": location_name,
        "timeline độ ẩm": [_hent(e) for e in timeline[:24]],
        "thống kê": {
            "độ ẩm TB": f"{int(round(stats.get('avg_humidity') or 0))}%" if stats.get("avg_humidity") is not None else "—",
            "độ ẩm cao nhất": f"{int(round(stats.get('max_humidity') or 0))}%" if stats.get("max_humidity") is not None else "—",
            "độ ẩm thấp nhất": f"{int(round(stats.get('min_humidity') or 0))}%" if stats.get("min_humidity") is not None else "—",
        },
        "khung nồm ẩm": [_fmt_window(w) for w in nom] if nom else ["Không có khung nồm ẩm"],
    }


def build_sunny_periods_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    level = raw.get("level") or "ward"
    location_name = _format_location(raw.get("resolved_location") or {}, level)

    def _sun_win(w: Mapping[str, Any]) -> Dict[str, Any]:
        base = _fmt_window(w)
        if w.get("avg_clouds") is not None:
            base["mây"] = label_clouds(w["avg_clouds"])
        return base

    # R11 Contract A + R16 P5: sunny periods scan 48h FORWARD-ONLY từ NOW.
    # Khung đã qua hôm nay KHÔNG được cover.
    return {
        **_emit_snapshot_metadata(None, note=(
            "Scan khung nắng 48h FORWARD-ONLY từ NOW. ⛔ KHÔNG cover khung đã qua "
            "trong hôm nay. User hỏi 'nắng sáng nay' lúc chiều/tối → BẮT BUỘC báo "
            "'sáng nay đã qua' + gợi ý get_weather_history(date=today)."
        )),
        "địa điểm": location_name,
        "khung nắng": [_sun_win(w) for w in (raw.get("sunny_windows") or [])],
        "khung nhiều mây": [_sun_win(w) for w in (raw.get("cloudy_windows") or [])],
        "khung nắng đẹp nhất": raw.get("best_sunny_time") or "—",
        "tóm tắt": raw.get("summary") or "",
    }


# ── Key maps for Group 2/4 (used by shape_labeled_dict / shape_ranking_output)

RESOLVE_LOCATION_KEYS = {
    "status": "trạng thái",
    "ward_id": "ward_id",
    "ward_name_vi": "phường/xã",
    "district_name_vi": "quận/huyện",
    "message": "ghi chú",
    "suggestions": "gợi ý",
}

WEATHER_ALERTS_KEYS = {
    "alerts": "cảnh báo",
    "count": "số lượng",
    "resolved_location": "địa điểm",
}

PHENOMENA_KEYS = {
    "phenomena": "hiện tượng",
    "has_dangerous": "có nguy hiểm",
    "weather_snapshot": "thời tiết hiện tại",
}

TEMP_TREND_KEYS = {
    "trend": "xu hướng",
    "slope_per_day": "thay đổi TB/ngày (°C)",
    "hottest_day": "ngày nóng nhất",
    "coldest_day": "ngày lạnh nhất",
    "daily_summary": "chi tiết theo ngày",
}

COMFORT_INDEX_KEYS = {
    "score": "điểm",
    "label": "mức độ",
    "recommendation": "khuyến nghị",
    "breakdown": "phân tích",
}

CHANGE_ALERT_KEYS = {
    "changes": "thay đổi",
    "has_significant_change": "có thay đổi đáng kể",
    "current_summary": "hiện trạng",
}

CLOTHING_ADVICE_KEYS = {
    "clothing_items": "trang phục đề xuất",
    "notes": "ghi chú",
    "temp": "nhiệt độ",
    "humidity": "độ ẩm",
    "pop": "xác suất mưa",
    "uvi": "UV",
    "wind_speed": "gió",
}

ACTIVITY_ADVICE_KEYS = {
    "advice": "khuyến nghị",
    "reason": "lý do",
    "recommendations": "gợi ý thêm",
}

DISTRICT_RANKING_METRIC_LABELS = {
    "avg_temp": "nhiệt độ TB",
    "temp": "nhiệt độ",
    "avg_humidity": "độ ẩm TB",
    "humidity": "độ ẩm",
    "total_rain": "tổng mưa (mm)",
    "rain_total": "tổng mưa (mm)",
    "avg_wind_speed": "gió TB (m/s)",
    "max_uvi": "UV đỉnh",
    "avg_pop": "xác suất mưa TB",
}


def build_resolve_location_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    return shape_labeled_dict(raw, RESOLVE_LOCATION_KEYS)


def build_weather_alerts_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    alerts = raw.get("alerts") or []
    fmt = []
    for a in alerts:
        if isinstance(a, Mapping):
            fmt.append({
                "loại": a.get("type") or a.get("severity") or "cảnh báo",
                "mô tả": a.get("description") or a.get("message") or "",
                "thời điểm": a.get("time_ict") or a.get("time") or "",
            })
        else:
            fmt.append({"mô tả": str(a)})
    # R11 Contract B: snapshot (alert data tại NOW)
    return {
        **_emit_snapshot_metadata(None, note="Cảnh báo được tra tại NOW. Không phải dự báo tương lai."),
        "cảnh báo": fmt,
        "số lượng": len(fmt),
    }


def build_detect_phenomena_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    # R11 Contract B: hiện tượng HN tính tại NOW (nồm ẩm / gió mùa / rét đậm)
    return {
        **_emit_snapshot_metadata(None, note="Hiện tượng đặc trưng HN tính tại NOW. User hỏi tương lai → gọi forecast tools."),
        **shape_labeled_dict(raw, PHENOMENA_KEYS),
    }


def build_temperature_trend_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    # R11 Contract A: trend có ngày cover (2-8 ngày), lấy từ daily_summary raw key
    details = raw.get("daily_summary") or raw.get("chi tiết theo ngày") or raw.get("daily_details") or raw.get("days") or []
    dates = [d.get("date") for d in details if isinstance(d, Mapping) and d.get("date")]
    return {
        **_emit_coverage_days(dates),
        # R15 T1.2: tool DAL chỉ SELECT date >= today → forward-only.
        # User dùng từ "tuần qua / mấy hôm trước" → output này KHÔNG cover.
        "⚠ scope": (
            "Phân tích này CHỈ cover ngày từ HÔM NAY trở đi (forecast forward-only). "
            "User hỏi 'tuần qua / mấy hôm trước / ngày qua / dạo trước' → KHÔNG dùng "
            "output này, PHẢI gọi get_weather_history thay. TUYỆT ĐỐI KHÔNG dán nhãn "
            "'X ngày qua' cho output này."
        ),
        **shape_labeled_dict(raw, TEMP_TREND_KEYS),
    }




def build_comfort_index_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    score = raw.get("score")
    result = {
        "điểm thoải mái": f"{score}/100" if score is not None else "—",
        "mức độ": raw.get("label") or "",
        "khuyến nghị": raw.get("recommendation") or "",
    }
    if isinstance(raw.get("breakdown"), Mapping):
        result["phân tích"] = raw["breakdown"]
    result["⚠ KHÔNG suy diễn"] = _ADVICE_NO_HALLUCINATE
    # R11 Contract B: comfort tính tại NOW
    return {**_emit_snapshot_metadata(None), **result}


def build_weather_change_alert_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    # R11 Contract B: alert đột biến 6-12h tới nhưng baseline là NOW
    return {
        **_emit_snapshot_metadata(None, note="Phát hiện đột biến 6-12h tới. Baseline là NOW."),
        **shape_labeled_dict(raw, CHANGE_ALERT_KEYS),
    }


def build_clothing_advice_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    # R11 Contract B: advice áp dụng tại NOW
    return {
        **_emit_snapshot_metadata(None, note="Lời khuyên trang phục áp dụng thời điểm hiện tại. User hỏi ngày khác → gọi forecast tool + clothing_advice lại."),
        "trang phục đề xuất": raw.get("clothing_items") or [],
        "ghi chú": raw.get("notes") or [],
        "⚠ KHÔNG suy diễn": _ADVICE_NO_HALLUCINATE,
    }


def build_activity_advice_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    # R11 Contract B: activity advice áp dụng tại NOW
    return {
        **_emit_snapshot_metadata(None, note="Khuyến nghị hoạt động áp dụng thời điểm hiện tại. Cuối tuần / ngày xa → gọi weather_period trước."),
        "khuyến nghị": raw.get("advice") or "",
        "lý do": raw.get("reason") or "",
        "gợi ý thêm": raw.get("recommendations") or [],
        "⚠ KHÔNG suy diễn": _ADVICE_NO_HALLUCINATE,
    }


def build_district_ranking_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    # R11 Contract B: xếp hạng quận tại NOW
    return {
        **_emit_snapshot_metadata(None, note="Xếp hạng quận tại NOW. KHÔNG dùng làm xếp hạng quá khứ/tương lai."),
        **shape_ranking_output(raw, "quận"),
    }


def build_ward_ranking_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    # R11 Contract B: xếp hạng phường tại NOW
    return {
        **_emit_snapshot_metadata(None, note="Xếp hạng phường tại NOW. KHÔNG dùng làm xếp hạng quá khứ/tương lai."),
        **shape_ranking_output(raw, "phường/xã"),
    }


def build_district_multi_compare_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if _is_error(raw):
        return build_error_output(raw)
    comparisons = raw.get("comparisons") or []
    units = raw.get("units_by_metric") or {}
    # comparisons có thể là dict (do merge by district) hoặc list raw
    if isinstance(comparisons, list):
        fmt: List[Dict[str, Any]] = []
        for c in comparisons:
            if not isinstance(c, Mapping):
                continue
            name = (c.get("district_name_vi") or c.get("district")
                    or c.get("name") or "")
            if not name:
                continue
            entry: Dict[str, Any] = {"quận": name}
            # R15 T1.1: lookup theo metric name (k) — tool đã store entry[metric] = value
            for k, vn in _METRIC_VN_LABEL.items():
                v = c.get(k)
                if v is None:
                    continue
                unit_disp = _UNIT_DISPLAY.get(units.get(k, ""), "")
                entry[vn] = f"{v:.1f}{unit_disp}" if isinstance(v, (int, float)) else str(v)
            if len(entry) > 1:  # giữ entry chỉ khi có ít nhất 1 metric value
                fmt.append(entry)
        if not fmt:
            # Defensive: tool gọi nhưng không lấy được metric nào → emit error rõ
            return {
                **_emit_snapshot_metadata(None, note="So sánh nhiều quận tại NOW."),
                "error": "no_metric_data",
                "⚠ ghi chú": (
                    "Tool không lấy được giá trị metric nào (DAL có thể empty hoặc "
                    "metrics không hợp lệ). TUYỆT ĐỐI KHÔNG bịa số liệu — refuse "
                    "với user hoặc gọi tool khác (compare_weather / get_district_ranking)."
                ),
                "metrics_attempted": list(units.keys()) or (raw.get("metrics_analyzed") or []),
            }
        # R11 Contract B: multi-compare tại NOW
        return {
            **_emit_snapshot_metadata(None, note="So sánh nhiều quận tại NOW."),
            "so sánh": fmt,
            "các chỉ số": raw.get("metrics_analyzed") or [],
            "tổng số quận": len(fmt),
        }
    return {
        **_emit_snapshot_metadata(None, note="So sánh nhiều quận tại NOW."),
        "so sánh": comparisons,
        "các chỉ số": raw.get("metrics_analyzed") or [],
    }
