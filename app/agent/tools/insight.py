"""Insight tools — phenomena, temperature_trend, comfort_index,
weather_change_alert, clothing_advice, activity_advice.

Tất cả đều hỗ trợ 3 tier nhất quán.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.config.constants import FORECAST_MAX_DAYS


# ============== Tool: detect_phenomena ==============

class DetectPhenomenaInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")


@tool(args_schema=DetectPhenomenaInput)
def detect_phenomena(ward_id: str = None, location_hint: str = None) -> dict:
    """Phát hiện các HIỆN TƯỢNG THỜI TIẾT ĐẶC BIỆT tại Hà Nội.

    DÙNG KHI: "có hiện tượng gì đặc biệt không?", "có nồm ẩm không?",
    "có gió mùa đông bắc không?", "có rét đậm không?".

    KHÔNG DÙNG KHI:
        - Hỏi tầm nhìn/visibility cụ thể (tool KHÔNG có field visibility).
        - "Sương mù sáng mai/tối nay" (future-frame) → gọi get_hourly_forecast trước,
          detect_phenomena chỉ check tại NOW snapshot.
        - Output KHÔNG có phenomena X (sương mù, băng giá, …) → KHÔNG bịa có;
          respond rằng "không phát hiện X trong snapshot".

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội.
    Trả về: danh sách hiện tượng (nồm ẩm, gió Lào, gió mùa ĐB, rét đậm, sương mù, mưa đông).
    ⚠ CHỈ liệt kê phenomena CÓ TRONG OUTPUT, KHÔNG suy diễn từ độ ẩm/mây/nhiệt.
    """
    from app.agent.dispatch import resolve_and_dispatch, normalize_agg_keys
    from app.dal.weather_knowledge_dal import detect_hanoi_weather_phenomena

    def _detect_ward(ward_id):
        from app.dal.weather_dal import get_current_weather
        weather = get_current_weather(ward_id)
        if weather.get("error"):
            return weather
        phenomena = detect_hanoi_weather_phenomena(weather)
        return {"phenomena": phenomena.get("phenomena", []),
                "has_dangerous": phenomena.get("has_dangerous", False),
                "weather_snapshot": weather}

    def _detect_district(district_id):
        from app.dal.weather_aggregate_dal import get_district_current_weather
        weather = get_district_current_weather(district_id)
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        phenomena = detect_hanoi_weather_phenomena(weather)
        return {"phenomena": phenomena.get("phenomena", []),
                "has_dangerous": phenomena.get("has_dangerous", False),
                "weather_snapshot": weather}

    def _detect_city():
        from app.dal.weather_aggregate_dal import get_city_current_weather
        weather = get_city_current_weather()
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        phenomena = detect_hanoi_weather_phenomena(weather)
        return {"phenomena": phenomena.get("phenomena", []),
                "has_dangerous": phenomena.get("has_dangerous", False),
                "weather_snapshot": weather}

    from app.agent.tools.output_builder import build_detect_phenomena_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=_detect_ward,
        district_fn=_detect_district,
        city_fn=_detect_city,
        normalize=False,
        label="hiện tượng thời tiết",
    )
    return build_detect_phenomena_output(raw)


# ============== Tool: get_temperature_trend ==============

class GetTemperatureTrendInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    days: int = Field(default=7, description="Số ngày phân tích (2-8)")


@tool(args_schema=GetTemperatureTrendInput)
def get_temperature_trend(ward_id: str = None, location_hint: str = None, days: int = 7) -> dict:
    """Phân tích XU HƯỚNG NHIỆT ĐỘ 2-8 ngày TỚI (ấm dần / lạnh dần / ổn định). FORWARD-ONLY.

    ⚠ CHỈ có data TƯƠNG LAI (today + N ngày tới). KHÔNG có data QUÁ KHỨ.

    DÙNG KHI: "nhiệt độ SẮP TỚI thay đổi thế nào?", "mấy ngày tới có lạnh dần không?",
    "xu hướng nhiệt độ (tuần này = phần còn lại phía trước)".

    KHÔNG DÙNG KHI:
        - "tuần qua / mấy hôm trước / X ngày qua" (PAST) → dùng get_weather_period(start_date, end_date).
        - "hôm qua nhiệt độ" → dùng get_weather_history.

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội.
    Trả về: trend (warming/cooling/stable), slope, inflection_date, hottest/coldest day.
    """
    from app.dal.weather_dal import get_temperature_trend as dal_ward_trend
    from app.dal.weather_aggregate_dal import (
        get_district_temperature_trend_data,
        get_city_temperature_trend_data,
    )

    days = max(2, min(days, FORECAST_MAX_DAYS))

    def _district_trend(district_id):
        rows = get_district_temperature_trend_data(district_id, days)
        return _analyze_trend(rows)

    def _city_trend():
        rows = get_city_temperature_trend_data(days)
        return _analyze_trend(rows)

    from app.agent.dispatch import resolve_and_dispatch
    from app.agent.tools.output_builder import build_temperature_trend_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=lambda ward_id: dal_ward_trend(ward_id, days),
        district_fn=_district_trend,
        city_fn=_city_trend,
        normalize=False,
        label="xu hướng nhiệt độ",
    )
    return build_temperature_trend_output(raw)


def _analyze_trend(rows: list) -> dict:
    """Reusable trend analysis cho district/city daily data."""
    if len(rows) < 2:
        return {"error": "no_data", "message": "Không đủ dữ liệu để phân tích xu hướng"}

    temps = [r["temp_avg"] for r in rows if r.get("temp_avg") is not None]
    if len(temps) < 2:
        return {"error": "no_data", "message": "Không đủ dữ liệu nhiệt độ"}

    slope = (temps[-1] - temps[0]) / (len(temps) - 1)
    if slope > 0.5:
        trend, trend_vi = "warming", "Ấm dần lên"
    elif slope < -0.5:
        trend, trend_vi = "cooling", "Lạnh dần"
    else:
        trend, trend_vi = "stable", "Ổn định"

    # Find inflection
    inflection = None
    for i in range(1, len(temps) - 1):
        prev_diff = temps[i] - temps[i - 1]
        next_diff = temps[i + 1] - temps[i]
        if (prev_diff > 0 and next_diff < -0.5) or (prev_diff < 0 and next_diff > 0.5):
            inflection = str(rows[i]["date"])
            break

    max_row = max(rows, key=lambda r: r.get("temp_max") or 0)
    min_row = min(rows, key=lambda r: r.get("temp_min") or 999)

    return {
        "trend": trend, "trend_vi": trend_vi,
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


# ============== Tool: get_comfort_index ==============

class GetComfortIndexInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")


@tool(args_schema=GetComfortIndexInput)
def get_comfort_index(ward_id: str = None, location_hint: str = None) -> dict:
    """Tính điểm THOẢI MÁI (0-100) kết hợp nhiệt độ, độ ẩm, gió, UV, mưa. SNAPSHOT tại NOW.

    ⚠ Đọc SNAPSHOT tại NOW. "tối nay / sáng mai thoải mái không?" → snapshot NOW KHÔNG
    đúng cho khung tương lai. Gọi get_hourly_forecast trước lấy data khung user hỏi.

    DÙNG KHI: "BÂY GIỜ thoải mái không?", "điểm thoải mái HIỆN TẠI bao nhiêu?",
    "có dễ chịu không (lúc này)?".

    KHÔNG DÙNG KHI:
        - "tối nay / sáng mai / cuối tuần thoải mái không?" → forecast trước.
        - Cần chi tiết mưa/UV → gọi kèm tool tương ứng.

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội.
    Trả về: score (0-100), label, recommendation, breakdown từng yếu tố.
    """
    # `compute_comfort_index` chỉ dùng trong `_compute_comfort` — import lại tại đó.
    from app.agent.dispatch import resolve_and_dispatch, normalize_agg_keys

    def _comfort_ward(ward_id):
        from app.dal.weather_dal import get_current_weather
        weather = get_current_weather(ward_id)
        if weather.get("error"):
            return weather
        return _compute_comfort(weather)

    def _comfort_district(district_id):
        from app.dal.weather_aggregate_dal import get_district_current_weather
        weather = get_district_current_weather(district_id)
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        return _compute_comfort(weather)

    def _comfort_city():
        from app.dal.weather_aggregate_dal import get_city_current_weather
        weather = get_city_current_weather()
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        return _compute_comfort(weather)

    from app.agent.tools.output_builder import build_comfort_index_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=_comfort_ward,
        district_fn=_comfort_district,
        city_fn=_comfort_city,
        normalize=False,
        label="chỉ số thoải mái",
    )
    return build_comfort_index_output(raw)


def _compute_comfort(weather: dict) -> dict:
    """Tính comfort index từ weather data (đã normalize)."""
    from app.dal.weather_helpers import compute_comfort_index
    comfort = compute_comfort_index(
        temp=weather.get("temp"),
        humidity=weather.get("humidity"),
        wind_speed=weather.get("wind_speed"),
        uvi=weather.get("uvi") or weather.get("uvi_max") or 0,
        pop=weather.get("pop") or 0,
    )
    if comfort is None:
        return {"error": "no_data", "message": "Không đủ dữ liệu để tính chỉ số thoải mái"}
    comfort["weather_snapshot"] = {
        "temp": weather.get("temp"),
        "humidity": weather.get("humidity"),
        "wind_speed": weather.get("wind_speed"),
        "uvi": weather.get("uvi"),
        "weather_main": weather.get("weather_main"),
    }
    return comfort


# ============== Tool: get_weather_change_alert ==============

class GetWeatherChangeAlertInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    hours: int = Field(default=6, description="Số giờ tới scan (1-12)")


@tool(args_schema=GetWeatherChangeAlertInput)
def get_weather_change_alert(ward_id: str = None, location_hint: str = None, hours: int = 6) -> dict:
    """Phát hiện THAY ĐỔI THỜI TIẾT LỚN sắp xảy ra trong 6-12h tới. KHÔNG phải cảnh báo NGUY HIỂM.

    Phát hiện: temp drop/rise >5°C, rain start/stop, wind increase, weather condition change.

    DÙNG KHI: "sắp có gì THAY ĐỔI không?", "thời tiết có BIẾN ĐỘNG không?",
    "có chuyển mùa không?", "nhiệt độ sắp tăng/giảm mạnh?".

    KHÔNG DÙNG KHI:
        - "có CẢNH BÁO gì không?" / "có bão không?" / "có rét hại không?" / "có giông không?"
          (cảnh báo NGUY HIỂM chuẩn) → dùng get_weather_alerts.
        - "có nồm ẩm / gió mùa ĐB không?" (hiện tượng đặc trưng HN) → dùng detect_phenomena.

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội.
    Trả về: changes list, has_significant_change, hours_scanned, current_summary.
    """
    from app.dal.weather_dal import detect_weather_changes as dal_ward_detect

    hours = max(1, min(hours, 12))

    def _district_detect(district_id):
        from app.dal.weather_aggregate_dal import (
            get_district_current_weather, get_district_hourly_forecast
        )
        from app.agent.dispatch import normalize_agg_keys
        current = get_district_current_weather(district_id)
        if current.get("error"):
            return current
        current = normalize_agg_keys(current)
        forecasts = get_district_hourly_forecast(district_id, hours)
        from app.agent.dispatch import normalize_rows
        forecasts = normalize_rows(forecasts)
        return _detect_changes(current, forecasts)

    def _city_detect():
        from app.dal.weather_aggregate_dal import (
            get_city_current_weather, get_city_hourly_forecast
        )
        from app.agent.dispatch import normalize_agg_keys
        current = get_city_current_weather()
        if current.get("error"):
            return current
        current = normalize_agg_keys(current)
        forecasts = get_city_hourly_forecast(hours)
        from app.agent.dispatch import normalize_rows
        forecasts = normalize_rows(forecasts)
        return _detect_changes(current, forecasts)

    from app.agent.dispatch import resolve_and_dispatch
    from app.agent.tools.output_builder import build_weather_change_alert_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=lambda ward_id: dal_ward_detect(ward_id, hours),
        district_fn=_district_detect,
        city_fn=_city_detect,
        normalize=False,
        label="biến động thời tiết",
    )
    return build_weather_change_alert_output(raw)


def _detect_changes(current: dict, forecasts: list) -> dict:
    """Detect significant changes between current and forecasts (reusable)."""
    from app.dal.timezone_utils import format_ict

    if not forecasts:
        return {"error": "no_data", "message": "Không có dữ liệu dự báo"}

    changes = []
    detected_types = set()
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

        if "temperature" not in detected_types and cur_temp is not None and f_temp is not None:
            temp_diff = f_temp - cur_temp
            if abs(temp_diff) >= 5:
                direction = "tăng" if temp_diff > 0 else "giảm"
                changes.append({
                    "type": "temperature",
                    "description": f"Nhiệt độ {direction} {abs(temp_diff):.1f}C ({cur_temp:.1f}->{f_temp:.1f}C)",
                    "time": f_time,
                    "severity": "high" if abs(temp_diff) >= 8 else "medium"
                })
                detected_types.add("temperature")

        if "rain_start" not in detected_types and f_pop - cur_pop >= 0.5:
            changes.append({
                "type": "rain_start",
                "description": f"Khả năng mưa tăng mạnh ({cur_pop*100:.0f}%->{f_pop*100:.0f}%)",
                "time": f_time,
                "severity": "high" if f_pop >= 0.8 else "medium"
            })
            detected_types.add("rain_start")

        if "weather_change" not in detected_types and not cur_is_rain and f_is_rain:
            changes.append({
                "type": "weather_change",
                "description": f"Trời chuyển mưa ({cur_weather}->{f_weather})",
                "time": f_time,
                "severity": "high" if f_weather == "Thunderstorm" else "medium"
            })
            detected_types.add("weather_change")

        if "rain_stop" not in detected_types and cur_is_rain and not f_is_rain and f_pop < 0.3:
            changes.append({
                "type": "rain_stop", "description": "Mưa có thể tạnh",
                "time": f_time, "severity": "low"
            })
            detected_types.add("rain_stop")

        if "wind_increase" not in detected_types and f_wind - cur_wind >= 5:
            changes.append({
                "type": "wind_increase",
                "description": f"Gió mạnh lên ({cur_wind:.1f}->{f_wind:.1f} m/s)",
                "time": f_time,
                "severity": "high" if f_wind >= 15 else "medium"
            })
            detected_types.add("wind_increase")

    return {
        "changes": changes,
        "has_significant_change": len(changes) > 0,
        "hours_scanned": len(forecasts),
        "current_summary": {
            "temp": cur_temp, "weather_main": cur_weather,
            "wind_speed": cur_wind, "pop": cur_pop
        }
    }


# ============== Tool: get_clothing_advice ==============

class GetClothingAdviceInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    hours_ahead: int = Field(default=0, description="Số giờ tới (0=hiện tại)")


@tool(args_schema=GetClothingAdviceInput)
def get_clothing_advice(ward_id: str = None, location_hint: str = None, hours_ahead: int = 0) -> dict:
    """Khuyến nghị TRANG PHỤC phù hợp với thời tiết. SNAPSHOT tại NOW.

    ⚠ Tool đọc SNAPSHOT tại NOW (district/city LUÔN dùng current, hours_ahead chỉ ward).
    "sáng mai / tối nay mặc gì?" → GỌI get_hourly_forecast hoặc get_daily_forecast TRƯỚC
    để lấy data đúng khung, rồi dùng clothing_advice bổ sung.

    DÙNG KHI: "mặc gì BÂY GIỜ?", "cần áo khoác không (lúc này)?", "nên mang ô không?".

    KHÔNG DÙNG ĐƠN LẺ KHI:
        - "sáng mai / tối nay / ngày mai mặc gì" (FUTURE) → forecast trước.
        - User hỏi chi tiết mưa/UV → gọi kèm hourly_forecast.

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội.
    Trả về: clothing_items, notes, và dữ liệu thời tiết cơ bản.
    """
    from app.dal.activity_dal import get_clothing_advice as dal_ward_clothing
    from app.agent.dispatch import resolve_and_dispatch, normalize_agg_keys

    def _district_clothing(district_id):
        from app.dal.weather_aggregate_dal import get_district_current_weather
        weather = get_district_current_weather(district_id)
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        return _clothing_from_weather(weather, hours_ahead)

    def _city_clothing():
        from app.dal.weather_aggregate_dal import get_city_current_weather
        weather = get_city_current_weather()
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        return _clothing_from_weather(weather, hours_ahead)

    from app.agent.tools.output_builder import build_clothing_advice_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=lambda ward_id: dal_ward_clothing(ward_id, hours_ahead),
        district_fn=_district_clothing,
        city_fn=_city_clothing,
        normalize=False,
        label="khuyến nghị trang phục",
    )
    return build_clothing_advice_output(raw)


def _clothing_from_weather(weather: dict, hours_ahead: int = 0) -> dict:
    """Generate clothing advice from weather data (reusable for district/city)."""
    temp = weather.get("temp")
    humidity = weather.get("humidity") or 50
    pop = weather.get("pop") or 0
    # Bug G fix: dùng max(wind_speed_avg, wind_gust) để khuyên trang phục —
    # gió giật mạnh (gust > avg) mới là yếu tố quyết định "tránh áo rộng".
    # Trước fix: chỉ check wind_speed avg → undershoot risk khi data ghi nhận
    # gió giật 12m/s nhưng avg chỉ 4m/s → notes không bật.
    wind_avg = weather.get("wind_speed") or 0
    wind_gust = weather.get("wind_gust") or 0
    wind = max(wind_avg, wind_gust)
    uvi = weather.get("uvi") or weather.get("uvi_max") or 0
    wm = weather.get("weather_main", "")

    if temp is None:
        return {"error": "Không có dữ liệu nhiệt độ"}

    items = []
    notes = []

    if temp < 10:
        items.extend(["Áo phào/áo khoác dày", "Khăn quàng cổ", "Găng tay", "Mũ len"])
        notes.append("Rét đậm - mặc nhiều lớp, giữ ấm cổ và tay")
    elif temp < 15:
        items.extend(["Áo khoác dày", "Áo len", "Quần dài"])
        notes.append("Lạnh - nên mặc áo khoác dày")
    elif temp < 20:
        items.extend(["Áo khoác nhẹ", "Áo dài tay"])
        notes.append("Se lạnh - áo khoác nhẹ là đủ")
    elif temp < 25:
        items.extend(["Áo thun dài tay hoặc ngắn tay", "Quần dài hoặc short"])
    elif temp < 32:
        items.extend(["Áo mỏng thoáng", "Quần short", "Mũ chống nắng"])
        notes.append("Nóng - chọn vải thoáng mát")
    else:
        items.extend(["Áo mỏng thoáng mát nhất", "Mũ rộng vành", "Kính râm"])
        notes.append("Rất nóng - hạn chế ra ngoài, uống nhiều nước")

    if pop > 0.5 or wm in ("Rain", "Drizzle", "Thunderstorm"):
        items.append("Ô/áo mưa")
        notes.append("Có mưa - nhớ mang ô")
    elif pop > 0.3:
        items.append("Ô gấp nhỏ")
        notes.append("Có thể mưa - mang ô phòng")

    if humidity > 90 and temp > 20:
        notes.append("Nồm ẩm - tránh vải cotton, chọn vải nhanh khô")

    if uvi >= 8:
        items.append("Kem chống nắng SPF50+")
        if "Kính râm" not in items:
            items.append("Kính râm")
        notes.append("UV rất cao - bảo vệ da")
    elif uvi >= 5:
        items.append("Kem chống nắng SPF30+")

    if wind > 8:
        notes.append("Gió mạnh - tránh áo rộng, chọn áo sát người")

    return {
        "clothing_items": items, "notes": notes,
        "temp": temp, "humidity": humidity,
        "pop": round(pop * 100), "uvi": uvi, "wind_speed": wind,
    }


# ============== Tool: get_activity_advice ==============

class GetActivityAdviceInput(BaseModel):
    activity: str = Field(description="Hoạt động: chay_bo, picnic, bike, chup_anh, du_lich, cam_trai, ...")
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")


@tool(args_schema=GetActivityAdviceInput)
def get_activity_advice(activity: str, ward_id: str = None, location_hint: str = None) -> dict:
    """KHUYẾN CÁO chung có nên LÀM hoạt động X hay không (output generic: nên/có thể/hạn chế/không nên).

    ⚠ TOOL NÀY ĐỌC SNAPSHOT NOW. KHÔNG dùng đơn lẻ cho FUTURE query: "tối nay đi chạy / sáng
    mai picnic / cuối tuần đi cắm trại / chiều mai đá bóng" — snapshot không phản ánh được
    khung tương lai. Cách đúng: gọi get_daily_forecast(start_date=target_iso) hoặc
    get_hourly_forecast(hours=cover_window) TRƯỚC để có data đúng khung, rồi mới activity_advice
    nếu cần khuyến cáo bổ sung (snapshot chỉ làm tham khảo phụ).

    DÙNG KHI: user cần ĐÁNH GIÁ CHUNG nhanh ngay BÂY GIỜ:
        "đi chơi được không (lúc này)?", "chạy bộ có ổn không (giờ)?", "có nên picnic (giờ) không?".

    KHÔNG DÙNG ĐƠN LẺ KHI user hỏi CHI TIẾT cần data cụ thể:
        - "chiều mưa đến khi nào?" → PHẢI gọi kèm get_rain_timeline.
        - "UV mấy giờ an toàn?" → PHẢI gọi kèm get_uv_safe_windows.
        - "mấy giờ là tốt nhất?" → PHẢI gọi get_best_time.
        - "mặc gì" → get_clothing_advice.
        - "tối nay/sáng mai/cuối tuần đi X" (FUTURE) → xem cảnh báo trên — get_daily_forecast trước.
        Output activity_advice CHỈ trả message generic ("nên/có thể..."), không có mốc giờ,
        không có số mưa/UV. Nếu câu hỏi đòi chi tiết mà bạn chỉ gọi tool này → TRẢ LỜI THIẾU.

    Returns: Flat VN dict `"khuyến nghị"` (nen/co_the/han_che/khong_nen), `"lý do"`,
    `"gợi ý thêm"` (list khuyến nghị thực tế).
    """
    from app.dal.activity_dal import get_activity_advice as dal_ward_activity
    from app.agent.dispatch import resolve_and_dispatch, normalize_agg_keys

    def _district_activity(district_id):
        from app.dal.weather_aggregate_dal import get_district_current_weather
        weather = get_district_current_weather(district_id)
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        # Reuse the same activity logic with normalized weather
        return _activity_from_weather(activity, weather)

    def _city_activity():
        from app.dal.weather_aggregate_dal import get_city_current_weather
        weather = get_city_current_weather()
        if weather.get("error"):
            return weather
        weather = normalize_agg_keys(weather)
        return _activity_from_weather(activity, weather)

    from app.agent.tools.output_builder import build_activity_advice_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=lambda ward_id: dal_ward_activity(activity, ward_id),
        district_fn=_district_activity,
        city_fn=_city_activity,
        normalize=False,
        label="khuyến cáo hoạt động",
    )
    return build_activity_advice_output(raw)


def _activity_from_weather(activity: str, weather: dict) -> dict:
    """Generate activity advice from weather data (district/city level).

    R18 P1-9 wiring (Bug A fix): mirror `app.dal.activity_dal.get_activity_advice`
    ward path — dùng `evaluate_activity` profile-based thresholds (ACSM/WHO/WMO)
    thay vì generic `KTTV_THRESHOLDS`. Trước fix: "chạy bộ" vs "chụp ảnh" cùng
    advice ở district/city; sau fix: per-activity threshold đúng research.
    """
    from app.config.activity_profiles import evaluate_activity
    from app.dal.weather_knowledge_dal import detect_hanoi_weather_phenomena

    eval_result = evaluate_activity(activity, weather)
    issues = list(eval_result["issues"])
    recommendations = list(eval_result["recommendations"])

    phenomena = detect_hanoi_weather_phenomena(weather)
    for p in phenomena.get("phenomena", []):
        issues.append(p["name"])
        recommendations.append(p["description"])

    severity = eval_result["severity"]
    if severity == "danger":
        advice = "khong_nen"
        reason = f"Thời tiết nguy hiểm cho {activity}: {', '.join(issues)}"
    elif severity == "warning" and len(issues) >= 3:
        advice = "han_che"
        reason = f"Nhiều yếu tố bất lợi: {', '.join(issues)}"
    elif severity == "warning":
        advice = "co_the"
        reason = f"Cần lưu ý: {', '.join(issues)}"
    elif len(issues) == 0:
        advice = "nen"
        reason = "Thời tiết thuận lợi cho hoạt động ngoài trời"
    else:
        # severity == "ok" nhưng có phenomena issues
        advice = "co_the"
        reason = f"Cần lưu ý: {', '.join(issues)}"

    return {
        "advice": advice,
        "reason": reason,
        "recommendations": recommendations,
        "activity": activity,
        "temp": weather.get("temp"),
        "humidity": weather.get("humidity"),
        "pop": weather.get("pop") or 0,
        "uvi": weather.get("uvi") or weather.get("uvi_max") or 0,
        "wind_speed": weather.get("wind_speed") or 0,
        "phenomena": phenomena.get("phenomena", []),
        "profile_used": eval_result["profile_used"],
        "profile_source": eval_result["source_notes"],
        "hanoi_context": eval_result["hanoi_context"],
    }
