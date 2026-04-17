"""Calibrate SLM Router v6 from exp6_per_sample.csv evaluation results.

This script reads predictions from the evaluation CSV and fits:
1. Temperature scaling (T) to minimize NLL
2. Per-intent thresholds for target precision ON CALIBRATED CONFIDENCE

IMPORTANT: Thresholds are computed on CALIBRATED confidence (after applying T),
           which matches how slm_router.py uses them at runtime.

Usage:
    python training/calibrate_from_csv.py
    python training/calibrate_from_csv.py --model "Qwen3-4B-v5" --precision 0.90

Output:
    model/router/calibration.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

# ── Paths ──
_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = _ROOT / "training" / "notebooks" / "run_02" / "outputs" / "exp6_per_sample.csv"
DEFAULT_OUTPUT_PATH = _ROOT / "model" / "router" / "calibration.json"

# ── Intent labels (must match training order) ──
INTENT_LABELS = [
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
]
INTENT_TO_IDX = {intent: i for i, intent in enumerate(INTENT_LABELS)}
N_INTENTS = len(INTENT_LABELS)


# ══════════════════════════════════════════════════════════════════════════════
# CRITICAL: This function MUST be identical to SLMRouter._apply_calibration()
# in app/agent/router/slm_router.py to ensure consistency.
# ══════════════════════════════════════════════════════════════════════════════
def apply_calibration_scalar(confidence: float, temperature: float) -> float:
    """Apply temperature scaling calibration to a single confidence value.
    
    This is the SAME logic as SLMRouter._apply_calibration() in slm_router.py.
    
    Args:
        confidence: Raw confidence from model (0-1)
        temperature: Fitted temperature T (T > 1 softens, T < 1 sharpens)
    
    Returns:
        Calibrated confidence
    """
    if abs(temperature - 1.0) < 0.001:
        return confidence  # No-op when T ≈ 1
    if confidence <= 0 or confidence >= 1:
        return confidence
    try:
        # Log-odds rescaling (same as slm_router.py)
        logit = math.log(confidence / (1 - confidence))
        scaled_logit = logit / temperature
        return 1.0 / (1.0 + math.exp(-scaled_logit))
    except (ValueError, OverflowError):
        return confidence


def softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    x = x - x.max(axis=-1, keepdims=True)
    exp_x = np.exp(x)
    return exp_x / exp_x.sum(axis=-1, keepdims=True)


def load_csv_data(csv_path: Path, model_filter: str) -> list[dict]:
    """Load predictions from CSV for specific model.
    
    Args:
        csv_path: Path to exp6_per_sample.csv
        model_filter: Model name to filter (e.g., "Qwen3-4B-v5")
    
    Returns:
        List of record dicts with gt_intent, pred_intent, confidence, correct
    """
    records = []
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["model"] != model_filter:
                continue
            
            gt_intent = row["gt_intent"]
            pred_intent = row["pred_intent"]
            
            # Parse confidence from pred_raw JSON
            try:
                pred_raw = json.loads(row["pred_raw"])
                confidence = float(pred_raw.get("confidence", 0.9))
            except (json.JSONDecodeError, TypeError, ValueError):
                confidence = 0.9
            
            # Clip confidence to valid range
            confidence = max(0.01, min(0.99, confidence))
            
            gt_idx = INTENT_TO_IDX.get(gt_intent, -1)
            pred_idx = INTENT_TO_IDX.get(pred_intent, -1)
            
            if gt_idx == -1:
                continue
            
            records.append({
                "gt_intent": gt_intent,
                "gt_idx": gt_idx,
                "pred_intent": pred_intent,
                "pred_idx": pred_idx,
                "confidence": confidence,
                "correct": gt_intent == pred_intent,
            })
    
    print(f"Loaded {len(records)} samples for model '{model_filter}'")
    return records


def build_logits(records: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Convert confidence values to approximate logits.
    
    Since we only have confidence (max prob), we approximate logits by:
    - logit_pred = log(conf / (1-conf))
    - other logits split uniformly
    
    Returns:
        logits: (N, N_INTENTS) float array
        labels: (N,) int array of ground truth intent indices
    """
    logits_list = []
    labels_list = []
    
    for rec in records:
        confidence = rec["confidence"]
        pred_idx = rec["pred_idx"]
        gt_idx = rec["gt_idx"]
        
        # Approximate logits from confidence
        logit_pred = math.log(confidence / (1 - confidence))
        other_prob = (1 - confidence) / (N_INTENTS - 1)
        logit_other = math.log(other_prob / (1 - other_prob + 1e-8))
        
        logits = np.full(N_INTENTS, logit_other)
        if pred_idx >= 0:
            logits[pred_idx] = logit_pred
        
        logits_list.append(logits)
        labels_list.append(gt_idx)
    
    return np.array(logits_list, dtype=np.float64), np.array(labels_list, dtype=np.int64)


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
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    
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
        correct_probs = calibrated_probs[np.arange(len(labels)), labels]
        correct_probs = np.clip(correct_probs, 1e-10, 1.0)
        return -np.mean(np.log(correct_probs))
    
    result = minimize_scalar(nll_loss, bounds=(0.1, 10.0), method="bounded")
    return float(result.x)


