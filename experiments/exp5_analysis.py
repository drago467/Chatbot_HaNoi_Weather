#!/usr/bin/env python3
"""
Experiment 5: Error Analysis & Case Studies (RQ3 supplement)

Pure analysis — NO model calls. Reads results from Exp 1/3/4 and produces:

  1. Confusion-matrix heatmap data (15x15 intent) for R1 router
  2. Per-intent weakness ranking (F1 sorted, bottom-5 highlighted)
  3. Failure taxonomy — classifies every error by root-cause category
  4. Case studies — 5 representative error examples with analysis
  5. Latency breakdown — P50/P90 across router configs + E2E pipeline
  6. Cross-experiment error summary

Outputs:
  data/evaluation/thesis_final/exp5/
    confusion_matrix_r1.csv          — 15x15 matrix for LaTeX/Excel
    per_intent_f1.csv                — all intents sorted by F1
    failure_taxonomy.csv             — every misclassified sample + category
    case_studies.json                — 5 detailed case objects
    latency_analysis.csv             — latency stats per config
    exp5_summary.json                — aggregate report
    confusion_heatmap_r1.png         — visual heatmap (if matplotlib available)

Usage:
  python experiments/exp5_analysis.py
  python experiments/exp5_analysis.py --no-plot   # skip heatmap PNG
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Paths ──
EXP1_DIR = ROOT / "data/evaluation/thesis_final/exp1_router"
EXP3_DIR = ROOT / "data/evaluation/thesis_final/exp3"
EXP4_DIR = ROOT / "data/evaluation/thesis_final/exp4"
OUTPUT   = ROOT / "data/evaluation/thesis_final/exp5"

# Canonical intent order (alphabetical for consistent heatmap)
INTENT_ORDER = [
    "activity_weather",
    "current_weather",
    "daily_forecast",
    "expert_weather_param",
    "historical_weather",
    "hourly_forecast",
    "humidity_fog_query",
    "location_comparison",
    "rain_query",
    "seasonal_context",
    "smalltalk_weather",
    "temperature_query",
    "weather_alert",
    "weather_overview",
    "wind_query",
]


# =====================================================================
#  1. CONFUSION MATRIX
# =====================================================================

def load_exp1_summary() -> dict:
    """Load Exp 1 summary JSON."""
    with open(EXP1_DIR / "summary.json", encoding="utf-8") as f:
        return json.load(f)


def export_confusion_matrix(summary: dict) -> list[list[int]]:
    """Extract R1 confusion matrix and export as labeled CSV."""
    r1 = summary["configs"][0]  # R1 is first config
    cm = r1["confusion_matrix"]
    labels = r1.get("confusion_labels", INTENT_ORDER)

    # Write CSV
    out_path = OUTPUT / "confusion_matrix_r1.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["actual \\ predicted"] + labels)
        for i, row in enumerate(cm):
            w.writerow([labels[i]] + row)

    print(f"[1/6] Confusion matrix → {out_path}")
    return cm


def plot_confusion_heatmap(cm: list[list[int]], labels: list[str]):
    """Generate heatmap PNG using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("      matplotlib not available, skipping heatmap PNG")
        return

    arr = np.array(cm, dtype=float)
    # Normalize per row (recall-based)
    row_sums = arr.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    norm = arr / row_sums

    fig, ax = plt.subplots(figsize=(14, 11))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)

    short_labels = [l.replace("_", "\n") for l in labels]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(short_labels, fontsize=7, rotation=45, ha="right")
    ax.set_yticklabels(short_labels, fontsize=7)
    ax.set_xlabel("Predicted Intent", fontsize=10)
    ax.set_ylabel("Actual Intent", fontsize=10)
    ax.set_title("R1 (Qwen3-4B FT) — Intent Confusion Matrix (row-normalized)",
                 fontsize=12, fontweight="bold")

    # Annotate cells
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = int(arr[i][j])
            if val > 0:
                color = "white" if norm[i][j] > 0.5 else "black"
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=6, color=color, fontweight="bold")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall ratio")
    fig.tight_layout()

    out_path = OUTPUT / "confusion_heatmap_r1.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"      Heatmap → {out_path}")


