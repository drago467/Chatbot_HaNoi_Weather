"""Abstract router backend — all 6-config eval routers share this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class RouterPrediction:
    """Output của 1 lần router classify.

    `intent=None` ↔ "no router" (NoneRouter) hoặc model abstain.
    Caller dùng `intent` để select tool subset (qua `tools.get_tool_subset()`).
    """

    intent: Optional[str]
    scope: str = "city"
    confidence: float = 0.0
    latency_ms: float = 0.0
    rewritten_query: Optional[str] = None
    fallback_reason: Optional[str] = None


class RouterBackend(ABC):
    """Interface — concrete: NoneRouter / SlmZeroShotRouter / SlmFtRouter."""

    @abstractmethod
    def predict(self, query: str) -> RouterPrediction:
        """Classify query → prediction. Phải deterministic khi temperature=0."""
        raise NotImplementedError

    def close(self) -> None:
        """Cleanup connections (HTTP clients). Default: no-op."""
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
