"""SLMRouter v7.1 — kiểm shape ChatML messages + parser strip thinking tag."""

from __future__ import annotations

import json

import pytest

from app.agent.conversation_state import ConversationState
from app.agent.router.slm_router import SLMRouter


@pytest.fixture
def router():
    return SLMRouter(
        ollama_base_url="http://test:11434",
        model="hanoi-weather-router",
    )


# ── _build_messages ─────────────────────────────────────────────────────────


def test_build_messages_no_state(router):
    msgs = router._build_messages("Cầu Giấy hôm nay?", state=None)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Cầu Giấy hôm nay?"}


def test_build_messages_empty_history(router):
    state = ConversationState()
    msgs = router._build_messages("q", state=state)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"


def test_build_messages_with_history_caps_at_k3(router):
    state = ConversationState()
    for i in range(5):
        state.record_turn(f"u{i}", f"a{i}")
    msgs = router._build_messages("now", state=state)
    # system + 3 pairs + user_now = 8
    assert len(msgs) == 8
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "u2"}  # oldest in window
    assert msgs[-1] == {"role": "user", "content": "now"}


# ── _parse_response ─────────────────────────────────────────────────────────


def test_parse_response_plain_json(router):
    text = '{"intent":"current_weather","scope":"ward","confidence":0.92,"rewritten_query":null}'
    parsed = router._parse_response(text)
    assert parsed == {
        "intent": "current_weather",
        "scope": "ward",
        "confidence": 0.92,
        "rewritten_query": None,
    }


def test_parse_response_strips_qwen3_thinking_tag(router):
    text = (
        "<think>\nUser hỏi thời tiết... đây là current_weather, scope ward.\n</think>\n"
        '{"intent":"current_weather","scope":"ward","confidence":0.92,"rewritten_query":null}'
    )
    parsed = router._parse_response(text)
    assert parsed is not None
    assert parsed["intent"] == "current_weather"
    assert parsed["scope"] == "ward"


def test_parse_response_strips_thinking_with_multiline_content(router):
    text = (
        "<think>line1\nline2\n  line3</think>"
        '\n{"intent":"weather_alert","scope":"city","confidence":0.85,"rewritten_query":null}'
    )
    parsed = router._parse_response(text)
    assert parsed["intent"] == "weather_alert"


def test_parse_response_handles_text_before_json(router):
    text = "Some preamble text {\"intent\":\"rain_query\",\"scope\":\"ward\",\"confidence\":0.85}"
    parsed = router._parse_response(text)
    assert parsed is not None
    assert parsed["intent"] == "rain_query"


def test_parse_response_returns_none_for_garbage(router):
    assert router._parse_response("not json at all") is None
    assert router._parse_response("") is None


# ── classify integration with mocked Ollama ─────────────────────────────────


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _MockClient:
    def __init__(self, response_text):
        self._response_text = response_text
        self.last_payload = None

    def post(self, url, json=None):  # noqa: A002
        self.last_payload = json
        return _MockResponse({"message": {"content": self._response_text}})

    def close(self):
        pass


def test_classify_passes_messages_array_to_ollama(router):
    """classify() phải gửi `messages` array thay vì `[CONTEXT: {...}]` injection."""
    raw_json = '{"intent":"current_weather","scope":"ward","confidence":0.92,"rewritten_query":"Phường Cầu Giấy hôm nay"}'
    mock = _MockClient(raw_json)
    router._client = mock

    state = ConversationState()
    state.record_turn(
        "Phường Cầu Giấy hôm qua",
        '{"intent":"historical_weather","scope":"ward","confidence":0.85,"rewritten_query":null}',
    )

    rr = router.classify("Phường Cầu Giấy hôm nay?", context=state)

    assert mock.last_payload is not None
    assert "messages" in mock.last_payload
    assert mock.last_payload["messages"][0]["role"] == "system"
    # phải chứa history pair của turn trước
    assert any(
        m["role"] == "assistant" and "historical_weather" in m["content"]
        for m in mock.last_payload["messages"]
    )
    # cuối là current user query
    assert mock.last_payload["messages"][-1] == {
        "role": "user",
        "content": "Phường Cầu Giấy hôm nay?",
    }
    # Result parse đúng
    assert rr.intent == "current_weather"
    assert rr.scope == "ward"
    assert rr.rewritten_query == "Phường Cầu Giấy hôm nay"


def test_classify_strips_thinking_in_real_response(router):
    raw = (
        "<think>Phải phân loại là current_weather scope ward</think>\n"
        '{"intent":"current_weather","scope":"ward","confidence":0.92,"rewritten_query":null}'
    )
    router._client = _MockClient(raw)

    rr = router.classify("Cầu Giấy thế nào?", context=None)
    assert rr.intent == "current_weather"
    assert rr.scope == "ward"
    assert rr.fallback_reason is None


def test_classify_no_state_sends_2_msg_payload(router):
    raw = '{"intent":"smalltalk_weather","scope":"city","confidence":0.85,"rewritten_query":null}'
    mock = _MockClient(raw)
    router._client = mock

    rr = router.classify("xin chào", context=None)
    assert len(mock.last_payload["messages"]) == 2
    assert mock.last_payload["messages"][0]["role"] == "system"
    assert mock.last_payload["messages"][1] == {"role": "user", "content": "xin chào"}
    assert rr.intent == "smalltalk_weather"


def test_classify_temperature_zero_options_present(router):
    """Quan trọng: temperature=0 đảm bảo deterministic, num_predict=256 cho thinking."""
    raw = '{"intent":"current_weather","scope":"city","confidence":0.92,"rewritten_query":null}'
    mock = _MockClient(raw)
    router._client = mock

    router.classify("q", context=None)
    opts = mock.last_payload.get("options", {})
    assert opts.get("temperature") == 0.0
    assert opts.get("num_predict") == 256
