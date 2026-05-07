"""V7 notebook generator — programmatically tạo 3 notebooks v7 từ template v6.

Outputs:
- training/notebooks/run_02/04c_train_qwen3_4b_v7.ipynb
- training/notebooks/run_02/05b_train_qwen3_8b_v7.ipynb
- training/notebooks/run_02/06b_eval_all_sizes_v7.ipynb

Critical changes vs v6:
1. HF_REPO: hanoi-router-qwen3-Xb-v7
2. HF_DATA_REPO: hanoi-weather-router-data-v7
3. Data files: multitask_train_v7.jsonl, multitask_val_v7.jsonl, system_prompt_v7.txt
4. Sample counts: 3470 train, 380 val
5. format_record(): handle history list (multi-turn ChatML) thay vì context dict
6. Eval: thêm multi-turn metric (turn=2/3 routing acc), tier calibration ECE
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
NB_DIR = ROOT / 'training/notebooks/run_02'

# ── Load v6 4B template ─────────────────────────────────────────────────────
template_4b = json.load(open(NB_DIR/'04b_train_qwen3_4b_v6.ipynb', encoding='utf-8'))
template_eval = json.load(open(NB_DIR/'06_eval_all_sizes.ipynb', encoding='utf-8'))


def src(text):
    """Convert string to ipynb source (list of lines with newlines)."""
    lines = text.split('\n')
    return [l + '\n' for l in lines[:-1]] + [lines[-1]] if lines else ['']


# ═══════════════════════════════════════════════════════════════════════════
# 1) Build training notebook (template for both 4B + 8B)
# ═══════════════════════════════════════════════════════════════════════════

def build_training_notebook(base_model: str, hf_repo: str, title_size: str) -> dict:
    nb = json.loads(json.dumps(template_4b))  # deep copy

    # Cell 0 — title markdown
    nb['cells'][0]['source'] = src(f"""# Exp7 Train {title_size} v7 — Multi-turn ChatML format

**Purpose**: Train router với v7 dataset (3470 train + 380 val) sử dụng multi-turn ChatML messages format.

**Key changes vs v6**:
- Schema: `history` list of (user, assistant_json) pairs thay cho `context` dict
- Sliding window K=3 (history max 3 prior turns)
- 5-tier confidence: 0.92 / 0.85 / 0.80 / 0.74 / 0.62
- POI banned (P8/P9 policy aligned)
- 100% ward + district coverage trong manual data

**Hyperparams**: identical to v5/v6 cho fair comparison.""")

    # Cell 3 — CONFIG
    nb['cells'][3]['source'] = src(f"""# ═══════════════════════ CONFIG (v7) ═══════════════════════
BASE_MODEL     = '{base_model}'
HF_REPO        = '{hf_repo}'
HF_DATA_REPO   = 'daredevil467/hanoi-weather-router-data-v7'

MAX_SEQ_LENGTH = 2048   # Increased for multi-turn (history adds ~500-1000 tokens turn 3)
LORA_R         = 32
LORA_ALPHA     = 64
LORA_DROPOUT   = 0.1
EPOCHS         = 10
BATCH_SIZE     = 4
GRAD_ACCUM     = 8
LR             = 2e-4
WARMUP_RATIO   = 0.06
EVAL_STEPS     = 50
OUTPUT_DIR     = '/content/outputs'

print(f'Model      : {{BASE_MODEL}}')
print(f'LoRA       : r={{LORA_R}}, alpha={{LORA_ALPHA}}, dropout={{LORA_DROPOUT}}')
print(f'Batch      : {{BATCH_SIZE}} x {{GRAD_ACCUM}} = {{BATCH_SIZE*GRAD_ACCUM}} effective')
print(f'Epochs     : {{EPOCHS}}')
print(f'LR         : {{LR}}')
print(f'Max seq len: {{MAX_SEQ_LENGTH}}')
print(f'HF target  : {{HF_REPO}}')""")

    # Cell 4 — DATA DOWNLOAD (v7 files)
    nb['cells'][4]['source'] = src("""# ═══════════════════════ DATA DOWNLOAD from HF (v7 files) ═══════════════════════
from huggingface_hub import hf_hub_download
import json as _json

