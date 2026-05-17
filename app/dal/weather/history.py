"""DAL module split from weather_dal.py in PR2.2 — behavior identical.

All function bodies are moved verbatim. The legacy `app.dal.weather_dal`
module re-exports everything via `from app.dal.weather import *` so existing
import paths still work.
"""

from typing import List, Dict, Any, Optional

from app.config.constants import FORECAST_MAX_DAYS, FORECAST_MAX_HOURS
from app.dal.timezone_utils import format_ict, to_ict
from app.db.dal import query, query_one
from app.dal.weather_helpers import wind_deg_to_vietnamese


def get_weather_history(ward_id: str, date: str) -> Dict[str, Any]:
    """Get weather for a specific date in the past.

    Queries fact_weather_hourly with data_kind='history' first.
    Falls back to fact_weather_daily if no hourly history available.

    Args:
        ward_id: Ward ID
        date: Date in YYYY-MM-DD format

    Returns:
        Dictionary with historical weather data or error
    """
    result = query_one("""
        SELECT temp, feels_like, humidity, dew_point, wind_speed, wind_deg,
               weather_main, weather_description, ts_utc
        FROM fact_weather_hourly
        WHERE ward_id = %s
          AND data_kind = 'history'
          AND (ts_utc AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = %s::date
        ORDER BY ABS(EXTRACT(HOUR FROM ts_utc AT TIME ZONE 'Asia/Ho_Chi_Minh') - 12)
        LIMIT 1
    """, (ward_id, date))

    if result:
        result["wind_direction_vi"] = wind_deg_to_vietnamese(result.get("wind_deg"))
        result["note"] = "Dữ liệu lúc 12:00 trưa"

    # Bổ sung daily summary (temp_min/max, rain_total, sunrise/sunset)
    daily = query_one(
        "SELECT temp_min, temp_max, temp_avg, humidity AS daily_humidity, "
        "rain_total, uvi, weather_main AS daily_weather_main, "
        "weather_description AS daily_weather_desc, sunrise, sunset "
        "FROM fact_weather_daily WHERE ward_id = %s AND date = %s::date",
        (ward_id, date)
    )

    if result and daily:
        result["daily_summary"] = daily
        result["note"] = "Dữ liệu trưa 12:00 + tổng hợp ngày"
        return result

    if result:
        return result

    # Fallback: use daily data only when no hourly history
    if daily:
        return {
            "temp": daily.get("temp_avg"),
            "temp_min": daily.get("temp_min"),
            "temp_max": daily.get("temp_max"),
            "humidity": daily.get("daily_humidity"),
            "rain_total": daily.get("rain_total"),
            "uvi": daily.get("uvi"),
            "weather_main": daily.get("daily_weather_main"),
            "weather_description": daily.get("daily_weather_desc"),
            "sunrise": daily.get("sunrise"),
            "sunset": daily.get("sunset"),
            "note": "Dữ liệu tổng hợp ngày (không có chi tiết theo giờ)",
            "source": "daily_summary"
        }

    return {
        "error": "no_data",
        "message": f"Không có dữ liệu thời tiết ngày {date}",
        "note": "Dữ liệu lịch sử chỉ lưu trữ 14 ngày gần nhất",
        "suggestion": "Thử hỏi ngày gần hơn hoặc dùng dự báo cho ngày tới"
    }

def get_city_weather_history(date: str) -> Dict[str, Any]:
    """Get historical weather from fact_weather_city_daily."""
    row = query_one("""
        SELECT avg_temp, temp_min, temp_max, avg_humidity, avg_pop, total_rain,
               weather_main, avg_dew_point, avg_pressure, avg_clouds,
               max_uvi, avg_wind_deg, max_wind_gust, ward_count
        FROM fact_weather_city_daily
        WHERE date = %s::date
    """, (date,))
    if not row:
        return {"error": "no_data",
                "message": f"Không có dữ liệu lịch sử thành phố ngày {date}",
                "note": "Dữ liệu lịch sử chỉ lưu trữ 14 ngày gần nhất",
                "suggestion": "Thử hỏi ngày gần hơn hoặc dùng dự báo cho ngày tới"}
    row["level"] = "city"
    row["date"] = date
    row["data_coverage"] = f"Dữ liệu ngày {date} (tổng hợp toàn Hà Nội)"
    row["wind_direction_vi"] = wind_deg_to_vietnamese(row.get("avg_wind_deg"))
    return row

