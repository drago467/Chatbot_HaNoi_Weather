"""V7.1 batch 17 — 50 disambig samples củng cố intent boundaries.

Targets 5 weak intents từ eval 4B v7:
- weather_alert (71% acc) — confused with rain_query
- hourly_forecast (72%) — confused with daily/temp
- current_weather (77%) — confused with rain_query
- smalltalk_weather (82%) — confused with activity
- weather_overview (82%) — confused with daily/current

Tuân thủ:
- intent_disambiguation_rules.md (signal words, anti-confusion rules)
- Weather Intent Design.md (intent definitions, sample utterances)
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

def s1(inp, intent, scope, conf, rew, kind="D"):
    SAMPLES.append({
        "_kind": kind, "history": [], "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

def s2(prior_user, prior_intent, prior_scope, prior_rew, inp, intent, scope, conf, rew, kind="D_mt"):
    SAMPLES.append({
        "_kind": kind,
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, prior_scope, 0.92, prior_rew)}],
        "input": inp,
        "output": {"intent": intent, "scope": scope, "confidence": conf,
                   "rewritten_query": rew}
    })

# ═══════════════════════════════════════════════════════════════════════════
# A) weather_alert vs rain_query disambig (15 samples)
# Per disambig rule: severity keywords (bão/giông/lũ/ngập/mưa to/lớn/đá) → alert
# Future tense + severity → alert. Past pattern → other intents.
# ═══════════════════════════════════════════════════════════════════════════

# Future + giông → alert
s1("Tối nay Hà Nội có giông không?",
   "weather_alert", "city", 0.92,
   "Tối nay Hà Nội có giông không?", kind="D_alert_giong")

s1("Phường Long Biên chiều nay có giông lốc không?",
   "weather_alert", "ward", 0.92,
   "Chiều nay Phường Long Biên có giông lốc không?", kind="D_alert_giong")

# Future + bão → alert
s1("Cuối tuần Hà Nội có bão không?",
   "weather_alert", "city", 0.92,
   "Cuối tuần Hà Nội có bão không?", kind="D_alert_bao")

s1("Tuần này có áp thấp nhiệt đới ảnh hưởng Hà Nội không?",
   "weather_alert", "city", 0.92,
   "Tuần này Hà Nội có bị áp thấp nhiệt đới ảnh hưởng không?", kind="D_alert_aptap")

# Future + ngập → alert
s1("Quận Hoàng Mai có nguy cơ ngập tối nay không?",
   "weather_alert", "district", 0.92,
   "Tối nay Quận Hoàng Mai có nguy cơ ngập lụt không?", kind="D_alert_ngap")

s1("Phường Tây Hồ chiều mai có ngập không?",
   "weather_alert", "ward", 0.92,
   "Chiều mai Phường Tây Hồ có ngập không?", kind="D_alert_ngap")

# Future + mưa to/lớn → alert
s1("Đêm nay Hà Nội có mưa lớn không?",
   "weather_alert", "city", 0.92,
   "Đêm nay Hà Nội có mưa lớn không?", kind="D_alert_mualon")

s1("Phường Cầu Giấy chiều nay có mưa to không?",
   "weather_alert", "ward", 0.92,
   "Chiều nay Phường Cầu Giấy có mưa to không?", kind="D_alert_muato")

# Future + rét đậm/hại → alert
s1("Tuần này Hà Nội có rét đậm không?",
   "weather_alert", "city", 0.92,
   "Tuần này Hà Nội có rét đậm không?", kind="D_alert_ret")

# Future + nắng nóng cực đoan → alert
s1("Tuần tới Hà Nội có nắng nóng gay gắt không?",
   "weather_alert", "city", 0.92,
   "Tuần tới Hà Nội có đợt nắng nóng gay gắt không?", kind="D_alert_nang")

# Counter-examples — pure rain_query (no severity)
s1("Ngày mai Hà Nội có mưa phùn không?",
   "rain_query", "city", 0.92,
   "Ngày mai Hà Nội có mưa phùn không?", kind="D_rain_phun")

s1("Mưa ở Phường Đống Đa lúc nào tạnh?",
   "rain_query", "ward", 0.92,
   "Mưa ở Phường Đống Đa khi nào tạnh?", kind="D_rain_duration")

s1("Khả năng mưa ở Hà Nội chiều nay bao nhiêu phần trăm?",
   "rain_query", "city", 0.92,
   "Xác suất mưa ở Hà Nội chiều nay bao nhiêu phần trăm?", kind="D_rain_prob")

s1("Ngày mai có cần mang ô không?",
   "rain_query", "city", 0.92,
   "Ngày mai Hà Nội có cần mang ô không?", kind="D_rain_practical")

# Multi-turn alert pattern: prior weather → current asks safety concern
s2("Phường Hoàng Mai hôm nay thế nào?", "current_weather", "ward",
   "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
   "có nguy cơ ngập không?",
   "weather_alert", "ward", 0.80,
   "Phường Hoàng Mai có nguy cơ ngập lụt không?", kind="D_alert_mt")

# ═══════════════════════════════════════════════════════════════════════════
# B) hourly_forecast vs daily_forecast disambig (10 samples)
# Per disambig rule: time slot trong 48h (sáng/chiều/tối + nay/mai) → hourly.
# Whole day or multi-day → daily.
# ═══════════════════════════════════════════════════════════════════════════

# Hourly: tomorrow time slots
s1("Sáng mai 7-9h ở Hà Nội thời tiết thế nào?",
   "hourly_forecast", "city", 0.92,
   "Sáng mai 7-9h Hà Nội thời tiết thế nào?", kind="D_hourly_morning")

s1("Trưa mai ở Phường Cầu Giấy có nắng to không?",
   "hourly_forecast", "ward", 0.92,
   "Trưa mai Phường Cầu Giấy có nắng to không?", kind="D_hourly_noon")

s1("Tối mai khoảng 22h ở Hà Nội thế nào?",
   "hourly_forecast", "city", 0.92,
   "Tối mai khoảng 22h Hà Nội thời tiết thế nào?", kind="D_hourly_night")

s1("Đêm nay Hà Nội từ 0h đến 4h thời tiết ra sao?",
   "hourly_forecast", "city", 0.92,
   "Đêm nay Hà Nội từ 0h đến 4h thời tiết ra sao?", kind="D_hourly_late")

s1("Chiều nay khoảng 15-17h ở Phường Tây Hồ thế nào?",
   "hourly_forecast", "ward", 0.92,
   "Chiều nay 15-17h Phường Tây Hồ thời tiết thế nào?", kind="D_hourly_aft")

# Daily: whole-day or multi-day (counter)
s1("Ngày mai Hà Nội thời tiết tổng thể thế nào?",
   "daily_forecast", "city", 0.92,
   "Ngày mai Hà Nội thời tiết tổng thể thế nào?", kind="D_daily_whole")

s1("Cuối tuần này ở Phường Hà Đông trời ra sao?",
   "daily_forecast", "ward", 0.92,
   "Cuối tuần này Phường Hà Đông thời tiết ra sao?", kind="D_daily_weekend")

s1("3 ngày tới Hà Nội có nóng không?",
   "daily_forecast", "city", 0.92,
   "3 ngày tới Hà Nội có nóng không?", kind="D_daily_3days")

s1("Thứ bảy ở Quận Long Biên trời thế nào?",
   "daily_forecast", "district", 0.92,
   "Thứ bảy Quận Long Biên trời thế nào?", kind="D_daily_weekday")

s1("Tuần sau ở Huyện Sóc Sơn dự báo ra sao?",
   "daily_forecast", "district", 0.92,
   "Tuần sau Huyện Sóc Sơn dự báo thế nào?", kind="D_daily_nextweek")

# ═══════════════════════════════════════════════════════════════════════════
# C) current_weather vs temperature_query disambig (8 samples)
# Per disambig rule: "thời tiết/trời thế nào" → current; "nhiệt độ/bao nhiêu độ" → temp.
# ═══════════════════════════════════════════════════════════════════════════

# Current — overview signals
s1("Bây giờ Phường Cầu Giấy trời thế nào?",
   "current_weather", "ward", 0.92,
   "Hiện tại Phường Cầu Giấy trời thế nào?", kind="D_current_overview")

s1("Hà Nội hiện tại có đang mưa không?",
   "current_weather", "city", 0.92,
   "Hà Nội hiện tại có đang mưa không?", kind="D_current_ongoing")

s1("Trời ở Quận Đống Đa lúc này có đẹp không?",
   "current_weather", "district", 0.92,
   "Trời ở Quận Đống Đa hiện tại có đẹp không?", kind="D_current_quality")

s1("Phường Long Biên giờ đang nắng hay mưa?",
   "current_weather", "ward", 0.92,
   "Phường Long Biên hiện tại đang nắng hay mưa?", kind="D_current_phenom")

# Temperature — explicit number signals (counter)
s1("Hà Nội bây giờ bao nhiêu độ?",
   "temperature_query", "city", 0.92,
   "Hà Nội hiện tại bao nhiêu độ?", kind="D_temp_number")

s1("Phường Tây Hồ hiện tại nhiệt độ bao nhiêu?",
   "temperature_query", "ward", 0.92,
   "Phường Tây Hồ nhiệt độ hiện tại bao nhiêu?", kind="D_temp_explicit")

s1("Quận Hoàn Kiếm bây giờ nóng không?",
   "temperature_query", "district", 0.92,
   "Quận Hoàn Kiếm hiện tại có nóng không?", kind="D_temp_implicit")

s1("Phường Bạch Mai hiện tại lạnh cỡ nào?",
   "temperature_query", "ward", 0.92,
   "Phường Bạch Mai hiện tại lạnh cỡ nào?", kind="D_temp_magnitude")

# ═══════════════════════════════════════════════════════════════════════════
# D) smalltalk_weather vs activity_weather disambig (10 samples)
# Per design + memory: clothing/recommendation → smalltalk;
# specific recreational activity (chạy bộ/picnic/đi dạo) → activity.
# ═══════════════════════════════════════════════════════════════════════════

# Smalltalk — clothing/recommendation
s1("Hôm nay Hà Nội có cần mang áo mưa không?",
   "smalltalk_weather", "city", 0.92,
   "Hôm nay Hà Nội có cần mang áo mưa không?", kind="D_smalltalk_umbrella")

s1("Bạn nghĩ trời Hà Nội hôm nay có lạnh quá không?",
   "smalltalk_weather", "city", 0.92,
   "Hôm nay Hà Nội có lạnh quá không?", kind="D_smalltalk_chitchat")

s1("Trời nóng thế này có cần kem chống nắng không?",
   "smalltalk_weather", "city", 0.92,
   "Hôm nay có cần kem chống nắng không?", kind="D_smalltalk_sunscreen")

s1("Tối nay Phường Tây Hồ trẻ em có cần mặc ấm không?",
   "smalltalk_weather", "ward", 0.92,
   "Tối nay Phường Tây Hồ trẻ em có cần mặc ấm không?", kind="D_smalltalk_kids")

s1("Chào bạn, hôm nay thời tiết Hà Nội thế nào?",
   "current_weather", "city", 0.92,
   "Hôm nay thời tiết Hà Nội thế nào?", kind="D_smalltalk_greeting_redirect")

# Activity — specific recreational
s1("Sáng mai có thích hợp chạy bộ ở Phường Tây Hồ không?",
   "activity_weather", "ward", 0.92,
   "Sáng mai Phường Tây Hồ có thích hợp chạy bộ không?", kind="D_activity_run")

s1("Cuối tuần có thích hợp đi picnic ở Huyện Ba Vì không?",
   "activity_weather", "district", 0.92,
   "Cuối tuần Huyện Ba Vì có thích hợp đi picnic không?", kind="D_activity_picnic")

s1("Phường Long Biên hôm nay có thích hợp đi xe đạp không?",
   "activity_weather", "ward", 0.92,
   "Phường Long Biên hôm nay có thích hợp đi xe đạp không?", kind="D_activity_bike")

s1("Chiều nay có thích hợp dắt chó đi dạo ở Phường Đống Đa không?",
   "activity_weather", "ward", 0.92,
   "Chiều nay Phường Đống Đa có thích hợp dắt chó đi dạo không?", kind="D_activity_pet")

s1("Hôm nay Hà Nội có thích hợp đi câu cá không?",
   "activity_weather", "city", 0.92,
   "Hôm nay Hà Nội có thích hợp đi câu cá không?", kind="D_activity_fishing")

# ═══════════════════════════════════════════════════════════════════════════
# E) weather_overview vs daily_forecast disambig (7 samples)
# Per disambig rule: "tổng quan/tóm tắt/nhìn chung" → overview;
# specific forecast or "ngày mai/cuối tuần" alone → daily.
# ═══════════════════════════════════════════════════════════════════════════

s1("Tóm tắt thời tiết Hà Nội hôm nay giúp mình",
   "weather_overview", "city", 0.92,
   "Tóm tắt thời tiết Hà Nội hôm nay", kind="D_overview_today")

s1("Cho mình một bản tổng quan thời tiết 3 ngày tới ở Quận Long Biên",
   "weather_overview", "district", 0.92,
   "Tổng quan thời tiết 3 ngày tới ở Quận Long Biên", kind="D_overview_3day")

s1("Mô tả ngắn gọn thời tiết tuần này ở Hà Nội",
   "weather_overview", "city", 0.92,
   "Mô tả ngắn gọn thời tiết Hà Nội tuần này", kind="D_overview_week")

s1("Tình hình thời tiết chung ở Phường Tây Hồ hôm nay",
   "weather_overview", "ward", 0.92,
   "Tình hình thời tiết chung Phường Tây Hồ hôm nay", kind="D_overview_general")

# Daily counter (specific forecast, no overview keyword)
s1("Ngày mai Phường Cầu Giấy nhiệt độ cao nhất bao nhiêu?",
   "daily_forecast", "ward", 0.92,
   "Ngày mai Phường Cầu Giấy nhiệt độ cao nhất bao nhiêu?", kind="D_daily_specific")

s1("Cuối tuần Hà Nội có nóng không?",
   "daily_forecast", "city", 0.92,
   "Cuối tuần Hà Nội có nóng không?", kind="D_daily_weekend")

s1("Trong 7 ngày tới ở Quận Hà Đông ngày nào mưa nhiều nhất?",
   "daily_forecast", "district", 0.92,
   "Trong 7 ngày tới Quận Hà Đông ngày nào mưa nhiều nhất?", kind="D_daily_peak")

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

out_path = Path(__file__).parent / 'batch_17_disambig.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for sample in SAMPLES:
        clean = {k: v for k, v in sample.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')

from collections import Counter
intents = Counter(s['output']['intent'] for s in SAMPLES)
print(f'\nIntent distribution:')
for i in sorted(intents):
    print(f'  {i}: {intents[i]}')
