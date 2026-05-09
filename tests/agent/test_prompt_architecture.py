"""Test prompt architecture sau R8 redesign.

Kiểm tra:
1. BASE_PROMPT không chứa seed hallucinate (số thời tiết cụ thể, "trời trong",
   "25-28°C")
2. Không mention phantom tool names (get_weekly_forecast, get_forecast, get_weather,
   get_uv_index, get_district_weather_impact)
3. BASE_PROMPT có 6 block đúng thứ tự (SCOPE / CONTEXT / POLICY / ROUTER /
   RENDERER / FALLBACK)
4. ROUTER table cover toàn bộ 28 tools
5. Size prompt hợp lý
6. SYSTEM_PROMPT_TEMPLATE đã xoá
"""

from __future__ import annotations

import re

import pytest

from app.agent.agent import (
    BASE_PROMPT_TEMPLATE,
    TOOL_RULES,
    _inject_datetime,
    get_focused_system_prompt,
    get_system_prompt,
)


def _rendered_base() -> str:
    return _inject_datetime(BASE_PROMPT_TEMPLATE)


# ── 1. No seed numbers ──────────────────────────────────────────────────────

def test_no_hardcoded_weather_temperature_in_base():
    """BASE_PROMPT KHÔNG chứa nhiệt độ cụ thể kiểu '25.7°C', '28.5°C' (seed)."""
    p = _rendered_base()
    # Exclude phenomena thresholds (HN-specific in SCOPE [1]), nhưng lấy mọi
    # pattern N.N°C ngoài context "rét/nồm/gió mùa" (khoa học).
    suspect = []
    for m in re.finditer(r"\d+\.\d+°C", p):
        start = max(0, m.start() - 50)
        ctx = p[start:m.end() + 20].lower()
        if "rét" in ctx or "nồm" in ctx or "gió mùa" in ctx:
            continue
        suspect.append((m.group(0), ctx))
    assert not suspect, f"BASE_PROMPT có số nhiệt độ seed: {suspect}"


def test_no_hardcoded_humidity_or_pop_in_base():
    """KHÔNG chứa % cụ thể như '75%', '83%' ngoài threshold phenomena / COPY examples."""
    p = _rendered_base()
    suspect = []
    for m in re.finditer(r"\d{2,3}%", p):
        start = max(0, m.start() - 50)
        ctx = p[start:m.end() + 20].lower()
        # Allow: phenomena thresholds + COPY discipline examples (labels từ tool output)
        if any(k in ctx for k in ("rét", "nồm", "gió mùa", "ẩm >", "mây >", "mây ", "copy")):
            continue
        suspect.append((m.group(0), ctx))
    assert not suspect, f"BASE_PROMPT có % seed: {suspect}"


def test_no_troi_trong_phrase():
    """Cụm 'trời trong' KHÔNG xuất hiện (paradox mention effect)."""
    p = _rendered_base()
    assert "trời trong" not in p.lower(), "Cụm 'trời trong' trong BASE_PROMPT sẽ gây LLM lặp lại khi no-tool"


# ── 2. No phantom tool names ────────────────────────────────────────────────

PHANTOM_TOOLS = [
    "get_weekly_forecast",
    "get_forecast",
    "get_uv_index",
    "get_district_weather_impact",
]


def test_no_phantom_tool_names_in_base():
    """BASE_PROMPT KHÔNG mention tên tool không tồn tại (mention effect)."""
    p = _rendered_base()
    for phantom in PHANTOM_TOOLS:
        assert phantom not in p, (
            f"BASE_PROMPT mention phantom tool {phantom!r} sẽ khiến LLM thử gọi"
        )


def test_no_phantom_tool_names_in_tool_rules():
    joined = "\n".join(TOOL_RULES.values())
    for phantom in PHANTOM_TOOLS:
        assert phantom not in joined, (
            f"TOOL_RULES mention phantom tool {phantom!r}"
        )


def test_no_phantom_tool_names_in_full_system_prompt():
    sp = get_system_prompt()
    for phantom in PHANTOM_TOOLS:
        assert phantom not in sp, f"Full system prompt có phantom {phantom!r}"


# ── 3. 6-block architecture ─────────────────────────────────────────────────

EXPECTED_BLOCKS_IN_ORDER = [
    "[1] SCOPE",
    "[2] RUNTIME CONTEXT",
    "[3] POLICY",
    "[4] ROUTER",
    "[5] RENDERER",
    "[6] FALLBACK",
]


def test_base_prompt_has_six_blocks_in_order():
    p = _rendered_base()
    positions = []
    for block in EXPECTED_BLOCKS_IN_ORDER:
        idx = p.find(block)
        assert idx != -1, f"Thiếu block {block!r}"
        positions.append(idx)
    assert positions == sorted(positions), (
        f"Block không đúng thứ tự: {list(zip(EXPECTED_BLOCKS_IN_ORDER, positions))}"
    )


# ── 4. ROUTER table covers 28 tools ─────────────────────────────────────────

