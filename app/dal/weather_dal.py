"""Weather DAL legacy shim — re-exports from app.dal.weather package.

PR2.2 split this module into app/dal/weather/{current,forecast,history,
analytics}.py. This shim preserves the import path
`from app.dal.weather_dal import get_current_weather` for existing callers.
"""

from app.dal.weather import *  # noqa: F401, F403
from app.dal.weather import (
    get_current_weather,
    get_latest_weather_time,
    get_hourly_forecast,
    get_daily_forecast,
    get_weather_range,
    get_weather_period_data,
    get_weather_history,
    get_city_weather_history,
    get_district_weather_history,
    get_daily_summary_data,
    analyze_rain_from_forecasts,
    get_rain_timeline,
    get_temperature_trend,
    detect_weather_changes,
)
