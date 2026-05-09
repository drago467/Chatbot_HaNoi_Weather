"""Tool-call telemetry helpers — unified cho cả invoke và stream paths.

R18 fix (P0-4): trước refactor, 4 entry points của agent (run/stream × routed/
fallback) ghi log 4 kiểu khác nhau:
- run_agent (invoke): log nhưng tool_output luôn rỗng (BLIND)
- stream_agent: log đầy đủ
- run_agent_routed: KHÔNG log gì
- stream_agent_routed: log đầy đủ + đúng turn_count

Module này tách logic extract+log ra helper dùng chung. 4 paths giờ gọi cùng
hàm `log_tool_calls()` với cùng schema.

Schema log entry:
    {
        "tool_name": str,
        "tool_input": str (stringified args),
        "tool_output": str (full content, no truncation),
        "success": bool (False if ToolMessage.status == 'error'),
    }
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Stream-mode helpers (LangGraph stream_mode='messages')
# ─────────────────────────────────────────────────────────────────────────

def accumulate_tool_call_chunks(
    chunks: list,
    pending: dict,
    index_to_id: dict,
) -> None:
    """Append `args` fragments từ tool_call_chunks vào `pending` đúng tool call.

    LangGraph stream chia tool call thành nhiều chunks: chunk đầu có
    `id` + `name` + 1 phần `args`; chunks sau chỉ có `index` + tiếp `args`.
    Route theo `index` thay vì lấy first key (sai khi parallel tool calls).

    Args:
        chunks: list `tool_call_chunks` từ AIMessageChunk.
        pending: mut dict — id → {"tool_name", "tool_input_parts"}.
        index_to_id: mut dict — index → id (cho continuation chunks).
    """
    for tc in chunks:
        tc_id = tc.get("id")
        tc_name = tc.get("name")
        tc_index = tc.get("index", 0)
        if tc_id and tc_id not in pending:
            pending[tc_id] = {
                "tool_name": tc_name or "unknown",
                "tool_input_parts": [],
            }
            index_to_id[tc_index] = tc_id
        target_id = tc_id or index_to_id.get(tc_index)
        if target_id and target_id in pending:
            args_str = tc.get("args", "")
            if args_str:
                pending[target_id]["tool_input_parts"].append(args_str)


def flush_tool_message_to_log(
    msg_chunk: ToolMessage,
    pending: dict,
    log_list: list,
) -> None:
    """Khi gặp ToolMessage (kết quả tool), match với pending entry và push log."""
    tc_id = getattr(msg_chunk, "tool_call_id", None)
    p = pending.pop(tc_id, None) if tc_id else None
    log_list.append({
        "tool_name": p["tool_name"] if p else getattr(msg_chunk, "name", "unknown"),
        "tool_input": "".join(p["tool_input_parts"]) if p else "",
        "tool_output": str(msg_chunk.content) if msg_chunk.content else "",
        "success": msg_chunk.status != "error" if hasattr(msg_chunk, "status") else True,
    })


# ─────────────────────────────────────────────────────────────────────────
# Invoke-mode helper (extract from final messages list)
# ─────────────────────────────────────────────────────────────────────────

def extract_tool_calls_from_messages(messages: list) -> list[dict[str, Any]]:
    """Extract tool_calls từ list messages sau invoke.

    Pair AIMessage.tool_calls với ToolMessage qua tool_call_id để có cả
    input + output (giống như stream mode đã có). Trước R18, run_agent
    chỉ lấy tool_calls.args nhưng tool_output để rỗng.
    """
    # Build maps tool_call_id → output / status
    outputs: dict[str, str] = {}
    statuses: dict[str, bool] = {}
    for m in messages:
        if isinstance(m, ToolMessage):
            tc_id = getattr(m, "tool_call_id", None)
            if tc_id:
                outputs[tc_id] = str(m.content) if m.content else ""
                statuses[tc_id] = m.status != "error" if hasattr(m, "status") else True

    logs: list[dict[str, Any]] = []
    for m in messages:
        tcs = getattr(m, "tool_calls", None)
        if not tcs:
            continue
        for tc in tcs:
            if isinstance(tc, dict):
                name = tc.get("name") or "unknown"
                args = tc.get("args", {})
                tc_id = tc.get("id", "")
            else:
                name = getattr(tc, "name", None) or "unknown"
                args = getattr(tc, "args", {})
                tc_id = getattr(tc, "id", "")
            logs.append({
                "tool_name": name,
                "tool_input": str(args),
                "tool_output": outputs.get(tc_id, ""),
                "success": statuses.get(tc_id, True),
            })
    return logs


# ─────────────────────────────────────────────────────────────────────────
# Logger sink — non-fatal
# ─────────────────────────────────────────────────────────────────────────

def log_tool_calls(thread_id: str, turn_number: int, tool_call_logs: list) -> None:
    """Push list of tool call dicts to evaluation logger.

    Telemetry failures are swallowed (logger.warning) — không break user request.
    """
    if not tool_call_logs:
        return
    try:
        from app.agent.telemetry import get_evaluation_logger
        tel_logger = get_evaluation_logger()
        for tc in tool_call_logs:
            tel_logger.log_tool_call(
                session_id=thread_id,
                turn_number=turn_number,
                tool_name=tc["tool_name"],
                tool_input=tc["tool_input"],
                tool_output=tc["tool_output"],
                success=tc["success"],
            )
    except Exception as e:
        logger.warning("Telemetry log_tool_calls failed: %s", e)
