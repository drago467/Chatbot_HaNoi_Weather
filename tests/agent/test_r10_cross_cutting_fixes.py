"""R10: Cross-cutting fixes cho các pattern còn lại sau audit v8.

Tests:
- P0.1: Past-frame detection output-level (hourly/rain_timeline có "⚠ lưu ý khung đã qua")
- P0.2: POLICY 3.7 + 3.8 có trong BASE_PROMPT
- P1.1: "Cuối tuần" hard-route trong TOOL_RULES (best_time/rain_timeline/activity/hourly)
- P1.2: Arithmetic pre-compute ("chênh nhiệt ngày-đêm" trong daily_summary)
- P2: Cấm-list advice tools (clothing/activity/comfort có "⚠ KHÔNG suy diễn")
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.agent.tools.output_builder import (
    _detect_forecast_range_gap,
    build_activity_advice_output,
    build_clothing_advice_output,
    build_comfort_index_output,
    build_daily_summary_output,
    build_hourly_forecast_output,
)

ICT = ZoneInfo("Asia/Ho_Chi_Minh")


# ── P0.1: Past-frame detection output-level ────────────────────────────────

def test_past_frame_trigger_when_eval_runs_evening():
    """Scenario v8 audit B1: NOW=22:14, data bắt đầu 23:00 → khung đã qua
    (sáng+trưa+chiều) phải được cảnh báo explicit."""
    fake_now = datetime(2026, 4, 20, 22, 14, tzinfo=ICT)
    start = datetime(2026, 4, 20, 23, 0, tzinfo=ICT)
    forecasts = [{"ts_utc": int(start.timestamp() + i * 3600)} for i in range(8)]

    out = _detect_forecast_range_gap(forecasts, now=fake_now)

    assert "phạm vi thực tế" in out
    assert "⚠ lưu ý khung đã qua" in out
    warn = out["⚠ lưu ý khung đã qua"]
    # Phải liệt kê 3 khung đã qua: sáng + trưa + chiều
    assert "sáng nay" in warn
    assert "trưa nay" in warn
    assert "chiều nay" in warn
    # Phải có hướng dẫn "KHÔNG dán nhãn khung hôm nay"
    assert "KHÔNG" in warn


def test_past_frame_morning_warns_about_rang_sang():
    """P12 F1: NOW=10:00 sáng, data bắt đầu 11:00 → "rạng sáng (2-6h)" vẫn ĐÃ
    QUA và không có data → phải warn (audit v2_0212: bot bịa "rạng sáng 21.4°C"
    khi data first=09:00). Sáng (6-11) chưa qua hết → không warn cho sáng.
    """
    fake_now = datetime(2026, 4, 20, 10, 0, tzinfo=ICT)
    start = datetime(2026, 4, 20, 11, 0, tzinfo=ICT)
    forecasts = [{"ts_utc": int(start.timestamp() + i * 3600)} for i in range(6)]

    out = _detect_forecast_range_gap(forecasts, now=fake_now)

    assert "phạm vi thực tế" in out
    warn = out.get("⚠ lưu ý khung đã qua", "")
    assert "rạng sáng" in warn  # 2-6h đã qua + uncovered
    assert "sáng nay (6-11h)" not in warn  # sáng chưa hết


def test_past_frame_no_trigger_when_data_covers_past():
    """Data bắt đầu trước NOW NHƯNG sau "rạng sáng" → vẫn cảnh báo cho rạng sáng.

    P12 F1: cover sáng/trưa nhưng không cover 2-6h → fragment uncovered.
    """
    fake_now = datetime(2026, 4, 20, 16, 0, tzinfo=ICT)
    start = datetime(2026, 4, 20, 8, 0, tzinfo=ICT)
    forecasts = [{"ts_utc": int(start.timestamp() + i * 3600)} for i in range(12)]

    out = _detect_forecast_range_gap(forecasts, now=fake_now)
    warn = out.get("⚠ lưu ý khung đã qua", "")
    # rạng sáng (2-6) uncovered (data starts 08), nên cảnh báo
    assert "rạng sáng" in warn
    # sáng (6-11) đã qua và data 08:00 covers một phần → vẫn còn uncovered (06-08h)
    # Hành vi mới: sáng cũng uncovered (first_dt.hour=8 >= sáng.end=11? NO 8<11 → covered)
    # → sáng KHÔNG warn
    assert "sáng nay (6-11h)" not in warn


def test_past_frame_no_warning_when_data_starts_early():
    """Data từ rạng sáng (3:00) cover hết frame quá khứ → không warn."""
    fake_now = datetime(2026, 4, 20, 16, 0, tzinfo=ICT)
    start = datetime(2026, 4, 20, 3, 0, tzinfo=ICT)
    forecasts = [{"ts_utc": int(start.timestamp() + i * 3600)} for i in range(15)]

    out = _detect_forecast_range_gap(forecasts, now=fake_now)
    assert "⚠ lưu ý khung đã qua" not in out


def test_past_frame_mid_afternoon_trigger():
    """NOW=15:00, data bắt đầu 16:00 → sáng + trưa đã qua, chiều chưa hoàn toàn qua."""
    fake_now = datetime(2026, 4, 20, 15, 0, tzinfo=ICT)
    start = datetime(2026, 4, 20, 16, 0, tzinfo=ICT)
    forecasts = [{"ts_utc": int(start.timestamp() + i * 3600)} for i in range(8)]

    out = _detect_forecast_range_gap(forecasts, now=fake_now)
    warn = out.get("⚠ lưu ý khung đã qua", "")
    assert "sáng nay" in warn
    assert "trưa nay" in warn
    # "chiều nay" KHÔNG nằm trong list vì chiều kết thúc 18h, NOW=15h chưa qua hết
    assert "chiều nay" not in warn


def test_hourly_forecast_output_includes_past_frame_detection():
    """build_hourly_forecast_output kết hợp _detect_forecast_range_gap."""
    start = int(datetime.now(ICT).timestamp())
    raw = {
        "level": "city",
        "resolved_location": {"city_name": "Hà Nội"},
        "forecasts": [
            {"ts_utc": start + i * 3600, "temp": 25, "humidity": 80,
             "pop": 0.3, "wind_speed": 3, "wind_deg": 180, "clouds": 60,
             "weather_main": "Clouds"}
            for i in range(6)
        ],
    }
    out = build_hourly_forecast_output(raw)
    assert "phạm vi thực tế" in out  # Luôn có khi forecasts ≥ 1


# ── P0.2: BASE_PROMPT POLICY 3.3 Past-frame + 3.4 Weekday (R12 RESTORE full text) ─────

def test_base_prompt_has_past_frame_rule():
    """R12 L1: past-frame rule RESTORE full text (R10 R12) ở 3.3."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    assert "3.3 Past-frame" in p
    # Phải mention cả 4 khung
    for frame in ("sáng", "trưa", "chiều", "tối"):
        assert frame in p.lower()
    assert "⚠ lưu ý khung đã qua" in p  # Reference to output key
    # R12 RESTORE: explicit get_weather_history fallback khi khung đã qua
    assert "get_weather_history" in p
    # R12 RESTORE: TUYỆT ĐỐI KHÔNG dán data ngày mai
    assert "TUYỆT ĐỐI KHÔNG" in p


