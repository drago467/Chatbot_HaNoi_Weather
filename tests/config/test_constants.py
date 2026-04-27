"""Pin giá trị của `app.config.constants`.

Mỗi giá trị PHẢI giữ identical với behavior trước PR1.2 (đã hardcoded ở
nhiều file). Đổi bất kỳ giá trị nào = behavior change → cần PR riêng.
"""

from __future__ import annotations

from app.config import constants


def test_forecast_max_hours_is_48():
    """OpenWeather hourly cap. Trước PR1.2 hardcoded 48 ở nhiều site."""
    assert constants.FORECAST_MAX_HOURS == 48
    assert isinstance(constants.FORECAST_MAX_HOURS, int)


def test_forecast_max_days_is_8():
    """OpenWeather daily cap. Trước PR1.2 hardcoded 8 ở nhiều site."""
    assert constants.FORECAST_MAX_DAYS == 8
    assert isinstance(constants.FORECAST_MAX_DAYS, int)


def test_uvi_safe_default_is_5():
    """Default UV ngưỡng an toàn cho `get_uv_safe_windows`. Trước PR1.2
    hardcoded 5.0 ở `insight_advanced.py:22, 27`."""
    assert constants.UVI_SAFE_DEFAULT == 5.0
    assert isinstance(constants.UVI_SAFE_DEFAULT, float)
