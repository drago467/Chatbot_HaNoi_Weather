"""Confidence Calibration for SLM Router — Temperature Scaling.

This script fits a scalar temperature T on the validation set to minimize
Negative Log-Likelihood (NLL), then evaluates:
- ECE (Expected Calibration Error) before/after calibration
- Per-intent optimal thresholds from precision-recall analysis
- Reliability diagram data

Reference:
- Guo et al. (2017) "On Calibration of Modern Neural Networks" (ICML)
- Adaptive Temperature Scaling: arxiv.org/abs/2409.19817

Usage:
    python scripts/router/calibrate.py
    python scripts/router/calibrate.py --val data/router/val_clean.jsonl
    python scripts/router/calibrate.py --output model/router/calibration.json

Output:
    model/router/calibration.json — fitted T + per-intent thresholds
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

import numpy as np
from scipy.optimize import minimize_scalar


# ── Intent label mapping (must match training order) ──
INTENT_LABELS = [
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
]
INTENT_TO_IDX = {intent: i for i, intent in enumerate(INTENT_LABELS)}
N_INTENTS = len(INTENT_LABELS)


def softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    x = x - x.max(axis=-1, keepdims=True)
    exp_x = np.exp(x)
    return exp_x / exp_x.sum(axis=-1, keepdims=True)


def load_val_data(val_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load validation JSONL and return (logits, labels).

    Expected JSONL format:
        {"input": "...", "output": {"intent": "...", "scope": "...", "confidence": 0.92}}

    Since we only have confidence (not raw logits) from the SLM, we approximate
    logits by: logit_correct = log(conf/(1-conf)), all others split uniformly.

    Returns:
        logits: (N, N_INTENTS) float array
        labels: (N,) int array of ground truth intent indices
    """
    records = []
    with open(val_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        raise ValueError(f"No records found in {val_path}")

    logits_list = []
    labels_list = []

    for rec in records:
        output = rec.get("output", {})
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except Exception:
                continue

        intent = output.get("intent", "")
        confidence = float(output.get("confidence", 0.8))
        confidence = max(0.01, min(0.99, confidence))  # Clip to avoid log(0)

        label_idx = INTENT_TO_IDX.get(intent, -1)
        if label_idx == -1:
            continue

        # Approximate logits from confidence
        # P(correct) = confidence → logit_correct = log(conf) - log(1-conf)
        # Distribute remaining probability uniformly across other classes
        logit_correct = np.log(confidence) - np.log(1 - confidence)
        other_prob = (1 - confidence) / (N_INTENTS - 1)
        logit_other = np.log(other_prob) - np.log(1 - other_prob + 1e-8)

        logits = np.full(N_INTENTS, logit_other)
        logits[label_idx] = logit_correct
        logits_list.append(logits)
        labels_list.append(label_idx)

    logits_arr = np.array(logits_list, dtype=np.float64)
    labels_arr = np.array(labels_list, dtype=np.int64)
    print(f"Loaded {len(labels_arr)} validation examples from {val_path}")
    return logits_arr, labels_arr


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """Expected Calibration Error with equal-width bins.

    Args:
        probs: (N, C) probability array
        labels: (N,) int array of ground truth
        n_bins: Number of bins (15 recommended)

    Returns:
        ECE value (lower = better calibrated)
    """
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(float)

    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(labels)

    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (confidences >= lo) & (confidences < hi)
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        bin_count = mask.sum()
        ece += (bin_count / n) * abs(bin_acc - bin_conf)

    return float(ece)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Fit scalar temperature T to minimize NLL on validation set.

    Args:
        logits: (N, C) raw logit array
        labels: (N,) ground truth class indices

    Returns:
        Optimal temperature T (T > 1 = softer, T < 1 = sharper)
    """
    def nll_loss(T: float) -> float:
        calibrated_probs = softmax(logits / T)
        # NLL = -mean(log(p_correct))
        correct_probs = calibrated_probs[np.arange(len(labels)), labels]
        correct_probs = np.clip(correct_probs, 1e-10, 1.0)
        return -np.mean(np.log(correct_probs))

    result = minimize_scalar(nll_loss, bounds=(0.1, 10.0), method="bounded")
    return float(result.x)


def compute_per_intent_thresholds(
    probs: np.ndarray, labels: np.ndarray, target_precision: float = 0.90
) -> dict[str, float]:
    """Compute per-intent confidence thresholds for target precision.

    For each intent, find the minimum threshold T* such that
    precision(intent | conf >= T*) >= target_precision.

    Args:
        probs: (N, C) calibrated probability array
        labels: (N,) ground truth
        target_precision: Desired precision (default 0.90)

    Returns:
        Dict mapping intent name → threshold float
    """
    thresholds = {}
    predictions = probs.argmax(axis=1)
    confidences = probs.max(axis=1)

    for intent_idx, intent_name in enumerate(INTENT_LABELS):
        # All predictions for this intent
        intent_mask = predictions == intent_idx
        if intent_mask.sum() < 5:
            # Not enough samples — use global default
            thresholds[intent_name] = 0.75
            continue

        intent_confs = confidences[intent_mask]
        intent_correct = (labels[intent_mask] == intent_idx).astype(float)

        # Sort by confidence descending and find threshold for target precision
        sorted_idx = np.argsort(intent_confs)[::-1]
        best_threshold = 0.75  # default

        for cutoff_idx in range(1, len(sorted_idx) + 1):
            top_k_confs = intent_confs[sorted_idx[:cutoff_idx]]
            top_k_correct = intent_correct[sorted_idx[:cutoff_idx]]
            precision = top_k_correct.mean()

            if precision >= target_precision and cutoff_idx >= 3:
                best_threshold = float(top_k_confs[-1])
                break

        # Clamp to [0.50, 0.90]
        thresholds[intent_name] = round(float(np.clip(best_threshold, 0.50, 0.90)), 2)

    return thresholds


def build_reliability_diagram_data(
    probs: np.ndarray, labels: np.ndarray, n_bins: int = 15
) -> list[dict]:
    """Build reliability diagram data for visualization.

    Returns list of bin dicts: {bin_lower, bin_upper, avg_confidence, accuracy, count}
    """
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(float)

    bins = np.linspace(0, 1, n_bins + 1)
    diagram = []

    for i in range(n_bins):
        lo, hi = float(bins[i]), float(bins[i + 1])
        mask = (confidences >= lo) & (confidences < hi)
        count = int(mask.sum())
        if count == 0:
            diagram.append({
                "bin_lower": round(lo, 3), "bin_upper": round(hi, 3),
                "avg_confidence": None, "accuracy": None, "count": 0,
            })
        else:
            diagram.append({
                "bin_lower": round(lo, 3), "bin_upper": round(hi, 3),
                "avg_confidence": round(float(confidences[mask].mean()), 4),
                "accuracy": round(float(accuracies[mask].mean()), 4),
                "count": count,
            })

    return diagram


def run_calibration(
    val_path: str = "data/router/val_clean.jsonl",
    output_path: str = "model/router/calibration.json",
    target_precision: float = 0.90,
) -> dict:
    """Main calibration pipeline.

    1. Load val set
    2. Fit temperature T (minimize NLL)
    3. Compute ECE before/after
    4. Compute per-intent thresholds
    5. Save to output_path

    Returns calibration result dict.
    """
    val_full = str(_ROOT / val_path) if not os.path.isabs(val_path) else val_path
    out_full = str(_ROOT / output_path) if not os.path.isabs(output_path) else output_path

    if not Path(val_full).exists():
        print(f"Val file not found: {val_full}")
        print("Run scripts/router/split_dataset.py first to generate val_clean.jsonl")
        return {}

    # Step 1: Load validation data
    logits, labels = load_val_data(val_full)

    # Step 2: ECE before calibration
    probs_before = softmax(logits)
    ece_before = compute_ece(probs_before, labels)
    acc_before = float((probs_before.argmax(axis=1) == labels).mean())
    print(f"Before calibration: ECE={ece_before:.4f}, Accuracy={acc_before:.4f}")

    # Step 3: Fit temperature
    T = fit_temperature(logits, labels)
    print(f"Fitted temperature: T = {T:.4f}")

    # Step 4: ECE after calibration
    probs_after = softmax(logits / T)
    ece_after = compute_ece(probs_after, labels)
    acc_after = float((probs_after.argmax(axis=1) == labels).mean())
    print(f"After calibration:  ECE={ece_after:.4f}, Accuracy={acc_after:.4f}")
    print(f"ECE improvement: {ece_before:.4f} → {ece_after:.4f} ({(ece_before - ece_after)/ece_before*100:.1f}% reduction)")

    # Step 5: Per-intent thresholds (from calibrated probs)
    per_intent_thresholds = compute_per_intent_thresholds(probs_after, labels, target_precision)
    print("\nPer-intent thresholds (target precision >= {:.0%}):".format(target_precision))
    for intent, thresh in sorted(per_intent_thresholds.items()):
        print(f"  {intent}: {thresh}")

    # Step 6: Reliability diagram data
    reliability_before = build_reliability_diagram_data(probs_before, labels)
    reliability_after = build_reliability_diagram_data(probs_after, labels)

    # Step 7: Save
    result = {
        "temperature": round(T, 4),
        "note": f"Fitted on {val_path} with {len(labels)} examples. Target precision={target_precision}",
        "fitted_on": val_path,
        "val_size": int(len(labels)),
        "val_ece_before": round(ece_before, 4),
        "val_ece_after": round(ece_after, 4),
        "val_accuracy": round(acc_after, 4),
        "per_intent_thresholds": per_intent_thresholds,
        "reliability_diagram_before": reliability_before,
        "reliability_diagram_after": reliability_after,
    }

    Path(out_full).parent.mkdir(parents=True, exist_ok=True)
    with open(out_full, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nCalibration saved to: {out_full}")
    print(f"Set SLM_CALIBRATION_TEMPERATURE={T:.4f} in .env to use calibrated confidence.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate SLM Router confidence via Temperature Scaling")
    parser.add_argument("--val", default="data/router/val_clean.jsonl",
                        help="Path to validation JSONL (relative to project root)")
    parser.add_argument("--output", default="model/router/calibration.json",
                        help="Output calibration JSON file")
    parser.add_argument("--target-precision", type=float, default=0.90,
                        help="Target precision for per-intent threshold computation (default: 0.90)")
    args = parser.parse_args()

    run_calibration(
        val_path=args.val,
        output_path=args.output,
        target_precision=args.target_precision,
    )
