"""LangGraph Agent for Weather Chatbot."""

import logging
import os
import re
import threading
from pathlib import Path

# load_dotenv() đã gọi ở app/api/main.py (entry point). Các script ngoài app/
# (experiments/, training/, scripts/) tự gọi load_dotenv riêng.

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
import psycopg

from app.agent.tools import TOOLS
from app.dal.timezone_utils import now_ict

logger = logging.getLogger(__name__)


# Compat shim: langgraph < 0.2.56 dùng `state_modifier=`, từ 0.2.56 dùng `prompt=`.
# Project chạy trên nhiều env (Docker có langgraph 1.x, laptop system python có
# bản cũ). Detect signature 1 lần lúc import để không phải try/except mỗi call.
_PROMPT_KWARG: str = "prompt"
try:
    import inspect as _inspect
    _sig_params = _inspect.signature(create_react_agent).parameters
    if "prompt" in _sig_params:
        _PROMPT_KWARG = "prompt"
    elif "state_modifier" in _sig_params:
        _PROMPT_KWARG = "state_modifier"
    else:
        logger.warning("create_react_agent signature unexpected: %s", list(_sig_params))
    del _sig_params, _inspect
except Exception as _e:
    logger.warning("Could not detect create_react_agent prompt kwarg: %s", _e)

# Vietnamese weekday names
_WEEKDAYS_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
_WEEKDAYS_NUM = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
_WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ═══════════════════════════════════════════════════════════════
# System Prompt — Modular Architecture
# BASE_PROMPT: luôn có (~65 dòng) — context chung cho mọi agent
# TOOL_RULES: per-tool rules — chỉ gửi khi tool đó được focused
# SYSTEM_PROMPT_TEMPLATE: full prompt cho fallback agent (25 tools)
# ═══════════════════════════════════════════════════════════════

_PROMPT_FILE = Path(__file__).parent / "prompts" / "base_prompt.vi.md"
BASE_PROMPT_TEMPLATE = _PROMPT_FILE.read_text(encoding="utf-8")

