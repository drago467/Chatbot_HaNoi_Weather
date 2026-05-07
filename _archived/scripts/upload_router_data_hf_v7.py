"""
scripts/router/upload_router_data_hf_v7.py
Upload v7 router data + system prompt to HF dataset repo.

v7 schema: multi-turn ChatML with `history` list (max K=3 sliding window).

Usage:
    export HF_TOKEN=hf_...
    python scripts/router/upload_router_data_hf_v7.py
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
HF_REPO_ID = "daredevil467/hanoi-weather-router-data-v7"

FILES_TO_UPLOAD = {
    "multitask_train_v7.jsonl":  ROOT / "data/router/multitask_train_v7.jsonl",
    "multitask_val_v7.jsonl":    ROOT / "data/router/multitask_val_v7.jsonl",
    "system_prompt_v7.txt":      ROOT / "data/router/system_prompt_v7.txt",
}

README_MD = """---
language:
- vi
license: cc-by-4.0
task_categories:
- text-classification
tags:
- intent-classification
- weather
- vietnamese
- hanoi
- routing
- slm
- qwen3
- multi-turn
- chatml
---

# Hanoi Weather Router — Training Data v7 (Multi-turn ChatML)

Multi-task intent + scope + rewrite classification data for Hanoi weather chatbot router SLM.
**v7 introduces multi-turn ChatML format** with sliding window K=3.

## Files

| File | Rows | Purpose |
|------|------|---------|
| `multitask_train_v7.jsonl` | 3470 | v7 training — multi-turn ChatML schema |
| `multitask_val_v7.jsonl`   | 380  | v7 validation — stratified split |
| `system_prompt_v7.txt`     | 1    | Router system prompt v7 (1.7k chars) |

## v7 Changes (vs v6)

### Architecture: Multi-turn ChatML messages format
Replaced single-shot `context: {location, intent, turn}` dict với multi-turn
ChatML `messages: [{role, content}]` format (sliding window K=3, router-only history).

Research-backed (CANARD/QReCC/CONQRR/CHIQ): proven format cho conversational query rewriting.
Generalizes anaphora resolution (location, time, intent) without per-issue field invention.

### Data quality fixes
- **357 manual FIX samples**: prefix collision cores (Cầu Giấy → Phường default), POI banned
  per P8/P9 policy, time anchor preservation.
- **250 multi-turn samples**: turn=2/3 anaphora resolution (location/time inheritance,
  explicit-switch patterns).
- **100 pure-ward samples**: full coverage 126/126 wards + 30/30 districts.
- **80 collision counter-examples**: T4 borderline tier + explicit-switch boost.
- **346 POI samples DROPPED**: hard-removed per P8/P9 commit (no silent fallback).

### Confidence: 5-tier calibration scheme
| Tier | Conf | Tình huống |
|---|---|---|
| T1 | 0.92 | Direct query đầy đủ entity + intent + time |
| T2 | 0.85 | Standard inference (1 default needed) |
| T3 | 0.80 | Multi-turn inherited anchor |
| T4 | 0.74 | Collision core không prefix |
| T5 | 0.62 | Smalltalk / POI / OOD (rewrite=null) |

Aligns with per-intent thresholds 0.73-0.85 → enables real calibration ECE measurement.

## Schema

Each line is a JSON object:
```json
{
  "history": [
    {"user": "Phường Cầu Giấy thứ 2 tuần sau thế nào?",
     "assistant": "{\\"intent\\":\\"daily_forecast\\",\\"scope\\":\\"ward\\",\\"confidence\\":0.92,\\"rewritten_query\\":\\"Dự báo Phường Cầu Giấy thứ 2 tuần sau thế nào?\\"}"}
  ],
  "input": "thứ 3 thì sao?",
  "output": {
    "intent": "daily_forecast",
    "scope": "ward",
    "confidence": 0.80,
    "rewritten_query": "Dự báo Phường Cầu Giấy thứ 3 tuần sau thế nào?"
  }
}
```

- `history`: array of `{user, assistant}` pairs, max K=3 (sliding window). Empty `[]` cho turn 1.
- `assistant` content: 4-keys core JSON (intent/scope/confidence/rewritten_query), JSON-stringified.
- `input`: current user query.
- `output`: 4-keys core JSON.

## Training Prompt format (ChatML multi-turn)

```
<|im_start|>system
{SYSTEM_PROMPT}
<|im_end|>
[for each (user, assistant) in history:]
  <|im_start|>user
  {user}
  <|im_end|>
  <|im_start|>assistant
  {assistant}
  <|im_end|>
<|im_start|>user
{input}
<|im_end|>
<|im_start|>assistant
{output_json}
<|im_end|>
```

## Intents (15 classes)

current_weather, hourly_forecast, daily_forecast, weather_overview, rain_query,
temperature_query, wind_query, humidity_fog_query, historical_weather,
location_comparison, activity_weather, expert_weather_param, weather_alert,
seasonal_context, smalltalk_weather

## Scopes (3 classes)

city, district, ward

## Distribution

- Turn distribution: 75% turn=1, 24% turn=2, ~1% turn=3
- Scope: 31% city, 26% district, 44% ward
- Tier: T1=22%, T2=27%, T3=22%, T4=22%, T5=7%
- Coverage: 126/126 wards (100%), 30/30 districts (100%) đều mention trong manual data
"""


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN env var not set.", file=sys.stderr)
        print("  export HF_TOKEN=hf_...", file=sys.stderr)
        sys.exit(1)

    for name, path in FILES_TO_UPLOAD.items():
        if not path.exists():
            print(f"ERROR: Missing file {path}", file=sys.stderr)
            sys.exit(1)

    api = HfApi(token=token)

    print(f"Creating/ensuring repo: {HF_REPO_ID} (dataset)")
    api.create_repo(
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    # Upload README
    print("Uploading README.md ...")
    api.upload_file(
        path_or_fileobj=README_MD.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=HF_REPO_ID,
        repo_type="dataset",
    )

    # Upload data files (system_prompt_v7.txt is included in FILES_TO_UPLOAD)
    for name, path in FILES_TO_UPLOAD.items():
        print(f"Uploading {name} ({path.stat().st_size} bytes) ...")
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=name,
            repo_id=HF_REPO_ID,
            repo_type="dataset",
        )

    print()
    print("=" * 60)
    print(f"Dataset v7 live at: https://huggingface.co/datasets/{HF_REPO_ID}")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f'  1. Open Colab notebook: 04c_train_qwen3_4b_v7.ipynb')
    print(f'  2. Set HF_TOKEN secret in Colab')
    print(f'  3. Run all cells (~5h on A100)')
    print(f'  4. Repeat for 05b_train_qwen3_8b_v7.ipynb (~9h)')
    print(f'  5. Eval both with 06b_eval_all_sizes_v7.ipynb')


if __name__ == "__main__":
    main()
