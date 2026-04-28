"""Shared HTTP logic cho SLM router backends (slm_zero_shot + slm_ft).

Cả 2 backend gọi qua OpenAI-compat `/v1/chat/completions` với prompt
classification → JSON output `{intent, scope, confidence}`. Khác biệt
duy nhất: gateway endpoint + model_name.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

from experiments.evaluation.backends.router.base import RouterBackend, RouterPrediction

logger = logging.getLogger(__name__)


_VALID_INTENTS = {
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
}
_VALID_SCOPES = {"city", "district", "ward"}


_SYSTEM_PROMPT = """Bạn là classifier câu hỏi thời tiết tiếng Việt (Hà Nội domain).

Phân loại câu hỏi vào:
- intent: 1 trong 15 nhãn (current_weather, hourly_forecast, daily_forecast, weather_overview, rain_query, temperature_query, wind_query, humidity_fog_query, historical_weather, location_comparison, activity_weather, expert_weather_param, weather_alert, seasonal_context, smalltalk_weather)
- scope: city | district | ward
- confidence: 0.0-1.0

Output JSON STRICT (không thêm markdown):
{"intent": "...", "scope": "...", "confidence": 0.85}"""


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class _SLMRouterBase(RouterBackend):
    """Common base — concrete subclass chỉ khác base_url + model_name.

    Retry logic: exponential backoff cho 429 (rate limit) + 5xx (server transient).
    Non-retryable (4xx other) → fallback ngay với fallback_reason.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_initial_wait: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_initial_wait = retry_initial_wait
        self._client = httpx.Client(timeout=timeout)

    def predict(self, query: str) -> RouterPrediction:
        # Router là classifier (output JSON ngắn) — KHÔNG cần thinking.
        # sv1 qwen3-4b BẮT BUỘC `enable_thinking=false` cho non-streaming
        # (gateway return 429 nếu thiếu). Colab Ollama tolerate flag.
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "extra_body": {"enable_thinking": False},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.time()
        resp = None
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                break  # success
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in _RETRYABLE_STATUS and attempt < self.max_retries:
                    wait = self.retry_initial_wait * (2 ** attempt)
                    logger.warning(
                        "SLM router HTTP %d (attempt %d/%d), retrying in %.1fs",
                        status, attempt + 1, self.max_retries, wait,
                    )
                    time.sleep(wait)
                    continue
                # Non-retryable or exhausted
                latency_ms = (time.time() - start) * 1000
                logger.warning("SLM router HTTP %d (final): %s", status, e)
                return RouterPrediction(
                    intent=None,
                    latency_ms=latency_ms,
                    fallback_reason=f"http_{status}_after_{attempt + 1}_attempts",
                )
            except httpx.HTTPError as e:
                # Connection/timeout errors — also retry (transient)
                if attempt < self.max_retries:
                    wait = self.retry_initial_wait * (2 ** attempt)
                    logger.warning(
                        "SLM router %s (attempt %d/%d), retrying in %.1fs",
                        type(e).__name__, attempt + 1, self.max_retries, wait,
                    )
                    time.sleep(wait)
                    last_error = str(e)
                    continue
                latency_ms = (time.time() - start) * 1000
                logger.warning("SLM router %s (final): %s", type(e).__name__, e)
                return RouterPrediction(
                    intent=None,
                    latency_ms=latency_ms,
                    fallback_reason=f"http_error: {type(e).__name__}",
                )

        if resp is None:
            # All retries exhausted với connection errors
            latency_ms = (time.time() - start) * 1000
            return RouterPrediction(
                intent=None,
                latency_ms=latency_ms,
                fallback_reason=f"http_error_exhausted: {last_error}",
            )

        latency_ms = (time.time() - start) * 1000
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            parsed = _parse_classification(content)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
            logger.warning("SLM router parse error: %s, raw=%r", e, data)
            return RouterPrediction(
                intent=None,
                latency_ms=latency_ms,
                fallback_reason=f"parse_error: {type(e).__name__}",
            )

        return RouterPrediction(
            intent=parsed["intent"],
            scope=parsed["scope"],
            confidence=parsed["confidence"],
            latency_ms=latency_ms,
        )

    def close(self) -> None:
        self._client.close()


def _parse_classification(content: str) -> dict:
    """Parse JSON content từ SLM response → validated dict.

    Robust: strip markdown code fences nếu model vô tình thêm.
    """
    content = content.strip()
    if content.startswith("```"):
        # Strip ```json ... ``` fences
        lines = content.split("\n")
        content = "\n".join(line for line in lines if not line.startswith("```"))
        content = content.strip()

    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected dict, got {type(parsed).__name__}")

    intent = parsed.get("intent")
    if intent not in _VALID_INTENTS:
        raise ValueError(f"Invalid intent: {intent!r}")

    scope = parsed.get("scope", "city")
    if scope not in _VALID_SCOPES:
        raise ValueError(f"Invalid scope: {scope!r}")

    confidence = float(parsed.get("confidence", 0.0))
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"Invalid confidence: {confidence}")

    return {"intent": intent, "scope": scope, "confidence": confidence}
