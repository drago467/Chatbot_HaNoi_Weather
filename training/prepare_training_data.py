"""
Phase 1: Prepare training data for SLM Intent Router.

Steps:
1. Convert 171 eval CSV → seed JSONL
2. Template-based augmentation using REAL ward/district data from dim_ward.csv
3. Output: data/router/raw/seed.jsonl, data/router/raw/templates.jsonl,
           data/router/raw/seed_and_templates.jsonl
"""

import csv
import json
import random
from pathlib import Path
from collections import Counter, defaultdict

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "evaluation" / "hanoi_weather_chatbot_eval_questions.csv"
DIM_WARD_PATH = ROOT / "data" / "processed" / "dim_ward.csv"
POI_PATH = ROOT / "app" / "config" / "poi_mapping.json"
OUTPUT_DIR = ROOT / "data" / "router" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# System prompt for SLM Router
# ─────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Phân loại intent và location_scope cho câu hỏi thời tiết Hà Nội.\n\n"
    "Intents: current_weather, hourly_forecast, daily_forecast, weather_overview, "
    "rain_query, temperature_query, wind_query, humidity_fog_query, historical_weather, "
    "location_comparison, activity_weather, expert_weather_param, weather_alert, "
    "seasonal_context, smalltalk_weather\n\n"
    "Scopes: city (toàn Hà Nội hoặc không nói rõ địa điểm), "
    "district (quận/huyện), ward (phường/xã), poi (địa điểm cụ thể/nổi tiếng)"
)


# ─────────────────────────────────────────────
# Load REAL location data from project files
# ─────────────────────────────────────────────
def load_locations():
    """Load authoritative ward/district/POI data from project files."""
    # --- dim_ward.csv ---
    wards_by_district = defaultdict(list)
    all_districts = set()
    with open(DIM_WARD_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = row.get("district_name_vi", "").strip()
            w = row.get("ward_name_vi", "").strip()
            if d:
                all_districts.add(d)
            if d and w:
                wards_by_district[d].append(w)

    # Build flat lists
    districts = sorted(all_districts)
    wards = []  # (ward_name_vi, district_name_vi)
    for d, ws in wards_by_district.items():
        for w in ws:
            wards.append((w, d))

    # --- poi_mapping.json ---
    with open(POI_PATH, encoding="utf-8") as f:
        poi_map = json.load(f)
    pois = list(poi_map.keys())

    # Extract short district names (without Quận/Huyện/Thị xã prefix)
    # for natural language usage: "Cầu Giấy" instead of "Quận Cầu Giấy"
    def short_district(full_name: str) -> str:
        for prefix in ("Quận ", "Huyện ", "Thị xã "):
            if full_name.startswith(prefix):
                return full_name[len(prefix):]
        return full_name

    # Extract short ward names (without Phường/Xã prefix)
    def short_ward(full_name: str) -> str:
        for prefix in ("Phường ", "Xã "):
            if full_name.startswith(prefix):
                return full_name[len(prefix):]
        return full_name

    districts_short = {d: short_district(d) for d in districts}
    wards_short = {w: short_ward(w) for w, _ in wards}

    return {
        "districts": districts,
        "districts_short": districts_short,
        "wards": wards,  # List of (ward_full, district_full)
        "wards_short": wards_short,
        "pois": pois,
    }


LOCS = None  # Lazy-loaded


def _locs():
    global LOCS
    if LOCS is None:
        LOCS = load_locations()
    return LOCS


# ─────────────────────────────────────────────
# Random pickers using real data
# ─────────────────────────────────────────────
def _district_full():
    """Random full district name: 'Quận Cầu Giấy'."""
    return random.choice(_locs()["districts"])


def _district_short():
    """Random short district name: 'Cầu Giấy'."""
    d = random.choice(_locs()["districts"])
    return _locs()["districts_short"][d]


def _district_both():
    """Random district, return (full, short)."""
    d = random.choice(_locs()["districts"])
    return d, _locs()["districts_short"][d]


def _ward():
    """Random ward, return (ward_full, ward_short, district_full, district_short)."""
    w_full, d_full = random.choice(_locs()["wards"])
    w_short = _locs()["wards_short"][w_full]
    d_short = _locs()["districts_short"][d_full]
    return w_full, w_short, d_full, d_short


def _poi():
    """Random POI name."""
    return random.choice(_locs()["pois"])


# ─────────────────────────────────────────────
# Time expressions
# ─────────────────────────────────────────────
TIME_NOW = [
    "hiện tại", "bây giờ", "lúc này", "giờ này", "hiện giờ",
    "ngay bây giờ", "hiện nay",
]
TIME_TODAY = [
    "hôm nay", "sáng nay", "chiều nay", "tối nay",
    "trưa nay", "buổi chiều", "buổi tối",
]
TIME_TOMORROW = ["ngày mai", "sáng mai", "chiều mai", "tối mai"]
TIME_FUTURE = [
    "2 ngày tới", "3 ngày tới", "cuối tuần này", "tuần này",
    "cuối tuần", "thứ 7 này", "chủ nhật tới", "tuần sau",
    "3 giờ nữa", "vài giờ tới", "2 ngày nữa",
]
TIME_PAST = [
    "hôm qua", "tuần trước", "3 ngày trước", "tháng trước",
    "hôm kia", "2 ngày trước", "tuần qua",
]
TIME_COMPARE = [
    "hôm nay vs hôm qua", "so với hôm qua", "mấy ngày qua",
    "gần đây", "mùa này", "tuần này vs tuần trước",
]

EXPERT_PARAMS = [
    "điểm sương", "áp suất", "tầm nhìn xa", "chỉ số UV",
    "nhiệt độ cảm giác", "mây", "gió giật", "hướng gió",
]

ACTIVITIES = [
    "chạy bộ", "đạp xe", "đi dạo", "dã ngoại", "picnic",
    "du lịch", "cắm trại", "câu cá", "làm vườn", "bơi lội",
    "leo núi", "tập thể dục ngoài trời", "chụp ảnh ngoài trời",
    "đi bộ buổi sáng", "tổ chức sự kiện ngoài trời",
]


def _t(group):
    return random.choice(group)


# ─────────────────────────────────────────────
# Training sample format
# ─────────────────────────────────────────────
def make_sample(question: str, intent: str, scope: str, source: str = "template") -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": json.dumps(
                {"intent": intent, "scope": scope}, ensure_ascii=False
            )},
        ],
        "metadata": {"source": source, "intent": intent, "scope": scope},
    }


