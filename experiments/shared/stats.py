"""Shared statistical tests for thesis experiments.

Consolidates duplicated wilson_ci, mcnemar_test, wilcoxon_test
that were copy-pasted across exp1/exp3/exp4/exp1_clean_rerun.
"""
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


def mcnemar_test(correct_a: list, correct_b: list) -> dict:
    """McNemar's test with continuity correction for paired binary outcomes.

    Args:
        correct_a: List of bool/int — whether system A was correct on each sample.
        correct_b: List of bool/int — whether system B was correct on each sample.

    Returns dict with chi2, p_value, discordant pair counts, significance flags.
    """
    from scipy.stats import chi2 as chi2_dist
    assert len(correct_a) == len(correct_b), "Lists must be same length"
    # b = A correct, B wrong; c = A wrong, B correct
    b = sum(1 for a, bb in zip(correct_a, correct_b) if a and not bb)
    c = sum(1 for a, bb in zip(correct_a, correct_b) if not a and bb)
    n = b + c
    if n == 0:
        return {"chi2": 0.0, "p_value": 1.0, "b_a_wins": 0, "c_b_wins": 0,
                "significant_0.05": False, "significant_0.01": False,
                "note": "No discordant pairs"}
    # Continuity correction
    chi2 = (abs(b - c) - 1) ** 2 / n
    p_value = float(1 - chi2_dist.cdf(chi2, df=1))
    return {
        "chi2": round(float(chi2), 4),
        "p_value": round(float(p_value), 6),
        "b_a_wins": int(b),
        "c_b_wins": int(c),
        "significant_0.05": bool(p_value < 0.05),
        "significant_0.01": bool(p_value < 0.01),
    }


def wilcoxon_test(scores_a: list, scores_b: list, dim: str = "") -> dict:
    """Wilcoxon signed-rank test for paired ordinal judge scores.

    Args:
        scores_a: Scores from system A (may contain None).
        scores_b: Scores from system B (may contain None).
        dim: Label for the dimension being compared.

    Returns dict with statistic, p_value, means, significance flags.
    """
    import numpy as np
    from scipy.stats import wilcoxon
    # Drop pairs where either score is missing
    pairs = [(a, b) for a, b in zip(scores_a, scores_b)
             if a is not None and b is not None]
    if len(pairs) < 20:
        return {"note": f"Too few paired samples ({len(pairs)}) for {dim}", "n": len(pairs)}
    a_vals = [p[0] for p in pairs]
    b_vals = [p[1] for p in pairs]
    # Check if all differences are zero
    diffs = [a - b for a, b in zip(a_vals, b_vals)]
    if all(d == 0 for d in diffs):
        return {"statistic": 0.0, "p_value": 1.0, "n": len(pairs),
                "significant_0.05": False, "note": "All differences zero"}
    stat, p_value = wilcoxon(a_vals, b_vals, alternative="two-sided")
    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_value), 6),
        "n": len(pairs),
        "mean_a": round(float(np.mean(a_vals)), 3),
        "mean_b": round(float(np.mean(b_vals)), 3),
        "significant_0.05": bool(p_value < 0.05),
        "significant_0.01": bool(p_value < 0.01),
    }


def significance_stars(p: float) -> str:
    """Return significance stars for p-value."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."
