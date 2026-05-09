"""Agent runner — 4 entry points unified theo pattern stream_agent_routed.

R18 refactor (P0-4): tách từ agent.py 957 dòng. 4 paths:

| Path                  | Routed | Mode    | Telemetry | turn_number     |
|-----------------------|--------|---------|-----------|-----------------|
| run_agent             | no     | invoke  | full      | context.turn    |
| stream_agent          | no     | stream  | full      | context.turn    |
| run_agent_routed      | yes    | invoke  | full      | context.turn    |
| stream_agent_routed   | yes    | stream  | full      | context.turn    |

Trước refactor: turn_number=0 hardcoded ở 2 paths, run_agent_routed không log
gì → faithfulness eval blind. Sau refactor: 4 paths cùng schema, đều log đủ
input + output qua `_telemetry.extract_tool_calls_from_messages` /
`flush_tool_message_to_log`.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent

from app.agent._model_config import build_chat_model
from app.agent._prompt_builder import (
    get_focused_system_prompt,
    get_system_prompt,
)
from app.agent._telemetry import (
    accumulate_tool_call_chunks,
    extract_tool_calls_from_messages,
    flush_tool_message_to_log,
    log_tool_calls,
)
from app.agent.tools import TOOLS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Compat shim: langgraph < 0.2.56 dùng `state_modifier=`, từ 0.2.56 dùng `prompt=`.
# Detect 1 lần lúc import — không try/except mỗi call.
# ─────────────────────────────────────────────────────────────────────────

_PROMPT_KWARG: str = "prompt"
try:
    _sig_params = inspect.signature(create_react_agent).parameters
    if "prompt" in _sig_params:
        _PROMPT_KWARG = "prompt"
    elif "state_modifier" in _sig_params:
        _PROMPT_KWARG = "state_modifier"
    else:
        logger.warning("create_react_agent signature unexpected: %s", list(_sig_params))
    del _sig_params
except Exception as e:
    logger.warning("Could not detect create_react_agent prompt kwarg: %s", e)


# ─────────────────────────────────────────────────────────────────────────
# Thinking-token strip (Qwen3 inline `<think>...</think>` fallback)
# ─────────────────────────────────────────────────────────────────────────

_THINK_TOKEN_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking_tokens(text: str) -> str:
    """Remove `<think>...</think>` từ Qwen3 streaming output (defensive)."""
    return _THINK_TOKEN_RE.sub("", text)


# ─────────────────────────────────────────────────────────────────────────
# Singleton agent + model + checkpointer (thread-safe)
# ─────────────────────────────────────────────────────────────────────────

_agent = None
_agent_lock = threading.Lock()
_db_connection = None
_model = None         # Shared ChatOpenAI (best-practice config từ _model_config)
_checkpointer = None  # Shared PostgresSaver (reused by focused agents)


def get_agent():
    """Get or create the weather agent (thread-safe singleton)."""
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                _agent = create_weather_agent()
    return _agent


def reset_agent():
    """Force recreation với fresh connections (used after stale-conn errors)."""
    global _agent, _db_connection, _model, _checkpointer
    with _agent_lock:
        if _db_connection is not None:
            try:
                _db_connection.close()
            except Exception as e:
                logger.warning("DB connection close error: %s", e)
            _db_connection = None
        _agent = None
        _model = None
        _checkpointer = None


def create_weather_agent():
    """Build full 27-tool agent + Postgres checkpointer.

    Best-practice Qwen3 config từ `_model_config.build_chat_model()` —
    thinking ON với T=0.6, top_p=0.95, top_k=20, presence_penalty=1.0.
    """
    global _model, _checkpointer, _db_connection

    _model = build_chat_model()

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in .env")

    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    _checkpointer = PostgresSaver(conn)
    _checkpointer.setup()
    _db_connection = conn

    return create_react_agent(
        model=_model, tools=TOOLS,
        checkpointer=_checkpointer,
        **{_PROMPT_KWARG: _full_prompt_callable},
    )


def _full_prompt_callable(state):
    """LangGraph prompt callable cho full agent (27 tools)."""
    return [SystemMessage(content=get_system_prompt())] + state["messages"]


def _focused_prompt_callable(tool_names: list):
    """Closure-based prompt callable cho focused agent (subset tools)."""
    def modifier(state):
        return [SystemMessage(content=get_focused_system_prompt(tool_names))] + state["messages"]
    return modifier


def _create_focused_agent(tools: list):
    """Build focused ReAct agent với subset tools (sau SLM routing)."""
    get_agent()  # ensure _model + _checkpointer init
    tool_names = [t.name for t in tools]
    return create_react_agent(
        model=_model,
        tools=tools,
        checkpointer=_checkpointer,
        **{_PROMPT_KWARG: _focused_prompt_callable(tool_names)},
    )


# ─────────────────────────────────────────────────────────────────────────
# Routing pipeline (shared cho run/stream routed)
# ─────────────────────────────────────────────────────────────────────────

class _RouteOutcome:
    """Kết quả routing: hoặc 'fallback' (caller chạy full agent), hoặc
    'routed' (caller chạy focused agent với focused_tools).

    `context` luôn non-None để caller lấy `turn_count` cho telemetry.
    """
    __slots__ = ("kind", "rr", "focused_tools", "effective_message", "context")

    def __init__(self, kind, rr, focused_tools, effective_message, context):
        self.kind = kind  # "fallback" | "routed"
        self.rr = rr
        self.focused_tools = focused_tools  # [] for fallback
        self.effective_message = effective_message
        self.context = context


def _route_request(
    message: str,
    thread_id: str,
    *,
    no_fallback: bool = False,
    use_rewrite: bool = True,
) -> _RouteOutcome:
    """Run SLM router → decide focused tools (hoặc fallback signal).

    Pipeline (mirror cũ stream_agent_routed Step 1-4):
    1. Get conversation context (or create empty)
    2. Router classify (multi-turn ChatML)
    3. Record turn vào history NGAY khi router success — anchor preservation
       trước tool exec (nếu tool fail, turn vẫn lưu)
    4. Compute effective_message (rewrite or original)
    5. Decide fallback vs focused tools
    """
    from app.agent.conversation_state import (
        ConversationState,
        get_conversation_store,
    )
    from app.agent.router.config import PER_INTENT_THRESHOLDS
    from app.agent.router.slm_router import get_router
    from app.agent.router.tool_mapper import get_focused_tools

    store = get_conversation_store()
    context = store.get(thread_id)

    router = get_router()
    rr = router.classify(message, context=context)
    logger.info("SLM Router: %s", rr)

    if context is None:
        context = ConversationState()

    # Record turn — chỉ khi router thành công (fallback turn không
    # contaminate multi-turn anchor history)
    if not rr.should_fallback:
        asst_json = json.dumps(
            {
                "intent": rr.intent,
                "scope": rr.scope,
                "confidence": round(rr.confidence, 2),
                "rewritten_query": rr.rewritten_query,
            },
            ensure_ascii=False,
        )
        context.record_turn(message, asst_json)
        store.put(thread_id, context)

    # Effective message — rewrite vs original (R11: ablation use_rewrite)
    if use_rewrite and rr.rewritten_query:
        effective_message = rr.rewritten_query
        logger.info("Router rewrite: %r → %r", message[:50], rr.rewritten_query[:60])
    else:
        effective_message = message

    # Fallback decision với no_fallback override (chỉ apply low_confidence)
    can_force = False
    if rr.should_fallback:
        can_force = bool(
            no_fallback
            and rr.fallback_reason
            and rr.fallback_reason.startswith("low_confidence")
        )
        if not can_force:
            logger.info("SLM Router → fallback (%s)", rr.fallback_reason)
            return _RouteOutcome("fallback", rr, [], effective_message, context)

    # Tool selection (confidence-aware)
    effective_conf = 1.0 if can_force else rr.confidence
    focused_tools = get_focused_tools(
        rr.intent, rr.scope, effective_conf, PER_INTENT_THRESHOLDS
    )

    if focused_tools is None:
        logger.info("SLM Router → fallback (no mapping for %s/%s)", rr.intent, rr.scope)
        return _RouteOutcome("fallback", rr, [], effective_message, context)

    if not focused_tools and rr.intent != "smalltalk_weather":
        logger.info("SLM Router → fallback (empty tools for %s/%s)", rr.intent, rr.scope)
        return _RouteOutcome("fallback", rr, [], effective_message, context)

    return _RouteOutcome("routed", rr, focused_tools or [], effective_message, context)


@contextmanager
def _scope_override(scope: Optional[str]):
    """Set router_scope_var ContextVar trong block, reset trong finally.

    `try/except ValueError` cho async-generator edge case (sync gen có thể
    được resume across threads via run_in_executor — ContextVar không tự
    inherit ở Python 3.10+; reset sai context raise ValueError).
    """
    from app.agent.dispatch import router_scope_var
    token = router_scope_var.set(scope)
    try:
        yield
    finally:
        try:
            router_scope_var.reset(token)
        except ValueError:
            pass  # SSE sync-generator across threads — leak harmless


# ─────────────────────────────────────────────────────────────────────────
# Core invoke / stream với telemetry
# ─────────────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG = {"recursion_limit": 15}


def _invoke_with_telemetry(
    agent,
    message: str,
    thread_id: str,
    *,
    turn_number: int,
) -> dict:
    """Invoke agent + extract tool_calls + log telemetry."""
    config = {"configurable": {"thread_id": thread_id}, **_DEFAULT_CONFIG}
    result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)
    tool_logs = extract_tool_calls_from_messages(result.get("messages", []))
    log_tool_calls(thread_id, turn_number, tool_logs)
    return result


def _stream_with_telemetry(
    agent,
    message: str,
    thread_id: str,
    *,
    turn_number: int,
    strip_thinking: bool = False,
) -> Iterator[str]:
    """Stream agent → yield text chunks; log tool calls sau khi stream xong.

    `strip_thinking=True` áp dụng `_strip_thinking_tokens` cho text chunks
    (defensive — Qwen3 thường tách reasoning_content qua langchain-openai
    >=0.3.35, nhưng provider có thể emit inline).
    """
    config = {"configurable": {"thread_id": thread_id}, **_DEFAULT_CONFIG}
    pending_tool_calls: dict = {}
    index_to_id: dict = {}
    tool_logs: list = []

    for event in agent.stream(
        {"messages": [{"role": "user", "content": message}]},
        config,
        stream_mode="messages",
    ):
        if not (event and len(event) >= 2):
            continue
        msg_chunk, metadata = event

        if isinstance(msg_chunk, ToolMessage):
            flush_tool_message_to_log(msg_chunk, pending_tool_calls, tool_logs)
            continue

        chunks = getattr(msg_chunk, "tool_call_chunks", None)
        if chunks:
            accumulate_tool_call_chunks(chunks, pending_tool_calls, index_to_id)
            continue

        if metadata.get("langgraph_node") == "agent":
            content = getattr(msg_chunk, "content", "") if hasattr(msg_chunk, "content") else ""
            if content:
                if strip_thinking:
                    content = _strip_thinking_tokens(content)
                if content:
                    yield content

    log_tool_calls(thread_id, turn_number, tool_logs)


# ─────────────────────────────────────────────────────────────────────────
# Retry wrappers (stale connection auto-recovery)
# ─────────────────────────────────────────────────────────────────────────

_MAX_RETRIES = 2


def _retry_invoke(fn):
    """Retry invoke-style fn 1 lần với reset_agent giữa attempts."""
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                reset_agent()
            else:
                raise last_error
    return None  # unreachable


def _retry_stream(gen_factory):
    """Retry stream-style fn 1 lần. WARNING: nếu yield đã xảy ra rồi exception,
    retry sẽ yield lại từ đầu → duplicate output. Bug latent kế thừa từ pre-R18
    (xem stream_agent gốc agent.py:546-602). Production hiếm gặp vì lỗi thường
    front-load (auth/conn). Giữ nguyên behavior để không phá compat.
    """
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            yield from gen_factory()
            return
        except Exception as e:
            last_error = e
            if attempt < _MAX_RETRIES - 1:
                reset_agent()
            else:
                raise last_error


# ─────────────────────────────────────────────────────────────────────────
# Public entry points (4) — backward-compatible signatures
# ─────────────────────────────────────────────────────────────────────────

def run_agent(message: str, thread_id: str = "default") -> dict:
    """Run full 27-tool agent (no router) — invoke mode.

    Backward-compat: signature unchanged. Telemetry now includes tool_output
    (R18 fix — pre-R18 logged tool_output=""). turn_number=0 vì non-routed
    path không record vào ConversationStateStore.
    """
    def _fn():
        agent = get_agent()
        return _invoke_with_telemetry(agent, message, thread_id, turn_number=0)
    return _retry_invoke(_fn)


def stream_agent(message: str, thread_id: str = "default"):
    """Stream full 27-tool agent (no router). Yield text chunks.

    Backward-compat: yield chunks chỉ từ node 'agent' (không yield tool output).
    """
    def _gen():
        agent = get_agent()
        yield from _stream_with_telemetry(
            agent, message, thread_id,
            turn_number=0, strip_thinking=False,
        )
    yield from _retry_stream(_gen)


def run_agent_routed(
    message: str,
    thread_id: str = "default",
    *,
    no_fallback: bool = False,
    use_rewrite: bool = True,
) -> dict:
    """Run với SLM routing (invoke mode).

    Backward-compat: returns dict với key `_router` chứa metadata.
    R18 fix: now logs tool calls (pre-R18 không log).
    """
    outcome = _route_request(
        message, thread_id,
        no_fallback=no_fallback, use_rewrite=use_rewrite,
    )
    rr = outcome.rr

    def _meta(path: str, **extra) -> dict:
        return {
            "path": path,
            "intent": rr.intent,
            "scope": rr.scope,
            "confidence": rr.confidence,
            "latency_ms": rr.latency_ms,
            "fallback_reason": rr.fallback_reason,
            "rewritten_query": rr.rewritten_query,
            **extra,
        }

    if outcome.kind == "fallback":
        result = run_agent(message, thread_id)
        result["_router"] = _meta("fallback")
        return result

    tool_names = [t.name for t in outcome.focused_tools]
    turn = outcome.context.turn_count
    logger.info(
        "SLM Router → routed: %s/%s (conf=%.2f), tools=%s",
        rr.intent, rr.scope, rr.confidence, tool_names,
    )

    def _fn():
        with _scope_override(rr.scope):
            agent = _create_focused_agent(outcome.focused_tools)
            result = _invoke_with_telemetry(
                agent, outcome.effective_message, thread_id,
                turn_number=turn,
            )
            result["_router"] = _meta("routed", focused_tools=tool_names)
            return result

    return _retry_invoke(_fn)


def stream_agent_routed(message: str, thread_id: str = "default"):
    """Stream với SLM routing. Yield text chunks.

    Backward-compat: respects USE_SLM_ROUTER flag (False → fallback đến
    stream_agent ngay). Strip thinking tokens (Qwen3 inline `<think>`).
    """
    from app.agent.router.config import USE_SLM_ROUTER
    if not USE_SLM_ROUTER:
        yield from stream_agent(message, thread_id)
        return

    outcome = _route_request(message, thread_id)
    rr = outcome.rr

    if outcome.kind == "fallback":
        yield from stream_agent(message, thread_id)
        return

    tool_names = [t.name for t in outcome.focused_tools]
    turn = outcome.context.turn_count
    logger.info(
        "SLM Router → fast path: %s/%s (conf=%.2f), %d tools: %s",
        rr.intent, rr.scope, rr.confidence,
        len(outcome.focused_tools), tool_names,
    )

    def _gen():
        with _scope_override(rr.scope):
            agent = _create_focused_agent(outcome.focused_tools)
            yield from _stream_with_telemetry(
                agent, outcome.effective_message, thread_id,
                turn_number=turn, strip_thinking=True,
            )

    yield from _retry_stream(_gen)