def test_base_prompt_has_weekday_mismatch_rule():
    """R12 L1: weekday rule RESTORE full text + 'hôm kia' mapping."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    assert "3.4 Weekday" in p
    # R12 RESTORE: explicit mismatch example "12/04 thực là Chủ Nhật"
    assert "Chủ Nhật" in p
    # R12 RESTORE: "hôm kia" = today-2 (audit v10 ID 98)
    assert "hôm kia" in p.lower()


def test_base_prompt_has_snapshot_superlative_binding():
    """R12 L2 POLICY 3.8: snapshot + superlative → BẮT BUỘC daily_summary (fix F2)."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "3.8 Snapshot discipline" in p
    assert "mạnh nhất" in p
    assert "get_daily_summary" in p


def test_base_prompt_has_tool_dispatch_mandatory():
    """R12 L4 POLICY 3.9: BẮT BUỘC gọi tool khi có entity thời tiết + địa điểm (fix F3)."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "3.9 Tool dispatch" in p
    assert "BẮT BUỘC gọi tool" in p
    # Typo handling examples
    assert "bnhieu" in p.lower() or "typo" in p.lower()


def test_base_prompt_has_phenomena_whitelist():
    """R12 L5 + R16 audit P3 POLICY 3.10: phenomena whitelist (was 'field-absence specific')."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    # R16 renamed POLICY 3.10 từ "Field-absence specific" → "Phenomena whitelist"
    assert "3.10 Phenomena whitelist" in p or "3.10 Field-absence" in p
    # Specific phenomena mentioned in whitelist or rules
    assert "gió mùa" in p.lower()
    assert "sương mù" in p.lower()
    assert "humidity_timeline" in p
    # R16: explicit whitelist mentions UV / mây / nắng requirements
    assert "uv" in p.lower() and "nắng" in p.lower()


