"""CLI entry point: python -m experiments.evaluation

Ba mode:
- Legacy: `--mode baseline|routed|hybrid` (Phase 1 baseline runner).
- 6-config ablation: `--config c1|c2|c3|c4|c5|c6` (Phase 2 PR-C.1c).
- Batch judge: `--judge-input <run_results.jsonl>` (Phase 2 PR-C.5 Step 2).
  Khi `--judge-input` set, các flag khác bị bỏ qua.
"""
import argparse
from pathlib import Path

from experiments.evaluation.runner import run_evaluation, run_eval_v2
from experiments.evaluation.multi_turn import evaluate_multi_turn


def main():
    parser = argparse.ArgumentParser(description="Evaluate weather chatbot")

    # Phase 2 PR-C.5 Step 2 — Batch judge
    parser.add_argument(
        "--judge-input", default=None,
        help="Path to run_results JSONL → batch judge mode (PR-C.5 Step 2). "
             "Output JSONL ghi per-sample (resumable, crash-safe).",
    )
    parser.add_argument(
        "--judge-output", default=None,
        help="Output judge_results JSONL path. Default: input.judge.jsonl",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable judge file cache (default: .cache/judge/).",
    )

    # Phase 2 — 6-config ablation (PR-C.1c)
    parser.add_argument(
        "--config", default=None,
        help="Eval config name (c1..c6). Set → dùng EvalConfig pluggable runner. "
             "Override --mode legacy.",
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/eval_dataset_500.csv",
        help="Dataset CSV path (default 500 câu).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop sau N câu (smoke test).",
    )
    parser.add_argument(
        "--run-output",
        default="data/evaluation/run_results",
        help="Output directory cho JSONL run results (--config mode).",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Path tới JSONL output cũ → resume mode. Skip qids đã có, append. "
             "Cần thiết cho long run (10h) để recover sau crash/disconnect.",
    )

    # Legacy flags — Phase 1 baseline runner
    parser.add_argument("--output", default="data/evaluation",
                        help="(Legacy) Base output dir.")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N questions (for incremental runs)")
    parser.add_argument("--skip-judge", action="store_true",
                        help="(Legacy) Skip LLM-as-Judge evaluation")
    parser.add_argument("--mode", choices=["baseline", "routed", "hybrid"],
                        default="baseline",
                        help="(Legacy) baseline: 27 tools | routed: SLM, no fallback | "
                             "hybrid: SLM + fallback")
    parser.add_argument("--multi-turn", action="store_true",
                        help="(Legacy) Run multi-turn evaluation")
    parser.add_argument("--mt-scenarios",
                        default="data/evaluation/multi_turn_scenarios.jsonl",
                        help="(Legacy) Path to multi-turn scenarios JSONL")
    parser.add_argument("--mt-mode", choices=["full", "context", "base"],
                        default="full",
                        help="(Legacy) full/context/base multi-turn mode")
    args = parser.parse_args()

    # Phase 2 PR-C.5 Step 2 — Batch judge takes top priority
    if args.judge_input:
        from experiments.evaluation.judge_run import judge_run

        cache_dir = None if args.no_cache else Path(".cache/judge")
        judge_run(
            input_jsonl=Path(args.judge_input),
            output_jsonl=Path(args.judge_output) if args.judge_output else None,
            cache_dir=cache_dir,
            limit=args.limit,
        )
        return

    # Phase 2 path: --config takes priority
    if args.config:
        run_eval_v2(
            config_name=args.config,
            dataset_path=args.dataset,
            output_dir=args.run_output,
            limit=args.limit,
            offset=args.offset,
            resume_from=Path(args.resume) if args.resume else None,
        )
        return

    # Legacy paths
    if args.multi_turn:
        evaluate_multi_turn(
            scenarios_path=args.mt_scenarios,
            output_dir=args.output + "/multi_turn",
            mode=args.mode,
            skip_judge=args.skip_judge,
            mt_mode=args.mt_mode,
        )
    else:
        run_evaluation(args.output, skip_judge=args.skip_judge,
                       mode=args.mode, offset=args.offset)


if __name__ == "__main__":
    main()
