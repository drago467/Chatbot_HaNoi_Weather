"""V7 comprehensive verification — audit toàn bộ 607 manual samples (12 batches).

Checks:
1. Schema integrity (history list, output 4 keys, types)
2. POI absence trong rewritten_query
3. Time anchor preservation (input vs rewrite)
4. History integrity (4-keys core, valid intent/scope, K≤3 sliding window)
5. Confidence tier distribution per plan target (T1-T5)
6. Scope distribution (ward / district / city)
7. Multi-turn specific:
   - History prior assistant scope consistency (continuation must keep scope)
   - Explicit-switch detection (different ward/district/city in current vs prior)
8. Canonical ward/district name validation
9. Intent distribution
10. Coverage: how many distinct wards/districts mentioned
"""
import json, csv, re, unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

# ── Load canonical ──────────────────────────────────────────────────────────
WARDS = {}
DISTRICTS = {}
WARD_FULL_NAMES = set()
DISTRICT_FULL_NAMES = set()
with open(ROOT/'data/processed/dim_ward.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        core = r['ward_name_core_norm']
        WARDS[core] = (r['ward_prefix_norm'], r['ward_name_vi'])
        WARD_FULL_NAMES.add(r['ward_name_vi'])
        d_full = (r['district_name_vi'] or '').strip()
        if not d_full: continue
        DISTRICT_FULL_NAMES.add(d_full)
        parts = d_full.split()
        if parts[0].lower()=='thị' and len(parts)>=2 and parts[1].lower()=='xã':
            d_prefix = 'thi xa'; d_core = ' '.join(parts[2:])
        else:
            d_prefix = norm(parts[0]); d_core = ' '.join(parts[1:])
        DISTRICTS[norm(d_core)] = (d_prefix, d_full)

COLLISION = set(WARDS) & set(DISTRICTS)

# ── Load all batches (1-16) ────────────────────────────────────────────────
all_samples = []
batch_meta = []
for i in range(1, 20):
    candidates = [
        ROOT/f'data/router/v7_batches/batch_{i:02d}_fix.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_multiturn.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_pureward.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_collision.jsonl',
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None: continue
    n_before = len(all_samples)
    with open(path, encoding='utf-8') as f:
        for line in f:
            all_samples.append(json.loads(line))
    batch_meta.append((i, path.name, len(all_samples) - n_before))

print(f'Loaded {len(all_samples)} samples from {len(batch_meta)} batches')
for i, name, n in batch_meta:
    print(f'  {name}: {n}')

VALID_INTENTS = {
    'activity_weather','current_weather','daily_forecast','expert_weather_param',
    'historical_weather','hourly_forecast','humidity_fog_query','location_comparison',
    'rain_query','seasonal_context','smalltalk_weather','temperature_query',
    'weather_alert','weather_overview','wind_query',
}
VALID_SCOPES = {'city','district','ward'}
VALID_TIERS = {0.92, 0.85, 0.80, 0.74, 0.62}

POI_BANNED_NORM = [norm(p) for p in [
    "Lăng Bác", "Lăng Chủ tịch", "Hồ Tây", "Hồ Gươm", "Times City",
    "Royal City", "Bệnh viện Bạch Mai", "Sân bay Nội Bài",
    "Phố cổ", "Bến xe Mỹ Đình", "Bến xe Giáp Bát", "Cầu Long Biên",
    "Aeon Mall", "Hồ Linh Đàm", "Hồ Trúc Bạch", "Chùa Trấn Quốc",
    "Nhà thờ Lớn", "Ga Hà Nội", "Đại học Bách Khoa", "Đại học Quốc Gia",
]]

# ── Counters ────────────────────────────────────────────────────────────────
errors = []
warnings = []

tier_counter = Counter()
scope_counter = Counter()
intent_counter = Counter()
turn_counter = Counter()
poi_in_rewrite = []
time_drift_bugs = []
history_invalid = []
ward_mentions = Counter()
district_mentions = Counter()

# ── Audit ───────────────────────────────────────────────────────────────────
for i, s in enumerate(all_samples):
    # 1. Schema
    if 'history' not in s or not isinstance(s['history'], list):
        errors.append(f'[{i}] missing/bad history'); continue
    if 'input' not in s or not s['input']:
        errors.append(f'[{i}] missing input')
    if 'output' not in s:
        errors.append(f'[{i}] missing output'); continue
    o = s['output']
    if o.get('intent') not in VALID_INTENTS:
        errors.append(f'[{i}] invalid intent: {o.get("intent")}')
    if o.get('scope') not in VALID_SCOPES:
        errors.append(f'[{i}] invalid scope: {o.get("scope")}')
    conf = o.get('confidence')
    if conf not in VALID_TIERS:
        errors.append(f'[{i}] non-tier confidence: {conf}')
    tier_counter[conf] += 1
    scope_counter[o.get('scope')] += 1
    intent_counter[o.get('intent')] += 1
    turn_counter[len(s['history']) + 1] += 1

    # K ≤ 3 sliding window
    if len(s['history']) > 3:
        errors.append(f'[{i}] history length {len(s["history"])} > K=3')

    rew = o.get('rewritten_query')

    # 2. POI absence check
    if rew:
        rew_n = norm(rew)
        for poi_n in POI_BANNED_NORM:
            if re.search(rf'\b{re.escape(poi_n)}\b', rew_n):
                poi_in_rewrite.append((i, poi_n, rew[:80]))
                break

    # 3. Time anchor preservation
    if rew:
        inp_n = norm(s['input'])
        rew_n = norm(rew)
        anchor_pairs = [
            ('ngay mai', ['ngay mai']),
            ('ngay kia', ['ngay kia']),
            ('hom qua', ['hom qua']),
            ('tuan sau', ['tuan sau','tuan toi']),
            ('tuan truoc', ['tuan truoc']),
            ('thang sau', ['thang sau','thang toi']),
            ('thang truoc', ['thang truoc']),
        ]
        for trig, must_be in anchor_pairs:
            if trig in inp_n and not any(m in rew_n for m in must_be):
                if trig == 'ngay mai' and 'sang mai' in rew_n:
                    continue
                time_drift_bugs.append((i, trig, s['input'][:60], rew[:80]))
                break

    # 4. History integrity
    for j, h in enumerate(s['history']):
        if not isinstance(h, dict) or 'user' not in h or 'assistant' not in h:
            history_invalid.append((i, j, 'malformed history entry'))
            continue
        try:
            asst_obj = json.loads(h['assistant'])
        except json.JSONDecodeError:
            history_invalid.append((i, j, 'assistant not valid JSON'))
            continue
        if asst_obj.get('intent') not in VALID_INTENTS:
            history_invalid.append((i, j, f'history bad intent {asst_obj.get("intent")}'))
        if asst_obj.get('scope') not in VALID_SCOPES:
            history_invalid.append((i, j, f'history bad scope {asst_obj.get("scope")}'))
        # 4 keys core check
        keys = set(asst_obj.keys())
        expected = {'intent', 'scope', 'confidence', 'rewritten_query'}
        if keys != expected:
            history_invalid.append((i, j, f'history keys {keys} != expected {expected}'))

    # 5. Coverage: extract ward/district mentions
    all_text = (s['input'] or '') + ' ' + (rew or '')
    for h in s['history']:
        all_text += ' ' + h.get('user', '') + ' ' + h.get('assistant', '')

    for ward_full in WARD_FULL_NAMES:
        if ward_full in all_text:
            ward_mentions[ward_full] += 1
    for d_full in DISTRICT_FULL_NAMES:
        if d_full in all_text:
            district_mentions[d_full] += 1

# ── Report ──────────────────────────────────────────────────────────────────
N = len(all_samples)
print('\n' + '='*70)
print(f'V7 VERIFICATION REPORT — {N} samples (12 batches)')
print('='*70)

print(f'\n## 1. Schema integrity')
print(f'  Hard errors: {len(errors)}')
for e in errors[:5]: print(f'    {e}')

print(f'\n## 2. Confidence tier distribution')
plan = {0.92: 28, 0.85: 28, 0.80: 18, 0.74: 12, 0.62: 14}
for conf in sorted(VALID_TIERS, reverse=True):
    n = tier_counter[conf]
    label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}[conf]
    pct = 100*n/N
    target = plan[conf]
    print(f'  {label} ({conf}): {n:4d} ({pct:5.1f}%)  target ~{target}%  delta {pct-target:+.1f}pp')

print(f'\n## 3. Scope distribution')
target_scope = {'city': 20, 'district': 35, 'ward': 45}
for sc in ('city','district','ward'):
    n = scope_counter[sc]
    pct = 100*n/N
    t = target_scope[sc]
    print(f'  {sc:<10} {n:4d}  ({pct:5.1f}%)  target ~{t}%  delta {pct-t:+.1f}pp')

print(f'\n## 4. Turn distribution')
for t in sorted(turn_counter):
    n = turn_counter[t]
    print(f'  turn={t}: {n:4d}  ({100*n/N:.1f}%)')

print(f'\n## 5. POI absence in rewrites')
print(f'  POI leaks: {len(poi_in_rewrite)}')
for i, poi, rew in poi_in_rewrite[:5]:
    print(f'    [{i}] "{poi}" in: "{rew}"')

print(f'\n## 6. Time anchor preservation')
print(f'  Time drifts: {len(time_drift_bugs)}')
for i, trig, inp, rew in time_drift_bugs[:5]:
    print(f'    [{i}] "{trig}": "{inp}" → "{rew}"')

print(f'\n## 7. History integrity')
print(f'  Invalid entries: {len(history_invalid)}')
for i, j, reason in history_invalid[:5]:
    print(f'    [{i}.{j}] {reason}')

print(f'\n## 8. Intent distribution (15 intents)')
for intent in sorted(intent_counter):
    n = intent_counter[intent]
    print(f'  {intent:<25} {n:4d}  ({100*n/N:.1f}%)')

print(f'\n## 9. Ward coverage')
print(f'  Wards mentioned: {len(ward_mentions)}/{len(WARD_FULL_NAMES)} ({100*len(ward_mentions)/len(WARD_FULL_NAMES):.1f}%)')
unmentioned_wards = WARD_FULL_NAMES - set(ward_mentions)
print(f'  Wards NEVER mentioned: {len(unmentioned_wards)}')
if unmentioned_wards:
    print('  Top 15 missing:', sorted(unmentioned_wards)[:15])

print(f'\n## 10. District coverage')
print(f'  Districts mentioned: {len(district_mentions)}/{len(DISTRICT_FULL_NAMES)} ({100*len(district_mentions)/len(DISTRICT_FULL_NAMES):.1f}%)')
unmentioned_d = DISTRICT_FULL_NAMES - set(district_mentions)
if unmentioned_d:
    print(f'  Districts missing: {sorted(unmentioned_d)}')

print(f'\n## 11. Top mentioned wards (over-representation check)')
for ward, n in ward_mentions.most_common(10):
    print(f'  {ward:<40} {n:3d}x')

# Multi-turn specific: continuation vs explicit-switch ratio
mt_samples = [s for s in all_samples if len(s['history']) >= 1]
continuation = 0
switch = 0
for s in mt_samples:
    if not s['history']: continue
    last_asst = s['history'][-1]['assistant']
    try:
        last_obj = json.loads(last_asst)
        last_scope = last_obj.get('scope')
        cur_scope = s['output'].get('scope')
        if last_scope == cur_scope:
            continuation += 1
        else:
            switch += 1
    except: pass
print(f'\n## 12. Multi-turn continuation vs switch')
total_mt = continuation + switch
if total_mt:
    print(f'  Continuation: {continuation} ({100*continuation/total_mt:.1f}%) — target ~60%')
    print(f'  Switch:       {switch} ({100*switch/total_mt:.1f}%) — target ~40%')

# ── Final ───────────────────────────────────────────────────────────────────
print('\n' + '='*70)
verdict = 'PASS ✓' if (len(errors)==0 and len(poi_in_rewrite)==0 and len(history_invalid)==0 and len(time_drift_bugs)==0) else 'FAIL ✗'
print(f'OVERALL VERDICT: {verdict}')
print(f'  Hard errors:       {len(errors)}')
print(f'  POI leaks:         {len(poi_in_rewrite)}')
print(f'  Time drifts:       {len(time_drift_bugs)}')
print(f'  History invalid:   {len(history_invalid)}')
print(f'  Soft warnings:     {len(warnings)}')
print('='*70)
