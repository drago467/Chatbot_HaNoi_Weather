"""Prompt + few-shot builder.

Nội dung tách từ `agent.py` (R18 refactor):
- `BASE_PROMPT_TEMPLATE` đọc 1 lần từ `prompts/base_prompt.vi.md`
- `TOOL_RULES` per-tool dict (snapshot/forecast/history/...)
- `_inject_datetime` format datetime placeholders cho BASE
- Few-shot exemplars cũng được format placeholders (R18: trước đây hardcoded
  date trong JSON → rot khi today đổi). Mọi `{tomorrow_iso}` trong exemplar
  đều được substitute bằng cùng ctx dùng cho BASE.
- `get_system_prompt` / `get_focused_system_prompt` build full prompt cho
  fallback agent (27 tools) và focused agent (1-N tools sau router).
"""

from __future__ import annotations

import functools
import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from app.dal.timezone_utils import now_ict


# ─────────────────────────────────────────────────────────────────────────
# Template loading
# ─────────────────────────────────────────────────────────────────────────

_PROMPT_FILE = Path(__file__).parent / "prompts" / "base_prompt.vi.md"
BASE_PROMPT_TEMPLATE = _PROMPT_FILE.read_text(encoding="utf-8")

_FEWSHOT_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "few_shot_examples.json"
)


# ─────────────────────────────────────────────────────────────────────────
# Per-tool rules (negative routing + edge cases ngoài ROUTER block [4])
# Format per entry: SCOPE → PARAMS → CẤM (negative routing) → OUTPUT notes
# Prefix: `-` standard, `⚠` critical anti-hallucination warning
# ─────────────────────────────────────────────────────────────────────────

