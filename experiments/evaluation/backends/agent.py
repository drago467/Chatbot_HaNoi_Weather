"""EvalAgent — chạy 1 query qua pipeline đầy đủ (router → tool subset → agent).

Wrap LangGraph `create_react_agent` + ChatOpenAI per gateway (3 alias). Hỗ trợ
cả Qwen3 thinking mode + commercial OpenAI-compat (gpt-4o-mini, gemini-flash).

KHÔNG truncate tool_outputs (CRITICAL — feed full vào judge ở PR-C.5).
KHÔNG đụng `app/agent/agent.py` runtime production.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from experiments.evaluation.config import EvalConfig, EvalSettings, get_eval_settings
from experiments.evaluation.backends.router import RouterPrediction, make_router
from experiments.evaluation.backends.tools import get_tool_subset

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Output 1 lần `EvalAgent.run(question)` — đầy đủ cho metric + judge."""

    question: str
    response: str
    tools_called: list[str]
    tool_outputs: str  # FULL tool outputs — KHÔNG truncate (feed judge faithfulness)
    success: bool
    error: Optional[str] = None
    error_category: Optional[str] = None

    # Router metadata (None nếu router_backend='none')
    router_intent: Optional[str] = None
    router_scope: str = "city"
    router_confidence: float = 0.0
    router_fallback_reason: Optional[str] = None
    router_latency_ms: float = 0.0

    # Latency breakdown
    agent_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Token usage (cost metric)
    input_tokens: int = 0
    output_tokens: int = 0

    # Debug — số tool subset feed vào agent (vd 4 với router_prefilter, 27 với full_27)
    tool_subset_size: int = 0

    # Per-call detailed tool calls — name + args + output (cho debug/CSV)
    detailed_tool_calls: list[dict[str, Any]] = field(default_factory=list)


class EvalAgent:
    """Pluggable agent cho 6 config eval (C1..C6).

    Usage:
        cfg = load_config("c1")
        with EvalAgent(cfg) as agent:
            result = agent.run("trời Hà Nội thế nào?")
            print(result.response, result.tools_called)
    """

    def __init__(
        self,
        config: EvalConfig,
        settings: Optional[EvalSettings] = None,
    ):
        self.config = config
        self.settings = settings or get_eval_settings()
        self.router = make_router(config, settings=self.settings)
        # Pre-resolve agent gateway để fail fast nếu .env thiếu
        self._agent_gateway = self.settings.resolve(config.agent_gateway)

    def _build_chat_model(self) -> ChatOpenAI:
        """Build ChatOpenAI per query (cheap — chỉ là config).

        Qwen3 family → enable_thinking flag qua extra_body (theo
        `app/agent/agent.py:373` pattern verified với sv1 gateway).
        Commercial models → standard ChatOpenAI.
        """
        kwargs: dict[str, Any] = {
            "model": self.config.agent_model_name,
            "base_url": self._agent_gateway.base_url,
            "api_key": self._agent_gateway.api_key,
            "temperature": 0.0,
        }
        if "qwen" in self.config.agent_model_name.lower():
            kwargs["extra_body"] = {"enable_thinking": self.config.agent_thinking}
        return ChatOpenAI(**kwargs)

    def run(self, question: str) -> AgentResult:
        """Execute full pipeline: router → tool subset → agent → extract."""
        total_start = time.time()

        # Step 1 — router classify
        router_pred = self.router.predict(question)

        # Step 2 — select tool subset
        tools = get_tool_subset(
            tool_path=self.config.tool_path,
            intent=router_pred.intent,
            scope=router_pred.scope,
        )

        # Step 3 — build agent + invoke
        agent_start = time.time()
        try:
            chat_model = self._build_chat_model()
            agent = create_react_agent(model=chat_model, tools=tools)
            invocation = agent.invoke(
                {"messages": [{"role": "user", "content": question}]}
            )
        except Exception as e:
            agent_latency = (time.time() - agent_start) * 1000
            logger.exception("Agent invocation failed: %s", e)
            return AgentResult(
                question=question,
                response="",
                tools_called=[],
                tool_outputs="",
                success=False,
                error=str(e),
                error_category=_categorize_error(str(e)),
                router_intent=router_pred.intent,
                router_scope=router_pred.scope,
                router_confidence=router_pred.confidence,
                router_fallback_reason=router_pred.fallback_reason,
                router_latency_ms=router_pred.latency_ms,
                agent_latency_ms=agent_latency,
                total_latency_ms=(time.time() - total_start) * 1000,
                tool_subset_size=len(tools),
            )

        agent_latency = (time.time() - agent_start) * 1000

        # Step 4 — extract outputs
        messages = invocation.get("messages", [])
        response = _extract_final_response(messages)
        tools_called = _extract_tool_names(messages)
        tool_outputs = _extract_tool_outputs_full(messages)
        detailed_calls = _extract_detailed_tool_calls(messages)
        in_tok, out_tok = _extract_token_usage(messages)

        return AgentResult(
            question=question,
            response=response,
            tools_called=tools_called,
            tool_outputs=tool_outputs,
            success=True,
            router_intent=router_pred.intent,
            router_scope=router_pred.scope,
            router_confidence=router_pred.confidence,
            router_fallback_reason=router_pred.fallback_reason,
            router_latency_ms=router_pred.latency_ms,
            agent_latency_ms=agent_latency,
            total_latency_ms=(time.time() - total_start) * 1000,
            input_tokens=in_tok,
            output_tokens=out_tok,
            tool_subset_size=len(tools),
            detailed_tool_calls=detailed_calls,
        )

    def close(self) -> None:
        self.router.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


