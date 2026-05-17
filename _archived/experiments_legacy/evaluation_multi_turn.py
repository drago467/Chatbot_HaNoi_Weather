"""Multi-turn conversation evaluation framework.

Metrics computed:
- ERA  (Entity Resolution Accuracy): % context-dependent turns where entity resolved correctly
- CSR  (Conversation Success Rate): % conversations where ALL turns had correct tool selection
- CRR  (Context Retention Rate): avg consecutive correct turns before first context failure
- Turn-level Tool Accuracy: weighted by turn index (later turns harder)
"""
import csv
import json
from pathlib import Path
from uuid import uuid4

from experiments.evaluation.helpers import extract_tool_names, load_jsonl
from experiments.evaluation.tool_accuracy import check_tool_accuracy, check_tool_precision


def _evaluate_turn_mt(result: dict, turn_spec: dict, turn_index: int) -> dict:
    """Evaluate a single turn in a multi-turn conversation."""
    tools_called = extract_tool_names(result)
    messages = result.get("messages", [])
    response = messages[-1].content if messages else ""
    if response is None:
        response = ""

    intent = turn_spec.get("expected_intent", "")
    scope = turn_spec.get("expected_scope", "city")
    expected_location = turn_spec.get("expected_location")
    requires_context = turn_spec.get("requires_context_from_turn") is not None

    tool_correct = check_tool_accuracy(intent, tools_called, scope)
    tool_precision = check_tool_precision(intent, tools_called, scope)

    # Entity Resolution Accuracy: for context-dependent turns,
    # check if expected location appears in response
    entity_resolved = True
    if requires_context and expected_location:
        loc_lower = expected_location.lower()
        resp_lower = response.lower()
        entity_resolved = loc_lower in resp_lower

    return {
        "turn": turn_index,
        "user": turn_spec.get("user", ""),
        "expected_intent": intent,
        "expected_scope": scope,
        "expected_location": expected_location,
        "requires_context": requires_context,
        "tools_called": ",".join(tools_called),
        "tool_correct": tool_correct,
        "tool_precision": tool_precision,
        "entity_resolved": entity_resolved,
        "response_snippet": response[:200],
    }


