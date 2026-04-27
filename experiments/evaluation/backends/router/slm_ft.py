"""SLM finetune router — qwen3-4b-finetune via `qwen-tunnel` (Colab) (C1/C4)."""

from __future__ import annotations

from experiments.evaluation.backends.router._slm_base import _SLMRouterBase


class SlmFtRouter(_SLMRouterBase):
    """qwen3-4b-finetune (LoRA) via Colab Cloudflare tunnel.

    Production baseline router. Pair với C2 (no router) + C3 (zero-shot) +
    C4 (no thinking) để justify thiết kế.
    """
