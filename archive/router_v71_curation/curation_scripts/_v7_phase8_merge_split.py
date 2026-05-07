"""V7 Phase 8 — Merge + stratified val split + final distribution validator.

Inputs:
- 16 manual batches (787 samples) trong data/router/v7_batches/batch_*.jsonl
- v7_keep_train.jsonl (2768) — relabel/migrate KEEP samples từ v6 train
- v7_keep_val.jsonl (295) — relabel/migrate KEEP samples từ v6 val

Outputs:
- data/router/multitask_train_v7.jsonl
- data/router/multitask_val_v7.jsonl

Strategy:
1. Pool train: KEEP_train (2768) + ~90% manual (700) = ~3470 train
2. Pool val: KEEP_val (295) + ~10% manual (87) = ~382 val
3. From manual, stratified-select for val:
   - ≥30 multi-turn samples (cover anaphora flows)
   - ≥10 collision T4 samples
   - ≥10 pure-ward samples
   - ≥10 fix-pattern samples
   - balanced across intents
4. Shuffle deterministically (seed=2026)
5. Final distribution check vs plan target.
"""
import json, random
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent
random.seed(2026)

# ── Load all manual batches ────────────────────────────────────────────────
manual = []
manual_meta = []  # parallel list of (batch_id, kind)
for i in range(1, 20):
    candidates = [
        ROOT/f'data/router/v7_batches/batch_{i:02d}_fix.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_multiturn.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_pureward.jsonl',
        ROOT/f'data/router/v7_batches/batch_{i:02d}_collision.jsonl',
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None: continue
    kind = path.stem.split('_', 2)[-1]  # fix / multiturn / pureward / collision
    with open(path, encoding='utf-8') as f:
        for line in f:
            sample = json.loads(line)
            manual.append(sample)
            manual_meta.append((i, kind))

print(f'Loaded {len(manual)} manual samples')

# ── Load KEEP samples ───────────────────────────────────────────────────────
with open(ROOT/'data/router/v7_batches/v7_keep_train.jsonl', encoding='utf-8') as f:
    keep_train = [json.loads(l) for l in f]
with open(ROOT/'data/router/v7_batches/v7_keep_val.jsonl', encoding='utf-8') as f:
    keep_val = [json.loads(l) for l in f]
print(f'KEEP train: {len(keep_train)}, KEEP val: {len(keep_val)}')

# ── Stratified select ~10% manual for val ──────────────────────────────────
# Group manual by kind
by_kind = defaultdict(list)
for idx, (batch_id, kind) in enumerate(manual_meta):
    by_kind[kind].append(idx)

# Select val targets per kind
val_target = {
    'multiturn': 30,   # ≥30 multi-turn for anaphora coverage
    'collision': 15,   # ≥15 collision T4 + switch
    'pureward': 15,    # ≥15 pure-ward
    'fix': 25,         # ≥25 from fix patterns
}

val_indices = set()
for kind, target in val_target.items():
    pool = by_kind.get(kind, [])
    # Shuffle pool deterministic
    pool_shuffled = sorted(pool)
    random.shuffle(pool_shuffled)
    selected = pool_shuffled[:target]
    val_indices.update(selected)

print(f'Selected {len(val_indices)} manual samples for val')

# Split manual
manual_for_val = [manual[i] for i in val_indices]
manual_for_train = [manual[i] for i in range(len(manual)) if i not in val_indices]

# ── Merge ─────────────────────────────────────────────────────────────────
final_train = keep_train + manual_for_train
final_val = keep_val + manual_for_val

# Shuffle deterministically
random.shuffle(final_train)
random.shuffle(final_val)

print(f'\nFinal train: {len(final_train)} samples')
print(f'Final val:   {len(final_val)} samples')
print(f'Total:       {len(final_train) + len(final_val)}')

# ── Distribution validator ─────────────────────────────────────────────────
def report(name, samples, plan_targets):
    print(f'\n## {name}: {len(samples)} samples')
    n = len(samples)
    tier = Counter(s['output']['confidence'] for s in samples)
    scope = Counter(s['output']['scope'] for s in samples)
    intent = Counter(s['output']['intent'] for s in samples)
    turn = Counter(len(s['history']) + 1 for s in samples)

    print('  Tier:')
    for c in sorted(tier, reverse=True):
        label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}.get(c, '?')
        pct = 100*tier[c]/n
        target = plan_targets['tier'].get(label, 0)
        delta = pct - target
        print(f'    {label} {c}: {tier[c]:5d} ({pct:5.1f}%)  target {target}%  delta {delta:+.1f}pp')

    print('  Scope:')
    for s in ('city','district','ward'):
        pct = 100*scope[s]/n
        target = plan_targets['scope'].get(s, 0)
        print(f'    {s:<10} {scope[s]:5d} ({pct:5.1f}%)  target {target}%')

    print('  Turn:')
    for t in sorted(turn):
        print(f'    turn={t}: {turn[t]:5d} ({100*turn[t]/n:.1f}%)')

    print('  Intent (15):')
    for it in sorted(intent):
        print(f'    {it:<25} {intent[it]:4d} ({100*intent[it]/n:.1f}%)')

plan = {
    'tier': {'T1': 28, 'T2': 28, 'T3': 18, 'T4': 12, 'T5': 14},
    'scope': {'city': 20, 'district': 35, 'ward': 45},
}
report('TRAIN', final_train, plan)
report('VAL', final_val, plan)

# ── Write final files ──────────────────────────────────────────────────────
out_train = ROOT/'data/router/multitask_train_v7.jsonl'
with open(out_train, 'w', encoding='utf-8') as f:
    for s in final_train:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'\nWrote {out_train}')

out_val = ROOT/'data/router/multitask_val_v7.jsonl'
with open(out_val, 'w', encoding='utf-8') as f:
    for s in final_val:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_val}')

# ── Schema sanity ──────────────────────────────────────────────────────────
def schema_check(samples, name):
    errs = 0
    for i, s in enumerate(samples):
        if 'history' not in s or not isinstance(s['history'], list): errs += 1
        if 'input' not in s or not s['input']: errs += 1
        if 'output' not in s: errs += 1; continue
        o = s['output']
        if set(o.keys()) != {'intent','scope','confidence','rewritten_query'}: errs += 1
        if len(s['history']) > 3: errs += 1  # K=3 max
    print(f'  {name}: schema errors = {errs}')

print('\nFinal schema check:')
schema_check(final_train, 'train')
schema_check(final_val, 'val')