# ── Tool-specific rules: CHỈ per-tool edge cases, KHÔNG duplicate ROUTER block [4] ──
# Format: rule chỉ ghi những gì ROUTER table của BASE_PROMPT chưa cover:
#   - Constraint ngoài signature (edge param, ngưỡng, ngoại lệ)
#   - Disambiguation "KHÔNG DÙNG KHI" cho cặp overlap
#   - Data limitation / behaviour khi error
TOOL_RULES = {
    "get_current_weather": """- Snapshot tại NOW cho 1 vị trí (phường/quận/city tự dispatch theo location_hint).
- KHÔNG DÙNG cho "chiều/tối/đêm/sáng mai/ngày mai/cuối tuần/max cả ngày" — dùng hourly/daily/summary.
- KHÔNG có field `pop` (xác suất mưa tương lai). Nếu user hỏi "có mưa không" → gọi thêm get_hourly_forecast.""",

    "get_hourly_forecast": """- `hours` ≤ 48. Đủ cover khung user hỏi (vd 8pm-midnight & NOW=16h → hours ≥10).
- KHÔNG DÙNG cho "ngày cụ thể / nhiều ngày" (>48h) — dùng daily_forecast/weather_period theo ROUTER.
- ⚠ KHÔNG DÙNG `hours=48` cho "cuối tuần / tuần này / tháng này" — dùng `get_weather_period(start_date, end_date)` với date range rõ ràng.
- ⚠ User hỏi "chiều mai / sáng mai / tối mai / sáng sớm mai" (khung NGÀY KHÁC hôm nay) → DÙNG `get_daily_forecast(start_date=tomorrow_iso, days=1)` để lấy min/max + 4 buổi. KHÔNG ép hourly tính `hours` 20+ cho mai (dễ thiếu, hoặc trả nhầm khung khác).
- Output có thể kèm `"⚠ lưu ý khung đã qua"` / `"ngày cover"` — ĐỌC + tuân theo (POLICY 3.3, 3.4). Khung đã qua → báo user, KHÔNG dán data ngày mai làm "chiều/trưa/sáng nay".""",

    "get_daily_forecast": """- `days` ≤ 8. User hỏi ngày cụ thể ≠ hôm nay → PHẢI truyền `start_date` (ISO).
  + "ngày mai" → `start_date=tomorrow_iso`. "ngày kia / mốt" → `start_date=day_after_tomorrow_iso`. COPY ISO từ RUNTIME CONTEXT [2], KHÔNG tự cộng/trừ.
- `days=3` (không start_date) = 3 ngày từ hôm nay gồm hôm nay; `start_date=tomorrow, days=3` = 3 ngày từ mai.
- KHÔNG DÙNG cho "cả ngày chi tiết 4 buổi sáng/trưa/chiều/tối" — dùng get_daily_summary.
- Output có key `"tổng hợp"` (ngày nóng/mát/mưa nhiều/ít nhất) — COPY, không tự argmax lại.
- ⚠ ANTI-HALLUCINATE aggregate: key `"nhiệt độ theo ngày"` chỉ có 3 mốc GỘP "Sáng X / Chiều Y / Tối Z" — KHÔNG có hourly. User hỏi "sáng ngày X" → CHỈ COPY "Sáng X°C", CẤM bịa từng giờ (05:00, 06:00...) hay mưa mm/h từng giờ. Cần granular giờ → gọi thêm get_hourly_forecast.""",

    "get_daily_summary": """- Chi tiết 1 ngày DUY NHẤT (min/max + 4 buổi sáng/trưa/chiều/tối). `date` ISO.
- KHÔNG DÙNG cho "bây giờ / tức thời" (dùng get_current_weather); KHÔNG DÙNG cho "nhiều ngày" (dùng daily_forecast/weather_period).
- Output có key `"gợi ý dùng output"` cảnh báo "tổng hợp cả ngày, không phải tức thời" — ĐỌC + theo.""",

    "get_weather_history": """- Past-only. `date` ≤ 14 ngày gần nhất. Vượt → refuse với limit.
- Output ward có thể CHỈ có `wind_gust` (không `wind_speed` avg) — COPY "Giật X m/s", KHÔNG bịa "avg".
- ⚠ User hỏi "tuần qua / N ngày qua / từ A đến B" (RANGE nhiều ngày past) → DÙNG `get_weather_period(start_date, end_date)` 1 call duy nhất, KHÔNG lặp tool này N lần (tránh vượt recursion_limit).""",

    "get_rain_timeline": """- `hours` ≤ 48. `"cường độ đỉnh"` = mm/h tại 1 giờ (KHÔNG phải tổng mm/ngày).
- User hỏi "tổng mưa ngày/tháng" → dùng daily_forecast/weather_period (có `"tổng lượng mưa"` mm).
- ⚠ KHÔNG DÙNG `hours=48` cho "cuối tuần / tuần này / tháng này" — dùng `get_weather_period(start_date, end_date)` với date range cụ thể.
- ĐỌC timestamp (start/end) trong đợt mưa. User hỏi "ngày mai mưa?" → CHỈ report đợt có date khớp; KHÔNG gán đợt hôm nay thành ngày mai.
- Output có thể kèm `"⚠ lưu ý khung đã qua"` / `"ngày cover"` — ĐỌC + tuân theo (POLICY 3.3, 3.12).""",

    "get_best_time": """- Rank khung giờ trong `hours` (≤48). Activity enum: chay_bo, picnic, bike, chup_anh, du_lich, cam_trai, cau_ca, lam_vuon, boi_loi, leo_nui, di_dao, su_kien, dua_dieu, tap_the_duc, phoi_do.
- Nếu user hỏi chi tiết mưa/UV → gọi kèm get_rain_timeline / get_uv_safe_windows.
- ⚠ "Cuối tuần đi X" → gọi `get_weather_period(start_date={this_saturday}, end_date={this_sunday})` TRƯỚC để lấy data 2 ngày cuối tuần, rồi mới best_time nếu còn cần. KHÔNG dùng `hours=48` cho cuối tuần.""",

    "get_clothing_advice": """- Output generic lời khuyên trang phục. Khi trả kết quả → DÙNG, KHÔNG nói "chưa hỗ trợ".""",

    "get_temperature_trend": """- Phân tích 2-8 ngày TỚI từ HÔM NAY (forecast forward-only — DAL chỉ SELECT date >= today).
- User hỏi "tuần qua / mấy hôm trước / dạo trước / X ngày qua" → KHÔNG dùng tool này, gọi `get_weather_history` thay.
- Output có key `"⚠ scope"` ghi rõ forward-only — TUYỆT ĐỐI KHÔNG label data làm "X ngày qua".
- Cần ≥2 ngày data. Nếu chỉ 1 ngày → refuse với lý do không đủ dữ liệu.""",

    "get_seasonal_comparison": """- So hiện tại vs TB climatology tháng HN. Dùng cho "nóng hơn bình thường", "dạo này khác thường", "mùa này".
- KHÔNG DÙNG cho "so tuần trước / hôm qua / ngày mai" — dùng compare_with_yesterday / compare_weather.
- Error "no_weather_data" → gợi ý hỏi thời tiết hiện tại trước.""",

    "get_activity_advice": """- Output generic {advice, reason, recommendations}. DÙNG cho "nên đi X không".
- KHÔNG DÙNG đơn lẻ khi user hỏi chi tiết mưa/UV/giờ → PHẢI gọi kèm rain_timeline/hourly_forecast/uv_safe_windows.
- ⚠ "Cuối tuần đi X" → gọi `get_weather_period` TRƯỚC lấy data 2 ngày cuối tuần, sau đó activity_advice.
- Khi có kết quả → DÙNG, KHÔNG nói "chưa hỗ trợ".
- Output có `"⚠ KHÔNG suy diễn"` — ĐỌC + KHÔNG thêm nhãn hiện tượng (mưa phùn/sương mù/đợt lạnh) ngoài list recommendations.
- Output có `"⚠ snapshot": True` + user hỏi "ngày mai X" → BẮT BUỘC gọi thêm `get_daily_forecast(start_date=tomorrow)` để lấy forecast (POLICY 3.8). KHÔNG dán snapshot làm "ngày mai".""",

    "get_comfort_index": """- Tính điểm thoải mái 0-100 từ nhiệt + ẩm + gió + UV + mưa.
- KHÔNG DÙNG thay cho chi tiết mưa/UV — chỉ trả score + breakdown.""",

    "get_weather_change_alert": """- Phát hiện đột biến thời tiết 6-12h tới (nhiệt drop/rise >5°C, wind up, rain start/stop).
- KHÔNG DÙNG cho "cảnh báo nguy hiểm chuẩn" (bão/rét hại) — dùng get_weather_alerts.
- KHÔNG DÙNG cho "hiện tượng đặc trưng HN" (nồm/gió mùa) — dùng detect_phenomena.""",

    "get_weather_alerts": """- Cảnh báo nguy hiểm chuẩn (bão, rét hại, nắng nóng, giông, lũ, ngập, gió giật).
- Nếu trả rỗng → nói rõ "Hiện không có cảnh báo nguy hiểm", KHÔNG bịa.
- User hỏi cảnh báo loại A mà data có loại B → nói rõ "không có [A], có [B]", KHÔNG lẫn loại.""",

    "detect_phenomena": """- Hiện tượng đặc trưng HN: nồm ẩm, gió mùa ĐB, rét đậm, mưa phùn xuân, sương mù.
- KHÔNG DÙNG cho "cảnh báo nguy hiểm" — dùng get_weather_alerts.""",

    "compare_weather": """- 2 địa điểm hiện tại (A, B). `compare_weather(location_hint1=A, location_hint2=B)`.
- BẮT BUỘC 1 call; KHÔNG gọi get_current_weather 2 lần rồi tự so.
- ⚠ Snapshot-based: KHÔNG dùng cho user hỏi "ngày mai / chiều nay / X nơi nào mưa hơn" (forecast comparison). Thay: gọi 2 lần `get_daily_forecast(start_date=target_date)` cho mỗi location rồi so sánh.""",

    "compare_with_yesterday": """- PAST-ONLY: today vs yesterday cùng 1 địa điểm.
- KHÔNG DÙNG cho "ngày mai vs hôm nay" (future direction) — thay bằng get_current_weather + get_daily_forecast(start_date=tomorrow, days=1) + so sánh trong câu trả lời.
- Error "not_enough_data" → gợi ý xem thời tiết hiện tại.""",

    "get_district_ranking": """- Xếp hạng toàn 30 quận theo 1 metric. Metric enum: nhiet_do, do_am, gio, mua, uvi, ap_suat, diem_suong, may.
- Nếu rankings rỗng hoặc quận rỗng → KHÔNG bịa, báo "tạm không có data".""",

    "get_ward_ranking_in_district": """- Xếp hạng phường TRONG 1 quận. PHẢI truyền `district_name` chính xác.""",

    "get_weather_period": """- Khoảng nhiều ngày. PHẢI truyền `start_date` và `end_date` (ISO).
- Range tối đa 14 ngày; vượt → refuse.
- Output có `"tổng hợp"` — COPY, không tự argmax.
- ⚠ DÙNG cho cả PAST range ("tuần qua / 7 ngày qua / N ngày qua / từ X đến Y" với Y ≤ hôm nay) — 1 call thay cho lặp `get_weather_history`. start_date = today − N, end_date = today (hoặc yesterday cho strict past).""",

    "get_uv_safe_windows": """- Tìm khung giờ UV ≤ ngưỡng trong 48h.""",

    "get_pressure_trend": """- Xu hướng áp suất 48h. Front lạnh = áp suất giảm > 3 hPa/3h.""",

    "get_daily_rhythm": """- Chia ngày thành 4 khung (sáng/trưa/chiều/tối). Khung user hỏi phải matching với output.""",

    "get_humidity_timeline": """- Timeline độ ẩm + điểm sương. Nồm ẩm = ẩm ≥85% AND temp-dew ≤2°C.""",

    "get_sunny_periods": """- Khung nắng = mây <40%, pop <30%, không mưa.""",

    "get_district_multi_compare": """- So 5-10 quận trên nhiều metric cùng lúc. Dùng khi user muốn nhìn bức tranh đa chiều.
- KHÔNG DÙNG cho "top N" đơn metric — dùng get_district_ranking.""",

    "resolve_location": """- Helper: tìm ward_id/district từ tên gần đúng. Thường các tool khác tự resolve qua location_hint — chỉ gọi tool này khi cần chắc chắn tên trước.""",
}

