"""Export Level B echo candidates với full data để manual review."""
import json, unicodedata, re
from pathlib import Path

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

def jaccard(a, b):
    sa, sb = set(norm(a).split()), set(norm(b).split())
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

def has_explicit_prefix(text):
    t = text.lower()
    return any(p in t for p in ('phường ', 'xã ', 'quận ', 'huyện ', 'thị xã ',
                                 'phuong ', 'xa ', 'quan ', 'huyen ', 'hà nội', 'ha noi'))

def has_time_anchor(text):
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

def extract_admin(text):
    """Extract admin entity (Phường/Xã/Quận/Huyện X)."""
    m = re.search(
        r'(Phường|Xã|Quận|Huyện|Thị xã)\s+[A-ZĐĂÂÊÔƠƯÁÀẢÃẠÉÈẺẼẸÍÌỈĨỊÓÒỎÕỌÚÙỦŨỤÝỲỶỸỴa-zđăâêôơư\s\-]+?(?=[\s,\.\?\!\(\)]|$|hôm|hiện|bây|tuần|tháng|ngày|gần|mùa|năm|và|với|đang|còn|có|nên|sẽ|để)',
        text)
    return m.group(0).strip() if m else None

train = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7_1.jsonl', encoding='utf-8')]
val   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7_1.jsonl',   encoding='utf-8')]

cands = []
for ds, samples in [('train', train), ('val', val)]:
    for i, s in enumerate(samples):
        if s.get('history'): continue  # multi-turn skip
        out = s.get('output', {})
        rewrite = out.get('rewritten_query')
        if not rewrite: continue
        inp = s.get('input', '') or ''

        if not (has_explicit_prefix(inp) or has_time_anchor(inp)): continue

        sim = jaccard(inp, rewrite)
        if sim < 0.85: continue   # Level B threshold

        len_ratio = len(rewrite) / max(1, len(inp))
        if not (0.85 <= len_ratio <= 1.15): continue  # length must be similar

        # Skip Telex-restore cases (input lowercase, rewrite TitleCase)
        if inp.lower() == inp and any(c.isupper() for c in rewrite):
            continue

        # Check admin entity match
        in_admin  = extract_admin(inp)
        rew_admin = extract_admin(rewrite)
        # If rewrite ADDED prefix that input didn't have → keep rewrite
        if rew_admin and not in_admin:
            continue

        cands.append({
            'dataset': ds, 'idx': i,
            'input': inp,
            'rewrite': rewrite,
            'jaccard': round(sim, 2),
            'len_ratio': round(len_ratio, 2),
            'intent': out.get('intent'),
            'scope': out.get('scope'),
            'conf': out.get('confidence'),
            'in_admin': in_admin,
            'rew_admin': rew_admin,
        })

print(f'Level B candidates: {len(cands)}')

# Save sorted by dataset, idx
cands.sort(key=lambda c: (c['dataset'], c['idx']))
with open(ROOT/'_v71_level_b_candidates.json', 'w', encoding='utf-8') as f:
    json.dump(cands, f, ensure_ascii=False, indent=2)
print('Saved _v71_level_b_candidates.json')

# Print all for review
for c in cands:
    print(f"[{c['dataset']}#{c['idx']}] j={c['jaccard']} lr={c['len_ratio']} intent={c['intent']}")
    print(f"  IN:  {c['input']}")
    print(f"  RW:  {c['rewrite']}")
