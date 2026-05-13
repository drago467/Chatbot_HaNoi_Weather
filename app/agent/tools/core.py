"""Core tools — resolve_location, get_current_weather, get_weather_alerts."""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool


# ============== Tool 1: resolve_location ==============

class ResolveLocationInput(BaseModel):
    location_hint: str = Field(
        description="Tên phường/xã hoặc quận/huyện tại Hà Nội. Ví dụ: Cầu Giấy, Đống Đa"
    )


@tool(args_schema=ResolveLocationInput)
def resolve_location(location_hint: str) -> dict:
    """Tìm phường/xã hoặc quận/huyện từ tên gần đúng.

    DÙNG KHI: cần xác định chính xác ward_id trước khi gọi tool khác,
    hoặc khi user nhập tên địa điểm không chính xác.
    KHÔNG DÙNG KHI: các tool khác đã có tham số location_hint (tự resolve bên trong).
    Trả về: ward_id, ward_name_vi, district_name_vi hoặc thông báo lỗi.
    """
    from app.dal.location_dal import resolve_location_scoped
    from app.agent.dispatch import router_scope_var
    from app.agent.tools.output_builder import build_resolve_location_output
    return build_resolve_location_output(
        resolve_location_scoped(location_hint, target_scope=router_scope_var.get(None))
    )


# ============== Tool 2: get_current_weather ==============

class GetCurrentWeatherInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="ward_id (ví dụ: ID_00169)")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")


@tool(args_schema=GetCurrentWeatherInput)
def get_current_weather(ward_id: str = None, location_hint: str = None) -> dict:
    """SNAPSHOT thời tiết tại NOW. CHỈ 1 mốc thời gian duy nhất, KHÔNG phải dự báo.

    ⚠ TUYỆT ĐỐI KHÔNG dùng cho FUTURE query: "tối nay / sáng mai / cuối tuần / X ngày tới /
    chiều mai / đêm nay" — kết quả sẽ SAI vì snapshot 1 thời điểm KHÔNG đại diện cho khung
    tương lai. Dùng get_hourly_forecast (1-48h) hoặc get_daily_forecast (1-8 ngày) thay.
    Cũng KHÔNG dùng cho PAST query ("hôm qua"): dùng get_weather_history.

    DÙNG KHI: user dùng từ khoá SNAPSHOT thật sự:
        "bây giờ", "hiện tại", "đang", "lúc này", "vừa xong".

    KHÔNG DÙNG KHI (để tránh "reaching for the hammer"):
        - "chiều / tối / đêm / sáng mai / X giờ tối nay" → dùng get_hourly_forecast.
        - "ngày mai / thứ X / cuối tuần / 3 ngày tới" → dùng get_daily_forecast.
        - "cả ngày chi tiết sáng/trưa/chiều/tối" → dùng get_daily_summary.
        - "hôm qua / ngày đã qua" → dùng get_weather_history.
        - "max/min/đỉnh/mạnh nhất/cao nhất cả ngày" → dùng get_daily_summary (superlative
          từ snapshot CHỈ là 1 mốc, KHÔNG phải max cả ngày).
        - "so hôm nay vs ngày mai" → gọi CẢ current + get_daily_forecast(tomorrow), KHÔNG
          1 mình current rồi tự ngoại suy.

    Returns: Flat VN dict, value = "[nhãn] [số] [đơn vị]":
    - "địa điểm", "thời điểm" (HH:MM Thứ X NGÀY/THÁNG/NĂM), "thời tiết chung"
    - "nhiệt độ", "độ ẩm", "cảm giác" (CHỈ ward)
    - "điểm sương", "xác suất mưa" (từ forecast lân cận vì snapshot không có pop)
    - "gió" (avg + giật + hướng), "mây", "UV", "áp suất"
    - "cường độ mưa hiện tại" (CHỈ khi đang mưa)
    - "cảm giác nóng"/"cảm giác lạnh" (conditional theo ngưỡng)
    - "tầm nhìn" (CHỈ khi <5km), "tóm tắt"
    - "gợi ý dùng output": nếu xuất hiện → ĐỌC + làm theo.
    """
    from app.agent.dispatch import resolve_and_dispatch
    from app.agent.utils import enrich_weather_response, enrich_district_response, enrich_city_response
    from app.dal.weather_dal import get_current_weather as dal_ward
    from app.dal.weather_aggregate_dal import (
        get_district_current_weather as dal_district,
        get_city_current_weather as dal_city,
    )

    from app.agent.tools.output_builder import build_current_output
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=dal_ward,
        district_fn=lambda district_id: enrich_district_response(dal_district(district_id)),
        city_fn=lambda: enrich_city_response(dal_city()),
        enrich_fn=enrich_weather_response,  # Only applied to ward result
        label="thời tiết hiện tại",
    )
    return build_current_output(raw)


# ============== Tool 3: get_weather_alerts ==============

class GetWeatherAlertsInput(BaseModel):
    ward_id: Optional[str] = Field(default=None, description="ward_id (mặc định: tất cả)")
    location_hint: Optional[str] = Field(default=None, description="Tên phường/xã hoặc quận/huyện")


@tool(args_schema=GetWeatherAlertsInput)
def get_weather_alerts(ward_id: str = None, location_hint: str = None) -> dict:
    """Lấy CẢNH BÁO thời tiết NGUY HIỂM chuẩn trong 24h tới.

    DÙNG KHI: "có CẢNH BÁO gì không?", "thời tiết có nguy hiểm không?",
    "có giông bão không?", "có rét hại không?", "có nắng nóng gay gắt không?".

    KHÔNG DÙNG KHI:
        - "sắp có gì thay đổi không?" (biến động nhẹ, không nguy hiểm) → get_weather_change_alert.
        - "có nồm ẩm / gió mùa ĐB không?" (hiện tượng đặc trưng) → detect_phenomena.

    Hỗ trợ: phường/xã, quận/huyện, toàn Hà Nội. Mặc định: toàn thành phố.
    Trả về: danh sách cảnh báo (gió giật > 20m/s, rét hại < 13°C, nắng nóng > 39°C, giông).
    District-level dùng aggregate severity (max_wind_gust / min_temp / max_temp trong quận).
    """
    from app.agent.dispatch import resolve_and_dispatch
    from app.dal.alerts_dal import (
        get_weather_alerts as dal_ward_alerts,
        get_district_weather_alerts as dal_district_alerts,
    )
    from app.agent.tools.output_builder import build_weather_alerts_output

    # Bug B fix + R18 P1-5 follow-up: dispatch theo level. resolve_and_dispatch
    # tự handle resolve error (fuzzy/not_found → error dict với needs_clarification).
    raw = resolve_and_dispatch(
        ward_id=ward_id,
        location_hint=location_hint,
        default_scope="city",
        ward_fn=dal_ward_alerts,                  # signature: ward_id=... → List
        district_fn=dal_district_alerts,          # signature: district_id=... → List
        city_fn=lambda: dal_ward_alerts(None),    # ward_id=None → DAL city scan
        normalize=False,
        label="cảnh báo thời tiết",
    )

    # Error dict (location ambiguous / DAL error) → builder format error output.
    if isinstance(raw, dict) and raw.get("error"):
        return build_weather_alerts_output(raw)

    # Success: dispatch trả LIST khi DAL trả list.
    alerts = raw if isinstance(raw, list) else []
    return build_weather_alerts_output({"alerts": alerts, "count": len(alerts)})
