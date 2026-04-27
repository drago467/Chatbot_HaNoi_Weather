"""Weather DAL package — split from weather_dal.py in PR2.2."""

from app.dal.weather.current import (
    get_current_weather,
    get_latest_weather_time,
)
from app.dal.weather.forecast import (
    get_hourly_forecast,
    get_daily_forecast,
    get_weather_range,
    get_weather_period_data,
)
from app.dal.weather.history import (
    get_weather_history,
    get_city_weather_history,
    get_district_weather_history,
    get_daily_summary_data,
)
from app.dal.weather.analytics import (
    analyze_rain_from_forecasts,
    get_rain_timeline,
    get_temperature_trend,
    detect_weather_changes,
)

__all__ = [
    "get_current_weather",
    "get_latest_weather_time",
    "get_hourly_forecast",
    "get_daily_forecast",
    "get_weather_range",
    "get_weather_period_data",
    "get_weather_history",
    "get_city_weather_history",
    "get_district_weather_history",
    "get_daily_summary_data",
    "analyze_rain_from_forecasts",
    "get_rain_timeline",
    "get_temperature_trend",
    "detect_weather_changes",
]