def test_base_prompt_has_multi_part_decomposition():
    """R12 L7 POLICY 3.11: multi-part decomposition (fix F6)."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "3.11 Multi-aspect" in p or "3.11 Multi" in p
    assert "TẤT CẢ tools" in p or "tất cả tools" in p.lower()


def test_base_prompt_has_range_coverage_check():
    """R12 L9 POLICY 3.12: range coverage check (fix F9)."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "3.12 Range coverage" in p
    assert "ngày cover" in p


def test_base_prompt_scope_bans_poi():
    """P8 (2026-05-03): SCOPE [1] phải có policy "KHÔNG hỗ trợ POI" + clarification."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "KHÔNG hỗ trợ POI" in p, "SCOPE [1] phải ban POI explicit"
    assert "hỏi lại" in p, "SCOPE [1] phải yêu cầu clarification cho POI/địa danh lạ"
    # POI examples cũ KHÔNG được liệt kê trong SCOPE như supported coverage
    # (chỉ được ghi như VÍ DỤ KHÔNG hỗ trợ).
    scope_block_start = p.find("## [1] SCOPE")
    scope_block_end = p.find("## [2]")
    assert scope_block_start != -1 and scope_block_end != -1
    scope = p[scope_block_start:scope_block_end]
    # Không còn dòng "POI (tự map về quận)" — đó là phrasing cũ
    assert "tự map về quận" not in scope


def test_runtime_context_has_sang_som_hoang_hon():
    """R12 L8: RUNTIME CONTEXT extend time mapping (fix F7: sáng sớm/hoàng hôn)."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    p = BASE_PROMPT_TEMPLATE
    assert "sáng sớm" in p
    assert "hoàng hôn" in p
    assert "rạng sáng" in p


def test_tool_rules_restore_cuoi_tuan_constraint():
    """R12 L6: RESTORE `⚠ KHÔNG hours=48 cho cuối tuần` cho hourly/rain_timeline."""
    from app.agent.agent import TOOL_RULES
    assert "hours=48" in TOOL_RULES["get_hourly_forecast"] or "cuối tuần" in TOOL_RULES["get_hourly_forecast"]
    assert "get_weather_period" in TOOL_RULES["get_hourly_forecast"]
    # best_time + activity_advice restore "get_weather_period TRƯỚC"
    assert "get_weather_period" in TOOL_RULES["get_best_time"]
    assert "get_weather_period" in TOOL_RULES["get_activity_advice"]


def test_tool_rules_compare_weather_forecast_warning():
    """R12 L6 / P11: compare_weather chỉ rõ FUTURE → compare_weather_forecast (1-call wrapper)."""
    from app.agent.agent import TOOL_RULES
    rule = TOOL_RULES["compare_weather"]
    assert "future" in rule.lower() or "snapshot" in rule.lower()
    assert "compare_weather_forecast" in rule


# ── P1.1 DEPRECATED: 4 duplicate "cuối tuần" warnings đã xoá khỏi TOOL_RULES (R11 L2)
# Cuối tuần dispatch giờ ở ROUTER table [4] (row "cuối tuần / tuần này → get_weather_period")
# — single source of truth, tránh dilute attention Qwen3-14B.

