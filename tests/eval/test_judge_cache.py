"""Test cache layer cho LLMJudge (PR-C.5 Step 2).

Verify:
- Cache key deterministic same input
- Cache write + read roundtrip
- Cache miss → API call (mock) → write file
- Cache hit → 0 API call (assert mock not called)
- Different config_name → different cache (no collision)
- Rubric version change → cache miss (auto-invalidate)
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from experiments.evaluation.backends.judge import (
    LLMJudge,
    JudgeScore,
    RUBRIC_VERSION,
    _cache_key,
    _load_cache,
    _write_cache_atomic,
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


def _make_completion(score: int, reasoning: str = "test") -> MagicMock:
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


# ── Cache key ──────────────────────────────────────────────────────────────


def test_cache_key_deterministic():
    a = _cache_key("C1", "v2_0001", "response text", "faithfulness")
    b = _cache_key("C1", "v2_0001", "response text", "faithfulness")
    assert a == b
    assert len(a) == 32  # 32-char hex prefix


def test_cache_key_differs_per_config():
    """Same question/response but different config → different key."""
    a = _cache_key("C1", "v2_0001", "response", "faithfulness")
    b = _cache_key("C2", "v2_0001", "response", "faithfulness")
    assert a != b


def test_cache_key_differs_per_dim():
    """Same context but different dim (faith vs rel) → different key."""
    a = _cache_key("C1", "v2_0001", "response", "faithfulness")
    b = _cache_key("C1", "v2_0001", "response", "relevance")
    assert a != b


def test_cache_key_differs_per_response():
    """Different response (after re-run) → different key."""
    a = _cache_key("C1", "v2_0001", "response v1", "faithfulness")
    b = _cache_key("C1", "v2_0001", "response v2", "faithfulness")
    assert a != b


# ── Atomic write + load roundtrip ──────────────────────────────────────────


def test_write_load_roundtrip(tmp_path):
    cache_path = tmp_path / "test.json"
    score = JudgeScore(
        score=4, reasoning="grounded", input_tokens=100,
        output_tokens=20, latency_ms=500.0,
    )
    _write_cache_atomic(cache_path, score)

    loaded = _load_cache(cache_path)
    assert loaded is not None
    assert loaded.score == 4
    assert loaded.reasoning == "grounded"
    assert loaded.input_tokens == 100
    assert loaded.output_tokens == 20
    assert loaded.latency_ms == 500.0
    assert loaded.cache_hit is True  # Marked as cache hit on load


def test_load_cache_returns_none_if_missing(tmp_path):
    """Cache miss → None (file not exists)."""
    assert _load_cache(tmp_path / "nonexistent.json") is None


def test_load_cache_invalidate_on_version_mismatch(tmp_path):
    """rubric_version mismatch → load returns None (auto-invalidate)."""
    cache_path = tmp_path / "old.json"
    cache_path.write_text(
        json.dumps({
            "score": 5, "reasoning": "old", "rubric_version": "v0_legacy",
        })
    )
    loaded = _load_cache(cache_path)
    assert loaded is None  # Different version → invalidate


def test_load_cache_handles_corrupt_json(tmp_path):
    """Corrupt JSON → log warn + return None."""
    cache_path = tmp_path / "corrupt.json"
    cache_path.write_text("not json {{{")
    assert _load_cache(cache_path) is None


def test_atomic_write_no_partial_corruption(tmp_path):
    """Tmp file approach: if atomic_write crashes mid-write, target file intact."""
    cache_path = tmp_path / "test.json"
    score = JudgeScore(score=3, reasoning="ok", latency_ms=100)
    _write_cache_atomic(cache_path, score)

    # No leftover .tmp file after successful atomic
    assert not (tmp_path / "test.json.tmp").exists()
    assert cache_path.exists()


# ── LLMJudge cache integration — mock API ──────────────────────────────────


def test_judge_cache_miss_calls_api_then_writes(mock_settings, tmp_path):
    """First call → API call → write cache file."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=tmp_path)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ) as mock_create:
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    assert result.faithfulness.score == 4
    assert result.faithfulness.cache_hit is False
    assert result.relevance.cache_hit is False
    assert mock_create.call_count == 2  # faith + rel both API call

    # Cache files written
    cache_files = list(tmp_path.glob("*.json"))
    assert len(cache_files) == 2  # 1 cho faith, 1 cho rel
    judge.close()


def test_judge_cache_hit_skips_api(mock_settings, tmp_path):
    """Second call (same context) → load from cache → 0 API call."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=tmp_path)

    # Run 1 — populate cache
    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=5),
    ):
        judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    # Run 2 — should hit cache, NOT call API
    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=99),  # If called, would return 99
    ) as mock_create2:
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    assert mock_create2.call_count == 0, "Cache hit should bypass API call"
    assert result.faithfulness.score == 5  # Original cached value, not 99
    assert result.faithfulness.cache_hit is True
    assert result.relevance.score == 5
    assert result.relevance.cache_hit is True
    judge.close()


def test_judge_cache_no_collision_between_configs(mock_settings, tmp_path):
    """Same question/response but C1 vs C2 → separate cache."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=tmp_path)

    # C1 → cache score=4
    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ):
        judge.judge(
            question="q", response="same response", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    # C2 (same question_id, response) → should NOT hit C1 cache
    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=2),
    ) as mock_create:
        result = judge.judge(
            question="q", response="same response", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C2", "question_id": "v2_0001"},
        )

    assert mock_create.call_count == 2  # Cache miss → API call cho C2
    assert result.faithfulness.score == 2
    assert result.faithfulness.cache_hit is False
    judge.close()


def test_judge_no_cache_dir_disables_caching(mock_settings, tmp_path):
    """cache_dir=None → no cache files created."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=None)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ):
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    assert result.faithfulness.cache_hit is False
    # tmp_path should still be empty (no cache written)
    assert list(tmp_path.glob("*.json")) == []
    judge.close()


def test_judge_no_cache_context_disables_caching(mock_settings, tmp_path):
    """cache_context=None + cache_dir set → no caching (test path)."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=tmp_path)

    with patch.object(
        judge._client.chat.completions, "create",
        return_value=_make_completion(score=4),
    ):
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            # cache_context omitted
        )

    assert result.faithfulness.cache_hit is False
    assert list(tmp_path.glob("*.json")) == []
    judge.close()


def test_judge_failed_call_not_cached(mock_settings, tmp_path):
    """API error → JudgeScore(score=None, error=...) — KHÔNG write cache."""
    cfg = load_judge_config()
    judge = LLMJudge(cfg, settings=mock_settings, cache_dir=tmp_path)

    with patch.object(
        judge._client.chat.completions, "create",
        side_effect=RuntimeError("network error"),
    ):
        result = judge.judge(
            question="q", response="r", tool_outputs="t",
            expected_intent="current_weather",
            cache_context={"config_name": "C1", "question_id": "v2_0001"},
        )

    assert result.faithfulness.score is None
    assert result.faithfulness.error is not None
    # No cache file written for failed call
    assert list(tmp_path.glob("*.json")) == []
    judge.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
