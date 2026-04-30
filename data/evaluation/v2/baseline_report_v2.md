# Phase 2 Ablation Eval — Baseline Report v2

**Dataset:** 500 single-turn questions, 6 configs, 3000 total rows.
**Judge:** GPT-4o (sv1 gateway), temperature 0.0.

## 1. Per-config Metrics

| Cfg | Success | tool_acc | tool_prec | faith_mean | faith=5 | rel_mean | rel=5 | avg_lat (s) | avg_in_tok | avg_subset |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 494/500 | 0.926 | 0.903 | 4.149 | 307/482 | 4.622 | 390/500 | 17.6 | 28,608 | 5.1 |
| C2 | 498/500 | 0.848 | 0.837 | 4.037 | 290/482 | 4.658 | 398/500 | 19.3 | 42,370 | 27.0 |
| C3 | 487/500 | 0.894 | 0.868 | 3.961 | 283/482 | 4.584 | 385/500 | 18.9 | 28,227 | 5.0 |
| C4 | 491/500 | 0.922 | 0.897 | 4.004 | 286/482 | 4.590 | 384/500 | 18.3 | 29,044 | 5.1 |
| C5 | 500/500 | 0.882 | 0.815 | 4.237 | 334/482 | 4.686 | 400/500 | 11.0 | 36,245 | 27.0 |
| C6 | 500/500 | 0.834 | 0.792 | 4.361 | 357/482 | 4.744 | 419/500 | 11.6 | 38,280 | 27.0 |

## 2. Faithfulness Distribution

| Cfg | score=1 | score=2 | score=3 | score=4 | score=5 | skipped (smalltalk) |
|---|---|---|---|---|---|---|
| C1 | 35 | 40 | 50 | 50 | 307 | 18 |
| C2 | 31 | 58 | 63 | 40 | 290 | 18 |
| C3 | 36 | 63 | 68 | 32 | 283 | 18 |
| C4 | 39 | 54 | 59 | 44 | 286 | 18 |
| C5 | 26 | 47 | 48 | 27 | 334 | 18 |
| C6 | 16 | 43 | 49 | 17 | 357 | 18 |

## 3. Relevance Distribution

| Cfg | score=1 | score=2 | score=3 | score=4 | score=5 |
|---|---|---|---|---|---|
| C1 | 4 | 17 | 33 | 56 | 390 |
| C2 | 2 | 15 | 33 | 52 | 398 |
| C3 | 11 | 12 | 36 | 56 | 385 |
| C4 | 8 | 16 | 33 | 59 | 384 |
| C5 | 0 | 13 | 31 | 56 | 400 |
| C6 | 6 | 4 | 21 | 50 | 419 |

## 4. Pairwise Wilcoxon Signed-Rank Test (5 ablation pairs × 3 metrics)

Two-sided test, paired by question_id. Significant level α=0.05.

| Pair (label) | Metric | n_paired | mean_A | mean_B | Δ (A-B) | W stat | p-value | sig? |
|---|---|---|---|---|---|---|---|---|
| C1_vs_C2 (router_value) | tool_acc | 500 | 0.926 | 0.848 | +0.078 | 476 | 2e-06 | ✓ |
| C1_vs_C2 (router_value) | faithfulness | 482 | 4.149 | 4.037 | +0.112 | 8204 | 0.06467 | — |
| C1_vs_C2 (router_value) | relevance | 500 | 4.622 | 4.658 | -0.036 | 4185 | 0.4416 | — |
| C1_vs_C3 (finetune_vs_zero_shot) | tool_acc | 500 | 0.926 | 0.894 | +0.032 | 108 | 0.003487 | ✓ |
| C1_vs_C3 (finetune_vs_zero_shot) | faithfulness | 482 | 4.149 | 3.961 | +0.189 | 7712 | 0.002779 | ✓ |
| C1_vs_C3 (finetune_vs_zero_shot) | relevance | 500 | 4.622 | 4.584 | +0.038 | 3164 | 0.4204 | — |
| C1_vs_C4 (thinking_value) | tool_acc | 500 | 0.926 | 0.922 | +0.004 | 0 | 0.1573 | — |
| C1_vs_C4 (thinking_value) | faithfulness | 482 | 4.149 | 4.004 | +0.145 | 5036 | 0.007636 | ✓ |
| C1_vs_C4 (thinking_value) | relevance | 500 | 4.622 | 4.590 | +0.032 | 1689 | 0.3251 | — |
| C2_vs_C5 (open_vs_gpt4o_mini) | tool_acc | 500 | 0.848 | 0.882 | -0.034 | 850 | 0.03781 | ✓ |
| C2_vs_C5 (open_vs_gpt4o_mini) | faithfulness | 482 | 4.037 | 4.237 | -0.199 | 10664 | 0.006549 | ✓ |
| C2_vs_C5 (open_vs_gpt4o_mini) | relevance | 500 | 4.658 | 4.686 | -0.028 | 4921 | 0.5401 | — |
| C2_vs_C6 (open_vs_gemini_flash) | tool_acc | 500 | 0.848 | 0.834 | +0.014 | 957 | 0.3853 | — |
| C2_vs_C6 (open_vs_gemini_flash) | faithfulness | 482 | 4.037 | 4.361 | -0.324 | 7070 | 7e-06 | ✓ |
| C2_vs_C6 (open_vs_gemini_flash) | relevance | 500 | 4.658 | 4.744 | -0.086 | 3726 | 0.02754 | ✓ |

## 5. Ablation Findings Summary

_Interpret each pair: A is the baseline/treatment, B is the comparison._

### C1_vs_C2 — router_value

- **tool_acc**: A=0.926, B=0.848, Δ=+0.078 ↑ | p=2e-06 (significant)
- **faithfulness**: A=4.149, B=4.037, Δ=+0.112 ↑ | p=0.06467 (not significant)
- **relevance**: A=4.622, B=4.658, Δ=-0.036 ↓ | p=0.4416 (not significant)

### C1_vs_C3 — finetune_vs_zero_shot

- **tool_acc**: A=0.926, B=0.894, Δ=+0.032 ↑ | p=0.003487 (significant)
- **faithfulness**: A=4.149, B=3.961, Δ=+0.189 ↑ | p=0.002779 (significant)
- **relevance**: A=4.622, B=4.584, Δ=+0.038 ↑ | p=0.4204 (not significant)

### C1_vs_C4 — thinking_value

- **tool_acc**: A=0.926, B=0.922, Δ=+0.004 ↑ | p=0.1573 (not significant)
- **faithfulness**: A=4.149, B=4.004, Δ=+0.145 ↑ | p=0.007636 (significant)
- **relevance**: A=4.622, B=4.590, Δ=+0.032 ↑ | p=0.3251 (not significant)

### C2_vs_C5 — open_vs_gpt4o_mini

- **tool_acc**: A=0.848, B=0.882, Δ=-0.034 ↓ | p=0.03781 (significant)
- **faithfulness**: A=4.037, B=4.237, Δ=-0.199 ↓ | p=0.006549 (significant)
- **relevance**: A=4.658, B=4.686, Δ=-0.028 ↓ | p=0.5401 (not significant)

### C2_vs_C6 — open_vs_gemini_flash

- **tool_acc**: A=0.848, B=0.834, Δ=+0.014 ↑ | p=0.3853 (not significant)
- **faithfulness**: A=4.037, B=4.361, Δ=-0.324 ↓ | p=7e-06 (significant)
- **relevance**: A=4.658, B=4.744, Δ=-0.086 ↓ | p=0.02754 (significant)
