"""Pin behavior của `conversation_state` module.

Mục tiêu:
- Document `_parse_json` xử lý mọi input edge case (str/dict/None/empty/invalid).
- Pin `_extract_location` priority: resolve_location output > location_hint arg.
- Pin `messages_to_tool_call_logs` pairing tool_call_id → ToolMessage,
  bao gồm trường hợp `entry is None` (đã có guard ở `:171-177`, KHÔNG là bug).
- Pin TTL eviction + state update.

Sau PR refactor, test này phải vẫn pass với behavior identical.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from app.agent.conversation_state import (
    ConversationState,
    ConversationStateStore,
    _extract_location,
    _parse_json,
    messages_to_tool_call_logs,
)


# ── _parse_json edge cases ──────────────────────────────────────────────────


def test_parse_json_returns_dict_unchanged():
    d = {"a": 1}
    assert _parse_json(d) is d


def test_parse_json_parses_valid_str():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_returns_none_for_empty_string():
    assert _parse_json("") is None


def test_parse_json_returns_none_for_none():
    assert _parse_json(None) is None


def test_parse_json_returns_none_for_invalid_json():
    assert _parse_json("not json") is None


def test_parse_json_returns_none_for_non_dict_json():
    """JSON valid nhưng top-level là list/string → None."""
    assert _parse_json("[1, 2, 3]") is None
    assert _parse_json('"just a string"') is None
    assert _parse_json("42") is None


def test_parse_json_returns_none_for_non_string_non_dict():
    assert _parse_json(123) is None
    assert _parse_json(["a"]) is None


# ── _extract_location priority ──────────────────────────────────────────────


def test_extract_location_prefers_resolve_output():
    """resolve_location output > location_hint arg (canonical wins).

    P11: schema sau build_resolve_location_output là VN keys top-level
    ("trạng thái", "phường/xã", "quận/huyện").
    """
    logs = [
        {"tool_name": "get_current_weather", "tool_input": '{"location_hint": "CG"}',
         "tool_output": ""},
        {"tool_name": "resolve_location", "tool_input": "{}",
         "tool_output": json.dumps({
             "trạng thái": "exact",
             "cấp": "ward",
             "phường/xã": "Phường Dịch Vọng",
             "quận/huyện": "Cầu Giấy",
         })},
    ]
    assert _extract_location(logs) == "Phường Dịch Vọng"


def test_extract_location_district_when_no_ward():
    logs = [
        {"tool_name": "resolve_location", "tool_input": "{}",
         "tool_output": json.dumps({
             "trạng thái": "exact",
             "cấp": "district",
             "quận/huyện": "Tây Hồ",
         })},
    ]
    assert _extract_location(logs) == "Tây Hồ"


def test_extract_location_city_when_only_city():
    """City-level resolve → trả tên thành phố."""
    logs = [
        {"tool_name": "resolve_location", "tool_input": "{}",
         "tool_output": json.dumps({
             "trạng thái": "exact",
             "cấp": "city",
             "thành phố": "Hà Nội",
         })},
    ]
    assert _extract_location(logs) == "Hà Nội"


def test_extract_location_falls_back_to_hanoi_when_status_ok_but_no_name():
    """Defensive: status hợp lệ nhưng thiếu cả 3 name keys → fallback Hà Nội."""
    logs = [
        {"tool_name": "resolve_location", "tool_input": "{}",
         "tool_output": json.dumps({"trạng thái": "exact"})},
    ]
    assert _extract_location(logs) == "Hà Nội"


def test_extract_location_falls_back_to_hint_when_no_resolve():
    """Không có resolve_location → fallback location_hint từ weather tool."""
    logs = [
        {"tool_name": "get_hourly_forecast",
         "tool_input": '{"location_hint": "Hoàn Kiếm"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "Hoàn Kiếm"


def test_extract_location_uses_first_hint_only():
    """Multiple weather tools → chỉ dùng hint đầu tiên (hint_name guard)."""
    logs = [
        {"tool_name": "get_current_weather",
         "tool_input": '{"location_hint": "Đầu tiên"}',
         "tool_output": ""},
        {"tool_name": "get_hourly_forecast",
         "tool_input": '{"location_hint": "Thứ hai"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "Đầu tiên"


def test_extract_location_returns_none_when_no_relevant_tool():
    logs = [
        {"tool_name": "get_random_tool", "tool_input": "{}", "tool_output": ""},
    ]
    assert _extract_location(logs) is None


def test_extract_location_handles_resolve_status_not_ok():
    """status != ok → bỏ qua resolve, fall back to hint."""
    logs = [
        {"tool_name": "resolve_location", "tool_input": "{}",
         "tool_output": json.dumps({"trạng thái": "not_found"})},
        {"tool_name": "get_current_weather",
         "tool_input": '{"location_hint": "X"}', "tool_output": ""},
    ]
    assert _extract_location(logs) == "X"


# ── P11: expanded whitelist (15+ tools previously missing) ──────────────────


@pytest.mark.parametrize("tool_name", [
    "get_clothing_advice",
    "get_activity_advice",
    "compare_with_yesterday",
    "get_seasonal_comparison",
    "detect_phenomena",
    "get_temperature_trend",
    "get_comfort_index",
    "get_weather_change_alert",
    "get_uv_safe_windows",
    "get_pressure_trend",
    "get_daily_rhythm",
    "get_humidity_timeline",
    "get_sunny_periods",
    "get_best_time",
    "get_weather_alerts",
])
def test_extract_location_picks_hint_from_expanded_whitelist(tool_name):
    """P11: tools insight/advice/advanced phải seed location qua location_hint.

    Trước P11: chỉ 7 tool trong whitelist → query "Cầu Giấy nên mặc gì" →
    state.location = None → multi-turn router mất anchor.
    """
    logs = [
        {"tool_name": tool_name,
         "tool_input": '{"location_hint": "Cầu Giấy"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "Cầu Giấy"


# ── P11: compare_weather has 2 hints (different key) ────────────────────────


def test_extract_location_compare_weather_uses_location_hint1():
    """compare_weather dùng location_hint1/location_hint2 (không location_hint).
    Ưu tiên location_hint1 vì là địa điểm đầu tiên user nhắc đến.
    """
    logs = [
        {"tool_name": "compare_weather",
         "tool_input": '{"location_hint1": "Cầu Giấy", "location_hint2": "Đống Đa"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "Cầu Giấy"


def test_extract_location_compare_weather_falls_back_to_hint2():
    """Nếu chỉ có location_hint2 → vẫn dùng được."""
    logs = [
        {"tool_name": "compare_weather",
         "tool_input": '{"location_hint2": "Tây Hồ"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "Tây Hồ"


def test_extract_location_compare_weather_yields_to_other_tool_hint():
    """Khi có cả compare_weather + tool khác → tool khác (P2) thắng compare (P3)."""
    logs = [
        {"tool_name": "compare_weather",
         "tool_input": '{"location_hint1": "compare_loc"}',
         "tool_output": ""},
        {"tool_name": "get_current_weather",
         "tool_input": '{"location_hint": "current_loc"}',
         "tool_output": ""},
    ]
    assert _extract_location(logs) == "current_loc"


# ── P11: integration với build_resolve_location_output ──────────────────────


def test_extract_location_integration_with_real_builder():
    """End-to-end: DAL output → builder shape → _extract_location.

    Pin contract giữa output_builder.build_resolve_location_output
    và conversation_state._extract_location: keys phải đồng bộ.
    """
    from app.agent.tools.output_builder import build_resolve_location_output

    # Mô phỏng output thật của resolve_location_scoped (level=ward).
    dal_raw = {
        "status": "exact",
        "level": "ward",
        "data": {
            "ward_id": "ID_00169",
            "ward_name_vi": "Phường Dịch Vọng",
            "district_name_vi": "Cầu Giấy",
            "district_id": 5,
        },
    }
    tool_output = build_resolve_location_output(dal_raw)
    logs = [{
        "tool_name": "resolve_location",
        "tool_input": "{}",
        "tool_output": json.dumps(tool_output, ensure_ascii=False),
    }]
    assert _extract_location(logs) == "Phường Dịch Vọng"


# ── messages_to_tool_call_logs ──────────────────────────────────────────────


def _ai_msg(tool_calls):
    """Mock AIMessage with tool_calls attr."""
    return SimpleNamespace(tool_calls=tool_calls, type="ai")


def _tool_msg(tool_call_id, content, name="unknown"):
    """Mock ToolMessage with tool_call_id."""
    return SimpleNamespace(
        type="tool", tool_call_id=tool_call_id, content=content, name=name,
    )


def test_msg_to_logs_pairs_aimessage_with_toolmessage():
    msgs = [
        _ai_msg([{"id": "tc_1", "name": "get_current_weather",
                  "args": {"location_hint": "Cầu Giấy"}}]),
        _tool_msg("tc_1", '{"temp": 28}'),
    ]
    logs = messages_to_tool_call_logs(msgs)
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "get_current_weather"
    assert json.loads(logs[0]["tool_input"]) == {"location_hint": "Cầu Giấy"}
    assert logs[0]["tool_output"] == '{"temp": 28}'
    assert logs[0]["success"] is True


def test_msg_to_logs_handles_orphan_toolmessage():
    """ToolMessage không có AIMessage tương ứng (entry is None ở pending.pop).

    Code đã có guard `entry["tool_name"] if entry else getattr(msg, "name", "unknown")`.
    Pin behavior: orphan vẫn append với name từ msg.name fallback.
    """
    msgs = [
        _tool_msg("tc_orphan", "output", name="resolve_location"),
    ]
    logs = messages_to_tool_call_logs(msgs)
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "resolve_location"
    assert logs[0]["tool_input"] == ""
    assert logs[0]["tool_output"] == "output"


def test_msg_to_logs_handles_missing_tool_call_id():
    """ToolMessage không có tool_call_id → dùng name fallback."""
    msg = SimpleNamespace(type="tool", content="x", name="my_tool")
    # tool_call_id attr không tồn tại
    logs = messages_to_tool_call_logs([msg])
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "my_tool"


def test_msg_to_logs_handles_object_style_toolcall():
    """Tool call có thể là dict hoặc object có .id/.name/.args."""
    tc = SimpleNamespace(id="tc_2", name="get_hourly_forecast",
                         args={"hours": 12})
    msgs = [
        _ai_msg([tc]),
        _tool_msg("tc_2", "[]"),
    ]
    logs = messages_to_tool_call_logs(msgs)
    assert logs[0]["tool_name"] == "get_hourly_forecast"
    assert json.loads(logs[0]["tool_input"]) == {"hours": 12}


def test_msg_to_logs_skips_messages_without_tool_calls():
    """Plain HumanMessage / AIMessage (no tool_calls) không tạo log."""
    msg = SimpleNamespace(type="human", content="hello")
    assert messages_to_tool_call_logs([msg]) == []


# ── ConversationStateStore ──────────────────────────────────────────────────


def test_store_returns_none_when_thread_not_seen():
    store = ConversationStateStore()
    assert store.get("unknown") is None


def test_store_update_creates_state():
    store = ConversationStateStore()
    logs = [
        {"tool_name": "get_current_weather",
         "tool_input": '{"location_hint": "Cầu Giấy"}', "tool_output": ""},
    ]
    state = store.update("th_1", logs, intent="current_weather")
    assert state.location == "Cầu Giấy"
    assert state.intent == "current_weather"
    assert state.turn_count == 1


def test_store_update_increments_turn_count():
    """Store trả cùng object reference qua các lần update — pin behavior này.

    Capture giá trị ngay sau mỗi update vì state là mutable dataclass.
    """
    store = ConversationStateStore()
    logs = [{"tool_name": "x", "tool_input": "{}", "tool_output": ""}]
    s1 = store.update("th_1", logs, intent="a")
    turn_after_first = s1.turn_count
    intent_after_first = s1.intent
    s2 = store.update("th_1", logs, intent="b")
    assert turn_after_first == 1
    assert intent_after_first == "a"
    assert s2.turn_count == 2
    assert s2.intent == "b"
    # Pin: s1 và s2 là same reference (mutated in place)
    assert s1 is s2


def test_store_update_keeps_old_location_when_new_extract_none():
    """Khi tool_call_logs không cho location mới, giữ location cũ."""
    store = ConversationStateStore()
    logs1 = [
        {"tool_name": "get_current_weather",
         "tool_input": '{"location_hint": "Đống Đa"}', "tool_output": ""},
    ]
    store.update("th_1", logs1, intent="a")
    # Lượt 2: tool không có location
    logs2 = [{"tool_name": "smalltalk", "tool_input": "{}", "tool_output": ""}]
    s = store.update("th_1", logs2, intent="b")
    assert s.location == "Đống Đa"  # giữ từ lượt 1


def test_store_ttl_eviction():
    """State quá TTL → get trả None và xóa khỏi store."""
    store = ConversationStateStore(ttl_seconds=0)  # mọi state đều expired
    logs = [{"tool_name": "x", "tool_input": "{}", "tool_output": ""}]
    store.update("th_1", logs, intent="a")
    time.sleep(0.01)
    assert store.get("th_1") is None


def test_store_evict_expired_returns_count():
    store = ConversationStateStore(ttl_seconds=0)
    for tid in ("a", "b", "c"):
        store.update(tid, [], intent="i")
    time.sleep(0.01)
    n = store.evict_expired()
    assert n == 3


def test_to_context_json_shape():
    """Schema phải khớp training data: location/intent/turn (không có turn_count)."""
    s = ConversationState(location="A", intent="i", turn_count=3)
    ctx = s.to_context_json()
    assert ctx == {"location": "A", "intent": "i", "turn": 3}
    # Quan trọng: KHÔNG có "turn_count" key (tránh bias router)
    assert "turn_count" not in ctx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
