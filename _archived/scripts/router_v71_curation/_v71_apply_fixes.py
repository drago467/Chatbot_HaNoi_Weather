"""V7.1 fix script — apply manual relabel decisions to v7 train/val.

71 case-by-case decisions per intent_disambiguation_rules.md + Weather Intent Design.md.
Each fix is explicit: (dataset, idx, new_intent, reason).

Output:
- data/router/multitask_train_v7_1.jsonl
- data/router/multitask_val_v7_1.jsonl
"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

# ── Load v7 ─────────────────────────────────────────────────────────────────
train = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7.jsonl', encoding='utf-8')]
val   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7.jsonl',   encoding='utf-8')]
print(f'Loaded train={len(train)} val={len(val)}')

# ── Manual fix decisions ────────────────────────────────────────────────────
# Format: (dataset, idx, new_intent, reason)
FIXES = [
    # ═══ Rule 1 — Alert severity → weather_alert (10 relabel) ═══
    ('train',  220, 'weather_alert', 'future "rét đậm" — cold-wave concern'),
    ('train',  740, 'weather_alert', 'future hourly + "mưa lớn" — safety concern'),
    ('train', 1250, 'weather_alert', 'future + "mưa to" — safety rule (rain_query→alert)'),
    ('train', 1523, 'weather_alert', '"chắc mưa lớn..." — concern phrasing + future severity'),
    ('train', 2189, 'weather_alert', 'future + "mưa to" — safety rule'),
    ('train', 2686, 'weather_alert', '"nắng nóng gay gắt" + future'),
    ('train', 3182, 'weather_alert', '"nguy hiểm" explicit + future'),
    ('train', 3304, 'weather_alert', 'future "rét đậm" — cold-wave'),
    ('train', 3429, 'weather_alert', 'future + "mưa lớn" — severity'),
    ('val',    378, 'weather_alert', 'future + "giông bão" explicit severity'),

    # ═══ Rule 2a — Clothing → smalltalk (32 relabel) ═══
    ('train',  229, 'smalltalk_weather', 'clothing query (áo khoác) → smalltalk per design'),
    ('train',  283, 'smalltalk_weather', 'clothing recommendation'),
    ('train',  430, 'smalltalk_weather', 'clothing'),
    ('train',  485, 'smalltalk_weather', 'clothing'),
    ('train',  510, 'smalltalk_weather', 'clothing (áo khoác)'),
    ('train',  561, 'smalltalk_weather', 'umbrella query'),
    ('train',  618, 'smalltalk_weather', 'clothing (áo khoác)'),
    ('train',  810, 'smalltalk_weather', 'clothing (áo khoác)'),
    ('train',  896, 'smalltalk_weather', 'clothing (áo ấm)'),
    ('train',  907, 'smalltalk_weather', 'clothing recommendation'),
    ('train',  939, 'smalltalk_weather', 'clothing'),
    ('train', 1128, 'smalltalk_weather', 'clothing (áo)'),
    ('train', 1152, 'smalltalk_weather', 'clothing'),
    ('train', 1388, 'smalltalk_weather', 'clothing'),
    ('train', 1707, 'smalltalk_weather', 'clothing (áo khoác) — POI sample, T5 stays'),
    ('train', 1867, 'smalltalk_weather', 'sunscreen recommendation'),
    ('train', 1947, 'smalltalk_weather', 'clothing'),
    ('train', 2031, 'smalltalk_weather', 'clothing'),
    ('train', 2233, 'smalltalk_weather', 'clothing'),
    ('train', 2262, 'smalltalk_weather', 'clothing'),
    ('train', 2321, 'smalltalk_weather', 'clothing'),
    ('train', 2880, 'smalltalk_weather', 'clothing (áo phao)'),
    ('train', 2995, 'smalltalk_weather', 'clothing (áo khoác)'),
    ('train', 2999, 'smalltalk_weather', 'clothing'),
    ('train', 3040, 'smalltalk_weather', 'clothing'),
    ('train', 3211, 'smalltalk_weather', 'sunscreen'),
    ('train', 3287, 'smalltalk_weather', 'clothing — POI sample, T5 stays'),
    ('train', 3377, 'smalltalk_weather', 'clothing'),
    ('val',   118, 'smalltalk_weather', 'clothing'),
    ('val',   194, 'smalltalk_weather', 'sunscreen'),
    ('val',   197, 'smalltalk_weather', 'clothing'),
    ('val',   311, 'smalltalk_weather', 'clothing'),

    # ═══ Rule 2b — Specific recreational activity → activity (4 relabel) ═══
    ('train',  256, 'activity_weather', '"đi bơi" — recreational specific'),
    ('train', 2272, 'activity_weather', '"dắt chó đi dạo" — recreational specific'),
    ('val',    38, 'activity_weather', '"thả diều" — recreational specific'),
    ('val',   173, 'activity_weather', '"dắt chó đi dạo" — recreational specific'),

    # ═══ Rule 3 — Tomorrow time slot → hourly_forecast (25 relabel) ═══
    ('train',  253, 'hourly_forecast', '"tối mai" — within 48h hourly slot'),
    ('train',  276, 'hourly_forecast', '"sáng mai" — hourly slot'),
    ('train',  521, 'hourly_forecast', '"tối mai" — hourly'),
    ('train',  636, 'hourly_forecast', '"tối mai" — hourly'),
    ('train',  793, 'hourly_forecast', '"chiều mai" — hourly'),
    ('train',  926, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 1004, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 1390, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 1427, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 1599, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 1602, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 1954, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 2182, 'hourly_forecast', '"chiều mai" — hourly'),
    ('train', 2231, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 2372, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 2815, 'hourly_forecast', '"chiều mai" — hourly'),
    ('train', 2950, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 3065, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 3157, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 3203, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 3208, 'hourly_forecast', '"sáng mai" — hourly'),
    ('train', 3256, 'hourly_forecast', '"tối mai" — hourly'),
    ('train', 3331, 'hourly_forecast', '"tối mai" — hourly'),
    ('val',    87, 'hourly_forecast', '"sáng mai" — hourly'),
    ('val',   205, 'hourly_forecast', '"sáng mai" — hourly'),
]

print(f'Manual fixes to apply: {len(FIXES)}')

# ── Apply ───────────────────────────────────────────────────────────────────
fixed_train = [dict(s) for s in train]  # copy
fixed_val   = [dict(s) for s in val]

applied = 0
skipped = 0
for dataset, idx, new_intent, reason in FIXES:
    samples = fixed_train if dataset == 'train' else fixed_val
    if idx >= len(samples):
        print(f'  WARN: {dataset}#{idx} out of range, skip')
        skipped += 1
        continue
    s = samples[idx]
    out = dict(s.get('output', {}))
    old_intent = out.get('intent')
    if old_intent == new_intent:
        print(f'  NOOP: {dataset}#{idx} already {new_intent}')
        skipped += 1
        continue
    out['intent'] = new_intent
    s['output'] = out
    samples[idx] = s
    applied += 1

print(f'Applied: {applied}, Skipped: {skipped}')

# ── Audit re-check (should be 0 violations after fix, except KEEP cases) ────
print(f'\nIntent distribution after fix:')
all_intents = Counter(s['output']['intent'] for s in fixed_train + fixed_val)
for intent in sorted(all_intents):
    print(f'  {intent:<25} {all_intents[intent]:4d}')

# ── Write ──────────────────────────────────────────────────────────────────
out_train = ROOT/'data/router/multitask_train_v7_1.jsonl'
out_val   = ROOT/'data/router/multitask_val_v7_1.jsonl'

with open(out_train, 'w', encoding='utf-8') as f:
    for s in fixed_train:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_train} ({len(fixed_train)} samples)')

with open(out_val, 'w', encoding='utf-8') as f:
    for s in fixed_val:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_val} ({len(fixed_val)} samples)')
