"""Shared helpers + metadata emitters + generic shapers.

Extracted from output_builder.py in PR2.1 to isolate "kho helper" away from
the 30+ public builders. Behavior identical — every function is moved
verbatim, no logic change.

Builders import from here via `from app.agent.tools.output._common import *`.
output_builder.py keeps that import at the top so existing
`from app.agent.tools.output_builder import build_X` paths still work.
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


_ICT = ZoneInfo("Asia/Ho_Chi_Minh")

_WEEKDAYS_VI = {
    0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 3: "Thứ Năm",
    4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật",
}

_LEVEL_SUFFIX = {
    "ward": "phường/xã",
    "district": "quận",
    "city": "Hà Nội (toàn thành phố)",
}


# ── Shared helpers ──────────────────────────────────────────────────────────

def _as_date(v: Any) -> Optional[_date_cls]:
    if v is None:
        return None
    if isinstance(v, _date_cls) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                pass
    return None


def _format_date_vi(d: Any) -> str:
    dt = _as_date(d)
    if not dt:
        return str(d) if d is not None else ""
    return f"{dt.strftime('%d/%m/%Y')} ({_WEEKDAYS_VI[dt.weekday()]})"


def _format_dt_ict(v: Any) -> str:
    """Unix ts / ISO string / datetime → 'HH:MM Thứ X NGÀY/THÁNG/NĂM'."""
    if v is None:
        return ""
    dt: Optional[datetime] = None
    if isinstance(v, datetime):
        dt = v.astimezone(_ICT) if v.tzinfo else v.replace(tzinfo=_ICT)
    elif isinstance(v, (int, float)):
        dt = datetime.fromtimestamp(float(v), tz=_ICT)
    elif isinstance(v, str):
        raw = v.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
            dt = parsed.astimezone(_ICT) if parsed.tzinfo else parsed.replace(tzinfo=_ICT)
        except ValueError:
            return v
    if not dt:
        return str(v)
    return f"{dt.strftime('%H:%M')} {_WEEKDAYS_VI[dt.weekday()]} {dt.strftime('%d/%m/%Y')}"


def _format_hour_short(v: Any) -> str:
    """Unix ts / ISO → 'HH:MM NGÀY/THÁNG'."""
    if v is None:
        return ""
    dt: Optional[datetime] = None
    if isinstance(v, datetime):
        dt = v.astimezone(_ICT) if v.tzinfo else v.replace(tzinfo=_ICT)
    elif isinstance(v, (int, float)):
        dt = datetime.fromtimestamp(float(v), tz=_ICT)
    elif isinstance(v, str):
        # Already formatted like "HH:MM (ICT)" → keep as-is
        if "(ICT)" in v or ":" in v and len(v) <= 12:
            return v
        raw = v.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
            dt = parsed.astimezone(_ICT) if parsed.tzinfo else parsed.replace(tzinfo=_ICT)
        except ValueError:
            return v
    if not dt:
        return str(v)
    return f"{dt.strftime('%H:%M')} {dt.strftime('%d/%m')}"


def _format_time_only(v: Any) -> str:
    """Unix ts / ISO → 'HH:MM'."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        dt = v.astimezone(_ICT) if v.tzinfo else v.replace(tzinfo=_ICT)
        return dt.strftime("%H:%M")
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), tz=_ICT).strftime("%H:%M")
    if isinstance(v, str):
        if ":" in v and len(v) <= 12:
            return v.split(" ")[0]  # "HH:MM (ICT)" → "HH:MM"
        raw = v.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
            dt = parsed.astimezone(_ICT) if parsed.tzinfo else parsed.replace(tzinfo=_ICT)
            return dt.strftime("%H:%M")
        except ValueError:
            return v
    return str(v)


