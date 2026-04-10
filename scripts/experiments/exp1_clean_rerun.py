"""
scripts/experiments/exp1_clean_rerun.py
Recompute Exp 1 metrics on the clean val set (434 samples, no train overlap).

Instead of re-running all 4 router configs (expensive API calls),
we filter the existing predictions.csv to exclude the 238 leaked samples
and recompute intent accuracy, macro-F1, scope accuracy, and McNemar tests.

This is valid because:
  - R2/R3/R4 (zero-shot) are NOT affected by data leakage, so their predictions
    are equally valid on any subset.
  - R1 (fine-tuned) was affected: its accuracy was inflated because 35.4% of val
    queries were seen during training. Filtering to unseen samples gives honest numbers.

Output:
  data/evaluation/thesis_final/exp1_router_clean/
    summary_clean.json
    comparison_table_clean.txt
    predictions_clean.csv
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.agent.router.config import VALID_INTENTS

INPUT_DIR = ROOT / "data/evaluation/thesis_final/exp1_router"
OUTPUT_DIR = ROOT / "data/evaluation/thesis_final/exp1_router_clean"
TRAIN_PATH = ROOT / "data/router/multitask_train_v3.jsonl"
VAL_PATH = ROOT / "data/router/multitask_val_v3.jsonl"
PREDICTIONS_CSV = INPUT_DIR / "predictions.csv"

CONFIGS = ["R1", "R2", "R3", "R4"]
CONFIG_LABELS = {
    "R1": "R1. Qwen3-4B FT (Ollama)",
    "R2": "R2. Qwen3-4B ZS (API)",
    "R3": "R3. GPT-4o-mini ZS",
    "R4": "R4. GPT-4o ZS",
}


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    center = p + z**2 / (2 * total)
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    lo = (center - spread) / denom
    hi = (center + spread) / denom
    return (max(0.0, lo), min(1.0, hi))


def mcnemar_test(correct_a: list[bool], correct_b: list[bool]) -> dict:
    from scipy.stats import chi2 as chi2_dist
    n = len(correct_a)
    c_only_a = sum(1 for a, b in zip(correct_a, correct_b) if a and not b)
    b_only_b = sum(1 for a, b in zip(correct_a, correct_b) if not a and b)
    discordant = c_only_a + b_only_b
    if discordant == 0:
        return {"chi2": 0.0, "p_value": 1.0, "note": "no discordant pairs",
                "only_a_correct": 0, "only_b_correct": 0,
                "significant_0.05": False, "significant_0.01": False}
    chi2 = (abs(c_only_a - b_only_b) - 1) ** 2 / discordant
    p_value = float(1 - chi2_dist.cdf(chi2, df=1))
    return {
        "chi2": round(float(chi2), 4),
        "p_value": round(p_value, 6),
        "only_a_correct": int(c_only_a),
        "only_b_correct": int(b_only_b),
        "significant_0.05": p_value < 0.05,
        "significant_0.01": p_value < 0.01,
    }


def compute_metrics(rows: list[dict], config: str) -> dict:
    from sklearn.metrics import f1_score, classification_report

    y_true_intent = [r["expected_intent"] for r in rows]
    y_pred_intent = [r[f"{config}_intent"] for r in rows]
    y_true_scope  = [r["expected_scope"] for r in rows]
    y_pred_scope  = [r[f"{config}_scope"] for r in rows]

    n = len(rows)
    intent_correct = [t == p for t, p in zip(y_true_intent, y_pred_intent)]
    scope_correct  = [t == p for t, p in zip(y_true_scope, y_pred_scope)]
    joint_correct  = [i and s for i, s in zip(intent_correct, scope_correct)]

    intent_acc = sum(intent_correct) / n * 100
    scope_acc  = sum(scope_correct)  / n * 100
    joint_acc  = sum(joint_correct)  / n * 100

    ci_lo, ci_hi = wilson_ci(sum(intent_correct), n)
    macro_f1 = f1_score(y_true_intent, y_pred_intent, average="macro", zero_division=0) * 100

    report = classification_report(
        y_true_intent, y_pred_intent,
        labels=sorted(VALID_INTENTS), zero_division=0, output_dict=True,
    )

    return {
        "config": CONFIG_LABELS[config],
        "config_key": config,
        "n": n,
        "intent_accuracy": round(intent_acc, 1),
        "ci_lo": round(ci_lo * 100, 1),
        "ci_hi": round(ci_hi * 100, 1),
        "intent_f1_macro": round(macro_f1, 1),
        "scope_accuracy": round(scope_acc, 1),
        "joint_accuracy": round(joint_acc, 1),
        "per_intent_report": report,
        "_intent_correct": intent_correct,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load train queries
    train_queries: set[str] = set()
    with open(TRAIN_PATH, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            train_queries.add(d["input"].strip())

    # 2. Load and filter predictions
    with open(PREDICTIONS_CSV, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    clean_rows = [r for r in all_rows if r["input"].strip() not in train_queries]
    leaked_count = len(all_rows) - len(clean_rows)

    print(f"Original predictions: {len(all_rows)}")
    print(f"Leaked (filtered out): {leaked_count} ({leaked_count/len(all_rows)*100:.1f}%)")
    print(f"Clean subset: {len(clean_rows)}")

    # 3. Compute metrics per config
    all_metrics = []
    for cfg in CONFIGS:
        m = compute_metrics(clean_rows, cfg)
        all_metrics.append(m)
        print(f"\n{CONFIG_LABELS[cfg]}:")
        print(f"  Intent Acc: {m['intent_accuracy']:.1f}% [{m['ci_lo']:.1f}, {m['ci_hi']:.1f}]")
        print(f"  Macro-F1:   {m['intent_f1_macro']:.1f}%")
        print(f"  Scope Acc:  {m['scope_accuracy']:.1f}%")
        print(f"  Joint Acc:  {m['joint_accuracy']:.1f}%")

    # 4. McNemar tests (R1 vs others)
    r1_correct = all_metrics[0]["_intent_correct"]
    mcnemar_results = {}
    for m in all_metrics[1:]:
        pair = f"R1 vs {m['config_key']}"
        mcnemar_results[pair] = mcnemar_test(r1_correct, m["_intent_correct"])

    print("\nMcNemar Tests (intent accuracy):")
    for pair, res in mcnemar_results.items():
        sig = "***" if res["significant_0.01"] else ("*" if res["significant_0.05"] else "n.s.")
        print(f"  {pair}: chi2={res['chi2']:.2f}, p={res['p_value']:.4f} {sig}")

    # 5. Save summary JSON
    summary = {
        "dataset": "multitask_val_v3_clean.jsonl (train-overlap removed)",
        "n_original": len(all_rows),
        "n_leaked": leaked_count,
        "n_clean": len(clean_rows),
        "configs": {},
    }
    for m in all_metrics:
        cfg = m["config_key"]
        summary["configs"][cfg] = {
            "label": m["config"],
            "intent_accuracy": m["intent_accuracy"],
            "ci_lo": m["ci_lo"],
            "ci_hi": m["ci_hi"],
            "intent_f1_macro": m["intent_f1_macro"],
            "scope_accuracy": m["scope_accuracy"],
            "joint_accuracy": m["joint_accuracy"],
        }
    summary["mcnemar"] = mcnemar_results

    summary_path = OUTPUT_DIR / "summary_clean.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {summary_path}")

    # 6. Save comparison table
    table_path = OUTPUT_DIR / "comparison_table_clean.txt"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("Exp 1 — Router Comparison (CLEAN val set, n=434, no train overlap)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'Config':<35} {'Intent Acc':>10} {'95% CI':>17} {'Macro-F1':>9} {'Scope Acc':>10} {'Joint Acc':>10}\n")
        f.write("-" * 95 + "\n")
        for m in all_metrics:
            f.write(
                f"{m['config']:<35} {m['intent_accuracy']:>9.1f}% "
                f"[{m['ci_lo']:>5.1f},{m['ci_hi']:>5.1f}] "
                f"{m['intent_f1_macro']:>8.1f}% "
                f"{m['scope_accuracy']:>9.1f}% "
                f"{m['joint_accuracy']:>9.1f}%\n"
            )
        f.write("\nMcNemar Tests (intent accuracy, paired):\n")
        for pair, res in mcnemar_results.items():
            sig = "***" if res["significant_0.01"] else ("*" if res["significant_0.05"] else "n.s.")
            f.write(f"  {pair}: chi2={res['chi2']:.3f}, p={res['p_value']:.6f} {sig}\n")

        # Per-intent breakdown for R1 (most important)
        f.write("\n--- R1. Qwen3-4B FT — per-intent F1 (clean val) ---\n")
        f.write(f"{'Intent':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}\n")
        f.write("-" * 65 + "\n")
        r1_report = all_metrics[0]["per_intent_report"]
        for intent in sorted(VALID_INTENTS):
            if intent in r1_report:
                r = r1_report[intent]
                f.write(
                    f"{intent:<25} {r['precision']:>9.2f} {r['recall']:>9.2f} "
                    f"{r['f1-score']:>9.2f} {int(r['support']):>10}\n"
                )

    print(f"Saved: {table_path}")

    # 7. Save predictions CSV (clean subset)
    pred_path = OUTPUT_DIR / "predictions_clean.csv"
    with open(pred_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(clean_rows[0].keys()))
        writer.writeheader()
        writer.writerows(clean_rows)
    print(f"Saved: {pred_path}")

    # 8. Comparison with original (leaked) results
    orig_summary_path = INPUT_DIR / "summary.json"
    if orig_summary_path.exists():
        with open(orig_summary_path, encoding="utf-8") as f:
            orig = json.load(f)

        print("\n=== COMPARISON: Original (n=672) vs Clean (n=434) ===")
        print(f"{'Config':<12} {'Orig Intent':>12} {'Clean Intent':>13} {'Delta':>8}")
        print("-" * 50)
        for cfg in CONFIGS:
            orig_acc = orig.get(cfg, {}).get("intent_accuracy", "N/A")
            clean_acc = next(m["intent_accuracy"] for m in all_metrics if m["config_key"] == cfg)
            if isinstance(orig_acc, (int, float)):
                delta = clean_acc - orig_acc
                print(f"  {cfg:<10} {orig_acc:>11.1f}% {clean_acc:>12.1f}% {delta:>+7.1f}pp")
            else:
                print(f"  {cfg:<10} {'N/A':>11} {clean_acc:>12.1f}%")


if __name__ == "__main__":
    main()
