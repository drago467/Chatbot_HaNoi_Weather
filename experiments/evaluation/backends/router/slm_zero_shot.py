"""SLM zero-shot router — qwen3-4b zero-shot via `qwen-api` gateway (C3)."""

from __future__ import annotations

from experiments.evaluation.backends.router._slm_base import _SLMRouterBase


class SlmZeroShotRouter(_SLMRouterBase):
    """qwen3-4b zero-shot (no finetune). Pair với C1 để justify finetune.

    Production gateway (sv1) chứ không phải Colab tunnel.
    """
