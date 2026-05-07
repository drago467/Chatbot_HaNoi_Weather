"""Audit script for router multitask training data — checks 4 issue classes."""
import json, csv, re, unicodedata
from collections import Counter

def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('d','d').replace('Đ','d').replace('đ','d')
    return s.lower().strip()

# 1) Load canonical ward/district mapping
wards = {}
districts = {}
with open('data/processed/dim_ward.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        wards[r['ward_name_core_norm']] = {
            'prefix': r['ward_prefix_norm'],
            'full': r['ward_name_vi'],
            'district_full': r['district_name_vi'],
        }
        d_full = (r['district_name_vi'] or '').strip()
        if not d_full:
            continue
        parts = d_full.split()
        if parts[0].lower() == 'thị' and len(parts) >= 2 and parts[1].lower() == 'xã':
            d_prefix = 'thị xã'
            d_core = ' '.join(parts[2:])
        else:
            d_prefix = parts[0]
            d_core = ' '.join(parts[1:])
        districts[norm(d_core)] = {'prefix': norm(d_prefix), 'full': d_full}

print(f'Loaded {len(wards)} wards, {len(districts)} districts')
phuong_count = sum(1 for w in wards.values() if w['prefix'] == 'phuong')
xa_count = sum(1 for w in wards.values() if w['prefix'] == 'xa')
quan_count = sum(1 for d in districts.values() if d['prefix'] == 'quan')
huyen_count = sum(1 for d in districts.values() if d['prefix'] == 'huyen')
thixa_count = sum(1 for d in districts.values() if d['prefix'].startswith('thi'))
print(f'  phuong={phuong_count} xa={xa_count} | quan={quan_count} huyen={huyen_count} thi xa={thixa_count}')

# 2) Load training data
with open('data/router/multitask_train_v6_clean.jsonl', encoding='utf-8') as f:
    rows = [json.loads(l) for l in f]
rw_rows = [r for r in rows if r.get('output', {}).get('rewritten_query')]
print(f'Total samples: {len(rows)}, rewrite samples: {len(rw_rows)}')

# ============================================================
# ISSUE A: Wrong prefix on WARD names (xa <-> phuong swap)
# ============================================================
print('\n' + '=' * 70)
print('ISSUE A: WRONG PREFIX tren ward (xa <-> phuong)')
print('=' * 70)

issue_a = []
for r in rw_rows:
    rew_n = norm(r['output']['rewritten_query'])
    for core, info in wards.items():
        if re.search(r'\bphuong\s+' + re.escape(core) + r'\b', rew_n):
            if info['prefix'] != 'phuong':
                issue_a.append((r, info, 'phuong'))
        if re.search(r'\bxa\s+' + re.escape(core) + r'\b', rew_n):
            if info['prefix'] != 'xa':
                issue_a.append((r, info, 'xa'))

print(f'Found: {len(issue_a)} samples with wrong ward prefix')
for r, info, used in issue_a[:6]:
    print(f"  - {info['full']:30s}  rewritten with prefix '{used}' (correct: '{info['prefix']}')")
    print(f"      input:    {r['input']}")
    print(f"      context:  {r.get('context')}")
    print(f"      rewrite:  {r['output']['rewritten_query']}")
    print()

# ============================================================
# ISSUE B: Wrong prefix on DISTRICT names
# ============================================================
print('=' * 70)
print('ISSUE B: WRONG PREFIX tren district (quan <-> huyen <-> thi xa)')
print('=' * 70)

issue_b = []
for r in rw_rows:
    rew_n = norm(r['output']['rewritten_query'])
    for core, info in districts.items():
        for prefix in ['quan', 'huyen', 'thi xa']:
            if re.search(r'\b' + re.escape(prefix) + r'\s+' + re.escape(core) + r'\b', rew_n):
                if info['prefix'] != prefix:
                    issue_b.append((r, info, prefix))

print(f'Found: {len(issue_b)} samples with wrong district prefix')
for r, info, used in issue_b[:6]:
    print(f"  - {info['full']:30s}  rewritten with prefix '{used}' (correct: '{info['prefix']}')")
    print(f"      input:    {r['input']}")
    print(f"      context:  {r.get('context')}")
    print(f"      rewrite:  {r['output']['rewritten_query']}")
    print()
b_tally = Counter((info['full'], used) for _, info, used in issue_b)
print('Top mis-prefixed districts:')
for (full, used), n in b_tally.most_common(12):
    print(f"  {full:25s} called as '{used}': {n}x")

# ============================================================
# ISSUE C: Ward elevated to district (scope or prefix)
# ============================================================
print('\n' + '=' * 70)
print('ISSUE C: WARD bi nang len district scope hoac prefix quan/huyen')
print('=' * 70)