def compute_per_intent_thresholds(
    records: list[dict], 
    temperature: float,
    target_precision: float = 0.90
) -> dict[str, float]:
    """Compute per-intent confidence thresholds for target precision.
    
    IMPORTANT: Thresholds are computed on CALIBRATED confidence (after applying
    temperature scaling), which matches how slm_router.py uses them at runtime.
    
    Logic:
    1. For each prediction, compute calibrated_conf = apply_calibration(raw_conf, T)
    2. Sort predictions by calibrated_conf descending  
    3. Find minimum threshold where precision >= target
    4. Threshold is in CALIBRATED space (directly comparable at runtime)
    
    Args:
        records: List of prediction records (with raw confidence)
        temperature: Fitted temperature T for calibration
        target_precision: Desired precision (default 0.90)
    
    Returns:
        Dict mapping intent name → threshold (in CALIBRATED confidence space)
    """
    thresholds = {}
    
    # Step 1: Precompute calibrated confidence for each record
    calibrated_records = []
    for rec in records:
        # Apply calibration (same formula as slm_router.py)
        calibrated_conf = apply_calibration_scalar(rec["confidence"], temperature)
        calibrated_records.append({
            **rec,  # Keep original fields
            "raw_confidence": rec["confidence"],  # Original for debugging
            "calibrated_confidence": calibrated_conf,  # Used for threshold computation
        })
    
    # Step 2: Group by predicted intent
    by_intent: dict[str, list] = {}
    for rec in calibrated_records:
        pred = rec["pred_intent"]
        if pred not in by_intent:
            by_intent[pred] = []
        by_intent[pred].append(rec)
    
    for intent in INTENT_LABELS:
        preds = by_intent.get(intent, [])
        
        if len(preds) < 5:
            # Not enough samples — use conservative default (in calibrated space)
            thresholds[intent] = 0.65
            continue
        
        # Step 3: Sort by CALIBRATED confidence descending
        preds_sorted = sorted(preds, key=lambda x: -x["calibrated_confidence"])
        
        # Step 4: Find threshold for target precision
        # Start from highest confidence and expand until precision drops below target
        best_threshold = 0.65  # default in calibrated space
        found = False
        
        for cutoff in range(1, len(preds_sorted) + 1):
            top_k = preds_sorted[:cutoff]
            n_correct = sum(1 for p in top_k if p["correct"])
            precision = n_correct / cutoff
            
            if precision >= target_precision and cutoff >= 3:
                # This cutoff achieves target precision
                # Threshold = calibrated confidence of last sample in top_k
                best_threshold = top_k[-1]["calibrated_confidence"]
                found = True
                # Don't break — keep expanding to find largest valid set
        
        if not found:
            # Can't achieve target precision — use highest confidence as threshold
            best_threshold = preds_sorted[0]["calibrated_confidence"]
        
        # Step 5: Clamp to [min_thresh, 0.85] in calibrated space
        # Lower min for safety-critical intents (weather_alert needs high recall)
        min_thresh = 0.30 if intent == "weather_alert" else 0.45
        max_thresh = 0.85  # Leave room for T effect
        clamped = float(np.clip(best_threshold, min_thresh, max_thresh))
        
        # CRITICAL: Round DOWN to avoid rejecting samples at the threshold boundary
        # Example: threshold=0.8274 should become 0.82, not 0.83
        # Otherwise, samples with calibrated_conf=0.8274 would be rejected (0.8274 < 0.83)
        thresholds[intent] = math.floor(clamped * 100) / 100.0
    
    return thresholds


def build_reliability_diagram(
    probs: np.ndarray, 
    labels: np.ndarray, 
    n_bins: int = 15
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
                "bin_lower": round(lo, 3),
                "bin_upper": round(hi, 3),
                "avg_confidence": None,
                "accuracy": None,
                "count": 0,
            })
        else:
            diagram.append({
                "bin_lower": round(lo, 3),
                "bin_upper": round(hi, 3),
                "avg_confidence": round(float(confidences[mask].mean()), 4),
                "accuracy": round(float(accuracies[mask].mean()), 4),
                "count": count,
            })
    
    return diagram


