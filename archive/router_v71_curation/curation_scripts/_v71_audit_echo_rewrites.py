"""Audit single-turn samples có echo rewrite không cần thiết.

Pattern cần fix (rewrite=null):
- history = [] (single-turn)
- input đã đầy đủ prefix admin (Phường/Xã/Quận/Huyện/Thị xã/Hà Nội)
- input đã có time anchor (hôm nay/ngày mai/...)
- rewrite chỉ echo lại input (không thêm thông tin gì mới)

Pattern KHÔNG fix (rewrite cần thiết):
- input thiếu prefix → rewrite thêm prefix (vd "Cầu Giấy" → "Phường Cầu Giấy")
- input thiếu city/time default → rewrite thêm
- input Telex/lowercase → rewrite restore diacritics + capitalize
- multi-turn (history non-empty)
"""
import json, re, unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

def has_explicit_prefix(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in (
        'phường ', 'xã ', 'quận ', 'huyện ', 'thị xã ',
        'phuong ', 'xa ', 'quan ', 'huyen ',  # Telex
        'hà nội', 'ha noi',
    ))

def has_time_anchor(text: str) -> bool:
    t = norm(text)
    return any(a in t for a in (
        'hom nay', 'ngay mai', 'ngay kia', 'hom qua', 'hom kia',
        'tuan nay', 'tuan sau', 'tuan toi', 'tuan truoc',
        'thang nay', 'thang sau', 'thang truoc',
        'hien tai', 'bay gio', 'luc nay', 'gio nay',
        'sang nay', 'chieu nay', 'toi nay', 'dem nay',
        'sang mai', 'chieu mai', 'toi mai', 'dem mai',
        'cuoi tuan', 'mua nay',
    ))

def jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard on normalized text."""
    sa = set(norm(a).split())
    sb = set(norm(b).split())
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

# ── Load v7.1 ───────────────────────────────────────────────────────────────
train = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7_1.jsonl', encoding='utf-8')]
val   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7_1.jsonl',   encoding='utf-8')]
print(f'Loaded train={len(train)} val={len(val)}')

candidates = []  # (dataset, idx, sample, jaccard, reason)

for dataset, samples in [('train', train), ('val', val)]:
    for i, s in enumerate(samples):
        if s.get('history'):
            continue  # multi-turn — rewrite needed
        out = s.get('output', {})
        rewrite = out.get('rewritten_query')
        if not rewrite:
            continue  # already null
        inp = s.get('input', '') or ''

        # Check completeness
        has_prefix = has_explicit_prefix(inp)
        has_time   = has_time_anchor(inp)
        if not (has_prefix or has_time):
            continue  # might need default fill, keep rewrite

        # Check if rewrite is similar to input (echo)
        sim = jaccard_similarity(inp, rewrite)
        # Echo threshold: jaccard ≥ 0.6 (most words overlap)
        if sim < 0.6:
            continue

        # Check if rewrite adds prefix (input has bare entity, rewrite explicit)
        # If input lowercase + rewrite has TitleCase prefix, it's diacritic restore — KEEP
        if inp.lower() == inp and any(c.isupper() for c in rewrite):
            # Likely Telex restore
            continue

        # Likely echo
        candidates.append({
            'dataset': dataset,
            'idx': i,
            'input': inp,
            'rewrite': rewrite,
            'jaccard': round(sim, 2),
            'has_prefix': has_prefix,
            'has_time': has_time,
            'output': out,
        })

print(f'\nEcho-rewrite candidates: {len(candidates)}')

# Show distribution by intent + scope
by_intent = Counter(c['output']['intent'] for c in candidates)
by_scope  = Counter(c['output']['scope'] for c in candidates)
by_conf   = Counter(c['output']['confidence'] for c in candidates)
print('By intent:')
for i, n in by_intent.most_common():
    print(f'  {i}: {n}')
print('By scope:', dict(by_scope))
print('By tier confidence:', dict(by_conf))

# Show samples
print('\nFirst 15 echo candidates:')
for c in candidates[:15]:
    print(f"  [{c['dataset']}#{c['idx']}] j={c['jaccard']} intent={c['output']['intent']}")
    print(f"    input:   '{c['input'][:80]}'")
    print(f"    rewrite: '{c['rewrite'][:80]}'")

# Save for review
out = ROOT / '_v71_echo_candidates.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(candidates, f, ensure_ascii=False, indent=2)
print(f'\nSaved {out} ({len(candidates)} candidates)')