# NOTE: SYSTEM_PROMPT_TEMPLATE đã XOÁ ở R8 (2026-04-21).
# Lý do: chứa seed hallucinate ("28.5°C, cảm giác 31°C, độ ẩm 75%", "65% / 80%") và
# duplicate ROUTER rules với BASE_PROMPT. Giờ fallback agent dùng BASE_PROMPT + full TOOL_RULES
# (xem get_system_prompt() bên dưới).


def _inject_datetime(template: str) -> str:
    """Inject current date/time into a prompt template."""
    from datetime import timedelta
    now = now_ict()
    weekday = now.weekday()  # 0=Mon ... 6=Sun

    # Tính ngày cuối tuần sắp tới
    if weekday <= 4:      # Mon-Fri → T7/CN tuần này
        days_to_sat = 5 - weekday
        days_to_sun = 6 - weekday
    elif weekday == 5:    # Saturday → hôm nay + ngày mai
        days_to_sat = 0
        days_to_sun = 1
    else:                 # Sunday → cuối tuần tới (đã qua)
        days_to_sat = 6
        days_to_sun = 7

    sat_date = (now + timedelta(days=days_to_sat)).date()
    sun_date = (now + timedelta(days=days_to_sun)).date()

    yesterday = (now - timedelta(days=1)).date()
    tomorrow = (now + timedelta(days=1)).date()
    day_before_yesterday = (now - timedelta(days=2)).date()
    day_after_tomorrow = (now + timedelta(days=2)).date()

    # 3 bảng anchor (prev/this/next week) — entry format: "<Tên VN>/T<N>/<Eng>: DD/MM"
    # Fix off-by-one bug khi user hỏi "Thứ N tuần sau" (model nhỏ map sai numeric thứ).
    monday_this_week = (now - timedelta(days=now.weekday())).date()
    horizon_cap = (now + timedelta(days=7)).date()  # forecast horizon = today + 7

    def _build_alias_table(monday_anchor, cap=None):
        parts = []
        for i in range(7):
            d = monday_anchor + timedelta(days=i)
            entry = (
                f"{_WEEKDAYS_VI[i]}/{_WEEKDAYS_NUM[i]}/{_WEEKDAYS_EN[i]}: "
                f"{d.strftime('%d/%m')}"
            )
            if cap is not None and d > cap:
                entry += " [ngoài horizon]"
            parts.append(entry)
        return " | ".join(parts)

    prev_week_table = _build_alias_table(monday_this_week - timedelta(days=7))
    week_table = _build_alias_table(monday_this_week)
    next_week_table = _build_alias_table(monday_this_week + timedelta(days=7), cap=horizon_cap)

    today_iso = now.strftime("%Y-%m-%d")

    return template.format(
        today_weekday=_WEEKDAYS_VI[now.weekday()],
        today_date=now.strftime("%d/%m/%Y"),
        today_time=now.strftime("%H:%M"),
        today_iso=today_iso,
        this_saturday=sat_date.strftime("%Y-%m-%d"),
        this_sunday=sun_date.strftime("%Y-%m-%d"),
        this_saturday_display=sat_date.strftime("%d/%m/%Y"),
        this_sunday_display=sun_date.strftime("%d/%m/%Y"),
        yesterday_date=yesterday.strftime("%d/%m/%Y"),
        yesterday_weekday=_WEEKDAYS_VI[yesterday.weekday()],
        yesterday_iso=yesterday.strftime("%Y-%m-%d"),
        tomorrow_date=tomorrow.strftime("%d/%m/%Y"),
        tomorrow_weekday=_WEEKDAYS_VI[tomorrow.weekday()],
        tomorrow_iso=tomorrow.strftime("%Y-%m-%d"),
        day_after_tomorrow_date=day_after_tomorrow.strftime("%d/%m/%Y"),
        day_after_tomorrow_weekday=_WEEKDAYS_VI[day_after_tomorrow.weekday()],
        day_after_tomorrow_iso=day_after_tomorrow.strftime("%Y-%m-%d"),
        day_before_yesterday_date=day_before_yesterday.strftime("%d/%m/%Y"),
        day_before_yesterday_weekday=_WEEKDAYS_VI[day_before_yesterday.weekday()],
        day_before_yesterday_iso=day_before_yesterday.strftime("%Y-%m-%d"),
        prev_week_table=prev_week_table,
        week_table=week_table,
        next_week_table=next_week_table,
    )


