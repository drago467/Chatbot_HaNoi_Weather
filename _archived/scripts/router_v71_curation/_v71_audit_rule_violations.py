"""V7.1 audit — tìm samples VI PHẠM intent_disambiguation_rules.md trong v7 train/val.

Rules được kiểm:
1. weather_alert vs rain_query (Confusion Pair #2):
   - "bão/áp thấp/lũ/ngập/lụt/giông/sét/lốc/mưa to/mưa lớn/mưa đá/cảnh báo/nguy hiểm/
      rét hại/rét đậm/nắng nóng gay gắt" → weather_alert (KHÔNG rain_query)

2. activity_weather vs smalltalk_weather (Section 6):
   - Clothing queries ("mặc gì/đeo gì/cần mặc/nên mặc/cần mang") → smalltalk
   - Specific activity ("chạy bộ/picnic/đi dạo/đi câu/tưới cây/giặt đồ") → activity

3. daily_forecast vs hourly_forecast (Section 4):
   - "chiều nay/tối nay/sáng mai/từ giờ/N tiếng" → hourly (today time slot)
   - "ngày mai/ngày kia/tuần tới/cuối tuần/thứ X" → daily

4. current_weather vs temperature_query (Section 1):
   - "thời tiết/trời thế nào/sao/ra sao" → current_weather
   - "nhiệt độ/bao nhiêu độ/nóng không/lạnh không" → temperature_query
"""
import json, re, unicodedata
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('Đ','d').replace('đ','d').lower().strip()

# ── Load v7 ─────────────────────────────────────────────────────────────────
train = [json.loads(l) for l in open(ROOT/'data/router/multitask_train_v7.jsonl', encoding='utf-8')]
val   = [json.loads(l) for l in open(ROOT/'data/router/multitask_val_v7.jsonl',   encoding='utf-8')]
print(f'Loaded train={len(train)} val={len(val)}')

# ── Rule keyword sets ───────────────────────────────────────────────────────
ALERT_TRIGGERS = [
    # storm / typhoon
    'bao', 'ap thap nhiet doi', 'ap thap',
    # flood
    'lu', 'ngap', 'lut', 'lu quet',
    # severe phenomena
    'giong', 'set', 'loc', 'mua da',
    # severe rain (per rule: mưa to/mưa lớn = severe → alert)
    'mua to', 'mua lon', 'mua kem giong', 'mua kem bao',
    # extreme temp
    'ret hai', 'ret dam', 'nang nong gay gat', 'nang nong cuc doan',
    'nang nong dac biet',
    # explicit
    'canh bao', 'khuyen cao', 'nguy hiem', 'an toan',
]

CLOTHING_TRIGGERS = [
    'mac gi', 'mac do gi', 'nen mac', 'can mac', 'phai mac',
    'deo gi', 'mang gi', 'can mang', 'nen mang', 'chuan bi gi',
    'mang o', 'mang ao mua', 'mang theo', 'kem chong nang',
    'ao khoac', 'ao ret', 'ao am', 'ao mua', 'ao phao',
]

ACTIVITY_TRIGGERS = [
    'chay bo', 'di bo', 'picnic', 'da ngoai', 'di dao', 'di lam',
    'di hoc', 'di cau ca', 'cau ca', 'tuoi cay', 'giat do', 'phoi do',
    'di choi', 'di trekking', 'leo nui', 'chup anh', 'di xe', 'di xe may',
    'di xe dap', 'tap the duc', 'tap gym', 'di boi', 'tha dieu',
]

HOURLY_TIME_TRIGGERS = [
    'chieu nay', 'toi nay', 'dem nay', 'sang nay', 'trua nay',
    'sang mai', 'chieu mai', 'toi mai', 'sang mai',
    'rang sang', 'binh minh', 'hoang hon',
    'tu gio', 'trong vai gio', 'trong vai tieng', 'trong N tieng',
    'tieng nua', 'gio nua', 'h sang', 'h chieu', 'h toi',
]