train_file = hf_hub_download(repo_id=HF_DATA_REPO, filename='multitask_train_v7.jsonl', repo_type='dataset')
val_file   = hf_hub_download(repo_id=HF_DATA_REPO, filename='multitask_val_v7.jsonl',   repo_type='dataset')
prompt_file= hf_hub_download(repo_id=HF_DATA_REPO, filename='system_prompt_v7.txt',     repo_type='dataset')

with open(train_file, encoding='utf-8') as f:
    train_raw = [_json.loads(l) for l in f]
with open(val_file, encoding='utf-8') as f:
    val_raw = [_json.loads(l) for l in f]
with open(prompt_file, encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read().strip()

print(f'Train: {len(train_raw)} samples')
print(f'Val:   {len(val_raw)} samples')
print(f'System prompt: {len(SYSTEM_PROMPT)} chars')

# Schema sanity: v7 expects 'history' field
assert 'history' in train_raw[0], 'v7 schema requires history field'
assert isinstance(train_raw[0]['history'], list), 'history must be list'

# Distribution checks
from collections import Counter
turn_dist = Counter(len(s['history']) + 1 for s in train_raw)
print(f'Train turn distribution: {dict(turn_dist)}')
tier_dist = Counter(s['output']['confidence'] for s in train_raw)
print(f'Train tier distribution: {{c: tier_dist[c] for c in sorted(tier_dist, reverse=True)}}')""")

    # Cell 8 — FORMAT RECORDS (CRITICAL change for v7 multi-turn ChatML)
    nb['cells'][8]['source'] = src("""# ═══════════════════════ FORMAT RECORDS (v7 multi-turn ChatML) ═══════════════════════
import json
from datasets import Dataset

IM_START = '<|im_start|>'
IM_END   = '<|im_end|>'
NL       = chr(10)

def format_record(rec):
    \"\"\"v7 multi-turn ChatML format.

    Schema:
      rec['history']: list of {user, assistant} pairs (max 3, K=3 sliding window)
      rec['input']:   current user query
      rec['output']:  4-keys core JSON (intent, scope, confidence, rewritten_query)
    \"\"\"
    history = rec.get('history', [])
    user_msg = str(rec.get('input', '')).strip()

    out = rec.get('output', {})
    if isinstance(out, str):
        out = json.loads(out)
    output_dict = {
        'intent':     out['intent'],
        'scope':      out['scope'],
        'confidence': round(float(out.get('confidence', 0.85)), 2),
        'rewritten_query': out.get('rewritten_query'),  # may be null for T5/abstain
    }
    # Drop null rewritten_query keys to keep output compact
    if output_dict['rewritten_query'] is None:
        del output_dict['rewritten_query']

    text = IM_START + 'system' + NL + SYSTEM_PROMPT + IM_END + NL
    # Insert history turns (sliding window — already capped at K=3 in data)
    for h in history:
        text += IM_START + 'user'      + NL + h['user']      + IM_END + NL
        text += IM_START + 'assistant' + NL + h['assistant'] + IM_END + NL
    # Current user + assistant target
    text += IM_START + 'user'      + NL + user_msg + IM_END + NL
    text += IM_START + 'assistant' + NL + json.dumps(output_dict, ensure_ascii=False) + IM_END + NL
    return text

train_texts = [format_record(r) for r in train_raw]
val_texts   = [format_record(r) for r in val_raw]

lengths = [len(tokenizer.encode(t)) for t in train_texts[:200]]
print(f'Avg tokens: {sum(lengths)/len(lengths):.0f}, Max: {max(lengths)}, Over {MAX_SEQ_LENGTH}: {sum(1 for l in lengths if l > MAX_SEQ_LENGTH)}')

# Multi-turn samples typically longer
mt_lengths = [len(tokenizer.encode(format_record(r))) for r in train_raw if len(r['history']) >= 1][:50]
if mt_lengths:
    print(f'Multi-turn avg: {sum(mt_lengths)/len(mt_lengths):.0f}, Max: {max(mt_lengths)}')

raw_train = Dataset.from_dict({'text': train_texts})
raw_val   = Dataset.from_dict({'text': val_texts})
print(f'Train: {len(raw_train)}, Val: {len(raw_val)}')""")

    # Cell 14 — Next steps markdown
    nb['cells'][14]['source'] = src(f"""## Next Steps

After training {title_size} v7:

1. **Evaluate** using `06b_eval_all_sizes_v7.ipynb` (same val v7 across all v7 models)
2. **Compare** v7 vs v6 metrics:
   - v6 baseline (from exp6_summary.json): routing_acc, multi-turn rewrite acc, parse failures
   - v7 expected improvements:
     * Routing acc +5pp (fix 357 prefix/scope errors)
     * Multi-turn anaphora acc ≥80% (was ~50% v6)
     * POI handling: 100% abstain (was hallucinated quận in v6)
     * Confidence calibration ECE < 0.05 (5-tier scheme)
3. **Decision tree**:
   - 4B routing acc ≥88% + multi-turn ≥80% → deploy 4B (sweet spot)
   - Else → fallback 8B
   - Cả 2 dưới 85% → review data quality, không deploy

Push GGUF Q4_K_M nếu deploy via Ollama (cell 13 optional).""")

    return nb


nb_4b = build_training_notebook('unsloth/Qwen3-4B', 'daredevil467/hanoi-router-qwen3-4b-v7', 'Qwen3-4B')
nb_8b = build_training_notebook('unsloth/Qwen3-8B', 'daredevil467/hanoi-router-qwen3-8b-v7', 'Qwen3-8B')
# 8B may need smaller batch — adjust
nb_8b['cells'][3]['source'] = [l.replace("BATCH_SIZE     = 4", "BATCH_SIZE     = 2  # 8B fits less per batch")
                               .replace("GRAD_ACCUM     = 8", "GRAD_ACCUM     = 16  # 2x16 = 32 effective (was 4x8)")
                               for l in nb_8b['cells'][3]['source']]

# Save
out_4b = NB_DIR / '04c_train_qwen3_4b_v7.ipynb'
with open(out_4b, 'w', encoding='utf-8') as f:
    json.dump(nb_4b, f, ensure_ascii=False, indent=1)
print(f'Wrote {out_4b}')

out_8b = NB_DIR / '05b_train_qwen3_8b_v7.ipynb'
with open(out_8b, 'w', encoding='utf-8') as f:
    json.dump(nb_8b, f, ensure_ascii=False, indent=1)
print(f'Wrote {out_8b}')


# ═══════════════════════════════════════════════════════════════════════════
# 2) Build eval notebook (06b_eval_all_sizes_v7)
# ═══════════════════════════════════════════════════════════════════════════

nb_eval = json.loads(json.dumps(template_eval))

# Cell 0 — title
nb_eval['cells'][0]['source'] = src("""# Exp7 — Eval All Router Sizes v7 (Colab A100)

Runs FP16 inference on 380 val v7 samples for v7 router models.

**v7 schema**: multi-turn ChatML (history list + input + output 4-keys core).

**Metrics** (extends v6 evaluation):
- Routing accuracy = intent + scope both correct (primary)
- Intent accuracy + Wilson 95% CI
- Scope accuracy
- Macro-F1 + per-intent F1
- Per-intent accuracy + top confusion pairs
- **Multi-turn routing acc** (turn=2/3 only) — anaphora resolution check
- **Rewrite quality**: exact-match + entity preservation (ward/district mention from history)
- **Confidence calibration ECE** (5-tier scheme alignment)
- **Tier-conditional accuracy** (T1/T2/T3/T4/T5 routing acc per tier)
- Latency P50/P90/P95

**Output**: `exp7_summary.json` + plots + per-sample CSV.""")

# Cell 3 — MODELS config (use v7 repos)
# Find cell with MODELS = [...] — typically cell 3 or so
for i, c in enumerate(nb_eval['cells']):
    s = ''.join(c.get('source', []))
    if 'MODELS = [' in s and 'daredevil467' in s:
        nb_eval['cells'][i]['source'] = src("""# ═══════════════════════ CONFIGS (v7) ═══════════════════════
HF_DATA_REPO = 'daredevil467/hanoi-weather-router-data-v7'

MODELS = [
    ('Qwen3-4B-v7',  'daredevil467/hanoi-router-qwen3-4b-v7',  4.0),
    ('Qwen3-8B-v7',  'daredevil467/hanoi-router-qwen3-8b-v7',  8.0),
]
# Optionally add v6 baselines for comparison (uncomment):
# MODELS += [
#     ('Qwen3-4B-v6 (baseline)',  'daredevil467/hanoi-router-qwen3-4b-v6',  4.0),
# ]

OUTPUT_DIR = Path('/content/outputs')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)""")
        break

# Cell 4 — LOAD VAL DATA + SYSTEM PROMPT (v7 files)
for i, c in enumerate(nb_eval['cells']):
    s = ''.join(c.get('source', []))
    if 'LOAD VAL DATA' in s or "hf_hub_download(repo_id=HF_DATA_REPO" in s:
        nb_eval['cells'][i]['source'] = src("""# ═══════════════════════ LOAD VAL DATA + SYSTEM PROMPT (v7) ═══════════════════════
