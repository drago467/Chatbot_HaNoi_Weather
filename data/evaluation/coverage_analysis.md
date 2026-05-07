# Coverage Analysis v1 — 199 câu cũ trên 135-cell matrix

> Output của PR-B.1. Phân tích phân bố 199 câu cũ (`hanoi_weather_chatbot_eval_questions.csv`) sang 135-cell matrix (15 intent × 3 scope × 3 difficulty), identify gap để PR-B.2+ fill bằng 301 câu mới.

## Tổng quan

| | Count |
|---|---|
| Total 199 cũ | 199 |
| Non-POI (vào 135-cell matrix) | **184** |
| POI (relabel `expected_clarification=True`, ngoài matrix) | **15** |
| Cells trong matrix có ≥1 câu | 81 / 135 (60%) |
| Cells **empty** (0 câu) | **54 / 135 (40%)** |
| Cells **thin** (1-2 câu) | 60 / 135 (44%) |
| Cells **ok** (≥3 câu cho city/district hoặc ≥4 cho ward) | 21 / 135 (16%) |

## Per-scope summary

| Scope | Cells | Old count | Target/cell | Min gap | After fill |
|---|---|---|---|---|---|
| `city` | 45 | 91 | 3 | 61 | ~135 |
| `district` | 45 | 79 | 3 | 71 | ~135 |
| `ward` | 45 | 14 | 4 | **166** | ~180 |
| **Total** | 135 | 184 | — | **298** | ~485 |

**Budget mới: 301 câu** → fits 298 min gap + 3 spare.
**Cuối cùng: 485 (matrix) + 15 (POI abstention) = 500 câu.**

## Per-intent distribution (184 non-POI)

| Intent | Total | city | district | ward | easy | medium | hard |
|---|---|---|---|---|---|---|---|
| `current_weather` | 6 | 3 | 1 | 2 | 5 | 1 | 0 |
| `hourly_forecast` | 10 | 1 | 7 | 2 | 2 | 6 | 2 |
| `daily_forecast` | 13 | 4 | 7 | 2 | 6 | 4 | 3 |
| `weather_overview` | 10 | 5 | 5 | 0 | 4 | 5 | 1 |
| `rain_query` | 18 | 7 | 9 | 2 | 7 | 7 | 4 |
| `temperature_query` | 16 | 6 | 9 | 1 | 10 | 4 | 2 |
| `wind_query` | 12 | 5 | 6 | 1 | 8 | 3 | 1 |
| `humidity_fog_query` | 11 | 5 | 5 | 1 | 5 | 4 | 2 |
| `historical_weather` | 10 | 5 | 5 | 0 | 4 | 4 | 2 |
| `location_comparison` | 7 | 2 | 5 | 0 | 1 | 4 | 2 |
| `activity_weather` | 15 | 7 | 7 | 1 | 4 | 6 | 5 |
| `expert_weather_param` | 9 | 5 | 4 | 0 | 4 | 2 | 3 |
| `weather_alert` | 19 | 13 | 4 | 2 | 4 | 9 | 6 |
| `seasonal_context` | 13 | 9 | 4 | 0 | 3 | 3 | 7 |
| `smalltalk_weather` | 15 | 14 | 1 | 0 | 8 | 2 | 5 |

## Top observations

1. **Ward cực kỳ sparse (33/45 cells empty, 0 cells ok).** Chỉ 14/184 câu ở ward scope. **Đây là priority #1** cho PR-B.2.
2. **`current_weather` chỉ có 6 câu** (intent quan trọng nhất nhưng ít) — cần augment lên ≥27 (3/cell × 9 cells).
3. **`smalltalk_weather` 14/15 câu ở city scope** — design đúng (smalltalk không cần location), nhưng có thể chỉ giữ 6-9 cells (city × 3 diff). 6 cells còn lại của smalltalk có thể skip.
4. **`location_comparison` 0 câu ward** — comparison logic between wards có thể đặc biệt; cần test.
5. **Difficulty skew:** 81 easy + 71 medium + 47 hard. Hard đang underrepresented (47/199 = 24%, lý tưởng ~33%).

## 15 POI cũ (abstention test set)

