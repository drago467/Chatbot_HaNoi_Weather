"""Single-turn evaluation runner.

Hai entry points:

- `run_evaluation()` — LEGACY (Phase 1 baseline/routed/hybrid mode). Giữ cho
  backward compat tới khi PR-C.4 confirm 6-config flow stable, sau đó archive.
- `run_eval_v2(config, ...)` — Phase 2 ablation (6 config qua EvalConfig +
  EvalAgent). Output JSONL per question. KHÔNG truncate tool_outputs.
"""
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from experiments.evaluation.helpers import (
    extract_tool_names, extract_tool_outputs, extract_detailed_tool_calls,
    categorize_error, load_test_queries,
)
from experiments.evaluation.tool_accuracy import (
    check_tool_accuracy, check_tool_precision, check_tool_recall,
)
from experiments.evaluation.judges import llm_judge
from experiments.evaluation.metrics import compute_metrics


def evaluate_query(question, query_id, expected_tool=None, expected_location=None,
                   location_scope="", judge_client=None, skip_judge=False,
                   mode="baseline"):
    """Evaluate a single query with unique thread_id and optional LLM judge.

    Args:
        mode: "baseline" (27 tools), "routed" (SLM, no fallback), "hybrid" (SLM + fallback)
    """
    from app.agent.agent import run_agent, run_agent_routed

    start_time = time.time()
    thread_id = f"eval_{query_id}_{uuid4().hex[:8]}"

    # Router metadata defaults
    _router_defaults = {
        "router_path": "", "router_intent": "", "router_scope": "",
        "router_confidence": None, "router_latency_ms": None,
        "router_focused_tools": "", "router_fallback_reason": "",
    }

    try:
        # Choose run function based on mode
        if mode == "routed":
            result = run_agent_routed(message=question, thread_id=thread_id,
                                      no_fallback=True)
        elif mode == "hybrid":
            result = run_agent_routed(message=question, thread_id=thread_id,
                                      no_fallback=False)
        else:  # baseline
            result = run_agent(message=question, thread_id=thread_id)

        # Extract router metadata if present
        router_info = result.pop("_router", None)

        messages = result.get("messages", [])
        response = messages[-1].content if messages else ""
        if response is None:
            response = ""
        elapsed_ms = (time.time() - start_time) * 1000

        tools_called = extract_tool_names(result)
        detailed_tool_calls = extract_detailed_tool_calls(result)
        intent = expected_tool or ""
        tool_correct = check_tool_accuracy(intent, tools_called, location_scope)
        tool_output = extract_tool_outputs(result)

        eval_result = {
            "question": question,
            "intent": expected_tool,
            "location": expected_location,
            "location_scope": location_scope,
            "response": response,
            "response_time_ms": round(elapsed_ms),
            "success": True,
            "error": None,
            "error_category": None,
            "tools_called": ",".join(tools_called),
            "tool_correct": tool_correct,
            "tool_precision": check_tool_precision(intent, tools_called, location_scope),
            "tool_recall": check_tool_recall(intent, tools_called, location_scope),
            "tool_output_raw": tool_output[:2000],
        }

        # Router metadata
        if router_info:
            eval_result["router_path"] = router_info.get("path", "")
            eval_result["router_intent"] = router_info.get("intent", "")
            eval_result["router_scope"] = router_info.get("scope", "")
            eval_result["router_confidence"] = router_info.get("confidence", 0)
            eval_result["router_latency_ms"] = round(router_info.get("latency_ms", 0), 1)
            eval_result["router_focused_tools"] = ",".join(router_info.get("focused_tools", []))
            eval_result["router_fallback_reason"] = router_info.get("fallback_reason") or ""
        else:
            eval_result.update(_router_defaults)

        # LLM-as-Judge
        if not skip_judge and response:
            judge_scores = llm_judge(question, response, tool_output, judge_client)
            eval_result.update({
                "judge_relevance": judge_scores.get("relevance"),
                "judge_completeness": judge_scores.get("completeness"),
                "judge_fluency": judge_scores.get("fluency"),
                "judge_actionability": judge_scores.get("actionability"),
                "judge_faithfulness": judge_scores.get("faithfulness"),
                "judge_reasoning": judge_scores.get("judge_reasoning", ""),
                "faith_reasoning": judge_scores.get("faith_reasoning", ""),
            })
        else:
            eval_result.update({
                "judge_relevance": None,
                "judge_completeness": None,
                "judge_fluency": None,
                "judge_actionability": None,
                "judge_faithfulness": None,
                "judge_reasoning": "",
                "faith_reasoning": "",
            })

        # Attach detailed tool calls for logging (popped before CSV write)
        eval_result["_detailed_tool_calls"] = detailed_tool_calls
        return eval_result

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        error_str = str(e)
        err_result = {
            "question": question,
            "intent": expected_tool,
            "location": expected_location,
            "location_scope": location_scope,
            "response": "",
            "response_time_ms": round(elapsed_ms),
            "success": False,
            "error": error_str,
            "error_category": categorize_error(error_str),
            "tools_called": "",
            "tool_correct": False,
            "tool_precision": 0.0,
            "tool_recall": 0.0,
            "tool_output_raw": "",
            "judge_relevance": None,
            "judge_completeness": None,
            "judge_fluency": None,
            "judge_actionability": None,
            "judge_faithfulness": None,
            "judge_reasoning": "",
            "faith_reasoning": "",
        }
        err_result.update(_router_defaults)
        return err_result


