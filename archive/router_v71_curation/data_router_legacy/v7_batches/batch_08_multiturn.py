"""V7 Batch 8 (Phase 4 — multi-turn) — 50 samples.

Composition:
- 25 TIME-INHERITANCE samples: turn ≥2 anaphoric time reference must propagate
  the time-window anchor from prior turn (e.g. "thứ 2 tuần sau" → "thứ 3 thì sao"
  resolves to "thứ 3 tuần sau" NOT "thứ 3 tuần này"). Includes 3 turn=3 chains.
- 25 LOCATION-INHERITANCE samples: turn ≥2 anaphoric "ở đó/khu đó/nơi đó/chỗ đó"
  must keep prior turn's prefix exactly (Phường→Phường, Xã→Xã, Quận→Quận, Huyện→Huyện).
  Includes 2 turn=3 chains and pure-ward variety (Minh Châu, Yên Nghĩa, Bồ Đề, Yên Lãng,
  Nghĩa Đô, Yên Hòa, Việt Hưng, Phú Thượng, Định Công, Phú Diễn).

All samples T3=0.80 (multi-turn inherited tier) unless explicit-switch (T2=0.85).
All wards/districts validated against dim_ward.csv canonical.
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# A) TIME-INHERITANCE (25)
# ═══════════════════════════════════════════════════════════════════════════

# T-01: "thứ 2 tuần sau" → "thứ 3 thì sao?" — PRIMARY BUG CASE Phường Cầu Giấy
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Cầu Giấy thứ 2 tuần sau thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Cầu Giấy thứ 2 tuần sau thế nào?")}
    ],
    "input": "thứ 3 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Cầu Giấy thứ 3 tuần sau thế nào?"}
})

# T-02: tuần sau weekday inherit, Phường Long Biên
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Long Biên thứ 4 tuần sau dự báo thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Long Biên thứ 4 tuần sau thế nào?")}
    ],
    "input": "thứ 5 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Long Biên thứ 5 tuần sau thế nào?"}
})

# T-03: tuần sau, pure-xã Minh Châu
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Xã Minh Châu thứ 6 tuần sau có mưa không?",
         "assistant": asst("rain_query", "ward", 0.92,
                           "Xã Minh Châu thứ 6 tuần sau có mưa không?")}
    ],
    "input": "Chủ nhật thì sao?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Minh Châu chủ nhật tuần sau có mưa không?"}
})

# T-04: tuần này (current week) inherit
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Hoàn Kiếm thứ 2 tuần này nóng bao nhiêu độ?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Phường Hoàn Kiếm thứ 2 tuần này nóng bao nhiêu độ?")}
    ],
    "input": "thứ 4 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàn Kiếm thứ 4 tuần này nóng bao nhiêu độ?"}
})

# T-05: tuần trước historical inherit, Phường Đống Đa
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Đống Đa thứ 3 tuần trước thời tiết ra sao?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Thời tiết Phường Đống Đa thứ 3 tuần trước ra sao?")}
    ],
    "input": "thứ 5 thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết Phường Đống Đa thứ 5 tuần trước ra sao?"}
})

# T-06: ngày mai → buổi tối thì sao
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Tây Hồ ngày mai nhiệt độ bao nhiêu?",
         "assistant": asst("temperature_query", "ward", 0.92,
                           "Nhiệt độ Phường Tây Hồ ngày mai bao nhiêu?")}
    ],
    "input": "buổi tối thì sao?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ Phường Tây Hồ ngày mai buổi tối bao nhiêu?"}
})

# T-07: ngày mai → sáng, pure phường Yên Nghĩa
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Yên Nghĩa ngày mai có mưa không?",
         "assistant": asst("rain_query", "ward", 0.92,
                           "Phường Yên Nghĩa ngày mai có mưa không?")}
    ],
    "input": "sáng thì sao?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Nghĩa ngày mai sáng có mưa không?"}
})

# T-08: ngày kia inherit, pure xã Quốc Oai
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Xã Quốc Oai ngày kia thời tiết thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Xã Quốc Oai ngày kia thế nào?")}
    ],
    "input": "có gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Quốc Oai ngày kia có gió không?"}
})

# T-09: cuối tuần inheritance
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Hà Đông cuối tuần này thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Hà Đông cuối tuần này thế nào?")}
    ],
    "input": "thứ 7 còn nắng không?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hà Đông thứ 7 cuối tuần này có còn nắng không?"}
})

# T-10: tháng sau inherit, city scope
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Hà Nội tháng sau thời tiết thế nào?",
         "assistant": asst("seasonal_context", "city", 0.85,
                           "Thời tiết Hà Nội tháng sau thế nào?")}
    ],
    "input": "đầu tháng thì sao?",
    "output": {"intent": "seasonal_context", "scope": "city", "confidence": 0.80,
               "rewritten_query": "Thời tiết Hà Nội đầu tháng sau thế nào?"}
})

# T-11: hôm qua → hôm kia, Phường Nghĩa Đô (pure phường - Cầu Giấy)
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Nghĩa Đô hôm qua nhiệt độ cao nhất bao nhiêu?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Nghĩa Đô hôm qua nhiệt độ cao nhất bao nhiêu?")}
    ],
    "input": "hôm kia thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Nghĩa Đô hôm kia nhiệt độ cao nhất bao nhiêu?"}
})

# T-12: hôm kia → tuần trước, Xã Sóc Sơn (collision rural, district default)
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Huyện Sóc Sơn hôm kia có mưa không?",
         "assistant": asst("historical_weather", "district", 0.92,
                           "Huyện Sóc Sơn hôm kia có mưa không?")}
    ],
    "input": "tuần trước thì sao?",
    "output": {"intent": "historical_weather", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Sóc Sơn tuần trước có mưa không?"}
})

# T-13: thứ 7 tuần trước → chủ nhật, Phường Phú Thượng
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Phú Thượng thứ 7 tuần trước thời tiết ra sao?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Phú Thượng thứ 7 tuần trước thời tiết ra sao?")}
    ],
    "input": "chủ nhật thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Phú Thượng chủ nhật tuần trước thời tiết ra sao?"}
})

# T-14: TURN=3 chain — thứ 2 tuần sau → thứ 3 → thứ 4 (cùng tuần sau)
SAMPLES.append({
    "_kind": "T_time_inherit_turn3",
    "history": [
        {"user": "Phường Cầu Giấy thứ 2 tuần sau thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Cầu Giấy thứ 2 tuần sau thế nào?")},
        {"user": "thứ 3 thì sao?",
         "assistant": asst("daily_forecast", "ward", 0.80,
                           "Dự báo Phường Cầu Giấy thứ 3 tuần sau thế nào?")}
    ],
    "input": "thứ 4 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Cầu Giấy thứ 4 tuần sau thế nào?"}
})

# T-15: TURN=3 — ngày mai → buổi sáng → buổi chiều (cùng ngày mai)
SAMPLES.append({
    "_kind": "T_time_inherit_turn3",
    "history": [
        {"user": "Phường Tây Hồ ngày mai có mưa không?",
         "assistant": asst("rain_query", "ward", 0.92,
                           "Phường Tây Hồ ngày mai có mưa không?")},
        {"user": "buổi sáng thì sao?",
         "assistant": asst("rain_query", "ward", 0.80,
                           "Phường Tây Hồ ngày mai buổi sáng có mưa không?")}
    ],
    "input": "buổi chiều thì sao?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ ngày mai buổi chiều có mưa không?"}
})

# T-16: cuối tuần này → thứ 7
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Bạch Mai cuối tuần này thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Bạch Mai cuối tuần này thế nào?")}
    ],
    "input": "thứ 7 nắng to không?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Bạch Mai thứ 7 cuối tuần này có nắng to không?"}
})

# T-17: tuần này rain, ngày mưa nhiều nhất, Phường Yên Hòa
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Yên Hòa tuần này mưa thế nào?",
         "assistant": asst("rain_query", "ward", 0.92,
                           "Phường Yên Hòa tuần này có mưa nhiều không?")}
    ],
    "input": "ngày nào mưa nhiều nhất?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Hòa tuần này ngày nào mưa nhiều nhất?"}
})

# T-18: tháng trước → tuần đầu tháng, Phường Vĩnh Tuy
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Vĩnh Tuy tháng trước nóng nhất ngày nào?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Vĩnh Tuy tháng trước nóng nhất ngày nào?")}
    ],
    "input": "tuần đầu tháng thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Vĩnh Tuy tuần đầu tháng trước thời tiết thế nào?"}
})

# T-19: thứ 5 tuần sau → 2 days, Phường Định Công
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Định Công thứ 5 tuần sau thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Định Công thứ 5 tuần sau thế nào?")}
    ],
    "input": "thứ 6 và thứ 7 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Định Công thứ 6 và thứ 7 tuần sau thế nào?"}
})

# T-20: ngày 15 tháng sau (semi-formal date)
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Đông Ngạc ngày 15 tháng sau dự báo thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Đông Ngạc ngày 15 tháng sau thế nào?")}
    ],
    "input": "ngày 20 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Đông Ngạc ngày 20 tháng sau thế nào?"}
})

# T-21: đầu tháng tới → cuối tháng, city
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Hà Nội đầu tháng tới thế nào?",
         "assistant": asst("seasonal_context", "city", 0.85,
                           "Hà Nội đầu tháng tới thời tiết thế nào?")}
    ],
    "input": "cuối tháng thì sao?",
    "output": {"intent": "seasonal_context", "scope": "city", "confidence": 0.80,
               "rewritten_query": "Hà Nội cuối tháng tới thời tiết thế nào?"}
})

# T-22: tuần đầu tháng → tuần cuối tháng, Phường Lĩnh Nam
SAMPLES.append({
    "_kind": "T_time_inherit",
    "history": [
        {"user": "Phường Lĩnh Nam tuần đầu tháng này có mưa không?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Lĩnh Nam tuần đầu tháng này có mưa không?")}
    ],
    "input": "tuần cuối tháng thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Lĩnh Nam tuần cuối tháng này có mưa không?"}
})

# T-23: TURN=3 weather alert chain (cảnh báo ngày mai → ngày kia → cuối tuần)
SAMPLES.append({
    "_kind": "T_time_inherit_turn3",
    "history": [
        {"user": "Huyện Đông Anh ngày mai có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.92,
                           "Huyện Đông Anh ngày mai có cảnh báo thời tiết gì không?")},
        {"user": "ngày kia thì sao?",
         "assistant": asst("weather_alert", "district", 0.80,
                           "Huyện Đông Anh ngày kia có cảnh báo gì không?")}
    ],
    "input": "thứ 7 cuối tuần này thì sao?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Đông Anh thứ 7 cuối tuần này có cảnh báo gì không?"}
})

# T-24: thứ 2 đầu tháng sau → ngày kia (giả định không kế thừa "tháng sau")
# Thực ra "ngày kia" là tuyệt đối, không phụ thuộc tháng sau → reset về today+2
SAMPLES.append({
    "_kind": "T_time_inherit_reset",
    "history": [
        {"user": "Phường Hoàng Mai thứ 2 đầu tháng sau dự báo thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Hoàng Mai thứ 2 đầu tháng sau thế nào?")}
    ],
    "input": "ngày kia thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai ngày kia dự báo thế nào?"}
})

# T-25: time scope refinement — "tuần này" → "ngày mai" (không cần tuần này)
SAMPLES.append({
    "_kind": "T_time_inherit_refine",
    "history": [
        {"user": "Phường Khương Đình tuần này thời tiết thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo Phường Khương Đình tuần này thế nào?")}
    ],
    "input": "ngày mai cụ thể thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Khương Đình ngày mai dự báo cụ thể thế nào?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# B) LOCATION-INHERITANCE (25)
# ═══════════════════════════════════════════════════════════════════════════

# L-01: pure xã Minh Châu — "ở đó" must keep Xã
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_xa",
    "history": [
        {"user": "Xã Minh Châu hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Minh Châu hôm nay thế nào?")}
    ],
    "input": "ở đó có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Minh Châu hôm nay có mưa không?"}
})

# L-02: pure xã Yên Lãng (Mê Linh) — "khu đó" keep Xã
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_xa",
    "history": [
        {"user": "Xã Yên Lãng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Yên Lãng hiện tại thế nào?")}
    ],
    "input": "khu đó nhiệt độ bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ ở Xã Yên Lãng hiện tại bao nhiêu?"}
})

# L-03: collision-xã Mỹ Đức — must keep Xã (NOT promote to Huyện)
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_xa",
    "history": [
        {"user": "Xã Mỹ Đức hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Mỹ Đức hôm nay thế nào?")}
    ],
    "input": "có cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Mỹ Đức hôm nay có cảnh báo thời tiết gì không?"}
})

# L-04: pure phường Yên Nghĩa — "nơi đó" keep
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Yên Nghĩa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Yên Nghĩa hôm nay thế nào?")}
    ],
    "input": "nơi đó có gió mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Nghĩa có gió mạnh không?"}
})

# L-05: pure phường Bồ Đề
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Bồ Đề hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Bồ Đề hôm nay thế nào?")}
    ],
    "input": "khu vực đó độ ẩm cao không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Bồ Đề độ ẩm cao không?"}
})

# L-06: pure phường Nghĩa Đô (Cầu Giấy district)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Nghĩa Đô hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Nghĩa Đô hôm nay thế nào?")}
    ],
    "input": "ở đó UV thế nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Nghĩa Đô UV hôm nay thế nào?"}
})

# L-07: pure phường Văn Miếu - QTG
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Văn Miếu - Quốc Tử Giám hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Văn Miếu - Quốc Tử Giám hôm nay thế nào?")}
    ],
    "input": "buổi tối thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Văn Miếu - Quốc Tử Giám buổi tối thế nào?"}
})

# L-08: pure phường Yên Hòa (Cầu Giấy)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Yên Hòa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Yên Hòa hôm nay thế nào?")}
    ],
    "input": "đêm nay khu đó ra sao?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Hòa đêm nay thời tiết ra sao?"}
})

# L-09: collision Phường Cầu Giấy — "ở đó" keep Phường
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "ở đó tối nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Cầu Giấy tối nay thời tiết thế nào?"}
})

# L-10: collision Phường Long Biên
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "khu đó có nắng không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Long Biên có nắng không?"}
})

# L-11: collision Phường Hoàn Kiếm
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "chỗ đó tầm nhìn xa thế nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàn Kiếm tầm nhìn xa hiện tại thế nào?"}
})

# L-12: collision Phường Đống Đa
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Đống Đa hôm nay thế nào?")}
    ],
    "input": "nơi đó áp suất bao nhiêu?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đống Đa áp suất hiện tại bao nhiêu?"}
})

# L-13: collision Phường Hai Bà Trưng
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Hai Bà Trưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?")}
    ],
    "input": "khu đó độ ẩm thế nào?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hai Bà Trưng độ ẩm hiện tại thế nào?"}
})

# L-14: collision Phường Tây Hồ
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "ở đó chiều nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ chiều nay thời tiết thế nào?"}
})

# L-15: collision Phường Hà Đông
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")}
    ],
    "input": "khu đó dự báo ngày mai thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hà Đông ngày mai dự báo thế nào?"}
})

# L-16: collision Phường Hoàng Mai
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "nơi đó có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Mai hôm nay có mưa không?"}
})

# L-17: collision Phường Thanh Xuân
SAMPLES.append({
    "_kind": "L_loc_inherit_collision_phuong",
    "history": [
        {"user": "Phường Thanh Xuân hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Thanh Xuân hôm nay thế nào?")}
    ],
    "input": "chỗ đó có nóng không?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Thanh Xuân hôm nay có nóng không?"}
})

# L-18: pure phường Định Công (Hoàng Mai)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Định Công hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Định Công hôm nay thế nào?")}
    ],
    "input": "khu đó hôm nay UV cao không?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Định Công UV hôm nay có cao không?"}
})

# L-19: pure phường Việt Hưng (Long Biên)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Việt Hưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Việt Hưng hôm nay thế nào?")}
    ],
    "input": "ở đó gió mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Việt Hưng có gió mạnh không?"}
})

# L-20: pure phường Phú Thượng (Tây Hồ)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Phú Thượng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Phú Thượng hôm nay thế nào?")}
    ],
    "input": "nơi đó có ổn không?",
    "output": {"intent": "smalltalk_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Phú Thượng thời tiết có ổn không?"}
})

# L-21: pure phường Phú Diễn (Bắc Từ Liêm)
SAMPLES.append({
    "_kind": "L_loc_inherit_pure_phuong",
    "history": [
        {"user": "Phường Phú Diễn hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Phú Diễn hôm nay thế nào?")}
    ],
    "input": "khu đó tổng quan ngày mai thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tổng quan thời tiết Phường Phú Diễn ngày mai"}
})

# L-22: district inheritance — Huyện Sóc Sơn
SAMPLES.append({
    "_kind": "L_loc_inherit_district",
    "history": [
        {"user": "Huyện Sóc Sơn hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Sóc Sơn hiện tại thế nào?")}
    ],
    "input": "khu đó có cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Sóc Sơn có cảnh báo thời tiết gì không?"}
})

# L-23: district inheritance — Huyện Đông Anh
SAMPLES.append({
    "_kind": "L_loc_inherit_district",
    "history": [
        {"user": "Huyện Đông Anh hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Đông Anh hôm nay thế nào?")}
    ],
    "input": "ở đó dự báo ngày mai thế nào?",
    "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Đông Anh ngày mai dự báo thế nào?"}
})

# L-24: district Huyện Ba Vì
SAMPLES.append({
    "_kind": "L_loc_inherit_district",
    "history": [
        {"user": "Huyện Ba Vì mùa này thế nào?",
         "assistant": asst("seasonal_context", "district", 0.92,
                           "Thời tiết Huyện Ba Vì mùa này thế nào?")}
    ],
    "input": "khu đó nhiệt độ thường ra sao?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ Huyện Ba Vì mùa này thường ra sao?"}
})

# L-25: TURN=3 location chain — Phường Cầu Giấy stays through 3 turns
SAMPLES.append({
    "_kind": "L_loc_inherit_turn3",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")},
        {"user": "nơi đó hôm qua ra sao?",
         "assistant": asst("historical_weather", "ward", 0.80,
                           "Hôm qua Phường Cầu Giấy thời tiết thế nào?")}
    ],
    "input": "tuần trước thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tuần trước Phường Cầu Giấy thời tiết thế nào?"}
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
kinds = {}
for s in SAMPLES:
    k = s.get('_kind', 'unknown')
    kinds[k] = kinds.get(k, 0) + 1
print('By kind:')
for k in sorted(kinds):
    print(f'  {k}: {kinds[k]}')

total_errs = 0
for i, s in enumerate(SAMPLES):
    errs = validate(s)
    if errs:
        print(f'  [SAMPLE {i}] {errs}')
        total_errs += 1
print(f'Validation errors: {total_errs}')
if total_errs > 0:
    sys.exit(1)

out_path = Path(__file__).parent / 'batch_08_multiturn.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')

# Turn distribution
turns = []
for s in SAMPLES:
    h_len = len(s['history'])
    turns.append(h_len + 1)  # current turn = history length + 1
from collections import Counter
print(f'Turn distribution: {dict(Counter(turns))}')
