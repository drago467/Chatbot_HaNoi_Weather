"""R18 (2026-05-09): 7 placeholder-templated exemplars validation.

Trước R18: 13 exemplars với hardcoded date (2026-04-21, 2026-04-22, 2026-05-15)
→ rot khi today thay đổi. Sau R18: 7 exemplars + ALL placeholders
({today_iso}, {tomorrow_iso}, {today_date}, {today_weekday}, {today_time},
{this_saturday}, ...) substitute trong _format_few_shot_block bằng cùng ctx
datetime với BASE prompt.

7 patterns chọn theo diversity (research: ARISE/AdaptAgent saturate 3-8):
1. In-horizon baseline + verify ngày cover
2. Out-of-horizon refuse
3. Past-frame → history
4. Superlative → daily_summary
5. Multi-part decomposition
6. Phenomena whitelist
7. Compare 2 locations + future (P11 wrapper)

Drop từ R17 (redundant pattern):
- compositional time (merged vào #1 templated)
- empty success refuse (covered POLICY 3.1)
- numeric weekday tuần sau (variant của #1 sau khi templated)
- sáng ngày kia (variant #1)
- scope transparency (covered POLICY 3.5/3.12)
- bare-form weekday past (variant #3)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FEW_SHOT_PATH = Path(__file__).resolve().parents[2] / "app" / "config" / "few_shot_examples.json"


@pytest.fixture(scope="module")
def data() -> dict:
    with FEW_SHOT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# Structural tests
# ─────────────────────────────────────────────────────────────────────

def test_examples_key_exists(data):
    assert "examples" in data
    assert isinstance(data["examples"], list)


def test_seven_exemplars(data):
    """R18: 7 exemplars (giảm từ 13, drop 6 redundant)."""
    assert len(data["examples"]) == 7, (
        f"Expected 7 exemplars (R18 redesign), got {len(data['examples'])}"
    )


def test_exemplar_fields(data):
    """Mỗi exemplar có đủ 6 fields."""
    required = {"title", "user", "thought", "action", "observation", "response_prefix"}
    for i, ex in enumerate(data["examples"]):
        missing = required - set(ex.keys())
        assert not missing, f"Exemplar #{i} ({ex.get('title','?')}) missing fields: {missing}"


def test_exemplar_titles_unique(data):
    titles = [ex["title"] for ex in data["examples"]]
    assert len(titles) == len(set(titles)), f"Duplicate titles: {titles}"


# ─────────────────────────────────────────────────────────────────────
# No hardcoded dates rule (R18 core invariant)
# ─────────────────────────────────────────────────────────────────────

# Match YYYY-MM-DD or DD/MM/YYYY but only if year looks like a real year
_DATE_PATTERN_ISO = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_DATE_PATTERN_DMY = re.compile(r"\b\d{1,2}/\d{1,2}/20\d{2}\b")


def test_no_hardcoded_iso_dates(data):
    """Không có date dạng YYYY-MM-DD trong field nào.

    Ngoại lệ: "today + N days" comments/templates OK; nhưng raw 2026-04-21 NO.
    R18 invariant: date phải là placeholder {today_iso}, {tomorrow_iso}, ...
    """
    fields_to_check = ("user", "thought", "action", "observation", "response_prefix")
    violations = []
    for i, ex in enumerate(data["examples"]):
        for f in fields_to_check:
            val = ex.get(f, "")
            for m in _DATE_PATTERN_ISO.finditer(val):
                violations.append((i, ex.get("title", "?"), f, m.group(0)))
    assert not violations, f"Hardcoded ISO dates: {violations}"


def test_no_hardcoded_dmy_dates(data):
    """Không có date dạng DD/MM/YYYY hardcoded."""
    fields_to_check = ("user", "thought", "action", "observation", "response_prefix")
    violations = []
    for i, ex in enumerate(data["examples"]):
        for f in fields_to_check:
            val = ex.get(f, "")
            for m in _DATE_PATTERN_DMY.finditer(val):
                violations.append((i, ex.get("title", "?"), f, m.group(0)))
    assert not violations, f"Hardcoded DMY dates: {violations}"


def test_uses_placeholders_for_dates(data):
    """Ít nhất 1 exemplar phải dùng placeholder date format `{...iso}` / `{...date}`."""
    placeholder_re = re.compile(r"\{(?:today|tomorrow|yesterday|day_after_tomorrow|day_before_yesterday|this_saturday|this_sunday|next_week|prev_week|week)[\w_]*\}")
    found_count = 0
    for ex in data["examples"]:
        joined = " ".join(ex.get(f, "") for f in ("user", "thought", "action", "observation", "response_prefix"))
        if placeholder_re.search(joined):
            found_count += 1
    assert found_count >= 5, (
        f"Expected ≥5 exemplars dùng placeholders date, got {found_count}"
    )


# ─────────────────────────────────────────────────────────────────────
# Per-exemplar pattern coverage (7 distinct patterns)
# ─────────────────────────────────────────────────────────────────────

def test_exemplar_1_in_horizon(data):
    """Ex 1: in-horizon single-day baseline + verify 'ngày cover'."""
    ex = data["examples"][0]
    title_lower = ex["title"].lower()
    assert "in-horizon" in title_lower or "single-day" in title_lower
    # Action: get_daily_forecast với placeholder start_date
    assert "get_daily_forecast" in ex["action"]
    assert "{tomorrow_iso}" in ex["action"]
    # Thought reference verify ngày cover
    assert "ngày cover" in ex["thought"].lower() or "verify" in ex["thought"].lower()


def test_exemplar_2_out_of_horizon(data):
    """Ex 2: out-of-horizon refuse."""
    ex = data["examples"][1]
    title_lower = ex["title"].lower()
    assert "out-of-horizon" in title_lower or "refuse" in title_lower
    # Thought mentions 8-day forecast limit
    assert "8" in ex["thought"] or "horizon" in ex["thought"].lower()
    # Response refuses politely
    response_lower = ex["response_prefix"].lower()
    assert any(w in response_lower for w in ("chỉ dự báo", "tối đa", "chưa có data", "còn xa"))


def test_exemplar_3_past_frame(data):
    """Ex 3: past-frame → get_weather_history."""
    ex = data["examples"][2]
    title_lower = ex["title"].lower()
    assert "past-frame" in title_lower or "đã qua" in title_lower
    # User asks past frame ("chiều nay" at evening)
    assert "chiều nay" in ex["user"].lower()
    # Action: get_weather_history with templated date
    assert "get_weather_history" in ex["action"]
    assert "{today_iso}" in ex["action"]
    # Response acknowledges past
    assert "đã qua" in ex["response_prefix"].lower()


def test_exemplar_4_superlative(data):
    """Ex 4: superlative → get_daily_summary."""
    ex = data["examples"][3]
    title_lower = ex["title"].lower()
    assert "superlative" in title_lower or "cả ngày" in title_lower
    # User has superlative word
    assert any(k in ex["user"].lower() for k in ("trung bình", "mạnh nhất", "max", "min"))
    # Action: daily_summary with templated date
    assert "get_daily_summary" in ex["action"]
    assert "{today_iso}" in ex["action"]
    # Observation has 'tổng hợp' key
    assert "tổng hợp" in ex["observation"]


def test_exemplar_5_multi_part(data):
    """Ex 5: multi-part — calls 2 tools in 1 turn."""
    ex = data["examples"][4]
    title_lower = ex["title"].lower()
    assert "multi-part" in title_lower or "aspects" in title_lower or "2" in title_lower
    # User has "và" connector
    assert "và" in ex["user"].lower()
    # Action shows both tools
    assert "get_weather_alerts" in ex["action"]
    assert "get_daily_forecast" in ex["action"]
    # Response numbers aspects
    assert "(1)" in ex["response_prefix"] and "(2)" in ex["response_prefix"]


def test_exemplar_6_phenomena_whitelist(data):
    """Ex 6: phenomena whitelist — không bịa nắng từ heuristic."""
    ex = data["examples"][5]
    title_lower = ex["title"].lower()
    assert "phenomena" in title_lower or "whitelist" in title_lower or "nắng" in title_lower
    # User asks về nắng
    assert "nắng" in ex["user"].lower()
    # Thought references POLICY 3.10 + UV/mây criteria
    assert "3.10" in ex["thought"] or "whitelist" in ex["thought"].lower()
    assert "uv" in ex["thought"].lower() and "mây" in ex["thought"].lower()
    # Action: get_current_weather (snapshot for "bây giờ")
    assert "get_current_weather" in ex["action"]
    # Response refuses despite being asked
    response_lower = ex["response_prefix"].lower()
    assert "không" in response_lower and "nắng" in response_lower


def test_exemplar_7_compare_future(data):
    """Ex 7: compare 2 locations + future → 1 call compare_weather_forecast."""
    ex = data["examples"][6]
    title_lower = ex["title"].lower()
    assert "compare" in title_lower or "so sánh" in title_lower
    # User asks comparison + future
    user_lower = ex["user"].lower()
    assert "so sánh" in user_lower
    assert any(w in user_lower for w in ("cuối tuần", "ngày mai", "tuần tới", "tối nay"))
    # Action: 1 call compare_weather_forecast (NOT 2× daily_forecast)
    assert "compare_weather_forecast" in ex["action"]
    assert ex["action"].count("compare_weather_forecast") == 1
    # Uses templated start_date
    assert "{this_saturday}" in ex["action"]
    # Response synthesizes both locations
    response_lower = ex["response_prefix"].lower()
    assert "minh châu" in response_lower and "cầu giấy" in response_lower


# ─────────────────────────────────────────────────────────────────────
# Format integrity — exemplar phải format được với ctx datetime thực
# ─────────────────────────────────────────────────────────────────────

def test_exemplars_format_with_runtime_context():
    """Mỗi exemplar phải format được không lỗi với ctx datetime thật.

    R18 critical invariant: nếu format() raise KeyError, có placeholder
    chưa được handle trong _build_runtime_context(). Test guard chống regression.
    """
    from app.agent._prompt_builder import _build_runtime_context, _format_few_shot_block

    ctx = _build_runtime_context()
    block = _format_few_shot_block(ctx)

    # Block phải chứa số ngày substituted (không còn placeholder text)
    # Placeholder failure → block chứa raw `{tomorrow_iso}` literal
    assert "{tomorrow_iso}" not in block, "Placeholder {tomorrow_iso} chưa substitute"
    assert "{today_iso}" not in block, "Placeholder {today_iso} chưa substitute"
    assert "{this_saturday}" not in block, "Placeholder {this_saturday} chưa substitute"
    # Block phải chứa ít nhất 1 ngày dạng YYYY-MM-DD đã substituted
    assert _DATE_PATTERN_ISO.search(block), "Block không có ngày substituted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