DAILY_TIME_TRIGGERS = [
    'ngay mai', 'ngay kia', 'mot vai ngay', 'cac ngay toi', 'nhung ngay toi',
    'tuan toi', 'tuan nay', 'tuan sau', 'cuoi tuan',
    'thu hai', 'thu ba', 'thu tu', 'thu nam', 'thu sau', 'thu bay',
    'chu nhat', '3 ngay', '7 ngay', 'tuan',
]

CURRENT_TRIGGERS = ['thoi tiet', 'troi the nao', 'troi sao', 'troi ra sao', 'troi co dep',
                    'tinh hinh thoi tiet', 'hien tai', 'bay gio', 'luc nay']
TEMP_TRIGGERS = ['nhiet do', 'bao nhieu do', 'nong khong', 'lanh khong',
                 'nong lam', 'lanh lam', 'nong cuc', 'lanh cuc']


def has_any(text_n: str, triggers: list[str]) -> list[str]:
    return [t for t in triggers if t in text_n]


# Strict accent-aware severity patterns (avoid false positives like "bao nhiêu" matching "bão")
ALERT_PATTERNS_RE = [
    re.compile(r'\bbão\b', re.IGNORECASE),
    re.compile(r'\bngập\b', re.IGNORECASE),
    re.compile(r'\blũ\b', re.IGNORECASE),
    re.compile(r'\blụt\b', re.IGNORECASE),
    re.compile(r'\bgiông\b', re.IGNORECASE),
    re.compile(r'\bsét\b', re.IGNORECASE),
    re.compile(r'\blốc\b', re.IGNORECASE),  # only matches "lốc" with accent, NOT "Lộc" (different vowel ộ vs ố)
    re.compile(r'\bmưa\s+(to|lớn|đá|rất to)\b', re.IGNORECASE),
    re.compile(r'\bmưa\s+kèm\s+(giông|bão|gió|sét)\b', re.IGNORECASE),
    re.compile(r'\bcảnh\s+báo\b', re.IGNORECASE),
    re.compile(r'\bnguy\s+hiểm\b', re.IGNORECASE),
    re.compile(r'\bkhuyến\s+cáo\b', re.IGNORECASE),
    re.compile(r'\brét\s+(hại|đậm)\b', re.IGNORECASE),
    re.compile(r'\bnắng\s+nóng\s+(gay\s+gắt|đặc\s+biệt|cực\s+đoan|kỷ\s+lục)\b', re.IGNORECASE),
    re.compile(r'\báp\s+thấp\s+nhiệt\s+đới\b', re.IGNORECASE),
    re.compile(r'\báp\s+thấp\b', re.IGNORECASE),
    # Telex variants (lowercase, no diacritics) — strict word-boundary
    re.compile(r'\bngap\b', re.IGNORECASE),    # ngap = ngập (rarely false-positive)
    re.compile(r'\bgiong\b(?!g)', re.IGNORECASE),  # giong (giông), NOT "giong" inside other word
    re.compile(r'\bmua\s+(to|lon|da)\b(?!o)', re.IGNORECASE),  # mưa to/lớn/đá
    re.compile(r'\bcanh\s+bao\b', re.IGNORECASE),  # cảnh báo
    re.compile(r'\bret\s+(hai|dam)\b', re.IGNORECASE),
    re.compile(r'\bnang\s+nong\s+(gay\s+gat|dac\s+biet|cuc\s+doan)\b', re.IGNORECASE),
    re.compile(r'\bap\s+thap\b', re.IGNORECASE),
]