def get_system_prompt() -> str:
    """Build full system prompt cho fallback agent (all 27 tools).

    R8+: dùng BASE_PROMPT (đã có ROUTER table canonical) + toàn bộ TOOL_RULES.
    Không còn duplicate block ở SYSTEM_PROMPT_TEMPLATE.
    """
    base = _inject_datetime(BASE_PROMPT_TEMPLATE)
    rules_block = "\n".join(
        f"### {name}\n{rule.strip()}" for name, rule in TOOL_RULES.items()
    )
    return f"{base}\n\n## Hướng dẫn per-tool\n{rules_block}"


def _load_few_shot_examples() -> dict:
    """Load few-shot examples from app/config/few_shot_examples.json (lazy, cached)."""
    if not hasattr(_load_few_shot_examples, "_cache"):
        try:
            import json as _json
            fse_path = os.path.join(os.path.dirname(__file__), "..", "config", "few_shot_examples.json")
            fse_path = os.path.normpath(fse_path)
            with open(fse_path, "r", encoding="utf-8") as f:
                _load_few_shot_examples._cache = _json.load(f)
        except Exception:
            _load_few_shot_examples._cache = {}
    return _load_few_shot_examples._cache


def get_focused_system_prompt(tool_names: list, router_result=None) -> str:
    """Build focused prompt: BASE + only rules for given tools + few-shot examples.

    Used by focused agents (1-2 tools) after SLM routing.
    Significantly shorter than full prompt — reduces confusion and tokens.

    Args:
        tool_names: List of tool names to include rules for
        router_result: Optional RouterResult — used to inject intent-specific few-shot examples
    """
    base = _inject_datetime(BASE_PROMPT_TEMPLATE)

    # Collect tool-specific rules
    rules = []
    for name in tool_names:
        rule = TOOL_RULES.get(name)
        if rule:
            rules.append(rule.strip())

    prompt = base

    # Tool restriction — router đã chọn focused subset.
    # Strict version trước đó làm agent từ chối ngay cả khi tool có data hỗ trợ
    # (ví dụ get_current_weather có dew_point cho expert query). Soften để agent
    # ưu tiên tool list nhưng VẪN dùng tool gần nhất khi cần.
    if tool_names:
        prompt += (
            "\n## Danh sách công cụ Ưu tiên\n"
            f"Ưu tiên dùng các tool sau: {', '.join(tool_names)}.\n"
            "Đây là tool CHÍNH cho câu hỏi này. KHÔNG gọi tool ngoài list trừ khi "
            "thực sự cần thiết.\n"
            "Nếu user hỏi thông số CỤ THỂ (dew_point, wind_chill, UV, áp suất...) "
            "mà tool trong list trả về data đó (ví dụ get_current_weather có nhiều "
            "field) → DÙNG tool đó + extract field user hỏi. KHÔNG từ chối.\n"
            "Chỉ trả \"chưa hỗ trợ\" khi tool gọi thực sự ERROR và không có "
            "alternative trong list.\n"
        )

    if rules:
        prompt += "\n## Hướng dẫn sử dụng công cụ\n" + "\n".join(rules)

    # R12 L3: inject ALL shared exemplars từ few_shot_examples.json (7 exemplars).
    # R11 dùng [:4] hard-cap → R12 expand 4→7 không có effect nếu giữ slice.
    # Pattern I/O (không Thought/Action ReAct vì Qwen3 thinking variant break stopword parse).
    # Source: top-level "examples" key trong few_shot_examples.json.
    fse = _load_few_shot_examples()
    shared = fse.get("examples", [])
    if shared:
        ex_lines = [f"\n## Ví dụ hành động ({len(shared)} pattern core)"]
        for i, ex in enumerate(shared, 1):
            ex_lines.append(f"\n### Ví dụ {i}: {ex.get('title', '')}")
            if ex.get("user"):
                ex_lines.append(f"User: {ex['user']}")
            if ex.get("thought"):
                ex_lines.append(f"Thought: {ex['thought']}")
            if ex.get("action"):
                ex_lines.append(f"Action: {ex['action']}")
            if ex.get("observation"):
                ex_lines.append(f"Observation: {ex['observation']}")
            if ex.get("response_prefix"):
                ex_lines.append(f"Response: {ex['response_prefix']}")
        prompt += "\n".join(ex_lines)

    return prompt


