"""V7 Batch 12 (Phase 4 multi-turn FINAL) — 50 samples.

Composition (final coverage push + tier T4 calibration):
- 8 NEW pure xã chưa cover: Suối Hai, Vật Lại, Yên Bài (Ba Vì), Quảng Bị,
  Xuân Mai (Chương Mỹ), Thượng Phúc (Thường Tín), Phường Vĩnh Hưng,
  Phường Yên Sở (Hoàng Mai).
- 10 Xã COLLISION versions (đối lập với Huyện same name): Xã Đan Phượng,
  Xã Đông Anh, Xã Hoài Đức, Xã Mê Linh, Xã Phúc Thọ, Xã Phú Xuyên, Xã Quốc Oai,
  Xã Thanh Oai, Xã Thanh Trì, Xã Thạch Thất, Xã Thường Tín, Xã Ứng Hòa.
- 7 Phường Chương Mỹ (collision rural phường) — only phường in Huyện Chương Mỹ;
  + 1 Xã Ba Vì (collision xã version).
- 8 BORDERLINE T4=0.74 samples: collision core ambiguous, scope decided BARELY
  by user prefix hint hoặc context. Tier T4 trial — calibration ECE depends on this.
- 5 turn=3 final chains.
- 5 misc final patterns (intent-shift, comparison-evolve).
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
        "_kind": kind, "history": hist, "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

def t1(name, intent="current_weather", time_phrase="hôm nay", scope="ward"):
    return {"user": f"{name} {time_phrase} thế nào?",
            "assistant": asst(intent, scope, 0.92,
                              f"Thời tiết {name} {time_phrase} thế nào?")}

# ═══════════════════════════════════════════════════════════════════════════
# A) NEW pure xã + phường (8) — final coverage push
# ═══════════════════════════════════════════════════════════════════════════

# 1. Xã Suối Hai (Ba Vì)
add("R_pure_xa", [t1("Xã Suối Hai")], "ngày mai có mưa không?",
    "rain_query", "ward", 0.80, "Ngày mai Xã Suối Hai có mưa không?")

# 2. Xã Vật Lại (Ba Vì)
add("R_pure_xa", [t1("Xã Vật Lại")], "khu đó tuần này gió thế nào?",
    "wind_query", "ward", 0.80, "Xã Vật Lại tuần này gió thế nào?")

# 3. Xã Yên Bài (Ba Vì)
add("R_pure_xa", [t1("Xã Yên Bài")], "ở đó hôm qua có mưa không?",
    "historical_weather", "ward", 0.80, "Hôm qua Xã Yên Bài có mưa không?")

# 4. Xã Quảng Bị (Chương Mỹ)
add("R_pure_xa", [t1("Xã Quảng Bị")], "khu đó cuối tuần thế nào?",
    "daily_forecast", "ward", 0.80, "Xã Quảng Bị cuối tuần dự báo thế nào?")

# 5. Xã Xuân Mai (Chương Mỹ)
add("R_pure_xa", [t1("Xã Xuân Mai")], "tổng quan ngày mai?",
    "weather_overview", "ward", 0.80, "Tổng quan thời tiết Xã Xuân Mai ngày mai")

# 6. Xã Thượng Phúc (Thường Tín)
add("R_pure_xa", [t1("Xã Thượng Phúc")], "có cảnh báo lũ không?",
    "weather_alert", "ward", 0.80, "Xã Thượng Phúc có cảnh báo lũ không?")

# 7. Phường Vĩnh Hưng (Hoàng Mai) — pure phường
add("R_pure_phuong", [t1("Phường Vĩnh Hưng")], "khu đó nhiệt độ?",
    "temperature_query", "ward", 0.80, "Phường Vĩnh Hưng nhiệt độ hiện tại bao nhiêu?")

# 8. Phường Yên Sở (Hoàng Mai) — pure phường
add("R_pure_phuong", [t1("Phường Yên Sở")], "ngày mai có mưa to không?",
    "rain_query", "ward", 0.80, "Ngày mai Phường Yên Sở có mưa to không?")

# ═══════════════════════════════════════════════════════════════════════════
# B) Xã COLLISION versions (12) — đối lập Huyện same name
# ═══════════════════════════════════════════════════════════════════════════

# 9. Xã Đan Phượng (collision xã)
add("R_collision_xa", [t1("Xã Đan Phượng")], "ở đó tuần này thế nào?",
    "daily_forecast", "ward", 0.80, "Xã Đan Phượng tuần này dự báo thế nào?")

# 10. Xã Đông Anh (collision xã, đối lập Huyện Đông Anh)
add("R_collision_xa", [t1("Xã Đông Anh")], "khu đó có gió mạnh không?",
    "wind_query", "ward", 0.80, "Xã Đông Anh có gió mạnh không?")

# 11. Xã Hoài Đức (collision)
add("R_collision_xa", [t1("Xã Hoài Đức")], "tổng quan hôm nay ra sao?",
    "weather_overview", "ward", 0.80, "Tổng quan thời tiết Xã Hoài Đức hôm nay")

# 12. Xã Mê Linh (collision)
add("R_collision_xa", [t1("Xã Mê Linh")], "ngày mai cảnh báo gì không?",
    "weather_alert", "ward", 0.80, "Ngày mai Xã Mê Linh có cảnh báo gì không?")

# 13. Xã Phúc Thọ (collision)
add("R_collision_xa", [t1("Xã Phúc Thọ")], "ở đó độ ẩm cao không?",
    "humidity_fog_query", "ward", 0.80, "Xã Phúc Thọ độ ẩm hiện tại có cao không?")

# 14. Xã Phú Xuyên (collision)
add("R_collision_xa", [t1("Xã Phú Xuyên")], "tuần trước thế nào?",
    "historical_weather", "ward", 0.80, "Xã Phú Xuyên tuần trước thời tiết thế nào?")

# 15. Xã Quốc Oai (collision)
add("R_collision_xa", [t1("Xã Quốc Oai")], "khu đó có thích hợp đi rừng không?",
    "activity_weather", "ward", 0.80, "Xã Quốc Oai hôm nay có thích hợp đi rừng không?")

# 16. Xã Thanh Oai (collision)
add("R_collision_xa", [t1("Xã Thanh Oai")], "buổi tối có mưa không?",
    "rain_query", "ward", 0.80, "Xã Thanh Oai buổi tối có mưa không?")

# 17. Xã Thanh Trì (collision)
add("R_collision_xa", [t1("Xã Thanh Trì")], "có cảnh báo ngập không?",
    "weather_alert", "ward", 0.80, "Xã Thanh Trì có cảnh báo ngập lụt không?")

# 18. Xã Thạch Thất (collision)
add("R_collision_xa", [t1("Xã Thạch Thất")], "ngày kia thế nào?",
    "daily_forecast", "ward", 0.80, "Xã Thạch Thất ngày kia dự báo thế nào?")

# 19. Xã Thường Tín (collision)
add("R_collision_xa", [t1("Xã Thường Tín")], "khu đó UV cao không?",
    "expert_weather_param", "ward", 0.80, "Xã Thường Tín UV hôm nay có cao không?")

# 20. Xã Ứng Hòa (collision)
add("R_collision_xa", [t1("Xã Ứng Hòa")], "ở đó có nóng không?",
    "temperature_query", "ward", 0.80, "Xã Ứng Hòa hôm nay có nóng không?")

# ═══════════════════════════════════════════════════════════════════════════
# C) Phường Chương Mỹ + Xã Ba Vì (collision rural — both rare patterns)
# ═══════════════════════════════════════════════════════════════════════════

# 21. Phường Chương Mỹ (only phường in Huyện Chương Mỹ — collision phường rural)
add("R_collision_phuong_rural", [t1("Phường Chương Mỹ")], "ngày mai có mưa không?",
    "rain_query", "ward", 0.80, "Ngày mai Phường Chương Mỹ có mưa không?")

# 22. Xã Ba Vì (collision xã, đối lập Huyện Ba Vì)
add("R_collision_xa", [t1("Xã Ba Vì")], "ở đó tuần này có rét không?",
    "seasonal_context", "ward", 0.80, "Xã Ba Vì tuần này có rét đậm không?")

# ═══════════════════════════════════════════════════════════════════════════
# D) BORDERLINE T4=0.74 confidence (8) — collision-decided ambiguous
# ═══════════════════════════════════════════════════════════════════════════

# 23. T4: user dùng "Cầu Giấy" trần (no prefix), context không strong → T4
add("T4_borderline",
    [{"user": "Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.74,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "khu đó có mưa không?",
    "rain_query", "ward", 0.74,
    "Phường Cầu Giấy có mưa không?")

# 24. T4: "Hà Đông" trần → ward (default Phường, but borderline)
add("T4_borderline",
    [{"user": "Hà Đông tuần này thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.74,
                        "Phường Hà Đông tuần này dự báo thế nào?")}],
    "ngày mai cụ thể?",
    "daily_forecast", "ward", 0.74,
    "Phường Hà Đông ngày mai dự báo thế nào?")

# 25. T4: "Hoàng Mai" trần → ward
add("T4_borderline",
    [{"user": "Hoàng Mai có mưa không?",
      "assistant": asst("rain_query", "ward", 0.74,
                        "Phường Hoàng Mai có mưa không?")}],
    "khoảng mấy giờ?",
    "rain_query", "ward", 0.74,
    "Phường Hoàng Mai mưa khoảng mấy giờ?")

# 26. T4: "Đông Anh" trần → district default rural
add("T4_borderline",
    [{"user": "Đông Anh hôm nay thế nào?",
      "assistant": asst("current_weather", "district", 0.74,
                        "Thời tiết Huyện Đông Anh hôm nay thế nào?")}],
    "có cảnh báo gì không?",
    "weather_alert", "district", 0.74,
    "Huyện Đông Anh có cảnh báo thời tiết gì không?")

# 27. T4: "Sóc Sơn" trần → district
add("T4_borderline",
    [{"user": "Sóc Sơn tuần này thế nào?",
      "assistant": asst("daily_forecast", "district", 0.74,
                        "Huyện Sóc Sơn tuần này dự báo thế nào?")}],
    "có gió mạnh không?",
    "wind_query", "district", 0.74,
    "Huyện Sóc Sơn tuần này có gió mạnh không?")

# 28. T4: "Mỹ Đức" trần — collision, default xã (ward)
add("T4_borderline",
    [{"user": "Mỹ Đức hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.74,
                        "Thời tiết Xã Mỹ Đức hôm nay thế nào?")}],
    "ở đó có ngập không?",
    "weather_alert", "ward", 0.74,
    "Xã Mỹ Đức có nguy cơ ngập lụt không?")

# 29. T4: "Hoàn Kiếm" trần → ward default
add("T4_borderline",
    [{"user": "Hoàn Kiếm sáng nay thế nào?",
      "assistant": asst("hourly_forecast", "ward", 0.74,
                        "Phường Hoàn Kiếm sáng nay thế nào?")}],
    "tầm nhìn xa thế nào?",
    "expert_weather_param", "ward", 0.74,
    "Phường Hoàn Kiếm tầm nhìn xa hiện tại thế nào?")

# 30. T4: "Long Biên" trần → ward
add("T4_borderline",
    [{"user": "Long Biên hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.74,
                        "Phường Long Biên hôm nay thế nào?")}],
    "buổi tối có mát không?",
    "smalltalk_weather", "ward", 0.74,
    "Phường Long Biên buổi tối có mát không?")

# ═══════════════════════════════════════════════════════════════════════════
# E) TURN=3 final chains (5)
# ═══════════════════════════════════════════════════════════════════════════

# 31. 3-turn comparison evolve, district-level
SAMPLES.append({
    "_kind": "Turn3_d_cmp",
    "history": [
        {"user": "So sánh Huyện Sóc Sơn và Huyện Đông Anh hôm nay",
         "assistant": asst("location_comparison", "district", 0.92,
                           "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh hôm nay")},
        {"user": "đâu nhiều mưa hơn?",
         "assistant": asst("rain_query", "district", 0.80,
                           "Huyện Sóc Sơn và Huyện Đông Anh, đâu mưa nhiều hơn?")}
    ],
    "input": "ngày mai thì sao?",
    "output": {"intent": "rain_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai Huyện Sóc Sơn và Huyện Đông Anh đâu mưa nhiều hơn?"}
})

# 32. 3-turn rural xã with explicit-switch
SAMPLES.append({
    "_kind": "Turn3_rural_switch",
    "history": [
        {"user": "Xã Minh Châu hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Xã Minh Châu hôm nay thế nào?")},
        {"user": "Huyện Ba Vì nói chung thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Tổng quan thời tiết Huyện Ba Vì hôm nay")}
    ],
    "input": "Xã Cổ Đô cụ thể?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Thời tiết Xã Cổ Đô hiện tại thế nào?"}
})

# 33. 3-turn time chain rural (Xã Đoài Phương)
SAMPLES.append({
    "_kind": "Turn3_xa_time_chain",
    "history": [
        {"user": "Xã Đoài Phương ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Xã Đoài Phương ngày mai thế nào?")},
        {"user": "ngày kia có mưa không?",
         "assistant": asst("rain_query", "ward", 0.80,
                           "Ngày kia Xã Đoài Phương có mưa không?")}
    ],
    "input": "cuối tuần thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Xã Đoài Phương cuối tuần này thế nào?"}
})

# 34. 3-turn city → ward → ward different (cross-ward in same district)
SAMPLES.append({
    "_kind": "Turn3_city_ward_ward",
    "history": [
        {"user": "Hà Nội tuần này nóng không?",
         "assistant": asst("daily_forecast", "city", 0.85,
                           "Hà Nội tuần này nóng không?")},
        {"user": "Phường Cầu Giấy cụ thể?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Phường Cầu Giấy tuần này nóng không?")}
    ],
    "input": "Phường Hoàn Kiếm thì sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Hoàn Kiếm tuần này nóng không?"}
})

# 35. 3-turn time + intent shift cùng lúc
SAMPLES.append({
    "_kind": "Turn3_intent_time",
    "history": [
        {"user": "Phường Hoàng Mai hôm nay nhiệt độ?",
         "assistant": asst("temperature_query", "ward", 0.92,
                           "Phường Hoàng Mai nhiệt độ hôm nay bao nhiêu?")},
        {"user": "ngày mai mấy độ?",
         "assistant": asst("temperature_query", "ward", 0.80,
                           "Ngày mai Phường Hoàng Mai nhiệt độ bao nhiêu?")}
    ],
    "input": "có gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai Phường Hoàng Mai có gió không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# F) MISC final patterns (10)
# ═══════════════════════════════════════════════════════════════════════════

# 36. Comparison ward vs city (mixed scope)
add("Misc_cmp_mixed",
    [{"user": "Phường Cầu Giấy hôm nay nóng không?",
      "assistant": asst("temperature_query", "ward", 0.92,
                        "Phường Cầu Giấy hôm nay nhiệt độ bao nhiêu?")}],
    "Hà Nội nói chung mát hơn không?",
    "location_comparison", "city", 0.85,
    "So sánh Phường Cầu Giấy với Hà Nội nói chung, đâu mát hơn?")

# 37. Comparison district vs district anaphoric
add("Misc_cmp_d2d",
    [{"user": "Huyện Sóc Sơn hôm nay thế nào?",
      "assistant": asst("current_weather", "district", 0.92,
                        "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}],
    "so với Huyện Đông Anh thì sao?",
    "location_comparison", "district", 0.85,
    "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh hôm nay")

# 38. Smalltalk → continue smalltalk
add("Misc_smalltalk_chain",
    [{"user": "Phường Hoàn Kiếm hôm nay có cần áo khoác không?",
      "assistant": asst("smalltalk_weather", "ward", 0.85,
                        "Phường Hoàn Kiếm hôm nay có cần áo khoác không?")}],
    "buổi tối thì sao?",
    "smalltalk_weather", "ward", 0.80,
    "Phường Hoàn Kiếm buổi tối có cần áo khoác không?")

# 39. Long-form anaphoric — "khu vực phía Tây thành phố"
add("Misc_loc_anaphor_complex",
    [{"user": "Phường Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "khu vực đó nói chung tuần này có mưa nhiều không?",
    "rain_query", "ward", 0.80,
    "Phường Cầu Giấy tuần này có mưa nhiều không?")

# 40. Bare weekday "thứ 4" với prior tuần này
add("Misc_bare_weekday_inherit",
    [{"user": "Phường Tây Hồ tuần này thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.85,
                        "Phường Tây Hồ tuần này thời tiết thế nào?")}],
    "thứ 4 cụ thể?",
    "daily_forecast", "ward", 0.80,
    "Phường Tây Hồ thứ 4 tuần này thời tiết thế nào?")

# 41. Mid-week → weekend
add("Misc_midweek_to_weekend",
    [{"user": "Phường Hà Đông thứ 4 tuần này thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.92,
                        "Dự báo Phường Hà Đông thứ 4 tuần này thế nào?")}],
    "thứ 7 cuối tuần thì sao?",
    "daily_forecast", "ward", 0.80,
    "Dự báo Phường Hà Đông thứ 7 cuối tuần này thế nào?")

# 42. Weather alert chain (alert → activity impact)
add("Misc_alert_to_activity",
    [{"user": "Phường Hoàng Mai có cảnh báo bão không?",
      "assistant": asst("weather_alert", "ward", 0.92,
                        "Phường Hoàng Mai có cảnh báo bão không?")}],
    "có nên đi học không?",
    "smalltalk_weather", "ward", 0.80,
    "Hôm nay Phường Hoàng Mai có nên đi học không?")

# 43. Activity → time advance
add("Misc_activity_time",
    [{"user": "Phường Tây Hồ hôm nay có thích hợp chạy bộ không?",
      "assistant": asst("activity_weather", "ward", 0.92,
                        "Phường Tây Hồ hôm nay có thích hợp chạy bộ không?")}],
    "ngày mai thì sao?",
    "activity_weather", "ward", 0.80,
    "Ngày mai Phường Tây Hồ có thích hợp chạy bộ không?")

# 44. Specific param → other param
add("Misc_param_shift",
    [{"user": "Phường Đống Đa hôm nay UV bao nhiêu?",
      "assistant": asst("expert_weather_param", "ward", 0.92,
                        "UV Phường Đống Đa hôm nay bao nhiêu?")}],
    "thế còn áp suất?",
    "expert_weather_param", "ward", 0.80,
    "Áp suất Phường Đống Đa hiện tại bao nhiêu?")

# 45. Negation/uncertainty handling
add("Misc_negation",
    [{"user": "Phường Cầu Giấy hôm nay có mưa không?",
      "assistant": asst("rain_query", "ward", 0.92,
                        "Phường Cầu Giấy hôm nay có mưa không?")}],
    "thế ngày mai chắc chắn không mưa chứ?",
    "rain_query", "ward", 0.80,
    "Ngày mai Phường Cầu Giấy có chắc chắn không mưa không?")

# 46. Tomorrow night specifically
add("Misc_specific_time",
    [{"user": "Phường Hoàn Kiếm ngày mai thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.92,
                        "Phường Hoàn Kiếm ngày mai thế nào?")}],
    "tối mai 8h thì sao?",
    "hourly_forecast", "ward", 0.80,
    "Phường Hoàn Kiếm tối mai khoảng 8 giờ thời tiết thế nào?")

# 47. Multi-day forecast → narrow to one day
add("Misc_narrow_day",
    [{"user": "Phường Long Biên 3 ngày tới thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.85,
                        "Dự báo Phường Long Biên 3 ngày tới thế nào?")}],
    "ngày kia cụ thể?",
    "daily_forecast", "ward", 0.80,
    "Phường Long Biên ngày kia cụ thể thế nào?")

# 48. Hist → seasonal pivot
add("Misc_hist_seasonal",
    [{"user": "Phường Cầu Giấy tuần trước có mưa không?",
      "assistant": asst("historical_weather", "ward", 0.92,
                        "Phường Cầu Giấy tuần trước có mưa không?")}],
    "so với mùa này năm trước?",
    "seasonal_context", "ward", 0.80,
    "Phường Cầu Giấy tuần trước so với mùa này năm trước thế nào?")

# 49. Wind → activity recommendation
add("Misc_wind_activity",
    [{"user": "Phường Bồ Đề hôm nay gió thế nào?",
      "assistant": asst("wind_query", "ward", 0.92,
                        "Phường Bồ Đề hôm nay gió thế nào?")}],
    "có thả diều được không?",
    "smalltalk_weather", "ward", 0.80,
    "Phường Bồ Đề hôm nay gió có thích hợp thả diều không?")

# 50. End-of-day fog → next-day fog
add("Misc_fog_continuity",
    [{"user": "Phường Tây Hồ sáng nay có sương không?",
      "assistant": asst("humidity_fog_query", "ward", 0.92,
                        "Phường Tây Hồ sáng nay có sương mù không?")}],
    "sáng mai thì sao?",
    "humidity_fog_query", "ward", 0.80,
    "Phường Tây Hồ sáng mai có sương mù không?")

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

out_path = Path(__file__).parent / 'batch_12_multiturn.jsonl'
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
confs = Counter(s['output']['confidence'] for s in SAMPLES)
print(f'Confidence distribution: {dict(confs)}')
