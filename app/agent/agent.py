"""LangGraph Agent for Weather Chatbot — public API surface.

R18 refactor (2026-05-09): split monolithic agent.py (957 dòng) thành 4 module:
- `_prompt_builder.py`  — BASE_PROMPT_TEMPLATE / TOOL_RULES / inject datetime
                          / few-shot exemplar templating
- `_model_config.py`    — ChatOpenAI factory với best-practice Qwen3 sampling
                          (T=0.6, top_p=0.95, top_k=20, presence_penalty=1.0)
- `_telemetry.py`       — unified tool-call log helpers (4 entry points cùng
                          schema; pre-R18 mỗi path log 1 kiểu)
- `_runner.py`          — 4 entry points (run/stream × routed/fallback)

File này giữ lại duy nhất public API surface — tests + eval scripts +
api/routes/chat.py import từ đây. KHÔNG thêm logic mới ở file này.
"""

from app.agent._prompt_builder import (
    BASE_PROMPT_TEMPLATE,
    TOOL_RULES,
    _inject_datetime,
    get_focused_system_prompt,
    get_system_prompt,
)
from app.agent._runner import (
    _PROMPT_KWARG,
    _strip_thinking_tokens,
    create_weather_agent,
    get_agent,
    reset_agent,
    run_agent,
    run_agent_routed,
    stream_agent,
    stream_agent_routed,
)

__all__ = [
    # Prompt builder
    "BASE_PROMPT_TEMPLATE",
    "TOOL_RULES",
    "_inject_datetime",
    "get_focused_system_prompt",
    "get_system_prompt",
    # Runner / public agent API
    "_PROMPT_KWARG",
    "_strip_thinking_tokens",
    "create_weather_agent",
    "get_agent",
    "reset_agent",
    "run_agent",
    "run_agent_routed",
    "stream_agent",
    "stream_agent_routed",
]
