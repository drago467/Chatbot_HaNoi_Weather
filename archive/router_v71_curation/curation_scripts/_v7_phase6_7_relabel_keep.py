"""V7 Phase 6+7 — Rule-based relabel + migrate KEEP samples from v6 → v7.

Phase 6: Recalibrate confidence for 2768 KEEP_RELABEL samples per 5-tier scheme.
Phase 7: Migrate v6 `context` dict → v7 `history` list (fabricate prior turn for
multi-turn samples from context, set history=[] for single-turn).

Tier assignment rule:
- smalltalk_weather intent → T5=0.62
- has rewrite + ctx with turn≥1 → T3=0.80 (multi-turn inherited)
- input contains bare collision core (no Phường/Xã/Quận/Huyện prefix) → T4=0.74
- has rewrite single-turn (no ctx) → T2=0.85
- no rewrite + scope=city or no entity → T2=0.85
- no rewrite + explicit prefix in input → T1=0.92
- else default → T2=0.85

Input:  data/router/multitask_train_v6_clean.jsonl + multitask_val_v6_clean.jsonl
        _v7_categorization.json (categorization tags)
Output: data/router/v7_batches/v7_keep_train.jsonl + v7_keep_val.jsonl
"""
import json, csv, re, unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

# ── Load canonical for collision detection ─────────────────────────────────
WARDS = {}
DISTRICTS = {}
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

# ── Tier assignment ─────────────────────────────────────────────────────────
def has_explicit_prefix(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in ('phường ', 'xã ', 'quận ', 'huyện ', 'thị xã '))

def has_bare_collision(text: str) -> bool:
    """Check if text contains a collision core WITHOUT explicit prefix."""
    text_n = norm(text)
    for core in COLLISION:
        if re.search(rf'\b{re.escape(core)}\b', text_n):
            # has core, check if explicit prefix used
            for prefix in ('phuong', 'xa', 'quan', 'huyen', 'thi xa'):
                if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', text_n):
                    return False  # explicit, not bare
            return True
    return False

def assign_tier(sample: dict) -> tuple[str, float]:
    """Return (tier_label, confidence)."""
    out = sample.get('output', {})
    intent = out.get('intent', '')
    has_rewrite = bool(out.get('rewritten_query'))
    ctx = sample.get('context')
    inp = sample.get('input', '') or ''

    # T5: smalltalk
    if intent == 'smalltalk_weather':
        return ('T5', 0.62)

    # T3: multi-turn (has context with turn ≥ 1)
    if ctx and ctx.get('turn', 0) >= 1:
        return ('T3', 0.80)

    # T4: bare collision core in input (single-turn)
    if has_bare_collision(inp):
        return ('T4', 0.74)

    # T2: rewrite added without context (default time/scope inferred)
    if has_rewrite:
        return ('T2', 0.85)

    # T2: city scope without explicit entity (just "Hà Nội" or no entity)
    if out.get('scope') == 'city' and not has_explicit_prefix(inp):
        # Only T2 if input has time-default needed
        if any(t in inp.lower() for t in ('hôm nay', 'bây giờ', 'hiện tại')):
            return ('T1', 0.92)  # has time anchor
        return ('T2', 0.85)

    # T1: explicit prefix + full info
    if has_explicit_prefix(inp):
        return ('T1', 0.92)

    # Default fallback T2
    return ('T2', 0.85)

# ── Migrate v6 context → v7 history ─────────────────────────────────────────
def fabricate_prior_turn(ctx: dict, current_output: dict) -> list[dict]:
    """For samples with v6 context (multi-turn implied), fabricate turn-1 history."""
    if not ctx:
        return []
    loc = ctx.get('location') or 'Hà Nội'
    prior_intent = ctx.get('intent') or 'current_weather'
    cur_scope = current_output.get('scope', 'city')

    # Determine prior scope from location entity
    loc_n = norm(loc)
    has_explicit = has_explicit_prefix(loc)

    if loc.strip().lower() in ('hà nội', 'hanoi'):
        prior_scope = 'city'
        prior_loc_full = 'Hà Nội'
    elif has_explicit:
        # Already has prefix in v6 context (rare)
        prior_loc_full = loc.strip()
        prior_scope = 'ward' if any(p in loc.lower() for p in ('phường', 'xã'))             else 'district' if any(p in loc.lower() for p in ('quận', 'huyện', 'thị xã'))             else cur_scope
    else:
        # Bare core — infer prefix per current_scope canonical
        if cur_scope == 'ward' and loc_n in WARDS:
            prefix_norm, full_name = WARDS[loc_n]
            prior_loc_full = full_name
            prior_scope = 'ward'
        elif cur_scope == 'district' and loc_n in DISTRICTS:
            prefix_norm, full_name = DISTRICTS[loc_n]
            prior_loc_full = full_name
            prior_scope = 'district'
        elif loc_n in COLLISION:
            # Default to ward (post-merger primary)
            _, full_name = WARDS[loc_n]
            prior_loc_full = full_name
            prior_scope = 'ward'
        elif loc_n in WARDS:
            _, full_name = WARDS[loc_n]
            prior_loc_full = full_name
            prior_scope = 'ward'
        elif loc_n in DISTRICTS:
            _, full_name = DISTRICTS[loc_n]
            prior_loc_full = full_name
            prior_scope = 'district'
        else:
            # Unknown location — use as-is
            prior_loc_full = loc.strip()
            prior_scope = cur_scope

    prior_user = f"{prior_loc_full} hôm nay thời tiết thế nào?"
    if prior_scope == 'city':
        prior_rewrite = f"Thời tiết {prior_loc_full} hôm nay thế nào?"
    else:
        prior_rewrite = f"Thời tiết {prior_loc_full} hôm nay thế nào?"
    prior_assistant = json.dumps({
        "intent": prior_intent if prior_intent else "current_weather",
        "scope": prior_scope,
        "confidence": 0.85,
        "rewritten_query": prior_rewrite,
    }, ensure_ascii=False, separators=(',', ':'))

    return [{"user": prior_user, "assistant": prior_assistant}]