# =====================================================================
#  2. PER-INTENT WEAKNESS RANKING
# =====================================================================

def export_per_intent_f1(summary: dict) -> list[dict]:
    """Rank intents by F1 for R1, export CSV."""
    r1 = summary["configs"][0]
    report = r1["per_intent_report"]

    rows = []
    for intent in INTENT_ORDER:
        m = report.get(intent, {})
        rows.append({
            "intent": intent,
            "precision": round(m.get("precision", 0), 4),
            "recall": round(m.get("recall", 0), 4),
            "f1": round(m.get("f1-score", 0), 4),
            "support": int(m.get("support", 0)),
        })
    rows.sort(key=lambda r: r["f1"])

    out_path = OUTPUT / "per_intent_f1.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["intent", "precision", "recall", "f1", "support"])
        w.writeheader()
        w.writerows(rows)

    print(f"[2/6] Per-intent F1 ranking → {out_path}")
    print("      Bottom-5 intents:")
    for r in rows[:5]:
        print(f"        {r['intent']:30s}  F1={r['f1']:.3f}  P={r['precision']:.3f}  R={r['recall']:.3f}")
    return rows


# =====================================================================
#  3. FAILURE TAXONOMY
# =====================================================================

# Error categories for classification failures
TAXONOMY = {
    # temporal_overlap: forecast horizon confusion (daily/hourly/rain)
    ("daily_forecast", "rain_query"):       "temporal_overlap",
    ("rain_query", "daily_forecast"):       "temporal_overlap",
    ("hourly_forecast", "rain_query"):      "temporal_overlap",
    ("rain_query", "hourly_forecast"):      "temporal_overlap",
    ("rain_query", "weather_overview"):     "temporal_overlap",

    # temporal_granularity: hourly vs daily confusion
    ("hourly_forecast", "daily_forecast"):  "temporal_granularity",
    ("daily_forecast", "hourly_forecast"):  "temporal_granularity",
    ("hourly_forecast", "weather_overview"): "temporal_granularity",
    ("weather_overview", "hourly_forecast"): "temporal_granularity",

    # specificity_mismatch: general weather vs specific parameter
    ("current_weather", "temperature_query"):   "specificity_mismatch",
    ("temperature_query", "current_weather"):   "specificity_mismatch",
    ("current_weather", "humidity_fog_query"):  "specificity_mismatch",
    ("humidity_fog_query", "current_weather"):  "specificity_mismatch",
    ("current_weather", "wind_query"):          "specificity_mismatch",
    ("wind_query", "current_weather"):          "specificity_mismatch",
    ("current_weather", "rain_query"):          "specificity_mismatch",
    ("hourly_forecast", "temperature_query"):   "specificity_mismatch",
    ("weather_overview", "temperature_query"):  "specificity_mismatch",
    ("expert_weather_param", "humidity_fog_query"): "specificity_mismatch",

    # scope_ambiguity: overview vs specific forecast
    ("current_weather", "weather_overview"):    "scope_ambiguity",
    ("weather_overview", "current_weather"):    "scope_ambiguity",
    ("weather_overview", "daily_forecast"):     "scope_ambiguity",
    ("daily_forecast", "weather_overview"):     "scope_ambiguity",
    ("location_comparison", "daily_forecast"):  "scope_ambiguity",

    # formality_mismatch: casual/smalltalk vs specific intent
    ("smalltalk_weather", "current_weather"):   "formality_mismatch",
    ("current_weather", "smalltalk_weather"):   "formality_mismatch",
    ("smalltalk_weather", "weather_overview"):  "formality_mismatch",
    ("weather_overview", "smalltalk_weather"):  "formality_mismatch",
    ("smalltalk_weather", "temperature_query"): "formality_mismatch",
    ("smalltalk_weather", "humidity_fog_query"): "formality_mismatch",
    ("smalltalk_weather", "activity_weather"):  "formality_mismatch",
    ("smalltalk_weather", "rain_query"):        "formality_mismatch",

    # temporal_scope: seasonal/historical confusion
    ("seasonal_context", "daily_forecast"):     "temporal_scope",
    ("daily_forecast", "seasonal_context"):     "temporal_scope",
    ("seasonal_context", "historical_weather"): "temporal_scope",
    ("historical_weather", "seasonal_context"): "temporal_scope",
    ("seasonal_context", "weather_overview"):   "temporal_scope",
    ("seasonal_context", "activity_weather"):   "temporal_scope",
    ("location_comparison", "seasonal_context"): "temporal_scope",

    # alert_vs_info: weather alert vs informational query
    ("weather_alert", "rain_query"):            "alert_vs_info",
    ("rain_query", "weather_alert"):            "alert_vs_info",
    ("weather_alert", "weather_overview"):       "alert_vs_info",
    ("weather_alert", "hourly_forecast"):        "alert_vs_info",
    ("hourly_forecast", "weather_alert"):        "alert_vs_info",
    ("weather_alert", "temperature_query"):      "alert_vs_info",
    ("weather_alert", "seasonal_context"):       "alert_vs_info",

    # comparison_vs_single: location comparison vs single-location
    ("location_comparison", "current_weather"):  "comparison_vs_single",
    ("current_weather", "location_comparison"):  "comparison_vs_single",
    ("location_comparison", "humidity_fog_query"): "comparison_vs_single",
}