def test_router_table_has_cuoi_tuan_dispatch():
    """R11 L2: cuối tuần dispatch duy nhất ở ROUTER table [4]."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE
    assert "cuối tuần" in BASE_PROMPT_TEMPLATE.lower()
    assert "get_weather_period" in BASE_PROMPT_TEMPLATE


# ── P1.2: Arithmetic pre-compute (ID 64) ────────────────────────────────────

def test_daily_summary_arithmetic_precomputed():
    """ID 64: bot tính 30.4-22.8=5.4 sai. Builder phải pre-compute đúng 7.6."""
    raw = {
        "level": "city", "resolved_location": {"city_name": "Hà Nội"},
        "date": "2026-04-21", "weather_main": "Clouds",
        "temp_min": 22.8, "temp_max": 30.4, "humidity": 75,
    }
    out = build_daily_summary_output(raw)
    assert "chênh nhiệt ngày-đêm" in out
    assert "7.6" in out["chênh nhiệt ngày-đêm"]  # Không phải 5.4
    assert "°C" in out["chênh nhiệt ngày-đêm"]
    assert "COPY" in out["chênh nhiệt ngày-đêm"]  # Instructs LLM


def test_daily_summary_arithmetic_various_values():
    for tmin, tmax, expected in [
        (20.0, 25.0, "5.0"),
        (15.5, 28.3, "12.8"),
        (18.0, 18.0, "0.0"),  # Edge: equal
    ]:
        raw = {
            "level": "city", "resolved_location": {"city_name": "Hà Nội"},
            "date": "2026-04-21", "weather_main": "Clouds",
            "temp_min": tmin, "temp_max": tmax,
        }
        out = build_daily_summary_output(raw)
        assert expected in out.get("chênh nhiệt ngày-đêm", ""), (
            f"temp_max={tmax} - temp_min={tmin} nên ra {expected}, "
            f"ra: {out.get('chênh nhiệt ngày-đêm')}"
        )


def test_daily_summary_no_arithmetic_when_temp_missing():
    """Khi thiếu min/max → không có key."""
    raw = {
        "level": "city", "resolved_location": {"city_name": "Hà Nội"},
        "date": "2026-04-21", "weather_main": "Clouds",
        "avg_temp": 25,
    }
    out = build_daily_summary_output(raw)
    assert "chênh nhiệt ngày-đêm" not in out


# ── P2: Cấm-list advice tools ──────────────────────────────────────────────

def test_clothing_advice_has_no_hallucinate_warning():
    out = build_clothing_advice_output({"clothing_items": ["áo thoáng"], "notes": ["mang ô"]})
    assert "⚠ KHÔNG suy diễn" in out
    warn = out["⚠ KHÔNG suy diễn"]
    # Phải liệt kê nhãn hiện tượng hay bị bịa
    assert "mưa phùn" in warn
    assert "sương mù" in warn


def test_activity_advice_has_no_hallucinate_warning():
    out = build_activity_advice_output({"advice": "nên", "reason": "trời thoáng"})
    assert "⚠ KHÔNG suy diễn" in out


def test_comfort_index_has_no_hallucinate_warning():
    out = build_comfort_index_output({"score": 75, "label": "Thoải mái"})
    assert "⚠ KHÔNG suy diễn" in out


# ── Regression: advice tools vẫn có field chính ────────────────────────────

def test_advice_tools_still_have_primary_fields():
    """Đảm bảo thêm ⚠ KHÔNG break các field chính (primary output)."""
    # clothing
    out_c = build_clothing_advice_output({"clothing_items": ["áo"], "notes": ["mang ô"]})
    assert out_c["trang phục đề xuất"] == ["áo"]
    assert out_c["ghi chú"] == ["mang ô"]
    # activity
    out_a = build_activity_advice_output({"advice": "nên", "reason": "thoáng",
                                           "recommendations": ["đi sáng"]})
    assert out_a["khuyến nghị"] == "nên"
    assert out_a["lý do"] == "thoáng"
    assert out_a["gợi ý thêm"] == ["đi sáng"]
    # comfort
    out_co = build_comfort_index_output({"score": 75, "label": "Thoải mái",
                                          "recommendation": "ra ngoài OK",
                                          "breakdown": {"temp": "ideal"}})
    assert out_co["điểm thoải mái"] == "75/100"
    assert out_co["mức độ"] == "Thoải mái"
    assert out_co["phân tích"] == {"temp": "ideal"}


# ── R13 Layer C: Structural absence emission ──────────────────────────────

def test_r13_current_output_emits_missing_fog_visibility():
    """R13 Layer C: current_weather không có visibility/fog fields
    → phải emit `⚠ không có dữ liệu` với ['tầm nhìn', 'sương mù']."""
    from app.agent.tools.output_builder import build_current_output
    raw = {
        "temp": 26.0, "humidity": 88, "time_ict": "2026-04-22T08:00:00+07:00",
        "level": "city", "resolved_location": {}, "weather_main": "Clouds",
        # KHÔNG có visibility, KHÔNG có fog
    }
    out = build_current_output(raw)
    assert "⚠ không có dữ liệu" in out
    missing = out["⚠ không có dữ liệu"]
    assert "tầm nhìn" in missing
    assert "sương mù" in missing
    # Phải có ghi chú hướng dẫn LLM
    assert "⚠ ghi chú trường thiếu" in out
    assert "KHÔNG" in out["⚠ ghi chú trường thiếu"]


def test_r13_current_output_no_missing_when_fields_present():
    """Absence emission KHÔNG fire khi tất cả expected fields đều có."""
    from app.agent.tools.output_builder import build_current_output
    raw = {
        "temp": 26.0, "humidity": 88, "time_ict": "2026-04-22T08:00:00+07:00",
        "level": "city", "resolved_location": {}, "weather_main": "Clouds",
        "visibility": 10000, "fog": False,
    }
    out = build_current_output(raw)
    assert "⚠ không có dữ liệu" not in out


def test_r13_weather_history_emits_missing_visibility():
    """R13: weather_history không có visibility → emit absence."""
    from app.agent.tools.output_builder import build_weather_history_output
    raw = {
        "temp": 25.0, "humidity": 80, "level": "ward", "resolved_location": {},
        "date": "2026-04-21", "weather_main": "Clouds",
    }
    out = build_weather_history_output(raw, date_hint="2026-04-21")
    assert "⚠ không có dữ liệu" in out
    assert "tầm nhìn" in out["⚠ không có dữ liệu"]


def test_r13_daily_summary_emits_missing_rain_hourly_mm():
    """R13: daily_summary không có rain_hourly_mm → emit absence."""
    from app.agent.tools.output_builder import build_daily_summary_output
    raw = {
        "temp_min": 22.0, "temp_max": 32.0, "avg_humidity": 75,
        "level": "city", "resolved_location": {},
        "date": "2026-04-22", "weather_main": "Clouds",
    }
    out = build_daily_summary_output(raw)
    assert "⚠ không có dữ liệu" in out
    missing = out["⚠ không có dữ liệu"]
    assert any("lượng mưa" in m for m in missing)


# ── R13 Layer D: Hour formula + Weekday COPY rules ─────────────────────────

def test_r13_hour_formula_in_base_prompt():
    """R13 Layer D.1: BASE_PROMPT [2] có quy ước giờ chính xác + formula."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    # Hour mappings
    assert "7 giờ tối" in p or "19:00" in p
    assert "10 giờ đêm" in p or "22:00" in p
    assert "12 giờ trưa" in p or "12:00" in p
    assert "nửa đêm" in p or "00:00" in p
    # Formula
    assert "NOW_hour" in p