# ── Process a sample ───────────────────────────────────────────────────────
def process_keep(sample: dict, tag_info: dict | None) -> dict | None:
    """Convert v6 KEEP sample to v7 schema. Return None if must be dropped."""
    if tag_info and tag_info.get('tag') == 'DROP_POI':
        return None

    out = dict(sample.get('output', {}))
    ctx = sample.get('context')

    # Tier relabel
    tier, conf = assign_tier(sample)
    out['confidence'] = conf

    # Strip rewrite for T5 (smalltalk should not have rewrite per plan)
    if tier == 'T5' and out.get('intent') == 'smalltalk_weather':
        out['rewritten_query'] = None

    # Ensure 4 keys core only
    keys = {'intent', 'scope', 'confidence', 'rewritten_query'}
    out = {k: out.get(k) for k in keys}

    # Migrate context → history
    history = fabricate_prior_turn(ctx, out)

    return {
        "history": history,
        "input": sample.get('input', ''),
        "output": out,
    }

# ── Run on train + val ──────────────────────────────────────────────────────
cat = json.load(open(ROOT/'_v7_categorization.json', encoding='utf-8'))

def process_file(in_path: Path, cat_section: str) -> list:
    with open(in_path, encoding='utf-8') as f:
        rows = [json.loads(l) for l in f]
    tag_by_idx = {t['idx']: t for t in cat[cat_section]['samples']}

    out_samples = []
    drop_count = 0
    fix_count = 0
    keep_count = 0
    for i, sample in enumerate(rows):
        info = tag_by_idx.get(i, {})
        tag = info.get('tag', '')

        # DROP_POI: skip
        if tag == 'DROP_POI':
            drop_count += 1
            continue

        # FIX_*: skip — these are handled by manual batches 1-7 for train
        # (val FIX samples will be handled separately)
        if tag.startswith('FIX'):
            fix_count += 1
            continue

        # KEEP_RELABEL: process
        v7 = process_keep(sample, info)
        if v7:
            out_samples.append(v7)
            keep_count += 1
    return out_samples, {'drop_poi': drop_count, 'fix_skip': fix_count, 'keep': keep_count}

train_v7, train_stats = process_file(ROOT/'data/router/multitask_train_v6_clean.jsonl', 'train')
val_v7, val_stats = process_file(ROOT/'data/router/multitask_val_v6_clean.jsonl', 'val')

print(f'Train: {train_stats}')
print(f'Val:   {val_stats}')

# Save
out_train = ROOT/'data/router/v7_batches/v7_keep_train.jsonl'
with open(out_train, 'w', encoding='utf-8') as f:
    for s in train_v7:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_train} ({len(train_v7)} KEEP samples)')

out_val = ROOT/'data/router/v7_batches/v7_keep_val.jsonl'
with open(out_val, 'w', encoding='utf-8') as f:
    for s in val_v7:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'Wrote {out_val} ({len(val_v7)} KEEP samples)')

# Audit tier distribution
all_keep = train_v7 + val_v7
tier_dist = Counter(s['output']['confidence'] for s in all_keep)
scope_dist = Counter(s['output']['scope'] for s in all_keep)
turn_dist = Counter(len(s['history']) + 1 for s in all_keep)
intent_dist = Counter(s['output']['intent'] for s in all_keep)

print(f'\nKEEP samples confidence distribution:')
for c in sorted(tier_dist, reverse=True):
    n = tier_dist[c]
    label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}.get(c, '?')
    print(f'  {label} ({c}): {n:4d}  ({100*n/len(all_keep):.1f}%)')

print(f'\nKEEP scope distribution:')
for s in sorted(scope_dist):
    print(f'  {s}: {scope_dist[s]:4d}  ({100*scope_dist[s]/len(all_keep):.1f}%)')

print(f'\nKEEP turn distribution:')
for t in sorted(turn_dist):
    print(f'  turn={t}: {turn_dist[t]:4d}')

print(f'\nKEEP intent distribution:')
for i in sorted(intent_dist):
    print(f'  {i}: {intent_dist[i]:4d}')
