"""Test EvalAgent + extraction helpers — mock-only, no live LLM/HTTP.

Mock LangGraph `create_react_agent` để test pipeline flow + extraction
logic không cần Colab tunnel hay sv1 live.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from experiments.evaluation.config import EvalSettings, load_config
from experiments.evaluation.backends.agent import (
    AgentResult,
    EvalAgent,
    _extract_detailed_tool_calls,
    _extract_final_response,
    _extract_token_usage,
    _extract_tool_names,
    _extract_tool_outputs_full,
)


@pytest.fixture
def mock_settings():
    return EvalSettings(
        QWEN_TUNNEL_API_BASE="https://tunnel.test/v1",
        QWEN_TUNNEL_API_KEY="dummy",
        QWEN_API_BASE="https://qwen.test/v1",
        QWEN_API_KEY="sk-qwen-test",
        OPENAI_COMPAT_API_BASE="https://compat.test/v1",
        OPENAI_COMPAT_API_KEY="sk-compat-test",
    )


# ── Extraction helpers ────────────────────────────────────────────────────


def test_extract_final_response_picks_last_ai_message():
    messages = [
        HumanMessage(content="hỏi gì đó"),
        AIMessage(
            content="",
            tool_calls=[{"name": "get_current_weather", "args": {}, "id": "tc1"}],
        ),
        ToolMessage(content="29.5°C", tool_call_id="tc1"),
        AIMessage(content="Hà Nội đang 29.5°C"),
    ]
    assert _extract_final_response(messages) == "Hà Nội đang 29.5°C"


def test_extract_final_response_empty_if_no_ai():
    messages = [HumanMessage(content="xyz")]
    assert _extract_final_response(messages) == ""


def test_extract_tool_names_collects_all_calls():
    messages = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "get_current_weather", "args": {}, "id": "tc1"},
                {"name": "get_rain_timeline", "args": {}, "id": "tc2"},
            ],
        ),
        ToolMessage(content="data1", tool_call_id="tc1"),
        ToolMessage(content="data2", tool_call_id="tc2"),
        AIMessage(content="response"),
    ]
    assert _extract_tool_names(messages) == [
        "get_current_weather",
        "get_rain_timeline",
    ]


def test_extract_tool_outputs_full_no_truncation():
    """CRITICAL: 15K char tool output phải feed full vào judge — không drop char."""
    big_output = "x" * 15000
    messages = [
        AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "tc1"}]),
        ToolMessage(content=big_output, tool_call_id="tc1"),
    ]
    full = _extract_tool_outputs_full(messages)
    assert len(full) == 15000, f"Expected 15000, got {len(full)} (TRUNCATION BUG)"
    assert full == big_output


def test_extract_tool_outputs_concatenates_multiple():
    messages = [
        AIMessage(content="", tool_calls=[
            {"name": "t1", "args": {}, "id": "id1"},
            {"name": "t2", "args": {}, "id": "id2"},
        ]),
        ToolMessage(content="output A", tool_call_id="id1"),
        ToolMessage(content="output B", tool_call_id="id2"),
    ]
    out = _extract_tool_outputs_full(messages)
    assert "output A" in out
    assert "output B" in out
    assert "---" in out  # separator


def test_extract_detailed_tool_calls_pairs_args_with_outputs():
    messages = [
        AIMessage(content="", tool_calls=[
            {"name": "get_current_weather", "args": {"location": "Hà Nội"}, "id": "tc1"},
        ]),
        ToolMessage(content="29°C", tool_call_id="tc1"),
    ]
    calls = _extract_detailed_tool_calls(messages)
    assert len(calls) == 1
    assert calls[0]["name"] == "get_current_weather"
    assert calls[0]["input"] == {"location": "Hà Nội"}  # full dict, not stringified
    assert calls[0]["output"] == "29°C"


def test_extract_token_usage_sums_multiple_ai_messages():
    """Multi-step ReAct: nhiều AIMessage → cộng dồn token."""
    messages = [
        AIMessage(
            content="step1",
            usage_metadata={"input_tokens": 100, "output_tokens": 30, "total_tokens": 130},
        ),
        AIMessage(
            content="step2",
            usage_metadata={"input_tokens": 150, "output_tokens": 50, "total_tokens": 200},
        ),
    ]
    in_tok, out_tok = _extract_token_usage(messages)
    assert in_tok == 250
    assert out_tok == 80


def test_extract_token_usage_zero_if_no_metadata():
    messages = [AIMessage(content="no meta")]
    in_tok, out_tok = _extract_token_usage(messages)
    assert in_tok == 0
    assert out_tok == 0


# ── EvalAgent flow — mock create_react_agent ──────────────────────────────


def _mock_invocation(response_text: str, tool_name: str = "get_current_weather"):
    """Build mock LangGraph invocation result với 1 tool call."""
    return {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": {}, "id": "tc1"}],
                usage_metadata={
                    "input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
                },
            ),
            ToolMessage(content="29.5°C ngày hôm nay", tool_call_id="tc1"),
            AIMessage(
                content=response_text,
                usage_metadata={
                    "input_tokens": 150, "output_tokens": 30, "total_tokens": 180,
                },
            ),
        ]
    }


def test_eval_agent_c2_runs_successfully(mock_settings):
    """C2: NoneRouter + qwen-api agent + full_27 tools → AgentResult success."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation("Hà Nội 29.5°C, trời nắng")

    with patch(
        "experiments.evaluation.backends.agent.create_react_agent",
        return_value=mock_agent,
    ):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            result = agent.run("trời Hà Nội thế nào?")

    assert result.success is True
    assert result.error is None
    assert result.response == "Hà Nội 29.5°C, trời nắng"
    assert result.tools_called == ["get_current_weather"]
    assert "29.5°C" in result.tool_outputs
    assert result.input_tokens == 250  # 100 + 150
    assert result.output_tokens == 50  # 20 + 30
    assert result.tool_subset_size == 27  # full_27
    assert result.router_intent is None  # NoneRouter
    assert result.total_latency_ms > 0


