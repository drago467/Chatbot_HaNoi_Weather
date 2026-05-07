"""V7 Batch 4 — Manual fix samples (50 total).

Composition:
- 25 FIX_POI_ADMIN: ~9 clean ward (Phường Láng, Ngọc Hà, Văn Miếu-QTG explicit),
  ~16 pure POI/POI-compound → T5
- 25 FIX_CONTEXT: ~17 default Phường, ~8 keep district (rural collision +
  weather_alert/seasonal); 1 explicit-switch to city ("Hà Nội")
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# FIX_POI_ADMIN (25)
# ═══════════════════════════════════════════════════════════════════════════

# idx=2094: Văn Miếu - QTG full ward name
SAMPLES.append({
    "_v6_idx": 2094, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Văn Miếu - Quốc Tử Giám tuần này có bất thường không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Văn Miếu - Quốc Tử Giám tuần này có bất thường về thời tiết không?"}
})

# idx=2099: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 2099, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở khu vực Lăng Bác lúc này nóng hay mát?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2104: sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 2104, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tầm nhìn xa ở sân bay Nội Bài hiện tại?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2111: sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 2111, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bây giờ ở sân bay Nội Bài có thời tiết như thế nào nhỉ?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2114: "Lăng Bác và sân bay Nội Bài" — both POI → T5
SAMPLES.append({
    "_v6_idx": 2114, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Nhiệt độ tại Lăng Bác so với sân bay Nội Bài chỗ nào mát hơn?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2131: "Phường Láng" explicit
SAMPLES.append({
    "_v6_idx": 2131, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Ở Phường Láng chiều nay có giông không?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Láng chiều nay có giông không?"}
})

# idx=2138: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 2138, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Giờ này ở Lăng Chủ tịch đang là nhiệt độ bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2155: "Phường Ngọc Hà" clean
SAMPLES.append({
    "_v6_idx": 2155, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Ngọc Hà cuối tuần trời thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Dự báo thời tiết Phường Ngọc Hà cuối tuần"}
})

# idx=2164: "Đại học Quốc Gia và Bến xe Nam Từ Liêm" — both POI → T5
SAMPLES.append({
    "_v6_idx": 2164, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "So sánh thời tiết Đại học Quốc Gia và Bến xe Nam Từ Liêm",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2181: "Nam Từ Liêm và Times City" — Nam Từ Liêm = pure district, Times City = POI
# Mixed: extract Nam Từ Liêm, drop Times City. But comparing district vs POI is broken — better T5
SAMPLES.append({
    "_v6_idx": 2181, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "So sánh thời tiết hiện tại ở Nam Từ Liêm và Times City giúp mình.",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2210: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2210, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hiện tại độ ẩm ở Bệnh viện Bạch Mai là bao nhiêu vậy?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2269: "phuong lang" — Phường Láng
SAMPLES.append({
    "_v6_idx": 2269, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Ở phường Láng có nguy cơ ngập không nhỉ?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Láng có nguy cơ ngập lụt không?"}
})

# idx=2313: "Phường Láng Hạ" — NOT in canonical → T5
SAMPLES.append({
    "_v6_idx": 2313, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Phường Láng Hạ hôm nay nóng không?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2335: "Phường Văn Miếu - QTG" clean
SAMPLES.append({
    "_v6_idx": 2335, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Gió ở Phường Văn Miếu - Quốc Tử Giám hiện tại mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Gió Phường Văn Miếu - Quốc Tử Giám hiện tại mạnh không?"}
})

# idx=2363: "Đại học Quốc Gia và Lăng Chủ tịch" → T5
SAMPLES.append({
    "_v6_idx": 2363, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "So sánh thời tiết hiện tại ở Đại học Quốc Gia và Lăng Chủ tịch đi, ai biết không?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2420: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2420, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Khu vực Bệnh viện Bạch Mai hôm nay có sương mù không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2423: "phuong ngoc ha" — Phường Ngọc Hà
SAMPLES.append({
    "_v6_idx": 2423, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "phường Ngọc Hà cuối tuần trời thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Dự báo thời tiết Phường Ngọc Hà cuối tuần"}
})

# idx=2429: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2429, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ngày mai ở Bệnh viện Bạch Mai trời ra sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2443: sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 2443, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "ở sân bay Nội Bài ngay bây giờ trời có nắng không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2464: "Bến xe Mỹ Đình với Lăng Chủ tịch" — both POI → T5
SAMPLES.append({
    "_v6_idx": 2464, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm nay thời tiết ở Bến xe Mỹ Đình với Lăng Chủ tịch chỗ nào lạnh hơn nhỉ?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2482: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 2482, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hiện tại áp suất không khí ở Lăng Chủ tịch là bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2501: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 2501, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Nhiệt độ tại Lăng Chủ tịch bây giờ có bao nhiêu độ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2586: "Lăng Chủ tịch hay Nội Bài" → T5
SAMPLES.append({
    "_v6_idx": 2586, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "ở Lăng Chủ tịch hay Nội Bài mát hơn?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2596: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2596, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tình hình thời tiết khu vực Bệnh viện Bạch Mai buổi tối thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2618: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 2618, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Có thông tin gì về dự báo thời tiết ở Lăng Chủ tịch bữa nay không?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# ═══════════════════════════════════════════════════════════════════════════
# FIX_CONTEXT (25)
# ═══════════════════════════════════════════════════════════════════════════

# idx=973 ctx=Cầu Giấy, expert "tầm nhìn" → ward
SAMPLES.append({
    "_v6_idx": 973, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hiện tại thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "Tầm nhìn xa không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tầm nhìn xa ở Phường Cầu Giấy hiện tại thế nào?"}
})

# idx=987 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 987, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "thời tiết bây giờ ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hiện tại thời tiết Phường Cầu Giấy như thế nào?"}
})

# idx=1014 ctx=Long Biên, activity → ward
SAMPLES.append({
    "_v6_idx": 1014, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Phù hợp chạy bộ không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Long Biên hôm nay có phù hợp để đi chạy bộ không?"}
})

# idx=1040 ctx=Gia Lâm → district keep (Huyện)
SAMPLES.append({
    "_v6_idx": 1040, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay có mưa không?",
         "assistant": asst("rain_query", "district", 0.85,
                           "Huyện Gia Lâm hôm nay có mưa không?")}
    ],
    "input": "Thế mưa kèm gió không?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Hôm nay Huyện Gia Lâm có mưa kèm gió không?"}
})

# idx=1049 ctx=Cầu Giấy, hourly → ward
SAMPLES.append({
    "_v6_idx": 1049, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy sáng nay thế nào?",
         "assistant": asst("hourly_forecast", "ward", 0.85,
                           "Dự báo theo giờ Phường Cầu Giấy sáng nay")}
    ],
    "input": "Chiều nay có gì mới không?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay Phường Cầu Giấy diễn biến thời tiết thế nào?"}
})

# idx=1053 ctx=Đống Đa, temperature → ward
SAMPLES.append({
    "_v6_idx": 1053, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Nhiệt độ ở đó thế nào?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ Phường Đống Đa bây giờ ra sao?"}
})

# idx=1056 ctx=Hoàn Kiếm, UV → ward
SAMPLES.append({
    "_v6_idx": 1056, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Khu đó UV bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Hoàn Kiếm hôm nay bao nhiêu?"}
})

# idx=1081 ctx=Ba Đình, wind → ward
SAMPLES.append({
    "_v6_idx": 1081, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hôm nay thế nào?")}
    ],
    "input": "Nơi đó gió thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Ba Đình hiện tại mạnh không?"}
})

# idx=1086 ctx=Ba Đình, seasonal → ward
SAMPLES.append({
    "_v6_idx": 1086, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hôm nay thế nào?")}
    ],
    "input": "Hôm nay so với ngày khác ra sao?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "So với hôm qua, thời tiết Phường Ba Đình hôm nay có gì khác không?"}
})

# idx=1089 ctx=Đông Anh → district keep (rural seasonal)
SAMPLES.append({
    "_v6_idx": 1089, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đông Anh mùa này thế nào?",
         "assistant": asst("seasonal_context", "district", 0.85,
                           "Thời tiết mùa này ở Huyện Đông Anh ra sao?")}
    ],
    "input": "còn về mùa tới thì sao?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Còn về mùa tới ở Huyện Đông Anh thì sao?"}
})

# idx=1090 ctx=Hoàng Mai, seasonal → ward
SAMPLES.append({
    "_v6_idx": 1090, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm qua nhiệt độ bao nhiêu?",
         "assistant": asst("historical_weather", "ward", 0.85,
                           "Nhiệt độ hôm qua ở Phường Hoàng Mai bao nhiêu?")}
    ],
    "input": "Nhiệt độ chênh bao nhiêu?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ Phường Hoàng Mai hôm nay chênh bao nhiêu so với hôm qua?"}
})

# idx=1104 ctx=Hoàn Kiếm, seasonal → ward
SAMPLES.append({
    "_v6_idx": 1104, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm qua thế nào?",
         "assistant": asst("historical_weather", "ward", 0.85,
                           "Thời tiết hôm qua ở Phường Hoàn Kiếm thế nào?")}
    ],
    "input": "So với hôm nay thế nào?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "So với hôm qua, hôm nay Phường Hoàn Kiếm nóng hơn hay mát hơn?"}
})

# idx=1106 ctx=Thanh Xuân, UV → ward
SAMPLES.append({
    "_v6_idx": 1106, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "khu đó có chỉ số UV cao không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Thanh Xuân hiện tại có cao không?"}
})

# idx=1125 ctx=Thanh Xuân, daily → ward
SAMPLES.append({
    "_v6_idx": 1125, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "Ngày mai dự báo sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo thời tiết ngày mai ở Phường Thanh Xuân thế nào?"}
})

# idx=1150 ctx=Mê Linh → district keep (rural)
SAMPLES.append({
    "_v6_idx": 1150, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Mê Linh thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Mê Linh hiện tại thế nào?")}
    ],
    "input": "thời tiết ra sao ở đó?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết hiện tại ở Huyện Mê Linh thế nào?"}
})

# idx=1172 ctx=Cầu Giấy, hourly → ward
SAMPLES.append({
    "_v6_idx": 1172, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Sáng mai?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai Phường Cầu Giấy nhiệt độ bao nhiêu?"}
})

# idx=1184 ctx=Gia Lâm → district keep
SAMPLES.append({
    "_v6_idx": 1184, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay gió thế nào?",
         "assistant": asst("wind_query", "district", 0.85,
                           "Gió Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Ngày mai có gió không nhỉ?",
    "output": {"intent": "wind_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Gia Lâm có gió không?"}
})

# idx=1240 ctx=Tây Hồ, wind → ward
SAMPLES.append({
    "_v6_idx": 1240, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ chiều nay gió thế nào?",
         "assistant": asst("wind_query", "ward", 0.85,
                           "Gió Phường Tây Hồ chiều nay thế nào?")}
    ],
    "input": "Gió lúc đó mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Tây Hồ chiều nay có mạnh không?"}
})

# idx=1259 ctx=Cầu Giấy, wind → ward
SAMPLES.append({
    "_v6_idx": 1259, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Gió mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Long Biên hiện tại có mạnh không?".replace("Long Biên", "Cầu Giấy")}
})

# idx=1282 ctx=Long Biên (v6 already scope=ward!) — already correct, just migrate
SAMPLES.append({
    "_v6_idx": 1282, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Chỗ đó có nên mặc áo mỏng không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ở Phường Long Biên hôm nay có nên mặc áo mỏng không?"}
})

# idx=1316 ctx=Hà Đông, smalltalk → ward
SAMPLES.append({
    "_v6_idx": 1316, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "Nơi đó có mát không?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hà Đông hôm nay thời tiết có mát mẻ không?"}
})

# idx=1332 ctx=Thanh Xuân BUT user says "Hà Nội" — explicit-switch district→city
SAMPLES.append({
    "_v6_idx": 1332, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "Hà Nội có nồm không?",
    "output": {"intent": "humidity_fog_query", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Hà Nội hôm nay có nồm ẩm không?"}
})

# idx=1373 ctx=Đan Phượng → district keep (Đan Phượng = collision Xã/Huyện, rural)
SAMPLES.append({
    "_v6_idx": 1373, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đan Phượng tuần này có mưa không?",
         "assistant": asst("rain_query", "district", 0.85,
                           "Tuần này Huyện Đan Phượng có mưa không?")}
    ],
    "input": "Mưa nhiều nhất ngày nào?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Tuần này Huyện Đan Phượng mưa nhiều nhất vào ngày nào?"}
})

# idx=1392 ctx=Đan Phượng → district keep
SAMPLES.append({
    "_v6_idx": 1392, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đan Phượng thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Đan Phượng hiện tại thế nào?")}
    ],
    "input": "Thời tiết hiện tại ở đó ra sao?",
    "output": {"intent": "current_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết hiện tại ở Huyện Đan Phượng thế nào?"}
})

# idx=1415 ctx=Đan Phượng → district keep
SAMPLES.append({
    "_v6_idx": 1415, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đan Phượng hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Đan Phượng hôm nay thế nào?")}
    ],
    "input": "Ngày mai cụ thể ra sao?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Đan Phượng thời tiết cụ thể thế nào?"}
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

out_path = Path(__file__).parent / 'batch_04_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
