"""Test run_eval_v2 resume + flush behavior cho long run safety.

Critical cho 10h C2 full eval — crash/Colab-disconnect không mất data.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.evaluation.runner import run_eval_v2


def _mock_agent_result(qid_seed: str = "test"):
    """Build mock AgentResult."""
    from experiments.evaluation.backends.agent import AgentResult
    return AgentResult(
        question=f"q_{qid_seed}",
        response=f"response for {qid_seed}",
        tools_called=["get_current_weather"],
        tool_outputs="29°C",
        success=True,
        router_intent="current_weather",
        router_scope="city",
        router_confidence=0.9,
        router_latency_ms=10,
        agent_latency_ms=100,
        total_latency_ms=110,
        input_tokens=200,
        output_tokens=20,
        tool_subset_size=4,
    )


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@pytest.fixture
def mini_dataset(tmp_path):
    """Build 5-row CSV dataset for tests."""
    import csv
    csv_path = tmp_path / "mini_dataset.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "question", "intent", "location_scope", "difficulty", "source",
            "expected_tools", "expected_abstain", "expected_clarification",
        ])
        writer.writeheader()
        for i in range(1, 6):
            writer.writerow({
                "id": f"v2_{i:04d}",
                "question": f"câu hỏi số {i}",
                "intent": "current_weather",
                "location_scope": "city",
                "difficulty": "easy",
                "source": "v2_new",
                "expected_tools": "[]",
                "expected_abstain": "False",
                "expected_clarification": "False",
            })
    return csv_path


# ── Per-row flush ─────────────────────────────────────────────────────────


def test_run_eval_v2_per_row_flush_crash_safe(tmp_path, mini_dataset):
    """Crash sau row 3 → output JSONL có exactly 3 rows persisted."""
    output_dir = tmp_path / "run_results"
    call_count = [0]

    def agent_run_side_effect(question):
        call_count[0] += 1
        if call_count[0] == 4:
            raise RuntimeError("simulated crash on query 4")
        return _mock_agent_result(f"q{call_count[0]}")

    with patch(
        "experiments.evaluation.backends.agent.EvalAgent"
    ) as MockAgent:
        instance = MagicMock()
        instance.run.side_effect = agent_run_side_effect
        instance.__enter__.return_value = instance
        MockAgent.return_value = instance

        with pytest.raises(RuntimeError, match="simulated crash"):
            run_eval_v2(
                config_name="c2",  # No router for simplicity
                dataset_path=str(mini_dataset),
                output_dir=str(output_dir),
            )

    # Find output file
    output_files = list(output_dir.glob("*.jsonl"))
    assert len(output_files) == 1
    rows = _read_jsonl(output_files[0])
    assert len(rows) == 3, (
        f"Per-row flush failed: expected 3 rows persisted before crash on row 4, "
        f"got {len(rows)}"
    )
    assert [r["question_id"] for r in rows] == ["v2_0001", "v2_0002", "v2_0003"]


# ── Resume ────────────────────────────────────────────────────────────────


def test_run_eval_v2_resume_skips_existing_qids(tmp_path, mini_dataset):
    """Resume từ existing JSONL → skip qids đã có, judge phần còn lại."""
    existing_jsonl = tmp_path / "existing.jsonl"
    # Pre-populate với rows 1-3
    with existing_jsonl.open("w", encoding="utf-8") as f:
        for i in range(1, 4):
            f.write(json.dumps({"question_id": f"v2_{i:04d}", "config": "C2"}) + "\n")

    with patch(
        "experiments.evaluation.backends.agent.EvalAgent"
    ) as MockAgent:
        instance = MagicMock()
        instance.run.side_effect = lambda q: _mock_agent_result("resumed")
        instance.__enter__.return_value = instance
        MockAgent.return_value = instance

        run_eval_v2(
            config_name="c2",
            dataset_path=str(mini_dataset),
            resume_from=existing_jsonl,
        )
        # Only rows 4 + 5 should be judged
        assert instance.run.call_count == 2

    rows = _read_jsonl(existing_jsonl)
    assert len(rows) == 5  # 3 pre + 2 mới
    qids = [r["question_id"] for r in rows]
    assert qids == ["v2_0001", "v2_0002", "v2_0003", "v2_0004", "v2_0005"]


def test_run_eval_v2_resume_after_crash_completes_all(tmp_path, mini_dataset):
    """Crash row 3 → resume → all 5 rows persist."""
    output_dir = tmp_path / "run_results"
    call_count = [0]

    def agent_run_crash_then_succeed(question):
        call_count[0] += 1
        if call_count[0] == 3:
            raise RuntimeError("crash row 3")
        return _mock_agent_result(f"q{call_count[0]}")

    with patch(
        "experiments.evaluation.backends.agent.EvalAgent"
    ) as MockAgent:
        instance = MagicMock()
        instance.run.side_effect = agent_run_crash_then_succeed
        instance.__enter__.return_value = instance
        MockAgent.return_value = instance

        with pytest.raises(RuntimeError):
            run_eval_v2(
                config_name="c2",
                dataset_path=str(mini_dataset),
                output_dir=str(output_dir),
            )

    crash_file = list(output_dir.glob("*.jsonl"))[0]
    assert len(_read_jsonl(crash_file)) == 2

    # Resume — chạy tiếp từ qid 3
    call_count[0] = 0  # reset; new run

    with patch(
        "experiments.evaluation.backends.agent.EvalAgent"
    ) as MockAgent2:
        instance2 = MagicMock()
        instance2.run.side_effect = lambda q: _mock_agent_result("resumed")
        instance2.__enter__.return_value = instance2
        MockAgent2.return_value = instance2

        run_eval_v2(
            config_name="c2",
            dataset_path=str(mini_dataset),
            resume_from=crash_file,
        )
        # 3 queries judge (rows 3, 4, 5) — 2 đã có
        assert instance2.run.call_count == 3

    final = _read_jsonl(crash_file)
    assert len(final) == 5
    assert {r["question_id"] for r in final} == {f"v2_{i:04d}" for i in range(1, 6)}


def test_run_eval_v2_fresh_creates_timestamped_file(tmp_path, mini_dataset):
    """Default mode (no resume) → tạo file timestamped trong output_dir."""
    output_dir = tmp_path / "run_results"

    with patch("experiments.evaluation.backends.agent.EvalAgent") as MockAgent:
        instance = MagicMock()
        instance.run.side_effect = lambda q: _mock_agent_result("fresh")
        instance.__enter__.return_value = instance
        MockAgent.return_value = instance

        output_path = run_eval_v2(
            config_name="c2",
            dataset_path=str(mini_dataset),
            output_dir=str(output_dir),
        )

    assert output_path.parent == output_dir
    assert output_path.name.startswith("c2_")
    assert output_path.name.endswith(".jsonl")
    assert len(_read_jsonl(output_path)) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
