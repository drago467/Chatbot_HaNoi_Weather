"""V7 Batch 9 (Phase 4 multi-turn cont) — 50 samples.

Composition:
- 25 EXPLICIT-SWITCH: user explicit nói tên/prefix mới ⇒ scope hoặc entity SWITCH.
  Patterns: ward↔district collision, ward→city, city→ward, ward→ward (different),
  district→district (different), pure-xã→huyện, pure-phường→collision-quận, ward→thị xã.
- 15 CONTINUATION với NEW wards (mở rộng coverage 15 wards mới: Đại Mỗ, Tây Mỗ,
  Phú Lương, Kiến Hưng, Dương Nội, Tây Tựu, Hoàng Liệt, Tương Mai, Giảng Võ,
  Cửa Nam, Kim Liên, Ô Chợ Dừa, Bát Tràng, Hương Sơn, Đa Phúc).
- 5 TURN=3 chains (mixed time + location + explicit-switch).
- 5 INTENT-SHIFT continuation (location/time stay, intent changes).

Confidence:
- Continuation/intent-shift: T3=0.80
- Explicit-switch: T2=0.85 (user re-anchored, less ambiguity)
- Turn=3: T3=0.80
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# A) EXPLICIT-SWITCH (25)
# ═══════════════════════════════════════════════════════════════════════════

# S-01: Phường Cầu Giấy → Quận Cầu Giấy (collision ward → district)
SAMPLES.append({
    "_kind": "S_switch_collision_w2d",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Quận Cầu Giấy thì sao?",
    "output": {"intent": "current_weather", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Thời tiết Quận Cầu Giấy hôm nay thế nào?"}
})

# S-02: Phường Long Biên → Quận Long Biên
SAMPLES.append({
    "_kind": "S_switch_collision_w2d",
    "history": [
        {"user": "Phường Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")}
    ],
    "input": "Quận Long Biên có mưa không?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Quận Long Biên hôm nay có mưa không?"}
})

# S-03: Phường Hoàn Kiếm → Quận Hoàn Kiếm
SAMPLES.append({
    "_kind": "S_switch_collision_w2d",
    "history": [
        {"user": "Phường Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Quận Hoàn Kiếm có cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Quận Hoàn Kiếm có cảnh báo thời tiết gì không?"}
})

# S-04: Quận Hà Đông → Phường Hà Đông (district → ward, collision)
SAMPLES.append({
    "_kind": "S_switch_collision_d2w",
    "history": [
        {"user": "Quận Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Quận Hà Đông hôm nay thế nào?")}
    ],
    "input": "Phường Hà Đông cụ thể nhiệt độ bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Hà Đông cụ thể nhiệt độ hiện tại bao nhiêu?"}
})

# S-05: Quận Đống Đa → Phường Đống Đa
SAMPLES.append({
    "_kind": "S_switch_collision_d2w",
    "history": [
        {"user": "Quận Đống Đa hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Quận Đống Đa hôm nay thế nào?")}
    ],
    "input": "Phường Đống Đa thì gió ra sao?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Đống Đa hiện tại gió ra sao?"}
})

# S-06: Phường Cầu Giấy → Hà Nội (ward → city broaden)
SAMPLES.append({
    "_kind": "S_switch_w2city",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Hà Nội nói chung thì sao?",
    "output": {"intent": "weather_overview", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Hà Nội hôm nay thế nào?"}
})

# S-07: Hà Nội → Phường Hoàn Kiếm (city → ward narrow)
SAMPLES.append({
    "_kind": "S_switch_city2w",
    "history": [
        {"user": "Hà Nội ngày mai nóng không?",
         "assistant": asst("daily_forecast", "city", 0.85,
                           "Hà Nội ngày mai nhiệt độ thế nào?")}
    ],
    "input": "Cụ thể Phường Hoàn Kiếm thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Cụ thể Phường Hoàn Kiếm ngày mai nhiệt độ thế nào?"}
})

# S-08: Phường Cầu Giấy → Phường Hoàn Kiếm (ward A → ward B different)
SAMPLES.append({
    "_kind": "S_switch_w2w_different",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Phường Hoàn Kiếm thì sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?"}
})

# S-09: Huyện Sóc Sơn → Huyện Đông Anh (district A → B)
SAMPLES.append({
    "_kind": "S_switch_d2d_different",
    "history": [
        {"user": "Huyện Sóc Sơn hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "Huyện Đông Anh thì sao?",
    "output": {"intent": "current_weather", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Thời tiết Huyện Đông Anh hôm nay thế nào?"}
})

# S-10: Xã Mỹ Đức → Huyện Mỹ Đức (collision xã → huyện)
SAMPLES.append({
    "_kind": "S_switch_collision_xa2huyen",
    "history": [
        {"user": "Xã Mỹ Đức hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Mỹ Đức hôm nay thế nào?")}
    ],
    "input": "Huyện Mỹ Đức nói chung thì sao?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Huyện Mỹ Đức hôm nay thế nào?"}
})

# S-11: Huyện Mỹ Đức → Xã Mỹ Đức
SAMPLES.append({
    "_kind": "S_switch_collision_huyen2xa",
    "history": [
        {"user": "Huyện Mỹ Đức hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Mỹ Đức hôm nay thế nào?")}
    ],
    "input": "Xã Mỹ Đức cụ thể có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Xã Mỹ Đức cụ thể có mưa không?"}
})

# S-12: Phường Tây Hồ → Quận Tây Hồ
SAMPLES.append({
    "_kind": "S_switch_collision_w2d",
    "history": [
        {"user": "Phường Tây Hồ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Quận Tây Hồ tổng quan thế nào?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Quận Tây Hồ hôm nay"}
})

# S-13: Quận Hai Bà Trưng → Phường Bạch Mai (district → ward different ward)
SAMPLES.append({
    "_kind": "S_switch_d2w_different_ward",
    "history": [
        {"user": "Quận Hai Bà Trưng hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Quận Hai Bà Trưng hôm nay thế nào?")}
    ],
    "input": "Phường Bạch Mai cụ thể thì sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Bạch Mai hiện tại thế nào?"}
})

# S-14: Phường Yên Hòa → Phường Cầu Giấy (pure-phường → collision-phường, same district)
SAMPLES.append({
    "_kind": "S_switch_w2w_different",
    "history": [
        {"user": "Phường Yên Hòa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Yên Hòa hôm nay thế nào?")}
    ],
    "input": "Phường Cầu Giấy thì sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Cầu Giấy hôm nay thế nào?"}
})

# S-15: Hà Nội → Huyện Sóc Sơn (city → district)
SAMPLES.append({
    "_kind": "S_switch_city2d",
    "history": [
        {"user": "Hà Nội tuần này thế nào?",
         "assistant": asst("daily_forecast", "city", 0.85,
                           "Hà Nội tuần này thời tiết thế nào?")}
    ],
    "input": "Huyện Sóc Sơn cụ thể thì sao?",
    "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Huyện Sóc Sơn tuần này thời tiết thế nào?"}
})

# S-16: Phường Hoàng Mai → Quận Hoàng Mai
SAMPLES.append({
    "_kind": "S_switch_collision_w2d",
    "history": [
        {"user": "Phường Hoàng Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Quận Hoàng Mai có ngập không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Quận Hoàng Mai có nguy cơ ngập lụt không?"}
})

# S-17: Xã Yên Lãng → Huyện Mê Linh (xã → encompassing huyện)
SAMPLES.append({
    "_kind": "S_switch_xa2huyen_parent",
    "history": [
        {"user": "Xã Yên Lãng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Yên Lãng hôm nay thế nào?")}
    ],
    "input": "Huyện Mê Linh nói chung thế nào?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Huyện Mê Linh hôm nay"}
})

# S-18: Phường Đại Mỗ → Quận Nam Từ Liêm (pure-phường → encompassing pure-district)
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Đại Mỗ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Đại Mỗ hôm nay thế nào?")}
    ],
    "input": "Quận Nam Từ Liêm tổng quan thế nào?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Quận Nam Từ Liêm hôm nay"}
})

# S-19: Phường Bồ Đề → Quận Long Biên
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Bồ Đề hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Bồ Đề hôm nay thế nào?")}
    ],
    "input": "Quận Long Biên dự báo thế nào?",
    "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Dự báo Quận Long Biên hôm nay thế nào?"}
})

# S-20: Phường Yên Nghĩa → Quận Hà Đông
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Yên Nghĩa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Yên Nghĩa hôm nay thế nào?")}
    ],
    "input": "Quận Hà Đông cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Quận Hà Đông có cảnh báo thời tiết gì không?"}
})

# S-21: Phường Định Công → Phường Hoàng Liệt (ward A → ward B same district)
SAMPLES.append({
    "_kind": "S_switch_w2w_different",
    "history": [
        {"user": "Phường Định Công hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Định Công hôm nay thế nào?")}
    ],
    "input": "Phường Hoàng Liệt thì sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Hoàng Liệt hôm nay thế nào?"}
})

# S-22: Phường Văn Miếu - QTG → Quận Đống Đa
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Văn Miếu - Quốc Tử Giám hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Văn Miếu - Quốc Tử Giám hôm nay thế nào?")}
    ],
    "input": "Quận Đống Đa nói chung thế nào?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Quận Đống Đa hôm nay"}
})

# S-23: Phường Cửa Nam → Quận Hoàn Kiếm
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Cửa Nam hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cửa Nam hôm nay thế nào?")}
    ],
    "input": "Quận Hoàn Kiếm cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Quận Hoàn Kiếm có cảnh báo thời tiết gì không?"}
})

# S-24: Phường Giảng Võ → Quận Ba Đình
SAMPLES.append({
    "_kind": "S_switch_w2d_parent",
    "history": [
        {"user": "Phường Giảng Võ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Giảng Võ hôm nay thế nào?")}
    ],
    "input": "Quận Ba Đình tổng quan?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Quận Ba Đình hôm nay"}
})

# S-25: Phường Sơn Tây → Thị xã Sơn Tây
SAMPLES.append({
    "_kind": "S_switch_w2thixa",
    "history": [
        {"user": "Phường Sơn Tây hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Sơn Tây hôm nay thế nào?")}
    ],
    "input": "Thị xã Sơn Tây nói chung?",
    "output": {"intent": "weather_overview", "scope": "district", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Thị xã Sơn Tây hôm nay"}
})

# ═══════════════════════════════════════════════════════════════════════════
# B) CONTINUATION với NEW WARDS (15)
# ═══════════════════════════════════════════════════════════════════════════

# C-01: Phường Đại Mỗ — anaphoric "ở đó hôm qua"
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Đại Mỗ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Đại Mỗ hôm nay thế nào?")}
    ],
    "input": "ở đó hôm qua thế nào?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm qua Phường Đại Mỗ thời tiết thế nào?"}
})

# C-02: Phường Tây Mỗ
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Tây Mỗ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Tây Mỗ hôm nay thế nào?")}
    ],
    "input": "khu đó độ ẩm cao không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Mỗ độ ẩm hiện tại có cao không?"}
})

# C-03: Phường Phú Lương
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Phú Lương hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Phú Lương hôm nay thế nào?")}
    ],
    "input": "ngày mai có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai Phường Phú Lương có mưa không?"}
})

# C-04: Phường Kiến Hưng
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Kiến Hưng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Kiến Hưng hôm nay thế nào?")}
    ],
    "input": "tối nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Kiến Hưng thời tiết thế nào?"}
})

# C-05: Phường Dương Nội
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Dương Nội hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Dương Nội hôm nay thế nào?")}
    ],
    "input": "có gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Dương Nội hiện tại có gió không?"}
})

# C-06: Phường Tây Tựu — tuần sau anchor
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Tây Tựu thứ 2 tuần sau thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Tây Tựu thứ 2 tuần sau thế nào?")}
    ],
    "input": "thứ 4 thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Tây Tựu thứ 4 tuần sau thế nào?"}
})

# C-07: Phường Hoàng Liệt — ngày kia
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Hoàng Liệt hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàng Liệt hôm nay thế nào?")}
    ],
    "input": "ngày kia thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Hoàng Liệt ngày kia thế nào?"}
})

# C-08: Phường Tương Mai
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Tương Mai hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Tương Mai hôm nay thế nào?")}
    ],
    "input": "ở đó có ấm không?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tương Mai hôm nay có ấm không?"}
})

# C-09: Phường Giảng Võ — tầm nhìn
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Giảng Võ hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Giảng Võ hôm nay thế nào?")}
    ],
    "input": "khu đó tầm nhìn xa thế nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Giảng Võ tầm nhìn xa hiện tại thế nào?"}
})

# C-10: Phường Cửa Nam — UV
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Cửa Nam hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cửa Nam hôm nay thế nào?")}
    ],
    "input": "UV ở đó thế nào?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV Phường Cửa Nam hiện tại thế nào?"}
})

# C-11: Phường Kim Liên
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Kim Liên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Kim Liên hôm nay thế nào?")}
    ],
    "input": "buổi sáng có sương không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Kim Liên buổi sáng có sương mù không?"}
})

# C-12: Phường Ô Chợ Dừa
SAMPLES.append({
    "_kind": "C_continue_new_ward",
    "history": [
        {"user": "Phường Ô Chợ Dừa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Ô Chợ Dừa hôm nay thế nào?")}
    ],
    "input": "đêm nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Đêm nay Phường Ô Chợ Dừa thời tiết thế nào?"}
})

# C-13: Xã Bát Tràng (Gia Lâm) — cuối tuần
SAMPLES.append({
    "_kind": "C_continue_new_xa",
    "history": [
        {"user": "Xã Bát Tràng hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Bát Tràng hôm nay thế nào?")}
    ],
    "input": "cuối tuần ở đó thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Xã Bát Tràng cuối tuần này thế nào?"}
})

# C-14: Xã Hương Sơn (Mỹ Đức) — tuần này
SAMPLES.append({
    "_kind": "C_continue_new_xa",
    "history": [
        {"user": "Xã Hương Sơn hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Hương Sơn hôm nay thế nào?")}
    ],
    "input": "tuần này có gì đáng chú ý?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Hương Sơn tuần này có cảnh báo thời tiết đáng chú ý không?"}
})

# C-15: Xã Đa Phúc (Sóc Sơn)
SAMPLES.append({
    "_kind": "C_continue_new_xa",
    "history": [
        {"user": "Xã Đa Phúc hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Đa Phúc hôm nay thế nào?")}
    ],
    "input": "có cảnh báo gì không?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Xã Đa Phúc có cảnh báo thời tiết gì không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# C) TURN=3 chains (5)
# ═══════════════════════════════════════════════════════════════════════════

# 3T-01: Time chain Phường Đại Mỗ
SAMPLES.append({
    "_kind": "Turn3_time_chain",
    "history": [
        {"user": "Phường Đại Mỗ ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Phường Đại Mỗ ngày mai thế nào?")},
        {"user": "buổi sáng thì sao?",
         "assistant": asst("hourly_forecast", "ward", 0.80,
                           "Phường Đại Mỗ ngày mai buổi sáng thế nào?")}
    ],
    "input": "buổi tối thì sao?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đại Mỗ ngày mai buổi tối thế nào?"}
})

# 3T-02: Location chain Phường Bồ Đề
SAMPLES.append({
    "_kind": "Turn3_loc_chain",
    "history": [
        {"user": "Phường Bồ Đề hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Bồ Đề hôm nay thế nào?")},
        {"user": "ở đó hôm qua ra sao?",
         "assistant": asst("historical_weather", "ward", 0.80,
                           "Hôm qua Phường Bồ Đề thời tiết thế nào?")}
    ],
    "input": "tuần trước thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tuần trước Phường Bồ Đề thời tiết thế nào?"}
})

# 3T-03: Mixed location keep + time advance — Phường Yên Hòa
SAMPLES.append({
    "_kind": "Turn3_mixed",
    "history": [
        {"user": "Phường Yên Hòa hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Yên Hòa hôm nay thế nào?")},
        {"user": "ngày mai có mưa không?",
         "assistant": asst("rain_query", "ward", 0.80,
                           "Phường Yên Hòa ngày mai có mưa không?")}
    ],
    "input": "ngày kia có gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Hòa ngày kia có gió không?"}
})

# 3T-04: Explicit-switch chain — turn 1 ward → turn 2 same district → turn 3 different ward (multi-step)
SAMPLES.append({
    "_kind": "Turn3_switch_chain",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")},
        {"user": "Quận Cầu Giấy thì sao?",
         "assistant": asst("current_weather", "district", 0.85,
                           "Thời tiết Quận Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Phường Nghĩa Đô cụ thể thì sao?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Nghĩa Đô hôm nay thế nào?"}
})

# 3T-05: City → ward → time advance
SAMPLES.append({
    "_kind": "Turn3_scope_narrow_then_time",
    "history": [
        {"user": "Hà Nội hôm nay thế nào?",
         "assistant": asst("current_weather", "city", 0.85,
                           "Thời tiết Hà Nội hôm nay thế nào?")},
        {"user": "Phường Tây Hồ cụ thể?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "ngày mai thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ ngày mai thời tiết thế nào?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# D) INTENT-SHIFT continuation (5)
# ═══════════════════════════════════════════════════════════════════════════

# I-01: Phường Yên Hòa, rain → wind
SAMPLES.append({
    "_kind": "I_intent_shift",
    "history": [
        {"user": "Phường Yên Hòa hôm nay có mưa không?",
         "assistant": asst("rain_query", "ward", 0.92,
                           "Phường Yên Hòa hôm nay có mưa không?")}
    ],
    "input": "thế còn gió thì sao?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Yên Hòa hôm nay gió thế nào?"}
})

# I-02: Phường Hoàng Liệt, current → daily_forecast
SAMPLES.append({
    "_kind": "I_intent_shift",
    "history": [
        {"user": "Phường Hoàng Liệt hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hoàng Liệt hôm nay thế nào?")}
    ],
    "input": "tuần này dự báo ra sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Phường Hoàng Liệt tuần này thế nào?"}
})

# I-03: Phường Phú Diễn, temp → humidity
SAMPLES.append({
    "_kind": "I_intent_shift",
    "history": [
        {"user": "Phường Phú Diễn hôm nay nóng không?",
         "assistant": asst("temperature_query", "ward", 0.92,
                           "Phường Phú Diễn hôm nay nóng không?")}
    ],
    "input": "độ ẩm thì sao?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Phú Diễn hôm nay độ ẩm bao nhiêu?"}
})

# I-04: Huyện Sóc Sơn, current → seasonal
SAMPLES.append({
    "_kind": "I_intent_shift_district",
    "history": [
        {"user": "Huyện Sóc Sơn hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "so với mùa này năm trước thì sao?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Thời tiết Huyện Sóc Sơn hôm nay so với mùa này năm trước thế nào?"}
})

# I-05: Phường Đại Mỗ, weather_overview → activity
SAMPLES.append({
    "_kind": "I_intent_shift",
    "history": [
        {"user": "Phường Đại Mỗ tổng quan hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.92,
                           "Tổng quan thời tiết Phường Đại Mỗ hôm nay")}
    ],
    "input": "có thích hợp đi dạo không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đại Mỗ hôm nay có thích hợp đi dạo không?"}
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

out_path = Path(__file__).parent / 'batch_09_multiturn.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')

from collections import Counter
turns = Counter(len(s['history']) + 1 for s in SAMPLES)
print(f'Turn distribution: {dict(turns)}')
scopes = Counter(s['output']['scope'] for s in SAMPLES)
print(f'Scope distribution: {dict(scopes)}')
