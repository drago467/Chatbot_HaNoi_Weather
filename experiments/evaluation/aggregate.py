"""PR-D.3: Aggregate run_results + judge_results across 6 configs.

Output:
- `data/evaluation/final_metrics.json` — machine-readable per-config metrics.
- `data/evaluation/final_report.md` — human-readable report với
  per-config breakdowns + pairwise Wilcoxon test cho 5 ablation pairs.

5 ablation pairs:
- C1 vs C2: router value
- C1 vs C3: finetune vs zero-shot router value
- C1 vs C4: thinking value
- C2 vs C5: open SLM vs gpt-4o-mini
- C2 vs C6: open SLM vs gemini-flash

3 metrics tested:
- tool_acc (binary recall via INTENT_TO_TOOLS)
- faithfulness (1-5)
- relevance (1-5)

Usage:
    python -m experiments.evaluation.aggregate
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from scipy.stats import wilcoxon

from experiments.evaluation.tool_accuracy import (
    check_tool_accuracy,
    check_tool_precision,
    check_tool_recall,
)

logger = logging.getLogger(__name__)


_DEFAULT_RUN_RESULTS_DIR = Path("data/evaluation/run_results")
_DEFAULT_OUTPUT_DIR = Path("data/evaluation")
_CONFIGS = ("C1", "C2", "C3", "C4", "C5", "C6")
_ABLATION_PAIRS = [
    ("C1", "C2", "router_value"),
    ("C1", "C3", "finetune_vs_zero_shot"),
    ("C1", "C4", "thinking_value"),
    ("C2", "C5", "open_vs_gpt4o_mini"),
    ("C2", "C6", "open_vs_gemini_flash"),
]


@dataclass
class ConfigMetrics:
    """Aggregate metrics cho 1 config × 500 rows."""

    config: str
    n_rows: int
    n_success: int
    n_errors: int
    n_smalltalk_skipped_faith: int

    # Tool accuracy (binary recall + continuous precision)
    tool_acc_mean: float
    tool_precision_mean: float

    # Judge scores
    faith_mean: float
    faith_median: float
    faith_score5_count: int  # rows with faith=5
    faith_distribution: dict  # {1: n, 2: n, ...}

    rel_mean: float
    rel_median: float
    rel_score5_count: int
    rel_distribution: dict

    # Latency + cost
    avg_input_tokens: float
    avg_output_tokens: float
    avg_total_latency_ms: float
    avg_router_latency_ms: float
    avg_tool_subset_size: float


@dataclass
class WilcoxonResult:
    """Paired Wilcoxon signed-rank test cho 1 metric × 1 ablation pair."""

    pair: str  # "C1_vs_C2"
    label: str  # "router_value"
    metric: str  # "tool_acc" / "faithfulness" / "relevance"
    n_paired: int  # n rows after dropping nulls
    mean_a: float  # config A mean
    mean_b: float  # config B mean
    delta: float  # mean_a - mean_b
    statistic: float  # Wilcoxon W statistic
    p_value: float
    significant_05: bool  # p < 0.05


def load_run_rows(run_dir: Path, cfg: str) -> list[dict]:
    """Load run_results JSONL for config (latest timestamp)."""
    matches = sorted(run_dir.glob(f"{cfg.lower()}_*.jsonl"))
    matches = [m for m in matches if not m.name.endswith(".judge.jsonl")]
    if not matches:
        raise FileNotFoundError(f"No run_results JSONL found for {cfg} in {run_dir}")
    fp = matches[-1]
    with fp.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_judge_rows(run_dir: Path, cfg: str) -> list[dict]:
    """Load judge_results JSONL (.judge.jsonl) for config."""
    matches = sorted(run_dir.glob(f"{cfg.lower()}_*.judge.jsonl"))
    if not matches:
        raise FileNotFoundError(f"No judge_results JSONL found for {cfg} in {run_dir}")
    fp = matches[-1]
    with fp.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def join_run_judge(run_rows: list[dict], judge_rows: list[dict]) -> list[dict]:
    """Join run + judge rows by question_id. Drop unmatched."""
    judge_by_qid = {r["question_id"]: r for r in judge_rows}
    joined = []
    for r in run_rows:
        qid = r.get("question_id")
        if qid is None:
            continue
        j = judge_by_qid.get(qid)
        if j is None:
            continue
        joined.append({**r, **{k: v for k, v in j.items() if k.startswith("judge_")}})
    return joined


def compute_config_metrics(cfg: str, joined: list[dict]) -> ConfigMetrics:
    """Compute aggregate metrics cho 1 config từ joined run+judge rows."""
    n = len(joined)
    n_success = sum(1 for r in joined if r.get("success"))
    n_errors = n - n_success

    # Tool accuracy + precision (per row)
    tool_acc_list = []
    tool_prec_list = []
    for r in joined:
        intent = r.get("intent_gold") or "current_weather"
        scope = r.get("scope_gold") or "city"
        tools = r.get("tools_called") or []
        tool_acc_list.append(1.0 if check_tool_accuracy(intent, tools, scope) else 0.0)
        tool_prec_list.append(check_tool_precision(intent, tools, scope))

    tool_acc_mean = sum(tool_acc_list) / n if n > 0 else 0.0
    tool_prec_mean = sum(tool_prec_list) / n if n > 0 else 0.0

    # Judge scores (skip None for smalltalk faith)
    faith_scores = [r["judge_faithfulness_score"] for r in joined
                    if r.get("judge_faithfulness_score") is not None]
    rel_scores = [r["judge_relevance_score"] for r in joined
                  if r.get("judge_relevance_score") is not None]
    n_skipped_faith = n - len(faith_scores)

    def _mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    def _median(lst):
        if not lst:
            return 0.0
        s = sorted(lst)
        return s[len(s) // 2]

    return ConfigMetrics(
        config=cfg,
        n_rows=n,
        n_success=n_success,
        n_errors=n_errors,
        n_smalltalk_skipped_faith=n_skipped_faith,
        tool_acc_mean=round(tool_acc_mean, 4),
        tool_precision_mean=round(tool_prec_mean, 4),
        faith_mean=round(_mean(faith_scores), 4),
        faith_median=_median(faith_scores),
        faith_score5_count=sum(1 for s in faith_scores if s == 5),
        faith_distribution=dict(Counter(faith_scores)),
        rel_mean=round(_mean(rel_scores), 4),
        rel_median=_median(rel_scores),
        rel_score5_count=sum(1 for s in rel_scores if s == 5),
        rel_distribution=dict(Counter(rel_scores)),
        avg_input_tokens=round(sum(r.get("input_tokens", 0) for r in joined) / n, 1),
        avg_output_tokens=round(sum(r.get("output_tokens", 0) for r in joined) / n, 1),
        avg_total_latency_ms=round(sum(r.get("total_latency_ms", 0) for r in joined) / n, 1),
        avg_router_latency_ms=round(sum(r.get("router_latency_ms", 0) for r in joined) / n, 1),
        avg_tool_subset_size=round(sum(r.get("tool_subset_size", 0) for r in joined) / n, 2),
    )


def paired_metric_arrays(
    joined_a: list[dict], joined_b: list[dict], metric: str,
) -> tuple[list[float], list[float]]:
    """Build paired arrays of metric values for 2 configs (matched by question_id).

    metric ∈ {"tool_acc", "faithfulness", "relevance"}.
    Drops rows where either side is None (smalltalk faith).
    """
    by_qid_a = {r["question_id"]: r for r in joined_a}
    by_qid_b = {r["question_id"]: r for r in joined_b}
    common_qids = sorted(set(by_qid_a) & set(by_qid_b),
                         key=lambda x: (str(x), x) if isinstance(x, (int, str)) else x)

    a_vals, b_vals = [], []
    for qid in common_qids:
        ra = by_qid_a[qid]
        rb = by_qid_b[qid]
        if metric == "tool_acc":
            intent_a = ra.get("intent_gold") or "current_weather"
            scope_a = ra.get("scope_gold") or "city"
            intent_b = rb.get("intent_gold") or "current_weather"
            scope_b = rb.get("scope_gold") or "city"
            va = 1.0 if check_tool_accuracy(intent_a, ra.get("tools_called") or [], scope_a) else 0.0
            vb = 1.0 if check_tool_accuracy(intent_b, rb.get("tools_called") or [], scope_b) else 0.0
        elif metric == "faithfulness":
            va = ra.get("judge_faithfulness_score")
            vb = rb.get("judge_faithfulness_score")
            if va is None or vb is None:
                continue
        elif metric == "relevance":
            va = ra.get("judge_relevance_score")
            vb = rb.get("judge_relevance_score")
            if va is None or vb is None:
                continue
        else:
            raise ValueError(f"Unknown metric: {metric}")
        a_vals.append(float(va))
        b_vals.append(float(vb))
    return a_vals, b_vals


def run_wilcoxon(
    cfg_a: str, cfg_b: str, label: str,
    joined_a: list[dict], joined_b: list[dict],
) -> list[WilcoxonResult]:
    """Run 3-metric Wilcoxon comparison cho 1 ablation pair."""
    results = []
    for metric in ["tool_acc", "faithfulness", "relevance"]:
        a_vals, b_vals = paired_metric_arrays(joined_a, joined_b, metric)
        if not a_vals or len(a_vals) < 5:
            logger.warning("Skipping %s/%s vs %s: insufficient paired data", metric, cfg_a, cfg_b)
            continue

        mean_a = sum(a_vals) / len(a_vals)
        mean_b = sum(b_vals) / len(b_vals)

        # Wilcoxon requires non-zero differences. If all equal, skip.
        diffs = [a - b for a, b in zip(a_vals, b_vals)]
        if all(d == 0 for d in diffs):
            stat, pval = 0.0, 1.0  # No difference detectable
        else:
            try:
                stat_obj = wilcoxon(a_vals, b_vals, zero_method="wilcox", alternative="two-sided")
                stat = float(stat_obj.statistic)
                pval = float(stat_obj.pvalue)
            except ValueError as e:
                logger.warning("Wilcoxon failed for %s %s_vs_%s: %s", metric, cfg_a, cfg_b, e)
                stat, pval = 0.0, 1.0

        results.append(WilcoxonResult(
            pair=f"{cfg_a}_vs_{cfg_b}",
            label=label,
            metric=metric,
            n_paired=len(a_vals),
            mean_a=round(mean_a, 4),
            mean_b=round(mean_b, 4),
            delta=round(mean_a - mean_b, 4),
            statistic=round(stat, 4),
            p_value=round(pval, 6),
            significant_05=pval < 0.05,
        ))
    return results


def render_markdown_report(
    metrics: dict[str, ConfigMetrics],
    wilcoxon_results: list[WilcoxonResult],
) -> str:
    """Build human-readable MD report."""
    lines = [
        "# Phase 2 Ablation Eval — Baseline Report v2",
        "",
        "**Dataset:** 500 single-turn questions, 6 configs, 3000 total rows.",
        "**Judge:** GPT-4o (sv1 gateway), temperature 0.0.",
        "",
        "## 1. Per-config Metrics",
        "",
        "| Cfg | Success | tool_acc | tool_prec | faith_mean | faith=5 | rel_mean | rel=5 | avg_lat (s) | avg_in_tok | avg_subset |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cfg in _CONFIGS:
        m = metrics.get(cfg)
        if m is None:
            continue
        lines.append(
            f"| {cfg} | {m.n_success}/{m.n_rows} | {m.tool_acc_mean:.3f} | "
            f"{m.tool_precision_mean:.3f} | {m.faith_mean:.3f} | "
            f"{m.faith_score5_count}/{m.n_rows - m.n_smalltalk_skipped_faith} | "
            f"{m.rel_mean:.3f} | {m.rel_score5_count}/{m.n_rows} | "
            f"{m.avg_total_latency_ms / 1000:.1f} | {m.avg_input_tokens:,.0f} | {m.avg_tool_subset_size:.1f} |"
        )

    lines.extend([
        "",
        "## 2. Faithfulness Distribution",
        "",
        "| Cfg | score=1 | score=2 | score=3 | score=4 | score=5 | skipped (smalltalk) |",
        "|---|---|---|---|---|---|---|",
    ])
    for cfg in _CONFIGS:
        m = metrics.get(cfg)
        if m is None:
            continue
        d = m.faith_distribution
        lines.append(
            f"| {cfg} | {d.get(1, 0)} | {d.get(2, 0)} | {d.get(3, 0)} | "
            f"{d.get(4, 0)} | {d.get(5, 0)} | {m.n_smalltalk_skipped_faith} |"
        )

    lines.extend([
        "",
        "## 3. Relevance Distribution",
        "",
        "| Cfg | score=1 | score=2 | score=3 | score=4 | score=5 |",
        "|---|---|---|---|---|---|",
    ])
    for cfg in _CONFIGS:
        m = metrics.get(cfg)
        if m is None:
            continue
        d = m.rel_distribution
        lines.append(
            f"| {cfg} | {d.get(1, 0)} | {d.get(2, 0)} | {d.get(3, 0)} | "
            f"{d.get(4, 0)} | {d.get(5, 0)} |"
        )

    lines.extend([
        "",
        "## 4. Pairwise Wilcoxon Signed-Rank Test (5 ablation pairs × 3 metrics)",
        "",
        "Two-sided test, paired by question_id. Significant level α=0.05.",
        "",
        "| Pair (label) | Metric | n_paired | mean_A | mean_B | Δ (A-B) | W stat | p-value | sig? |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for w in wilcoxon_results:
        sig = "✓" if w.significant_05 else "—"
        lines.append(
            f"| {w.pair} ({w.label}) | {w.metric} | {w.n_paired} | "
            f"{w.mean_a:.3f} | {w.mean_b:.3f} | {w.delta:+.3f} | "
            f"{w.statistic:.0f} | {w.p_value:.4g} | {sig} |"
        )

    lines.extend([
        "",
        "## 5. Ablation Findings Summary",
        "",
        "_Interpret each pair: A is the baseline/treatment, B is the comparison._",
        "",
    ])
    by_pair: dict[str, list[WilcoxonResult]] = {}
    for w in wilcoxon_results:
        by_pair.setdefault(w.pair, []).append(w)
    for pair, results_for_pair in by_pair.items():
        label = results_for_pair[0].label if results_for_pair else "?"
        lines.append(f"### {pair} — {label}")
        lines.append("")
        for w in results_for_pair:
            sign = "↑" if w.delta > 0 else ("↓" if w.delta < 0 else "=")
            sig = " (significant)" if w.significant_05 else " (not significant)"
            lines.append(
                f"- **{w.metric}**: A={w.mean_a:.3f}, B={w.mean_b:.3f}, Δ={w.delta:+.3f} "
                f"{sign} | p={w.p_value:.4g}{sig}"
            )
        lines.append("")

    return "\n".join(lines)


def aggregate(
    run_dir: Path = _DEFAULT_RUN_RESULTS_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Main entrypoint: load all 6 configs, compute metrics + Wilcoxon, write outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics: dict[str, ConfigMetrics] = {}
    joined_per_cfg: dict[str, list[dict]] = {}

    for cfg in _CONFIGS:
        run_rows = load_run_rows(run_dir, cfg)
        judge_rows = load_judge_rows(run_dir, cfg)
        joined = join_run_judge(run_rows, judge_rows)
        joined_per_cfg[cfg] = joined
        metrics[cfg] = compute_config_metrics(cfg, joined)
        print(f"{cfg}: loaded {len(joined)} joined rows")

    wilcoxon_results = []
    for cfg_a, cfg_b, label in _ABLATION_PAIRS:
        wilcoxon_results.extend(run_wilcoxon(
            cfg_a, cfg_b, label, joined_per_cfg[cfg_a], joined_per_cfg[cfg_b],
        ))

    # Write JSON
    json_path = output_dir / "final_metrics.json"
    payload = {
        "configs": {cfg: asdict(m) for cfg, m in metrics.items()},
        "ablation_pairs": [
            {"a": a, "b": b, "label": lbl} for a, b, lbl in _ABLATION_PAIRS
        ],
        "wilcoxon_results": [asdict(w) for w in wilcoxon_results],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {json_path}")

    # Write Markdown
    md_path = output_dir / "final_report.md"
    md = render_markdown_report(metrics, wilcoxon_results)
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote {md_path}")

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Aggregate 6-config eval metrics + Wilcoxon")
    parser.add_argument("--run-dir", default=str(_DEFAULT_RUN_RESULTS_DIR))
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    aggregate(run_dir=Path(args.run_dir), output_dir=Path(args.output_dir))


if __name__ == "__main__":
    main()
