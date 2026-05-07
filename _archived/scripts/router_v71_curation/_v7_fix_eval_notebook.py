"""Fix bugs trong 06b_eval_all_sizes_v7.ipynb:

Bug 1: rw_entity_ok dùng `sample.get('context')` (v6 schema) → luôn None ở v7
       → entity_cov luôn 0/N. Fix: extract entity từ expected rewritten_query
       (regex "Phường|Xã|Quận|Huyện X") và check pred rewrite chứa nó.

Bug 2: per_sample_rows['has_context'] tương tự — đổi sang `bool(sample['history'])`.

Plus thêm metrics v7-specific:
- Tier-conditional accuracy (T1/T2/T3/T4/T5)
- Turn-conditional accuracy (turn=1 vs turn=2 vs turn=3)
- ECE for 5-tier calibration (uses expected_calibration_error already in cell 5)
"""
import json
import re as _re
from pathlib import Path

ROOT = Path(__file__).parent
NB_PATH = ROOT / 'training/notebooks/run_02/06b_eval_all_sizes_v7.ipynb'

nb = json.load(open(NB_PATH, encoding='utf-8'))


def src(text):
    lines = text.split('\n')
    return [l + '\n' for l in lines[:-1]] + [lines[-1]] if lines else ['']


# Find eval-loop cell (cell 6 — has 'rw_entity_ok')
target_idx = None
for i, c in enumerate(nb['cells']):
    if 'rw_entity_ok' in ''.join(c.get('source', [])):
        target_idx = i
        break
assert target_idx is not None, "Could not find eval cell with rw_entity_ok"
print(f'Patching cell {target_idx}')