| id | intent | location | question (preview) |
|---|---|---|---|
| 9 | current_weather | Mỹ Đình | Cho mình biết thời tiết hiện tại ở khu vực Mỹ Đình với. |
| 10 | current_weather | Hồ Gươm | Bầu trời ở khu vực Hồ Gươm bây giờ trông như thế nào? |
| 12 | current_weather | Sân bay Nội Bài | Tầm nhìn hiện tại ở sân bay Nội Bài có ổn không? |
| 68 | temperature_query | Mỹ Đình | Nhiệt độ tối nay ở khu vực Mỹ Đình có xuống dưới 15 độ không |
| 90 | humidity_fog_query | Cao tốc Pháp Vân | Tầm nhìn trên đường cao tốc Pháp Vân sáng mai thế nào? |
| 104 | location_comparison | Mỹ Đình, Times City | So sánh thời tiết hiện tại ở Mỹ Đình và Times City giúp mình |
| 109 | activity_weather | Hồ Gươm | Chiều nay ở Hồ Gươm thời tiết có phù hợp để đi dạo không? |
| 110 | activity_weather | Sân Mỹ Đình | Tối nay ở Mỹ Đình mình chạy bộ có ổn không... |
| 113 | activity_weather | Công viên Cầu Giấy | Tối nay đưa trẻ con đi chơi ở công viên Cầu Giấy có lạnh quá... |
| 115 | activity_weather | Hồ Tây | Cuối tuần này đi chụp ảnh ở Hồ Tây thì thời tiết có đẹp không... |
| 119 | activity_weather | Hồ Gươm | Sáng chủ nhật ở Hồ Gươm đi bộ có bị ướt mưa không? |
| 120 | activity_weather | Sân Mỹ Đình | Chiều nay ở sân Mỹ Đình thời tiết có ổn để xem bóng đá... |
| 130 | expert_weather_param | Hồ Tây | Độ che phủ mây lúc hoàng hôn ở Hồ Tây chiều nay là bao nhiêu... |
| 153 | activity_weather | Hồ Tây | Chiều nay ở Hồ Tây ra ngoài có ổn không? |
| 162 | activity_weather | Mỹ Đình | Hôm nay thời tiết có phù hợp để tổ chức sự kiện ngoài trời ở... |

**Relabel rule (PR-B.2 chính thức):**
- `expected_clarification=True`
- `expected_tools=[]` (không gọi tool ngay; phải hỏi user trước)
- `gold_response_constraint`: "Phải hỏi lại quận/phường cụ thể (vì POI chỉ tham chiếu địa điểm, cần resolve về district/ward để query data)"

## Priority cells cho PR-B.2 (top 30 empty)

```
intent                    | scope    | difficulty | count
─────────────────────────────────────────────────────────
current_weather           | city     | hard       | 0
current_weather           | district | medium     | 0
current_weather           | district | hard       | 0
current_weather           | ward     | medium     | 0
current_weather           | ward     | hard       | 0
hourly_forecast           | city     | easy       | 0
hourly_forecast           | city     | hard       | 0
hourly_forecast           | ward     | hard       | 0
daily_forecast            | city     | medium     | 0
daily_forecast            | ward     | easy       | 0
daily_forecast            | ward     | hard       | 0
weather_overview          | city     | hard       | 0
weather_overview          | ward     | easy       | 0
weather_overview          | ward     | medium     | 0
weather_overview          | ward     | hard       | 0
rain_query                | ward     | hard       | 0
temperature_query         | city     | easy       | 0
temperature_query         | district | medium     | 0
temperature_query         | district | hard       | 0
temperature_query         | ward     | medium     | 0
temperature_query         | ward     | hard       | 0
wind_query                | district | hard       | 0
wind_query                | ward     | medium     | 0
wind_query                | ward     | hard       | 0
humidity_fog_query        | district | hard       | 0
humidity_fog_query        | ward     | easy       | 0
humidity_fog_query        | ward     | hard       | 0
historical_weather        | city     | medium     | 0
historical_weather        | district | hard       | 0
historical_weather        | ward     | easy       | 0
```

(Full 54 empty + 60 thin cells trong `coverage_tracker.csv`.)

## Plan PR-B.2 (batch đầu 50 câu mới)

Workflow Mode C:
1. Tôi propose 30 câu cho 10 cell rare nhất (ưu tiên ward + intent thiếu nhất).
2. User review, accept/edit/reject.
3. User dictate 5-10 câu edge case.
4. Tôi expand 10-15 câu paraphrase từ template.

Sau PR-B.2 batch01 → update `coverage_tracker.csv` (`count_new`, `count_total`, `status`).

## Reference

- `dataset_schema.md` — schema 16 columns chi tiết.
- `coverage_tracker.csv` — 135 rows tracker.
- `docs/Weather Intent Design.md` — canonical intent design.
- `docs/intent_disambiguation_rules.md` — confusion pair rules.
- `data/processed/dim_ward.csv` — canonical 126 ward + 31 district.