def test_eval_agent_c5_uses_qwen_api_gateway(mock_settings):
    """C5: gpt-4o-mini via qwen-api (sv1, cost-optimal 2026-04-28).

    Moved từ openai-compat (gpt1) sang qwen-api (sv1) — sv1 cheaper 18% real VND.
    """
    cfg = load_config("c5")
    with EvalAgent(cfg, settings=mock_settings) as agent:
        assert agent._agent_gateway.base_url == "https://qwen.test/v1"
        assert agent._agent_gateway.api_key == "sk-qwen-test"


def test_eval_agent_chat_model_qwen_thinking_flag(mock_settings):
    """Qwen agent → enable_thinking flag set theo config.agent_thinking.

    ChatOpenAI lift `extra_body` thành top-level field (langchain-openai 0.3+).
    """
    cfg_thinking_on = load_config("c1")  # thinking=True
    with EvalAgent(cfg_thinking_on, settings=mock_settings) as agent:
        model = agent._build_chat_model()
        assert getattr(model, "extra_body", {}).get("enable_thinking") is True

    cfg_thinking_off = load_config("c4")  # thinking=False
    with EvalAgent(cfg_thinking_off, settings=mock_settings) as agent:
        model = agent._build_chat_model()
        assert getattr(model, "extra_body", {}).get("enable_thinking") is False


def test_eval_agent_chat_model_gpt_no_thinking_flag(mock_settings):
    """gpt-4o-mini → KHÔNG có extra_body (chỉ Qwen mới cần)."""
    cfg = load_config("c5")
    with EvalAgent(cfg, settings=mock_settings) as agent:
        model = agent._build_chat_model()
        # extra_body có thể None hoặc empty dict — đều OK miễn không có enable_thinking
        eb = getattr(model, "extra_body", None) or {}
        assert "enable_thinking" not in eb


def test_eval_agent_handles_invocation_error(mock_settings):
    """Agent.invoke raises → AgentResult success=False, error captured."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = RuntimeError("connection refused to upstream")

    with patch(
        "experiments.evaluation.backends.agent.create_react_agent",
        return_value=mock_agent,
    ):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            result = agent.run("xyz")

    assert result.success is False
    assert "connection refused" in result.error
    assert result.error_category == "network"
    assert result.tools_called == []
    assert result.tool_outputs == ""


def test_eval_agent_router_prefilter_uses_subset(mock_settings):
    """C1 (router_prefilter) → tool_subset_size < 27 nếu router predict intent."""
    cfg = load_config("c1")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation("response")

    # Mock router predict → return current_weather intent
    from experiments.evaluation.backends.router.base import RouterPrediction

    with patch(
        "experiments.evaluation.backends.agent.create_react_agent",
        return_value=mock_agent,
    ):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            with patch.object(
                agent.router,
                "predict",
                return_value=RouterPrediction(
                    intent="current_weather", scope="city", confidence=0.9, latency_ms=15.0,
                ),
            ):
                result = agent.run("trời thế nào?")

    assert result.router_intent == "current_weather"
    assert result.router_confidence == 0.9
    assert result.router_latency_ms == 15.0
    assert result.tool_subset_size < 27  # prefiltered
    assert result.tool_subset_size > 0


def test_eval_agent_router_no_intent_falls_back_full_27(mock_settings):
    """Router predict intent=None (low conf) → fallback full 27 tools."""
    cfg = load_config("c1")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation("response")

    from experiments.evaluation.backends.router.base import RouterPrediction

    with patch(
        "experiments.evaluation.backends.agent.create_react_agent",
        return_value=mock_agent,
    ):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            with patch.object(
                agent.router,
                "predict",
                return_value=RouterPrediction(
                    intent=None, scope="city", confidence=0.0, latency_ms=10.0,
                    fallback_reason="parse_error",
                ),
            ):
                result = agent.run("xyz")

    assert result.router_intent is None
    assert result.router_fallback_reason == "parse_error"
    assert result.tool_subset_size == 27  # fallback full_27


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