def load_seed_data() -> list[dict]:
    """Convert eval CSV → seed JSONL samples."""
    samples = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            samples.append(make_sample(
                question=row["question"],
                intent=row["intent"],
                scope=row["location_scope"],
                source="seed",
            ))
    return samples


# ─────────────────────────────────────────────
# Template definitions per intent × scope
#
# Naming convention for location references in templates:
#   - district: người dùng nói nhiều cách:
#     "quận Cầu Giấy", "Cầu Giấy", "ở Cầu Giấy", "bên Cầu Giấy"
#     Dùng short name, thi thoảng thêm "quận"/"huyện" prefix
#   - ward: "phường X, quận Y", "X, Y", "phường X"
#     Dùng short name, kèm district context
#   - poi: tên trực tiếp: "Hồ Gươm", "Sân bay Nội Bài"
# ─────────────────────────────────────────────

TEMPLATES = {
    # ── current_weather ──
    "current_weather": {
        "city": [
            lambda: f"Thời tiết Hà Nội {_t(TIME_NOW)} thế nào?",
            lambda: f"Trời Hà Nội {_t(TIME_NOW)} ra sao?",
            lambda: f"Cho mình biết thời tiết {_t(TIME_NOW)} ở Hà Nội",
            lambda: f"Hà Nội {_t(TIME_NOW)} trời có đẹp không?",
            lambda: f"{_t(TIME_NOW).capitalize()} ở Hà Nội nhiệt độ bao nhiêu?",
            lambda: f"Thời tiết {_t(TIME_NOW)} ở thủ đô thế nào nhỉ?",
            lambda: f"Ngoài trời Hà Nội {_t(TIME_NOW)} có nắng không?",
            lambda: f"Bây giờ Hà Nội trời thế nào?",
            lambda: f"Thời tiết Hà Nội đang ra sao?",
        ],
        "district": [
            lambda: f"Thời tiết ở {_district_short()} {_t(TIME_NOW)} thế nào?",
            lambda: f"{_t(TIME_NOW).capitalize()} ở quận {_district_short()} trời ra sao?",
            lambda: f"Cho mình biết thời tiết {_district_short()} {_t(TIME_NOW)}",
            lambda: f"Quận {_district_short()} {_t(TIME_NOW)} nhiệt độ bao nhiêu?",
            lambda: f"Ở {_district_short()} {_t(TIME_NOW)} trời có mưa không?",
            lambda: f"Ngoài trời ở {_district_short()} {_t(TIME_NOW)} thế nào?",
            lambda: f"Trời {_district_short()} {_t(TIME_NOW)} nóng hay mát?",
            lambda: f"Thời tiết huyện {_district_short()} {_t(TIME_NOW)} ra sao?",
            lambda: f"Bên {_district_short()} {_t(TIME_NOW)} trời thế nào?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Thời tiết ở {w[0]}, {w[3]} {_t(TIME_NOW)} thế nào?")[-1],
            lambda: (w := _ward(), f"{_t(TIME_NOW).capitalize()} ở {w[1]}, {w[3]} trời ra sao?")[-1],
            lambda: (w := _ward(), f"Phường {w[1]} ({w[3]}) {_t(TIME_NOW)} nhiệt độ bao nhiêu?")[-1],
            lambda: (w := _ward(), f"Cho mình hỏi thời tiết ở {w[1]}, {w[2]}")[-1],
            lambda: (w := _ward(), f"Xã {w[1]}, {w[3]} {_t(TIME_NOW)} trời thế nào?")[-1],
        ],
        "poi": [
            lambda: f"Thời tiết ở {_poi()} {_t(TIME_NOW)} thế nào?",
            lambda: f"{_t(TIME_NOW).capitalize()} ở khu vực {_poi()} trời ra sao?",
            lambda: f"Cho mình biết thời tiết ở {_poi()} {_t(TIME_NOW)}",
            lambda: f"Ở {_poi()} {_t(TIME_NOW)} trời có nắng không?",
            lambda: f"Thời tiết khu vực {_poi()} {_t(TIME_NOW)} thế nào?",
        ],
    },

    # ── hourly_forecast ──
    "hourly_forecast": {
        "city": [
            lambda: f"Dự báo thời tiết Hà Nội theo giờ {_t(TIME_TODAY)}",
            lambda: f"{_t(TIME_TODAY).capitalize()} thời tiết Hà Nội từng giờ thế nào?",
            lambda: f"Cho mình xem dự báo theo giờ Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Thời tiết Hà Nội {_t(TIME_TODAY)} biến đổi ra sao?",
            lambda: f"Dự báo chi tiết theo giờ cho Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Thời tiết Hà Nội các giờ tới thế nào?",
        ],
        "district": [
            lambda: f"Dự báo thời tiết {_district_short()} theo giờ {_t(TIME_TODAY)}",
            lambda: f"Thời tiết {_district_short()} {_t(TIME_TODAY)} từng giờ thế nào?",
            lambda: f"{_t(TIME_TODAY).capitalize()} ở quận {_district_short()} thời tiết thay đổi ra sao?",
            lambda: f"Cho mình biết dự báo theo giờ ở {_district_short()} {_t(TIME_TODAY)}",
            lambda: f"Thời tiết quận {_district_short()} {_t(TIME_TODAY)} diễn biến thế nào?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Dự báo theo giờ ở {w[1]}, {w[3]} {_t(TIME_TODAY)}")[-1],
            lambda: (w := _ward(), f"Thời tiết {w[0]} {_t(TIME_TODAY)} từng giờ ra sao?")[-1],
        ],
        "poi": [
            lambda: f"Dự báo theo giờ ở {_poi()} {_t(TIME_TODAY)}",
            lambda: f"Thời tiết ở {_poi()} {_t(TIME_TODAY)} biến đổi thế nào?",
            lambda: f"Cho mình xem dự báo theo giờ khu vực {_poi()}",
        ],
    },

    # ── daily_forecast ──
    "daily_forecast": {
        "city": [
            lambda: f"Dự báo thời tiết Hà Nội {_t(TIME_FUTURE)}",
            lambda: f"Thời tiết Hà Nội {_t(TIME_FUTURE)} thế nào?",
            lambda: f"{_t(TIME_TOMORROW).capitalize()} thời tiết Hà Nội ra sao?",
            lambda: f"Dự báo {_t(TIME_FUTURE)} ở Hà Nội",
            lambda: f"Thời tiết những ngày tới ở Hà Nội thế nào?",
            lambda: f"Hà Nội {_t(TIME_TOMORROW)} trời thế nào?",
        ],
        "district": [
            lambda: f"Dự báo thời tiết {_district_short()} {_t(TIME_FUTURE)}",
            lambda: f"Thời tiết quận {_district_short()} {_t(TIME_TOMORROW)} thế nào?",
            lambda: f"{_t(TIME_FUTURE).capitalize()} ở {_district_short()} thời tiết ra sao?",
            lambda: f"Dự báo {_t(TIME_TOMORROW)} cho quận {_district_short()}",
            lambda: f"Mấy ngày tới ở {_district_short()} thời tiết thế nào?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Dự báo thời tiết {w[1]}, {w[3]} {_t(TIME_FUTURE)}")[-1],
            lambda: (w := _ward(), f"Thời tiết {w[0]} {_t(TIME_TOMORROW)} ra sao?")[-1],
            lambda: (w := _ward(), f"{_t(TIME_TOMORROW).capitalize()} ở xã {w[1]} trời thế nào?")[-1],
        ],
        "poi": [
            lambda: f"Dự báo thời tiết ở {_poi()} {_t(TIME_TOMORROW)}",
            lambda: f"Thời tiết {_poi()} {_t(TIME_FUTURE)} thế nào?",
            lambda: f"{_t(TIME_TOMORROW).capitalize()} ở {_poi()} trời ra sao?",
        ],
    },

    # ── weather_overview ──
    "weather_overview": {
        "city": [
            lambda: f"Tổng quan thời tiết Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Cho mình cái nhìn tổng thể về thời tiết Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Thời tiết Hà Nội {_t(TIME_TODAY)} nhìn chung thế nào?",
            lambda: f"Tóm tắt thời tiết Hà Nội {_t(TIME_TODAY)} cho mình",
            lambda: f"Hà Nội {_t(TIME_TODAY)} thời tiết chung ra sao?",
            lambda: f"Tình hình thời tiết chung ở Hà Nội {_t(TIME_TODAY)}",
        ],
        "district": [
            lambda: f"Tổng quan thời tiết {_district_short()} {_t(TIME_TODAY)}",
            lambda: f"Thời tiết quận {_district_short()} {_t(TIME_TODAY)} nhìn chung thế nào?",
            lambda: f"Tóm tắt thời tiết ở {_district_short()} {_t(TIME_TODAY)}",
            lambda: f"Cho mình biết tình hình thời tiết {_district_short()} {_t(TIME_TODAY)}",
        ],
        "ward": [
            lambda: (w := _ward(), f"Tổng quan thời tiết ở {w[1]}, {w[3]} {_t(TIME_TODAY)}")[-1],
            lambda: (w := _ward(), f"Tình hình thời tiết {w[0]} {_t(TIME_TODAY)}")[-1],
        ],
        "poi": [
            lambda: f"Tổng quan thời tiết ở {_poi()} {_t(TIME_TODAY)}",
            lambda: f"Tình hình thời tiết khu vực {_poi()} {_t(TIME_TODAY)} thế nào?",
        ],
    },

    # ── rain_query ──
    "rain_query": {
        "city": [
            lambda: f"Hà Nội {_t(TIME_TODAY)} có mưa không?",
            lambda: f"{_t(TIME_TODAY).capitalize()} Hà Nội mưa không nhỉ?",
            lambda: f"Khả năng mưa ở Hà Nội {_t(TIME_TODAY)} bao nhiêu phần trăm?",
            lambda: f"Hà Nội {_t(TIME_FUTURE)} có mưa không?",
            lambda: f"Khi nào Hà Nội sẽ mưa?",
            lambda: f"Trời Hà Nội có sắp mưa không?",
            lambda: f"Mưa bao giờ tạnh ở Hà Nội?",
            lambda: f"Hà Nội {_t(TIME_TOMORROW)} có mưa không?",
        ],
        "district": [
            lambda: f"{_district_short()} {_t(TIME_TODAY)} có mưa không?",
            lambda: f"Quận {_district_short()} {_t(TIME_TODAY)} mưa không nhỉ?",
            lambda: f"Xác suất mưa ở {_district_short()} {_t(TIME_TODAY)} bao nhiêu?",
            lambda: f"{_t(TIME_TODAY).capitalize()} bên {_district_short()} có mưa không?",
            lambda: f"Ở {_district_short()} có đang mưa không?",
            lambda: f"Khi nào {_district_short()} hết mưa?",
        ],
        "ward": [
            lambda: (w := _ward(), f"{w[1]}, {w[3]} {_t(TIME_TODAY)} có mưa không?")[-1],
            lambda: (w := _ward(), f"Phường {w[1]} {_t(TIME_TODAY)} mưa không?")[-1],
            lambda: (w := _ward(), f"Trời ở {w[1]}, {w[3]} có đang mưa không?")[-1],
        ],
        "poi": [
            lambda: f"Ở {_poi()} {_t(TIME_TODAY)} có mưa không?",
            lambda: f"Khu vực {_poi()} {_t(TIME_TODAY)} mưa không nhỉ?",
            lambda: f"Có mưa ở {_poi()} không?",
        ],
    },

    # ── temperature_query ──
    "temperature_query": {
        "city": [
            lambda: f"Nhiệt độ Hà Nội {_t(TIME_NOW)} bao nhiêu?",
            lambda: f"Hà Nội {_t(TIME_TODAY)} nóng bao nhiêu độ?",
            lambda: f"Nhiệt độ cao nhất ở Hà Nội {_t(TIME_TODAY)} là bao nhiêu?",
            lambda: f"Hà Nội {_t(TIME_TODAY)} nóng hay lạnh?",
            lambda: f"Nhiệt độ thấp nhất {_t(TIME_TODAY)} ở Hà Nội?",
            lambda: f"Hà Nội hôm nay bao nhiêu độ C?",
        ],
        "district": [
            lambda: f"Nhiệt độ ở {_district_short()} {_t(TIME_NOW)} bao nhiêu?",
            lambda: f"Quận {_district_short()} {_t(TIME_TODAY)} nóng bao nhiêu độ?",
            lambda: f"{_district_short()} {_t(TIME_TODAY)} nhiệt độ cao nhất bao nhiêu?",
            lambda: f"Ở {_district_short()} {_t(TIME_NOW)} bao nhiêu độ?",
            lambda: f"Nhiệt độ {_district_short()} {_t(TIME_TODAY)} thấp nhất là mấy?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Nhiệt độ ở {w[1]}, {w[3]} {_t(TIME_NOW)} bao nhiêu?")[-1],
            lambda: (w := _ward(), f"{w[0]} {_t(TIME_TODAY)} nóng bao nhiêu?")[-1],
        ],
        "poi": [
            lambda: f"Nhiệt độ ở {_poi()} {_t(TIME_NOW)} bao nhiêu độ?",
            lambda: f"Ở khu vực {_poi()} {_t(TIME_NOW)} nóng hay mát?",
            lambda: f"Bao nhiêu độ ở {_poi()} {_t(TIME_NOW)}?",
        ],
    },

    # ── wind_query ──
    "wind_query": {
        "city": [
            lambda: f"Gió ở Hà Nội {_t(TIME_NOW)} mạnh không?",
            lambda: f"Tốc độ gió Hà Nội {_t(TIME_TODAY)} bao nhiêu?",
            lambda: f"Hà Nội {_t(TIME_TODAY)} có gió mạnh không?",
            lambda: f"Hướng gió Hà Nội {_t(TIME_NOW)} thế nào?",
            lambda: f"Gió giật ở Hà Nội {_t(TIME_TODAY)} có mạnh không?",
        ],
        "district": [
            lambda: f"Gió ở {_district_short()} {_t(TIME_NOW)} mạnh không?",
            lambda: f"Tốc độ gió ở quận {_district_short()} bao nhiêu?",
            lambda: f"{_district_short()} {_t(TIME_TODAY)} gió thế nào?",
            lambda: f"Ở {_district_short()} {_t(TIME_NOW)} có gió giật không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Gió ở {w[1]}, {w[3]} {_t(TIME_NOW)} mạnh không?")[-1],
            lambda: (w := _ward(), f"{w[0]} {_t(TIME_NOW)} tốc độ gió bao nhiêu?")[-1],
        ],
        "poi": [
            lambda: f"Gió ở {_poi()} {_t(TIME_NOW)} mạnh không?",
            lambda: f"Tốc độ gió ở khu vực {_poi()} bao nhiêu?",
        ],
    },

    # ── humidity_fog_query ──
    "humidity_fog_query": {
        "city": [
            lambda: f"Độ ẩm Hà Nội {_t(TIME_NOW)} bao nhiêu?",
            lambda: f"Hà Nội {_t(TIME_TODAY)} có sương mù không?",
            lambda: f"Độ ẩm ở Hà Nội {_t(TIME_TODAY)} cao không?",
            lambda: f"Trời Hà Nội {_t(TIME_TODAY)} có sương không?",
            lambda: f"Hà Nội sáng nay có mù không nhỉ?",
        ],
        "district": [
            lambda: f"Độ ẩm ở {_district_short()} {_t(TIME_NOW)} bao nhiêu?",
            lambda: f"Quận {_district_short()} {_t(TIME_TODAY)} có sương mù không?",
            lambda: f"{_district_short()} {_t(TIME_NOW)} độ ẩm cao không?",
            lambda: f"Ở {_district_short()} {_t(TIME_TODAY)} có sương không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Độ ẩm ở {w[1]}, {w[3]} bao nhiêu?")[-1],
            lambda: (w := _ward(), f"{w[0]} {_t(TIME_TODAY)} có sương mù không?")[-1],
        ],
        "poi": [
            lambda: f"Độ ẩm ở {_poi()} {_t(TIME_NOW)} bao nhiêu?",
            lambda: f"Khu vực {_poi()} {_t(TIME_TODAY)} có sương mù không?",
        ],
    },

    # ── historical_weather ──
    "historical_weather": {
        "city": [
            lambda: f"Thời tiết Hà Nội {_t(TIME_PAST)} thế nào?",
            lambda: f"{_t(TIME_PAST).capitalize()} Hà Nội trời ra sao?",
            lambda: f"Cho mình xem lịch sử thời tiết Hà Nội {_t(TIME_PAST)}",
            lambda: f"Hà Nội {_t(TIME_PAST)} nhiệt độ bao nhiêu?",
            lambda: f"{_t(TIME_PAST).capitalize()} Hà Nội có mưa không?",
        ],
        "district": [
            lambda: f"Thời tiết {_district_short()} {_t(TIME_PAST)} thế nào?",
            lambda: f"{_t(TIME_PAST).capitalize()} ở quận {_district_short()} trời ra sao?",
            lambda: f"Nhiệt độ ở {_district_short()} {_t(TIME_PAST)} bao nhiêu?",
            lambda: f"{_district_short()} {_t(TIME_PAST)} có mưa không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Thời tiết {w[1]}, {w[3]} {_t(TIME_PAST)} thế nào?")[-1],
            lambda: (w := _ward(), f"{_t(TIME_PAST).capitalize()} ở {w[0]} trời ra sao?")[-1],
        ],
        "poi": [
            lambda: f"Thời tiết ở {_poi()} {_t(TIME_PAST)} thế nào?",
            lambda: f"{_t(TIME_PAST).capitalize()} ở {_poi()} trời ra sao?",
        ],
    },

    # ── location_comparison ──
    "location_comparison": {
        "city": [
            lambda: f"Quận nào ở Hà Nội {_t(TIME_NOW)} nóng nhất?",
            lambda: f"So sánh thời tiết các quận ở Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Quận nào mát nhất Hà Nội {_t(TIME_NOW)}?",
            lambda: f"Xếp hạng nhiệt độ các quận Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Quận nào ở Hà Nội đang mưa?",
            lambda: f"Nơi nào ở Hà Nội {_t(TIME_NOW)} nóng nhất?",
        ],
        "district": [
            lambda: (d1 := _district_short(), d2 := _district_short(),
                     f"So sánh thời tiết {d1} và {d2} {_t(TIME_TODAY)}")[-1],
            lambda: (d1 := _district_short(), d2 := _district_short(),
                     f"{_t(TIME_NOW).capitalize()} {d1} hay {d2} nóng hơn?")[-1],
            lambda: (d1 := _district_short(), d2 := _district_short(),
                     f"Thời tiết {d1} có khác {d2} không?")[-1],
            lambda: f"So sánh thời tiết giữa {_district_short()} với {_district_short()}",
        ],
        "ward": [
            lambda: (w1 := _ward(), w2 := _ward(),
                     f"So sánh thời tiết {w1[0]} và {w2[0]}")[-1],
            lambda: (w1 := _ward(), w2 := _ward(),
                     f"{w1[1]} ({w1[3]}) hay {w2[1]} ({w2[3]}) nóng hơn?")[-1],
        ],
        "poi": [
            lambda: (p1 := _poi(), p2 := _poi(),
                     f"So sánh thời tiết {p1} và {p2}")[-1],
            lambda: (p1 := _poi(), p2 := _poi(),
                     f"Ở {p1} hay {p2} mát hơn?")[-1],
        ],
    },

    # ── activity_weather ──
    "activity_weather": {
        "city": [
            lambda: (a := random.choice(ACTIVITIES),
                     f"Hà Nội {_t(TIME_TODAY)} có nên {a} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Thời tiết Hà Nội {_t(TIME_TODAY)} có phù hợp để {a} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Hôm nay đi {a} ở Hà Nội được không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Mình muốn {a} ở Hà Nội {_t(TIME_TODAY)}, thời tiết có ổn không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Lúc nào {_t(TIME_TODAY)} thích hợp để {a} ở Hà Nội?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Có nên {a} ở Hà Nội {_t(TIME_TOMORROW)} không?")[-1],
        ],
        "district": [
            lambda: (a := random.choice(ACTIVITIES),
                     f"Có nên {a} ở {_district_short()} {_t(TIME_TODAY)} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Thời tiết {_district_short()} {_t(TIME_TODAY)} có phù hợp để {a} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Mình muốn {a} ở quận {_district_short()}, thời tiết thế nào?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Ở {_district_short()} {_t(TIME_TODAY)} có thuận lợi cho việc {a} không?")[-1],
        ],
        "ward": [
            lambda: (a := random.choice(ACTIVITIES), w := _ward(),
                     f"Có nên {a} ở {w[1]}, {w[3]} {_t(TIME_TODAY)} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES), w := _ward(),
                     f"Thời tiết {w[0]} {_t(TIME_TODAY)} có ổn để {a} không?")[-1],
        ],
        "poi": [
            lambda: (a := random.choice(ACTIVITIES),
                     f"Thời tiết ở {_poi()} có phù hợp để {a} không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Mình muốn {a} ở {_poi()} {_t(TIME_TODAY)}, thời tiết ổn không?")[-1],
            lambda: (a := random.choice(ACTIVITIES),
                     f"Có nên {a} ở {_poi()} {_t(TIME_TODAY)} không?")[-1],
        ],
    },

    # ── expert_weather_param ──
    "expert_weather_param": {
        "city": [
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"{p.capitalize()} ở Hà Nội {_t(TIME_NOW)} bao nhiêu?")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"Cho mình biết {p} ở Hà Nội {_t(TIME_TODAY)}")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"Chỉ số {p} Hà Nội {_t(TIME_NOW)} là bao nhiêu?")[-1],
            lambda: f"Chỉ số UV ở Hà Nội {_t(TIME_TODAY)} có cao không?",
            lambda: f"Áp suất khí quyển Hà Nội {_t(TIME_NOW)} bao nhiêu?",
        ],
        "district": [
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"{p.capitalize()} ở {_district_short()} {_t(TIME_NOW)} bao nhiêu?")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"Cho mình biết {p} ở quận {_district_short()}")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"Chỉ số {p} ở {_district_short()} {_t(TIME_NOW)} là bao nhiêu?")[-1],
        ],
        "ward": [
            lambda: (p := random.choice(EXPERT_PARAMS), w := _ward(),
                     f"{p.capitalize()} ở {w[1]}, {w[3]} {_t(TIME_NOW)} bao nhiêu?")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS), w := _ward(),
                     f"Cho mình biết {p} ở {w[0]}")[-1],
        ],
        "poi": [
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"{p.capitalize()} ở {_poi()} {_t(TIME_NOW)} bao nhiêu?")[-1],
            lambda: (p := random.choice(EXPERT_PARAMS),
                     f"Chỉ số {p} khu vực {_poi()} thế nào?")[-1],
        ],
    },

    # ── weather_alert ──
    "weather_alert": {
        "city": [
            lambda: f"Hà Nội {_t(TIME_TODAY)} có cảnh báo thời tiết gì không?",
            lambda: f"Có cảnh báo mưa lớn ở Hà Nội {_t(TIME_TODAY)} không?",
            lambda: f"Cảnh báo thời tiết Hà Nội {_t(TIME_TODAY)}",
            lambda: f"Hà Nội {_t(TIME_TODAY)} có nguy cơ ngập lụt không?",
            lambda: f"Thời tiết Hà Nội {_t(TIME_TODAY)} có gì đáng lo không?",
            lambda: f"Cảnh báo nắng nóng Hà Nội {_t(TIME_TODAY)} thế nào?",
        ],
        "district": [
            lambda: f"Quận {_district_short()} {_t(TIME_TODAY)} có cảnh báo thời tiết gì không?",
            lambda: f"Cảnh báo thời tiết ở {_district_short()} {_t(TIME_TODAY)}",
            lambda: f"{_district_short()} {_t(TIME_TODAY)} có nguy cơ mưa to không?",
            lambda: f"Có cảnh báo gì đặc biệt ở {_district_short()} {_t(TIME_TODAY)} không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Cảnh báo thời tiết ở {w[1]}, {w[3]} {_t(TIME_TODAY)}")[-1],
            lambda: (w := _ward(), f"{w[0]} {_t(TIME_TODAY)} có nguy hiểm gì không?")[-1],
        ],
        "poi": [
            lambda: f"Ở {_poi()} {_t(TIME_TODAY)} có cảnh báo thời tiết gì không?",
            lambda: f"Khu vực {_poi()} {_t(TIME_TODAY)} có an toàn không?",
        ],
    },

    # ── seasonal_context ──
    "seasonal_context": {
        "city": [
            lambda: f"Hôm nay Hà Nội nóng hơn hôm qua không?",
            lambda: f"So với hôm qua thì thời tiết Hà Nội hôm nay thế nào?",
            lambda: f"Nhiệt độ Hà Nội mấy ngày nay có xu hướng tăng hay giảm?",
            lambda: f"Hà Nội năm nay rét muộn không?",
            lambda: f"Thời tiết Hà Nội {_t(TIME_TODAY)} có gì bất thường không?",
            lambda: f"Hà Nội {_t(TIME_COMPARE)} thời tiết khác nhau thế nào?",
            lambda: f"Mùa này Hà Nội thường mưa nhiều không?",
            lambda: f"Hà Nội gần đây có hiện tượng thời tiết cực đoan không?",
            lambda: f"Thời tiết Hà Nội gần đây biến đổi ra sao?",
        ],
        "district": [
            lambda: f"So với hôm qua thì {_district_short()} hôm nay thế nào?",
            lambda: f"{_district_short()} hôm nay nóng hơn hôm qua không?",
            lambda: f"Nhiệt độ ở {_district_short()} mấy ngày nay tăng hay giảm?",
            lambda: f"Thời tiết {_district_short()} {_t(TIME_COMPARE)} có thay đổi gì không?",
            lambda: f"Ở quận {_district_short()} gần đây thời tiết có bất thường không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"So với hôm qua thì {w[1]}, {w[3]} hôm nay thế nào?")[-1],
            lambda: (w := _ward(), f"Nhiệt độ {w[0]} hôm nay so với hôm qua chênh bao nhiêu?")[-1],
            lambda: (w := _ward(), f"Ở {w[1]} gần đây thời tiết có gì lạ không?")[-1],
        ],
        "poi": [
            lambda: f"So với hôm qua thì ở {_poi()} hôm nay thế nào?",
            lambda: f"Nhiệt độ {_poi()} hôm nay so với hôm qua chênh bao nhiêu?",
            lambda: f"Gần đây ở {_poi()} thời tiết có bất thường không?",
        ],
    },

    # ── smalltalk_weather ──
    "smalltalk_weather": {
        "city": [
            lambda: "Hôm nay trời đẹp nhỉ?",
            lambda: "Ra ngoài có cần mang ô không?",
            lambda: "Hà Nội hôm nay nên mặc gì?",
            lambda: "Thời tiết ở Đà Nẵng thế nào?",
            lambda: "Bạn là ai?",
            lambda: "Hôm nay đi ra ngoài có cần áo khoác không?",
            lambda: "Trời hôm nay có buồn không nhỉ?",
            lambda: "Nên mặc áo mỏng hay dày hôm nay?",
            lambda: "Tối nay trời có sao không nhỉ?",
            lambda: "Cảm ơn bạn nhé!",
            lambda: "Xin chào, bạn giúp mình được gì?",
        ],
        "district": [
            lambda: f"Ở {_district_short()} hôm nay có cần mang ô không?",
            lambda: f"Đi {_district_short()} hôm nay mặc gì cho phù hợp?",
            lambda: f"Trời ở {_district_short()} hôm nay đẹp không?",
        ],
        "ward": [
            lambda: (w := _ward(), f"Ở {w[1]} hôm nay cần mang ô không?")[-1],
            lambda: (w := _ward(), f"Ra ngoài ở {w[1]}, {w[3]} có cần áo khoác không?")[-1],
        ],
        "poi": [
            lambda: f"Đi {_poi()} hôm nay có cần mang ô không?",
            lambda: f"Ở {_poi()} hôm nay mặc gì cho phù hợp?",
        ],
    },
}


