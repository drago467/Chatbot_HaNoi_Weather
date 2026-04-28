"""Test judge_run CLI batch judge (PR-C.5 Step 2).

Mock LLMJudge để không gọi API thực. Verify:
- Process JSONL → output JSONL với expected fields
- skip_existing resumable
- limit=N stops correctly
- Output dir auto-create
- Per-sample flush: crash sau row N → N rows persisted (KHÔNG mất)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.evaluation.judge_run import judge_run
from experiments.evaluation.backends.judge import JudgeResult, JudgeScore


def _make_input_jsonl(path: Path, rows: list[dict]) -> Path:
    """Write rows as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _mock_judge_result(faith_score=4, rel_score=5, faith_cache_hit=False) -> JudgeResult:
    return JudgeResult(
        faithfulness=JudgeScore(
            score=faith_score, reasoning="f-reason",
            input_tokens=200, output_tokens=40, latency_ms=500,
            cache_hit=faith_cache_hit,
        ),
        relevance=JudgeScore(
            score=rel_score, reasoning="r-reason",
            input_tokens=150, output_tokens=30, latency_ms=400,
        ),
    )


@pytest.fixture
def sample_input_rows():
    """3 rows simulating run_eval_v2 output."""
    return [
        {
            "config": "C1", "question_id": "v2_0001",
            "question": "trời thế nào?", "response": "29°C nắng",
            "tool_outputs": "tool data 1",
            "intent_gold": "current_weather", "scope_gold": "city",
            "difficulty": "easy", "source": "v1_legacy",
        },
        {
            "config": "C1", "question_id": "v2_0002",
            "question": "Giá vé máy bay?", "response": "Mình là chatbot khí tượng",
            "tool_outputs": "",
            "intent_gold": "smalltalk_weather", "scope_gold": "city",
            "difficulty": "easy", "source": "v1_legacy",
        },
        {
            "config": "C1", "question_id": "v2_0003",
            "question": "ngày mai mưa?", "response": "Có mưa từ 14h-17h",
            "tool_outputs": "rain data",
            "intent_gold": "rain_query", "scope_gold": "city",
            "difficulty": "medium", "source": "v2_new",
        },
    ]


# ── Basic happy path ──────────────────────────────────────────────────────


def test_judge_run_processes_all_rows(tmp_path, sample_input_rows):
    """3 input rows → 3 output rows với expected fields."""
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "output.jsonl"

    with patch(
        "experiments.evaluation.judge_run.LLMJudge"
    ) as MockJudge:
        instance = MagicMock()
        instance.judge.return_value = _mock_judge_result()
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance

        judge_run(
            input_jsonl=input_path,
            output_jsonl=output_path,
            cache_dir=None,
        )

    output_rows = _read_jsonl(output_path)
    assert len(output_rows) == 3

    # Verify schema
    first = output_rows[0]
    assert first["config"] == "C1"
    assert first["question_id"] == "v2_0001"
    assert first["judge_faithfulness_score"] == 4
    assert first["judge_relevance_score"] == 5
    assert first["judge_input_tokens"] == 350  # 200 + 150
    assert first["judge_output_tokens"] == 70  # 40 + 30
    assert "judge_total_latency_ms" in first


# ── Resumable ─────────────────────────────────────────────────────────────


def test_judge_run_skips_existing_question_ids(tmp_path, sample_input_rows):
    """skip_existing=True + partial output → skip those qids."""
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "output.jsonl"

    # Pre-populate output với row v2_0001 + v2_0002 (resume scenario)
    pre_existing = [
        {"question_id": "v2_0001", "judge_faithfulness_score": 5},
        {"question_id": "v2_0002", "judge_faithfulness_score": 4},
    ]
    output_path.write_text(
        "\n".join(json.dumps(r) for r in pre_existing) + "\n",
        encoding="utf-8",
    )

    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge:
        instance = MagicMock()
        instance.judge.return_value = _mock_judge_result()
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance

        judge_run(
            input_jsonl=input_path,
            output_jsonl=output_path,
            cache_dir=None,
            skip_existing=True,
        )

        # Only row v2_0003 should be judged (others skipped)
        assert instance.judge.call_count == 1

    output_rows = _read_jsonl(output_path)
    assert len(output_rows) == 3  # 2 pre + 1 mới
    qids = [r["question_id"] for r in output_rows]
    assert qids == ["v2_0001", "v2_0002", "v2_0003"]


