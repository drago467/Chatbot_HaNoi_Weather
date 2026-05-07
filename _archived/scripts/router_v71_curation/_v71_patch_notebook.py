"""Patch 04c_train_qwen3_4b_v7.ipynb to use v7.1 data files."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
NB_IN  = ROOT/'training/notebooks/run_02/04c_train_qwen3_4b_v7.ipynb'
NB_OUT = ROOT/'training/notebooks/run_02/04d_train_qwen3_4b_v7_1.ipynb'

nb = json.load(open(NB_IN, encoding='utf-8'))

for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))

    # Cell 0 — title
    if i == 0 and 'Exp7 Train' in src:
        nb['cells'][i]['source'] = [
            "# Exp7.1 Train Qwen3-4B v7.1 — Targeted disambiguation fix\n",
            "\n",
            "**v7.1 vs v7**: 71 manual relabels (alert/clothing/hourly) + 50 disambig samples + stronger anti-confusion rules in system prompt.\n",
            "\n",
            "**Goal**: push routing acc 86.6% → ≥88% (close +1.4pp gap from confusion fixes).\n",
        ]

    # Cell 3 — CONFIG (HF_REPO)
    if 'HF_REPO' in src and 'qwen3-4b-v7' in src:
        new_src = []
        for line in c['source']:
            if "HF_REPO        = 'daredevil467/hanoi-router-qwen3-4b-v7'" in line:
                new_src.append("HF_REPO        = 'daredevil467/hanoi-router-qwen3-4b-v7-1'\n")
            else:
                new_src.append(line)
        nb['cells'][i]['source'] = new_src

    # Cell 4 — DATA DOWNLOAD (v7 → v7_1)
    if "filename='multitask_train_v7.jsonl'" in src:
        new_src = []
        for line in c['source']:
            line = line.replace("multitask_train_v7.jsonl",  "multitask_train_v7_1.jsonl")
            line = line.replace("multitask_val_v7.jsonl",    "multitask_val_v7_1.jsonl")
            line = line.replace("system_prompt_v7.txt",      "system_prompt_v7_1.txt")
            new_src.append(line)
        nb['cells'][i]['source'] = new_src

with open(NB_OUT, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Wrote {NB_OUT}')
print('Critical patches:')
print('  - Cell 0: title v7.1')
print('  - Cell 3: HF_REPO → hanoi-router-qwen3-4b-v7-1')
print('  - Cell 4: data files v7 → v7_1')

# Same for eval notebook
NB_EVAL_IN  = ROOT/'training/notebooks/run_02/06b_eval_all_sizes_v7.ipynb'
NB_EVAL_OUT = ROOT/'training/notebooks/run_02/06c_eval_all_sizes_v7_1.ipynb'
nb_eval = json.load(open(NB_EVAL_IN, encoding='utf-8'))

for i, c in enumerate(nb_eval['cells']):
    src = ''.join(c.get('source', []))

    if 'multitask_val_v7.jsonl' in src or 'system_prompt_v7.txt' in src:
        new_src = []
        for line in c['source']:
            line = line.replace("multitask_val_v7.jsonl", "multitask_val_v7_1.jsonl")
            line = line.replace("system_prompt_v7.txt",   "system_prompt_v7_1.txt")
            new_src.append(line)
        nb_eval['cells'][i]['source'] = new_src

    if "'daredevil467/hanoi-router-qwen3-4b-v7'" in src:
        new_src = []
        for line in c['source']:
            line = line.replace("'daredevil467/hanoi-router-qwen3-4b-v7'",
                                "'daredevil467/hanoi-router-qwen3-4b-v7-1'")
            new_src.append(line)
        nb_eval['cells'][i]['source'] = new_src

with open(NB_EVAL_OUT, 'w', encoding='utf-8') as f:
    json.dump(nb_eval, f, ensure_ascii=False, indent=1)
print(f'Wrote {NB_EVAL_OUT}')
