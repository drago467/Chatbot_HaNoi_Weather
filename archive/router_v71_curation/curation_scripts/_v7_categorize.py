"""Phase 1 v7 — Categorize each v6 sample as KEEP-RELABEL / FIX / DROP.

Per-sample tags follow plan v7 'Hiến pháp':
- KEEP-RELABEL: passes prefix/scope/time check, only needs confidence relabel + schema migrate
- FIX-PREFIX:   collision core with wrong prefix in rewritten_query (Issue A/B/C from audit)
- FIX-TIME:     time-drift in single-turn rewrite (Issue D)
- FIX-CONTEXT:  context.location prefix-stripped on collision core, ambiguous
- DROP:         smalltalk with junk context, or sample inconsistent beyond salvage

Reads:
- data/processed/dim_ward.csv
- data/router/multitask_train_v6_clean.jsonl
- data/router/multitask_val_v6_clean.jsonl

Writes:
- _v7_categorization.json (full per-sample tags + summary stats)
"""
import json
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent

# ── Normalization ────────────────────────────────────────────────────────────
def norm(s: str) -> str:
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('Đ', 'd').replace('đ', 'd')
    return s.lower().strip()

# ── Load canonical authority ─────────────────────────────────────────────────
WARDS = {}      # core_norm -> {prefix, full_name, district_full}
DISTRICTS = {}  # core_norm -> {prefix, full_name}

