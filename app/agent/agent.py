"""LangGraph Agent for Weather Chatbot."""

import functools
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

# ── Tool-specific rules: per-tool edge cases ngoài ROUTER block [4] ──
# Format per entry: SCOPE (1 line) → PARAMS constraints → CẤM (negative routing) → OUTPUT notes
# Prefix: `-` = standard rule, `⚠` = critical anti-hallucination warning
TOOL_RULES = {
    "get_current_weather": """- Snapshot NOW. KHÔNG có `pop` (xác suất mưa) → hỏi mưa thêm hourly.
- KHÔNG DÙNG cho future/max cả ngày — dùng hourly/daily/summary.""",

    "get_hourly_forecast": """- `hours` ≤ 48. Đủ cover khung user hỏi.
- KHÔNG ép `hours=48` cho cuối tuần/tuần này — dùng get_weather_period.
- Khung NGÀY KHÁC hôm nay (mai/kia) → ưu tiên get_daily_forecast(start_date, days=1).
- Output kèm `"⚠ lưu ý khung đã qua"` → tuân theo POLICY 3.3.""",

    "get_daily_forecast": """- `days` ≤ 8. Ngày ≠ hôm nay → PHẢI `start_date` (ISO từ RUNTIME CONTEXT).
- `"nhiệt độ theo ngày"` = 3 mốc GỘP Sáng/Chiều/Tối — CẤM bịa hourly. Cần giờ → thêm hourly.
- `"tổng hợp"` → COPY nguyên. "sáng sớm/rạng sáng" (5-7h) → daily không đủ, thêm hourly.""",

    "get_daily_summary": """- 1 ngày DUY NHẤT (min/max + 4 buổi). `date` ISO.
- KHÔNG cho "bây giờ" (current) hay "nhiều ngày" (daily_forecast/period).""",

    "get_weather_history": """- Past-only, ≤ 14 ngày. Ward có thể CHỈ có `wind_gust` (không avg) → COPY.
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

    "compare_weather": """- 2 địa điểm hiện tại. 1 call duy nhất.
- ⚠ Snapshot-only: future → 2× get_daily_forecast thay thế.""",

    "compare_with_yesterday": """- Today vs yesterday. KHÔNG cho "ngày mai vs hôm nay" → current + daily_forecast.""",

    "get_district_ranking": """- 30 quận, 1 metric. Enum: nhiet_do, do_am, gio, mua, uvi, ap_suat, diem_suong, may.""",

    "get_ward_ranking_in_district": """- Phường TRONG 1 quận. `district_name` chính xác.""",

    "get_weather_period": """- Nhiều ngày, `start_date` + `end_date` ISO. Max 14 ngày. `"tổng hợp"` → COPY.
- DÙNG cho cả PAST range (tuần qua / N ngày qua) — 1 call thay N× history.""",

    "get_uv_safe_windows": """- Khung UV ≤ ngưỡng, 48h.""",

    "get_pressure_trend": """- Áp suất 48h. Front lạnh = giảm > 3 hPa/3h.""",

    "get_daily_rhythm": """- 4 khung (sáng/trưa/chiều/tối), forward-only 24h. Hôm qua → daily_summary.""",

    "get_humidity_timeline": """- Độ ẩm + điểm sương 48h. Nồm = ẩm ≥85% AND temp-dew ≤2°C. Nhiều ngày → period.""",

    "get_sunny_periods": """- Nắng = mây <40%, pop <30%. 48h. Nhiều ngày → daily_forecast/period.""",

    "get_district_multi_compare": """- So 5-10 quận multimetric. ⚠ Snapshot NOW — future → forecast cho từng quận.""",

    "resolve_location": """- Tìm ward/district gần đúng. `not_found`/`ambiguous` → hỏi lại user.""",
}

# NOTE: SYSTEM_PROMPT_TEMPLATE đã XOÁ ở R8 (2026-04-21).
# Lý do: chứa seed hallucinate ("28.5°C, cảm giác 31°C, độ ẩm 75%", "65% / 80%") và
# duplicate ROUTER rules với BASE_PROMPT. Giờ fallback agent dùng BASE_PROMPT + full TOOL_RULES
# (xem get_system_prompt() bên dưới).


# 5 ngày anchor user thường tham chiếu trong câu hỏi. Tuple (prefix, offset).
# Mỗi anchor sinh 3 keys: `<prefix>_date` (DD/MM/YYYY), `<prefix>_weekday` (Việt),
# `<prefix>_iso` (YYYY-MM-DD).
_DATETIME_ANCHORS = (
    ("today", 0),
    ("yesterday", -1),
    ("tomorrow", 1),
    ("day_before_yesterday", -2),
    ("day_after_tomorrow", 2),
)


def _next_weekend(now) -> tuple:
    """Trả (sat_date, sun_date) của cuối tuần SẮP TỚI (hoặc hôm nay nếu đang T7/CN)."""
    from datetime import timedelta
    wd = now.weekday()  # 0=Mon ... 6=Sun
    if wd <= 4:        # Mon-Fri: T7/CN tuần này
        days_to_sat, days_to_sun = 5 - wd, 6 - wd
    elif wd == 5:      # Saturday: hôm nay + ngày mai
        days_to_sat, days_to_sun = 0, 1
    else:              # Sunday: weekend tuần sau
        days_to_sat, days_to_sun = 6, 7
    return (now + timedelta(days=days_to_sat)).date(), (now + timedelta(days=days_to_sun)).date()


def _build_week_alias_table(monday_anchor, cap_date=None) -> str:
    """Bảng 7 entry "<Tên VN>/T<N>/<Eng>: DD/MM" cho 1 tuần.

    `cap_date`: nếu set, entry vượt ngày này nhận suffix "[ngoài horizon]"
    (dùng cho `next_week_table` — forecast chỉ cover today+7).
    """
    from datetime import timedelta
    parts = []
    for i in range(7):
        d = monday_anchor + timedelta(days=i)
        entry = (
            f"{_WEEKDAYS_VI[i]}/{_WEEKDAYS_NUM[i]}/{_WEEKDAYS_EN[i]}: "
            f"{d.strftime('%d/%m')}"
        )
        if cap_date is not None and d > cap_date:
            entry += " [ngoài horizon]"
        parts.append(entry)
    return " | ".join(parts)


def _inject_datetime(template: str) -> str:
    """Inject current date/time vào prompt template.

    Sinh 3 nhóm key:
    - 5 anchors (today/yesterday/...): mỗi anchor 3 keys (_date, _weekday, _iso).
    - Cuối tuần sắp tới: this_saturday(_display), this_sunday(_display).
    - 3 bảng tuần (prev/this/next) — fix bug "Thứ N tuần sau" của model nhỏ.
    """
    from datetime import timedelta
    now = now_ict()

    ctx: dict = {
        "today_time": now.strftime("%H:%M"),
    }

    # 5 anchor ngày
    for prefix, offset in _DATETIME_ANCHORS:
        d = (now + timedelta(days=offset)).date()
        ctx[f"{prefix}_date"] = d.strftime("%d/%m/%Y")
        ctx[f"{prefix}_weekday"] = _WEEKDAYS_VI[d.weekday()]
        ctx[f"{prefix}_iso"] = d.strftime("%Y-%m-%d")

    # Cuối tuần sắp tới (4 keys: sat/sun × iso/display)
    sat, sun = _next_weekend(now)
    ctx["this_saturday"] = sat.strftime("%Y-%m-%d")
    ctx["this_sunday"] = sun.strftime("%Y-%m-%d")
    ctx["this_saturday_display"] = sat.strftime("%d/%m/%Y")
    ctx["this_sunday_display"] = sun.strftime("%d/%m/%Y")

    # 3 bảng tuần (prev/this/next). horizon_cap = today+7 cho next_week.
    monday_this = (now - timedelta(days=now.weekday())).date()
    horizon_cap = (now + timedelta(days=7)).date()
    ctx["prev_week_table"] = _build_week_alias_table(monday_this - timedelta(days=7))
    ctx["week_table"] = _build_week_alias_table(monday_this)
    ctx["next_week_table"] = _build_week_alias_table(
        monday_this + timedelta(days=7), cap_date=horizon_cap
    )

    return template.format(**ctx)


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


@functools.lru_cache(maxsize=1)
def _load_few_shot_examples() -> dict:
    """Load few-shot examples từ app/config/few_shot_examples.json (lazy, cached)."""
    import json as _json
    fse_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "config", "few_shot_examples.json")
    )
    try:
        with open(fse_path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}


def get_focused_system_prompt(tool_names: list) -> str:
    """Build focused prompt: BASE + only rules for given tools + few-shot examples.

    Used by focused agents (1-2 tools) after SLM routing.
    Significantly shorter than full prompt — reduces confusion and tokens.

    Args:
        tool_names: List of tool names to include rules for
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


def _focused_prompt_callable(tool_names: list):
    """Return a state_modifier callable for focused agent with dynamic prompt."""
    def modifier(state) -> list:
        from langchain_core.messages import SystemMessage
        prompt = get_focused_system_prompt(tool_names)
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


def _accumulate_tool_call_chunks(chunks, pending: dict, index_to_id: dict) -> None:
    """Append `args` fragments từ tool_call_chunks vào `pending` đúng tool call.

    LangGraph stream mode chia tool call thành nhiều chunks: chunk đầu có
    `id` + `name` + 1 phần `args`; chunks sau chỉ có `index` + tiếp `args`.
    Cần ghép `args` đúng tool call (route theo `index` thay vì lấy first key
    — sai khi có parallel tool calls).

    Args:
        chunks: list `tool_call_chunks` từ AIMessageChunk.
        pending: dict mut: id -> {"tool_name", "tool_input_parts"}.
        index_to_id: dict mut: index -> id (cho continuation chunks).
    """
    for tc in chunks:
        tc_id = tc.get("id")
        tc_name = tc.get("name")
        tc_index = tc.get("index", 0)
        if tc_id and tc_id not in pending:
            pending[tc_id] = {
                "tool_name": tc_name or "unknown",
                "tool_input_parts": [],
            }
            index_to_id[tc_index] = tc_id
        target_id = tc_id or index_to_id.get(tc_index)
        if target_id and target_id in pending:
            args_str = tc.get("args", "")
            if args_str:
                pending[target_id]["tool_input_parts"].append(args_str)


def _flush_tool_message_to_log(msg_chunk, pending: dict, log_list: list) -> None:
    """Khi gặp ToolMessage (kết quả tool), match với pending entry và push vào log."""
    tc_id = getattr(msg_chunk, "tool_call_id", None)
    p = pending.pop(tc_id, None) if tc_id else None
    log_list.append({
        "tool_name": p["tool_name"] if p else getattr(msg_chunk, "name", "unknown"),
        "tool_input": "".join(p["tool_input_parts"]) if p else "",
        "tool_output": str(msg_chunk.content) if msg_chunk.content else "",
        "success": msg_chunk.status != "error" if hasattr(msg_chunk, "status") else True,
    })


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
    from langchain_core.messages import ToolMessage

    max_retries = 2
    last_error = None
    
    for attempt in range(max_retries):
        try:
            agent = get_agent()
            config = {"configurable": {"thread_id": thread_id}}
            
            # Stream with "messages" mode to get token-by-token updates.
            # Accumulate raw args from tool_call_chunks by id, then merge with
            # ToolMessage output for complete telemetry logging.
            pending_tool_calls = {}   # id -> {"tool_name", "tool_input_parts"}
            index_to_id = {}          # tool_call_chunks index -> id
            tool_call_logs = []
            for event in agent.stream(
                {"messages": [{"role": "user", "content": message}]},
                config,
                stream_mode="messages"
            ):
                if not (event and len(event) >= 2):
                    continue
                msg_chunk, metadata = event

                if isinstance(msg_chunk, ToolMessage):
                    _flush_tool_message_to_log(msg_chunk, pending_tool_calls, tool_call_logs)
                    continue

                chunks = getattr(msg_chunk, "tool_call_chunks", None)
                if chunks:
                    _accumulate_tool_call_chunks(chunks, pending_tool_calls, index_to_id)
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


def _create_focused_agent(tools: list):
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
        **{_PROMPT_KWARG: _focused_prompt_callable(tool_names)},
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
                focused_agent = _create_focused_agent(focused_tools)
                config = {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 15,
                }

                # Collect tool call info for telemetry. AIMessageChunks split
                # tool_calls across multiple stream chunks: chunk đầu có id+name,
                # chunks sau chỉ có index → ghép theo index. Helpers ở đầu file
                # (`_accumulate_tool_call_chunks`, `_flush_tool_message_to_log`)
                # dùng chung với `stream_agent` (fallback path).
                pending_tool_calls = {}   # id -> {"tool_name", "tool_input_parts"}
                index_to_id = {}          # tool_call_chunks index -> id
                tool_call_logs = []
                for event in focused_agent.stream(
                    {"messages": [{"role": "user", "content": effective_message}]},
                    config,
                    stream_mode="messages",
                ):
                    if not (event and len(event) >= 2):
                        continue
                    msg_chunk, metadata = event

                    if isinstance(msg_chunk, ToolMessage):
                        _flush_tool_message_to_log(msg_chunk, pending_tool_calls, tool_call_logs)
                        continue

                    chunks = getattr(msg_chunk, "tool_call_chunks", None)
                    if chunks:
                        _accumulate_tool_call_chunks(chunks, pending_tool_calls, index_to_id)
                        continue

                    if metadata.get("langgraph_node") == "agent":
                        if hasattr(msg_chunk, "content") and msg_chunk.content:
                            content = _strip_thinking_tokens(msg_chunk.content)
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
    can_force = False
    if rr.should_fallback:
        can_force = (no_fallback and rr.fallback_reason
                     and rr.fallback_reason.startswith("low_confidence"))
        if not can_force:
            logger.info("SLM Router → fallback (%s)", rr.fallback_reason)
            result = run_agent(message, thread_id)
            result["_router"] = _router_meta("fallback")
            return result

    # Step 4: Get focused tools (confidence-aware).
    # Khi `can_force=True` (no_fallback ablation cho low_confidence): bypass
    # threshold gate trong tool_mapper bằng cách truyền confidence=1.0. Nếu
    # không, gate (tool_mapper.py:339) sẽ trả None và rơi fallback ở step dưới
    # → cờ `no_fallback` vô tác dụng cho đúng case nó được thiết kế.
    effective_conf = 1.0 if can_force else rr.confidence
    focused_tools = get_focused_tools(
        rr.intent, rr.scope, effective_conf, PER_INTENT_THRESHOLDS
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
                focused_agent = _create_focused_agent(focused_tools)
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