def _prompt_with_datetime(state) -> list:
    """LangGraph prompt callable: full prompt for 25-tool agent."""
    from langchain_core.messages import SystemMessage
    system_msg = SystemMessage(content=get_system_prompt())
    return [system_msg] + state["messages"]


def _focused_prompt_callable(tool_names: list, router_result=None):
    """Return a state_modifier callable for focused agent with dynamic prompt."""
    def modifier(state) -> list:
        from langchain_core.messages import SystemMessage
        prompt = get_focused_system_prompt(tool_names, router_result)
        return [SystemMessage(content=prompt)] + state["messages"]
    return modifier

# Thread-safe agent cache
_agent = None
_agent_lock = threading.Lock()
_db_connection = None
_model = None         # Shared ChatOpenAI (enable_thinking=True for Qwen3, unified invoke+stream)
_checkpointer = None  # Shared PostgresSaver (reused by focused agents)


def get_agent():
    """Get or create the weather agent (thread-safe)."""
    global _agent
    if _agent is None:
        with _agent_lock:
            # Double-check after acquiring lock
            if _agent is None:
                _agent = create_weather_agent()
    return _agent


def reset_agent():
    """Reset the cached agent to force recreation with fresh connections."""
    global _agent, _db_connection, _model, _checkpointer
    with _agent_lock:
        if _db_connection is not None:
            try:
                _db_connection.close()
            except:
                pass
            _db_connection = None
        _agent = None
        _model = None
        _checkpointer = None


def create_weather_agent():
    global _model, _checkpointer, _db_connection

    # AGENT_* takes priority; fallback to legacy API_* for backward compat
    API_BASE = os.getenv("AGENT_API_BASE") or os.getenv("API_BASE")
    API_KEY = os.getenv("AGENT_API_KEY") or os.getenv("API_KEY")
    MODEL_NAME = os.getenv("AGENT_MODEL") or os.getenv("MODEL", "gpt-4o-mini-2024-07-18")

    if not API_BASE or not API_KEY:
        raise ValueError("AGENT_API_BASE and AGENT_API_KEY must be set in .env")

    # R11 L4.1: thinking bật cho toàn bộ intents (eval + production) với temp=0.
    # Verified sv1.shupremium.com accept enable_thinking=True cho cả invoke và stream
    # (scripts/verify_thinking_api.py). langchain-openai 0.3.35+ handle reasoning_content
    # chunks đúng (0.2.0 có bug Unknown NoneType → upgrade required).
    _extra_kwargs = {}
    if "qwen3" in MODEL_NAME.lower():
        _extra_kwargs = {"extra_body": {"enable_thinking": True}}
    _model = ChatOpenAI(model=MODEL_NAME, 
                        temperature=0, 
                        base_url=API_BASE, 
                        api_key=API_KEY, 
                        **_extra_kwargs)

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in .env")

    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    _checkpointer = PostgresSaver(conn)
    _checkpointer.setup()
    _db_connection = conn

    agent = create_react_agent(
        model=_model, tools=TOOLS,
        checkpointer=_checkpointer,
        **{_PROMPT_KWARG: _prompt_with_datetime},
    )
    return agent

def run_agent(message: str, thread_id: str = "default") -> dict:
    """Run agent synchronously (blocking).
    
    Also logs tool calls to evaluation_logger.
    Includes automatic retry on connection errors.
    """
        
    # Get logger
    try:
        from app.agent.telemetry import get_evaluation_logger
        logger = get_evaluation_logger()
    except Exception:
        logger = None
    
    agent = get_agent()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Wrap tools to log calls (if logger available)
    if logger:
        # We'll log after getting results
        pass
    
    # Retry logic for stale connections
    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config)
            break  # Success, exit retry loop
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Reset agent to get fresh connection
                reset_agent()
                agent = get_agent()
            else:
                raise last_error
    
    # Extract and log tool calls from result
    if logger:
        try:
            messages = result.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        logger.log_tool_call(
                            session_id=thread_id,
                            turn_number=0,
                            tool_name=tc.get("name", "unknown"),
                            tool_input=str(tc.get("args", {})),
                            tool_output="",
                            success=True,
                            execution_time_ms=0
                        )
        except Exception as e:
            pass  # Don't break on logging errors
    
    return result


