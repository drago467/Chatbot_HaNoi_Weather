"""R12 L3 + R16 (audit C1 fix): 11 shared exemplars validation.

Tests:
- 11 exemplars trong top-level "examples" key (R11 4 + R12 3 + 2 off-by-one fixes + R16 P3 + R16 P4)
- Mỗi exemplar có đủ fields: title, user, thought, action, observation, response_prefix
- 3 exemplars mới cover F1/F2/F6 (past-frame, superlative, multi-part)
- Exemplar 8: numeric weekday tuần sau (fix off-by-one bug)
- Exemplar 9: time-of-day + ngày kia (fix date off-by-one + aggregate→hourly hallucinate)
- Exemplar 10: phenomena whitelist — output không có nắng → KHÔNG bịa (R16 audit P3)
- Exemplar 11: scope transparency — tool cover < user hỏi → disclaim mở đầu (R16 audit P4)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FEW_SHOT_PATH = Path(__file__).resolve().parents[2] / "app" / "config" / "few_shot_examples.json"


@pytest.fixture(scope="module")
def data() -> dict:
    with FEW_SHOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_examples_key_exists(data):
    assert "examples" in data
    assert isinstance(data["examples"], list)


def test_eleven_exemplars(data):
    """R12 L3 + R16: 4 R11 + 3 R12 + 2 off-by-one + R16 P3 phenomena + R16 P4 scope = 11."""
    assert len(data["examples"]) == 11, (
        f"Expected 11 exemplars, got {len(data['examples'])}"
    )


def test_exemplar_8_numeric_weekday(data):
    """Exemplar 8: numeric weekday tuần sau → COPY từ next_week_table (fix off-by-one)."""
    ex = data["examples"][7]
    title_lower = ex["title"].lower()
    assert "numeric weekday" in title_lower or "next_week_table" in title_lower
    # User dùng "thứ 4" (numeric, không phải "Thứ Tư")
    assert "thứ 4" in ex["user"].lower()
    # Thought đề cập 3-alias mapping
    assert "T4" in ex["thought"] and "Thứ Tư" in ex["thought"]
    # Reference next_week_table
    assert "next_week_table" in ex["thought"]
    # Action gọi daily_forecast
    assert "get_daily_forecast" in ex["action"]


def test_exemplar_9_time_of_day_day_after_tomorrow(data):
    """Exemplar 9: 'sáng ngày kia' → daily_forecast(start_date=day_after_tomorrow_iso) + anti-hallucinate aggregate."""
    ex = data["examples"][8]
    # User pattern: time-of-day + ngày kia
    assert "sáng" in ex["user"].lower()
    assert "ngày kia" in ex["user"].lower()
    # Thought reference day_after_tomorrow_iso
    assert "day_after_tomorrow_iso" in ex["thought"]
    # Anti-hallucinate signal
    thought_lower = ex["thought"].lower()
    assert "khÔng bịa".lower() in thought_lower or "không bịa" in thought_lower or "cấm" in thought_lower
    # Action: daily_forecast (per design intent for time-of-day on future day)
    assert "get_daily_forecast" in ex["action"]
    # Response chỉ COPY aggregate
    response_lower = ex["response_prefix"].lower()
    assert "sáng" in response_lower


def test_exemplar_10_phenomena_whitelist(data):
    """Exemplar 10: phenomena whitelist — output không có UV cao + mây thấp → KHÔNG bịa nắng (R16 audit P3)."""
    ex = data["examples"][9]
    title_lower = ex["title"].lower()
    assert "phenomena" in title_lower or "whitelist" in title_lower or "nắng" in title_lower
    # User asks about "nắng"
    assert "nắng" in ex["user"].lower()
    # Thought references POLICY 3.10 + UV/mây whitelist condition
    thought_lower = ex["thought"].lower()
    assert "3.10" in ex["thought"] or "whitelist" in thought_lower
    assert "uv" in thought_lower and ("mây" in thought_lower or "may" in thought_lower)
    # Action: get_current_weather (snapshot for "bây giờ")
    assert "get_current_weather" in ex["action"]
    # Response refuses to assert nắng despite being asked
    response_lower = ex["response_prefix"].lower()
    assert "không" in response_lower or "khong" in response_lower
    assert "nắng" in response_lower


def test_exemplar_11_scope_transparency(data):
    """Exemplar 11: tool cover < user hỏi → BẮT BUỘC disclaim mở đầu (R16 audit P4)."""
    ex = data["examples"][10]
    title_lower = ex["title"].lower()
    assert "scope" in title_lower or "transparency" in title_lower or "cover" in title_lower or "disclaim" in title_lower
    # User asks về range "X ngày tới" (multi-day)
    assert "ngày tới" in ex["user"].lower() or "tuần" in ex["user"].lower()
    # Thought references POLICY 3.12 + verify ngày cover
    assert "3.12" in ex["thought"]
    # Response opens with disclaim about coverage gap
    response_lower = ex["response_prefix"].lower()
    assert any(w in response_lower for w in ("chỉ cover", "chỉ có", "chưa đủ", "không đủ"))


def test_exemplar_fields(data):
    """Mỗi exemplar có đủ 6 fields."""
    required = {"title", "user", "thought", "action", "observation", "response_prefix"}
    for i, ex in enumerate(data["examples"]):
        missing = required - set(ex.keys())
        assert not missing, f"Exemplar #{i} ({ex.get('title','?')}) missing fields: {missing}"


def test_exemplar_5_past_frame(data):
    """Exemplar 5: past-frame refuse with get_weather_history."""
    ex = data["examples"][4]
    assert "past-frame" in ex["title"].lower() or "đã qua" in ex["title"].lower()
    # User asks "chiều nay" — a past frame at 21:00
    assert "chiều nay" in ex["user"].lower()
    # Action must call weather_history (not hourly_forecast)
    assert "get_weather_history" in ex["action"]
    # Response acknowledges "đã qua"
    assert "đã qua" in ex["response_prefix"].lower()


def test_exemplar_6_superlative(data):
    """Exemplar 6: superlative → daily_summary, not current_weather snapshot."""
    ex = data["examples"][5]
    assert "superlative" in ex["title"].lower() or "cả ngày" in ex["title"].lower()
    # User query has superlative word
    assert any(k in ex["user"].lower() for k in ("trung bình", "mạnh nhất", "max", "min"))
    # Action uses daily_summary (not get_current_weather)
    assert "get_daily_summary" in ex["action"]
    # Observation has "tổng hợp" key
    assert "tổng hợp" in ex["observation"]


def test_exemplar_7_multi_part(data):
    """Exemplar 7: multi-part, calls 2 tools in 1 turn."""
    ex = data["examples"][6]
    assert "multi-part" in ex["title"].lower() or "aspects" in ex["title"].lower() or "2" in ex["title"]
    # User query has "và" connector
    assert "và" in ex["user"].lower()
    # Action shows both tools
    assert "get_weather_alerts" in ex["action"]
    assert "get_daily_forecast" in ex["action"]
    # Response numbers the aspects
    assert "(1)" in ex["response_prefix"] and "(2)" in ex["response_prefix"]


def test_exemplar_titles_unique(data):
    """Mỗi exemplar có title unique."""
    titles = [ex["title"] for ex in data["examples"]]
    assert len(titles) == len(set(titles)), f"Duplicate titles: {titles}"


def test_r11_exemplars_retained(data):
    """R11 4 exemplars (in-horizon, compositional, out-of-horizon, empty) vẫn có."""
    titles_lower = [ex["title"].lower() for ex in data["examples"]]
    joined = " | ".join(titles_lower)
    assert "in-horizon" in joined
    assert "compositional" in joined or "verify" in joined
    assert "out-of-horizon" in joined
    assert "empty" in joined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
