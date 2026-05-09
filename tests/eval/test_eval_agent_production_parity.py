"""PR-C.7: Verify EvalAgent matches production agent behavior.

Tests 6 production-parity components đã miss trong eval framework trước fix:

1-2. Time injection + system prompt — both `full_27` and `router_prefilter` paths
   inject fresh `now_ict()` + 246-line BASE_PROMPT + 27 TOOL_RULES (or focused
   subset + few-shot).
3.   Fresh time per call — timing không bị cache giữa queries.
4.   Placeholder resolution — `{today_date}` etc. được format(), không leak literal.
5-6. `router_scope_var` ContextVar CONDITIONAL — set khi `router_backend != "none"`,
   KHÔNG set cho NoneRouter (C2/C5/C6) để tránh break `auto_resolve_location`.
7.   `recursion_limit=15` truyền vào `agent.invoke()` (mirror `agent.py:747`).
8.   `_strip_thinking_tokens` áp lên final response (defensive cho Qwen3 leak).

Mock-only — no live LLM/HTTP/Postgres.
"""

from __future__ import annotations

import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.dispatch import router_scope_var
from experiments.evaluation.backends.agent import EvalAgent
from experiments.evaluation.backends.router.base import RouterPrediction
from experiments.evaluation.config import EvalSettings, load_config


# ── Fixtures ──────────────────────────────────────────────────────────────


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


def _mock_invocation(response_text: str = "ok"):
    return {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[{"name": "get_current_weather", "args": {}, "id": "tc1"}],
                usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            ),
            ToolMessage(content="29.5°C", tool_call_id="tc1"),
            AIMessage(
                content=response_text,
                usage_metadata={"input_tokens": 150, "output_tokens": 30, "total_tokens": 180},
            ),
        ]
    }


def _capture_prompt_callable(mock_create):
    """Extract prompt callable từ create_react_agent mock kwargs.

    `_PROMPT_KWARG` có thể là 'prompt' (langgraph >=0.2.56) hoặc 'state_modifier'
    (langgraph <0.2.56) — check cả 2.
    """
    kwargs = mock_create.call_args.kwargs
    return kwargs.get("prompt") or kwargs.get("state_modifier")


def _build_prompt_text(prompt_callable):
    """Invoke prompt callable với fake state → return SystemMessage content."""
    state = {"messages": [HumanMessage(content="trời Hà Nội thế nào?")]}
    msgs = prompt_callable(state)
    sys_msg = msgs[0]
    assert isinstance(sys_msg, SystemMessage)
    return sys_msg.content


def _extract_runtime_time(prompt_text: str) -> str | None:
    """Extract HH:MM từ RUNTIME CONTEXT [2] line `Hôm nay: ... — HH:MM (ICT/UTC+7)`.

    Tránh match `09:00 sáng mai` literal trong TOOL_RULES `get_hourly_forecast`.
    """
    m = re.search(r"Hôm nay:.*?—\s*(\d{2}:\d{2})\s*\(ICT", prompt_text)
    return m.group(1) if m else None


# Placeholders MUST be replaced by _inject_datetime() (in BASE_PROMPT only).
# {this_saturday}/{this_sunday} appear LITERAL trong TOOL_RULES `get_best_time` —
# intentional LLM instruction, KHÔNG phải format placeholder. Whitelist them.
_REQUIRED_PLACEHOLDERS = [
    "{today_weekday}", "{today_date}", "{today_time}", "{today_iso}",
    "{yesterday_weekday}", "{yesterday_date}", "{yesterday_iso}",
    "{tomorrow_weekday}", "{tomorrow_date}", "{tomorrow_iso}",
    "{week_weekday_table}",
    "{this_saturday_display}", "{this_sunday_display}",
]


# ── Test 1+2: System prompt injection cho full_27 + router_prefilter ──────