def stream_agent(message: str, thread_id: str = "default"):
    """Stream agent response token by token.
    
    Yields chunks of the response for real-time display.
    Only yields LLM text (AIMessageChunk from node "agent").
    
    Includes automatic retry on connection errors.
    
    Args:
        message: User message
        thread_id: Conversation thread ID
        
    Yields:
        Text chunks from the agent's response
    """
    from langchain_core.messages import ToolMessage, AIMessageChunk
    
    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": thread_id}}
            
            # Stream with "messages" mode to get token-by-token updates
            # Accumulate raw args from tool_call_chunks by id,
            # then merge with ToolMessage output for complete logging.
            _pending_tool_calls = {}   # id -> {"tool_name", "tool_input_parts"}
            tool_call_logs = []
            for event in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                config,
                stream_mode="messages"
            ):
                # event is a tuple of (message_chunk, metadata)
                if event and len(event) >= 2:
                    msg_chunk, metadata = event

                    # Skip tool messages (they contain raw JSON from DAL)
                    if isinstance(msg_chunk, ToolMessage):
                        tc_id = getattr(msg_chunk, "tool_call_id", None)
                        pending = _pending_tool_calls.pop(tc_id, None) if tc_id else None
                        tool_call_logs.append({
                            "tool_name": pending["tool_name"] if pending else getattr(msg_chunk, "name", "unknown"),
                            "tool_input": "".join(pending["tool_input_parts"]) if pending else "",
                            "tool_output": str(msg_chunk.content) if msg_chunk.content else "",
                            "success": msg_chunk.status != "error" if hasattr(msg_chunk, "status") else True,
                        })
                        continue

                    # Use tool_call_chunks (raw args strings) instead of tool_calls (parsed partial dicts)
                    chunks = getattr(msg_chunk, "tool_call_chunks", None)
                    if chunks:
                        for tc in chunks:
                            tc_id = tc.get("id")
                            tc_name = tc.get("name")
                            if tc_id and tc_id not in _pending_tool_calls:
                                _pending_tool_calls[tc_id] = {
                                    "tool_name": tc_name or "unknown",
                                    "tool_input_parts": [],
                                }
                            target_id = tc_id
                            if not target_id:
                                for pid in _pending_tool_calls:
                                    target_id = pid
                                    break
                            if target_id and target_id in _pending_tool_calls:
                                args_str = tc.get("args", "")
                                if args_str:
                                    _pending_tool_calls[target_id]["tool_input_parts"].append(args_str)
                        continue
                    
                    # Only yield content from agent node, not tools node
                    if metadata.get("langgraph_node") == "agent":
                        if hasattr(msg_chunk, "content") and msg_chunk.content:
                            yield msg_chunk.content
            # Log tool calls to telemetry
            if tool_call_logs:
                try:
                    from app.agent.telemetry import get_evaluation_logger
                    tel_logger = get_evaluation_logger()
                    for tc in tool_call_logs:
                        tel_logger.log_tool_call(
                            session_id=thread_id,
                            turn_number=0,
                            tool_name=tc["tool_name"],
                            tool_input=tc["tool_input"],
                            tool_output=tc["tool_output"],
                            success=tc["success"],
                        )
                except Exception:
                    pass  # Telemetry failure is non-critical
            return  # Success, exit function
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Reset agent to get fresh connection
                reset_agent()
            else:
                raise last_error


def stream_agent_with_updates(message: str, thread_id: str = "default"):
    """Stream agent response with both messages and tool updates.
    
    Yields dict with 'type' and 'content' keys:
    - type='message': text chunk from LLM
    - type='tool': tool call start/update/end
    
    Also logs tool calls to evaluation_logger.
    
    Args:
        message: User message
        thread_id: Conversation thread ID
        
    Yields:
        Dict with type and content
    """
    from langchain_core.messages import ToolMessage, AIMessageChunk
        
    # Retry logic for stale connections
    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get logger
            try:
                from app.agent.telemetry import get_evaluation_logger
                logger = get_evaluation_logger()
            except Exception:
                logger = None
            
            # Stream with both messages and updates
            for event in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                config,
                stream_mode=["messages", "updates"]
            ):
                # Handle different event formats from LangGraph
                # When stream_mode is a list, events come as (stream_name, event_data)
                if isinstance(event, tuple) and len(event) == 2:
                    stream_name, event_data = event
                    
                    if stream_name == "messages":
                        # event_data is (chunk, metadata)
                        if isinstance(event_data, tuple) and len(event_data) == 2:
                            msg_chunk, metadata = event_data
                            
                            # Skip tool messages (raw JSON from DAL)
                            if isinstance(msg_chunk, ToolMessage):
                                continue
                            
                            # Skip messages with tool_calls (function calling JSON)
                            if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                                continue
                            
                            # Message chunk from agent node
                            if metadata.get("langgraph_node") == "agent":
                                if hasattr(msg_chunk, "content") and msg_chunk.content:
                                    yield {"type": "message", "content": msg_chunk.content}
                            
                            # Tool updates (from tools node)
                            if metadata.get("langgraph_node") == "tools":
                                yield {"type": "tool", "content": msg_chunk if isinstance(msg_chunk, str) else str(msg_chunk)}
                    
                    elif stream_name == "updates":
                        # event_data is dict with tool outputs
                        yield {"type": "tool", "content": event_data}

            return  # Success, exit function

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Reset agent to get fresh connection
                reset_agent()
            else:
                raise last_error


# ═══════════════════════════════════════════════════════════════
# SLM Router — Focused ReAct Agent (1-2 tools instead of 25)
# ═══════════════════════════════════════════════════════════════


# ── Qwen3 thinking mode (R11 L4.1: global for all intents, temp=0 uniform) ──
# Strip <think>...</think> blocks từ streaming output (provider có thể emit inline
# hoặc qua reasoning_content field; regex này catch inline case).
_THINK_TOKEN_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking_tokens(text: str) -> str:
    """Remove <think>...</think> blocks from Qwen3 streaming output."""
    return _THINK_TOKEN_RE.sub("", text)