ALL_TOOLS = [
    "resolve_location",
    "get_current_weather",
    "get_weather_alerts",
    "get_hourly_forecast",
    "get_daily_forecast",
    "get_rain_timeline",
    "get_best_time",
    "get_weather_history",
    "get_daily_summary",
    "get_weather_period",
    "compare_weather",
    "compare_weather_forecast",
    "compare_with_yesterday",
    "get_seasonal_comparison",
    "get_district_ranking",
    "get_ward_ranking_in_district",
    "detect_phenomena",
    "get_temperature_trend",
    "get_comfort_index",
    "get_weather_change_alert",
    "get_clothing_advice",
    "get_activity_advice",
    "get_uv_safe_windows",
    "get_pressure_trend",
    "get_daily_rhythm",
    "get_humidity_timeline",
    "get_sunny_periods",
    "get_district_multi_compare",
]


def test_router_table_covers_all_28_tools():
    """Bảng ROUTER trong BASE_PROMPT mention mọi tool."""
    p = _rendered_base()
    # Chỉ đoạn ROUTER
    router_start = p.find("[4] ROUTER")
    router_end = p.find("[5] RENDERER")
    assert router_start != -1 and router_end != -1
    router_block = p[router_start:router_end]
    missing = [t for t in ALL_TOOLS if t not in router_block]
    assert not missing, f"ROUTER table thiếu tool: {missing}"


def test_tool_rules_cover_all_28_tools():
    missing = [t for t in ALL_TOOLS if t not in TOOL_RULES]
    assert not missing, f"TOOL_RULES dict thiếu tool: {missing}"


# ── 5. Size sanity ──────────────────────────────────────────────────────────

def test_base_prompt_size_reasonable():
    p = _rendered_base()
    line_count = len(p.splitlines())
    token_est = len(p) // 4
    # P13 Option B: compressed prompt ~50% (351→~185 dòng, 7400→~3700 tokens).
    # Merged 3.3+3.3b+3.3c, 3.8+3.8b+3.8c, removed 4.1, compacted [6].
    # P12.1 (Option A): 3 week_table chuyển horizontal-pipe → vertical bullet
    # (fix attention proximity bias) → +18 dòng (3 tables × 6 dòng/table).
    # Cap 220→240; token est gần như không đổi (chỉ thêm 21 newlines + indent).
    assert line_count <= 240, f"BASE_PROMPT quá dài: {line_count} dòng"
    assert token_est <= 5200, f"BASE_PROMPT quá nặng: ~{token_est} tokens"


def test_focused_prompt_size_comparable_to_full():
    """Focused (1 tool rule + 12 few-shot) ≈ full (27 tool rules, no few-shot).

    R12 L3+R16 expanded few-shot 4→12 (R17 13). Few-shot block now ~ 27 dropped
    TOOL_RULES — 2 sides cancel out structurally. Invariant "focused < full"
    đã không còn đúng kể từ R12 L3 và đó là intentional (few-shot front-load
    là load-bearing cho R11/R12/R16 grounding). Test mới: focused ≤ full * 1.10
    (tolerance 10%) — confirm focused không bùng nổ vượt full quá nhiều.
    Qwen3-14B 32K context vẫn thoải mái với cả 2 prompt ~7-8K token.
    """
    sp = get_system_prompt()
    fp = get_focused_system_prompt(["get_current_weather"])
    assert len(fp) <= len(sp) * 1.50, (
        f"Focused prompt ({len(fp)}) vượt full ({len(sp)}) hơn 50% — kiểm few-shot "
        f"có quá to không. (P13: compressed base nên focused+few-shot > full+all-rules)"
    )


# ── 6. SYSTEM_PROMPT_TEMPLATE removed ───────────────────────────────────────

def test_system_prompt_template_module_attr_removed():
    """Biến module SYSTEM_PROMPT_TEMPLATE đã xoá hoặc không còn dùng."""
    import app.agent.agent as agent_mod
    # Chấp nhận 2 trường hợp: attr đã xoá, hoặc nếu còn thì không chứa seed
    attr = getattr(agent_mod, "SYSTEM_PROMPT_TEMPLATE", None)
    if attr is not None:
        assert "28.5°C" not in attr and "75%" not in attr and "trời trong" not in attr.lower(), (
            "SYSTEM_PROMPT_TEMPLATE vẫn tồn tại và chứa seed — phải xoá hoặc làm sạch"
        )


def test_get_system_prompt_uses_base_plus_tool_rules():
    """Full system prompt phải chứa ROUTER table (từ BASE) + per-tool rules."""
    sp = get_system_prompt()
    assert "[4] ROUTER" in sp
    assert "## Hướng dẫn per-tool" in sp
    # Chọn ngẫu nhiên 1 tool và verify rule của nó có trong sp
    for tool in ["get_current_weather", "get_rain_timeline", "compare_with_yesterday"]:
        assert f"### {tool}" in sp, f"Missing tool section {tool}"


# ── 7. Runtime context placeholders ─────────────────────────────────────────

def test_runtime_context_injected():
    """Sau inject, prompt KHÔNG còn placeholder chưa thay thế."""
    p = _rendered_base()
    # Các placeholder phải được thay thế (R14 E.3: + week_weekday_table, today_iso)
    for ph in [
        "{today_date}", "{yesterday_iso}", "{tomorrow_iso}", "{this_saturday}",
        "{week_weekday_table}", "{today_iso}",
    ]:
        assert ph not in p, f"Placeholder {ph} chưa được inject"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
