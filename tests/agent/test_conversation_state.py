"""Unit tests cho ConversationState v7.1 — multi-turn ChatML history.

Cover:
- record_turn append + sliding window K=3
- to_messages output shape khớp Ollama /api/chat format
- TTL eviction
- store.put/get round-trip
"""

from __future__ import annotations

import json
import time

from app.agent.conversation_state import (
    ConversationState,
    ConversationStateStore,
    get_conversation_store,
)


# ── ConversationState.record_turn / sliding window ──────────────────────────


def test_record_turn_appends_below_window():
    s = ConversationState()
    s.record_turn(
        "u1",
        '{"intent":"current_weather","scope":"city","confidence":0.92,"rewritten_query":null}',
    )
    s.record_turn(
        "u2",
        '{"intent":"daily_forecast","scope":"city","confidence":0.85,"rewritten_query":null}',
    )
    assert len(s.history) == 2
    assert s.turn_count == 2
    assert s.history[0][0] == "u1"
    assert s.history[1][0] == "u2"


def test_record_turn_slides_window_at_k3():
    s = ConversationState()
    for i in range(5):
        s.record_turn(
            f"u{i}",
            f'{{"intent":"x","scope":"city","confidence":0.9,"rewritten_query":null,"i":{i}}}',
        )
    # K=3 → chỉ giữ 3 newest (u2, u3, u4)
    assert len(s.history) == 3
    assert s.turn_count == 5  # turn_count tích lũy không bị cap
    assert [u for u, _ in s.history] == ["u2", "u3", "u4"]


def test_record_turn_updates_timestamp():
    s = ConversationState()
    t0 = s.updated_at
    time.sleep(0.01)
    s.record_turn("u", '{"x":1}')
    assert s.updated_at > t0


# ── to_messages format ──────────────────────────────────────────────────────


def test_to_messages_empty_history():
    s = ConversationState()
    msgs = s.to_messages("SYS", "current question")
    assert msgs == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "current question"},
    ]


def test_to_messages_with_history_one_pair():
    s = ConversationState()
    s.record_turn("u1", '{"intent":"current_weather"}')
    msgs = s.to_messages("SYS", "u2")
    assert msgs == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": '{"intent":"current_weather"}'},
        {"role": "user", "content": "u2"},
    ]


def test_to_messages_caps_at_k3_window():
    """history có 5 pairs (đã slide xuống 3) → messages: system + 3*(u,a) + current."""
    s = ConversationState()
    for i in range(5):
        s.record_turn(f"u{i}", f"a{i}")
    msgs = s.to_messages("SYS", "now")
    # System(1) + 3 cặp (u2,a2,u3,a3,u4,a4) + user_now(1) = 8
    assert len(msgs) == 8
    assert msgs[0] == {"role": "system", "content": "SYS"}
    assert msgs[1] == {"role": "user", "content": "u2"}
    assert msgs[2] == {"role": "assistant", "content": "a2"}
    assert msgs[-1] == {"role": "user", "content": "now"}


# ── ConversationStateStore.get/put + TTL ───────────────────────────────────


def test_store_put_get_roundtrip():
    store = ConversationStateStore(ttl_seconds=60)
    s = ConversationState()
    s.record_turn("u1", "a1")
    store.put("th_a", s)

    got = store.get("th_a")
    assert got is not None
    assert got.history == [("u1", "a1")]
    assert got.turn_count == 1


def test_store_get_returns_none_for_unknown_thread():
    store = ConversationStateStore(ttl_seconds=60)
    assert store.get("never-seen") is None


def test_store_ttl_evicts_expired():
    store = ConversationStateStore(ttl_seconds=1)
    s = ConversationState()
    s.record_turn("u1", "a1")
    store.put("th_a", s)
    # Force expire bằng cách ép updated_at lùi quá TTL
    s.updated_at = time.time() - 5
    assert store.get("th_a") is None


def test_store_evict_expired_returns_count():
    store = ConversationStateStore(ttl_seconds=1)
    s1, s2 = ConversationState(), ConversationState()
    store.put("a", s1)
    store.put("b", s2)
    s1.updated_at = time.time() - 100
    s2.updated_at = time.time() - 100
    assert store.evict_expired() == 2
    assert store.get("a") is None
    assert store.get("b") is None


def test_store_singleton_returns_same_instance():
    a = get_conversation_store()
    b = get_conversation_store()
    assert a is b


# ── Round-trip: record_turn + put + get + to_messages ───────────────────────


def test_full_roundtrip_three_turn_dialog():
    """Simulate 3-turn dialog persisted qua store, build messages cho turn 3."""
    store = ConversationStateStore(ttl_seconds=60)

    # Turn 1
    s = ConversationState()
    s.record_turn(
        "Thời tiết phường Cầu Giấy thứ 2 tuần sau",
        json.dumps(
            {
                "intent": "daily_forecast",
                "scope": "ward",
                "confidence": 0.92,
                "rewritten_query": "Thời tiết Phường Cầu Giấy thứ 2 tuần sau",
            },
            ensure_ascii=False,
        ),
    )
    store.put("session", s)

    # Turn 2 (load lại từ store)
    s2 = store.get("session")
    assert s2 is not None
    s2.record_turn(
        "thứ 3 thì sao?",
        json.dumps(
            {
                "intent": "daily_forecast",
                "scope": "ward",
                "confidence": 0.80,
                "rewritten_query": "Thời tiết Phường Cầu Giấy thứ 3 tuần sau",
            },
            ensure_ascii=False,
        ),
    )
    store.put("session", s2)

    # Turn 3 — build messages cho user query mới
    s3 = store.get("session")
    assert s3 is not None
    msgs = s3.to_messages("PROMPT", "Quận Cầu Giấy thì sao?")
    # System + 2*(u,a) + user_now = 6
    assert len(msgs) == 6
    assert msgs[0]["role"] == "system"
    assert msgs[1]["content"] == "Thời tiết phường Cầu Giấy thứ 2 tuần sau"
    assert "Phường Cầu Giấy thứ 2 tuần sau" in msgs[2]["content"]
    assert msgs[3]["content"] == "thứ 3 thì sao?"
    assert "Phường Cầu Giấy thứ 3 tuần sau" in msgs[4]["content"]
    assert msgs[5]["content"] == "Quận Cầu Giấy thì sao?"
    assert s3.turn_count == 2  # 2 record_turn calls trên session


def test_history_pair_serialization_4_keys_format():
    """Assistant content phải JSON parseable với đúng 4 keys core."""
    s = ConversationState()
    asst = json.dumps(
        {
            "intent": "rain_query",
            "scope": "ward",
            "confidence": 0.85,
            "rewritten_query": "Phường Cầu Giấy có mưa không?",
        },
        ensure_ascii=False,
    )
    s.record_turn("u", asst)

    parsed = json.loads(s.history[0][1])
    assert set(parsed.keys()) == {"intent", "scope", "confidence", "rewritten_query"}
