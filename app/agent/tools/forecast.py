"""Forecast tools — hourly, daily, rain_timeline, best_time.

Tất cả đều hỗ trợ 3 tier (ward/district/city) nhất quán thông qua dispatch_forecast.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.config.constants import FORECAST_MAX_DAYS, FORECAST_MAX_HOURS


# ============== Tool: get_hourly_forecast ==============

class GetHourlyForecastInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID (ví dụ: ID_00169)")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    hours: int = Field(default=24, description="Số giờ dự báo (1-48)")


@tool(args_schema=GetHourlyForecastInput)
def get_hourly_forecast(ward_id: str = None, location_hint: str = None, hours: int = 24) -> dict:
    """DỰ BÁO THEO GIỜ cho 1-48 giờ tới. MAX `hours` = 48.

    DÙNG KHI: user hỏi khung giờ CỤ THỂ trong 48h:
        "chiều/tối/đêm nay", "sáng mai", "X giờ tối nay", "vài giờ tới", "6-9h sáng mai",
        "mưa lúc mấy giờ", "nhiệt độ tối nay", "gió đêm nay", khoảng thời gian cụ thể.
        Set `hours` ĐỦ phủ khung user hỏi (vd NOW=16h & "8pm-midnight" → `hours` ≥ 10;
        NOW=11h & "6-9h sáng mai" → `hours` ≥ 24).
    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội (tự động dispatch).

    KHÔNG DÙNG KHI:
        - "bây giờ / hiện tại" → get_current_weather (snapshot).
        - "ngày cụ thể / nhiều ngày" (>48h) → get_daily_forecast.
        - "hôm qua / ngày đã qua" → get_weather_history.
        - "mưa đến bao giờ / tạnh lúc nào" → get_rain_timeline.
        - Khoảng vượt 48h → refuse hoặc chuyển daily_forecast.

    Returns: Flat VN dict, key `"dự báo"` = list per-hour flat VN dict
    (`"thời điểm"`, `"thời tiết"`, `"nhiệt độ"`, `"độ ẩm"`, `"xác suất mưa"`,
    `"cường độ mưa"` khi mưa, `"gió"`, `"mây"`) + `"tóm tắt tổng"` + `"ghi chú dữ liệu"`.

    ⚠ QUAN TRỌNG về param `hours`:
    - `hours` là KHOẢNG THỜI GIAN (range từ NOW đến NOW+hours), KHÔNG phải 1 giờ cụ thể.
    - hours=3 → trả 3 record đầu tiên từ NOW (KHÔNG phải "3 giờ user hỏi").
    - `hours` được CLAMP vào [1, 48] silent (không error). Pass hours=49 → silently
      truncated thành 48, có thể miss 1h biên. Nếu cần cover xa hơn 48h → dùng
      get_daily_forecast (8 ngày tới).
    - Nếu user hỏi khung giờ tương lai xa (ví dụ "6h-9h SÁNG MAI"):
      → phải set hours đủ lớn để cover khung đó (thường hours=24-30).
      → Sau đó đọc forecasts array, PICK entries có `time_ict` match khung user hỏi.
      → KHÔNG báo cáo data của 3 giờ đầu tiên khi user hỏi sáng mai.

    VÍ DỤ:
    - "chiều nay có mưa không" (13-18h TODAY, NOW=8am) → hours=10-11 (đủ cover đến 18h)
    - "9h tối nay Cầu Giấy nhiệt độ" (21h TODAY) → hours=13+, pick entry có time_ict='21:00'
    - "6h-9h sáng mai Long Biên sương mù" (NOW=10am) → hours=24, pick entries 06-09:00 ngày mai
    - "3 giờ tới có giông không" → hours=3 (đúng nghĩa 3 giờ từ NOW)
    """
    from app.agent.dispatch import dispatch_forecast
    from app.dal.weather_dal import get_hourly_forecast as dal_ward
    from app.dal.weather_aggregate_dal import (
        get_district_hourly_forecast as dal_district,
        get_city_hourly_forecast as dal_city,
    )

    from app.agent.tools.output_builder import build_hourly_forecast_output

    hours = max(1, min(hours, FORECAST_MAX_HOURS))
    raw = dispatch_forecast(
        ward_id=ward_id,
        location_hint=location_hint,
        ward_fn=dal_ward,
        district_fn=dal_district,
        city_fn=dal_city,
        ward_args={"hours": hours},
        district_args={"hours": hours},
        city_args={"hours": hours},
        forecast_type="hourly",
        default_scope="city",
    )
    return build_hourly_forecast_output(raw)


# ============== Tool: get_daily_forecast ==============

class GetDailyForecastInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID (ví dụ: ID_00169)")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    days: int = Field(default=7, description="Số ngày dự báo (1-8)")
    start_date: Optional[str] = Field(default=None, description="ISO YYYY-MM-DD. COPY từ RUNTIME CONTEXT [2] (tomorrow_iso/day_after_tomorrow_iso/this_saturday/week_table/next_week_table). Default: hôm nay nếu absent. KHÔNG tự cộng/trừ.")


@tool(args_schema=GetDailyForecastInput)
def get_daily_forecast(ward_id: str = None, location_hint: str = None, days: int = 7, start_date: str = None) -> dict:
    """DỰ BÁO THEO NGÀY cho khoảng 1-8 ngày (overview per-day). MAX `days` = 8.

    DÙNG KHI: user hỏi nguyên ngày hoặc nhiều ngày tương lai:
        "ngày mai", "ngày kia", "thứ X", "3 ngày tới", "cuối tuần này",
        "tuần tới" (phần trong 8 ngày).

    KHÔNG DÙNG KHI:
        - "cả ngày X chi tiết sáng/trưa/chiều/tối" 1 ngày duy nhất → get_daily_summary.
        - "chiều/tối/X giờ" trong 48h cho HÔM NAY → get_hourly_forecast.
        - "hôm qua / hôm kia" → get_weather_history.
        - "bây giờ" → get_current_weather.
        - Khoảng vượt 8 ngày → refuse nói rõ "tối đa 8 ngày", KHÔNG bịa.

    ⚠ ANTI-HALLUCINATION với aggregate Sáng/Chiều/Tối:
        Output `"nhiệt độ theo ngày"` chỉ có 3 mốc gộp (Sáng/Chiều/Tối) per ngày.
        KHÔNG có data hourly chi tiết (vd 05:00, 06:00, 07:00). Khi user hỏi "sáng
        ngày X" → CHỈ COPY "Sáng Y°C" từ aggregate, TUYỆT ĐỐI KHÔNG bịa từng giờ
        cụ thể (mưa mm/h, độ ẩm % theo giờ). Cần granular hourly trong 48h?
        → gọi thêm get_hourly_forecast với `hours` đủ cover khung user hỏi.

    LOGIC param:
        - `start_date` (ISO YYYY-MM-DD): mặc định hôm nay. User hỏi "ngày mai" → PHẢI
          truyền `start_date=tomorrow_iso`, `days=1`. KHÔNG gọi days=1 thiếu start_date.
        - `days`: số ngày bao gồm start_date. 1 ≤ days ≤ 8.

    Returns: Flat VN dict:
        - `"dự báo"`: list per-day flat VN dict (`"ngày"` DD/MM/YYYY `(Thứ X)`,
          `"thời tiết"`, `"nhiệt độ"` Thấp-Cao, `"nhiệt độ theo ngày"` Sáng/Trưa/Chiều/Tối
          overview, `"xác suất mưa"`, `"tổng lượng mưa"` mm, `"gió"`, `"UV"`, `"mọc-lặn"`).
        - `"tổng hợp"`: pre-computed superlatives (ngày nóng/mát/mưa nhiều/ít nhất).
          COPY thẳng, KHÔNG tự argmax qua list.
    """
    from app.agent.dispatch import dispatch_forecast
    from app.dal.weather_dal import get_daily_forecast as dal_ward
    from app.dal.weather_aggregate_dal import (
        get_district_daily_forecast as dal_district,
        get_city_daily_forecast as dal_city,
    )

    from app.agent.tools.output_builder import build_daily_forecast_output

    days = max(1, min(days, FORECAST_MAX_DAYS))
    extra_args = {"days": days}
    if start_date:
        extra_args["start_date"] = start_date
    raw = dispatch_forecast(
        ward_id=ward_id,
        location_hint=location_hint,
        ward_fn=dal_ward,
        district_fn=dal_district,
        city_fn=dal_city,
        ward_args=extra_args,
        district_args=extra_args,
        city_args=extra_args,
        forecast_type="daily",
        default_scope="city",
    )
    return build_daily_forecast_output(raw)


# ============== Tool: get_rain_timeline ==============

class GetRainTimelineInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    hours: int = Field(default=24, description="Số giờ scan (1-48)")


@tool(args_schema=GetRainTimelineInput)
def get_rain_timeline(ward_id: str = None, location_hint: str = None, hours: int = 24) -> dict:
    """TIMELINE MƯA: đợt mưa bắt đầu/kết thúc/cường độ đỉnh trong 1-48h. MAX `hours` = 48.

    SCOPE: Tool LUÔN scan từ NOW + `hours` giờ tới. KHÔNG có param `start_date` —
    nếu agent pass `start_date` sẽ bị silently ignore. Muốn check khung thời gian
    bắt đầu KHÔNG phải NOW (e.g. "sáng CN" trong khi NOW là chiều T7) → tăng `hours`
    đủ lớn để cover khung user hỏi (vd: NOW=13:00 T7, user hỏi 7h CN → `hours=42`).

    DÙNG KHI: user hỏi MỐC mưa trong 48h:
        "lúc nào mưa?", "mưa đến bao giờ?", "trời tạnh lúc nào?", "chiều có mưa không?".
        Phải đọc timestamp start/end trong output — gán vào đúng NGÀY user hỏi.

    KHÔNG DÙNG KHI:
        - "tổng lượng mưa ngày / tháng" → dùng get_daily_forecast / get_weather_period
          (có `"tổng lượng mưa"` mm/ngày). Key `"cường độ đỉnh"` ở đây là mm/h TẠI 1 GIỜ,
          KHÔNG phải tổng.
        - "ngày mai có mưa không" nếu data chỉ 48h và hỏi ngày > 48h tới → refuse với limit.

    Returns: Flat VN dict với `"đợt mưa"` = list `[{"bắt đầu", "kết thúc", "xác suất cao nhất",
    "cường độ đỉnh" (mm/h)}]`, `"tổng số đợt"`, `"tóm tắt"` (next_rain / next_clear).
    """
    from app.agent.dispatch import dispatch_forecast
    from app.dal.weather_dal import get_hourly_forecast as dal_ward_hourly
    from app.dal.weather_aggregate_dal import (
        get_district_hourly_forecast as dal_district_hourly,
        get_city_hourly_forecast as dal_city_hourly,
    )
    from app.dal.weather_dal import analyze_rain_from_forecasts

    hours = max(1, min(hours, FORECAST_MAX_HOURS))

    # We need raw forecasts first, then analyze
    result = dispatch_forecast(
        ward_id=ward_id,
        location_hint=location_hint,
        ward_fn=dal_ward_hourly,
        district_fn=dal_district_hourly,
        city_fn=dal_city_hourly,
        ward_args={"hours": hours},
        district_args={"hours": hours},
        city_args={"hours": hours},
        forecast_type="hourly",
        default_scope="city",
    )

    from app.agent.tools.output_builder import build_rain_timeline_output, build_error_output

    if result.get("error"):
        return build_error_output(result)

    forecasts = result.get("forecasts", [])
    rain_analysis = analyze_rain_from_forecasts(forecasts, hours)
    rain_analysis["resolved_location"] = result.get("resolved_location", {})
    rain_analysis["level"] = result.get("level", "city")
    rain_analysis["data_coverage"] = result.get("data_coverage")
    # Forward forecasts để builder detect past-frame (R10)
    rain_analysis["forecasts"] = forecasts
    return build_rain_timeline_output(rain_analysis)


# ============== Tool: get_best_time ==============

class GetBestTimeInput(BaseModel):
    activity: str = Field(description="Hoạt động: chay_bo, picnic, bike, chup_anh, du_lich, cam_trai, ...")
    ward_id: Optional[str] = Field(default=None, description="Ward ID")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")
    hours: int = Field(default=24, description="Số giờ quét (1-48)")


@tool(args_schema=GetBestTimeInput)
def get_best_time(activity: str, ward_id: str = None, location_hint: str = None, hours: int = 24) -> dict:
    """Tìm KHUNG GIỜ TỐT NHẤT để thực hiện hoạt động ngoài trời. MAX hours=48.

    ⚠ Tool scan từ NOW + hours giờ. Output CÓ THỂ chứa slot HÔM NAY lẫn NGÀY MAI.
    Khi user hỏi "NGÀY MAI đi X" → PHẢI đọc `"thời điểm"` trong output, CHỈ report
    slot có DATE = ngày mai. KHÔNG trả slot hôm nay cho user hỏi ngày mai.

    DÙNG KHI: "mấy giờ chạy bộ tốt?", "lúc nào đi chơi đẹp nhất? (trong 48h)".

    KHÔNG DÙNG KHI:
        - "Cuối tuần / 2-3 ngày tới đi X" → gọi get_weather_period(start, end) TRƯỚC
          lấy data nhiều ngày, rồi best_time nếu cần 1 ngày.
        - "Ngày mai / thứ X đi X" (ngoài 48h) → daily_forecast trước.
        - User chỉ hỏi tổng quan "thời tiết đi chơi thế nào" → get_activity_advice.

    Returns: Flat VN dict với `"giờ tốt nhất": [top 5 slots]`, `"giờ kém nhất": [bottom 3]`,
    mỗi slot có `"thời điểm", "điểm" (N/100), "nhiệt độ", "xác suất mưa", "ghi chú"`.
    """
    from app.agent.dispatch import dispatch_forecast
    from app.dal.weather_dal import get_hourly_forecast as dal_ward_hourly
    from app.dal.weather_aggregate_dal import (
        get_district_hourly_forecast as dal_district_hourly,
        get_city_hourly_forecast as dal_city_hourly,
    )
    from app.dal.activity_dal import get_best_time_for_activity

    hours = max(1, min(hours, FORECAST_MAX_HOURS))

    # Get forecasts first
    result = dispatch_forecast(
        ward_id=ward_id,
        location_hint=location_hint,
        ward_fn=dal_ward_hourly,
        district_fn=dal_district_hourly,
        city_fn=dal_city_hourly,
        ward_args={"hours": hours},
        district_args={"hours": hours},
        city_args={"hours": hours},
        forecast_type="hourly",
        default_scope="city",
    )

    from app.agent.tools.output_builder import build_best_time_output, build_error_output

    if result.get("error"):
        return build_error_output(result)

    forecasts = result.get("forecasts", [])
    best = get_best_time_for_activity(activity, forecasts=forecasts, hours=hours)
    best["resolved_location"] = result.get("resolved_location", {})
    best["level"] = result.get("level", "city")
    return build_best_time_output(best)