TAXONOMY_DESCRIPTIONS = {
    "temporal_overlap":      "Ambiguity between forecast horizons (daily vs hourly vs rain)",
    "temporal_granularity":  "Confusion between hourly and daily time scales",
    "specificity_mismatch":  "General weather vs specific parameter (temp, wind, humidity)",
    "scope_ambiguity":       "Overlap between overview and specific forecast types",
    "formality_mismatch":    "Casual/smalltalk query misclassified as specific intent",
    "temporal_scope":        "Seasonal/historical vs daily forecast confusion",
    "alert_vs_info":         "Weather alert vs informational query confusion",
    "comparison_vs_single":  "Location comparison vs single-location query",
    "other":                 "No clear pattern — requires manual inspection",
}


def build_failure_taxonomy(summary: dict) -> list[dict]:
    """Load predictions CSV, classify every R1 error, export taxonomy CSV."""
    pred_path = EXP1_DIR / "predictions.csv"
    errors = []

    with open(pred_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected = row["expected_intent"]
            predicted = row["R1_intent"]
            if expected == predicted:
                continue  # correct — skip

            pair = (expected, predicted)
            category = TAXONOMY.get(pair, "other")

            errors.append({
                "idx": row["idx"],
                "query": row["input"],
                "expected_intent": expected,
                "predicted_intent": predicted,
                "expected_scope": row["expected_scope"],
                "predicted_scope": row["R1_scope"],
                "confidence": row["R1_conf"],
                "error_category": category,
                "category_description": TAXONOMY_DESCRIPTIONS[category],
                "scope_also_wrong": row["expected_scope"] != row["R1_scope"],
            })

    # Export
    out_path = OUTPUT / "failure_taxonomy.csv"
    if errors:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=errors[0].keys())
            w.writeheader()
            w.writerows(errors)

    # Summary by category
    cat_counts = Counter(e["error_category"] for e in errors)
    total_errors = len(errors)
    total_samples = summary["n_samples"]

    print(f"[3/6] Failure taxonomy → {out_path}")
    print(f"      Total errors: {total_errors}/{total_samples} ({total_errors/total_samples*100:.1f}%)")
    print(f"      By category:")
    for cat, count in cat_counts.most_common():
        pct = count / total_errors * 100 if total_errors > 0 else 0
        print(f"        {cat:25s}  {count:3d} ({pct:.1f}%)  — {TAXONOMY_DESCRIPTIONS[cat]}")

    return errors


# =====================================================================
#  4. CASE STUDIES
# =====================================================================

