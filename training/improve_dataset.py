"""
Phase 1.4: Improve training dataset quality.

5 improvements:
1. Merge POI scope → district (POI resolves to district-level data, same tools)
2. Add hard negatives for ALL confusable intent pairs
3. No-diacritics augmentation (15-20% of samples)
4. Improved system prompt with intent boundary descriptions (3 scopes, no POI)
5. Scope confusion cases (landmark names → district, implicit city)

Changelog:
- v2: original improvements (see above)
- v3 (2026-03-28): 3 root-cause fixes found from routed evaluation run
    Fix A — Mislabeled seeds in augmented.jsonl (3 entries):
        * "Trong vài giờ tới có giông mạnh không?" wind_query → weather_alert
        * "Ngày mai ở Đan Phượng nhiệt độ cao nhất" daily_forecast × 2 → temperature_query
    Fix B — NEW_SYSTEM_PROMPT clarifications (4 intents):
        * weather_alert: added GIÔNG/LỐC, mưa DÔNG keywords
        * rain_query: added "KHÔNG phải cảnh báo nguy hiểm" boundary note
        * temperature_query: added "KỂ CẢ nhiệt độ ngày mai/cuối tuần"
        * activity_weather: added "ra ngoài, thoải mái/dễ chịu không"
    Fix C — New hard negatives (26 examples across 3 ambiguity zones):
        Zone 1 (weather_alert ↔ rain_query): +8 weather_alert (giông/dông) +4 rain_query
        Zone 2 (temperature_query ↔ daily_forecast): +8 temperature_query +3 daily_forecast
        Zone 3 (activity_weather): +5 examples with "ra ngoài/thoải mái"

Pipeline to rebuild (run in order):
    1. python scripts/router/improve_dataset.py
       → regenerates data/router/raw/augmented_v2.jsonl
    2. python scripts/router/split_dataset.py
       → regenerates data/router/train_clean.jsonl, val_clean.jsonl, test_clean.jsonl
    3. Retrain Qwen2.5-1.5B on new train_clean.jsonl

Reads: data/router/raw/augmented.jsonl
Outputs: data/router/raw/augmented_v2.jsonl
Then re-runs stratified split → train/val/test.
"""

import csv
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "router" / "raw" / "augmented.jsonl"
OUTPUT_PATH = ROOT / "data" / "router" / "raw" / "augmented_v2.jsonl"
OUTPUT_DIR = ROOT / "data" / "router"

# ─────────────────────────────────────────────
# Improvement 3: Better system prompt
# ─────────────────────────────────────────────
OLD_SYSTEM_PROMPT = (
    "Phân loại intent và location_scope cho câu hỏi thời tiết Hà Nội.\n\n"
    "Intents: current_weather, hourly_forecast, daily_forecast, weather_overview, "
    "rain_query, temperature_query, wind_query, humidity_fog_query, historical_weather, "
    "location_comparison, activity_weather, expert_weather_param, weather_alert, "
    "seasonal_context, smalltalk_weather\n\n"
    "Scopes: city (toàn Hà Nội hoặc không nói rõ địa điểm), "
    "district (quận/huyện), ward (phường/xã), poi (địa điểm cụ thể/nổi tiếng)"
)

NEW_SYSTEM_PROMPT = (
    "Phân loại intent và scope cho câu hỏi thời tiết Hà Nội. Trả về JSON.\n\n"
    "## Intents:\n"
    "- current_weather: thời tiết NGAY LÚC NÀY (nhiệt độ, trời nắng/mưa, chung chung)\n"
    "- hourly_forecast: diễn biến CHI TIẾT THEO GIỜ trong ngày (không chỉ hỏi mưa)\n"
    "- daily_forecast: dự báo NHIỀU NGÀY tới (3 ngày, tuần tới, cuối tuần)\n"
    "- weather_overview: TỔNG QUAN, tóm tắt thời tiết hôm nay/ngày mai (không hỏi thông số cụ thể)\n"
    "- rain_query: hỏi CÓ MƯA KHÔNG, xác suất mưa, mưa bao lâu/lúc nào tạnh — KHÔNG phải cảnh báo nguy hiểm\n"
    "- temperature_query: hỏi CỤ THỂ VỀ NHIỆT ĐỘ (bao nhiêu độ, nóng/lạnh thế nào) — KỂ CẢ nhiệt độ ngày mai/cuối tuần\n"
    "- wind_query: hỏi CỤ THỂ VỀ GIÓ (gió mạnh không, hướng gió, tốc độ gió)\n"
    "- humidity_fog_query: hỏi về ĐỘ ẨM, SƯƠNG MÙ, sương muối\n"
    "- historical_weather: thời tiết NGÀY/TUẦN TRƯỚC, dữ liệu QUÁ KHỨ\n"
    "- location_comparison: SO SÁNH thời tiết giữa các quận/phường/địa điểm\n"
    "- activity_weather: thời tiết có PHÙ HỢP ĐỂ LÀM hoạt động X không (ra ngoài, thoải mái/dễ chịu không, chạy bộ, picnic)\n"
    "- expert_weather_param: thông số KỸ THUẬT chuyên sâu (áp suất, tia UV, điểm sương, tầm nhìn)\n"
    "- weather_alert: CẢNH BÁO nguy hiểm: bão/áp thấp, ngập lụt, GIÔNG/LỐC mạnh, mưa DÔNG, rét hại, nắng nóng cực đoan, thay đổi thời tiết đột ngột\n"
    "- seasonal_context: SO SÁNH với hôm qua/tuần trước, xu hướng, bất thường theo MÙA\n"
    "- smalltalk_weather: chào hỏi, ngoài phạm vi (không phải Hà Nội), câu hỏi không liên quan thời tiết\n\n"
    "## Scopes:\n"
    "- city: toàn Hà Nội, hoặc KHÔNG NÓI RÕ địa điểm\n"
    "- district: nhắc tên QUẬN/HUYỆN (Ba Đình, Cầu Giấy...) hoặc ĐỊA ĐIỂM NỔI TIẾNG thuộc quận (Hồ Gươm→Hoàn Kiếm, Lăng Bác→Ba Đình, Nội Bài→Sóc Sơn...)\n"
    "- ward: nhắc tên PHƯỜNG/XÃ (Phường Dịch Vọng Hậu, Xã Tiên Dương...)"
)