# Replace cell 6 with v7-correct version
nb['cells'][target_idx]['source'] = src("""# ═══════════════════════ EVAL LOOP — v7 multi-turn aware ═══════════════════════
# Bugs fixed (vs v6 template):
# - rw_entity_ok now extracts admin entity from EXPECTED rewrite (regex Phường|Xã|Quận|Huyện X)
#   instead of v6 sample['context']['location'] (v7 doesn't have context field).
# - has_context replaced by has_history.
# Plus new v7 metrics: tier-conditional acc, turn-conditional acc, 5-tier ECE.
from transformers import AutoModelForCausalLM, AutoTokenizer

# Helper: extract first admin entity phrase from text ("Phường Cầu Giấy", "Xã Minh Châu"...)
ENTITY_RE = re.compile(
    r'(Phường|Xã|Quận|Huyện|Thị xã)\\s+[A-Z\\u00C0-\\u1EF9][\\w\\s\\-\\u00C0-\\u1EF9]*?'
    r'(?=[\\s,\\.\\?\\!\\(\\)]|$|hôm|hiện|bây|sáng|chiều|tối|trưa|đêm|tuần|tháng|ngày|năm|gần|mùa|lúc|từ|đến|và|có|không|nóng|lạnh|mát|gió|mưa|đang|còn|nên|sẽ|cảnh|báo|thì|thế|nhỉ|nào|trong|so|với)',
    re.UNICODE
)

def extract_entity(text):
    if not text: return None
    m = ENTITY_RE.search(text)
    return m.group(0).strip() if m else None

results = {}
per_sample_rows = []

for name, repo, params_b in MODELS:
    print(f'\\n{"="*60}')
    print(f'Evaluating {name} ({repo})')
    print(f'{"="*60}')

    tokenizer = AutoTokenizer.from_pretrained(repo, token=HF_TOKEN)
    model = AutoModelForCausalLM.from_pretrained(
        repo, token=HF_TOKEN, torch_dtype=torch.float16, device_map='auto',
    )
    model.eval()

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Counters ─────────────────────────────────────────────────────────
    correct_route  = 0
    total_route    = 0
    correct_intent = 0
    correct_scope  = 0
    parse_failures = 0
    # Rewrite tracking (v7 schema)
    rw_correct, rw_total, rw_entity_ok = 0, 0, 0
    norw_correct, norw_total = 0, 0
    # Per-intent
    intent_correct = Counter()
    intent_total   = Counter()
    confusion_pairs = Counter()
    intent_true, intent_pred = [], []
    latencies = []
    # Tier-conditional (5-tier confidence)
    tier_correct = Counter()  # by expected confidence
    tier_total   = Counter()
    # Turn-conditional (1 / 2 / 3)
    turn_correct = Counter()
    turn_total   = Counter()
    # ECE — predicted confidence vs correctness
    ece_probs = []     # predicted confidence
    ece_correct = []   # 1 if route_ok else 0

    for idx, sample in enumerate(val_samples):
        prompt = build_prompt(sample)
        inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=4096).to('cuda')
        t0 = time.time()
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=tokenizer.eos_token_id,
            )
        latency_ms = (time.time() - t0) * 1000
        latencies.append(latency_ms)

        gen_ids = out[0][inputs['input_ids'].shape[1]:]
        gen_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
        pred = parse_output(gen_text)

        gt = sample['output']
        expected_intent = gt['intent']
        expected_scope  = gt['scope']
        expected_conf   = round(float(gt.get('confidence', 0.85)), 2)
        expected_rw     = gt.get('rewritten_query')
        has_rw          = bool(expected_rw)
        has_history     = bool(sample.get('history'))
        turn_n          = len(sample.get('history', []) or []) + 1

        intent_true.append(expected_intent)
        intent_total[expected_intent] += 1
        total_route += 1
        tier_total[expected_conf] += 1
        turn_total[turn_n] += 1

        if pred is None:
            parse_failures += 1
            intent_pred.append('<parse_error>')
            confusion_pairs[(expected_intent, '<parse_error>')] += 1
            if has_rw: rw_total += 1
            else:      norw_total += 1
        else:
            pi = pred.get('intent', '')
            ps = pred.get('scope',  '')
            pc = round(float(pred.get('confidence', 0.85)), 2)
            intent_pred.append(pi)
            route_ok = (pi == expected_intent and ps == expected_scope)

            if pi == expected_intent:
                correct_intent += 1
                intent_correct[expected_intent] += 1
            else:
                confusion_pairs[(expected_intent, pi)] += 1
            if ps == expected_scope:
                correct_scope += 1
            if route_ok:
                correct_route += 1
                tier_correct[expected_conf] += 1
                turn_correct[turn_n] += 1

            # ECE — uses PREDICTED confidence
            ece_probs.append(pc)
            ece_correct.append(1 if route_ok else 0)

            # Rewrite tracking (v7 fix: extract entity from EXPECTED rw, check pred rw contains it)
            if has_rw:
                rw_total += 1
                if route_ok:
                    rw_correct += 1
                pred_rw = pred.get('rewritten_query') or ''
                expected_entity = extract_entity(expected_rw)
                if expected_entity and expected_entity.lower() in pred_rw.lower():
                    rw_entity_ok += 1
            else:
                norw_total += 1
                if route_ok:
                    norw_correct += 1

        per_sample_rows.append({
            'model': name, 'query': sample['input'],
            'has_history': has_history,                       # v7 fix
            'turn': turn_n,
            'gt_intent': expected_intent, 'gt_scope': expected_scope,
            'gt_conf': expected_conf,
            'pred_raw': gen_text,
            'pred_intent': intent_pred[-1],
            'pred_scope': pred.get('scope', '') if pred else '',
            'pred_conf': pred.get('confidence', None) if pred else None,
            'route_ok': pred is not None and (pred.get('intent') == expected_intent and pred.get('scope') == expected_scope),
            'latency_ms': round(latency_ms, 1),
        })

        if (idx + 1) % 50 == 0:
            print(f'  [{idx+1}/{len(val_samples)}] routing_acc={correct_route/(idx+1)*100:.1f}%')

    # ── Compute metrics ──
    n = len(val_samples)
    routing_acc = correct_route / n
    intent_acc  = correct_intent / n
    scope_acc   = correct_scope  / n
    ci_low, ci_high = wilson_ci(correct_route, n)
    ci_intent_low, ci_intent_high = wilson_ci(correct_intent, n)

    from sklearn.metrics import f1_score, classification_report
    labels = sorted(set(intent_true))
    macro_f1 = f1_score(intent_true, intent_pred, labels=labels, average='macro', zero_division=0)
    per_intent_report = classification_report(intent_true, intent_pred, labels=labels, zero_division=0, output_dict=True)

    sorted_lats = sorted(latencies)
    def pctl(p): return sorted_lats[int(len(sorted_lats)*p)] if sorted_lats else 0

    # ECE
    ece = expected_calibration_error(ece_probs, ece_correct, n_bins=10) if ece_probs else 0.0

    results[name] = {
        'repo': repo,
        'params_billions': params_b,
        'routing_accuracy_pct':  round(routing_acc*100, 2),
        'routing_ci95':          [ci_low, ci_high],
        'intent_accuracy_pct':   round(intent_acc*100, 2),
        'intent_ci95':           [ci_intent_low, ci_intent_high],
        'scope_accuracy_pct':    round(scope_acc*100, 2),
        'macro_f1':              round(macro_f1, 4),
        'parse_failures':        parse_failures,
        # Rewrite metrics (v7 fixed)
        'rewrite_routing_acc':   round(rw_correct/rw_total*100, 2) if rw_total else None,
        'rewrite_entity_cov':    round(rw_entity_ok/rw_total*100, 2) if rw_total else None,
        'rewrite_n':             rw_total,
        'no_rewrite_routing_acc': round(norw_correct/norw_total*100, 2) if norw_total else None,
        # Tier-conditional (5-tier)
        'tier_conditional_acc': {
            f'{conf:.2f}': {
                'n': tier_total[conf],
                'correct': tier_correct[conf],
                'acc': round(tier_correct[conf]/tier_total[conf]*100, 2) if tier_total[conf] else None
            } for conf in sorted(tier_total)
        },
        # Turn-conditional
        'turn_conditional_acc': {
            f'turn_{t}': {
                'n': turn_total[t],
                'correct': turn_correct[t],
                'acc': round(turn_correct[t]/turn_total[t]*100, 2) if turn_total[t] else None,
            } for t in sorted(turn_total)
        },
        # Calibration
        'calibration_ece':       round(ece, 4),
        # Latency
        'latency_p50_ms':        round(pctl(0.50), 1),
        'latency_p90_ms':        round(pctl(0.90), 1),
        'latency_p95_ms':        round(pctl(0.95), 1),
        # Per-intent detail
        'per_intent_f1':         {k: round(v['f1-score'], 3) for k, v in per_intent_report.items() if isinstance(v, dict) and 'f1-score' in v},
        'per_intent_accuracy':   {i: round(intent_correct[i]/intent_total[i]*100, 1) if intent_total[i] else 0 for i in sorted(intent_total)},
        'top_confusion_pairs':   [(f'{e}->{p}', c) for (e, p), c in confusion_pairs.most_common(10)],
    }

    # ── Print summary ──
    print(f'  Routing acc:   {correct_route}/{n} = {routing_acc:.1%}  CI=[{ci_low}, {ci_high}]')
    print(f'  Intent acc:    {correct_intent}/{n} = {intent_acc:.1%}  Macro-F1={macro_f1:.4f}')
    print(f'  Scope acc:     {correct_scope}/{n} = {scope_acc:.1%}')
    if rw_total:
        print(f'  Rewrite routing: {rw_correct}/{rw_total} = {rw_correct/rw_total:.1%}')
        print(f'  Rewrite entity cov: {rw_entity_ok}/{rw_total} = {rw_entity_ok/rw_total:.1%}  [v7-fixed]')
    print(f'  ECE (5-tier):  {ece:.4f}')
    print(f'  P50={pctl(0.50):.0f}ms  ParseFail={parse_failures}')

    # Tier-conditional
    print(f'\\n  Tier-conditional accuracy:')
    print(f'  {"Tier":<8} {"Conf":<6} {"Correct":>8} {"Total":>6} {"Acc":>7}')
    tier_label = {0.92:'T1', 0.85:'T2', 0.80:'T3', 0.74:'T4', 0.62:'T5'}
    for c in sorted(tier_total, reverse=True):
        t = tier_total[c]
        cc = tier_correct.get(c, 0)
        acc = cc/t if t else 0
        print(f'  {tier_label.get(c, "?"):<8} {c:<6} {cc:>8} {t:>6} {acc:>6.1%}')

    # Turn-conditional
    print(f'\\n  Turn-conditional accuracy:')
    for t in sorted(turn_total):
        n_t = turn_total[t]
        c_t = turn_correct.get(t, 0)
        acc = c_t/n_t if n_t else 0
        flag = ' ←multi-turn' if t > 1 else ''
        print(f'  turn={t}: {c_t}/{n_t} = {acc:.1%}{flag}')

    # Per-intent
    print(f'\\n  Per-intent accuracy:')
    print(f'  {"Intent":<25} {"Correct":>7} {"Total":>7} {"Acc":>7}')
    for intent in sorted(intent_total):
        t = intent_total[intent]
        c = intent_correct.get(intent, 0)
        acc = c/t if t else 0
        flag = ' <<<' if acc < 0.85 else ''
        print(f'  {intent:<25} {c:>7} {t:>7} {acc:>6.1%}{flag}')

    if confusion_pairs:
        print(f'\\n  TOP CONFUSION:')
        for (exp, pred), cnt in confusion_pairs.most_common(5):
            print(f'    {exp:<25} -> {pred:<25} x{cnt}')

    # Free GPU
    del model, tokenizer
    torch.cuda.empty_cache()
    gc.collect()""")

# Save
with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Patched {NB_PATH}')
print(f'Cells in notebook: {len(nb["cells"])}')

# Sanity: verify the cell now has no `sample.get(\'context\')`
patched_src = ''.join(nb['cells'][target_idx]['source'])
if "sample.get('context')" in patched_src:
    print('WARNING: cell still references sample.get("context") — patch incomplete')
else:
    print('✓ Cell no longer references sample.get("context")')
if 'has_history' in patched_src:
    print('✓ Cell uses has_history (v7 schema)')
if 'extract_entity' in patched_src:
    print('✓ Cell uses extract_entity helper')
if 'tier_conditional_acc' in patched_src:
    print('✓ Cell adds tier-conditional metric')
if 'turn_conditional_acc' in patched_src:
    print('✓ Cell adds turn-conditional metric')
if 'calibration_ece' in patched_src:
    print('✓ Cell adds ECE metric')
