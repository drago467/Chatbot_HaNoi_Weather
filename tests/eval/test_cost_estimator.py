"""Test cost estimator (PR-C.3).

Verify rate lookup + math formulas + error handling cho missing rate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.evaluation.cost_estimator import (
    CostBreakdown,
    JudgeCostBreakdown,
    estimate_config_cost,
    estimate_judge_cost,
    estimate_total,
    load_rates,
)
from experiments.evaluation.config import load_config


@pytest.fixture
def rates():
    """Default rates từ configs/rates.yaml (chốt 2026-04-28)."""
    rates_path = Path(__file__).resolve().parents[2] / (
        "experiments/evaluation/configs/rates.yaml"
    )
    return load_rates(rates_path)


# ── Rate loading ──────────────────────────────────────────────────────────


def test_rates_load_from_yaml(rates):
    assert "qwen3-14b" in rates
    assert rates["qwen3-14b"]["input"] == 1.0
    assert rates["qwen3-14b"]["output"] == 4.0
    # GPT models moved sang sv1 (qwen-api) 2026-04-28 — cheaper 18% real VND.
    assert rates["gpt-4o"]["input"] == 1.50
    assert rates["gpt-4o-mini"]["input"] == 0.09


def test_rates_qwen_finetune_zero_cost(rates):
    """hanoi-weather-router (Colab tunnel) = $0."""
    assert rates["hanoi-weather-router"]["input"] == 0.0
    assert rates["hanoi-weather-router"]["output"] == 0.0


# ── estimate_config_cost ──────────────────────────────────────────────────


def test_c1_uses_qwen14b_agent_router_finetune_free(rates):
    """C1: agent qwen3-14b ($1/$4) + router hanoi-weather-router ($0)."""
    cfg = load_config("c1")
    bd = estimate_config_cost(cfg, dataset_size=500, rates=rates)
    assert bd.config_name == "C1"
    # Router free (hanoi-weather-router on Colab tunnel)
    assert bd.router_cost == 0.0
    # Agent prefilter post-PR-C.7: 500 × 33500 input × $1/1M + 500 × 250 × $4/1M
    expected_agent = (500 * 33500 * 1.0 + 500 * 250 * 4.0) / 1_000_000
    assert bd.agent_cost == pytest.approx(expected_agent)
    assert bd.total_cost == pytest.approx(expected_agent)


def test_c2_no_router_full27_higher_input(rates):
    """C2: no router + full_27 qwen → input ~52K tokens (cao hơn C1 prefilter)."""
    cfg = load_config("c2")
    bd = estimate_config_cost(cfg, dataset_size=500, rates=rates)
    assert bd.router_cost == 0.0  # no router
    # Agent full_27 qwen3-14b: 500 × 52000 × $1 + 500 × 250 × $4
    expected = (500 * 52000 * 1.0 + 500 * 250 * 4.0) / 1_000_000
    assert bd.agent_cost == pytest.approx(expected)


def test_c3_zero_shot_router_paid(rates):
    """C3: router = qwen3-4b zero-shot via qwen-api → có cost."""
    cfg = load_config("c3")
    bd = estimate_config_cost(cfg, dataset_size=500, rates=rates)
    # Router: 500 × 300 × $0.30 + 500 × 50 × $1.20
    expected_router = (500 * 300 * 0.30 + 500 * 50 * 1.20) / 1_000_000
    assert bd.router_cost == pytest.approx(expected_router)


def test_c5_gpt4o_mini_cheap(rates):
    """C5: gpt-4o-mini ($0.09/$0.36 trên sv1) — cheap, full_27 commercial path."""
    cfg = load_config("c5")
    bd = estimate_config_cost(cfg, dataset_size=500, rates=rates)
    # Full_27 commercial post-PR-C.7: 500 × 45000 × 0.09 + 500 × 250 × 0.36
    expected = (500 * 45000 * 0.09 + 500 * 250 * 0.36) / 1_000_000
    assert bd.agent_cost == pytest.approx(expected)
    assert bd.router_cost == 0.0


def test_c6_gemini_more_expensive_than_c5(rates):
    """C6 gemini-2.5-flash > C5 gpt-4o-mini cho cùng input/output volume."""
    bd5 = estimate_config_cost(load_config("c5"), 500, rates)
    bd6 = estimate_config_cost(load_config("c6"), 500, rates)
    assert bd6.total_cost > bd5.total_cost


def test_dataset_size_scales_linearly(rates):
    """Cost tỷ lệ tuyến tính với dataset_size."""
    cfg = load_config("c2")
    bd_500 = estimate_config_cost(cfg, 500, rates)
    bd_1000 = estimate_config_cost(cfg, 1000, rates)
    assert bd_1000.total_cost == pytest.approx(2 * bd_500.total_cost)


def test_unknown_agent_model_raises(rates):
    """Agent model không có trong rates → KeyError."""
    cfg = load_config("c1")
    cfg.agent_model_name = "nonexistent-model"
    with pytest.raises(KeyError, match="agent_model"):
        estimate_config_cost(cfg, 500, rates)


# ── estimate_judge_cost ───────────────────────────────────────────────────


def test_judge_cost_includes_faith_and_rel(rates):
    judge_bd = estimate_judge_cost(dataset_size=500, rates=rates)
    # Skip ~2.4% smalltalk faithfulness (nhưng mọi row đều có relevance)
    assert judge_bd.n_relevance_calls == 500
    assert judge_bd.n_faithfulness_calls < 500
    assert judge_bd.n_faithfulness_calls > 480  # most rows still get faith
    assert judge_bd.cost > 0


def test_judge_uses_gpt4o_rate(rates):
    """Judge cost = GPT-4o sv1 rate ($1.50 input / $6 output) — moved 2026-04-28."""
    bd = estimate_judge_cost(dataset_size=100, rates=rates)
    # Math check: 100 × ~2.4% smalltalk skip = 98 faith calls
    # faith input: 98 × 5500 = 539,000; faith output: 98 × 80 = 7,840
    # rel input: 100 × 700 = 70,000; rel output: 100 × 80 = 8,000
    # Total in: 609,000 × $1.50/M = $0.9135
    # Total out: 15,840 × $6/M = $0.0950
    # ≈ $1.01
    assert 0.9 < bd.cost < 1.2


def test_judge_cost_zero_dataset(rates):
    bd = estimate_judge_cost(dataset_size=0, rates=rates)
    assert bd.cost == 0.0
    assert bd.n_faithfulness_calls == 0
    assert bd.n_relevance_calls == 0


# ── estimate_total — full report ──────────────────────────────────────────


def test_estimate_total_aggregates_all_6(rates):
    report = estimate_total(
        config_names=["c1", "c2", "c3", "c4", "c5", "c6"],
        dataset_size=500,
        rates=rates,
    )
    assert len(report["config_breakdowns"]) == 6
    assert report["run_total"] > 0
    assert report["judge_total"] > 0
    assert report["grand_total"] == pytest.approx(
        report["run_total"] + report["judge_total"]
    )
    assert report["dataset_size"] == 500
    assert report["n_configs"] == 6


def test_estimate_total_subset_configs(rates):
    """User chỉ chạy C1+C2 thay full → chỉ tính 2 config."""
    report = estimate_total(
        config_names=["c1", "c2"],
        dataset_size=500,
        rates=rates,
    )
    assert len(report["config_breakdowns"]) == 2
    assert report["n_configs"] == 2


# ── Sanity: total estimate trong khoảng reasonable ────────────────────────


def test_total_500_row_under_500_usd(rates):
    """Sanity: 500 câu × 6 config + judge < $500 budget."""
    report = estimate_total(
        config_names=["c1", "c2", "c3", "c4", "c5", "c6"],
        dataset_size=500,
        rates=rates,
    )
    # Rough sanity bound — nếu vượt $500 thì có bug ở rate hoặc heuristic
    assert report["grand_total"] < 500, (
        f"Total estimate ${report['grand_total']:.2f} vượt $500 sanity bound — "
        "check rate config + heuristic constants."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
