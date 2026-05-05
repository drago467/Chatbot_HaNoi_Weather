"""ConversationState — thread-safe in-memory store for multi-turn router context.

Schema mirrors training data (multitask_train_v6_clean.jsonl):
    {"location": str, "intent": str, "turn": int}

Anything beyond these three fields was never seen during fine-tuning and biases
the router's rewrite output (the model latches onto stray strings like
"Hà Nội" inside richer context dicts). Keep this surface minimal.

TTL = 30 minutes (configurable via CONVERSATION_TTL_SECONDS env var).
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field


_TTL_SECONDS = int(os.getenv("CONVERSATION_TTL_SECONDS", "1800"))

# Tools whose `location_hint` argument should seed last location when no
# resolve_location call was made. P11 (2026-05-04): expanded từ 7 → 22 tools
# để cover toàn bộ tools nhận location_hint (trước đây thiếu 15 tool insight/
# advice/advanced → state.location không update khi user hỏi vd "Cầu Giấy nên
# mặc gì"). `compare_weather` xử lý riêng (location_hint1/location_hint2).
_LOCATION_HINT_TOOLS = frozenset({
    # core
    "get_current_weather", "get_weather_alerts",
    # forecast
    "get_hourly_forecast", "get_daily_forecast",
    "get_rain_timeline", "get_best_time",
    # history
    "get_weather_history", "get_daily_summary", "get_weather_period",
    # compare (single-hint)
    "compare_with_yesterday", "get_seasonal_comparison",
    # insight
    "detect_phenomena", "get_temperature_trend", "get_comfort_index",
    "get_weather_change_alert", "get_clothing_advice", "get_activity_advice",
    # insight advanced
    "get_uv_safe_windows", "get_pressure_trend", "get_daily_rhythm",
    "get_humidity_timeline", "get_sunny_periods",
})


@dataclass
class ConversationState:
    """Per-thread router context. Three fields, matched to training schema."""
    location: str | None = None
    intent: str | None = None
    turn_count: int = 0
    updated_at: float = field(default_factory=time.time)

    def to_context_json(self) -> dict:
        """Serialize for [CONTEXT: ...] injection into the router prompt."""
        return {
            "location": self.location,
            "intent": self.intent,
            "turn": self.turn_count,
        }


class ConversationStateStore:
    """Thread-safe in-memory store with TTL. Not persisted across restarts."""

    def __init__(self, ttl_seconds: int = _TTL_SECONDS):
        self._store: dict[str, ConversationState] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, thread_id: str) -> ConversationState | None:
        with self._lock:
            state = self._store.get(thread_id)
            if state is None:
                return None
            if time.time() - state.updated_at > self._ttl:
                del self._store[thread_id]
                return None
            return state

    def update(
        self, thread_id: str, tool_call_logs: list[dict], intent: str
    ) -> ConversationState:
        """Advance state for one completed turn.

        tool_call_logs: list of {tool_name, tool_input(JSON str or dict), tool_output(JSON str)}.
        Both streaming and non-streaming paths produce this shape (the latter
        via messages_to_tool_call_logs).
        """
        new_loc = _extract_location(tool_call_logs)
        with self._lock:
            state = self._store.get(thread_id) or ConversationState()
            if new_loc is not None:
                state.location = new_loc
            state.intent = intent
            state.turn_count += 1
            state.updated_at = time.time()
            self._store[thread_id] = state
            return state

    def evict_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now - v.updated_at > self._ttl]
            for k in expired:
                del self._store[k]
        return len(expired)


def _parse_json(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _extract_location(tool_call_logs: list[dict]) -> str | None:
    """Pick a location name from this turn's tool calls.

    Priority:
      1. resolve_location tool output (canonical từ DAL, đã flatten ở
         build_resolve_location_output P11).
      2. location_hint arg từ bất kỳ tool nào trong _LOCATION_HINT_TOOLS.
      3. compare_weather → location_hint1 (fallback location_hint2).

    P11 (2026-05-04):
      - resolve_location output schema mới sau fix builder: top-level VN keys
        ("phường/xã", "quận/huyện", "thành phố") + "trạng thái". Trước P11
        builder bóc nhầm thành chỉ {"trạng thái": ...} → nhánh này dead code.
      - _LOCATION_HINT_TOOLS expanded từ 7 → 22 tools.
      - compare_weather có 2 hints (location_hint1/location_hint2), không có
        location_hint đơn lẻ → cần xử lý riêng.
    """
    resolve_name: str | None = None
    hint_name: str | None = None
    compare_hint: str | None = None

    for tc in tool_call_logs:
        name = tc.get("tool_name", "")

        if name == "resolve_location":
            if resolve_name is not None:
                continue
            out = _parse_json(tc.get("tool_output", ""))
            if not out:
                continue
            # Post-P11 builder shape: VN keys ở top-level. Status check qua
            # "trạng thái" (shaped) hoặc "status" (defensive cho old data).
            status = out.get("trạng thái") or out.get("status")
            if status not in ("exact", "fuzzy", "ok"):
                continue
            resolve_name = (
                out.get("phường/xã")
                or out.get("quận/huyện")
                or out.get("thành phố")
                or "Hà Nội"
            )
        elif name == "compare_weather":
            if compare_hint is not None:
                continue
            args = _parse_json(tc.get("tool_input", "")) or {}
            lh = args.get("location_hint1") or args.get("location_hint2")
            if lh:
                compare_hint = str(lh)
        elif name in _LOCATION_HINT_TOOLS and hint_name is None:
            args = _parse_json(tc.get("tool_input", "")) or {}
            lh = args.get("location_hint")
            if lh:
                hint_name = str(lh)

    return resolve_name or hint_name or compare_hint


def messages_to_tool_call_logs(messages) -> list[dict]:
    """Convert a LangGraph result['messages'] list into the tool_call_logs shape.

    Pairs AIMessage.tool_calls with their matching ToolMessage outputs by
    tool_call_id.
    """
    pending: dict[str, dict] = {}
    logs: list[dict] = []
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            if isinstance(tc, dict):
                tc_id = tc.get("id", "") or ""
                tc_name = tc.get("name", "") or ""
                tc_args = tc.get("args", {}) or {}
            else:
                tc_id = getattr(tc, "id", "") or ""
                tc_name = getattr(tc, "name", "") or ""
                tc_args = getattr(tc, "args", {}) or {}
            args_str = (
                json.dumps(tc_args, ensure_ascii=False)
                if isinstance(tc_args, dict)
                else str(tc_args)
            )
            if tc_id:
                pending[tc_id] = {"tool_name": tc_name, "tool_input": args_str}

        if getattr(msg, "type", None) == "tool":
            tc_id = getattr(msg, "tool_call_id", "") or ""
            entry = pending.pop(tc_id, None)
            logs.append({
                "tool_name": entry["tool_name"] if entry else getattr(msg, "name", "unknown"),
                "tool_input": entry["tool_input"] if entry else "",
                "tool_output": str(getattr(msg, "content", "") or ""),
                "success": True,
            })
    return logs


_store: ConversationStateStore | None = None
_store_lock = threading.Lock()


def get_conversation_store() -> ConversationStateStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ConversationStateStore()
    return _store