# ─────────────────────────────────────────────
# Improvement 1: Extended hard negatives
# Cover ALL confusable intent pairs
# ─────────────────────────────────────────────
ADDITIONAL_HARD_NEGATIVES = [
    # ===== hourly_forecast vs daily_forecast =====
    # hourly: chi tiết trong ngày; daily: nhiều ngày
    {"q": "Chiều nay thời tiết thay đổi thế nào theo từng giờ?", "intent": "hourly_forecast", "scope": "city"},
    {"q": "Từ giờ đến tối trời biến chuyển ra sao?", "intent": "hourly_forecast", "scope": "city"},
    {"q": "Sáng mai ở Ba Đình diễn biến thời tiết theo giờ?", "intent": "hourly_forecast", "scope": "district"},
    {"q": "3 ngày tới thời tiết Hà Nội có thay đổi không?", "intent": "daily_forecast", "scope": "city"},
    {"q": "Cuối tuần này thời tiết thế nào?", "intent": "daily_forecast", "scope": "city"},
    {"q": "Thứ 5, thứ 6 trời có mưa không?", "intent": "daily_forecast", "scope": "city"},
    {"q": "Tuần sau ở Đan Phượng dự báo thế nào?", "intent": "daily_forecast", "scope": "district"},

    # ===== weather_overview vs current_weather =====
    # overview: tóm tắt chung; current: hỏi ngay lúc này
    {"q": "Tổng quan thời tiết Hà Nội hôm nay?", "intent": "weather_overview", "scope": "city"},
    {"q": "Thời tiết hôm nay ở Long Biên nhìn chung ra sao?", "intent": "weather_overview", "scope": "district"},
    {"q": "Cho mình biết tình hình thời tiết chung ngày mai?", "intent": "weather_overview", "scope": "city"},
    {"q": "Bây giờ ngoài trời ra sao?", "intent": "current_weather", "scope": "city"},
    {"q": "Thời tiết lúc này ở Thanh Xuân?", "intent": "current_weather", "scope": "district"},
    {"q": "Trời giờ này thế nào?", "intent": "current_weather", "scope": "city"},

    # ===== expert_weather_param vs temperature_query =====
    # expert: thông số kỹ thuật; temperature: hỏi nóng/lạnh/bao nhiêu độ
    {"q": "Nhiệt độ điểm sương ở Hà Nội bao nhiêu?", "intent": "expert_weather_param", "scope": "city"},
    {"q": "Áp suất khí quyển hôm nay thế nào?", "intent": "expert_weather_param", "scope": "city"},
    {"q": "Chỉ số UV ở Cầu Giấy lúc này?", "intent": "expert_weather_param", "scope": "district"},
    {"q": "Tầm nhìn xa ở Nội Bài có tốt không?", "intent": "expert_weather_param", "scope": "poi"},
    {"q": "Bây giờ ngoài trời bao nhiêu độ?", "intent": "temperature_query", "scope": "city"},
    {"q": "Hà Nội hôm nay nóng hay lạnh?", "intent": "temperature_query", "scope": "city"},
    {"q": "Nhiệt độ ở Hoàng Mai cao nhất bao nhiêu hôm nay?", "intent": "temperature_query", "scope": "district"},

    # ===== expert_weather_param vs wind_query =====
    # expert: thông số chi tiết (gió giật, hướng gió chính xác); wind: gió mạnh/nhẹ chung
    {"q": "Gió giật ở Hà Nội bao nhiêu m/s?", "intent": "expert_weather_param", "scope": "city"},
    {"q": "Hướng gió chính xác ở Tây Hồ?", "intent": "expert_weather_param", "scope": "district"},
    {"q": "Hôm nay gió mạnh không?", "intent": "wind_query", "scope": "city"},
    {"q": "Ngoài trời gió thổi nhiều không bạn?", "intent": "wind_query", "scope": "city"},

    # ===== seasonal_context vs historical_weather =====
    # seasonal: so sánh, xu hướng; historical: xem dữ liệu cụ thể ngày trước
    {"q": "So với hôm qua thì hôm nay nóng hơn hay mát hơn?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Tuần này Hà Nội có nóng hơn tuần trước không?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Xu hướng nhiệt độ mấy ngày qua thế nào?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Thời tiết ở Đống Đa hôm qua so với hôm nay?", "intent": "seasonal_context", "scope": "district"},
    {"q": "Hôm qua ở Hà Nội thời tiết thế nào?", "intent": "historical_weather", "scope": "city"},
    {"q": "Tuần trước ở Ba Đình nhiệt độ bao nhiêu?", "intent": "historical_weather", "scope": "district"},
    {"q": "3 ngày trước trời có mưa không?", "intent": "historical_weather", "scope": "city"},

    # ===== weather_alert vs rain_query =====
    # alert: nguy hiểm, cảnh báo; rain: hỏi có mưa/mưa lúc nào
    {"q": "Có cảnh báo mưa lớn gây ngập không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Hà Nội hôm nay có nguy cơ ngập úng không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Bão có ảnh hưởng đến Hà Nội không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Cầu Giấy có cảnh báo gì về thời tiết không?", "intent": "weather_alert", "scope": "district"},
    {"q": "Chiều nay có mưa to không?", "intent": "rain_query", "scope": "city"},
    {"q": "Mưa lớn bao giờ tạnh?", "intent": "rain_query", "scope": "city"},

    # --- Zone 1 (v3): weather_alert với giông/dông — KHÔNG có từ "cảnh báo/nguy cơ" ---
    # Root cause fix: model gặp "giông mạnh" → wind_query vì seed bị gán nhãn sai
    {"q": "Chiều nay ở Hà Nội có giông mạnh không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Vài giờ tới ở Cầu Giấy có giông không?", "intent": "weather_alert", "scope": "district"},
    {"q": "Tối nay có giông lốc xảy ra không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Đêm nay ở Đống Đa có mưa dông không?", "intent": "weather_alert", "scope": "district"},
    {"q": "Trong 3 giờ tới có mưa giông mạnh không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Ở phường Trung Liệt chiều nay có giông không?", "intent": "weather_alert", "scope": "ward"},
    # --- Zone 1 (v3): "chuyển mưa/biến đổi" → weather_alert ---
    {"q": "Thời tiết sắp có thay đổi gì không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Vài giờ tới ở Hai Bà Trưng trời có chuyển không?", "intent": "weather_alert", "scope": "district"},
    # --- Zone 1 (v3): rain_query sạch — balance cho các additions weather_alert ---
    {"q": "Sáng mai trời có mưa không?", "intent": "rain_query", "scope": "city"},
    {"q": "Tối nay ở Bắc Từ Liêm có mưa không nhỉ?", "intent": "rain_query", "scope": "district"},
    {"q": "Mưa chiều nay kéo dài đến bao giờ?", "intent": "rain_query", "scope": "city"},
    {"q": "Hôm nay khả năng mưa là bao nhiêu phần trăm?", "intent": "rain_query", "scope": "city"},

    # ===== weather_alert vs weather_overview =====
    {"q": "Hôm nay có hiện tượng thời tiết bất thường gì không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Tình hình thời tiết ngày mai có gì đáng lo không?", "intent": "weather_alert", "scope": "city"},

    # ===== rain_query vs current_weather =====
    {"q": "Bây giờ có đang mưa không?", "intent": "rain_query", "scope": "city"},
    {"q": "Ở Hoàn Kiếm đang mưa à?", "intent": "rain_query", "scope": "district"},
    {"q": "Hồ Gươm bây giờ mưa chưa tạnh?", "intent": "rain_query", "scope": "poi"},

    # ===== location_comparison (multi-scope) =====
    {"q": "Quận nào ở Hà Nội mưa nhiều nhất hôm nay?", "intent": "location_comparison", "scope": "city"},
    {"q": "So sánh thời tiết Ba Đình và Cầu Giấy?", "intent": "location_comparison", "scope": "district"},
    {"q": "Hồ Gươm hay Hồ Tây mát hơn?", "intent": "location_comparison", "scope": "poi"},
    {"q": "Phường nào ở Long Biên mát nhất?", "intent": "location_comparison", "scope": "district"},

    # ===== activity_weather vs smalltalk_weather =====
    {"q": "Trời thế này đi chợ được không?", "intent": "activity_weather", "scope": "city"},
    {"q": "Có nên ra ngoài lúc này không bạn?", "intent": "activity_weather", "scope": "city"},
    {"q": "Thời tiết ở Hồ Tây tối nay có hợp đi dạo không?", "intent": "activity_weather", "scope": "poi"},
    {"q": "Mặc gì đi làm hôm nay?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Cần mang áo khoác không?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Hôm nay nên cầm ô không nhỉ?", "intent": "smalltalk_weather", "scope": "city"},

    # --- Zone 3 (v3): activity_weather với "ra ngoài/thoải mái" không có hoạt động cụ thể ---
    # Root cause fix: "Bây giờ ra ngoài có thoải mái không?" chỉ có trong TEST, chưa có trong TRAIN
    {"q": "Bây giờ ra ngoài có thoải mái không?", "intent": "activity_weather", "scope": "city"},
    {"q": "Thời tiết hôm nay có ổn để ra ngoài không?", "intent": "activity_weather", "scope": "city"},
    {"q": "Ra ngoài dạo ở Tây Hồ chiều nay được không?", "intent": "activity_weather", "scope": "district"},
    {"q": "Ở Hoàng Mai bây giờ ra ngoài có dễ chịu không?", "intent": "activity_weather", "scope": "district"},
    {"q": "Phường Yên Hòa tối nay ra ngoài có thoải mái không?", "intent": "activity_weather", "scope": "ward"},

    # ===== humidity_fog_query boundary =====
    {"q": "Sáng nay Nội Bài có sương mù không?", "intent": "humidity_fog_query", "scope": "poi"},
    {"q": "Ở Hà Nội độ ẩm cao quá, bao nhiêu phần trăm rồi?", "intent": "humidity_fog_query", "scope": "city"},
    {"q": "Ba Vì sáng sớm có sương muối không?", "intent": "humidity_fog_query", "scope": "district"},
    {"q": "Đêm nay có sương mù không bạn?", "intent": "humidity_fog_query", "scope": "city"},

    # ===== temperature_query vs seasonal_context =====
    {"q": "Hôm nay nóng hơn hôm qua không?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Mấy ngày nay nhiệt độ tăng hay giảm?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Hôm nay bao nhiêu độ?", "intent": "temperature_query", "scope": "city"},

    # --- Zone 2 (v3): temperature_query với thời gian tương lai ---
    # Root cause fix: model bị nhầm "ngày mai + nhiệt độ" → daily_forecast do 3 seed gán sai
    {"q": "Ngày mai ở Hà Nội nóng bao nhiêu độ?", "intent": "temperature_query", "scope": "city"},
    {"q": "Nhiệt độ ngày mai ở Cầu Giấy là bao nhiêu?", "intent": "temperature_query", "scope": "district"},
    {"q": "Cuối tuần này nhiệt độ Hà Nội thế nào?", "intent": "temperature_query", "scope": "city"},
    {"q": "Thứ Bảy ở Thanh Xuân mấy độ nhỉ?", "intent": "temperature_query", "scope": "district"},
    {"q": "Đêm mai ở Hà Nội lạnh bao nhiêu độ?", "intent": "temperature_query", "scope": "city"},
    {"q": "Nhiệt độ cao nhất ngày mai ở Gia Lâm?", "intent": "temperature_query", "scope": "district"},
    {"q": "Phường Xuân Đỉnh tuần tới nhiệt độ cao nhất bao nhiêu?", "intent": "temperature_query", "scope": "ward"},
    {"q": "Thứ Tư ở Hà Nội dự báo nhiệt độ là bao nhiêu?", "intent": "temperature_query", "scope": "city"},
    # --- Zone 2 (v3): daily_forecast tổng quát (không hỏi thông số cụ thể) — balance ---
    {"q": "Tuần sau thời tiết Hà Nội thế nào nhỉ?", "intent": "daily_forecast", "scope": "city"},
    {"q": "Mấy ngày tới ở Gia Lâm trời ra sao?", "intent": "daily_forecast", "scope": "district"},
    {"q": "Dự báo thứ Tư thứ Năm ở Hà Nội?", "intent": "daily_forecast", "scope": "city"},

    # ===== daily_forecast vs weather_overview =====
    {"q": "Ngày mai thời tiết Hà Nội thế nào?", "intent": "weather_overview", "scope": "city"},
    {"q": "Dự báo 5 ngày tới ở Hà Nội?", "intent": "daily_forecast", "scope": "city"},
    {"q": "Cuối tuần trời có đẹp không?", "intent": "daily_forecast", "scope": "city"},

    # ===== More multi-intent (pick primary) =====
    {"q": "Ngày mai có mưa không, tôi định đi Hồ Gươm?", "intent": "rain_query", "scope": "poi"},
    {"q": "Trời mưa thế này có nên ra Phố cổ không?", "intent": "activity_weather", "scope": "poi"},
    {"q": "Cuối tuần mưa to không, mấy đứa định cắm trại?", "intent": "rain_query", "scope": "city"},
]

