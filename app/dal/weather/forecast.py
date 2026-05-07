"""DAL module split from weather_dal.py in PR2.2 — behavior identical.

All function bodies are moved verbatim. The legacy `app.dal.weather_dal`
module re-exports everything via `from app.dal.weather import *` so existing
import paths still work.
"""

from typing import List, Dict, Any, Optional

from app.config.constants import FORECAST_MAX_DAYS, FORECAST_MAX_HOURS
from app.dal.timezone_utils import format_ict, to_ict
from app.db.dal import query, query_one
from app.dal.weather_helpers import (
    wind_deg_to_vietnamese,
    wind_speed_to_beaufort,
    clean_chinese_weather_desc,
)


def get_hourly_forecast(ward_id: str, hours: int = 48) -> List[Dict[str, Any]]:
    """Get hourly forecast for a ward.
    
    Args:
        ward_id: Ward ID
        hours: Number of hours to forecast (max 48)
        
    Returns:
        List of hourly forecast data
    """
    hours = max(1, min(hours, FORECAST_MAX_HOURS))  # Clamp 1-FORECAST_MAX_HOURS
    
    results = query("""
        SELECT ts_utc, temp, feels_like, humidity, dew_point, pop, rain_1h,
               wind_speed, wind_deg, clouds, uvi, visibility,
               weather_main, weather_description
        FROM fact_weather_hourly
        WHERE ward_id = %s
          AND data_kind = 'forecast'
          AND ts_utc > NOW()
        ORDER BY ts_utc
        LIMIT %s
    """, (ward_id, hours))
    
    # Add Vietnamese wind direction and ICT time
    for r in results:
        r["wind_direction_vi"] = wind_deg_to_vietnamese(r.get("wind_deg"))
        r["wind_beaufort"] = wind_speed_to_beaufort(r.get("wind_speed"))
        r["time_ict"] = format_ict(r.get("ts_utc"))
        r["weather_description"] = clean_chinese_weather_desc(r.get("weather_description"))
    
    return results

def get_daily_forecast(ward_id: str, days: int = 8, start_date: str = None) -> List[Dict[str, Any]]:
    """Get daily forecast for a ward.

    Args:
        ward_id: Ward ID
        days: Number of days to forecast (max 8)
        start_date: Start date (YYYY-MM-DD). Defaults to today.

    Returns:
        List of daily forecast data
    """
    days = max(1, min(days, FORECAST_MAX_DAYS))  # Clamp 1-FORECAST_MAX_DAYS

    if start_date:
        date_filter = "date >= %s::date"
        params = (ward_id, start_date, days)
    else:
        date_filter = "date >= (NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date"
        params = (ward_id, days)

    results = query(f"""
        SELECT date, temp_min, temp_max, temp_avg, temp_morn, temp_eve, temp_night,
               humidity, pop, rain_total, uvi, weather_main, weather_description,
               summary, sunrise, sunset,
               wind_speed, wind_deg, wind_gust
        FROM fact_weather_daily
        WHERE ward_id = %s
          AND {date_filter}
        ORDER BY date
        LIMIT %s
    """, params)
    
    # Add ICT times + wind direction + day_of_week
    from datetime import datetime

    # Vietnamese day-of-week mapping
    _DAYS_VI = {
        "Monday": "Thứ Hai", "Tuesday": "Thứ Ba", "Wednesday": "Thứ Tư",
        "Thursday": "Thứ Năm", "Friday": "Thứ Sáu", "Saturday": "Thứ Bảy",
        "Sunday": "Chủ Nhật",
    }

    for r in results:
        # Day of week (giúp model không tính sai thứ)
        if r.get('date'):
            try:
                date_obj = datetime.strptime(str(r['date']), '%Y-%m-%d')
                r['day_of_week'] = _DAYS_VI.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
            except (ValueError, TypeError):
                pass
        if r.get('sunrise'):
            r['sunrise_ict'] = format_ict(r['sunrise'])
            r['sunrise_time'] = format_ict(r['sunrise'], fmt="%H:%M")
        if r.get('sunset'):
            r['sunset_ict'] = format_ict(r['sunset'])
            r['sunset_time'] = format_ict(r['sunset'], fmt="%H:%M")
        if r.get('wind_deg') is not None:
            r['wind_direction_vi'] = wind_deg_to_vietnamese(r['wind_deg'])
        r['weather_description'] = clean_chinese_weather_desc(r.get('weather_description'))

    return results

def get_weather_range(ward_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get weather data for a date range.
    
    Args:
        ward_id: Ward ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        List of daily weather data
    """
    results = query("""
        SELECT date, temp_min, temp_max, temp_avg, humidity, 
               rain_total, weather_main, weather_description
        FROM fact_weather_daily
        WHERE ward_id = %s 
          AND date BETWEEN %s AND %s
        ORDER BY date
    """, (ward_id, start_date, end_date))

    for r in results:
        r['weather_description'] = clean_chinese_weather_desc(r.get('weather_description'))

    return results

def get_weather_period_data(ward_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Get daily weather data for a date range (used by get_weather_period tool).

    Args:
        ward_id: Ward ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of daily weather rows
    """
    # R11 P15 extension: thêm dew_point/clouds để _summarize_period có đủ
    # field chạy detect_hanoi_weather_phenomena (nồm ẩm cần dew_point; rét
    # đậm cần clouds). NOTE: visibility chỉ tồn tại ở fact_weather_hourly;
    # daily schema không lưu → suong_mu detector skip gracefully.
    return query(
        "SELECT date, temp_min, temp_max, temp_avg, humidity, dew_point, "
        "pop, rain_total, uvi, wind_speed, wind_deg, wind_gust, "
        "weather_main, clouds "
        "FROM fact_weather_daily "
        "WHERE ward_id = %s AND date BETWEEN %s AND %s "
        "AND data_kind IN ('forecast', 'history') ORDER BY date",
        (ward_id, start_date, end_date)
    )

