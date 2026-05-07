"""Experiment 3 — End-to-End Quality Comparison (RQ4).

So sánh 4 cấu hình hệ thống về chất lượng end-to-end trên 171 câu hỏi đơn lượt:

  E1. Full SLM      — Qwen3-4B FT router (Ollama) + Qwen3-8B agent     [REUSE verify_v2]
  E2. SLM+GPT-mini  — Qwen3-4B FT router (Ollama) + GPT-4o-mini agent  [NEW: mode=routed]
  E3. GPT-mini Base — Không router (27 tools)     + GPT-4o-mini agent  [NEW: mode=baseline]
  E4. GPT-4o Upper  — Không router (27 tools)     + GPT-4o agent       [NEW: mode=baseline]

Trục so sánh (mỗi cặp isolate 1 biến):
  E1 vs E2 — cùng SLM router, khác agent → giá trị Qwen3-8B vs GPT-4o-mini
  E2 vs E3 — cùng GPT-4o-mini agent, có/không router → giá trị SLM routing
  E3 vs E4 — cùng no-router, khác agent → GPT-4o-mini vs GPT-4o (upper bound gap)
  E1 vs E4 — full SLM vs best-effort LLM → core thesis claim

Methodology:
  - FrugalGPT (Chen et al., 2023): cost-quality tradeoff across system configs
  - Hybrid LLM (Ding et al., ICLR 2024): router × agent dimension
  - G-Eval (Liu et al., NeurIPS 2023): LLM-as-Judge (5 dimensions, 1-5 scale)
  - McNemar test: paired binary comparison (tool_correct per question)
  - Wilcoxon signed-rank: paired ordinal comparison (judge scores per question)

Lý do subprocess thay vì direct import:
  agent.py dùng global singleton _model (line 459). Direct import reuse instance
  cũ giữa E2→E3→E4, làm sai agent model. Subprocess → fresh process → safe init.

Usage:
  # Run E2 + E3 + E4 + compile:
  python experiments/exp3_e2e.py

  # Run specific configs only:
  python experiments/exp3_e2e.py --configs E2 E3

  # Skip run, just compile comparison (all 4 results already exist):
  python experiments/exp3_e2e.py --compare-only

  # Dry-run (3 questions) to verify pipeline:
  python experiments/exp3_e2e.py --dry-run
  python experiments/exp3_e2e.py --dry-run --configs E2
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# ── Project root ──
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ──
EVAL_QUESTIONS_SRC = ROOT / "data" / "evaluation" / "hanoi_weather_chatbot_eval_questions.csv"
E1_SUMMARY  = ROOT / "data" / "evaluation" / "thesis_final" / "exp3" / "e1_full_slm" / "routed" / "evaluation_summary.json"
E1_RESULTS  = ROOT / "data" / "evaluation" / "thesis_final" / "exp3" / "e1_full_slm" / "routed" / "evaluation_results.csv"
OUTPUT_DIR  = ROOT / "data" / "evaluation" / "thesis_final" / "exp3"

# ── Config definitions ──
# Sub-dir name → (evaluation runner --mode, AGENT env overrides)
CONFIGS: dict[str, dict] = {
    "E1": {
        "label": "E1. Full SLM (Qwen3-4B FT router + Qwen3-8B agent)",
        "subdir": "e1_full_slm",
        "mode": "routed",
        "agent_model":    os.getenv("AGENT_MODEL", "qwen3-8b"),
        "agent_api_base": os.getenv("AGENT_API_BASE"),
        "agent_api_key":  os.getenv("AGENT_API_KEY"),
        "cost_per_1k": 1.0,
        "description": "SLM router (local Ollama) + Qwen3-8B agent — proposed system",
    },
    "E2": {
        "label": "E2. SLM+GPT-mini (Qwen3-4B router + GPT-4o-mini agent)",
        "subdir": "e2_slm_gpt4mini",
        "mode": "routed",
        "agent_model":    "gpt-4o-mini-2024-07-18",  # pinned — independent of JUDGE_MODEL
        "agent_api_base": os.getenv("JUDGE_API_BASE"),
        "agent_api_key":  os.getenv("JUDGE_API_KEY"),
        "cost_per_1k": 3.0,   # USD estimate
        "description": "SLM router (local) + GPT-4o-mini agent",
    },
    "E3": {
        "label": "E3. GPT-mini Baseline (no router + GPT-4o-mini agent)",
        "subdir": "e3_gpt4mini_baseline",
        "mode": "baseline",
        "agent_model":    "gpt-4o-mini-2024-07-18",  # pinned — independent of JUDGE_MODEL
        "agent_api_base": os.getenv("JUDGE_API_BASE"),
        "agent_api_key":  os.getenv("JUDGE_API_KEY"),
        "cost_per_1k": 3.0,
        "description": "No router, GPT-4o-mini agent (27 tools)",
    },
    "E4": {
        "label": "E4. GPT-4o Upper Bound (no router + GPT-4o agent)",
        "subdir": "e4_gpt4o_baseline",
        "mode": "baseline",
        "agent_model":    os.getenv("GPT_4o_MODEL", "gpt-4o"),
        "agent_api_base": os.getenv("GPT_4o_API_BASE"),
        "agent_api_key":  os.getenv("GPT_4o_API_KEY"),
        "cost_per_1k": 15.0,
        "description": "No router, GPT-4o agent (27 tools) — upper bound",
    },
}

E1_META = {
    "label": "E1. Full SLM (Qwen3-4B FT router + Qwen3-8B agent)",
    "subdir": "e1_full_slm",
    "mode": "routed",
    "agent_model":    os.getenv("AGENT_MODEL", "qwen3-8b"),
    "agent_api_base": os.getenv("AGENT_API_BASE"),
    "agent_api_key":  None,   # key not logged
    "cost_per_1k": 1.0,
    "description": "SLM router (local Ollama) + Qwen3-8B agent — proposed system",
}

VALID_CONFIGS = list(CONFIGS.keys())


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _json_default(obj: Any) -> Any:
    """Convert numpy types for json.dump."""
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


from experiments.shared.stats import wilson_ci, mcnemar_test, wilcoxon_test


def load_csv_results(csv_path: Path) -> list[dict]:
    """Load evaluation_results.csv into list of dicts."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {csv_path}")
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_summary(json_path: Path) -> dict:
    """Load evaluation_summary.json."""
    if not json_path.exists():
        raise FileNotFoundError(f"Summary JSON not found: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════
# Config runner — subprocess per config
# ═══════════════════════════════════════════════════════════════════

NEW_QUESTIONS_OFFSET = 171  # Q172-199 are the 28 new questions

def run_config(config_id: str, cfg: dict, output_base: Path,
               dry_run: bool = False, new_only: bool = False) -> Path:
    """Run evaluation module for one config via subprocess. Returns results dir.

    Args:
        new_only: If True, run only the 28 new questions (offset=171).
                  Output goes to {subdir}_28new/ to avoid overwriting original results.
    """
    subdir_name = cfg["subdir"] + ("_28new" if new_only else "")
    subdir = output_base / subdir_name
    subdir.mkdir(parents=True, exist_ok=True)

    # evaluation module expects hanoi_weather_chatbot_eval_questions.csv in output_dir
    dest_csv = subdir / "hanoi_weather_chatbot_eval_questions.csv"
    if dry_run:
        # Dry-run: create 3-row subset. For new_only, use rows 171-173 (first 3 new questions)
        with open(EVAL_QUESTIONS_SRC, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        start = NEW_QUESTIONS_OFFSET if new_only else 0
        sample_rows = rows[start:start + 3]
        with open(dest_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(sample_rows)
        logger.info("[%s] Dry-run: created 3-row CSV (rows %d-%d) at %s",
                    config_id, start + 1, start + 3, dest_csv)
    else:
        shutil.copy2(EVAL_QUESTIONS_SRC, dest_csv)

    # Build env for subprocess
    env = os.environ.copy()
    env["AGENT_MODEL"]    = cfg["agent_model"]
    env["AGENT_API_BASE"] = cfg["agent_api_base"] or ""
    env["AGENT_API_KEY"]  = cfg["agent_api_key"] or ""
    # Keep USE_SLM_ROUTER from .env for routed mode; force off for baseline
    if cfg["mode"] == "baseline":
        env["USE_SLM_ROUTER"] = "false"
    else:
        env["USE_SLM_ROUTER"] = "true"

    # evaluate module writes to {output_dir}/{mode}/
    cmd = [
        sys.executable,
        "-m", "experiments.evaluation",
        "--mode", cfg["mode"],
        "--output", str(subdir),
    ]
    if new_only and not dry_run:
        cmd += ["--offset", str(NEW_QUESTIONS_OFFSET)]

    logger.info("[%s] Starting subprocess: mode=%s, agent=%s", config_id, cfg["mode"], cfg["agent_model"])
    logger.info("[%s] Command: %s", config_id, " ".join(cmd))
    t0 = time.perf_counter()

    result = subprocess.run(cmd, env=env, cwd=str(ROOT), capture_output=False)

    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        raise RuntimeError(f"[{config_id}] experiments.evaluation exited with code {result.returncode}")

    logger.info("[%s] Done in %.1fs", config_id, elapsed)

    # Results written to subdir/{mode}/
    results_dir = subdir / cfg["mode"]
    if not (results_dir / "evaluation_summary.json").exists():
        raise RuntimeError(f"[{config_id}] Expected summary not found at {results_dir}")

    return results_dir


# ═══════════════════════════════════════════════════════════════════
# Compile comparison from all 4 result sets
# ═══════════════════════════════════════════════════════════════════

JUDGE_DIMS = ["judge_relevance", "judge_completeness", "judge_fluency",
              "judge_actionability", "judge_faithfulness"]


def _get_tool_correct(row: dict) -> bool:
    """Parse tool_correct column (handles True/False/1/0/'True'/'False')."""
    val = row.get("tool_correct", "")
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "1.0")


def _get_judge_score(row: dict, dim: str) -> float | None:
    val = row.get(dim)
    if val is None or str(val).strip() in ("", "None", "nan"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def compile_comparison(
    configs_run: list[str],
    output_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Load results for all configs, compute stats, write output files."""

    # ── Load E1 (always reuse verify_v2) ──
    logger.info("Loading E1 from verify_v2/routed/")
    e1_summary = load_summary(E1_SUMMARY)
    e1_rows    = load_csv_results(E1_RESULTS)

    all_data: dict[str, dict] = {}
    all_data["E1"] = {
        "meta": E1_META,
        "summary": e1_summary,
        "rows": e1_rows,
    }

    # ── Load E2/E3/E4 ──
    for config_id in configs_run:
        cfg = CONFIGS[config_id]
        results_dir = output_dir / cfg["subdir"] / cfg["mode"]
        logger.info("Loading %s from %s", config_id, results_dir)
        summary = load_summary(results_dir / "evaluation_summary.json")
        rows    = load_csv_results(results_dir / "evaluation_results.csv")
        all_data[config_id] = {"meta": cfg, "summary": summary, "rows": rows}

    # ── Align rows by question index (same CSV, same order) ──
    # E1 may have 171 rows; dry-run configs have 3 rows — use min length for paired tests
    n_e1   = len(all_data["E1"]["rows"])
    n_min  = min(len(d["rows"]) for d in all_data.values())
    if dry_run:
        logger.info("Dry-run: aligning to %d rows (E1 has %d)", n_min, n_e1)
        # Slice E1 rows to match dry-run length for pairing
        all_data["E1"]["rows_paired"] = all_data["E1"]["rows"][:n_min]
    else:
        all_data["E1"]["rows_paired"] = all_data["E1"]["rows"]

    for config_id in configs_run:
        all_data[config_id]["rows_paired"] = all_data[config_id]["rows"]

    # ── McNemar tests (paired binary — tool_correct) ──
    def get_correct_list(config_id: str) -> list[bool]:
        rows = all_data[config_id]["rows_paired"]
        return [_get_tool_correct(r) for r in rows]

    e1_correct = get_correct_list("E1")
    mcnemar: dict[str, dict] = {}

    pairs_for_mcnemar = [
        ("E1", "E2"), ("E1", "E3"), ("E1", "E4"),
        ("E2", "E3"), ("E3", "E4"),
    ]
    for a, b in pairs_for_mcnemar:
        if a not in all_data or b not in all_data:
            continue
        pair_key = f"{a} vs {b}"
        try:
            ca = get_correct_list(a)
            cb = get_correct_list(b)
            # Align lengths
            n = min(len(ca), len(cb))
            mcnemar[pair_key] = mcnemar_test(ca[:n], cb[:n])
        except Exception as exc:
            logger.warning("McNemar %s failed: %s", pair_key, exc)
            mcnemar[pair_key] = {"error": str(exc)}

    # ── Wilcoxon tests (paired ordinal — judge scores, E1 vs E4 primary) ──
    wilcoxon_results: dict[str, dict] = {}
    pairs_for_wilcoxon = [("E1", "E4"), ("E1", "E3"), ("E2", "E3")]
    for a, b in pairs_for_wilcoxon:
        if a not in all_data or b not in all_data:
            continue
        pair_key = f"{a} vs {b}"
        wilcoxon_results[pair_key] = {}
        rows_a = all_data[a]["rows_paired"]
        rows_b = all_data[b]["rows_paired"]
        n = min(len(rows_a), len(rows_b))
        for dim in JUDGE_DIMS:
            dim_short = dim.replace("judge_", "")
            scores_a = [_get_judge_score(r, dim) for r in rows_a[:n]]
            scores_b = [_get_judge_score(r, dim) for r in rows_b[:n]]
            try:
                wilcoxon_results[pair_key][dim_short] = wilcoxon_test(scores_a, scores_b, dim)
            except Exception as exc:
                logger.warning("Wilcoxon %s %s failed: %s", pair_key, dim, exc)
                wilcoxon_results[pair_key][dim_short] = {"error": str(exc)}

    # ── Build per-config summary rows ──
    config_order = ["E1"] + [c for c in ["E2", "E3", "E4"] if c in all_data]
    summary_rows = []
    for config_id in config_order:
        d = all_data[config_id]
        s = d["summary"]
        meta = d["meta"]
        row = {
            "config_id": config_id,
            "config": meta["label"],
            "mode": meta["mode"],
            "agent_model": meta["agent_model"],
            "description": meta["description"],
            "cost_per_1k_usd": meta["cost_per_1k"],
            "total_questions": s.get("total", 0),
            "tool_accuracy_pct": s.get("tool_accuracy", 0),
            "tool_accuracy_ci95": s.get("tool_accuracy_ci95", [None, None]),
            "p50_ms": s.get("p50_time_ms", 0),
            "p90_ms": s.get("p90_time_ms", 0),
            "p95_ms": s.get("p95_time_ms", 0),
            "avg_ms": s.get("avg_time_ms", 0),
            "router_coverage_pct": s.get("router_coverage"),
            "router_fallback_pct": s.get("router_fallback_rate"),
            "router_intent_acc_pct": s.get("router_intent_accuracy"),
        }
        for dim in JUDGE_DIMS:
            row[dim + "_avg"] = s.get(dim + "_avg")
        summary_rows.append(row)

    # ── Full summary dict ──
    import datetime
    full_summary = {
        "experiment": "Exp3_E2E_Comparison",
        "rq": "RQ4: SLM-first system quality vs LLM-only baselines",
        "methodology": ["FrugalGPT (Chen et al. 2023)", "Hybrid LLM (Ding et al. ICLR 2024)",
                        "G-Eval (Liu et al. NeurIPS 2023)"],
        "dataset": "hanoi_weather_chatbot_eval_questions.csv",
        "n_questions": n_min if dry_run else 171,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "configs": summary_rows,
        "mcnemar_tests": mcnemar,
        "wilcoxon_tests": wilcoxon_results,
        "e1_source": str(E1_SUMMARY),
        "notes": {
            "E1": "Re-run with gpt-4o judge (exp3/e1_full_slm/routed/), consistent judge across all configs",
            "E2": "SLM router (Ollama, local) + GPT-4o-mini agent via JUDGE_API",
            "E3": "No router, GPT-4o-mini agent, 27 tools available",
            "E4": "No router, GPT-4o agent, 27 tools available — upper bound",
        },
    }

    # ── Save exp3_summary.json ──
    summary_path = output_dir / "exp3_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(full_summary, f, indent=2, ensure_ascii=False, default=_json_default)
    logger.info("Saved summary → %s", summary_path)

    # ── Save exp3_comparison_table.txt ──
    table_path = output_dir / "exp3_comparison_table.txt"
    _write_comparison_table(table_path, summary_rows, mcnemar, wilcoxon_results, n_min if dry_run else 171)
    logger.info("Saved table → %s", table_path)

    return full_summary


def _write_comparison_table(
    path: Path,
    rows: list[dict],
    mcnemar: dict,
    wilcoxon_results: dict,
    n: int,
) -> None:
    """Write human-readable comparison table."""
    SEP = "=" * 110
    sep = "-" * 110
    lines = [
        SEP,
        "Experiment 3: End-to-End Quality Comparison (RQ4)",
        f"Dataset: {n} single-turn evaluation questions",
        SEP,
        "",
    ]

    # Header
    lines.append(f"{'Config':<40} {'Tool Acc':>9} {'95% CI':>15} {'Rel':>5} {'Cmp':>5} {'Flu':>5} {'Act':>5} {'Fai':>5} {'P50 (ms)':>10} {'Cost/1K':>9}")
    lines.append(sep)

    for r in rows:
        ci = r["tool_accuracy_ci95"] or ["-", "-"]
        ci_str = f"[{ci[0]}, {ci[1]}]" if ci[0] != "-" else "[-]"

        def fmt_judge(key: str) -> str:
            val = r.get(key + "_avg")
            return f"{val:.2f}" if val is not None else "  -  "

        lines.append(
            f"{r['config'][:40]:<40} "
            f"{r['tool_accuracy_pct']:>8.1f}% "
            f"{ci_str:>15} "
            f"{fmt_judge('judge_relevance'):>5} "
            f"{fmt_judge('judge_completeness'):>5} "
            f"{fmt_judge('judge_fluency'):>5} "
            f"{fmt_judge('judge_actionability'):>5} "
            f"{fmt_judge('judge_faithfulness'):>5} "
            f"{r['p50_ms']:>10,} "
            f"${r['cost_per_1k_usd']:>7.1f}"
        )

    lines += ["", ""]

    # McNemar
    lines.append("McNemar's Test (paired binary, tool accuracy):")
    lines.append(f"{'Pair':<18} {'chi2':>8} {'p-value':>10} {'Sig':>6} {'A wins':>8} {'B wins':>8}")
    lines.append("-" * 65)
    for pair, res in mcnemar.items():
        if "error" in res or "note" in res:
            lines.append(f"{pair:<18}  {'ERROR: ' + res.get('error', res.get('note', ''))}")
            continue
        sig = "***" if res.get("significant_0.01") else ("*" if res.get("significant_0.05") else "n.s.")
        lines.append(
            f"{pair:<18} {res['chi2']:>8.3f} {res['p_value']:>10.6f} {sig:>6} "
            f"{res.get('b_a_wins', '-'):>8} {res.get('c_b_wins', '-'):>8}"
        )

    lines += ["", ""]

    # Wilcoxon
    lines.append("Wilcoxon Signed-Rank Test (paired ordinal, judge scores):")
    dim_labels = ["relevance", "completeness", "fluency", "actionability", "faithfulness"]
    for pair, dims in wilcoxon_results.items():
        lines.append(f"\n  Pair: {pair}")
        lines.append(f"  {'Dimension':<16} {'stat':>8} {'p-value':>10} {'Sig':>6} {'mean_A':>8} {'mean_B':>8} {'n':>5}")
        lines.append("  " + "-" * 65)
        for dim in dim_labels:
            res = dims.get(dim, {})
            if not res or "error" in res or "note" in res:
                lines.append(f"  {dim:<16}  {res.get('error', res.get('note', 'N/A'))}")
                continue
            sig = "***" if res.get("significant_0.01") else ("*" if res.get("significant_0.05") else "n.s.")
            lines.append(
                f"  {dim:<16} {res['statistic']:>8.3f} {res['p_value']:>10.6f} {sig:>6} "
                f"{res.get('mean_a', '-'):>8} {res.get('mean_b', '-'):>8} {res.get('n', '-'):>5}"
            )

    lines += ["", ""]

    # Router rows only
    router_rows = [r for r in rows if r.get("router_coverage_pct") is not None]
    if router_rows:
        lines.append("Router Metadata (routed configs only):")
        lines.append(f"{'Config':<10} {'Coverage':>10} {'Fallback':>10} {'Intent Acc':>12}")
        lines.append("-" * 50)
        for r in router_rows:
            lines.append(
                f"{r['config_id']:<10} "
                f"{r.get('router_coverage_pct', '-'):>9.1f}% "
                f"{r.get('router_fallback_pct', '-'):>9.1f}% "
                f"{r.get('router_intent_acc_pct', '-'):>11.1f}%"
            )

    lines += ["", SEP, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Exp 3: End-to-End Quality Comparison")
    parser.add_argument(
        "--configs", nargs="+", default=["E2", "E3", "E4"],
        choices=VALID_CONFIGS,
        help="Which configs to run (default: E2 E3 E4). E1 uses local Ollama; others use API.",
    )
    parser.add_argument(
        "--compare-only", action="store_true",
        help="Skip subprocess runs, just compile comparison from existing results.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run each config on only 3 questions to verify pipeline.",
    )
    parser.add_argument(
        "--new-only", action="store_true",
        help=(
            "Run only the 28 new questions (Q172-199, offset=171). "
            "Output goes to {subdir}_28new/ — does NOT overwrite original 171-question results. "
            "After running, use merge_exp3_results.py to combine old + new."
        ),
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Validate E1 source exists ──
    if not E1_SUMMARY.exists():
        logger.error("E1 source not found: %s", E1_SUMMARY)
        logger.error("Expected verify_v2/routed/ results from code-freeze evaluation.")
        sys.exit(1)
    if not E1_RESULTS.exists():
        logger.error("E1 results CSV not found: %s", E1_RESULTS)
        sys.exit(1)

    # ── Validate required env vars ──
    missing = []
    needs_judge_api = any(c in args.configs for c in ("E2", "E3")) and not args.compare_only
    if needs_judge_api:
        if not os.getenv("JUDGE_API_KEY"):
            missing.append("JUDGE_API_KEY (needed for E2, E3 agent)")
        if not os.getenv("JUDGE_API_BASE"):
            missing.append("JUDGE_API_BASE (needed for E2, E3 agent)")
    if "E4" in args.configs and not args.compare_only:
        if not os.getenv("GPT_4o_API_KEY"):
            missing.append("GPT_4o_API_KEY (needed for E4)")
        if not os.getenv("GPT_4o_API_BASE"):
            missing.append("GPT_4o_API_BASE (needed for E4)")
        if not os.getenv("GPT_4o_MODEL"):
            missing.append("GPT_4o_MODEL (needed for E4)")
    if missing:
        logger.error("Missing required env vars:\n  %s", "\n  ".join(missing))
        sys.exit(1)

    # ── Print plan ──
    logger.info("=" * 60)
    logger.info("Experiment 3 — End-to-End Quality Comparison")
    logger.info("E1: REUSE from %s", E1_SUMMARY.parent)
    configs_to_run = [] if args.compare_only else args.configs
    for cfg_id in configs_to_run:
        cfg = CONFIGS[cfg_id]
        label = "[DRY-RUN 3q] " if args.dry_run else ""
        logger.info("  %s%s: mode=%s, agent=%s", label, cfg_id, cfg["mode"], cfg["agent_model"])
    logger.info("Output: %s", OUTPUT_DIR)
    logger.info("=" * 60)

    # ── Run configs ──
    if not args.compare_only:
        new_only = getattr(args, "new_only", False)
        if new_only:
            logger.info("NEW-ONLY mode: running Q172-199 (offset=%d). Output → {subdir}_28new/",
                        NEW_QUESTIONS_OFFSET)
            logger.info("After running, merge with: python experiments/merge_exp3.py")
        for cfg_id in configs_to_run:
            cfg = CONFIGS[cfg_id]
            logger.info("\n>>> Running %s: %s", cfg_id, cfg["label"])
            try:
                results_dir = run_config(cfg_id, cfg, OUTPUT_DIR,
                                         dry_run=args.dry_run, new_only=new_only)
                logger.info("[%s] Results at: %s", cfg_id, results_dir)
            except Exception as exc:
                logger.error("[%s] FAILED: %s", cfg_id, exc)
                raise

    # ── Skip compilation when --new-only (results not merged yet) ──
    new_only = getattr(args, "new_only", False)
    if new_only and not args.compare_only:
        logger.info("=" * 60)
        logger.info("NEW-ONLY run complete. Next steps:")
        logger.info("  1. python experiments/merge_exp3.py")
        logger.info("  2. python experiments/exp3_e2e.py --compare-only")
        logger.info("=" * 60)
        sys.exit(0)

    # ── Determine which configs have results for compilation ──
    configs_available = []
    for cfg_id in VALID_CONFIGS:
        cfg = CONFIGS[cfg_id]
        results_dir = OUTPUT_DIR / cfg["subdir"] / cfg["mode"]
        summary_path = results_dir / "evaluation_summary.json"
        if summary_path.exists():
            configs_available.append(cfg_id)
            logger.info("[%s] Found results at %s", cfg_id, results_dir)
        else:
            logger.info("[%s] No results found, skipping compilation", cfg_id)

    if not configs_available:
        logger.warning("No E2/E3/E4 results found. Run with --configs E2 E3 E4 first.")
        sys.exit(0)

    # ── Compile comparison ──
    logger.info("\n>>> Compiling comparison across E1 + %s", configs_available)
    try:
        summary = compile_comparison(configs_available, OUTPUT_DIR, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("Compilation failed: %s", exc)
        raise

    # ── Print quick summary table ──
    print("\n" + "=" * 80)
    print("EXPERIMENT 3 — END-TO-END QUALITY COMPARISON — RESULTS")
    print("=" * 80)
    print(f"{'Config':<12} {'Tool Acc':>9} {'Relevance':>10} {'Fluency':>9} {'P50 (ms)':>10} {'Cost/1K':>9}")
    print("-" * 65)
    for row in summary["configs"]:
        rel  = row.get("judge_relevance_avg")
        flu  = row.get("judge_fluency_avg")
        print(
            f"{row['config_id']:<12} "
            f"{row['tool_accuracy_pct']:>8.1f}% "
            f"{(str(round(rel, 2)) if rel is not None else '-'):>10} "
            f"{(str(round(flu, 2)) if flu is not None else '-'):>9} "
            f"{row['p50_ms']:>10,} "
            f"${row['cost_per_1k_usd']:>7.1f}"
        )
    print("-" * 65)

    print("\nMcNemar Tests (tool accuracy):")
    for pair, res in summary["mcnemar_tests"].items():
        if "error" in res:
            print(f"  {pair}: ERROR")
            continue
        sig = " ***" if res.get("significant_0.01") else (" *" if res.get("significant_0.05") else " n.s.")
        print(f"  {pair}: chi2={res.get('chi2', '-')}, p={res.get('p_value', '-')}{sig}")

    print(f"\nResults saved to: {OUTPUT_DIR}")
    print(f"  Summary:  exp3_summary.json")
    print(f"  Table:    exp3_comparison_table.txt")


if __name__ == "__main__":
    main()
