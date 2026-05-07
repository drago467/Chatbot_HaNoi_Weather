"""V7 Batch 16 (Phase 5 batch 2 — FINAL collision counter-examples) — 40 samples.

Purpose: hoàn thiện coverage 28 collision cores + final T4 boost + final
explicit-switch boost.

Composition:
- 6 EXPLICIT T1 cho 3 cores còn lại (Chương Mỹ, Thạch Thất, Thanh Trì): mỗi core
  có ward-version + district-version T1 contrast.
- 3 T4 BARE-CORE cho 3 cores này (default decision).
- 17 T4 BARE-CORE variations cho 28 cores (mở rộng intent + thời gian + ngữ cảnh).
- 10 EXPLICIT-SWITCH multi-turn (urban + rural + reverse direction).
- 4 MISC edge cases: turn=3 switch chain, intent-shift after switch,
  bare→explicit refinement, switch + time advance.
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

def s1(inp, intent, scope, conf, rew, kind="P5b"):
    SAMPLES.append({
        "_kind": kind, "history": [], "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

def s2(prior_user, prior_intent, prior_scope, prior_rew, inp, intent, scope, conf, rew, kind="P5b_mt"):
    SAMPLES.append({
        "_kind": kind,
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, prior_scope, 0.92, prior_rew)}],
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) 3 collision cores còn lại × 2 versions (T1 explicit) + 3 T4 bare-core
# ═══════════════════════════════════════════════════════════════════════════

# Phường Chương Mỹ (only phường in Huyện Chương Mỹ — special collision)
s1("Phường Chương Mỹ hôm nay nhiệt độ bao nhiêu?",
   "temperature_query", "ward", 0.92,
   "Nhiệt độ Phường Chương Mỹ hôm nay bao nhiêu?", kind="P5b_T1_w_chuongmy")

s1("Huyện Chương Mỹ tuần này có cảnh báo gì không?",
   "weather_alert", "district", 0.92,
   "Huyện Chương Mỹ tuần này có cảnh báo thời tiết gì không?", kind="P5b_T1_d_chuongmy")

# Xã Thạch Thất + Huyện Thạch Thất
s1("Xã Thạch Thất hôm nay có mưa không?",
   "rain_query", "ward", 0.92,
   "Xã Thạch Thất hôm nay có mưa không?", kind="P5b_T1_xa_thachthat")

s1("Huyện Thạch Thất tổng quan tuần này",
   "weather_overview", "district", 0.92,
   "Tổng quan thời tiết Huyện Thạch Thất tuần này", kind="P5b_T1_h_thachthat")

# Xã Thanh Trì + Huyện Thanh Trì
s1("Xã Thanh Trì có gió mạnh không?",
   "wind_query", "ward", 0.92,
   "Xã Thanh Trì có gió mạnh không?", kind="P5b_T1_xa_thanhtri")

s1("Huyện Thanh Trì có nguy cơ ngập không?",
   "weather_alert", "district", 0.92,
   "Huyện Thanh Trì có nguy cơ ngập lụt không?", kind="P5b_T1_h_thanhtri")

# T4 bare-core cho 3 cores này
s1("Chương Mỹ ngày mai thế nào?",
   "daily_forecast", "ward", 0.74,
   "Phường Chương Mỹ ngày mai dự báo thế nào?", kind="P5b_T4_bare_chuongmy")

s1("Thạch Thất hôm nay có nóng không?",
   "temperature_query", "ward", 0.74,
   "Xã Thạch Thất hôm nay có nóng không?", kind="P5b_T4_bare_thachthat")

s1("Thanh Trì có cảnh báo lũ không?",
   "weather_alert", "district", 0.74,
   "Huyện Thanh Trì có cảnh báo lũ không?", kind="P5b_T4_bare_thanhtri")

# ═══════════════════════════════════════════════════════════════════════════
# B) 17 T4 bare-core variations (urban + rural + district-default)
# ═══════════════════════════════════════════════════════════════════════════

# Urban T4 variations (more intents/times)
s1("Cầu Giấy buổi tối thế nào?",
   "hourly_forecast", "ward", 0.74,
   "Buổi tối Phường Cầu Giấy thời tiết thế nào?", kind="P5b_T4_var_urban")

s1("Hoàn Kiếm có thích hợp đi bộ buổi sáng không?",
   "activity_weather", "ward", 0.74,
   "Phường Hoàn Kiếm buổi sáng có thích hợp đi bộ không?", kind="P5b_T4_var_urban")

s1("Hà Đông sáng mai có sương dày không?",
   "humidity_fog_query", "ward", 0.74,
   "Phường Hà Đông sáng mai có sương dày không?", kind="P5b_T4_var_urban")

s1("Hoàng Mai tuần này dự báo ra sao?",
   "daily_forecast", "ward", 0.74,
   "Phường Hoàng Mai tuần này dự báo thế nào?", kind="P5b_T4_var_urban")

s1("Long Biên có cảnh báo bão không?",
   "weather_alert", "ward", 0.74,
   "Phường Long Biên có cảnh báo bão không?", kind="P5b_T4_var_urban")

s1("Tây Hồ tổng quan ngày mai",
   "weather_overview", "ward", 0.74,
   "Tổng quan thời tiết Phường Tây Hồ ngày mai", kind="P5b_T4_var_urban")

s1("Đống Đa nhiệt độ chiều nay bao nhiêu?",
   "temperature_query", "ward", 0.74,
   "Chiều nay Phường Đống Đa nhiệt độ bao nhiêu?", kind="P5b_T4_var_urban")

s1("Thanh Xuân tuần này có nồm không?",
   "humidity_fog_query", "ward", 0.74,
   "Phường Thanh Xuân tuần này có nồm ẩm không?", kind="P5b_T4_var_urban")

s1("Hai Bà Trưng hôm qua mưa không?",
   "historical_weather", "ward", 0.74,
   "Hôm qua Phường Hai Bà Trưng có mưa không?", kind="P5b_T4_var_urban")

s1("Ba Đình so với hôm qua thế nào?",
   "seasonal_context", "ward", 0.74,
   "Phường Ba Đình hôm nay so với hôm qua thế nào?", kind="P5b_T4_var_urban")

# Rural T4 variations
s1("Đan Phượng buổi sáng có sương không?",
   "humidity_fog_query", "ward", 0.74,
   "Xã Đan Phượng buổi sáng có sương mù không?", kind="P5b_T4_var_rural")

s1("Gia Lâm có thích hợp đi chợ không?",
   "activity_weather", "ward", 0.74,
   "Xã Gia Lâm hôm nay có thích hợp đi chợ không?", kind="P5b_T4_var_rural")

s1("Hoài Đức tuần này có gió mạnh không?",
   "wind_query", "ward", 0.74,
   "Xã Hoài Đức tuần này có gió mạnh không?", kind="P5b_T4_var_rural")

s1("Đông Anh chiều nay thế nào?",
   "hourly_forecast", "ward", 0.74,
   "Chiều nay Xã Đông Anh thời tiết thế nào?", kind="P5b_T4_var_rural")

s1("Quốc Oai cuối tuần có thích hợp đi rừng không?",
   "activity_weather", "ward", 0.74,
   "Xã Quốc Oai cuối tuần có thích hợp đi rừng không?", kind="P5b_T4_var_rural")

# District-default T4 variations
s1("So sánh Sóc Sơn với Đông Anh hôm nay",
   "location_comparison", "district", 0.74,
   "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh hôm nay", kind="P5b_T4_var_dist")

s1("Phú Xuyên có nguy cơ ngập không?",
   "weather_alert", "district", 0.74,
   "Huyện Phú Xuyên có nguy cơ ngập lụt không?", kind="P5b_T4_var_dist")

# ═══════════════════════════════════════════════════════════════════════════
# C) 10 EXPLICIT-SWITCH multi-turn (additional cores + reverse direction)
# ═══════════════════════════════════════════════════════════════════════════

s2("Phường Hai Bà Trưng hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?",
   "Quận Hai Bà Trưng có cảnh báo gì không?",
   "weather_alert", "district", 0.85,
   "Quận Hai Bà Trưng có cảnh báo thời tiết gì không?", kind="P5b_switch_w2d")

s2("Phường Tây Hồ hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Tây Hồ hôm nay thế nào?",
   "Quận Tây Hồ tuần này có nóng không?",
   "temperature_query", "district", 0.85,
   "Quận Tây Hồ tuần này có nóng không?", kind="P5b_switch_w2d")

s2("Phường Ba Đình hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Ba Đình hôm nay thế nào?",
   "Quận Ba Đình tổng quan ngày mai?",
   "weather_overview", "district", 0.85,
   "Tổng quan thời tiết Quận Ba Đình ngày mai", kind="P5b_switch_w2d")

s2("Phường Thanh Xuân hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
   "Quận Thanh Xuân có ngập không?",
   "weather_alert", "district", 0.85,
   "Quận Thanh Xuân có nguy cơ ngập lụt không?", kind="P5b_switch_w2d")

s2("Quận Long Biên hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Quận Long Biên hôm nay thế nào?",
   "Phường Long Biên cụ thể có mưa không?",
   "rain_query", "ward", 0.85,
   "Phường Long Biên cụ thể có mưa không?", kind="P5b_switch_d2w")

s2("Quận Hoàng Mai hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Quận Hoàng Mai hôm nay thế nào?",
   "Phường Hoàng Mai cụ thể nhiệt độ bao nhiêu?",
   "temperature_query", "ward", 0.85,
   "Phường Hoàng Mai cụ thể nhiệt độ hiện tại bao nhiêu?", kind="P5b_switch_d2w")

s2("Xã Quốc Oai hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Xã Quốc Oai hôm nay thế nào?",
   "Huyện Quốc Oai nói chung có cảnh báo gì không?",
   "weather_alert", "district", 0.85,
   "Huyện Quốc Oai có cảnh báo thời tiết gì không?", kind="P5b_switch_xa2h")

s2("Xã Hoài Đức hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Xã Hoài Đức hôm nay thế nào?",
   "Huyện Hoài Đức tuần này dự báo ra sao?",
   "daily_forecast", "district", 0.85,
   "Huyện Hoài Đức tuần này dự báo thế nào?", kind="P5b_switch_xa2h")

s2("Huyện Mê Linh hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Huyện Mê Linh hôm nay thế nào?",
   "Xã Mê Linh cụ thể có gió không?",
   "wind_query", "ward", 0.85,
   "Xã Mê Linh cụ thể có gió không?", kind="P5b_switch_h2xa")

s2("Huyện Phú Xuyên hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Huyện Phú Xuyên hôm nay thế nào?",
   "Xã Phú Xuyên cụ thể có mưa không?",
   "rain_query", "ward", 0.85,
   "Xã Phú Xuyên cụ thể có mưa không?", kind="P5b_switch_h2xa")

# ═══════════════════════════════════════════════════════════════════════════
# D) 4 MISC edge cases
# ═══════════════════════════════════════════════════════════════════════════

# 37. TURN=3 explicit-switch chain: Phường → Quận → another Phường (different ward)
SAMPLES.append({
    "_kind": "P5b_misc_turn3_switch",
    "history": [
        {"user": "Phường Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.92,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")},
        {"user": "Quận Cầu Giấy có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Quận Cầu Giấy có cảnh báo thời tiết gì không?")}
    ],
    "input": "Phường Yên Hòa cụ thể thì sao?",
    "output": {"intent": "weather_alert", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Phường Yên Hòa có cảnh báo thời tiết gì không?"}
})

# 38. Intent-shift after switch: alert → smalltalk recommendation
s2("Phường Hoàng Mai có cảnh báo bão không?", "weather_alert", "ward",
   "Phường Hoàng Mai có cảnh báo bão không?",
   "Quận Hoàng Mai có nên đi học không?",
   "smalltalk_weather", "district", 0.85,
   "Hôm nay Quận Hoàng Mai có nên đi học không?", kind="P5b_misc_intent_shift_switch")

# 39. Bare core → explicit refinement (turn 1 ambiguous, turn 2 explicit confirm)
s2("Cầu Giấy hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Cầu Giấy hôm nay thế nào?",
   "ý mình là Quận Cầu Giấy nói chung",
   "weather_overview", "district", 0.85,
   "Tổng quan thời tiết Quận Cầu Giấy hôm nay", kind="P5b_misc_bare_to_explicit")

# 40. Switch + time advance combined
s2("Phường Long Biên hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Long Biên hôm nay thế nào?",
   "Quận Long Biên ngày mai có cảnh báo gì không?",
   "weather_alert", "district", 0.85,
   "Quận Long Biên ngày mai có cảnh báo thời tiết gì không?", kind="P5b_misc_switch_time")

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
for sample in SAMPLES:
    k = sample.get('_kind', 'unknown')
    kinds[k] = kinds.get(k, 0) + 1
print('By kind:')
for k in sorted(kinds):
    print(f'  {k}: {kinds[k]}')

total_errs = 0
for i, sample in enumerate(SAMPLES):
    errs = validate(sample)
    if errs:
        print(f'  [SAMPLE {i}] {errs}')
        total_errs += 1
print(f'Validation errors: {total_errs}')
if total_errs > 0:
    sys.exit(1)

out_path = Path(__file__).parent / 'batch_16_collision.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for sample in SAMPLES:
        clean = {k: v for k, v in sample.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')

from collections import Counter
turns = Counter(len(s['history']) + 1 for s in SAMPLES)
scopes = Counter(s['output']['scope'] for s in SAMPLES)
confs = Counter(s['output']['confidence'] for s in SAMPLES)
print(f'Turn distribution: {dict(turns)}')
print(f'Scope distribution: {dict(scopes)}')
print(f'Confidence distribution: {dict(confs)}')