def generate_template_samples(target_per_combo: int = 12) -> list[dict]:
    """
    Generate template-based samples to balance all intent×scope combos.
    Uses real location data from dim_ward.csv and poi_mapping.json.
    """
    samples = []

    for intent, scopes in TEMPLATES.items():
        for scope, template_fns in scopes.items():
            seen = set()
            attempts = 0

            while len(seen) < target_per_combo and attempts < target_per_combo * 8:
                fn = random.choice(template_fns)
                question = fn()
                if question not in seen:
                    seen.add(question)
                    samples.append(make_sample(question, intent, scope, source="template"))
                attempts += 1

    return samples


def deduplicate(samples: list[dict]) -> list[dict]:
    """Remove duplicate questions (keep first occurrence, prefer 'seed' source)."""
    # Sort so seed comes first
    samples.sort(key=lambda s: (0 if s["metadata"]["source"] == "seed" else 1))
    seen = set()
    result = []
    for s in samples:
        q = s["messages"][1]["content"]
        if q not in seen:
            seen.add(q)
            result.append(s)
    return result


def print_distribution(samples: list[dict], label: str = ""):
    combo_counts = Counter()
    intent_counts = Counter()
    scope_counts = Counter()
    source_counts = Counter()
    for s in samples:
        meta = s["metadata"]
        combo_counts[(meta["intent"], meta["scope"])] += 1
        intent_counts[meta["intent"]] += 1
        scope_counts[meta["scope"]] += 1
        source_counts[meta["source"]] += 1

    print(f"\n{'='*60}")
    print(f"  {label}: {len(samples)} samples")
    print(f"{'='*60}")

    print(f"\n  Sources: {dict(source_counts)}")

    print(f"\n  Intents ({len(intent_counts)}):")
    for k, v in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:30s} {v:4d}")

    print(f"\n  Scopes ({len(scope_counts)}):")
    for k, v in sorted(scope_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:15s} {v:4d}")

    # Show min/max per combo
    vals = list(combo_counts.values())
    print(f"\n  Intent×Scope combos: {len(combo_counts)}, "
          f"min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.1f}")

    low = [(k, v) for k, v in combo_counts.items() if v < 5]
    if low:
        print(f"\n  LOW-COUNT combos (<5):")
        for k, v in sorted(low, key=lambda x: x[1]):
            print(f"    {k[0]:30s} × {k[1]:10s} = {v:3d}")


