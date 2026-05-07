"""Phase 10 — Calibration analysis cho router v7.1.

Input : training/notebooks/run_03/outputs_02/exp6_per_sample.csv
        (385 val samples với pred_intent, pred_conf, gt_intent, route_ok)

Output:
- experiments/calibration/outputs/ece_summary.json — ECE overall + per-intent
- experiments/calibration/outputs/threshold_recommendations.json — tune đề xuất
- experiments/calibration/outputs/reliability_diagram.png — overall + per-intent
- experiments/calibration/outputs/confidence_histograms.png — pred_conf per intent
- experiments/calibration/outputs/threshold_f1_curves.png — F1 vs threshold per intent

Nguyên lý:
- Router output 5 tier (0.62/0.74/0.80/0.85/0.92) → confidence rời rạc.
- Vì confidence rời rạc, ECE tính trên các tier (không phải bin liên tục).
- Threshold tune theo F1: với mỗi intent, sweep threshold từ 0.5→0.95, tìm value
  cho F1 cao nhất KHI intent đó được predict.
- Filter: chỉ tune intent có ≥10 prediction (đủ signal).

Usage: python experiments/calibration/analyze_router_calibration.py
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EVAL_CSV = ROOT / "training/notebooks/run_03/outputs_02/exp6_per_sample.csv"
OUT_DIR = ROOT / "experiments/calibration/outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CURRENT_THRESHOLDS = {
    "current_weather":      0.82,
    "hourly_forecast":      0.82,
    "daily_forecast":       0.80,
    "weather_overview":     0.85,
    "rain_query":           0.85,
    "temperature_query":    0.82,
    "wind_query":           0.80,
    "humidity_fog_query":   0.82,
    "historical_weather":   0.82,
    "location_comparison":  0.82,
    "activity_weather":     0.75,
    "expert_weather_param": 0.79,
    "weather_alert":        0.73,
    "seasonal_context":     0.78,
    "smalltalk_weather":    0.85,
}


def load_samples() -> list[dict]:
    rows = []
    with open(EVAL_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["pred_conf"] = float(row["pred_conf"]) if row["pred_conf"] else 0.0
            row["route_ok"] = row["route_ok"].lower() == "true"
            rows.append(row)
    return rows


def compute_ece(samples: list[dict], n_bins: int = 10) -> dict:
    """Expected Calibration Error — bin confidences, so sánh acc vs avg_conf.

    ECE = sum_bin (|bin| / N) * |acc(bin) - avg_conf(bin)|
    """
    bins = [(i / n_bins, (i + 1) / n_bins) for i in range(n_bins)]
    bin_data = []
    n = len(samples)
    ece = 0.0
    for lo, hi in bins:
        in_bin = [s for s in samples if lo <= s["pred_conf"] < hi or
                  (hi == 1.0 and s["pred_conf"] == 1.0)]
        if not in_bin:
            bin_data.append({"range": (lo, hi), "n": 0, "acc": None, "conf": None})
            continue
        acc = sum(s["route_ok"] for s in in_bin) / len(in_bin)
        avg_conf = sum(s["pred_conf"] for s in in_bin) / len(in_bin)
        weight = len(in_bin) / n
        ece += weight * abs(acc - avg_conf)
        bin_data.append({
            "range": (round(lo, 2), round(hi, 2)),
            "n": len(in_bin),
            "acc": round(acc, 4),
            "conf": round(avg_conf, 4),
        })
    return {"ece": round(ece, 4), "n_bins": n_bins, "bins": bin_data}


def compute_tier_calibration(samples: list[dict]) -> dict:
    """Confidence rời rạc 5-tier — tính acc trên từng tier."""
    by_tier = defaultdict(list)
    for s in samples:
        by_tier[s["pred_conf"]].append(s["route_ok"])
    rows = []
    for tier in sorted(by_tier.keys()):
        results = by_tier[tier]
        rows.append({
            "tier": tier,
            "n": len(results),
            "accuracy": round(sum(results) / len(results), 4),
            "expected": tier,
            "gap": round(abs(sum(results) / len(results) - tier), 4),
        })
    return {"tiers": rows}


def per_intent_threshold_sweep(
    samples: list[dict],
    intent: str,
    sweep: np.ndarray,
) -> dict:
    """Với mỗi candidate threshold τ, tính:
    - precision = predict==intent ∧ correct ∧ pred_conf≥τ / predict==intent ∧ pred_conf≥τ
    - recall    = predict==intent ∧ correct ∧ pred_conf≥τ / gt==intent
    - F1        = 2*P*R/(P+R)
    - n_routed  = predict==intent ∧ pred_conf≥τ (số sample sẽ vào fast path)

    Note: τ bên dưới chỉ ảnh hưởng accept/reject CỦA INTENT NÀY. Sample bị reject
    rơi fallback agent — vẫn có thể correct, nên đây là conservative analysis.
    """
    pred_intent_mask = [s["pred_intent"] == intent for s in samples]
    gt_intent_mask = [s["gt_intent"] == intent for s in samples]
    n_gt = sum(gt_intent_mask)
    if n_gt < 10:
        return {"intent": intent, "n_gt": n_gt, "skipped": "insufficient ground truth"}

    rows = []
    best = {"threshold": None, "f1": -1, "precision": 0, "recall": 0, "n_routed": 0}
    for tau in sweep:
        tp = sum(
            1
            for s, p in zip(samples, pred_intent_mask)
            if p and s["pred_conf"] >= tau and s["route_ok"] and s["gt_intent"] == intent
        )
        fp = sum(
            1
            for s, p in zip(samples, pred_intent_mask)
            if p and s["pred_conf"] >= tau and s["gt_intent"] != intent
        )
        fn = sum(
            1
            for s, g in zip(samples, gt_intent_mask)
            if g and (s["pred_intent"] != intent or s["pred_conf"] < tau)
        )
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        n_routed = sum(1 for s, p in zip(samples, pred_intent_mask) if p and s["pred_conf"] >= tau)
        rows.append({
            "tau": round(tau, 3),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "n_routed": n_routed,
        })
        if f1 > best["f1"]:
            best = {
                "threshold": round(tau, 3),
                "f1": round(f1, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "n_routed": n_routed,
            }
    return {"intent": intent, "n_gt": n_gt, "sweep": rows, "best_f1": best}


def plot_reliability(samples: list[dict], path: Path):
    tier_cal = compute_tier_calibration(samples)
    tiers = [r["tier"] for r in tier_cal["tiers"]]
    accs = [r["accuracy"] for r in tier_cal["tiers"]]
    ns = [r["n"] for r in tier_cal["tiers"]]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Perfect calibration")
    sizes = [50 + 10 * n for n in ns]
    ax.scatter(tiers, accs, s=sizes, c="steelblue", alpha=0.7, edgecolors="navy")
    for t, a, n in zip(tiers, accs, ns):
        ax.annotate(f"n={n}", (t, a), textcoords="offset points", xytext=(8, 8))
    ax.set_xlabel("Predicted confidence (tier)")
    ax.set_ylabel("Empirical accuracy")
    ax.set_title("Reliability — 5-tier calibration")
    ax.set_xlim(0.55, 1.0)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.3)
    ax.legend()

    ax = axes[1]
    ax.bar(tiers, ns, width=0.04, color="darkorange", alpha=0.7)
    ax.set_xlabel("Predicted confidence (tier)")
    ax.set_ylabel("# samples")
    ax.set_title("Confidence distribution (val 385)")
    ax.set_xlim(0.55, 1.0)
    ax.grid(alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close()


def plot_per_intent_histogram(samples: list[dict], path: Path):
    by_intent = defaultdict(list)
    for s in samples:
        by_intent[s["pred_intent"]].append(s["pred_conf"])

    intents = sorted(by_intent.keys())
    n_intents = len(intents)
    n_cols = 4
    n_rows = (n_intents + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    axes = axes.flatten()

    for ax, intent in zip(axes, intents):
        confs = by_intent[intent]
        ax.hist(confs, bins=np.arange(0.55, 1.0, 0.03), color="steelblue", alpha=0.7)
        cur_thr = CURRENT_THRESHOLDS.get(intent)
        if cur_thr:
            ax.axvline(cur_thr, color="red", linestyle="--", alpha=0.7, label=f"current τ={cur_thr}")
        ax.set_title(f"{intent} (n={len(confs)})")
        ax.set_xlim(0.55, 1.0)
        ax.legend(fontsize=8)

    for ax in axes[len(intents):]:
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close()


def plot_threshold_f1_curves(per_intent_results: dict, path: Path):
    valid = [r for r in per_intent_results.values() if "sweep" in r]
    n_intents = len(valid)
    n_cols = 4
    n_rows = (n_intents + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    axes = axes.flatten()

    for ax, r in zip(axes, valid):
        taus = [row["tau"] for row in r["sweep"]]
        f1s = [row["f1"] for row in r["sweep"]]
        precs = [row["precision"] for row in r["sweep"]]
        recs = [row["recall"] for row in r["sweep"]]
        ax.plot(taus, f1s, label="F1", color="steelblue", linewidth=2)
        ax.plot(taus, precs, label="Precision", color="green", alpha=0.6)
        ax.plot(taus, recs, label="Recall", color="orange", alpha=0.6)
        cur_thr = CURRENT_THRESHOLDS.get(r["intent"])
        if cur_thr:
            ax.axvline(cur_thr, color="red", linestyle="--", alpha=0.5, label=f"current={cur_thr}")
        best = r["best_f1"]["threshold"]
        ax.axvline(best, color="purple", linestyle=":", alpha=0.7, label=f"best={best}")
        ax.set_title(f"{r['intent']} (n_gt={r['n_gt']})")
        ax.set_xlabel("threshold τ")
        ax.set_ylabel("metric")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)

    for ax in axes[len(valid):]:
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close()


def main():
    samples = load_samples()
    print(f"Loaded {len(samples)} val samples")

    # ── Overall ECE ──
    ece_result = compute_ece(samples, n_bins=10)
    tier_result = compute_tier_calibration(samples)
    print(f"\nECE overall: {ece_result['ece']}")
    print("\n5-tier calibration:")
    for r in tier_result["tiers"]:
        print(f"  τ={r['tier']:.2f}  n={r['n']:3d}  acc={r['accuracy']:.4f}  gap={r['gap']:.4f}")

    # ── Per-intent threshold sweep ──
    sweep = np.arange(0.50, 0.96, 0.01)
    per_intent_results = {}
    for intent in CURRENT_THRESHOLDS:
        r = per_intent_threshold_sweep(samples, intent, sweep)
        per_intent_results[intent] = r

    # ── Threshold recommendations ──
    print("\n" + "=" * 80)
    print("Per-intent threshold tuning (max F1):")
    print("=" * 80)
    print(f"{'intent':<22} {'n_gt':>5} {'cur_τ':>6} {'best_τ':>7} {'best_f1':>8} {'cur_f1_at_τ':>12}")
    recs = {}
    for intent, r in per_intent_results.items():
        cur_thr = CURRENT_THRESHOLDS[intent]
        if "sweep" not in r:
            print(f"{intent:<22} {r['n_gt']:>5} {cur_thr:>6.2f}  SKIPPED (insufficient gt)")
            recs[intent] = {"current": cur_thr, "recommended": cur_thr, "reason": "insufficient_gt"}
            continue

        cur_row = next((row for row in r["sweep"] if abs(row["tau"] - cur_thr) < 0.001), None)
        cur_f1 = cur_row["f1"] if cur_row else None
        best = r["best_f1"]
        delta_f1 = best["f1"] - (cur_f1 or 0)

        # Conservative tune: chỉ thay đổi nếu best_f1 - cur_f1 ≥ 0.02 (2pp F1 gain).
        # Smaller gains likely noise (n_gt < 30 cho hầu hết intent).
        if delta_f1 >= 0.02:
            recommended = best["threshold"]
            reason = f"best_f1_gain_{delta_f1:.3f}"
        else:
            recommended = cur_thr
            reason = "no_significant_gain"

        recs[intent] = {
            "current": cur_thr,
            "recommended": recommended,
            "current_f1_at_threshold": cur_f1,
            "best_threshold": best["threshold"],
            "best_f1": best["f1"],
            "delta_f1": round(delta_f1, 4),
            "n_gt": r["n_gt"],
            "reason": reason,
        }
        flag = " ★" if recommended != cur_thr else ""
        cur_f1_str = f"{cur_f1:.4f}" if cur_f1 is not None else "N/A"
        print(f"{intent:<22} {r['n_gt']:>5} {cur_thr:>6.2f} {best['threshold']:>7.2f} {best['f1']:>8.4f} {cur_f1_str:>12}{flag}")

    # ── Save outputs ──
    json.dump(
        {"ece": ece_result, "tier_calibration": tier_result},
        open(OUT_DIR / "ece_summary.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )
    json.dump(
        recs,
        open(OUT_DIR / "threshold_recommendations.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )
    json.dump(
        per_intent_results,
        open(OUT_DIR / "per_intent_sweep.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False,
    )

    # ── Plots ──
    plot_reliability(samples, OUT_DIR / "reliability_diagram.png")
    plot_per_intent_histogram(samples, OUT_DIR / "confidence_histograms.png")
    plot_threshold_f1_curves(per_intent_results, OUT_DIR / "threshold_f1_curves.png")

    print(f"\nOutputs saved to {OUT_DIR}/")
    print("  - ece_summary.json")
    print("  - threshold_recommendations.json")
    print("  - per_intent_sweep.json")
    print("  - reliability_diagram.png")
    print("  - confidence_histograms.png")
    print("  - threshold_f1_curves.png")

    # ── Final summary ──
    n_changed = sum(1 for r in recs.values() if r["recommended"] != r["current"])
    print(f"\n{n_changed}/{len(recs)} intents có recommended threshold khác current")


if __name__ == "__main__":
    main()
