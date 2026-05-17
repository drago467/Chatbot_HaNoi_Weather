"""Evaluation framework for Hanoi Weather Chatbot.

Tach tu app/agent/evaluate.py (1318 dong) thanh package module hoa:
- helpers.py:       extract tool info, load data
- metrics.py:       wilson_ci, compute_metrics
- tool_accuracy.py: INTENT_TO_TOOLS mapping, check_tool_*
- judges.py:        LLM-as-Judge (G-Eval, faithfulness)
- runner.py:        evaluate_query, run_evaluation (single-turn)
- __main__.py:      CLI: python -m experiments.evaluation
"""
from experiments.evaluation.tool_accuracy import (
    INTENT_TO_TOOLS,
    check_tool_accuracy,
    check_tool_precision,
    check_tool_recall,
)
from experiments.evaluation.judges import llm_judge
from experiments.evaluation.runner import run_evaluation, evaluate_query
from experiments.evaluation.metrics import compute_metrics, wilson_ci
from experiments.evaluation.helpers import (
    extract_tool_names,
    extract_tool_outputs,
    load_test_queries,
)

__all__ = [
    "INTENT_TO_TOOLS",
    "check_tool_accuracy",
    "check_tool_precision",
    "check_tool_recall",
    "llm_judge",
    "run_evaluation",
    "evaluate_query",
    "compute_metrics",
    "wilson_ci",
    "extract_tool_names",
    "extract_tool_outputs",
    "load_test_queries",
]
