"""
scripts/data/add_eval_questions.py
Append 28 manually crafted E2E evaluation questions to the eval CSV.

Coverage added:
  +8  ward-level questions (post-merger wards from dim_ward.csv)
  +5  out-of-scope queries
  +5  ambiguous / incomplete queries
  +5  typo / informal / no-diacritics queries
  +5  complex / multi-param queries

Total: 171 + 28 = 199 questions
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = ROOT / "data/evaluation/hanoi_weather_chatbot_eval_questions.csv"

FIELDNAMES = [
    "id", "question", "intent", "intent_vi", "location_scope", "location_name",
    "time_expression", "weather_param", "api_endpoint", "api_fields", "difficulty", "notes",
]

NEW_ROWS = [
    # ── Ward-level (8) — sử dụng phường từ dim_ward.csv (post-merger) ──────
    {
        "id": 172,
        "question": "Thời tiết tại phường Bạch Mai, Hai Bà Trưng hiện tại thế nào?",
        "intent": "current_weather", "intent_vi": "Thời tiết hiện tại",
        "location_scope": "ward", "location_name": "Bạch Mai (Hai Bà Trưng)",
        "time_expression": "hiện tại", "weather_param": "general",
        "api_endpoint": "onecall/current", "api_fields": "temp,weather,humidity,wind_speed",
        "difficulty": "easy", "notes": "Ward-level post-merger: Bạch Mai thuộc Hai Bà Trưng",
    },
    {
        "id": 173,
        "question": "Phường Lĩnh Nam, Hoàng Mai chiều nay có mưa không?",
        "intent": "rain_query", "intent_vi": "Truy vấn mưa",
        "location_scope": "ward", "location_name": "Lĩnh Nam (Hoàng Mai)",
        "time_expression": "chiều nay", "weather_param": "rain",
        "api_endpoint": "onecall/hourly", "api_fields": "pop,rain.1h,weather",
        "difficulty": "medium", "notes": "Ward-level: Lĩnh Nam - Hoàng Mai",
    },
    {
        "id": 174,
        "question": "Gió ở phường Vĩnh Tuy, Hai Bà Trưng tối nay mạnh không?",
        "intent": "wind_query", "intent_vi": "Truy vấn gió",
        "location_scope": "ward", "location_name": "Vĩnh Tuy (Hai Bà Trưng)",
        "time_expression": "tối nay", "weather_param": "wind",
        "api_endpoint": "onecall/hourly", "api_fields": "wind_speed,wind_gust,wind_deg",
        "difficulty": "easy", "notes": "Ward-level: Vĩnh Tuy - Hai Bà Trưng",
    },
    {
        "id": 175,
        "question": "Khoảng 8 giờ tối nay ở phường Nghĩa Đô, Cầu Giấy nhiệt độ bao nhiêu?",
        "intent": "hourly_forecast", "intent_vi": "Dự báo theo giờ",
        "location_scope": "ward", "location_name": "Nghĩa Đô (Cầu Giấy)",
        "time_expression": "20:00 hôm nay", "weather_param": "temperature",
        "api_endpoint": "onecall/hourly", "api_fields": "temp,feels_like",
        "difficulty": "medium", "notes": "Ward-level + giờ cụ thể: Nghĩa Đô - Cầu Giấy",
    },
    {
        "id": 176,
        "question": "Nhiệt độ phường Tương Mai, Hoàng Mai lúc này là bao nhiêu độ?",
        "intent": "temperature_query", "intent_vi": "Truy vấn nhiệt độ",
        "location_scope": "ward", "location_name": "Tương Mai (Hoàng Mai)",
        "time_expression": "hiện tại", "weather_param": "temperature",
        "api_endpoint": "onecall/current", "api_fields": "temp,feels_like",
        "difficulty": "easy", "notes": "Ward-level: Tương Mai - Hoàng Mai",
    },
    {
        "id": 177,
        "question": "Độ ẩm và khả năng có sương mù ở phường Giảng Võ, Ba Đình sáng nay thế nào?",
        "intent": "humidity_fog_query", "intent_vi": "Truy vấn độ ẩm/sương mù",
        "location_scope": "ward", "location_name": "Giảng Võ (Ba Đình)",
        "time_expression": "sáng nay", "weather_param": "humidity_fog",
        "api_endpoint": "onecall/current", "api_fields": "humidity,dew_point,visibility,weather",
        "difficulty": "medium", "notes": "Ward-level humidity+fog: Giảng Võ - Ba Đình",
    },
    {
        "id": 178,
        "question": "Dự báo thời tiết 3 ngày tới ở phường Kiến Hưng, Hà Đông ra sao?",
        "intent": "daily_forecast", "intent_vi": "Dự báo theo ngày",
        "location_scope": "ward", "location_name": "Kiến Hưng (Hà Đông)",
        "time_expression": "3 ngày tới", "weather_param": "general",
        "api_endpoint": "onecall/daily", "api_fields": "temp,weather,pop,wind_speed",
        "difficulty": "medium", "notes": "Ward-level daily forecast: Kiến Hưng - Hà Đông",
    },
    {
        "id": 179,
        "question": "Cuối tuần đi chạy bộ ở phường Xuân Phương, Nam Từ Liêm có thời tiết ổn không?",
        "intent": "activity_weather", "intent_vi": "Thời tiết theo hoạt động",
        "location_scope": "ward", "location_name": "Xuân Phương (Nam Từ Liêm)",
        "time_expression": "cuối tuần", "weather_param": "running",
        "api_endpoint": "onecall/daily", "api_fields": "temp,pop,wind_speed,humidity",
        "difficulty": "medium", "notes": "Ward-level activity (chạy bộ): Xuân Phương - Nam Từ Liêm",
    },
    # ── Out-of-scope (5) ─────────────────────────────────────────────────────
    {
        "id": 180,
        "question": "Giá vé máy bay Hà Nội - TP.HCM hôm nay bao nhiêu tiền?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "easy", "notes": "OOS: hỏi giá vé máy bay - ngoài domain thời tiết",
    },
    {
        "id": 181,
        "question": "Nhà hàng nào ngon ở quận Hoàn Kiếm?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "district", "location_name": "Hoàn Kiếm",
        "time_expression": "", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "easy", "notes": "OOS: hỏi nhà hàng - ngoài domain thời tiết",
    },
    {
        "id": 182,
        "question": "Thời tiết Đà Nẵng cuối tuần này thế nào?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "Đà Nẵng",
        "time_expression": "cuối tuần", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "easy", "notes": "OOS: địa điểm ngoài Hà Nội (Đà Nẵng) - cần từ chối lịch sự",
    },
    {
        "id": 183,
        "question": "Tỷ giá đô la Mỹ hôm nay bao nhiêu?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "easy", "notes": "OOS: hỏi tỷ giá - hoàn toàn ngoài domain",
    },
    {
        "id": 184,
        "question": "Bạn có thể viết code Python giúp mình không?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "easy", "notes": "OOS: yêu cầu lập trình - hoàn toàn ngoài domain",
    },
    # ── Ambiguous (5) ─────────────────────────────────────────────────────────
    {
        "id": 185,
        "question": "Ở đó nóng không?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "hiện tại", "weather_param": "temperature",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "hard", "notes": "Ambiguous: anaphoric reference không có context - chatbot cần hỏi lại",
    },
    {
        "id": 186,
        "question": "Thời tiết ngày mai?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "ngày mai", "weather_param": "general",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "hard", "notes": "Ambiguous: thiếu địa điểm - query chưa đầy đủ",
    },
    {
        "id": 187,
        "question": "Khu đó có mưa không?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "hiện tại", "weather_param": "rain",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "hard", "notes": "Ambiguous: anaphoric khu đó - thiếu context",
    },
    {
        "id": 188,
        "question": "Thế còn chỗ kia thì sao?",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "hiện tại", "weather_param": "general",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "hard", "notes": "Ambiguous: vague anaphora - hoàn toàn mơ hồ",
    },
    {
        "id": 189,
        "question": "Cho mình xem thời tiết đi.",
        "intent": "smalltalk_weather", "intent_vi": "Small talk khí tượng",
        "location_scope": "city", "location_name": "",
        "time_expression": "", "weather_param": "",
        "api_endpoint": "none", "api_fields": "none",
        "difficulty": "hard", "notes": "Ambiguous: không có địa điểm và thời gian - quá mơ hồ",
    },
    # ── Typo / Informal / No diacritics (5) ─────────────────────────────────
    {
        "id": 190,
        "question": "ha noi hom nay nong ko",
        "intent": "temperature_query", "intent_vi": "Truy vấn nhiệt độ",
        "location_scope": "city", "location_name": "Hà Nội",
        "time_expression": "hôm nay", "weather_param": "temperature",
        "api_endpoint": "onecall/current", "api_fields": "temp,feels_like",
        "difficulty": "medium", "notes": "Informal robustness: không dấu tiếng Việt",
    },
    {
        "id": 191,
        "question": "toi o cau giay troi mua k",
        "intent": "rain_query", "intent_vi": "Truy vấn mưa",
        "location_scope": "district", "location_name": "Cầu Giấy",
        "time_expression": "tối nay", "weather_param": "rain",
        "api_endpoint": "onecall/hourly", "api_fields": "pop,rain.1h",
        "difficulty": "medium", "notes": "Informal robustness: viết tắt và không dấu",
    },
    {
        "id": 192,
        "question": "troi ha noi co dep hem",
        "intent": "current_weather", "intent_vi": "Thời tiết hiện tại",
        "location_scope": "city", "location_name": "Hà Nội",
        "time_expression": "hiện tại", "weather_param": "general",
        "api_endpoint": "onecall/current", "api_fields": "weather,clouds",
        "difficulty": "medium", "notes": "Informal robustness: Southern slang hem=không + không dấu",
    },
    {
        "id": 193,
        "question": "nhiet do ha noi bnhieu do",
        "intent": "temperature_query", "intent_vi": "Truy vấn nhiệt độ",
        "location_scope": "city", "location_name": "Hà Nội",
        "time_expression": "hiện tại", "weather_param": "temperature",
        "api_endpoint": "onecall/current", "api_fields": "temp,feels_like",
        "difficulty": "medium", "notes": "Informal robustness: bnhieu=bao nhiêu + không dấu",
    },
    {
        "id": 194,
        "question": "bac tu liem hom nay co mua hong",
        "intent": "rain_query", "intent_vi": "Truy vấn mưa",
        "location_scope": "district", "location_name": "Bắc Từ Liêm",
        "time_expression": "hôm nay", "weather_param": "rain",
        "api_endpoint": "onecall/current", "api_fields": "pop,weather,rain.1h",
        "difficulty": "medium", "notes": "Informal robustness: Southern hong=không + không dấu",
    },
    # ── Complex / Multi-param (5) ─────────────────────────────────────────────
    {
        "id": 195,
        "question": "So sánh nhiệt độ hôm nay và ngày mai ở quận Hoàng Mai",
        "intent": "location_comparison", "intent_vi": "So sánh địa điểm",
        "location_scope": "district", "location_name": "Hoàng Mai",
        "time_expression": "hôm nay vs ngày mai", "weather_param": "temperature_compare",
        "api_endpoint": "onecall/current+daily", "api_fields": "temp,feels_like",
        "difficulty": "hard", "notes": "Complex: so sánh thời điểm current vs forecast",
    },
    {
        "id": 196,
        "question": "Chiều nay mưa không và nên mặc gì khi ra ngoài?",
        "intent": "activity_weather", "intent_vi": "Thời tiết theo hoạt động",
        "location_scope": "city", "location_name": "Hà Nội",
        "time_expression": "chiều nay", "weather_param": "rain+clothing",
        "api_endpoint": "onecall/hourly", "api_fields": "pop,rain.1h,temp,weather",
        "difficulty": "hard", "notes": "Complex multi-intent: rain query + clothing advice",
    },
    {
        "id": 197,
        "question": "Từ 6 giờ sáng đến 9 giờ tối nay nhiệt độ ở Ba Đình thay đổi thế nào?",
        "intent": "hourly_forecast", "intent_vi": "Dự báo theo giờ",
        "location_scope": "district", "location_name": "Ba Đình",
        "time_expression": "06:00-21:00 hôm nay", "weather_param": "temperature_trend",
        "api_endpoint": "onecall/hourly", "api_fields": "temp,feels_like,weather",
        "difficulty": "hard", "notes": "Complex: khoảng thời gian 15 giờ liên tục",
    },
    {
        "id": 198,
        "question": "Hà Nội tuần này ngày nào đẹp trời nhất để tổ chức sự kiện ngoài trời?",
        "intent": "activity_weather", "intent_vi": "Thời tiết theo hoạt động",
        "location_scope": "city", "location_name": "Hà Nội",
        "time_expression": "tuần này", "weather_param": "event",
        "api_endpoint": "onecall/daily", "api_fields": "temp,pop,wind_speed,weather",
        "difficulty": "hard", "notes": "Complex: lựa chọn ngày tốt nhất trong tuần",
    },
    {
        "id": 199,
        "question": "Cuối tuần đi Ba Vì thời tiết có ổn không, cần chuẩn bị những gì?",
        "intent": "activity_weather", "intent_vi": "Thời tiết theo hoạt động",
        "location_scope": "district", "location_name": "Ba Vì",
        "time_expression": "cuối tuần", "weather_param": "trip_planning",
        "api_endpoint": "onecall/daily", "api_fields": "temp,pop,wind_speed,weather,humidity",
        "difficulty": "hard", "notes": "Complex: trip planning với multiple weather criteria",
    },
]


def main():
    # Count existing rows
    existing_count = 0
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            existing_count += 1

    print(f"Existing questions: {existing_count}")

    # Append
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        for row in NEW_ROWS:
            writer.writerow(row)

    print(f"Added: {len(NEW_ROWS)} new questions")
    print(f"Total: {existing_count + len(NEW_ROWS)}")

    # Distribution check
    from collections import Counter
    scope_count: Counter = Counter()
    intent_count: Counter = Counter()
    diff_count: Counter = Counter()
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scope_count[row["location_scope"]] += 1
            intent_count[row["intent"]] += 1
            diff_count[row["difficulty"]] += 1

    total = sum(scope_count.values())
    print(f"\nScope distribution (n={total}):")
    for k, v in sorted(scope_count.items(), key=lambda x: -x[1]):
        print(f"  {k:<12} {v:>4}  ({v/total*100:.1f}%)")

    print(f"\nDifficulty distribution:")
    for k, v in sorted(diff_count.items(), key=lambda x: -x[1]):
        print(f"  {k:<12} {v:>4}  ({v/total*100:.1f}%)")


if __name__ == "__main__":
    main()
