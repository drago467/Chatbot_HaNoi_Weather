"""V7 Batch 7 — FINAL fix batch (55 samples, all FIX_CONTEXT).

Composition: ~46 default Phường, ~9 keep district (Mê Linh/Gia Lâm/Đông Anh
rural collision + Ba Đình weather_alert).

After this batch: ALL 357 FIX samples done. Phase 2 complete.
Next phases: pure-ward generation, multi-turn, collision counter-examples.
"""
import json, sys
from pathlib import Path

def asst(intent, scope, conf, rewrite):
    return json.dumps({"intent": intent, "scope": scope, "confidence": conf,
                       "rewritten_query": rewrite},
                      ensure_ascii=False, separators=(',', ':'))

SAMPLES = []

# Helper to add ward-default sample (most common pattern in this batch)
def add_ward(idx, prior_user, prior_intent, prior_rewrite, current_input, intent, rewrite):
    SAMPLES.append({
        "_v6_idx": idx, "_fix_type": "FIX_CONTEXT",
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, "ward", 0.85, prior_rewrite)}],
        "input": current_input,
        "output": {"intent": intent, "scope": "ward", "confidence": 0.80,
                   "rewritten_query": rewrite}
    })

def add_district(idx, prior_user, prior_intent, prior_rewrite, current_input, intent, rewrite):
    SAMPLES.append({
        "_v6_idx": idx, "_fix_type": "FIX_CONTEXT",
        "history": [{"user": prior_user,
                     "assistant": asst(prior_intent, "district", 0.85, prior_rewrite)}],
        "input": current_input,
        "output": {"intent": intent, "scope": "district", "confidence": 0.80,
                   "rewritten_query": rewrite}
    })

# Long Biên samples (collision Phường/Quận → ward)
add_ward(2619, "Long Biên hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Long Biên hôm nay thế nào?",
         "Ở đó ngày mai có mưa không?",
         "rain_query", "Ngày mai Phường Long Biên có mưa không?")

# Hoàn Kiếm
add_ward(2620, "Hoàn Kiếm giờ thế nào?", "current_weather",
         "Thời tiết Phường Hoàn Kiếm hiện tại thế nào?",
         "Dễ chịu không?",
         "activity_weather", "Thời tiết Phường Hoàn Kiếm hiện tại có dễ chịu không?")

# Hoàng Mai
add_ward(2630, "Hoàng Mai chiều nay thế nào?", "hourly_forecast",
         "Dự báo Phường Hoàng Mai chiều nay thế nào?",
         "Chiều nay còn gió không?",
         "wind_query", "Chiều nay Phường Hoàng Mai còn gió không?")

add_ward(2670, "Hoàng Mai hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
         "Ngày mai dự báo thế nào?",
         "daily_forecast", "Ngày mai Phường Hoàng Mai dự báo thế nào?")

# Mê Linh — rural collision Xã/Huyện → district
add_district(2707, "Mê Linh thế nào?", "current_weather",
             "Thời tiết Huyện Mê Linh hiện tại thế nào?",
             "Thời tiết như thế nào ở đây?",
             "weather_overview", "Thời tiết hiện tại ở Huyện Mê Linh như thế nào?")

# Ba Đình
add_ward(2710, "Ba Đình hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Ba Đình hôm nay thế nào?",
         "tuần trước thì sao?",
         "historical_weather", "Tuần trước thời tiết Phường Ba Đình thế nào?")

# Hoàn Kiếm
add_ward(2724, "Hoàn Kiếm sáng nay có mưa không?", "rain_query",
         "Phường Hoàn Kiếm sáng nay có mưa không?",
         "Rồi sao gió thế nào?",
         "wind_query", "Sau khi tạnh mưa, gió ở Phường Hoàn Kiếm thế nào?")

# Gia Lâm — collision Xã/Huyện → district
add_district(2726, "Gia Lâm hôm nay thế nào?", "current_weather",
             "Thời tiết Huyện Gia Lâm hiện tại thế nào?",
             "Ở đó bây giờ gió thế nào?",
             "wind_query", "Gió ở Huyện Gia Lâm bây giờ thế nào?")

# Hoàng Mai
add_ward(2740, "Hoàng Mai hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
         "Chỗ đó có thích hợp để đi dạo không?",
         "activity_weather", "Thời tiết Phường Hoàng Mai có thích hợp để đi dạo không?")

# Cầu Giấy
add_ward(2752, "Cầu Giấy giờ thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hiện tại thế nào?",
         "Có nhìn xa được không?",
         "expert_weather_param", "Tầm nhìn xa ở Phường Cầu Giấy hiện tại thế nào?")

