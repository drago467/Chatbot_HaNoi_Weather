"""Statistical metrics for evaluation — Wilson CI, compute_metrics."""
import math


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple:
    """Wilson score confidence interval for binomial proportion.

    More accurate than normal approximation for small samples (n < 30).
    Reference: Agresti & Coull (1998), Wilson (1927).

    Args:
        successes: Number of successes (e.g., correct tool selections)
        total: Total number of trials
        z: Z-score for confidence level (1.96 = 95% CI)

    Returns:
        (lower_bound, upper_bound) as percentages (0-100)
    """
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z ** 2 / total
    center = (p + z ** 2 / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z ** 2 / (4 * total ** 2)) / denom
    lower = round(max(0.0, center - margin) * 100, 1)
    upper = round(min(1.0, center + margin) * 100, 1)
    return (lower, upper)


def compute_metrics(results):
    """Compute comprehensive evaluation metrics including judge scores."""
    total = len(results)
    successful = [r for r in results if r["success"]]
    times = sorted([r["response_time_ms"] for r in results])

    # Core counts for CI calculation
    tool_correct_count = sum(1 for r in results if r.get("tool_correct"))
    recall_correct_count = sum(1 for r in results if r.get("tool_recall", 0) >= 1.0)

    metrics = {
        "total": total,
        "successful": len(successful),
        "success_rate": round(len(successful) / total * 100, 1) if total else 0,
        "tool_accuracy": round(tool_correct_count / total * 100, 1) if total else 0,
        "tool_accuracy_ci95": wilson_ci(tool_correct_count, total),
        "tool_precision_avg": round(
            sum(r.get("tool_precision", 0) for r in results) / total, 2
        ) if total else 0,
        "tool_recall_avg": round(
            sum(r.get("tool_recall", 0) for r in results) / total, 2
        ) if total else 0,
        "tool_recall_ci95": wilson_ci(recall_correct_count, total),
        "avg_time_ms": round(sum(times) / total) if total else 0,
        "p50_time_ms": round(times[total // 2]) if times else 0,
        "p90_time_ms": round(times[int(total * 0.9)]) if times else 0,
        "p95_time_ms": round(times[int(total * 0.95)]) if times else 0,
    }

    # Error category breakdown
    error_cats = {}
    for r in results:
        cat = r.get("error_category")
        if cat:
            error_cats[cat] = error_cats.get(cat, 0) + 1
    if error_cats:
        metrics["error_categories"] = error_cats

    # Router metrics (if available)
    routed_results = [r for r in results if r.get("router_path") == "routed"]
    fallback_results = [r for r in results if r.get("router_path") == "fallback"]
    has_router = bool(routed_results or fallback_results)

    if has_router:
        total_with_router = len(routed_results) + len(fallback_results)
        metrics["router_coverage"] = round(len(routed_results) / total_with_router * 100, 1)
        metrics["router_fallback_rate"] = round(len(fallback_results) / total_with_router * 100, 1)

        router_latencies = [r["router_latency_ms"] for r in results
                            if r.get("router_latency_ms") is not None]
        if router_latencies:
            metrics["router_avg_latency_ms"] = round(sum(router_latencies) / len(router_latencies), 1)

        # Router intent accuracy vs expected intent from CSV
        intent_correct = sum(1 for r in results
                             if r.get("router_intent") and r.get("router_intent") == r.get("intent"))
        intent_total = sum(1 for r in results if r.get("router_intent"))
        if intent_total:
            metrics["router_intent_accuracy"] = round(intent_correct / intent_total * 100, 1)
            metrics["router_intent_accuracy_ci95"] = wilson_ci(intent_correct, intent_total)

        # Routed-only tool accuracy (how accurate when using focused tools)
        routed_correct = sum(1 for r in routed_results if r.get("tool_correct"))
        if routed_results:
            metrics["routed_tool_accuracy"] = round(routed_correct / len(routed_results) * 100, 1)

    # Judge score averages
    judge_dims = ["judge_relevance", "judge_completeness", "judge_fluency", "judge_actionability", "judge_faithfulness"]
    for dim in judge_dims:
        vals = [r[dim] for r in results if r.get(dim) is not None]
        metrics[dim + "_avg"] = round(sum(vals) / len(vals), 2) if vals else None
        metrics[dim + "_count"] = len(vals)

    # By intent (with judge scores)
    by_intent = {}
    for r in results:
        intent = r.get("intent", "unknown")
        if intent not in by_intent:
            by_intent[intent] = {
                "total": 0, "success": 0, "tool_correct": 0, "times": [],
                "judge_scores": {d: [] for d in judge_dims},
            }
        by_intent[intent]["total"] += 1
        if r["success"]:
            by_intent[intent]["success"] += 1
        if r.get("tool_correct"):
            by_intent[intent]["tool_correct"] += 1
        by_intent[intent]["times"].append(r["response_time_ms"])
        for d in judge_dims:
            if r.get(d) is not None:
                by_intent[intent]["judge_scores"][d].append(r[d])

    metrics["by_intent"] = {}
    for k, v in by_intent.items():
        entry = {
            "total": v["total"],
            "success_rate": round(v["success"] / v["total"] * 100, 1),
            "tool_accuracy": round(v["tool_correct"] / v["total"] * 100, 1),
            "tool_accuracy_ci95": wilson_ci(v["tool_correct"], v["total"]),
            "avg_time_ms": round(sum(v["times"]) / len(v["times"])),
        }
        for d in judge_dims:
            vals = v["judge_scores"][d]
            entry[d + "_avg"] = round(sum(vals) / len(vals), 2) if vals else None
        metrics["by_intent"][k] = entry

    # By difficulty (with judge scores)
    by_diff = {}
    for r in results:
        diff = r.get("difficulty", "unknown")
        if diff not in by_diff:
            by_diff[diff] = {
                "total": 0, "success": 0, "tool_correct": 0,
                "judge_scores": {d: [] for d in judge_dims},
            }
        by_diff[diff]["total"] += 1
        if r["success"]:
            by_diff[diff]["success"] += 1
        if r.get("tool_correct"):
            by_diff[diff]["tool_correct"] += 1
        for d in judge_dims:
            if r.get(d) is not None:
                by_diff[diff]["judge_scores"][d].append(r[d])

    metrics["by_difficulty"] = {}
    for k, v in by_diff.items():
        entry = {
            "total": v["total"],
            "success_rate": round(v["success"] / v["total"] * 100, 1),
            "tool_accuracy": round(v["tool_correct"] / v["total"] * 100, 1),
            "tool_accuracy_ci95": wilson_ci(v["tool_correct"], v["total"]),
        }
        for d in judge_dims:
            vals = v["judge_scores"][d]
            entry[d + "_avg"] = round(sum(vals) / len(vals), 2) if vals else None
        metrics["by_difficulty"][k] = entry

    return metrics
