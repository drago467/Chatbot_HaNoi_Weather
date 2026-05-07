"""V7 Batch 6 — Manual fix samples (50 total).

Composition:
- 2 FIX_POI_ADMIN: Phường Ngọc Hà (Ba Đình) clean extracts (final POI batch)
- 48 FIX_CONTEXT: ~40 default Phường, ~8 keep district (Sóc Sơn/Gia Lâm/Đông Anh/Thanh Trì rural)

After this batch: only ~57 FIX_CONTEXT remaining for final batch 7.
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# FIX_POI_ADMIN — final 2
# ═══════════════════════════════════════════════════════════════════════════

# idx=3399: "phường Ngọc Hà, Ba Đình"
SAMPLES.append({
    "_v6_idx": 3399, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Chiều nay từ 13h đến 17h ở phường Ngọc Hà, Ba Đình có nắng không?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Chiều nay 13-17h Phường Ngọc Hà (Ba Đình) có nắng không?"}
})

# idx=3405
SAMPLES.append({
    "_v6_idx": 3405, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "chiều nay từ 13h đến 17h ở phường Ngọc Hà, Ba Đình có nắng không?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Chiều nay 13-17h Phường Ngọc Hà (Ba Đình) có nắng không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# FIX_CONTEXT (48)
# ═══════════════════════════════════════════════════════════════════════════

# idx=1984 ctx=Tây Hồ, rain → ward
SAMPLES.append({
    "_v6_idx": 1984, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Có khả năng mưa ở đây không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ hôm nay có khả năng mưa không?"}
})

# idx=1987 ctx=Sóc Sơn → district keep (rural)
SAMPLES.append({
    "_v6_idx": 1987, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Sóc Sơn thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Sóc Sơn hiện tại thế nào?")}
    ],
    "input": "Hôm nay ở đó thế nào?",
    "output": {"intent": "current_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết hôm nay ở Huyện Sóc Sơn thế nào?"}
})

# idx=1992 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 1992, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Tối nay thời tiết ra sao?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Tây Hồ thời tiết ra sao?"}
})

# idx=2003 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2003, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "Bây giờ nhiệt độ chỗ đó?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ hiện tại ở Phường Cầu Giấy bao nhiêu?"}
})

# idx=2008 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2008, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Nơi đó có sương sáng sớm không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng sớm Phường Đống Đa có sương mù không?"}
})

# idx=2033 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2033, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Đêm nay?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Đêm nay Phường Tây Hồ dự báo thế nào?"}
})

# idx=2056 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2056, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Hôm nay có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay Phường Tây Hồ có khả năng mưa không?"}
})

# idx=2058 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2058, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "gió thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió ở Phường Đống Đa hiện tại thế nào?"}
})

# idx=2064 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2064, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hiện tại thế nào?")}
    ],
    "input": "hiện tại khu đó ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai hiện tại trời ra sao?"}
})

# idx=2073 ctx=Hà Đông → ward
SAMPLES.append({
    "_v6_idx": 2073, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "hôm nay khu đó ra sao?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tổng quan thời tiết Phường Hà Đông hôm nay"}
})

# idx=2118 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2118, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Hôm nay trời có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đống Đa hôm nay có mưa không?"}
})

# idx=2123 ctx=Sóc Sơn → district
SAMPLES.append({
    "_v6_idx": 2123, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "So sánh Sóc Sơn với khu khác",
         "assistant": asst("location_comparison", "district", 0.85,
                           "So sánh thời tiết Huyện Sóc Sơn với khu khác")}
    ],
    "input": "Tình hình ở đó thế nào?",
    "output": {"intent": "location_comparison", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Còn tình hình thời tiết ở Huyện Sóc Sơn thì thế nào?"}
})

# idx=2130 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2130, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Chỗ đó có nồm không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đống Đa có nồm ẩm không?"}
})

# idx=2158 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2158, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay áp suất thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Áp suất Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Có tác động gì đến sức khỏe không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Áp suất thay đổi ở Phường Cầu Giấy có ảnh hưởng đến sức khỏe không?"}
})

# idx=2167 ctx=Long Biên → ward
SAMPLES.append({
    "_v6_idx": 2167, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Có mưa ở đó không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Long Biên có mưa không?"}
})

# idx=2176 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2176, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Hôm nay có mát không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai hôm nay có mát hơn hôm qua không?"}
})

# idx=2219 ctx=Long Biên scope=ward (v6 đã đúng)
SAMPLES.append({
    "_v6_idx": 2219, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Thời tiết dạo này ra sao?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết gần đây ở Phường Long Biên thế nào?"}
})

# idx=2222 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2222, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.85,
                           "Phường Đống Đa hôm nay có mưa không?")}
    ],
    "input": "Mưa đến mấy giờ?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Mưa ở Phường Đống Đa đến mấy giờ thì tạnh?"}
})

# idx=2231 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2231, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Cầu Giấy ngày mai thế nào?")}
    ],
    "input": "Ngày kia thời tiết như thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo thời tiết ngày kia ở Phường Cầu Giấy"}
})

# idx=2233 ctx=Hà Đông → ward
SAMPLES.append({
    "_v6_idx": 2233, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "khu đó hôm nay nhìn chung thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhìn chung thời tiết Phường Hà Đông hôm nay thế nào?"}
})

# idx=2238 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2238, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Hôm nay chiều nhiệt độ bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều nay Phường Cầu Giấy nhiệt độ bao nhiêu?"}
})

# idx=2245 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2245, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "hôm qua thế nào?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua ở Phường Cầu Giấy thời tiết thế nào?"}
})

# idx=2246 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2246, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "hôm nay có gì thú vị ngoài trời không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay Phường Hoàng Mai có hoạt động ngoài trời nào thú vị không?"}
})

# idx=2268 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2268, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Cuối tuần sẽ ra sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo thời tiết cuối tuần ở Phường Cầu Giấy"}
})

# idx=2272 ctx=Thanh Trì → district keep (collision Xã/Huyện rural)
SAMPLES.append({
    "_v6_idx": 2272, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Trì hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Thanh Trì hiện tại thế nào?")}
    ],
    "input": "Gió có thổi không?",
    "output": {"intent": "wind_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Hôm nay Huyện Thanh Trì có gió không?"}
})

# idx=2280 ctx=Hai Bà Trưng → ward
SAMPLES.append({
    "_v6_idx": 2280, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hai Bà Trưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?")}
    ],
    "input": "Chỗ đó có thích hợp cho việc chạy bộ không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hai Bà Trưng hôm nay có phù hợp để chạy bộ không?"}
})

# idx=2282 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2282, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "tối nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Tây Hồ thời tiết ra sao?"}
})

# idx=2288 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2288, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "ở đó sáng mai thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai Phường Tây Hồ trời thế nào?"}
})

# idx=2294 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2294, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Tây Hồ ngày mai thế nào?")}
    ],
    "input": "Chiều có thời tiết chạy bộ được không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều mai Phường Tây Hồ có phù hợp chạy bộ không?"}
})

# idx=2303 ctx=Hai Bà Trưng → ward
SAMPLES.append({
    "_v6_idx": 2303, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hai Bà Trưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?")}
    ],
    "input": "Bên đó có phù hợp chạy bộ không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hai Bà Trưng hôm nay có phù hợp để chạy bộ không?"}
})

# idx=2306 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2306, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Tháng này mưa nhiều không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tháng này Phường Cầu Giấy có mưa nhiều không?"}
})

# idx=2333 ctx=Gia Lâm → district
SAMPLES.append({
    "_v6_idx": 2333, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Khu đó chiều nay mưa không?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Chiều nay Huyện Gia Lâm có mưa không?"}
})

# idx=2334 ctx=Đông Anh → district keep
SAMPLES.append({
    "_v6_idx": 2334, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đông Anh hôm nay có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Đông Anh hôm nay có cảnh báo thời tiết không?")}
    ],
    "input": "Mức độ thế nào?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Cảnh báo thời tiết Huyện Đông Anh hôm nay mức độ ra sao?"}
})

# idx=2367 ctx=Sóc Sơn → district keep
SAMPLES.append({
    "_v6_idx": 2367, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "So sánh Sóc Sơn với khu khác",
         "assistant": asst("location_comparison", "district", 0.85,
                           "So sánh thời tiết Huyện Sóc Sơn với khu khác")}
    ],
    "input": "Còn chỗ đó thì sao?",
    "output": {"intent": "location_comparison", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết ở Huyện Sóc Sơn như thế nào?"}
})

# idx=2368 ctx=Gia Lâm → district keep
SAMPLES.append({
    "_v6_idx": 2368, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Gia Lâm hôm nay có cảnh báo thời tiết không?")}
    ],
    "input": "Có mưa rào không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Gia Lâm hôm nay có giông bão không?"}
})

# idx=2371 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2371, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Gió ở đó thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Gió tại Phường Tây Hồ hôm nay thế nào?"}
})

# idx=2415 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2415, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Tây Hồ ngày mai thế nào?")}
    ],
    "input": "Chiều chạy bộ được không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều mai Phường Tây Hồ có phù hợp chạy bộ không?"}
})

# idx=2458 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2458, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay UV thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "UV ở Phường Cầu Giấy hôm nay bao nhiêu?")}
    ],
    "input": "UV cao nhất lúc mấy giờ?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Cầu Giấy hôm nay cao nhất lúc mấy giờ?"}
})

# idx=2461 ctx=Thanh Xuân → ward
SAMPLES.append({
    "_v6_idx": 2461, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "Khu đó có chỉ số UV cao không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Thanh Xuân hiện tại có cao không?"}
})

# idx=2494 ctx=Hà Đông → ward
SAMPLES.append({
    "_v6_idx": 2494, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "Khu đó hôm nay nhìn chung thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhìn chung thời tiết Phường Hà Đông hôm nay thế nào?"}
})

# idx=2497 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2497, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Chỗ đó có đáng để đi dạo không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết Phường Hoàng Mai có thích hợp để đi dạo không?"}
})

# idx=2531 ctx=Đống Đa → ward
SAMPLES.append({
    "_v6_idx": 2531, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "Nhiệt độ thì sao?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ hiện tại Phường Đống Đa bao nhiêu?"}
})

# idx=2553 ctx=Thanh Xuân → ward
SAMPLES.append({
    "_v6_idx": 2553, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "Cuối tuần ở đó thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Cuối tuần này Phường Thanh Xuân thời tiết thế nào?"}
})

# idx=2559 ctx=Gia Lâm → district
SAMPLES.append({
    "_v6_idx": 2559, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Gia Lâm hôm nay gió thế nào?",
         "assistant": asst("wind_query", "district", 0.85,
                           "Gió Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Đi xe có bị ảnh hưởng không?",
    "output": {"intent": "activity_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Gió Huyện Gia Lâm hôm nay có ảnh hưởng đến việc đi xe không?"}
})

# idx=2567 ctx=Cầu Giấy → ward
SAMPLES.append({
    "_v6_idx": 2567, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy giờ thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hiện tại thế nào?")}
    ],
    "input": "Còn lúc này trời ra sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Trời ở Phường Cầu Giấy lúc này ra sao?"}
})

# idx=2582 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2582, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm qua thế nào?",
         "assistant": asst("historical_weather", "ward", 0.85,
                           "Hôm qua Phường Hoàng Mai thế nào?")}
    ],
    "input": "Hôm nay mát hơn không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai hôm nay có mát hơn hôm qua không?"}
})

# idx=2584 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2584, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Hôm nay có thể làm gì ở đây không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay Phường Hoàng Mai có thể làm gì thú vị không?"}
})

# idx=2590 ctx=Tây Hồ → ward
SAMPLES.append({
    "_v6_idx": 2590, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Tây Hồ ngày mai thế nào?")}
    ],
    "input": "chiều chạy bộ được không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Chiều mai Phường Tây Hồ có phù hợp chạy bộ không?"}
})

# idx=2605 ctx=Hoàn Kiếm → ward
SAMPLES.append({
    "_v6_idx": 2605, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Có thông tin gì về gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Có thông tin gì về gió ở Phường Hoàn Kiếm không?"}
})

# idx=2614 ctx=Hoàng Mai → ward
SAMPLES.append({
    "_v6_idx": 2614, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai sáng mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Hoàng Mai sáng mai thế nào?")}
    ],
    "input": "Cần mang áo mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai đi học ở Phường Hoàng Mai có cần mang áo mưa không?"}
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

out_path = Path(__file__).parent / 'batch_06_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