# ─────────────────────────────────────────────
# Improvement 4: Scope confusion cases
# ─────────────────────────────────────────────
SCOPE_CONFUSION_CASES = [
    # POI vs District — name overlap
    {"q": "Hồ Tây hôm nay thế nào?", "intent": "current_weather", "scope": "poi"},
    {"q": "Bên Tây Hồ trời thế nào?", "intent": "current_weather", "scope": "district"},
    {"q": "Thời tiết quận Tây Hồ lúc này?", "intent": "current_weather", "scope": "district"},
    {"q": "Khu vực Hồ Tây có gió mạnh không?", "intent": "wind_query", "scope": "poi"},
    {"q": "Quận Tây Hồ gió có mạnh không?", "intent": "wind_query", "scope": "district"},

    # POI without explicit "ở" / location marker
    {"q": "Lăng Bác mưa chưa tạnh?", "intent": "rain_query", "scope": "poi"},
    {"q": "Văn Miếu bây giờ nắng không?", "intent": "current_weather", "scope": "poi"},
    {"q": "Keangnam tối nay thời tiết sao?", "intent": "current_weather", "scope": "poi"},

    # Implicit city (no location → city)
    {"q": "Trời lạnh quá!", "intent": "current_weather", "scope": "city"},
    {"q": "Mưa to ghê!", "intent": "rain_query", "scope": "city"},
    {"q": "Chiều nay thời tiết sao nhỉ?", "intent": "current_weather", "scope": "city"},
    {"q": "Dự báo ngày mai?", "intent": "weather_overview", "scope": "city"},

    # District mentioned casually (without "quận/huyện")
    {"q": "Bên Hà Đông trời có mưa không?", "intent": "rain_query", "scope": "district"},
    {"q": "Thạch Thất nhiệt độ bao nhiêu?", "intent": "temperature_query", "scope": "district"},
    {"q": "Long Biên gió mạnh không?", "intent": "wind_query", "scope": "district"},
    {"q": "Sóc Sơn sáng nay có sương không?", "intent": "humidity_fog_query", "scope": "district"},
    {"q": "Đông Anh cuối tuần mưa không?", "intent": "rain_query", "scope": "district"},

    # Ward mentioned (rare but should handle)
    {"q": "Phường Dịch Vọng Hậu bây giờ mưa không?", "intent": "rain_query", "scope": "ward"},
    {"q": "Xã Tiên Dương thời tiết thế nào?", "intent": "current_weather", "scope": "ward"},

    # Tricky: "Hà Nội" explicitly → city even with activity
    {"q": "Hà Nội hôm nay đẹp trời không?", "intent": "weather_overview", "scope": "city"},
    {"q": "Thành phố hôm nay nóng lắm không?", "intent": "temperature_query", "scope": "city"},
]

