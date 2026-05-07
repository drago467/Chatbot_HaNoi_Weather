"""Test get_tool_subset — full_27 vs router_prefilter scenarios.

`full_27` là legacy tool_path name (semantic, không strict count). Sau P11 trả 28 tools.
Phụ thuộc `app/agent/tools/__init__.py:TOOLS` (28 tools) +
`app/agent/router/tool_mapper.py:PRIMARY_TOOL_MAP` (15 intents).
"""

from __future__ import annotations

import pytest

from experiments.evaluation.backends.tools import get_tool_subset


def test_full_27_returns_28_tools():
    """tool_path='full_27' legacy semantic name; sau P11 trả 28 tools (compare_weather_forecast)."""
    tools = get_tool_subset(tool_path="full_27")
    assert len(tools) == 28, f"Expected 28 tools, got {len(tools)}"


def test_full_27_ignores_intent():
    """tool_path='full_27' → intent argument bị bỏ qua."""
    a = get_tool_subset(tool_path="full_27", intent="current_weather", scope="ward")
    b = get_tool_subset(tool_path="full_27")
    assert [t.name for t in a] == [t.name for t in b]


def test_router_prefilter_with_intent_returns_subset():
    """router_prefilter + intent='current_weather' → subset (< full)."""
    tools = get_tool_subset(
        tool_path="router_prefilter",
        intent="current_weather",
        scope="city",
    )
    tool_names = [t.name for t in tools]
    assert "get_current_weather" in tool_names
    assert len(tools) < 28
    assert len(tools) >= 1


def test_router_prefilter_no_intent_falls_back_full_27():
    """intent=None → fallback full (router low confidence path). P11: 28 tools."""
    tools = get_tool_subset(tool_path="router_prefilter", intent=None)
    assert len(tools) == 28


def test_router_prefilter_unknown_intent_falls_back_full_27():
    """intent invalid → fallback full (defensive). P11: 28 tools."""
    tools = get_tool_subset(
        tool_path="router_prefilter",
        intent="nonexistent_intent",
        scope="city",
    )
    assert len(tools) == 28


@pytest.mark.parametrize("intent", [
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
])
def test_router_prefilter_all_15_intents(intent):
    """Mỗi 15 intent có subset không rỗng cho cả 3 scope."""
    for scope in ("city", "district", "ward"):
        tools = get_tool_subset(
            tool_path="router_prefilter", intent=intent, scope=scope,
        )
        assert len(tools) > 0, f"{intent}/{scope} empty subset"
        assert len(tools) <= 28


def test_router_prefilter_location_comparison_scope_aware():
    """location_comparison có tool list khác nhau per scope (city dùng ranking,
    district/ward dùng compare_weather)."""
    city = get_tool_subset(
        tool_path="router_prefilter", intent="location_comparison", scope="city"
    )
    ward = get_tool_subset(
        tool_path="router_prefilter", intent="location_comparison", scope="ward"
    )
    # PRIMARY_TOOL_MAP nested for location_comparison — different per scope
    city_names = {t.name for t in city}
    ward_names = {t.name for t in ward}
    # At least 1 tool name khác nhau between city và ward
    assert city_names != ward_names, "location_comparison phải khác per scope"


def test_invalid_tool_path_raises():
    with pytest.raises(ValueError, match="Unknown tool_path"):
        get_tool_subset(tool_path="invalid_path")


def test_router_prefilter_smalltalk_returns_tools():
    """smalltalk có tool subset (theo INTENT_TO_TOOLS) — không empty."""
    tools = get_tool_subset(
        tool_path="router_prefilter", intent="smalltalk_weather", scope="city"
    )
    assert len(tools) > 0


# ── Sanity: tool list returned là LangChain BaseTool ──────────────────────


def test_returned_tools_have_name_attr():
    """Mỗi tool phải có `.name` (LangChain BaseTool interface)."""
    tools = get_tool_subset(tool_path="full_27")
    for t in tools:
        assert hasattr(t, "name")
        assert isinstance(t.name, str)
        assert len(t.name) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
