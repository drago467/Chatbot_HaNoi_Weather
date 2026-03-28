"""ConversationState — thread-safe in-memory store for multi-turn context.

Tracks last_location, last_time_expr, last_intent across turns per thread.
TTL = 30 minutes (configurable via CONVERSATION_TTL_SECONDS env var).

Usage:
    store = get_conversation_store()
    state = store.get(thread_id)           # Returns ConversationState or None
    store.update_from_result(thread_id, agent_result, intent)  # After each turn
    needs_rewrite = store.needs_rewrite(thread_id, query)      # Before routing
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any


# ── TTL: default 30 minutes ──
_TTL_SECONDS = int(os.getenv("CONVERSATION_TTL_SECONDS", "1800"))

# ── Vietnamese pronoun / underspecification patterns ──
# These signal that the query cannot stand alone without prior context.
_ANAPHORA_PATTERNS = re.compile(
    r"\b(ở đó|chỗ đó|nơi đó|khu đó|thế còn|vậy còn|rồi sao|"
    r"còn đó|ở khu đó|chỗ kia|thế còn\s|vậy thì|đó thì|khu vực đó)\b",
    re.IGNORECASE,
)

# Vietnamese location indicator words — presence suggests query has its own location
_LOCATION_INDICATORS = re.compile(
    r"\b(quận|huyện|phường|xã|thị trấn|thị xã|"
    r"cầu giấy|đống đa|hoàn kiếm|ba đình|hai bà trưng|tây hồ|"
    r"thanh xuân|hoàng mai|long biên|bắc từ liêm|nam từ liêm|hà đông|"
    r"sóc sơn|đông anh|gia lâm|thanh trì|mê linh|sơn tây|ba vì|"
    r"phúc thọ|đan phượng|hoài đức|quốc oai|thạch thất|chương mỹ|"
    r"thanh oai|thường tín|phú xuyên|ứng hòa|mỹ đức|"
    r"hà nội|nội bài|mỹ đình|hồ gươm|hồ tây|lăng bác|văn miếu)\b",
    re.IGNORECASE,
)


@dataclass
class ConversationState:
    """Per-thread conversation context for multi-turn resolution.

    Fields:
        last_location: Dict from resolve_location tool result
                       {level, name, ward_id, district_name, city_name}
        last_time_expr: Last time expression mentioned ("chiều nay", "ngày mai", ...)
        last_intent: Last classified intent (e.g. "current_weather")
        turn_count: Number of completed turns
        updated_at: UNIX timestamp of last update (for TTL check)
    """
    last_location: dict | None = None
    last_time_expr: str | None = None
    last_intent: str | None = None
    turn_count: int = 0
    updated_at: float = field(default_factory=time.time)

    def location_name(self) -> str | None:
        """Return human-readable location name, or None if no location stored."""
        if not self.last_location:
            return None
        return (
            self.last_location.get("name")
            or self.last_location.get("district_name")
            or self.last_location.get("city_name")
        )

    def to_context_json(self) -> dict:
        """Serialize state for injection into SLM router prompt."""
        return {
            "location": self.location_name(),
            "location_detail": self.last_location,
            "time_expr": self.last_time_expr,
            "intent": self.last_intent,
            "turn": self.turn_count,
        }


class ConversationStateStore:
    """Thread-safe in-memory store for ConversationState with TTL.

    Not persisted across server restarts (by design — conversations are session-scoped).
    """

    def __init__(self, ttl_seconds: int = _TTL_SECONDS):
        self._store: dict[str, ConversationState] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, thread_id: str) -> ConversationState | None:
        """Return state for thread_id if within TTL, else None."""
        with self._lock:
            state = self._store.get(thread_id)
            if state is None:
                return None
            if time.time() - state.updated_at > self._ttl:
                del self._store[thread_id]
                return None
            return state

    def update_from_result(
        self, thread_id: str, result: dict, intent: str
    ) -> ConversationState:
        """Extract entities from LangGraph agent result and update state.

        Scans result["messages"] for:
        - AIMessage.tool_calls with name="resolve_location" → extract location
        - AIMessage.tool_calls args for time-related parameters

        Args:
            thread_id: Conversation thread ID
            result: LangGraph agent result dict (with "messages" key)
            intent: Classified intent for this turn

        Returns:
            Updated ConversationState
        """
        with self._lock:
            state = self._store.get(thread_id) or ConversationState()
            messages = result.get("messages", [])

            # Scan messages for tool calls and outputs
            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None) or []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        name = tc.get("name", "")
                        args = tc.get("args", {})
                    else:
                        name = getattr(tc, "name", "")
                        args = getattr(tc, "args", {}) or {}

                    # Extract location from any tool call that has location_hint or ward_id
                    loc_hint = args.get("location_hint") or args.get("ward_id")
                    if loc_hint and not state.last_location:
                        # Store a minimal location dict for context
                        state.last_location = {"name": loc_hint, "level": "hint"}

                    # Extract time expression from tool args
                    for time_key in ("date", "start_date", "time_range", "period"):
                        if time_key in args:
                            state.last_time_expr = str(args[time_key])
                            break

            # Scan ToolMessage responses for resolve_location output
            for msg in messages:
                if getattr(msg, "type", None) == "tool":
                    # Try to match with preceding tool call named resolve_location
                    pass  # ToolMessage content is resolved below via tool_call_id

            # Better: pair AIMessage.tool_calls with ToolMessages via tool_call_id
            tool_outputs: dict[str, str] = {}
            for msg in messages:
                if getattr(msg, "type", None) == "tool":
                    tc_id = getattr(msg, "tool_call_id", "")
                    content = getattr(msg, "content", "")
                    if tc_id and content:
                        tool_outputs[tc_id] = str(content)

            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None) or []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        name = tc.get("name", "")
                        tc_id = tc.get("id", "")
                    else:
                        name = getattr(tc, "name", "")
                        tc_id = getattr(tc, "id", "")

                    if name == "resolve_location" and tc_id in tool_outputs:
                        try:
                            import json
                            loc_data = json.loads(tool_outputs[tc_id])
                            if isinstance(loc_data, dict) and loc_data.get("status") == "ok":
                                data = loc_data.get("data", {})
                                state.last_location = {
                                    "level": loc_data.get("level", ""),
                                    "name": (
                                        data.get("ward_name")
                                        or data.get("district_name")
                                        or "Hà Nội"
                                    ),
                                    "ward_id": data.get("ward_id"),
                                    "district_name": data.get("district_name"),
                                    "city_name": "Hà Nội",
                                }
                        except Exception:
                            pass  # Ignore parse errors — best-effort extraction

                    # Also extract location from get_current_weather / get_daily_forecast args
                    # when resolve_location is not explicitly called
                    if name in (
                        "get_current_weather", "get_daily_forecast", "get_hourly_forecast",
                        "get_rain_timeline", "get_weather_history", "get_daily_summary",
                        "get_weather_period",
                    ):
                        if isinstance(tc, dict):
                            args = tc.get("args", {})
                        else:
                            args = getattr(tc, "args", {}) or {}
                        loc_hint = args.get("location_hint")
                        if loc_hint and (
                            state.last_location is None
                            or state.last_location.get("level") == "hint"
                        ):
                            state.last_location = {
                                "level": "hint",
                                "name": loc_hint,
                                "ward_id": None,
                                "district_name": loc_hint,
                                "city_name": "Hà Nội",
                            }

            state.last_intent = intent
            state.turn_count += 1
            state.updated_at = time.time()
            self._store[thread_id] = state
            return state

    def needs_rewrite(self, thread_id: str, query: str) -> bool:
        """Determine if query needs contextual rewriting before routing.

        Returns True when:
        1. There IS prior context (turn_count > 0)
        2. AND the query is ambiguous:
           - Contains Vietnamese anaphora ("ở đó", "thế còn", ...)
           - OR query is very short (< 6 words) AND has no location indicator
           - OR no location keyword found AND intent was location-specific

        Returns False when:
        - No prior context (first turn)
        - Query has clear standalone location
        """
        state = self.get(thread_id)
        if state is None or state.turn_count == 0:
            return False

        # Explicit anaphora → definitely needs rewrite
        if _ANAPHORA_PATTERNS.search(query):
            return True

        # Short query with no location → likely depends on context
        word_count = len(query.split())
        has_location = bool(_LOCATION_INDICATORS.search(query))

        if word_count < 6 and not has_location:
            return True

        # Medium query without location, and previous intent was location-specific
        location_specific_intents = {
            "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
            "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
            "activity_weather", "expert_weather_param", "weather_alert",
        }
        if not has_location and state.last_intent in location_specific_intents:
            # Query has no location but previous turn had one → carry over
            if word_count < 10:
                return True

        return False

    def evict_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now - v.updated_at > self._ttl]
            for k in expired:
                del self._store[k]
        return len(expired)


# ── Singleton ──
_store: ConversationStateStore | None = None
_store_lock = threading.Lock()


def get_conversation_store() -> ConversationStateStore:
    """Get or create the singleton ConversationStateStore."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ConversationStateStore()
    return _store