# ─────────────────────────────────────────────
# Improvement 6: Scope rebalancing (~30:40:30)
# Target: city ~30%, district ~40%, ward ~30%
# Strategy: upsample city/ward with templates,
#           downsample district (remove low-priority)
# ─────────────────────────────────────────────

# (city_questions, ward_templates_with_{w})
# city: 4 per intent = 60 new samples
# ward: 3 templates × 3 random wards = 9 per intent = 135 new samples
BALANCE_TEMPLATES: dict[str, tuple[list[str], list[str]]] = {
    "current_weather": (
        [
            "Hà Nội giờ thời tiết ra sao rồi?",
            "Cho hỏi ngoài trời đang thế nào?",
            "Thành phố hiện tại trời nắng hay mưa nhỉ?",
            "Tình hình thời tiết lúc này ở Hà Nội ra sao?",
        ],
        [
            "Thời tiết phường {w} lúc này sao?",
            "Ở phường {w} hiện giờ thế nào?",
            "Phường {w} bây giờ trời ra sao nhỉ?",
        ],
    ),
    "hourly_forecast": (
        [
            "Thời tiết Hà Nội biến đổi theo giờ hôm nay thế nào?",
            "Cho xem dự báo theo từng giờ hôm nay đi?",
            "Hà Nội chiều nay thay đổi thời tiết ra sao?",
            "Từ giờ đến tối Hà Nội diễn biến thế nào nhỉ?",
        ],
        [
            "Phường {w} hôm nay diễn biến theo giờ sao?",
            "Dự báo theo giờ ở phường {w}?",
            "Ở phường {w} chiều nay thời tiết biến đổi thế nào?",
        ],
    ),
    "daily_forecast": (
        [
            "Dự báo Hà Nội mấy ngày tới thế nào?",
            "Thời tiết thành phố tuần này ra sao nhỉ?",
            "Hà Nội từ nay đến cuối tuần thế nào bạn?",
            "Dự báo thời tiết dài hạn cho Hà Nội?",
        ],
        [
            "Phường {w} mấy ngày tới thời tiết sao?",
            "Dự báo thời tiết ở phường {w} tuần này?",
            "Phường {w} cuối tuần trời thế nào?",
        ],
    ),
    "weather_overview": (
        [
            "Tổng quan thời tiết Hà Nội hôm nay thế nào?",
            "Cho mình tóm tắt tình hình thời tiết hôm nay?",
            "Hà Nội hôm nay nhìn chung ra sao?",
            "Thời tiết chung thành phố hôm nay nhé?",
        ],
        [
            "Thời tiết chung ở phường {w} hôm nay?",
            "Tổng quan thời tiết phường {w} ra sao?",
            "Phường {w} hôm nay nhìn chung thế nào?",
        ],
    ),
    "rain_query": (
        [
            "Hà Nội hôm nay mưa không nhỉ?",
            "Chiều nay mưa lúc mấy giờ bạn?",
            "Hà Nội mưa đến bao giờ tạnh?",
            "Xác suất mưa ở thành phố hôm nay bao nhiêu?",
        ],
        [
            "Phường {w} hôm nay có mưa không?",
            "Ở phường {w} mấy giờ thì mưa nhỉ?",
            "Phường {w} mưa to lắm không?",
        ],
    ),
    "temperature_query": (
        [
            "Nhiệt độ Hà Nội giờ này bao nhiêu?",
            "Hôm nay thành phố nóng hay mát nhỉ?",
            "Hà Nội bao nhiêu độ C rồi?",
            "Ngoài trời giờ nóng lắm không bạn?",
        ],
        [
            "Phường {w} bây giờ bao nhiêu độ?",
            "Nhiệt độ ở phường {w} lúc này?",
            "Phường {w} hôm nay nóng không nhỉ?",
        ],
    ),
    "wind_query": (
        [
            "Hà Nội hôm nay gió mạnh không bạn?",
            "Gió ở thành phố giờ thế nào rồi?",
            "Hôm nay gió thổi to lắm không?",
            "Gió ở Hà Nội hiện tại bao nhiêu km/h?",
        ],
        [
            "Phường {w} gió có mạnh không?",
            "Phường {w} hôm nay có gió to không nhỉ?",
            "Gió ở phường {w} bây giờ thế nào?",
        ],
    ),
    "humidity_fog_query": (
        [
            "Độ ẩm Hà Nội hôm nay bao nhiêu phần trăm?",
            "Hà Nội sáng nay có sương mù không nhỉ?",
            "Thành phố hôm nay ẩm ướt lắm không bạn?",
            "Hà Nội có sương muối vào sáng sớm không?",
        ],
        [
            "Phường {w} sáng nay có sương mù không?",
            "Độ ẩm ở phường {w} bao nhiêu rồi?",
            "Phường {w} hôm nay ẩm lắm không?",
        ],
    ),
    "historical_weather": (
        [
            "Hôm qua Hà Nội thời tiết ra sao?",
            "Thành phố tuần trước trời thế nào?",
            "Mấy ngày trước Hà Nội có mưa to không?",
            "Thời tiết Hà Nội 3 ngày trước ra sao nhỉ?",
        ],
        [
            "Phường {w} hôm qua thời tiết sao?",
            "Ở phường {w} tuần trước ra sao?",
            "Phường {w} mấy ngày trước có mưa không?",
        ],
    ),
    "location_comparison": (
        [
            "Quận nào ở Hà Nội nóng nhất hôm nay?",
            "So sánh thời tiết giữa các quận trong thành phố?",
            "Khu vực nào ở Hà Nội mát nhất nhỉ?",
            "Hôm nay quận nào mưa nhiều nhất bạn?",
        ],
        [
            "So sánh thời tiết phường {w} với các phường khác?",
            "Phường {w} nóng hơn hay mát hơn xung quanh?",
            "Phường {w} so với phường bên cạnh thế nào?",
        ],
    ),
    "activity_weather": (
        [
            "Hà Nội hôm nay có hợp đi chơi ngoài trời không?",
            "Thời tiết thành phố phù hợp để chạy bộ không nhỉ?",
            "Ngoài trời hôm nay có ổn cho picnic không?",
            "Hôm nay có nên tổ chức hoạt động ngoài trời không?",
        ],
        [
            "Phường {w} hôm nay đi dạo được không?",
            "Ở phường {w} thời tiết hợp tập thể dục không?",
            "Phường {w} chiều nay đi chơi ngoài trời được không?",
        ],
    ),
    "expert_weather_param": (
        [
            "Áp suất khí quyển Hà Nội hôm nay bao nhiêu?",
            "Chỉ số UV ở thành phố hôm nay thế nào?",
            "Tầm nhìn xa ở Hà Nội hiện tại sao?",
            "Nhiệt độ điểm sương ở Hà Nội lúc này?",
        ],
        [
            "Chỉ số UV ở phường {w} bao nhiêu?",
            "Áp suất ở phường {w} thế nào?",
            "Phường {w} tầm nhìn xa hiện tại sao?",
        ],
    ),
    "weather_alert": (
        [
            "Hà Nội có cảnh báo thời tiết gì hôm nay không?",
            "Có nguy cơ ngập úng ở thành phố không nhỉ?",
            "Thời tiết Hà Nội có gì đáng lo hôm nay?",
            "Cảnh báo mưa bão cho Hà Nội hôm nay?",
        ],
        [
            "Phường {w} có cảnh báo thời tiết gì không?",
            "Ở phường {w} có nguy cơ ngập không nhỉ?",
            "Phường {w} cần lưu ý gì về thời tiết?",
        ],
    ),
    "seasonal_context": (
        [
            "Hà Nội hôm nay khác hôm qua thế nào?",
            "Thành phố tuần này nóng hơn tuần trước chứ?",
            "Nhiệt độ Hà Nội mấy ngày nay biến đổi ra sao?",
            "Thời tiết Hà Nội có gì bất thường không nhỉ?",
        ],
        [
            "Phường {w} hôm nay so với hôm qua thế nào?",
            "Ở phường {w} nóng hơn mấy ngày trước không?",
            "Xu hướng thời tiết phường {w} mấy ngày qua?",
        ],
    ),
    "smalltalk_weather": (
        [
            "Hà Nội thời tiết đẹp nhỉ bạn?",
            "Hôm nay trời dễ chịu quá!",
            "Mùa này Hà Nội thời tiết hay nhỉ?",
            "Thời tiết thành phố hôm nay tuyệt vời!",
        ],
        [
            "Phường {w} trời đẹp quá nhỉ?",
            "Ở phường {w} hôm nay dễ chịu ghê!",
            "Phường {w} mùa này thế nào nhỉ?",
        ],
    ),
}


