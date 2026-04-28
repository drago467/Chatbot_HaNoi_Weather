"""Test LLMJudge backend — score parsing, smalltalk skip, error handling.

Mock OpenAI client cho stable test (no live API call).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from experiments.evaluation.backends.judge import (
    JudgeResult,
    JudgeScore,
    LLMJudge,
    _parse_judge_response,
)
from experiments.evaluation.config import EvalSettings, load_judge_config


@pytest.fixture
def mock_settings():
    return EvalSettings(
        QWEN_TUNNEL_API_BASE="https://tunnel.test/v1",
        QWEN_TUNNEL_API_KEY="dummy",
        QWEN_API_BASE="https://qwen.test/v1",
        QWEN_API_KEY="sk-qwen",
        OPENAI_COMPAT_API_BASE="https://compat.test/v1",
        OPENAI_COMPAT_API_KEY="sk-compat",
    )


def _make_completion(score: int, reasoning: str = "test reasoning") -> MagicMock:
    completion = MagicMock()
    completion.choices = [
        SimpleNamespace(
            message=SimpleNamespace(
                content=f'{{"score": {score}, "reasoning": "{reasoning}"}}'
            )
        )
    ]
    completion.usage = SimpleNamespace(prompt_tokens=200, completion_tokens=40)
    return completion


# ── _parse_judge_response — JSON parsing robustness ───────────────────────


def test_parse_valid_json():
    parsed = _parse_judge_response('{"score": 4, "reasoning": "good"}')
    assert parsed["score"] == 4
    assert parsed["reasoning"] == "good"


def test_parse_strips_markdown_fences():
    fenced = '```json\n{"score": 5, "reasoning": "perfect"}\n```'
    parsed = _parse_judge_response(fenced)
    assert parsed["score"] == 5


def test_parse_invalid_score_raises():
    with pytest.raises(ValueError, match="Invalid score"):
        _parse_judge_response('{"score": 7, "reasoning": "x"}')

    with pytest.raises(ValueError, match="Invalid score"):
        _parse_judge_response('{"score": "five", "reasoning": "x"}')


def test_parse_missing_score_raises():
    with pytest.raises(ValueError, match="Invalid score"):
        _parse_judge_response('{"reasoning": "no score field"}')


def test_parse_malformed_json_raises():
    import json as _json
    with pytest.raises(_json.JSONDecodeError):
        _parse_judge_response('not json {{{')


# ── LLMJudge.judge — full flow ────────────────────────────────────────────


def test_judge_returns_2_dim_for_weather_query(mock_settings):
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ):
        result = judge.judge(
            question="trời Hà Nội thế nào?",
            response="Hà Nội 29°C, trời nắng",
            tool_outputs="nhiệt độ: 29°C\ntình trạng: nắng",
            expected_intent="current_weather",
        )

    assert isinstance(result, JudgeResult)
    assert result.faithfulness.score == 4
    assert result.relevance.score == 4
    assert result.faithfulness.reasoning == "test reasoning"
    assert result.total_input_tokens == 400  # 200 × 2 calls
    assert result.total_output_tokens == 80  # 40 × 2 calls
    judge.close()


def test_judge_smalltalk_skips_faithfulness(mock_settings):
    """smalltalk_weather → faithfulness.score=None (no claim to ground)."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=5),
    ) as mock_create:
        result = judge.judge(
            question="Giá vé máy bay Hà Nội - SG?",
            response="Mình là chatbot khí tượng, không hỗ trợ vé máy bay.",
            tool_outputs="",
            expected_intent="smalltalk_weather",
        )

    # Faithfulness skipped
    assert result.faithfulness.score is None
    assert "smalltalk" in result.faithfulness.reasoning.lower()
    # Relevance still scored
    assert result.relevance.score == 5
    # Only 1 API call (relevance, faithfulness skipped)
    assert mock_create.call_count == 1
    judge.close()


def test_judge_api_error_returns_none_score(mock_settings):
    """API error → JudgeScore(score=None, error='...')."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)

    with patch.object(
        judge._client.chat.completions, "create",
        side_effect=RuntimeError("Connection timeout"),
    ):
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
        )

    assert result.faithfulness.score is None
    assert "api_error" in result.faithfulness.error
    assert result.relevance.score is None
    assert "api_error" in result.relevance.error
    judge.close()


def test_judge_parse_error_returns_none_score(mock_settings):
    """Judge return malformed JSON → JudgeScore(score=None, error='parse_error')."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)

    bad_completion = MagicMock()
    bad_completion.choices = [
        SimpleNamespace(message=SimpleNamespace(content="not json {{"))
    ]
    bad_completion.usage = SimpleNamespace(prompt_tokens=100, completion_tokens=10)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=bad_completion,
    ):
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
        )

    assert result.faithfulness.score is None
    assert "parse_error" in result.faithfulness.error
    judge.close()


def test_judge_uses_openai_compat_gateway(mock_settings):
    """Judge gateway = openai-compat by default (judge.yaml)."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)
    assert str(judge._client.base_url).rstrip("/") == "https://compat.test/v1"
    judge.close()


def test_judge_score_dataclass_aggregates():
    """JudgeResult properties: total tokens + latency aggregate cả 2 dim."""
    f = JudgeScore(score=4, reasoning="x", input_tokens=100, output_tokens=20, latency_ms=300)
    r = JudgeScore(score=5, reasoning="y", input_tokens=80, output_tokens=15, latency_ms=200)
    res = JudgeResult(faithfulness=f, relevance=r)
    assert res.total_input_tokens == 180
    assert res.total_output_tokens == 35
    assert res.total_latency_ms == 500


# ── Smalltalk semantics — guard memory feedback ───────────────────────────


@pytest.mark.parametrize("intent", [
    "current_weather", "rain_query", "historical_weather", "weather_alert",
    "location_comparison", "expert_weather_param",
])
def test_judge_non_smalltalk_runs_faithfulness(mock_settings, intent):
    """Non-smalltalk intents → faithfulness được call (score not None)."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ) as mock_create:
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent=intent,
        )
    assert result.faithfulness.score == 4
    assert mock_create.call_count == 2  # Both dim called
    judge.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