def select_case_studies(errors: list[dict], summary: dict) -> list[dict]:
    """Pick 5 representative case studies from different error categories."""
    # Strategy: 1 case per top category, prioritize high-confidence errors
    # (high confidence + wrong = most interesting for thesis)
    categories_seen = set()
    cases = []

    # Sort by confidence descending — high-confidence errors are most insightful
    sorted_errors = sorted(errors, key=lambda e: float(e["confidence"]), reverse=True)

    for err in sorted_errors:
        cat = err["error_category"]
        if cat in categories_seen:
            continue
        categories_seen.add(cat)

        # Build case study object
        case = {
            "case_id": len(cases) + 1,
            "query": err["query"],
            "expected_intent": err["expected_intent"],
            "predicted_intent": err["predicted_intent"],
            "confidence": float(err["confidence"]),
            "error_category": cat,
            "scope_error": err["scope_also_wrong"],
            "analysis": _generate_analysis(err),
        }
        cases.append(case)
        if len(cases) >= 5:
            break

    # If fewer than 5 categories, add more from largest category
    if len(cases) < 5:
        cat_counts = Counter(e["error_category"] for e in errors)
        largest_cat = cat_counts.most_common(1)[0][0] if cat_counts else "other"
        for err in sorted_errors:
            if err["error_category"] == largest_cat and err["query"] not in [c["query"] for c in cases]:
                case = {
                    "case_id": len(cases) + 1,
                    "query": err["query"],
                    "expected_intent": err["expected_intent"],
                    "predicted_intent": err["predicted_intent"],
                    "confidence": float(err["confidence"]),
                    "error_category": err["error_category"],
                    "scope_error": err["scope_also_wrong"],
                    "analysis": _generate_analysis(err),
                }
                cases.append(case)
                if len(cases) >= 5:
                    break

    out_path = OUTPUT / "case_studies.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    print(f"[4/6] Case studies ({len(cases)}) → {out_path}")
    for c in cases:
        print(f'      CS{c["case_id"]}: "{c["query"][:60]}..."')
        print(f'        {c["expected_intent"]} → {c["predicted_intent"]} '
              f'(conf={c["confidence"]:.2f}, cat={c["error_category"]})')

    return cases


def _generate_analysis(err: dict) -> str:
    """Generate analysis text for a case study based on error category."""
    cat = err["error_category"]
    exp = err["expected_intent"]
    pred = err["predicted_intent"]
    q = err["query"]

    analyses = {
        "temporal_overlap": (
            f"The query contains temporal cues that overlap between '{exp}' and "
            f"'{pred}'. Vietnamese weather queries often embed implicit time "
            f"references (e.g., 'chiều mai' could trigger both daily_forecast "
            f"and rain_query). The router chose '{pred}' with confidence "
            f"{err['confidence']}, suggesting the temporal signal was ambiguous."
        ),
        "temporal_granularity": (
            f"The router confused the time granularity: '{exp}' operates at a "
            f"different temporal resolution than '{pred}'. This is a known "
            f"challenge in weather NLU where 'ngày mai' (tomorrow) could be "
            f"interpreted as needing hourly or daily granularity."
        ),
        "specificity_mismatch": (
            f"The query asks about a specific weather parameter ('{exp}') but "
            f"the router classified it as the more general '{pred}'. This "
            f"indicates the model sometimes fails to detect parameter-specific "
            f"keywords when they co-occur with general weather terms."
        ),
        "scope_ambiguity": (
            f"The query could reasonably be classified as either '{exp}' or "
            f"'{pred}' — both are valid interpretations depending on user "
            f"intent. This ambiguity is inherent in weather queries that don't "
            f"specify a clear temporal scope."
        ),
        "formality_mismatch": (
            f"The casual/conversational phrasing of '{q[:50]}' was misclassified. "
            f"Smalltalk-style weather queries use informal Vietnamese that the "
            f"router maps to a specific intent rather than the smalltalk category."
        ),
        "temporal_scope": (
            f"Confusion between seasonal/historical context and forecast scope. "
            f"The query references a broader time range that overlaps with both "
            f"'{exp}' and '{pred}' intent definitions."
        ),
        "alert_vs_info": (
            f"The query about weather warnings/alerts was confused with an "
            f"informational query. Vietnamese alert queries often use similar "
            f"vocabulary to regular weather inquiries."
        ),
        "comparison_vs_single": (
            f"The router failed to detect the comparative aspect of the query, "
            f"classifying a location comparison as a single-location query."
        ),
        "other": (
            f"This error does not fit standard taxonomy patterns. "
            f"Expected '{exp}' but predicted '{pred}' with confidence "
            f"{err['confidence']}. May indicate a labeling edge case or "
            f"a novel error pattern requiring further investigation."
        ),
    }
    return analyses.get(cat, analyses["other"])


