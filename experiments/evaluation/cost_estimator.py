"""Cost estimator cho 6-config eval (PR-C.3, updated post-PR-C.7).

Heuristic per-row token estimate × rate (`configs/rates.yaml`) → USD per config + judge.
Phát hiện sớm config nào tốn quá ngân sách trước khi run thực PR-D.1+D.2.

Heuristic constants — updated 2026-04-28 từ smoke 6×10 actual measurements
sau PR-C.7 fix (system prompt 246 dòng + 27 TOOL_RULES injected per call):
- Agent prefilter (~5 tools, qwen3-14b thinking): input ~26K / output ~200 tokens/row.
- Agent full_27 (qwen3-14b thinking): input ~40K / output ~200.
- Agent full_27 (commercial — gpt-4o-mini, gemini-flash, no thinking): input ~35K / output ~200.
- SLM router classification: input ~300 / output ~50 tokens/row.
- Judge faithfulness (rubric ~1.5K + tool_outputs ~1.5K + question + response): input ~3.5K / output ~80.
- Judge relevance (rubric + question + response): input ~700 / output ~80.

NOTE: Smoke nghiêng simple "current weather" queries (1 tool call avg, ~1.5K
tool_outputs). Full 500 dataset có queries phức tạp (forecasts, comparisons,
multi-aspect) sẽ tăng tool_calls + tool_outputs size → input tokens ~1.3-1.5x
smoke baseline. Apply 30% buffer trong heuristic dưới đây.

Sau PR-D.1 first 50 rows (mixed difficulty) → re-calibrate nếu actual lệch >20%.

Usage:
    python -m experiments.evaluation.cost_estimator
    python -m experiments.evaluation.cost_estimator --dataset-size 500
    python -m experiments.evaluation.cost_estimator --rates path/to/rates.yaml
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import yaml

from experiments.evaluation.config import EvalConfig, load_config

_DEFAULT_RATES_FILE = (
    Path(__file__).resolve().parent / "configs" / "rates.yaml"
)
_DEFAULT_DATASET_SIZE = 500
_DEFAULT_CONFIG_NAMES = ("c1", "c2", "c3", "c4", "c5", "c6")
_DEFAULT_JUDGE_MODEL = "gpt-4o"

# Heuristic token per row — calibrated 2026-04-28 từ smoke 6×10 + 30% buffer
# cho query complexity variance (smoke biased simple "current weather" queries).
# Smoke baseline (avg over 10 simple queries):
#   prefilter qwen3-14b thinking: 25,769 in / 198 out
#   full_27 qwen3-14b thinking:    40,000 in / 190 out
#   full_27 gpt-4o-mini/gemini:    34,780 in / 206 out
# Buffer 30% → conservative estimate cho 500 mixed-complexity dataset.
_AGENT_TOKENS_PREFILTER = {"input": 33500, "output": 250}
_AGENT_TOKENS_FULL27_QWEN = {"input": 52000, "output": 250}
_AGENT_TOKENS_FULL27_COMMERCIAL = {"input": 45000, "output": 250}
_ROUTER_TOKENS = {"input": 300, "output": 50}
# Judge: rubric prompt ~1.5K + tool_outputs ~1.5K (smoke) + question ~50 + response ~600.
# Buffer 30% cho complex queries với larger tool_outputs.
_JUDGE_FAITH_TOKENS = {"input": 4500, "output": 100}
_JUDGE_REL_TOKENS = {"input": 1200, "output": 100}

# % rows assumed smalltalk → skip faithfulness (theo dataset v2 ~12 smalltalk/500=2.4%)
_SMALLTALK_RATIO = 0.024


@dataclass
class CostBreakdown:
    """Per-config cost decomposition."""

    config_name: str
    router_input_tokens: int
    router_output_tokens: int
    router_cost: float
    agent_input_tokens: int
    agent_output_tokens: int
    agent_cost: float

    @property
    def total_cost(self) -> float:
        return self.router_cost + self.agent_cost

    @property
    def total_tokens(self) -> int:
        return (
            self.router_input_tokens + self.router_output_tokens
            + self.agent_input_tokens + self.agent_output_tokens
        )


@dataclass
class JudgeCostBreakdown:
    """Judge cost cho 1 config (faithfulness + relevance × dataset_size)."""

    n_faithfulness_calls: int  # = dataset_size × (1 - smalltalk_ratio)
    n_relevance_calls: int  # = dataset_size
    input_tokens: int
    output_tokens: int
    cost: float


def load_rates(rates_path: Path) -> dict[str, dict[str, float]]:
    """Load rate config từ YAML."""
    return yaml.safe_load(rates_path.read_text(encoding="utf-8"))


def _compute_cost(input_tokens: int, output_tokens: int, rate: dict) -> float:
    return (
        input_tokens * rate["input"] / 1_000_000
        + output_tokens * rate["output"] / 1_000_000
    )


def estimate_config_cost(
    config: EvalConfig,
    dataset_size: int,
    rates: dict[str, dict],
) -> CostBreakdown:
    """Estimate run cost cho 1 config × dataset_size rows."""
    if config.agent_model_name not in rates:
        raise KeyError(
            f"Rate cho agent_model={config.agent_model_name!r} không có trong rates.yaml"
        )
    agent_rate = rates[config.agent_model_name]

    if config.tool_path == "router_prefilter":
        agent_tok = _AGENT_TOKENS_PREFILTER
    elif "qwen" in config.agent_model_name.lower():
        # Qwen3-14b thinking mode: input ~52K (smoke 40K + 30% buffer)
        agent_tok = _AGENT_TOKENS_FULL27_QWEN
    else:
        # Commercial (gpt-4o-mini, gemini-flash, no thinking): input ~45K
        agent_tok = _AGENT_TOKENS_FULL27_COMMERCIAL

    agent_in = dataset_size * agent_tok["input"]
    agent_out = dataset_size * agent_tok["output"]
    agent_cost = _compute_cost(agent_in, agent_out, agent_rate)

    router_in = 0
    router_out = 0
    router_cost = 0.0
    if config.router_backend != "none" and config.router_model_name:
        if config.router_model_name not in rates:
            raise KeyError(
                f"Rate cho router_model={config.router_model_name!r} không có"
            )
        router_rate = rates[config.router_model_name]
        router_in = dataset_size * _ROUTER_TOKENS["input"]
        router_out = dataset_size * _ROUTER_TOKENS["output"]
        router_cost = _compute_cost(router_in, router_out, router_rate)

    return CostBreakdown(
        config_name=config.name,
        router_input_tokens=router_in,
        router_output_tokens=router_out,
        router_cost=router_cost,
        agent_input_tokens=agent_in,
        agent_output_tokens=agent_out,
        agent_cost=agent_cost,
    )


def estimate_judge_cost(
    dataset_size: int,
    rates: dict[str, dict],
    judge_model: str = _DEFAULT_JUDGE_MODEL,
    smalltalk_ratio: float = _SMALLTALK_RATIO,
) -> JudgeCostBreakdown:
    """Estimate judge cost cho 1 config × dataset_size."""
    if judge_model not in rates:
        raise KeyError(f"Rate cho judge_model={judge_model!r} không có")
    rate = rates[judge_model]

    n_faith = int(round(dataset_size * (1 - smalltalk_ratio)))
    n_rel = dataset_size

    in_tok = (
        n_faith * _JUDGE_FAITH_TOKENS["input"]
        + n_rel * _JUDGE_REL_TOKENS["input"]
    )
    out_tok = (
        n_faith * _JUDGE_FAITH_TOKENS["output"]
        + n_rel * _JUDGE_REL_TOKENS["output"]
    )
    cost = _compute_cost(in_tok, out_tok, rate)
    return JudgeCostBreakdown(
        n_faithfulness_calls=n_faith,
        n_relevance_calls=n_rel,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost=cost,
    )


def estimate_total(
    config_names: Iterable[str],
    dataset_size: int,
    rates: dict[str, dict],
    judge_model: str = _DEFAULT_JUDGE_MODEL,
) -> dict:
    """Aggregate cost cho N config + judge."""
    breakdowns = [
        estimate_config_cost(load_config(n), dataset_size, rates)
        for n in config_names
    ]
    run_total = sum(b.total_cost for b in breakdowns)
    judge_per_config = estimate_judge_cost(dataset_size, rates, judge_model)
    judge_total = judge_per_config.cost * len(breakdowns)
    return {
        "config_breakdowns": breakdowns,
        "run_total": run_total,
        "judge_per_config": judge_per_config,
        "judge_total": judge_total,
        "grand_total": run_total + judge_total,
        "dataset_size": dataset_size,
        "n_configs": len(breakdowns),
    }


def print_report(report: dict) -> None:
    """Pretty-print cost estimate table tới stdout."""
    n = report["dataset_size"]
    n_cfg = report["n_configs"]
    print(f"\n=== Cost estimate cho {n} câu × {n_cfg} config + GPT-4o judge ===\n")

    print(
        f"{'Cfg':<5} {'Router model':<20} {'Agent model':<22} "
        f"{'Tool path':<18} {'Router $':>8} {'Agent $':>9} {'Total $':>9}"
    )
    print("-" * 95)

    for b in report["config_breakdowns"]:
        # Re-load config để lấy tên router model + tool_path
        cfg = load_config(b.config_name.lower())
        router_name = cfg.router_model_name or "-"
        print(
            f"{cfg.name:<5} {router_name:<20} {cfg.agent_model_name:<22} "
            f"{cfg.tool_path:<18} ${b.router_cost:>7.2f} "
            f"${b.agent_cost:>8.2f} ${b.total_cost:>8.2f}"
        )

    print("-" * 95)
    print(f"{'TOTAL agent run':<70} ${report['run_total']:>8.2f}")

    j = report["judge_per_config"]
    print()
    print(
        f"Judge per config: faith {j.n_faithfulness_calls} calls + rel "
        f"{j.n_relevance_calls} calls = ${j.cost:.2f}"
    )
    print(f"  (input {j.input_tokens:,} tokens + output {j.output_tokens:,} tokens)")
    print(f"Judge × {n_cfg} config: ${report['judge_total']:.2f}")

    print()
    print("=" * 95)
    print(f"GRAND TOTAL ESTIMATE: ${report['grand_total']:.2f}")
    print("=" * 95)
    print()
    print("⚠ Heuristic ±30%. Sau PR-C.4 smoke (10 câu × 6 config) actual sẽ chính xác hơn.")


def main():
    parser = argparse.ArgumentParser(
        description="Estimate cost cho 6-config eval + judge."
    )
    parser.add_argument(
        "--rates", default=str(_DEFAULT_RATES_FILE),
        help="Path tới rates.yaml.",
    )
    parser.add_argument(
        "--dataset-size", type=int, default=_DEFAULT_DATASET_SIZE,
        help="Số câu mỗi config (default 500).",
    )
    parser.add_argument(
        "--config-names", nargs="+", default=list(_DEFAULT_CONFIG_NAMES),
        help="Config names (c1..c6).",
    )
    parser.add_argument(
        "--judge-model", default=_DEFAULT_JUDGE_MODEL,
        help="Judge model name (default gpt-4o).",
    )
    args = parser.parse_args()

    rates = load_rates(Path(args.rates))
    report = estimate_total(
        config_names=args.config_names,
        dataset_size=args.dataset_size,
        rates=rates,
        judge_model=args.judge_model,
    )
    print_report(report)


if __name__ == "__main__":
    main()