TOOL_RULES = {
    "get_current_weather": """- Snapshot NOW. KHÔNG có `pop` (xác suất mưa) → hỏi mưa thêm hourly.
- KHÔNG DÙNG cho future/max cả ngày — dùng hourly/daily/summary.""",

    "get_hourly_forecast": """- `hours` ≤ 48. Đủ cover khung user hỏi.
- KHÔNG ép `hours=48` cho cuối tuần/tuần này — dùng get_weather_period.
- Khung NGÀY KHÁC hôm nay (mai/kia) → ưu tiên get_daily_forecast(start_date ISO từ RUNTIME CONTEXT [2], days=1).
- Output kèm `"⚠ lưu ý khung đã qua"` → tuân theo POLICY 3.3.""",

    "get_daily_forecast": """- `days` ≤ 8. Ngày ≠ hôm nay → PHẢI `start_date` (ISO từ RUNTIME CONTEXT).
- `"nhiệt độ theo ngày"` = 3 mốc GỘP Sáng/Chiều/Tối — CẤM bịa hourly. Cần giờ → thêm hourly.
- `"tổng hợp"` → COPY nguyên. "sáng sớm/rạng sáng" (5-7h) → daily không đủ, thêm hourly.""",

    "get_daily_summary": """- 1 ngày DUY NHẤT (min/max + 4 buổi). `date` ISO từ RUNTIME CONTEXT [2] (today_iso/yesterday_iso/week_table).
- KHÔNG cho "bây giờ" (current) hay "nhiều ngày" (daily_forecast/period).""",

    "get_weather_history": """- Past-only, ≤ 14 ngày. `date` ISO từ RUNTIME CONTEXT [2] (yesterday_iso/prev_week_table/week_table).
- Ward có thể CHỈ có `wind_gust` (không avg) → COPY.
- Range nhiều ngày → get_weather_period 1 call, KHÔNG lặp N lần.""",

    "get_rain_timeline": """- `hours` ≤ 48. `"cường độ đỉnh"` = mm/h (KHÔNG phải tổng mm/ngày).
- ĐỌC timestamp đợt mưa — CHỈ report đợt có date khớp ngày user hỏi.""",

    "get_best_time": """- Activity enum: chay_bo, picnic, bike, chup_anh, du_lich, cam_trai, cau_ca, lam_vuon, boi_loi, leo_nui, di_dao, su_kien, dua_dieu, tap_the_duc, phoi_do.
- "Cuối tuần đi X" → get_weather_period TRƯỚC, rồi best_time.""",

    "get_clothing_advice": """- Snapshot NOW. "sáng mai mặc gì" → gọi forecast trước.
- Khi có kết quả → DÙNG, KHÔNG nói "chưa hỗ trợ".""",

    "get_temperature_trend": """- Forward-only 2-8 ngày TỚI. "tuần qua / X ngày qua" → dùng history/period.
- CẤM label data làm "X ngày qua". Cần ≥2 ngày.""",

    "get_seasonal_comparison": """- So hiện tại vs TB climatology tháng HN. KHÔNG cho "so hôm qua / ngày mai".""",

    "get_activity_advice": """- DÙNG cho "nên đi X không". Chi tiết mưa/UV → kèm rain/hourly/uv.
- "Cuối tuần" → get_weather_period TRƯỚC. Snapshot + future → thêm daily_forecast.""",

    "get_comfort_index": """- Score 0-100 snapshot NOW. "tối nay thoải mái?" → cần forecast trước.""",

    "get_weather_change_alert": """- Đột biến 6-12h tới. KHÔNG cho "cảnh báo nguy hiểm" (alerts) hay "nồm/gió mùa" (phenomena).""",

    "get_weather_alerts": """- Cảnh báo nguy hiểm (bão, rét hại, nắng nóng, giông, lũ, ngập). Rỗng → "Không có cảnh báo.".""",

    "detect_phenomena": """- Hiện tượng HN: nồm ẩm, gió mùa ĐB, rét đậm, sương mù. KHÔNG cho cảnh báo nguy hiểm.""",

    "compare_weather": """- 2 địa điểm HIỆN TẠI. 1 call duy nhất.
- ⚠ Snapshot-only: future → compare_weather_forecast (1 call) thay thế.""",

    "compare_weather_forecast": """- 2 địa điểm FUTURE. 1 call duy nhất với `start_date` + `days`.
- DÙNG: "A vs B ngày mai/cuối tuần/T7/CN tới". CẤM cho current (→ compare_weather) hoặc past.
- `start_date` ISO từ RUNTIME CONTEXT [2] (tomorrow_iso/this_saturday/next_week_table).
- Output symmetric với compare_weather: `địa điểm 1/2`, `chênh lệch` (per ngày), `tóm tắt`.""",

    "compare_with_yesterday": """- Today vs yesterday. KHÔNG cho "ngày mai vs hôm nay" → current + daily_forecast.""",

    "get_district_ranking": """- 30 quận, 1 metric. Enum: nhiet_do, do_am, gio, mua, uvi, ap_suat, diem_suong, may.""",

    "get_ward_ranking_in_district": """- Phường TRONG 1 quận. `district_name` chính xác.""",

    "get_weather_period": """- Nhiều ngày, `start_date` + `end_date` ISO từ RUNTIME CONTEXT [2] (week_table/prev_week_table cho range tuần). Max 14 ngày. `"tổng hợp"` → COPY.
- DÙNG cho cả PAST range (tuần qua / N ngày qua) — 1 call thay N× history.""",

    "get_uv_safe_windows": """- Khung UV ≤ ngưỡng, 48h.""",

    "get_pressure_trend": """- Áp suất 48h. Front lạnh = giảm > 3 hPa/3h.""",

    "get_daily_rhythm": """- 4 khung (sáng/trưa/chiều/tối), forward-only 24h. Hôm qua → daily_summary.""",

    "get_humidity_timeline": """- Độ ẩm + điểm sương 48h. Nồm = ẩm ≥85% AND temp-dew ≤2°C. Nhiều ngày → period.""",

    "get_sunny_periods": """- Nắng = mây <40%, pop <30%. 48h. Nhiều ngày → daily_forecast/period.""",

    "get_district_multi_compare": """- So 5-10 quận multimetric. ⚠ Snapshot NOW — future → forecast cho từng quận.""",

    "resolve_location": """- Tìm ward/district gần đúng. `not_found`/`ambiguous` → hỏi lại user.""",
}