# =====================================================================
#  5. LATENCY ANALYSIS
# =====================================================================

def export_latency_analysis(exp1_summary: dict) -> list[dict]:
    """Extract and export latency stats from Exp 1 + Exp 3."""
    rows = []

    # Exp 1: Router latency (4 configs)
    for cfg in exp1_summary["configs"]:
        lat = cfg["latency"]
        rows.append({
            "experiment": "Exp1_Router",
            "config": cfg["config"][:50],
            "p50_ms": lat["p50_ms"],
            "p90_ms": lat["p90_ms"],
            "p95_ms": lat["p95_ms"],
            "mean_ms": lat["mean_ms"],
            "min_ms": lat["min_ms"],
            "max_ms": lat["max_ms"],
        })

    # Exp 3: E2E pipeline latency (4 configs)
    exp3_path = EXP3_DIR / "exp3_summary.json"
    if exp3_path.exists():
        with open(exp3_path, encoding="utf-8") as f:
            exp3 = json.load(f)
        for cfg in exp3["configs"]:
            rows.append({
                "experiment": "Exp3_E2E",
                "config": cfg["config"][:50],
                "p50_ms": cfg.get("p50_ms"),
                "p90_ms": cfg.get("p90_ms"),
                "p95_ms": cfg.get("p95_ms"),
                "mean_ms": cfg.get("avg_ms"),
                "min_ms": None,
                "max_ms": None,
            })

    out_path = OUTPUT / "latency_analysis.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"[5/6] Latency analysis → {out_path}")
    print(f"      {'Config':50s}  {'P50':>8s}  {'P90':>8s}  {'Mean':>8s}")
    for r in rows:
        p50 = f"{r['p50_ms']:.0f}" if r['p50_ms'] else "N/A"
        p90 = f"{r['p90_ms']:.0f}" if r['p90_ms'] else "N/A"
        mean = f"{r['mean_ms']:.0f}" if r['mean_ms'] else "N/A"
        print(f"      {r['config']:50s}  {p50:>8s}  {p90:>8s}  {mean:>8s}")

    return rows


# =====================================================================
#  6. CROSS-EXPERIMENT SUMMARY
# =====================================================================

