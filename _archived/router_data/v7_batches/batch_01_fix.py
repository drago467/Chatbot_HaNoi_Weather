"""V7 Batch 1 — Manual fix samples (50 total).

Composition:
- 5 FIX_PREFIX (Gia Lâm wrongly called "quận", canonical = Huyện)
- 8 FIX_TIME (anchor preservation: "ngày mai", "ngày kia", "tuần sau")
- 25 FIX_POI_ADMIN (extract admin from POI+admin samples; pure POI → T5 abstain)
- 12 FIX_CONTEXT (collision core ambiguous → default Phường post-merger)

Each sample: {history, input, output} per v7 schema.
- history: list of {user, assistant} pairs for multi-turn (max K=3); [] for single-turn
- input: current user query (verbatim from v6)
- output: 4 keys core (intent, scope, confidence, rewritten_query|null)

Confidence tiers (Hiến pháp v7):
  T1=0.92 unambiguous, T2=0.85 standard, T3=0.80 multi-turn,
  T4=0.74 collision-decided, T5=0.62 smalltalk/POI/OOD.

Run: python batch_01_fix.py → writes batch_01_fix.jsonl
"""
import json
import sys
from pathlib import Path

# ── helper: assistant JSON for fabricated prior turns (4 keys core only) ────
def asst(intent: str, scope: str, conf: float, rewrite: str | None) -> str:
    return json.dumps({
        "intent": intent, "scope": scope, "confidence": conf,
        "rewritten_query": rewrite,
    }, ensure_ascii=False, separators=(',', ':'))

# ── BATCH 1 SAMPLES ─────────────────────────────────────────────────────────
SAMPLES = []

# ═══════════════════════════════════════════════════════════════════════════
# A) 5 FIX_PREFIX — Gia Lâm canonical = Huyện, NOT Quận
#    Strategy: synthesize turn-1 prior establishing Huyện Gia Lâm; current
#    rewrite uses Huyện. Tier T3 (multi-turn inherited).
# ═══════════════════════════════════════════════════════════════════════════

# v6 idx=191: "ngay mai thi sao?" ctx=Gia Lâm/weather_alert
SAMPLES.append({
    "_v6_idx": 191, "_fix_type": "FIX_PREFIX",
    "history": [
        {"user": "Gia Lâm có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Gia Lâm có cảnh báo thời tiết nào không?")}
    ],
    "input": "ngày mai thì sao?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai Huyện Gia Lâm còn giông không?"}
})

# v6 idx=1599
SAMPLES.append({
    "_v6_idx": 1599, "_fix_type": "FIX_PREFIX",
    "history": [
        {"user": "Gia Lâm thời tiết thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm như thế nào?")}
    ],
    "input": "Có ngập lụt không?",
    "output": {"intent": "weather_alert", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Gia Lâm có nguy cơ ngập lụt không?"}
})

# v6 idx=1734
SAMPLES.append({
    "_v6_idx": 1734, "_fix_type": "FIX_PREFIX",
    "history": [
        {"user": "Gia Lâm có giông không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Gia Lâm có giông không?")}
    ],
    "input": "Gió mạnh đến mức nào?",
    "output": {"intent": "wind_query", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Gió giông ở Huyện Gia Lâm mạnh đến mức nào?"}
})

# v6 idx=2819: user EXPLICITLY says "Hà Nội" — scope SWITCH district→city
SAMPLES.append({
    "_v6_idx": 2819, "_fix_type": "FIX_PREFIX",
    "history": [
        {"user": "Gia Lâm có cảnh báo gì không?",
         "assistant": asst("weather_alert", "district", 0.85,
                           "Huyện Gia Lâm có cảnh báo thời tiết nào không?")}
    ],
    "input": "Hà Nội có bị ngập không?",
    "output": {"intent": "weather_alert", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Hà Nội có nguy cơ ngập lụt không?"}
})

# v6 idx=3250
SAMPLES.append({
    "_v6_idx": 3250, "_fix_type": "FIX_PREFIX",
    "history": [
        {"user": "Gia Lâm hôm nay thời tiết thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Gia Lâm hôm nay thế nào?")}
    ],
    "input": "Thế còn ngày mai?",
    "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Ngày mai Huyện Gia Lâm thời tiết thế nào?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# B) 8 FIX_TIME — preserve user's time anchor (no drift)
# ═══════════════════════════════════════════════════════════════════════════

# v6 idx=479: "Ngày mai còn sương không?" — input self-contained, drop spurious ctx
SAMPLES.append({
    "_v6_idx": 479, "_fix_type": "FIX_TIME",
    "history": [],
    "input": "Ngày mai còn sương không?",
    "output": {"intent": "humidity_fog_query", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Hà Nội ngày mai có còn sương mù không?"}
})

# v6 idx=501: "So với hôm qua thế nào?" ctx Sóc Sơn (canonical=Huyện) seasonal
SAMPLES.append({
    "_v6_idx": 501, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Sóc Sơn hôm nay thời tiết thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "So với hôm qua thế nào?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Sóc Sơn hôm nay so với hôm qua thế nào?"}
})

# v6 idx=742: similar
SAMPLES.append({
    "_v6_idx": 742, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Sóc Sơn hôm nay thời tiết thế nào?",
         "assistant": asst("weather_overview", "district", 0.85,
                           "Thời tiết Huyện Sóc Sơn hôm nay thế nào?")}
    ],
    "input": "Hôm nay khác hôm qua ra sao?",
    "output": {"intent": "seasonal_context", "scope": "district", "confidence": 0.80,
               "rewritten_query": "Huyện Sóc Sơn hôm nay khác hôm qua ra sao?"}
})

