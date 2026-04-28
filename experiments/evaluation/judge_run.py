"""CLI batch judge — read run_results JSONL, judge từng row, write judge_results JSONL.

Per-sample flush: mỗi judge call success → write line + flush → crash KHÔNG mất data.
Resumable: `skip_existing=True` đọc question_ids đã trong output → skip.

Usage:
    python -m experiments.evaluation \\
        --judge-input data/evaluation/v2/run_results/c1_20260428_103000.jsonl

    # Custom output:
    python -m experiments.evaluation \\
        --judge-input ...c1_run.jsonl \\
        --judge-output ...c1_judge.jsonl \\
        --limit 50
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from experiments.evaluation.backends.judge import LLMJudge
from experiments.evaluation.config import JudgeConfig, load_judge_config

logger = logging.getLogger(__name__)


_DEFAULT_CACHE_DIR = Path(".cache/judge")


def judge_run(
    input_jsonl: Path,
    output_jsonl: Optional[Path] = None,
    judge_config: Optional[JudgeConfig] = None,
    cache_dir: Optional[Path] = _DEFAULT_CACHE_DIR,
    limit: Optional[int] = None,
    skip_existing: bool = True,
) -> Path:
    """Batch judge run_results JSONL → judge_results JSONL.

    Args:
        input_jsonl: Output từ `run_eval_v2` (1 row/question với response, tools_called, ...).
        output_jsonl: Output path. Default = input.with_suffix(".judge.jsonl").
        judge_config: Override JudgeConfig. Default load từ `configs/judge.yaml`.
        cache_dir: Cache `.cache/judge/`. None → no caching.
        limit: Stop sau N row mới (resumed rows không count).
        skip_existing: Resumable — skip question_ids đã có trong output.

    Returns:
        Path tới output JSONL.
    """
    input_jsonl = Path(input_jsonl)
    if not input_jsonl.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")

    if output_jsonl is None:
        output_jsonl = input_jsonl.with_suffix(".judge.jsonl")
    output_jsonl = Path(output_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    judge_config = judge_config or load_judge_config()

    # Load existing question_ids cho resume
    existing_qids: set[str] = set()
    if skip_existing and output_jsonl.exists():
        with output_jsonl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    qid = row.get("question_id")
                    if qid:
                        existing_qids.add(qid)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed line in existing output")

    # Read input rows
    input_rows = []
    with input_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            input_rows.append(json.loads(line))

    print(f"Input: {input_jsonl} ({len(input_rows)} rows)")
    print(f"Output: {output_jsonl}")
    if existing_qids:
        print(f"Resume: skip {len(existing_qids)} đã có trong output")
    print(f"Cache: {cache_dir if cache_dir else 'DISABLED'}")
    print(f"Judge model: {judge_config.judge_model_name}")
    print()

    n_judged = 0
    n_skipped = 0
    n_cache_hits = 0
    total_in_tok = 0
    total_out_tok = 0

    # Open output append mode (resume) — flush per row
    mode = "a" if existing_qids else "w"
    with LLMJudge(judge_config, cache_dir=cache_dir) as judge, \
            output_jsonl.open(mode, encoding="utf-8", buffering=1) as f_out:
        for i, row in enumerate(input_rows, 1):
            qid = row.get("question_id", f"row_{i}")

            if qid in existing_qids:
                n_skipped += 1
                continue

            if limit is not None and n_judged >= limit:
                print(f"Reached --limit {limit}, stopping.")
                break

            config_name = row.get("config", "unknown")
            question = row.get("question", "")
            response = row.get("response", "")
            tool_outputs = row.get("tool_outputs", "")
            expected_intent = row.get("intent_gold")

            judge_result = judge.judge(
                question=question,
                response=response,
                tool_outputs=tool_outputs,
                expected_intent=expected_intent,
                cache_context={"config_name": config_name, "question_id": qid},
            )

            faith = judge_result.faithfulness
            rel = judge_result.relevance

            out_row = {
                "config": config_name,
                "question_id": qid,
                "question": question,
                "response": response,
                "intent_gold": expected_intent,
                "scope_gold": row.get("scope_gold"),
                "difficulty": row.get("difficulty"),
                "source": row.get("source"),
                "judge_faithfulness_score": faith.score,
                "judge_faithfulness_reasoning": faith.reasoning,
                "judge_faithfulness_cache_hit": faith.cache_hit,
                "judge_faithfulness_error": faith.error,
                "judge_relevance_score": rel.score,
                "judge_relevance_reasoning": rel.reasoning,
                "judge_relevance_cache_hit": rel.cache_hit,
                "judge_relevance_error": rel.error,
                "judge_input_tokens": judge_result.total_input_tokens,
                "judge_output_tokens": judge_result.total_output_tokens,
                "judge_total_latency_ms": round(judge_result.total_latency_ms, 2),
            }
            f_out.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            f_out.flush()  # Per-sample flush — crash safe

            n_judged += 1
            if faith.cache_hit:
                n_cache_hits += 1
            if rel.cache_hit:
                n_cache_hits += 1
            total_in_tok += judge_result.total_input_tokens
            total_out_tok += judge_result.total_output_tokens

            faith_s = faith.score if faith.score is not None else "-"
            rel_s = rel.score if rel.score is not None else "-"
            cache_marker = " [CACHE]" if (faith.cache_hit or rel.cache_hit) else ""
            print(
                f"[{i}/{len(input_rows)}] {qid} → faith={faith_s} rel={rel_s} "
                f"({judge_result.total_latency_ms:.0f}ms){cache_marker}"
            )

    print()
    print("=" * 60)
    print(f"DONE — judged {n_judged} rows (skipped {n_skipped} resumed)")
    print(f"  Cache hits: {n_cache_hits} (out of {n_judged * 2} dim calls)")
    print(f"  Tokens: in={total_in_tok:,} out={total_out_tok:,}")
    print(f"  Output: {output_jsonl}")
    return output_jsonl
