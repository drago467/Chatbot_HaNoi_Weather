"""V7 Batch 10 (Phase 4 multi-turn cont) — 50 samples.

Composition:
- 25 RURAL/SUBURBAN ward variety: chưa cover trong batch 8-9.
  New wards: Phường Phúc Lợi (Long Biên), Phường Đông Ngạc, Phường Thượng Cát,
  Phường Xuân Đỉnh (Bắc Từ Liêm), Phường Tùng Thiện (Sơn Tây), Phường Phương Liệt
  (Thanh Xuân), Phường Lĩnh Nam (Hoàng Mai - revisit), Xã Phù Đổng, Xã Thuận An
  (Gia Lâm), Xã An Khánh (Hoài Đức), Xã Phù Đổng (Gia Lâm). NEW xã: Hồng Sơn,
  Phúc Sơn (Mỹ Đức), Hát Môn (Phúc Thọ), Tam Hưng (Thanh Oai), Hồng Vân
  (Thường Tín), Hòa Lạc (Thạch Thất), Vân Đình (Ứng Hòa), Đại Xuyên (Phú Xuyên),
  Cổ Đô (Ba Vì), Bình Minh (Thanh Oai), Hưng Đạo (Quốc Oai), Thanh Liệt (Thanh
  Trì), Phường Hồng Hà (special - thị xã empty district).
- 10 LOCATION_COMPARISON multi-turn (so sánh, thêm địa điểm thứ 3).
- 5 SMALLTALK continuation (recommendation-style, mặc gì/mang gì).
- 5 TIME edge cases (bare weekday, specific date, rạng sáng, đầu tháng).
- 5 turn=3 chains (mix patterns).
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

def add(kind, hist, inp, intent, scope, conf, rew):
    SAMPLES.append({
        "_kind": kind,
        "history": hist,
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) RURAL/SUBURBAN ward variety (25)
# ═══════════════════════════════════════════════════════════════════════════

# 1. Phường Phúc Lợi (Long Biên)
add("R_new_ward",
    [{"user": "Phường Phúc Lợi hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Phúc Lợi hôm nay thế nào?")}],
    "ngày mai có mưa không?",
    "rain_query", "ward", 0.80,
    "Ngày mai Phường Phúc Lợi có mưa không?")

# 2. Phường Đông Ngạc (Bắc Từ Liêm)
add("R_new_ward",
    [{"user": "Phường Đông Ngạc hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Đông Ngạc hôm nay thế nào?")}],
    "khu đó độ ẩm cao không?",
    "humidity_fog_query", "ward", 0.80,
    "Phường Đông Ngạc độ ẩm hiện tại có cao không?")

# 3. Phường Thượng Cát
add("R_new_ward",
    [{"user": "Phường Thượng Cát hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Thượng Cát hôm nay thế nào?")}],
    "tối nay nhiệt độ bao nhiêu?",
    "temperature_query", "ward", 0.80,
    "Tối nay Phường Thượng Cát nhiệt độ bao nhiêu?")

# 4. Phường Xuân Đỉnh
add("R_new_ward",
    [{"user": "Phường Xuân Đỉnh hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Xuân Đỉnh hôm nay thế nào?")}],
    "ở đó có cảnh báo gì không?",
    "weather_alert", "ward", 0.80,
    "Phường Xuân Đỉnh có cảnh báo thời tiết gì không?")

# 5. Phường Tùng Thiện (Sơn Tây)
add("R_new_ward",
    [{"user": "Phường Tùng Thiện hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Tùng Thiện hôm nay thế nào?")}],
    "tuần này dự báo ra sao?",
    "daily_forecast", "ward", 0.80,
    "Dự báo Phường Tùng Thiện tuần này thế nào?")

# 6. Phường Phương Liệt (Thanh Xuân)
add("R_new_ward",
    [{"user": "Phường Phương Liệt hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Phương Liệt hôm nay thế nào?")}],
    "khu đó UV cao không?",
    "expert_weather_param", "ward", 0.80,
    "UV Phường Phương Liệt hiện tại có cao không?")

# 7. Xã Phù Đổng (Gia Lâm)
add("R_new_xa",
    [{"user": "Xã Phù Đổng hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Phù Đổng hôm nay thế nào?")}],
    "ngày kia thế nào?",
    "daily_forecast", "ward", 0.80,
    "Xã Phù Đổng ngày kia thời tiết thế nào?")

# 8. Xã Thuận An (Gia Lâm)
add("R_new_xa",
    [{"user": "Xã Thuận An hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Thuận An hôm nay thế nào?")}],
    "ở đó có gió mạnh không?",
    "wind_query", "ward", 0.80,
    "Xã Thuận An có gió mạnh không?")

# 9. Xã An Khánh (Hoài Đức)
add("R_new_xa",
    [{"user": "Xã An Khánh hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã An Khánh hôm nay thế nào?")}],
    "khu đó có mưa kéo dài không?",
    "rain_query", "ward", 0.80,
    "Xã An Khánh có mưa kéo dài không?")

# 10. Xã Hồng Sơn (Mỹ Đức)
add("R_new_xa",
    [{"user": "Xã Hồng Sơn hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Hồng Sơn hôm nay thế nào?")}],
    "tuần trước thì sao?",
    "historical_weather", "ward", 0.80,
    "Xã Hồng Sơn tuần trước thời tiết thế nào?")

# 11. Xã Phúc Sơn (Mỹ Đức)
add("R_new_xa",
    [{"user": "Xã Phúc Sơn hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Phúc Sơn hôm nay thế nào?")}],
    "có thích hợp đi dạo không?",
    "activity_weather", "ward", 0.80,
    "Xã Phúc Sơn hôm nay có thích hợp đi dạo không?")

# 12. Xã Hát Môn (Phúc Thọ)
add("R_new_xa",
    [{"user": "Xã Hát Môn hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Hát Môn hôm nay thế nào?")}],
    "buổi tối thế nào?",
    "hourly_forecast", "ward", 0.80,
    "Buổi tối Xã Hát Môn thời tiết thế nào?")

# 13. Xã Tam Hưng (Thanh Oai)
add("R_new_xa",
    [{"user": "Xã Tam Hưng hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Tam Hưng hôm nay thế nào?")}],
    "khu đó hôm qua có mưa không?",
    "historical_weather", "ward", 0.80,
    "Hôm qua Xã Tam Hưng có mưa không?")

# 14. Xã Hồng Vân (Thường Tín)
add("R_new_xa",
    [{"user": "Xã Hồng Vân hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Hồng Vân hôm nay thế nào?")}],
    "ở đó áp suất bao nhiêu?",
    "expert_weather_param", "ward", 0.80,
    "Xã Hồng Vân áp suất hiện tại bao nhiêu?")

# 15. Xã Hòa Lạc (Thạch Thất)
add("R_new_xa",
    [{"user": "Xã Hòa Lạc hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Hòa Lạc hôm nay thế nào?")}],
    "tuần này có nắng không?",
    "daily_forecast", "ward", 0.80,
    "Xã Hòa Lạc tuần này có nắng không?")

# 16. Xã Vân Đình (Ứng Hòa)
add("R_new_xa",
    [{"user": "Xã Vân Đình hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Vân Đình hôm nay thế nào?")}],
    "ngày mai mưa to không?",
    "rain_query", "ward", 0.80,
    "Ngày mai Xã Vân Đình có mưa to không?")

# 17. Xã Đại Xuyên (Phú Xuyên)
add("R_new_xa",
    [{"user": "Xã Đại Xuyên hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Đại Xuyên hôm nay thế nào?")}],
    "khu đó tổng quan ngày mai?",
    "weather_overview", "ward", 0.80,
    "Tổng quan Xã Đại Xuyên ngày mai thế nào?")

# 18. Xã Cổ Đô (Ba Vì)
add("R_new_xa",
    [{"user": "Xã Cổ Đô hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Cổ Đô hôm nay thế nào?")}],
    "ở đó có sương sáng không?",
    "humidity_fog_query", "ward", 0.80,
    "Xã Cổ Đô buổi sáng có sương mù không?")

# 19. Xã Bình Minh (Thanh Oai)
add("R_new_xa",
    [{"user": "Xã Bình Minh hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Bình Minh hôm nay thế nào?")}],
    "có thích hợp ra đồng không?",
    "activity_weather", "ward", 0.80,
    "Xã Bình Minh hôm nay có thích hợp ra đồng làm việc không?")

# 20. Xã Hưng Đạo (Quốc Oai)
add("R_new_xa",
    [{"user": "Xã Hưng Đạo hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Hưng Đạo hôm nay thế nào?")}],
    "khu đó có ngập không?",
    "weather_alert", "ward", 0.80,
    "Xã Hưng Đạo có nguy cơ ngập lụt không?")

# 21. Phường Thanh Liệt (Thanh Trì — special: this is Phường, not Xã!)
add("R_new_ward_special",
    [{"user": "Phường Thanh Liệt hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Thanh Liệt hôm nay thế nào?")}],
    "ngày mai có mưa không?",
    "rain_query", "ward", 0.80,
    "Ngày mai Phường Thanh Liệt có mưa không?")

# 22. Phường Hồng Hà (special — empty district in canonical)
add("R_new_ward_special",
    [{"user": "Phường Hồng Hà hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Hồng Hà hôm nay thế nào?")}],
    "ở đó có mát mẻ không?",
    "smalltalk_weather", "ward", 0.80,
    "Phường Hồng Hà hôm nay có mát mẻ không?")

# 23. Phường Lĩnh Nam (Hoàng Mai) — multi-turn refine
add("R_new_ward",
    [{"user": "Phường Lĩnh Nam hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Lĩnh Nam hôm nay thế nào?")}],
    "tối nay khoảng 22h thế nào?",
    "hourly_forecast", "ward", 0.80,
    "Tối nay khoảng 22h Phường Lĩnh Nam thời tiết thế nào?")

# 24. Xã Đoài Phương (Sơn Tây — only xã in Thị xã Sơn Tây)
add("R_new_xa",
    [{"user": "Xã Đoài Phương hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Đoài Phương hôm nay thế nào?")}],
    "khu đó dự báo cuối tuần?",
    "daily_forecast", "ward", 0.80,
    "Xã Đoài Phương dự báo cuối tuần thế nào?")

# 25. Xã Sóc Sơn — pure-collision-xa, but here we treat as ward (alternate xã interpretation)
add("R_new_xa_collision_ward_version",
    [{"user": "Xã Sóc Sơn hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Xã Sóc Sơn hôm nay thế nào?")}],
    "ở đó có cảnh báo gì không?",
    "weather_alert", "ward", 0.80,
    "Xã Sóc Sơn có cảnh báo thời tiết gì không?")

# ═══════════════════════════════════════════════════════════════════════════
# B) LOCATION_COMPARISON multi-turn (10)
# ═══════════════════════════════════════════════════════════════════════════

# Cmp-01: 2-way → add 3rd
add("Cmp_add_third",
    [{"user": "So sánh Phường Cầu Giấy với Phường Hoàn Kiếm hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Phường Cầu Giấy với Phường Hoàn Kiếm hôm nay")}],
    "thêm Phường Đống Đa nữa?",
    "location_comparison", "ward", 0.80,
    "So sánh thời tiết Phường Cầu Giấy, Phường Hoàn Kiếm và Phường Đống Đa hôm nay")

# Cmp-02: comparison → time advance
add("Cmp_time_advance",
    [{"user": "So sánh Phường Long Biên và Phường Bồ Đề hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Phường Long Biên và Phường Bồ Đề hôm nay")}],
    "ngày mai thì sao?",
    "location_comparison", "ward", 0.80,
    "So sánh thời tiết Phường Long Biên và Phường Bồ Đề ngày mai")

# Cmp-03: comparison → focus on one
add("Cmp_focus_one",
    [{"user": "So sánh Huyện Sóc Sơn và Huyện Đông Anh hôm nay",
      "assistant": asst("location_comparison", "district", 0.92,
                        "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh hôm nay")}],
    "Huyện Sóc Sơn cụ thể có nóng không?",
    "temperature_query", "district", 0.85,
    "Huyện Sóc Sơn hôm nay có nóng không?")

# Cmp-04: 2-way ward comparison → ngày mai
add("Cmp_time_advance",
    [{"user": "Phường Tây Hồ và Phường Hoàng Mai hôm nay đâu mát hơn?",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh độ mát Phường Tây Hồ và Phường Hoàng Mai hôm nay")}],
    "ngày mai thì sao?",
    "location_comparison", "ward", 0.80,
    "So sánh độ mát Phường Tây Hồ và Phường Hoàng Mai ngày mai")

# Cmp-05: ward vs district comparison
add("Cmp_cross_scope",
    [{"user": "Phường Cầu Giấy với Quận Cầu Giấy hôm nay khác nhau ra sao?",
      "assistant": asst("location_comparison", "district", 0.85,
                        "So sánh thời tiết Phường Cầu Giấy và Quận Cầu Giấy hôm nay")}],
    "thế còn nhiệt độ?",
    "temperature_query", "district", 0.80,
    "So sánh nhiệt độ Phường Cầu Giấy và Quận Cầu Giấy hôm nay")

# Cmp-06: 3-way district
add("Cmp_3way",
    [{"user": "So sánh Huyện Mê Linh, Huyện Sóc Sơn và Huyện Đông Anh",
      "assistant": asst("location_comparison", "district", 0.92,
                        "So sánh thời tiết Huyện Mê Linh, Huyện Sóc Sơn và Huyện Đông Anh hôm nay")}],
    "đâu khô nhất?",
    "humidity_fog_query", "district", 0.80,
    "Trong Huyện Mê Linh, Huyện Sóc Sơn và Huyện Đông Anh, đâu có độ ẩm thấp nhất?")

# Cmp-07: comparison → drop one
add("Cmp_drop",
    [{"user": "So sánh Phường Yên Nghĩa và Phường Phú Lương hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Phường Yên Nghĩa và Phường Phú Lương hôm nay")}],
    "Phường Yên Nghĩa cụ thể thế nào?",
    "current_weather", "ward", 0.85,
    "Thời tiết Phường Yên Nghĩa hiện tại thế nào?")

# Cmp-08: comparison + alert intent
add("Cmp_intent_shift",
    [{"user": "So sánh Phường Tây Hồ và Phường Tây Mỗ hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Phường Tây Hồ và Phường Tây Mỗ hôm nay")}],
    "đâu có nguy cơ ngập?",
    "weather_alert", "ward", 0.80,
    "Phường Tây Hồ và Phường Tây Mỗ, đâu có nguy cơ ngập lụt hơn?")

# Cmp-09: rural xã comparison
add("Cmp_xa",
    [{"user": "So sánh Xã Minh Châu và Xã Quốc Oai hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Xã Minh Châu và Xã Quốc Oai hôm nay")}],
    "tuần sau ra sao?",
    "location_comparison", "ward", 0.80,
    "So sánh thời tiết Xã Minh Châu và Xã Quốc Oai tuần sau")

# Cmp-10: xã + phường comparison (mixed entity types but same ward scope)
add("Cmp_mixed_ward",
    [{"user": "So sánh Xã Yên Lãng và Phường Cầu Giấy hôm nay",
      "assistant": asst("location_comparison", "ward", 0.92,
                        "So sánh thời tiết Xã Yên Lãng và Phường Cầu Giấy hôm nay")}],
    "đâu mát hơn?",
    "temperature_query", "ward", 0.80,
    "Xã Yên Lãng và Phường Cầu Giấy hôm nay đâu mát hơn?")

# ═══════════════════════════════════════════════════════════════════════════
# C) SMALLTALK continuation (5) — recommendation-style
# ═══════════════════════════════════════════════════════════════════════════

# Sk-01: weather → mặc gì recommendation
add("Sk_recommend",
    [{"user": "Phường Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "có cần mặc ấm không?",
    "smalltalk_weather", "ward", 0.80,
    "Hôm nay Phường Cầu Giấy có cần mặc ấm không?")

# Sk-02: rain → mang ô không
add("Sk_recommend",
    [{"user": "Phường Hoàng Mai có mưa không?",
      "assistant": asst("rain_query", "ward", 0.92,
                        "Phường Hoàng Mai hôm nay có mưa không?")}],
    "có cần mang ô không?",
    "smalltalk_weather", "ward", 0.80,
    "Phường Hoàng Mai hôm nay có cần mang ô không?")

# Sk-03: hot day → smalltalk
add("Sk_recommend",
    [{"user": "Phường Tây Hồ hôm nay nhiệt độ bao nhiêu?",
      "assistant": asst("temperature_query", "ward", 0.92,
                        "Nhiệt độ Phường Tây Hồ hôm nay bao nhiêu?")}],
    "nóng vậy đi bơi được không nhỉ?",
    "smalltalk_weather", "ward", 0.80,
    "Hôm nay Phường Tây Hồ có thích hợp đi bơi không?")

# Sk-04: cold morning → smalltalk
add("Sk_recommend",
    [{"user": "Phường Đống Đa sáng nay nhiệt độ bao nhiêu?",
      "assistant": asst("temperature_query", "ward", 0.92,
                        "Nhiệt độ Phường Đống Đa sáng nay bao nhiêu?")}],
    "có cần áo khoác đi làm không?",
    "smalltalk_weather", "ward", 0.80,
    "Sáng nay Phường Đống Đa có cần áo khoác khi đi làm không?")

# Sk-05: smalltalk → smalltalk continuation (chat-style)
add("Sk_chat",
    [{"user": "Phường Long Biên hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Long Biên hôm nay thế nào?")}],
    "tối thế này dắt chó đi dạo được không?",
    "smalltalk_weather", "ward", 0.80,
    "Tối nay Phường Long Biên có thích hợp dắt chó đi dạo không?")

# ═══════════════════════════════════════════════════════════════════════════
# D) TIME edge cases (5)
# ═══════════════════════════════════════════════════════════════════════════

# Te-01: bare weekday "thứ 4" without tuần qualifier (default upcoming)
add("Te_bare_weekday",
    [{"user": "Phường Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "thứ 4 thì sao?",
    "daily_forecast", "ward", 0.80,
    "Dự báo Phường Cầu Giấy thứ 4 thế nào?")

# Te-02: rạng sáng (early dawn 2-5h)
add("Te_part_of_day",
    [{"user": "Phường Tây Hồ ngày mai thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.92,
                        "Dự báo Phường Tây Hồ ngày mai thế nào?")}],
    "rạng sáng có sương không?",
    "humidity_fog_query", "ward", 0.80,
    "Phường Tây Hồ ngày mai rạng sáng có sương mù không?")

# Te-03: đầu tháng tới (semi-vague time)
add("Te_month_segment",
    [{"user": "Hà Nội tháng tới thế nào?",
      "assistant": asst("seasonal_context", "city", 0.85,
                        "Hà Nội tháng tới thời tiết thế nào?")}],
    "đầu tháng có mưa nhiều không?",
    "rain_query", "city", 0.80,
    "Hà Nội đầu tháng tới có mưa nhiều không?")

# Te-04: specific date "ngày 25"
add("Te_specific_date",
    [{"user": "Phường Hoàng Mai tuần sau thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.85,
                        "Dự báo Phường Hoàng Mai tuần sau thế nào?")}],
    "ngày 25 cụ thể?",
    "daily_forecast", "ward", 0.80,
    "Dự báo Phường Hoàng Mai ngày 25 thế nào?")

# Te-05: out-of-horizon time → smalltalk refusal-style (>8 days = refuse)
add("Te_out_of_horizon",
    [{"user": "Phường Cầu Giấy ngày mai thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.92,
                        "Dự báo Phường Cầu Giấy ngày mai thế nào?")}],
    "tháng sau ngày 15 thì sao?",
    "smalltalk_weather", "ward", 0.62,
    None)

# ═══════════════════════════════════════════════════════════════════════════
# E) TURN=3 chains (5)
# ═══════════════════════════════════════════════════════════════════════════

# 3T-01: rural xã chain — Xã Bát Tràng time chain
SAMPLES.append({
    "_kind": "Turn3_xa_time",
    "history": [
        {"user": "Xã Bát Tràng ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Xã Bát Tràng ngày mai thế nào?")},
        {"user": "ngày kia thì sao?",
         "assistant": asst("daily_forecast", "ward", 0.80,
                           "Dự báo Xã Bát Tràng ngày kia thế nào?")}
    ],
    "input": "cuối tuần thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Xã Bát Tràng cuối tuần này thế nào?"}
})

# 3T-02: comparison → time → drop
SAMPLES.append({
    "_kind": "Turn3_cmp_evolve",
    "history": [
        {"user": "So sánh Phường Cầu Giấy và Phường Hoàn Kiếm hôm nay",
         "assistant": asst("location_comparison", "ward", 0.92,
                           "So sánh thời tiết Phường Cầu Giấy và Phường Hoàn Kiếm hôm nay")},
        {"user": "ngày mai thì sao?",
         "assistant": asst("location_comparison", "ward", 0.80,
                           "So sánh Phường Cầu Giấy và Phường Hoàn Kiếm ngày mai")}
    ],
    "input": "Phường Cầu Giấy cụ thể có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Cầu Giấy ngày mai có mưa không?"}
})

# 3T-03: ward → district → drill back to ward
SAMPLES.append({
    "_kind": "Turn3_scope_drill",
    "history": [
        {"user": "Phường Hà Đông hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Hà Đông hôm nay thế nào?")},
        {"user": "Quận Hà Đông tổng quan thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Tổng quan thời tiết Quận Hà Đông hôm nay")}
    ],
    "input": "Phường Yên Nghĩa cụ thể nhỉ?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Phường Yên Nghĩa hiện tại thế nào?"}
})

# 3T-04: time chain với historical
SAMPLES.append({
    "_kind": "Turn3_historical_chain",
    "history": [
        {"user": "Phường Đống Đa hôm qua nhiệt độ bao nhiêu?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Đống Đa hôm qua nhiệt độ bao nhiêu?")},
        {"user": "hôm kia thì sao?",
         "assistant": asst("historical_weather", "ward", 0.80,
                           "Phường Đống Đa hôm kia nhiệt độ bao nhiêu?")}
    ],
    "input": "tuần trước trung bình?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Đống Đa tuần trước nhiệt độ trung bình bao nhiêu?"}
})

# 3T-05: rural district chain
SAMPLES.append({
    "_kind": "Turn3_district_rural",
    "history": [
        {"user": "Huyện Đông Anh hôm nay thế nào?",
         "assistant": asst("current_weather", "district", 0.92,
                           "Thời tiết Huyện Đông Anh hôm nay thế nào?")},
        {"user": "có gió không?",
         "assistant": asst("wind_query", "district", 0.80,
                           "Huyện Đông Anh hiện tại có gió không?")}
    ],
    "input": "ngày mai gió mạnh hơn không?",
    "output": {"intent": "wind_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai Huyện Đông Anh gió có mạnh hơn hôm nay không?"}
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

out_path = Path(__file__).parent / 'batch_10_multiturn.jsonl'
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
intents = Counter(s['output']['intent'] for s in SAMPLES)
print(f'Intent distribution: {dict(intents)}')