issue_c = []
for r in rw_rows:
    rew_n = norm(r['output']['rewritten_query'])
    scope = r['output'].get('scope')
    ctx = r.get('context') or {}
    ctx_loc = ctx.get('location', '') or ''
    ctx_loc_n = norm(ctx_loc)
    for core, info in wards.items():
        if core in ctx_loc_n or ctx_loc_n.endswith(core):
            if re.search(r'\b(quan|huyen)\s+' + re.escape(core) + r'\b', rew_n):
                issue_c.append((r, info, 'district-prefix-on-ward'))
                break
            if scope == 'district':
                issue_c.append((r, info, 'scope=district'))
                break
            break

print(f'Found: {len(issue_c)} samples')
kinds = Counter(k for _, _, k in issue_c)
print('  by kind:', dict(kinds))
for r, info, kind in issue_c[:6]:
    print(f"  - [{kind}] context.location is ward {info['full']}")
    print(f"      input:    {r['input']}")
    print(f"      context:  {r.get('context')}")
    print(f"      rewrite:  {r['output']['rewritten_query']}")
    print(f"      scope:    {r['output'].get('scope')}")
    print()

# ============================================================
# ISSUE D: TIME DRIFT
# ============================================================
print('=' * 70)
print('ISSUE D: TIME DRIFT trong rewrite')
print('=' * 70)

drift_patterns = [
    ('tuan sau',    ['tuan sau'],         ['tuan nay', 'tuan truoc']),
    ('tuan toi',    ['tuan toi', 'tuan sau'], ['tuan nay']),
    ('thang sau',   ['thang sau', 'thang toi'], ['thang nay']),
    ('ngay mai',    ['ngay mai'],         ['hom nay']),
    ('ngay kia',    ['ngay kia'],         ['hom nay', 'ngay mai']),
    ('hom qua',     ['hom qua'],          ['hom nay']),
    ('tuan truoc',  ['tuan truoc'],       ['tuan nay']),
]

issue_d = []
for r in rw_rows:
    inp_n = norm(r['input'])
    rew_n = norm(r['output']['rewritten_query'])
    for trigger, must_be, must_not in drift_patterns:
        if trigger in inp_n:
            preserved = any(m in rew_n for m in must_be)
            drifted = any(m in rew_n for m in must_not)
            if (not preserved) or drifted:
                issue_d.append((r, trigger, preserved, drifted))
                break

print(f'Found: {len(issue_d)} samples with time drift in rewrite vs input')
for r, trig, preserved, drifted in issue_d[:10]:
    print(f"  - input has '{trig}' | preserved={preserved} drifted={drifted}")
    print(f"      input:    {r['input']}")
    print(f"      context:  {r.get('context')}")
    print(f"      rewrite:  {r['output']['rewritten_query']}")
    print()

# Also: context carries time but rewrite drops it. Look for context.intent indicators
# Context-based drift: input refers to a specific future weekday but rewrite says "this week"
weekday_pat = re.compile(r'\b(thu hai|thu ba|thu tu|thu nam|thu sau|thu bay|chu nhat|cn)\b')
ctx_drift = []
for r in rw_rows:
    inp_n = norm(r['input'])
    rew_n = norm(r['output']['rewritten_query'])
    if weekday_pat.search(inp_n) and 'tuan sau' not in inp_n and 'tuan toi' not in inp_n:
        # ambiguous weekday in input — rewrite should ideally not invent "tuan nay"
        if 'tuan nay' in rew_n:
            ctx_drift.append(r)

print(f'\n[bonus] weekday in input + rewrite adds "tuan nay": {len(ctx_drift)} samples')
for r in ctx_drift[:4]:
    print(f"      input:    {r['input']}")
    print(f"      rewrite:  {r['output']['rewritten_query']}")
    print()

# ============================================================
# SUMMARY
# ============================================================
print('=' * 70)
print(f'SUMMARY  /  on {len(rw_rows)} rewrite samples')
print('=' * 70)
print(f'  A. Sai prefix ward (xa/phuong):       {len(issue_a):4d}  ({100*len(issue_a)/len(rw_rows):.1f}%)')
print(f'  B. Sai prefix district (quan/huyen):  {len(issue_b):4d}  ({100*len(issue_b)/len(rw_rows):.1f}%)')
print(f'  C. Ward bi nang -> district:          {len(issue_c):4d}  ({100*len(issue_c)/len(rw_rows):.1f}%)')
print(f'  D. Time drift trong rewrite:          {len(issue_d):4d}  ({100*len(issue_d)/len(rw_rows):.1f}%)')

# Save full dump
with open('_audit_router_data_issues.json', 'w', encoding='utf-8') as f:
    json.dump({
        'issue_a_wrong_ward_prefix':    [{'sample': r, 'canonical': info, 'used': used} for r, info, used in issue_a],
        'issue_b_wrong_district_prefix': [{'sample': r, 'canonical': info, 'used': used} for r, info, used in issue_b],
        'issue_c_ward_to_district':     [{'sample': r, 'canonical': info, 'kind': k}    for r, info, k in issue_c],
        'issue_d_time_drift':           [{'sample': r, 'trigger': t, 'preserved': p, 'drifted': d} for r, t, p, d in issue_d],
    }, f, ensure_ascii=False, indent=2)
print('\nFull dump -> _audit_router_data_issues.json')