def audit_sample(s: dict, idx: int, dataset: str) -> list[dict]:
    """Return list of violations for this sample."""
    violations = []
    inp = s.get('input', '') or ''
    out = s.get('output', {})
    intent = out.get('intent', '')
    inp_n = norm(inp)

    # Rule 1: weather_alert severity keywords (strict accent-aware)
    alert_hits = []
    for pat in ALERT_PATTERNS_RE:
        m = pat.search(inp)
        if m:
            alert_hits.append(m.group(0))
    if alert_hits and intent != 'weather_alert':
        # Exception: rain_query is OK if user asks duration/probability (not severity)
        # But severe phrases like "mưa to" / "bão" should always be alert
        violations.append({
            'rule': '1_alert_severity',
            'expected': 'weather_alert',
            'actual': intent,
            'triggers': alert_hits,
            'input': inp[:80],
            'idx': idx, 'dataset': dataset,
        })

    # Rule 2a: clothing → smalltalk
    clothing_hits = has_any(inp_n, CLOTHING_TRIGGERS)
    if clothing_hits and intent == 'activity_weather':
        # check if also has SPECIFIC activity word (then keep activity)
        activity_hits = has_any(inp_n, [a for a in ACTIVITY_TRIGGERS if a not in CLOTHING_TRIGGERS])
        if not activity_hits:
            violations.append({
                'rule': '2a_clothing_should_be_smalltalk',
                'expected': 'smalltalk_weather',
                'actual': intent,
                'triggers': clothing_hits,
                'input': inp[:80],
                'idx': idx, 'dataset': dataset,
            })

    # Rule 2b: specific activity → activity (not smalltalk)
    activity_hits = has_any(inp_n, ACTIVITY_TRIGGERS)
    activity_hits = [a for a in activity_hits if a not in CLOTHING_TRIGGERS]
    if activity_hits and intent == 'smalltalk_weather' and not clothing_hits:
        violations.append({
            'rule': '2b_specific_activity_should_be_activity',
            'expected': 'activity_weather',
            'actual': intent,
            'triggers': activity_hits,
            'input': inp[:80],
            'idx': idx, 'dataset': dataset,
        })

    # Rule 3: hourly slot keywords with daily intent
    hourly_hits = has_any(inp_n, HOURLY_TIME_TRIGGERS)
    daily_hits = has_any(inp_n, DAILY_TIME_TRIGGERS)
    # Mixed "ngày mai chiều" → hourly per rule
    if 'chieu mai' in inp_n or 'sang mai' in inp_n or 'toi mai' in inp_n or 'dem mai' in inp_n:
        # explicit slot tomorrow → hourly
        if intent == 'daily_forecast':
            violations.append({
                'rule': '3_slot_tomorrow_should_be_hourly',
                'expected': 'hourly_forecast',
                'actual': intent,
                'triggers': hourly_hits,
                'input': inp[:80],
                'idx': idx, 'dataset': dataset,
            })

    return violations


# ── Run audit ───────────────────────────────────────────────────────────────
all_violations = []
for i, s in enumerate(train):
    all_violations.extend(audit_sample(s, i, 'train'))
for i, s in enumerate(val):
    all_violations.extend(audit_sample(s, i, 'val'))

print(f'\nTotal violations: {len(all_violations)}')
by_rule = Counter(v['rule'] for v in all_violations)
print('\nBy rule:')
for r, n in by_rule.most_common():
    print(f'  {r:<40} {n}')

print('\nBy expected intent:')
by_expected = Counter(v['expected'] for v in all_violations)
for e, n in by_expected.most_common():
    print(f'  {e:<25} {n}')

# Show samples per rule
for rule in sorted(set(v['rule'] for v in all_violations)):
    rule_vios = [v for v in all_violations if v['rule'] == rule]
    print(f'\n=== {rule} ({len(rule_vios)} cases) ===')
    for v in rule_vios[:8]:
        print(f"  [{v['dataset']}#{v['idx']}] {v['actual']} → {v['expected']}")
        print(f"    input:    '{v['input']}'")
        print(f"    triggers: {v['triggers'][:3]}")

# Save full report
out = ROOT / '_v71_violations.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(all_violations, f, ensure_ascii=False, indent=2)
print(f'\nSaved {out} ({len(all_violations)} violations)')