val_file    = hf_hub_download(repo_id=HF_DATA_REPO, filename='multitask_val_v7.jsonl', repo_type='dataset')
prompt_file = hf_hub_download(repo_id=HF_DATA_REPO, filename='system_prompt_v7.txt',   repo_type='dataset')

with open(val_file, encoding='utf-8') as f:
    val_samples = [json.loads(l) for l in f]
with open(prompt_file, encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read().strip()

print(f'Val samples: {len(val_samples)}')
print(f'System prompt: {len(SYSTEM_PROMPT)} chars')

# v7 distribution checks
from collections import Counter
turn_dist = Counter(len(s['history']) + 1 for s in val_samples)
print(f'Turn distribution: {dict(turn_dist)}')
n_with_history = sum(1 for s in val_samples if s['history'])
n_with_rw      = sum(1 for s in val_samples if s['output'].get('rewritten_query'))
print(f'With history (multi-turn): {n_with_history}  |  With rewrite: {n_with_rw}')""")
        break

# Cell — build_prompt (CRITICAL for eval — must match training format)
for i, c in enumerate(nb_eval['cells']):
    s = ''.join(c.get('source', []))
    if 'def build_prompt' in s:
        nb_eval['cells'][i]['source'] = src("""# ═══════════════════════ HELPERS (v7 multi-turn) ═══════════════════════

def wilson_ci(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / denom
    return (round((center - margin)*100, 2), round((center + margin)*100, 2))

JSON_RE = re.compile(r'\\{[^{}]*\\}', re.DOTALL)

def parse_output(text: str):
    \"\"\"Parse JSON from model output, stripping </think> tags (Qwen3).\"\"\"
    if '</think>' in text:
        text = text[text.rfind('</think>') + len('</think>'):].strip()
    m = JSON_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def build_prompt(sample: dict) -> str:
    \"\"\"v7 multi-turn ChatML — must match training format exactly.\"\"\"
    history = sample.get('history', []) or []
    user_msg = str(sample.get('input', '')).strip()
    text = '<|im_start|>system\\n' + SYSTEM_PROMPT + '<|im_end|>\\n'
    for h in history:
        text += '<|im_start|>user\\n'      + h['user']      + '<|im_end|>\\n'
        text += '<|im_start|>assistant\\n' + h['assistant'] + '<|im_end|>\\n'
    text += '<|im_start|>user\\n' + user_msg + '<|im_end|>\\n<|im_start|>assistant\\n'
    return text

def expected_calibration_error(probs, correct, n_bins=10):
    \"\"\"ECE for confidence calibration. Returns ECE in [0,1] (lower is better).\"\"\"
    bins = [(i/n_bins, (i+1)/n_bins) for i in range(n_bins)]
    ece = 0.0
    n = len(probs)
    for lo, hi in bins:
        in_bin = [(p, c) for p, c in zip(probs, correct) if lo < p <= hi]
        if not in_bin: continue
        bin_acc = sum(c for _, c in in_bin) / len(in_bin)
        bin_conf = sum(p for p, _ in in_bin) / len(in_bin)
        ece += (len(in_bin)/n) * abs(bin_acc - bin_conf)
    return ece""")
        break

# Save eval notebook
out_eval = NB_DIR / '06b_eval_all_sizes_v7.ipynb'
with open(out_eval, 'w', encoding='utf-8') as f:
    json.dump(nb_eval, f, ensure_ascii=False, indent=1)
print(f'Wrote {out_eval}')

print('\n✓ All v7 notebooks generated. Critical cells changed:')
print('  - Cell 0: title v7')
print('  - Cell 3: HF_REPO/HF_DATA_REPO v7')
print('  - Cell 4: data files multitask_*_v7.jsonl, system_prompt_v7.txt')
print('  - Cell 8 (training): format_record() with history list multi-turn ChatML')
print('  - Eval cells: build_prompt() with history + ECE helper')
print('\nNote: bạn còn cần run upload_router_data_hf.py với --version v7 để push data lên HF.')
