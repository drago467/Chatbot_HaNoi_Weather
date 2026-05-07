"""Integration test 3-turn dialog v7.1 — kiểm history pipeline end-to-end.

Mock SLMRouter._call_ollama (HTTP) để verify:
- Turn 1 (no history) → message gửi 2 msgs (system + user)
- Turn 2 (history=[turn1_pair]) → 4 msgs (system + u1 + a1 + user_now)
- Turn 3 (history=[turn1, turn2]) → 6 msgs
- ConversationStateStore persist history qua các lượt
"""

from __future__ import annotations

import json
import pytest

from app.agent.conversation_state import (
    ConversationState,
    ConversationStateStore,
)
from app.agent.router.slm_router import SLMRouter


class _CapturingMockClient:
    """Mock httpx.Client capture từng payload + lần lượt trả raw_text khác nhau."""

    def __init__(self, response_texts):
        self._responses = list(response_texts)
        self.captured_payloads = []

    def post(self, url, json=None):  # noqa: A002
        self.captured_payloads.append(json)
        return _MockResponse({"message": {"content": self._responses.pop(0)}})

    def close(self):
        pass


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _asst_json(intent, scope, conf, rewrite):
    return json.dumps(
        {
            "intent": intent,
            "scope": scope,
            "confidence": conf,
            "rewritten_query": rewrite,
        },
        ensure_ascii=False,
    )


def test_three_turn_dialog_preserves_anchor():
    """Simulate user thực sự agent_routed flow:

    Turn 1: "Phường Cầu Giấy thứ 2 tuần sau" — no history → router rewrite preserves prefix+time
    Turn 2: "thứ 3 thì sao?" — history=[turn1] → router phải nhận messages có turn 1 assistant_json
    Turn 3: "Quận Cầu Giấy thì sao?" — history=[turn1, turn2] → switch scope district
    """
    # Mock 3 router responses
    mock_responses = [
        _asst_json("daily_forecast", "ward", 0.92, "Thời tiết Phường Cầu Giấy thứ 2 tuần sau"),
        _asst_json("daily_forecast", "ward", 0.80, "Thời tiết Phường Cầu Giấy thứ 3 tuần sau"),
        _asst_json("daily_forecast", "district", 0.85, "Thời tiết Quận Cầu Giấy thứ 3 tuần sau"),
    ]
    mock_client = _CapturingMockClient(mock_responses)

    router = SLMRouter(ollama_base_url="http://test:11434", model="hanoi-weather-router")
    router._client = mock_client

    store = ConversationStateStore(ttl_seconds=3600)
    thread = "session"

    # ── Turn 1 ──
    state = store.get(thread)
    rr1 = router.classify("Thời tiết phường Cầu Giấy thứ 2 tuần sau", context=state)
    assert rr1.intent == "daily_forecast"
    assert rr1.scope == "ward"
    assert "Phường Cầu Giấy thứ 2 tuần sau" in rr1.rewritten_query

    # Caller record turn (giống agent.py Step 2.5)
    if state is None:
        state = ConversationState()
    state.record_turn(
        "Thời tiết phường Cầu Giấy thứ 2 tuần sau",
        _asst_json(rr1.intent, rr1.scope, round(rr1.confidence, 2), rr1.rewritten_query),
    )
    store.put(thread, state)

    # Verify turn 1 payload: 2 msgs (no history yet)
    payload1 = mock_client.captured_payloads[0]
    assert len(payload1["messages"]) == 2
    assert payload1["messages"][0]["role"] == "system"
    assert payload1["messages"][1]["role"] == "user"

    # ── Turn 2 ──
    state = store.get(thread)
    assert state is not None
    assert len(state.history) == 1
    rr2 = router.classify("thứ 3 thì sao?", context=state)
    assert "Phường Cầu Giấy thứ 3 tuần sau" in rr2.rewritten_query

    state.record_turn(
        "thứ 3 thì sao?",
        _asst_json(rr2.intent, rr2.scope, round(rr2.confidence, 2), rr2.rewritten_query),
    )
    store.put(thread, state)

    # Verify turn 2 payload: 4 msgs (system + u1 + a1 + user_now)
    payload2 = mock_client.captured_payloads[1]
    assert len(payload2["messages"]) == 4
    assert payload2["messages"][0]["role"] == "system"
    assert payload2["messages"][1] == {
        "role": "user",
        "content": "Thời tiết phường Cầu Giấy thứ 2 tuần sau",
    }
    # Assistant content phải là JSON 4 keys của turn 1
    asst_content = payload2["messages"][2]["content"]
    parsed = json.loads(asst_content)
    assert set(parsed.keys()) == {"intent", "scope", "confidence", "rewritten_query"}
    assert "Phường Cầu Giấy thứ 2 tuần sau" in parsed["rewritten_query"]
    assert payload2["messages"][3] == {"role": "user", "content": "thứ 3 thì sao?"}

    # ── Turn 3 ──
    state = store.get(thread)
    assert state is not None
    assert len(state.history) == 2
    rr3 = router.classify("Quận Cầu Giấy thì sao?", context=state)
    assert rr3.scope == "district"
    assert "Quận Cầu Giấy" in rr3.rewritten_query

    state.record_turn(
        "Quận Cầu Giấy thì sao?",
        _asst_json(rr3.intent, rr3.scope, round(rr3.confidence, 2), rr3.rewritten_query),
    )
    store.put(thread, state)

    # Verify turn 3 payload: 6 msgs (system + 2 pairs + user_now)
    payload3 = mock_client.captured_payloads[2]
    assert len(payload3["messages"]) == 6
    assert payload3["messages"][-1]["content"] == "Quận Cầu Giấy thì sao?"
    # Cả 2 history pair đều đã chứa rewrite có "Phường Cầu Giấy"
    assert "Phường Cầu Giấy" in payload3["messages"][2]["content"]
    assert "Phường Cầu Giấy thứ 3 tuần sau" in payload3["messages"][4]["content"]

    # ── Final state assertions ──
    final = store.get(thread)
    assert final is not None
    assert len(final.history) == 3
    assert final.turn_count == 3
    # Pair cuối phải khớp turn 3 output
    last_user, last_asst = final.history[-1]
    assert last_user == "Quận Cầu Giấy thì sao?"
    last_asst_parsed = json.loads(last_asst)
    assert last_asst_parsed["scope"] == "district"