with open(ROOT / 'data/processed/dim_ward.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        core = r['ward_name_core_norm']
        WARDS[core] = {
            'prefix': r['ward_prefix_norm'],
            'full': r['ward_name_vi'],
            'district_full': r['district_name_vi'],
        }
        d_full = (r['district_name_vi'] or '').strip()
        if not d_full:
            continue
        parts = d_full.split()
        if parts[0].lower() == 'thị' and len(parts) >= 2 and parts[1].lower() == 'xã':
            d_prefix = 'thi xa'
            d_core = ' '.join(parts[2:])
        else:
            d_prefix = norm(parts[0])
            d_core = ' '.join(parts[1:])
        DISTRICTS[norm(d_core)] = {'prefix': d_prefix, 'full': d_full}

COLLISION_CORES = set(WARDS) & set(DISTRICTS)
PURE_WARDS = set(WARDS) - COLLISION_CORES
PURE_DISTRICTS = set(DISTRICTS) - COLLISION_CORES

# POI list reconstructed from deleted poi_mapping.json (commit 02c46eb~1)
# Filter: only names NOT colliding with current admin (dim_ward post-merger).
# 'Văn Miếu', 'Nội Bài', 'Bạch Mai' became ward names → exclude from POI-only list.
POI_PHRASES_RAW = [
    "Hồ Gươm", "Hồ Hoàn Kiếm", "Bờ Hồ", "Phố cổ", "Phố cổ Hà Nội",
    "Nhà thờ Lớn",
    "Mỹ Đình",  # NOT admin; refers to stadium/area
    "Sân Mỹ Đình", "Bến xe Mỹ Đình", "Keangnam",
    "Hồ Tây",
    "Chùa Trấn Quốc",
    "Sân bay Nội Bài",
    "Times City", "ĐH Bách Khoa", "Đại học Bách Khoa",
    "Công viên Cầu Giấy", "ĐH Quốc Gia", "Đại học Quốc Gia",
    "Văn Miếu - Quốc Tử Giám",  # specifically the landmark phrase
    "Bệnh viện Bạch Mai",
    "Lăng Bác", "Lăng Chủ tịch", "Hồ Trúc Bạch",
    "Royal City",
    "Hồ Linh Đàm", "Bến xe Giáp Bát",
    "Cầu Long Biên",  # the bridge, NOT Quận Long Biên
    "Cao tốc Pháp Vân",
    "Ga Hà Nội",
    "Nhà hát Lớn",
    "Chợ Đồng Xuân",
    "Trung tâm Hội nghị Quốc gia",
    "Aeon Mall Long Biên",
    # Common patterns from v6 not in mapping but POI-style
    "Ngọc Hà", "Lăng", "Nhà thờ", "Bờ hồ",
]
POI_PHRASES_NORM = [norm(p) for p in POI_PHRASES_RAW]

print(f'Canonical: {len(WARDS)} wards, {len(DISTRICTS)} districts')
print(f'  Collision cores: {len(COLLISION_CORES)}')
print(f'  Pure wards: {len(PURE_WARDS)}')
print(f'  Pure districts: {len(PURE_DISTRICTS)}')
print(f'  POI phrases: {len(POI_PHRASES_NORM)}')

# ── Categorization rules ─────────────────────────────────────────────────────
def find_ward_in_rewrite(rew_n: str) -> tuple[str, str] | None:
    """Return (core, used_prefix) if a ward-core is found with a prefix in rewrite."""
    for core in WARDS:
        for prefix in ('phuong', 'xa'):
            if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', rew_n):
                return (core, prefix)
        for prefix in ('quan', 'huyen'):
            if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', rew_n):
                return (core, prefix)
    return None

def find_district_in_rewrite(rew_n: str) -> tuple[str, str] | None:
    """Return (core, used_prefix) if a district-core is found in rewrite."""
    for core in DISTRICTS:
        for prefix in ('quan', 'huyen', 'thi xa'):
            if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', rew_n):
                return (core, prefix)
    return None

def detect_admin_in_text(text_n: str) -> list[tuple[str, str]]:
    """Find admin name occurrences in normalized text.
    Returns list of (kind, full_name) where kind in {'ward', 'district', 'collision'}.
    """
    hits = []
    for core, info in WARDS.items():
        # Match with explicit prefix to be confident
        for prefix in ('phuong', 'xa'):
            if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', text_n):
                kind = 'collision' if core in COLLISION_CORES else 'ward'
                hits.append((kind, info['full']))
                break
    for core, info in DISTRICTS.items():
        for prefix in ('quan', 'huyen', 'thi xa'):
            if re.search(rf'\b{prefix}\s+{re.escape(core)}\b', text_n):
                kind = 'collision' if core in COLLISION_CORES else 'district'
                hits.append((kind, info['full']))
                break
    # Bare core names (no prefix) — only count pure wards/districts to avoid
    # collision-core ambiguity contaminating "has admin context" check.
    bare_admin_cores = (PURE_WARDS | PURE_DISTRICTS)
    for core in bare_admin_cores:
        if re.search(rf'\b{re.escape(core)}\b', text_n):
            if core in PURE_WARDS:
                hits.append(('ward', WARDS[core]['full']))
            else:
                hits.append(('district', DISTRICTS[core]['full']))
    return hits

def detect_poi(text: str) -> list[str]:
    """Return list of POI phrases found in text (case/accent-insensitive)."""
    text_n = norm(text)
    found = []
    for poi_n, poi_raw in zip(POI_PHRASES_NORM, POI_PHRASES_RAW):
        # Use word-boundary match
        if re.search(rf'\b{re.escape(poi_n)}\b', text_n):
            found.append(poi_raw)
    return found

def detect_time_drift(input_text: str, rewrite: str) -> str | None:
    """Return drift description if input has explicit time marker but rewrite drifts."""
    inp_n = norm(input_text)
    rew_n = norm(rewrite)
    pairs = [
        ('tuan sau',   ['tuan sau'],             ['tuan nay', 'tuan truoc']),
        ('tuan toi',   ['tuan toi', 'tuan sau'], ['tuan nay']),
        ('thang sau',  ['thang sau','thang toi'],['thang nay']),
        ('ngay mai',   ['ngay mai'],             ['hom nay']),
        ('ngay kia',   ['ngay kia'],             ['hom nay', 'ngay mai']),
        ('hom qua',    ['hom qua'],              ['hom nay']),
        ('tuan truoc', ['tuan truoc'],           ['tuan nay']),
    ]
    for trig, must_be, must_not in pairs:
        if trig in inp_n:
            preserved = any(m in rew_n for m in must_be)
            drifted = any(m in rew_n for m in must_not)
            if (not preserved) or drifted:
                return f"input has '{trig}' | preserved={preserved} drifted={drifted}"
    return None

def categorize(sample: dict) -> dict:
    """Return tag info for a sample. Does NOT modify sample."""
    out = sample.get('output', {})
    ctx = sample.get('context')
    has_rewrite = bool(out.get('rewritten_query'))
    intent = out.get('intent', '')
    scope = out.get('scope', '')
    inp = sample.get('input', '') or ''

    issues = []
    rationale_bits = []

    # ── POI detection (P8/P9 policy: POI banned from admin auto-resolve) ──
    poi_hits = detect_poi(inp)
    admin_hits = detect_admin_in_text(norm(inp))
    pure_admin_hits = [h for h in admin_hits if h[0] in ('ward', 'district')]
    if poi_hits:
        if pure_admin_hits:
            # POI + admin: extract admin, drop POI
            issues.append('poi_with_admin_context')
            rationale_bits.append(
                f"input contains POI {poi_hits} AND admin {pure_admin_hits[:2]}; "
                "v7: keep admin scope, T2 confidence, rewrite uses admin only"
            )
        else:
            # Pure POI: refuse + clarify pattern
            issues.append('pure_poi_input')
            rationale_bits.append(
                f"input contains POI {poi_hits} only (no admin context); "
                "v7: scope=ward, T5=0.62, rewrite=null → trigger downstream clarification"
            )

    # Audit rewrite samples for prefix/scope/time errors
    if has_rewrite:
        rew = out['rewritten_query']
        rew_n = norm(rew)

        # Issue A/B: wrong prefix on canonical name
        ward_hit = find_ward_in_rewrite(rew_n)
        if ward_hit:
            core, used_prefix = ward_hit
            canonical = WARDS[core]['prefix']
            # check ward-prefix correctness
            if used_prefix in ('phuong', 'xa') and used_prefix != canonical:
                issues.append('wrong_ward_prefix')
                rationale_bits.append(
                    f"ward '{core}' canonical='{canonical}' but rewrite uses '{used_prefix}'"
                )
            # ward core with district prefix → Issue C
            if used_prefix in ('quan', 'huyen'):
                if core in COLLISION_CORES:
                    # Maybe legit district reference if scope=district
                    if scope == 'district':
                        canonical_d = DISTRICTS[core]['prefix']
                        if used_prefix != canonical_d:
                            issues.append('wrong_district_prefix_collision')
                            rationale_bits.append(
                                f"collision core '{core}' as district, "
                                f"canonical='{canonical_d}' but used '{used_prefix}'"
                            )
                    else:
                        issues.append('ward_with_district_prefix')
                        rationale_bits.append(
                            f"collision core '{core}' rewritten as '{used_prefix} X' "
                            f"but scope={scope} (should be 'phuong/xa X')"
                        )
                else:
                    issues.append('pure_ward_with_district_prefix')
                    rationale_bits.append(
                        f"pure ward '{core}' rewritten as '{used_prefix} X' "
                        "(no canonical district exists with this name)"
                    )

        # Issue B: wrong district prefix (only if no ward hit at all OR scope=district)
        if not ward_hit or scope == 'district':
            d_hit = find_district_in_rewrite(rew_n)
            if d_hit:
                core, used_prefix = d_hit
                canonical = DISTRICTS[core]['prefix']
                if used_prefix != canonical:
                    if 'wrong_district_prefix_collision' not in issues:
                        issues.append('wrong_district_prefix')
                        rationale_bits.append(
                            f"district '{core}' canonical='{canonical}' but used '{used_prefix}'"
                        )

        # Issue D: time drift (single-turn only — multi-turn drift is in input semantics)
        drift = detect_time_drift(sample.get('input', ''), rew)
        if drift:
            issues.append('time_drift')
            rationale_bits.append(drift)

        # Context.location prefix-stripped on collision core
        if ctx and ctx.get('location'):
            loc_n = norm(ctx['location'])
            if loc_n in COLLISION_CORES:
                # Check if location string includes prefix
                full_loc = ctx['location'].strip().lower()
                if not (full_loc.startswith('phường') or full_loc.startswith('xã')
                        or full_loc.startswith('quận') or full_loc.startswith('huyện')
                        or full_loc.startswith('thị xã')):
                    issues.append('context_loc_no_prefix_collision')
                    rationale_bits.append(
                        f"context.location='{ctx['location']}' is collision core "
                        "without prefix → ambiguous between phường/quận"
                    )

    # ── Determine tier (5-tier confidence scheme from plan) ─────────────────
    if intent == 'smalltalk_weather':
        tier = 'T5'  # 0.62
    elif has_rewrite and ctx and (ctx.get('turn', 0) >= 1):
        tier = 'T3'  # 0.80 multi-turn inherited
    elif has_rewrite:
        # Rewrite without prior turn = inferring something
        tier = 'T2'  # 0.85
    elif scope == 'city' and not ctx:
        tier = 'T2'  # default city
    elif intent in ('weather_alert', 'activity_weather'):
        # often borderline ambiguous
        tier = 'T2'
    else:
        # Direct query, full info
        tier = 'T1'  # 0.92

    # Detect collision-decided ambiguity → T4
    inp_n = norm(sample.get('input', ''))
    for core in COLLISION_CORES:
        if re.search(rf'\b{re.escape(core)}\b', inp_n):
            inp_l = sample['input'].lower()
            has_explicit = any(p in inp_l for p in ('phường', 'xã', 'quận', 'huyện', 'thị xã'))
            if not has_explicit:
                tier = 'T4'  # 0.74 ambiguous
            break

    # ── Final tag decision (POI takes priority — sample-level intent) ──────
    if 'pure_poi_input' in issues:
        tag = 'DROP_POI'  # hybrid policy (c): drop pure POI samples
        tier = 'T5'
        rationale = '; '.join(rationale_bits)
    elif 'poi_with_admin_context' in issues:
        tag = 'FIX_POI_ADMIN'  # hybrid policy (c): rewrite to extract admin only
        tier = 'T2'
        rationale = '; '.join(rationale_bits)
    elif not issues:
        tag = 'KEEP_RELABEL'
        rationale = f"Pass all checks; tier={tier}"
    elif any(i.startswith('pure_ward') for i in issues):
        tag = 'FIX_PREFIX'
        rationale = '; '.join(rationale_bits)
    elif any(i in ('ward_with_district_prefix', 'wrong_district_prefix',
                   'wrong_district_prefix_collision', 'wrong_ward_prefix')
             for i in issues):
        tag = 'FIX_PREFIX'
        rationale = '; '.join(rationale_bits)
    elif 'time_drift' in issues:
        tag = 'FIX_TIME'
        rationale = '; '.join(rationale_bits)
    elif 'context_loc_no_prefix_collision' in issues:
        tag = 'FIX_CONTEXT'
        rationale = '; '.join(rationale_bits)
    else:
        tag = 'KEEP_RELABEL'
        rationale = f"Minor issues, salvageable; tier={tier}"

    return {
        'tag': tag,
        'tier': tier,
        'issues': issues,
        'rationale': rationale,
    }

# ── Run categorization on train + val ────────────────────────────────────────
def categorize_file(path: Path) -> tuple[list, dict]:
    with open(path, encoding='utf-8') as f:
        rows = [json.loads(l) for l in f]
    tagged = []
    for i, sample in enumerate(rows):
        info = categorize(sample)
        tagged.append({
            'idx': i,
            'input': sample.get('input', '')[:120],
            'context': sample.get('context'),
            'has_rewrite': bool(sample.get('output', {}).get('rewritten_query')),
            'intent': sample['output'].get('intent'),
            'scope': sample['output'].get('scope'),
            'old_confidence': sample['output'].get('confidence'),
            **info,
        })
    summary = {
        'total': len(tagged),
        'tag_counts': dict(Counter(t['tag'] for t in tagged)),
        'tier_counts': dict(Counter(t['tier'] for t in tagged)),
        'issue_counts': dict(Counter(
            issue for t in tagged for issue in t['issues']
        )),
    }
    return tagged, summary

train_tagged, train_summary = categorize_file(ROOT / 'data/router/multitask_train_v6_clean.jsonl')
val_tagged,   val_summary   = categorize_file(ROOT / 'data/router/multitask_val_v6_clean.jsonl')

# ── Write output ────────────────────────────────────────────────────────────
output = {
    'spec_version': 'v7-phase1',
    'tier_definitions': {
        'T1': {'confidence': 0.92, 'desc': 'Unambiguous direct query'},
        'T2': {'confidence': 0.85, 'desc': 'Standard inference (default city/time)'},
        'T3': {'confidence': 0.80, 'desc': 'Multi-turn inherited anchor'},
        'T4': {'confidence': 0.74, 'desc': 'Ambiguous-but-decided (collision core, scope hint)'},
        'T5': {'confidence': 0.62, 'desc': 'Smalltalk / OOD / abstain candidate'},
    },
    'train': {'summary': train_summary, 'samples': train_tagged},
    'val':   {'summary': val_summary,   'samples': val_tagged},
}

out_path = ROOT / '_v7_categorization.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\nWrote {out_path}')
print(f'Train summary: {train_summary["total"]} samples')
for tag, n in sorted(train_summary['tag_counts'].items()):
    print(f'  {tag:<20} {n:>5}  ({100*n/train_summary["total"]:.1f}%)')
print('Train tier distribution:')
for tier, n in sorted(train_summary['tier_counts'].items()):
    print(f'  {tier}: {n:>5}  ({100*n/train_summary["total"]:.1f}%)')
print('Issue counts:')
for issue, n in sorted(train_summary['issue_counts'].items(), key=lambda x: -x[1]):
    print(f'  {issue:<40} {n:>5}')
print(f'\nVal summary: {val_summary["total"]} samples')
for tag, n in sorted(val_summary['tag_counts'].items()):
    print(f'  {tag:<20} {n:>5}  ({100*n/val_summary["total"]:.1f}%)')