def _format_location(
    resolved: Optional[Mapping[str, Any]],
    level: Optional[str],
    fallback_name: Optional[str] = None,
) -> str:
    """Tên địa điểm + cấp độ."""
    if not resolved:
        resolved = {}
    ward = resolved.get("ward_name_vi")
    district = resolved.get("district_name_vi")
    city = resolved.get("city_name") or "Hà Nội"
    if level == "ward" and ward:
        parts = [ward]
        if district:
            parts.append(f"{district}, {city}")
        return " — ".join(parts)
    if level == "district" and district:
        return f"{district} (quận/huyện)"
    if level == "city":
        return f"{city} (toàn thành phố)"
    return fallback_name or ward or district or city or "Hà Nội"


def _wind_text(speed: Optional[float], gust: Optional[float], deg: Optional[float]) -> str:
    """Combined 'Gió vừa cấp 4 (5.5 m/s), giật 9.4 m/s, hướng Nam'."""
    parts: List[str] = []
    if speed is not None:
        bf = wind_speed_to_beaufort(speed)
        label = wind_beaufort_vietnamese(bf)
        parts.append(f"{label} cấp {bf} ({speed:.1f} m/s)")
    if gust is not None and (speed is None or gust > speed + 0.5):
        parts.append(f"giật {gust:.1f} m/s")
    if deg is not None:
        parts.append(f"hướng {wind_deg_to_vietnamese(int(deg))}")
    return ", ".join(parts) if parts else "Không xác định"


def _wind_gust_only(gust: Optional[float], deg: Optional[float]) -> str:
    """Cho history daily: chỉ có wind_gust, không bịa avg."""
    parts: List[str] = []
    if gust is not None:
        parts.append(f"Giật {gust:.1f} m/s")
    if deg is not None:
        parts.append(f"hướng {wind_deg_to_vietnamese(int(deg))}")
    return ", ".join(parts) if parts else "Không xác định"


def _add_conditional_comfort(result: Dict[str, Any], temp: Optional[float],
                             humidity: Optional[float], wind_ms: Optional[float]) -> None:
    """Thêm 'cảm giác nóng'/'cảm giác lạnh' CHỈ khi ngưỡng trigger."""
    if temp is not None and humidity is not None and temp >= 27 and humidity >= 40:
        hi = compute_heat_index(temp, int(humidity))
        if hi and hi["level"] != "An toàn":
            result["cảm giác nóng"] = f"{hi['level']} {hi['heat_index']:.1f}°C"
    if temp is not None and wind_ms is not None and temp <= 10 and wind_ms >= 1.3:
        wc = compute_wind_chill(temp, wind_ms)
        if wc:
            result["cảm giác lạnh"] = f"{wc['level']} {wc['wind_chill']:.1f}°C"


def _add_visibility(result: Dict[str, Any], vis_m: Optional[float]) -> None:
    """Thêm key tầm nhìn khi có data, gắn nhãn theo ngưỡng để LLM copy thẳng (B.1).

    Trước đây chỉ show khi <5km, dẫn tới user hỏi tầm nhìn lúc trời quang
    không thấy field → bot suy diễn từ độ ẩm/mây (v12 ID 12). Giờ luôn show
    để bot có data ground truth.
    """
    if vis_m is not None and vis_m > 0:
        km = vis_m / 1000
        if km < 1:
            label = "Kém"
        elif km < 3:
            label = "Hạn chế"
        elif km < 5:
            label = "Trung bình"
        else:
            label = "Tốt"
        result["tầm nhìn"] = f"{label} {km:.1f} km"


