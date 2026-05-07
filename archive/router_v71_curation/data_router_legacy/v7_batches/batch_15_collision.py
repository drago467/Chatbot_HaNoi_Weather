"""V7 Batch 15 (Phase 5 batch 1 — collision counter-examples) — 40 samples.

Purpose:
1. Boost T4=0.74 confidence từ 1.1% lên ~12% (cần ~75 T4 samples).
2. Boost explicit-switch ratio từ 6.5% lên 30%+.
3. Cân bằng 28 collision cores: ward-version + district-version.

Composition:
- 20 T4 BARE-CORE single-turn ward default (10 urban + 9 rural + 1 Sơn Tây).
  Pattern: user gõ "Cầu Giấy hôm nay thế nào?" trần (no prefix) → router defaults
  Phường (urban) hoặc Xã (rural), confidence T4=0.74, rewrite uses default prefix.
- 5 T4 BARE-CORE district default (rural collision với intent strongly suggesting
  district scope: alert/comparison/seasonal).
- 10 EXPLICIT-SWITCH multi-turn (Phường→Quận, Quận→Phường, Xã→Huyện, Huyện→Xã).
- 5 EXPLICIT T1 contrast (clear ward vs clear district for same core).

Coverage này: 25/28 collision cores (3 còn lại — Chương Mỹ, Thạch Thất, Thanh Trì
— sẽ trong batch 16).
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

def s1(inp, intent, scope, conf, rew, kind="P5"):
    SAMPLES.append({
        "_kind": kind, "history": [], "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

def s2(prior_user, prior_intent, prior_scope, prior_rew, inp, intent, scope, conf, rew, kind="P5_mt"):
    SAMPLES.append({
        "_kind": kind,
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, prior_scope, 0.92, prior_rew)}],
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) T4 BARE-CORE WARD DEFAULT (20) — urban Phường + rural Xã
# ═══════════════════════════════════════════════════════════════════════════

# Urban collision: bare core → Phường (default post-merger primary)
s1("Ba Đình hôm nay thế nào?",
   "current_weather", "ward", 0.74,
   "Thời tiết Phường Ba Đình hôm nay thế nào?", kind="P5_T4_urban")

s1("Cầu Giấy ngày mai có mưa không?",
   "rain_query", "ward", 0.74,
   "Phường Cầu Giấy ngày mai có mưa không?", kind="P5_T4_urban")

s1("Đống Đa tối nay thế nào?",
   "hourly_forecast", "ward", 0.74,
   "Tối nay Phường Đống Đa thời tiết thế nào?", kind="P5_T4_urban")

s1("Hà Đông buổi sáng có sương không?",
   "humidity_fog_query", "ward", 0.74,
   "Phường Hà Đông buổi sáng có sương mù không?", kind="P5_T4_urban")

s1("Hai Bà Trưng nóng bao nhiêu độ?",
   "temperature_query", "ward", 0.74,
   "Phường Hai Bà Trưng hôm nay nóng bao nhiêu độ?", kind="P5_T4_urban")

s1("Hoàn Kiếm tuần này thế nào?",
   "daily_forecast", "ward", 0.74,
   "Phường Hoàn Kiếm tuần này thời tiết thế nào?", kind="P5_T4_urban")

s1("Hoàng Mai có gió mạnh không?",
   "wind_query", "ward", 0.74,
   "Phường Hoàng Mai có gió mạnh không?", kind="P5_T4_urban")

s1("Long Biên cuối tuần thế nào?",
   "daily_forecast", "ward", 0.74,
   "Phường Long Biên cuối tuần thời tiết thế nào?", kind="P5_T4_urban")

s1("Tây Hồ chiều nay có mưa không?",
   "rain_query", "ward", 0.74,
   "Chiều nay Phường Tây Hồ có mưa không?", kind="P5_T4_urban")

s1("Thanh Xuân hôm nay UV cao không?",
   "expert_weather_param", "ward", 0.74,
   "UV Phường Thanh Xuân hôm nay có cao không?", kind="P5_T4_urban")

# Special: Sơn Tây (Phường/Thị xã collision)
s1("Sơn Tây hôm nay thế nào?",
   "current_weather", "ward", 0.74,
   "Thời tiết Phường Sơn Tây hôm nay thế nào?", kind="P5_T4_thixa")

# Rural collision: bare core → Xã (default ward, post-merger primary)
s1("Ba Vì sáng nay có sương không?",
   "humidity_fog_query", "ward", 0.74,
   "Xã Ba Vì sáng nay có sương mù không?", kind="P5_T4_rural")

s1("Đan Phượng ngày mai dự báo thế nào?",
   "daily_forecast", "ward", 0.74,
   "Dự báo Xã Đan Phượng ngày mai thế nào?", kind="P5_T4_rural")

s1("Đông Anh hôm nay thế nào?",
   "current_weather", "ward", 0.74,
   "Thời tiết Xã Đông Anh hôm nay thế nào?", kind="P5_T4_rural")

s1("Gia Lâm tối nay nhiệt độ?",
   "temperature_query", "ward", 0.74,
   "Tối nay Xã Gia Lâm nhiệt độ bao nhiêu?", kind="P5_T4_rural")

s1("Hoài Đức cuối tuần có mưa không?",
   "rain_query", "ward", 0.74,
   "Xã Hoài Đức cuối tuần có mưa không?", kind="P5_T4_rural")

s1("Mê Linh tuần này gió thế nào?",
   "wind_query", "ward", 0.74,
   "Xã Mê Linh tuần này gió thế nào?", kind="P5_T4_rural")

s1("Mỹ Đức ngày mai mấy độ?",
   "temperature_query", "ward", 0.74,
   "Xã Mỹ Đức ngày mai nhiệt độ bao nhiêu?", kind="P5_T4_rural")

s1("Quốc Oai có thích hợp đi rừng không?",
   "activity_weather", "ward", 0.74,
   "Xã Quốc Oai hôm nay có thích hợp đi rừng không?", kind="P5_T4_rural")

s1("Phú Xuyên hôm qua thế nào?",
   "historical_weather", "ward", 0.74,
   "Xã Phú Xuyên hôm qua thời tiết thế nào?", kind="P5_T4_rural")

# ═══════════════════════════════════════════════════════════════════════════
# B) T4 BARE-CORE DISTRICT DEFAULT (5) — intent suggests district scope
# ═══════════════════════════════════════════════════════════════════════════

s1("Sóc Sơn có cảnh báo lũ không?",
   "weather_alert", "district", 0.74,
   "Huyện Sóc Sơn có cảnh báo lũ không?", kind="P5_T4_dist_alert")

s1("Phúc Thọ có cảnh báo gì không?",
   "weather_alert", "district", 0.74,
   "Huyện Phúc Thọ có cảnh báo thời tiết gì không?", kind="P5_T4_dist_alert")

s1("So sánh Thanh Oai với Mỹ Đức hôm nay",
   "location_comparison", "district", 0.74,
   "So sánh thời tiết Huyện Thanh Oai và Huyện Mỹ Đức hôm nay", kind="P5_T4_dist_cmp")

s1("Thường Tín mùa này thế nào?",
   "seasonal_context", "district", 0.74,
   "Thời tiết Huyện Thường Tín mùa này thế nào?", kind="P5_T4_dist_season")

s1("Ứng Hòa có nguy cơ ngập không?",
   "weather_alert", "district", 0.74,
   "Huyện Ứng Hòa có nguy cơ ngập lụt không?", kind="P5_T4_dist_alert")

# ═══════════════════════════════════════════════════════════════════════════
# C) EXPLICIT-SWITCH multi-turn (10) — Phường↔Quận, Xã↔Huyện
# ═══════════════════════════════════════════════════════════════════════════

s2("Phường Cầu Giấy hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Cầu Giấy hôm nay thế nào?",
   "Quận Cầu Giấy có cảnh báo gì không?",
   "weather_alert", "district", 0.85,
   "Quận Cầu Giấy có cảnh báo thời tiết gì không?", kind="P5_switch_w2d_urban")

s2("Phường Hoàn Kiếm hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?",
   "Quận Hoàn Kiếm tổng quan ra sao?",
   "weather_overview", "district", 0.85,
   "Tổng quan thời tiết Quận Hoàn Kiếm hôm nay", kind="P5_switch_w2d_urban")

s2("Phường Đống Đa hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Đống Đa hôm nay thế nào?",
   "Quận Đống Đa cụ thể có nóng không?",
   "temperature_query", "district", 0.85,
   "Quận Đống Đa hôm nay có nóng không?", kind="P5_switch_w2d_urban")

s2("Phường Long Biên hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Long Biên hôm nay thế nào?",
   "Quận Long Biên có ngập không?",
   "weather_alert", "district", 0.85,
   "Quận Long Biên có nguy cơ ngập lụt không?", kind="P5_switch_w2d_urban")

s2("Phường Hoàng Mai hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
   "Quận Hoàng Mai gió thế nào?",
   "wind_query", "district", 0.85,
   "Quận Hoàng Mai hiện tại gió thế nào?", kind="P5_switch_w2d_urban")

s2("Quận Hà Đông hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Quận Hà Đông hôm nay thế nào?",
   "Phường Hà Đông cụ thể nhiệt độ?",
   "temperature_query", "ward", 0.85,
   "Phường Hà Đông cụ thể nhiệt độ hiện tại bao nhiêu?", kind="P5_switch_d2w_urban")

s2("Quận Tây Hồ hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Quận Tây Hồ hôm nay thế nào?",
   "Phường Tây Hồ cụ thể có sương không?",
   "humidity_fog_query", "ward", 0.85,
   "Phường Tây Hồ có sương mù không?", kind="P5_switch_d2w_urban")

s2("Xã Mỹ Đức hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Xã Mỹ Đức hôm nay thế nào?",
   "Huyện Mỹ Đức nói chung ra sao?",
   "weather_overview", "district", 0.85,
   "Tổng quan thời tiết Huyện Mỹ Đức hôm nay", kind="P5_switch_xa2huyen_rural")

s2("Xã Đông Anh hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Xã Đông Anh hôm nay thế nào?",
   "Huyện Đông Anh có cảnh báo gì không?",
   "weather_alert", "district", 0.85,
   "Huyện Đông Anh có cảnh báo thời tiết gì không?", kind="P5_switch_xa2huyen_rural")

s2("Huyện Sóc Sơn hôm nay thế nào?", "current_weather", "district",
   "Thời tiết Huyện Sóc Sơn hôm nay thế nào?",
   "Xã Sóc Sơn cụ thể có mưa không?",
   "rain_query", "ward", 0.85,
   "Xã Sóc Sơn cụ thể có mưa không?", kind="P5_switch_huyen2xa_rural")

# ═══════════════════════════════════════════════════════════════════════════
# D) EXPLICIT T1 contrast (5) — clear ward + clear district pairs
# ═══════════════════════════════════════════════════════════════════════════

s1("Phường Cầu Giấy hôm nay nhiệt độ chính xác bao nhiêu?",
   "temperature_query", "ward", 0.92,
   "Nhiệt độ Phường Cầu Giấy hôm nay chính xác bao nhiêu?", kind="P5_T1_explicit_ward")

s1("Quận Cầu Giấy tổng quan tuần này",
   "weather_overview", "district", 0.92,
   "Tổng quan thời tiết Quận Cầu Giấy tuần này", kind="P5_T1_explicit_dist")

s1("Xã Mỹ Đức ngày mai có mưa không?",
   "rain_query", "ward", 0.92,
   "Ngày mai Xã Mỹ Đức có mưa không?", kind="P5_T1_explicit_xa")

s1("Huyện Mỹ Đức tuần này có cảnh báo lũ không?",
   "weather_alert", "district", 0.92,
   "Huyện Mỹ Đức tuần này có cảnh báo lũ không?", kind="P5_T1_explicit_huyen")

s1("Thị xã Sơn Tây tuần sau dự báo thế nào?",
   "daily_forecast", "district", 0.92,
   "Thị xã Sơn Tây tuần sau dự báo thế nào?", kind="P5_T1_explicit_thixa")

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

out_path = Path(__file__).parent / 'batch_15_collision.jsonl'
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