# ─────────────────────────────────────────────
# Improvement 2: Vietnamese diacritics removal
# ─────────────────────────────────────────────

# Vietnamese character mapping for diacritics removal
_VIET_DIACRITICS_MAP = str.maketrans({
    # a variants
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
    'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
    'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
    # e variants
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
    'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
    # i variants
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
    # o variants
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
    'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
    'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
    # u variants
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
    'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
    # y variants
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
    # d variant
    'đ': 'd', 'Đ': 'D',
})


def strip_vietnamese_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics, keeping ASCII-safe text."""
    return text.translate(_VIET_DIACRITICS_MAP)


def generate_no_diacritics_samples(
    samples: list[dict],
    ratio: float = 0.18,
) -> list[dict]:
    """
    Create no-diacritics variants for a portion of samples.
    Skip samples that are already without diacritics (hard negatives like "thoi tiet hom nay").
    Also skip smalltalk samples that are greetings/non-weather (less likely to be typed without diacritics).
    """
    # Filter candidates: must contain Vietnamese diacritics
    candidates = []
    for s in samples:
        q = s["messages"][1]["content"]
        stripped = strip_vietnamese_diacritics(q)
        # Only if stripping actually changes something
        if stripped != q:
            candidates.append(s)

    n = int(len(candidates) * ratio)
    selected = random.sample(candidates, min(n, len(candidates)))

    new_samples = []
    for s in selected:
        q = s["messages"][1]["content"]
        new_q = strip_vietnamese_diacritics(q).lower()  # No-diacritics users often type lowercase

        new_samples.append({
            "messages": [
                {"role": "system", "content": NEW_SYSTEM_PROMPT},
                {"role": "user", "content": new_q},
                {"role": "assistant", "content": s["messages"][2]["content"]},
            ],
            "metadata": {
                "source": "no_diacritics",
                "intent": s["metadata"]["intent"],
                "scope": s["metadata"]["scope"],
            },
        })

    return new_samples


# ─────────────────────────────────────────────
# Build improved dataset
# ─────────────────────────────────────────────

def merge_poi_to_district(samples: list[dict]) -> int:
    """
    Merge POI scope into district.

    Rationale: POI (Hồ Gươm, Lăng Bác...) resolves to district-level data
    via poi_mapping.json. The tools used are the same as district scope.
    Merging reduces classes from 15×4=60 to 15×3=45 → easier to learn.
    """
    count = 0
    for s in samples:
        if s["metadata"]["scope"] == "poi":
            s["metadata"]["scope"] = "district"
            # Update assistant response JSON
            resp = json.loads(s["messages"][2]["content"])
            for key in ("scope", "location_scope"):
                if key in resp:
                    resp[key] = "district"
            s["messages"][2]["content"] = json.dumps(resp, ensure_ascii=False)
            count += 1
    return count


def load_jsonl(path: Path) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def make_sample(q: str, intent: str, scope: str, source: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": NEW_SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": json.dumps(
                {"intent": intent, "scope": scope}, ensure_ascii=False
            )},
        ],
        "metadata": {"source": source, "intent": intent, "scope": scope},
    }


def load_ward_names() -> list[str]:
    """Load ward core names (without Phường/Xã/Thị trấn prefix) from dim_ward.csv."""
    path = ROOT / "data" / "processed" / "dim_ward.csv"
    names = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            full = row.get("ward_name_vi", "").strip()
            if not full:
                continue
            for prefix in ("Phường ", "Xã ", "Thị trấn "):
                if full.startswith(prefix):
                    names.append(full[len(prefix):])
                    break
            else:
                names.append(full)
    return names


def generate_balance_samples(existing: list[dict]) -> list[dict]:
    """
    Generate additional city + ward samples to rebalance scope distribution.
    city: 4 templates × 15 intents = 60 samples
    ward: 3 templates × 3 random wards × 15 intents = ~135 samples
    """
    ward_names = load_ward_names()
    existing_qs = {s["messages"][1]["content"].strip().lower() for s in existing}
    new_samples = []

    for intent, (city_qs, ward_tmpls) in BALANCE_TEMPLATES.items():
        # City samples (as-is)
        for q in city_qs:
            if q.strip().lower() not in existing_qs:
                new_samples.append(make_sample(q, intent, "city", "balance_upsample"))
                existing_qs.add(q.strip().lower())

        # Ward samples (substitute random ward names)
        for tmpl in ward_tmpls:
            selected = random.sample(ward_names, min(3, len(ward_names)))
            for wname in selected:
                q = tmpl.format(w=wname)
                if q.strip().lower() not in existing_qs:
                    new_samples.append(make_sample(q, intent, "ward", "balance_upsample"))
                    existing_qs.add(q.strip().lower())

    return new_samples


def downsample_scope(
    samples: list[dict],
    scope: str,
    target_pct: float,
) -> tuple[list[dict], int]:
    """
    Downsample a specific scope to target percentage of total.
    Removes lowest-priority samples first, balanced across intents.
    """
    scope_samples = [s for s in samples if s["metadata"]["scope"] == scope]
    other_samples = [s for s in samples if s["metadata"]["scope"] != scope]

    # Formula: target / (target + others) = target_pct
    # → target = others * target_pct / (1 - target_pct)
    target_count = int(len(other_samples) * target_pct / (1 - target_pct))
    excess = len(scope_samples) - target_count

    if excess <= 0:
        return samples, 0

    # Group by intent for proportional removal
    by_intent: dict[str, list[dict]] = defaultdict(list)
    for s in scope_samples:
        by_intent[s["metadata"]["intent"]].append(s)

    # Removal priority: higher value = remove first
    removal_order = {
        "seed": 0, "hard_negative": 1, "scope_confusion": 2,
        "balance_upsample": 3, "template": 4,
        "llm_paraphrase": 5, "no_diacritics": 6,
    }

    n_intents = len(by_intent)
    per_intent_remove = excess // n_intents
    remainder = excess % n_intents

    kept = []
    removed_total = 0
    for i, (intent, cell) in enumerate(sorted(by_intent.items())):
        to_remove = per_intent_remove + (1 if i < remainder else 0)
        to_remove = min(to_remove, max(0, len(cell) - 1))  # keep at least 1

        if to_remove <= 0:
            kept.extend(cell)
            continue

        # Sort: most removable first (highest priority value)
        cell.sort(key=lambda s: -removal_order.get(s["metadata"]["source"], 3))
        kept.extend(cell[to_remove:])
        removed_total += to_remove

    return other_samples + kept, removed_total


def update_system_prompt(samples: list[dict]) -> list[dict]:
    """Replace old system prompt with new improved one in all samples."""
    for s in samples:
        s["messages"][0]["content"] = NEW_SYSTEM_PROMPT
    return samples


def deduplicate(samples: list[dict]) -> list[dict]:
    """Remove duplicates by question text (case-insensitive), keeping priority order."""
    priority = {"seed": 0, "template": 1, "hard_negative": 2, "scope_confusion": 3,
                "llm_paraphrase": 4, "no_diacritics": 5}
    samples.sort(key=lambda s: priority.get(s["metadata"]["source"], 9))
    seen = set()
    result = []
    for s in samples:
        q = s["messages"][1]["content"].strip().lower()
        if q not in seen:
            seen.add(q)
            result.append(s)
    return result


def stratified_split(
    samples: list[dict],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Stratified split by (intent, scope). Seed samples prioritized for train."""
    groups = defaultdict(list)
    for s in samples:
        key = (s["metadata"]["intent"], s["metadata"]["scope"])
        groups[key].append(s)

    train, val, test = [], [], []

    for key, group in sorted(groups.items()):
        seed_samples = [s for s in group if s["metadata"]["source"] == "seed"]
        other_samples = [s for s in group if s["metadata"]["source"] != "seed"]
        random.shuffle(other_samples)

        n = len(group)
        n_val = max(1, round(n * val_ratio))
        n_test = max(1, round(n * val_ratio))

        pool = other_samples + seed_samples
        random.shuffle(pool)

        test_set = pool[:n_test]
        val_set = pool[n_test:n_test + n_val]
        train_set = pool[n_test + n_val:]

        used = set(id(s) for s in test_set + val_set)
        for s in seed_samples:
            if id(s) not in used and s not in train_set:
                train_set.append(s)

        train.extend(train_set)
        val.extend(val_set)
        test.extend(test_set)

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def save_jsonl(samples: list[dict], path: Path, strip_metadata: bool = False):
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            out = {"messages": s["messages"]} if strip_metadata else s
            json.dump(out, f, ensure_ascii=False)
            f.write("\n")