# ── Message extraction helpers (no truncation) ────────────────────────────


def _extract_final_response(messages: list) -> str:
    """Lấy content của AIMessage cuối cùng (response cho user)."""
    for msg in reversed(messages):
        msg_type = getattr(msg, "type", None)
        if msg_type == "ai":
            content = getattr(msg, "content", "")
            return str(content) if content else ""
    return ""


def _extract_tool_names(messages: list) -> list[str]:
    """List tên tool đã được gọi (theo thứ tự call)."""
    tools = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    tools.append(name)
    return tools


def _extract_tool_outputs_full(messages: list) -> str:
    """Concat FULL tool outputs (CRITICAL: no truncation cho judge faithfulness)."""
    outputs = []
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            content = getattr(msg, "content", "")
            if content:
                outputs.append(str(content))
    return "\n---\n".join(outputs) if outputs else ""


def _extract_detailed_tool_calls(messages: list) -> list[dict[str, Any]]:
    """Pair AIMessage.tool_calls với ToolMessage qua tool_call_id."""
    tool_outputs: dict[str, str] = {}
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            tc_id = getattr(msg, "tool_call_id", "")
            content = getattr(msg, "content", "")
            if tc_id:
                tool_outputs[tc_id] = str(content)

    calls: list[dict[str, Any]] = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name")
                    args = tc.get("args", {})
                    tc_id = tc.get("id", "")
                else:
                    name = getattr(tc, "name", None)
                    args = getattr(tc, "args", {})
                    tc_id = getattr(tc, "id", "")
                if name:
                    calls.append({
                        "name": name,
                        "input": args,  # full dict — không truncate
                        "output": tool_outputs.get(tc_id, ""),
                    })
    return calls


def _extract_token_usage(messages: list) -> tuple[int, int]:
    """Sum input + output tokens từ usage_metadata.

    LangChain >=0.3.0 gắn `usage_metadata` lên AIMessage. Multi-step ReAct
    có thể có nhiều AIMessage — cộng dồn.
    """
    in_total = 0
    out_total = 0
    for msg in messages:
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            in_total += usage.get("input_tokens", 0) or 0
            out_total += usage.get("output_tokens", 0) or 0
    return in_total, out_total


def _categorize_error(error_str: str) -> str:
    """Categorize error string. Reuse logic từ helpers.py:categorize_error."""
    err = error_str.lower()
    if "location" in err or "not_found" in err or "ambiguous" in err:
        return "location_resolution"
    if "no_data" in err or "database" in err or "không có dữ liệu" in err:
        return "data_unavailable"
    if "timeout" in err or "connection" in err or "refused" in err:
        return "network"
    if "openai" in err or "api" in err or "rate_limit" in err:
        return "llm_api"
    return "unknown"