# ─────────────────────────────────────────────────────────────────────────
# Datetime helpers (Vietnamese weekday vocabulary)
# ─────────────────────────────────────────────────────────────────────────

_WEEKDAYS_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
_WEEKDAYS_NUM = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
# User-typed quoted form ("thứ 2"...) — substring match wins over ISO/list-position interpretations.
_WEEKDAYS_USER = ['"thứ 2"', '"thứ 3"', '"thứ 4"', '"thứ 5"', '"thứ 6"', '"thứ 7"', '"chủ nhật"']

# 5 anchor ngày user thường tham chiếu. Mỗi anchor sinh 3 keys
# (`<prefix>_date` DD/MM/YYYY, `<prefix>_weekday` Việt, `<prefix>_iso` YYYY-MM-DD).
_DATETIME_ANCHORS = (
    ("today", 0),
    ("yesterday", -1),
    ("tomorrow", 1),
    ("day_before_yesterday", -2),
    ("day_after_tomorrow", 2),
)


def _next_weekend(now) -> tuple:
    """Trả (sat_date, sun_date) của cuối tuần SẮP TỚI (hoặc hôm nay nếu đang T7/CN)."""
    wd = now.weekday()  # 0=Mon ... 6=Sun
    if wd <= 4:        # Mon-Fri: T7/CN tuần này
        days_to_sat, days_to_sun = 5 - wd, 6 - wd
    elif wd == 5:      # Saturday: hôm nay + ngày mai
        days_to_sat, days_to_sun = 0, 1
    else:              # Sunday: weekend tuần sau
        days_to_sat, days_to_sun = 6, 7
    return (now + timedelta(days=days_to_sat)).date(), (now + timedelta(days=days_to_sun)).date()


def _build_week_alias_table(monday_anchor, cap_date=None) -> str:
    """7 dòng vertical `<user-text> / <Tên VN> (T<N>) = YYYY-MM-DD`.

    P12.2: user-text quoted form FIRST — fix bug "thứ 3 → 2026-05-13".
    Tiếng Việt "thứ 3 / Thứ Ba" có 4 cách interpret cạnh tranh:
    (a) VN name → Thứ Ba → Tue ✓; (b) ISO 8601 day-3 → Wed ✗;
    (c) list position 3 → Thứ Tư ✗; (d) ordinal "Ba=3" → Wed ✗.
    Đặt user-typed `"thứ 3"` đầu dòng → substring match thắng mọi interpretation.

    `cap_date`: entry vượt ngày này nhận suffix `[NGOÀI HORIZON]`.
    """
    lines = []
    for i in range(7):
        d = monday_anchor + timedelta(days=i)
        line = (
            f"  - {_WEEKDAYS_USER[i]} / {_WEEKDAYS_VI[i]} ({_WEEKDAYS_NUM[i]}) "
            f"= {d.strftime('%Y-%m-%d')}"
        )
        if cap_date is not None and d > cap_date:
            line += "  [NGOÀI HORIZON]"
        lines.append(line)
    return "\n".join(lines)


def _build_runtime_context() -> dict:
    """Build datetime ctx dict cho format() — share giữa BASE + few-shot.

    Sinh 3 nhóm key:
    - 5 anchors (today/yesterday/...) × 3 keys (_date, _weekday, _iso)
    - Cuối tuần sắp tới: this_saturday(_display), this_sunday(_display)
    - 3 bảng tuần (prev/this/next) — fix bug "Thứ N tuần sau" của model nhỏ
    """
    now = now_ict()
    ctx: dict = {"today_time": now.strftime("%H:%M")}

    for prefix, offset in _DATETIME_ANCHORS:
        d = (now + timedelta(days=offset)).date()
        ctx[f"{prefix}_date"] = d.strftime("%d/%m/%Y")
        ctx[f"{prefix}_weekday"] = _WEEKDAYS_VI[d.weekday()]
        ctx[f"{prefix}_iso"] = d.strftime("%Y-%m-%d")

    sat, sun = _next_weekend(now)
    ctx["this_saturday"] = sat.strftime("%Y-%m-%d")
    ctx["this_sunday"] = sun.strftime("%Y-%m-%d")
    ctx["this_saturday_display"] = sat.strftime("%d/%m/%Y")
    ctx["this_sunday_display"] = sun.strftime("%d/%m/%Y")

    monday_this = (now - timedelta(days=now.weekday())).date()
    horizon_cap = (now + timedelta(days=7)).date()
    ctx["prev_week_table"] = _build_week_alias_table(monday_this - timedelta(days=7))
    ctx["week_table"] = _build_week_alias_table(monday_this)
    ctx["next_week_table"] = _build_week_alias_table(
        monday_this + timedelta(days=7), cap_date=horizon_cap
    )
    return ctx