def _create_focused_agent(tools: list, router_result=None):
    """Create a ReAct agent with focused tool set and dynamic prompt.

    R11 L4.1: unified thinking-enabled path cho cả stream và invoke.
    Global `_model` có enable_thinking=True + temp=0. langchain-openai 0.3.35+
    handle reasoning_content chunks đúng.
    """
    get_agent()  # ensure _model và _checkpointer đã init
    tool_names = [t.name for t in tools]

    return create_react_agent(
        model=_model,
        tools=tools,
        checkpointer=_checkpointer,
        **{_PROMPT_KWARG: _focused_prompt_callable(tool_names, router_result)},
    )


def stream_agent_routed(message: str, thread_id: str = "default"):
    """Stream agent response with SLM routing.

    Pipeline:
    1. ConversationState lookup → check if rewrite needed (Module 1a)
    2. SLM Router classifies intent + scope + optional rewrite (1 Ollama call)
    3. Tool selection: PRIMARY (high confidence) or EXPANDED (medium confidence)
    4. Focused ReAct agent streams response (trim_messages context)
    5. ConversationState updated with extracted entities

    Yields text chunks (same interface as stream_agent).
    """
    from langchain_core.messages import ToolMessage

    from app.agent.router.config import PER_INTENT_THRESHOLDS, USE_SLM_ROUTER
    from app.agent.router.slm_router import get_router
    from app.agent.router.tool_mapper import get_focused_tools
    from app.agent.conversation_state import get_conversation_store

    # If router disabled, use standard path
    if not USE_SLM_ROUTER:
        yield from stream_agent(message, thread_id)
        return

    # Step 1: Get conversation context
    store = get_conversation_store()
    context = store.get(thread_id)

    # Step 2: Classify (with context for multi-task rewriting)
    router = get_router()
    rr = router.classify(message, context=context)
    logger.info("SLM Router: %s", rr)

    # Step 3: Decide path
    if rr.should_fallback:
        logger.info("SLM Router → fallback (%s)", rr.fallback_reason)
        yield from stream_agent(message, thread_id)
        return

    # Use rewritten query if model produced one
    effective_message = rr.rewritten_query if rr.rewritten_query else message
    if rr.rewritten_query:
        logger.info("SLM Router rewrote query: %r → %r", message[:50], rr.rewritten_query[:60])

    # Step 4: Get focused tools (confidence-aware selection)
    focused_tools = get_focused_tools(
        rr.intent, rr.scope, rr.confidence, PER_INTENT_THRESHOLDS
    )

    if focused_tools is None or (not focused_tools and rr.intent != "smalltalk_weather"):
        logger.info("SLM Router → fallback (no tool mapping for %s/%s)", rr.intent, rr.scope)
        yield from stream_agent(message, thread_id)
        return

    focused_tools = focused_tools or []

    logger.info(
        "SLM Router → fast path: %s/%s (conf=%.2f), %d tools: %s",
        rr.intent, rr.scope, rr.confidence,
        len(focused_tools), [t.name for t in focused_tools],
    )

    # Step 5: Create focused agent and stream (with scope enforcement)
    from app.agent.dispatch import router_scope_var
    scope_token = router_scope_var.set(rr.scope)

    max_retries = 2
    last_error = None

    try:
        for attempt in range(max_retries):
            try:
                focused_agent = _create_focused_agent(focused_tools, router_result=rr)
                config = {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 15,
                }

                # Collect tool call info for telemetry logging
                # AIMessageChunks split tool_calls across multiple chunks during streaming.
                # tool_call_chunks contains raw args strings; tool_calls contains parsed (incomplete) dicts.
                # We accumulate raw args from tool_call_chunks by id, then merge with ToolMessage output.
                _pending_tool_calls = {}   # id -> {"tool_name", "tool_input_parts"}
                tool_call_logs = []
                for event in focused_agent.stream(
                    {"messages": [{"role": "user", "content": effective_message}]},
                    config,
                    stream_mode="messages",
                ):
                    if event and len(event) >= 2:
                        msg_chunk, metadata = event
                        if isinstance(msg_chunk, ToolMessage):
                            tc_id = getattr(msg_chunk, "tool_call_id", None)
                            pending = _pending_tool_calls.pop(tc_id, None) if tc_id else None
                            tool_call_logs.append({
                                "tool_name": pending["tool_name"] if pending else getattr(msg_chunk, "name", "unknown"),
                                "tool_input": "".join(pending["tool_input_parts"]) if pending else "",
                                "tool_output": str(msg_chunk.content) if msg_chunk.content else "",
                                "success": msg_chunk.status != "error" if hasattr(msg_chunk, "status") else True,
                            })
                            continue
                        # Use tool_call_chunks (raw args strings) instead of tool_calls (parsed partial dicts)
                        chunks = getattr(msg_chunk, "tool_call_chunks", None)
                        if chunks:
                            for tc in chunks:
                                tc_id = tc.get("id")
                                tc_name = tc.get("name")
                                if tc_id and tc_id not in _pending_tool_calls:
                                    _pending_tool_calls[tc_id] = {
                                        "tool_name": tc_name or "unknown",
                                        "tool_input_parts": [],
                                    }
                                target_id = tc_id
                                if not target_id:
                                    # Continuation chunks may have no id; match by index
                                    idx = tc.get("index", 0)
                                    for pid, pval in _pending_tool_calls.items():
                                        target_id = pid
                                        break
                                if target_id and target_id in _pending_tool_calls:
                                    args_str = tc.get("args", "")
                                    if args_str:
                                        _pending_tool_calls[target_id]["tool_input_parts"].append(args_str)
                            continue
                        if metadata.get("langgraph_node") == "agent":
                            if hasattr(msg_chunk, "content") and msg_chunk.content:
                                content = msg_chunk.content
                                # Strip Qwen3 thinking tokens before streaming
                                content = _strip_thinking_tokens(content)
                                if content:
                                    yield content

                # Advance ConversationState for next turn (extract location from
                # this turn's tool calls; without this, multi-turn rewrites lose
                # ward/district context and fall back to "Hà Nội").
                try:
                    store.update(thread_id, tool_call_logs, rr.intent)
                except Exception:
                    pass  # State update failure is non-critical

                # Log tool calls to telemetry
                if tool_call_logs:
                    try:
                        from app.agent.telemetry import get_evaluation_logger
                        tel_logger = get_evaluation_logger()
                        turn = (context.turn_count or 0) + 1 if context else 1
                        for tc in tool_call_logs:
                            tel_logger.log_tool_call(
                                session_id=thread_id,
                                turn_number=turn,
                                tool_name=tc["tool_name"],
                                tool_input=tc["tool_input"],
                                tool_output=tc["tool_output"],
                                success=tc["success"],
                            )
                    except Exception:
                        pass  # Telemetry failure is non-critical

                return
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    reset_agent()
                else:
                    raise last_error
    finally:
        try:
            router_scope_var.reset(scope_token)
        except ValueError:
            # Sync generator can be driven across threads via run_in_executor.
            # SSE layer already pins a single context, but if a caller forgets,
            # leaking the value is harmless (its context copy dies with the call).
            pass


