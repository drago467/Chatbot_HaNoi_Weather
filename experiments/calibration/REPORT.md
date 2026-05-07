# Phase 10 — Router v7.1 Calibration Analysis

## Context

Router v7.1 deploy (Qwen3-4B GGUF Q4_K_M) đạt **89.6% routing accuracy** trên val 385 samples. Thresholds production hiện tại (`PER_INTENT_THRESHOLDS` 0.73-0.85) được tune trên v6 (model hardcode confidence=0.9 — meaningless signal). v7.1 dùng **5-tier confidence scheme** (0.62/0.74/0.80/0.85/0.92) có semantic ý nghĩa → thresholds cần tune lại.

**Mục tiêu Phase 10**: phân tích Expected Calibration Error (ECE), per-intent F1 vs threshold curve, và đề xuất chiến lược threshold mới giảm fallback rate mà không mất routing accuracy.

## Data

- Eval CSV: `training/notebooks/run_03/outputs_02/exp6_per_sample.csv`
- 385 samples (val v7.1 stratified split)
- Cols: `pred_intent`, `pred_conf`, `gt_intent`, `route_ok`

## Key Findings

### 1. Reliability per tier — moderate miscalibration

| Tier | Predicted conf | n | Empirical acc | Gap | Diagnosis |
|---|---|---|---|---|---|
| T5 | 0.62 | 33 | 0.879 | +0.259 | **Underconfident** — model says "uncertain" nhưng đúng 88% |
| T4 | 0.74 | 100 | 0.860 | +0.120 | **Underconfident** by 12pp |
| T3 | 0.80 | 82 | 0.854 | +0.054 | Close — gap 5pp |
| T2 | 0.85 | 73 | 0.932 | -0.082 | Slight overconfident — actually đúng 93% |
| T1 | 0.92 | 97 | 0.949 | -0.029 | **Well calibrated** |

**Overall ECE = 0.0874** (≈9% — moderate miscalibration). Phần lớn lỗi calibration đến từ T5 (model nói 0.62 khi thật ra 0.88) và T4 (0.74 thật ra 0.86).

### 2. Tier 0.62 (T5) — semantic clean

Composition của 33 sample T5:
- `smalltalk_weather`: 29 (88%) — đúng tier semantic (smalltalk/POI/OOD)
- `location_comparison`: 2 (6%, both correct)
- `expert_weather_param`: 2 (6%, both correct)

→ **T5 đúng là tier "smalltalk floor"** như thiết kế. Model rất hiếm khi assign T5 cho intent khác smalltalk (4/33 = 12% ngoại lệ, đều đúng).

### 3. Threshold strategy comparison

Simulate 5 chiến lược trên val 385:

| Strategy | Fast path | Fallback | Acc on fast path |
|---|---|---|---|
| **Current (0.73-0.85 per-intent)** | 56.6% | 43.4% | 93.1% |
| Uniform 0.62 (accept all) | 100.0% | 0.0% | 89.6% |
| **Uniform 0.74 (reject T5 only)** | **91.4%** | **8.6%** | **89.8%** |
| Uniform 0.80 (reject T4+T5) | 65.5% | 34.5% | 91.3% |
| Uniform 0.85 (reject T3+T4+T5) | 44.2% | 55.8% | 94.1% |

**Current thresholds reject 43.4% of samples → fallback** — too conservative, lãng phí compute. Phần lớn rejected samples là **T2 (0.85) đúng 93% và T3 (0.80) đúng 85%** vốn nên đi fast path.

### 4. Per-intent F1 sweep

14/15 intents có best-F1 threshold ≤ 0.74 (xem `outputs/threshold_recommendations.json`). Chỉ `weather_alert` đã ở 0.73 (gần 0.74) là OK.

Đặc biệt `smalltalk_weather`: F1@τ=0.85 = 0.20 (rejected most) vs F1@τ=0.50 = 0.89 — current threshold gây miss-route nghiêm trọng.

## Recommendation

### Adopt: uniform threshold τ=0.74 cho tất cả intents

**Lý do**:
1. **Aligned with 5-tier semantic**: τ=0.74 là biên T4 — reject chỉ T5 (smalltalk/POI/OOD), accept T4-T1 (model decided với mọi mức confidence ý nghĩa).
2. **+34.8pp fast path rate** (56.6% → 91.4%) — giảm latency đáng kể, đặc biệt với SLM router on Colab (fallback path = full agent ~5s extra).
3. **Acc on fast path: 89.8% vs current 93.1%** — drop nhẹ 3.3pp nhưng tổng thể overall accuracy không đổi vì rejected samples vẫn đúng qua fallback agent.
4. **Đơn giản hóa config**: thay 15 per-intent thresholds bằng 1 global → giảm cognitive load cho future tuning.
5. **T5 fallback bảo toàn safety**: 33 sample smalltalk T5 vẫn fallback → general agent xử lý phù hợp (chitchat, OOD).

### Alternative (not adopted): τ=0.62 fully open

Routes 100% via fast path nhưng smalltalk T5 (n=29, acc=86%) bị fast-path-route → focused agent có thể không xử lý tốt OOD/chitchat. Mặc dù acc 86% nhưng safety net (general agent) bị bypass — risky. Defer.

### Code change

`app/agent/router/config.py`:

```python
# Trước (15 per-intent thresholds 0.73-0.85)
PER_INTENT_THRESHOLDS: dict[str, float] = {...}

# Sau (uniform 0.74)
PER_INTENT_THRESHOLDS: dict[str, float] = {intent: 0.74 for intent in VALID_INTENTS}
```

## Outputs

- [ece_summary.json](outputs/ece_summary.json) — ECE + 5-tier acc/gap
- [threshold_recommendations.json](outputs/threshold_recommendations.json) — per-intent best F1
- [per_intent_sweep.json](outputs/per_intent_sweep.json) — full F1 vs τ curves
- [reliability_diagram.png](outputs/reliability_diagram.png) — calibration plot
- [confidence_histograms.png](outputs/confidence_histograms.png) — pred_conf per intent
- [threshold_f1_curves.png](outputs/threshold_f1_curves.png) — F1 vs τ per intent

## Caveats

- Val 385 samples — moderate sample size. 95% CI on 89.6% acc ≈ ±3pp.
- Per-intent n_gt range 20-36 → individual intent F1 estimates noisy.
- Eval doesn't measure user-perceived quality of fallback path (assumed equal).
- Threshold change effect on production needs A/B test for definitive comparison.

## Reproduction

```bash
python experiments/calibration/analyze_router_calibration.py
```

Outputs ghi vào `experiments/calibration/outputs/`.
