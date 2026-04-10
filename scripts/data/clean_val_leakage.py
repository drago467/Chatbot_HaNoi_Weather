"""
scripts/data/clean_val_leakage.py
Fix data leakage: remove val samples that appear in train set.

Input:
  data/router/multitask_train_v3.jsonl  (4005 samples)
  data/router/multitask_val_v3.jsonl    (672 samples)

Output:
  data/router/multitask_val_v3_clean.jsonl  (~434 samples, 0 overlap)

Finding: 238/672 (35.4%) val samples were exact-match duplicates of train queries.
This inflated R1 (fine-tuned) accuracy in Exp 1, since R1 "saw" those queries during
training. R2/R3/R4 (zero-shot) were not affected → unfair comparison.

Resolution: Use clean set for re-run. Report BOTH results in thesis.
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TRAIN_PATH = ROOT / "data/router/multitask_train_v3.jsonl"
VAL_PATH = ROOT / "data/router/multitask_val_v3.jsonl"
CLEAN_PATH = ROOT / "data/router/multitask_val_v3_clean.jsonl"


def main():
    # Load train queries
    train_queries: set[str] = set()
    with open(TRAIN_PATH, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            train_queries.add(d["input"].strip())
    print(f"Train unique queries: {len(train_queries)}")

    # Filter val
    val_total = 0
    val_clean = []
    val_leaked = 0
    leaked_examples = []

    with open(VAL_PATH, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            val_total += 1
            if d["input"].strip() in train_queries:
                val_leaked += 1
                if len(leaked_examples) < 5:
                    leaked_examples.append(d["input"][:80])
            else:
                val_clean.append(d)

    pct = val_leaked / val_total * 100
    print(f"Val total: {val_total}")
    print(f"Val leaked (train overlap): {val_leaked} ({pct:.1f}%)")
    print(f"Val clean: {len(val_clean)}")
    print("\nSample leaked queries:")
    for ex in leaked_examples:
        print(f"  {ex}")

    # Distribution of clean set
    intents: Counter = Counter()
    scopes: Counter = Counter()
    for d in val_clean:
        intents[d["output"]["intent"]] += 1
        scopes[d["output"]["scope"]] += 1

    print("\nClean val intent distribution:")
    for k, v in sorted(intents.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    print("\nClean val scope distribution:")
    for k, v in sorted(scopes.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    # Save
    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        for d in val_clean:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\nSaved: {CLEAN_PATH}")
    print("Next: re-run Exp 1 pointing to multitask_val_v3_clean.jsonl")


if __name__ == "__main__":
    main()