def build_exp5_summary(
    cm: list[list[int]],
    f1_rows: list[dict],
    errors: list[dict],
    cases: list[dict],
    latency_rows: list[dict],
) -> dict:
    """Compile full Exp 5 summary JSON."""
    cat_counts = Counter(e["error_category"] for e in errors)
    total_samples = 672  # from Exp 1

    # Exp 4 pattern-level failures
    exp4_patterns = {}
    exp4_path = EXP4_DIR / "exp4_summary.json"
    if exp4_path.exists():
        with open(exp4_path, encoding="utf-8") as f:
            exp4 = json.load(f)
        # Compare MT-Full vs MT-Base by pattern
        base_patterns = exp4.get("MT-Base", {}).get("by_pattern", {})
        full_patterns = exp4.get("MT-Full", {}).get("by_pattern", {})
        for pattern in base_patterns:
            base_csr = base_patterns[pattern]["csr"]
            full_csr = full_patterns.get(pattern, {}).get("csr", 0)
            exp4_patterns[pattern] = {
                "base_csr": base_csr,
                "full_csr": full_csr,
                "improvement_pp": round(full_csr - base_csr, 1),
            }

    # Bottom/Top intents
    bottom_5 = f1_rows[:5]
    top_5 = f1_rows[-5:]

    summary = {
        "experiment": "Exp5_Error_Analysis",
        "description": "Qualitative error analysis across Exp 1/3/4",
        "data_sources": {
            "exp1_router": f"{total_samples} samples, 4 configs",
            "exp3_e2e": "171 questions, 4 configs",
            "exp4_multiturn": "60 conversations, 188 turns, 3 configs",
        },
        "confusion_matrix": {
            "router": "R1 (Qwen3-4B FT)",
            "total_errors": len(errors),
            "error_rate_pct": round(len(errors) / total_samples * 100, 1),
        },
        "weakness_analysis": {
            "bottom_5_intents": [
                {"intent": r["intent"], "f1": r["f1"], "support": r["support"]}
                for r in bottom_5
            ],
            "top_5_intents": [
                {"intent": r["intent"], "f1": r["f1"], "support": r["support"]}
                for r in top_5
            ],
        },
        "failure_taxonomy": {
            "total_errors": len(errors),
            "categories": {
                cat: {
                    "count": count,
                    "pct": round(count / len(errors) * 100, 1) if errors else 0,
                    "description": TAXONOMY_DESCRIPTIONS[cat],
                }
                for cat, count in cat_counts.most_common()
            },
        },
        "case_studies_count": len(cases),
        "multiturn_pattern_analysis": exp4_patterns,
        "key_findings": [
            f"Router R1 achieves {round(100 - len(errors)/total_samples*100, 1)}% "
            f"intent accuracy with {len(errors)} total errors",
            f"Most common error category: "
            f"{cat_counts.most_common(1)[0][0] if cat_counts else 'N/A'} "
            f"({cat_counts.most_common(1)[0][1] if cat_counts else 0} cases)",
            f"Weakest intent: {bottom_5[0]['intent']} "
            f"(F1={bottom_5[0]['f1']:.3f})" if bottom_5 else "N/A",
            f"Strongest intent: {top_5[-1]['intent']} "
            f"(F1={top_5[-1]['f1']:.3f})" if top_5 else "N/A",
        ],
    }

    out_path = OUTPUT / "exp5_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[6/6] Summary → {out_path}")
    print()
    print("=" * 60)
    print("  EXP 5 — KEY FINDINGS")
    print("=" * 60)
    for i, finding in enumerate(summary["key_findings"], 1):
        print(f"  {i}. {finding}")

    if exp4_patterns:
        print()
        print("  Multi-turn pattern improvements (Base → Full):")
        for pat, data in sorted(exp4_patterns.items(), key=lambda x: x[1]["improvement_pp"]):
            delta = data["improvement_pp"]
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "="
            sign = "+" if delta >= 0 else ""
            print(f"    {pat:25s}  {data['base_csr']:5.1f}% → {data['full_csr']:5.1f}%  "
                  f"({arrow} {sign}{delta:.1f}pp)")

    return summary


# =====================================================================
#  MAIN
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Exp 5: Error Analysis & Case Studies")
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip confusion matrix heatmap generation")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  EXPERIMENT 5: ERROR ANALYSIS & CASE STUDIES")
    print("=" * 60)
    print()

    # Load Exp 1 data
    exp1_summary = load_exp1_summary()

    # 1. Confusion matrix
    cm = export_confusion_matrix(exp1_summary)
    if not args.no_plot:
        labels = exp1_summary["configs"][0].get("confusion_labels", INTENT_ORDER)
        plot_confusion_heatmap(cm, labels)

    print()

    # 2. Per-intent F1 ranking
    f1_rows = export_per_intent_f1(exp1_summary)
    print()

    # 3. Failure taxonomy
    errors = build_failure_taxonomy(exp1_summary)
    print()

    # 4. Case studies
    cases = select_case_studies(errors, exp1_summary)
    print()

    # 5. Latency
    latency_rows = export_latency_analysis(exp1_summary)
    print()

    # 6. Summary
    build_exp5_summary(cm, f1_rows, errors, cases, latency_rows)

    print()
    print("=" * 60)
    print("  Exp 5 complete. All outputs in:")
    print(f"  {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
