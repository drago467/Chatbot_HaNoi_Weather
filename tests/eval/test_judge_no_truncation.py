"""Pin test — judge MUST receive FULL tool_outputs, no truncation.

PR-C.5 fix bug `[:8000]` ở `judges.py:185` + `[:4000]` ở `helpers.py:26`.
Test này regression-pin: nếu ai re-add truncation, test FAIL ngay.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from experiments.evaluation.helpers import extract_tool_outputs


# ── Layer 1: helpers.extract_tool_outputs (legacy path) ───────────────────


def test_helpers_extract_tool_outputs_no_truncation():
    """`extract_tool_outputs` phải feed full content (PR-C.5 fix helpers.py:26)."""
    big_content = "X" * 15000
    result = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[{"name": "tool_a", "args": {}, "id": "tc1"}],
            ),
            ToolMessage(content=big_content, tool_call_id="tc1"),
            AIMessage(content="response"),
        ]
    }
    out = extract_tool_outputs(result)
    assert len(out) == 15000, (
        f"TRUNCATION BUG: expected 15000 chars, got {len(out)}. "
        "helpers.py extract_tool_outputs phải KHÔNG truncate."
    )
    assert out == big_content


def test_helpers_extract_tool_outputs_concat_two_big_tools():
    """2 tool × 10K chars each → output 20K + separator. KHÔNG truncate."""
    a = "A" * 10000
    b = "B" * 10000
    result = {
        "messages": [
            AIMessage(content="", tool_calls=[
                {"name": "t1", "args": {}, "id": "id1"},
                {"name": "t2", "args": {}, "id": "id2"},
            ]),
            ToolMessage(content=a, tool_call_id="id1"),
            ToolMessage(content=b, tool_call_id="id2"),
        ]
    }
    out = extract_tool_outputs(result)
    assert len(out) >= 20000
    assert a in out
    assert b in out


# ── Layer 2: backends.judge.LLMJudge feed full prompt ─────────────────────


@pytest.fixture
def mock_settings():
    from experiments.evaluation.config import EvalSettings
    return EvalSettings(
        QWEN_TUNNEL_API_BASE="https://tunnel.test/v1",
        QWEN_TUNNEL_API_KEY="dummy",
        QWEN_API_BASE="https://qwen.test/v1",
        QWEN_API_KEY="sk-qwen",
        OPENAI_COMPAT_API_BASE="https://compat.test/v1",
        OPENAI_COMPAT_API_KEY="sk-compat",
    )


def _make_judge_completion(score: int, reasoning: str = "test") -> MagicMock:
    """Build mock OpenAI ChatCompletion response."""
    completion = MagicMock()
    completion.choices = [
        SimpleNamespace(
            message=SimpleNamespace(
                content=f'{{"score": {score}, "reasoning": "{reasoning}"}}'
            )
        )
    ]
    completion.usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20)
    return completion


def test_judge_faithfulness_receives_full_tool_outputs(mock_settings):
    """LLMJudge phải feed FULL tool_outputs vào prompt — KHÔNG truncate.

    Critical regression pin cho thesis credibility.
    """
    from experiments.evaluation.backends.judge import LLMJudge
    from experiments.evaluation.config import load_judge_config

    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)
    big_tool_output = "Y" * 15000  # 15K chars — vượt cả 8K cũ và 4K cũ

    captured_prompts = []
    def mock_create(**kwargs):
        # Capture prompt từng call
        captured_prompts.append(kwargs["messages"][0]["content"])
        return _make_judge_completion(score=4)

    with patch.object(
        judge._client.chat.completions, "create", side_effect=mock_create
    ):
        result = judge.judge(
            question="trời thế nào?",
            response="29.5°C",
            tool_outputs=big_tool_output,
            expected_intent="current_weather",
        )

    # Verify faithfulness call received full tool_outputs
    faith_prompt = captured_prompts[0]  # faithfulness gọi trước relevance
    assert big_tool_output in faith_prompt, (
        "TRUNCATION BUG: judge prompt thiếu chars. Full 15K tool_output "
        "phải có trong faithfulness prompt."
    )

    # Verify scores parsed correctly
    assert result.faithfulness.score == 4
    assert result.relevance.score == 4
    judge.close()


def test_judge_handles_50k_tool_output_no_truncation(mock_settings):
    """50K char tool_output (edge case multi-tool 48h hourly) → full feed."""
    from experiments.evaluation.backends.judge import LLMJudge
    from experiments.evaluation.config import load_judge_config

    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)
    huge = "Z" * 50000

    captured = []
    def mock_create(**kwargs):
        captured.append(kwargs["messages"][0]["content"])
        return _make_judge_completion(score=3)

    with patch.object(
        judge._client.chat.completions, "create", side_effect=mock_create
    ):
        result = judge.judge(
            question="forecast 48h",
            response="response",
            tool_outputs=huge,
            expected_intent="hourly_forecast",
        )

    assert huge in captured[0], "50K tool_output phải feed full vào judge"
    assert result.faithfulness.score == 3
    judge.close()


# ── Layer 3: legacy judges.py also no truncate (PR-C.5 fix line 185) ──────


def test_legacy_judges_no_truncate_above_8k():
    """Legacy `experiments.evaluation.judges.llm_judge` phải KHÔNG truncate
    tool_output ở 8000 chars (bug cũ ở line 185)."""
    from experiments.evaluation import judges

    # Inspect source — không còn `[:8000]` slice trên tool_output
    import inspect
    src = inspect.getsource(judges.llm_judge)
    # Cho phép `tool_output[:8000]` xuất hiện trong COMMENT (PR note) chứ không
    # phải trong code thật. Quick heuristic: line `tool_output=tool_output[:8000]`
    # KHÔNG được tồn tại.
    assert "tool_output=tool_output[:8000]" not in src, (
        "BUG REGRESSION: judges.py line ~185 đã re-add truncate `[:8000]`. "
        "PR-C.5 đã fix — KHÔNG được revert."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