add_ward(2767, "Cầu Giấy hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hôm nay thế nào?",
         "Cuối tuần?",
         "daily_forecast", "Cuối tuần này Phường Cầu Giấy thời tiết ra sao?")

add_ward(2789, "Cầu Giấy hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hôm nay thế nào?",
         "Thời tiết cuối tuần thế nào?",
         "daily_forecast", "Cuối tuần này Phường Cầu Giấy thời tiết ra sao?")

add_ward(2793, "Cầu Giấy giờ thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hiện tại thế nào?",
         "Bây giờ nhiệt độ ở đó thế nào?",
         "temperature_query", "Nhiệt độ hiện tại Phường Cầu Giấy bao nhiêu?")

# Hoàng Mai
add_ward(2800, "Hoàng Mai sáng mai có mưa không?", "rain_query",
         "Phường Hoàng Mai sáng mai có mưa không?",
         "mấy giờ mưa?",
         "rain_query", "Sáng mai Phường Hoàng Mai mấy giờ bắt đầu mưa?")

# Hà Đông
add_ward(2808, "Hà Đông hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hà Đông hôm nay thế nào?",
         "Có vẻ trời sẽ mát mẻ nhỉ?",
         "smalltalk_weather", "Phường Hà Đông hôm nay có vẻ sẽ mát mẻ nhỉ?")

# Thanh Xuân
add_ward(2823, "Thanh Xuân hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
         "Thời tiết trong những ngày tới thế nào?",
         "daily_forecast", "Dự báo thời tiết những ngày tới ở Phường Thanh Xuân ra sao?")

# Hoàng Mai
add_ward(2835, "Hoàng Mai giờ thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hiện tại thế nào?",
         "Khu vực đó giờ thế nào?",
         "current_weather", "Phường Hoàng Mai hiện tại trời ra sao?")

# Ba Đình
add_ward(2868, "Ba Đình giờ thế nào?", "current_weather",
         "Thời tiết Phường Ba Đình hiện tại thế nào?",
         "bây giờ thời tiết ở đó ra sao?",
         "current_weather", "Trời ở Phường Ba Đình hiện giờ thế nào?")

# Gia Lâm — district
add_district(2896, "Gia Lâm hôm nay gió thế nào?", "wind_query",
             "Gió Huyện Gia Lâm hôm nay thế nào?",
             "Ngày mai còn gió không?",
             "wind_query", "Ngày mai Huyện Gia Lâm còn gió không?")

# Hoàn Kiếm
add_ward(2901, "Hoàn Kiếm hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?",
         "Tối nay ở đó có mưa không?",
         "hourly_forecast", "Tối nay Phường Hoàn Kiếm có mưa không?")

# Long Biên
add_ward(2907, "Long Biên hôm nay có phù hợp chạy bộ không?", "activity_weather",
         "Phường Long Biên hôm nay có phù hợp chạy bộ không?",
         "Thời tiết có thích hợp để chạy bộ không?",
         "activity_weather", "Phường Long Biên hôm nay có phù hợp để chạy bộ không?")

# Hoàng Mai
add_ward(2943, "Hoàng Mai giờ thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hiện tại thế nào?",
         "Còn bây giờ nắng hay mưa?",
         "current_weather", "Phường Hoàng Mai bây giờ đang nắng hay mưa?")

# Tây Hồ
add_ward(2944, "Tây Hồ hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Tây Hồ hôm nay thế nào?",
         "Ngày mai theo giờ thế nào?",
         "hourly_forecast", "Ngày mai Phường Tây Hồ diễn biến theo giờ ra sao?")

# Long Biên
add_ward(2946, "Long Biên gần đây thế nào?", "seasonal_context",
         "Thời tiết Phường Long Biên gần đây thế nào?",
         "Có thông tin gì về tình hình thời tiết gần đây không?",
         "seasonal_context", "Tình hình thời tiết gần đây ở Phường Long Biên thế nào?")

# Gia Lâm — district
add_district(2968, "Gia Lâm hôm nay thế nào?", "current_weather",
             "Thời tiết Huyện Gia Lâm hiện tại thế nào?",
             "bây giờ gió ở đó ra sao?",
             "wind_query", "Gió Huyện Gia Lâm bây giờ thế nào?")

# Đống Đa
add_ward(3012, "Đống Đa hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Đống Đa hôm nay thế nào?",
         "Độ ẩm bao nhiêu phần trăm?",
         "humidity_fog_query", "Độ ẩm Phường Đống Đa hôm nay là bao nhiêu phần trăm?")