def test_window_caps_at_k3_after_4_turns():
    """5 lượt → store giữ lại 3 lượt mới nhất → router payload có max 3 history pairs."""
    mock_responses = [
        _asst_json("current_weather", "city", 0.92, None) for _ in range(5)
    ]
    mock_client = _CapturingMockClient(mock_responses)
    router = SLMRouter(ollama_base_url="http://test:11434", model="hanoi-weather-router")
    router._client = mock_client

    store = ConversationStateStore(ttl_seconds=3600)
    thread = "long-thread"

    for i in range(5):
        state = store.get(thread) or ConversationState()
        rr = router.classify(f"q{i}", context=state)
        state.record_turn(
            f"q{i}",
            _asst_json(rr.intent, rr.scope, round(rr.confidence, 2), rr.rewritten_query),
        )
        store.put(thread, state)

    # Turn 5 (i=4) payload: state có 4 prior turns nhưng đã slide xuống 3
    # → messages: system + 3 pairs + user_now = 8
    last_payload = mock_client.captured_payloads[-1]
    assert len(last_payload["messages"]) == 8
    # Oldest pair trong window phải là q1 (q0 đã bị slide ra)
    assert last_payload["messages"][1]["content"] == "q1"
    assert last_payload["messages"][-1]["content"] == "q4"

    # State final: history 3 pairs
    final = store.get(thread)
    assert len(final.history) == 3
    assert final.turn_count == 5  # tích lũy đầy đủ