def test_r13_weekday_copy_rule_in_base_prompt():
    """R13 Layer D.2: POLICY 3.4 có COPY-don't-compute rule."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    assert "COPY" in p and "compute" in p.lower()


# ── R13 Layer A: Widen PRIMARY_TOOL_MAP baseline trio ──────────────────────

def test_r13_widen_rain_query_has_current():
    """R13: rain_query phải include get_current_weather cho 'đang mưa' snapshot."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP
    tools = PRIMARY_TOOL_MAP["rain_query"]["city"]
    tool_names = {t.name for t in tools}
    assert "get_current_weather" in tool_names


def test_r13_widen_humidity_fog_has_forecast_tools():
    """R13: humidity_fog_query phải include hourly + daily cho future-frame."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP
    tools = PRIMARY_TOOL_MAP["humidity_fog_query"]["city"]
    tool_names = {t.name for t in tools}
    assert "get_hourly_forecast" in tool_names
    assert "get_daily_forecast" in tool_names


def test_r13_widen_weather_alert_has_current_and_daily():
    """R13: weather_alert phải include current + daily cho snapshot + 'mấy ngày tới'."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP
    tools = PRIMARY_TOOL_MAP["weather_alert"]["city"]
    tool_names = {t.name for t in tools}
    assert "get_current_weather" in tool_names
    assert "get_daily_forecast" in tool_names


