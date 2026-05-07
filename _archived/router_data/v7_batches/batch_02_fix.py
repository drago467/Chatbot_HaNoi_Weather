"""V7 Batch 2 — Manual fix samples (50 total).

Composition:
- 25 FIX_POI_ADMIN (mostly Lăng Bác/Sân bay Nội Bài/Bệnh viện Bạch Mai → T5;
  ~5 with clean admin extraction Phường Ngọc Hà / Láng / Yên Lãng / Văn Miếu-QTG)
- 25 FIX_CONTEXT (collision cores: ~80% default Phường, ~20% keep district when context implies)

Each sample validated against dim_ward.csv canonical authority.

Run: python batch_02_fix.py → writes batch_02_fix.jsonl
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# C continued) 25 FIX_POI_ADMIN
# ═══════════════════════════════════════════════════════════════════════════

# idx=610: "Ngọc Hà, Ba Đình" — Phường Ngọc Hà ✓ canonical
SAMPLES.append({
    "_v6_idx": 610, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Ra ngoài ở Ngọc Hà, Ba Đình có cần áo khoác không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Ngọc Hà (Ba Đình) có cần áo khoác khi ra ngoài không?"}
})

# idx=645: "Lăng Chủ tịch" pure POI → T5
SAMPLES.append({
    "_v6_idx": 645, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Lăng Chủ tịch hôm qua có thời tiết ra sao vậy?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=652: "Xã Yên Lãng" ✓ canonical
SAMPLES.append({
    "_v6_idx": 652, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Tình hình thời tiết trưa nay ở Xã Yên Lãng ra sao nhỉ?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Tình hình thời tiết trưa nay ở Xã Yên Lãng ra sao?"}
})

# idx=653: "Láng, Quận Đống Đa" — Phường Láng ✓
SAMPLES.append({
    "_v6_idx": 653, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Mọi người cho mình biết thời tiết ở Láng, Quận Đống Đa bây giờ ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Láng (Quận Đống Đa) hiện tại thế nào?"}
})

# idx=668: "sân bay Nội Bài" pure POI → T5
SAMPLES.append({
    "_v6_idx": 668, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tầm nhìn hiện tại ở sân bay Nội Bài có ổn không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=683
SAMPLES.append({
    "_v6_idx": 683, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Gió ở Lăng Chủ tịch bây giờ mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=685: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 685, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết ở Lăng Bác hiện tại là nóng hay lạnh?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=688: "Phường Văn Miếu - Quốc Tử Giám" explicit, clean
SAMPLES.append({
    "_v6_idx": 688, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Văn Miếu - Quốc Tử Giám bây giờ thời tiết thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Văn Miếu - Quốc Tử Giám hiện tại thế nào?"}
})

# idx=705: "phường Láng Hạ" — NOT in canonical post-merger → T5 abstain
SAMPLES.append({
    "_v6_idx": 705, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Trời ở phường Láng Hạ ngày hôm nay thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=718: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 718, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Gió tại Lăng Chủ tịch bây giờ có hơi mạnh không ta?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=728: Bệnh viện Bạch Mai → T5 (POI compound, not Phường Bạch Mai)
SAMPLES.append({
    "_v6_idx": 728, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ngày mai trời ở Bệnh viện Bạch Mai sẽ thế nào nhỉ?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=761
SAMPLES.append({
    "_v6_idx": 761, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết hiện tại ở Sân bay Nội Bài ra sao bữa nay?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=811
SAMPLES.append({
    "_v6_idx": 811, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "bữa nay ở Lăng Bác thì nên chọn đồ như thế nào cho hợp lý?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=851
SAMPLES.append({
    "_v6_idx": 851, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Đi Lăng Bác hôm nay thì phải mặc sao cho vừa phải?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=874: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 874, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hiện tại, áp suất không khí tại Lăng Chủ tịch đang ở mức nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=910
SAMPLES.append({
    "_v6_idx": 910, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Sân bay Nội Bài có sương mù không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=918
SAMPLES.append({
    "_v6_idx": 918, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "gió ở Lăng Chủ tịch bây giờ mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=971
SAMPLES.append({
    "_v6_idx": 971, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Độ ẩm ở Bệnh viện Bạch Mai hiện nay bao nhiêu?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1010
SAMPLES.append({
    "_v6_idx": 1010, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở khu vực Lăng Bác bây giờ nóng hay mát?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1013: "lang, quan dong da" — Phường Láng (lowercase)
SAMPLES.append({
    "_v6_idx": 1013, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "cho mình hỏi thời tiết ở Láng, Quận Đống Đa",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Láng (Quận Đống Đa) hiện tại thế nào?"}
})

# idx=1037
SAMPLES.append({
    "_v6_idx": 1037, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "hiện tại ở khu vực Lăng Bác thì trời ấm hay dễ chịu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1070: "Lăng Chủ tịch hay Phố cổ Hà Nội" — both POI → T5
SAMPLES.append({
    "_v6_idx": 1070, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở Lăng Chủ tịch hay Phố cổ Hà Nội mát hơn?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1078
SAMPLES.append({
    "_v6_idx": 1078, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tuần trước ở sân bay Nội Bài thời tiết thế nào nhỉ?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1127: "benh vien bach mai" → T5
SAMPLES.append({
    "_v6_idx": 1127, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "bệnh viện Bạch Mai hiện tại có nhiệt độ cảm nhận là bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1178: "van mieu - quoc tu giam" full ward name
SAMPLES.append({
    "_v6_idx": 1178, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Văn Miếu - Quốc Tử Giám tuần này có bất thường không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Văn Miếu - Quốc Tử Giám tuần này có bất thường về thời tiết không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# D continued) 25 FIX_CONTEXT — collision cores; mostly default Phường (post-merger),
#   keep district when context strongly implies (alert spans, large area)
# ═══════════════════════════════════════════════════════════════════════════

# idx=235 ctx=Ba Đình, weather_alert "Có thông báo gì không?" — alerts span district → keep Quận
SAMPLES.append({
    "_v6_idx": 235, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Ba Đình hôm nay có cảnh báo thời tiết nào không?")}
    ],
    "input": "Có thông báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Có thông báo thời tiết nào cho Quận Ba Đình không?"}
})

# idx=244 ctx=Hoàn Kiếm, weather_alert mưa - keep district (alert)
SAMPLES.append({
    "_v6_idx": 244, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm có cảnh báo mưa không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Hoàn Kiếm có cảnh báo mưa không?")}
    ],
    "input": "Ở đó mưa đến bao giờ?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Mưa ở Quận Hoàn Kiếm đến bao giờ thì tạnh?"}
})

# idx=245 ctx=Thanh Xuân, rain_query → ward default
SAMPLES.append({
    "_v6_idx": 245, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.85,
                           "Phường Thanh Xuân hôm nay có mưa không?")}
    ],
    "input": "Có mưa đến tối không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Mưa ở Phường Thanh Xuân có kéo dài đến tối không?"}
})

# idx=270 ctx=Tây Hồ, expert UV → ward
SAMPLES.append({
    "_v6_idx": 270, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ chỉ số UV thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Chỉ số UV ở Phường Tây Hồ hôm nay bao nhiêu?")}
    ],
    "input": "UV sáng mai thế nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chỉ số UV sáng mai ở Phường Tây Hồ bao nhiêu?"}
})

# idx=280 ctx=Hoàn Kiếm, UV → ward
SAMPLES.append({
    "_v6_idx": 280, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay UV thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "UV ở Phường Hoàn Kiếm hôm nay bao nhiêu?")}
    ],
    "input": "khu đó UV bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Hoàn Kiếm hôm nay bao nhiêu?"}
})

# idx=285 ctx=Hoàng Mai, wind → ward
SAMPLES.append({
    "_v6_idx": 285, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai sáng nay gió thế nào?",
         "assistant": asst("wind_query", "ward", 0.85,
                           "Tốc độ gió ở Phường Hoàng Mai sáng nay bao nhiêu?")}
    ],
    "input": "gió mạnh hay nhẹ thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Hoàng Mai sáng nay mạnh hay nhẹ?"}
})

# idx=315 ctx=Hoàng Mai, activity → ward
SAMPLES.append({
    "_v6_idx": 315, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Hôm nay có hoạt động nào ngoài trời không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay ở Phường Hoàng Mai có hoạt động nào ngoài trời phù hợp không?"}
})

# idx=333 ctx=Cầu Giấy, current → ward
SAMPLES.append({
    "_v6_idx": 333, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Bây giờ ở đó thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết hiện tại ở Phường Cầu Giấy như thế nào?"}
})

# idx=399 ctx=Cầu Giấy, daily_forecast → ward
SAMPLES.append({
    "_v6_idx": 399, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Cầu Giấy ngày mai thế nào?")}
    ],
    "input": "Ngày kia có sao không?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo thời tiết ngày kia ở Phường Cầu Giấy thế nào?"}
})

# idx=424 ctx=Hoàn Kiếm, activity → ward
SAMPLES.append({
    "_v6_idx": 424, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Hôm nay mặc gì nhỉ?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàn Kiếm hôm nay nên mặc gì khi ra ngoài?"}
})

# idx=427 ctx=Cầu Giấy, current → ward
SAMPLES.append({
    "_v6_idx": 427, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "Trời thế nào nhỉ?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Trời ở Phường Cầu Giấy lúc này ra sao?"}
})

# idx=448 ctx=Hoàn Kiếm, rain → district keep (rain alerts span district)
SAMPLES.append({
    "_v6_idx": 448, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay có mưa không?",
         "assistant": asst("rain_query", "district", 0.85,
                           "Quận Hoàn Kiếm hôm nay có mưa không?")}
    ],
    "input": "Mưa ở đó sẽ kéo dài đến khi nào?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Mưa ở Quận Hoàn Kiếm sẽ kéo dài đến khi nào?"}
})

# idx=460 ctx=Cầu Giấy, hourly → ward
SAMPLES.append({
    "_v6_idx": 460, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy sáng nay thế nào?",
         "assistant": asst("hourly_forecast", "ward", 0.85,
                           "Dự báo theo giờ ở Phường Cầu Giấy sáng nay")}
    ],
    "input": "Chiều nay tiếp tục?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay ở Phường Cầu Giấy diễn biến thời tiết thế nào?"}
})

# idx=466 ctx=Hoàng Mai, hourly → ward
SAMPLES.append({
    "_v6_idx": 466, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay nhiệt độ thế nào?",
         "assistant": asst("temperature_query", "ward", 0.85,
                           "Nhiệt độ Phường Hoàng Mai hôm nay bao nhiêu?")}
    ],
    "input": "Sáng mai mấy độ?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai ở Phường Hoàng Mai nhiệt độ bao nhiêu?"}
})

# idx=468 ctx=Hoàng Mai, weather_overview → ward
SAMPLES.append({
    "_v6_idx": 468, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Ngày mai cụ thể?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Phường Hoàng Mai thời tiết cụ thể thế nào?"}
})

# idx=486 ctx=Hoàng Mai, activity → ward
SAMPLES.append({
    "_v6_idx": 486, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay có gì hay?",
         "assistant": asst("activity_weather", "ward", 0.85,
                           "Hôm nay Phường Hoàng Mai có hoạt động ngoài trời nào hay không?")}
    ],
    "input": "Hôm nay ở đây có gì hay không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay ở Phường Hoàng Mai có hoạt động ngoài trời nào thú vị không?"}
})

# idx=495 ctx=Long Biên BUT user says "Hà Nội" — explicit scope SWITCH district→city
SAMPLES.append({
    "_v6_idx": 495, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên gần đây thế nào?",
         "assistant": asst("seasonal_context", "ward", 0.85,
                           "Tình hình thời tiết Phường Long Biên gần đây thế nào?")}
    ],
    "input": "Thời tiết Hà Nội dạo này thế nào?",
    "output": {"intent": "seasonal_context", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Tình hình thời tiết Hà Nội dạo gần đây thế nào?"}
})

# idx=505 ctx=Ba Đình, current → ward
SAMPLES.append({
    "_v6_idx": 505, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hiện tại thế nào?")}
    ],
    "input": "Ở đó trời hiện giờ thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Trời ở Phường Ba Đình hiện giờ thế nào?"}
})

# idx=507 ctx=Hoàng Mai, wind → ward
SAMPLES.append({
    "_v6_idx": 507, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay gió thế nào?",
         "assistant": asst("wind_query", "ward", 0.85,
                           "Gió ở Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Chiều nay có gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay ở Phường Hoàng Mai có gió không?"}
})

# idx=522 ctx=Đống Đa, expert "áp suất" → ward
SAMPLES.append({
    "_v6_idx": 522, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay áp suất thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Áp suất không khí Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Thế còn áp suất?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Áp suất ở Phường Đống Đa đang thay đổi không?"}
})

# idx=559 ctx=Tây Hồ, hourly → ward
SAMPLES.append({
    "_v6_idx": 559, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Chiều tối thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều tối hôm nay ở Phường Tây Hồ thời tiết như thế nào?"}
})

# idx=566 ctx=Gia Lâm — collision (Xã/Huyện); v6 used "huyện" correct → keep district
SAMPLES.append({
    "_v6_idx": 566, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Có mưa và gió không nhỉ?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Hôm nay Huyện Gia Lâm có mưa kèm gió không?"}
})

# idx=605 ctx=Tây Hồ, hourly → ward
SAMPLES.append({
    "_v6_idx": 605, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay dự báo thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Ở đó sáng mai thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai ở Phường Tây Hồ trời thế nào?"}
})

# idx=609 ctx=Gia Lâm, daily — Huyện Gia Lâm canonical district
SAMPLES.append({
    "_v6_idx": 609, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Nơi đó ngày mai dự báo sao?",
    "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Gia Lâm dự báo thế nào?"}
})

# idx=621 ctx=Cầu Giấy, rain → ward
SAMPLES.append({
    "_v6_idx": 621, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy sáng nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.85,
                           "Phường Cầu Giấy sáng nay có mưa không?")}
    ],
    "input": "mưa lúc mấy giờ?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng nay ở Phường Cầu Giấy mưa bắt đầu lúc mấy giờ?"}
})

# ── Validate + write ────────────────────────────────────────────────────────
def validate(s):
    errs = []
    if 'history' not in s: errs.append('missing history')
    if 'input' not in s: errs.append('missing input')
    if 'output' not in s: errs.append('missing output')
    o = s.get('output', {})
    if o.get('intent') not in {
        'activity_weather', 'current_weather', 'daily_forecast', 'expert_weather_param',
        'historical_weather', 'hourly_forecast', 'humidity_fog_query', 'location_comparison',
        'rain_query', 'seasonal_context', 'smalltalk_weather', 'temperature_query',
        'weather_alert', 'weather_overview', 'wind_query',
    }: errs.append(f"bad intent: {o.get('intent')}")
    if o.get('scope') not in {'city', 'district', 'ward'}: errs.append(f"bad scope: {o.get('scope')}")
    c = o.get('confidence')
    if not isinstance(c, (int, float)) or not (0.5 <= c <= 1.0):
        errs.append(f"bad confidence: {c}")
    if not isinstance(s.get('history'), list): errs.append("history not a list")
    return errs

print(f'Total samples: {len(SAMPLES)}')
fix_types = {}
for s in SAMPLES:
    ft = s.get('_fix_type', 'unknown')
    fix_types[ft] = fix_types.get(ft, 0) + 1
print('By fix type:', fix_types)

total_errs = 0
for i, s in enumerate(SAMPLES):
    errs = validate(s)
    if errs:
        print(f'  [SAMPLE {i} v6_idx={s.get("_v6_idx")}] {errs}')
        total_errs += 1
print(f'Validation errors: {total_errs}')
if total_errs > 0:
    sys.exit(1)

out_path = Path(__file__).parent / 'batch_02_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