def run_evaluation(output_dir="data/evaluation", skip_judge=False, mode="baseline", offset=0):
    """Run full evaluation pipeline.

    Args:
        output_dir: Base directory (contains eval questions CSV)
        skip_judge: Skip LLM-as-Judge evaluation
        mode: "baseline" (27 tools), "routed" (SLM, no fallback), "hybrid" (SLM + fallback)
        offset: Skip first N questions (for incremental runs on new questions only)
    """
    from app.agent.agent import reset_agent
    from app.agent.telemetry import get_evaluation_logger

    # Reset agent to ensure fresh instance
    reset_agent()

    # Results go to mode-specific subdirectory
    results_dir = Path(output_dir) / mode
    results_dir.mkdir(parents=True, exist_ok=True)

    logger = get_evaluation_logger(str(results_dir))

    test_file = Path(output_dir) / "hanoi_weather_chatbot_eval_questions.csv"
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return

    queries = load_test_queries(str(test_file))
    if offset:
        queries = queries[offset:]
        print(f"Loaded {len(queries)} test queries (offset={offset}, skipped first {offset})")
    else:
        print(f"Loaded {len(queries)} test queries")
    print(f"Mode: {mode}")

    # Initialize judge client once (reuse connection)
    judge_client = None
    if not skip_judge:
        try:
            from openai import OpenAI
            judge_client = OpenAI(
                base_url=os.getenv("JUDGE_API_BASE") or os.getenv("API_BASE"),
                api_key=os.getenv("JUDGE_API_KEY") or os.getenv("API_KEY"),
            )
            judge_model = os.getenv("JUDGE_MODEL") or os.getenv("MODEL", "gpt-4o-mini")
            print(f"LLM-as-Judge: ENABLED (model={judge_model})")
        except Exception as e:
            print(f"LLM-as-Judge: DISABLED ({e})")
            skip_judge = True
    else:
        print("LLM-as-Judge: SKIPPED (--skip-judge)")

    results = []
    for i, q in enumerate(queries, 1):
        question = q.get("question", q.get("query", ""))
        print(f"[{i}/{len(queries)}] {question[:60]}...")

        result = evaluate_query(
            question=question,
            query_id=i,
            expected_tool=q.get("intent"),
            expected_location=q.get("location_name"),
            location_scope=q.get("location_scope", ""),
            judge_client=judge_client,
            skip_judge=skip_judge,
            mode=mode,
        )
        result["difficulty"] = q.get("difficulty", "unknown")
        results.append(result)

        # Print router info inline
        if mode != "baseline" and result.get("router_path"):
            rp = result["router_path"]
            ri = result.get("router_intent", "?")
            rs = result.get("router_scope", "?")
            rc = result.get("router_confidence", "?")
            rl = result.get("router_latency_ms", "?")
            print(f"  -> Router: {rp} ({ri}/{rs}, conf={rc}, {rl}ms)")

        # Print judge scores inline
        if not skip_judge and result.get("judge_relevance") is not None:
            r, c, fl, a, fa = (
                result.get("judge_relevance", "-"),
                result.get("judge_completeness", "-"),
                result.get("judge_fluency", "-"),
                result.get("judge_actionability", "-"),
                result.get("judge_faithfulness", "-"),
            )
            print(f"  -> Judge: R={r} C={c} F={fl} A={a} Faith={fa}")

        # Log conversation (with tool names)
        tools_called_list = result.get("tools_called", "").split(",") if result.get("tools_called") else None
        logger.log_conversation(
            session_id=f"eval_{i}",
            turn_number=i,
            user_query=question,
            llm_response=result["response"][:500],
            response_time_ms=result["response_time_ms"],
            tool_calls=tools_called_list,
            error_type=result["error"],
        )

        # Log individual tool calls
        for tc in result.get("_detailed_tool_calls", []):
            logger.log_tool_call(
                session_id=f"eval_{i}",
                turn_number=i,
                tool_name=tc["name"],
                tool_input=tc["input"],
                tool_output=tc["output"],
                success=True,
            )

    # Remove internal key before saving to CSV
    for r in results:
        r.pop("_detailed_tool_calls", None)

    # Compute metrics
    metrics = compute_metrics(results)
    metrics["mode"] = mode

    # Print summary
    print()
    print("=" * 60)
    print(f"EVALUATION RESULTS (mode={mode})")
    print("=" * 60)
    print(f"Total: {metrics['total']}")
    print(f"Success rate: {metrics['success_rate']}%")
    ci = metrics['tool_accuracy_ci95']
    print(f"Tool accuracy: {metrics['tool_accuracy']}% [95% CI: {ci[0]}-{ci[1]}%]")
    rci = metrics['tool_recall_ci95']
    print(f"Tool precision: {metrics['tool_precision_avg']} | Tool recall: {metrics['tool_recall_avg']} [95% CI: {rci[0]}-{rci[1]}%]")
    print(f"Avg time: {metrics['avg_time_ms']}ms | p50: {metrics['p50_time_ms']}ms | p90: {metrics['p90_time_ms']}ms | p95: {metrics['p95_time_ms']}ms")

    # Router metrics
    if mode != "baseline" and metrics.get("router_coverage") is not None:
        print()
        print("Router Metrics:")
        print(f"  Coverage (routed): {metrics.get('router_coverage')}%")
        print(f"  Fallback rate: {metrics.get('router_fallback_rate')}%")
        print(f"  Avg router latency: {metrics.get('router_avg_latency_ms')}ms")
        ria = metrics.get('router_intent_accuracy')
        if ria is not None:
            ria_ci = metrics.get('router_intent_accuracy_ci95', (0, 0))
            print(f"  Router intent accuracy: {ria}% [95% CI: {ria_ci[0]}-{ria_ci[1]}%]")
        rta = metrics.get('routed_tool_accuracy')
        if rta is not None:
            print(f"  Routed-only tool accuracy: {rta}%")

    # Judge scores
    if not skip_judge:
        print()
        print("LLM-as-Judge Scores (1-5):")
        for dim in ["judge_relevance", "judge_completeness", "judge_fluency",
                     "judge_actionability", "judge_faithfulness"]:
            avg = metrics.get(dim + "_avg")
            cnt = metrics.get(dim + "_count", 0)
            label = dim.replace("judge_", "").capitalize()
            print(f"  {label}: {avg}/5 ({cnt} rated)")

    print()
    print("By Intent:")
    for intent, data in sorted(metrics["by_intent"].items()):
        ci = data.get("tool_accuracy_ci95", (0, 0))
        judge_str = ""
        if not skip_judge:
            r_avg = data.get("judge_relevance_avg", "-")
            f_avg = data.get("judge_faithfulness_avg", "-")
            judge_str = f", rel={r_avg}, faith={f_avg}"
        print(f"  {intent}: {data['tool_accuracy']}% [CI: {ci[0]}-{ci[1]}%], {data['avg_time_ms']}ms{judge_str} ({data['total']}q)")

    print()
    print("By Difficulty:")
    for diff, data in sorted(metrics["by_difficulty"].items()):
        ci = data.get("tool_accuracy_ci95", (0, 0))
        judge_str = ""
        if not skip_judge:
            r_avg = data.get("judge_relevance_avg", "-")
            f_avg = data.get("judge_faithfulness_avg", "-")
            judge_str = f", rel={r_avg}, faith={f_avg}"
        print(f"  {diff}: acc={data['tool_accuracy']}% [CI: {ci[0]}-{ci[1]}%]{judge_str} ({data['total']}q)")

    # Save results
    csv_file = results_dir / "evaluation_results.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    json_file = results_dir / "evaluation_summary.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\nResults: {csv_file}")
    print(f"Summary: {json_file}")


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 — 6-config ablation (PR-C.1c)
# ═══════════════════════════════════════════════════════════════════════════