def _pick_temp(raw: Mapping[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = raw.get(k)
        if v is not None:
            return float(v)
    return None


def _narrative_current(raw: Mapping[str, Any], location_name: str,
                       temp: Optional[float], clouds: Optional[float],
                       pop_pct: Optional[float], rain_1h: Optional[float]) -> str:
    bits: List[str] = []
    time_str = _format_time_only(raw.get("time_ict") or raw.get("ts_utc"))
    if time_str:
        bits.append(f"Lúc {time_str}")
    bits.append(f"tại {location_name}")
    wm = weather_main_to_vietnamese(raw.get("weather_main") or "")
    if wm:
        bits.append(wm.lower())
    if temp is not None:
        bits.append(f"nhiệt độ {temp:.1f}°C")
    if rain_1h and rain_1h >= 0.1:
        bits.append(f"đang {label_rain_intensity(rain_1h).lower()}")
    elif pop_pct is not None and pop_pct >= 40:
        bits.append(f"xác suất mưa {int(round(pop_pct))}%")
    if clouds is not None:
        bits.append(f"mây {int(round(clouds))}%")
    text = ", ".join(bits)
    return (text[:1].upper() + text[1:] + ".") if text else ""


# ── Error ───────────────────────────────────────────────────────────────────

def build_error_output(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Chuẩn hoá {error, message, note?, suggestion?} → flat VN."""
    result: Dict[str, Any] = {
        "lỗi": raw.get("message") or raw.get("error") or "Không có dữ liệu",
    }
    if raw.get("note"):
        result["ghi chú"] = raw["note"]
    if raw.get("suggestion"):
        result["gợi ý"] = raw["suggestion"]
    if raw.get("data_stale"):
        result["ghi chú"] = (result.get("ghi chú") or "") + " Dữ liệu có thể cũ."
    return result


def _is_error(raw: Any) -> bool:
    return isinstance(raw, Mapping) and (raw.get("error") or raw.get("status") == "error")


def _detect_forecast_range_gap(
    forecasts: Sequence[Mapping[str, Any]],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """R11 Contract A: emit grounding metadata + past-frame warning cho temporal-window tools.

    Trả dict với các key (order intentionally front-loaded):
    - "ngày cover": list ["DD/MM/YYYY (Thứ X)"] — machine-checkable grounding (R11 L1).
    - "phạm vi thực tế": "từ HH:MM Thứ X DD/MM đến HH:MM Thứ Y DD/MM" (R10 — GIỮ backward compat).
    - "trong phạm vi": bool True khi có data (R11 L1).
    - "⚠ lưu ý khung đã qua": cảnh báo past-frame nếu data không cover khung
      sáng/trưa/chiều/tối HÔM NAY đã qua (R10 — GIỮ).

    Lý do past-frame: tool hourly/rain_timeline chỉ trả forecast TỪ NOW. Khi NOW=22:14 tối,
    các khung "chiều/trưa/sáng nay" (13-18h / 11-13h / 6-11h) ĐÃ QUA hoàn toàn.
    Bot thường lấy data tương lai (23:00+ hoặc ngày mai) rồi dán nhãn khung đã
    qua → sai nghiêm trọng (audit v8 B1, 15 IDs).

    Args:
        forecasts: list forecast entries (có ts_utc).
        now: optional datetime override để test. Mặc định datetime.now(ICT).
    """
    result: Dict[str, Any] = {}
    if not forecasts:
        return result

    def _dt_of(entry: Mapping[str, Any]) -> Optional[datetime]:
        ts = entry.get("ts_utc")
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=_ICT)
        return None

    first_dt = _dt_of(forecasts[0])
    last_dt = _dt_of(forecasts[-1])
    if first_dt is None or last_dt is None:
        return result

    # R11 Contract A: "ngày cover" — list ISO dates với weekday (machine-checkable).
    dates_covered: List[str] = []
    seen_dates = set()
    for entry in forecasts:
        dt_e = _dt_of(entry)
        if dt_e is None:
            continue
        d_iso = dt_e.date().isoformat()
        if d_iso in seen_dates:
            continue
        seen_dates.add(d_iso)
        dates_covered.append(f"{dt_e.strftime('%d/%m/%Y')} ({_WEEKDAYS_VI[dt_e.weekday()]})")
    if dates_covered:
        result["ngày cover"] = dates_covered

    # R10 key — giữ nguyên (backward compat 6 test R10).
    result["phạm vi thực tế"] = (
        f"từ {first_dt.strftime('%H:%M')} {_WEEKDAYS_VI[first_dt.weekday()]} "
        f"{first_dt.strftime('%d/%m/%Y')} đến {last_dt.strftime('%H:%M')} "
        f"{_WEEKDAYS_VI[last_dt.weekday()]} {last_dt.strftime('%d/%m/%Y')}"
    )
    # R11 Contract A: bool rõ ràng — LLM đọc nhanh.
    result["trong phạm vi"] = True

    now = now or datetime.now(_ICT)
    today = now.date()
    # Data có cover khung "quá khứ trong hôm nay" không?
    # Nếu first_dt > NOW (data chỉ forecast tương lai) → các khung đã qua KHÔNG cover.
    data_covers_today_past = first_dt.date() < today or (
        first_dt.date() == today and first_dt.hour <= now.hour
    )

    if data_covers_today_past:
        return result  # Data cover được → không cần warn

    # Liệt kê khung đã qua so với NOW (dựa giờ)
    past_frames: List[str] = []
    if now.hour >= 12:
        past_frames.append("sáng nay (6-11h)")
    if now.hour >= 14:
        past_frames.append("trưa nay (11-13h)")
    if now.hour >= 19:
        past_frames.append("chiều nay (13-18h)")
    if now.hour >= 23:
        past_frames.append("tối nay (18-22h)")

    if past_frames:
        result["⚠ lưu ý khung đã qua"] = (
            f"NOW={now.strftime('%H:%M %d/%m')}. Data forecast chỉ bắt đầu từ "
            f"{first_dt.strftime('%H:%M %d/%m')}. Các khung HÔM NAY đã qua: "
            f"{', '.join(past_frames)}. TOOL NÀY KHÔNG COVER khung đã qua — "
            f"nếu user hỏi về các khung đó → BÁO RÕ 'khung [X] hôm nay đã qua "
            f"(hiện là {now.strftime('%H:%M')})', TUYỆT ĐỐI KHÔNG dùng data "
            f"ngày mai dán nhãn khung hôm nay."
        )
    return result


def _emit_coverage_days(dates: Sequence[Any]) -> Dict[str, Any]:
    """R11 Contract A (variant cho daily tools): emit `ngày cover` + `trong phạm vi`.

    Dùng khi builder có sẵn list dates (không phải forecast entries với ts_utc).
    Ví dụ: build_daily_forecast, build_weather_period, build_daily_rhythm.

    Args:
        dates: list date/string/datetime — được normalize qua `_as_date`.

    Returns:
        dict có `"ngày cover"` (list "DD/MM/YYYY (Thứ X)") và `"trong phạm vi"` (bool).
    """
    result: Dict[str, Any] = {}
    covered: List[str] = []
    seen = set()
    for d in dates:
        dd = _as_date(d)
        if dd is None:
            continue
        iso = dd.isoformat()
        if iso in seen:
            continue
        seen.add(iso)
        covered.append(f"{dd.strftime('%d/%m/%Y')} ({_WEEKDAYS_VI[dd.weekday()]})")
    if covered:
        result["ngày cover"] = covered
        result["trong phạm vi"] = True
    return result


def _emit_snapshot_metadata(
    ts_or_dt: Any, now: Optional[datetime] = None, note: Optional[str] = None
) -> Dict[str, Any]:
    """R11 Contract B + R14 E.2: emit snapshot metadata cho tools single-point.

    Trả:
    - "áp dụng cho": formatted timestamp "HH:MM Thứ X DD/MM/YYYY".
    - "⚠ snapshot": True — LLM không dán cho future/past khung.
    - "⚠ KHÔNG dùng cho" (R14 E.2): structured list các khung cấm + tool thay thế.
      LLM thấy key này KHÓ bỏ qua hơn note prose (v12 IDs 103, 113, 123, 150 fail vì ignore prose).
    - "⚠ ghi chú snapshot": note chi tiết (backward compat với tests).

    Args:
        ts_or_dt: unix ts / ISO string / datetime.
        now: fallback nếu ts_or_dt None (dùng cho advice tools không có timestamp).
        note: custom warning note. Default = snapshot rejection default.
    """
    result: Dict[str, Any] = {}
    when = _format_dt_ict(ts_or_dt) if ts_or_dt is not None else None
    if not when:
        fallback = now or datetime.now(_ICT)
        when = _format_dt_ict(fallback)
    if when:
        result["áp dụng cho"] = when
    result["⚠ snapshot"] = True
    result["⚠ KHÔNG dùng cho"] = (
        "tối nay / ngày mai / cuối tuần / mấy ngày tới — "
        "gọi get_hourly_forecast (≤48h) hoặc get_daily_forecast (≤8 ngày) THAY THẾ."
    )
    result["⚠ ghi chú snapshot"] = note or (
        "Đây là SNAPSHOT tại thời điểm trên. KHÔNG dán số/nhãn này làm 'chiều/tối/mai/cuối tuần'. "
        "User hỏi khung tương lai → gọi hourly/daily forecast."
    )
    return result


def _emit_historical_metadata(loai: str, note: Optional[str] = None) -> Dict[str, Any]:
    """R11 Contract C: emit historical/aggregate metadata cho tools past-only hoặc tổng hợp.

    Trả:
    - "loại dữ liệu": "quá khứ" | "tổng hợp cả ngày" | "so sánh past".
    - "⚠ không phải hiện tại": True — LLM không dùng cho câu hỏi "bây giờ".

    Args:
        loai: "quá khứ" | "tổng hợp cả ngày" | "so sánh past".
        note: custom warning note.
    """
    result: Dict[str, Any] = {
        "loại dữ liệu": loai,
        "⚠ không phải hiện tại": True,
    }
    result["⚠ ghi chú loại dữ liệu"] = note or (
        f"Đây là {loai}, KHÔNG phải tức thời. User hỏi 'bây giờ / hiện tại' → "
        f"dùng get_current_weather thay."
    )
    return result


def _emit_missing_fields(
    raw: Mapping[str, Any],
    expected_topics: Sequence[tuple],
) -> Dict[str, Any]:
    """R13 Contract D: emit `⚠ không có dữ liệu` key cho fields absent.

    Forces LLM to say "Dữ liệu chưa có X" thay vì suy diễn X từ độ ẩm/mây/etc.
    Same category với R11 L1 Contract A/B/C — additive metadata emission.

    Args:
        raw: dict thô từ DAL (để check key presence).
        expected_topics: list[(topic_vi, key_en)]. Mỗi tuple khai báo 1 topic
            user có thể hỏi (vd "tầm nhìn") và key raw dict tương ứng (vd "visibility").
            Nếu raw không có key_en OR value là None/empty → topic vào missing list.

    Returns:
        dict có `"⚠ không có dữ liệu"` = ["topic1", "topic2"] nếu CÓ missing,
        empty dict nếu tất cả topics đều có data.

    Example:
        _emit_missing_fields(raw, [("tầm nhìn", "visibility"), ("sương mù", "fog")])
        # Nếu raw không có key "visibility" và "fog":
        # → {"⚠ không có dữ liệu": ["tầm nhìn", "sương mù"]}
    """
    missing: List[str] = []
    for topic_vi, key_en in expected_topics:
        value = raw.get(key_en)
        # Absent if key missing, None, or empty string/list
        if value is None or value == "" or value == []:
            missing.append(topic_vi)
    if not missing:
        return {}
    return {
        "⚠ không có dữ liệu": missing,
        "⚠ ghi chú trường thiếu": (
            f"Output KHÔNG có field: {', '.join(missing)}. Nếu user hỏi về "
            f"{'/'.join(missing)} → TRẢ LỜI RÕ 'Dữ liệu chưa có', TUYỆT ĐỐI KHÔNG "
            f"suy diễn từ độ ẩm/mây/nhiệt/điểm sương."
        ),
    }


# ── Group 2: generic shape_labeled_dict ─────────────────────────────────────

def shape_labeled_dict(raw: Mapping[str, Any],
                       key_map: Mapping[str, str],
                       extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Rename raw keys → VN keys. Keep values as-is (assume already labeled or simple).

    Args:
        raw: input dict
        key_map: {raw_key: vn_key} — keys not in map are dropped
        extra: optional dict merged into result

    Error handling: if raw has 'error', return build_error_output.
    """
    if _is_error(raw):
        return build_error_output(raw)
    result: Dict[str, Any] = {}
    for raw_key, vn_key in key_map.items():
        if raw_key in raw:
            v = raw[raw_key]
            if v is not None:
                result[vn_key] = v
    if extra:
        result.update(extra)
    return result


# ── Group 4: generic ranking output ─────────────────────────────────────────

_METRIC_VN_LABEL = {
    "nhiet_do": "nhiệt độ", "do_am": "độ ẩm", "gio": "gió",
    "mua": "lượng mưa", "uvi": "UV", "ap_suat": "áp suất",
    "diem_suong": "điểm sương", "may": "mây",
}

_UNIT_DISPLAY = {"C": "°C", "%": "%", "m/s": " m/s", "hPa": " hPa", "": ""}


def shape_ranking_output(raw: Mapping[str, Any],
                         location_vn_key: str) -> Dict[str, Any]:
    """Rankings list → flat VN per-entry.

    DAL trả: {metric, unit, order, rankings: [{rank, district|ward, value, unit}]}
    """
    if _is_error(raw):
        return build_error_output(raw)
    rankings = raw.get("rankings") or []
    metric = raw.get("metric") or ""
    unit = raw.get("unit") or ""
    metric_vn = _METRIC_VN_LABEL.get(metric, metric)
    order_vn = "cao nhất" if raw.get("order") == "cao_nhat" else "thấp nhất"

    entries: List[Dict[str, Any]] = []
    for r in rankings:
        # DAL dùng keys "district" / "ward" — không phải district_name_vi
        name = (r.get("district") or r.get("ward")
                or r.get("district_name_vi") or r.get("ward_name_vi")
                or r.get("name") or "")
        if not name:
            continue  # Skip empty (bug defensive)
        value = r.get("value")
        entry: Dict[str, Any] = {
            "hạng": r.get("rank") or len(entries) + 1,
            location_vn_key: name,
        }
        if value is not None:
            unit_disp = _UNIT_DISPLAY.get(unit, f" {unit}" if unit else "")
            if isinstance(value, float):
                entry[metric_vn] = f"{value:.1f}{unit_disp}"
            else:
                entry[metric_vn] = f"{value}{unit_disp}"
        entries.append(entry)

    return {
        "chỉ số": metric_vn,
        "thứ tự": order_vn,
        "xếp hạng": entries,
        "tổng số": len(entries),
    }


# ── Group 3: window/list builders (insight_advanced) ────────────────────────

def _fmt_window(w: Mapping[str, Any]) -> Dict[str, Any]:
    """Common window format."""
    out: Dict[str, Any] = {}
    if w.get("start"):
        out["bắt đầu"] = w["start"]
    if w.get("end"):
        out["kết thúc"] = w["end"]
    if w.get("time") or w.get("time_ict"):
        out["thời điểm"] = w.get("time") or w["time_ict"]
    if w.get("duration_hours") is not None:
        out["thời lượng"] = f"{w['duration_hours']} giờ"
    return out


_ADVICE_NO_HALLUCINATE = (
    "⚠ KHÔNG suy diễn ngoài output: CHỈ dùng các field có trong output này. "
    "TUYỆT ĐỐI KHÔNG thêm nhãn hiện tượng (mưa phùn, sương mù, đợt lạnh mạnh, "
    "nắng đẹp, nồm ẩm...) không có trong recommendations/ghi chú. "
    "Nếu user hỏi chi tiết mưa/UV/giờ cụ thể → gọi tool tương ứng "
    "(get_rain_timeline / get_uv_safe_windows / get_hourly_forecast) để lấy data."
)
