"""CLI entry point: python -m experiments.evaluation"""
import argparse

from experiments.evaluation.runner import run_evaluation
from experiments.evaluation.multi_turn import evaluate_multi_turn


def main():
    parser = argparse.ArgumentParser(description="Evaluate weather chatbot")
    parser.add_argument("--output", default="data/evaluation")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N questions (for incremental runs)")
    parser.add_argument("--skip-judge", action="store_true",
                        help="Skip LLM-as-Judge evaluation")
    parser.add_argument("--mode", choices=["baseline", "routed", "hybrid"],
                        default="baseline",
                        help="baseline: 27 tools | routed: SLM, no fallback | hybrid: SLM + fallback")
    parser.add_argument("--multi-turn", action="store_true",
                        help="Run multi-turn evaluation instead of single-turn")
    parser.add_argument("--mt-scenarios", default="data/evaluation/multi_turn_scenarios.jsonl",
                        help="Path to multi-turn scenarios JSONL")
    parser.add_argument("--mt-mode", choices=["full", "context", "base"], default="full",
                        help="full: SLM rewrite+context | context: no rewrite | base: independent turns")
    args = parser.parse_args()

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
