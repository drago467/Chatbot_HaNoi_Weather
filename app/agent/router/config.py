"""Router configuration — paths, thresholds, constants."""

import os
from pathlib import Path

# Project root
_ROOT = Path(__file__).resolve().parents[3]

# ── Model ──
GGUF_PATH = os.getenv(
    "SLM_MODEL_PATH",
    str(_ROOT / "model" / "router" / "Qwen2.5-1.5B-Instruct.Q8_0.gguf"),
)

# ── Ollama (primary inference backend) ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hanoi-weather-router")

# ── Thresholds ──
CONFIDENCE_THRESHOLD = float(os.getenv("SLM_CONFIDENCE_THRESHOLD", "0.75"))

# ── Feature flag ──
USE_SLM_ROUTER = os.getenv("USE_SLM_ROUTER", "false").lower() in ("true", "1", "yes")

# ── System prompt (same as training) ──
ROUTER_SYSTEM_PROMPT = """Phân loại intent và scope cho câu hỏi thời tiết Hà Nội. Trả về JSON.

## Intents:
- current_weather: thời tiết NGAY LÚC NÀY (nhiệt độ, trời nắng/mưa, chung chung)
- hourly_forecast: diễn biến CHI TIẾT THEO GIỜ trong ngày (không chỉ hỏi mưa)
- daily_forecast: dự báo NHIỀU NGÀY tới (3 ngày, tuần tới, cuối tuần)
- weather_overview: TỔNG QUAN, tóm tắt thời tiết hôm nay/ngày mai (không hỏi thông số cụ thể)
- rain_query: hỏi CÓ MƯA KHÔNG, mưa bao lâu, xác suất mưa, mưa lúc nào tạnh
- temperature_query: hỏi CỤ THỂ VỀ NHIỆT ĐỘ (bao nhiêu độ, nóng/lạnh thế nào)
- wind_query: hỏi CỤ THỂ VỀ GIÓ (gió mạnh không, hướng gió, tốc độ gió)
- humidity_fog_query: hỏi về ĐỘ ẨM, SƯƠNG MÙ, sương muối
- historical_weather: thời tiết NGÀY/TUẦN TRƯỚC, dữ liệu QUÁ KHỨ
- location_comparison: SO SÁNH thời tiết giữa các quận/phường/địa điểm
- activity_weather: thời tiết có PHÙ HỢP ĐỂ LÀM hoạt động X không (chạy bộ, picnic, du lịch)
- expert_weather_param: thông số KỸ THUẬT chuyên sâu (áp suất, tia UV, điểm sương, tầm nhìn)
- weather_alert: CẢNH BÁO, nguy hiểm, bão, ngập, thay đổi đột ngột
- seasonal_context: SO SÁNH với hôm qua/tuần trước, xu hướng, bất thường theo MÙA
- smalltalk_weather: chào hỏi, ngoài phạm vi (không phải Hà Nội), câu hỏi không liên quan thời tiết

## Scopes:
- city: toàn Hà Nội, hoặc KHÔNG NÓI RÕ địa điểm
- district: nhắc tên QUẬN/HUYỆN (Ba Đình, Cầu Giấy...) hoặc ĐỊA ĐIỂM NỔI TIẾNG thuộc quận (Hồ Gươm→Hoàn Kiếm, Lăng Bác→Ba Đình, Nội Bài→Sóc Sơn...)
- ward: nhắc tên PHƯỜNG/XÃ (Phường Dịch Vọng Hậu, Xã Tiên Dương...)"""

# ── Intents + Scopes (must match training data) ──
VALID_INTENTS = [
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
]
VALID_SCOPES = ["city", "district", "ward"]

# ── Convenience dict ──
ROUTER_CONFIG = {
    "gguf_path": GGUF_PATH,
    "ollama_base_url": OLLAMA_BASE_URL,
    "ollama_model": OLLAMA_MODEL,
    "confidence_threshold": CONFIDENCE_THRESHOLD,
    "use_slm_router": USE_SLM_ROUTER,
}