# Hoàn Kiếm
add_ward(3020, "Hoàn Kiếm hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?",
         "Khu đó có chỉ số UV thế nào?",
         "expert_weather_param", "UV ở Phường Hoàn Kiếm hôm nay bao nhiêu?")

# Ba Đình
add_ward(3027, "Ba Đình hôm qua thế nào?", "historical_weather",
         "Hôm qua Phường Ba Đình thế nào?",
         "Nhiệt độ hôm qua bao nhiêu?",
         "historical_weather", "Nhiệt độ hôm qua Phường Ba Đình bao nhiêu độ?")

# Cầu Giấy
add_ward(3043, "Cầu Giấy giờ thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hiện tại thế nào?",
         "Bây giờ thời tiết ở đó như thế nào?",
         "current_weather", "Hiện tại thời tiết Phường Cầu Giấy thế nào?")

# Thanh Xuân
add_ward(3045, "Thanh Xuân hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
         "Có nồm không?",
         "humidity_fog_query", "Phường Thanh Xuân có nồm ẩm không?")

add_ward(3077, "Thanh Xuân hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
         "Thế còn gió mạnh không?",
         "wind_query", "Gió ở Phường Thanh Xuân hiện tại có mạnh không?")

# Gia Lâm — district
add_district(3085, "Gia Lâm hôm nay thế nào?", "current_weather",
             "Thời tiết Huyện Gia Lâm hiện tại thế nào?",
             "Bây giờ gió ở đó ra sao?",
             "wind_query", "Gió Huyện Gia Lâm bây giờ thế nào?")

# Đống Đa
add_ward(3097, "Đống Đa hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Đống Đa hôm nay thế nào?",
         "Chiều nay còn ẩm không?",
         "humidity_fog_query", "Chiều nay Phường Đống Đa còn nồm ẩm không?")

add_ward(3100, "Đống Đa hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Đống Đa hôm nay thế nào?",
         "Nơi đó ngày mai thế nào?",
         "daily_forecast", "Ngày mai Phường Đống Đa thời tiết thế nào?")

# Hoàng Mai
add_ward(3101, "Hoàng Mai hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
         "Hôm nay có gì thú vị ngoài trời không?",
         "activity_weather", "Hôm nay Phường Hoàng Mai có hoạt động ngoài trời nào thú vị không?")

add_ward(3139, "Hoàng Mai sáng mai có mưa không?", "rain_query",
         "Phường Hoàng Mai sáng mai có mưa không?",
         "Mấy giờ mưa?",
         "rain_query", "Sáng mai Phường Hoàng Mai mấy giờ bắt đầu mưa?")

# Thanh Xuân
add_ward(3152, "Thanh Xuân hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
         "Khu đó UV cao không?",
         "expert_weather_param", "UV ở Phường Thanh Xuân hiện tại có cao không?")

# Long Biên — already scope=ward in v6
add_ward(3155, "Long Biên dạo này thế nào?", "seasonal_context",
         "Thời tiết Phường Long Biên gần đây thế nào?",
         "thời tiết dạo này ra sao?",
         "seasonal_context", "Thời tiết gần đây ở Phường Long Biên thế nào?")

# Ba Đình weather_alert → district
add_district(3156, "Ba Đình có cảnh báo gì không?", "weather_alert",
             "Quận Ba Đình có cảnh báo thời tiết nào không?",
             "Có thông báo gì về thời tiết không?",
             "weather_alert", "Có thông báo gì về thời tiết ở Quận Ba Đình không?")

# Hà Đông
add_ward(3167, "Hà Đông hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hà Đông hôm nay thế nào?",
         "Chỗ đó có mát không?",
         "smalltalk_weather", "Phường Hà Đông hôm nay có thời tiết mát mẻ không?")

# Hoàng Mai
add_ward(3168, "Hoàng Mai hôm nay gió thế nào?", "wind_query",
         "Gió Phường Hoàng Mai hôm nay thế nào?",
         "Gió ảnh hưởng đến giao thông không?",
         "activity_weather", "Gió Phường Hoàng Mai hôm nay có ảnh hưởng đến giao thông không?")

# Ba Đình
add_ward(3181, "Ba Đình giờ thế nào?", "current_weather",
         "Thời tiết Phường Ba Đình hiện tại thế nào?",
         "Giờ này có nắng không?",
         "current_weather", "Phường Ba Đình bây giờ có nắng không?")