# v6 idx=1055: "hom nay so voi ngay mai thi sao?" ctx Hoàn Kiếm (collision, default Phường)
SAMPLES.append({
    "_v6_idx": 1055, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Hoàn Kiếm thời tiết hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Hôm nay so với ngày mai thì sao?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay so với ngày mai ở Phường Hoàn Kiếm thời tiết khác nhau thế nào?"}
})

# v6 idx=1391: "Còn ngày kia?" ctx Hà Nội — v6 wrongly went historical; should be daily_forecast
SAMPLES.append({
    "_v6_idx": 1391, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Hà Nội ngày mai nhiệt độ cao nhất bao nhiêu?",
         "assistant": asst("daily_forecast", "city", 0.85,
                           "Nhiệt độ cao nhất Hà Nội ngày mai bao nhiêu?")}
    ],
    "input": "Còn ngày kia?",
    "output": {"intent": "daily_forecast", "scope": "city", "confidence": 0.80,
               "rewritten_query": "Nhiệt độ cao nhất Hà Nội ngày kia bao nhiêu?"}
})

# v6 idx=1407: same family as 1055
SAMPLES.append({
    "_v6_idx": 1407, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thời tiết thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Hôm nay so với ngày mai thì sao?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay so với ngày mai ở Phường Hoàn Kiếm thời tiết khác nhau thế nào?"}
})

# v6 idx=2147: "Ngày mai có sương không nhỉ?" — same family as 479
SAMPLES.append({
    "_v6_idx": 2147, "_fix_type": "FIX_TIME",
    "history": [],
    "input": "Ngày mai có sương không nhỉ?",
    "output": {"intent": "humidity_fog_query", "scope": "city", "confidence": 0.85,
               "rewritten_query": "Hà Nội ngày mai có sương mù không?"}
})

# v6 idx=2580: ctx Bồ Đề (Phường Bồ Đề pure ward); preserve "ngày mai"
SAMPLES.append({
    "_v6_idx": 2580, "_fix_type": "FIX_TIME",
    "history": [
        {"user": "Bồ Đề hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Bồ Đề hôm nay thế nào?")}
    ],
    "input": "Ngày mai thời tiết có khác không?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Ngày mai thời tiết Phường Bồ Đề có khác hôm nay không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# C) 25 FIX_POI_ADMIN — extract admin context, drop POI mention
#    Cases:
#    - POI + clear admin → rewrite uses admin only, scope per admin level, T2
#    - POI alone (mis-categorized as POI_ADMIN) → scope=ward, T5, rewrite=null
# ═══════════════════════════════════════════════════════════════════════════

# v6 idx=10: "Văn Miếu - Quốc Tử Giám" — full ward name match
# Phường Văn Miếu - Quốc Tử Giám exists; user said full phrase but no "Phường" prefix.
# Treat as ward (default ward when full phrase matches), T2.
SAMPLES.append({
    "_v6_idx": 10, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Văn Miếu - Quốc Tử Giám nhiệt độ hiện tại bao nhiêu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Nhiệt độ hiện tại Phường Văn Miếu - Quốc Tử Giám bao nhiêu?"}
})

# v6 idx=34: "Láng, Quận Đống Đa" — Phường Láng + Quận Đống Đa context
SAMPLES.append({
    "_v6_idx": 34, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Cho mình hỏi thời tiết ở Láng, Quận Đống Đa",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Phường Láng (Quận Đống Đa) hiện tại thế nào?"}
})

