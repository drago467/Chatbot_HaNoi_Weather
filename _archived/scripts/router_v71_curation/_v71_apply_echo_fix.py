"""V7.1 echo-rewrite fix — manual case-by-case decisions.

102 candidates Level B reviewed manually:
- 91 KILL: set rewrite=null (echo/reorder, no new info added)
- 11 KEEP: rewrite is legitimate (adds prefix, time anchor, clarification)

Output: overwrites multitask_train_v7_1.jsonl + multitask_val_v7_1.jsonl
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent

# 11 KEEP indices — rewrite stays
KEEP = {
    ('train', 186),   # "sương" → "sương mù" clarify
    ('train', 421),   # ADDS "Hôm nay" time
    ('train', 562),   # "ngập" → "ngập lụt" clarify
    ('train', 1725),  # "Quốc Oai" → "Xã Quốc Oai" prefix
    ('train', 2077),  # "Thạch Thất" → "Xã Thạch Thất" prefix
    ('train', 2368),  # "Hoài Đức" → "Xã Hoài Đức" prefix
    ('train', 2694),  # ADDS "hôm nay" time
    ('train', 3150),  # "phường" → "Phường" case normalize
    ('val', 56),      # "sương" → "sương mù"
    ('val', 95),      # "Hoài Đức" → "Xã Hoài Đức" prefix
    ('val', 179),     # "ngập" → "ngập lụt"
}

# Load Level B candidates
cands = json.load(open(ROOT/'_v71_level_b_candidates.json', encoding='utf-8'))
print(f'Level B candidates: {len(cands)}')

# Load v7.1 data
train = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7_1.jsonl', encoding='utf-8')]
val   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7_1.jsonl',   encoding='utf-8')]

# Apply: for each candidate NOT in KEEP, set rewrite=null
killed_count = 0
for c in cands:
    key = (c['dataset'], c['idx'])
    if key in KEEP:
        continue
    samples = train if c['dataset'] == 'train' else val
    s = samples[c['idx']]
    out = dict(s.get('output', {}))
    if out.get('rewritten_query'):
        out['rewritten_query'] = None
        s['output'] = out
        samples[c['idx']] = s
        killed_count += 1

print(f'Killed (set null): {killed_count}')
print(f'Kept: {len(KEEP)}')
print(f'Total: {killed_count + len(KEEP)} (should = {len(cands)})')

# Verify
from collections import Counter
def count_with_rewrite(samples):
    return sum(1 for s in samples if s['output'].get('rewritten_query'))

print(f'\nWith-rewrite count after fix:')
print(f'  Train: {count_with_rewrite(train)} / {len(train)} ({100*count_with_rewrite(train)/len(train):.1f}%)')
print(f'  Val:   {count_with_rewrite(val)} / {len(val)} ({100*count_with_rewrite(val)/len(val):.1f}%)')

# Save
out_train = ROOT/'data/router/multitask_train_v7_1.jsonl'
out_val   = ROOT/'data/router/multitask_val_v7_1.jsonl'

with open(out_train, 'w', encoding='utf-8') as f:
    for s in train:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'\nWrote {out_train}')

with open(out_val, 'w', encoding='utf-8') as f:
    for s in val:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_val}')

# Schema check
def check(samples, name):
    errs = 0
    for s in samples:
        o = s.get('output', {})
        if set(o.keys()) != {'intent','scope','confidence','rewritten_query'}: errs += 1
    print(f'  {name}: {errs} schema errors')

print('\nSchema check:')
check(train, 'train')
check(val, 'val')
