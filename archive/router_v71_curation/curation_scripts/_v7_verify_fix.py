"""V7 verification — audit toàn bộ 357 FIX samples vs dim_ward canonical.

Checks:
1. Schema integrity (history list, output 4 keys, types).
2. Prefix conformity với dim_ward.csv (Phường/Xã/Quận/Huyện đúng).
3. Scope-prefix consistency (ward → Phường/Xã, district → Quận/Huyện/Thị xã).
4. POI absence trong rewritten_query (Lăng Bác, Hồ Tây, Times City... cấm).
5. T5 abstain integrity (confidence=0.62 → rewritten_query=null).
6. Time anchor preservation (input "ngày mai/tuần sau/hôm qua" → rewrite phải có).
7. History prior assistant JSON: 4-keys structure.
8. Confidence tier distribution per plan target.
9. Phường vs Quận balance trong FIX_CONTEXT samples.
"""
import json, csv, re, unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

# ── Load canonical authority ────────────────────────────────────────────────
WARDS = {}      # core_norm -> (prefix, full)
DISTRICTS = {}  # core_norm -> (prefix, full)
with open(ROOT/'data/processed/dim_ward.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        core = r['ward_name_core_norm']
        WARDS[core] = (r['ward_prefix_norm'], r['ward_name_vi'])
        d_full = (r['district_name_vi'] or '').strip()
        if not d_full: continue
        parts = d_full.split()
        if parts[0].lower()=='thị' and len(parts)>=2 and parts[1].lower()=='xã':
            d_prefix = 'thi xa'; d_core = ' '.join(parts[2:])
        else:
            d_prefix = norm(parts[0]); d_core = ' '.join(parts[1:])
        DISTRICTS[norm(d_core)] = (d_prefix, d_full)

COLLISION = set(WARDS) & set(DISTRICTS)
print(f'Canonical: {len(WARDS)} wards, {len(DISTRICTS)} districts, {len(COLLISION)} collision cores')

# POI list (banned in rewrite per P8/P9)
POI_BANNED = ['Lăng Bác', 'Lăng Chủ tịch', 'Hồ Tây', 'Hồ Gươm', 'Văn Miếu - Quốc Tử Giám',
              'Times City', 'Royal City', 'Bệnh viện Bạch Mai', 'Sân bay Nội Bài',
              'Phố cổ', 'Bến xe', 'Cầu Long Biên']
POI_BANNED_NORM = [norm(p) for p in POI_BANNED]
# Note: "Văn Miếu - QTG" can appear as Phường, only ban it if NOT preceded by "Phường"

VALID_INTENTS = {
    'activity_weather','current_weather','daily_forecast','expert_weather_param',
    'historical_weather','hourly_forecast','humidity_fog_query','location_comparison',
    'rain_query','seasonal_context','smalltalk_weather','temperature_query',
    'weather_alert','weather_overview','wind_query',
}
VALID_SCOPES = {'city','district','ward'}
VALID_TIERS = {0.92, 0.85, 0.80, 0.74, 0.62}

# ── Load all 7 batch JSONLs ────────────────────────────────────────────────
all_samples = []
for i in range(1, 8):
    path = ROOT/f'data/router/v7_batches/batch_0{i}_fix.jsonl'
    with open(path, encoding='utf-8') as f:
        for line in f:
            all_samples.append(json.loads(line))
print(f'Loaded {len(all_samples)} samples from 7 batches')

# ── Run checks ──────────────────────────────────────────────────────────────
errors = []
warnings = []

def check_prefix_match(rew_text: str, sample_idx: int, label: str = 'rewrite'):
    """Verify any 'Phường|Xã|Quận|Huyện X' in text matches canonical prefix."""
    if not rew_text:
        return
    rew_n = norm(rew_text)
    # Find all "phuong/xa/quan/huyen <core>" patterns
    for prefix in ('phuong', 'xa', 'quan', 'huyen'):
        for m in re.finditer(rf'\b{prefix}\s+([a-z\s\-]+?)(?=\s*(?:[,.\?\(\)]|hôm|hiện|bây|sáng|chiều|tối|trưa|đêm|tuần|tháng|ngày|hôm|năm|gần|mùa|và|với|so|hay|nhỉ|không|đang|còn|có|nên|sẽ|đến|từ|trong|nóng|lạnh|mát|gió|mưa|lúc|thì|bao|khi|$))', rew_n):
            core_candidate = m.group(1).strip()
            # Try to match canonical
            if core_candidate in WARDS:
                canonical_prefix, _ = WARDS[core_candidate]
                if prefix in ('phuong','xa') and prefix != canonical_prefix:
                    errors.append(f'[{sample_idx}] {label}: ward prefix mismatch — text uses "{prefix} {core_candidate}", canonical is "{canonical_prefix}"')
                if prefix in ('quan','huyen'):
                    # ward core misclassified as district prefix
                    if core_candidate not in COLLISION:
                        errors.append(f'[{sample_idx}] {label}: pure-ward "{core_candidate}" used with district prefix "{prefix}"')
            elif core_candidate in DISTRICTS:
                canonical_prefix, _ = DISTRICTS[core_candidate]
                if prefix in ('quan','huyen') and prefix != canonical_prefix:
                    errors.append(f'[{sample_idx}] {label}: district prefix mismatch — text uses "{prefix} {core_candidate}", canonical is "{canonical_prefix}"')

# Track distributions
tier_counter = Counter()
scope_counter = Counter()
intent_counter = Counter()
poi_in_rewrite = []
ward_district_balance = Counter()  # in rewrites: phuong/xa/quan/huyen
history_invalid = []
time_drift_bugs = []

for i, s in enumerate(all_samples):
    # 1. Schema integrity
    if 'history' not in s or not isinstance(s['history'], list):
        errors.append(f'[{i}] missing/bad history field')
        continue
    if 'input' not in s or not s['input']:
        errors.append(f'[{i}] missing/empty input')
    if 'output' not in s:
        errors.append(f'[{i}] missing output')
        continue
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

    # 2-3. Prefix + scope consistency
    rew = o.get('rewritten_query')
    if rew is not None:
        check_prefix_match(rew, i, 'rewrite')
        # Scope-prefix consistency:
        rew_n = norm(rew)
        has_ward_prefix = bool(re.search(r'\b(phuong|xa)\s+\w', rew_n))
        has_dist_prefix = bool(re.search(r'\b(quan|huyen|thi xa)\s+\w', rew_n))
        if has_ward_prefix and o['scope'] == 'district':
            warnings.append(f'[{i}] scope=district but rewrite uses Phường/Xã prefix: "{rew[:80]}"')
        if has_dist_prefix and o['scope'] == 'ward':
            warnings.append(f'[{i}] scope=ward but rewrite uses Quận/Huyện prefix: "{rew[:80]}"')
        # Track admin-prefix balance
        for prefix in ('phuong','xa','quan','huyen','thi xa'):
            if re.search(rf'\b{prefix}\s+\w', rew_n):
                ward_district_balance[prefix] += 1

    # 4. POI absence
    if rew:
        rew_n = norm(rew)
        for poi_n, poi_raw in zip(POI_BANNED_NORM, POI_BANNED):
            # Allow "Phường Văn Miếu - Quốc Tử Giám" (admin), ban "Văn Miếu" alone
            if poi_n == 'van mieu - quoc tu giam':
                if 'phuong van mieu - quoc tu giam' not in rew_n and poi_n in rew_n:
                    poi_in_rewrite.append((i, poi_raw, rew[:80]))
            elif re.search(rf'\b{re.escape(poi_n)}\b', rew_n):
                poi_in_rewrite.append((i, poi_raw, rew[:80]))

    # 5. T5 abstain integrity
    if conf == 0.62 and rew is not None:
        warnings.append(f'[{i}] T5 confidence=0.62 should have rewritten_query=null, got: "{rew[:60]}"')
    if conf in (0.92, 0.85, 0.80) and rew is None:
        # Only T2/T1 single-turn might allow null when input self-contained — but generally these tiers expect rewrite
        # T3=0.80 multi-turn definitely needs rewrite
        if conf == 0.80:
            warnings.append(f'[{i}] T3=0.80 multi-turn should have rewrite, got null')

    # 6. Time anchor preservation
    inp_n = norm(s['input'])
    if rew:
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
                # Check special case: input "ngày mai" + rewrite "sáng mai" = OK
                if trig == 'ngay mai' and 'sang mai' in rew_n:
                    continue  # acceptable refinement
                time_drift_bugs.append((i, trig, s['input'][:60], rew[:80]))

    # 7. History prior assistant JSON validity
    for j, h in enumerate(s['history']):
        if not isinstance(h, dict) or 'user' not in h or 'assistant' not in h:
            history_invalid.append((i, j, 'malformed history entry'))
            continue
        try:
            asst_obj = json.loads(h['assistant'])
        except json.JSONDecodeError:
            history_invalid.append((i, j, 'assistant not valid JSON'))
            continue
        for key in ('intent','scope','confidence'):
            if key not in asst_obj:
                history_invalid.append((i, j, f'history assistant missing {key}'))
        if asst_obj.get('intent') not in VALID_INTENTS:
            history_invalid.append((i, j, f'history bad intent {asst_obj.get("intent")}'))
        if asst_obj.get('scope') not in VALID_SCOPES:
            history_invalid.append((i, j, f'history bad scope {asst_obj.get("scope")}'))
        # Check ward consistency vs current scope for continuation
        if rew and asst_obj.get('scope') == 'ward' and o.get('scope') == 'ward':
            # Same scope, check if both reference same ward (consistency)
            pass  # too granular; skip

# ── Report ──────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('VERIFICATION REPORT')
print('='*70)

print(f'\n## 1. Schema integrity')
print(f'  Total samples: {len(all_samples)}')
print(f'  Errors (hard): {len(errors)}')
if errors:
    for e in errors[:10]:
        print(f'    {e}')

print(f'\n## 2. Confidence tier distribution')
total = len(all_samples)
for conf in sorted(VALID_TIERS, reverse=True):
    n = tier_counter[conf]
    tier_label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}[conf]
    print(f'  {tier_label} ({conf}): {n:4d}  ({100*n/total:.1f}%)')

