"""V7 Batch 5 — Manual fix samples (50 total).

Composition:
- 25 FIX_POI_ADMIN: ~9 clean ward (Phường Láng, Văn Miếu-QTG, Yên Lãng/Láng+admin),
  ~16 pure POI/POI-compound → T5
- 25 FIX_CONTEXT: ~16 default Phường, ~8 keep district (rural+alert), 1 explicit-switch
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

# idx=2658: "Yên Lãng, Mê Linh" → Xã Yên Lãng (Mê Linh)
SAMPLES.append({
    "_v6_idx": 2658, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Tổng quan thời tiết ở Yên Lãng, Mê Linh buổi tối",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Tổng quan thời tiết Xã Yên Lãng (Huyện Mê Linh) buổi tối"}
})

# idx=2695: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 2695, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bây giờ gió ở khu vực Lăng Bác có thổi mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2700: "Văn Miếu - QTG" full ward name
SAMPLES.append({
    "_v6_idx": 2700, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Văn Miếu - Quốc Tử Giám hôm nay có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Văn Miếu - Quốc Tử Giám hôm nay có mưa không?"}
})

# idx=2716: "Láng, Đống Đa" → Phường Láng
SAMPLES.append({
    "_v6_idx": 2716, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Tổng quan thời tiết ở Láng, Đống Đa sáng nay",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Phường Láng (Đống Đa) sáng nay"}
})

# idx=2727: "Láng, Đống Đa" → Phường Láng
SAMPLES.append({
    "_v6_idx": 2727, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Sáng nay thời tiết ở Láng, Đống Đa có ổn không nhỉ?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Láng (Đống Đa) sáng nay có ổn không?"}
})

# idx=2743: "phuong lang" → Phường Láng
SAMPLES.append({
    "_v6_idx": 2743, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "phường Láng lúc này tốc độ gió bao nhiêu?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Tốc độ gió ở Phường Láng lúc này bao nhiêu?"}
})

# idx=2772: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 2772, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm qua ở Lăng Bác trời có đẹp không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2774: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2774, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bệnh viện Bạch Mai bữa nay có bị ảnh hưởng bởi thời tiết không?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2794: Sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 2794, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết Sân bay Nội Bài cuối tuần này thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2795: "Phường Văn Miếu - QTG" explicit
SAMPLES.append({
    "_v6_idx": 2795, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Văn Miếu - Quốc Tử Giám nhiệt độ hiện tại bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Nhiệt độ hiện tại Phường Văn Miếu - Quốc Tử Giám bao nhiêu?"}
})

# idx=2890: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2890, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết ở Bệnh viện Bạch Mai bữa trước ra sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2989: "Nam Từ Liêm và Phố cổ Hà Nội" — district + POI mixed → T5
SAMPLES.append({
    "_v6_idx": 2989, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "So sánh thời tiết Nam Từ Liêm và Phố cổ Hà Nội",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3000: "phuong van mieu - quoc tu giam" lowercase
SAMPLES.append({
    "_v6_idx": 3000, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "phường Văn Miếu - Quốc Tử Giám bây giờ thời tiết thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Văn Miếu - Quốc Tử Giám hiện tại thế nào?"}
})

# idx=3007: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 3007, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bao nhiêu độ ở Lăng Chủ tịch ngay bây giờ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3031: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 3031, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Áp suất ở Lăng Chủ tịch hiện giờ bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3049: "Phường Láng" explicit
SAMPLES.append({
    "_v6_idx": 3049, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Láng chiều nay mấy độ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Láng chiều nay nhiệt độ bao nhiêu?"}
})

# idx=3057: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 3057, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Sáng nay tại Lăng Bác có mưa không hả bạn?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3116: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 3116, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết ở Lăng Chủ tịch có phù hợp để đi dạo không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3118: "Yên Lãng, Mê Linh" → Xã Yên Lãng
SAMPLES.append({
    "_v6_idx": 3118, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Thời tiết hiện tại ở Yên Lãng, Mê Linh đêm nay như thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Xã Yên Lãng (Huyện Mê Linh) đêm nay thế nào?"}
})

# idx=3127: Sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 3127, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Gần đây ở Sân bay Nội Bài thời tiết có bất thường không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3141: Lăng Chủ tịch → T5 (intent wind_query mismatched in v6 — re-classify expert)
SAMPLES.append({
    "_v6_idx": 3141, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "áp suất ở Lăng Chủ tịch hiện giờ bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3262: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 3262, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm qua ở Lăng Chủ tịch trời ra sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3291: Sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 3291, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tổng quan thời tiết ở Sân bay Nội Bài chiều nay",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3345: "Đường đến sân bay Nội Bài" — off-topic non-weather, smalltalk
SAMPLES.append({
    "_v6_idx": 3345, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Đường đến sân bay Nội Bài đi thế nào?",
    "output": {"intent": "smalltalk_weather", "scope": "city", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=3395: "phường Láng, Đống Đa" — Phường Láng
SAMPLES.append({
    "_v6_idx": 3395, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Sáng nay 6-9h dự báo theo giờ ở phường Láng, Đống Đa?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Dự báo theo giờ Phường Láng (Đống Đa) sáng nay 6-9h"}
})

# ═══════════════════════════════════════════════════════════════════════════
# FIX_CONTEXT (25)
# ═══════════════════════════════════════════════════════════════════════════

# idx=1440 ctx=Ba Đình, historical → ward
SAMPLES.append({
    "_v6_idx": 1440, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hôm nay thế nào?")}
    ],
    "input": "Hôm qua có mưa không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua ở Phường Ba Đình có mưa không?"}
})

# idx=1469 ctx=Hoàng Mai, wind → ward
SAMPLES.append({
    "_v6_idx": 1469, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai sáng nay gió thế nào?",
         "assistant": asst("wind_query", "ward", 0.85,
                           "Gió ở Phường Hoàng Mai sáng nay thế nào?")}
    ],
    "input": "Gió mạnh hay nhẹ thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tốc độ gió Phường Hoàng Mai sáng nay bao nhiêu km/h?"}
})

# idx=1496 ctx=Cầu Giấy, historical → ward
SAMPLES.append({
    "_v6_idx": 1496, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Hôm qua thời tiết ra sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua ở Phường Cầu Giấy thời tiết thế nào?"}
})

# idx=1498 ctx=Cầu Giấy, daily → ward
SAMPLES.append({
    "_v6_idx": 1498, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Cuối tuần thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo thời tiết cuối tuần ở Phường Cầu Giấy"}
})

# idx=1502 ctx=Hoàng Mai, current → ward
SAMPLES.append({
    "_v6_idx": 1502, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hiện tại thế nào?")}
    ],
    "input": "Hiện tại khu đó ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai hiện tại trời ra sao?"}
})

# idx=1504 ctx=Cầu Giấy, current → ward
SAMPLES.append({
    "_v6_idx": 1504, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "Hiện tại trời thế nào ở đây?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hiện tại thời tiết Phường Cầu Giấy như thế nào?"}
})

# idx=1517 ctx=Hoàn Kiếm, overview → ward
SAMPLES.append({
    "_v6_idx": 1517, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Cho mình biết thời tiết ở đó hôm nay nhé?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tóm tắt thời tiết Phường Hoàn Kiếm hôm nay"}
})

# idx=1534 ctx=Long Biên, activity → ward
SAMPLES.append({
    "_v6_idx": 1534, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay có phù hợp chạy bộ không?",
         "assistant": asst("activity_weather", "ward", 0.85,
                           "Phường Long Biên hôm nay có phù hợp chạy bộ không?")}
    ],
    "input": "Lúc nào là thời điểm tốt nhất?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Long Biên hôm nay lúc nào là thời điểm tốt nhất để chạy bộ?"}
})

# idx=1590 ctx=Gia Lâm → district keep
SAMPLES.append({
    "_v6_idx": 1590, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "thời tiết có phù hợp cho các hoạt động ngoài trời không?",
    "output": {"intent": "activity_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết Huyện Gia Lâm có phù hợp cho hoạt động ngoài trời không?"}
})

# idx=1621 ctx=Ba Đình, historical → ward
SAMPLES.append({
    "_v6_idx": 1621, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hôm nay thế nào?")}
    ],
    "input": "Hôm qua trời có mưa không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua ở Phường Ba Đình có mưa không?"}
})

# idx=1638 ctx=Gia Lâm → district keep
SAMPLES.append({
    "_v6_idx": 1638, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay gió thế nào?",
         "assistant": asst("wind_query", "district", 0.85,
                           "Gió Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "ngày mai có gió không nhỉ?",
    "output": {"intent": "wind_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Gia Lâm có gió không?"}
})

# idx=1640 ctx=Đống Đa, humidity → ward
SAMPLES.append({
    "_v6_idx": 1640, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Chiều nay có ẩm không nhỉ?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay Phường Đống Đa có nồm ẩm không?"}
})

# idx=1643 ctx=Đông Anh → district keep (rural seasonal)
SAMPLES.append({
    "_v6_idx": 1643, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đông Anh mùa này thế nào?",
         "assistant": asst("seasonal_context", "district", 0.85,
                           "Thời tiết mùa này ở Huyện Đông Anh ra sao?")}
    ],
    "input": "Còn về mùa tới thì sao?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Còn về mùa tới ở Huyện Đông Anh thì sao?"}
})

# idx=1706 ctx=Hoàn Kiếm, hourly → ward
SAMPLES.append({
    "_v6_idx": 1706, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Chỗ đó tối nay có mưa không?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay ở Phường Hoàn Kiếm có mưa không?"}
})

# idx=1773 ctx=Ba Đình, weather_alert → district
SAMPLES.append({
    "_v6_idx": 1773, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Ba Đình hôm nay có cảnh báo thời tiết nào không?")}
    ],
    "input": "Thời tiết hôm nay có gì đặc biệt không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Có thông báo thời tiết đặc biệt nào ở Quận Ba Đình hôm nay không?"}
})

# idx=1790 ctx=Cầu Giấy, historical → ward
SAMPLES.append({
    "_v6_idx": 1790, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Hôm qua thế nào?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua ở Phường Cầu Giấy thời tiết thế nào?"}
})

# idx=1812 ctx=Đống Đa, humidity → ward
SAMPLES.append({
    "_v6_idx": 1812, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Sáng sớm ở đó có sương không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng sớm Phường Đống Đa có sương mù không?"}
})

# idx=1836 ctx=Long Biên BUT user "Hà Nội" — explicit-switch ward→city
SAMPLES.append({
    "_v6_idx": 1836, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Ngày mai Hà Nội có mưa không?",
    "output": {"intent": "rain_query", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Ngày mai Hà Nội có mưa không?"}
})

# idx=1872 ctx=Ba Đình, current → ward
SAMPLES.append({
    "_v6_idx": 1872, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hiện tại thế nào?")}
    ],
    "input": "giờ này có nắng không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Ba Đình bây giờ có nắng không?"}
})

# idx=1886 ctx=Sóc Sơn → district keep (rural)
SAMPLES.append({
    "_v6_idx": 1886, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Sóc Sơn hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "Ở đó ngày mai cụ thể?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Sóc Sơn thời tiết cụ thể thế nào?"}
})

# idx=1913 ctx=Tây Hồ, wind → ward
SAMPLES.append({
    "_v6_idx": 1913, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Gió có to không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay Phường Tây Hồ có gió to không?"}
})

# idx=1929 ctx=Tây Hồ, wind → ward
SAMPLES.append({
    "_v6_idx": 1929, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ chiều nay thế nào?",
         "assistant": asst("hourly_forecast", "ward", 0.85,
                           "Dự báo Phường Tây Hồ chiều nay thế nào?")}
    ],
    "input": "Thế còn gió?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Tây Hồ chiều nay có mạnh không?"}
})

# idx=1930 ctx=Hai Bà Trưng, activity → ward (collision Phường/Quận, default Phường)
SAMPLES.append({
    "_v6_idx": 1930, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hai Bà Trưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?")}
    ],
    "input": "Ở đó đi làm thì nên mặc gì?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ở Phường Hai Bà Trưng hôm nay nên mặc gì khi đi làm?"}
})

# idx=1936 ctx=Thanh Xuân, current → ward
SAMPLES.append({
    "_v6_idx": 1936, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân sáng nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.85,
                           "Phường Thanh Xuân sáng nay có mưa không?")}
    ],
    "input": "Bây giờ trời tạnh chưa?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Thanh Xuân bây giờ trời đã tạnh chưa?"}
})

# idx=1978 ctx=Tây Hồ, hourly → ward
SAMPLES.append({
    "_v6_idx": 1978, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Thế chiều tối?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều tối hôm nay Phường Tây Hồ thời tiết thế nào?"}
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

out_path = Path(__file__).parent / 'batch_05_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