def _inject_datetime(template: str) -> str:
    """Format datetime placeholders trong BASE prompt.

    Public-ish (test imports it). Returns BASE_PROMPT_TEMPLATE với placeholders
    `{today_iso}`, `{week_table}`, ... đã substitute.
    """
    return template.format(**_build_runtime_context())


# ─────────────────────────────────────────────────────────────────────────
# Few-shot exemplars — placeholder-aware
# ─────────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _load_few_shot_examples() -> dict:
    """Load few-shot từ JSON (cached). Returns {} on error."""
    try:
        with _FEWSHOT_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_format(s: str, ctx: dict) -> str:
    """Format string với ctx, giữ nguyên nếu KeyError/IndexError.

    Few-shot có thể chứa string không cần substitute (text mô tả). format()
    sẽ raise KeyError trên `{key}` không có trong ctx; ta fallback giữ nguyên.
    """
    if not s:
        return s
    try:
        return s.format(**ctx)
    except (KeyError, IndexError):
        return s


def _format_few_shot_block(ctx: dict) -> str:
    """Build few-shot block với placeholders đã substitute từ ctx.

    R18: tất cả `{tomorrow_iso}`, `{today_date}`, ... trong exemplar JSON
    được resolve cùng datetime với BASE → exemplar không rot.
    """
    fse = _load_few_shot_examples()
    examples = fse.get("examples", [])
    if not examples:
        return ""

    lines = [f"\n## Ví dụ hành động ({len(examples)} pattern core)"]
    fields = (
        ("user", "User"),
        ("thought", "Thought"),
        ("action", "Action"),
        ("observation", "Observation"),
        ("response_prefix", "Response"),
    )
    for i, ex in enumerate(examples, 1):
        lines.append(f"\n### Ví dụ {i}: {ex.get('title', '')}")
        for key, label in fields:
            val = ex.get(key)
            if val:
                lines.append(f"{label}: {_safe_format(val, ctx)}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────

def get_system_prompt() -> str:
    """Full system prompt cho fallback agent (all 27 tools)."""
    base = _inject_datetime(BASE_PROMPT_TEMPLATE)
    rules_block = "\n".join(
        f"### {name}\n{rule.strip()}" for name, rule in TOOL_RULES.items()
    )
    return f"{base}\n\n## Hướng dẫn per-tool\n{rules_block}"


def get_focused_system_prompt(tool_names: Iterable[str]) -> str:
    """Focused prompt: BASE + chỉ rules cho tool_names + few-shot exemplars.

    Used by focused agents (1-N tools sau SLM routing). Few-shot exemplars
    được format placeholders cùng ctx datetime (R18) — không hardcoded.
    """
    ctx = _build_runtime_context()
    base = BASE_PROMPT_TEMPLATE.format(**ctx)

    tool_names = list(tool_names)
    rules = [TOOL_RULES[n].strip() for n in tool_names if n in TOOL_RULES]

    parts = [base]

    if tool_names:
        # Soft tool-restriction (R11 L4 calibration): ưu tiên list nhưng vẫn
        # cho phép tool gần nhất khi user hỏi chi tiết tool đó cover.
        parts.append(
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
        parts.append("\n## Hướng dẫn sử dụng công cụ\n" + "\n".join(rules))

    fewshot = _format_few_shot_block(ctx)
    if fewshot:
        parts.append(fewshot)

    return "".join(parts)
