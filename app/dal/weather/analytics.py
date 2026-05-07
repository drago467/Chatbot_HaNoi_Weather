"""DAL module split from weather_dal.py in PR2.2 — behavior identical.

All function bodies are moved verbatim. The legacy `app.dal.weather_dal`
module re-exports everything via `from app.dal.weather import *` so existing
import paths still work.
"""

from typing import List, Dict, Any, Optional

from app.config.constants import FORECAST_MAX_DAYS, FORECAST_MAX_HOURS
from app.dal.timezone_utils import format_ict, to_ict
from app.db.dal import query, query_one
# analytics.py uses functions from current/forecast modules.
from app.dal.weather.current import get_current_weather
from app.dal.weather.forecast import get_hourly_forecast


def analyze_rain_from_forecasts(rows: list, hours: int = 24, source_note: str = "") -> Dict[str, Any]:
    """Analyze rain periods from forecast data (reusable for ward/district/city).

    Supports both ward-level (pop, rain_1h) and aggregate (avg_pop, avg_rain_1h) keys.

    Args:
        rows: List of forecast dicts with ts_utc + pop/avg_pop + rain_1h/avg_rain_1h + weather_main
        hours: Number of hours scanned (for metadata)
        source_note: Optional note about data source level

    Returns:
        Dict with rain_periods, next_rain, next_clear, hours_scanned, data_coverage
    """
    if not rows:
        return {"error": "no_data", "message": "Không có dữ liệu dự báo",
                "suggestion": "Thử hỏi thời tiết hiện tại hoặc dự báo ngắn hạn"}

    from app.dal.timezone_utils import format_ict

    rain_keywords = {"Rain", "Drizzle", "Thunderstorm"}
    periods = []
    current_period = None

    for row in rows:
        # Support both ward-level keys (pop, rain_1h) and aggregate keys (avg_pop, avg_rain_1h)
        pop = row.get("pop") or row.get("avg_pop") or 0
        rain_1h = row.get("rain_1h") or row.get("avg_rain_1h") or 0
        wm = row.get("weather_main", "")
        is_rain = pop >= 0.3 or wm in rain_keywords or rain_1h > 0

        ts = row["ts_utc"]
        if is_rain and current_period is None:
            current_period = {"start": ts, "end": ts, "max_pop": pop, "max_rain_1h": rain_1h}
        elif is_rain and current_period is not None:
            current_period["end"] = ts
            current_period["max_pop"] = max(current_period["max_pop"], pop)
            current_period["max_rain_1h"] = max(current_period["max_rain_1h"], rain_1h)
        elif not is_rain and current_period is not None:
            periods.append(current_period)
            current_period = None

    if current_period is not None:
        periods.append(current_period)

    # Format periods
    formatted = []
    for p in periods:
        formatted.append({
            "start": format_ict(p["start"]),
            "end": format_ict(p["end"]),
            "max_pop": round(p["max_pop"] * 100),
            "max_rain_1h": round(p["max_rain_1h"], 1),
        })

    # Next rain / next clear
    first_rain = format_ict(periods[0]["start"]) if periods else None
    first_clear = None
    if periods:
        last_rain_end = periods[0]["end"]
        for row in rows:
            if row["ts_utc"] > last_rain_end:
                pop = row.get("pop") or row.get("avg_pop") or 0
                wm = row.get("weather_main", "")
                if pop < 0.3 and wm not in rain_keywords:
                    first_clear = format_ict(row["ts_utc"])
                    break

    result = {
        "rain_periods": formatted,
        "total_rain_periods": len(formatted),
        "next_rain": first_rain,
        "next_clear": first_clear,
        "hours_scanned": len(rows),
        "data_coverage": f"Dự báo {len(rows)} giờ tới",
    }
    if source_note:
        result["source_note"] = source_note
    return result

def get_rain_timeline(ward_id: str, hours: int = 24) -> Dict[str, Any]:
    """Scan hourly forecast to detect rain start/stop transitions.

    Returns rain periods, next rain time, next clear time.
    """
    rows = query("""
        SELECT ts_utc, pop, rain_1h, weather_main
        FROM fact_weather_hourly
        WHERE ward_id = %s
          AND data_kind = 'forecast'
          AND ts_utc > NOW()
        ORDER BY ts_utc
        LIMIT %s
    """, (ward_id, min(hours, FORECAST_MAX_HOURS)))

    return analyze_rain_from_forecasts(rows, hours)

