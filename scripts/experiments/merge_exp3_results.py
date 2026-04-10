"""
scripts/experiments/merge_exp3_results.py

Merge the 28-question incremental run (--new-only) into the original 171-question
results, producing a 199-question combined evaluation for each config.

Usage:
  # Preview only — no files overwritten:
  python scripts/experiments/merge_exp3_results.py --dry-run

  # Merge all configs (default):
  python scripts/experiments/merge_exp3_results.py

  # Merge specific configs only:
  python scripts/experiments/merge_exp3_results.py --configs E1 E2

  # Skip backup of original files:
  python scripts/experiments/merge_exp3_results.py --no-backup

What it does (per config E1/E2/E3/E4):
  1. Load old 171-row CSV  from exp3/{subdir}/{mode}/evaluation_results.csv
  2. Load new  28-row CSV  from exp3/{subdir}_28new/{mode}/evaluation_results.csv
  3. Concat → 199-row merged CSV
  4. Recompute all summary metrics (tool_accuracy, Wilson CI, judge scores, latency...)
  5. Backup originals → exp3/{subdir}_backup/{mode}/
  6. Overwrite evaluation_results.csv + evaluation_summary.json

After this script completes, run:
  python scripts/experiments/exp3_e2e_comparison.py --compare-only
to regenerate the cross-config comparison table and exp3_summary.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "data" / "evaluation" / "thesis_final" / "exp3"
OLD_N = 171   # expected row count in original results

CONFIGS = {
    "E1": {"subdir": "e1_full_slm",          "mode": "routed"},
    "E2": {"subdir": "e2_slm_gpt4mini",      "mode": "routed"},
    "E3": {"subdir": "e3_gpt4mini_baseline", "mode": "baseline"},
    "E4": {"subdir": "e4_gpt4o_baseline",    "mode": "baseline"},
}

JUDGE_DIMS = [
    "judge_relevance", "judge_completeness", "judge_fluency",
    "judge_actionability", "judge_faithfulness",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _bool(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "1.0")


def _float_or_none(val) -> float | None:
    if val is None or str(val).strip() in ("", "None", "nan"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5) / denom
    return (round((centre - half) * 100, 1), round((centre + half) * 100, 1))


def _json_default(obj):
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ── Summary computation ───────────────────────────────────────────────────────

def _group_stats(group: list[dict], mode: str | None = None) -> dict:
    """Compute tool accuracy, success rate, latency, and judge scores for a group."""
    ng = len(group)
    tc  = sum(_bool(r.get("tool_correct", False)) for r in group)
    suc = sum(_bool(r.get("success", True))       for r in group)
    ci  = wilson_ci(tc, ng)
    times = [_float_or_none(r.get("response_time_ms")) for r in group]
    times_v = [t for t in times if t is not None]

    entry: dict = {
        "total":              ng,
        "success_rate":       round(suc / ng * 100, 1) if ng else 0.0,
        "tool_accuracy":      round(tc  / ng * 100, 1) if ng else 0.0,
        "tool_accuracy_ci95": list(ci),
        "avg_time_ms":        int(round(float(np.mean(times_v)))) if times_v else 0,
    }
    for dim in JUDGE_DIMS:
        scores = [_float_or_none(r.get(dim)) for r in group]
        valid  = [s for s in scores if s is not None]
        entry[f"{dim}_avg"] = round(float(np.mean(valid)), 2) if valid else None
    return entry


def compute_summary(rows: list[dict], mode: str) -> dict:
    n   = len(rows)
    tc  = sum(_bool(r.get("tool_correct", False)) for r in rows)
    suc = sum(_bool(r.get("success", True))       for r in rows)
    ci  = wilson_ci(tc, n)

    # Latency
    times   = [_float_or_none(r.get("response_time_ms")) for r in rows]
    times_v = [t for t in times if t is not None]

    # Tool precision / recall
    tprec_v = [_float_or_none(r.get("tool_precision")) for r in rows]
    trec_v  = [_float_or_none(r.get("tool_recall"))    for r in rows]
    tprec_v = [v for v in tprec_v if v is not None]
    trec_v  = [v for v in trec_v  if v is not None]

    summary: dict = {
        "total":             n,
        "successful":        suc,
        "success_rate":      round(suc / n * 100, 1) if n else 0.0,
        "tool_accuracy":     round(tc  / n * 100, 1) if n else 0.0,
        "tool_accuracy_ci95":    list(ci),
        "tool_precision_avg": round(float(np.mean(tprec_v)), 2) if tprec_v else None,
        "tool_recall_avg":    round(float(np.mean(trec_v)),  2) if trec_v  else None,
        "tool_recall_ci95":   list(ci),  # same n as tool_correct
        "avg_time_ms": int(round(float(np.mean(times_v))))    if times_v else 0,
        "p50_time_ms": int(round(float(np.percentile(times_v, 50)))) if times_v else 0,
        "p90_time_ms": int(round(float(np.percentile(times_v, 90)))) if times_v else 0,
        "p95_time_ms": int(round(float(np.percentile(times_v, 95)))) if times_v else 0,
    }

    # Router stats (routed mode only) — mirrors evaluate.py logic exactly
    if mode == "routed":
        routed_rows  = [r for r in rows if r.get("router_path") == "routed"]
        fallback_rows = [r for r in rows if r.get("router_path") == "fallback"]
        total_router = len(routed_rows) + len(fallback_rows)

        r_lats = [_float_or_none(r.get("router_latency_ms")) for r in rows]
        r_lats_v = [v for v in r_lats if v is not None]

        # Router intent accuracy: rows where router_intent is set
        intent_with_router = [r for r in rows if r.get("router_intent")]
        r_correct = sum(1 for r in intent_with_router
                        if r.get("router_intent") == r.get("intent"))
        r_n = len(intent_with_router)
        r_ci = wilson_ci(r_correct, r_n)

        # Routed-only tool accuracy (when router succeeded, not fallback)
        routed_tc = sum(1 for r in routed_rows if _bool(r.get("tool_correct", False)))

        summary["router_coverage"]    = round(len(routed_rows)  / total_router * 100, 1) if total_router else 0.0
        summary["router_fallback_rate"] = round(len(fallback_rows) / total_router * 100, 1) if total_router else 0.0
        summary["router_avg_latency_ms"]       = round(float(np.mean(r_lats_v)), 1) if r_lats_v else None
        summary["router_intent_accuracy"]      = round(r_correct / r_n * 100, 1) if r_n else None
        summary["router_intent_accuracy_ci95"] = list(r_ci)
        summary["routed_tool_accuracy"] = round(routed_tc / len(routed_rows) * 100, 1) if routed_rows else None
    else:
        summary["router_coverage"]             = None
        summary["router_fallback_rate"]        = None
        summary["router_avg_latency_ms"]       = None
        summary["router_intent_accuracy"]      = None
        summary["router_intent_accuracy_ci95"] = None
        summary["routed_tool_accuracy"]        = None

    # Judge scores (top-level)
    for dim in JUDGE_DIMS:
        scores = [_float_or_none(r.get(dim)) for r in rows]
        valid  = [s for s in scores if s is not None]
        summary[f"{dim}_avg"]   = round(float(np.mean(valid)), 2) if valid else None
        summary[f"{dim}_count"] = len(valid)

    # By intent
    by_intent: dict[str, list] = {}
    for r in rows:
        k = r.get("intent", "unknown").strip() or "unknown"
        by_intent.setdefault(k, []).append(r)
    summary["by_intent"] = {
        intent: _group_stats(group)
        for intent, group in sorted(by_intent.items())
    }

    # By difficulty
    by_diff: dict[str, list] = {}
    for r in rows:
        k = r.get("difficulty", "unknown").strip() or "unknown"
        by_diff.setdefault(k, []).append(r)
    summary["by_difficulty"] = {
        diff: _group_stats(group)
        for diff, group in sorted(by_diff.items())
    }

    summary["mode"] = mode
    return summary


# ── Diff display ─────────────────────────────────────────────────────────────

DIFF_FIELDS = [
    ("n",               "total",                       ""),
    ("Tool Acc",        "tool_accuracy",               "%"),
    ("Judge Relevance", "judge_relevance_avg",         ""),
    ("Judge Complete",  "judge_completeness_avg",      ""),
    ("Judge Fluency",   "judge_fluency_avg",           ""),
    ("Judge Action",    "judge_actionability_avg",     ""),
    ("Judge Faith",     "judge_faithfulness_avg",      ""),
    ("P50 ms",          "p50_time_ms",                 ""),
    ("P90 ms",          "p90_time_ms",                 ""),
]


def print_diff(cfg_id: str, old: dict, new: dict) -> None:
    print(f"\n  {'─'*56}")
    print(f"  [{cfg_id}]  n: {old.get('total')} → {new.get('total')}")
    print(f"  {'Metric':<24} {'Old':>8} {'New':>8} {'Δ':>8}")
    print(f"  {'─'*56}")
    for label, key, suffix in DIFF_FIELDS:
        ov = old.get(key)
        nv = new.get(key)
        if ov is None and nv is None:
            continue
        try:
            delta = float(nv) - float(ov)
            sign = "+" if delta >= 0 else ""
            print(f"  {label:<24} {float(ov):>7.2f}{suffix} {float(nv):>7.2f}{suffix} {sign}{delta:.2f}")
        except (TypeError, ValueError):
            print(f"  {label:<24} {str(ov):>8} {str(nv):>8}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge Exp 3 results: 171 + 28 → 199 questions per config"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — do not write any files")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip backing up original files before overwriting")
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS.keys()),
                        choices=list(CONFIGS.keys()),
                        help="Configs to merge (default: all)")
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  Merge Exp 3: {OLD_N} (original) + 28 (new) → 199 questions")
    if args.dry_run:
        print("  Mode: DRY-RUN — no files will be modified")
    print(f"{'═'*60}")

    any_missing = False
    for cfg_id in args.configs:
        cfg      = CONFIGS[cfg_id]
        subdir   = cfg["subdir"]
        mode     = cfg["mode"]

        old_csv  = OUTPUT_DIR / subdir / mode / "evaluation_results.csv"
        old_json = OUTPUT_DIR / subdir / mode / "evaluation_summary.json"
        new_csv  = OUTPUT_DIR / f"{subdir}_28new" / mode / "evaluation_results.csv"
        bak_dir  = OUTPUT_DIR / f"{subdir}_backup" / mode

        print(f"\n[{cfg_id}]  {subdir}/{mode}")

        # ── Validate inputs ──
        if not old_csv.exists():
            print(f"  ERROR: Original results not found: {old_csv}")
            any_missing = True
            continue
        if not new_csv.exists():
            print(f"  ERROR: New results not found: {new_csv}")
            print(f"  → Run first:")
            print(f"      python scripts/experiments/exp3_e2e_comparison.py "
                  f"--configs {cfg_id} --new-only")
            any_missing = True
            continue

        old_rows = load_csv(old_csv)
        new_rows = load_csv(new_csv)
        print(f"  Old CSV : {len(old_rows)} rows")
        print(f"  New CSV : {len(new_rows)} rows")

        if len(old_rows) != OLD_N:
            print(f"  WARNING: Expected {OLD_N} rows in original CSV, got {len(old_rows)}")
        if len(new_rows) == 0:
            print(f"  ERROR: New CSV is empty — skipping {cfg_id}")
            any_missing = True
            continue

        # ── Merge ──
        merged = old_rows + new_rows
        print(f"  Merged  : {len(merged)} rows")

        # ── Load old summary for diff ──
        old_summary: dict = {}
        if old_json.exists():
            with open(old_json, encoding="utf-8") as f:
                old_summary = json.load(f)

        # ── Recompute summary ──
        new_summary = compute_summary(merged, mode)

        # ── Print diff ──
        print_diff(cfg_id, old_summary, new_summary)

        if args.dry_run:
            print(f"\n  [DRY-RUN] Would overwrite:")
            print(f"    {old_csv}")
            print(f"    {old_json}")
            continue

        # ── Backup ──
        if not args.no_backup:
            bak_dir.mkdir(parents=True, exist_ok=True)
            if old_csv.exists():
                shutil.copy2(old_csv,  bak_dir / "evaluation_results_orig.csv")
            if old_json.exists():
                shutil.copy2(old_json, bak_dir / "evaluation_summary_orig.json")
            print(f"\n  Backed up originals → {bak_dir.relative_to(ROOT)}")

        # ── Overwrite ──
        save_csv(merged, old_csv)
        with open(old_json, "w", encoding="utf-8") as f:
            json.dump(new_summary, f, indent=2, ensure_ascii=False,
                      default=_json_default)
        print(f"  Saved {len(merged)} rows  → {old_csv.relative_to(ROOT)}")
        print(f"  Updated summary     → {old_json.relative_to(ROOT)}")

    # ── Footer ──
    print(f"\n{'═'*60}")
    if any_missing:
        print("  Some configs were skipped due to missing input files.")
        print("  Run the --new-only pipeline for missing configs, then re-run this script.")
    elif args.dry_run:
        print("  Dry-run complete — no files modified.")
    else:
        print("  All configs merged successfully.")
        print()
        print("  Next step — recompute cross-config comparison:")
        print("    python scripts/experiments/exp3_e2e_comparison.py --compare-only")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