def save_jsonl(samples: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            json.dump(s, f, ensure_ascii=False)
            f.write("\n")
    print(f"\n  Saved {len(samples)} samples → {path}")


def main():
    print("Phase 1.1: Prepare training data for SLM Intent Router")
    print("=" * 60)

    # Step 1: Load seed data
    print("\n[1/4] Loading seed data from eval CSV...")
    seed = load_seed_data()
    print_distribution(seed, "Seed data (eval CSV)")

    # Step 2: Generate templates using real location data
    print("\n[2/4] Generating template-based samples (real dim_ward data)...")
    locs = _locs()
    print(f"  Loaded: {len(locs['districts'])} districts, "
          f"{len(locs['wards'])} wards, {len(locs['pois'])} POIs")
    templates = generate_template_samples(target_per_combo=12)
    print_distribution(templates, "Template data")

    # Step 3: Merge & deduplicate
    print("\n[3/4] Merging and deduplicating...")
    all_samples = seed + templates
    all_samples = deduplicate(all_samples)
    print_distribution(all_samples, "Merged (seed + templates, deduplicated)")

    # Step 4: Save
    print("\n[4/4] Saving...")
    save_jsonl(seed, OUTPUT_DIR / "seed.jsonl")
    save_jsonl(templates, OUTPUT_DIR / "templates.jsonl")
    save_jsonl(all_samples, OUTPUT_DIR / "seed_and_templates.jsonl")

    print(f"\n{'='*60}")
    print(f"  Done! Ready for LLM augmentation (augment_with_llm.py)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
