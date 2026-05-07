"""V7 Batch 11 (Phase 4 multi-turn cont) — 50 samples.

Composition:
- 30 RURAL Xã coverage (chưa cover): Bất Bạt, Quảng Oai (Ba Vì), Hòa Phú, Phú Nghĩa,
  Trần Phú (Chương Mỹ), Liên Minh, Ô Diên (Đan Phượng), Phúc Thịnh, Thiên Lộc, Thư Lâm,
  Vĩnh Thanh (Đông Anh), Dương Hòa, Sơn Đồng (Hoài Đức), Quang Minh, Tiến Thắng (Mê Linh),
  Chuyên Mỹ, Phượng Dực (Phú Xuyên), Phúc Lộc (Phúc Thọ), Kiều Phú, Phú Cát (Quốc Oai),
  Kim Anh, Nội Bài, Trung Giã (Sóc Sơn), Dân Hòa (Thanh Oai), Đại Thanh, Nam Phù,
  Ngọc Hồi (Thanh Trì), Chương Dương, Thượng Phúc (Thường Tín), Tây Phương,
  Yên Xuân (Thạch Thất), Hạ Bằng (Thạch Thất), Hòa Xá, Ứng Thiên (Ứng Hòa).
- 5 NAM TỪ LIÊM remaining wards: Từ Liêm, Xuân Phương.
- 5 CITY-LEVEL multi-turn (Hà Nội context across turns).
- 5 ABSTAIN/REFUSE edge cases (out-of-scope phenomena/time/location).
- 5 turn=3 chains (rural focus).
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

def t1_xa(ward_name):
    """Helper: synthesized turn-1 establishing a Xã."""
    return {"user": f"{ward_name} hôm nay thế nào?",
            "assistant": asst("current_weather", "ward", 0.92,
                              f"Thời tiết {ward_name} hôm nay thế nào?")}

def t1_phuong(ward_name):
    return {"user": f"{ward_name} hôm nay thế nào?",
            "assistant": asst("current_weather", "ward", 0.92,
                              f"Thời tiết {ward_name} hôm nay thế nào?")}

# ═══════════════════════════════════════════════════════════════════════════
# A) RURAL Xã coverage (30) — diverse anaphoric inputs
# ═══════════════════════════════════════════════════════════════════════════

# 1. Xã Bất Bạt (Ba Vì)
add("R_xa", [t1_xa("Xã Bất Bạt")], "ngày mai có mưa không?",
    "rain_query", "ward", 0.80, "Ngày mai Xã Bất Bạt có mưa không?")

# 2. Xã Quảng Oai (Ba Vì)
add("R_xa", [t1_xa("Xã Quảng Oai")], "khu đó có cảnh báo lũ không?",
    "weather_alert", "ward", 0.80, "Xã Quảng Oai có cảnh báo lũ lụt không?")

# 3. Xã Hòa Phú (Chương Mỹ)
add("R_xa", [t1_xa("Xã Hòa Phú")], "ở đó có gió mạnh không?",
    "wind_query", "ward", 0.80, "Xã Hòa Phú có gió mạnh không?")

# 4. Xã Phú Nghĩa (Chương Mỹ)
add("R_xa", [t1_xa("Xã Phú Nghĩa")], "tuần này có mưa nhiều không?",
    "rain_query", "ward", 0.80, "Xã Phú Nghĩa tuần này có mưa nhiều không?")

# 5. Xã Trần Phú (Chương Mỹ)
add("R_xa", [t1_xa("Xã Trần Phú")], "ngày mai có thích hợp ra đồng không?",
    "activity_weather", "ward", 0.80, "Xã Trần Phú ngày mai có thích hợp ra đồng không?")

# 6. Xã Liên Minh (Đan Phượng)
add("R_xa", [t1_xa("Xã Liên Minh")], "buổi sáng có sương mù không?",
    "humidity_fog_query", "ward", 0.80, "Xã Liên Minh buổi sáng có sương mù không?")

# 7. Xã Ô Diên (Đan Phượng)
add("R_xa", [t1_xa("Xã Ô Diên")], "khu đó nhiệt độ tối thiểu?",
    "temperature_query", "ward", 0.80, "Xã Ô Diên nhiệt độ tối thiểu hôm nay bao nhiêu?")

# 8. Xã Phúc Thịnh (Đông Anh)
add("R_xa", [t1_xa("Xã Phúc Thịnh")], "ngày kia thế nào?",
    "daily_forecast", "ward", 0.80, "Xã Phúc Thịnh ngày kia dự báo thế nào?")

# 9. Xã Thiên Lộc (Đông Anh)
add("R_xa", [t1_xa("Xã Thiên Lộc")], "ở đó độ ẩm cao không?",
    "humidity_fog_query", "ward", 0.80, "Xã Thiên Lộc độ ẩm hiện tại có cao không?")

# 10. Xã Thư Lâm (Đông Anh)
add("R_xa", [t1_xa("Xã Thư Lâm")], "tuần trước nhiệt độ thế nào?",
    "historical_weather", "ward", 0.80, "Xã Thư Lâm tuần trước nhiệt độ thế nào?")

# 11. Xã Vĩnh Thanh (Đông Anh)
add("R_xa", [t1_xa("Xã Vĩnh Thanh")], "khu đó có cảnh báo gì không?",
    "weather_alert", "ward", 0.80, "Xã Vĩnh Thanh có cảnh báo thời tiết gì không?")

# 12. Xã Dương Hòa (Hoài Đức)
add("R_xa", [t1_xa("Xã Dương Hòa")], "tổng quan ngày mai?",
    "weather_overview", "ward", 0.80, "Tổng quan thời tiết Xã Dương Hòa ngày mai")

# 13. Xã Sơn Đồng (Hoài Đức)
add("R_xa", [t1_xa("Xã Sơn Đồng")], "có thích hợp đi cấy không?",
    "activity_weather", "ward", 0.80, "Xã Sơn Đồng hôm nay có thích hợp đi cấy không?")

# 14. Xã Quang Minh (Mê Linh)
add("R_xa", [t1_xa("Xã Quang Minh")], "buổi tối có mưa không?",
    "rain_query", "ward", 0.80, "Xã Quang Minh buổi tối có mưa không?")

# 15. Xã Tiến Thắng (Mê Linh)
add("R_xa", [t1_xa("Xã Tiến Thắng")], "tuần sau có nắng không?",
    "daily_forecast", "ward", 0.80, "Xã Tiến Thắng tuần sau có nắng không?")

# 16. Xã Chuyên Mỹ (Phú Xuyên)
add("R_xa", [t1_xa("Xã Chuyên Mỹ")], "khu đó có ngập không?",
    "weather_alert", "ward", 0.80, "Xã Chuyên Mỹ có nguy cơ ngập lụt không?")

# 17. Xã Phượng Dực (Phú Xuyên)
add("R_xa", [t1_xa("Xã Phượng Dực")], "ngày mai gió thế nào?",
    "wind_query", "ward", 0.80, "Xã Phượng Dực ngày mai gió thế nào?")

# 18. Xã Phúc Lộc (Phúc Thọ)
add("R_xa", [t1_xa("Xã Phúc Lộc")], "ở đó có sương sáng?",
    "humidity_fog_query", "ward", 0.80, "Xã Phúc Lộc buổi sáng có sương mù không?")

# 19. Xã Kiều Phú (Quốc Oai)
add("R_xa", [t1_xa("Xã Kiều Phú")], "tổng quan tuần này?",
    "weather_overview", "ward", 0.80, "Tổng quan thời tiết Xã Kiều Phú tuần này")

# 20. Xã Phú Cát (Quốc Oai)
add("R_xa", [t1_xa("Xã Phú Cát")], "có thích hợp đi rừng không?",
    "activity_weather", "ward", 0.80, "Xã Phú Cát hôm nay có thích hợp đi rừng không?")

# 21. Xã Kim Anh (Sóc Sơn)
add("R_xa", [t1_xa("Xã Kim Anh")], "ngày mai mưa kéo dài đến mấy giờ?",
    "rain_query", "ward", 0.80, "Ngày mai Xã Kim Anh mưa kéo dài đến mấy giờ?")

# 22. Xã Nội Bài (Sóc Sơn) — KHÔNG nhầm với Sân bay Nội Bài (POI)
add("R_xa_collision_admin",
    [t1_xa("Xã Nội Bài")], "ở đó tầm nhìn xa thế nào?",
    "expert_weather_param", "ward", 0.80, "Xã Nội Bài tầm nhìn xa hiện tại thế nào?")

# 23. Xã Trung Giã (Sóc Sơn)
add("R_xa", [t1_xa("Xã Trung Giã")], "khu đó UV cao không?",
    "expert_weather_param", "ward", 0.80, "Xã Trung Giã UV hôm nay có cao không?")

# 24. Xã Dân Hòa (Thanh Oai)
add("R_xa", [t1_xa("Xã Dân Hòa")], "tuần này có rét đậm không?",
    "seasonal_context", "ward", 0.80, "Xã Dân Hòa tuần này có rét đậm không?")

# 25. Xã Đại Thanh (Thanh Trì)
add("R_xa", [t1_xa("Xã Đại Thanh")], "có cảnh báo giông không?",
    "weather_alert", "ward", 0.80, "Xã Đại Thanh có cảnh báo giông không?")

# 26. Xã Nam Phù (Thanh Trì)
add("R_xa", [t1_xa("Xã Nam Phù")], "ngày mai có mưa rào không?",
    "rain_query", "ward", 0.80, "Ngày mai Xã Nam Phù có mưa rào không?")

# 27. Xã Ngọc Hồi (Thanh Trì)
add("R_xa", [t1_xa("Xã Ngọc Hồi")], "đêm nay nhiệt độ?",
    "temperature_query", "ward", 0.80, "Xã Ngọc Hồi đêm nay nhiệt độ bao nhiêu?")

# 28. Xã Chương Dương (Thường Tín)
add("R_xa", [t1_xa("Xã Chương Dương")], "khu đó có ngập sông Hồng không?",
    "weather_alert", "ward", 0.80, "Xã Chương Dương có nguy cơ ngập từ sông Hồng không?")

# 29. Xã Tây Phương (Thạch Thất)
add("R_xa", [t1_xa("Xã Tây Phương")], "ngày kia có mưa không?",
    "rain_query", "ward", 0.80, "Xã Tây Phương ngày kia có mưa không?")

# 30. Xã Hạ Bằng (Thạch Thất)
add("R_xa", [t1_xa("Xã Hạ Bằng")], "ở đó hôm qua thế nào?",
    "historical_weather", "ward", 0.80, "Hôm qua Xã Hạ Bằng thời tiết thế nào?")

# ═══════════════════════════════════════════════════════════════════════════
# B) NAM TỪ LIÊM remaining wards (3) + Đông Anh extras (2)
# ═══════════════════════════════════════════════════════════════════════════

# 31. Phường Từ Liêm
add("R_phuong", [t1_phuong("Phường Từ Liêm")], "tuần này có mưa không?",
    "rain_query", "ward", 0.80, "Phường Từ Liêm tuần này có mưa không?")

# 32. Phường Xuân Phương
add("R_phuong", [t1_phuong("Phường Xuân Phương")], "ở đó tổng quan ra sao?",
    "weather_overview", "ward", 0.80, "Tổng quan thời tiết Phường Xuân Phương hôm nay")

# 33. Xã Yên Xuân (Thạch Thất)
add("R_xa", [t1_xa("Xã Yên Xuân")], "khu đó cuối tuần thế nào?",
    "daily_forecast", "ward", 0.80, "Xã Yên Xuân cuối tuần dự báo thế nào?")

# 34. Xã Hòa Xá (Ứng Hòa)
add("R_xa", [t1_xa("Xã Hòa Xá")], "tuần trước có mưa không?",
    "historical_weather", "ward", 0.80, "Xã Hòa Xá tuần trước có mưa không?")

# 35. Xã Ứng Thiên (Ứng Hòa)
add("R_xa", [t1_xa("Xã Ứng Thiên")], "ngày mai gió mạnh không?",
    "wind_query", "ward", 0.80, "Ngày mai Xã Ứng Thiên gió mạnh không?")

# ═══════════════════════════════════════════════════════════════════════════
# C) CITY-LEVEL multi-turn (5)
# ═══════════════════════════════════════════════════════════════════════════

# 36. Hà Nội time chain
add("City_time_chain",
    [{"user": "Hà Nội hôm nay thế nào?",
      "assistant": asst("current_weather", "city", 0.85,
                        "Thời tiết Hà Nội hôm nay thế nào?")}],
    "ngày mai thế nào?",
    "daily_forecast", "city", 0.80, "Hà Nội ngày mai thời tiết thế nào?")

# 37. Hà Nội intent shift
add("City_intent_shift",
    [{"user": "Hà Nội hôm nay nóng không?",
      "assistant": asst("temperature_query", "city", 0.85,
                        "Hà Nội hôm nay nhiệt độ bao nhiêu?")}],
    "có nồm không?",
    "humidity_fog_query", "city", 0.80, "Hà Nội hôm nay có nồm ẩm không?")

# 38. Hà Nội historical → forecast
add("City_temporal_shift",
    [{"user": "Hà Nội hôm qua mưa to không?",
      "assistant": asst("historical_weather", "city", 0.85,
                        "Hà Nội hôm qua có mưa to không?")}],
    "ngày mai có mưa tiếp không?",
    "rain_query", "city", 0.80, "Hà Nội ngày mai có mưa tiếp không?")

# 39. Hà Nội weather_alert
add("City_alert",
    [{"user": "Hà Nội tuần này thế nào?",
      "assistant": asst("daily_forecast", "city", 0.85,
                        "Hà Nội tuần này thời tiết thế nào?")}],
    "có cảnh báo giông không?",
    "weather_alert", "city", 0.80, "Hà Nội tuần này có cảnh báo giông không?")

# 40. Hà Nội seasonal
add("City_seasonal",
    [{"user": "Hà Nội mùa này thế nào?",
      "assistant": asst("seasonal_context", "city", 0.85,
                        "Hà Nội mùa này thời tiết thế nào?")}],
    "so với mùa này năm ngoái thì sao?",
    "seasonal_context", "city", 0.80, "Hà Nội mùa này so với mùa này năm ngoái thế nào?")

# ═══════════════════════════════════════════════════════════════════════════
# D) ABSTAIN/REFUSE edge cases (5)
# ═══════════════════════════════════════════════════════════════════════════

# 41. Out-of-scope city (HCM, Hải Phòng) — must abstain
add("Abstain_other_city",
    [{"user": "Phường Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "TP Hồ Chí Minh thế nào?",
    "smalltalk_weather", "city", 0.62, None)

# 42. Out-of-scope phenomenon (tuyết — Hà Nội không có tuyết) — abstain
add("Abstain_oos_phenomenon",
    [{"user": "Hà Nội hôm nay thế nào?",
      "assistant": asst("current_weather", "city", 0.85,
                        "Thời tiết Hà Nội hôm nay thế nào?")}],
    "có tuyết rơi không?",
    "smalltalk_weather", "city", 0.62, None)

# 43. Quá xa thời gian forecast (>8 days)
add("Abstain_oos_time",
    [{"user": "Phường Hoàng Mai tuần này thế nào?",
      "assistant": asst("daily_forecast", "ward", 0.92,
                        "Dự báo Phường Hoàng Mai tuần này thế nào?")}],
    "thứ 5 cuối tháng sau dự báo ra sao?",
    "smalltalk_weather", "ward", 0.62, None)

# 44. Quá xa thời gian history (>14 days)
add("Abstain_oos_history",
    [{"user": "Phường Hà Đông hôm qua thế nào?",
      "assistant": asst("historical_weather", "ward", 0.92,
                        "Phường Hà Đông hôm qua thời tiết thế nào?")}],
    "tháng 1 năm 2024 thì sao?",
    "smalltalk_weather", "ward", 0.62, None)

# 45. Off-topic (không phải thời tiết)
add("Abstain_off_topic",
    [{"user": "Phường Cầu Giấy hôm nay thế nào?",
      "assistant": asst("current_weather", "ward", 0.92,
                        "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}],
    "có nhà hàng nào ngon không?",
    "smalltalk_weather", "ward", 0.62, None)

# ═══════════════════════════════════════════════════════════════════════════
# E) TURN=3 chains (5)
# ═══════════════════════════════════════════════════════════════════════════

# 46. Rural xã 3-turn time
SAMPLES.append({
    "_kind": "Turn3_rural_xa",
    "history": [
        {"user": "Xã Minh Châu ngày mai thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.92,
                           "Dự báo Xã Minh Châu ngày mai thế nào?")},
        {"user": "ngày kia thì sao?",
         "assistant": asst("daily_forecast", "ward", 0.80,
                           "Dự báo Xã Minh Châu ngày kia thế nào?")}
    ],
    "input": "cuối tuần ra sao?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Dự báo Xã Minh Châu cuối tuần này thế nào?"}
})

# 47. City → ward → narrow time
SAMPLES.append({
    "_kind": "Turn3_city_to_ward",
    "history": [
        {"user": "Hà Nội hôm nay thế nào?",
         "assistant": asst("current_weather", "city", 0.85,
                           "Thời tiết Hà Nội hôm nay thế nào?")},
        {"user": "Phường Hoàn Kiếm cụ thể?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "buổi tối thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Hoàn Kiếm thời tiết thế nào?"}
})

# 48. Phường → Quận → another Phường (cross-collision)
SAMPLES.append({
    "_kind": "Turn3_collision_drill",
    "history": [
        {"user": "Phường Long Biên hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Long Biên hôm nay thế nào?")},
        {"user": "Quận Long Biên cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Long Biên có cảnh báo thời tiết không?")}
    ],
    "input": "Phường Bồ Đề cụ thể có ngập không?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Bồ Đề có nguy cơ ngập lụt không?"}
})

# 49. Time chain với historical → forecast (transition)
SAMPLES.append({
    "_kind": "Turn3_temporal_pivot",
    "history": [
        {"user": "Phường Tây Hồ tuần trước có mưa không?",
         "assistant": asst("historical_weather", "ward", 0.92,
                           "Phường Tây Hồ tuần trước có mưa không?")},
        {"user": "tuần này thì sao?",
         "assistant": asst("rain_query", "ward", 0.80,
                           "Phường Tây Hồ tuần này có mưa không?")}
    ],
    "input": "tuần sau dự báo có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Tây Hồ tuần sau có mưa không?"}
})

# 50. Comparison evolve through 3 turns
SAMPLES.append({
    "_kind": "Turn3_cmp_evolve",
    "history": [
        {"user": "So sánh Phường Cầu Giấy và Phường Hoàn Kiếm hôm nay",
         "assistant": asst("location_comparison", "ward", 0.92,
                           "So sánh thời tiết Phường Cầu Giấy và Phường Hoàn Kiếm hôm nay")},
        {"user": "đâu mát hơn?",
         "assistant": asst("temperature_query", "ward", 0.80,
                           "Phường Cầu Giấy và Phường Hoàn Kiếm hôm nay đâu mát hơn?")}
    ],
    "input": "ngày mai cũng vậy không?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai Phường Cầu Giấy và Phường Hoàn Kiếm đâu mát hơn?"}
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

out_path = Path(__file__).parent / 'batch_11_multiturn.jsonl'
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
