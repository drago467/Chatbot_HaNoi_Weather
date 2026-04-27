"""Router backends — factory + concrete classes for 3 router types.

Usage:
    from experiments.evaluation.config import load_config
    from experiments.evaluation.backends.router import make_router

    cfg = load_config("c1")
    with make_router(cfg) as router:
        prediction = router.predict("trời Hà Nội hôm nay thế nào?")
"""

from __future__ import annotations

from typing import Optional

from experiments.evaluation.config import EvalConfig, EvalSettings, get_eval_settings
from experiments.evaluation.backends.router.base import RouterBackend, RouterPrediction
from experiments.evaluation.backends.router.none import NoneRouter
from experiments.evaluation.backends.router.slm_ft import SlmFtRouter
from experiments.evaluation.backends.router.slm_zero_shot import SlmZeroShotRouter

__all__ = [
    "RouterBackend",
    "RouterPrediction",
    "NoneRouter",
    "SlmFtRouter",
    "SlmZeroShotRouter",
    "make_router",
]


def make_router(
    config: EvalConfig,
    settings: Optional[EvalSettings] = None,
) -> RouterBackend:
    """Factory — return concrete router theo `config.router_backend`.

    `settings` optional cho test inject mock. Default lazy-load `.env`.
    """
    if config.router_backend == "none":
        return NoneRouter()

    settings = settings or get_eval_settings()
    if config.router_gateway is None:
        raise ValueError(
            f"router_backend={config.router_backend!r} requires router_gateway "
            "(should have been caught by EvalConfig validator)"
        )
    if not config.router_model_name:
        raise ValueError(
            f"router_backend={config.router_backend!r} requires router_model_name"
        )

    gateway = settings.resolve(config.router_gateway)
    kwargs = {
        "base_url": gateway.base_url,
        "api_key": gateway.api_key,
        "model_name": config.router_model_name,
    }

    if config.router_backend == "slm_ft":
        return SlmFtRouter(**kwargs)
    if config.router_backend == "slm_zero_shot":
        return SlmZeroShotRouter(**kwargs)

    raise ValueError(f"Unknown router_backend: {config.router_backend!r}")