def get_temperature_trend(ward_id: str, days: int = 7) -> Dict[str, Any]:
    """Analyze daily forecast to detect warming/cooling trend."""
    rows = query("""
        SELECT date, temp_min, temp_max, temp_avg, weather_main
        FROM fact_weather_daily
        WHERE ward_id = %s
          AND data_kind = 'forecast'
          AND date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
        ORDER BY date
        LIMIT %s
    """, (ward_id, min(days, FORECAST_MAX_DAYS)))

    if len(rows) < 2:
        return {"error": "no_data", "message": "Không đủ dữ liệu để phân tích xu hướng"}

    temps = [r["temp_avg"] for r in rows if r.get("temp_avg") is not None]
    if len(temps) < 2:
        return {"error": "no_data", "message": "Không đủ dữ liệu nhiệt độ"}

    # Simple linear trend: slope = (last - first) / n
    slope = (temps[-1] - temps[0]) / (len(temps) - 1)

    if slope > 0.5:
        trend = "warming"
        trend_vi = "Ấm dần lên"
    elif slope < -0.5:
        trend = "cooling"
        trend_vi = "Lạnh dần"
    else:
        trend = "stable"
        trend_vi = "Ổn định"

    # Find inflection point (day when trend reverses)
    inflection = None
    for i in range(1, len(temps) - 1):
        prev_diff = temps[i] - temps[i - 1]
        next_diff = temps[i + 1] - temps[i]
        if (prev_diff > 0 and next_diff < -0.5) or (prev_diff < 0 and next_diff > 0.5):
            inflection = str(rows[i]["date"])
            break

    # Find hottest and coldest days
    max_row = max(rows, key=lambda r: r.get("temp_max") or 0)
    min_row = min(rows, key=lambda r: r.get("temp_min") or 999)

    return {
        "trend": trend,
        "trend_vi": trend_vi,
        "slope_per_day": round(slope, 1),
        "days_analyzed": len(rows),
        "inflection_date": inflection,
        "hottest_day": {"date": str(max_row["date"]), "temp_max": max_row.get("temp_max")},
        "coldest_day": {"date": str(min_row["date"]), "temp_min": min_row.get("temp_min")},
        "daily_summary": [
            {"date": str(r["date"]), "min": r.get("temp_min"), "max": r.get("temp_max"),
             "avg": r.get("temp_avg"), "weather": r.get("weather_main")}
            for r in rows
        ],
    }

def detect_weather_changes(ward_id: str, hours: int = 6) -> Dict[str, Any]:
    """Detect significant weather changes in the next few hours.

    Compares current weather with forecast to find:
    - Temperature drop/rise > 5°C
    - Rain probability jump > 50%
    - Wind speed increase > 5 m/s
    - Weather condition change (clear → rain, etc.)

    Args:
        ward_id: Ward ID
        hours: Hours ahead to scan (default 6)

    Returns:
        Dictionary with detected changes and timing
    """
    current = get_current_weather(ward_id)
    if "error" in current:
        return current

    forecasts = get_hourly_forecast(ward_id, hours=min(hours, 12))
    if not forecasts:
        return {"error": "no_data", "message": "Không có dữ liệu dự báo"}

    changes = []
    cur_temp = current.get("temp")
    cur_pop = current.get("pop") or 0
    cur_wind = current.get("wind_speed") or 0
    cur_weather = current.get("weather_main", "")

    rain_keywords = {"Rain", "Drizzle", "Thunderstorm"}
    cur_is_rain = cur_weather in rain_keywords

    for f in forecasts:
        f_temp = f.get("temp")
        f_pop = f.get("pop") or 0
        f_wind = f.get("wind_speed") or 0
        f_weather = f.get("weather_main", "")
        f_time = format_ict(f.get("ts_utc"))
        f_is_rain = f_weather in rain_keywords

        # Temperature change > 5°C
        if cur_temp is not None and f_temp is not None:
            temp_diff = f_temp - cur_temp
            if abs(temp_diff) >= 5:
                direction = "tăng" if temp_diff > 0 else "giảm"
                changes.append({
                    "type": "temperature",
                    "description": f"Nhiệt độ {direction} {abs(temp_diff):.1f}°C ({cur_temp:.1f}→{f_temp:.1f}°C)",
                    "time": f_time,
                    "severity": "high" if abs(temp_diff) >= 8 else "medium"
                })
                break  # Only report first significant temp change

        # Rain probability jump
        if f_pop - cur_pop >= 0.5:
            changes.append({
                "type": "rain_start",
                "description": f"Khả năng mưa tăng mạnh ({cur_pop*100:.0f}%→{f_pop*100:.0f}%)",
                "time": f_time,
                "severity": "high" if f_pop >= 0.8 else "medium"
            })
            break

        # Weather condition change: clear → rain
        if not cur_is_rain and f_is_rain:
            changes.append({
                "type": "weather_change",
                "description": f"Trời chuyển mưa ({cur_weather}→{f_weather})",
                "time": f_time,
                "severity": "high" if f_weather == "Thunderstorm" else "medium"
            })
            break

        # Rain → clear
        if cur_is_rain and not f_is_rain and f_pop < 0.3:
            changes.append({
                "type": "rain_stop",
                "description": f"Mưa có thể tạnh",
                "time": f_time,
                "severity": "low"
            })
            break

        # Wind increase > 5 m/s
        if f_wind - cur_wind >= 5:
            changes.append({
                "type": "wind_increase",
                "description": f"Gió mạnh lên ({cur_wind:.1f}→{f_wind:.1f} m/s)",
                "time": f_time,
                "severity": "high" if f_wind >= 15 else "medium"
            })
            break

    return {
        "changes": changes,
        "has_significant_change": len(changes) > 0,
        "hours_scanned": len(forecasts),
        "current_summary": {
            "temp": cur_temp,
            "weather_main": cur_weather,
            "wind_speed": cur_wind,
            "pop": cur_pop
        }
    }