def test_full27_prompt_includes_today_date_and_tool_rules(mock_settings):
    """C2 (full_27) → prompt có today_date + Thứ + per-tool rules + no leftover {}."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    mock_create = MagicMock(return_value=mock_agent)
    with patch("experiments.evaluation.backends.agent.create_react_agent", mock_create):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            agent.run("trời Hà Nội thế nào?")

    prompt_callable = _capture_prompt_callable(mock_create)
    assert prompt_callable is not None, "prompt= kwarg phải được truyền vào create_react_agent"

    prompt_text = _build_prompt_text(prompt_callable)

    # Time injection (current ICT date in dd/mm/yyyy format)
    today = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y")
    assert today in prompt_text, f"prompt missing today_date={today}"
    assert "Thứ" in prompt_text or "Chủ Nhật" in prompt_text, "missing Vietnamese weekday"

    # Full 27 path → per-tool rules block
    assert "## Hướng dẫn per-tool" in prompt_text, "missing TOOL_RULES block"

    # Required placeholders đã được resolved (KHÔNG còn literal trong prompt).
    # Note: {this_saturday}/{this_sunday} không check vì xuất hiện literal trong
    # TOOL_RULES `get_best_time` — intentional LLM instruction.
    for ph in _REQUIRED_PLACEHOLDERS:
        assert ph not in prompt_text, f"unresolved placeholder leaked: {ph!r}"


def test_router_prefilter_prompt_focused_on_subset(mock_settings):
    """C1 (router_prefilter) → focused prompt với tool subset + few-shot."""
    cfg = load_config("c1")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    mock_create = MagicMock(return_value=mock_agent)
    with patch("experiments.evaluation.backends.agent.create_react_agent", mock_create):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            with patch.object(
                agent.router,
                "predict",
                return_value=RouterPrediction(
                    intent="current_weather", scope="city",
                    confidence=0.9, latency_ms=15.0,
                ),
            ):
                agent.run("trời thế nào?")

    prompt_text = _build_prompt_text(_capture_prompt_callable(mock_create))

    # Focused agent marker (app/agent/agent.py:268)
    assert "Ưu tiên dùng các tool sau:" in prompt_text, "missing focused tool restriction"

    # Time still injected
    today = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y")
    assert today in prompt_text


# ── Test 3: Fresh time per call ───────────────────────────────────────────


def test_prompt_injects_fresh_time_per_call(mock_settings):
    """2 successive run() với patched now_ict → 2 prompts khác nhau ở RUNTIME CONTEXT time."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    captured_times = []
    mock_create = MagicMock(return_value=mock_agent)

    def grab_time():
        callable_ = _capture_prompt_callable(mock_create)
        prompt_text = _build_prompt_text(callable_)
        captured_times.append(_extract_runtime_time(prompt_text))

    ict = pytz.timezone("Asia/Ho_Chi_Minh")
    fake_now_a = datetime(2026, 4, 28, 9, 0, tzinfo=ict)    # 09:00
    fake_now_b = datetime(2026, 4, 28, 21, 30, tzinfo=ict)  # 21:30

    with patch("experiments.evaluation.backends.agent.create_react_agent", mock_create):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            with patch("app.agent._prompt_builder.now_ict", return_value=fake_now_a):
                agent.run("q1")
                grab_time()

            mock_create.reset_mock()
            mock_create.return_value = mock_agent

            with patch("app.agent._prompt_builder.now_ict", return_value=fake_now_b):
                agent.run("q2")
                grab_time()

    assert captured_times[0] == "09:00", f"got {captured_times[0]}"
    assert captured_times[1] == "21:30", f"got {captured_times[1]}"


# ── Test 4: No unresolved placeholders ────────────────────────────────────


def test_prompt_no_unresolved_placeholders(mock_settings):
    """Build prompt cho cả full_27 + router_prefilter — required placeholders đã resolved.

    Catch missing key trong _inject_datetime() format() — vd nếu thêm placeholder
    mới vào BASE_PROMPT mà quên update format() args → literal leak vào prompt.
    """
    for cfg_name in ["c1", "c2"]:  # 1 router_prefilter + 1 full_27
        cfg = load_config(cfg_name)
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_invocation()
        mock_create = MagicMock(return_value=mock_agent)

        with patch(
            "experiments.evaluation.backends.agent.create_react_agent", mock_create
        ):
            with EvalAgent(cfg, settings=mock_settings) as agent:
                with patch.object(
                    agent.router,
                    "predict",
                    return_value=RouterPrediction(
                        intent="current_weather", scope="city",
                        confidence=0.9, latency_ms=10.0,
                    ),
                ):
                    agent.run("q")

        prompt_text = _build_prompt_text(_capture_prompt_callable(mock_create))
        for ph in _REQUIRED_PLACEHOLDERS:
            assert ph not in prompt_text, \
                f"{cfg_name} leaked required placeholder: {ph!r}"


# ── Test 5+6: router_scope_var CONDITIONAL ────────────────────────────────