def run_agent_routed(message: str, thread_id: str = "default", *,
                     no_fallback: bool = False,
                     use_rewrite: bool = True) -> dict:
    """Run agent with SLM routing (blocking).

    Always attempts SLM routing (ignores USE_SLM_ROUTER flag).
    Use run_agent() for the baseline (no routing) path.

    Args:
        message: User message
        thread_id: Conversation thread ID
        no_fallback: If True, force routing even for low confidence
                     (structural failures like model_error still fall back)
        use_rewrite: If False, ignore SLM rewritten query and use original
                     message. Used for MT-Context ablation (context injection
                     without query rewriting).

    Returns:
        Agent result dict with '_router' metadata key.
    """
    from app.agent.router.config import PER_INTENT_THRESHOLDS
    from app.agent.router.slm_router import get_router
    from app.agent.router.tool_mapper import get_focused_tools
    from app.agent.conversation_state import get_conversation_store

    # Step 1: Get conversation context
    store = get_conversation_store()
    context = store.get(thread_id)

    # Step 2: Classify (with context for multi-task rewriting)
    router = get_router()
    rr = router.classify(message, context=context)
    logger.info("SLM Router: %s", rr)

    def _router_meta(path, **extra):
        meta = {
            "path": path,
            "intent": rr.intent,
            "scope": rr.scope,
            "confidence": rr.confidence,
            "latency_ms": rr.latency_ms,
            "fallback_reason": rr.fallback_reason,
            "rewritten_query": rr.rewritten_query,
        }
        meta.update(extra)
        return meta

    # Use rewritten query if available (and rewriting not disabled for ablation)
    if use_rewrite and rr.rewritten_query:
        effective_message = rr.rewritten_query
        logger.info("Router rewrite: %r → %r", message[:50], rr.rewritten_query[:60])
    else:
        effective_message = message

    # Step 3: Fallback decision
    if rr.should_fallback:
        can_force = (no_fallback and rr.fallback_reason
                     and rr.fallback_reason.startswith("low_confidence"))
        if not can_force:
            logger.info("SLM Router → fallback (%s)", rr.fallback_reason)
            result = run_agent(message, thread_id)
            result["_router"] = _router_meta("fallback")
            return result

    # Step 4: Get focused tools (confidence-aware)
    focused_tools = get_focused_tools(
        rr.intent, rr.scope, rr.confidence, PER_INTENT_THRESHOLDS
    )

    if focused_tools is None:
        logger.info("SLM Router → fallback (no mapping for %s/%s)", rr.intent, rr.scope)
        result = run_agent(message, thread_id)
        result["_router"] = _router_meta("fallback",
                                          fallback_reason=f"no_mapping:{rr.intent}/{rr.scope}")
        return result

    if not focused_tools and rr.intent != "smalltalk_weather":
        logger.info("SLM Router → fallback (empty tools for %s/%s)", rr.intent, rr.scope)
        result = run_agent(message, thread_id)
        result["_router"] = _router_meta("fallback",
                                          fallback_reason=f"empty_tools:{rr.intent}/{rr.scope}")
        return result

    tool_names = [t.name for t in focused_tools]
    logger.info("SLM Router → routed: %s/%s (conf=%.2f), tools=%s",
                rr.intent, rr.scope, rr.confidence, tool_names)

    # Step 5: Run focused agent (with scope enforcement)
    from app.agent.dispatch import router_scope_var
    scope_token = router_scope_var.set(rr.scope)

    max_retries = 2
    last_error = None

    try:
        for attempt in range(max_retries):
            try:
                focused_agent = _create_focused_agent(focused_tools, router_result=rr)
                config = {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 15,
                }
                result = focused_agent.invoke(
                    {"messages": [{"role": "user", "content": effective_message}]}, config
                )
                result["_router"] = _router_meta("routed", focused_tools=tool_names)

                # Step 6: Advance ConversationState for next turn
                try:
                    from app.agent.conversation_state import messages_to_tool_call_logs
                    logs = messages_to_tool_call_logs(result.get("messages", []))
                    store.update(thread_id, logs, rr.intent)
                except Exception as e:
                    logger.debug("ConversationState update failed (non-critical): %s", e)

                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    reset_agent()
                else:
                    raise last_error
    finally:
        router_scope_var.reset(scope_token)