def run_eval_v2(
    config_name: str,
    dataset_path: str = "data/evaluation/v2/hanoi_weather_eval_v2_500.csv",
    output_dir: str = "data/evaluation/v2/run_results",
    limit: Optional[int] = None,
    offset: int = 0,
) -> Path:
    """Run 1 ablation config qua dataset v2 → JSONL output (no judge).

    Judge sẽ chạy riêng ở PR-D.2 (`experiments.evaluation.judge_run`) sau khi
    có response đầy đủ.

    Args:
        config_name: 'c1'..'c6' — tên YAML ở `configs/`.
        dataset_path: CSV dataset (default v2 500 câu).
        output_dir: Where JSONL output saved.
        limit: Stop sau N câu (None = full).
        offset: Skip N câu đầu.

    Returns:
        Path tới file JSONL output.
    """
    from experiments.evaluation.config import load_config
    from experiments.evaluation.backends.agent import EvalAgent

    config = load_config(config_name)

    dataset_path_p = Path(dataset_path)
    if not dataset_path_p.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path_p}")

    output_dir_p = Path(output_dir)
    output_dir_p.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir_p / f"{config.name.lower()}_{timestamp}.jsonl"

    queries = load_test_queries(str(dataset_path_p))
    if offset:
        queries = queries[offset:]
    if limit:
        queries = queries[:limit]

    print(f"Config: {config.name}")
    print(f"  router_backend: {config.router_backend}")
    print(f"  agent: {config.agent_model_name} ({config.agent_gateway.value})")
    print(f"  thinking: {config.agent_thinking}")
    print(f"  tool_path: {config.tool_path}")
    print(f"Dataset: {dataset_path_p} ({len(queries)} queries)")
    print(f"Output: {output_file}")
    print()

    n_success = 0
    n_error = 0
    total_input_tokens = 0
    total_output_tokens = 0

    with EvalAgent(config) as agent:
        with output_file.open("w", encoding="utf-8") as f_out:
            for i, q in enumerate(queries, 1):
                question = q.get("question", "")
                qid = q.get("id", f"row_{i}")

                result = agent.run(question)

                row = {
                    "config": config.name,
                    "question_id": qid,
                    "question": question,
                    "intent_gold": q.get("intent"),
                    "scope_gold": q.get("location_scope"),
                    "difficulty": q.get("difficulty"),
                    "source": q.get("source"),
                    "expected_tools": q.get("expected_tools"),
                    "expected_abstain": q.get("expected_abstain"),
                    "expected_clarification": q.get("expected_clarification"),
                    "response": result.response,
                    "tools_called": result.tools_called,
                    "tool_outputs": result.tool_outputs,
                    "tool_subset_size": result.tool_subset_size,
                    "detailed_tool_calls": result.detailed_tool_calls,
                    "router_intent": result.router_intent,
                    "router_scope": result.router_scope,
                    "router_confidence": result.router_confidence,
                    "router_fallback_reason": result.router_fallback_reason,
                    "router_latency_ms": round(result.router_latency_ms, 2),
                    "agent_latency_ms": round(result.agent_latency_ms, 2),
                    "total_latency_ms": round(result.total_latency_ms, 2),
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "success": result.success,
                    "error": result.error,
                    "error_category": result.error_category,
                }
                f_out.write(json.dumps(row, ensure_ascii=False) + "\n")

                if result.success:
                    n_success += 1
                else:
                    n_error += 1
                total_input_tokens += result.input_tokens
                total_output_tokens += result.output_tokens

                tools_str = ",".join(result.tools_called) if result.tools_called else "-"
                print(
                    f"[{i}/{len(queries)}] {question[:50]}... → {tools_str} "
                    f"({result.total_latency_ms:.0f}ms)"
                )

    print()
    print("=" * 60)
    print(f"DONE — {config.name}")
    print(f"  Success: {n_success}/{len(queries)}")
    print(f"  Error: {n_error}/{len(queries)}")
    print(f"  Total tokens: in={total_input_tokens:,} out={total_output_tokens:,}")
    print(f"  Output: {output_file}")
    return output_file