def run_calibration(
    csv_path: Path,
    output_path: Path,
    model_filter: str,
    target_precision: float = 0.90,
) -> dict:
    """Main calibration pipeline.
    
    1. Load predictions from CSV
    2. Build approximate logits from confidence
    3. Fit temperature T (minimize NLL)
    4. Compute ECE before/after
    5. Compute per-intent thresholds
    6. Save to output_path
    
    Returns calibration result dict.
    """
    print("=" * 60)
    print("Calibrating SLM Router from exp6_per_sample.csv")
    print("=" * 60)
    print(f"CSV path: {csv_path}")
    print(f"Model filter: {model_filter}")
    print(f"Target precision: {target_precision:.0%}")
    print()
    
    # Step 1: Load data
    records = load_csv_data(csv_path, model_filter)
    if not records:
        print(f"ERROR: No records found for model '{model_filter}'")
        return {}
    
    # Step 2: Build logits
    logits, labels = build_logits(records)
    
    # Step 3: ECE before calibration
    probs_before = softmax(logits)
    ece_before = compute_ece(probs_before, labels)
    intent_acc = sum(1 for r in records if r["correct"]) / len(records)
    print(f"Before calibration: ECE={ece_before:.4f}, Intent Accuracy={intent_acc:.4f}")
    
    # Step 4: Fit temperature
    T = fit_temperature(logits, labels)
    print(f"Fitted temperature: T = {T:.4f}")
    
    # Step 5: ECE after calibration
    probs_after = softmax(logits / T)
    ece_after = compute_ece(probs_after, labels)
    print(f"After calibration:  ECE={ece_after:.4f}")
    
    if ece_before > 0:
        improvement = (ece_before - ece_after) / ece_before * 100
        print(f"ECE improvement: {ece_before:.4f} → {ece_after:.4f} ({improvement:.1f}% reduction)")
    
    # Step 6: Per-intent thresholds (COMPUTED ON CALIBRATED CONFIDENCE!)
    print(f"\n🔧 Computing per-intent thresholds on CALIBRATED confidence (T={T:.4f})...")
    per_intent_thresholds = compute_per_intent_thresholds(records, T, target_precision)
    print(f"\nPer-intent thresholds (target precision >= {target_precision:.0%}):")
    print("  (These thresholds are in CALIBRATED confidence space)")
    for intent in INTENT_LABELS:
        thresh = per_intent_thresholds.get(intent, 0.65)
        print(f"  {intent:<25}: {thresh}")
    
    # Step 7: Reliability diagram data
    reliability_before = build_reliability_diagram(probs_before, labels)
    reliability_after = build_reliability_diagram(probs_after, labels)
    
    # Step 8: Build result
    result = {
        "temperature": round(T, 4),
        "note": f"Calibrated from exp6_per_sample.csv ({len(records)} samples, model={model_filter}). "
                f"IMPORTANT: per_intent_thresholds are in CALIBRATED confidence space (after applying T={T:.4f}).",
        "model": "hanoi-router-qwen3-4b-v6",
        "fitted_on": str(csv_path.name),
        "val_size": len(records),
        "val_intent_accuracy": round(intent_acc, 4),
        "val_ece_before": round(ece_before, 4),
        "val_ece_after": round(ece_after, 4),
        "target_precision": target_precision,
        "threshold_space": "calibrated",  # IMPORTANT: thresholds are in calibrated space
        "per_intent_thresholds": per_intent_thresholds,
        "reliability_diagram_before": reliability_before,
        "reliability_diagram_after": reliability_after,
    }
    
    # Step 9: Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"✅ Calibration saved to: {output_path}")
    print(f"   Temperature: {T:.4f}")
    print(f"   ECE: {ece_before:.4f} → {ece_after:.4f}")
    print(f"\n   The router will auto-load this file on startup.")
    print(f"   (Optional) Set SLM_CALIBRATION_TEMPERATURE={T:.4f} in .env")
    print("=" * 60)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate SLM Router from evaluation CSV"
    )
    parser.add_argument(
        "--csv", 
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to exp6_per_sample.csv"
    )
    parser.add_argument(
        "--output", 
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output calibration JSON file"
    )
    parser.add_argument(
        "--model", 
        default="Qwen3-4B-v5",
        help="Model name to filter in CSV (default: Qwen3-4B-v5 for v6 model)"
    )
    parser.add_argument(
        "--precision", 
        type=float, 
        default=0.90,
        help="Target precision for per-intent threshold computation (default: 0.90)"
    )
    args = parser.parse_args()
    
    run_calibration(
        csv_path=args.csv,
        output_path=args.output,
        model_filter=args.model,
        target_precision=args.precision,
    )


if __name__ == "__main__":
    main()