# Đông Anh — district keep
add_district(3182, "Đông Anh hôm nay có cảnh báo gì không?", "weather_alert",
             "Huyện Đông Anh hôm nay có cảnh báo thời tiết không?",
             "Có ảnh hưởng gì đến việc di chuyển không?",
             "activity_weather",
             "Cảnh báo thời tiết Huyện Đông Anh hôm nay có ảnh hưởng đến việc di chuyển không?")

# Hai Bà Trưng
add_ward(3214, "Hai Bà Trưng hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hai Bà Trưng hôm nay thế nào?",
         "Ở đó mặc gì đi làm?",
         "activity_weather", "Phường Hai Bà Trưng hôm nay nên mặc gì đi làm?")

# Long Biên
add_ward(3226, "Long Biên hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Long Biên hôm nay thế nào?",
         "Ngày mai có thời tiết thế nào?",
         "rain_query", "Ngày mai Phường Long Biên có mưa không?")

# Thanh Xuân
add_ward(3253, "Thanh Xuân hôm nay có mưa không?", "rain_query",
         "Phường Thanh Xuân hôm nay có mưa không?",
         "có mưa đến tối không?",
         "rain_query", "Mưa Phường Thanh Xuân có kéo dài đến tối không?")

add_ward(3260, "Thanh Xuân sáng nay có mưa không?", "rain_query",
         "Phường Thanh Xuân sáng nay có mưa không?",
         "Trời đã ngớt mưa chưa?",
         "current_weather", "Phường Thanh Xuân bây giờ trời đã tạnh chưa?")

# Hoàn Kiếm
add_ward(3268, "Hoàn Kiếm hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?",
         "Mặc gì đi?",
         "activity_weather", "Phường Hoàn Kiếm hôm nay nên mặc gì khi ra ngoài?")

# Đông Anh — district
add_district(3283, "Đông Anh có cảnh báo gì không?", "weather_alert",
             "Huyện Đông Anh có cảnh báo thời tiết không?",
             "Mức độ ra sao?",
             "weather_alert", "Cảnh báo thời tiết Huyện Đông Anh mức độ ra sao?")

# Hoàn Kiếm
add_ward(3299, "Hoàn Kiếm sau khi tạnh mưa thế nào?", "current_weather",
         "Phường Hoàn Kiếm sau khi tạnh mưa thế nào?",
         "Gió ra sao nhỉ?",
         "wind_query", "Sau khi tạnh mưa, gió ở Phường Hoàn Kiếm thế nào?")

# Cầu Giấy
add_ward(3456, "Cầu Giấy hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Cầu Giấy hôm nay thế nào?",
         "Tối nay thì ra sao?",
         "hourly_forecast", "Tối nay Phường Cầu Giấy thời tiết thế nào?")

# Hoàng Mai
add_ward(3459, "Hoàng Mai tối nay thế nào?", "hourly_forecast",
         "Tối nay Phường Hoàng Mai thế nào?",
         "Từ 22h thì sao?",
         "hourly_forecast", "Từ 22h tối nay Phường Hoàng Mai thời tiết ra sao?")

# Tây Hồ
add_ward(3461, "Tây Hồ hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Tây Hồ hôm nay thế nào?",
         "Còn buổi trưa?",
         "hourly_forecast", "Trưa nay Phường Tây Hồ thời tiết thế nào?")

# Thanh Xuân
add_ward(3463, "Thanh Xuân hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Thanh Xuân hôm nay thế nào?",
         "Ngày cuối tuần?",
         "daily_forecast", "Cuối tuần này Phường Thanh Xuân thời tiết thế nào?")

# Hoàng Mai
add_ward(3466, "Hoàng Mai hôm nay thế nào?", "current_weather",
         "Thời tiết Phường Hoàng Mai hôm nay thế nào?",
         "Ngày mai trước đi",
         "daily_forecast", "Ngày mai Phường Hoàng Mai thời tiết thế nào?")

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
fix_types = {}
for s in SAMPLES:
    ft = s.get('_fix_type', 'unknown')
    fix_types[ft] = fix_types.get(ft, 0) + 1
print('By fix type:', fix_types)

total_errs = 0
for i, s in enumerate(SAMPLES):
    errs = validate(s)
    if errs:
        print(f'  [SAMPLE {i} v6_idx={s.get("_v6_idx")}] {errs}')
        total_errs += 1
print(f'Validation errors: {total_errs}')
if total_errs > 0:
    sys.exit(1)

out_path = Path(__file__).parent / 'batch_07_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')
print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
