"""V7 Batch 3 — Manual fix samples (50 total).

Composition:
- 25 FIX_POI_ADMIN: ~7 clean admin extract (Phường Láng, Ngọc Hà, Văn Miếu-QTG),
  ~18 pure POI → T5 abstain
- 25 FIX_CONTEXT: ~17 default Phường (ward), ~8 keep district
  (alert/seasonal/comparison + rural collision cores Sóc Sơn/Đông Anh/Mê Linh)
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

# idx=1208: Sân bay Nội Bài → T5
SAMPLES.append({
    "_v6_idx": 1208, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "tuần trước ở sân bay Nội Bài thời tiết thế nào nhỉ?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1242: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 1242, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tháng trước ở Bệnh viện Bạch Mai trời ra sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1279: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 1279, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "hôm qua ở Lăng Bác trời có đẹp không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1293: "Phường Ngọc Hà, Ba Đình" — clean ward
SAMPLES.append({
    "_v6_idx": 1293, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Thời tiết ở Phường Ngọc Hà, Ba Đình ngay bây giờ thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Ngọc Hà (Ba Đình) hiện tại thế nào?"}
})

# idx=1323: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 1323, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Nhiệt độ cảm giác ở Bệnh viện Bạch Mai ngay bây giờ bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1333: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 1333, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hiện tại nhiệt độ ở Lăng Bác là bao nhiêu nhỉ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1395: "lang, dong da" — Phường Láng
SAMPLES.append({
    "_v6_idx": 1395, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "tổng quan thời tiết ở Láng, Đống Đa sáng nay",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Phường Láng (Đống Đa) sáng nay"}
})

# idx=1437: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 1437, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bệnh viện Bạch Mai hiện tại có nhiệt độ cảm nhận là bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1457: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 1457, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "hôm nay ở Lăng Bác có nên mặc đồ gì cho hợp lý không?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1459: Văn Miếu - QTG → ward
SAMPLES.append({
    "_v6_idx": 1459, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Dự báo thời tiết Văn Miếu - Quốc Tử Giám ngày mai?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Dự báo thời tiết Phường Văn Miếu - Quốc Tử Giám ngày mai"}
})

# idx=1471: "Phường Láng" → clean ward keep
SAMPLES.append({
    "_v6_idx": 1471, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Láng có gió mạnh không nhỉ, bây giờ thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Láng hiện tại có gió mạnh không?"}
})

# idx=1565: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 1565, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "thời tiết ở Bệnh viện Bạch Mai bữa trước ra sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1636: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 1636, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bữa nay ở Lăng Bác có nắng không, có cần chuẩn bị áo khoác không?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1674: Lăng Chủ tịch → T5
SAMPLES.append({
    "_v6_idx": 1674, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bây giờ ở khu vực Lăng Chủ tịch trời ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1782: "Lăng Chủ tịch hay Nội Bài" — both POI-leaning → T5
SAMPLES.append({
    "_v6_idx": 1782, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở Lăng Chủ tịch hay Nội Bài mát hơn?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1845: Láng → Phường Láng
SAMPLES.append({
    "_v6_idx": 1845, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Tốc độ gió ở Láng giờ này thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Tốc độ gió ở Phường Láng giờ này bao nhiêu?"}
})

# idx=1877: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 1877, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Nhiệt độ thực tế cảm nhận được tại Bệnh viện Bạch Mai bây giờ là bao nhiêu nhỉ?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=1922: "Phường Văn Miếu - QTG" clean ward
SAMPLES.append({
    "_v6_idx": 1922, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Dự báo thời tiết Phường Văn Miếu - Quốc Tử Giám ngày mai?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Dự báo thời tiết Phường Văn Miếu - Quốc Tử Giám ngày mai"}
})

# idx=1951: "Ngọc Hà, Ba Đình" → Phường Ngọc Hà
SAMPLES.append({
    "_v6_idx": 1951, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Bữa nay ở Ngọc Hà, Ba Đình có nên mặc áo khoác không nhỉ?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Hôm nay ở Phường Ngọc Hà (Ba Đình) có nên mặc áo khoác không?"}
})

# idx=1981: Hồ Tây → T5
SAMPLES.append({
    "_v6_idx": 1981, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Chiều nay Hồ Tây có độ che phủ mây khoảng bao nhiêu lúc hoàng hôn?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2027: Bệnh viện Bạch Mai → T5
SAMPLES.append({
    "_v6_idx": 2027, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bao nhiêu độ ở Bệnh viện Bạch Mai giờ này?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2065: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 2065, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Bữa nay ở Lăng Bác thì nên chọn đồ như thế nào cho hợp lý?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2066: "Bến xe Nam Từ Liêm với Lăng Chủ tịch" — both POI → T5
SAMPLES.append({
    "_v6_idx": 2066, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm nay thời tiết ở Bến xe Nam Từ Liêm với Lăng Chủ tịch chỗ nào lạnh hơn nhỉ?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# idx=2067: "phường Láng" → clean ward
SAMPLES.append({
    "_v6_idx": 2067, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Ở phường Láng có nguy cơ ngập không nhỉ?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Láng có nguy cơ ngập lụt không?"}
})

# idx=2083: Lăng Bác → T5
SAMPLES.append({
    "_v6_idx": 2083, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Lăng Bác bây giờ là thời tiết ra sao? Nóng hay lạnh?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# ═══════════════════════════════════════════════════════════════════════════
# FIX_CONTEXT (25)
# ═══════════════════════════════════════════════════════════════════════════

# idx=643 ctx=Hoàn Kiếm, weather_overview → ward
SAMPLES.append({
    "_v6_idx": 643, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Tóm tắt thời tiết chỗ đó đi?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tóm tắt thời tiết Phường Hoàn Kiếm hôm nay"}
})

# idx=655 ctx=Tây Hồ, expert UV → ward
SAMPLES.append({
    "_v6_idx": 655, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay UV thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Chỉ số UV Phường Tây Hồ hôm nay bao nhiêu?")}
    ],
    "input": "Sáng mai chỉ số UV ra sao?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chỉ số UV sáng mai ở Phường Tây Hồ bao nhiêu?"}
})

# idx=657 ctx=Gia Lâm, weather_alert → district keep (Huyện Gia Lâm)
SAMPLES.append({
    "_v6_idx": 657, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Có thông tin gì cần chú ý không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Gia Lâm hôm nay có cảnh báo thời tiết nào cần chú ý không?"}
})

# idx=671 ctx=Hoàng Mai, rain → ward
SAMPLES.append({
    "_v6_idx": 671, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Chiều có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay Phường Hoàng Mai có mưa không?"}
})

# idx=679 ctx=Tây Hồ, rain → ward
SAMPLES.append({
    "_v6_idx": 679, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.85,
                           "Phường Tây Hồ hôm nay có mưa không?")}
    ],
    "input": "Thế mai thì sao?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai Phường Tây Hồ có mưa không?"}
})

# idx=696 ctx=Hà Đông, weather_overview → ward (Phường Hà Đông)
SAMPLES.append({
    "_v6_idx": 696, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "Hôm nay khu đó ra sao?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tổng quan thời tiết Phường Hà Đông hôm nay thế nào?"}
})

# idx=721 ctx=Hoàng Mai, current → ward
SAMPLES.append({
    "_v6_idx": 721, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hiện tại thế nào?")}
    ],
    "input": "Bây giờ thời tiết thế nào, nắng hay mưa?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai bây giờ đang nắng hay mưa?"}
})

# idx=724 ctx=Đống Đa, temperature → ward
SAMPLES.append({
    "_v6_idx": 724, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Thế còn nhiệt độ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ hiện tại ở Phường Đống Đa bao nhiêu?"}
})

# idx=750 ctx=Đống Đa, rain → ward
SAMPLES.append({
    "_v6_idx": 750, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Trời có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ở Phường Đống Đa có mưa không?"}
})

# idx=757 ctx=Sóc Sơn, location_comparison → district (Huyện Sóc Sơn — comparison thường district)
SAMPLES.append({
    "_v6_idx": 757, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "So sánh Sóc Sơn với Đông Anh",
         "assistant": asst("location_comparison", "district", 0.85,
                           "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh")}
    ],
    "input": "Chỗ đó thì thế nào?",
    "output": {"intent": "location_comparison", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết ở Huyện Sóc Sơn như thế nào?"}
})

# idx=782 ctx=Sóc Sơn, comparison → district keep
SAMPLES.append({
    "_v6_idx": 782, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "So sánh Sóc Sơn với khu vực khác",
         "assistant": asst("location_comparison", "district", 0.85,
                           "So sánh thời tiết Huyện Sóc Sơn với khu vực khác")}
    ],
    "input": "Còn tình hình ở đó thì sao?",
    "output": {"intent": "location_comparison", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Còn tình hình thời tiết ở Huyện Sóc Sơn thì như thế nào?"}
})

# idx=795 ctx=Đông Anh, seasonal → district (rural seasonal)
SAMPLES.append({
    "_v6_idx": 795, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đông Anh mùa này thế nào?",
         "assistant": asst("seasonal_context", "district", 0.85,
                           "Thời tiết mùa này ở Huyện Đông Anh ra sao?")}
    ],
    "input": "Thời tiết bây giờ thế nào?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết hiện tại ở Huyện Đông Anh ra sao?"}
})

# idx=815 ctx=Đông Anh, activity → district keep
SAMPLES.append({
    "_v6_idx": 815, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đông Anh hôm nay có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Đông Anh hôm nay có cảnh báo thời tiết không?")}
    ],
    "input": "Ảnh hưởng đến đi lại không?",
    "output": {"intent": "activity_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Cảnh báo thời tiết ở Huyện Đông Anh hôm nay có ảnh hưởng đến đi lại không?"}
})

# idx=826 ctx=Hoàng Mai, seasonal → ward
SAMPLES.append({
    "_v6_idx": 826, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm qua nhiệt độ bao nhiêu?",
         "assistant": asst("historical_weather", "ward", 0.85,
                           "Nhiệt độ hôm qua ở Phường Hoàng Mai bao nhiêu?")}
    ],
    "input": "Chênh lệch nhiệt độ là bao nhiêu?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ Phường Hoàng Mai hôm nay chênh lệch bao nhiêu so với hôm qua?"}
})

# idx=844 ctx=Gia Lâm, weather_alert → district
SAMPLES.append({
    "_v6_idx": 844, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Đó có cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Gia Lâm hôm nay có cảnh báo thời tiết gì không?"}
})

# idx=845 ctx=Hoàng Mai, hourly → ward
SAMPLES.append({
    "_v6_idx": 845, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Sáng mai thời tiết thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai ở Phường Hoàng Mai thời tiết thế nào?"}
})

# idx=855 ctx=Sóc Sơn, weather_overview → district keep
SAMPLES.append({
    "_v6_idx": 855, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Sóc Sơn hôm nay thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "Ngày mai thời tiết ở đó như thế nào?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai ở Huyện Sóc Sơn thời tiết thế nào?"}
})

# idx=888 ctx=Long Biên, weather_overview → ward
SAMPLES.append({
    "_v6_idx": 888, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Hôm nay tổng quan ở đó thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tổng quan thời tiết Phường Long Biên hôm nay thế nào?"}
})

# idx=893 ctx=Cầu Giấy, expert → ward
SAMPLES.append({
    "_v6_idx": 893, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy áp suất thay đổi thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Áp suất ở Phường Cầu Giấy thay đổi thế nào?")}
    ],
    "input": "Có ảnh hưởng đến sức khỏe không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Áp suất thay đổi ở Phường Cầu Giấy có ảnh hưởng đến sức khỏe không?"}
})

# idx=900 ctx=Tây Hồ, rain → ward
SAMPLES.append({
    "_v6_idx": 900, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Ở đây có khả năng mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ hôm nay có khả năng mưa không?"}
})

# idx=904 ctx=Mê Linh, weather_overview → district keep (rural collision Xã/Huyện, "Mê Linh" bare often Huyện)
SAMPLES.append({
    "_v6_idx": 904, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Mê Linh thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Mê Linh hiện tại thế nào?")}
    ],
    "input": "Thời tiết ra sao ở đó?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết hiện tại ở Huyện Mê Linh như thế nào?"}
})

# idx=909 ctx=Ba Đình, weather_alert → district
SAMPLES.append({
    "_v6_idx": 909, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Ba Đình có cảnh báo thời tiết nào không?")}
    ],
    "input": "Có tin gì mới không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Có thông báo thời tiết mới gì cho Quận Ba Đình không?"}
})

# idx=929 ctx=Ba Đình, current → ward
SAMPLES.append({
    "_v6_idx": 929, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hiện tại thế nào?")}
    ],
    "input": "Bây giờ thời tiết ở đó ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết Phường Ba Đình bây giờ ra sao?"}
})

# idx=968 ctx=Hoàng Mai, wind → ward
SAMPLES.append({
    "_v6_idx": 968, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai sáng nay thế nào?",
         "assistant": asst("hourly_forecast", "ward", 0.85,
                           "Dự báo sáng nay ở Phường Hoàng Mai thế nào?")}
    ],
    "input": "Tốc độ gió bao nhiêu?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tốc độ gió Phường Hoàng Mai sáng nay bao nhiêu km/h?"}
})

# idx=972 ctx=Ba Đình, current → ward
SAMPLES.append({
    "_v6_idx": 972, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hiện tại thế nào?")}
    ],
    "input": "Bây giờ nắng không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Ba Đình bây giờ có nắng không?"}
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

out_path = Path(__file__).parent / 'batch_03_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
