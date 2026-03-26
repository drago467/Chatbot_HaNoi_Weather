"""SLM Router — classify user query → {intent, scope, confidence}.

Inference backend: Ollama HTTP API (primary).
Model: fine-tuned Qwen2.5-1.5B-Instruct (GGUF Q8_0).
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time

import httpx

from app.agent.router.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    ROUTER_SYSTEM_PROMPT,
    VALID_INTENTS,
    VALID_SCOPES,
)

logger = logging.getLogger(__name__)

# ── Anaphora patterns (multi-turn references → fallback) ──
_ANAPHORA_RE = re.compile(
    r"\b(ở đó|chỗ đó|nơi đó|khu đó|thế còn|vậy còn|rồi sao)\b",
    re.IGNORECASE,
)


class RouterResult:
    """Classification result from SLM Router."""

    __slots__ = ("intent", "scope", "confidence", "latency_ms", "fallback_reason")

    def __init__(
        self,
        intent: str = "",
        scope: str = "city",
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        fallback_reason: str | None = None,
    ):
        self.intent = intent
        self.scope = scope
        self.confidence = confidence
        self.latency_ms = latency_ms
        self.fallback_reason = fallback_reason

    @property
    def should_fallback(self) -> bool:
        return self.fallback_reason is not None

    def __repr__(self) -> str:
        if self.fallback_reason:
            return f"RouterResult(FALLBACK: {self.fallback_reason}, {self.latency_ms:.0f}ms)"
        return (
            f"RouterResult({self.intent}/{self.scope}, "
            f"conf={self.confidence:.2f}, {self.latency_ms:.0f}ms)"
        )


class SLMRouter:
    """SLM-based intent + scope classifier using Ollama."""

    def __init__(
        self,
        ollama_base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        confidence_threshold: float = 0.75,
        timeout: float = 10.0,
    ):
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._healthy: bool | None = None

    def classify(self, query: str) -> RouterResult:
        """Classify user query → RouterResult.

        Returns RouterResult with fallback_reason set if:
        - Anaphora detected (multi-turn context needed)
        - Model unavailable / error
        - JSON parse failure
        - Confidence below threshold
        - Invalid intent/scope
        """
        t0 = time.perf_counter()

        # Check anaphora first (no model call needed)
        if _ANAPHORA_RE.search(query):
            return RouterResult(
                latency_ms=_elapsed_ms(t0),
                fallback_reason="anaphora_detected",
            )

        # Call Ollama
        try:
            raw_text = self._call_ollama(query)
        except Exception as e:
            logger.warning("SLM Router error: %s", e)
            return RouterResult(
                latency_ms=_elapsed_ms(t0),
                fallback_reason=f"model_error: {e}",
            )

        # Parse JSON response
        parsed = self._parse_response(raw_text)
        if parsed is None:
            logger.warning("SLM Router JSON parse failed: %r", raw_text)
            return RouterResult(
                latency_ms=_elapsed_ms(t0),
                fallback_reason=f"json_parse_error: {raw_text[:100]}",
            )

        intent = parsed.get("intent", "")
        scope = parsed.get("scope", "city")

        # Validate intent/scope
        if intent not in VALID_INTENTS:
            return RouterResult(
                intent=intent,
                scope=scope,
                latency_ms=_elapsed_ms(t0),
                fallback_reason=f"invalid_intent: {intent}",
            )
        if scope not in VALID_SCOPES:
            scope = "city"  # safe default

        # Confidence: use model-reported if available, else 1.0 for valid JSON
        confidence = parsed.get("confidence", 1.0)
        if not isinstance(confidence, (int, float)):
            confidence = 1.0

        ms = _elapsed_ms(t0)

        # Threshold check
        if confidence < self.confidence_threshold:
            return RouterResult(
                intent=intent,
                scope=scope,
                confidence=confidence,
                latency_ms=ms,
                fallback_reason=f"low_confidence: {confidence:.2f}",
            )

        return RouterResult(
            intent=intent,
            scope=scope,
            confidence=confidence,
            latency_ms=ms,
        )

    def _call_ollama(self, query: str) -> str:
        """Call Ollama /api/chat endpoint."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 64,  # JSON output ~20 tokens
            },
        }
        resp = self._client.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    def _parse_response(self, text: str) -> dict | None:
        """Parse JSON from model output. Handles extra text around JSON."""
        text = text.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON from text
        match = re.search(r"\{[^{}]+\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def health_check(self) -> bool:
        """Check if Ollama is reachable and model is loaded."""
        try:
            resp = self._client.get(f"{self.ollama_base_url}/api/tags")
            if resp.status_code != 200:
                self._healthy = False
                return False
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            # Check if our model exists (with or without :latest tag)
            self._healthy = any(
                self.model in m or m.startswith(self.model + ":") for m in models
            )
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def close(self):
        self._client.close()


# ── Singleton ──
_router: SLMRouter | None = None
_router_lock = threading.Lock()


def get_router() -> SLMRouter:
    """Get or create the singleton SLM Router."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                from app.agent.router.config import (
                    CONFIDENCE_THRESHOLD,
                    OLLAMA_BASE_URL,
                    OLLAMA_MODEL,
                )
                _router = SLMRouter(
                    ollama_base_url=OLLAMA_BASE_URL,
                    model=OLLAMA_MODEL,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )
    return _router


def _elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000
