"""V7 Batch 13 (Phase 3 — pure-ward & balance) — 50 samples.

Purpose: balance tier T1/T2 distribution (currently T3 over 70%, target T1+T2 ≈ 56%).
Strategy: mostly turn=1 single-turn direct queries với explicit prefix. T1=0.92 cho
unambiguous queries (full info), T2=0.85 cho cases có 1 default (vd time hôm nay
implicit, hoặc city default).

Composition:
- 10 CITY-level (Hà Nội explicit) — push city scope mass.
- 18 DISTRICT-level explicit "Quận X" / "Huyện X" / "Thị xã X" — gồm 11 districts
  chưa mention full-name: Huyện Chương Mỹ, Hoài Đức, Phú Xuyên, Phúc Thọ, Quốc Oai,
  Thanh Oai, Thường Tín, Thạch Thất, Ứng Hòa, Quận Bắc Từ Liêm, Quận Thanh Xuân.
- 22 WARD-level explicit "Phường X" / "Xã X" — mix pure-ward (T1 unambiguous);
  bao gồm Xã Gia Lâm (missing 1 ward).
"""
import json, sys
from pathlib import Path

SAMPLES = []

def s(inp, intent, scope, conf, rew, hist=None, kind="P_pure"):
    SAMPLES.append({
        "_kind": kind,
        "history": hist if hist is not None else [],
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) CITY-level (10) — Hà Nội explicit, push city scope mass
# ═══════════════════════════════════════════════════════════════════════════

s("Hà Nội hôm nay nhiệt độ bao nhiêu?",
  "temperature_query", "city", 0.92,
  "Nhiệt độ Hà Nội hôm nay bao nhiêu?", kind="P_city")

s("Thời tiết Hà Nội ngày mai thế nào?",
  "daily_forecast", "city", 0.92,
  "Dự báo thời tiết Hà Nội ngày mai thế nào?", kind="P_city")

s("Hà Nội tuần này mưa nhiều không?",
  "rain_query", "city", 0.92,
  "Hà Nội tuần này có mưa nhiều không?", kind="P_city")

s("Trời Hà Nội hôm nay có gió không?",
  "wind_query", "city", 0.92,
  "Hà Nội hôm nay có gió không?", kind="P_city")

s("Hà Nội có cảnh báo bão không?",
  "weather_alert", "city", 0.92,
  "Hà Nội có cảnh báo bão không?", kind="P_city")

s("Mùa này Hà Nội thế nào?",
  "seasonal_context", "city", 0.92,
  "Thời tiết Hà Nội mùa này thế nào?", kind="P_city")

s("Hôm qua Hà Nội mưa không?",
  "historical_weather", "city", 0.92,
  "Hôm qua Hà Nội có mưa không?", kind="P_city")

s("Buổi tối Hà Nội thế nào?",
  "hourly_forecast", "city", 0.85,
  "Buổi tối hôm nay Hà Nội thời tiết thế nào?", kind="P_city")

s("Cuối tuần Hà Nội có nóng không?",
  "daily_forecast", "city", 0.92,
  "Cuối tuần Hà Nội có nóng không?", kind="P_city")

s("Tổng quan thời tiết Hà Nội tuần này",
  "weather_overview", "city", 0.92,
  "Tổng quan thời tiết Hà Nội tuần này", kind="P_city")

# ═══════════════════════════════════════════════════════════════════════════
# B) DISTRICT explicit (18) — bao gồm 11 missing districts
# ═══════════════════════════════════════════════════════════════════════════

# 11 missing districts ─────────────────────────────────────────────────
s("Huyện Chương Mỹ hôm nay thời tiết thế nào?",
  "current_weather", "district", 0.92,
  "Thời tiết Huyện Chương Mỹ hôm nay thế nào?", kind="P_d_missing")

s("Huyện Hoài Đức tuần này có mưa không?",
  "rain_query", "district", 0.92,
  "Huyện Hoài Đức tuần này có mưa không?", kind="P_d_missing")

s("Dự báo Huyện Phú Xuyên ngày mai",
  "daily_forecast", "district", 0.92,
  "Dự báo thời tiết Huyện Phú Xuyên ngày mai", kind="P_d_missing")

s("Huyện Phúc Thọ có cảnh báo gì không?",
  "weather_alert", "district", 0.92,
  "Huyện Phúc Thọ có cảnh báo thời tiết không?", kind="P_d_missing")

s("Nhiệt độ Huyện Quốc Oai hiện tại bao nhiêu?",
  "temperature_query", "district", 0.92,
  "Nhiệt độ Huyện Quốc Oai hiện tại bao nhiêu?", kind="P_d_missing")

s("Huyện Thanh Oai sáng nay có sương không?",
  "humidity_fog_query", "district", 0.92,
  "Huyện Thanh Oai sáng nay có sương mù không?", kind="P_d_missing")

s("Huyện Thường Tín gió mạnh không?",
  "wind_query", "district", 0.92,
  "Huyện Thường Tín hiện tại có gió mạnh không?", kind="P_d_missing")

s("Huyện Thạch Thất hôm qua thời tiết ra sao?",
  "historical_weather", "district", 0.92,
  "Huyện Thạch Thất hôm qua thời tiết thế nào?", kind="P_d_missing")

s("Huyện Ứng Hòa tuần sau có nắng không?",
  "daily_forecast", "district", 0.92,
  "Huyện Ứng Hòa tuần sau có nắng không?", kind="P_d_missing")

s("Quận Bắc Từ Liêm hôm nay thế nào?",
  "current_weather", "district", 0.92,
  "Thời tiết Quận Bắc Từ Liêm hôm nay thế nào?", kind="P_d_missing")

s("Quận Thanh Xuân hôm nay thời tiết thế nào?",
  "current_weather", "district", 0.92,
  "Thời tiết Quận Thanh Xuân hôm nay thế nào?", kind="P_d_missing")

# 7 additional district samples for balance ─────────────────────────────
s("Quận Cầu Giấy hôm nay có mưa không?",
  "rain_query", "district", 0.92,
  "Quận Cầu Giấy hôm nay có mưa không?", kind="P_d_balance")

s("Quận Long Biên có ngập lụt không?",
  "weather_alert", "district", 0.92,
  "Quận Long Biên có nguy cơ ngập lụt không?", kind="P_d_balance")

s("Quận Hà Đông buổi tối thế nào?",
  "hourly_forecast", "district", 0.92,
  "Buổi tối Quận Hà Đông thời tiết thế nào?", kind="P_d_balance")

s("Huyện Đông Anh hôm nay nhiệt độ?",
  "temperature_query", "district", 0.92,
  "Huyện Đông Anh hôm nay nhiệt độ bao nhiêu?", kind="P_d_balance")

s("Huyện Sóc Sơn cuối tuần này thế nào?",
  "daily_forecast", "district", 0.92,
  "Huyện Sóc Sơn cuối tuần này thời tiết thế nào?", kind="P_d_balance")

s("Thị xã Sơn Tây hôm nay thời tiết ra sao?",
  "current_weather", "district", 0.92,
  "Thời tiết Thị xã Sơn Tây hôm nay ra sao?", kind="P_d_balance")

s("Huyện Mỹ Đức tổng quan tuần này",
  "weather_overview", "district", 0.92,
  "Tổng quan thời tiết Huyện Mỹ Đức tuần này", kind="P_d_balance")

# ═══════════════════════════════════════════════════════════════════════════
# C) WARD explicit (22) — pure wards + missing Xã Gia Lâm
# ═══════════════════════════════════════════════════════════════════════════

# Xã Gia Lâm (missing collision-xã) ─────────────────────────────────────
s("Xã Gia Lâm hôm nay thế nào?",
  "current_weather", "ward", 0.92,
  "Thời tiết Xã Gia Lâm hôm nay thế nào?", kind="P_w_xa_gia_lam")

# Pure wards (mix intents) ─────────────────────────────────────────────
s("Phường Yên Nghĩa hôm nay có mưa không?",
  "rain_query", "ward", 0.92,
  "Phường Yên Nghĩa hôm nay có mưa không?", kind="P_w_pure")

s("Phường Bồ Đề tuần này gió thế nào?",
  "wind_query", "ward", 0.92,
  "Phường Bồ Đề tuần này gió thế nào?", kind="P_w_pure")

s("Phường Nghĩa Đô buổi tối nhiệt độ bao nhiêu?",
  "temperature_query", "ward", 0.92,
  "Phường Nghĩa Đô buổi tối nhiệt độ bao nhiêu?", kind="P_w_pure")

s("Phường Yên Hòa ngày mai có cảnh báo gì không?",
  "weather_alert", "ward", 0.92,
  "Phường Yên Hòa ngày mai có cảnh báo thời tiết không?", kind="P_w_pure")

s("Phường Văn Miếu - Quốc Tử Giám UV thế nào?",
  "expert_weather_param", "ward", 0.92,
  "UV Phường Văn Miếu - Quốc Tử Giám hôm nay thế nào?", kind="P_w_pure")

s("Phường Láng có thích hợp chạy bộ không?",
  "activity_weather", "ward", 0.92,
  "Phường Láng hôm nay có thích hợp chạy bộ không?", kind="P_w_pure")

s("Phường Phú Thượng cuối tuần thế nào?",
  "daily_forecast", "ward", 0.92,
  "Phường Phú Thượng cuối tuần dự báo thế nào?", kind="P_w_pure")

s("Phường Định Công có sương sáng nay không?",
  "humidity_fog_query", "ward", 0.92,
  "Phường Định Công sáng nay có sương mù không?", kind="P_w_pure")

s("Phường Việt Hưng hôm qua mưa không?",
  "historical_weather", "ward", 0.92,
  "Hôm qua Phường Việt Hưng có mưa không?", kind="P_w_pure")

s("Phường Đại Mỗ tổng quan thời tiết hôm nay?",
  "weather_overview", "ward", 0.92,
  "Tổng quan thời tiết Phường Đại Mỗ hôm nay", kind="P_w_pure")

s("Phường Phú Lương có nồm không nhỉ?",
  "humidity_fog_query", "ward", 0.92,
  "Phường Phú Lương hôm nay có nồm ẩm không?", kind="P_w_pure")

s("Phường Kiến Hưng so với hôm qua mát hơn không?",
  "seasonal_context", "ward", 0.92,
  "Phường Kiến Hưng hôm nay so với hôm qua có mát hơn không?", kind="P_w_pure")

# Pure xã variety ──────────────────────────────────────────────────────
s("Xã Minh Châu mùa này có rét đậm không?",
  "seasonal_context", "ward", 0.92,
  "Xã Minh Châu mùa này có rét đậm không?", kind="P_w_xa")

s("Xã Yên Lãng tuần sau có thích hợp đi cấy không?",
  "activity_weather", "ward", 0.92,
  "Xã Yên Lãng tuần sau có thích hợp đi cấy không?", kind="P_w_xa")

s("Xã Bát Tràng hôm nay có nắng không?",
  "current_weather", "ward", 0.92,
  "Xã Bát Tràng hôm nay có nắng không?", kind="P_w_xa")

s("Xã Hương Sơn nhiệt độ tối thiểu hôm nay?",
  "temperature_query", "ward", 0.92,
  "Xã Hương Sơn nhiệt độ tối thiểu hôm nay bao nhiêu?", kind="P_w_xa")

s("Xã Hòa Lạc tuần này có mưa lớn không?",
  "rain_query", "ward", 0.92,
  "Xã Hòa Lạc tuần này có mưa lớn không?", kind="P_w_xa")

# Collision wards explicit Phường (NOT default — user explicit prefix)
s("Phường Cầu Giấy hôm nay áp suất không khí bao nhiêu?",
  "expert_weather_param", "ward", 0.92,
  "Phường Cầu Giấy áp suất không khí hôm nay bao nhiêu?", kind="P_w_collision_explicit")

s("Phường Hà Đông tuần này có nóng không?",
  "temperature_query", "ward", 0.92,
  "Phường Hà Đông tuần này có nóng không?", kind="P_w_collision_explicit")

s("Phường Hoàn Kiếm sáng mai mấy giờ mưa?",
  "rain_query", "ward", 0.92,
  "Phường Hoàn Kiếm sáng mai mấy giờ mưa?", kind="P_w_collision_explicit")

s("Phường Đống Đa có thích hợp dắt chó đi dạo tối nay không?",
  "smalltalk_weather", "ward", 0.92,
  "Phường Đống Đa tối nay có thích hợp dắt chó đi dạo không?", kind="P_w_collision_explicit")

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

out_path = Path(__file__).parent / 'batch_13_pureward.jsonl'
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
