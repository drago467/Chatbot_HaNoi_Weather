#!/usr/bin/env python3
"""
Experiment 4: Multi-Turn Ablation (RQ2)

Measures the incremental value of each component in the multi-turn pipeline:

  MT-Base    — each turn is independent (no LangGraph history, no ConversationState)
  MT-Context — same thread across turns (LangGraph history kept), but SLM does NOT rewrite query
  MT-Full    — production: SLM rewrite + ConversationState context (LangGraph history kept)

Comparison pairs:
  MT-Base → MT-Context : value of conversation context injection
  MT-Context → MT-Full : value of SLM query rewriting  ← novel contribution
  MT-Base → MT-Full    : total improvement

All 3 configs use the same router (Qwen3-4B FT / Ollama) and agent (Qwen3-8B).
Dataset: 60 multi-turn conversations, 188 turns total.

Usage:
  python scripts/experiments/exp4_multiturn_ablation.py              # full run
  python scripts/experiments/exp4_multiturn_ablation.py --dry-run    # 3 conversations
  python scripts/experiments/exp4_multiturn_ablation.py --configs MT-Full MT-Context
  python scripts/experiments/exp4_multiturn_ablation.py --compare-only
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

# ── Output paths ──
OUTPUT_BASE = ROOT / "data/evaluation/thesis_final/exp4"
SCENARIOS   = ROOT / "data/evaluation/multi_turn_scenarios.jsonl"

# ── Config table ──
CONFIGS = [
    {
        "name":    "MT-Base",
        "mt_mode": "base",
        "subdir":  "mt_base",
        "label":   "No context, no rewrite (independent turns)",
    },
    {
        "name":    "MT-Context",
        "mt_mode": "context",
        "subdir":  "mt_context",
        "label":   "Context injection only (LangGraph history, no SLM rewrite)",
    },
    {
        "name":    "MT-Full",
        "mt_mode": "full",
        "subdir":  "mt_full",
        "label":   "Full pipeline (SLM rewrite + LangGraph history) — production",
    },
]


# ── Helpers ──

def _load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bool(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes")


def _mcnemar(a_vals: list[int], b_vals: list[int]):
    """McNemar's test with continuity correction.

    Returns (chi2, p_value, a_wins, b_wins).
    a_wins = #cases where A correct but B wrong.
    b_wins = #cases where A wrong but B correct.
    """
    from scipy.stats import chi2 as chi2_dist

    n01 = sum(1 for a, b in zip(a_vals, b_vals) if a == 1 and b == 0)  # A right, B wrong
    n10 = sum(1 for a, b in zip(a_vals, b_vals) if a == 0 and b == 1)  # A wrong, B right
    denom = n01 + n10
    if denom == 0:
        return 0.0, 1.0, n01, n10
    chi2 = (abs(n01 - n10) - 1) ** 2 / denom  # continuity correction
    p = float(chi2_dist.sf(chi2, df=1))
    return chi2, p, n01, n10


def _sig(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


# ── Runner ──

def run_config(cfg: dict, dry_run: bool = False) -> dict:
    """Run evaluate_multi_turn for one mt_mode config."""
    from app.agent.evaluate import evaluate_multi_turn
    from app.agent.agent import reset_agent

    reset_agent()

    subdir = OUTPUT_BASE / cfg["subdir"]
    subdir.mkdir(parents=True, exist_ok=True)

    scenarios_path = str(SCENARIOS)

    if dry_run:
        # Write a 3-conversation subset to a temp file
        import tempfile, json as _json
        convs = []
        with open(SCENARIOS, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                convs.append(line)
        tmp = Path(tempfile.mktemp(suffix=".jsonl", prefix="exp4_dry_"))
        tmp.write_text("".join(convs), encoding="utf-8")
        scenarios_path = str(tmp)

    print(f"\n{'=' * 65}")
    print(f"Running {cfg['name']}  (mt_mode={cfg['mt_mode']})")
    print(f"  {cfg['label']}")
    print(f"  Output: {subdir}")
    print(f"{'=' * 65}")

    try:
        metrics = evaluate_multi_turn(
            scenarios_path=scenarios_path,
            output_dir=str(subdir),
            mode="routed",
            skip_judge=True,
            mt_mode=cfg["mt_mode"],
        )
    finally:
        if dry_run:
            Path(scenarios_path).unlink(missing_ok=True)

    return metrics


# ── Comparison compiler ──

def compile_comparison() -> None:
    """Load all 3 result sets and print/save comparison table + McNemar tests."""

    summaries: dict[str, dict] = {}
    conv_data: dict[str, list[dict]] = {}
    turn_data: dict[str, list[dict]] = {}

    for cfg in CONFIGS:
        subdir = OUTPUT_BASE / cfg["subdir"]
        summary_file  = subdir / f"summary_{cfg['mt_mode']}.json"
        conv_csv_file  = subdir / f"conv_results_{cfg['mt_mode']}.csv"
        turn_csv_file  = subdir / f"turn_results_{cfg['mt_mode']}.csv"

        if not summary_file.exists():
            print(f"  WARNING: {summary_file} not found — skipping {cfg['name']}")
            continue

        with open(summary_file, encoding="utf-8") as f:
            summaries[cfg["name"]] = json.load(f)

        if conv_csv_file.exists():
            conv_data[cfg["name"]] = _load_csv(conv_csv_file)

        if turn_csv_file.exists():
            turn_data[cfg["name"]] = _load_csv(turn_csv_file)

    if not summaries:
        print("No results found. Run experiments first.")
        return

    present = [c for c in CONFIGS if c["name"] in summaries]

    # ── Table header ──
    lines: list[str] = []
    sep90 = "=" * 90

    lines.append(sep90)
    lines.append("Experiment 4: Multi-Turn Ablation (RQ2)")

    total_convs = summaries[present[0]["name"]].get("total_conversations", "?")
    total_turns = summaries[present[0]["name"]].get("total_turns", "?")
    lines.append(f"Dataset: {total_convs} conversations, {total_turns} turns")
    lines.append("Router: Qwen3-4B FT (Ollama)  |  Agent: Qwen3-8B")
    lines.append(sep90)
    lines.append("")

    # ── Main metrics table ──
    col_w = 22
    lines.append(
        f"{'Config':<{col_w}}  {'CSR':>7}  {'ERA':>7}  {'ToolAcc':>8}  {'avg_CRR':>8}"
    )
    lines.append("-" * 58)

    for cfg in present:
        name = cfg["name"]
        m = summaries[name]
        lines.append(
            f"{name:<{col_w}}  {m['CSR']:>6.1f}%  {m['ERA']:>6.1f}%"
            f"  {m['overall_tool_accuracy']:>7.1f}%  {m['avg_CRR']:>7.2f}"
        )

    lines.append("")

    # ── Delta table (incremental gains) ──
    if "MT-Base" in summaries and "MT-Context" in summaries and "MT-Full" in summaries:
        lines.append("Incremental gains:")
        lines.append(f"  MT-Base → MT-Context  (context injection): "
                     f"CSR +{summaries['MT-Context']['CSR'] - summaries['MT-Base']['CSR']:+.1f}pp  "
                     f"ERA +{summaries['MT-Context']['ERA'] - summaries['MT-Base']['ERA']:+.1f}pp")
        lines.append(f"  MT-Context → MT-Full  (SLM rewriting):    "
                     f"CSR +{summaries['MT-Full']['CSR'] - summaries['MT-Context']['CSR']:+.1f}pp  "
                     f"ERA +{summaries['MT-Full']['ERA'] - summaries['MT-Context']['ERA']:+.1f}pp")
        lines.append(f"  MT-Base → MT-Full     (total):            "
                     f"CSR +{summaries['MT-Full']['CSR'] - summaries['MT-Base']['CSR']:+.1f}pp  "
                     f"ERA +{summaries['MT-Full']['ERA'] - summaries['MT-Base']['ERA']:+.1f}pp")
        lines.append("")

    # ── CSR by pattern ──
    all_patterns = sorted(
        {p for m in summaries.values() for p in m.get("by_pattern", {})}
    )
    if all_patterns:
        lines.append("CSR by Pattern (%):")
        name_header = "".join(f"  {c['name']:>12}" for c in present)
        lines.append(f"  {'Pattern':<25}{name_header}")
        lines.append("  " + "-" * (25 + 14 * len(present)))
        for pat in all_patterns:
            row = f"  {pat:<25}"
            for cfg in present:
                val = summaries[cfg["name"]].get("by_pattern", {}).get(pat, {}).get("csr")
                row += f"  {str(val) + '%':>12}" if val is not None else f"  {'—':>12}"
            lines.append(row)
        lines.append("")

    # ── McNemar — conversation-level CSR ──
    pairs = [("MT-Full", "MT-Context"), ("MT-Full", "MT-Base"), ("MT-Context", "MT-Base")]

    lines.append("McNemar's Test — Conversation-level CSR (paired, n=60 conversations):")
    lines.append(
        f"  {'Pair':<30}  {'chi2':>8}  {'p-value':>10}  {'Sig':>5}  {'A wins':>7}  {'B wins':>7}"
    )
    lines.append("  " + "-" * 74)

    for name_a, name_b in pairs:
        if name_a not in conv_data or name_b not in conv_data:
            lines.append(f"  {name_a + ' vs ' + name_b:<30}  (data missing)")
            continue

        map_a = {r["conversation_id"]: r for r in conv_data[name_a]}
        map_b = {r["conversation_id"]: r for r in conv_data[name_b]}
        common = sorted(set(map_a) & set(map_b))

        a_vals = [int(_bool(map_a[c]["conversation_success"])) for c in common]
        b_vals = [int(_bool(map_b[c]["conversation_success"])) for c in common]

        chi2, p, a_wins, b_wins = _mcnemar(a_vals, b_vals)
        sig = _sig(p)
        label = f"{name_a} vs {name_b}"
        lines.append(
            f"  {label:<30}  {chi2:>8.3f}  {p:>10.6f}  {sig:>5}  {a_wins:>7}  {b_wins:>7}"
        )

    lines.append("")

    # ── McNemar — turn-level tool accuracy ──
    lines.append("McNemar's Test — Turn-level Tool Accuracy (paired turns):")
    lines.append(
        f"  {'Pair':<30}  {'chi2':>8}  {'p-value':>10}  {'Sig':>5}  {'A wins':>7}  {'B wins':>7}"
    )
    lines.append("  " + "-" * 74)

    for name_a, name_b in pairs:
        if name_a not in turn_data or name_b not in turn_data:
            lines.append(f"  {name_a + ' vs ' + name_b:<30}  (data missing)")
            continue

        map_a = {(r["conversation_id"], str(r["turn"])): r for r in turn_data[name_a]}
        map_b = {(r["conversation_id"], str(r["turn"])): r for r in turn_data[name_b]}
        common = sorted(set(map_a) & set(map_b))

        a_vals = [int(_bool(map_a[k]["tool_correct"])) for k in common]
        b_vals = [int(_bool(map_b[k]["tool_correct"])) for k in common]

        chi2, p, a_wins, b_wins = _mcnemar(a_vals, b_vals)
        sig = _sig(p)
        label = f"{name_a} vs {name_b}"
        lines.append(
            f"  {label:<30}  {chi2:>8.3f}  {p:>10.6f}  {sig:>5}  {a_wins:>7}  {b_wins:>7}"
        )

    lines.append("")

    # ── ERA McNemar — context-dependent turns only ──
    lines.append("McNemar's Test — ERA (Entity Resolution, context-dependent turns only):")
    lines.append(
        f"  {'Pair':<30}  {'chi2':>8}  {'p-value':>10}  {'Sig':>5}  {'A wins':>7}  {'B wins':>7}"
    )
    lines.append("  " + "-" * 74)

    for name_a, name_b in pairs:
        if name_a not in turn_data or name_b not in turn_data:
            lines.append(f"  {name_a + ' vs ' + name_b:<30}  (data missing)")
            continue

        map_a = {(r["conversation_id"], str(r["turn"])): r
                 for r in turn_data[name_a] if _bool(r.get("requires_context", False))}
        map_b = {(r["conversation_id"], str(r["turn"])): r
                 for r in turn_data[name_b] if _bool(r.get("requires_context", False))}
        common = sorted(set(map_a) & set(map_b))

        if not common:
            lines.append(f"  {name_a + ' vs ' + name_b:<30}  (no context-dependent turns)")
            continue

        a_vals = [int(_bool(map_a[k]["entity_resolved"])) for k in common]
        b_vals = [int(_bool(map_b[k]["entity_resolved"])) for k in common]

        chi2, p, a_wins, b_wins = _mcnemar(a_vals, b_vals)
        sig = _sig(p)
        label = f"{name_a} vs {name_b}"
        lines.append(
            f"  {label:<30}  {chi2:>8.3f}  {p:>10.6f}  {sig:>5}  {a_wins:>7}  {b_wins:>7}"
        )

    lines.append("")
    lines.append(sep90)

    table_str = "\n".join(lines)
    print("\n" + table_str)

    # ── Save ──
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    out_txt = OUTPUT_BASE / "exp4_comparison_table.txt"
    out_txt.write_text(table_str, encoding="utf-8")

    out_json = OUTPUT_BASE / "exp4_summary.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {out_txt}")
    print(f"       {out_json}")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(
        description="Experiment 4: Multi-Turn Ablation (RQ2)"
    )
    parser.add_argument(
        "--configs", nargs="+",
        choices=["MT-Base", "MT-Context", "MT-Full"],
        default=["MT-Base", "MT-Context", "MT-Full"],
        help="Which configs to run (default: all 3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run with only 3 conversations to verify pipeline before full run",
    )
    parser.add_argument(
        "--compare-only", action="store_true",
        help="Skip experiment runs; only compile comparison from existing results",
    )
    args = parser.parse_args()

    if not args.compare_only:
        configs_to_run = [c for c in CONFIGS if c["name"] in args.configs]
        if not configs_to_run:
            print("No configs selected.")
            sys.exit(1)

        print(f"Running {len(configs_to_run)} config(s): {[c['name'] for c in configs_to_run]}")
        if args.dry_run:
            print("DRY-RUN mode: 3 conversations only")

        for cfg in configs_to_run:
            run_config(cfg, dry_run=args.dry_run)

    print("\nCompiling comparison table...")
    compile_comparison()


if __name__ == "__main__":
    main()