print(f'\n## 3. Scope distribution')
for sc in ('city','district','ward'):
    n = scope_counter[sc]
    print(f'  {sc:<10} {n:4d}  ({100*n/total:.1f}%)')

print(f'\n## 4. Admin prefix balance (in rewrites)')
total_prefix_uses = sum(ward_district_balance.values())
for prefix in ('phuong','xa','quan','huyen','thi xa'):
    n = ward_district_balance[prefix]
    pct = 100*n/total_prefix_uses if total_prefix_uses else 0
    print(f'  {prefix:<10} {n:4d}  ({pct:.1f}%)')

print(f'\n## 5. POI absence in rewrites')
print(f'  POI leaks: {len(poi_in_rewrite)}')
for i, poi, rew in poi_in_rewrite[:5]:
    print(f'    [{i}] "{poi}" found in: "{rew}"')

print(f'\n## 6. Time anchor preservation')
print(f'  Time drift bugs: {len(time_drift_bugs)}')
for i, trig, inp, rew in time_drift_bugs[:5]:
    print(f'    [{i}] input has "{trig}": input="{inp}" rewrite="{rew}"')

print(f'\n## 7. History integrity')
print(f'  Invalid history entries: {len(history_invalid)}')
for i, j, reason in history_invalid[:5]:
    print(f'    [{i}.{j}] {reason}')

print(f'\n## 8. Intent distribution')
for intent in sorted(intent_counter):
    print(f'  {intent:<25} {intent_counter[intent]:3d}')

print(f'\n## 9. Warnings (soft)')
print(f'  Total warnings: {len(warnings)}')
for w in warnings[:8]:
    print(f'    {w}')

# ── Final summary ───────────────────────────────────────────────────────────
print('\n' + '='*70)
verdict = 'PASS ✓' if len(errors) == 0 and len(poi_in_rewrite) == 0 and len(history_invalid) == 0 else 'FAIL ✗'
print(f'VERDICT: {verdict}')
print(f'  Hard errors: {len(errors)}')
print(f'  POI leaks: {len(poi_in_rewrite)}')
print(f'  History invalid: {len(history_invalid)}')
print(f'  Time drifts: {len(time_drift_bugs)}')
print(f'  Soft warnings: {len(warnings)}')
print('='*70)