def get_district_weather_history(district_id: int, date: str) -> Dict[str, Any]:
    """Get historical weather from fact_weather_district_daily."""
    row = query_one("""
        SELECT fwd.district_id, dd.district_name_vi,
               fwd.avg_temp, fwd.temp_min, fwd.temp_max, fwd.avg_humidity,
               fwd.avg_pop, fwd.total_rain,
               fwd.weather_main, fwd.avg_dew_point, fwd.avg_pressure, fwd.avg_clouds,
               fwd.max_uvi, fwd.avg_wind_deg, fwd.max_wind_gust, fwd.ward_count
        FROM fact_weather_district_daily fwd
        JOIN dim_district dd ON fwd.district_id = dd.district_id
        WHERE fwd.district_id = %s AND fwd.date = %s::date
    """, (district_id, date))
    if not row:
        return {"error": "no_data",
                "message": f"Không có dữ liệu lịch sử quận (district_id={district_id}) ngày {date}",
                "note": "Dữ liệu lịch sử chỉ lưu trữ 14 ngày gần nhất",
                "suggestion": "Thử hỏi ngày gần hơn hoặc dùng dự báo cho ngày tới"}
    row["level"] = "district"
    row["date"] = date
    row["data_coverage"] = f"Dữ liệu ngày {date} (quận/huyện {row.get('district_name_vi')})"
    row["wind_direction_vi"] = wind_deg_to_vietnamese(row.get("avg_wind_deg"))
    return row

def get_daily_summary_data(ward_id: str, query_date) -> Dict[str, Any]:
    """Get daily weather summary data for a ward.

    Args:
        ward_id: Ward ID
        query_date: Date object (date or datetime.date)

    Returns:
        Dictionary with daily weather data or error
    """
    row = query_one(
        "SELECT * FROM fact_weather_daily WHERE ward_id = %s AND date = %s",
        (ward_id, query_date)
    )

    if not row:
        return {"error": "no_data", "message": f"Không có dữ liệu ngày {query_date}"}

    # Temp range + bien do nhiet
    temp_min = row.get("temp_min")
    temp_max = row.get("temp_max")
    temp_range = temp_max - temp_min if temp_min is not None and temp_max is not None else 0
    bien_do_nhiet = f"Biên độ nhiệt {temp_range:.0f}°C" if temp_range > 0 else ""
    if temp_range > 10:
        bien_do_nhiet += " - Sáng lạnh, trưa nóng, nên mặc áo khoác"

    # Feels like gap
    feels_like_day = row.get("feels_like_day")
    temp_day = row.get("temp_day")
    feels_like_gap = (feels_like_day - temp_day) if feels_like_day is not None and temp_day is not None else 0

    # Rain assessment
    rain_total = row.get("rain_total") or 0
    if rain_total == 0:
        rain_assessment = "Không mưa"
    elif rain_total < 10:
        rain_assessment = f"Mưa nhẹ {rain_total:.1f}mm"
    elif rain_total < 25:
        rain_assessment = f"Mưa vừa {rain_total:.1f}mm"
    else:
        rain_assessment = f"Mưa to {rain_total:.1f}mm - Nên mang ô"

    # UV level
    uvi = row.get("uvi") or 0
    if uvi >= 11:
        uv_level = "Cực cao - Nguy hiểm"
    elif uvi >= 8:
        uv_level = "Rất cao - Hạn chế ra ngoài 10h-14h"
    elif uvi >= 6:
        uv_level = "Cao - Cần che nắng"
    elif uvi >= 3:
        uv_level = "Trung bình"
    else:
        uv_level = "Thấp"

    # Daylight hours
    daylight_hours = None
    if row.get("sunrise") and row.get("sunset"):
        try:
            sunrise = row["sunrise"]
            sunset = row["sunset"]
            if hasattr(sunrise, "replace"):
                sunrise = sunrise.replace(tzinfo=None)
                sunset = sunset.replace(tzinfo=None)
            daylight_hours = round((sunset - sunrise).total_seconds() / 3600, 1)
        except (TypeError, ValueError, AttributeError):
            pass

    # Wind direction
    wind_dir = wind_deg_to_vietnamese(row.get("wind_deg")) if row.get("wind_deg") is not None else None

    return {
        "date": str(query_date),
        "temp_range": {"min": temp_min, "max": temp_max, "bien_do": temp_range},
        "temp_progression": {
            "sang": row.get("temp_morn"),
            "trua": row.get("temp_day"),
            "chieu": row.get("temp_eve"),
            "toi": row.get("temp_night"),
        },
        "feels_like_gap": feels_like_gap,
        "humidity": row.get("humidity"),
        "dew_point": row.get("dew_point"),
        "pressure": row.get("pressure"),
        "rain_assessment": rain_assessment,
        "rain_total": rain_total,
        "pop": row.get("pop"),
        "uvi": uvi,
        "uv_level": uv_level,
        "daylight_hours": daylight_hours,
        "wind": {"speed": row.get("wind_speed"), "direction": wind_dir, "gust": row.get("wind_gust")},
        "clouds": row.get("clouds"),
        "weather_main": row.get("weather_main"),
        "weather_description": row.get("weather_description"),
        "sunrise": str(row.get("sunrise")) if row.get("sunrise") else None,
        "sunset": str(row.get("sunset")) if row.get("sunset") else None,
        "note": bien_do_nhiet,
    }

