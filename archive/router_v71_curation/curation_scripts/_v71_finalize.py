"""V7.1 finalize — merge fixed v7 + batch 17 disambig → final v7.1 train/val.

Inputs:
- data/router/multitask_train_v7_1.jsonl (3470, 71 fixes applied)
- data/router/multitask_val_v7_1.jsonl   (380)
- data/router/v7_batches/batch_17_disambig.jsonl (50 new disambig)

Strategy:
- Manual fixes already in v7_1 train+val
- Batch 17 disambig: split 90/10 → 45 train + 5 val
- Stratified split (mostly same intent groups)
- Output FINAL v7.1 files

Outputs:
- data/router/multitask_train_v7_1.jsonl  (3515 = 3470 + 45)
- data/router/multitask_val_v7_1.jsonl   (385 = 380 + 5)
"""
import json, random
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
random.seed(2026)

# ── Load inputs ─────────────────────────────────────────────────────────────
train_v71 = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7_1.jsonl', encoding='utf-8')]
val_v71   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7_1.jsonl',   encoding='utf-8')]
disambig  = [json.loads(l) for l in open(ROOT/'data/router/v7_batches/batch_17_disambig.jsonl', encoding='utf-8')]

print(f'Train v7_1 (with fixes): {len(train_v71)}')
print(f'Val v7_1 (with fixes):   {len(val_v71)}')
print(f'Batch 17 disambig:       {len(disambig)}')

# ── Split disambig 90/10 → 45 train + 5 val ─────────────────────────────────
random.shuffle(disambig)
disambig_val   = disambig[:5]
disambig_train = disambig[5:]
print(f'Disambig split: {len(disambig_train)} train + {len(disambig_val)} val')

# ── Merge ──────────────────────────────────────────────────────────────────
final_train = train_v71 + disambig_train
final_val   = val_v71 + disambig_val
random.shuffle(final_train)
random.shuffle(final_val)

print(f'\nFinal train: {len(final_train)}')
print(f'Final val:   {len(final_val)}')

# ── Distribution ───────────────────────────────────────────────────────────
def report(name, samples):
    print(f'\n=== {name}: {len(samples)} ===')
    n = len(samples)
    tier = Counter(s['output']['confidence'] for s in samples)
    scope = Counter(s['output']['scope'] for s in samples)
    intent = Counter(s['output']['intent'] for s in samples)
    turn = Counter(len(s['history']) + 1 for s in samples)

    print('  Tier:')
    for c in sorted(tier, reverse=True):
        label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}.get(c, '?')
        print(f'    {label} {c}: {tier[c]:5d} ({100*tier[c]/n:.1f}%)')

    print('  Scope:')
    for s in ('city','district','ward'):
        print(f'    {s:<10} {scope[s]:5d} ({100*scope[s]/n:.1f}%)')

    print('  Turn:')
    for t in sorted(turn):
        print(f'    turn={t}: {turn[t]:5d}')

    print('  Intent (15):')
    for it in sorted(intent):
        print(f'    {it:<25} {intent[it]:4d}')

report('TRAIN v7.1', final_train)
report('VAL v7.1', final_val)

# ── Schema check ───────────────────────────────────────────────────────────
def schema_check(samples, name):
    errs = 0
    for i, s in enumerate(samples):
        if 'history' not in s or not isinstance(s['history'], list): errs += 1
        if 'input' not in s or not s['input']: errs += 1
        if 'output' not in s: errs += 1; continue
        o = s['output']
        if set(o.keys()) != {'intent','scope','confidence','rewritten_query'}: errs += 1
        if len(s['history']) > 3: errs += 1
    print(f'  {name}: schema errors = {errs}')

print('\nSchema check:')
schema_check(final_train, 'train')
schema_check(final_val, 'val')

# ── Write final files (overwrite intermediate v7_1) ────────────────────────
out_train = ROOT/'data/router/multitask_train_v7_1.jsonl'
out_val   = ROOT/'data/router/multitask_val_v7_1.jsonl'

with open(out_train, 'w', encoding='utf-8') as f:
    for s in final_train:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'\nWrote {out_train}')

with open(out_val, 'w', encoding='utf-8') as f:
    for s in final_val:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_val}')