# ── Limit ─────────────────────────────────────────────────────────────────


def test_judge_run_limit_stops_after_n_new(tmp_path, sample_input_rows):
    """limit=2 với 3 input → only 2 judged."""
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "output.jsonl"

    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge:
        instance = MagicMock()
        instance.judge.return_value = _mock_judge_result()
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance

        judge_run(
            input_jsonl=input_path,
            output_jsonl=output_path,
            cache_dir=None,
            limit=2,
        )

        assert instance.judge.call_count == 2

    output_rows = _read_jsonl(output_path)
    assert len(output_rows) == 2


# ── Output dir auto-create ────────────────────────────────────────────────


def test_judge_run_creates_output_dir(tmp_path, sample_input_rows):
    """Output dir chưa có → auto-create."""
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "deeply" / "nested" / "out.jsonl"

    assert not output_path.parent.exists()

    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge:
        instance = MagicMock()
        instance.judge.return_value = _mock_judge_result()
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance

        judge_run(
            input_jsonl=input_path,
            output_jsonl=output_path,
            cache_dir=None,
        )

    assert output_path.exists()
    assert output_path.parent.exists()


# ── Per-sample flush — crash safety ───────────────────────────────────────


def test_judge_run_per_sample_flush_crash_safe(tmp_path, sample_input_rows):
    """Simulate crash sau row 2 → output JSONL có exactly 2 rows persisted.

    Critical: write per-sample + flush(), KHÔNG buffer. Crash giữa chừng
    không mất data đã judge thành công.
    """
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "output.jsonl"

    call_count = [0]

    def judge_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("Simulated crash on row 3")
        return _mock_judge_result()

    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge:
        instance = MagicMock()
        instance.judge.side_effect = judge_side_effect
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance

        with pytest.raises(RuntimeError, match="Simulated crash"):
            judge_run(
                input_jsonl=input_path,
                output_jsonl=output_path,
                cache_dir=None,
            )

    # 2 rows should be persisted (rows 1+2 succeeded before crash on row 3)
    output_rows = _read_jsonl(output_path)
    assert len(output_rows) == 2, (
        f"Per-sample flush failed: expected 2 rows persisted before crash, "
        f"got {len(output_rows)}. Buffer chưa flush?"
    )
    qids = [r["question_id"] for r in output_rows]
    assert qids == ["v2_0001", "v2_0002"]


def test_judge_run_resume_after_crash(tmp_path, sample_input_rows):
    """Sau crash test trên, re-run → resume → judge chỉ row 3 (đã có 1+2)."""
    input_path = _make_input_jsonl(tmp_path / "input.jsonl", sample_input_rows)
    output_path = tmp_path / "output.jsonl"

    # Step 1: simulate crash sau row 2
    call_count = [0]

    def judge_side_effect_crash(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("Crash row 3")
        return _mock_judge_result(faith_score=4)

    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge:
        instance = MagicMock()
        instance.judge.side_effect = judge_side_effect_crash
        instance.__enter__.return_value = instance
        MockJudge.return_value = instance
        with pytest.raises(RuntimeError):
            judge_run(input_jsonl=input_path, output_jsonl=output_path, cache_dir=None)

    # Verify 2 rows persisted
    assert len(_read_jsonl(output_path)) == 2

    # Step 2: re-run with skip_existing → only judge row 3
    with patch("experiments.evaluation.judge_run.LLMJudge") as MockJudge2:
        instance2 = MagicMock()
        instance2.judge.return_value = _mock_judge_result(faith_score=5)
        instance2.__enter__.return_value = instance2
        MockJudge2.return_value = instance2

        judge_run(
            input_jsonl=input_path,
            output_jsonl=output_path,
            cache_dir=None,
            skip_existing=True,
        )
        assert instance2.judge.call_count == 1  # Only row 3

    # Final: 3 rows total
    final = _read_jsonl(output_path)
    assert len(final) == 3
    assert {r["question_id"] for r in final} == {"v2_0001", "v2_0002", "v2_0003"}


# ── File not found ────────────────────────────────────────────────────────


def test_judge_run_missing_input_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Input JSONL not found"):
        judge_run(
            input_jsonl=tmp_path / "nonexistent.jsonl",
            output_jsonl=tmp_path / "out.jsonl",
            cache_dir=None,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