def test_router_scope_var_set_for_routed_configs(mock_settings):
    """C1/C3/C4 (router_backend != 'none') → router_scope_var.set called với router scope.

    Patch module-level binding `experiments.evaluation.backends.agent.router_scope_var`
    với MagicMock để spy. Real ContextVar không bị động (ContextVar attrs read-only,
    không patch được trực tiếp).
    """
    cfg = load_config("c1")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    mock_var = MagicMock()
    mock_var.set.return_value = "fake_token"  # set() returns Token; reset(token) là OK với MagicMock

    with patch("experiments.evaluation.backends.agent.create_react_agent",
               return_value=mock_agent):
        with patch("experiments.evaluation.backends.agent.router_scope_var", mock_var):
            with EvalAgent(cfg, settings=mock_settings) as agent:
                with patch.object(
                    agent.router,
                    "predict",
                    return_value=RouterPrediction(
                        intent="current_weather", scope="ward",
                        confidence=0.9, latency_ms=10.0,
                    ),
                ):
                    agent.run("Phường Trung Hòa thế nào?")

    # Set called với scope="ward" (router output)
    mock_var.set.assert_called_once_with("ward")
    # Reset called với token returned by set() → ContextVar không leak
    mock_var.reset.assert_called_once_with("fake_token")

    # Real ContextVar (không bị patch ở scope ngoài) vẫn default None
    assert router_scope_var.get(None) is None, "real ContextVar leak"


def test_router_scope_var_NOT_set_for_none_router(mock_settings):
    """C2/C5/C6 (router_backend == 'none') → router_scope_var.set KHÔNG được called.

    Critical: blindly set scope='city' (NoneRouter default) sẽ break
    auto_resolve_location("Cầu Giấy", target_scope="city") → skip ward/district
    fuzzy → trả city-aggregated thay vì district data. Mirror production
    `stream_agent` line 692-693 (router off path không set ContextVar).
    """
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    mock_var = MagicMock()

    with patch("experiments.evaluation.backends.agent.create_react_agent",
               return_value=mock_agent):
        with patch("experiments.evaluation.backends.agent.router_scope_var", mock_var):
            with EvalAgent(cfg, settings=mock_settings) as agent:
                agent.run("trời Hà Nội thế nào?")

    mock_var.set.assert_not_called()
    mock_var.reset.assert_not_called()

    # Real ContextVar vẫn None (chưa từng bị set qua eval)
    assert router_scope_var.get(None) is None


# ── Test 7: recursion_limit=15 ────────────────────────────────────────────


def test_recursion_limit_15_passed_to_invoke(mock_settings):
    """agent.invoke() phải nhận config={'recursion_limit': 15} match production."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = _mock_invocation()

    with patch("experiments.evaluation.backends.agent.create_react_agent",
               return_value=mock_agent):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            agent.run("q")

    # Inspect kwargs của agent.invoke call
    invoke_kwargs = mock_agent.invoke.call_args.kwargs
    config = invoke_kwargs.get("config")
    # Hoặc positional arg thứ 2
    if config is None:
        args = mock_agent.invoke.call_args.args
        config = args[1] if len(args) > 1 else None

    assert config == {"recursion_limit": 15}, \
        f"recursion_limit=15 phải match production agent.py:747, got config={config}"


# ── Test 8: Strip thinking tokens ─────────────────────────────────────────


def test_thinking_tokens_stripped_from_response(mock_settings):
    """`<think>...</think>` blocks trong final AIMessage → stripped khỏi response."""
    cfg = load_config("c2")
    mock_agent = MagicMock()
    # AIMessage cuối có inline thinking blocks
    mock_agent.invoke.return_value = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[{"name": "get_current_weather", "args": {}, "id": "tc1"}],
                usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            ),
            ToolMessage(content="29°C", tool_call_id="tc1"),
            AIMessage(
                content="<think>tool returned 29°C, format response</think>Hà Nội đang 29°C, trời nắng.",
                usage_metadata={"input_tokens": 150, "output_tokens": 30, "total_tokens": 180},
            ),
        ]
    }

    with patch("experiments.evaluation.backends.agent.create_react_agent",
               return_value=mock_agent):
        with EvalAgent(cfg, settings=mock_settings) as agent:
            result = agent.run("q")

    assert "<think>" not in result.response, "thinking tokens leak: " + result.response
    assert "</think>" not in result.response
    assert result.response == "Hà Nội đang 29°C, trời nắng."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