def test_r13_widen_daily_forecast_has_history_recovery():
    """R13: daily_forecast phải include weather_history cho '7 ngày qua' misrouted."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP
    tools = PRIMARY_TOOL_MAP["daily_forecast"]["city"]
    tool_names = {t.name for t in tools}
    assert "get_weather_history" in tool_names


# ══════════════════════════════════════════════════════════════════════════════
# R14 Coherence Extensions tests (2026-04-23)
# E.1 activity_weather widen | E.2 snapshot rejection hint | E.3 week table
# E.4 TOOL_RULES mai→daily  | E.5 POLICY 3.9 keyword bypass | E.6 POLICY 3.12 period mapping
# ══════════════════════════════════════════════════════════════════════════════


def test_r14_e1_activity_weather_has_daily_and_period():
    """R14 E.1: activity_weather intent thêm daily_forecast + weather_period cho future-frame."""
    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP
    tools = PRIMARY_TOOL_MAP["activity_weather"]["city"]
    tool_names = {t.name for t in tools}
    assert "get_daily_forecast" in tool_names, "sáng mai/ngày mai tập X cần daily"
    assert "get_weather_period" in tool_names, "cuối tuần đi X cần period"
    # Tool count ≤ 7 cap
    assert 1 <= len(tools) <= 7, f"activity_weather vượt cap: {len(tools)} tools"


def test_r14_e2_snapshot_metadata_has_rejection_key():
    """R14 E.2: _emit_snapshot_metadata emit `⚠ KHÔNG dùng cho` structured key."""
    from app.agent.tools.output_builder import _emit_snapshot_metadata
    meta = _emit_snapshot_metadata(None)
    assert "⚠ KHÔNG dùng cho" in meta, "Thiếu structured rejection key"
    rejection = meta["⚠ KHÔNG dùng cho"]
    # Phải liệt kê future-frame keywords + suggest replacement tools
    assert "tối nay" in rejection
    assert "ngày mai" in rejection
    assert "cuối tuần" in rejection
    assert "get_hourly_forecast" in rejection or "hourly" in rejection
    assert "get_daily_forecast" in rejection or "daily" in rejection


def test_week_alias_tables_injected():
    """3 bảng tuần trước/này/sau với user-text + VN name + T<N> alias (P12.2: drop English).

    Format: `  - "<user-text>" / <Tên VN> (T<N>) = YYYY-MM-DD`.
    """
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    # 3 markers
    for marker in ["Lịch tuần trước", "Lịch tuần này", "Lịch tuần sau"]:
        assert marker in p, f"Missing marker {marker!r} in rendered prompt"
    # 7 named weekdays VN
    for wd in ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]:
        assert wd in p, f"Missing weekday name {wd!r}"
    # 6 numeric alias T2-T7 + CN
    for num in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]:
        assert num in p, f"Missing numeric alias {num!r}"
    # 7 user-text quoted forms (P12.2: substring-match thắng ISO/position interpretation)
    for ut in ['"thứ 2"', '"thứ 3"', '"thứ 4"', '"thứ 5"', '"thứ 6"', '"thứ 7"', '"chủ nhật"']:
        assert ut in p, f"Missing user-text form {ut!r}"


def test_3_alias_format_per_entry():
    """P12.2 (full systemic): Mỗi DÒNG đúng format `  - "<user-text>" / <Tên VN> (T<N>) = YYYY-MM-DD`."""
    import re
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    # Pattern: '  - "thứ 3" / Thứ Ba (T3) = 2026-05-12' hoặc '  - "chủ nhật" / Chủ Nhật (CN) = 2026-05-17'
    pattern = re.compile(
        r'  - "(?:thứ\s\d|chủ\snhật)"\s/\s(?:Thứ\s\S+|Chủ\sNhật)\s\((?:T\d|CN)\)\s=\s\d{4}-\d{2}-\d{2}'
    )
    matches = pattern.findall(p)
    # 3 bảng × 7 entries = 21 matches tối thiểu (chưa kể suffix `[NGOÀI HORIZON]`)
    assert len(matches) >= 21, f"Expected ≥21 alias entries, got {len(matches)}: {matches[:5]}"


@pytest.mark.parametrize("fake_weekday", [0, 1, 2, 3, 4, 5, 6])
def test_prev_next_week_anchors_correct(monkeypatch, fake_weekday):
    """P12: Bảng prev/next anchor đúng với ISO format mới.

    R18: now_ict moved từ agent.py → _prompt_builder.py. Patch tại
    use-site (_prompt_builder) thay vì re-exported reference (agent).
    """
    from datetime import datetime, timedelta
    import app.agent.agent as agent_mod
    import app.agent._prompt_builder as pb_mod
    # Pick a fake "today" với weekday cụ thể (anchor: 2026-04-27 = Monday)
    base_monday = datetime(2026, 4, 27, 12, 0)
    fake_today = base_monday + timedelta(days=fake_weekday)
    monkeypatch.setattr(pb_mod, "now_ict", lambda: fake_today)
    p = agent_mod._inject_datetime(agent_mod.BASE_PROMPT_TEMPLATE)
    monday_this_week = base_monday.date()
    # Prev Monday entry → ISO = (monday_this_week - 7)
    prev_mon_iso = (monday_this_week - timedelta(days=7)).strftime("%Y-%m-%d")
    assert f'  - "thứ 2" / Thứ Hai (T2) = {prev_mon_iso}' in p, f"prev_week Mon mismatch (fake_wd={fake_weekday}): expected ISO {prev_mon_iso}"
    # Next Sunday entry → ISO = (monday_this_week + 13)
    next_sun_iso = (monday_this_week + timedelta(days=13)).strftime("%Y-%m-%d")
    assert f'  - "chủ nhật" / Chủ Nhật (CN) = {next_sun_iso}' in p, f"next_week Sun mismatch (fake_wd={fake_weekday}): expected ISO {next_sun_iso}"


def test_next_week_horizon_cap_marker(monkeypatch):
    """P12: next_week_table có suffix `[NGOÀI HORIZON]` cho entry > today+7."""
    from datetime import datetime
    import app.agent.agent as agent_mod
    import app.agent._prompt_builder as pb_mod
    monkeypatch.setattr(pb_mod, "now_ict", lambda: datetime(2026, 4, 27, 12, 0))
    p = agent_mod._inject_datetime(agent_mod.BASE_PROMPT_TEMPLATE)
    assert "[NGOÀI HORIZON]" in p, "Today=Monday → next_week phải có entry NGOÀI HORIZON"
    assert p.count("[NGOÀI HORIZON]") >= 6


def test_thu4_tuan_sau_correct_for_today_friday(monkeypatch):
    """P12 repro user case: today = Thứ Sáu 2026-05-01, 'Thứ 4 tuần sau' phải = 06/05 (today+5) — ISO format."""
    from datetime import datetime
    import app.agent.agent as agent_mod
    import app.agent._prompt_builder as pb_mod
    monkeypatch.setattr(pb_mod, "now_ict", lambda: datetime(2026, 5, 1, 15, 30))
    p = agent_mod._inject_datetime(agent_mod.BASE_PROMPT_TEMPLATE)
    # next_week_table phải có dòng '  - "thứ 4" / Thứ Tư (T4) = 2026-05-06'
    assert '  - "thứ 4" / Thứ Tư (T4) = 2026-05-06' in p, "Thứ 4 tuần sau phải = 2026-05-06 khi today=Friday 01/05"
    # Đảm bảo 2026-05-07 KHÔNG xuất hiện như "Thứ Tư" (đó là Thursday)
    assert '  - "thứ 4" / Thứ Tư (T4) = 2026-05-07' not in p


def test_day_after_tomorrow_iso_injected(monkeypatch):
    """Inject day_after_tomorrow_iso (today+2) — fix repro 'sáng ngày kia' off-by-one.

    User case: today=Thứ Sáu 2026-05-01 → 'ngày kia' = 2026-05-03 (CN), KHÔNG phải 02/05.
    """
    from datetime import datetime
    import app.agent.agent as agent_mod
    import app.agent._prompt_builder as pb_mod
    monkeypatch.setattr(pb_mod, "now_ict", lambda: datetime(2026, 5, 1, 15, 30))
    p = agent_mod._inject_datetime(agent_mod.BASE_PROMPT_TEMPLATE)
    # Ngày kia phải là 03/05/2026 (Chủ Nhật) — KHÔNG được map sang 02/05 (= ngày mai)
    assert "Ngày kia / mốt: Chủ Nhật, 03/05/2026" in p
    assert "2026-05-03" in p
    # Hôm kia symmetric: 29/04 (Thứ Tư)
    assert "Hôm kia: Thứ Tư, 29/04/2026" in p
    assert "2026-04-29" in p


@pytest.mark.parametrize("today_offset_from_monday,expected_dat_iso", [
    (0, "2026-04-29"),  # today=Mon 27/04 → DAT=Wed 29/04
    (1, "2026-04-30"),  # today=Tue 28/04 → DAT=Thu 30/04
    (4, "2026-05-03"),  # today=Fri 01/05 → DAT=Sun 03/05 (user repro)
    (6, "2026-05-05"),  # today=Sun 03/05 → DAT=Tue 05/05
])
def test_day_after_tomorrow_iso_correct_anchor(monkeypatch, today_offset_from_monday, expected_dat_iso):
    """day_after_tomorrow_iso = today + 2 ngày, kiểm cho 4 weekday-of-today fake."""
    from datetime import datetime, timedelta
    import app.agent.agent as agent_mod
    import app.agent._prompt_builder as pb_mod
    base_monday = datetime(2026, 4, 27, 12, 0)
    fake_today = base_monday + timedelta(days=today_offset_from_monday)
    monkeypatch.setattr(pb_mod, "now_ict", lambda: fake_today)
    p = agent_mod._inject_datetime(agent_mod.BASE_PROMPT_TEMPLATE)
    assert expected_dat_iso in p, f"Expected day_after_tomorrow ISO {expected_dat_iso} when today={fake_today.date()}"


def test_r14_e4_tool_rules_hourly_has_tomorrow_rule():
    """R14 E.4: TOOL_RULES[get_hourly_forecast] có rule "chiều mai/sáng mai → daily"."""
    from app.agent.agent import TOOL_RULES
    rule = TOOL_RULES["get_hourly_forecast"]
    assert "mai" in rule or "NGÀY KHÁC" in rule
    assert "get_daily_forecast" in rule or "daily_forecast" in rule


def test_r14_e5_policy_3_9_has_keyword_mapping():
    """R14 E.5: POLICY 3.9 có token mapping + CẤM refuse examples."""
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    # Token mapping table (restored — validated fix for informal Vietnamese)
    assert "troi→trời" in p or "troi" in p
    assert "bnhieu" in p
    # Rule CẤM refuse
    assert "CẤM" in p and ("không tra được" in p or "tạm không tra được" in p)
    # Example
    assert "troi ha noi co dep hem" in p


def test_r14_e6_policy_3_12_has_period_mapping():
    """R14 E.6: POLICY 3.12 có Mapping period → params block.
    P12 F6: 'tuần trước/qua/rồi' explicit prev_week_table lookup (audit v2_0269).
    """
    from app.agent.agent import BASE_PROMPT_TEMPLATE, _inject_datetime
    p = _inject_datetime(BASE_PROMPT_TEMPLATE)
    # "tuần này" CẤM start_date=this_saturday
    assert "tuần này" in p
    assert "CẤM" in p
    # P12 F6: "tuần trước/qua/rồi" → prev_week_table (no self-compute)
    assert "tuần trước" in p and "tuần qua" in p
    assert "prev_week_table" in p or "Lịch tuần trước" in p
    # "cuối tuần" weather_period
    assert "get_weather_period" in p


def test_r14_build_current_output_has_rejection_key():
    """R14 E.2 integration: build_current_output inherits snapshot rejection via _emit_snapshot_metadata."""
    from app.agent.tools.output_builder import build_current_output
    raw = {
        "dt": 1745312400,  # some timestamp
        "temp": 33.0, "humidity": 60, "feels_like": 38.0, "visibility": 10000,
        "wind_speed": 3.5, "wind_deg": 90, "wind_gust": 5.0,
        "pressure": 1010, "clouds": 20, "pop": 0, "uvi": 3.0,
        "dew_point": 22.0, "weather_main": "Clouds", "weather_description": "scattered clouds",
        "level": "city", "resolved_location": {},
    }
    out = build_current_output(raw)
    assert "⚠ snapshot" in out
    assert "⚠ KHÔNG dùng cho" in out, "build_current_output phải inherit rejection key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
