"""ChatOpenAI factory với best-practice sampling theo model family.

R18 fix (P0-2): trước đây `temperature=0` + `enable_thinking=True` cho Qwen3 —
Qwen team chính thức warn `"DO NOT use greedy decoding"` với thinking mode
(model card https://huggingface.co/Qwen/Qwen3-14B). Lý do: greedy + long thinking
trace gây "performance degradation and endless repetitions". Cũng là root cause
"stop-after-1-tool" (model emit stop-token bên trong `<think>` block — vLLM issue
#39056, llama.cpp issue #20837).

Best-practice cho thinking ON (mọi size 4B-235B, uniform per Qwen team):
    T=0.6, top_p=0.95, top_k=20, min_p=0, presence_penalty=1.0

`top_k` và `min_p` không phải OpenAI standard params → đẩy qua `extra_body`
(vLLM/SGLang accept). `langchain-openai >=0.3.35` forward y nguyên.
"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


# ─────────────────────────────────────────────────────────────────────────
# Best-practice sampling configs (per Qwen team)
# ─────────────────────────────────────────────────────────────────────────

# Qwen3 thinking mode — uniform recommendation 4B → 235B per HuggingFace cards.
# DO NOT lower temperature: Qwen team explicitly warns greedy decoding causes
# endless repetitions với thinking. presence_penalty 1.0 reduces repetition
# without language-mixing risk.
_QWEN3_THINKING = {
    "temperature": 0.6,
    "top_p": 0.95,
    "presence_penalty": 1.0,
    # top_k, min_p, enable_thinking via extra_body (vLLM/SGLang OpenAI-compat)
    "extra_body": {
        "enable_thinking": True,
        "top_k": 20,
        "min_p": 0.0,
    },
}

# Qwen3 non-thinking (fallback nếu user disable thinking explicitly via env)
_QWEN3_NON_THINKING = {
    "temperature": 0.7,
    "top_p": 0.8,
    "extra_body": {
        "enable_thinking": False,
        "top_k": 20,
        "min_p": 0.0,
    },
}

# Commercial models (gpt-4o-mini, gemini-flash, etc.) — deterministic eval baseline
_COMMERCIAL_DEFAULT = {"temperature": 0.0}


def _is_qwen3(model_name: str) -> bool:
    """Detect Qwen3 family. Tolerant of common spellings."""
    name = (model_name or "").lower()
    return "qwen3" in name or "qwen-3" in name


def make_qwen3_kwargs(thinking: bool = True) -> dict:
    """Return ChatOpenAI kwargs cho Qwen3 best-practice (thinking on/off).

    Public helper cho eval backends + ablation studies — eval cần override
    `thinking` flag không qua env. Production code gọi `build_chat_model()`
    thay vì hàm này.

    Args:
        thinking: True → T=0.6 + enable_thinking=True (Qwen team rec).
                  False → T=0.7 + enable_thinking=False.

    Returns:
        dict ChatOpenAI kwargs (top-level + extra_body merged).
    """
    return dict(_QWEN3_THINKING if thinking else _QWEN3_NON_THINKING)


def _resolve_endpoint() -> tuple[str, str, str]:
    """Read AGENT_API_BASE / AGENT_API_KEY / AGENT_MODEL với fallback legacy.

    Raises ValueError nếu thiếu base/key — fail-fast.
    """
    api_base = os.getenv("AGENT_API_BASE") or os.getenv("API_BASE")
    api_key = os.getenv("AGENT_API_KEY") or os.getenv("API_KEY")
    model_name = os.getenv("AGENT_MODEL") or os.getenv("MODEL", "gpt-4o-mini-2024-07-18")
    if not api_base or not api_key:
        raise ValueError("AGENT_API_BASE and AGENT_API_KEY must be set in .env")
    return api_base, api_key, model_name


def build_chat_model() -> ChatOpenAI:
    """Build ChatOpenAI instance với best-practice sampling cho model hiện tại.

    Qwen3 → thinking mode default ON (T=0.6, ...). Override bằng env
    `AGENT_THINKING=false` nếu cần ablation.
    Commercial → T=0 (reproducible eval baseline).
    """
    api_base, api_key, model_name = _resolve_endpoint()

    common = {
        "model": model_name,
        "base_url": api_base,
        "api_key": api_key,
    }

    if _is_qwen3(model_name):
        thinking_on = os.getenv("AGENT_THINKING", "true").lower() in ("true", "1", "yes")
        cfg = dict(_QWEN3_THINKING if thinking_on else _QWEN3_NON_THINKING)
        # Spread top-level params + extra_body separately
        extra_body = cfg.pop("extra_body", {})
        return ChatOpenAI(**common, **cfg, extra_body=extra_body)

    return ChatOpenAI(**common, **_COMMERCIAL_DEFAULT)