# v6 idx=60: "Văn Miếu - Quốc Tử Giám" + wind
SAMPLES.append({
    "_v6_idx": 60, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Gió ở Văn Miếu - Quốc Tử Giám hiện tại mạnh không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Gió ở Phường Văn Miếu - Quốc Tử Giám hiện tại mạnh không?"}
})

# v6 idx=65: "Sân bay Nội Bài" — POI compound, refuse + clarify
SAMPLES.append({
    "_v6_idx": 65, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tổng quan thời tiết ở Sân bay Nội Bài trưa nay",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=86: "Xã Yên Lãng" — explicit ward, clean admin (false-positive POI detect)
SAMPLES.append({
    "_v6_idx": 86, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Tình hình thời tiết Xã Yên Lãng trưa nay",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Thời tiết Xã Yên Lãng trưa nay thế nào?"}
})

# v6 idx=100: "san bay noi bai" pure POI → T5 abstain
SAMPLES.append({
    "_v6_idx": 100, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "gan day o san bay noi bai thoi tiet co bat thuong khong?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=119: "Lăng Bác" pure POI → T5
SAMPLES.append({
    "_v6_idx": 119, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm nay ở khu vực Lăng Bác có mưa không bạn?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=187: "Sân bay Nội Bài" → T5
SAMPLES.append({
    "_v6_idx": 187, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Có thông tin gì về thời tiết ở Sân bay Nội Bài trưa nay không?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=208: "Hồ Tây" pure POI → T5
SAMPLES.append({
    "_v6_idx": 208, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Giờ này ở Hồ Tây có độ ẩm cao không?",
    "output": {"intent": "humidity_fog_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=228: "Bệnh viện Bạch Mai" pure POI → T5
SAMPLES.append({
    "_v6_idx": 228, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết ngày hôm qua tại Bệnh viện Bạch Mai thế nào?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=229: "Phường Văn Miếu - Quốc Tử Giám" — explicit Phường prefix, clean
SAMPLES.append({
    "_v6_idx": 229, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Văn Miếu - Quốc Tử Giám tuần này có bất thường không?",
    "output": {"intent": "seasonal_context", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Phường Văn Miếu - Quốc Tử Giám tuần này thời tiết có bất thường không?"}
})

# v6 idx=268: "Lăng Chủ tịch" → T5
SAMPLES.append({
    "_v6_idx": 268, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Dự báo theo giờ ở Lăng Chủ tịch trưa nay",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=274: "lang gio nay" — Phường Láng (lowercase ambiguous, but Láng = ward)
SAMPLES.append({
    "_v6_idx": 274, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "tốc độ gió ở Láng giờ này thế nào?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Tốc độ gió ở Phường Láng giờ này bao nhiêu?"}
})

# v6 idx=287: "Phường Láng" — explicit, clean
SAMPLES.append({
    "_v6_idx": 287, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Phường Láng lúc này tốc độ gió bao nhiêu?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Tốc độ gió ở Phường Láng lúc này bao nhiêu?"}
})

# v6 idx=303: "Lăng Bác" → T5
SAMPLES.append({
    "_v6_idx": 303, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở Lăng Bác hôm nay mặc gì cho phù hợp?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=335: "Bệnh viện Bạch Mai" → T5
SAMPLES.append({
    "_v6_idx": 335, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Tối nay tại Bệnh viện Bạch Mai, thời tiết có ổn không nhỉ?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=355: "Lăng Chủ tịch" → T5
SAMPLES.append({
    "_v6_idx": 355, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Thời tiết bây giờ ở Lăng Chủ tịch như thế nào, bao nhiêu độ?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=387: "Lăng Bác" → T5
SAMPLES.append({
    "_v6_idx": 387, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hiện tại ở khu vực Lăng Bác thì trời ấm hay dễ chịu?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=416: "yen lang, me linh" — Xã Yên Lãng + Mê Linh (huyện) context
SAMPLES.append({
    "_v6_idx": 416, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "tổng quan thời tiết ở Yên Lãng, Mê Linh buổi tối",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.92,
               "rewritten_query": "Tổng quan thời tiết Xã Yên Lãng (Huyện Mê Linh) buổi tối"}
})

# v6 idx=447: "Lăng Bác và Hồ Tây" comparison — both POI → T5
SAMPLES.append({
    "_v6_idx": 447, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Lăng Bác và Hồ Tây, nơi nào thời tiết dễ chịu hơn vậy?",
    "output": {"intent": "location_comparison", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=454: "lang bac" → T5
SAMPLES.append({
    "_v6_idx": 454, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "bữa nay ở Lăng Bác có nắng không, có cần chuẩn bị áo khoác không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=465: "Văn Miếu - Quốc Tử Giám" full match → ward
SAMPLES.append({
    "_v6_idx": 465, "_fix_type": "FIX_POI_ADMIN",
    "history": [],
    "input": "Văn Miếu - Quốc Tử Giám tổng quan thời tiết hôm nay?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.85,
               "rewritten_query": "Tổng quan thời tiết Phường Văn Miếu - Quốc Tử Giám hôm nay"}
})

# v6 idx=510: "lang bac" → T5
SAMPLES.append({
    "_v6_idx": 510, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Lăng Bác mưa chưa tạnh?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=579: "Sân bay Nội Bài" → T5
SAMPLES.append({
    "_v6_idx": 579, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Hôm nay chiều ở Sân bay Nội Bài có khả năng mưa không ta?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# v6 idx=598: "Sân bay Nội Bài" → T5
SAMPLES.append({
    "_v6_idx": 598, "_fix_type": "FIX_POI_ADMIN_to_T5",
    "history": [],
    "input": "Ở Sân bay Nội Bài ngay bây giờ trời có nắng không?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.62,
               "rewritten_query": None}
})

# ═══════════════════════════════════════════════════════════════════════════
# D) 12 FIX_CONTEXT — collision core ambiguous, default to Phường (post-merger)
# ═══════════════════════════════════════════════════════════════════════════

# v6 idx=11: ctx=Cầu Giấy, "thang nay co mua nhieu khong?"
SAMPLES.append({
    "_v6_idx": 11, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "Tháng này có mưa nhiều không?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tháng này Phường Cầu Giấy có mưa nhiều không?"}
})

# v6 idx=28: ctx=Long Biên
SAMPLES.append({
    "_v6_idx": 28, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên thời tiết thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hiện tại thế nào?")}
    ],
    "input": "Nơi đó hôm nay thế nào?",
    "output": {"intent": "weather_overview", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết Phường Long Biên hôm nay như thế nào?"}
})

# v6 idx=63: ctx=Hoàn Kiếm
SAMPLES.append({
    "_v6_idx": 63, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Tuần trước như thế nào?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tuần trước thời tiết Phường Hoàn Kiếm như thế nào?"}
})

# v6 idx=68: ctx=Hoàn Kiếm
SAMPLES.append({
    "_v6_idx": 68, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay dự báo thế nào?",
         "assistant": asst("hourly_forecast", "ward", 0.85,
                           "Dự báo theo giờ Phường Hoàn Kiếm hôm nay")}
    ],
    "input": "Có tin gì về gió không?",
    "output": {"intent": "wind_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Có thông tin gì về gió ở Phường Hoàn Kiếm không?"}
})

# v6 idx=85: ctx=Hoàng Mai
SAMPLES.append({
    "_v6_idx": 85, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàng Mai hôm nay thế nào?",
         "assistant": asst("weather_overview", "ward", 0.85,
                           "Thời tiết Phường Hoàng Mai hôm nay thế nào?")}
    ],
    "input": "Hôm nay có thể ra ngoài làm gì không?",
    "output": {"intent": "activity_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Hôm nay ở Phường Hoàng Mai có thể làm hoạt động gì ngoài trời không?"}
})

# v6 idx=97: ctx=Cầu Giấy
SAMPLES.append({
    "_v6_idx": 97, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay nhiệt độ bao nhiêu?",
         "assistant": asst("temperature_query", "ward", 0.85,
                           "Nhiệt độ Phường Cầu Giấy hôm nay bao nhiêu?")}
    ],
    "input": "Thời tiết hôm nay thế nào?",
    "output": {"intent": "current_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Thời tiết Phường Cầu Giấy hôm nay thế nào?"}
})

# v6 idx=150: ctx=Hoàn Kiếm
SAMPLES.append({
    "_v6_idx": 150, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Hoàn Kiếm hôm nay thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Hoàn Kiếm hôm nay thế nào?")}
    ],
    "input": "Tối nay mấy độ?",
    "output": {"intent": "temperature_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Hoàn Kiếm bao nhiêu độ?"}
})

# v6 idx=175: ctx=Ba Đình
SAMPLES.append({
    "_v6_idx": 175, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Ba Đình hôm nay thời tiết thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Ba Đình hôm nay thế nào?")}
    ],
    "input": "Tuần trước thì sao?",
    "output": {"intent": "historical_weather", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tuần trước thời tiết Phường Ba Đình như thế nào?"}
})

# v6 idx=181: ctx=Tây Hồ
SAMPLES.append({
    "_v6_idx": 181, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ thời tiết thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Tây Hồ hiện tại thế nào?")}
    ],
    "input": "Sáng mai ở đó trời như thế nào?",
    "output": {"intent": "daily_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Sáng mai Phường Tây Hồ trời thế nào?"}
})

# v6 idx=188: ctx=Tây Hồ
SAMPLES.append({
    "_v6_idx": 188, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Tây Hồ hôm nay dự báo thế nào?",
         "assistant": asst("daily_forecast", "ward", 0.85,
                           "Dự báo thời tiết Phường Tây Hồ hôm nay thế nào?")}
    ],
    "input": "Tối nay thế nào?",
    "output": {"intent": "hourly_forecast", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Tối nay Phường Tây Hồ thời tiết ra sao?"}
})

# v6 idx=217: ctx=Cầu Giấy
SAMPLES.append({
    "_v6_idx": 217, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Cầu Giấy hôm nay UV thế nào?",
         "assistant": asst("expert_weather_param", "ward", 0.85,
                           "Chỉ số UV ở Phường Cầu Giấy hôm nay thế nào?")}
    ],
    "input": "UV đạt đỉnh vào khoảng mấy giờ?",
    "output": {"intent": "expert_weather_param", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "UV ở Phường Cầu Giấy hôm nay đạt đỉnh vào khoảng mấy giờ?"}
})

# v6 idx=225: ctx=Long Biên
SAMPLES.append({
    "_v6_idx": 225, "_fix_type": "FIX_CONTEXT",
    "history": [
        {"user": "Long Biên thời tiết thế nào?",
         "assistant": asst("current_weather", "ward", 0.85,
                           "Thời tiết Phường Long Biên hiện tại thế nào?")}
    ],
    "input": "Ở đó có mưa không?",
    "output": {"intent": "rain_query", "scope": "ward", "confidence": 0.80,
               "rewritten_query": "Phường Long Biên có mưa không?"}
})

# ═══════════════════════════════════════════════════════════════════════════
# Validate + write
# ═══════════════════════════════════════════════════════════════════════════
def validate(s: dict) -> list[str]:
    errs = []
    if 'history' not in s: errs.append('missing history')
    if 'input' not in s: errs.append('missing input')
    if 'output' not in s: errs.append('missing output')
    o = s.get('output', {})
    if o.get('intent') not in {
        'activity_weather', 'current_weather', 'daily_forecast', 'expert_weather_param',
        'historical_weather', 'hourly_forecast', 'humidity_fog_query', 'location_comparison',
        'rain_query', 'seasonal_context', 'smalltalk_weather', 'temperature_query',
        'weather_alert', 'weather_overview', 'wind_query',
    }: errs.append(f"bad intent: {o.get('intent')}")
    if o.get('scope') not in {'city', 'district', 'ward'}: errs.append(f"bad scope: {o.get('scope')}")
    c = o.get('confidence')
    if not isinstance(c, (int, float)) or not (0.5 <= c <= 1.0):
        errs.append(f"bad confidence: {c}")
    if not isinstance(s.get('history'), list):
        errs.append("history not a list")
    return errs

print(f'Total samples: {len(SAMPLES)}')
fix_types = {}
for s in SAMPLES:
    ft = s.get('_fix_type', 'unknown')
    fix_types[ft] = fix_types.get(ft, 0) + 1
print('By fix type:', fix_types)

# Validate all
total_errs = 0
for i, s in enumerate(SAMPLES):
    errs = validate(s)
    if errs:
        print(f'  [SAMPLE {i} v6_idx={s.get("_v6_idx")}] {errs}')
        total_errs += 1
print(f'Validation errors: {total_errs}')

if total_errs > 0:
    sys.exit(1)

# Write JSONL (strip _ meta keys)
out_path = Path(__file__).parent / 'batch_01_fix.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for s in SAMPLES:
        clean = {k: v for k, v in s.items() if not k.startswith('_')}
        f.write(json.dumps(clean, ensure_ascii=False) + '\n')

print(f'Wrote {out_path} ({len(SAMPLES)} samples)')
