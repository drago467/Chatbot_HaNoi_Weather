"""V7 Batch 14 (Phase 3 batch 2 — final pure-ward) — 50 samples.

Purpose: fill intent gaps (location_comparison 3.6% và smalltalk_weather 4.3%
đang underrepresented). Mix T1/T2/T3 để giữ tier balance push.

Composition:
- 15 LOCATION_COMPARISON (turn=1 + turn=2): 2-way & 3-way comparisons,
  mix ward-ward, district-district, ward-district, city-ward.
- 8 SMALLTALK_WEATHER variety (mặc gì, mang ô, hoạt động cụ thể).
- 7 WEATHER_ALERT variety (giông, ngập, sương dày, mưa lớn).
- 5 ACTIVITY_WEATHER (chạy bộ, dắt chó, đi học, đi làm, picnic).
- 8 EXPERT_WEATHER_PARAM (UV, áp suất, tầm nhìn, cảm giác nhiệt) +
  HUMIDITY_FOG_QUERY (sương sớm, nồm, độ ẩm).
- 7 multi-turn pure-ward T3 inheritance edge cases.
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

def s1(inp, intent, scope, conf, rew, kind="P2"):
    """Single-turn (history=[])."""
    SAMPLES.append({
        "_kind": kind, "history": [], "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

def s2(prior_user, prior_intent, prior_scope, prior_rew, inp, intent, scope, conf, rew, kind="P2_mt"):
    """Multi-turn (history=1 entry)."""
    SAMPLES.append({
        "_kind": kind,
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, prior_scope, 0.92, prior_rew)}],
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) LOCATION_COMPARISON (15) — push intent gap
# ═══════════════════════════════════════════════════════════════════════════

# 2-way ward-ward
s1("So sánh Phường Cầu Giấy và Phường Tây Hồ hôm nay đâu mát hơn?",
   "location_comparison", "ward", 0.92,
   "So sánh Phường Cầu Giấy và Phường Tây Hồ hôm nay đâu mát hơn?", kind="P2_cmp_w2w")

s1("Phường Hà Đông với Phường Hoàng Mai, đâu có mưa nhiều hơn?",
   "location_comparison", "ward", 0.92,
   "So sánh lượng mưa Phường Hà Đông và Phường Hoàng Mai hôm nay", kind="P2_cmp_w2w")

s1("So sánh Phường Long Biên và Phường Bồ Đề về độ ẩm",
   "location_comparison", "ward", 0.92,
   "So sánh độ ẩm Phường Long Biên và Phường Bồ Đề hiện tại", kind="P2_cmp_w2w")

s1("Phường Yên Nghĩa với Phường Yên Hòa, đâu gió mạnh hơn?",
   "location_comparison", "ward", 0.92,
   "So sánh tốc độ gió Phường Yên Nghĩa và Phường Yên Hòa hôm nay", kind="P2_cmp_w2w")

# District-district
s1("So sánh Huyện Sóc Sơn và Huyện Đông Anh hôm nay",
   "location_comparison", "district", 0.92,
   "So sánh thời tiết Huyện Sóc Sơn và Huyện Đông Anh hôm nay", kind="P2_cmp_d2d")

s1("Quận Cầu Giấy với Quận Hoàn Kiếm, đâu nóng hơn?",
   "location_comparison", "district", 0.92,
   "So sánh nhiệt độ Quận Cầu Giấy và Quận Hoàn Kiếm hôm nay", kind="P2_cmp_d2d")

s1("Huyện Mê Linh với Huyện Đan Phượng đâu có mưa nhiều?",
   "location_comparison", "district", 0.92,
   "So sánh lượng mưa Huyện Mê Linh và Huyện Đan Phượng hôm nay", kind="P2_cmp_d2d")

# Ward vs district (cross-scope, scope=district as broader)
s1("Phường Cầu Giấy so với Quận Đống Đa khác nhau ra sao?",
   "location_comparison", "district", 0.92,
   "So sánh thời tiết Phường Cầu Giấy và Quận Đống Đa hôm nay", kind="P2_cmp_w2d")

# City vs ward
s1("Hà Nội nói chung và Phường Tây Hồ có khác nhau không?",
   "location_comparison", "city", 0.92,
   "So sánh thời tiết Hà Nội nói chung và Phường Tây Hồ hôm nay", kind="P2_cmp_city2w")

# 3-way comparison
s1("So sánh Phường Cầu Giấy, Phường Long Biên và Phường Hoàng Mai",
   "location_comparison", "ward", 0.92,
   "So sánh thời tiết Phường Cầu Giấy, Phường Long Biên và Phường Hoàng Mai hôm nay",
   kind="P2_cmp_3way")

s1("Quận Hà Đông, Quận Đống Đa và Quận Tây Hồ hôm nay đâu mát nhất?",
   "location_comparison", "district", 0.92,
   "So sánh độ mát Quận Hà Đông, Quận Đống Đa và Quận Tây Hồ hôm nay",
   kind="P2_cmp_3way")

# Xã-Phường mixed (pure-ward comparison across types)
s1("Xã Minh Châu so với Phường Cầu Giấy hôm nay đâu lạnh hơn?",
   "location_comparison", "ward", 0.92,
   "So sánh nhiệt độ Xã Minh Châu và Phường Cầu Giấy hôm nay", kind="P2_cmp_xa2phuong")

s1("Xã Yên Lãng và Xã Quốc Oai đâu mưa nhiều hơn?",
   "location_comparison", "ward", 0.92,
   "So sánh lượng mưa Xã Yên Lãng và Xã Quốc Oai hôm nay", kind="P2_cmp_xa2xa")

# Time-specific comparison
s1("Ngày mai Phường Tây Hồ với Phường Phú Thượng đâu có mưa?",
   "location_comparison", "ward", 0.92,
   "Ngày mai so sánh Phường Tây Hồ và Phường Phú Thượng đâu có mưa hơn?",
   kind="P2_cmp_time")

s1("Hôm qua Quận Hà Đông và Quận Hoàng Mai đâu nóng hơn?",
   "location_comparison", "district", 0.92,
   "Hôm qua Quận Hà Đông và Quận Hoàng Mai đâu nóng hơn?", kind="P2_cmp_hist")

# ═══════════════════════════════════════════════════════════════════════════
# B) SMALLTALK_WEATHER variety (8) — fill gap
# ═══════════════════════════════════════════════════════════════════════════

s1("Hôm nay ở Phường Cầu Giấy có cần mặc ấm không?",
   "smalltalk_weather", "ward", 0.92,
   "Hôm nay Phường Cầu Giấy có cần mặc ấm không?", kind="P2_sk_clothing")

s1("Đi làm Quận Đống Đa hôm nay có cần mang ô không?",
   "smalltalk_weather", "district", 0.92,
   "Hôm nay Quận Đống Đa có cần mang ô khi đi làm không?", kind="P2_sk_umbrella")

s1("Trẻ em Phường Hoàng Mai có nên mặc áo khoác đi học không?",
   "smalltalk_weather", "ward", 0.92,
   "Hôm nay Phường Hoàng Mai trẻ em có nên mặc áo khoác đi học không?", kind="P2_sk_kids")

s1("Tối nay Phường Tây Hồ có lạnh không nhỉ?",
   "smalltalk_weather", "ward", 0.92,
   "Tối nay Phường Tây Hồ có lạnh không?", kind="P2_sk_general")

s1("Phường Bồ Đề trời thế này có nên đi xe máy không?",
   "smalltalk_weather", "ward", 0.92,
   "Hôm nay Phường Bồ Đề có nên đi xe máy không?", kind="P2_sk_transport")

s1("Cuối tuần Hà Nội có thích hợp đi chợ Tết không?",
   "smalltalk_weather", "city", 0.92,
   "Cuối tuần Hà Nội thời tiết có thích hợp đi chợ Tết không?", kind="P2_sk_event")

s1("Phường Long Biên hôm nay có nên đi du lịch không?",
   "smalltalk_weather", "ward", 0.92,
   "Hôm nay Phường Long Biên thời tiết có thích hợp đi du lịch không?", kind="P2_sk_travel")

s1("Mưa thế này ở Phường Hà Đông có nên ra ngoài không?",
   "smalltalk_weather", "ward", 0.92,
   "Hôm nay Phường Hà Đông mưa, có nên ra ngoài không?", kind="P2_sk_safety")

# ═══════════════════════════════════════════════════════════════════════════
# C) WEATHER_ALERT variety (7)
# ═══════════════════════════════════════════════════════════════════════════

s1("Phường Hoàng Mai có nguy cơ ngập do mưa lớn không?",
   "weather_alert", "ward", 0.92,
   "Phường Hoàng Mai có nguy cơ ngập do mưa lớn không?", kind="P2_alert_flood")

s1("Hà Nội tuần này có cảnh báo giông bão không?",
   "weather_alert", "city", 0.92,
   "Hà Nội tuần này có cảnh báo giông bão không?", kind="P2_alert_storm")

s1("Quận Long Biên có cảnh báo gió giật mạnh không?",
   "weather_alert", "district", 0.92,
   "Quận Long Biên có cảnh báo gió giật mạnh không?", kind="P2_alert_wind")

s1("Sáng nay Huyện Sóc Sơn có sương mù dày đặc không?",
   "weather_alert", "district", 0.92,
   "Sáng nay Huyện Sóc Sơn có sương mù dày đặc không?", kind="P2_alert_fog")

s1("Phường Yên Nghĩa có cảnh báo nồm ẩm không?",
   "weather_alert", "ward", 0.92,
   "Phường Yên Nghĩa có cảnh báo nồm ẩm không?", kind="P2_alert_humid")

s1("Huyện Ba Vì có cảnh báo lũ quét không?",
   "weather_alert", "district", 0.92,
   "Huyện Ba Vì có cảnh báo lũ quét không?", kind="P2_alert_flash")

s1("Tuần này Hà Nội có cảnh báo rét đậm rét hại không?",
   "weather_alert", "city", 0.92,
   "Tuần này Hà Nội có cảnh báo rét đậm rét hại không?", kind="P2_alert_cold")

# ═══════════════════════════════════════════════════════════════════════════
# D) ACTIVITY_WEATHER (5)
# ═══════════════════════════════════════════════════════════════════════════

s1("Sáng nay Phường Cầu Giấy có thích hợp chạy bộ không?",
   "activity_weather", "ward", 0.92,
   "Sáng nay Phường Cầu Giấy có thích hợp chạy bộ không?", kind="P2_act_run")

s1("Tối nay Phường Tây Hồ có thích hợp dắt chó đi dạo không?",
   "activity_weather", "ward", 0.92,
   "Tối nay Phường Tây Hồ có thích hợp dắt chó đi dạo không?", kind="P2_act_pet")

s1("Cuối tuần ở Phường Long Biên có thích hợp đi picnic không?",
   "activity_weather", "ward", 0.92,
   "Cuối tuần Phường Long Biên có thích hợp đi picnic không?", kind="P2_act_picnic")

s1("Quận Đống Đa hôm nay có thích hợp đi xe đạp không?",
   "activity_weather", "district", 0.92,
   "Quận Đống Đa hôm nay có thích hợp đi xe đạp không?", kind="P2_act_cycle")

s1("Phường Hà Đông có thích hợp tổ chức tiệc ngoài trời không?",
   "activity_weather", "ward", 0.92,
   "Phường Hà Đông hôm nay có thích hợp tổ chức tiệc ngoài trời không?", kind="P2_act_party")

# ═══════════════════════════════════════════════════════════════════════════
# E) EXPERT_WEATHER_PARAM + HUMIDITY_FOG_QUERY (8)
# ═══════════════════════════════════════════════════════════════════════════

s1("Áp suất khí quyển ở Phường Hoàn Kiếm hiện tại bao nhiêu?",
   "expert_weather_param", "ward", 0.92,
   "Áp suất khí quyển Phường Hoàn Kiếm hiện tại bao nhiêu?", kind="P2_exp_pressure")

s1("Tầm nhìn xa ở Quận Tây Hồ hôm nay khoảng bao nhiêu km?",
   "expert_weather_param", "district", 0.92,
   "Tầm nhìn xa Quận Tây Hồ hôm nay khoảng bao nhiêu km?", kind="P2_exp_visibility")

s1("Nhiệt độ cảm giác ở Phường Cầu Giấy hôm nay bao nhiêu?",
   "expert_weather_param", "ward", 0.92,
   "Nhiệt độ cảm giác Phường Cầu Giấy hôm nay bao nhiêu?", kind="P2_exp_feels")

s1("Điểm sương ở Phường Hà Đông hôm nay là bao nhiêu?",
   "expert_weather_param", "ward", 0.92,
   "Điểm sương Phường Hà Đông hôm nay là bao nhiêu?", kind="P2_exp_dewpoint")

s1("Phường Định Công sáng nay có sương mù dày không?",
   "humidity_fog_query", "ward", 0.92,
   "Phường Định Công sáng nay có sương mù dày không?", kind="P2_humid_fog")

s1("Độ ẩm Phường Văn Miếu - Quốc Tử Giám hiện tại bao nhiêu phần trăm?",
   "humidity_fog_query", "ward", 0.92,
   "Độ ẩm Phường Văn Miếu - Quốc Tử Giám hiện tại bao nhiêu phần trăm?", kind="P2_humid_pct")

s1("Hà Nội tuần này có nồm ẩm kéo dài không?",
   "humidity_fog_query", "city", 0.92,
   "Hà Nội tuần này có nồm ẩm kéo dài không?", kind="P2_humid_nom")

s1("Huyện Sóc Sơn rạng sáng có sương mù không?",
   "humidity_fog_query", "district", 0.92,
   "Huyện Sóc Sơn rạng sáng có sương mù không?", kind="P2_humid_dawn")

# ═══════════════════════════════════════════════════════════════════════════
# F) Multi-turn T3 pure-ward edge cases (7)
# ═══════════════════════════════════════════════════════════════════════════

s2("Phường Yên Nghĩa hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Yên Nghĩa hôm nay thế nào?",
   "ngày kia có mưa không?", "rain_query", "ward", 0.80,
   "Phường Yên Nghĩa ngày kia có mưa không?", kind="P2_mt_xa")

s2("Phường Bồ Đề tuần sau dự báo thế nào?", "daily_forecast", "ward",
   "Phường Bồ Đề tuần sau dự báo thế nào?",
   "thứ 7 cuối tuần thì sao?", "daily_forecast", "ward", 0.80,
   "Phường Bồ Đề thứ 7 cuối tuần sau thế nào?", kind="P2_mt_time")

s2("Phường Tây Mỗ hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Tây Mỗ hôm nay thế nào?",
   "có thích hợp đi siêu thị không?", "smalltalk_weather", "ward", 0.80,
   "Phường Tây Mỗ hôm nay có thích hợp đi siêu thị không?", kind="P2_mt_act")

s2("Xã Minh Châu hôm qua thế nào?", "historical_weather", "ward",
   "Xã Minh Châu hôm qua thời tiết thế nào?",
   "tuần trước nói chung?", "historical_weather", "ward", 0.80,
   "Xã Minh Châu tuần trước nói chung thời tiết thế nào?", kind="P2_mt_hist")

s2("Phường Định Công hôm nay UV bao nhiêu?", "expert_weather_param", "ward",
   "UV Phường Định Công hôm nay bao nhiêu?",
   "đỉnh điểm lúc mấy giờ?", "expert_weather_param", "ward", 0.80,
   "UV Phường Định Công hôm nay đỉnh điểm lúc mấy giờ?", kind="P2_mt_exp")

s2("Phường Phú Lương hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Phú Lương hôm nay thế nào?",
   "có cảnh báo nồm không?", "weather_alert", "ward", 0.80,
   "Phường Phú Lương có cảnh báo nồm ẩm không?", kind="P2_mt_alert")

s2("Phường Đại Mỗ tổng quan tuần này", "weather_overview", "ward",
   "Tổng quan thời tiết Phường Đại Mỗ tuần này",
   "ngày nào nóng nhất?", "temperature_query", "ward", 0.80,
   "Phường Đại Mỗ tuần này ngày nào nóng nhất?", kind="P2_mt_specific")

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

out_path = Path(__file__).parent / 'batch_14_pureward.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for sample in SAMPLES:
        clean = {k: v for k, v in sample.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')

from collections import Counter
turns = Counter(len(s['history']) + 1 for s in SAMPLES)
scopes = Counter(s['output']['scope'] for s in SAMPLES)
confs = Counter(s['output']['confidence'] for s in SAMPLES)
intents = Counter(s['output']['intent'] for s in SAMPLES)
print(f'Turn distribution: {dict(turns)}')
print(f'Scope distribution: {dict(scopes)}')
print(f'Confidence distribution: {dict(confs)}')
print(f'Intent distribution:')
for i in sorted(intents):
    print(f'  {i}: {intents[i]}')
