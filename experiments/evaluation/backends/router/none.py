"""NoneRouter — passthrough cho config có `router_backend='none'` (C2/C5/C6).

Không classify intent → caller (`tools.get_tool_subset`) sẽ rơi vào full_27.
"""

from __future__ import annotations

from experiments.evaluation.backends.router.base import RouterBackend, RouterPrediction


class NoneRouter(RouterBackend):
    """No-op router. Predict luôn return `intent=None`."""

    def predict(self, query: str) -> RouterPrediction:
        return RouterPrediction(intent=None, scope="city", confidence=0.0, latency_ms=0.0)