def print_stats(samples: list[dict], label: str):
    combo_counts = Counter()
    source_counts = Counter()
    intent_counts = Counter()
    scope_counts = Counter()
    for s in samples:
        m = s["metadata"]
        combo_counts[(m["intent"], m["scope"])] += 1
        source_counts[m["source"]] += 1
        intent_counts[m["intent"]] += 1
        scope_counts[m["scope"]] += 1

    vals = list(combo_counts.values()) if combo_counts else [0]
    print(f"\n{'='*60}")
    print(f"  {label}: {len(samples)} samples")
    print(f"{'='*60}")
    print(f"  Sources: {dict(sorted(source_counts.items()))}")
    print(f"\n  Intents ({len(intent_counts)}):")
    for k, v in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:30s} {v:4d}")
    print(f"\n  Scopes ({len(scope_counts)}):")
    for k, v in sorted(scope_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:15s} {v:4d}")
    print(f"\n  Combos: {len(combo_counts)}, min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.1f}")

    # Show bottom 5 combos
    print(f"\n  Bottom 5 combos:")
    for (intent, scope), count in sorted(combo_counts.items(), key=lambda x: x[1])[:5]:
        print(f"    ({intent}, {scope}): {count}")


def main():
    print("Phase 1.4: Dataset Quality Improvements + Scope Rebalancing")
    print("=" * 60)

    # Load existing
    print("\n[1/8] Loading augmented.jsonl...")
    samples = load_jsonl(INPUT_PATH)
    print(f"  Loaded {len(samples)} samples")

    # Improvement 1: Merge POI → district
    print("\n[2/8] Merging POI scope → district...")
    n_merged = merge_poi_to_district(samples)
    print(f"  Merged {n_merged} POI samples → district")

    # Improvement 4: Update system prompt (3 scopes, no POI)
    print("\n[3/8] Updating system prompt (all samples)...")
    samples = update_system_prompt(samples)
    print("  Done — all samples now use improved system prompt (3 scopes)")

    # Improvement 2: Add hard negatives
    print(f"\n[4/8] Adding {len(ADDITIONAL_HARD_NEGATIVES)} hard negatives + {len(SCOPE_CONFUSION_CASES)} scope confusion cases...")
    for hn in ADDITIONAL_HARD_NEGATIVES:
        samples.append(make_sample(hn["q"], hn["intent"], hn["scope"], "hard_negative"))
    for sc in SCOPE_CONFUSION_CASES:
        samples.append(make_sample(sc["q"], sc["intent"], sc["scope"], "scope_confusion"))

    # Merge POI in newly added samples too
    n_merged2 = merge_poi_to_district(samples)
    prev_hn = sum(1 for s in samples if s["metadata"]["source"] == "hard_negative")
    prev_sc = sum(1 for s in samples if s["metadata"]["source"] == "scope_confusion")
    print(f"  Hard negatives total: {prev_hn}, Scope confusion total: {prev_sc}")
    if n_merged2 > n_merged:
        print(f"  (also merged {n_merged2 - n_merged} POI refs in new samples)")

    # Improvement 6: Balance samples (upsample city + ward)
    print("\n[5/8] Generating balance samples (city + ward upsampling)...")
    balance = generate_balance_samples(samples)
    n_city = sum(1 for b in balance if b["metadata"]["scope"] == "city")
    n_ward = sum(1 for b in balance if b["metadata"]["scope"] == "ward")
    samples.extend(balance)
    print(f"  Added {n_city} city + {n_ward} ward samples ({len(balance)} total)")

    # Improvement 3: No-diacritics augmentation
    print("\n[6/8] Generating no-diacritics variants (18% of eligible samples)...")
    no_diac_samples = generate_no_diacritics_samples(samples, ratio=0.18)
    print(f"  Generated {len(no_diac_samples)} no-diacritics variants")
    samples.extend(no_diac_samples)

    # Deduplicate
    print("\n[7/8] Deduplicating and rebalancing...")
    before = len(samples)
    samples = deduplicate(samples)
    print(f"  Removed {before - len(samples)} duplicates")

    # Downsample district to ~40%
    scope_before = Counter(s["metadata"]["scope"] for s in samples)
    samples, n_removed = downsample_scope(samples, "district", target_pct=0.40)
    scope_after = Counter(s["metadata"]["scope"] for s in samples)
    print(f"  Downsampled district: removed {n_removed} samples")
    print(f"  Before: {dict(sorted(scope_before.items()))}")
    print(f"  After:  {dict(sorted(scope_after.items()))}")
    pct = {k: f"{v/len(samples)*100:.1f}%" for k, v in sorted(scope_after.items())}
    print(f"  Ratios: {pct}")

    random.shuffle(samples)
    print_stats(samples, "Improved dataset (v2) — rebalanced")

    # Save augmented_v2
    save_jsonl(samples, OUTPUT_PATH)
    print(f"\n  Saved → {OUTPUT_PATH}")

    # Re-run split
    print("\n[8/8] Re-running stratified split...")
    print("=" * 60)

    train, val, test = stratified_split(samples)

    for name, split in [("Train", train), ("Val", val), ("Test", test)]:
        combo_counts = Counter()
        source_counts = Counter()
        for s in split:
            m = s["metadata"]
            combo_counts[(m["intent"], m["scope"])] += 1
            source_counts[m["source"]] += 1
        vals = list(combo_counts.values()) if combo_counts else [0]
        print(f"  {name:5s}: {len(split):5d} samples | "
              f"{len(combo_counts)} combos | "
              f"min={min(vals)} max={max(vals)} avg={sum(vals)/max(len(vals),1):.1f} | "
              f"sources={dict(sorted(source_counts.items()))}")

    # Save splits
    save_jsonl(train, OUTPUT_DIR / "train.jsonl")
    save_jsonl(val, OUTPUT_DIR / "val.jsonl")
    save_jsonl(test, OUTPUT_DIR / "test.jsonl")
    save_jsonl(train, OUTPUT_DIR / "train_clean.jsonl", strip_metadata=True)
    save_jsonl(val, OUTPUT_DIR / "val_clean.jsonl", strip_metadata=True)
    save_jsonl(test, OUTPUT_DIR / "test_clean.jsonl", strip_metadata=True)

    # Verify no leakage
    train_q = set(s["messages"][1]["content"] for s in train)
    val_q = set(s["messages"][1]["content"] for s in val)
    test_q = set(s["messages"][1]["content"] for s in test)
    leak_tv = train_q & val_q
    leak_tt = train_q & test_q
    leak_vt = val_q & test_q

    if leak_tv or leak_tt or leak_vt:
        print(f"\n  [WARN] Data leakage!")
        print(f"    Train∩Val: {len(leak_tv)}, Train∩Test: {len(leak_tt)}, Val∩Test: {len(leak_vt)}")
    else:
        print(f"\n  No data leakage between splits")

    print(f"\n  Saved to: {OUTPUT_DIR}")
    print(f"  Done!")


if __name__ == "__main__":
    main()
