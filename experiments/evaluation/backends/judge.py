"""LLM-as-Judge backend cho 6-config eval (PR-C.5).

Faithfulness anchor `tool_outputs` (RAGAS pattern, Es et al. 2024):
split response → atomic claims → check supported by tool_outputs.

Relevance anchor `question`: response có giải quyết câu hỏi không.

CRITICAL: KHÔNG truncate `tool_outputs` khi feed vào judge prompt — bug cũ
ở `judges.py:185` (`[:8000]`) + `helpers.py:26` (`[:4000]`) đã fix ở PR-C.5.

Edge case: smalltalk (off-topic) skip faithfulness vì không có claim
weather để check — chỉ score relevance.

Step 2 (PR-C.5): file-based cache (`.cache/judge/{key}.json`) để judge run
3000 row idempotent. Write per-sample atomic (os.replace). Skip cache nếu
`cache_dir=None` (test path) hoặc `cache_context=None`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from openai import OpenAI

from experiments.evaluation.config import (
    EvalSettings,
    JudgeConfig,
    get_eval_settings,
    load_judge_config,
)

logger = logging.getLogger(__name__)


_DEFAULT_RUBRIC_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Cache invalidation: bump khi rubric prompt change → tự động miss cache cũ.
RUBRIC_VERSION = "v1"


@dataclass
class JudgeScore:
    """1 dim score (faithfulness hoặc relevance)."""

    score: Optional[int]  # 1-5; None nếu skip (vd smalltalk faithfulness)
    reasoning: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    cache_hit: bool = False  # PR-C.5 Step 2 — True nếu loaded từ cache file


@dataclass
class JudgeResult:
    """Output 1 lần judge cho 1 (config, question, response) row."""

    faithfulness: JudgeScore
    relevance: JudgeScore

    @property
    def total_input_tokens(self) -> int:
        return self.faithfulness.input_tokens + self.relevance.input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self.faithfulness.output_tokens + self.relevance.output_tokens

    @property
    def total_latency_ms(self) -> float:
        return self.faithfulness.latency_ms + self.relevance.latency_ms


class LLMJudge:
    """Wrap OpenAI-compat client cho GPT-4o judge.

    Usage:
        from experiments.evaluation.config import load_judge_config
        cfg = load_judge_config()
        with LLMJudge(cfg) as judge:
            result = judge.judge(
                question="...", response="...",
                tool_outputs="...", expected_intent="current_weather",
            )
            print(result.faithfulness.score, result.relevance.score)
    """

    def __init__(
        self,
        config: JudgeConfig,
        settings: Optional[EvalSettings] = None,
        rubric_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.config = config
        self.settings = settings or get_eval_settings()
        gateway = self.settings.resolve(config.judge_gateway)
        self._client = OpenAI(base_url=gateway.base_url, api_key=gateway.api_key)
        self.cache_dir = cache_dir  # None → no caching (test path)

        rubric_dir = rubric_dir or _DEFAULT_RUBRIC_DIR
        self._faithfulness_rubric = (rubric_dir / "judge_faithfulness_v1.md").read_text(
            encoding="utf-8"
        )
        self._relevance_rubric = (rubric_dir / "judge_relevance_v1.md").read_text(
            encoding="utf-8"
        )

    def judge(
        self,
        question: str,
        response: str,
        tool_outputs: str,
        expected_intent: Optional[str] = None,
        cache_context: Optional[dict[str, str]] = None,
    ) -> JudgeResult:
        """Score (faithfulness, relevance) cho 1 response.

        `expected_intent='smalltalk_weather'` → skip faithfulness (no claim
        to check, theo memory feedback_smalltalk_vs_abstain).

        `cache_context={"config_name": "C1", "question_id": "v2_0001"}` →
        enable file cache. None → no caching. Cache hit short-circuits API call.
        """
        is_smalltalk = expected_intent == "smalltalk_weather"

        if is_smalltalk:
            faithfulness = JudgeScore(
                score=None,
                reasoning="Skipped: smalltalk has no weather claim to ground.",
            )
        else:
            faithfulness = self._judge_with_cache(
                dim_name="faithfulness",
                response=response,
                cache_context=cache_context,
                call_fn=lambda: self._call_faithfulness(
                    question, response, tool_outputs
                ),
            )

        relevance = self._judge_with_cache(
            dim_name="relevance",
            response=response,
            cache_context=cache_context,
            call_fn=lambda: self._call_relevance(question, response),
        )
        return JudgeResult(faithfulness=faithfulness, relevance=relevance)

    def _judge_with_cache(
        self,
        dim_name: str,
        response: str,
        cache_context: Optional[dict[str, str]],
        call_fn: Callable[[], JudgeScore],
    ) -> JudgeScore:
        """Wrap call_fn với cache check + atomic write.

        No-op (passthrough) nếu cache_dir=None hoặc cache_context=None.
        """
        cache_path: Optional[Path] = None
        if self.cache_dir is not None and cache_context is not None:
            key = _cache_key(
                config_name=cache_context["config_name"],
                question_id=cache_context["question_id"],
                response=response,
                dim_name=dim_name,
            )
            cache_path = self.cache_dir / f"{key}.json"
            cached = _load_cache(cache_path)
            if cached is not None:
                logger.debug("Cache HIT %s/%s", cache_context["question_id"], dim_name)
                return cached

        score = call_fn()

        # Chỉ cache khi success (score≠None, error=None) — KHÔNG cache failed call
        if cache_path is not None and score.score is not None and score.error is None:
            _write_cache_atomic(cache_path, score)

        return score

    def _call_faithfulness(
        self, question: str, response: str, tool_outputs: str
    ) -> JudgeScore:
        prompt = self._faithfulness_rubric.format(
            question=question, response=response, tool_outputs=tool_outputs,
        )
        return self._call_judge(prompt, dim_name="faithfulness")

    def _call_relevance(self, question: str, response: str) -> JudgeScore:
        prompt = self._relevance_rubric.format(
            question=question, response=response,
        )
        return self._call_judge(prompt, dim_name="relevance")

    def _call_judge(self, prompt: str, dim_name: str) -> JudgeScore:
        """Common path — POST to /v1/chat/completions với JSON mode."""
        start = time.time()
        try:
            completion = self._client.chat.completions.create(
                model=self.config.judge_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.judge_temperature,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.warning("Judge %s API error: %s", dim_name, e)
            return JudgeScore(
                score=None, reasoning="", latency_ms=latency,
                error=f"api_error: {type(e).__name__}: {e}",
            )

        latency = (time.time() - start) * 1000
        try:
            content = completion.choices[0].message.content or ""
            parsed = _parse_judge_response(content)
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            logger.warning("Judge %s parse error: %s, raw=%r", dim_name, e, content[:200])
            return JudgeScore(
                score=None, reasoning="", latency_ms=latency,
                error=f"parse_error: {type(e).__name__}",
            )

        usage = getattr(completion, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0

        return JudgeScore(
            score=parsed["score"],
            reasoning=parsed["reasoning"],
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency,
        )

    def close(self) -> None:
        """OpenAI client tự cleanup. Reserve hook cho cache layer ở Step 2."""
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


# ── Cache layer (PR-C.5 Step 2) ───────────────────────────────────────────


def _cache_key(
    config_name: str, question_id: str, response: str, dim_name: str
) -> str:
    """Compute deterministic cache key.

    Includes RUBRIC_VERSION → bump version → auto-invalidate.
    """
    response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()[:16]
    key_str = f"{config_name}|{question_id}|{response_hash}|{dim_name}|{RUBRIC_VERSION}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


def _load_cache(cache_path: Path) -> Optional[JudgeScore]:
    """Load cached JudgeScore từ file. Return None nếu miss/invalid/version-mismatch."""
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Cache load failed %s: %s", cache_path.name, e)
        return None

    if data.get("rubric_version") != RUBRIC_VERSION:
        logger.debug("Cache version mismatch %s → invalidate", cache_path.name)
        return None

    try:
        return JudgeScore(
            score=data["score"],
            reasoning=data["reasoning"],
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            latency_ms=data.get("latency_ms", 0.0),
            cache_hit=True,
        )
    except KeyError as e:
        logger.warning("Cache schema invalid %s: missing %s", cache_path.name, e)
        return None


def _write_cache_atomic(cache_path: Path, score: JudgeScore) -> None:
    """Atomic write — tmp file + os.replace.

    Crash giữa write KHÔNG để lại corrupted cache (vì replace atomic
    trên cả POSIX + Windows).
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "score": score.score,
        "reasoning": score.reasoning,
        "input_tokens": score.input_tokens,
        "output_tokens": score.output_tokens,
        "latency_ms": score.latency_ms,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": RUBRIC_VERSION,
    }
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, cache_path)


def _parse_judge_response(content: str) -> dict[str, Any]:
    """Parse JSON từ judge response → {score: int, reasoning: str}.

    Robust: strip markdown fences nếu model vô tình thêm.
    """
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(line for line in lines if not line.startswith("```"))
        content = content.strip()

    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected dict, got {type(parsed).__name__}")

    score = parsed.get("score")
    if not isinstance(score, int) or not (1 <= score <= 5):
        raise ValueError(f"Invalid score: {score!r} (expect int 1-5)")

    reasoning = parsed.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    return {"score": score, "reasoning": reasoning}
