"""Test load 6 YAML config + judge.yaml + EvalConfig pydantic validation.

Pin schema cho 6 ablation config (C1..C6) — đảm bảo:
- Mỗi YAML load thành EvalConfig hợp lệ.
- 6 config có đủ ablation pair (C1 vs C2/C3/C4 + C2 vs C5/C6).
- Cross-field validation: router_backend='none' → router_gateway/model phải None.
- Invalid YAML reject đúng (tool_path='router_prefilter' với router_backend='none').
"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.evaluation.config import (
    EvalConfig,
    GatewayAlias,
    JudgeConfig,
    load_config,
    load_judge_config,
)

CONFIG_NAMES = ["c1", "c2", "c3", "c4", "c5", "c6"]


# ── Each config loads + parses ────────────────────────────────────────────


@pytest.mark.parametrize("name", CONFIG_NAMES)
def test_config_loads(name: str):
    cfg = load_config(name)
    assert cfg.name.lower() == name
    assert cfg.router_backend in ("slm_ft", "slm_zero_shot", "none")
    assert cfg.tool_path in ("router_prefilter", "full_27")


def test_judge_config_loads():
    cfg = load_judge_config()
    # Judge moved sang sv1 (qwen-api) 2026-04-28 — rẻ hơn 18% real VND.
    assert cfg.judge_gateway == GatewayAlias.qwen_api
    assert cfg.judge_model_name == "gpt-4o"
    assert cfg.judge_temperature == 0.0
    assert cfg.max_tool_output_chars is None  # CRITICAL: no truncate


# ── Concrete C1..C6 mapping (chốt 2026-04-27) ─────────────────────────────


def test_c1_baseline():
    """C1 = production (hanoi-weather-router on Colab + qwen3-14b agent thinking)."""
    cfg = load_config("c1")
    assert cfg.router_backend == "slm_ft"
    assert cfg.router_gateway == GatewayAlias.qwen_tunnel
    assert cfg.router_model_name == "hanoi-weather-router"
    assert cfg.agent_gateway == GatewayAlias.qwen_api
    assert cfg.agent_model_name == "qwen3-14b"
    assert cfg.agent_thinking is True
    assert cfg.tool_path == "router_prefilter"


def test_c2_no_router():
    """C2 = no router, full 27 tool — pair với C1 để justify router."""
    cfg = load_config("c2")
    assert cfg.router_backend == "none"
    assert cfg.router_gateway is None
    assert cfg.router_model_name is None
    assert cfg.tool_path == "full_27"


def test_c3_zero_shot_router():
    """C3 = qwen3-4b zero-shot router — pair với C1 để justify finetune."""
    cfg = load_config("c3")
    assert cfg.router_backend == "slm_zero_shot"
    assert cfg.router_model_name == "qwen3-4b"
    assert cfg.router_gateway == GatewayAlias.qwen_api  # zero-shot ở sv1 không phải Colab


def test_c4_no_thinking():
    """C4 = giống C1 nhưng tắt thinking — pair với C1 để justify thinking mode."""
    cfg = load_config("c4")
    assert cfg.router_backend == "slm_ft"
    assert cfg.agent_thinking is False
    # Còn lại giống C1
    c1 = load_config("c1")
    assert cfg.router_model_name == c1.router_model_name
    assert cfg.agent_model_name == c1.agent_model_name


def test_c5_gpt4o_mini():
    """C5 = gpt-4o-mini agent — pair với C2 để so open vs commercial.

    Moved sang qwen-api (sv1) 2026-04-28 — rẻ hơn 18% real VND so với gpt1.
    """
    cfg = load_config("c5")
    assert cfg.agent_gateway == GatewayAlias.qwen_api
    assert cfg.agent_model_name == "gpt-4o-mini"
    assert cfg.router_backend == "none"


def test_c6_gemini_flash():
    """C6 = gemini-2.5-flash agent — pair với C2 để so open vs commercial.

    sv1 (qwen-api alias) là multi-provider gateway, host cả gemini-2.5-flash.
    Không phải openai-compat (gpt1) như C5.
    """
    cfg = load_config("c6")
    assert cfg.agent_gateway == GatewayAlias.qwen_api
    assert cfg.agent_model_name == "gemini-2.5-flash"
    assert cfg.router_backend == "none"


# ── Cross-field validation: pydantic rejects invalid combos ───────────────


def test_invalid_router_none_with_gateway():
    """router_backend='none' + router_gateway='qwen-api' → ValidationError."""
    with pytest.raises(ValueError, match="router_gateway=None"):
        EvalConfig(
            name="bad",
            router_backend="none",
            router_gateway=GatewayAlias.qwen_api,
            router_model_name=None,
            agent_gateway=GatewayAlias.qwen_api,
            agent_model_name="qwen3-14b",
            agent_thinking=True,
            tool_path="full_27",
        )


def test_invalid_router_slm_without_gateway():
    """router_backend='slm_ft' + router_gateway=None → ValidationError."""
    with pytest.raises(ValueError, match="requires router_gateway"):
        EvalConfig(
            name="bad",
            router_backend="slm_ft",
            router_gateway=None,
            router_model_name="hanoi-weather-router",
            agent_gateway=GatewayAlias.qwen_api,
            agent_model_name="qwen3-14b",
            agent_thinking=True,
            tool_path="router_prefilter",
        )


def test_invalid_router_none_with_prefilter():
    """router_backend='none' + tool_path='router_prefilter' → ValidationError."""
    with pytest.raises(ValueError, match="không có router để prefilter"):
        EvalConfig(
            name="bad",
            router_backend="none",
            router_gateway=None,
            router_model_name=None,
            agent_gateway=GatewayAlias.qwen_api,
            agent_model_name="qwen3-14b",
            agent_thinking=True,
            tool_path="router_prefilter",
        )


def test_invalid_router_slm_without_model():
    """router_backend='slm_ft' + router_model_name=None → ValidationError."""
    with pytest.raises(ValueError, match="requires router_model_name"):
        EvalConfig(
            name="bad",
            router_backend="slm_ft",
            router_gateway=GatewayAlias.qwen_tunnel,
            router_model_name=None,
            agent_gateway=GatewayAlias.qwen_api,
            agent_model_name="qwen3-14b",
            agent_thinking=True,
            tool_path="router_prefilter",
        )


# ── Coverage: 4 ablation pair phải compile được ───────────────────────────


def test_ablation_pairs_consistent():
    """Verify 4 cặp ablation chính có config khớp story."""
    c1, c2, c3, c4, c5, c6 = (load_config(n) for n in CONFIG_NAMES)

    # C1 vs C2 → router value: chỉ khác router_backend + tool_path
    assert c1.agent_gateway == c2.agent_gateway
    assert c1.agent_model_name == c2.agent_model_name
    assert c1.agent_thinking == c2.agent_thinking
    assert c1.router_backend != c2.router_backend

    # C1 vs C3 → finetune value: chỉ khác router gateway/model
    assert c1.agent_model_name == c3.agent_model_name
    assert c1.tool_path == c3.tool_path
    assert c1.router_backend != c3.router_backend

    # C1 vs C4 → thinking value: chỉ khác agent_thinking
    assert c1.router_backend == c4.router_backend
    assert c1.router_model_name == c4.router_model_name
    assert c1.agent_model_name == c4.agent_model_name
    assert c1.agent_thinking != c4.agent_thinking

    # C2 vs C5/C6 → open vs commercial: cùng config trừ agent_model_name
    # Update 2026-04-28: cả C5 + C6 đều route qua qwen-api (sv1 multi-provider) —
    # cost-optimal so với gpt1. Distinction giữa C2/C5/C6 là agent_model_name.
    assert c2.router_backend == c5.router_backend == c6.router_backend
    assert c2.tool_path == c5.tool_path == c6.tool_path
    assert c2.agent_gateway == c5.agent_gateway == c6.agent_gateway  # all sv1 now
    assert c2.agent_model_name != c5.agent_model_name
    assert c2.agent_model_name != c6.agent_model_name
    assert c5.agent_model_name != c6.agent_model_name


# ── File not found ────────────────────────────────────────────────────────


def test_load_unknown_config_raises():
    with pytest.raises(FileNotFoundError):
        load_config("c99")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