def evaluate_multi_turn(
    scenarios_path: str = "data/evaluation/multi_turn_scenarios.jsonl",
    output_dir: str = "data/evaluation/multi_turn",
    mode: str = "routed",
    skip_judge: bool = True,
    mt_mode: str = "full",
) -> dict:
    """Multi-turn evaluation framework.

    Args:
        scenarios_path: Path to multi_turn_scenarios.jsonl
        output_dir: Output directory for results
        mode: Agent mode ("routed" recommended; "baseline" for comparison)
        skip_judge: Skip LLM-as-Judge (expensive for multi-turn)
        mt_mode: Multi-turn ablation mode:
            "full"    -- production (SLM rewrite + ConversationState context)
            "context" -- ConversationState maintained but SLM rewrite disabled
            "base"    -- each turn is independent (fresh thread_id, no context)
    """
    from app.agent.agent import run_agent_routed, run_agent, reset_agent

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not Path(scenarios_path).exists():
        print(f"Scenarios file not found: {scenarios_path}")
        return {}

    conversations = load_jsonl(scenarios_path)
    print(f"Loaded {len(conversations)} conversations from {scenarios_path}")
    print(f"Mode: {mode} | mt_mode: {mt_mode}")

    # Per-conversation results
    conv_results = []
    all_turn_results = []

    for conv_idx, conv in enumerate(conversations, 1):
        thread_id = f"mt_{mt_mode}_{conv['conversation_id']}_{uuid4().hex[:8]}"
        pattern = conv.get("pattern", "unknown")
        difficulty = conv.get("difficulty", "unknown")
        turns = conv.get("turns", [])

        print(f"\n[{conv_idx}/{len(conversations)}] {conv['conversation_id']} ({pattern}, {difficulty})")

        turn_metrics = []
        conv_success = True

        for turn_spec in turns:
            user_msg = turn_spec.get("user", "")
            turn_idx = turn_spec.get("turn", 0)
            print(f"  Turn {turn_idx}: {user_msg[:60]}...")

            try:
                if mt_mode == "base":
                    turn_thread_id = f"mt_base_{conv['conversation_id']}_t{turn_idx}_{uuid4().hex[:8]}"
                    result = run_agent_routed(user_msg, turn_thread_id, no_fallback=False)
                elif mt_mode == "context":
                    result = run_agent_routed(user_msg, thread_id, no_fallback=False, use_rewrite=False)
                elif mode == "routed":
                    result = run_agent_routed(user_msg, thread_id, no_fallback=False)
                else:
                    result = run_agent(user_msg, thread_id)

                tm = _evaluate_turn_mt(result, turn_spec, turn_idx)
                tm["success"] = True
                tm["error"] = None

            except Exception as e:
                tm = {
                    "turn": turn_idx,
                    "user": user_msg,
                    "expected_intent": turn_spec.get("expected_intent", ""),
                    "expected_scope": turn_spec.get("expected_scope", "city"),
                    "expected_location": turn_spec.get("expected_location"),
                    "requires_context": turn_spec.get("requires_context_from_turn") is not None,
                    "tools_called": "",
                    "tool_correct": False,
                    "tool_precision": 0.0,
                    "entity_resolved": False,
                    "response_snippet": "",
                    "success": False,
                    "error": str(e)[:200],
                }

            if not tm["tool_correct"]:
                conv_success = False

            turn_metrics.append(tm)
            all_turn_results.append({
                **tm,
                "conversation_id": conv["conversation_id"],
                "pattern": pattern,
                "difficulty": difficulty,
            })

            # Print turn result
            tc = tm.get("tool_correct", False)
            er = tm.get("entity_resolved", True)
            tools = tm.get("tools_called", "")[:50]
            print(f"    tool_correct={tc}, entity_resolved={er}, tools=[{tools}]")

        # Compute Context Retention Rate
        crr = 0
        for tm in turn_metrics:
            if tm["tool_correct"]:
                crr += 1
            else:
                break

        conv_results.append({
            "conversation_id": conv["conversation_id"],
            "pattern": pattern,
            "difficulty": difficulty,
            "num_turns": len(turns),
            "conversation_success": conv_success,
            "context_retention_rate": crr,
            "turn_tool_accuracy": round(
                sum(1 for t in turn_metrics if t["tool_correct"]) / len(turn_metrics) * 100, 1
            ) if turn_metrics else 0.0,
            "era": round(
                sum(1 for t in turn_metrics if t.get("requires_context") and t.get("entity_resolved", False))
                / max(1, sum(1 for t in turn_metrics if t.get("requires_context"))) * 100, 1
            ) if any(t.get("requires_context") for t in turn_metrics) else None,
        })

    # ── Aggregate Metrics ──
    total_convs = len(conv_results)
    total_turns = len(all_turn_results)

    csr = sum(1 for c in conv_results if c["conversation_success"]) / total_convs * 100 if total_convs else 0
    avg_crr = sum(c["context_retention_rate"] for c in conv_results) / total_convs if total_convs else 0

    context_turns = [t for t in all_turn_results if t.get("requires_context")]
    era = (
        sum(1 for t in context_turns if t.get("entity_resolved", False)) / len(context_turns) * 100
        if context_turns else 0
    )
    overall_tool_acc = (
        sum(1 for t in all_turn_results if t.get("tool_correct")) / total_turns * 100
        if total_turns else 0
    )

    # By pattern
    by_pattern: dict = {}
    for c in conv_results:
        p = c["pattern"]
        if p not in by_pattern:
            by_pattern[p] = {"total": 0, "success": 0}
        by_pattern[p]["total"] += 1
        if c["conversation_success"]:
            by_pattern[p]["success"] += 1
    for p in by_pattern:
        d = by_pattern[p]
        d["csr"] = round(d["success"] / d["total"] * 100, 1)

    metrics = {
        "mode": mode,
        "mt_mode": mt_mode,
        "total_conversations": total_convs,
        "total_turns": total_turns,
        "CSR": round(csr, 1),
        "ERA": round(era, 1),
        "avg_CRR": round(avg_crr, 2),
        "overall_tool_accuracy": round(overall_tool_acc, 1),
        "context_dependent_turns": len(context_turns),
        "by_pattern": by_pattern,
    }

    # ── Print Summary ──
    print("\n" + "=" * 60)
    print(f"MULTI-TURN EVALUATION RESULTS (mode={mode}, mt_mode={mt_mode})")
    print("=" * 60)
    print(f"Total conversations: {total_convs} | Total turns: {total_turns}")
    print(f"CSR  (Conversation Success Rate):   {metrics['CSR']}%")
    print(f"ERA  (Entity Resolution Accuracy):  {metrics['ERA']}%")
    print(f"avg_CRR (Avg context retention):    {metrics['avg_CRR']} turns")
    print(f"Overall turn-level tool accuracy:   {metrics['overall_tool_accuracy']}%")
    print()
    print("By Pattern:")
    for p, d in sorted(by_pattern.items()):
        print(f"  {p}: CSR={d['csr']}% ({d['success']}/{d['total']} convs)")

    # ── Save Results ──
    conv_csv = output_path / f"conv_results_{mt_mode}.csv"
    with open(conv_csv, "w", newline="", encoding="utf-8") as f:
        if conv_results:
            writer = csv.DictWriter(f, fieldnames=conv_results[0].keys())
            writer.writeheader()
            writer.writerows(conv_results)

    turn_csv = output_path / f"turn_results_{mt_mode}.csv"
    with open(turn_csv, "w", newline="", encoding="utf-8") as f:
        if all_turn_results:
            writer = csv.DictWriter(f, fieldnames=all_turn_results[0].keys())
            writer.writeheader()
            writer.writerows(all_turn_results)

    summary_json = output_path / f"summary_{mt_mode}.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_path}")
    return metrics
