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
    clean_chinese_weather_desc,
)


def get_current_weather(ward_id: str) -> Dict[str, Any]:
    """Get current weather for a ward.
    
    Args:
        ward_id: Ward ID (e.g., 'ID_XXXXX')
        
    Returns:
        Dictionary with current weather data or error
    """
    # Step 1: Try to get fresh data (within 2 hours, KHÔNG lấy future data)
    # Bound trên ts_utc <= NOW() để tránh bắt forecast bị mislabel 'current'.
    result = query_one("""
        SELECT temp, feels_like, humidity, pressure, dew_point, wind_speed, wind_deg,
               wind_gust, clouds, visibility, uvi, pop, rain_1h,
               weather_main, weather_description, ts_utc,
               NOW() - ts_utc AS data_age
        FROM fact_weather_hourly
        WHERE ward_id = %s AND data_kind = 'current'
          AND ts_utc > NOW() - INTERVAL '2 hours'
          AND ts_utc <= NOW() + INTERVAL '30 minutes'
        ORDER BY ts_utc DESC
        LIMIT 1
    """, (ward_id,))

    # Step 2: Fallback — dữ liệu cũ nhưng không quá tương lai
    if not result:
        result = query_one("""
            SELECT temp, feels_like, humidity, pressure, dew_point, wind_speed, wind_deg,
                   wind_gust, clouds, visibility, uvi, pop, rain_1h,
                   weather_main, weather_description, ts_utc,
                   NOW() - ts_utc AS data_age
            FROM fact_weather_hourly
            WHERE ward_id = %s AND data_kind = 'current'
              AND ts_utc <= NOW() + INTERVAL '30 minutes'
            ORDER BY ts_utc DESC
            LIMIT 1
        """, (ward_id,))
        
        if result:
            # Mark as stale data
            result["data_stale"] = True
            result["data_warning"] = "Dữ liệu cũ, có thể không chính xác"

    if not result:
        return {"error": "no_data", "message": "Không có dữ liệu thời tiết hiện tại"}
    
    # Add data age info
    data_age = result.pop('data_age', None)
    if data_age:
        result["data_age_minutes"] = int(data_age.total_seconds() / 60)
        result["data_age_hours"] = round(data_age.total_seconds() / 3600, 1)
    
    # Add Vietnamese context. Status labels (uv/dew_point/pressure/feels_like/
    # wind_beaufort_vi) đã được builder layer compute lại từ raw → DAL không
    # enrich nữa để tránh DUPLICATE work + drift. Chỉ giữ wind_direction_vi
    # (data hygiene đơn giản, builder vẫn xài qua _wind_text mà không bắt buộc),
    # time_ict (format helper), weather_description clean (data hygiene at source).
    result["wind_direction_vi"] = wind_deg_to_vietnamese(result.get("wind_deg"))
    result["time_ict"] = format_ict(result.get("ts_utc"))
    result["weather_description"] = clean_chinese_weather_desc(result.get("weather_description"))
    
    return result

def get_latest_weather_time(ward_id: str) -> List[Dict[str, Any]]:
    """Get the latest weather timestamp for a ward.
    
    Args:
        ward_id: Ward ID
        
    Returns:
        List of dictionaries with latest timestamp for each data_kind
    """
    return query("""
        SELECT MAX(ts_utc) as latest, 
               NOW() - MAX(ts_utc) as age,
               data_kind
        FROM fact_weather_hourly
        WHERE ward_id = %s
        GROUP BY data_kind
        ORDER BY data_kind
    """, (ward_id,))

